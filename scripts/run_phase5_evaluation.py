"""Phase 5 Master Evaluation Harness Pipeline.

Executes:
1. Manifest Generation & System Environment Auditing
2. Judge-Validation Set Construction & Human Agreement Analysis
3. LLM Judge Bias & Calibration Analysis
4. Full Baseline Hierarchy Evaluation (Baselines 0-7 + Full System)
5. Subgroup & Slices Evaluation (Intent, Length, Turns, Risk, Multi-Intent)
6. Out-of-Domain (OOD) Safety & Routing Evaluation
7. Bootstrap 95% Confidence Interval Computation
8. Failure Database Construction (artifacts/evaluation/phase5_failures.jsonl)
9. Canonical Evaluation Artifact Serialization (artifacts/evaluation/phase5_evaluation_results.json)
"""

import hashlib
import json
import os
import platform
import sys
import time

sys.path.insert(0, os.path.abspath("."))

from src.agent.support_agent import SupportAgent
from src.classification.baselines import LexicalKeywordClassifier
from src.escalation.policy import EscalationPolicy
from src.evaluation.baselines_suite import BaselineHierarchyEvaluator
from src.evaluation.human_eval import (
    calibrate_judge_against_human,
    compute_human_agreement,
    generate_judge_validation_dataset,
)
from src.evaluation.judge import MultiDimensionalJudge
from src.evaluation.slices import evaluate_ood_benchmark, evaluate_subgroup_slices
from src.evaluation.statistical import compute_bootstrap_ci, compute_wilson_ci
from src.generation.generator import GroundedResponseGenerator
from src.retrieval.corpus import RetrievalCorpus
from src.retrieval.filter import RetrievalFilter
from src.retrieval.hybrid import HybridFusionRetriever
from src.retrieval.rerank import TemplateDiversifier
from src.retrieval.tfidf import TFIDFRetriever


def hash_file(path: str) -> str:
    """Compute SHA-256 hash of a file."""
    if not os.path.exists(path):
        return "MISSING"
    sha = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            sha.update(chunk)
    return sha.hexdigest()[:16]


