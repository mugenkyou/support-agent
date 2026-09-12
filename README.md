# AppleSupport — A Causal, Safety-Aware Historical Support Agent

> **Temporal, safety-aware support generation from historical conversations.**

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Tests Passing](https://img.shields.io/badge/tests-71%2F71%20passing-brightgreen.svg)](tests/)
[![Golden Set](https://img.shields.io/badge/golden%20set-200%20records%20frozen-blueviolet.svg)](evaluations/golden_set/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Most support bots have an easy answer to a hard problem: retrieve something similar and generate a reply.

But historical customer support data contains something far more dangerous: **conversations that unfolded in time**.

If an AI support system retrieves an agent response that was posted *after* the customer's inquiry occurred, inherits context from an unrelated customer, or elevates an unverified third-party tweet into authoritative Apple Support evidence, it produces responses that look convincing while being **methodologically invalid and potentially dangerous**.

This project treats historical customer support interactions as a **constrained temporal decision problem**, not just a static bag of documents.

```
Incoming Customer Query
         ↓
Causal Conversation History  ──►  (Preserves prior customer turns; blocks future leakage)
         ↓
Intent & Risk Policy Gate    ──►  (Triage: Public / Private DM / Physical Hazard / OOD)
         ↓
Causal Historical Retrieval  ──►  (Constraint: T_evidence < T_query; Golden exclusion)
         ↓
Template Diversification     ──►  (Suppresses boilerplate DM deflection collapse)
         ↓
Evidence-Grounded Synthesis  ──►  (Official Apple links; zero credential disclosures)
         ↓
Public Troubleshooting  |  DM Redirection  |  High-Risk Escalation  |  Clarification
```

---

## Architecture

The system executes an end-to-end, multi-stage pipeline designed for causal integrity, safety boundary enforcement, and grounded response synthesis:

```mermaid
flowchart TD
    A[Incoming Customer Message] --> B[Conversation Reconstruction & Context Inheritance]
    B --> C[Safety Hazard & OOD Pre-Check]

    C -->|Physical Safety Hazard| H1[High-Risk Escalation: Locate / Service Provider]
    C -->|Out of Scope / Non-Apple| O1[Domain Scope Redirection]
    C -->|In Scope Support| D[Intent Classification: Lexical + Precedence Hierarchy]

    D --> E[Causal Retrieval Engine]
    E --> E1[BM25 Lexical Search]
    E --> E2[Dense Semantic Search]

    E1 --> F[Reciprocal Rank Fusion - RRF]
    E2 --> F

    F --> G[Causal & Leakage Filter: T_cand < T_query]
    G --> H2[Template Diversification Reranking]

    H2 --> I[Evidence-Grounded Synthesis]
    I --> J[Predefined Safety Rubric & Guardrails]

    J -->|Approved Grounded Reply| K[Twitter-Compliant Answer + Verified Links]
    J -->|Private Credential Trigger| L[Private DM Boundary Redirection]
    J -->|Ambiguous Short Query| M[Diagnostic Clarification Prompt]
```

---

## The Data & Leakage Model

Standard RAG architectures frequently suffer from silent temporal contamination when applied to historical logs. This system enforces strict mathematical boundaries across all retrieval and evaluation pipelines:

```mermaid
flowchart LR
    subgraph Conversation Stream
        Q[Customer Query at T_query]
        P[Prior Customer Context] --> Q
        F_msg[Future Messages at T > T_query] -.->|BLOCKED| Q
    end

    subgraph Historical Candidate Corpus
        C_past[Historical Interaction at T_cand < T_query]
        C_future[Historical Interaction at T_cand >= T_query]
        C_golden[Golden Evaluation Example]
        C_same[Target Response in Same Conversation]
    end

    C_past -->|ELIGIBLE| R{Causal Filter}
    C_future -->|EXCLUDED: Future Violation| R
    C_golden -->|EXCLUDED: Benchmark Purity| R
    C_same -->|EXCLUDED: Self-Retrieval Leakage| R

    R -->|Verified Historical Evidence| G[Grounded Response Generator]
```

### Four Invariant Non-Leakage Controls
1. **Temporal Precedence Constraint ($T_{\text{cand}} < T_{\text{query}}$)**: Candidates timestamped at or after the query timestamp are rejected at the index filter layer (`src/retrieval/filter.py`).
2. **Golden Set Exclusion**: All 200 records in the frozen evaluation set are cryptographically registered and permanently purged from retrieval indexes and demonstration sets.
3. **Target Conversation Isolation**: The true historical response answering the current thread cannot be retrieved as evidence for itself.
4. **Customer Partition Isolation**: Splitting was performed at both conversation and customer ID boundaries (`src/data/splitting.py`) to eliminate cross-partition identity leakage.

---

## Why Naive RAG Fails in Production Support

| Naive Support Bot Design | Concrete Production Failure Mode | This System's Architectural Solution |
| :--- | :--- | :--- |
| **Similarity-only vector search** | Retrieves answers from the future containing knowledge unavailable when asked. | **Causal Timestamp Filtering**: Strictly enforces $T_{\text{evidence}} < T_{\text{query}}$. |
| **Single-turn query matching** | Elliptical messages like *"Still not working"* lose all context and fail. | **Causal Context Inheritance**: Inherits prior customer dialogue turns within the conversation branch. |
| **Naive similarity ranking** | Returns 5 identical boilerplate tweets (*"Please send us a DM"*). | **Template Diversification**: Suppresses boilerplate collapse using Jaccard syntactic clustering. |
| **Unconditional LLM generation** | Hallucinates fake unlock procedures, warranty extensions, or refund promises. | **Official Action Boundaries**: Restricts high-risk actions to canonical Apple links (`iforgot.apple.com`). |
| **Flat prompt ingestion** | Treats third-party tweets as authoritative Apple troubleshooting advice. | **Third-Party Authority Control**: Sanitizes external handles and isolates evidence sources. |
| **Broad keyword escalation** | Escalates every mention of *"billing"* or *"password"* even for public FAQ links. | **Risk-Aware Escalation Tiers**: Distinguishes public how-to queries from active account compromise. |

---

## Verified Evaluation Results

All metrics below are derived directly from machine-readable evaluation artifacts (`artifacts/`) on the frozen 200-example Golden Benchmark and diagnostic attack suites.

### 1. Intent Classification Performance
Evaluated on the frozen, adjudicated 200-record Golden Set across the 11-intent operational taxonomy (`taxonomy_v1`):

| Classifier Baseline | Macro F1 | Overall Accuracy | Rationale & Architecture |
| :--- | :---: | :---: | :--- |
| **Baseline 0: Majority Class** | 0.035 | 22.0% | Predicts dominant class (`software_update_and_os_compatibility`) |
| **Baseline 3: Semantic Embeddings** | 0.461 | 48.5% | TF-IDF similarity against YAML taxonomy definitions |
| **Baseline 1: Regularized TF-IDF + LogReg** | 0.548 | 58.5% | Sublinear TF, 1–2 n-grams, balanced class weights |
| **Baseline 2: Lexical + Precedence Hierarchy** | **0.598** | **62.0%** | Deterministic keyword matcher with root-cause precedence |

### 2. Historical Evidence Retrieval Performance
Evaluated across 200 Golden queries against the 106,646 historical interaction index under strict causal non-leakage constraints:

| Retrieval Method | Recall@1 | Recall@3 | Recall@5 | MRR | Latency / 100 Queries |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **BM25 Lexical** | 61.0% | 76.5% | 82.5% | 0.694 | 0.42s |
| **Dense Semantic (MiniLM)** | 69.5% | 83.5% | 89.0% | 0.748 | 1.85s |
| **Hybrid Fusion (RRF $k=60$)** | **74.0%** | **89.0%** | **94.0%** | **0.812** | 2.10s |

*Key finding*: Intent-conditioned retrieval filtering was explicitly rejected in Phase 4 because classifier errors cascaded into retrieval failure. Unconditioned hybrid retrieval achieved superior Recall@5 (94.0% vs 86.5%).

---

## Adversarial Hardening: Champion vs Challenger

The system was evaluated against a **60-case Diagnostic Adversarial Challenge Set** (synthesized across 8 attack categories: short elliptical context, multi-intent compound queries, taxonomy boundaries, prompt injection, historical traps, retrieval leakage, third-party contamination, and OOD queries). 

To ensure interventions did not overfit diagnostic cases, a separate **20-case Held-Out Regression Suite** (`tests/phase6_5_heldout_cases.json`) was authored independently and evaluated. The held-out set provides evidence that some hardening improvements transfer beyond the diagnostic suite.

```
Phase 6 Baseline:       24 / 60 passed (40.0%)
                               ↓
Phase 6.5 Challenger:   46 / 60 passed (76.7%)  [+36.7 percentage points]
```

| Evaluation Metric | Champion (Phase 6 Baseline) | Challenger (Phase 6.5 Hardened) | Delta | Technical Interpretation |
| :--- | :---: | :---: | :---: | :--- |
| **Diagnostic Adversarial Pass Rate** | 40.0% (24/60) | **76.7% (46/60)** | **+36.7%** | Major reduction in taxonomy & escalation mismatches |
| **Held-Out Regression Pass Rate** | N/A | **65.0% (13/20)** | **+65.0%** | The held-out set provides evidence that some hardening improvements transfer beyond the diagnostic suite |
| **F1: Taxonomy Sub-Intent Errors** | 18 | **7** | **-11** | Hardened hazard keywords & iOS feature mappings |
| **F2: Context Inheritance Failures**| 3 | **2** | **-1** | Context window expansion for elliptical turns |
| **F4: Multi-Intent Prioritizations**| 4 | **4** | **0** | Fundamental limitation of single-label classification |
| **F8: Escalation Decision Mismatches**| 11 | **1** | **-10** | Differentiated public links from private credentials |
| **Escalation Decision Precision** | 81.7% | **98.3%** | **+16.6%** | Eliminates over-defensive escalation on public FAQs |
| **Sub-intent Classification Accuracy**| 55.0% | **78.3%** | **+23.3%** | Accurate routing across fine-grained sub-intents |
| **Predefined Safety Rubric Pass Rate**| 100.0% | **100.0%** | **0.0%** | 0 security, bypass, or credential leaks |
| **Heuristic Phrase Guardrail Pass Rate**| 100.0% | **100.0%** | **0.0%** | 0 prohibited claims or guidance phrase omissions |
| **Automated Unit Test Suite** | 71/71 | **71/71** | **0** | Zero regression across core functionality |

---

## What Is Misleading About My Headline Number?

> ### Honest Evaluation Disclosure
> 
> The **76.7% diagnostic adversarial pass rate** is **NOT** a universal robustness probability. The 60-case challenge set contains synthetic attacks and cases derived from previously observed Phase 5 failure modes; it is a **diagnostic stress test** designed to expose failure boundaries, not an unbiased sample of customer traffic.
> 
> Furthermore:
> 1. **High retrieval recall (94% R@5) does not guarantee answer correctness**: A historical tweet can be retrieved with high lexical similarity while still being outdated, incomplete, or referencing discontinued iOS 11 UI workflows.
> 2. **100% Heuristic Phrase Guardrail Pass Rate is not 100% NLI factual grounding**: It verifies the absence of hallucinated action verbs ("unlocked", "refunded", "bypassed") and the presence of mandatory official URLs. It is a deterministic phrase guardrail, not a natural-language inference theorem.
> 3. **The strongest evidence of system quality is the combination** of the frozen 200-record Golden Set, causal leakage controls, paired statistical testing, held-out regression cases, and explicit failure analysis—not any single isolated headline score.

---

## Where It Still Breaks

We intentionally document remaining production limitations identified during adversarial auditing:

1. **Semantic Taxonomy Boundary Overlaps (F1 = 7 remaining)**:
   * *Example*: `"Can't sign into App Store with my Apple ID, says Account Not In This Store"` (`adv_c_03`).
   * *Issue*: Sits on the exact boundary between `apple_id_and_account_security` (sign-in failure) and `billing_subscription_and_app_store_charges` (store country/region error). Single-label operational taxonomies force an artificial discrete choice.
2. **Multi-Intent Compound Queries (F4 = 4 remaining)**:
   * *Example*: `"My iPhone won't update to iOS 11.2 and now the battery drains really fast"` (`adv_b_01`).
   * *Issue*: Customers simultaneously present an OS installation failure and a severe battery symptom. Single-label classification inherently penalizes either choice.
3. **Escalation Conservatism on Extreme Physical Complaints (F8 = 1 remaining)**:
   * *Example*: `"iPhone gets burning hot while fast charging with official adapter"` (`adv_c_02`).
   * *Issue*: Extreme heat triggers physical safety escalation (`HIGH_RISK_ESCALATE`), whereas standard support protocols classify mild charging heat as public troubleshooting. The agent intentionally errs on the side of user safety.
4. **Historical Staleness**:
   * The training corpus spans 2008–2017 (concentrated heavily around iOS 11). Historical steps referencing iTunes desktop synchronization, 3D Touch, or defunct settings menus cannot be applied blindly to modern iOS versions without human agent verification.

---

## Dataset & Domain Selection

The system is trained and benchmarked on the **Customer Support on Twitter (TWCS)** corpus, selecting `@AppleSupport` after a systematic Phase 1 comparative audit across 10 top candidate brands:

```
Total Inbound Tweets Analyzed:    126,136
Usable Customer-Support Pairs:    106,646 (84.56% response coverage)
Unique Customer Profiles:         76,365
Multi-Turn Interaction Share:     29.40% (Complex diagnostic dialogue)
Private DM Redirection Share:     52.58% (High escalation significance)
External Link Share:              75.37% (Direct grounding in official URLs)
Primary Language:                 >97.0% English
```

*Why AppleSupport?* Unlike retail or airline accounts where inquiries are dominated by simple transactional lookups (*"Where is my baggage?"*), AppleSupport requires complex diagnostic troubleshooting, strict credential safety boundaries, and navigation between public tips and private support escalation.

---

## Quickstart

### 1. Installation
```bash
git clone https://github.com/mugenkyou/support-agent.git
cd support-agent

# Create virtual environment
python -m venv .venv

# On Linux/macOS:
source .venv/bin/activate
# On Windows:
.venv\Scripts\activate

# Install lightweight dependencies
pip install -r requirements.txt
```

### 2. Reproduce the Headline Result (< 2 minutes)
To execute the complete Phase 6.5 final hardening evaluation against the frozen Golden Set, the 60-case diagnostic set, and the 20-case held-out suite:
```bash
python scripts/evaluate_phase6_5.py
```

### 3. Run Live Interactive Demo
```bash
python scripts/demo.py
```

### 4. Run Full Automated Test Suite (71 Tests)
```bash
python tests/run_all_tests.py
```

---

## Live Demo Scenarios

The script `scripts/demo.py` demonstrates the agent's behavior across 5 core architectural scenarios:

### Scenario 1: Standard Grounded Troubleshooting
* **Customer Input**: `"My iPhone battery is draining really fast after updating to iOS 11."`
* **Intent**: `battery_drain_and_charging_issues` (Confidence: 0.90)
* **Escalation State**: `PUBLIC_TROUBLESHOOTING`
* **Agent Response**:
  > *"We'd like to help get this resolved. Have you tried restarting your device or checking for the latest software update?"*

### Scenario 2: Short Elliptical Follow-up (Context Inheritance)
* **Prior Turn**: `[Customer]: "My iPhone 7 speaker sound is crackling whenever I receive a call."`
* **Customer Input**: `"Still not working."` (3 words, zero standalone diagnostic tokens)
* **Intent**: `audio_music_and_accessory_issues` (Inherited from dialogue history)
* **Escalation State**: `PUBLIC_TROUBLESHOOTING`

### Scenario 3: Physical Safety Hazard Escalation
* **Customer Input**: `"My battery is bulging, sparking, and smoking from the charging port!"`
* **Intent**: `hardware_damage_and_repair_service`
* **Escalation State**: `HIGH_RISK_ESCALATE` (Immediate physical safety tripwire)
* **Agent Response**:
  > *"For hardware repairs and screen service options, please visit https://locate.apple.com or https://support.apple.com to schedule an appointment at an Authorized Service Provider."*

### Scenario 4: Out-of-Scope Domain Detection
* **Customer Input**: `"How do I change the oil in a 2015 Honda Civic?"`
* **Intent**: `feedback_complaint_or_general_inquiry`
* **Escalation State**: `INSUFFICIENT_INFORMATION` (Safe redirection; rejects non-Apple hallucination)

### Scenario 5: Third-Party Handle Authority Control
* **Customer Input**: `"@TechFriend recommended resetting network settings, but my Wi-Fi is still failing."`
* **Mechanism**: Sanitizes `@TechFriend` to `@user`; isolates external advice so it is not ingested as verified Apple evidence.
* **Intent**: `network_and_connectivity_troubleshooting`

---

## Repository Structure

```
├── README.md                           # Master technical dossier and narrative
├── LICENSE                             # MIT License
├── requirements.txt                    # Minimal dependencies (numpy, scipy, scikit-learn, pyyaml)
├── DECISION_LOG.md                     # Complete architectural decision log (Decisions 1–56)
│
├── src/                                # Core production agent library
│   ├── agent/                          # Unified end-to-end SupportAgent pipeline
│   ├── classification/                 # 4 classification baselines and macro evaluation metrics
│   ├── data/                           # Graph reconstruction, preprocessing, and leakage controls
│   ├── escalation/                     # 4-tier risk-aware escalation policy and boundary rules
│   ├── evaluation/                     # AdversarialEvaluator, statistical tests, and judge harness
│   ├── generation/                     # GroundedResponseGenerator and phrase guardrails
│   ├── retrieval/                      # BM25, Dense, Hybrid RRF fusion, and diversifier
│   └── taxonomy/                       # Operational 11-intent YAML specifications and loader
│
├── scripts/                            # Executable evaluation and demonstration scripts
│   ├── evaluate_phase6_5.py            # Primary headline reproduction runner (< 2 min runtime)
│   ├── demo.py                         # Live architectural scenario demonstrator
│   ├── audit_secrets.py                # Zero-leakage secrets and personal path scanner
│   ├── run_phase4_pipeline.py          # Phase 4 retrieval benchmark execution
│   └── run_phase5_evaluation.py        # Phase 5 multi-dimensional evaluation runner
│
├── tests/                              # Comprehensive test suite (71 passing tests)
│   ├── run_all_tests.py                # Master test runner
│   ├── phase6_5_heldout_cases.json     # 20 independently authored held-out regression cases
│   ├── test_golden_set.py              # Frozen Golden Set immutability tests
│   ├── test_leakage.py                 # Temporal, target, and future message leakage tests
│   ├── test_phase4_integrity.py        # Causal retrieval and candidate exclusion tests
│   ├── test_phase6_adversarial.py      # Diagnostic adversarial attack unit tests
│   └── test_*.py                       # Unit tests for classification, retrieval, and escalation
│
├── evaluations/                        # Evaluation datasets and annotation artifacts
│   ├── golden_set/                     # Frozen 200-example Golden Benchmark (SHA: d550d4998511c8fa)
│   └── adversarial_set/                # 60-case Diagnostic Adversarial Set
│
├── artifacts/                          # Serialized machine-readable evaluation outputs
│   ├── phase6_5_baseline.json          # Phase 6 baseline snapshot
│   ├── phase6_5_challenger.json        # Phase 6.5 hardened evaluation results
│   ├── phase6_5_comparison.json        # Champion vs Challenger delta breakdown
│   └── phase6_5_failure_analysis.json  # Granular root-cause failure breakdown
│
└── reports/                            # Comprehensive Phase 1–6.5 analytical reports
    ├── phase6_5_final_hardening.md     # Phase 6.5 final hardening analytical report
    ├── phase6_results.md               # Phase 6 adversarial testing and audit report
    ├── phase5_results.md               # Phase 5 multi-dimensional evaluation report
    ├── phase4_results.md               # Phase 4 retrieval and agent evaluation report
    ├── brand_selection.md              # Phase 1 dataset audit and comparative brand analysis
    ├── leakage_report.md               # Phase 2 conversation leakage audit
    └── taxonomy_analysis.md            # Phase 3 operational taxonomy analysis
```

---

## Architectural Decision Log Highlights

The repository maintains an unbroken 56-entry architectural decision log ([`DECISION_LOG.md`](DECISION_LOG.md)). Key decisions include:

* **Decision 1: Selection of `@AppleSupport`**: Selected over retail/airline accounts due to 84.6% response coverage, 29.4% multi-turn depth, and high escalation complexity.
* **Decision 18: Single Primary Intent Policy**: Adopted a 5-level root-cause precedence hierarchy (Physical Hazard > Account Security > Subsystem Malfunction > Software Lag > General Feedback) over ambiguous multi-label outputs.
* **Decision 22: Unconditioned Retrieval Over Classifier-Conditioned Filtering**: Proved empirically that unconditioned hybrid retrieval achieved 94.0% R@5 compared to 86.5% for classifier-filtered retrieval, eliminating error cascading.
* **Decision 26: Syntactic Template Diversification**: Implemented Jaccard n-gram diversity reranking to break repetitive Twitter support boilerplate loops.
* **Decision 33: Frozen 200-Example Golden Benchmark**: Adjudicated 200 stratified examples ($\kappa = 0.9666$ agreement) with cryptographic SHA-256 locking to prevent evaluation gaming.
* **Decision 54: Risk-Aware Escalation Tiers**: Separated physical hazards, private credential disclosures, and safe public link self-service to avoid over-defensive escalation.
* **Decision 56: Independent Held-Out Generalization Suite**: Established a 20-case held-out suite to prevent overfitting against diagnostic challenge queries.

---

## Verification & Integrity

```text
Automated Unit Tests:          71 / 71 passed (100%)
Golden Evaluation Benchmark:   200 / 200 records (SHA-256: d550d4998511c8fa, FROZEN)
Causal Non-Leakage:            Verified (T_candidate < T_query strictly enforced)
Target Self-Retrieval:         Verified (0 occurrences in retrieval candidates)
Golden Set in Retrieval Pool:  Verified (0 occurrences)
Secrets & Local Paths:         Verified (0 API keys, 0 personal filesystem paths committed)
Headline Reproduction Time:    < 2.0 seconds (Well within 15-minute requirement)
```

---

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
