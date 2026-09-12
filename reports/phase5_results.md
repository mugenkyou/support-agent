# Phase 5: Evaluation Harness, Baselines & LLM-Judge Validation

**Target Brand**: `AppleSupport` (Kaggle Customer Support on Twitter)  
**Evaluation Scope**: Baseline Hierarchy, Multidimensional Response Quality, Human vs. LLM-Judge Calibration, Subgroup & OOD Slices, Statistical Uncertainty  
**Benchmark Domain**: Historical 2017 / iOS 11-era Twitter Customer Support  
**Status**: **PASS — FROZEN**  

---

## 1. Evaluation Objective

Phase 5 empirically determines whether the evidence-grounded Conversational AI Support Agent built in Phase 4 outperforms trivial, lexical, ungrounded, and raw retrieval baselines across **Helpfulness, Relevance, Groundedness, Safety, Actionability, and Escalation Appropriateness**. The evaluation framework prioritizes **evaluator reliability, statistical defensibility, and transparent limitation reporting** over inflated single-metric headline scores.

---

## 2. Dataset and Evaluation Boundaries

The evaluation operates on strictly partitioned historical data:
- **Training Set ($N = 85,316$)**: Sole evidence source for candidate retrieval indexes and classifier fitting.
- **Dev Set ($N = 10,664$)**: Used for hyperparameter tuning and prompt verification.
- **Judge-Validation Set ($N = 50$)**: Non-golden dev sample used to calibrate the LLM Judge against human raters.
- **Frozen Golden Benchmark ($N = 200$)**: Protected stratified evaluation set ($t_{\text{cand}} < t_{\text{query}}$).

---

## 3. Golden Set Protection

The 200-example Phase 3 Golden Benchmark remained 100% frozen:
- Zero golden records were used for model fitting, prompt tuning, threshold selection, or index construction.
- Target responses ($S_k$) were strictly shielded from candidate retrieval pools.
- The golden benchmark was executed strictly **once** at the conclusion of pipeline freezing.

---

## 4. Baseline Hierarchy Definitions

We evaluate 8 distinct baselines to isolate the source of performance gains:
- **Baseline 0 (Trivial Fallback)**: Fixed generic support message with majority class prior.
- **Baseline 1 (Lexical Rule Matcher)**: Pure keyword pattern matching with template response.
- **Baseline 2 (Retrieval-Only Top-1)**: Raw unedited top-1 historical agent tweet.
- **Baseline 3 (Qwen Zero-Shot)**: Generative response with prompt instructions but **zero retrieved evidence**.
- **Baseline 4 (Qwen + BM25)**: Evidence-grounded generation using top-3 BM25 sparse matches.
- **Baseline 5 (Qwen + Dense)**: Evidence-grounded generation using top-3 dense vector matches.
- **Baseline 6 (Qwen + Hybrid)**: Evidence-grounded generation using Reciprocal Rank Fusion (RRF $k=60$).
- **Baseline 7 (Qwen + Hybrid + Diversification)**: Evidence-grounded generation using non-redundant candidates.
- **Full SupportAgent**: Hybrid + Diversification + Safety Pre-Check Gate + 4-Tier Escalation Policy + Guardrails.

---

## 5. Classification Results

Evaluated on the 200 frozen Golden Benchmark examples across 11 fine-grained classes (`taxonomy_v1`):

| Model Baseline | Accuracy | Macro F1 | Weighted F1 | 95% Bootstrap CI (Accuracy) |
| :--- | :---: | :---: | :---: | :---: |
| **Majority Class Prior** | 22.00% | 0.0328 | 0.0793 | [16.50%, 28.00%] |
| **Semantic Taxonomy Matcher** | 48.50% | 0.4620 | 0.4780 | [41.50%, 55.50%] |
| **TF-IDF + Logistic Regression** | 58.50% | 0.5720 | 0.5810 | [51.50%, 65.50%] |
| **Lexical Matcher + Pre-Check** | **62.00%** | **0.6130** | **0.6192** | **[55.50%, 68.51%]** |

---

## 6. Retrieval Results (Causal Train Pool, 10,000 Candidates)

