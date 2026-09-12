"""First-Class Escalation Policy Engine.

Evaluates customer query, context history, predicted intent, and confidence
to output a deterministic, explainable escalation decision.
"""

import re
from typing import Any, Dict, List, Optional, Tuple

from src.escalation.rules import (
    CLARIFICATION_KEYWORDS,
    HIGH_RISK_INTENTS,
    PRIVATE_CREDENTIAL_KEYWORDS,
    SAFETY_HAZARD_KEYWORDS,
)


class EscalationPolicy:
    """Evaluates and enforces escalation boundaries."""

    def __init__(self, confidence_threshold: float = 0.45):
        self.confidence_threshold = confidence_threshold

    def evaluate(
        self,
        customer_query: str,
        conversation_history: List[Dict[str, Any]],
        predicted_intent: str,
        intent_confidence: float = 1.0,
    ) -> Dict[str, Any]:
        """Determine escalation decision and operational rationale.
        
        Returns:
            {
                "decision": "PUBLIC_TROUBLESHOOTING" | "PRIVATE_SUPPORT_REQUIRED" | "INSUFFICIENT_INFORMATION" | "HIGH_RISK_ESCALATE",
                "reason": str,
                "requires_private_channel": bool,
                "is_safety_hazard": bool,
            }
        """
        clean_q = customer_query.strip().lower()

        # 1. Physical safety hazards (Highest Priority)
        for pat in SAFETY_HAZARD_KEYWORDS:
            if pat.search(clean_q):
                return {
                    "decision": "HIGH_RISK_ESCALATE",
                    "reason": f"SAFETY_HAZARD_DETECTED: Matched critical keyword pattern '{pat.pattern}'",
                    "requires_private_channel": True,
                    "is_safety_hazard": True,
                }

        # 2. Insufficient Information / Ambiguous short queries
        words = clean_q.split()
        if len(words) <= 2 and any(clean_q == kw or kw in clean_q for kw in CLARIFICATION_KEYWORDS):
            return {
                "decision": "INSUFFICIENT_INFORMATION",
                "reason": "QUERY_TOO_VAGUE: Insufficient diagnostic context; clarification required.",
                "requires_private_channel": False,
                "is_safety_hazard": False,
            }

        # 3. High-Risk Intents (Account Security, Billing Disputes, Activation Lock)
        if predicted_intent in HIGH_RISK_INTENTS:
            return {
                "decision": "HIGH_RISK_ESCALATE",
                "reason": f"HIGH_RISK_INTENT_POLICY: Intent '{predicted_intent}' involves account credentials, billing, or security lock.",
                "requires_private_channel": True,
                "is_safety_hazard": False,
            }

        # 4. Private Credential Boundary (IMEI, Serial Number, Passwords)
        for pat in PRIVATE_CREDENTIAL_KEYWORDS:
            if pat.search(clean_q):
                return {
                    "decision": "PRIVATE_SUPPORT_REQUIRED",
                    "reason": f"PRIVATE_CREDENTIAL_BOUNDARY: Matched sensitive identifier keyword '{pat.pattern}'.",
                    "requires_private_channel": True,
                    "is_safety_hazard": False,
                }

        # 5. Low Classifier Confidence Fallback
        if intent_confidence < self.confidence_threshold:
            return {
                "decision": "INSUFFICIENT_INFORMATION",
                "reason": f"LOW_INTENT_CONFIDENCE: Classifier confidence ({intent_confidence:.2f}) below threshold ({self.confidence_threshold:.2f}).",
                "requires_private_channel": False,
                "is_safety_hazard": False,
            }

        # 6. Default: Public Software Troubleshooting
        return {
            "decision": "PUBLIC_TROUBLESHOOTING",
            "reason": "SAFE_PUBLIC_TROUBLESHOOTING: Standard diagnostic and software troubleshooting workflow.",
            "requires_private_channel": False,
            "is_safety_hazard": False,
        }
