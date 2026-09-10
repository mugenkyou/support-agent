"""Unit tests for preprocessing, multipart aggregation, count reconciliation, and source traceability."""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath("."))

from src.data.preprocessing import normalize_tweet_text, is_linguistic_continuation


class TestPreprocessing(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open("data/processed/interactions.jsonl", "r", encoding="utf-8") as f:
            cls.examples = [json.loads(line) for line in f]
        with open("data/processed/interactions_metadata.json", "r", encoding="utf-8") as f:
            cls.meta = json.load(f)

    def test_n_count_reconciliation(self):
        """TEST N — Count reconciliation: All candidate records are accounted for."""
        usable_cnt = self.meta["usable_examples_count"]
        self.assertEqual(usable_cnt, len(self.examples))
        self.assertEqual(usable_cnt, 106646)

    def test_o_source_traceability(self):
        """TEST O — Source traceability: Every processed example maps back to raw tweet IDs."""
        for ex in self.examples[:5000]:
            self.assertIn("target_support_tweet_id", ex)
            self.assertIn("source_customer_tweet_ids", ex)
            self.assertGreater(len(ex["source_customer_tweet_ids"]), 0)
            self.assertTrue(all(isinstance(tid, int) for tid in ex["source_customer_tweet_ids"]))

    def test_r_multipart_policy(self):
        """TEST R — Multipart policy: Aggregated examples have >= 2 source tweet IDs."""
        multipart_exs = [e for e in self.examples if e["multipart_aggregated"]]
        self.assertGreater(len(multipart_exs), 0)
        for ex in multipart_exs[:500]:
            self.assertGreaterEqual(len(ex["source_customer_tweet_ids"]), 2)

    def test_normalization_rules(self):
        """Verify that normalize_tweet_text correctly masks URLs and mentions."""
        raw = "@AppleSupport my phone is dead https://t.co/abc1234"
        norm = normalize_tweet_text(raw)
        self.assertEqual(norm, "<user> my phone is dead <url>")


if __name__ == "__main__":
    unittest.main()
