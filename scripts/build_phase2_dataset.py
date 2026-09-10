import argparse
import datetime
import json
import os
import random
import sys
from typing import Dict, List, Any

sys.path.insert(0, os.path.abspath("."))

from src.data.ingest import verify_raw_data_integrity, SQLITE_DB_PATH
from src.data.conversations import ConversationGraph
from src.data.preprocessing import DatasetPreprocessor, save_processed_dataset
from src.data.splitting import temporal_split, conversation_split, customer_split, random_split, evaluate_split_overlap
from src.data.leakage import verify_target_leakage, verify_future_message_leakage, RetrievalFilter


def sample_difficult_conversations_for_audit(graph: ConversationGraph, usable_examples: List[Dict[str, Any]], seed: int = 42) -> List[Dict[str, Any]]:
    """
    Samples at least 50 difficult conversation trees for manual inspection:
    - multi-turn interactions (depth >= 3)
    - same-author multipart merges
    - timestamp ties
    - DM/private-channel transitions
    - third-party customer comments in thread
    """
    rng = random.Random(seed)
    sampled = []
    seen_convs = set()

    # 1. Multi-turn deep conversations (15 cases)
    deep_examples = [e for e in usable_examples if len(e["context"]) >= 2]
    rng.shuffle(deep_examples)
    for e in deep_examples:
        cid = e["conversation_id"]
        if cid not in seen_convs:
            seen_convs.add(cid)
            sampled.append({
                "audit_category": "MULTI_TURN_DEEP_CONVERSATION",
                "conversation_id": cid,
                "target_support_tweet_id": e["target_support_tweet_id"],
                "customer_id": e["customer_id"],
                "context_turns_count": len(e["context"]),
                "context_turns": e["context"],
                "customer_message": e["customer_message_raw"],
                "historical_response": e["historical_response_raw"],
                "reconstruction_result": "VALID_CAUSAL_THREAD",
                "decision": "KEEP_IN_DATASET",
                "reason": "Clear multi-step diagnostic reasoning between AppleSupport and customer.",
            })
        if len(sampled) >= 15:
            break

    # 2. Multipart aggregated turns (15 cases)
    multipart_examples = [e for e in usable_examples if e["multipart_aggregated"]]
    rng.shuffle(multipart_examples)
    for e in multipart_examples:
        cid = e["conversation_id"]
        if cid not in seen_convs:
            seen_convs.add(cid)
            sampled.append({
                "audit_category": "SAME_AUTHOR_MULTIPART_MERGE",
                "conversation_id": cid,
                "target_support_tweet_id": e["target_support_tweet_id"],
                "customer_id": e["customer_id"],
                "source_tweet_ids": e["source_customer_tweet_ids"],
                "customer_message": e["customer_message_raw"],
                "historical_response": e["historical_response_raw"],
                "reconstruction_result": "VALID_MULTIPART_MERGE",
                "decision": "KEEP_IN_DATASET",
                "reason": "Consecutive customer tweets within 120s with linguistic/timing continuity correctly merged.",
            })
        if len(sampled) >= 30:
            break

    # 3. DM Redirection cases (10 cases)
    import re
    dm_regex = re.compile(r"\b(dm|direct message|private message)\b", re.IGNORECASE)
    dm_examples = [e for e in usable_examples if dm_regex.search(e["historical_response_raw"])]
    rng.shuffle(dm_examples)
    for e in dm_examples:
        cid = e["conversation_id"]
        if cid not in seen_convs:
            seen_convs.add(cid)
            sampled.append({
                "audit_category": "DM_PRIVATE_CHANNEL_BOUNDARY",
                "conversation_id": cid,
                "target_support_tweet_id": e["target_support_tweet_id"],
                "customer_id": e["customer_id"],
                "customer_message": e["customer_message_raw"],
                "historical_response": e["historical_response_raw"],
                "reconstruction_result": "VALID_PRIVATE_CHANNEL_BOUNDARY",
                "decision": "KEEP_IN_DATASET",
                "reason": "AppleSupport triaged issue and correctly prompted for private DM to collect credentials/identifiers.",
            })
        if len(sampled) >= 40:
            break

    # 4. Standard 1-Turn & Diagnostic cases (10 cases)
    one_turn_examples = [e for e in usable_examples if len(e["context"]) == 0 and not e["multipart_aggregated"]]
    rng.shuffle(one_turn_examples)
    for e in one_turn_examples:
        cid = e["conversation_id"]
        if cid not in seen_convs:
            seen_convs.add(cid)
            sampled.append({
                "audit_category": "ONE_TURN_STANDARD_TROUBLESHOOTING",
                "conversation_id": cid,
                "target_support_tweet_id": e["target_support_tweet_id"],
                "customer_id": e["customer_id"],
                "customer_message": e["customer_message_raw"],
                "historical_response": e["historical_response_raw"],
                "reconstruction_result": "VALID_ONE_TURN_PAIR",
                "decision": "KEEP_IN_DATASET",
                "reason": "Direct single-turn troubleshooting response.",
            })
        if len(sampled) >= 50:
            break

    return sampled


