"""Dataset splitting strategies: Random, Conversation-level, Customer-level, and Temporal."""

import datetime
import hashlib
import json
import os
import random
from collections import Counter, defaultdict
from typing import Dict, List, Any, Tuple, Set


def random_split(
    examples: List[Dict[str, Any]],
    train_ratio: float = 0.80,
    dev_ratio: float = 0.10,
    test_ratio: float = 0.10,
    seed: int = 42,
) -> Dict[str, List[str]]:
    """Random splitting by interaction_id (diagnostic baseline)."""
    rng = random.Random(seed)
    indices = list(range(len(examples)))
    rng.shuffle(indices)

    n_total = len(examples)
    n_train = int(n_total * train_ratio)
    n_dev = int(n_total * dev_ratio)

    train_ids = [examples[i]["interaction_id"] for i in indices[:n_train]]
    dev_ids = [examples[i]["interaction_id"] for i in indices[n_train : n_train + n_dev]]
    test_ids = [examples[i]["interaction_id"] for i in indices[n_train + n_dev :]]

    return {"train": train_ids, "dev": dev_ids, "test": test_ids}


def conversation_split(
    examples: List[Dict[str, Any]],
    train_ratio: float = 0.80,
    dev_ratio: float = 0.10,
    test_ratio: float = 0.10,
    seed: int = 42,
) -> Dict[str, List[str]]:
    """Splits by conversation_id ensuring zero conversation overlap."""
    conv_to_examples = defaultdict(list)
    for ex in examples:
        conv_to_examples[ex["conversation_id"]].append(ex["interaction_id"])

    conv_ids = sorted(list(conv_to_examples.keys()))
    rng = random.Random(seed)
    rng.shuffle(conv_ids)

    n_convs = len(conv_ids)
    n_train_convs = int(n_convs * train_ratio)
    n_dev_convs = int(n_convs * dev_ratio)

    train_convs = set(conv_ids[:n_train_convs])
    dev_convs = set(conv_ids[n_train_convs : n_train_convs + n_dev_convs])
    test_convs = set(conv_ids[n_train_convs + n_dev_convs :])

    train_ids = [iid for cid in train_convs for iid in conv_to_examples[cid]]
    dev_ids = [iid for cid in dev_convs for iid in conv_to_examples[cid]]
    test_ids = [iid for cid in test_convs for iid in conv_to_examples[cid]]

    return {"train": train_ids, "dev": dev_ids, "test": test_ids}


def customer_split(
    examples: List[Dict[str, Any]],
    train_ratio: float = 0.80,
    dev_ratio: float = 0.10,
    test_ratio: float = 0.10,
    seed: int = 42,
) -> Dict[str, List[str]]:
    """Splits by customer_id ensuring zero customer overlap."""
    cust_to_examples = defaultdict(list)
    for ex in examples:
        cust_to_examples[ex["customer_id"]].append(ex["interaction_id"])

    cust_ids = sorted(list(cust_to_examples.keys()))
    rng = random.Random(seed)
    rng.shuffle(cust_ids)

    n_custs = len(cust_ids)
    n_train_custs = int(n_custs * train_ratio)
    n_dev_custs = int(n_custs * dev_ratio)

    train_custs = set(cust_ids[:n_train_custs])
    dev_custs = set(cust_ids[n_train_custs : n_train_custs + n_dev_custs])
    test_custs = set(cust_ids[n_train_custs + n_dev_custs :])

    train_ids = [iid for cid in train_custs for iid in cust_to_examples[cid]]
    dev_ids = [iid for cid in dev_custs for iid in cust_to_examples[cid]]
    test_ids = [iid for cid in test_custs for iid in cust_to_examples[cid]]

    return {"train": train_ids, "dev": dev_ids, "test": test_ids}