| Retrieval Architecture | Recall@1 | Recall@3 | Recall@5 | Recall@10 | MRR | Unique Resp. % |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **BM25 Sparse** | 61.0% | 76.5% | 82.5% | 88.0% | 0.6940 | 78.2% |
| **Dense Semantic (64-dim)** | 69.5% | 83.5% | 89.0% | 92.5% | 0.7480 | 44.2% |
| **Hybrid Fusion (RRF $k=60$)** | **74.0%** | **89.0%** | **94.0%** | **96.5%** | **0.8120** | 48.6% |
| **Hybrid + Diversifier** | **74.0%** | **89.0%** | **94.0%** | **96.5%** | **0.8120** | **92.4%** |

*Retrieval Hit Definition*: Causal candidate ($t_{\text{cand}} < t_{\text{query}}$) achieving $\text{score} > 0.05$ with matching diagnostic symptom tokens under programmatic proxy evaluation.

---

## 7. End-to-End Response Quality Results (Golden Set $N=200$)

All systems evaluated across the 6 core operational dimensions (0 to 3 scale):

| System Architecture | Intent Acc | Helpfulness | Relevance | Groundedness | Safety | Escalation | Safety Pass % |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Baseline 0 (Trivial)** | 22.0% | 2.00 | 3.00 | 1.00 | 3.00 | 2.87 | 100.0% |
| **Baseline 1 (Lexical)** | 62.0% | 2.00 | 3.00 | 1.00 | 3.00 | 2.87 | 100.0% |
| **Baseline 2 (Retrieval-Only)** | 62.0% | 2.00 | 3.00 | 3.00 | 1.00 | 2.87 | **0.0%** |
| **Baseline 3 (Zero-Shot Qwen)** | 62.0% | 2.00 | 3.00 | 1.00 | 3.00 | 2.87 | 100.0% |
| **Baseline 4 (Qwen + BM25)** | 62.0% | 2.00 | 3.00 | 1.00 | 3.00 | 2.87 | 100.0% |
| **Baseline 5 (Qwen + Dense)** | 62.0% | 2.08 | 3.00 | 2.79 | 3.00 | 2.87 | 100.0% |
| **Baseline 6 (Qwen + Hybrid)** | 62.0% | 2.08 | 3.00 | 2.79 | 3.00 | 2.87 | 100.0% |
| **Baseline 7 (Qwen + Diversified)**| 62.0% | 2.08 | 3.00 | 2.79 | 3.00 | 2.87 | 100.0% |
| **Full SupportAgent** | **62.0%** | **1.99** | **2.56** | **2.81** | **3.00** | **2.83** | **100.0%** |

---

## 8. End-to-End Bottleneck & Tradeoff Analysis (No "Full System Superiority" Claim)

A critical comparison of the baseline hierarchy and paired statistical analysis ($B=10,000$, seed=42) reveals:
- **Retrieval-Augmented Baselines (Baselines 5–7: Qwen + Dense / Hybrid / Diversified)** achieve nominal Helpfulness of **2.08**, Relevance of **3.00**, and Groundedness of **2.79 / 3.0**.
- **The Full SupportAgent** achieves Helpfulness of **1.99**, Relevance of **2.56**, and Groundedness of **2.81 / 3.0**.

### Paired Statistical Comparison Results (N=200 Golden Examples)
Formula: $\Delta = \text{Full System} - \text{Baseline}$

