"""Tests for Central Retrieval Filter and Leakage Controls."""

import unittest
from src.retrieval.filter import RetrievalFilter


class TestRetrievalFilter(unittest.TestCase):
    def setUp(self):
        self.filter = RetrievalFilter(golden_set_path="evaluations/golden_set/golden_set.jsonl")

    def test_self_retrieval_excluded(self):
        query = {"interaction_id": "inter_001", "created_ts": 1500000000}
        cand = {"interaction_id": "inter_001", "created_ts": 1490000000, "split": "train"}
        is_elig, reason = self.filter.is_retrieval_eligible(query, cand)
        self.assertFalse(is_elig)
        self.assertEqual(reason, "EXCLUDED_SELF_INTERACTION")

    def test_future_temporal_candidate_excluded(self):
        query = {"interaction_id": "inter_001", "created_ts": 1500000000}
        cand = {"interaction_id": "inter_002", "created_ts": 1500000100, "split": "train"}
        is_elig, reason = self.filter.is_retrieval_eligible(query, cand)
        self.assertFalse(is_elig)
        self.assertEqual(reason, "EXCLUDED_FUTURE_TEMPORAL_VIOLATION")

    def test_golden_set_candidate_excluded(self):
        if self.filter.golden_interaction_ids:
            gold_iid = next(iter(self.filter.golden_interaction_ids))
            query = {"interaction_id": "inter_test_999", "created_ts": 1600000000}
            cand = {"interaction_id": gold_iid, "created_ts": 1500000000, "split": "train"}
            is_elig, reason = self.filter.is_retrieval_eligible(query, cand)
            self.assertFalse(is_elig)
            self.assertEqual(reason, "EXCLUDED_GOLDEN_SET_RECORD")

    def test_valid_past_train_candidate_allowed(self):
        query = {"interaction_id": "inter_001", "created_ts": 1500000000}
        cand = {"interaction_id": "inter_99999", "created_ts": 1490000000, "split": "train"}
        is_elig, reason = self.filter.is_retrieval_eligible(query, cand)
        self.assertTrue(is_elig)
        self.assertIsNone(reason)


if __name__ == "__main__":
    unittest.main()
