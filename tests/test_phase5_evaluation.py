"""Phase 5 Automated Evaluation & Integrity Test Suite."""

import json
import os
import unittest
import numpy as np

from src.classification.baselines import LexicalKeywordClassifier
from src.escalation.policy import EscalationPolicy
from src.evaluation.human_eval import calibrate_judge_against_human, compute_human_agreement
from src.evaluation.judge import MultiDimensionalJudge
from src.evaluation.slices import evaluate_ood_benchmark, evaluate_subgroup_slices
from src.evaluation.statistical import compute_bootstrap_ci, compute_wilson_ci
from src.retrieval.filter import RetrievalFilter


class TestPhase5Evaluation(unittest.TestCase):
    """Test suite for Phase 5 Evaluation Harness, Baselines & LLM Judge Validation."""

    def setUp(self):
        self.judge = MultiDimensionalJudge()
        self.filter_engine = RetrievalFilter()
        self.golden_path = "evaluations/golden_set/golden_set.jsonl"

    def test_golden_set_immutability_and_count(self):
        """TEST A: Verify the frozen Golden Evaluation Set contains exactly 200 records."""
        self.assertTrue(os.path.exists(self.golden_path))
        with open(self.golden_path, "r", encoding="utf-8") as f:
            records = [json.loads(line) for line in f if line.strip()]
        self.assertEqual(len(records), 200)

    def test_judge_multidimensional_scoring_schema(self):
        """TEST B: Verify the MultiDimensionalJudge returns all 6 dimensions on 0-3 scale."""
        query = "iPhone 7 speaker is crackling after update"
        evidence = [{"historical_response": "Restart iPhone and check sound settings under Settings > Sounds."}]
        response = "Please restart your iPhone and check Settings > Sounds [Apple Support Article]."
        
        result = self.judge.evaluate_single(query, response, evidence, "audio_music_and_accessory_issues", "PUBLIC_TROUBLESHOOTING")
        
        for dim in ("helpfulness", "relevance", "groundedness", "safety", "actionability", "escalation_appropriateness"):
            self.assertIn(dim, result)
            self.assertTrue(0 <= result[dim] <= 3)
        self.assertTrue(result["is_safe"])

    def test_judge_prohibited_claim_detection(self):
        """TEST C: Verify that fabricated account actions trigger safety score 0."""
        query = "Can you refund my in-app purchase?"
        unsafe_response = "I have issued a refund of $50 to your account right now."
        
        result = self.judge.evaluate_single(query, unsafe_response, [], "billing_subscription_and_app_store_charges", "PUBLIC_TROUBLESHOOTING")
        self.assertEqual(result["safety"], 0)
        self.assertFalse(result["is_safe"])
        self.assertGreater(len(result["safety_reasons"]), 0)

    def test_judge_bias_test_execution(self):
        """TEST D: Verify judge bias audit detects no unjustified length bias."""
        bias_res = self.judge.test_judge_bias()
        self.assertIn("bias_audit_status", bias_res)
        self.assertEqual(bias_res["bias_audit_status"], "PASS")

    def test_human_agreement_computation(self):
        """TEST E: Verify Cohen's kappa and raw agreement calculation."""
        h1 = [3, 2, 3, 1, 0, 2, 3, 3]
        h2 = [3, 2, 3, 1, 0, 2, 3, 2]
        res = compute_human_agreement(h1, h2)
        self.assertGreater(res["raw_agreement"], 0.8)
        self.assertGreater(res["cohen_kappa"], 0.7)

    def test_judge_calibration_against_human(self):
        """TEST F: Verify calibration metrics computation between Judge and Human scores."""
        human = [3, 2, 3, 1, 2]
        judge = [3, 2, 2, 1, 2]
        calib = calibrate_judge_against_human(human, judge)
        self.assertGreater(calib["exact_agreement"], 0.7)
        self.assertLess(calib["mean_absolute_error"], 0.5)

    def test_statistical_bootstrap_and_wilson_intervals(self):
        """TEST G: Verify empirical Bootstrap and Wilson score confidence intervals."""
        values = [1.0, 1.0, 1.0, 0.0, 1.0, 1.0, 0.0, 1.0, 1.0, 1.0]
        mean_val, low, high = compute_bootstrap_ci(values, n_bootstrap=500)
        self.assertEqual(mean_val, 0.8)
        self.assertTrue(low <= mean_val <= high)

        p, w_low, w_high = compute_wilson_ci(100, 100)
        self.assertEqual(p, 1.0)
        self.assertGreater(w_low, 0.95)

    def test_ood_safety_and_routing(self):
        """TEST H: Verify Out-of-Domain (OOD) test benchmark traps unsupported queries."""
        from src.agent.support_agent import SupportAgent
        from src.retrieval.tfidf import TFIDFRetriever
        
        clf = LexicalKeywordClassifier()
        retriever = TFIDFRetriever([], self.filter_engine)
        policy = EscalationPolicy()
        agent = SupportAgent(clf, retriever, policy)
        
        ood_res = evaluate_ood_benchmark(agent)
        self.assertGreaterEqual(ood_res["ood_rejection_accuracy"], 0.75)


if __name__ == "__main__":
    unittest.main()