| Comparison Pair | Metric | Mean Diff ($\Delta$) | Median Diff | 95% Paired Bootstrap CI | Permutation $p$-value | Statistically Significant? |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **Full vs Qwen + Dense** | Helpfulness | -0.095 | 0.000 | [-0.170, -0.020] | $p = 0.0206$ | Yes (Slight Drop due to Redirection) |
| | Relevance | -0.440 | 0.000 | [-0.550, -0.335] | $p = 0.0000$ | Yes (Significant Drop due to Redirection) |
| | Groundedness | +0.015 | 0.000 | [-0.035, +0.065] | $p = 0.6954$ | No (CI spans 0) |
| **Full vs Qwen + Hybrid** | Helpfulness | -0.095 | 0.000 | [-0.170, -0.020] | $p = 0.0206$ | Yes (Slight Drop due to Redirection) |
| | Relevance | -0.440 | 0.000 | [-0.550, -0.335] | $p = 0.0000$ | Yes (Significant Drop due to Redirection) |
| | Groundedness | +0.015 | 0.000 | [-0.035, +0.065] | $p = 0.6954$ | No (CI spans 0) |
| **Full vs Qwen + Diversified** | Helpfulness | -0.095 | 0.000 | [-0.170, -0.020] | $p = 0.0206$ | Yes (Slight Drop due to Redirection) |
| | Relevance | -0.440 | 0.000 | [-0.550, -0.335] | $p = 0.0000$ | Yes (Significant Drop due to Redirection) |
| | Groundedness | +0.015 | 0.000 | [-0.035, +0.065] | $p = 0.6954$ | No (CI spans 0) |

*Statistical Conclusion*: The Full System does **not** demonstrate categorical superiority. The observed difference in groundedness was small (+0.015) and not sufficient to establish superiority on this benchmark ($p = 0.6954$, 95% CI spans 0). The drops in helpfulness (-0.095) and relevance (-0.440) reflect an active safety and privacy redirection tradeoff.

### Why the Full System Scores Lower on Relevance
The Full SupportAgent does **not** demonstrate overall superiority in raw helpfulness or relevance on the frozen benchmark. This difference is driven by an **intentional safety and boundary tradeoff**:
1. **Active Escalation & Privacy Routing**: The Full System routes 18.5% of queries to High-Risk Escalation, 8.0% to Private DM Boundaries, and 5.0% to Clarification (31.5% total redirection rate). When a query involves private credentials (IMEI, Apple ID) or physical hazards (swollen battery), the Full System intentionally refuses to provide public self-serve troubleshooting steps and emits a private channel redirect.
2. **Judge Rubric Penalty on Redirection**: The automated judge scores a clarification request (*"Could you clarify your device model and iOS version?"*) or escalation redirect lower on direct actionability/relevance than a baseline system that blindly provides generic technical advice.
3. **Statistical Equivalence on Groundedness**: The observed difference between Baseline 7 (2.795) and Full System (2.810) was small (+0.015) and not sufficient to establish superiority on this benchmark ($p = 0.6954$).


---

## 9. Grounding Metric Hierarchy & Threshold Provenance

### Grounding Metric Hierarchy
To maintain strict evaluation integrity, we establish the following explicit metric hierarchy:

1. **PRIMARY OBJECTIVE PROXY**: Programmatic Evidence Overlap = **88.00%**
   - Percentage of non-escalated queries where generated response contains $\ge 35\%$ diagnostic token/entity overlap with retrieved evidence.
2. **AUXILIARY**: LLM-Judge Groundedness = **2.81 / 3.0**
   - Continuous 0–3 score assessing claim support and hallucination absence via automated judge.
3. **HUMAN VALIDATION**: Human Grounding Validation = **2.85 / 3.0** ($N=50$)
   - Manual verification of claim support against retrieved candidates by dual independent human raters.

### Grounding Threshold Provenance Audit
- **Provenance**: The $\ge 35\%$ evidence-overlap threshold was **selected using a separate development/calibration set** ($N=10,664$) during Phase 4 candidate filtering prior to running the final Golden evaluation.
- **Validation Status**: The 88.00% metric is explicitly designated as a **heuristic proxy** and was not independently validated as exact ground truth against the Golden benchmark. The 88.00% figure is never presented as absolute ground-truth grounding.

---

## 10. Human Evaluation & LLM-Judge Calibration

- **Human Dual-Annotator Agreement ($N=30$, Non-Golden Dev Sample)**:
  - Raw Agreement: **`83.33%`**
  - Cohen's Kappa: **`0.7115`** (Substantial inter-annotator agreement).
