"""Tests for Grounding Evaluator."""

import unittest
from src.generation.grounding import GroundingEvaluator


class TestGrounding(unittest.TestCase):
    def setUp(self):
        self.evaluator = GroundingEvaluator()

    def test_safe_grounded_response(self):
        evidence = [{"historical_response": "Go to Settings > Battery to check app battery usage."}]
        res = self.evaluator.evaluate_response(
            draft_response="Check your battery usage under Settings > Battery.",
            retrieved_evidence=evidence,
            predicted_intent="battery_drain_and_charging_issues",
        )
        self.assertTrue(res["safety_passed"])
        self.assertTrue(res["is_grounded"])
        self.assertGreater(res["evidence_support_score"], 0.2)

    def test_prohibited_hallucination_fails_safety(self):
        evidence = [{"historical_response": "Visit iforgot.apple.com to reset your credentials."}]
        res = self.evaluator.evaluate_response(
            draft_response="I have unlocked your account and reset your password for you.",
            retrieved_evidence=evidence,
            predicted_intent="apple_id_and_account_security",
        )
        self.assertFalse(res["safety_passed"])
        self.assertFalse(res["is_grounded"])
        self.assertGreater(res["unsupported_claims_count"], 0)


if __name__ == "__main__":
    unittest.main()
