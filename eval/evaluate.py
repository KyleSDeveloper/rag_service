import argparse, json, requests, re, sys, inspect

def safe_mean(xs): 
    return sum(xs)/max(1, len(xs))

def f1(a,b):
    tok=lambda s: re.findall(r"[a-z0-9]+", s.lower())
    A,B=tok(a),tok(b)
    if not A and not B: return 1.0
    if not A or not B: return 0.0
    common=0; used=[False]*len(B)
    for x in A:
        for j,y in enumerate(B):
            if not used[j] and x==y:
                common+=1; used[j]=True; break
    pr=common/len(A); rc=common/len(B)
    return 0.0 if pr+rc==0 else 2*pr*rc/(pr+rc)

def contains(sub, text):
    return sub.lower().strip() in text.lower()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--gold", required=True)
    ap.add_argument("--api", default="http://localhost:8000/ask")
    ap.add_argument("--k", type=int, default=5)
    args=ap.parse_args()

    gold=[json.loads(l) for l in open(args.gold, encoding="utf-8") if l.strip()]
    f1s, substr_hits, recall_hits, n_used = [], [], [], 0

    for rec in gold:
        q, a = rec["question"], rec.get("answer","").strip()
        if not a: 
            continue
        n_used += 1
        resp = requests.post(args.api, json={"question": q, "k": args.k}, timeout=30).json()
        pred = resp.get("answer","")
        docs = resp.get("docs", [])
        f1s.append(f1(pred, a))
        substr_hits.append(1.0 if contains(a, pred) else 0.0)
        recall_hits.append(1.0 if any(contains(a, d.get("text","")) for d in docs) else 0.0)

    print(f"Evaluator path: {inspect.getsourcefile(sys.modules[__name__])}")
    print(f"Used {n_used} answered gold items (of {len(gold)} total)")
    print(f"Answer F1 (mean): {safe_mean(f1s):.3f}")
    print(f"Substring match rate (pred contains gold): {safe_mean(substr_hits):.3f}")
    print(f"Retrieval Recall@{args.k} (any doc contains gold): {safe_mean(recall_hits):.3f}")

if __name__ == "__main__":
    main()
