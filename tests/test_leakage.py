"""Unit tests for leakage audits: Target leakage, Future message leakage, Retrieval leakage."""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath("."))

from src.data.leakage import verify_target_leakage, verify_future_message_leakage, RetrievalFilter


class TestLeakage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open("data/processed/interactions.jsonl", "r", encoding="utf-8") as f:
            cls.examples = [json.loads(line) for line in f]

    def test_f_target_leakage(self):
        """TEST F — Target leakage: Historical target response cannot occur in model input/context."""
        result = verify_target_leakage(self.examples)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["violations_count"], 0)

    def test_g_future_message_leakage(self):
        """TEST G — Future message leakage: Future customer/support messages cannot enter context."""
        result = verify_future_message_leakage(self.examples)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["future_violations_count"], 0)

    def test_h_timestamp_ordering(self):
        """TEST H — Timestamp ordering: Context timestamps obey causal non-lookahead rule."""
        for ex in self.examples[:5000]:
            target_ts = ex["created_ts"]
            for ctx in ex["context"]:
                self.assertLessEqual(ctx["created_ts"], target_ts, "Context timestamp must be <= target timestamp")

    def test_j_retrieval_exclusion(self):
        """TEST J — Retrieval exclusion: Evaluation examples cannot retrieve themselves or same response."""
        retrieval_filter = RetrievalFilter()
        query_ex = self.examples[-1]
        candidate_pool = self.examples[:5000] + [query_ex]

        filtered = retrieval_filter.filter_candidate_pool(query_ex, candidate_pool, strict_temporal=True)
        self.assertFalse(any(c["interaction_id"] == query_ex["interaction_id"] for c in filtered))
        self.assertFalse(any(c["target_support_tweet_id"] == query_ex["target_support_tweet_id"] for c in filtered))

    def test_k_temporal_retrieval_leakage(self):
        """TEST K — Temporal retrieval leakage: Retrieved records strictly obey temporal policy (t < query.t)."""
        retrieval_filter = RetrievalFilter()
        query_ex = self.examples[5000]
        candidate_pool = self.examples

        filtered = retrieval_filter.filter_candidate_pool(query_ex, candidate_pool, strict_temporal=True)
        for cand in filtered:
            self.assertLess(cand["created_ts"], query_ex["created_ts"], "Retrieved candidate must be strictly in the past")


if __name__ == "__main__":
    unittest.main()
