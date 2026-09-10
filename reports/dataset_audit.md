# Dataset Audit Report: Customer Support on Twitter

**Analysis Version**: 1.0.0  
**Generated On**: September 2026  
**Auditor**: Lead Data Engineer & Adversarial Evaluator (Antigravity)  
**Target Dataset**: `data/raw/twcs.csv`  

---

## 1. Executive Summary & File-Level Properties

A comprehensive, zero-assumption empirical audit was conducted on the raw Customer Support on Twitter dataset (`twcs.csv`). All metrics were computed via streaming inspection and deterministic SQLite relational indexing (`data/twcs.sqlite`).

### File Properties
- **Exact Path**: `data/raw/twcs.csv`
- **File Size**: 516,508,641 bytes (492.58 MB)
- **SHA-256 Checksum**: `cd297fcfa1bf6f99938be242e8e578980bc6d1b96adc8691abec9a39175b03c0`
- **Encoding**: UTF-8 (CSV formatted with standard commas and RFC 4180 double-quote escaping)
- **Total Records (Rows)**: 2,811,774
- **Total Columns**: 7

---

## 2. Schema & Column-Level Audit

The dataset consists of 7 structured fields. The empirical distribution and nullability of each column across all 2,811,774 rows are summarized below:

| Column Name | Inferred Type | Total Rows | Non-Null Rows | Null Rows | Null % | Unique Values | Description / Semantics |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `tweet_id` | Integer ID | 2,811,774 | 2,811,774 | 0 | **0.00%** | 2,811,774 | Unique identifier for each tweet. 100% unique, zero duplicates. |
| `author_id` | String / Token | 2,811,774 | 2,811,774 | 0 | **0.00%** | 702,777 | Either an anonymized customer ID (702,669 IDs) or a brand handle (108 brands). |
| `inbound` | Boolean | 2,811,774 | 2,811,774 | 0 | **0.00%** | 2 | `True` for incoming customer queries, `False` for support agent responses. |
| `created_at` | Timestamp | 2,811,774 | 2,811,774 | 0 | **0.00%** | 2,126,897 | Date & time in UTC format (`%a %b %d %H:%M:%S %z %Y`). 100% parseable. |
| `text` | String (Text) | 2,811,774 | 2,811,774 | 0 | **0.00%** | 2,752,045 | Message body. Zero empty or whitespace-only records. |
| `response_tweet_id`| String (List) | 2,811,774 | 1,771,145 | 1,040,629 | **37.01%** | 1,720,298 | Comma-separated list of downstream child tweet IDs replying to this tweet. |
| `in_response_to_tweet_id` | Integer ID | 2,811,774 | 2,017,439 | 794,335 | **28.25%** | 1,980,121 | Upstream parent tweet ID that this tweet directly replies to. |

---

## 3. Data Integrity & Anomaly Findings

### 3.1 Tweet ID Uniqueness
- **Result**: PASS (2,811,774 unique IDs).
- **Duplicate ID Rate**: 0.00%. No ID collision or overwriting was detected.

### 3.2 Timestamp Integrity & Chronology
- **Parse Success Rate**: 100.00% (0 invalid timestamps).
- **Earliest Timestamp**: `2008-05-08 20:13:59+00:00`
- **Latest Timestamp**: `2017-12-03 23:14:01+00:00`
- **Active Temporal Span**: 3,496.1 days (~9.5 years), though >85% of records are concentrated between 2016 and late 2017.

### 3.3 Text Corpus Metrics
- **Character Length**:
  - Min: 2 characters (e.g. "@115712 ?")
  - Max: 495 characters (multi-part concatenated tweets / extended handles)
  - Mean: 113.96 characters
  - Median (p50): 115 characters
  - p90: 169 characters | p95: 215 characters
- **Mentions (`@username`)**: 2,752,045 tweets (97.88%) contain at least one user mention (due to Twitter reply conventions).
- **URLs / Hyperlinks**: 631,485 tweets (22.46%) contain web links (knowledge base links, tracking links, DM deep-links).
- **Hashtags (`#topic`)**: 159,126 tweets (5.66%) contain hashtags.

---

## 4. Conversation Graph & Reconstruction Analysis

The dataset is an explicit directed conversation graph connected by `in_response_to_tweet_id` and `response_tweet_id`.

```
           [Root Inbound Customer Tweet] (in_response_to_tweet_id = NULL)
                         │
                         ▼ (in_response_to_tweet_id)
           [Outbound Support Response] (Author = Brand)
                         │
                         ▼ (in_response_to_tweet_id)
           [Customer Follow-up Turn]   (Author = Customer)
```

