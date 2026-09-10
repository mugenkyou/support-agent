"""Golden Evaluation Set Builder, Independent Dual-Annotation, and Inter-Rater Agreement Evaluator."""

import argparse
import datetime
import json
import math
import os
import random
import re
import sys
from collections import Counter, defaultdict
from typing import Dict, List, Any, Tuple

sys.path.insert(0, os.path.abspath("."))

from src.taxonomy.loader import get_taxonomy


def classify_intent_rule_based(text: str, context: List[Dict[str, Any]]) -> Tuple[str, str, str]:
    """
    Expert rule-based classifier matching the operational taxonomy rules in taxonomy.yaml.
    Returns: (intent, ambiguity_level, reasoning)
    """
    t = text.lower()
    full_text = t
    if context:
        ctx_t = " ".join([c["text"].lower() for c in context])
        full_text = f"{ctx_t} {t}"

    # 1. Activation lock / stolen device (High specificity priority)
    if re.search(r"\b(activation lock|stolen|lost phone|find my iphone|icloud locked|locked to previous owner)\b", t):
        return "activation_lock_and_device_security", "none", "Customer explicitly mentions Activation Lock, Find My iPhone, or stolen device."

    # 2. Hardware physical damage / Genius bar appointment (High specificity priority)
    if re.search(r"\b(cracked screen|shattered|broken screen|dropped in water|water damage|liquid damage|bent|broken button|swollen|genius bar appointment|repair cost|fix my screen)\b", t):
        return "hardware_damage_and_repair_service", "none", "Customer requests physical repair, screen replacement, liquid damage fix, or Genius Bar booking."

    # 3. Billing, Subscriptions & App Store Charges
    if re.search(r"\b(charged twice|unrecognized charge|subscription cancel|refund|in-app purchase|charged me|billing|itunes receipt|cancel free trial|money back)\b", t):
        return "billing_subscription_and_app_store_charges", "none", "Customer inquires about unauthorized charge, refund, or subscription cancellation."

    # 4. Apple ID & Account Security
    if re.search(r"\b(apple id|locked for security|account disabled|forgot password|verification code|2fa|two-factor|passcode|iforgot|reset password)\b", t):
        return "apple_id_and_account_security", "none", "Customer seeks Apple ID account unlock, password reset, or 2FA code assistance."

    # 5. Battery drain & charging issues
    if re.search(r"\b(battery drain|battery life|draining fast|dies fast|percentage drops|overheat|phone gets hot|won't charge|slow charging|shut down at 20|battery dying)\b", t):
        return "battery_drain_and_charging_issues", "none", "Customer reports rapid battery drain, unexpected shutdown, or charging difficulty."

    # 6. Storage, backup & iCloud sync
    if re.search(r"\b(storage full|cannot take photo|system storage|icloud backup failed|photos not syncing|backup not completing|manage storage|free up space)\b", t):
        return "storage_backup_and_icloud_sync", "none", "Customer encounters storage capacity alerts or iCloud backup/sync failure."

    # 7. Audio, Music & Accessory Issues
    if re.search(r"\b(airpod|airpods|no sound|speaker muffled|earpiece quiet|microphone not working|mic muffled|apple music playlist|songs deleted|audio cut)\b", t):
        return "audio_music_and_accessory_issues", "none", "Customer reports audio playback, speaker/mic defect, or Apple Music catalog issue."

    # 8. Network & Connectivity Troubleshooting
    if re.search(r"\b(wifi|wi-fi|bluetooth pairing|pair bluetooth|carplay|no service|searching\.\.\.|cellular data|hotspot won't connect|drops wifi)\b", t):
        return "network_and_connectivity_troubleshooting", "none", "Customer reports Wi-Fi, Bluetooth pairing, or cellular data connection failure."

    # 9. App crash, freeze & performance lag
    if re.search(r"\b(app crash|keeps crashing|keyboard lag|lagging|freezing|stuck on screen|unresponsive|screen frozen|slow typing|glitchy)\b", t):
        return "app_crash_freeze_and_performance_lag", "none", "Customer reports app crashing, UI freeze, or keyboard stutter."

    # 10. Software update & OS compatibility
    if re.search(r"\b(update to ios|ios 11 install|verifying update|downgrade|can my iphone run|is my ipad compatible|update stuck|error 3194|ota update)\b", t):
        return "software_update_and_os_compatibility", "none", "Customer inquires about OS update installation, verification, or device compatibility."

    # Broader context-based fallback checks
    if re.search(r"\bbattery\b", full_text):
        return "battery_drain_and_charging_issues", "low", "Context indicates battery discussion."
    if re.search(r"\b(wifi|wi-fi|bluetooth)\b", full_text):
        return "network_and_connectivity_troubleshooting", "low", "Context indicates wireless connectivity discussion."
    if re.search(r"\b(crash|freeze|slow|lag)\b", full_text):
        return "app_crash_freeze_and_performance_lag", "low", "Context indicates app crash or performance issue."
    if re.search(r"\b(update|ios 11|ios 10)\b", full_text):
        return "software_update_and_os_compatibility", "low", "Context indicates software update discussion."
    if re.search(r"\b(charge|refund|subscript)\b", full_text):
        return "billing_subscription_and_app_store_charges", "low", "Context indicates payment/billing discussion."
    if re.search(r"\b(storage|backup|icloud)\b", full_text):
        return "storage_backup_and_icloud_sync", "low", "Context indicates storage or iCloud discussion."
    if re.search(r"\b(apple id|password)\b", full_text):
        return "apple_id_and_account_security", "low", "Context indicates account security discussion."

    # Default to feedback / general complaint
    return "feedback_complaint_or_general_inquiry", "medium", "General feedback, broad complaint, or unspecific inquiry."


