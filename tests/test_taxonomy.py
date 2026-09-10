"""Unit tests for Phase 3 Intent Taxonomy validation (Tests A, B, C, L)."""

import json
import unittest
from pathlib import Path

from src.taxonomy.loader import load_taxonomy, load_taxonomy_dict, get_all_intent_names, validate_intent_name

ROOT = Path(__file__).resolve().parent.parent


class TestTaxonomy(unittest.TestCase):
    def setUp(self):
        self.taxonomy = load_taxonomy()
        self.taxonomy_dict = load_taxonomy_dict()
        self.golden_path = ROOT / "evaluations" / "golden_set" / "golden_set.jsonl"

    def test_test_a_intent_completeness_in_golden(self):
        """TEST A: Every golden example has exactly one valid final intent."""
        self.assertTrue(self.golden_path.exists(), "Golden set file must exist")
        with open(self.golden_path, "r", encoding="utf-8") as f:
            for line_idx, line in enumerate(f):
                if not line.strip():
                    continue
                record = json.loads(line)
                intent = record.get("intent")
                self.assertIsNotNone(intent, f"Line {line_idx} missing intent")
                self.assertIsInstance(intent, str, f"Line {line_idx} intent must be single string")
                self.assertTrue(validate_intent_name(intent), f"Line {line_idx} has invalid intent {intent}")

    def test_test_b_valid_intent_values(self):
        """TEST B: Every defined intent name adheres to canonical naming conventions."""
        valid_intents = get_all_intent_names()
        self.assertEqual(len(valid_intents), 11, "Taxonomy must contain exactly 11 intents")
        for name in valid_intents:
            self.assertTrue(name.islower(), f"Intent name {name} must be lowercase")
            self.assertRegex(name, r"^[a-z_]+$", f"Intent name {name} must use snake_case")

    def test_test_c_definition_completeness(self):
        """TEST C: Every intent contains complete operational specifications."""
        for intent in self.taxonomy.intents:
            self.assertTrue(len(intent.name.strip()) > 0, "Intent name cannot be empty")
            self.assertTrue(len(intent.definition.strip()) > 20, f"Definition too short for {intent.name}")
            self.assertGreaterEqual(len(intent.inclusion_criteria), 2, f"Insufficient inclusion criteria for {intent.name}")
            self.assertGreaterEqual(len(intent.exclusion_criteria), 2, f"Insufficient exclusion criteria for {intent.name}")
            self.assertGreaterEqual(len(intent.positive_examples), 3, f"Insufficient positive examples for {intent.name}")
            self.assertGreaterEqual(len(intent.negative_examples), 2, f"Insufficient negative examples for {intent.name}")
            self.assertGreaterEqual(len(intent.boundary_cases), 1, f"Insufficient boundary cases for {intent.name}")
            support_notes = intent.support_behavior_notes
            if isinstance(support_notes, list):
                self.assertTrue(len(support_notes) > 0, f"Missing support notes for {intent.name}")
            else:
                self.assertTrue(len(str(support_notes).strip()) > 5, f"Missing support notes for {intent.name}")

    def test_test_l_taxonomy_determinism(self):
        """TEST L: Serializing taxonomy produces deterministic JSON structure."""
        dict1 = load_taxonomy_dict()
        dict2 = load_taxonomy_dict()
        self.assertEqual(json.dumps(dict1, sort_keys=True), json.dumps(dict2, sort_keys=True))


if __name__ == "__main__":
    unittest.main()
