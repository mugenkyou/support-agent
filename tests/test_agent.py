"""Tests for End-to-End SupportAgent Pipeline."""

import unittest
from src.agent.support_agent import SupportAgent
from src.retrieval.filter import RetrievalFilter
from src.retrieval.tfidf import TFIDFRetriever


class TestAgent(unittest.TestCase):
    def setUp(self):
        candidates = [
            {
                "retrieval_id": "cand_1",
                "interaction_id": "inter_1",
                "created_ts": 1500000000,
                "customer_message_raw": "battery percentage drops fast",
                "searchable_text": "battery percentage drops fast",
                "historical_response_raw": "Go to Settings > Battery to view usage. Force restart if needed.",
                "split": "train",
            }
        ]
        retriever = TFIDFRetriever(candidates, RetrievalFilter())
        self.agent = SupportAgent(retriever=retriever)

    def test_end_to_end_prediction_pipeline(self):
        result = self.agent.predict(
            conversation_history=[],
            customer_message="my battery dies quickly in 2 hours",
        )
        self.assertEqual(result["intent"], "battery_drain_and_charging_issues")
        self.assertEqual(result["escalation_decision"], "PUBLIC_TROUBLESHOOTING")
        self.assertGreaterEqual(len(result["retrieval_candidates"]), 0)
        self.assertTrue(result["safety_passed"])
        self.assertIn("draft_response", result)
        self.assertIn("model_metadata", result)


if __name__ == "__main__":
    unittest.main()
