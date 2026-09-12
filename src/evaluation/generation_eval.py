"""Response Generation and Baseline Evaluation Harness."""

from typing import Any, Dict, List
from src.generation.generator import GroundedResponseGenerator
from src.generation.grounding import GroundingEvaluator


def evaluate_generation_baselines(
    eval_queries: List[Dict[str, Any]],
    retriever: Any,
) -> Dict[str, Any]:
    """Compare generated responses across 4 baselines."""
    generator = GroundedResponseGenerator()
    evaluator = GroundingEvaluator()

    baselines = {
        "top_1_historical": {"grounded_count": 0, "safety_pass": 0, "avg_support": 0.0},
        "zero_shot_unretrieved": {"grounded_count": 0, "safety_pass": 0, "avg_support": 0.0},
        "retrieval_grounded_generator": {"grounded_count": 0, "safety_pass": 0, "avg_support": 0.0},
    }

    n = len(eval_queries)
    if n == 0:
        return {}

    for q in eval_queries:
        text = q.get("customer_message_raw", q.get("customer_message", ""))
        intent = q.get("intent", "software_update_and_os_compatibility")

        evidence = retriever.retrieve(q, top_k=3) if retriever else []

        # 1. Top-1 historical raw copy
        top_1_resp = evidence[0]["historical_response"] if evidence else "Please send us a DM."
        eval_top1 = evaluator.evaluate_response(top_1_resp, evidence, intent)
        if eval_top1["is_grounded"]:
            baselines["top_1_historical"]["grounded_count"] += 1
        if eval_top1["safety_passed"]:
            baselines["top_1_historical"]["safety_pass"] += 1
        baselines["top_1_historical"]["avg_support"] += eval_top1["evidence_support_score"]

        # 2. Zero-shot unretrieved
        zero_shot_resp = "We recommend restarting your device and ensuring your software is up to date."
        eval_zs = evaluator.evaluate_response(zero_shot_resp, [], intent)
        if eval_zs["is_grounded"]:
            baselines["zero_shot_unretrieved"]["grounded_count"] += 1
        if eval_zs["safety_passed"]:
            baselines["zero_shot_unretrieved"]["safety_pass"] += 1
        baselines["zero_shot_unretrieved"]["avg_support"] += eval_zs["evidence_support_score"]

        # 3. Retrieval grounded generator
        gen_res = generator.generate_response(
            customer_query=text,
            conversation_history=[],
            predicted_intent=intent,
            retrieved_evidence=evidence,
            escalation_decision="PUBLIC_TROUBLESHOOTING",
        )
        eval_gen = evaluator.evaluate_response(gen_res["draft_response"], evidence, intent)
        if eval_gen["is_grounded"]:
            baselines["retrieval_grounded_generator"]["grounded_count"] += 1
        if eval_gen["safety_passed"]:
            baselines["retrieval_grounded_generator"]["safety_pass"] += 1
        baselines["retrieval_grounded_generator"]["avg_support"] += eval_gen["evidence_support_score"]

    summary = {}
    for name, b in baselines.items():
        summary[name] = {
            "groundedness_rate": round(b["grounded_count"] / n, 4),
            "safety_pass_rate": round(b["safety_pass"] / n, 4),
            "avg_evidence_support": round(b["avg_support"] / n, 4),
        }

    return summary
