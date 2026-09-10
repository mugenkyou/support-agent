"""Dataset Structural Audit Script for Hiver SDE Intern Take-Home Phase 1.

Streams through data/raw/twcs.csv to audit:
- File-level properties (size, hash, encoding, line count)
- Schema, column types, missingness, uniqueness
- Integrity of tweet_id, author_id, inbound, created_at, text, response pointers
- Text statistics (lengths, URLs, mentions, hashtags)
- Generates artifacts/dataset_profile.json
"""

import argparse
import csv
import datetime
import hashlib
import json
import math
import os
import re
import sys
from collections import Counter


def compute_sha256(filepath: str, chunk_size: int = 65536) -> str:
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(chunk_size):
            sha256.update(chunk)
    return sha256.hexdigest()


def audit_dataset(csv_path: str, output_profile_path: str, random_seed: int = 42):
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Dataset CSV not found at: {csv_path}")

    file_size = os.path.getsize(csv_path)
    print(f"Auditing file: {csv_path}")
    print(f"File size: {file_size} bytes ({file_size / (1024 * 1024):.2f} MB)")

    print("Computing SHA-256 checksum...")
    sha256_hash = compute_sha256(csv_path)
    print(f"SHA-256: {sha256_hash}")

    # Inspect line count and encoding
    print("Streaming through CSV rows...")
    expected_columns = [
        "tweet_id",
        "author_id",
        "inbound",
        "created_at",
        "text",
        "response_tweet_id",
        "in_response_to_tweet_id",
    ]

    total_rows = 0
    column_non_nulls = Counter()
    column_nulls = Counter()
    column_samples = {col: [] for col in expected_columns}

    # Tweet ID tracking
    seen_tweet_ids = set()
    duplicate_tweet_ids = set()
    malformed_tweet_ids = 0

    # Inbound tracking
    inbound_counts = Counter()

    # Author tracking
    author_counts = Counter()
    inbound_authors = Counter()
    outbound_authors = Counter()

    # Timestamp tracking
    earliest_time = None
    latest_time = None
    invalid_timestamps = 0
    time_format = "%a %b %d %H:%M:%S %z %Y"

    # Text metrics
    text_lengths = []
    text_null_count = 0
    text_empty_count = 0
    text_whitespace_count = 0
    text_with_url = 0
    text_with_mention = 0
    text_with_hashtag = 0

    # Pointer metrics
    response_tweet_id_counts = 0
    response_tweet_multi_counts = 0
    in_response_to_counts = 0
    in_response_to_malformed = 0

    # Length reservoir for percentile calculation
    length_reservoir = []
    reservoir_max = 200000
    import random
    rng = random.Random(random_seed)

    url_pattern = re.compile(r"https?://\S+|www\.\S+")
    mention_pattern = re.compile(r"@\w+")
    hashtag_pattern = re.compile(r"#\w+")

    with open(csv_path, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        actual_columns = reader.fieldnames
        if not actual_columns or actual_columns != expected_columns:
            print(f"Warning: Fieldnames mismatch. Found {actual_columns}, expected {expected_columns}")

        for row in reader:
            total_rows += 1
            if total_rows % 500000 == 0:
                print(f"Processed {total_rows:,} rows...")

            # Column nullability & sample collection
            for col in expected_columns:
                val = row.get(col, "")
                if val is not None and val != "":
                    column_non_nulls[col] += 1
                    if len(column_samples[col]) < 5:
                        column_samples[col].append(val)
                else:
                    column_nulls[col] += 1

            # tweet_id check
            tid = row.get("tweet_id", "")
            if not tid or not tid.isdigit():
                malformed_tweet_ids += 1
            else:
                tid_int = int(tid)
                if tid_int in seen_tweet_ids:
                    duplicate_tweet_ids.add(tid_int)
                else:
                    seen_tweet_ids.add(tid_int)

            # author_id check
            aid = row.get("author_id", "")
            author_counts[aid] += 1

            # inbound check
            inb_val = row.get("inbound", "")
            inbound_counts[inb_val] += 1
            if inb_val.lower() == "true":
                inbound_authors[aid] += 1
            elif inb_val.lower() == "false":
                outbound_authors[aid] += 1

            # timestamp check
            created_str = row.get("created_at", "")
            if created_str:
                try:
                    dt = datetime.datetime.strptime(created_str, time_format)
                    if earliest_time is None or dt < earliest_time:
                        earliest_time = dt
                    if latest_time is None or dt > latest_time:
                        latest_time = dt
                except ValueError:
                    invalid_timestamps += 1
            else:
                invalid_timestamps += 1

            # text analysis
            txt = row.get("text", "")
            if txt is None:
                text_null_count += 1
            elif txt == "":
                text_empty_count += 1
            elif txt.strip() == "":
                text_whitespace_count += 1
            else:
                txt_len = len(txt)
                if len(length_reservoir) < reservoir_max:
                    length_reservoir.append(txt_len)
                else:
                    idx = rng.randint(0, total_rows)
                    if idx < reservoir_max:
                        length_reservoir[idx] = txt_len

                if url_pattern.search(txt):
                    text_with_url += 1
                if mention_pattern.search(txt):
                    text_with_mention += 1
                if hashtag_pattern.search(txt):
                    text_with_hashtag += 1

            # response_tweet_id
            resp_id = row.get("response_tweet_id", "")
            if resp_id:
                response_tweet_id_counts += 1
                if "," in resp_id:
                    response_tweet_multi_counts += 1

            # in_response_to_tweet_id
            in_resp_id = row.get("in_response_to_tweet_id", "")
            if in_resp_id:
                in_response_to_counts += 1
                if not in_resp_id.isdigit():
                    in_response_to_malformed += 1

    length_reservoir.sort()
    p50_len = length_reservoir[int(len(length_reservoir) * 0.50)] if length_reservoir else 0
    p90_len = length_reservoir[int(len(length_reservoir) * 0.90)] if length_reservoir else 0
    p95_len = length_reservoir[int(len(length_reservoir) * 0.95)] if length_reservoir else 0
    mean_len = sum(length_reservoir) / len(length_reservoir) if length_reservoir else 0
    min_len = length_reservoir[0] if length_reservoir else 0
    max_len = length_reservoir[-1] if length_reservoir else 0

    profile = {
        "metadata": {
            "dataset_path": csv_path,
            "analysis_version": "1.0.0",
            "generation_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "random_seed": random_seed,
        },
        "file_properties": {
            "file_size_bytes": file_size,
            "file_size_mb": round(file_size / (1024 * 1024), 2),
            "sha256_checksum": sha256_hash,
            "encoding": "utf-8",
            "delimiter": ",",
            "total_rows": total_rows,
            "column_count": len(actual_columns) if actual_columns else 0,
            "columns": actual_columns,
        },
        "column_statistics": {},
        "integrity_checks": {
            "unique_tweet_ids_count": len(seen_tweet_ids),
            "duplicate_tweet_ids_count": len(duplicate_tweet_ids),
            "duplicate_tweet_id_rate": len(duplicate_tweet_ids) / total_rows if total_rows else 0,
            "malformed_tweet_ids": malformed_tweet_ids,
            "invalid_timestamps": invalid_timestamps,
            "earliest_timestamp": earliest_time.isoformat() if earliest_time else None,
            "latest_timestamp": latest_time.isoformat() if latest_time else None,
            "inbound_values_distribution": dict(inbound_counts),
            "malformed_in_response_to_tweet_id": in_response_to_malformed,
        },
        "text_statistics": {
            "null_text_count": text_null_count,
            "empty_text_count": text_empty_count,
            "whitespace_only_text_count": text_whitespace_count,
            "char_length_min": min_len,
            "char_length_max": max_len,
            "char_length_mean": round(mean_len, 2),
            "char_length_median_p50": p50_len,
            "char_length_p90": p90_len,
            "char_length_p95": p95_len,
            "tweets_with_url_count": text_with_url,
            "tweets_with_url_pct": round((text_with_url / total_rows) * 100, 2) if total_rows else 0,
            "tweets_with_mention_count": text_with_mention,
            "tweets_with_mention_pct": round((text_with_mention / total_rows) * 100, 2) if total_rows else 0,
            "tweets_with_hashtag_count": text_with_hashtag,
            "tweets_with_hashtag_pct": round((text_with_hashtag / total_rows) * 100, 2) if total_rows else 0,
        },
        "response_pointer_statistics": {
            "rows_with_response_tweet_id": response_tweet_id_counts,
            "rows_with_response_tweet_id_pct": round((response_tweet_id_counts / total_rows) * 100, 2) if total_rows else 0,
            "rows_with_multiple_responses": response_tweet_multi_counts,
            "rows_with_in_response_to_tweet_id": in_response_to_counts,
            "rows_with_in_response_to_tweet_id_pct": round((in_response_to_counts / total_rows) * 100, 2) if total_rows else 0,
        },
        "author_statistics": {
            "total_unique_authors": len(author_counts),
            "total_inbound_authors": len(inbound_authors),
            "total_outbound_authors": len(outbound_authors),
            "top_20_authors_by_volume": [
                {"author_id": aid, "total_tweets": count, "outbound_count": outbound_authors[aid], "inbound_count": inbound_authors[aid]}
                for aid, count in author_counts.most_common(20)
            ],
        },
    }

    for col in expected_columns:
        non_null = column_non_nulls[col]
        null_count = column_nulls[col]
        null_pct = round((null_count / total_rows) * 100, 2) if total_rows else 0
        profile["column_statistics"][col] = {
            "total_rows": total_rows,
            "non_null_rows": non_null,
            "null_rows": null_count,
            "null_percentage": null_pct,
            "sample_values": column_samples[col],
        }

    os.makedirs(os.path.dirname(output_profile_path), exist_ok=True)
    with open(output_profile_path, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2)

    print(f"\nAudit complete! Profile saved to: {output_profile_path}")
    print(f"Total Rows: {total_rows:,}")
    print(f"Unique Tweet IDs: {len(seen_tweet_ids):,}")
    print(f"Unique Authors: {len(author_counts):,}")
    print(f"Date Range: {earliest_time} to {latest_time}")
    print(f"Top 5 Authors: {author_counts.most_common(5)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Audit customer support twitter dataset")
    parser.add_argument("--csv", default="data/raw/twcs.csv", help="Path to raw CSV file")
    parser.add_argument("--output", default="artifacts/dataset_profile.json", help="Path to output profile JSON")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for sampling")
    args = parser.parse_args()

    audit_dataset(args.csv, args.output, args.seed)