def temporal_split(
    examples: List[Dict[str, Any]],
    train_ratio: float = 0.80,
    dev_ratio: float = 0.10,
    test_ratio: float = 0.10,
) -> Dict[str, Any]:
    """
    Splits chronologically by created_ts (earliest -> train, middle -> dev, latest -> test).
    Ensures that conversation trees are kept together by assigning the conversation to the partition
    of its earliest interaction, or strictly by timestamp cutoff.
    """
    sorted_examples = sorted(examples, key=lambda x: (x["created_ts"], x["target_support_tweet_id"]))
    n_total = len(sorted_examples)

    n_train = int(n_total * train_ratio)
    n_dev = int(n_total * dev_ratio)

    train_examples = sorted_examples[:n_train]
    dev_examples = sorted_examples[n_train : n_train + n_dev]
    test_examples = sorted_examples[n_train + n_dev :]

    train_ids = [e["interaction_id"] for e in train_examples]
    dev_ids = [e["interaction_id"] for e in dev_examples]
    test_ids = [e["interaction_id"] for e in test_examples]

    train_start = datetime.datetime.fromtimestamp(train_examples[0]["created_ts"], datetime.timezone.utc).isoformat() if train_examples else None
    train_end = datetime.datetime.fromtimestamp(train_examples[-1]["created_ts"], datetime.timezone.utc).isoformat() if train_examples else None

    dev_start = datetime.datetime.fromtimestamp(dev_examples[0]["created_ts"], datetime.timezone.utc).isoformat() if dev_examples else None
    dev_end = datetime.datetime.fromtimestamp(dev_examples[-1]["created_ts"], datetime.timezone.utc).isoformat() if dev_examples else None

    test_start = datetime.datetime.fromtimestamp(test_examples[0]["created_ts"], datetime.timezone.utc).isoformat() if test_examples else None
    test_end = datetime.datetime.fromtimestamp(test_examples[-1]["created_ts"], datetime.timezone.utc).isoformat() if test_examples else None

    return {
        "partitions": {"train": train_ids, "dev": dev_ids, "test": test_ids},
        "metadata": {
            "strategy": "TemporalSplit",
            "train_count": len(train_ids),
            "dev_count": len(dev_ids),
            "test_count": len(test_ids),
            "train_date_range": [train_start, train_end],
            "dev_date_range": [dev_start, dev_end],
            "test_date_range": [test_start, test_end],
        },
    }


def evaluate_split_overlap(
    examples_map: Dict[str, Dict[str, Any]],
    partitions: Dict[str, List[str]],
) -> Dict[str, Any]:
    """Calculates customer overlap, conversation overlap, and exact/normalized duplicate overlap."""
    train_exs = [examples_map[iid] for iid in partitions["train"]]
    dev_exs = [examples_map[iid] for iid in partitions["dev"]]
    test_exs = [examples_map[iid] for iid in partitions["test"]]

    train_custs = set(e["customer_id"] for e in train_exs)
    dev_custs = set(e["customer_id"] for e in dev_exs)
    test_custs = set(e["customer_id"] for e in test_exs)

    train_convs = set(e["conversation_id"] for e in train_exs)
    dev_convs = set(e["conversation_id"] for e in dev_exs)
    test_convs = set(e["conversation_id"] for e in test_exs)

    # Customer overlaps
    cust_train_dev = len(train_custs & dev_custs)
    cust_train_test = len(train_custs & test_custs)
    cust_dev_test = len(dev_custs & test_custs)

    # Conversation overlaps
    conv_train_dev = len(train_convs & dev_convs)
    conv_train_test = len(train_convs & test_convs)
    conv_dev_test = len(dev_convs & test_convs)

    # Duplicates overlap
    train_queries_exact = set(e["customer_message_raw"] for e in train_exs)
    test_queries_exact = set(e["customer_message_raw"] for e in test_exs)
    exact_dup_overlap = len(train_queries_exact & test_queries_exact)

    train_queries_norm = set(e["customer_message_normalized"] for e in train_exs)
    test_queries_norm = set(e["customer_message_normalized"] for e in test_exs)
    norm_dup_overlap = len(train_queries_norm & test_queries_norm)

    return {
        "customer_overlap": {
            "train_dev_overlap_count": cust_train_dev,
            "train_test_overlap_count": cust_train_test,
            "dev_test_overlap_count": cust_dev_test,
            "total_test_customers": len(test_custs),
            "test_customer_in_train_pct": round((cust_train_test / len(test_custs)) * 100, 2) if test_custs else 0,
        },
        "conversation_overlap": {
            "train_dev_overlap_count": conv_train_dev,
            "train_test_overlap_count": conv_train_test,
            "dev_test_overlap_count": conv_dev_test,
        },
        "cross_split_duplicates": {
            "train_test_exact_duplicate_queries": exact_dup_overlap,
            "train_test_exact_duplicate_pct": round((exact_dup_overlap / len(test_queries_exact)) * 100, 2) if test_queries_exact else 0,
            "train_test_normalized_duplicate_queries": norm_dup_overlap,
            "train_test_normalized_duplicate_pct": round((norm_dup_overlap / len(test_queries_norm)) * 100, 2) if test_queries_norm else 0,
        },
    }


if __name__ == "__main__":
    from src.data.preprocessing import DatasetPreprocessor
    preprocessor = DatasetPreprocessor()
    usable, excluded, meta = preprocessor.process_all_interactions()

    ex_map = {e["interaction_id"]: e for e in usable}
    temp_res = temporal_split(usable)
    overlap_report = evaluate_split_overlap(ex_map, temp_res["partitions"])
    print("Temporal Split Overlap Report:", json.dumps(overlap_report, indent=2))