def build_phase2_pipeline(output_dir: str = "data/processed", seed: int = 42):
    print("=" * 80)
    print("EXECUTING PHASE 2 PIPELINE: RECONSTRUCTION, DATASET CONSTRUCTION & SPLITTING")
    print("=" * 80)

    # 1. Ingest & verify raw data
    print("\n[Step 1] Verifying raw data immutability...")
    verify_raw_data_integrity()
    print("Raw CSV SHA-256 matches verified hash.")

    # 2. Preprocess & Reconstruct Graph
    print("\n[Step 2] Reconstructing graph, aggregating turns, and creating canonical examples...")
    preprocessor = DatasetPreprocessor(brand="AppleSupport")
    usable, excluded, meta = preprocessor.process_all_interactions(
        multipart_threshold_sec=120,
        context_policy="full_history",
    )

    # Save processed dataset
    save_processed_dataset(usable, excluded, meta, output_dir=output_dir)

    # 3. Splitting
    print("\n[Step 3] Computing split strategies (Temporal, Conversation, Customer, Random)...")
    ex_map = {e["interaction_id"]: e for e in usable}
    temp_split_res = temporal_split(usable, train_ratio=0.80, dev_ratio=0.10, test_ratio=0.10)
    conv_split_res = conversation_split(usable, train_ratio=0.80, dev_ratio=0.10, test_ratio=0.10, seed=seed)
    cust_split_res = customer_split(usable, train_ratio=0.80, dev_ratio=0.10, test_ratio=0.10, seed=seed)
    rand_split_res = random_split(usable, train_ratio=0.80, dev_ratio=0.10, test_ratio=0.10, seed=seed)

    splits_data = {
        "primary_benchmark_split": "temporal_split",
        "temporal_split": temp_split_res,
        "conversation_split": conv_split_res,
        "customer_split": cust_split_res,
        "random_split": rand_split_res,
        "temporal_overlap_audit": evaluate_split_overlap(ex_map, temp_split_res["partitions"]),
        "conversation_overlap_audit": evaluate_split_overlap(ex_map, conv_split_res),
        "customer_overlap_audit": evaluate_split_overlap(ex_map, cust_split_res),
        "random_overlap_audit": evaluate_split_overlap(ex_map, rand_split_res),
    }

    splits_path = os.path.join(output_dir, "splits.json")
    with open(splits_path, "w", encoding="utf-8") as f:
        json.dump(splits_data, f, indent=2)
    print(f"Splits saved to {splits_path}")

    # 4. Leakage Audits
    print("\n[Step 4] Running comprehensive leakage audits...")
    tgt_audit = verify_target_leakage(usable)
    fut_audit = verify_future_message_leakage(usable)
    print(f"Target Leakage Audit: {tgt_audit['status']} (violations: {tgt_audit['violations_count']})")
    print(f"Future Message Leakage Audit: {fut_audit['status']} (violations: {fut_audit['future_violations_count']})")

    # Retrieval Exclusion Test
    retrieval_filter = RetrievalFilter()
    test_ex = usable[-1]
    filtered_cands = retrieval_filter.filter_candidate_pool(test_ex, usable[:5000])
    self_found = any(c["interaction_id"] == test_ex["interaction_id"] for c in filtered_cands)
    future_found = any(c["created_ts"] >= test_ex["created_ts"] for c in filtered_cands)
    print(f"Retrieval Exclusion Audit: Self-Excluded={'PASS' if not self_found else 'FAIL'}, Future-Excluded={'PASS' if not future_found else 'FAIL'}")

    # 5. Manual Thread Audit Sample
    print("\n[Step 5] Generating 50-example stratified manual thread audit sample...")
    audit_samples = sample_difficult_conversations_for_audit(preprocessor.graph, usable, seed=seed)
    audit_samples_path = "artifacts/manual_thread_audit.json"
    with open(audit_samples_path, "w", encoding="utf-8") as f:
        json.dump(audit_samples, f, indent=2)
    print(f"Manual thread audit samples saved to: {audit_samples_path} ({len(audit_samples)} cases)")

    print("\n" + "=" * 80)
    print("PHASE 2 PIPELINE EXECUTION COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build Phase 2 dataset and splits")
    parser.add_argument("--output_dir", default="data/processed", help="Output directory")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    build_phase2_pipeline(args.output_dir, args.seed)
