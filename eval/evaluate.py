import argparse, json, time, statistics, sys
from pathlib import Path
from typing import Dict, Any, List
import requests

# local metrics
try:
    from eval.metrics import recall_at_k, mrr_at_k, exact_match, token_f1
except ImportError:
    # fallback for "python -m eval.evaluate" when PYTHONPATH is weird
    from metrics import recall_at_k, mrr_at_k, exact_match, token_f1

def load_gold(path: Path) -> List[Dict[str, Any]]:
    """Supports lines like:
    {"id":"q1","question":"...","answer":"...","allowed_docs":["doc:1","doc:3"],"unanswerable":false}
    'allowed_docs' and 'unanswerable' are optional.
    """
    items = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            items.append(json.loads(line))
    return items

def post_ask(api: str, api_key: str, question: str, k: int, timeout: float = 10.0) -> Dict[str, Any]:
    headers = {"x-api-key": api_key} if api_key else {}
    t0 = time.perf_counter()
    r = requests.post(api, json={"question": question, "k": k}, headers=headers, timeout=timeout)
    dt_ms = (time.perf_counter() - t0) * 1000.0
    r.raise_for_status()
    data = r.json()
    data["_latency_ms"] = dt_ms
    return data

def main():
    p = argparse.ArgumentParser(description="Evaluate rag_service retrieval + extractive answers.")
    p.add_argument("--gold", required=True, type=Path, help="Path to gold.jsonl")
    p.add_argument("--api",  required=True, help="http://127.0.0.1:8010/ask")
    p.add_argument("--k", type=int, default=10)
    p.add_argument("--api-key", default="", help="dev key if your service requires it")
    p.add_argument("--limit", type=int, default=0, help="evaluate only first N items")
    args = p.parse_args()

    gold = load_gold(args.gold)
    if args.limit:
        gold = gold[: args.limit]

    per_item = []
    latencies = []
    recalls, mrrs, ems, f1s = [], [], [], []

    for row in gold:
        qid = row.get("id")
        question = row["question"]
        gold_answer = row.get("answer", "")
        allowed_docs = row.get("allowed_docs", [])  # optional
        unanswerable = bool(row.get("unanswerable", False))

        try:
            resp = post_ask(args.api, args.api_key, question, k=args.k)
        except requests.RequestException as e:
            print(f"[ERROR] qid={qid} request failed: {e}", file=sys.stderr)
            continue

        latencies.append(resp.get("_latency_ms", 0.0))

        # Expecting your service response like:
        # {
        #   "answer": "...",
        #   "docs": [{"doc_id":"sample:0","text":"..."}, ...],
        #   "latency_ms": 12.34
        # }
        answer = str(resp.get("answer", ""))
        docs = resp.get("docs", [])
        ranked_ids = [d.get("doc_id", "") for d in docs]

        # Retrieval metrics (only if allowed_docs provided)
        r_at_k = recall_at_k(ranked_ids, allowed_docs, k=args.k) if allowed_docs else None
        mrr_k  = mrr_at_k(ranked_ids, allowed_docs, k=args.k) if allowed_docs else None

        # Answer metrics (skip if unanswerable)
        if not unanswerable and gold_answer:
            em = exact_match(answer, gold_answer)
            f1 = token_f1(answer, gold_answer)
        else:
            em, f1 = None, None

        per_item.append({
            "id": qid,
            "recall@k": r_at_k,
            "mrr@k": mrr_k,
            "em": em,
            "f1": f1,
            "latency_ms": resp.get("_latency_ms"),
        })

        if r_at_k is not None: recalls.append(r_at_k)
        if mrr_k  is not None: mrrs.append(mrr_k)
        if em     is not None: ems.append(em)
        if f1     is not None: f1s.append(f1)

    summary = {
        "k": args.k,
        "count": len(per_item),
        "recall@k": round(sum(recalls)/len(recalls), 4) if recalls else None,
        "mrr@k":    round(sum(mrrs)/len(mrrs), 4) if mrrs else None,
        "em":       round(sum(ems)/len(ems), 4) if ems else None,
        "f1":       round(sum(f1s)/len(f1s), 4) if f1s else None,
        "p50_ms":   round(statistics.median(latencies), 2) if latencies else None,
        "p95_ms":   round(statistics.quantiles(latencies, n=100)[94], 2) if len(latencies) >= 20 else None,
    }

    print(json.dumps({"summary": summary, "items": per_item}, indent=2))

if __name__ == "__main__":
    main()

