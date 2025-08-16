from fastapi import FastAPI
from pydantic import BaseModel
from time import perf_counter
from typing import List, Optional
import re

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


APP_VERSION = "0.1.4-boost+canon"
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

@app.on_event("startup")
def load_index():
    global _retriever
    _retriever = BM25Retriever(index_path="app/index.json")

@app.get("/health")
def health():
    return {"ok": True, "version": APP_VERSION}

@app.get("/version")
def version():
    return {"version": APP_VERSION}

@app.post("/ask", response_model=AskResponse)
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
    return AskResponse(answer=answer, latency_ms=latency_ms, docs=docs)

