"""Preprocessing, multipart customer aggregation, text normalization, and canonical dataset creation."""

import csv
import datetime
import json
import os
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any, Set, Tuple

from src.data.ingest import get_db_connection, SQLITE_DB_PATH
from src.data.conversations import ConversationGraph, ConversationTurn


def normalize_tweet_text(text: str) -> str:
    """
    Normalizes tweet text:
    - Replaces URLs with <URL>
    - Replaces @mentions with <USER>
    - Normalizes whitespace
    - Lowercases
    """
    t = re.sub(r"https?://\S+|www\.\S+", "<URL>", text)
    t = re.sub(r"@\w+", "<USER>", t)
    t = re.sub(r"\s+", " ", t).strip().lower()
    return t


def is_linguistic_continuation(text: str) -> bool:
    """Checks if text contains continuation markers such as ..., 1/2, Part 1, -, +."""
    num_pattern = re.compile(r"\b([1-9]/[1-9]|\([1-9]\)|part\s*[1-9])\b", re.IGNORECASE)
    cont_pattern = re.compile(r"(\.\.\.|…|-|\+)\s*$", re.IGNORECASE)
    return bool(num_pattern.search(text) or cont_pattern.search(text.strip()))


class DatasetPreprocessor:
    def __init__(self, db_path: str = SQLITE_DB_PATH, brand: str = "AppleSupport"):
        self.db_path = db_path
        self.brand = brand
        self.graph = ConversationGraph(db_path)
        self.graph.load_graph(brand)

    def process_all_interactions(
        self,
        multipart_threshold_sec: int = 120,
        context_policy: str = "full_history",
        max_context_turns: Optional[int] = None,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
        """
        Extracts and reconciles all customer interactions with AppleSupport.
        Produces:
        1. usable_interactions (Canonical supervised modeling examples)
        2. exclusion_log (All excluded or non-response records with explicit reasons)
        3. reconciliation_metadata (Summary counts)
        """
        conn = get_db_connection(self.db_path)
        cur = conn.cursor()

        print(f"Querying all customer inbound tweets replying to or replied by {self.brand}...")

        # 1. Fetch all direct customer -> AppleSupport response pairs
        cur.execute("""
        SELECT p.tweet_id as cust_tid, p.author_id as cust_aid, p.created_at as cust_cat, p.created_ts as cust_ts, p.text as cust_txt,
               p.in_response_to_tweet_id as cust_parent,
               c.tweet_id as supp_tid, c.author_id as supp_aid, c.created_at as supp_cat, c.created_ts as supp_ts, c.text as supp_txt
        FROM tweets c
        JOIN tweets p ON c.in_response_to_tweet_id = p.tweet_id
        WHERE c.author_id = ? AND c.inbound = 0 AND p.inbound = 1
        ORDER BY p.created_ts ASC, p.tweet_id ASC
        """, (self.brand,))
        paired_records = cur.fetchall()
        print(f"Total candidate customer -> {self.brand} pairs: {len(paired_records):,}")

        # 2. Fetch all inbound tweets that mention brand but received no reply in CSV
        cur.execute("""
        SELECT tweet_id, author_id, created_at, created_ts, text, in_response_to_tweet_id
        FROM tweets
        WHERE inbound = 1 AND text LIKE ?
          AND tweet_id NOT IN (
              SELECT p.tweet_id FROM tweets c JOIN tweets p ON c.in_response_to_tweet_id = p.tweet_id
              WHERE c.author_id = ? AND c.inbound = 0
          )
        """, (f"%@{self.brand}%", self.brand))
        unreplied_records = cur.fetchall()
        print(f"Total candidate customer tweets with no observed reply: {len(unreplied_records):,}")

        usable_examples: List[Dict[str, Any]] = []
        exclusion_log: List[Dict[str, Any]] = []
        seen_interactions: Set[int] = set()

        # Track multipart merges
        # If customer C sent tweet 1, then tweet 2 (parent = tweet 1, same author, <= 120s), and Apple replied to tweet 2
        for r in paired_records:
            cust_tid = int(r["cust_tid"])
            cust_aid = str(r["cust_aid"])
            cust_ts = int(r["cust_ts"])
            cust_txt = str(r["cust_txt"])
            cust_parent = int(r["cust_parent"]) if r["cust_parent"] else None

            supp_tid = int(r["supp_tid"])
            supp_ts = int(r["supp_ts"])
            supp_txt = str(r["supp_txt"])
            supp_cat = str(r["supp_cat"])

            # Temporal validity check
            if supp_ts < cust_ts:
                exclusion_log.append({
                    "target_tweet_id": cust_tid,
                    "reason": "TEMPORAL_INVERSION",
                    "details": f"Support timestamp {supp_ts} < Customer timestamp {cust_ts}",
                })
                continue

            # Multipart Check: check if parent is from same author and within threshold
            source_tids = [cust_tid]
            aggregated_raw_text = cust_txt
            is_multipart = False

            if cust_parent and cust_parent in self.graph.tweets:
                parent_turn = self.graph.tweets[cust_parent]
                if parent_turn.author_id == cust_aid and parent_turn.author_type == "customer":
                    delta_t = cust_ts - parent_turn.created_ts
                    if 0 <= delta_t <= multipart_threshold_sec:
                        # Check linguistic or timing heuristic
                        if is_linguistic_continuation(parent_turn.text) or delta_t <= 60:
                            aggregated_raw_text = f"{parent_turn.text} {cust_txt}"
                            source_tids = [parent_turn.tweet_id, cust_tid]
                            is_multipart = True

            # Build context (strictly excluding target turn & future turns)
            context = self.graph.build_context(
                target_customer_tweet_id=cust_tid,
                context_policy=context_policy,
                max_turns=max_context_turns,
            )

            conv_id = self.graph.get_conversation_id(cust_tid)
            latency = supp_ts - cust_ts

            interaction_id = f"app_{supp_tid}_{cust_tid}"
            example = {
                "interaction_id": interaction_id,
                "conversation_id": conv_id,
                "customer_id": cust_aid,
                "brand": self.brand,
                "timestamp": r["cust_cat"],
                "created_ts": cust_ts,
                "customer_message_raw": aggregated_raw_text,
                "customer_message_normalized": normalize_tweet_text(aggregated_raw_text),
                "context": context,
                "historical_response_raw": supp_txt,
                "historical_response_normalized": normalize_tweet_text(supp_txt),
                "target_support_tweet_id": supp_tid,
                "source_customer_tweet_ids": source_tids,
                "multipart_aggregated": is_multipart,
                "latency_seconds": latency,
                "lifecycle_state": "USABLE_RESPONSE_EXAMPLE",
            }

            usable_examples.append(example)
            seen_interactions.add(supp_tid)

        # Process unreplied records into exclusion log
        for r in unreplied_records:
            tid = int(r["tweet_id"])
            aid = str(r["author_id"])
            exclusion_log.append({
                "target_tweet_id": tid,
                "author_id": aid,
                "reason": "NO_OBSERVED_RESPONSE",
                "details": "Inbound customer tweet mentioning brand had no direct outbound reply in dataset.",
            })

        reconciliation = {
            "brand": self.brand,
            "total_candidate_pairs": len(paired_records),
            "total_unreplied_inbound": len(unreplied_records),
            "usable_examples_count": len(usable_examples),
            "excluded_examples_count": len(exclusion_log),
            "multipart_aggregated_count": sum(1 for e in usable_examples if e["multipart_aggregated"]),
            "multipart_rate_pct": round(sum(1 for e in usable_examples if e["multipart_aggregated"]) / len(usable_examples) * 100, 2) if usable_examples else 0,
        }

        print(f"Reconciliation Summary: {reconciliation['usable_examples_count']:,} usable, {reconciliation['excluded_examples_count']:,} excluded ({reconciliation['multipart_aggregated_count']:,} multipart aggregated).")
        return usable_examples, exclusion_log, reconciliation


def save_processed_dataset(
    usable_examples: List[Dict[str, Any]],
    exclusion_log: List[Dict[str, Any]],
    reconciliation_meta: Dict[str, Any],
    output_dir: str = "data/processed",
):
    os.makedirs(output_dir, exist_ok=True)

    interactions_jsonl = os.path.join(output_dir, "interactions.jsonl")
    print(f"Saving {len(usable_examples):,} usable interactions to {interactions_jsonl}...")
    with open(interactions_jsonl, "w", encoding="utf-8") as f:
        for ex in usable_examples:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")

    exclusion_jsonl = os.path.join(output_dir, "exclusion_log.jsonl")
    print(f"Saving {len(exclusion_log):,} excluded records to {exclusion_jsonl}...")
    with open(exclusion_jsonl, "w", encoding="utf-8") as f:
        for ex in exclusion_log:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")

    metadata_json = os.path.join(output_dir, "interactions_metadata.json")
    with open(metadata_json, "w", encoding="utf-8") as f:
        json.dump(reconciliation_meta, f, indent=2)

    print(f"Dataset processing complete. Output saved to: {output_dir}")


if __name__ == "__main__":
    preprocessor = DatasetPreprocessor()
    usable, excluded, meta = preprocessor.process_all_interactions()
    save_processed_dataset(usable, excluded, meta)