- **LLM Judge vs. Human Calibration ($N=50$, Non-Golden Dev Sample)**:
  - Exact Agreement: **`22.00%`** (discrete step threshold sensitivity).
  - Pearson Correlation: **`0.3727`**
  - Mean Absolute Error (MAE): **`0.820`**
- **Methodological Designation**: Because calibration against human judgments showed weak exact agreement (22%), Pearson $r = 0.3727$, and MAE = 0.820, the LLM Judge is formally designated as an **auxiliary LLM-judge estimate with limited human agreement**. Human evaluation remains the primary validation reference and is not replaced by the LLM judge.
- **Judge Bias Audit**: Evaluated for length/verbosity and citation bias. Result: **`PASS`** (concise grounded responses correctly preferred over verbose unsupported answers).

---

## 11. Safety Evaluation

- **Denominator**: 200 Golden examples audited across 12 prohibited risk categories.
- **Safety Pass Rate**: **200/200 examples passed the predefined safety rubric; this does not establish universal or real-world safety.**
- **Statistical Bound**: 100.00% observed pass rate (95% Wilson Score CI: `[98.12%, 100.00%]`).
- **Metric Scope**: Evaluates combined policy compliance, absence of unsafe claims, and correct escalation routing.
- **Retrieval-Only Safety Interpretation**: Baseline 2 (Retrieval-Only) scored **0.0% Safety Pass** because **unfiltered historical-response replay violates the current response safety rubric** (exposing unmasked raw shortened `t.co` URLs and customer handles). This indicates that unfiltered historical-response replay violates the current response safety rubric, not that historical retrieval is inherently unsafe.

---

## 12. Escalation Evaluation ($N=200$)

- `PUBLIC_TROUBLESHOOTING`: **68.5%** (137 / 200)
- `HIGH_RISK_ESCALATE`: **18.5%** (37 / 200)
- `PRIVATE_SUPPORT_REQUIRED`: **8.0%** (16 / 200)
- `INSUFFICIENT_INFORMATION`: **5.0%** (10 / 200)
- **High-Risk Escalation Recall**: **`100.0%`** on hazardous hardware, fire/smoke, and credential theft vectors.

---

## 13. Out-of-Domain (OOD) Evaluation

- **Test Cohort ($N=4$)**: Windows BSODs, Linux Kernel Panics, Samsung Galaxy S8 Hardware, Banking Queries.
- **OOD Rejection Result**: **4/4 predefined OOD scenarios passed.**
- *Methodological Limitation*: Stating that 4/4 predefined OOD scenarios passed is evidence of correct behavior on those specific test prompts, and is **not statistical proof of general OOD robustness**.

---

## 14. Subgroup & Slice Analysis

| Subgroup Slice | Sample Count | Intent Accuracy | Groundedness Rate | Safety Rate |
| :--- | :---: | :---: | :---: | :---: |
| **Short Queries ($\le 5$ words)** | 7 | 14.29% | 85.71% | 100.0% |
| **Long Queries ($> 5$ words)** | 193 | 63.73% | 86.53% | 100.0% |
| **Single-Turn Context** | 125 | 72.80% | 88.00% | 100.0% |
| **Multi-Turn Context** | 75 | 44.00% | 84.00% | 100.0% |
| **High-Risk Queries** | 69 | 65.22% | 86.96% | 100.0% |
| **Multi-Intent Queries** | 97 | 61.86% | 85.57% | 100.0% |

---

## 15. Component Ablations Summary

1. **No Causal Filter**: Artificially inflates Recall@3 by +4.2% (93.2%) through future lookahead leakage.
2. **Dense Only**: Recall@3 drops by -5.5% (83.5%) due to missing exact error codes.
3. **BM25 Only**: Recall@3 drops by -12.5% (76.5%) due to lexical synonym misses.
4. **Predicted-Intent Filter**: Recall@3 drops by **-10.6%** (89.0% $\to$ 78.4%) due to cascading classifier errors.
5. **No Evidence Generation**: Groundedness drops from 2.81 down to 1.00 / 3.0.
6. **Escalation Disabled**: Safety violations surge to 26.5% on hazardous queries.

---

## 16. Comprehensive Failure Attribution (88 Cases in `artifacts/evaluation/phase5_failures.jsonl`)

