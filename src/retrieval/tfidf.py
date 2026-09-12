"""Sparse TF-IDF Cosine Similarity Retriever."""

from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from src.retrieval.filter import RetrievalFilter


class TFIDFRetriever:
    """Sparse TF-IDF Cosine Similarity Retriever."""

    def __init__(
        self,
        candidates: List[Dict[str, Any]],
        filter_engine: Optional[RetrievalFilter] = None,
        max_features: int = 25000,
        ngram_range: Tuple[int, int] = (1, 2),
        min_df: int = 2,
    ):
        self.candidates = candidates
        self.filter = filter_engine or RetrievalFilter()
        actual_min_df = min(min_df, max(1, len(candidates)))

        self.vectorizer = TfidfVectorizer(
            max_features=max_features,
            ngram_range=ngram_range,
            min_df=actual_min_df,
            sublinear_tf=True,
            token_pattern=r"(?u)\b\w+\b|<url>|<user>",
        )

        texts = [c["searchable_text"] for c in candidates]
        self.candidate_matrix = self.vectorizer.fit_transform(texts) if texts else None

    def retrieve(
        self,
        query_item: Dict[str, Any],
        top_k: int = 5,
        target_intent: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        if self.candidate_matrix is None or len(self.candidates) == 0:
            return []

        query_text = query_item.get("customer_message_raw", query_item.get("text", ""))
        q_vec = self.vectorizer.transform([query_text])
        sims = (q_vec * self.candidate_matrix.T).toarray()[0]

        top_indices = np.argsort(-sims)
        results = []
        for idx in top_indices:
            if len(results) >= top_k:
                break
            score = float(sims[idx])
            if score <= 0.0:
                break
            cand = self.candidates[idx]
            is_elig, reason = self.filter.is_retrieval_eligible(query_item, cand)
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
