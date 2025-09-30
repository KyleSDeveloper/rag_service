# eval/metrics.py
from collections import Counter
import re
from typing import Iterable, List

_WS = re.compile(r"\s+")

def norm(s: str) -> str:
    return _WS.sub(" ", s.lower().strip())

def exact_match(pred: str, gold: str) -> float:
    return 1.0 if norm(pred) == norm(gold) else 0.0

def token_f1(pred: str, gold: str) -> float:
    p_tokens, g_tokens = norm(pred).split(), norm(gold).split()
    if not p_tokens or not g_tokens:
        return 0.0
    p, g = Counter(p_tokens), Counter(g_tokens)
    overlap = sum((p & g).values())
    if overlap == 0:
        return 0.0
    precision = overlap / sum(p.values())
    recall    = overlap / sum(g.values())
    return 2 * precision * recall / (precision + recall)

def recall_at_k(ranked_ids: List[str], gold_ids: Iterable[str], k: int = 10) -> float:
    return 1.0 if set(ranked_ids[:k]) & set(gold_ids) else 0.0

def mrr_at_k(ranked_ids: List[str], gold_ids: Iterable[str], k: int = 10) -> float:
    gold = set(gold_ids)
    for i, doc_id in enumerate(ranked_ids[:k], start=1):
        if doc_id in gold:
            return 1.0 / i
    return 0.0
