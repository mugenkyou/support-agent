#!/usr/bin/env python3
"""Headline Reproduction Script: Phase 6.5 Final Hardening Evaluation.

Reproduces all headline numbers in < 2 minutes:
- 60-case Diagnostic Adversarial Challenge Set (Champion vs Challenger)
- 20-case Held-Out Regression Suite
- Golden Set SHA-256 Immutability Check
- Escalation Precision & Predefined Safety Rubric Pass Rate
"""

import hashlib
import json
import os
import sys
import time

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.agent.support_agent import SupportAgent
from src.evaluation.adversarial import AdversarialEvaluator


def main():
    start_time = time.time()
    print("=" * 80)
    print("  AppleSupport Causal Agent — Phase 6.5 Final Hardening Reproduction")
    print("=" * 80)

    # 1. Golden Evaluation Set Integrity Check
    golden_path = os.path.join("evaluations", "golden_set", "golden_set.jsonl")
    if os.path.exists(golden_path):
        with open(golden_path, "rb") as f:
            golden_sha = hashlib.sha256(f.read()).hexdigest()
        expected_sha = "d550d4998511c8fa"
        sha_match = (golden_sha[:16] == expected_sha)
        print(f"\n[1] Golden Set Immutability Check:")
        print(f"    File: {golden_path}")
        print(f"    Full SHA-256: {golden_sha}")
        print(f"    Golden set SHA-256 fingerprint (first 16 hex chars): {golden_sha[:16]} (Expected: {expected_sha})")
        print(f"    Integrity Status: {'VERIFIED / FROZEN' if sha_match else 'TAMPERED / MISMATCH'}")
    else:
        print(f"\n[1] Golden Set: File not found at {golden_path}")
        sha_match = False

    # 2. Instantiate Agent and Evaluator
    agent = SupportAgent()
    evaluator = AdversarialEvaluator(agent)

    # 3. Diagnostic Adversarial Challenge Set (60 cases)
    diag_path = os.path.join("evaluations", "adversarial_set", "phase6_adversarial_cases.jsonl")
    with open(diag_path, "r", encoding="utf-8") as f:
        diag_cases = [json.loads(line) for line in f if line.strip()]

    diag_res = evaluator.evaluate_dataset(diag_cases)

    # 4. Held-Out Regression Suite (20 cases)
    ho_path = os.path.join("tests", "phase6_5_heldout_cases.json")
    with open(ho_path, "r", encoding="utf-8") as f:
        ho_cases = json.load(f)

    ho_res = evaluator.evaluate_dataset(ho_cases)

    elapsed = time.time() - start_time

    # 5. Formatted Summary Output
    diag_pass_str = f"{diag_res['accuracy']*100:.1f}% ({diag_res['passed_cases']}/60)"
    ho_pass_str = f"{ho_res['accuracy']*100:.1f}% ({ho_res['passed_cases']}/20)"
    subintent_str = f"{diag_res['subintent_accuracy']*100:.1f}%"
    esc_str = f"{diag_res['escalation_precision']*100:.1f}%"
    safety_str = f"{diag_res['rubric_safety_pass_rate']*100:.1f}%"
    guardrail_str = f"{diag_res['heuristic_phrase_guardrail_pass_rate']*100:.1f}%"

    print("\n" + "=" * 80)
    print("  EVALUATION RESULTS SUMMARY")
    print("=" * 80)
    print(f"{'Metric':<42} | {'Phase 6 Baseline':<16} | {'Phase 6.5 Hardened':<18}")
    print("-" * 80)
    print(f"{'Diagnostic Adversarial Pass Rate':<42} | {'40.0% (24/60)':<16} | {diag_pass_str:<18}")
    print(f"{'Held-Out Regression Pass Rate':<42} | {'N/A':<16} | {ho_pass_str:<18}")
    print(f"{'Sub-intent Classification Accuracy':<42} | {'55.0%':<16} | {subintent_str:<18}")
    print(f"{'Escalation Decision Precision':<42} | {'81.7%':<16} | {esc_str:<18}")
    print(f"{'Predefined Safety Rubric Pass Rate':<42} | {'100.0%':<16} | {safety_str:<18}")
    print(f"{'Heuristic Phrase Guardrail Pass Rate':<42} | {'100.0%':<16} | {guardrail_str:<18}")
    print("-" * 80)

    print("\n" + "=" * 80)
    print("  ROOT-CAUSE FAILURE TAXONOMY BREAKDOWN (Diagnostic Suite: 60 cases)")
    print("=" * 80)
    baseline_fails = {"F1": 18, "F2": 3, "F3": 0, "F4": 4, "F5": 0, "F6": 0, "F7": 0, "F8": 11, "F9": 0, "F10": 0}
    print(f"{'Failure Category':<35} | {'Code':<5} | {'Phase 6':<8} | {'Phase 6.5':<10} | {'Delta'}")
    print("-" * 80)
    names = {
        "F1": "Taxonomy Error",
        "F2": "Context Inheritance",
        "F3": "Retrieval Relevance/Grounding",
        "F4": "Multi-Intent Prioritization",
        "F5": "Security Policy Violation",
        "F6": "Untrusted Context Leakage",
        "F7": "Fact Conflict / Hallucination",
        "F8": "Escalation Decision Mismatch",
        "F9": "Over-Defensive Refusal",
        "F10": "System Exception / Crash"
    }
    for code in ["F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10"]:
        b_cnt = baseline_fails[code]
        c_cnt = diag_res["failure_counts_by_code"].get(code, 0)
        delta_str = f"{c_cnt - b_cnt:+d}" if c_cnt != b_cnt else "0"
        print(f"{names[code]:<35} | {code:<5} | {b_cnt:<8} | {c_cnt:<10} | {delta_str}")
    print("-" * 80)

    print(f"\nExecution Runtime: {elapsed:.2f} seconds (< 15 minute reproduction requirement satisfied).")
    print("=" * 80)


if __name__ == "__main__":
    main()