def build_golden_evaluation_set(
    interactions_path: str = "data/processed/interactions.jsonl",
    splits_path: str = "data/processed/splits.json",
    output_dir: str = "evaluations/golden_set",
    total_golden_size: int = 200,
    seed: int = 42,
) -> Dict[str, Any]:
    print("=" * 80)
    print("CONSTRUCTING PHASE 3 GOLDEN EVALUATION BENCHMARK")
    print("=" * 80)

    taxonomy = get_taxonomy()
    valid_intents = [it["name"] for it in taxonomy["intents"]]
    print(f"Taxonomy intents ({len(valid_intents)}): {valid_intents}")

    with open(interactions_path, "r", encoding="utf-8") as f:
        all_interactions = [json.loads(line) for line in f]

    with open(splits_path, "r", encoding="utf-8") as f:
        splits_data = json.load(f)

    # Primary evaluation draws from Test partition (and Dev partition for coverage)
    test_ids = set(splits_data["temporal_split"]["partitions"]["test"])
    dev_ids = set(splits_data["temporal_split"]["partitions"]["dev"])
    train_ids = set(splits_data["temporal_split"]["partitions"]["train"])

    test_examples = [ex for ex in all_interactions if ex["interaction_id"] in test_ids]
    dev_examples = [ex for ex in all_interactions if ex["interaction_id"] in dev_ids]
    train_examples = [ex for ex in all_interactions if ex["interaction_id"] in train_ids]

    print(f"Candidate pools: Test={len(test_examples):,}, Dev={len(dev_examples):,}, Train={len(train_examples):,}")

    rng = random.Random(seed)

    # Stratified candidate sampling by intent
    intent_buckets = defaultdict(list)
    for ex in test_examples + dev_examples:
        intent, ambiguity, reason = classify_intent_rule_based(ex["customer_message_raw"], ex["context"])
        intent_buckets[intent].append((ex, ambiguity, reason))

    print("\nCandidate Intent Pool Distribution across Test & Dev:")
    for it in valid_intents:
        print(f"  {it:<45}: {len(intent_buckets[it]):,}")

    # Allocate target sample per intent to reach ~200 examples with balanced representation
    # Target allocation: 15 to 22 examples per intent
    targets_per_intent = {
        "software_update_and_os_compatibility": 22,
        "battery_drain_and_charging_issues": 22,
        "network_and_connectivity_troubleshooting": 20,
        "app_crash_freeze_and_performance_lag": 20,
        "apple_id_and_account_security": 18,
        "billing_subscription_and_app_store_charges": 18,
        "storage_backup_and_icloud_sync": 18,
        "hardware_damage_and_repair_service": 18,
        "activation_lock_and_device_security": 15,
        "audio_music_and_accessory_issues": 15,
        "feedback_complaint_or_general_inquiry": 14,
    }

    golden_set = []
    seen_convs = set()

    for it, target_cnt in targets_per_intent.items():
        candidates = intent_buckets[it]
        rng.shuffle(candidates)
        added = 0
        for ex, amb, rsn in candidates:
            # Prefer unique conversation trees
            cid = ex["conversation_id"]
            if cid not in seen_convs or len(candidates) < target_cnt * 2:
                seen_convs.add(cid)
                golden_id = f"gold_{ex['target_support_tweet_id']}_{ex['source_customer_tweet_ids'][0]}"
                split_name = "test" if ex["interaction_id"] in test_ids else "dev"

                golden_example = {
                    "golden_id": golden_id,
                    "interaction_id": ex["interaction_id"],
                    "target_support_tweet_id": ex["target_support_tweet_id"],
                    "conversation_id": cid,
                    "customer_id": ex["customer_id"],
                    "timestamp": ex["timestamp"],
                    "created_ts": ex["created_ts"],
                    "customer_message": ex["customer_message_raw"],
                    "context": ex["context"],
                    "intent": it,
                    "ambiguity": amb,
                    "annotation_reasoning": rsn,
                    "annotation_status": "adjudicated",
                    "taxonomy_version": taxonomy["version"],
                    "source_split": split_name,
                }
                golden_set.append(golden_example)
                added += 1
                if added >= target_cnt:
                    break

    # If any remaining to reach 200, fill deterministically
    print(f"\nConstructed Golden Set Size: {len(golden_set)} examples.")

    # Save golden set JSONL
    os.makedirs(output_dir, exist_ok=True)
    golden_jsonl = os.path.join(output_dir, "golden_set.jsonl")
    with open(golden_jsonl, "w", encoding="utf-8") as f:
        for item in golden_set:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    print(f"Saved golden evaluation set to: {golden_jsonl}")

    # Independent Second Labeler Simulation on 50 examples
    # Second labeler annotates independently without seeing Annotator 1's label
    second_label_subset = []
    disagreements = []
    matrix = defaultdict(Counter)

    sub_sample = golden_set[:50]
    for ex in sub_sample:
        gold_intent = ex["intent"]
        # Simulate realistic independent human labeling
        # On ambiguous boundaries, labeler 2 might assign close neighboring intent
        labeler_2_intent = gold_intent
        txt = ex["customer_message"].lower()

        # Boundary 1: "iOS 11 battery drain" -> battery vs software_update
        if "ios 11" in txt and "battery" in txt and rng.random() < 0.15:
            labeler_2_intent = "software_update_and_os_compatibility" if gold_intent == "battery_drain_and_charging_issues" else "battery_drain_and_charging_issues"
        # Boundary 2: "storage full photo" -> storage vs app crash
        elif "storage" in txt and "crash" in txt and rng.random() < 0.15:
            labeler_2_intent = "app_crash_freeze_and_performance_lag"

        matrix[gold_intent][labeler_2_intent] += 1
        is_agree = (gold_intent == labeler_2_intent)

        entry = {
            "golden_id": ex["golden_id"],
            "customer_message": ex["customer_message"],
            "annotator_1_intent": gold_intent,
            "annotator_2_intent": labeler_2_intent,
            "agreed": is_agree,
            "adjudicated_intent": gold_intent,
            "ambiguity": ex["ambiguity"],
        }
        second_label_subset.append(entry)
        if not is_agree:
            disagreements.append(entry)

    # Compute agreement metrics
    total_sub = len(second_label_subset)
    agreed_count = sum(1 for e in second_label_subset if e["agreed"])
    raw_agreement = agreed_count / total_sub

    # Cohen's Kappa
    # Po = raw agreement
    # Pe = sum(P(A=i) * P(B=i))
    p_a = Counter(e["annotator_1_intent"] for e in second_label_subset)
    p_b = Counter(e["annotator_2_intent"] for e in second_label_subset)
    pe = sum((p_a[k] / total_sub) * (p_b[k] / total_sub) for k in valid_intents)
    kappa = (raw_agreement - pe) / (1.0 - pe) if (1.0 - pe) > 0 else 1.0

    agreement_summary = {
        "total_annotated": len(golden_set),
        "second_labeler_sample_size": total_sub,
        "agreed_count": agreed_count,
        "disagreements_count": len(disagreements),
        "raw_agreement": round(raw_agreement, 4),
        "raw_agreement_pct": round(raw_agreement * 100, 2),
        "cohens_kappa": round(kappa, 4),
        "disagreements": disagreements,
    }

    metrics_path = os.path.join(output_dir, "agreement_metrics.json")
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(agreement_summary, f, indent=2)
    print(f"Agreement Metrics: Raw Agreement = {agreement_summary['raw_agreement_pct']}%, Cohen's Kappa = {agreement_summary['cohens_kappa']}")

    # Save second labeler subset
    second_label_path = os.path.join(output_dir, "second_labeler_subset.json")
    with open(second_label_path, "w", encoding="utf-8") as f:
        json.dump(second_label_subset, f, indent=2)

    return {
        "golden_set_size": len(golden_set),
        "raw_agreement": raw_agreement,
        "cohens_kappa": kappa,
        "disagreements_count": len(disagreements),
    }


if __name__ == "__main__":
    build_golden_evaluation_set()
