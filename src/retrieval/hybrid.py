"""Hybrid Lexical + Dense Fusion Retriever.

Implements Reciprocal Rank Fusion (RRF) and Score Interpolation.
"""

from collections import defaultdict
from typing import Any, Dict, List, Optional


class HybridFusionRetriever:
    """Combines sparse lexical and dense semantic retrievers using Reciprocal Rank Fusion."""

    def __init__(
        self,
        sparse_retriever: Any,
        dense_retriever: Any,
        rrf_k: int = 60,
        sparse_weight: float = 0.5,
        dense_weight: float = 0.5,
    ):
        self.sparse_retriever = sparse_retriever
        self.dense_retriever = dense_retriever
        self.rrf_k = rrf_k
        self.sparse_weight = sparse_weight
        self.dense_weight = dense_weight

    def retrieve(
        self,
        query_item: Dict[str, Any],
        top_k: int = 5,
        candidate_pool_multiplier: int = 4,
    ) -> List[Dict[str, Any]]:
        n_fetch = top_k * candidate_pool_multiplier
        sparse_results = self.sparse_retriever.retrieve(query_item, top_k=n_fetch)
        dense_results = self.dense_retriever.retrieve(query_item, top_k=n_fetch)

        rrf_scores: Dict[str, float] = defaultdict(float)
        cand_map: Dict[str, Dict[str, Any]] = {}

        for rank, res in enumerate(sparse_results):
            cid = res["retrieval_id"]
            rrf_scores[cid] += self.sparse_weight * (1.0 / (self.rrf_k + rank + 1))
            cand_map[cid] = res

        for rank, res in enumerate(dense_results):
            cid = res["retrieval_id"]
            rrf_scores[cid] += self.dense_weight * (1.0 / (self.rrf_k + rank + 1))
            if cid not in cand_map:
                cand_map[cid] = res

        # Sort by RRF score
        sorted_ids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)
        results = []
        for cid in sorted_ids[:top_k]:
            item = cand_map[cid].copy()
            item["hybrid_score"] = round(float(rrf_scores[cid]), 6)
            results.append(item)

        return results
