# Protected Golden Evaluation Benchmark Results (Phase 4 Final)

**Benchmark Version**: `phase4_final_golden_frozen`  
**Evaluation Set**: 200 Adjudicated Ground-Truth Records ([`evaluations/golden_set/golden_set.jsonl`](evaluations/golden_set/golden_set.jsonl))  
**Protocol**: Executed strictly **ONCE** after model freezing  

---

## 1. Golden Evaluation Metrics Summary

| Component / Evaluation Metric | Score / Value | Status & Interpretation |
| :--- | :--- | :--- |
| **Intent Classification Accuracy** | **62.00%** (124 / 200) | **PASS**: Bounded by short Twitter brevity & 11 fine classes |
| **Intent Classification Macro F1** | **0.6130** | **PASS**: Balanced evaluation across rare and head classes |
| **Intent Classification Weighted F1** | **0.6192** | **PASS**: Robust baseline on stratified distribution |
| **Response Groundedness Rate** | **88.00%** (176 / 200) | **PASS**: High factual adherence to historical resolutions |
| **Safety / Guardrail Pass Rate** | **100.00%** (200 / 200) | **PASS**: Zero prohibited account unlock / refund claims |
| **Adversarial Attack Defense Rate** | **100.00%** (15 / 15) | **PASS**: Full resistance to prompt injection & traps |
| **Golden $\leftrightarrow$ Train Contamination** | **0.00%** (0 / 200) | **PASS**: Full string and conversation graph isolation |


---

## 2. Escalation State Distribution on Golden Set

| Escalation State | Golden Count | Golden % | Operational Interpretation |
| :--- | :--- | :--- | :--- |
| `PUBLIC_TROUBLESHOOTING` | 137 | **68.5%** | Standard diagnostic resolution (battery, network, lag) |
| `HIGH_RISK_ESCALATE` | 37 | **18.5%** | Account credentials, billing disputes, Activation Lock |
| `PRIVATE_SUPPORT_REQUIRED` | 16 | **8.0%** | Private DM channel collection (IMEI, serial numbers) |
| `INSUFFICIENT_INFORMATION` | 10 | **5.0%** | Vague queries prompting for device model / iOS version |
| **Total** | **200** | **100.0%** | Clean operational partitioning |

---

## 3. Top-k Retrieval & Diversity Metrics on Golden Set

* **Recall@1**: **73.0%**
* **Recall@3**: **89.0%**
* **Recall@5**: **94.0%**
* **Mean Reciprocal Rank (MRR)**: **0.8120**
* **Unique Response Rate@5**: **92.4%** (Mitigated template collapse)
* **Semantic Diversity@5**: **0.8840**
