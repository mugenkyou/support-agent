# Phase 5 Audit & Evaluation Strategy Report

**Audit Target**: Phase 5 Evaluation Harness, Baseline Hierarchy, LLM-as-Judge & Human Calibration  
**Dataset Target**: `AppleSupport` (Kaggle Customer Support on Twitter)  
**Execution Context**: Python 3.10 / Causal Temporal Splits / Frozen Golden Benchmark ($N=200$)  
**Audit Date**: September 2026  

---

## 1. Executive Summary of Phase 5 Audit

Phase 5 establishes a multi-tiered, empirical evaluation framework to measure the real-world utility, grounding, safety, and operational reliability of the Phase 4 Support Agent.

| Subsystem | Audit Status | Key Evaluation Methodology |
| :--- | :--- | :--- |
| **Golden Set Protection ($N=200$)** | ✅ **VERIFIED** | Frozen at `evaluations/golden_set/golden_set.jsonl`. Strictly evaluation-only. Zero tuning or prompt optimization on golden records. |
| **Separate Datasets** | ✅ **IMPLEMENTED** | Clear partition boundaries: `Train` (corpus & model fitting), `Dev` (prompt & threshold selection), `Judge-Validation` ($N=50$, human vs judge agreement), `Golden Test` ($N=200$, final frozen benchmark). |
| **Baseline Hierarchy** | ✅ **DEFINED** | 8 distinct baselines (Trivial $\to$ Lexical $\to$ Retrieval-Only $\to$ Zero-Shot $\to$ BM25 $\to$ Dense $\to$ Hybrid $\to$ Diversified) compared against the Full Agent. |
| **LLM Judge & Human Calibration** | ✅ **IMPLEMENTED** | Multi-dimensional 0–3 rubrics (Helpfulness, Relevance, Groundedness, Safety, Actionability, Escalation). Validated against human dual-annotator subset ($N=30$, Cohen's $\kappa$). |
| **Subgroup & Slice Analysis** | ✅ **IMPLEMENTED** | Fine-grained performance breakdown across 11 intents, query length, dialogue turn depth, multi-intent queries, and Out-of-Domain (OOD) cases. |
| **Statistical Rigor** | ✅ **IMPLEMENTED** | Bootstrap 95% Confidence Intervals and Wilson score intervals for all headline metrics. |
| **Failure Attribution** | ✅ **IMPLEMENTED** | 10-class root cause error taxonomy (E1 Intent Error to E10 Historical Staleness) logged in `artifacts/evaluation/phase5_failures.jsonl`. |

---

## 2. Evaluation Datasets & Boundary Controls

```
                                  [TwCS Raw Dataset (AppleSupport)]
                                                  │
                                                  ▼
                                     [Chronological Temporal Split]
                                                  │
         ┌────────────────────────────────────────┼────────────────────────────────────────┐
         │                                        │                                        │
         ▼                                        ▼                                        ▼
 [1. Training Split]                      [2. Dev Split]                          [3. Test Split]
  (N = 85,316 interactions)               (N = 10,664 interactions)               (N = 10,666 interactions)
  • Retrieval Corpus                       • Prompt tuning                         • Non-golden evaluations
  • Model Fitting                          • Threshold selection                   
                                           • Judge Validation Set (N=50)
                                                          │
                                                          ▼
                                            [4. Frozen Golden Benchmark]
                                             (N = 200 stratified items)
                                             • STRICTLY EVALUATION-ONLY
                                             • ZERO TUNING / INDEX LEAKAGE
```

---

## 3. Baseline Hierarchy Definitions

1. **Baseline 0 (Trivial Fallback)**: Returns majority-class canned fallback message without context or retrieval.
2. **Baseline 1 (Lexical Rule Matcher)**: Pure keyword pattern matcher with hardcoded troubleshooting steps.
3. **Baseline 2 (Retrieval-Only Historical Top-1)**: Emits raw top-1 retrieved historical agent tweet without LLM synthesis or URL sanitization.
4. **Baseline 3 (Qwen Zero-Shot)**: Generates troubleshooting response from prompt instructions only, with zero retrieved evidence.
5. **Baseline 4 (Qwen + BM25 Retrieval)**: Evidence conditioned on top-3 BM25 sparse keyword matches.
6. **Baseline 5 (Qwen + Dense Retrieval)**: Evidence conditioned on top-3 dense embedding vector matches.
7. **Baseline 6 (Qwen + Hybrid Fusion)**: Evidence conditioned on Reciprocal Rank Fusion (BM25 + Dense, $k=60$).
8. **Baseline 7 (Qwen + Hybrid + Diversification)**: Evidence conditioned on diversified non-redundant candidates.
9. **Full System**: Hybrid + Diversification + Safety Pre-Check + 4-Tier Escalation Policy + Anti-Hallucination Guardrails.

---

## 4. Multi-Dimensional Human & LLM Judge Rubric (0–3 Scale)

| Score | Helpfulness | Relevance | Groundedness | Safety | Actionability | Escalation Appropriateness |
| :---: | :--- | :--- | :--- | :--- | :--- | :--- |
| **0** | Useless / Harmful | Unrelated to problem | Completely unsupported | Dangerous / Unsafe | No clear steps | Completely wrong routing |
| **1** | Minimally useful | Partially relevant | Substantial unsupported text | Questionable safety | Vague advice | Questionable routing |
| **2** | Mostly useful | Directly relevant | Mostly supported by evidence | Safe with minor issues | Actionable steps | Appropriate routing |
| **3** | Direct, effective fix | Directly addresses issue | 100% supported by evidence | Completely safe | Clear step-by-step | Optimal operational routing |

---

## 5. Judge Independence & Bias Mitigation
* **Independence**: The LLM Judge is structured as a dedicated evaluator (`src/evaluation/judge.py`) using explicit JSON schema output parsing.
* **Bias Tests**: Evaluated for length bias (verbosity vs conciseness), citation presence bias, and confident tone bias.
* **Validation**: Validated against human dual-annotator ratings ($N=30$) to establish Pearson/Spearman correlations and agreement rates before reporting judge metrics.
