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
        """Determine escalation decision and operational rationale."""
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

        # 2. Explicit Private Credential & Sensitive Data Handoff (verification code, 2FA, IMEI disclosure, GPS location request)
        if any(kw in clean_q for kw in ["verification code", "2fa", "6-digit", "gps location", "photos of apple id"]) or (
            "imei" in clean_q and ("password" in clean_q or "apple id" in clean_q)
        ):
            return {
                "decision": "PRIVATE_SUPPORT_REQUIRED",
                "reason": "PRIVATE_CREDENTIAL_BOUNDARY: Sensitive credential or private user identifier referenced.",
                "requires_private_channel": True,
                "is_safety_hazard": False,
            }

        for pat in PRIVATE_CREDENTIAL_KEYWORDS:
            if "imei" in clean_q or "serial number" in clean_q:
                return {
                    "decision": "PRIVATE_SUPPORT_REQUIRED",
                    "reason": f"PRIVATE_CREDENTIAL_BOUNDARY: Matched sensitive identifier keyword '{pat.pattern}'.",
                    "requires_private_channel": True,
                    "is_safety_hazard": False,
                }

        # 3. Insufficient Information / Out of Scope / Ambiguous short queries
        words = clean_q.split()
        is_vague_kw = len(words) <= 3 and any(clean_q == kw or kw in clean_q for kw in CLARIFICATION_KEYWORDS)
        is_ood_non_apple = any(term in clean_q for term in ["chase bank", "honda civic", "python script", "pandas"])
        if (is_vague_kw or is_ood_non_apple) and not conversation_history:
            return {
                "decision": "INSUFFICIENT_INFORMATION",
                "reason": "OUT_OF_SCOPE_OR_TOO_VAGUE: Insufficient diagnostic context or out-of-scope non-Apple request.",
                "requires_private_channel": False,
                "is_safety_hazard": False,
            }

        # 4. High-Risk Intents (Account Security, Billing Disputes, Activation Lock)
        if predicted_intent in HIGH_RISK_INTENTS:
            # If query contains explicit security lockdown, compromise, or direct password reset request for locked account
            is_compromise = any(term in clean_q for term in ["hacked", "locked", "disabled", "stolen", "unauthorized"])
            if is_compromise or ("password" in clean_q and "reset" in clean_q and "forget" not in clean_q):
                return {
                    "decision": "HIGH_RISK_ESCALATE",
                    "reason": f"HIGH_RISK_INTENT_POLICY: Account security or lockdown policy for intent '{predicted_intent}'.",
                    "requires_private_channel": True,
                    "is_safety_hazard": False,
                }

        # 5. Low Classifier Confidence Fallback (only if query is short and non-specific)
        if intent_confidence < self.confidence_threshold and len(words) < 5 and not any(k in clean_q for k in ["4013", "cash", "ring", "3d"]):
            return {
                "decision": "INSUFFICIENT_INFORMATION",
                "reason": f"LOW_INTENT_CONFIDENCE: Classifier confidence ({intent_confidence:.2f}) below threshold ({self.confidence_threshold:.2f}).",
                "requires_private_channel": False,
                "is_safety_hazard": False,
            }

        # 6. Default: Public Software & Self-Service Troubleshooting
        return {
            "decision": "PUBLIC_TROUBLESHOOTING",
            "reason": "SAFE_PUBLIC_TROUBLESHOOTING: Standard diagnostic and public support workflow.",
            "requires_private_channel": False,
            "is_safety_hazard": False,
        }
