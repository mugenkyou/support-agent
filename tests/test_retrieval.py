"""Tests for Sparse, Dense, Hybrid Retrievers and Template Diversifier."""

import unittest
from src.retrieval.bm25 import BM25Retriever
from src.retrieval.dense import DenseEmbeddingRetriever
from src.retrieval.filter import RetrievalFilter
from src.retrieval.hybrid import HybridFusionRetriever
from src.retrieval.rerank import TemplateDiversifier
from src.retrieval.tfidf import TFIDFRetriever


class TestRetrieval(unittest.TestCase):
    def setUp(self):
        self.candidates = [
            {
                "retrieval_id": "cand_1",
                "interaction_id": "inter_1",
                "created_ts": 1500000000,
                "customer_message_raw": "my battery dies quickly in 2 hours",
                "searchable_text": "my battery dies quickly in 2 hours",
                "historical_response_raw": "Check Settings > Battery for high usage apps. Send us a DM if this continues.",
                "split": "train",
            },
            {
                "retrieval_id": "cand_2",
                "interaction_id": "inter_2",
                "created_ts": 1500000010,
                "customer_message_raw": "battery percentage jumps from 50% to 10%",
                "searchable_text": "battery percentage jumps from 50% to 10%",
                "historical_response_raw": "Try a force restart of your iPhone by holding power and home buttons.",
                "split": "train",
            },
            {
                "retrieval_id": "cand_3",
                "interaction_id": "inter_3",
                "created_ts": 1500000020,
                "customer_message_raw": "wifi disconnects repeatedly",
                "searchable_text": "wifi disconnects repeatedly",
                "historical_response_raw": "Go to Settings > General > Reset > Reset Network Settings.",
                "split": "train",
            },
            {
                "retrieval_id": "cand_4",
                "interaction_id": "inter_4",
                "created_ts": 1500000030,
                "customer_message_raw": "shattered my screen need repair",
                "searchable_text": "shattered my screen need repair",
                "historical_response_raw": "You can schedule a Genius Bar appointment at locate.apple.com.",
                "split": "train",
            },
        ]
        self.filter = RetrievalFilter()

    def test_tfidf_retriever(self):
        retriever = TFIDFRetriever(self.candidates, self.filter)
        query = {"interaction_id": "query_1", "customer_message_raw": "my battery is draining fast", "created_ts": 1500000100}
        results = retriever.retrieve(query, top_k=2)
        self.assertGreater(len(results), 0)
        self.assertIn("cand_1", [r["retrieval_id"] for r in results])

    def test_bm25_retriever(self):
        retriever = BM25Retriever(self.candidates, self.filter)
        query = {"interaction_id": "query_2", "customer_message_raw": "wifi disconnecting", "created_ts": 1500000100}
        results = retriever.retrieve(query, top_k=2)
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0]["retrieval_id"], "cand_3")

    def test_dense_retriever(self):
        retriever = DenseEmbeddingRetriever(self.candidates, self.filter, embedding_dim=4)
        query = {"interaction_id": "query_3", "customer_message_raw": "battery percentage drops", "created_ts": 1500000100}
        results = retriever.retrieve(query, top_k=2)
        self.assertGreater(len(results), 0)

    def test_hybrid_fusion_retriever(self):
        tfidf = TFIDFRetriever(self.candidates, self.filter)
        dense = DenseEmbeddingRetriever(self.candidates, self.filter, embedding_dim=4)
        hybrid = HybridFusionRetriever(tfidf, dense)
        query = {"interaction_id": "query_4", "customer_message_raw": "screen broke need repair", "created_ts": 1500000100}
        results = hybrid.retrieve(query, top_k=2)
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0]["retrieval_id"], "cand_4")

    def test_template_diversifier(self):
        diversifier = TemplateDiversifier()
        items = [
            {"retrieval_id": "r1", "historical_response": "Send us a DM with your IMEI."},
            {"retrieval_id": "r2", "historical_response": "Please send a direct message with details."},
            {"retrieval_id": "r3", "historical_response": "Schedule a repair at locate.apple.com."},
        ]
        div_res = diversifier.diversify(items, top_k=2, max_per_family=1)
        self.assertEqual(len(div_res), 2)
        families = [diversifier.extract_template_family(x["historical_response"]) for x in div_res]
        self.assertEqual(len(set(families)), 2)


if __name__ == "__main__":
    unittest.main()
