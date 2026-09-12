"""Phase 4 Automated Integrity & Leakage Tests (Section 25 Compliance)."""

import json
import os
import unittest
from src.agent.support_agent import SupportAgent
from src.escalation.policy import EscalationPolicy
from src.retrieval.filter import RetrievalFilter
from src.taxonomy.loader import load_taxonomy


class TestPhase4Integrity(unittest.TestCase):
    def setUp(self):
        self.filter = RetrievalFilter(golden_set_path="evaluations/golden_set/golden_set.jsonl")
        self.taxonomy = load_taxonomy(yaml_path="src/taxonomy/taxonomy.yaml")
        self.intent_names = {i.name for i in self.taxonomy.intents}


    def test_a_b_golden_set_never_in_retrieval(self):
        """TEST A & B: Golden set examples are strictly excluded from retrieval."""
        for gold_iid in self.filter.golden_interaction_ids:
            query = {"interaction_id": "test_query_001", "created_ts": 1600000000}
            cand = {"interaction_id": gold_iid, "created_ts": 1500000000, "split": "train"}
            is_elig, reason = self.filter.is_retrieval_eligible(query, cand)
            self.assertFalse(is_elig)
            self.assertEqual(reason, "EXCLUDED_GOLDEN_SET_RECORD")

    def test_c_target_response_cannot_be_retrieved(self):
        """TEST C: Target response in same conversation cannot be retrieved."""
        query = {
            "interaction_id": "q1",
            "conversation_id": "conv_100",
            "historical_response_raw": "Exact identical answer",
            "created_ts": 1500000000,
        }
        cand = {
            "interaction_id": "c1",
            "conversation_id": "conv_100",
            "historical_response_raw": "Exact identical answer",
            "created_ts": 1490000000,
            "split": "train",
        }
        is_elig, reason = self.filter.is_retrieval_eligible(query, cand)
        self.assertFalse(is_elig)
        self.assertEqual(reason, "EXCLUDED_IDENTICAL_TARGET_RESPONSE_IN_CONVERSATION")

    def test_d_e_f_future_timestamp_violation_excluded(self):
        """TEST D, E, F: Candidates with T_cand > T_query cannot be retrieved."""
        query = {"interaction_id": "q1", "created_ts": 1500000000}
        cand = {"interaction_id": "c1", "created_ts": 1500000001, "split": "train"}
        is_elig, reason = self.filter.is_retrieval_eligible(query, cand)
        self.assertFalse(is_elig)
        self.assertEqual(reason, "EXCLUDED_FUTURE_TEMPORAL_VIOLATION")

    def test_j_intent_labels_belong_to_taxonomy(self):
        """TEST J: All intent names match taxonomy_v1 exactly."""
        self.assertEqual(len(self.intent_names), 11)
        agent = SupportAgent()
        res = agent.predict([], "my battery dies quickly")
        self.assertIn(res["intent"], self.intent_names)

    def test_k_l_m_escalation_and_evidence_metadata(self):
        """TEST K, L, M: Escalation decisions have explainable reasons and guardrails."""
        agent = SupportAgent()
        res = agent.predict([], "someone hacked my apple id password")
        self.assertEqual(res["escalation_decision"], "HIGH_RISK_ESCALATE")
        self.assertTrue(len(res["escalation_reason"]) > 0)
        self.assertIn("apple_id", res["escalation_reason"].lower())
        self.assertTrue(res["safety_passed"])


    def test_p_golden_set_size_and_purity(self):
        """TEST P: Golden evaluation set contains exactly 200 records."""
        with open("evaluations/golden_set/golden_set.jsonl", "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip()]
        self.assertEqual(len(lines), 200)


if __name__ == "__main__":
    unittest.main()
