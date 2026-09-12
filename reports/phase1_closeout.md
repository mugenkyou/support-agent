# Phase 1 Closeout Report: Dataset Audit, Brand Selection & Problem Framing

**Phase Status**: **PASS — FROZEN**  
**Lead Evaluator / Engineer**: Senior ML & Data Engineer (Antigravity)  
**Target Brand**: **`AppleSupport`**  
**Date**: September 2026  

---

## 1. What We Verified

1. **Raw Dataset Integrity & Preservation**:
   - `data/raw/twcs.csv` is preserved in its immutable state (516,508,641 bytes; SHA-256: `cd297fcfa1bf6f99938be242e8e578980bc6d1b96adc8691abec9a39175b03c0`).
   - Exactly **2,811,774 rows** and **7 columns**. 100% unique `tweet_id`s (0 duplicates, 0 nulls, 0 malformed IDs).
   - Exactly **702,777 unique authors** (702,669 anonymized customer IDs and 108 support accounts).
2. **Graph Topology & Pointers**:
   - 2,013,577 of 2,017,439 parent references (**99.81%**) resolve cleanly within the dataset; only 3,862 (**0.19%**) are clipped roots.
   - Total conversation trees: **798,197** (Mean size: 3.52 tweets; Median: 2; p90: 6; Max: 1,390).
3. **Temporal Ordering**:
   - Strict chronological ordering ($P_{\text{created\_at}} < C_{\text{created\_at}}$): **2,013,521 links (99.9972%)**.
   - Timestamp ties ($P_{\text{created\_at}} == C_{\text{created\_at}}$): **56 links (0.0028%)**.
   - Temporal inversions ($P_{\text{created\_at}} > C_{\text{created\_at}}$): **0 links (0.0000%)**.
4. **AppleSupport Corpus Metrics**:
   - Total outbound volume: **106,860 tweets**.
   - Usable customer $\rightarrow$ support interaction pairs: **106,646**.
   - Unique customers served: **76,365** (Rank 1 across all 108 brands).
   - Top-10 customer volume concentration: **0.16%** (virtually zero distortion by super-users).
   - Median response latency: **70.97 minutes** (p75: 207.9m; p90: 446.6m).

---

## 2. What We Corrected

During the adversarial audit, several assumptions and claims were corrected based on direct empirical measurements:

1. **Inbound $\rightarrow$ Inbound Link Disambiguation**:
   - *Previous Assumption*: Claimed that all 188,447 (9.36%) Inbound $\rightarrow$ Inbound links represented multipart customer messages.
   - *Empirical Correction*: Detailed author inspection revealed that **103,028 (54.67%)** are **third-party customer comments** (different customers replying on public threads), and only **85,419 (45.33%)** share the same author ID. Furthermore, only 35,434 of these same-author links occur within $\le 120$s.
2. **Removal of Pseudo-Precision Confidence Numbers**:
   - *Previous Prose*: Included arbitrary percentages such as "92% Grounded Empirical Confidence", "98% Confidence", etc.
   - *Correction*: Removed all artificial numerical precision. Replaced with well-defined qualitative confidence levels (`HIGH`, `MEDIUM`, `LOW`) backed by explicit methodological criteria.
3. **Response Coverage vs. Resolution Rate**:
   - *Clarification*: Clarified that `response_coverage_pct` (84.56% for AppleSupport) measures historical public reply availability, not successful problem resolution.
4. **Historical DM Redirection vs. Operational Ground Truth**:
   - *Clarification*: 52.58% of AppleSupport responses requested a private DM. Corrected framing to treat this as a *historical private-channel boundary*, rather than assuming that all such cases fundamentally mandate human intervention.
5. **Separation of Timestamp Ties from Strict Chronology**:
   - *Correction*: Separated the 56 timestamp ties (0.0028%) from strictly chronological links (99.9972%) rather than loosely stating "100% strictly chronological".

---

## 3. Selected Brand: `AppleSupport`

`AppleSupport` is formally confirmed as the target brand for the Hiver SDE Intern assignment.

| Dimension | `AppleSupport` Metric | Ranking / Significance |
| :--- | :--- | :--- |
| **Usable Interaction Pairs** | 106,646 | Substantial volume for training and evaluation |
| **Unique Customers** | 76,365 | **Rank 1** across all 108 brands in dataset |
| **Customer Concentration (Top 10)** | 0.16% | Lowest customer skew; highly representative |
| **Normalized Query Duplication** | 2.73% | High lexical query diversity |
| **Multi-Turn Interactions** | 31,350 (29.40%) | High conversational troubleshooting depth |
| **Language Distribution** | >97% English | Clean monolingual corpus |
| **Domain Scope** | iOS, macOS, watchOS, iCloud | Natural diagnostic structure & clear escalation lines |

---

## 4. Why `AppleSupport` Survived Adversarial Review

