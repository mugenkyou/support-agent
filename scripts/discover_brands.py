"""Brand Discovery and Comparative Evaluation Script for Hiver SDE Intern Take-Home Phase 1.

Identifies and evaluates candidate support brands across:
- Volume (outbound, inbound, total)
- Customer diversity (unique customers, concentration)
- Usable customer -> support interaction pairs
- Response coverage & conversation reconstruction
- Multi-turn conversation depth
- Duplicate rates (exact & normalized query duplicates)
- Support template repetition rate
- Support behavior characteristics (DM redirects, external link redirects, action requests)
- Generates reports/brand_comparison.csv
"""

import argparse
import csv
import datetime
import json
import os
import re
import sqlite3
from collections import Counter, defaultdict


def normalize_text(text: str) -> str:
    # Remove mentions, URLs, punctuation, extra whitespace, lowercase
    t = re.sub(r"https?://\S+|www\.\S+", "", text)
    t = re.sub(r"@\w+", "", t)
    t = re.sub(r"[^\w\s]", " ", t)
    t = re.sub(r"\s+", " ", t).strip().lower()
    return t


def analyze_brands(db_path: str, output_csv: str = "reports/brand_comparison.csv", min_outbound: int = 5000):
    print(f"Connecting to SQLite database at {db_path}...")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    print("Fetching list of support accounts (outbound authors)...")
    cur.execute("""
    SELECT author_id, COUNT(*) as cnt
    FROM tweets
    WHERE inbound = 0
    GROUP BY author_id
    HAVING cnt >= ?
    ORDER BY cnt DESC
    """, (min_outbound,))
    candidate_brands = cur.fetchall()
    print(f"Found {len(candidate_brands)} brands with >= {min_outbound:,} outbound tweets.")

    results = []

    dm_regex = re.compile(r"\b(dm|direct message|private message|pm|send us a dm|dm us|message us)\b", re.IGNORECASE)
    link_regex = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)

    for idx, (brand, outbound_count) in enumerate(candidate_brands, start=1):
        print(f"[{idx}/{len(candidate_brands)}] Analyzing brand: {brand} (outbound: {outbound_count:,})...")

        # 1. Usable Customer -> Support interactions (Inbound message directly replied by this brand)
        cur.execute("""
        SELECT p.tweet_id, p.author_id, p.text, p.created_ts,
               c.tweet_id, c.text, c.created_ts
        FROM tweets c
        JOIN tweets p ON c.in_response_to_tweet_id = p.tweet_id
        WHERE c.author_id = ? AND c.inbound = 0 AND p.inbound = 1
        """, (brand,))
        interactions = cur.fetchall()
        usable_pairs_count = len(interactions)

        # 2. Total Inbound Tweets addressed to this brand (either replied to by brand, or mentioning @brand)
        # To be precise and fast: customer tweets replied by brand + customer tweets mentioning @brand
        cur.execute("""
        SELECT COUNT(DISTINCT tweet_id) FROM (
            SELECT p.tweet_id FROM tweets c
            JOIN tweets p ON c.in_response_to_tweet_id = p.tweet_id
            WHERE c.author_id = ? AND c.inbound = 0 AND p.inbound = 1
            UNION
            SELECT tweet_id FROM tweets
            WHERE inbound = 1 AND text LIKE ?
        )
        """, (brand, f"%@{brand}%"))
        total_inbound_estimated = cur.fetchone()[0]

        # 3. Unique Customers
        unique_customers = set(r[1] for r in interactions)
        unique_customers_count = len(unique_customers)

        # 4. Customer concentration (top 1% / top 10 customers share)
        customer_counts = Counter(r[1] for r in interactions)
        top_10_cust_volume = sum(cnt for _, cnt in customer_counts.most_common(10))
        top_10_cust_share = (top_10_cust_volume / usable_pairs_count * 100) if usable_pairs_count else 0.0

        # 5. Customer Query Duplication (Exact and Normalized)
        customer_texts = [r[2] for r in interactions]
        unique_exact_queries = len(set(customer_texts))
        exact_duplicate_rate = (1.0 - (unique_exact_queries / usable_pairs_count)) * 100 if usable_pairs_count else 0.0

        normalized_customer_texts = [normalize_text(t) for t in customer_texts if len(normalize_text(t)) > 5]
        unique_norm_queries = len(set(normalized_customer_texts))
        norm_duplicate_rate = (1.0 - (unique_norm_queries / len(normalized_customer_texts))) * 100 if normalized_customer_texts else 0.0

        # 6. Support Response Template Repetition
        support_texts = [r[5] for r in interactions]
        unique_exact_responses = len(set(support_texts))
        support_exact_repeat_rate = (1.0 - (unique_exact_responses / len(support_texts))) * 100 if support_texts else 0.0

        normalized_support_texts = [normalize_text(t) for t in support_texts if len(normalize_text(t)) > 5]
        unique_norm_responses = len(set(normalized_support_texts))
        support_norm_repeat_rate = (1.0 - (unique_norm_responses / len(normalized_support_texts))) * 100 if normalized_support_texts else 0.0

        # 7. Support DM and Link redirection rates
        dm_count = sum(1 for t in support_texts if dm_regex.search(t))
        dm_redirect_rate = (dm_count / len(support_texts) * 100) if support_texts else 0.0

        link_count = sum(1 for t in support_texts if link_regex.search(t))
        link_share_rate = (link_count / len(support_texts) * 100) if support_texts else 0.0

        # 8. Date Range
        cur.execute("SELECT MIN(created_ts), MAX(created_ts) FROM tweets WHERE author_id = ?", (brand,))
        min_ts, max_ts = cur.fetchone()
        start_date = datetime.datetime.fromtimestamp(min_ts, datetime.timezone.utc).strftime("%Y-%m-%d") if min_ts else "N/A"
        end_date = datetime.datetime.fromtimestamp(max_ts, datetime.timezone.utc).strftime("%Y-%m-%d") if max_ts else "N/A"
        days_span = round((max_ts - min_ts) / 86400, 1) if (min_ts and max_ts) else 0

        # 9. Multi-turn conversation depth for this brand
        # Trace conversations where this brand participated:
        # A conversation is initiated by customer -> replied by brand -> customer replies back
        cur.execute("""
        SELECT COUNT(DISTINCT c.tweet_id)
        FROM tweets f
        JOIN tweets c ON f.in_response_to_tweet_id = c.tweet_id
        JOIN tweets p ON c.in_response_to_tweet_id = p.tweet_id
        WHERE c.author_id = ? AND c.inbound = 0 AND p.inbound = 1 AND f.inbound = 1
        """, (brand,))
        multi_turn_count = cur.fetchone()[0]
        multi_turn_rate = (multi_turn_count / usable_pairs_count * 100) if usable_pairs_count else 0.0

        # Response coverage: usable pairs / total estimated inbound
        response_coverage = (usable_pairs_count / total_inbound_estimated * 100) if total_inbound_estimated else 0.0

        row = {
            "brand": brand,
            "total_outbound_tweets": outbound_count,
            "estimated_inbound_tweets": total_inbound_estimated,
            "usable_support_interactions": usable_pairs_count,
            "response_coverage_pct": round(response_coverage, 2),
            "unique_customers": unique_customers_count,
            "customer_concentration_top10_pct": round(top_10_cust_share, 2),
            "multi_turn_interactions": multi_turn_count,
            "multi_turn_rate_pct": round(multi_turn_rate, 2),
            "exact_query_duplicate_pct": round(exact_duplicate_rate, 2),
            "norm_query_duplicate_pct": round(norm_duplicate_rate, 2),
            "support_template_exact_repeat_pct": round(support_exact_repeat_rate, 2),
            "support_template_norm_repeat_pct": round(support_norm_repeat_rate, 2),
            "dm_redirect_rate_pct": round(dm_redirect_rate, 2),
            "link_share_rate_pct": round(link_share_rate, 2),
            "date_start": start_date,
            "date_end": end_date,
            "days_active": days_span,
        }
        results.append(row)

    # Sort results by usable support interactions
    results.sort(key=lambda x: x["usable_support_interactions"], reverse=True)

    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    fieldnames = list(results[0].keys()) if results else []
    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"\nBrand comparison report saved to: {output_csv}")
    print("\n--- Top 10 Candidate Brands by Usable Interactions ---")
    header_fmt = "{:<16} | {:<12} | {:<12} | {:<10} | {:<12} | {:<10} | {:<10} | {:<10}"
    print(header_fmt.format("Brand", "Outbound", "Usable Pairs", "Resp Cov %", "Unique Cust", "Multi-Turn%", "Query Dup%", "DM Redir%"))
    print("-" * 105)
    for r in results[:10]:
        print(header_fmt.format(
            r["brand"],
            f"{r['total_outbound_tweets']:,}",
            f"{r['usable_support_interactions']:,}",
            f"{r['response_coverage_pct']}%",
            f"{r['unique_customers']:,}",
            f"{r['multi_turn_rate_pct']}%",
            f"{r['norm_query_duplicate_pct']}%",
            f"{r['dm_redirect_rate_pct']}%",
        ))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze and rank customer support brands")
    parser.add_argument("--db", default="data/twcs.sqlite", help="Path to SQLite database file")
    parser.add_argument("--output", default="reports/brand_comparison.csv", help="Path to output CSV")
    parser.add_argument("--min_outbound", type=int, default=5000, help="Minimum outbound tweets to consider")
    args = parser.parse_args()

    analyze_brands(args.db, args.output, args.min_outbound)
