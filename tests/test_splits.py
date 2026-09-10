"""Unit tests for split strategies, conversation leakage, and split reproducibility."""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath("."))

from src.data.splitting import conversation_split, customer_split, temporal_split, evaluate_split_overlap


class TestSplits(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open("data/processed/interactions.jsonl", "r", encoding="utf-8") as f:
            cls.examples = [json.loads(line) for line in f]
        with open("data/processed/splits.json", "r", encoding="utf-8") as f:
            cls.splits_data = json.load(f)

    def test_b_conversation_leakage_in_conv_split(self):
        """TEST B — Conversation leakage: No conversation crosses partitions in ConversationSplit."""
        conv_split = self.splits_data["conversation_split"]
        conv_overlap = self.splits_data["conversation_overlap_audit"]["conversation_overlap"]
        self.assertEqual(conv_overlap["train_dev_overlap_count"], 0)
        self.assertEqual(conv_overlap["train_test_overlap_count"], 0)
        self.assertEqual(conv_overlap["dev_test_overlap_count"], 0)

    def test_c_customer_leakage_in_cust_split(self):
        """TEST C — Customer leakage: No customer crosses partitions in CustomerSplit."""
        cust_overlap = self.splits_data["customer_overlap_audit"]["customer_overlap"]
        self.assertEqual(cust_overlap["train_dev_overlap_count"], 0)
        self.assertEqual(cust_overlap["train_test_overlap_count"], 0)
        self.assertEqual(cust_overlap["dev_test_overlap_count"], 0)

    def test_l_m_split_reproducibility(self):
        """TEST L & M — Split reproducibility: Same seed produces identical partition assignments."""
        split_1 = conversation_split(self.examples[:1000], seed=42)
        split_2 = conversation_split(self.examples[:1000], seed=42)
        self.assertEqual(split_1["train"], split_2["train"])
        self.assertEqual(split_1["dev"], split_2["dev"])
        self.assertEqual(split_1["test"], split_2["test"])

        split_3 = conversation_split(self.examples[:1000], seed=999)
        self.assertNotEqual(split_1["train"], split_3["train"])


if __name__ == "__main__":
    unittest.main()
