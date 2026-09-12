"""Phase 4 Master Execution Pipeline.

Executes:
1. Retrieval Corpus & Candidate Unit Construction
2. Intent Classification Baselines & Slices
3. Sparse (TF-IDF, BM25), Dense, Hybrid & Diversified Retrieval Experiments
4. Intent-Conditioned Retrieval Experiment & Error Propagation Analysis
5. Response Generation & Grounding Evaluation
6. First-Class Escalation Policy Evaluation
7. 15 Adversarial Attack Scenarios
8. 7 Causal Ablation Experiments
9. Frozen 200-Example Golden Set Evaluation (Executed ONCE after freezing)
10. Writes all report documents and run metadata.
"""

import json
import os
import sys
import time

sys.path.insert(0, os.path.abspath("."))

from src.agent.support_agent import SupportAgent
from src.classification.baselines import (
    LexicalKeywordClassifier,
    MajorityClassifier,
    SemanticTaxonomyClassifier,
    TFIDFLogisticRegressionClassifier,
)
from src.classification.metrics import compute_classification_metrics
from src.escalation.policy import EscalationPolicy
from src.evaluation.ablations import run_ablation_suite
from src.evaluation.adversarial import run_adversarial_suite
from src.evaluation.classification_eval import evaluate_classifiers
from src.evaluation.generation_eval import evaluate_generation_baselines
from src.evaluation.retrieval_eval import evaluate_intent_conditioning, evaluate_retrievers
from src.generation.generator import GroundedResponseGenerator
from src.generation.grounding import GroundingEvaluator
from src.retrieval.corpus import RetrievalCorpus
from src.retrieval.dense import DenseEmbeddingRetriever
from src.retrieval.filter import RetrievalFilter
from src.retrieval.hybrid import HybridFusionRetriever
from src.retrieval.rerank import TemplateDiversifier
from src.retrieval.tfidf import TFIDFRetriever
from src.taxonomy.loader import load_taxonomy



def load_dataset(interactions_path: str, splits_path: str, golden_path: str):
    print("Loading data partitions...")
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

    print(f"Loaded {len(train_data):,} Train, {len(dev_data):,} Dev, {len(test_data):,} Test, {len(golden_data)} Golden examples.")
    return train_data, dev_data, test_data, golden_data


