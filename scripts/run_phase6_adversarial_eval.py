"""Phase 6 Adversarial Evaluation Harness.

Executes non-Golden adversarial evaluation against frozen/hardened SupportAgent.
Generates:
- artifacts/evaluation/phase6_adversarial_results_before.json (or after.json)
- artifacts/evaluation/phase6_failures.jsonl
- artifacts/evaluation/phase6_failure_summary.json
- artifacts/evaluation/phase6_manifest.json
"""

import argparse
import datetime
import hashlib
import json
import os
import sys
import time

sys.path.insert(0, os.path.abspath("."))

from src.agent.support_agent import SupportAgent
from src.evaluation.adversarial import AdversarialEvaluator


def hash_file(path: str) -> str:
    """Compute SHA-256 hash of a file."""
    if not os.path.exists(path):
        return "MISSING"
    sha = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            sha.update(chunk)
    return sha.hexdigest()[:16]


def run_adversarial_evaluation(is_after: bool = False):
    suffix = "after" if is_after else "before"
    print("=" * 80)
    print(f"PHASE 6: ADVERSARIAL BENCHMARK EVALUATION ({suffix.upper()})")
    print("=" * 80)

    dataset_path = "evaluations/adversarial_set/phase6_adversarial_cases.jsonl"
    if not os.path.exists(dataset_path):
        raise FileNotFoundError(f"Adversarial dataset not found at {dataset_path}. Run build_phase6_adversarial_set.py first.")

    cases = []
    with open(dataset_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                cases.append(json.loads(line))

    print(f"Loaded {len(cases)} Phase 6 non-Golden adversarial test cases.")
    print("Initializing SupportAgent...")
    agent = SupportAgent()
    evaluator = AdversarialEvaluator(agent)

    print("Running evaluation across all 60 adversarial cases...")
    eval_results = evaluator.evaluate_dataset(cases)

    os.makedirs("artifacts/evaluation", exist_ok=True)
    results_path = f"artifacts/evaluation/phase6_adversarial_results_{suffix}.json"

    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(eval_results, f, indent=2)
    print(f"Saved evaluation results to {results_path}")

    # Build phase6_failures.jsonl
    failures_path = "artifacts/evaluation/phase6_failures.jsonl"
    failed_cases = [r for r in eval_results["results"] if not r["passed"]]
    with open(failures_path, "w", encoding="utf-8") as f:
        for fc in failed_cases:
            f.write(json.dumps(fc) + "\n")
    print(f"Saved {len(failed_cases)} failure cases to {failures_path}")

    # Build phase6_failure_summary.json
    summary_path = "artifacts/evaluation/phase6_failure_summary.json"
    summary_data = {
        "stage": suffix,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "total_cases": eval_results["total_cases"],
        "passed_cases": eval_results["passed_cases"],
        "failed_cases": eval_results["failed_cases"],
        "accuracy": eval_results["accuracy"],
        "subintent_accuracy": eval_results["subintent_accuracy"],
        "groundedness_pass_rate": eval_results["groundedness_pass_rate"],
        "safety_pass_rate": eval_results["safety_pass_rate"],
        "escalation_precision": eval_results["escalation_precision"],
        "failure_counts_by_code": eval_results["failure_counts_by_code"],
        "failure_counts_by_category": eval_results["failure_counts_by_category"],
    }
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2)
    print(f"Saved failure summary to {summary_path}")

    # Build phase6_manifest.json
    manifest_path = "artifacts/evaluation/phase6_manifest.json"
    manifest_data = {
        "phase": "PHASE_6_ADVERSARIAL_BENCHMARK",
        "stage": suffix,
        "freeze_commit": "ba5eb7a1c2c5b416371a15b361245c4cb8c5945c",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "environment": {
            "python_version": sys.version,
            "platform": sys.platform,
        },
        "dataset_hashes": {
            "golden_set": hash_file("evaluations/golden_set/golden_set.jsonl"),
            "adversarial_set": hash_file(dataset_path),
            "phase5_failures": hash_file("artifacts/evaluation/phase5_failures.jsonl"),
        },
        "summary_metrics": {
            "total_cases": eval_results["total_cases"],
            "passed_cases": eval_results["passed_cases"],
            "failed_cases": eval_results["failed_cases"],
            "accuracy": eval_results["accuracy"],
            "subintent_accuracy": eval_results["subintent_accuracy"],
            "groundedness_pass_rate": eval_results["groundedness_pass_rate"],
            "safety_pass_rate": eval_results["safety_pass_rate"],
            "escalation_precision": eval_results["escalation_precision"],
        },
        "failure_counts_by_code": eval_results["failure_counts_by_code"],
    }
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)
    print(f"Saved phase 6 manifest to {manifest_path}")

    # Print clean summary table
    print("\n" + "=" * 80)
    print(f"PHASE 6 ADVERSARIAL EVALUATION RESULTS ({suffix.upper()})")
    print("=" * 80)
    print(f"Total Test Cases:       {eval_results['total_cases']}")
    print(f"Passed Test Cases:      {eval_results['passed_cases']} ({eval_results['accuracy']*100:.1f}%)")
    print(f"Failed Test Cases:      {eval_results['failed_cases']}")
    print(f"Sub-Intent Accuracy:    {eval_results['subintent_accuracy']*100:.1f}%")
    print(f"Groundedness Pass Rate: {eval_results['groundedness_pass_rate']*100:.1f}%")
    print(f"Safety Pass Rate:       {eval_results['safety_pass_rate']*100:.1f}%")
    print(f"Escalation Precision:   {eval_results['escalation_precision']*100:.1f}%")
    print("-" * 80)
    print("Failure Counts by Code:")
    for code, cnt in eval_results["failure_counts_by_code"].items():
        print(f"  {code}: {cnt}")
    print("-" * 80)
    print("Failure Counts by Category:")
    for cat, info in eval_results["failure_counts_by_category"].items():
        print(f"  {cat:32s}: {info['passed']}/{info['total']} passed ({info['failed']} failed)")
    print("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Phase 6 Adversarial Evaluation Harness")
    parser.add_argument("--after", action="store_true", help="Run evaluation as post-fix stage")
    args = parser.parse_args()
    run_adversarial_evaluation(is_after=args.after)