1. **Versus `AmazonHelp`**: `AmazonHelp` had higher total volume (169k vs 106k), but was rejected because >30% of its data is unlabelled multilingual text (Japanese, German, Spanish, French, Italian), and its English tweets primarily consist of generic order-lookup links (`amazon.com/contact-us`) without public diagnostic depth.
2. **Versus `Uber_Support`**: `Uber_Support` exhibits 64.23% normalized template repetition, dominated by canned fare-dispute responses.
3. **Versus Telecom Brands (`TMobileHelp`, `sprintcare`, `comcastcares`)**: Telecoms have >72–82% immediate DM deflection rates with almost zero public troubleshooting.
4. **Versus `SpotifyCares`**: `SpotifyCares` is clean, but has smaller volume (43k) and is limited to a single media app, whereas Apple encompasses an entire operating system and device ecosystem.

---

## 5. Dataset Risks & Mitigations

| Risk | Description | Phase 2 / 3 Mitigation |
| :--- | :--- | :--- |
| **Unobservable Private DMs** | 52.58% of interactions redirect to DM; the resolution is not in the dataset. | Model DM deflection as an explicit `ESCALATE_TO_PRIVATE_CHANNEL` action. |
| **Temporal OS Drift** | Dataset is concentrated in Oct-Nov 2017 during iOS 11 launch; settings and UI changed across iOS 9/10/11. | Enforce strict chronological time-based train/test splitting; evaluate temporal generalization explicitly. |
| **Shortened Links** | 75.37% of replies link to `support.apple.com/HT...` via `t.co` shorteners. | Abstract link generation to validated canonical support topic categories. |
| **Third-Party Noise in Threads** | 54.67% of Inbound $\rightarrow$ Inbound links are other customers interjecting. | Filter conversation threads by `(Author == Target Customer) OR (Author == AppleSupport)` during tree reconstruction. |

---

## 6. Prediction-Time Information Boundary

To eliminate data leakage, the exact prediction-time information boundary is formally defined:

$$\text{Input Context for Turn } k: \mathcal{H}_k = (C_1, S_1, C_2, S_2, \dots, C_k)$$

- **Available**: All prior conversation turns $(C_1 \dots C_k)$ occurring at timestamps $t \le T(C_k)$.
- **Strictly Forbidden**: The target support response $S_k$, subsequent customer follow-ups $(C_{k+1}, \dots)$, and any global dataset events with timestamps $t > T(C_k)$.

---

## 7. Historical Grounding Boundary

- **Primary Evidence Source**: Historical `AppleSupport` conversation interactions in `twcs.csv`.
- **Constraint**: The benchmark must evaluate the agent's ability to learn and reproduce historical brand support workflows.
- **External Documentation Rule**: Modern Apple documentation (post-2017) must **NOT** be silently injected into the primary evaluation benchmark, as it would cause anachronistic contamination (e.g. referencing iOS 16/17 features for an iOS 11 problem).

---

## 8. Open Questions for Phase 2

1. **Multipart Heuristic Refinement**: What combination of time-delta ($\le 60$s vs $\le 120$s) and NLP signals (sentence continuation, "1/2" indicators) yields optimal grouping precision for same-author inbound chains?
2. **Conversation Context Window**: Should context truncation be fixed at $N$ turns (e.g., last 3 turns) or dynamic based on token length?
3. **Temporal Split Cutoff Date**: What exact calendar cutoff (e.g. Nov 15, 2017) produces the most balanced Train vs Test distribution for iOS 11 support surge evaluation?
4. **Handling Ambiguous Historical DM Replies**: How to evaluate customer turns where Apple Support requested a DM without prior diagnostic questioning?

---

## 9. Automated Regression Test Suite (18/18 Tests Passed)

All 18 automated tests in [`scripts/run_phase1_tests.py`](scripts/run_phase1_tests.py) executed and passed:
- `TEST A (Schema Integrity)`: **PASS**
- `TEST B (Tweet ID Integrity)`: **PASS**
- `TEST C (Timestamp Integrity)`: **PASS**
- `TEST D (Inbound Integrity)`: **PASS**
- `TEST E (Response References)`: **PASS**
- `TEST F (Conversation Reconstruction)`: **PASS**
- `TEST G (Response Validity)`: **PASS**
- `TEST H (Brand Identification)`: **PASS**
- `TEST I (Duplicate Contamination)`: **PASS**
- `TEST J (Temporal Leakage)`: **PASS**
- `TEST K (Sampling Reproducibility)`: **PASS**
- `TEST L (Brand Ranking Reproducibility)`: **PASS**
- `TEST M (Timestamp Ties Accounting)`: **PASS**
- `TEST N (Inbound->Inbound Disambiguation)`: **PASS**
- `TEST O (Prediction Boundary Enforcement)`: **PASS**
- `TEST P (Multi-Criteria Selection Reproducibility)`: **PASS**
- `TEST Q (Raw Data Immutability Check)`: **PASS**
- `TEST R (Claim Metrics Reproducibility)`: **PASS**

---

## 10. Final Acceptance Decision

```text
================================================================================
FINAL PHASE 1 STATUS: PASS — FROZEN
================================================================================
```

The dataset audit, brand selection (`AppleSupport`), causal information boundary, and foundational methodology are empirically verified, reproducible, and formally frozen. Phase 1 is officially closed.
