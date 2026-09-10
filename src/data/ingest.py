"""Raw data loading, schema validation, and brand extraction."""

import csv
import hashlib
import os
import sqlite3
from typing import Dict, Any, List, Optional

RAW_CSV_PATH = "data/raw/twcs.csv"
SQLITE_DB_PATH = "data/twcs.sqlite"
EXPECTED_SHA256 = "cd297fcfa1bf6f99938be242e8e578980bc6d1b96adc8691abec9a39175b03c0"
EXPECTED_COLUMNS = [
    "tweet_id",
    "author_id",
    "inbound",
    "created_at",
    "text",
    "response_tweet_id",
    "in_response_to_tweet_id",
]


def verify_raw_data_integrity(csv_path: str = RAW_CSV_PATH) -> bool:
    """Verifies that the raw CSV file exists and matches the verified SHA-256 hash."""
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Raw CSV file not found at: {csv_path}")

    sha256 = hashlib.sha256()
    with open(csv_path, "rb") as f:
        while chunk := f.read(65536):
            sha256.update(chunk)
    file_hash = sha256.hexdigest()
    if file_hash != EXPECTED_SHA256:
        raise ValueError(f"Raw CSV SHA-256 mismatch! Expected {EXPECTED_SHA256}, found {file_hash}")
    return True


def get_db_connection(db_path: str = SQLITE_DB_PATH) -> sqlite3.Connection:
    """Gets connection to the indexed SQLite database."""
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database file not found at: {db_path}")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def fetch_brand_tweets(brand: str = "AppleSupport", db_path: str = SQLITE_DB_PATH) -> List[sqlite3.Row]:
    """Fetches all tweets authored by the brand."""
    conn = get_db_connection(db_path)
    cur = conn.cursor()
    cur.execute("""
    SELECT tweet_id, author_id, inbound, created_at, created_ts, text, response_tweet_id, in_response_to_tweet_id
    FROM tweets
    WHERE author_id = ?
    ORDER BY created_ts ASC, tweet_id ASC
    """, (brand,))
    return cur.fetchall()


def fetch_all_relevant_brand_conversations(brand: str = "AppleSupport", db_path: str = SQLITE_DB_PATH) -> Dict[str, Any]:
    """Fetches all brand tweets and their direct/upstream customer conversation parent tweets."""
    conn = get_db_connection(db_path)
    cur = conn.cursor()

    # Get all outbound brand tweets
    cur.execute("""
    SELECT tweet_id, author_id, inbound, created_at, created_ts, text, response_tweet_id, in_response_to_tweet_id
    FROM tweets
    WHERE author_id = ?
    """, (brand,))
    brand_tweets = cur.fetchall()

    # Get all customer tweets that are parents of brand tweets
    cur.execute("""
    SELECT p.tweet_id, p.author_id, p.inbound, p.created_at, p.created_ts, p.text, p.response_tweet_id, p.in_response_to_tweet_id
    FROM tweets c
    JOIN tweets p ON c.in_response_to_tweet_id = p.tweet_id
    WHERE c.author_id = ? AND c.inbound = 0 AND p.inbound = 1
    """, (brand,))
    parent_customer_tweets = cur.fetchall()

    return {
        "brand": brand,
        "brand_tweets_count": len(brand_tweets),
        "parent_customer_tweets_count": len(parent_customer_tweets),
    }


if __name__ == "__main__":
    print("Verifying raw data integrity...")
    verify_raw_data_integrity()
    print("Raw data hash verified: PASS")
    stats = fetch_all_relevant_brand_conversations("AppleSupport")
    print(f"Loaded AppleSupport records: {stats['brand_tweets_count']:,} outbound, {stats['parent_customer_tweets_count']:,} parent customer turns.")
