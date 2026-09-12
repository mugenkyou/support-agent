"""Tests for Escalation Policy Engine."""

import unittest
from src.escalation.policy import EscalationPolicy


class TestEscalation(unittest.TestCase):
    def setUp(self):
        self.policy = EscalationPolicy(confidence_threshold=0.45)

    def test_safety_hazard_triggers_high_risk(self):
        res = self.policy.evaluate(
            customer_query="my iphone battery is swollen and smoking",
            conversation_history=[],
            predicted_intent="battery_drain_and_charging_issues",
            intent_confidence=0.9,
        )
        self.assertEqual(res["decision"], "HIGH_RISK_ESCALATE")
        self.assertTrue(res["is_safety_hazard"])

    def test_vague_query_triggers_clarification(self):
        res = self.policy.evaluate(
            customer_query="help please",
            conversation_history=[],
            predicted_intent="software_update_and_os_compatibility",
            intent_confidence=0.5,
        )
        self.assertEqual(res["decision"], "INSUFFICIENT_INFORMATION")

    def test_high_risk_intent_requires_escalation(self):
        res = self.policy.evaluate(
            customer_query="my account is locked need password reset",
            conversation_history=[],
            predicted_intent="apple_id_and_account_security",
            intent_confidence=0.88,
        )
        self.assertEqual(res["decision"], "HIGH_RISK_ESCALATE")
        self.assertTrue(res["requires_private_channel"])

    def test_imei_credential_boundary_triggers_private_support(self):
        res = self.policy.evaluate(
            customer_query="can I give you my imei to check warranty?",
            conversation_history=[],
            predicted_intent="hardware_damage_and_repair_service",
            intent_confidence=0.8,
        )
        self.assertEqual(res["decision"], "PRIVATE_SUPPORT_REQUIRED")

    def test_safe_software_troubleshooting_allowed(self):
        res = self.policy.evaluate(
            customer_query="wifi drops when locking phone",
            conversation_history=[],
            predicted_intent="network_and_connectivity_troubleshooting",
            intent_confidence=0.85,
        )
        self.assertEqual(res["decision"], "PUBLIC_TROUBLESHOOTING")


if __name__ == "__main__":
    unittest.main()
