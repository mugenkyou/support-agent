"""Leakage control, retrieval exclusion engine, and contamination audits."""

import json
from typing import Dict, List, Set, Any, Optional


def verify_target_leakage(examples: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Verifies that:
    1. The target support tweet_id does NOT appear in the context.
    2. The target response was not authored before the customer query.
    3. The context turns do not contain the target support tweet itself.
    """
    violations = []
    for ex in examples:
        supp_tid = ex["target_support_tweet_id"]
        context_tids = [t["tweet_id"] for t in ex["context"]]

        if supp_tid in context_tids:
            violations.append({
                "interaction_id": ex["interaction_id"],
                "violation_type": "TARGET_TWEET_ID_IN_CONTEXT",
                "details": f"Target support tweet {supp_tid} was found inside preceding context.",
            })

        if ex["latency_seconds"] < 0:
            violations.append({
                "interaction_id": ex["interaction_id"],
                "violation_type": "NEGATIVE_RESPONSE_LATENCY",
                "details": f"Support timestamp occurred before customer timestamp (latency={ex['latency_seconds']}s).",
            })

    return {
        "status": "PASS" if len(violations) == 0 else "FAIL",
        "total_checked": len(examples),
        "violations_count": len(violations),
        "violations": violations[:10],
    }


def verify_future_message_leakage(examples: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Verifies that no turn in the context has a timestamp greater than the target customer turn timestamp.
    """
    violations = []
    for ex in examples:
        target_ts = ex["created_ts"]
        for ctx_turn in ex["context"]:
            if ctx_turn["created_ts"] > target_ts:
                violations.append({
                    "interaction_id": ex["interaction_id"],
                    "target_ts": target_ts,
                    "future_turn_ts": ctx_turn["created_ts"],
                    "future_turn_id": ctx_turn["tweet_id"],
                })

    return {
        "status": "PASS" if len(violations) == 0 else "FAIL",
        "total_checked": len(examples),
        "future_violations_count": len(violations),
        "violations": violations[:10],
    }


class RetrievalFilter:
    """
    Enforces causal and anti-leakage boundaries for historical retrieval candidates.
    """
    def __init__(self, golden_ids: Optional[Set[str]] = None):
        self.golden_ids = golden_ids or set()

    def filter_candidate_pool(
        self,
        query_example: Dict[str, Any],
        candidate_pool: List[Dict[str, Any]],
        strict_temporal: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Filters candidate pool for a query interaction:
        1. Excludes the query interaction itself (and its target response).
        2. Excludes any example belonging to the golden evaluation set.
        3. Excludes future historical interactions (t >= query.created_ts) if strict_temporal=True.
        4. Excludes other turns from the same conversation if they contain future information.
        """
        query_iid = query_example["interaction_id"]
        query_conv = query_example["conversation_id"]
        query_ts = query_example["created_ts"]
        query_supp_id = query_example["target_support_tweet_id"]

        valid_candidates = []
        for cand in candidate_pool:
            cand_iid = cand["interaction_id"]
            cand_ts = cand["created_ts"]
            cand_conv = cand["conversation_id"]
            cand_supp_id = cand["target_support_tweet_id"]

            # Exclude self or same support response
            if cand_iid == query_iid or cand_supp_id == query_supp_id:
                continue

            # Exclude golden set items
            if cand_iid in self.golden_ids:
                continue

            # Temporal rule: cannot retrieve future interactions
            if strict_temporal and cand_ts >= query_ts:
                continue

            # Same conversation rule: if same conversation, must strictly precede
            if cand_conv == query_conv and cand_ts >= query_ts:
                continue

            valid_candidates.append(cand)

        return valid_candidates


if __name__ == "__main__":
    from src.data.preprocessing import DatasetPreprocessor
    preprocessor = DatasetPreprocessor()
    usable, _, _ = preprocessor.process_all_interactions()

    tgt_audit = verify_target_leakage(usable[:1000])
    fut_audit = verify_future_message_leakage(usable[:1000])
    print("Target Leakage Audit:", tgt_audit)
    print("Future Message Leakage Audit:", fut_audit)