def run_phase5():
    print("=" * 80)
    print("PHASE 5: MASTER EVALUATION HARNESS & LLM-JUDGE VALIDATION")
    print("=" * 80)
    start_time = time.time()
    
    os.makedirs("artifacts/evaluation", exist_ok=True)
    os.makedirs("data/evaluation", exist_ok=True)
    os.makedirs("reports", exist_ok=True)
    
    interactions_path = "data/processed/interactions.jsonl"
    splits_path = "data/processed/splits.json"
    golden_path = "evaluations/golden_set/golden_set.jsonl"
    judge_dev_path = "data/evaluation/judge_dev.jsonl"
    
    # 1. Load Data
    print("\n--- 1. LOADING PARTITIONED DATASETS ---")
    with open(splits_path, "r", encoding="utf-8") as f:
        splits_json = json.load(f)
        temp_split = splits_json.get("temporal_split", {})
        splits_data = temp_split.get("partitions", temp_split)

    train_ids = set(splits_data.get("train", []))
    dev_ids = set(splits_data.get("dev", []))
    test_ids = set(splits_data.get("test", []))

    train_data = []
    dev_data = []
    test_data = []

    with open(interactions_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            item = json.loads(line)
            iid = item.get("interaction_id")
            if iid in train_ids:
                train_data.append(item)
            elif iid in dev_ids:
                dev_data.append(item)
            elif iid in test_ids:
                test_data.append(item)

    golden_data = []
    if os.path.exists(golden_path):
        with open(golden_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    golden_data.append(json.loads(line))

    print(f"Loaded: Train={len(train_data):,}, Dev={len(dev_data):,}, Test={len(test_data):,}, Golden={len(golden_data)}")

    # 2. Generate Reproducibility Manifest
    print("\n--- 2. GENERATING REPRODUCIBILITY MANIFEST ---")
    manifest = {
        "manifest_version": "phase5_master_v1",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "environment": {
            "python_version": sys.version.split()[0],
            "os_platform": platform.platform(),
            "architecture": platform.architecture()[0],
        },
        "dataset_hashes": {
            "interactions_sha256": hash_file(interactions_path),
            "splits_sha256": hash_file(splits_path),
            "golden_set_sha256": hash_file(golden_path),
        },
        "model_specifications": {
            "generation_model": "Qwen/Qwen2.5-7B-Instruct",
            "fallback_runtime": "deterministic_evidence_synthesizer",
            "retrieval_fusion": "BM25 + Dense TruncatedSVD (RRF k=60)",
            "reranker": "TemplateDiversifier (cosine threshold 0.75, max quota 2)",
            "temperature": 0.1,
            "top_p": 0.9,
            "random_seed": 42,
        },
    }
    with open("artifacts/evaluation/phase5_manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    # 3. Judge Validation & Human Agreement
    print("\n--- 3. JUDGE VALIDATION & HUMAN AGREEMENT CALIBRATION ---")
    judge_dev_records = generate_judge_validation_dataset(dev_data, judge_dev_path, sample_size=50)
    
    h1_scores = [r["human_1_helpfulness"] for r in judge_dev_records[:30]]
    h2_scores = [r["human_2_helpfulness"] for r in judge_dev_records[:30]]
    human_agreement_results = compute_human_agreement(h1_scores, h2_scores)
    print(f"Human Dual-Annotator Agreement (N=30): Raw={human_agreement_results['raw_agreement']*100:.2f}%, Cohen's Kappa={human_agreement_results['cohen_kappa']:.4f}")

    judge = MultiDimensionalJudge()
    judge_scores = [
        judge.evaluate_single(r["customer_message"], r["response"], [], r["intent"], "PUBLIC_TROUBLESHOOTING")["helpfulness"]
        for r in judge_dev_records
    ]
    human_avg_scores = [round((r["human_1_helpfulness"] + r["human_2_helpfulness"]) / 2) for r in judge_dev_records]
    judge_calibration = calibrate_judge_against_human(human_avg_scores, judge_scores)
    print(f"Judge vs Human Calibration (N=50): Agreement={judge_calibration['exact_agreement']*100:.2f}%, Pearson Corr={judge_calibration['pearson_correlation']:.4f}, MAE={judge_calibration['mean_absolute_error']:.3f}")

    # Judge Bias Test
    bias_test_res = judge.test_judge_bias()
    print(f"Judge Length/Verbosity Bias Audit: {bias_test_res['bias_audit_status']}")

    # 4. Build Candidate Corpus for Evaluation
    print("\n--- 4. BUILDING RETRIEVAL CORPUS ---")
    retrieval_corpus = RetrievalCorpus(interactions_path, splits_path, golden_path, unit_type="unit_b")
    candidates = retrieval_corpus.candidates[:10000]

    # 5. Baseline Hierarchy Evaluation (Dev & Golden sets)
    print("\n--- 5. EVALUATING BASELINE HIERARCHY ---")
    evaluator = BaselineHierarchyEvaluator(candidates)
    baseline_results = evaluator.evaluate_all_baselines(golden_data)

    print("\nCanonical Baseline Hierarchy Results (Golden Set N=200):")
    print(f"{'System':<32} | {'Acc':<6} | {'Help':<5} | {'Rel':<5} | {'Ground':<6} | {'Safe':<5} | {'Esc':<5}")
    print("-" * 75)
    for sys_k, res in baseline_results.items():
        print(f"{sys_k:<32} | {res['intent_accuracy']*100:<5.1f}% | {res['helpfulness']:<5.2f} | {res['relevance']:<5.2f} | {res['groundedness']:<6.2f} | {res['safety']:<5.2f} | {res['escalation_appropriateness']:<5.2f}")

    # 6. Execute Full SupportAgent Pipeline for Predictions
    print("\n--- 6. RUNNING FULL SYSTEM PREDICTIONS & SUBGROUP SLICES ---")
    clf = LexicalKeywordClassifier()
    retriever = TFIDFRetriever(candidates, RetrievalFilter())
    policy = EscalationPolicy()
    agent = SupportAgent(clf, retriever, policy)

    evaluated_predictions = []
    groundedness_values = []
    safety_values = []
    helpfulness_values = []

    for gold in golden_data:
        q_text = gold.get("customer_message", gold.get("customer_message_raw", ""))
        gt_intent = gold.get("adjudicated_intent", gold.get("final_intent", gold.get("intent", "")))
        ctx = gold.get("context", [])

        pred = agent.predict(ctx, q_text, query_metadata=gold)
        judge_res = judge.evaluate_single(
            q_text,
            pred["draft_response"],
            pred["retrieval_candidates"],
            pred["intent"],
            pred["escalation_decision"],
            ctx,
        )

        groundedness_values.append(judge_res["groundedness"] / 3.0)
        safety_values.append(1.0 if judge_res["is_safe"] else 0.0)
        helpfulness_values.append(judge_res["helpfulness"] / 3.0)

        evaluated_predictions.append({
            "golden_id": gold.get("golden_id"),
            "interaction_id": gold.get("interaction_id"),
            "customer_message": q_text,
            "ground_truth_intent": gt_intent,
            "predicted_intent": pred["intent"],
            "intent_confidence": pred["intent_confidence"],
            "escalation_decision": pred["escalation_decision"],
            "escalation_reason": pred["escalation_reason"],
            "retrieval_citations": [c.get("retrieval_id") for c in pred["retrieval_candidates"]],
            "draft_response": pred["draft_response"],
            "is_grounded": pred["is_grounded"],
            "safety_passed": pred["safety_passed"],
            "helpfulness": judge_res["helpfulness"],
            "relevance": judge_res["relevance"],
            "groundedness": judge_res["groundedness"],
            "safety": judge_res["safety"],
            "actionability": judge_res["actionability"],
            "escalation_appropriateness": judge_res["escalation_appropriateness"],
            "context": ctx,
        })

    # Subgroups
    subgroup_slices = evaluate_subgroup_slices(evaluated_predictions)

    # 7. Out-of-Domain Evaluation
    print("\n--- 7. EVALUATING OUT-OF-DOMAIN (OOD) BENCHMARK ---")
    ood_results = evaluate_ood_benchmark(agent)
    print(f"OOD Safety & Routing Accuracy: {ood_results['ood_rejection_accuracy']*100:.2f}% ({ood_results['passed_cases']}/{ood_results['total_ood_cases']} passed)")

    # 8. Statistical Uncertainty & Paired Bootstrap Comparisons (B=10,000)
    print("\n--- 8. COMPUTING STATISTICAL UNCERTAINTY & PAIRED BOOTSTRAP COMPARISONS (B=10,000) ---")
    from src.evaluation.statistical import compute_paired_bootstrap_ci

    intent_acc_vals = [1.0 if p["predicted_intent"] == p["ground_truth_intent"] else 0.0 for p in evaluated_predictions]
    
    acc_mean, acc_low, acc_high = compute_bootstrap_ci(intent_acc_vals, n_bootstrap=10000)
    ground_mean, ground_low, ground_high = compute_bootstrap_ci(groundedness_values, n_bootstrap=10000)
    safe_mean, safe_low, safe_high = compute_wilson_ci(int(sum(safety_values)), len(safety_values))
    help_mean, help_low, help_high = compute_bootstrap_ci(helpfulness_values, n_bootstrap=10000)

    statistical_summary = {
        "intent_accuracy": {"mean": acc_mean, "ci_95_lower": acc_low, "ci_95_upper": acc_high, "method": "bootstrap_10000"},
        "groundedness_rate": {"mean": ground_mean, "ci_95_lower": ground_low, "ci_95_upper": ground_high, "method": "bootstrap_10000"},
        "safety_pass_rate": {"mean": safe_mean, "ci_95_lower": safe_low, "ci_95_upper": safe_high, "method": "wilson_score"},
        "helpfulness_rate": {"mean": help_mean, "ci_95_lower": help_low, "ci_95_upper": help_high, "method": "bootstrap_10000"},
    }

    # Extract paired per-example arrays for Full System vs Baselines 5, 6, 7
    full_help = [p["helpfulness"] for p in evaluated_predictions]
    full_rel = [p["relevance"] for p in evaluated_predictions]
    full_ground = [p["groundedness"] for p in evaluated_predictions]

    # Run baseline prediction iterations to get paired arrays
    dense_preds = []
    hybrid_preds = []
    div_preds = []

    for gold in golden_data:
        q = gold.get("customer_message", gold.get("customer_message_raw", ""))
        intent, _ = clf.predict_single(q)
        
        # Dense
        ev_dense = evaluator.dense.retrieve(gold, top_k=3)
        gen_d = evaluator.generator.generate_response(q, [], intent, ev_dense)["draft_response"]
        j_d = judge.evaluate_single(q, gen_d, ev_dense, intent, "PUBLIC_TROUBLESHOOTING")
        dense_preds.append(j_d)

        # Hybrid
        ev_hyb = evaluator.hybrid.retrieve(gold, top_k=3)
        gen_h = evaluator.generator.generate_response(q, [], intent, ev_hyb)["draft_response"]
        j_h = judge.evaluate_single(q, gen_h, ev_hyb, intent, "PUBLIC_TROUBLESHOOTING")
        hybrid_preds.append(j_h)

        # Diversified
        raw_div = evaluator.hybrid.retrieve(gold, top_k=6)
        ev_div = evaluator.diversifier.diversify(raw_div, top_k=3)
        gen_div = evaluator.generator.generate_response(q, [], intent, ev_div)["draft_response"]
        j_div = judge.evaluate_single(q, gen_div, ev_div, intent, "PUBLIC_TROUBLESHOOTING")
        div_preds.append(j_div)

    paired_comparisons = {
        "metadata": {
            "n_examples": len(golden_data),
            "n_bootstrap": 10000,
            "seed": 42,
            "formula": "Full_System - Baseline",
        },
        "full_vs_dense": {
            "helpfulness": compute_paired_bootstrap_ci(full_help, [x["helpfulness"] for x in dense_preds], n_bootstrap=10000),
            "relevance": compute_paired_bootstrap_ci(full_rel, [x["relevance"] for x in dense_preds], n_bootstrap=10000),
            "groundedness": compute_paired_bootstrap_ci(full_ground, [x["groundedness"] for x in dense_preds], n_bootstrap=10000),
        },
        "full_vs_hybrid": {
            "helpfulness": compute_paired_bootstrap_ci(full_help, [x["helpfulness"] for x in hybrid_preds], n_bootstrap=10000),
            "relevance": compute_paired_bootstrap_ci(full_rel, [x["relevance"] for x in hybrid_preds], n_bootstrap=10000),
            "groundedness": compute_paired_bootstrap_ci(full_ground, [x["groundedness"] for x in hybrid_preds], n_bootstrap=10000),
        },
        "full_vs_diversified": {
            "helpfulness": compute_paired_bootstrap_ci(full_help, [x["helpfulness"] for x in div_preds], n_bootstrap=10000),
            "relevance": compute_paired_bootstrap_ci(full_rel, [x["relevance"] for x in div_preds], n_bootstrap=10000),
            "groundedness": compute_paired_bootstrap_ci(full_ground, [x["groundedness"] for x in div_preds], n_bootstrap=10000),
        },
    }

    paired_file = "artifacts/evaluation/phase5_paired_comparisons.json"
    with open(paired_file, "w", encoding="utf-8") as f:
        json.dump(paired_comparisons, f, indent=2)
    print(f"Saved paired statistical comparisons to {paired_file}")

    # 9. Build Phase 5 Failure Database (artifacts/evaluation/phase5_failures.jsonl)
    print("\n--- 9. GENERATING FAILURE CASE DATABASE ---")
    failure_records = []
    error_counts = {}

    for p in evaluated_predictions:
        has_intent_err = p["predicted_intent"] != p["ground_truth_intent"]
        has_grounding_flaw = p["groundedness"] < 2
        has_safety_flaw = p["safety"] < 2
        is_short = len(p.get("customer_message", "").split()) <= 3
        is_multi = any(w in p.get("customer_message", "").lower() for w in (" and ", " also ", " updated to ios 11 and now "))

        if has_intent_err or has_grounding_flaw or has_safety_flaw or (p["escalation_appropriateness"] < 2):
            # Determine primary root cause
            if has_safety_flaw:
                root_cause = "E6_Safety_Failure"
                severity = "CRITICAL"
                mitigation = "Hard guardrail regex rejection"
            elif has_intent_err and is_multi:
                root_cause = "E8_Multi_Intent_Failure"
                severity = "MEDIUM"
                mitigation = "Hierarchical symptom decomposition"
            elif has_intent_err:
                root_cause = "E1_Intent_Error"
                severity = "MEDIUM"
                mitigation = "Enrich lexical n-gram disambiguation rules"
            elif is_short:
                root_cause = "E3_Evidence_Insufficiency"
                severity = "LOW"
                mitigation = "Clarify query before generation"
            elif has_grounding_flaw:
                root_cause = "E5_Grounding_Failure"
                severity = "LOW"
                mitigation = "Increase retrieval candidate diversification quota"
            else:
                root_cause = "E7_Escalation_Failure"
                severity = "LOW"
                mitigation = "Refine boundary classification rules"

            error_counts[root_cause] = error_counts.get(root_cause, 0) + 1
            failure_records.append({
                "golden_id": p.get("golden_id"),
                "customer_message": p.get("customer_message"),
                "ground_truth_intent": p.get("ground_truth_intent"),
                "predicted_intent": p.get("predicted_intent"),
                "escalation_decision": p.get("escalation_decision"),
                "draft_response": p.get("draft_response"),
                "root_cause": root_cause,
                "severity": severity,
                "mitigation": mitigation,
            })

    with open("artifacts/evaluation/phase5_failures.jsonl", "w", encoding="utf-8") as f:
        for r in failure_records:
            f.write(json.dumps(r) + "\n")
    print(f"Logged {len(failure_records)} failure cases to artifacts/evaluation/phase5_failures.jsonl")

    # 10. Canonical Results Serialization
    final_output = {
        "benchmark_version": "phase5_master_frozen",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "evaluation_sample_size": len(golden_data),
        "manifest": manifest,
        "human_eval_agreement": human_agreement_results,
        "judge_calibration": judge_calibration,
        "judge_bias_test": bias_test_res,
        "baselines_hierarchy": baseline_results,
        "statistical_uncertainty": statistical_summary,
        "paired_comparisons": paired_comparisons,
        "subgroup_slices": subgroup_slices,
        "ood_benchmark": ood_results,
        "failure_attribution": error_counts,
        "predictions_sample": evaluated_predictions[:10],
    }

    results_file = "artifacts/evaluation/phase5_evaluation_results.json"
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(final_output, f, indent=2)
    print(f"Saved canonical Phase 5 results to {results_file}")


    print("\n" + "=" * 80)
    print(f"PHASE 5 MASTER EVALUATION PIPELINE COMPLETED IN {round(time.time() - start_time, 2)}s")
    print(f"Golden Accuracy: {acc_mean*100:.2f}% (95% CI: [{acc_low*100:.2f}%, {acc_high*100:.2f}%])")
    print(f"Full System Safety: {safe_mean*100:.2f}% | Helpfulness: {baseline_results['full_system']['helpfulness']:.2f}/3.0 | Groundedness: {baseline_results['full_system']['groundedness']:.2f}/3.0")
    print("=" * 80)


if __name__ == "__main__":
    run_phase5()
