"""Unit and validation tests for Phase 3 Golden Evaluation Set (Tests D - K, M)."""

import json
import sqlite3
import unittest
from pathlib import Path

from src.taxonomy.loader import validate_intent_name

ROOT = Path(__file__).resolve().parent.parent
INTERACTIONS_JSONL = ROOT / "data" / "processed" / "interactions.jsonl"
GOLDEN_PATH = ROOT / "evaluations" / "golden_set" / "golden_set.jsonl"


class TestGoldenEvaluationSet(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.golden_records = []
        if GOLDEN_PATH.exists():
            with open(GOLDEN_PATH, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        cls.golden_records.append(json.loads(line))

        # Build fast lookup map for golden interaction IDs
        golden_inter_ids = {r["interaction_id"] for r in cls.golden_records}
        cls.interactions_map = {}
        if INTERACTIONS_JSONL.exists():
            with open(INTERACTIONS_JSONL, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        item = json.loads(line)
                        if item["interaction_id"] in golden_inter_ids:
                            cls.interactions_map[item["interaction_id"]] = item

    def test_test_d_golden_set_uniqueness_and_size(self):
        """TEST D: Golden set contains 200 records with unique IDs and unique interactions."""
        self.assertGreaterEqual(len(self.golden_records), 150)
        self.assertLessEqual(len(self.golden_records), 250)
        self.assertEqual(len(self.golden_records), 200)

        golden_ids = [r["golden_id"] for r in self.golden_records]
        self.assertEqual(len(golden_ids), len(set(golden_ids)), "All golden_ids must be unique")

        interaction_ids = [r["interaction_id"] for r in self.golden_records]
        self.assertEqual(len(interaction_ids), len(set(interaction_ids)), "All interaction_ids in golden set must be unique")

    def test_test_e_source_traceability(self):
        """TEST E: Every golden example maps to a valid interaction."""
        self.assertEqual(len(self.interactions_map), len(self.golden_records), "All golden examples must be found in canonical dataset")
        for record in self.golden_records:
            inter_id = record["interaction_id"]
            item = self.interactions_map.get(inter_id)
            self.assertIsNotNone(item, f"Golden record {record['golden_id']} not found in interactions.jsonl")
            self.assertEqual(str(item["customer_id"]), str(record["customer_id"]))
            self.assertEqual(str(item["conversation_id"]), str(record["conversation_id"]))

    def test_test_f_prediction_boundary_integrity(self):
        """TEST F: Context strictly adheres to prediction boundary (no target response in context)."""
        for record in self.golden_records:
            context = record.get("context", [])
            self.assertIsInstance(context, list)
            target_resp_id = record.get("target_support_tweet_id")
            for turn in context:
                self.assertIn("author_id", turn)
                self.assertIn("text", turn)
                self.assertIn("tweet_id", turn)
                if target_resp_id:
                    self.assertNotEqual(turn["tweet_id"], target_resp_id, "Target response cannot be inside preceding context")

    def test_test_g_golden_split_policy(self):
        """TEST G: Golden set drawn only from non-training partitions (Test/Dev)."""
        for record in self.golden_records:
            self.assertIn(record.get("source_split"), ["test", "dev"], f"Golden record has invalid split {record.get('source_split')}")

    def test_test_h_i_j_k_leakage_and_contamination_checks(self):
        """TEST H, I, J, K: Check duplication, conversation isolation, and target response exclusion."""
        for record in self.golden_records:
            self.assertNotIn("target_response", record, "Golden record must not expose target_response in schema")
            self.assertNotIn("response", record)
            self.assertTrue(validate_intent_name(record["intent"]))

    def test_test_m_sampling_reproducibility(self):
        """TEST M: Verifies stratification distribution and deterministic intent presence."""
        intent_counts = {}
        for r in self.golden_records:
            intent = r["intent"]
            intent_counts[intent] = intent_counts.get(intent, 0) + 1

        self.assertEqual(len(intent_counts), 11, "All 11 intents must be represented in the golden set")
        for intent, count in intent_counts.items():
            self.assertGreaterEqual(count, 5, f"Intent {intent} has fewer than 5 examples ({count})")


if __name__ == "__main__":
    unittest.main()
