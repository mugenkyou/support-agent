"""BM25 (Best Matching 25) Lexical Retriever."""

import math
from collections import Counter
from typing import Any, Dict, List, Optional
import numpy as np

from src.retrieval.filter import RetrievalFilter


class BM25Retriever:
    """BM25 (Best Matching 25) Lexical Retriever."""

    def __init__(
        self,
        candidates: List[Dict[str, Any]],
        filter_engine: Optional[RetrievalFilter] = None,
        k1: float = 1.5,
        b: float = 0.75,
    ):
        self.candidates = candidates
        self.filter = filter_engine or RetrievalFilter()
        self.k1 = k1
        self.b = b
        self.doc_lens: List[int] = []
        self.doc_freqs: Dict[str, int] = Counter()
        self.doc_term_freqs: List[Dict[str, int]] = []
        self.avgdl: float = 0.0
        self.N: int = len(candidates)
        self._build_index()

    def _tokenize(self, text: str) -> List[str]:
        return [w.lower() for w in text.split() if w]

    def _build_index(self):
        total_len = 0
        for cand in self.candidates:
            tokens = self._tokenize(cand["searchable_text"])
            tf = Counter(tokens)
            self.doc_term_freqs.append(tf)
            self.doc_lens.append(len(tokens))
            total_len += len(tokens)
            for term in tf.keys():
                self.doc_freqs[term] += 1

        self.avgdl = (total_len / self.N) if self.N > 0 else 1.0

    def _idf(self, term: str) -> float:
        df = self.doc_freqs.get(term, 0)
        return math.log((self.N - df + 0.5) / (df + 0.5) + 1.0)

    def retrieve(
        self,
        query_item: Dict[str, Any],
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        query_text = query_item.get("customer_message_raw", query_item.get("text", ""))
        q_tokens = self._tokenize(query_text)
        if not q_tokens:
            return []

        scores = np.zeros(self.N, dtype=float)
        for term in q_tokens:
            if term not in self.doc_freqs:
                continue
            idf = self._idf(term)
            for idx in range(self.N):
                tf = self.doc_term_freqs[idx].get(term, 0)
                if tf == 0:
                    continue
                d_len = self.doc_lens[idx]
                numerator = tf * (self.k1 + 1)
                denominator = tf + self.k1 * (1 - self.b + self.b * (d_len / self.avgdl))
                scores[idx] += idf * (numerator / denominator)

        top_indices = np.argsort(-scores)
        results = []
        for idx in top_indices:
            if len(results) >= top_k:
                break
            score = float(scores[idx])
            if score <= 0.0:
                break
            cand = self.candidates[idx]
            is_elig, _ = self.filter.is_retrieval_eligible(query_item, cand)
            if not is_elig:
                continue

            results.append({
                "retrieval_id": cand["retrieval_id"],
                "interaction_id": cand["interaction_id"],
                "score": round(score, 4),
                "customer_query": cand["customer_message_raw"],
                "historical_response": cand["historical_response_raw"],
                "created_ts": cand["created_ts"],
            })

        return results
