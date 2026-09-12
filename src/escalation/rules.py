"""Escalation Policy Rules and State Definitions.

Defines 4 operational escalation states:
1. PUBLIC_TROUBLESHOOTING: Safe diagnostic/software instructions in public view.
2. PRIVATE_SUPPORT_REQUIRED: Requires private channel handoff (DM boundary) for IMEI, Apple ID, serial number.
3. INSUFFICIENT_INFORMATION: Unambiguous clarification required before diagnosis.
4. HIGH_RISK_ESCALATE: Physical safety (battery swelling), account takeover, disputed billing.
"""

import re
from typing import Any, Dict, List, Set, Tuple

HIGH_RISK_INTENTS: Set[str] = {
    "apple_id_and_account_security",
    "billing_subscription_and_app_store_charges",
    "activation_lock_and_device_security",
}

PRIVATE_CREDENTIAL_KEYWORDS: List[re.Pattern] = [
    re.compile(r"\b(imei|serial\s+number|apple\s+id|credit\s+card|debit\s+card|billing\s+address|password)\b", re.IGNORECASE),
    re.compile(r"\b(send\s+dm|direct\s+message|private\s+message)\b", re.IGNORECASE),
]

SAFETY_HAZARD_KEYWORDS: List[re.Pattern] = [
    re.compile(r"\b(swollen|swelling|exploded|smoking|burning|spark|melted|fire)\b", re.IGNORECASE),
]

CLARIFICATION_KEYWORDS: List[str] = [
    "help",
    "not working",
    "broken",
    "why",
    "please fix",
    "help me",
    "fix it",
]
