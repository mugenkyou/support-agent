"""Tests for Grounded Response Generator."""

import unittest
from src.generation.generator import GroundedResponseGenerator


class TestGeneration(unittest.TestCase):
    def setUp(self):
        self.generator = GroundedResponseGenerator()

    def test_clarification_generation_on_short_query(self):
        res = self.generator.generate_response(
            customer_query="help",
            conversation_history=[],
            predicted_intent="software_update_and_os_compatibility",
            retrieved_evidence=[],
            escalation_decision="INSUFFICIENT_INFORMATION",
        )
        self.assertEqual(res["grounding_status"], "CLARIFICATION_REQUIRED")
        self.assertIn("device model", res["draft_response"])

    def test_high_risk_guardrail_applied(self):
        res = self.generator.generate_response(
            customer_query="reset my apple id password please",
            conversation_history=[],
            predicted_intent="apple_id_and_account_security",
            retrieved_evidence=[{"retrieval_id": "ret_001", "historical_response": "Go to iforgot.apple.com."}],
            escalation_decision="HIGH_RISK_ESCALATE",
        )
        self.assertEqual(res["grounding_status"], "HIGH_RISK_GUARDRAIL_APPLIED")
        self.assertIn("iforgot.apple.com", res["draft_response"])
        self.assertNotIn("I unlocked your account", res["draft_response"])

    def test_evidence_grounded_synthesis(self):
        evidence = [{
            "retrieval_id": "ret_battery_1",
            "historical_response": "@Customer Try going to Settings > Battery to view battery health and force restart.",
        }]
        res = self.generator.generate_response(
            customer_query="my battery drops from 40 to 0",
            conversation_history=[],
            predicted_intent="battery_drain_and_charging_issues",
            retrieved_evidence=evidence,
            escalation_decision="PUBLIC_TROUBLESHOOTING",
        )
        self.assertEqual(res["grounding_status"], "GROUNDED_IN_HISTORICAL_EVIDENCE")
        self.assertIn("ret_battery_1", res["evidence_citations"])
        self.assertNotIn("@Customer", res["draft_response"])


if __name__ == "__main__":
    unittest.main()
