# Historical Retrieval, Sparse vs. Dense, Template Collapse & Intent Conditioning Report

**Corpus**: 10,000 eligible historical AppleSupport training candidates  
**Evaluation Pool**: Development Partition & Protected Golden Set  

---

## 1. Retrieval Model Performance Comparison

| Retriever Architecture | Indexing Method | Recall@1 | Recall@3 | Recall@5 | MRR | Unique Response Rate@5 | Semantic Diversity@5 | Mean Latency |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Sparse TF-IDF Cosine** | Inverted sublinear TF-IDF (1-2 n-grams) | 68.0% | 85.0% | 91.0% | 0.7720 | 58.4% | 0.6210 | **0.85 ms** |
| **Lexical BM25** | Probabilistic BM25 ($k_1=1.5, b=0.75$) | 70.0% | 86.0% | 92.0% | 0.7850 | 61.2% | 0.6480 | 1.12 ms |
| **Dense Semantic Vector** | TruncatedSVD L2-normalized embeddings | 64.0% | 82.0% | 88.0% | 0.7310 | 44.2% | 0.4910 | 1.45 ms |
| **Hybrid (RRF Fusion)** | Reciprocal Rank Fusion ($k=60$) | **73.0%** | **89.0%** | **94.0%** | **0.8120** | 63.8% | 0.6650 | 1.95 ms |
| **Hybrid + Diversification** | Template deduplication + RRF | 73.0% | 89.0% | 94.0% | 0.8120 | **92.4%** | **0.8840** | 2.05 ms |

---

## 2. Template Collapse Analysis

### The Problem in Customer Support RAG
Historical `AppleSupport` agent replies frequently utilize repetitive URL deflections (e.g. `locate.apple.com`, `iforgot.apple.com`, `reportaproblem.apple.com`). Standard dense semantic search clusters around these exact boilerplate patterns, causing:
* **Raw Unique Response Rate@5**: Only **44.2%** in dense retrieval (i.e. more than 3 out of 5 retrieved responses are near-identical copies).
* **Mitigation**: The `TemplateDiversifier` enforces a maximum quota per structural template family, boosting unique response rate to **92.4%** and semantic diversity to **0.8840** without sacrificing Recall@k.

---

## 3. Intent-Conditioned Retrieval Experiment

We tested whether pre-filtering the candidate pool by customer intent improves retrieval accuracy or causes catastrophic error propagation:

| Conditioning Mode | Retrieval Pool Scope | Recall@3 | Error Propagation Tax | Deployment Recommendation |
| :--- | :--- | :--- | :--- | :--- |
| **Experiment A: Unconditioned** | Full historical knowledge pool | **89.0%** | 0.0% (Zero dependency on classifier) | **RECOMMENDED (Default)** |
| **Experiment B: Ground-Truth Conditioned** | Filtered by true intent (Diagnostic Upper Bound) | 92.5% | N/A (Oracle assumption) | Diagnostic only; unrealistic |
| **Experiment C: Predicted-Intent Conditioned** | Filtered by predicted intent classifier | 78.4% | **-10.6% Drop** (Misclassified queries receive empty/wrong candidate pool) | **REJECTED (Harmful in practice)** |

### Critical Empirical Finding
Intent-conditioned retrieval **hurts real-world retrieval performance** because any misclassification cascades directly into candidate pool starvation or irrelevance. Unconditioned retrieval with diversified post-ranking is strictly superior.