- **Attribution Methodology**: Each non-perfect example receives one mutually exclusive primary failure attribution; secondary contributing factors may be recorded separately.
- **Categorical Breakdown ($N=88$ non-perfect cases)**:
  - **E1 (Single-Intent Misclassification — 39 cases, 44.3%)**: Primary confusion between `software_update` and related subsystem classes on single-symptom queries.
  - **E8 (Multi-Intent Failure — 37 cases, 42.0%)**: Queries mentioning multiple defects (e.g. OS update + battery drain) where the secondary symptom was misprioritized.
  - **E5 (Grounding Flaw — 12 cases, 13.6%)**: Minor diagnostic step omissions on brief follow-up queries.
  - **E6 (Safety Failure — 0 cases, 0.0%)**: Zero prohibited safety violations occurred.
  - **Total**: Exactly 88 cases ($39 + 37 + 12 + 0 = 88$).

---

## 17. Statistical Uncertainty Summary (95% Confidence Intervals)

| Metric | Point Estimate | 95% Confidence Interval | Method |
| :--- | :---: | :---: | :--- |
| **Golden Intent Accuracy** | 62.00% | **[55.00%, 69.00%]** | Empirical Bootstrap ($B=10000$) |
| **Full System Groundedness** | 2.81 / 3.0 | **[2.74, 2.88]** | Empirical Bootstrap ($B=10000$) |
| **Safety Pass Rate** | 100.00% | **[98.12%, 100.00%]** | Wilson Score Interval |
| **Helpfulness Score** | 1.99 / 3.0 | **[1.93, 2.05]** | Empirical Bootstrap ($B=10000$) |

---

## 18. What the Benchmark Actually Proves

- **Evidence Grounding Utility**: Retrieved historical resolutions substantially improve grounding compared with zero-shot generation (1.00 to 2.81).
- **Hybrid Retrieval Superiority**: Combining BM25 with dense semantic representations achieves higher retrieval recall (89.0%) than individual retrievers.
- **Intent Conditioning Degradation**: Conditioning retrieval candidate pools on statistical classifier predictions degrades recall (-10.6%).
- **Safety Policy Enforcement**: Hard rule pre-checks reliably trap hazardous hardware and credential requests before generation.

---

## 19. What the Benchmark Does NOT Prove

- **Current Apple Support Accuracy**: Primary benchmark is locked to Q4 2017 (iOS 11) and does not reflect modern Apple policies.
- **Universal Jailbreak Immunity**: Passing 15 handcrafted adversarial scenarios does not guarantee mathematical robustness against novel automated prompt attacks.
- **Human Resolution Equivalence**: Historical DM redirections represent private security boundaries, not proof that the customer's problem was permanently resolved.
- **Superiority Over Simpler Baselines**: The full safety and escalation pipeline does not demonstrate superior overall helpfulness or relevance on the benchmark due to necessary escalation tradeoffs.

---

## 20. "What is Misleading About the Headline Number?"

1. **Groundedness Score (2.81 / 3.0)**: Measures procedural overlap with historical 2017 tweets, not real-world customer problem resolution.
2. **Safety Pass Rate (100.00%)**: Measures compliance with 12 predefined prohibited risk patterns; novel adversarial prompts could bypass static rules.
3. **Retrieval Recall@3 (89.0%)**: Measures candidate retrieval matching symptom keywords, not verified resolution success.
4. **Intent Accuracy (62.00%)**: Evaluated on an oversampled stratified benchmark; natural head-class distribution accuracy is higher (~88%) but masks rare failure modes.

---

## 21. Final Evaluation Summary & Nuanced Finding

Historical retrieval substantially improves evidence alignment, while the full safety and escalation pipeline does not yet demonstrate superior overall helpfulness or relevance over simpler RAG configurations on the frozen benchmark. The Full System achieves strong observed safety performance and slightly higher observed grounding, but the small grounding difference requires paired statistical analysis and should not be presented as categorical superiority. This unresolved end-to-end quality tradeoff motivates targeted failure analysis rather than metric optimization.

