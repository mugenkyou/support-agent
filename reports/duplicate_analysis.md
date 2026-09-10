# Duplicate & Template Repetition Analysis Report

**Target Brand**: `AppleSupport`  
**Phase**: Phase 2 — Dataset Construction & Leakage Control  

---

## 1. Customer Query Duplication

We audited duplication across all 106,646 customer query texts in the canonical `AppleSupport` dataset:

| Duplication Level | Definition / Criteria | Unique Count | Duplicate Count | Duplicate Rate (%) |
| :--- | :--- | :--- | :--- | :--- |
| **Exact Raw Text** | Identical raw string matches (including casing, whitespace, URLs) | 104,821 | 1,825 | **1.71%** |
| **Normalized Text** | Lowercased, whitespace stripped, mentions `<user>` & URLs `<url>` masked | 103,734 | 2,912 | **2.73%** |
| **Short Generic Queries** | Extreme short turns ($\le 15$ chars, e.g. "I did", "thank you", "yes") | 1,210 | 1,480 | **1.39%** |

### Findings on Customer Duplication:
- At **2.73% normalized duplication**, customer queries exhibit exceptional linguistic variety.
- The small fraction of exact duplicates is dominated by short conversational affirmations in multi-turn dialogues (*"I did that"*, *"Still not working"*, *"iOS 11.0.3"*, *"iPhone 7"*).
- The low duplication rate confirms that models cannot achieve high performance simply by memorizing common customer strings.

---

## 2. Support Response Duplication & Template Analysis

We audited repetition across all 106,646 historical `AppleSupport` responses:

| Duplication Level | Definition / Criteria | Unique Count | Duplicate Count | Duplicate Rate (%) |
| :--- | :--- | :--- | :--- | :--- |
| **Exact Raw Response** | Identical raw tweet string (including unique `@customer` mention) | 106,561 | 85 | **0.08%** |
| **Normalized Response** | Lowercased, `@customer` handle masked to `<user>`, URLs masked to `<url>` | 81,872 | 24,774 | **23.23%** |
| **Core Boilerplate Canned Responses** | Repeated $> 100$ times (e.g. DM requests, English-only disclaimer) | 48 templates | 18,210 | **17.07%** |

### Top 5 Repeated Normalized Support Templates:
1. `"<user> we'd love to help. send us a dm with your device model and ios version to get started: <url>"` (5,412 occurrences)
2. `"<user> let's look into this with you. send us a dm to continue: <url>"` (3,840 occurrences)
3. `"<user> we're here to help. send us a dm with what's going on, and we'll take a look: <url>"` (2,915 occurrences)
4. `"<user> since our twitter support is available in english, please visit <url> for help in your region."` (1,248 occurrences)
5. `"<user> let's get this sorted out. what version of ios is currently running on your iphone?"` (985 occurrences)

---

## 3. Cross-Split Duplication & Test Set Integrity

Under the primary `TemporalSplit` (Train: 85,316 | Dev: 10,664 | Test: 10,666):

- **Exact Duplicate Queries (Train $\cap$ Test)**: Exactly **59 queries (0.56%)**.
- **Normalized Duplicate Queries (Train $\cap$ Test)**: Exactly **105 queries (1.00%)**.

### Semantic Similarity vs. Evaluation Contamination
An important engineering distinction is established:
- **Similar Support Problem (Acceptable)**: Two distinct customers experiencing battery drain after updating to iOS 11 using different phrasings (*"My 6s battery dies after 11.0"* vs *"Battery health drops rapidly on iOS 11 update"*). This represents valid real-world evaluation of intent generalization.
- **Unfair Test Contamination (Forbidden)**: A test example retrieving its own exact historical response or an identical conversation thread from the future.
- Automated Test J and Test K verify that exact retrieval contamination is programmatically prevented.
