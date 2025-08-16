import json, re
from typing import List, Tuple
from rank_bm25 import BM25Okapi
from loguru import logger

def _tok(s: str) -> List[str]:
    return re.findall(r"[a-z0-9]+", s.lower())

class BM25Retriever:
    def __init__(self, index_path: str):
        with open(index_path, "r", encoding="utf-8") as f:
            entries = json.load(f)
        self.docs = [e["text"] for e in entries]
        self.ids  = [e["doc_id"] for e in entries]
        self.tokens = [_tok(d) for d in self.docs]
        self.bm25 = BM25Okapi(self.tokens)
        logger.info(f"Loaded {len(self.docs)} snippets")

    def query(self, question: str, k: int = 5) -> List[Tuple[str,str,float]]:
        scores = self.bm25.get_scores(_tok(question))
        top = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)[:k]
        return [(self.ids[i], self.docs[i], float(s)) for i, s in top]
