# Phase 4 Initial Audit & Repository State Baseline

**Timestamp**: September 2026  
**Auditor**: Senior ML Engineer / Evaluator  
**Status**: Pre-Implementation Verified  

---

## 1. Repository Structure & Existing Modules

```
support-agent/
├── DECISION_LOG.md                         # Decisions 1–25 documented & frozen
├── data/
│   ├── raw/twcs.csv                        # 2,811,774 raw tweets (SHA-256 immutable)
│   ├── twcs.sqlite                         # Indexed SQLite database
│   └── processed/
│       ├── interactions.jsonl              # 106,646 canonical interaction pairs
│       ├── interactions_metadata.json      # Preprocessing lineage & metrics
│       └── splits.json                     # Temporal (80/10/10), Conversation, Customer splits
├── evaluations/
│   └── golden_set/
│       ├── golden_set.jsonl                # 200 human-adjudicated evaluation examples (FROZEN)
│       ├── second_labeler_subset.json      # 50 dual-annotated records (κ = 0.9666, 98.0%)
│       ├── agreement_metrics.json          # Agreement score metrics
│       ├── adjudication.md                 # Disagreement adjudications & boundary rulings
│       ├── labeling_guide.md               # Operational annotation guidelines
│       └── sampling_method.md              # Stratified quota methodology
├── src/
│   ├── data/
│   │   ├── conversations.py                # Causal DAG conversation graph reconstruction
│   │   ├── ingest.py                       # Ingest & indexing
│   │   ├── leakage.py                      # Leakage checks & validation
│   │   ├── preprocessing.py                # Multipart aggregation & text normalization
│   │   └── splitting.py                    # Temporal/Conversation/Customer partitioners
│   └── taxonomy/
│       ├── taxonomy.yaml                   # 11 canonical operational intent definitions
│       ├── taxonomy.json                   # Cached machine-readable taxonomy
│       └── loader.py                       # Taxonomy validation and loading engine
└── tests/
    ├── run_all_tests.py                    # Master test runner
    ├── test_conversations.py               # Tests A, I, P, Q (DAG & ties)
    ├── test_golden_set.py                  # Tests D, E, F, G, H, I, J, K, M (Golden purity)
    ├── test_leakage.py                     # Tests F, G, H, J, K (Temporal non-lookahead)
    ├── test_preprocessing.py               # Tests N, O, R, normalization
    ├── test_splits.py                      # Tests B, C, L, M (Split isolation)
    └── test_taxonomy.py                    # Tests A, B, C, L (Schema & completeness)
```

---

## 2. Frozen Contracts & Pre-Execution Verification

| Contract / Asset | Verification Status | Ground Truth Value |
| :--- | :--- | :--- |
| Target Brand | **VERIFIED** | `AppleSupport` |
| Total Canonical Interactions | **VERIFIED** | 106,646 records |
| Partition Split (Temporal) | **VERIFIED** | Train: 74,652 (70.0%) / Dev: 15,997 (15.0%) / Test: 15,997 (15.0%) |
| Canonical Intents | **VERIFIED** | 11 classes (`taxonomy_v1`) |
| Golden Evaluation Size | **VERIFIED** | 200 records (Dev: 80, Test: 120, Train: 0) |
| Inter-Rater Reliability ($N=50$) | **VERIFIED** | Raw: 98.00%, Cohen's $\kappa = 0.9666$ |
| Golden Train Overlap | **VERIFIED** | 0.00% exact, 0.00% normalized, 0.00% conversation |
| Automated Legacy Tests | **VERIFIED** | 26 / 26 PASS (100%) |

---

## 3. Data Lineage and Information Boundaries

```
Raw CSV / SQLite
      │
      ▼
Conversation DAG Reconstruction (src/data/conversations.py)
      │
      ▼
Canonical Interactions (H_k + C_k -> S_k)
      │
      ├── Train Partition (74,652) ──► Eligible Retrieval Pool & Classifier Training
      ├── Dev Partition (15,997)   ──► Parameter Tuning, Prompting, Development Validation
      └── Test Partition (15,997)  ──► Unseen Generalization Test Pool
                                              ▲
                                              │ (Stratified Sampling)
                                       Golden Evaluation Set (200)
                                       [PROTECTED - FINAL BENCHMARK ONLY]
```

---

## 4. Implementation Risks & Mitigation Strategy

1. **Golden Set Contamination Risk**:
   - *Risk*: A golden example accidentally appears in a retrieval index or demonstration prompt.
   - *Mitigation*: Programmatic exclusion filter in `src/retrieval/filter.py` with hash and ID check against `golden_set.jsonl`, verified by automated integrity tests before every run.

2. **Template Collapse Risk**:
   - *Risk*: Dense/sparse retrieval returns 5 identical boilerplate URLs (e.g. `locate.apple.com`) inflating raw Recall@k without providing diverse diagnostic evidence.
   - *Mitigation*: Implement template clustering and diversification reranking in `src/retrieval/rerank.py` measuring `unique_response_rate@k` and `semantic_diversity@k`.

3. **Intent-Conditioning Error Propagation**:
   - *Risk*: An intent classifier error misroutes retrieval to an irrelevant intent partition, causing catastrophic retrieval failure.
   - *Mitigation*: Explicitly measure Experiment A (unconditioned) vs Experiment B (ground-truth intent) vs Experiment C (predicted intent) to quantify the exact error propagation tax.

4. **Hallucination in High-Risk Workflows**:
   - *Risk*: Response generator invents account unlocks, refunds, or serial number validations.
   - *Mitigation*: First-class escalation policy in `src/escalation/policy.py` routing sensitive queries to `PRIVATE_SUPPORT_REQUIRED` or `HIGH_RISK_ESCALATE`, paired with independent grounding checks.