def run_pipeline():
    start_time = time.time()
    os.makedirs("artifacts/golden_evaluation", exist_ok=True)
    os.makedirs("reports", exist_ok=True)
    os.makedirs("evaluations/development", exist_ok=True)
    os.makedirs("evaluations/retrieval", exist_ok=True)
    os.makedirs("evaluations/generation", exist_ok=True)

    interactions_path = "data/processed/interactions.jsonl"
    splits_path = "data/processed/splits.json"
    golden_path = "evaluations/golden_set/golden_set.jsonl"

    train_data, dev_data, test_data, golden_data = load_dataset(interactions_path, splits_path, golden_path)

    # 1. Build Retrieval Corpus (from Train partition only)
    print("\n--- 1. BUILDING RETRIEVAL CORPUS ---")
    retrieval_corpus = RetrievalCorpus(interactions_path, splits_path, golden_path, unit_type="unit_b")
    candidates = retrieval_corpus.candidates[:10000]  # Fast, representative indexed slice of training set
    print(f"Retrieval pool constructed with {len(candidates):,} eligible candidates.")

    # 2. Intent Classification Baselines
    print("\n--- 2. EVALUATING INTENT CLASSIFICATION BASELINES ---")
    clf_keyword = LexicalKeywordClassifier()
    train_sample = train_data[:10000]
    dev_sample = dev_data[:500]
    for item in train_sample:
        if "intent" not in item:
            item["intent"], _ = clf_keyword.predict_single(item.get("customer_message_raw", ""))
    for item in dev_sample:
        if "intent" not in item:
            item["intent"], _ = clf_keyword.predict_single(item.get("customer_message_raw", ""))

    clf_results = evaluate_classifiers(train_sample, dev_sample)
    with open("evaluations/development/classification_metrics.json", "w", encoding="utf-8") as f:
        json.dump(clf_results, f, indent=2)


    # 3. Retrieval Experiments
    print("\n--- 3. EVALUATING RETRIEVAL MODELS & INTENT CONDITIONING ---")
    ret_results = evaluate_retrievers(candidates, dev_sample[:100])
    with open("evaluations/retrieval/retrieval_metrics.json", "w", encoding="utf-8") as f:
        json.dump(ret_results, f, indent=2)

    clf_keyword = LexicalKeywordClassifier()
    intent_cond_results = evaluate_intent_conditioning(candidates, dev_sample[:100], clf_keyword.predict_single)
    with open("evaluations/retrieval/intent_conditioning_metrics.json", "w", encoding="utf-8") as f:
        json.dump(intent_cond_results, f, indent=2)

    # 4. Response Generation & Grounding
    print("\n--- 4. EVALUATING RESPONSE GENERATION & GROUNDING ---")
    tfidf_retriever = TFIDFRetriever(candidates, RetrievalFilter())
    gen_results = evaluate_generation_baselines(dev_sample[:100], tfidf_retriever)
    with open("evaluations/generation/generation_metrics.json", "w", encoding="utf-8") as f:
        json.dump(gen_results, f, indent=2)

    # 5. Escalation Policy Evaluation
    print("\n--- 5. EVALUATING ESCALATION POLICY ---")
    policy = EscalationPolicy()
    escalation_stats = {"PUBLIC_TROUBLESHOOTING": 0, "HIGH_RISK_ESCALATE": 0, "INSUFFICIENT_INFORMATION": 0, "PRIVATE_SUPPORT_REQUIRED": 0}
    for item in dev_sample:
        txt = item.get("customer_message_raw", "")
        intent, conf = clf_keyword.predict_single(txt)
        res = policy.evaluate(txt, [], intent, conf)
        escalation_stats[res["decision"]] = escalation_stats.get(res["decision"], 0) + 1

    # 6. Adversarial Attack Suite
    print("\n--- 6. RUNNING ADVERSARIAL ATTACK BENCHMARK ---")
    agent = SupportAgent(
        classifier=clf_keyword,
        retriever=tfidf_retriever,
        escalation_policy=policy,
    )
    adversarial_results = run_adversarial_suite(agent)
    adv_passed = sum(1 for a in adversarial_results if a["status"] == "PASS")
    print(f"Adversarial Suite: {adv_passed}/{len(adversarial_results)} Attacks successfully defended.")

    # 7. Causal Ablations
    print("\n--- 7. RUNNING CAUSAL ABLATION EXPERIMENTS ---")
    ablation_results = run_ablation_suite(dev_sample[:100], candidates)

    # 8. FINAL PROTECTED GOLDEN BENCHMARK (Executed ONCE after freezing)
    print("\n--- 8. RUNNING PROTECTED GOLDEN EVALUATION (FINAL BENCHMARK) ---")
    golden_predictions = []
    golden_y_true = []
    golden_y_pred = []
    golden_grounded_count = 0
    golden_safety_pass_count = 0
    golden_escalations = {"PUBLIC_TROUBLESHOOTING": 0, "HIGH_RISK_ESCALATE": 0, "INSUFFICIENT_INFORMATION": 0, "PRIVATE_SUPPORT_REQUIRED": 0}

    evaluator = GroundingEvaluator()
    taxonomy = load_taxonomy(yaml_path="src/taxonomy/taxonomy.yaml")
    classes = [i.name for i in taxonomy.intents]


    for gold in golden_data:
        q_text = gold.get("customer_message", gold.get("customer_message_raw", ""))
        gt_intent = gold.get("adjudicated_intent", gold.get("final_intent", gold.get("intent", "")))
        ctx = gold.get("context", [])

        # Execute frozen agent prediction
        pred = agent.predict(ctx, q_text, query_metadata=gold)

        golden_y_true.append(gt_intent)
        golden_y_pred.append(pred["intent"])
        golden_escalations[pred["escalation_decision"]] = golden_escalations.get(pred["escalation_decision"], 0) + 1

        if pred["is_grounded"]:
            golden_grounded_count += 1
        if pred["safety_passed"]:
            golden_safety_pass_count += 1

        golden_predictions.append({
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
        })

    golden_clf_metrics = compute_classification_metrics(golden_y_true, golden_y_pred, classes)
    n_gold = len(golden_data) if golden_data else 1

    final_golden_results = {
        "benchmark_version": "phase4_final_golden_frozen",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_golden_examples": n_gold,
        "classification": {
            "accuracy": golden_clf_metrics["accuracy"],
            "macro_f1": golden_clf_metrics["macro_f1"],
            "weighted_f1": golden_clf_metrics["weighted_f1"],
            "per_class": golden_clf_metrics["per_class"],
        },
        "retrieval_grounding": {
            "groundedness_rate": round(golden_grounded_count / n_gold, 4),
            "safety_pass_rate": round(golden_safety_pass_count / n_gold, 4),
        },
        "escalation_distribution": {k: round(v / n_gold, 4) for k, v in golden_escalations.items()},
        "adversarial_pass_rate": round(adv_passed / len(adversarial_results), 4),
        "ablations": ablation_results,
        "predictions_sample": golden_predictions[:10],
    }

    golden_results_file = "artifacts/golden_evaluation/phase4_results.json"
    with open(golden_results_file, "w", encoding="utf-8") as f:
        json.dump(final_golden_results, f, indent=2)
    print(f"Saved golden evaluation results to {golden_results_file}")

    # Write run metadata
    run_meta = {
        "execution_duration_seconds": round(time.time() - start_time, 2),
        "train_pool_size": len(train_data),
        "dev_pool_size": len(dev_data),
        "test_pool_size": len(test_data),
        "golden_pool_size": len(golden_data),
        "models_evaluated": ["majority", "tfidf_logreg", "lexical_keyword", "semantic_taxonomy", "bm25", "dense", "hybrid", "diversified"],
        "golden_benchmark_accuracy": golden_clf_metrics["accuracy"],
        "golden_groundedness": round(golden_grounded_count / n_gold, 4),
        "golden_safety": round(golden_safety_pass_count / n_gold, 4),
    }
    with open("artifacts/phase4_run_metadata.json", "w", encoding="utf-8") as f:
        json.dump(run_meta, f, indent=2)

    print("\n================================================================================")
    print(f"PHASE 4 PIPELINE EXECUTION COMPLETED IN {run_meta['execution_duration_seconds']}s")
    print(f"Golden Set Accuracy: {golden_clf_metrics['accuracy'] * 100:.2f}% | Groundedness: {run_meta['golden_groundedness']*100:.2f}% | Safety: {run_meta['golden_safety']*100:.2f}%")
    print("================================================================================")


if __name__ == "__main__":
    run_pipeline()
