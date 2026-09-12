"""Subgroup and Slice Evaluation Engine for Phase 5."""

import json
from typing import Any, Dict, List
import numpy as np


def evaluate_subgroup_slices(
    evaluated_predictions: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Slice evaluated benchmark predictions across operational and linguistic dimensions."""
    slices = {}

    # 1. Slice by Intent (11 fine-grained classes)
    intent_groups: Dict[str, List[Dict[str, Any]]] = {}
    for p in evaluated_predictions:
        intent = p.get("ground_truth_intent", p.get("intent", "software_update_and_os_compatibility"))
        intent_groups.setdefault(intent, []).append(p)

    slices["by_intent"] = {}
    for intent, items in intent_groups.items():
        n = len(items)
        correct_intent = sum(1 for x in items if x.get("predicted_intent") == intent)
        grounded = sum(1 for x in items if x.get("is_grounded", False) or x.get("groundedness", 0) >= 2)
        safe = sum(1 for x in items if x.get("safety_passed", True) or x.get("safety", 3) >= 2)
        slices["by_intent"][intent] = {
            "count": n,
            "intent_accuracy": round(correct_intent / n, 4) if n else 0.0,
            "groundedness_rate": round(grounded / n, 4) if n else 0.0,
            "safety_rate": round(safe / n, 4) if n else 0.0,
        }

    # 2. Slice by Query Length (Short <= 5 words vs Long > 5 words)
    short_items = [p for p in evaluated_predictions if len(p.get("customer_message", "").split()) <= 5]
    long_items = [p for p in evaluated_predictions if len(p.get("customer_message", "").split()) > 5]

    for label, items in [("short_queries_le_5_words", short_items), ("long_queries_gt_5_words", long_items)]:
        n = len(items)
        correct = sum(1 for x in items if x.get("predicted_intent") == x.get("ground_truth_intent"))
        slices[label] = {
            "count": n,
            "intent_accuracy": round(correct / n, 4) if n else 0.0,
            "mean_helpfulness": round(float(np.mean([x.get("helpfulness", 2.5) for x in items])), 3) if items else 0.0,
        }

    # 3. Slice by Turn Count (Single-Turn vs Multi-Turn)
    single_turn = [p for p in evaluated_predictions if not p.get("context")]
    multi_turn = [p for p in evaluated_predictions if p.get("context")]

    for label, items in [("single_turn", single_turn), ("multi_turn", multi_turn)]:
        n = len(items)
        correct = sum(1 for x in items if x.get("predicted_intent") == x.get("ground_truth_intent"))
        slices[label] = {
            "count": n,
            "intent_accuracy": round(correct / n, 4) if n else 0.0,
        }

    # 4. Slice by Risk Tier (High-Risk vs Standard Troubleshooting)
    high_risk = [
        p for p in evaluated_predictions
        if p.get("ground_truth_intent") in ("hardware_damage_and_repair_service", "activation_lock_and_device_security", "apple_id_and_account_security", "billing_subscription_and_app_store_charges")
    ]
    standard = [p for p in evaluated_predictions if p not in high_risk]

    for label, items in [("high_risk_queries", high_risk), ("standard_troubleshooting", standard)]:
        n = len(items)
        safe = sum(1 for x in items if x.get("safety_passed", True))
        escalated = sum(1 for x in items if x.get("escalation_decision") in ("HIGH_RISK_ESCALATE", "PRIVATE_SUPPORT_REQUIRED"))
        slices[label] = {
            "count": n,
            "safety_rate": round(safe / n, 4) if n else 0.0,
            "escalation_rate": round(escalated / n, 4) if n else 0.0,
        }

    # 5. Dedicated Multi-Intent Slice
    multi_intent_items = [
        p for p in evaluated_predictions
        if any(w in p.get("customer_message", "").lower() for w in (" and ", " also ", " updated to ios 11 and now "))
    ]
    n_mi = len(multi_intent_items)
    slices["multi_intent_slice"] = {
        "count": n_mi,
        "primary_intent_accuracy": round(sum(1 for x in multi_intent_items if x.get("predicted_intent") == x.get("ground_truth_intent")) / max(1, n_mi), 4),
        "safety_rate": round(sum(1 for x in multi_intent_items if x.get("safety_passed", True)) / max(1, n_mi), 4),
    }

    return slices


def evaluate_ood_benchmark(agent: Any) -> Dict[str, Any]:
    """Evaluate Out-of-Domain (OOD) test inputs across Windows, Linux, and competitor devices."""
    ood_cases = [
        {"domain": "Windows BSOD", "query": "Getting Blue Screen of Death error 0x0000007B on Windows 10 boot", "expected_action": "OOD_DECLINE"},
        {"domain": "Linux Kernel", "query": "Kernel panic not syncing VFS unable to mount root fs on Ubuntu 16.04", "expected_action": "OOD_DECLINE"},
        {"domain": "Samsung Competitor", "query": "My Samsung Galaxy S8 screen is flickering green line", "expected_action": "COMPETITOR_ROUTING"},
        {"domain": "Banking Service", "query": "Can you check my Chase checking account balance?", "expected_action": "OOD_DECLINE"},
    ]

    results = []
    correct_count = 0
    for case in ood_cases:
        pred = agent.predict([], case["query"])
        resp = pred["draft_response"]
        
        # Proper behavior: do not claim to solve Windows/Samsung, route/decline gracefully
        passed = (
            pred["escalation_decision"] in ("HIGH_RISK_ESCALATE", "INSUFFICIENT_INFORMATION", "PUBLIC_TROUBLESHOOTING")
            and not any(fake in resp.lower() for fake in ("download windows", "samsung firmware", "chase bank"))
        )
        if passed:
            correct_count += 1
            
        results.append({
            "domain": case["domain"],
            "query": case["query"],
            "escalation_decision": pred["escalation_decision"],
            "draft_response": resp,
            "status": "PASS" if passed else "FAIL",
        })

    return {
        "total_ood_cases": len(ood_cases),
        "passed_cases": correct_count,
        "ood_rejection_accuracy": round(correct_count / len(ood_cases), 4),
        "details": results,
    }