### 4.1 Parent Pointer Resolution
- **Total Tweets with Parent (`in_response_to_tweet_id` is non-null)**: 2,017,439
- **Resolved Parent Pointers (Parent exists in dataset)**: 2,013,577 (**99.81%**)
- **Dangling Parent Pointers (Parent outside dataset)**: 3,862 (**0.19%**)
- **Root Tweets (True conversation initiators)**: 798,197

### 4.2 Temporal Consistency on Parent-Child Links
- **Strictly Chronological (`Parent.created_ts < Child.created_ts`)**: 2,013,521 (**100.00%**)
- **Timestamp Ties (`Parent.created_ts == Child.created_ts`)**: 56 (<0.003%)
- **Temporal Inversions (`Parent.created_ts > Child.created_ts`)**: **0 (0.00%)**

### 4.3 Turn Transition Topology
Across all 2,013,577 verified parent-child links:
1. **Customer $\rightarrow$ Support Response (`Inbound 1 -> Outbound 0`)**: 1,261,888 links (**62.67%**)
2. **Support $\rightarrow$ Customer Follow-up (`Outbound 0 -> Inbound 1`)**: 559,849 links (**27.80%**)
3. **Customer $\rightarrow$ Customer (`Inbound 1 -> Inbound 1`, Multi-part query)**: 188,447 links (**9.36%**)
4. **Support $\rightarrow$ Support (`Outbound 0 -> Outbound 0`, Thread continuation / agent handoff)**: 3,393 links (**0.17%**)

### 4.4 Conversation Tree Depth Distribution
- **Total Conversation Trees**: 798,197
- **2-turn interactions**: 435,398 trees (**54.55%**)
- **3-turn interactions**: 112,012 trees (**14.03%**)
- **4-turn interactions**: 104,844 trees (**13.14%**)
- **5+ turn interactions**: 145,943 trees (**18.28%**)
- **Mean Conversation Length**: 3.52 tweets
- **Median**: 2 tweets | **p90**: 6 tweets | **p95**: 8 tweets | **p99**: 15 tweets | **Max**: 1,390 tweets (viral mega-thread)

---

## 5. Account & Brand Discovery

There are exactly **108 distinct support accounts (brands)** responsible for all 1,273,931 outbound messages. The remaining 702,669 authors represent inbound customer accounts.

### Top Support Brands by Outbound Volume:
1. `AmazonHelp` (169,840 outbound tweets)
2. `AppleSupport` (106,860 outbound tweets)
3. `Uber_Support` (56,270 outbound tweets)
4. `SpotifyCares` (43,265 outbound tweets)
5. `Delta` (42,253 outbound tweets)
6. `Tesco` (38,573 outbound tweets)
7. `AmericanAir` (36,764 outbound tweets)
8. `TMobileHelp` (34,317 outbound tweets)
9. `comcastcares` (33,031 outbound tweets)
10. `British_Airways` (29,361 outbound tweets)

---

## 6. Key Dataset Anomalies & Limitations

1. **Customer Anonymization**: All customer user handles are masked as numeric tokens (`@115712`), while brand handles remain unmasked (`@AppleSupport`, `@AmazonHelp`).
2. **Missing Out-of-Band Private DMs**: High volumes of conversations terminate with support instructing the customer to send a DM. The subsequent DM resolution occurs off-platform and is not present in the dataset.
3. **Multi-Part Customer Messages**: In ~9.36% of interactions, customers post consecutive tweets because of the 140/280 character limit. A robust pipeline must group consecutive inbound tweets before evaluation.
4. **URL Shorteners**: 22.46% of tweets contain shortened links (`https://t.co/...`).
5. **Dangling Roots (0.19%)**: 3,862 tweets reference parent IDs that were clipped during data collection. These must be treated as orphaned conversation fragments.

---

## 7. Implications for Future Phases

- **Data Unit**: The atomic unit of customer support cannot be treated as an isolated single tweet. It must be framed as a **Contextualized Turn**: $(C_1, S_1, \dots, C_k) \rightarrow S_k$.
- **Leakage Prevention**: Standard random train/test splitting will cause severe data leakage across conversational turns. A **time-based temporal split** or **conversation-tree level split** is mandatory.
- **Escalation Definition**: Support responses that redirect to private channels (DM, phone, website) represent real-world escalation / authentication boundaries and must be modeled explicitly.
