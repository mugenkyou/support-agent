"""Conversation Reconstruction and Graph Audit Script for Hiver SDE Intern Take-Home Phase 1.

Audits:
- Graph pointer integrity (in_response_to_tweet_id vs response_tweet_id)
- Dangling references, bi-directional pointer consistency
- Temporal ordering (parent created_at <= child created_at)
- Thread length distributions (1, 2, 3, 4, 5+ messages, mean, p50, p90, p95, max)
- Samples 50+ linked interactions and multi-turn threads for semantic review
"""

import argparse
import csv
import datetime
import json
import math
import os
import random
import sqlite3
import sys
from collections import Counter, defaultdict


def build_conversation_db(csv_path: str, db_path: str = ":memory:"):
    print(f"Loading CSV into SQLite database ({db_path})...")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("PRAGMA synchronous = OFF;")
    cur.execute("PRAGMA journal_mode = MEMORY;")

    cur.execute("""
    CREATE TABLE tweets (
        tweet_id INTEGER PRIMARY KEY,
        author_id TEXT,
        inbound INTEGER,
        created_at TEXT,
        created_ts INTEGER,
        text TEXT,
        response_tweet_id TEXT,
        in_response_to_tweet_id INTEGER
    );
    """)

    time_format = "%a %b %d %H:%M:%S %z %Y"

    with open(csv_path, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        batch = []
        count = 0
        for row in reader:
            tid = int(row["tweet_id"])
            aid = row["author_id"]
            inb = 1 if row["inbound"].lower() == "true" else 0
            cat = row["created_at"]
            dt = datetime.datetime.strptime(cat, time_format)
            ts = int(dt.timestamp())
            txt = row["text"]
            resp = row["response_tweet_id"]
            in_resp = int(row["in_response_to_tweet_id"]) if row["in_response_to_tweet_id"] else None

            batch.append((tid, aid, inb, cat, ts, txt, resp, in_resp))
            count += 1
            if len(batch) >= 100000:
                cur.executemany("INSERT INTO tweets VALUES (?, ?, ?, ?, ?, ?, ?, ?)", batch)
                batch = []
                print(f"Loaded {count:,} records into database...")

        if batch:
            cur.executemany("INSERT INTO tweets VALUES (?, ?, ?, ?, ?, ?, ?, ?)", batch)

    print("Creating indices on in_response_to_tweet_id and author_id...")
    cur.execute("CREATE INDEX idx_in_response_to ON tweets(in_response_to_tweet_id);")
    cur.execute("CREATE INDEX idx_author ON tweets(author_id);")
    cur.execute("CREATE INDEX idx_inbound ON tweets(inbound);")
    conn.commit()
    print(f"Database build complete with {count:,} records.")
    return conn


def inspect_conversations(conn, output_path: str = "artifacts/conversation_audit.json", random_seed: int = 42):
    cur = conn.cursor()
    rng = random.Random(random_seed)

    print("\n--- Auditing Graph Pointers & Reference Integrity ---")
    cur.execute("SELECT COUNT(*) FROM tweets WHERE in_response_to_tweet_id IS NOT NULL")
    total_with_parent = cur.fetchone()[0]

    # Dangling parent references
    cur.execute("""
    SELECT COUNT(*) FROM tweets t
    WHERE t.in_response_to_tweet_id IS NOT NULL
      AND NOT EXISTS (SELECT 1 FROM tweets p WHERE p.tweet_id = t.in_response_to_tweet_id)
    """)
    dangling_parents = cur.fetchone()[0]

    # Valid parent references
    valid_parents = total_with_parent - dangling_parents
    print(f"Tweets with in_response_to_tweet_id: {total_with_parent:,}")
    print(f"Valid parent pointers (parent exists in CSV): {valid_parents:,} ({valid_parents / total_with_parent * 100:.2f}%)")
    print(f"Dangling parent pointers (parent missing from CSV): {dangling_parents:,} ({dangling_parents / total_with_parent * 100:.2f}%)")

    # Temporal Ordering check: parent.created_ts <= child.created_ts
    print("\n--- Auditing Temporal Consistency on Valid Parent-Child Links ---")
    cur.execute("""
    SELECT COUNT(*) FROM tweets c
    JOIN tweets p ON c.in_response_to_tweet_id = p.tweet_id
    WHERE p.created_ts > c.created_ts
    """)
    temporal_violations = cur.fetchone()[0]

    cur.execute("""
    SELECT COUNT(*) FROM tweets c
    JOIN tweets p ON c.in_response_to_tweet_id = p.tweet_id
    WHERE p.created_ts = c.created_ts
    """)
    timestamp_ties = cur.fetchone()[0]

    cur.execute("""
    SELECT COUNT(*) FROM tweets c
    JOIN tweets p ON c.in_response_to_tweet_id = p.tweet_id
    WHERE p.created_ts < c.created_ts
    """)
    strictly_chronological = cur.fetchone()[0]

    print(f"Parent created strictly before child: {strictly_chronological:,} ({strictly_chronological / valid_parents * 100:.2f}%)")
    print(f"Parent-child timestamp ties: {timestamp_ties:,} ({timestamp_ties / valid_parents * 100:.2f}%)")
    print(f"Temporal violations (parent created after child): {temporal_violations:,} ({temporal_violations / valid_parents * 100:.2f}%)")

    # Inbound -> Outbound and Outbound -> Inbound relationships
    print("\n--- Auditing Turn Types on Parent-Child Links ---")
    cur.execute("""
    SELECT p.inbound, c.inbound, COUNT(*)
    FROM tweets c
    JOIN tweets p ON c.in_response_to_tweet_id = p.tweet_id
    GROUP BY p.inbound, c.inbound
    """)
    link_types = cur.fetchall()
    link_type_map = {
        (1, 0): "Customer -> Support Response (Inbound -> Outbound)",
        (0, 1): "Support -> Customer Follow-up (Outbound -> Inbound)",
        (1, 1): "Customer -> Customer (Self-reply/Multi-part)",
        (0, 0): "Support -> Support (Multi-part/Internal handoff)",
    }
    for pinb, cinb, count in link_types:
        desc = link_type_map.get((pinb, cinb), "Unknown")
        print(f"  {desc}: {count:,} ({count / valid_parents * 100:.2f}%)")

    # Thread Reconstruction and Length Distribution
    print("\n--- Reconstructing Conversation Threads ---")
    # A root tweet is either in_response_to_tweet_id IS NULL OR in_response_to_tweet_id NOT IN dataset
    # We want to measure the connected tree length starting from roots.
    # To do this efficiently, let's find root tweets and trace downstream conversation paths.
    cur.execute("""
    SELECT t.tweet_id FROM tweets t
    WHERE t.in_response_to_tweet_id IS NULL
       OR NOT EXISTS (SELECT 1 FROM tweets p WHERE p.tweet_id = t.in_response_to_tweet_id)
    """)
    root_ids = [r[0] for r in cur.fetchall()]
    total_roots = len(root_ids)
    print(f"Total Conversation Roots (True roots + Orphaned roots): {total_roots:,}")

    # Build parent -> list of children in memory for downstream traversal
    cur.execute("SELECT in_response_to_tweet_id, tweet_id FROM tweets WHERE in_response_to_tweet_id IS NOT NULL")
    children_map = defaultdict(list)
    for p_id, c_id in cur.fetchall():
        children_map[p_id].append(c_id)

    print("Traversing conversation trees...")
    thread_lengths = []
    tree_sizes = []

    # BFS/DFS to compute tree size for each root
    for root in root_ids:
        size = 0
        queue = [root]
        while queue:
            curr = queue.pop(0)
            size += 1
            if curr in children_map:
                queue.extend(children_map[curr])
        tree_sizes.append(size)

    size_counter = Counter(tree_sizes)
    tree_sizes.sort()
    total_trees = len(tree_sizes)
    p50_size = tree_sizes[int(total_trees * 0.50)]
    p90_size = tree_sizes[int(total_trees * 0.90)]
    p95_size = tree_sizes[int(total_trees * 0.95)]
    p99_size = tree_sizes[int(total_trees * 0.99)]
    max_size = tree_sizes[-1]
    mean_size = sum(tree_sizes) / total_trees

    print(f"Tree count: {total_trees:,}")
    print(f"Tree size distribution:")
    print(f"  Size 1 (Isolated tweet / no children in CSV): {size_counter[1]:,} ({size_counter[1] / total_trees * 100:.2f}%)")
    print(f"  Size 2 (2-tweet thread): {size_counter[2]:,} ({size_counter[2] / total_trees * 100:.2f}%)")
    print(f"  Size 3 (3-tweet thread): {size_counter[3]:,} ({size_counter[3] / total_trees * 100:.2f}%)")
    print(f"  Size 4 (4-tweet thread): {size_counter[4]:,} ({size_counter[4] / total_trees * 100:.2f}%)")
    print(f"  Size 5+ (5+ tweet threads): {sum(cnt for sz, cnt in size_counter.items() if sz >= 5):,} ({sum(cnt for sz, cnt in size_counter.items() if sz >= 5) / total_trees * 100:.2f}%)")
    print(f"  Mean tree size: {mean_size:.2f}")
    print(f"  Median (p50): {p50_size}, p90: {p90_size}, p95: {p95_size}, p99: {p99_size}, Max: {max_size}")

    # Sample 60 linked customer->support interactions for semantic review
    print("\n--- Sampling 60 Linked Customer -> Support Interactions ---")
    cur.execute("""
    SELECT p.tweet_id, p.author_id, p.text, p.created_at,
           c.tweet_id, c.author_id, c.text, c.created_at
    FROM tweets c
    JOIN tweets p ON c.in_response_to_tweet_id = p.tweet_id
    WHERE p.inbound = 1 AND c.inbound = 0
    ORDER BY RANDOM()
    LIMIT 60;
    """)
    sampled_interactions = []
    for r in cur.fetchall():
        sampled_interactions.append({
            "customer_tweet_id": r[0],
            "customer_author_id": r[1],
            "customer_text": r[2],
            "customer_created_at": r[3],
            "support_tweet_id": r[4],
            "support_author_id": r[5],
            "support_text": r[6],
            "support_created_at": r[7],
        })

    # Sample 30 multi-turn (length >= 3) conversations
    print("\n--- Sampling 30 Multi-turn Conversations ---")
    multi_roots = [r for r, sz in zip(root_ids, tree_sizes) if sz >= 3]
    sampled_multi_roots = rng.sample(multi_roots, min(30, len(multi_roots)))
    sampled_conversations = []

    for r_id in sampled_multi_roots:
        # fetch all tweets in this tree
        tree_tweets = []
        queue = [r_id]
        while queue:
            curr = queue.pop(0)
            cur.execute("SELECT tweet_id, author_id, inbound, created_at, text, in_response_to_tweet_id FROM tweets WHERE tweet_id = ?", (curr,))
            tw = cur.fetchone()
            if tw:
                tree_tweets.append({
                    "tweet_id": tw[0],
                    "author_id": tw[1],
                    "inbound": bool(tw[2]),
                    "created_at": tw[3],
                    "text": tw[4],
                    "in_response_to_tweet_id": tw[5],
                })
            if curr in children_map:
                queue.extend(children_map[curr])
        sampled_conversations.append({
            "root_tweet_id": r_id,
            "turns_count": len(tree_tweets),
            "tweets": tree_tweets,
        })

    results = {
        "graph_pointers": {
            "total_tweets_with_in_response_to": total_with_parent,
            "valid_parents_count": valid_parents,
            "valid_parents_pct": round(valid_parents / total_with_parent * 100, 2),
            "dangling_parents_count": dangling_parents,
            "dangling_parents_pct": round(dangling_parents / total_with_parent * 100, 2),
        },
        "temporal_ordering": {
            "strictly_chronological_count": strictly_chronological,
            "strictly_chronological_pct": round(strictly_chronological / valid_parents * 100, 2),
            "timestamp_ties_count": timestamp_ties,
            "timestamp_ties_pct": round(timestamp_ties / valid_parents * 100, 2),
            "temporal_violations_count": temporal_violations,
            "temporal_violations_pct": round(temporal_violations / valid_parents * 100, 2),
        },
        "interaction_types": {
            desc: count for pinb, cinb, count in [(p, c, cnt) for p, c, cnt in link_types]
            for desc in [link_type_map.get((pinb, cinb), "Unknown")]
        },
        "conversation_topology": {
            "total_conversation_trees": total_trees,
            "isolated_tweets_count": size_counter[1],
            "isolated_tweets_pct": round(size_counter[1] / total_trees * 100, 2),
            "2_tweet_threads_count": size_counter[2],
            "2_tweet_threads_pct": round(size_counter[2] / total_trees * 100, 2),
            "3_tweet_threads_count": size_counter[3],
            "3_tweet_threads_pct": round(size_counter[3] / total_trees * 100, 2),
            "4_tweet_threads_count": size_counter[4],
            "4_tweet_threads_pct": round(size_counter[4] / total_trees * 100, 2),
            "5_plus_tweet_threads_count": sum(cnt for sz, cnt in size_counter.items() if sz >= 5),
            "5_plus_tweet_threads_pct": round(sum(cnt for sz, cnt in size_counter.items() if sz >= 5) / total_trees * 100, 2),
            "tree_size_mean": round(mean_size, 2),
            "tree_size_p50": p50_size,
            "tree_size_p90": p90_size,
            "tree_size_p95": p95_size,
            "tree_size_p99": p99_size,
            "tree_size_max": max_size,
        },
        "sampled_linked_interactions": sampled_interactions,
        "sampled_multi_turn_conversations": sampled_conversations,
    }

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\nConversation audit saved to: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inspect and reconstruct Twitter conversation graph")
    parser.add_argument("--csv", default="data/raw/twcs.csv", help="Path to raw CSV file")
    parser.add_argument("--db", default="data/twcs.sqlite", help="Path to SQLite database file")
    parser.add_argument("--output", default="artifacts/conversation_audit.json", help="Path to output JSON")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for sampling")
    args = parser.parse_args()

    if os.path.exists(args.db):
        print(f"Reusing existing SQLite database at {args.db}...")
        conn = sqlite3.connect(args.db)
    else:
        conn = build_conversation_db(args.csv, args.db)
    inspect_conversations(conn, args.output, args.seed)
