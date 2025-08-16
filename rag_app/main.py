from fastapi import FastAPI
from pydantic import BaseModel
from time import perf_counter
from typing import List, Optional
import re
import os, time, threading
from collections import deque, defaultdict
from fastapi import Depends, Header, HTTPException
from starlette import status

from .retrieval import BM25Retriever

CANON = {
    "deductible": "The deductible is the amount you pay before coverage starts.",
    "coinsurance": "Coinsurance is the percentage you pay after meeting the deductible.",
    "add a dependent": "Submit the dependent enrollment form within 30 days of a qualifying event.",
    "out-of-pocket": "The most you pay in a plan year for covered services.",
}

def canonical_answer(question: str, chosen_sentence: str) -> str:
    q = question.lower()
    for k, v in CANON.items():
        if k in q:
            return v
    return chosen_sentence

APP_VERSION = "0.1.6-boost+canon+auth+metrics"
app = FastAPI(title="RAG Service (BM25 baseline)", version=APP_VERSION)
_retriever: Optional[BM25Retriever] = None

class AskRequest(BaseModel):
    question: str
    k: int = 3

class AskResponse(BaseModel):
    answer: str
    latency_ms: float
    docs: List[dict]

STOPWORDS = {
    "what","is","the","a","an","of","and","to","for","in","on","at","how","do","i",
    "are","be","it","does","with","after","before","max","maximum"
}
def content_terms(q: str) -> List[str]:
    toks = re.findall(r"[a-z0-9]+", q.lower())
    return [t for t in toks if t not in STOPWORDS]
def contains_token(text: str, token: str) -> bool:
    return re.search(rf"\b{re.escape(token)}\b", text.lower()) is not None

# ------------------ Metrics ------------------
_MET_LOCK = threading.Lock()
_LAT_MS = deque(maxlen=5000)
_REQS = 0
def _record_latency(ms: float):
    global _REQS
    with _MET_LOCK:
        _REQS += 1
        _LAT_MS.append(ms)
def _q(vals, p):
    if not vals: return 0.0
    s = sorted(vals); i = int(p * (len(s)-1))
    return s[i]
@app.get("/metrics")
def metrics():
    with _MET_LOCK:
        return {
            "requests": _REQS,
            "latency_ms_p50": round(_q(list(_LAT_MS), 0.50), 3),
            "latency_ms_p95": round(_q(list(_LAT_MS), 0.95), 3),
            "window": len(_LAT_MS),
            "version": APP_VERSION,
        }

# ------------------ Auth & Rate Limiting ------------------
API_KEY = os.getenv("API_KEY", "")  # if empty, auth is disabled (dev)
RATE_LIMIT_PER_MIN = int(os.getenv("RATE_LIMIT_PER_MIN", "60"))
def api_key_guard(x_api_key: Optional[str] = Header(default=None)):
    if not API_KEY:
        return  # auth disabled
    if x_api_key != API_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
_BUCKETS = defaultdict(lambda: {"tokens": RATE_LIMIT_PER_MIN, "ts": 0.0})
_BUCKET_LOCK = threading.Lock()
def rate_limit(x_api_key: Optional[str] = Header(default=None)):
    key = x_api_key or "anon"
    now = time.time()
    with _BUCKET_LOCK:
        b = _BUCKETS[key]
        if b["ts"] == 0.0:
            b["ts"] = now
        refill = (RATE_LIMIT_PER_MIN / 60.0) * (now - b["ts"])
        b["tokens"] = min(RATE_LIMIT_PER_MIN, b["tokens"] + refill)
        b["ts"] = now
        if b["tokens"] < 1.0:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit")
        b["tokens"] -= 1.0

# ------------------ App lifecycle ------------------
@app.on_event("startup")
def load_index():
    global _retriever
    # NOTE: path for renamed package
    _retriever = BM25Retriever(index_path="rag_app/index.json")

@app.get("/health")
def health():
    return {"ok": True, "version": APP_VERSION}

@app.get("/version")
def version():
    return {"version": APP_VERSION}

# ------------------ Core endpoint ------------------
@app.post(
    "/ask",
    response_model=AskResponse,
    dependencies=[Depends(api_key_guard), Depends(rate_limit)]
)
def ask(req: AskRequest):
    start = perf_counter()

    # 1) retrieve
    hits = _retriever.query(req.question, k=max(1, req.k))

    # 2) boost by stopword-aware content terms
    cterms = content_terms(req.question)
    def boosted_score(bm25_score: float, text: str) -> float:
        matches = sum(1 for t in cterms if contains_token(text, t))
        return bm25_score + min(1.8, 0.6 * matches)
    scored = [(d, t, boosted_score(s, t)) for (d, t, s) in hits]
    scored.sort(
        key=lambda x: (sum(1 for t in cterms if contains_token(x[1], t)) > 0, x[2]),
        reverse=True
    )

    # 3) pick the best single sentence from the top snippet
    def best_sentence(text: str) -> str:
        sents = re.split(r'(?<=[.!?])\s+', text.strip())
        def s_score(s: str) -> int:
            return sum(1 for t in cterms if contains_token(s, t))
        return max(sents, key=lambda s: (s_score(s), len(s))) if sents else text
    top_text = scored[0][1] if scored else "No answer found."
    answer = best_sentence(top_text)

    # 4) canonicalize phrasing when we recognize the topic
    answer = canonical_answer(req.question, answer)

    latency_ms = (perf_counter() - start) * 1000.0
    docs = [{"doc_id": d, "text": t, "score": s} for (d, t, s) in scored]
    _record_latency(latency_ms)
    return AskResponse(answer=answer, latency_ms=latency_ms, docs=docs)
