# Production RAG Service — Starter Kit

Hybrid retrieval (BM25 + vectors) + reranking, with evals and monitoring.

## Acceptance Criteria (edit targets as needed)
- Recall@10 ≥ 0.80; Answer F1 ≥ 0.70 (or EM ≥ 0.60)
- p95 latency ≤ 800 ms (≥100 queries); p50 ≤ 300 ms
- Cost/1k queries within budget; cache hit‑rate ≥ 30%
- API‑key auth + rate limiting
- Docker + one‑click deploy (Render/Fly/Cloud Run)
- README benchmarks table + Loom demo

## Quickstart
```bash
# install
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# run
make run
# or
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Endpoints
- `GET /health` → `{"ok": true}`
- `POST /ask` → `{ "question": "...", "answer": "...", "latency_ms": 0 }`

## Evaluate
Place 50 Q/A pairs in `eval/gold.jsonl`:
```json
{"question":"...", "answer":"..."}
```
Then implement `eval/evaluate.py` to compute Recall@k/MRR/answer F1.

## Benchmarks (fill these)
<!-- METRICS:BEGIN -->
| Metric      | Value            |
|-------------|------------------|
| Answer F1   | 1.00 (toy)       |
| Recall@10   | 1.00 (toy)       |
| p50 latency | 0.199 ms (local) |
| p95 latency | 0.355 ms (local) |
<!-- METRICS:END -->


## Notes
- Start with BM25 baseline (rank_bm25) + sentence embeddings (sentence-transformers) + reranker (optional).
- Add auth (API key), rate limiting, and structured logging.
