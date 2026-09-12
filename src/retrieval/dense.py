"""Dense Semantic Embedding Retriever.

Provides dense semantic vector representation and nearest-neighbor search.
Uses L2-normalized dense embeddings with cosine similarity.
"""

from typing import Any, Dict, List, Optional
import numpy as np
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer

from src.retrieval.filter import RetrievalFilter


class DenseEmbeddingRetriever:
    """Dense Semantic Retriever using Latent Semantic / Embedding Projections."""

    def __init__(
        self,
        candidates: List[Dict[str, Any]],
        filter_engine: Optional[RetrievalFilter] = None,
        embedding_dim: int = 128,
    ):
        self.candidates = candidates
        self.filter = filter_engine or RetrievalFilter()
        self.embedding_dim = min(embedding_dim, max(2, len(candidates) - 1)) if candidates else embedding_dim

        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            max_features=20000,
            sublinear_tf=True,
            token_pattern=r"(?u)\b\w+\b|<url>|<user>",
        )
        self.svd = TruncatedSVD(n_components=self.embedding_dim, random_state=42)

        texts = [c["searchable_text"] for c in candidates]
        if texts:
            tfidf_mat = self.vectorizer.fit_transform(texts)
            raw_embeddings = self.svd.fit_transform(tfidf_mat)
            # L2 normalize
            norms = np.linalg.norm(raw_embeddings, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            self.embeddings = raw_embeddings / norms
        else:
            self.embeddings = np.zeros((0, self.embedding_dim))

    def retrieve(
        self,
        query_item: Dict[str, Any],
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        if len(self.candidates) == 0 or self.embeddings.shape[0] == 0:
            return []

        query_text = query_item.get("customer_message_raw", query_item.get("text", ""))
        q_tfidf = self.vectorizer.transform([query_text])
        q_emb = self.svd.transform(q_tfidf)
        norm = np.linalg.norm(q_emb)
        if norm > 0:
            q_emb = q_emb / norm

        sims = np.dot(self.embeddings, q_emb[0])
        top_indices = np.argsort(-sims)

        results = []
        for idx in top_indices:
            if len(results) >= top_k:
                break
            score = float(sims[idx])
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
