# Dataset Partitioning & Split Analysis Report

**Target Brand**: `AppleSupport`  
**Phase**: Phase 2 — Dataset Construction & Leakage Control  
**Total Canonical Examples**: 106,646  

---

## 1. Executive Summary & Split Strategy Comparison

We evaluated four distinct data partitioning strategies across the 106,646 usable `AppleSupport` interactions:
1. **Temporal Split (Primary Benchmark Strategy)**: Strict chronological separation.
2. **Conversation Split**: Graph-partitioned by `conversation_id`.
3. **Customer Split**: Clustered by `customer_id`.
4. **Random Split**: Uniform random assignment (Diagnostic baseline).

### Comparative Partitioning Matrix

| Dimension | `TemporalSplit` (Primary) | `ConversationSplit` | `CustomerSplit` | `RandomSplit` |
| :--- | :--- | :--- | :--- | :--- |
| **Train Count (%)** | 85,316 (80.0%) | 85,316 (80.0%) | 85,316 (80.0%) | 85,316 (80.0%) |
| **Dev Count (%)** | 10,664 (10.0%) | 10,664 (10.0%) | 10,664 (10.0%) | 10,664 (10.0%) |
| **Test Count (%)** | 10,666 (10.0%) | 10,666 (10.0%) | 10,666 (10.0%) | 10,666 (10.0%) |
| **Train Date Range** | 2016-03-04 $\rightarrow$ 2017-11-17 | 2016-03-04 $\rightarrow$ 2017-12-03 | 2016-03-04 $\rightarrow$ 2017-12-03 | 2016-03-04 $\rightarrow$ 2017-12-03 |
| **Dev Date Range** | 2017-11-17 $\rightarrow$ 2017-11-26 | 2016-03-04 $\rightarrow$ 2017-12-03 | 2016-03-04 $\rightarrow$ 2017-12-03 | 2016-03-04 $\rightarrow$ 2017-12-03 |
| **Test Date Range** | 2017-11-26 $\rightarrow$ 2017-12-03 | 2016-03-04 $\rightarrow$ 2017-12-03 | 2016-03-04 $\rightarrow$ 2017-12-03 | 2016-03-04 $\rightarrow$ 2017-12-03 |
| **Conversation Overlap (Train $\cap$ Test)** | 35 convs (0.04%) | **0 (0.00%)** | 0 (0.00%) | 1,482 convs (1.8%) |
| **Customer Overlap (Train $\cap$ Test)** | 909 custs (11.82%) | 1,120 custs (14.6%) | **0 (0.00%)** | 6,104 custs (79.9%) |
| **Exact Query Overlap (Train $\cap$ Test)** | 59 queries (0.56%) | 84 queries (0.79%) | 88 queries (0.83%) | 142 queries (1.33%) |
| **Temporal Leakage Prevention** | **STRICT (Zero lookahead)** | Moderate risk | Moderate risk | **SEVERE LEAKAGE** |

---

## 2. Why `TemporalSplit` Was Selected as Primary Benchmark

1. **Realistic Production Simulation**: In production, an AI support agent must resolve customer issues arising tomorrow using models and retrieval pools built from data collected up to today.
2. **Preventing Anachronistic Software Leakage**: The dataset captures the live launch and adoption curve of iOS 11 and iPhone 8/X (Sept–Nov 2017). Random and customer-level splits mix later bug fixes, point releases (e.g. iOS 11.1), and known system outages into earlier training sets.
3. **Low Natural Duplication Overlap**: Only 59 exact query texts (0.56%) and 105 normalized queries (1.00%) recur between Train and Test, proving that the temporal test set tests genuine linguistic generalization rather than memorized string recall.

---

## 3. Customer & Conversation Overlap Analysis

### 3.1 Customer Overlap in Temporal Split
- In the Temporal Split, 7,691 distinct customers submitted queries in the Test window (Nov 26 to Dec 3, 2017).
- 6,782 customers (**88.18%**) are **completely new first-time customers** never seen in Train.
- 909 customers (**11.82%**) are repeat customers who interacted with AppleSupport earlier in the year.

### 3.2 Long-Running Conversation Overlap
- Across the 10,666 Test interactions, exactly 35 conversation trees originated in Train and had late follow-up replies during the Test window.
- For retrieval and training isolation, our `RetrievalFilter` excludes any turns occurring at $t \ge T(\text{query})$, ensuring zero future conversation leakage.
