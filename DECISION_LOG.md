# Project Decision Log

This document records the foundational architectural, analytical, and problem-framing decisions made across project phases.

---

# Phase 1 Decisions (Dataset Audit & Brand Discovery)

## Decision 1: Target Brand Selection (`AppleSupport`)
- **Decision**: Select `AppleSupport` as the single target brand for the AI Support Agent task.
- **Reason**: `AppleSupport` exhibits the highest customer diversity, cleanest English monolingual corpus, richest multi-turn diagnostic workflows, and clearest objective boundaries between automatable software troubleshooting and high-risk human escalation.
- **Evidence**:
  - 106,646 usable customer $\rightarrow$ support interaction pairs.
  - 76,365 unique customers (Rank 1 across all 108 brands in dataset).
  - Customer concentration: top 10 customers represent only 0.16% of volume.
  - Low customer query duplication (2.73% normalized string duplicate rate).
  - Template repetition (23.23%) is balanced—neither overly boilerplated (like Uber at 64.23%) nor purely link-deflective.
- **Alternatives Considered**:
  - `AmazonHelp`: Rejected due to severe multilingual contamination (DE, JA, ES, FR, IT mixed without language tags) and generic order-lookup link deflections (>60%).
  - `Uber_Support`: Rejected due to high boilerplate repetition (64.23%) and narrow domain (trip fare disputes).
  - `TMobileHelp` / Telecoms: Rejected due to extreme DM deflection (>82%), making public autonomous troubleshooting unrealistic.
  - `SpotifyCares`: Viable runner-up, but smaller volume (43k vs 106k) and narrower domain scope than Apple's device/OS ecosystem.
- **Trade-off**: High link sharing (75.37%) and DM deflection (52.58%) require explicit modeling of link generation and DM handoffs as escalation actions.
- **Confidence**: **HIGH**

---

## Decision 2: Atomic Unit of Customer Support Modeling
- **Decision**: Frame the fundamental prediction unit as a **Contextualized Turn**: $(C_1, S_1, \dots, C_k) \rightarrow S_k$, rather than treating tweets as independent single-row records.
- **Reason**: Customer support conversations are multi-turn dialogue trees. In the dataset, 45.45% of conversations have 3 or more tweets, and customer messages frequently refer back to prior agent troubleshooting steps.
- **Evidence**:
  - Conversation graph audit revealed 798,197 conversation trees with mean length 3.52 tweets.
  - In `AppleSupport`, 29.40% of interactions (31,350 turns) are multi-turn follow-ups where context is required to understand user answers like "I already did that and it still doesn't work".
- **Alternatives Considered**:
  - Single-turn classification (predicting intent/response solely from $C_k$): Fails on elliptical follow-up replies.
  - Full-thread generation at once: Unrealistic for real-time live support streaming.
- **Trade-off**: Requires reconstructing and maintaining parent-child context windows during training, evaluation, and live inference.
- **Confidence**: **HIGH**

---

## Decision 3: Data Splitting Strategy (Chronological Temporal Split)
- **Decision**: Enforce a strict **time-based chronological split** (Train: earlier timestamps $\rightarrow$ Test/Validation: later timestamps) rather than random row-level or random conversation-level splitting.
- **Reason**: Random splitting causes lookahead data leakage where future support knowledge, software updates (e.g. iOS 11 features), and recurring incident threads leak into the training set.
- **Evidence**:
  - The dataset spans 2008 to late 2017. `AppleSupport` records span 2016-03-03 to 2017-12-03, with >97% concentrated in Oct-Nov 2017 around the iOS 11 release.
  - Major OS updates introduce temporal shifts in troubleshooting logic and UI settings.
  - Automated Test J confirmed zero future-parent inversions when following time ordering.
- **Alternatives Considered**:
  - Random row split: Severe leakage across turns of the same conversation.
  - Random conversation split: Prevents intra-thread leakage but allows temporal lookahead leakage across ecosystem updates.
- **Trade-off**: Model performance on later time periods reflects genuine temporal generalization challenges rather than inflated random cross-validation scores.
- **Confidence**: **HIGH**

---

## Decision 4: Framing Direct Message (DM) Redirections as Historical Private-Channel Boundaries
- **Decision**: Treat historical support replies instructing customers to "Send a DM with your serial number / Apple ID" as **Historical Private-Channel Boundaries / Information-Gathering Actions**, clearly distinguished from ground-truth operational escalation.
- **Reason**: Public customer support channels have strict privacy boundaries. Asking for a DM was Apple's historical protocol when sensitive private identifiers or account credentials were required.
- **Evidence**:
  - 52.58% of `AppleSupport` tweets request a DM when hardware serial numbers, IMEI, or Apple ID account verifications are necessary.
  - Real-world AI agents must recognize when to stop public troubleshooting and escalate to a secure, private communication channel.
- **Alternatives Considered**:
  - Filtering out all DM-request tweets: Destroys >52% of dataset and removes essential safety boundaries.
  - Treating historical DM as absolute proof of necessary human escalation: Conflates brand policy with technical necessity.
- **Trade-off**: The evaluation benchmark must score both direct automated troubleshooting and appropriate escalation to DM as valid correct behaviors depending on privacy/safety triggers.
- **Confidence**: **HIGH**

---

## Decision 5: Multipart Customer Tweet Aggregation & Inbound Link Disambiguation
- **Decision**: Distinguish third-party customer comments (54.67% of Inbound $\rightarrow$ Inbound links) from same-author consecutive turns (45.33%). For same-author chains, adopt $\Delta t \le 120$s with linguistic continuity checks as the candidate multipart aggregation heuristic for Phase 2.
- **Reason**: Empirical analysis revealed that more than half of Inbound $\rightarrow$ Inbound links are other customers replying to a public thread. Treating all Inbound $\rightarrow$ Inbound links as multipart was an unsupported assumption.
- **Evidence**:
  - Out of 188,447 Inbound $\rightarrow$ Inbound links in the raw dataset, exactly 85,419 (45.33%) share the same author ID, while 103,028 (54.67%) have different author IDs.
  - Among same-author links: 41.48% occur within $\le 120$s (35,434 links), 50.40% within $\le 180$s, while 32.51% occur $> 10$ minutes later (representing delayed customer nudges/updates).
- **Alternatives Considered**:
  - Blindly grouping all Inbound $\rightarrow$ Inbound links: Grouped third-party tweets and corrupts customer problem statements.
  - No grouping (treating every tweet independently): Truncates customer issues split across multiple 140-character messages.
- **Trade-off**: Requires evaluating both time-delta and textual continuity (e.g. "1/2", sentence continuation) during Phase 2 dataset construction.
- **Confidence**: **MEDIUM**

---

# Phase 2 Decisions (Conversation Reconstruction, Preprocessing & Leakage Control)

## Decision 6: Canonical Schema Definition for Modeling Examples
- **Decision**: Define every canonical interaction example as $(\mathcal{H}_k, C_k, S_k)$ with full provenance metadata (`interaction_id`, `conversation_id`, `customer_id`, `created_ts`, `context`, `customer_message_raw`, `customer_message_normalized`, `historical_response_raw`, `target_support_tweet_id`, `source_customer_tweet_ids`, `multipart_aggregated`, `latency_seconds`).
- **Reason**: Guarantees full auditability and traceability back to raw tweets in `data/raw/twcs.csv` while ensuring context and target are strictly separated.
- **Evidence**: 106,646 canonical records built with 0 missing fields and 0 schema errors in `data/processed/interactions.jsonl`.
- **Alternatives Considered**: Flattened single-string prompts (loses turn structure and token auditing).
- **Trade-off**: Slightly larger JSON record size (~150 MB dataset on disk) compensated by complete reproducibility and auditability.
- **Confidence**: **HIGH**

---

## Decision 7: Multi-Part Same-Author Aggregation Heuristic
- **Decision**: Group same-author customer tweets into a unified turn when $\Delta t \le 120$s AND (`is_linguistic_continuation` is True OR $\Delta t \le 60$s).
- **Reason**: Solves Twitter's 140-character limit problem where customers split a single sentence or error log across 2 consecutive tweets.
- **Evidence**: Identified and aggregated exactly 1,929 genuine multi-part customer query chains in `AppleSupport` without incorrectly merging separate delayed queries.
- **Alternatives Considered**:
  - Fixed 300s window without linguistic check: Merged unrelated follow-up turns.
  - No merging: Truncated 1,929 initial problem descriptions.
- **Trade-off**: Modest increase in preprocessing complexity for higher problem completeness.
- **Confidence**: **HIGH**

---

## Decision 8: Strict Third-Party Customer Comment Isolation
- **Decision**: Filter out third-party customer comments from the target customer's context path during conversation reconstruction.
- **Reason**: 54.67% of Inbound $\rightarrow$ Inbound links represent third-party customers chiming in. Injecting third-party complaints into the target customer's context corrupts the customer profile and confuses issue attribution.
- **Evidence**: Automated Test Q verified that 100% of reconstructed contexts isolate `(Author == Target Customer) OR (Author == AppleSupport)`.
- **Alternatives Considered**: Including all public thread participants in context (causes severe multi-customer confusion).
- **Trade-off**: Thread-level social banter is lost; target-level diagnostic clarity is preserved.
- **Confidence**: **HIGH**

---

## Decision 9: Causal Tie-Breaking for Identical Timestamps
- **Decision**: When $T(\text{parent}) == T(\text{child})$, the directed edge (`child.in_response_to == parent.tweet_id`) places the parent strictly before the child. Sibling ties are sorted deterministically by integer `tweet_id`.
- **Reason**: Twitter timestamps have 1-second resolution; rapid automated agent acknowledgments can share the same second as the incoming tweet.
- **Evidence**: 56 timestamp ties in the dataset graph were verified and placed in strictly causal parent $\rightarrow$ child order with zero temporal loops.
- **Alternatives Considered**: Discarding tied turns (unnecessary loss of valid data) or random tie breaking (nondeterministic).
- **Trade-off**: None. Preserves causality and 100% determinism.
- **Confidence**: **HIGH**

---

## Decision 10: Primary Benchmark Partitioning Strategy (`TemporalSplit` 80/10/10)
- **Decision**: Adopt chronological `TemporalSplit` (Train: 85,316 [80.0%] | Dev: 10,664 [10.0%] | Test: 10,666 [10.0%]) as the primary evaluation split.
- **Reason**: Accurately simulates the production reality where models trained on past data are evaluated on future customer support queries during the iOS 11 rollout surge.
- **Evidence**: Train spans 2016-03-04 to 2017-11-17; Test spans 2017-11-26 to 2017-12-03. Exact query overlap between Train and Test is minimal (59 queries, 0.56%).
- **Alternatives Considered**: Random split (rejected due to lookahead leakage); Customer split (useful as secondary generalization diagnostic).
- **Trade-off**: Small temporal distribution shift between early iOS 11.0 (Train) and iOS 11.1/11.2 (Test) must be handled by the model.
- **Confidence**: **HIGH**

---

## Decision 11: Programmatic Retrieval Leakage Exclusion Engine
- **Decision**: The RAG retrieval candidate filter (`RetrievalFilter`) must programmatically exclude: (1) query $k$ itself, (2) target support response $S_k$, (3) any candidates with $T \ge T(C_k)$, (4) same-conversation future turns, and (5) registered golden evaluation examples.
- **Reason**: Prevents RAG systems from retrieving identical or future answers during evaluation.
- **Evidence**: Automated Tests J and K verified zero self-retrieval and zero future retrieval violations across candidate pools.
- **Alternatives Considered**: Manual exclusion lists (error-prone, non-scalable).
- **Trade-off**: None. Essential requirement for evaluation integrity.
- **Confidence**: **HIGH**

---

## Decision 12: Permanent Golden Set Isolation Mechanism
- **Decision**: Establish an immutable registration registry (`golden_ids`) that automatically purges golden examples from training sets, demonstration pools, and vector retrieval indexes.
- **Reason**: Ensures that when the 150–250 golden evaluation benchmark is created in Phase 3, zero contamination of training or RAG index pools can occur.
- **Evidence**: Verified in `src/data/leakage.py` and `tests/test_leakage.py`.
- **Alternatives Considered**: Ad-hoc post-hoc filtering (high risk of accidental contamination).
- **Trade-off**: None.
- **Confidence**: **HIGH**

---

## Decision 13: Lifecycle Classification of Unreplied Customer Queries
- **Decision**: Classify all 19,490 customer inbound tweets mentioning `AppleSupport` that received no observed reply in the dataset as `NO_OBSERVED_RESPONSE` and isolate them in `exclusion_log.jsonl`.
- **Reason**: Prevents hallucinating or synthesizing ground-truth support responses while preserving the unreplied cohort for future intent/escalation distribution audits.
- **Evidence**: Complete reconciliation: 106,646 usable + 19,490 unreplied = 126,136 total inbound queries accounted for.
- **Alternatives Considered**: Dropping unreplied rows silently (unreconciled data loss).
- **Trade-off**: None. Clean separation between supervised pairs and unreplied queries.
- **Confidence**: **HIGH**

---

## Decision 14: Text Normalization Strategy
- **Decision**: Maintain both `raw_text` (original characters, casing, punctuation) and `normalized_text` (lowercased, URLs masked as `<url>`, mentions masked as `<user>`).
- **Reason**: Response generation models require natural casing and punctuation, while deduplication and retrieval benefit from masked representations.
- **Evidence**: Preserves 100% of raw text fidelity while enabling exact string and normalized duplicate auditing (2.73% normalized query duplication).
- **Alternatives Considered**: Overwriting raw text destructively (destroys data fidelity).
- **Trade-off**: Small storage overhead for dual representations.
- **Confidence**: **HIGH**

---

## Decision 15: Primary Evidence Source Locking
- **Decision**: Historical `AppleSupport` conversation interactions in `twcs.csv` are formally locked as the sole primary evidence source for the benchmark. Modern post-2017 Apple documentation is strictly prohibited from entering the primary benchmark.
- **Reason**: Mixing modern documentation (iOS 16/17/18, Apple Silicon) into a 2017 iOS 11 dataset creates anachronistic hallucinations.
- **Evidence**: Confirmed in temporal drift analysis (`reports/temporal_analysis.md`).
- **Alternatives Considered**: Allowing modern web scraping (corrupts historical baseline).
- **Trade-off**: Limits knowledge to what was publicly known up to Q4 2017.
- **Confidence**: **HIGH**

---

## Decision 16: Canonical Processed Storage Format
- **Decision**: Store processed dataset as newline-delimited JSON (`data/processed/interactions.jsonl`) with companion metadata (`interactions_metadata.json`, `splits.json`, `exclusion_log.jsonl`).
- **Reason**: Zero external C-extension dependencies (no pyarrow requirement), human-auditable, streamable in chunks, and cross-platform reproducible.
- **Evidence**: Successfully generated and tested across 106,646 interactions.
- **Alternatives Considered**: Parquet (requires third-party binary wheels); SQLite-only (less convenient for batch streaming).
- **Trade-off**: Larger file size than snappy-compressed parquet (~150 MB vs ~40 MB).
- **Confidence**: **HIGH**

---

## Decision 17: Intent Granularity & 11-Class Operational Taxonomy
- **Decision**: Adopt the 11-intent operational support taxonomy (`taxonomy_v1`), rejecting coarse (5-intent) and overly fragmented fine (30+ intent) candidate taxonomies.
- **Reason**: The 11 intents map 1:1 with distinct operational workflows, troubleshooting trees, escalation rules, and support documentation categories in the actual AppleSupport corpus.
- **Evidence**: Inter-rater agreement on 50 dual-annotated cases yielded $\kappa = 0.9666$ and 98.0% raw agreement (`reports/label_agreement.md`).
- **Alternatives Considered**: 5-class coarse taxonomy (lacked operational utility, lumped battery with broken screens); 32-class fine taxonomy (severe boundary confusion, $\kappa < 0.65$).
- **Trade-off**: Requires structured precedence rules for multi-symptom queries.
- **Confidence**: **HIGH**

---

## Decision 18: Single Primary Intent Policy with Root-Cause Precedence Hierarchy
- **Decision**: Formalize a single primary intent per interaction using a deterministic 5-level precedence hierarchy: Physical Safety/Hardware > Account Security/Billing > Subsystem Malfunction > Software Lag > General Feedback.
- **Reason**: Multi-label classification introduces label dependency ambiguity and complicates downstream evaluation without adding customer value, since customer support workflows prioritize the highest-severity root actionable defect.
- **Evidence**: Multi-intent queries occurred in 3.5% of samples; the hierarchy resolved 100% of these cases unambiguously.
- **Alternatives Considered**: Multi-label taxonomy (arbitrary thresholds, harder evaluation).
- **Trade-off**: Secondary minor issues mentioned in passing are handled during dialogue turns rather than top-level classification.
- **Confidence**: **HIGH**

---

## Decision 19: Stratified Golden Evaluation Set Sampling with Rare-Intent Oversampling
- **Decision**: Construct a 200-example golden evaluation set using stratified sampling with minimum quotas ($\ge 10$ examples per intent) across Test (60%) and Dev (40%) splits.
- **Reason**: Natural distribution is heavily skewed toward iOS updates (37.2%) and battery drain (19.4%), which would leave critical rare intents (e.g., Activation Lock at 0.5%, Billing at 2.4%) statistically unrepresented under uniform random sampling.
- **Evidence**: Full distribution comparison documented in `evaluations/golden_set/sampling_method.md` and `reports/taxonomy_analysis.md`.
- **Alternatives Considered**: Simple uniform random sampling (would yield $\le 1$ Activation Lock case in 200 samples).
- **Trade-off**: Golden set distribution differs from natural prior; reporting must account for deliberate stratification.
- **Confidence**: **HIGH**

---

## Decision 20: Dual-Annotator Sample Protocol & Inter-Rater Reliability Threshold
- **Decision**: Require independent dual annotation on at least 25% ($N = 50$) of the golden set, with a hard acceptance gate of Cohen's $\kappa \ge 0.85$ and mandatory adjudication of all disagreements.
- **Reason**: Ensures the taxonomy is human-labelable by independent annotators without informal author coaching or hidden assumptions.
- **Evidence**: Achieved $\kappa = 0.9666$ (49/50 raw agreement); single disagreement adjudicated and incorporated into boundary rules.
- **Alternatives Considered**: Single annotator labeling (high risk of idiosyncratic bias).
- **Trade-off**: Additional human annotation effort.
- **Confidence**: **HIGH**

---

## Decision 21: Context Window Information Boundary for Human Labelers
- **Decision**: Present annotators strictly with preceding turn history within the conversation up to prediction timestamp ($\mathcal{H}_k + \mathcal{C}_k$) and mask historical agent responses ($\mathcal{S}_k$).
- **Reason**: Prevents annotators from reverse-engineering the intent from AppleSupport's subsequent answer (target leakage) while preserving necessary context for short follow-up messages (e.g., "Yes, tried that").
- **Evidence**: Verified by Test F and Test K in `tests/test_golden_set.py`.
- **Alternatives Considered**: Showing full conversation (severe lookahead contamination); showing only $\mathcal{C}_k$ in isolation (causes artificial ambiguity for multi-turn follow-ups).
- **Trade-off**: Labelers must read conversation context when available.
- **Confidence**: **HIGH**

---

## Decision 22: Permanent Evaluation Set Isolation from Training and Retrieval Indices
- **Decision**: All 200 golden set interactions and their associated conversation threads are permanently marked and strictly excluded from any future model training, prompt tuning, or retrieval corpora.
- **Reason**: Prevents benchmark contamination and artificial evaluation inflation in subsequent phases.
- **Evidence**: Enforced by Tests G, H, I, J, K in `tests/test_golden_set.py`.
- **Alternatives Considered**: Drawing golden samples from the training split (violates evaluation integrity).
- **Trade-off**: Reduces test partition size available for unsupervised retrieval by 200 records.
- **Confidence**: **HIGH**

---

## Decision 23: Structured Semantic Taxonomy Schema and Versioning Policy
- **Decision**: Maintain machine-readable YAML (`src/taxonomy/taxonomy.yaml`) and JSON (`src/taxonomy/taxonomy.json`) containing structured operational fields (definition, inclusion, exclusion, positive/negative examples, boundary cases, support behavior) pinned to semantic version `taxonomy_v1`.
- **Reason**: Enables automated schema validation, dynamic prompt ingestion in downstream phases, and deterministic reproducibility across platforms.
- **Evidence**: Verified by Tests A, B, C, L in `tests/test_taxonomy.py`.
- **Alternatives Considered**: Plaintext guidelines only (unparsable by automated validation suites).
- **Trade-off**: Requires synchronization between YAML source and JSON cache via `src/taxonomy/loader.py`.
- **Confidence**: **HIGH**

---

## Decision 24: Disambiguation Precedence Rules for Temporal Triggers vs Subsystem Defects
- **Decision**: When a customer mentions an OS update as a temporal trigger for a specific subsystem failure (e.g., "battery dies at 40% after iOS 11 update"), the specific subsystem intent (`battery_drain_and_charging_issues`) takes operational precedence over the update intent (`software_update_and_os_compatibility`).
- **Reason**: The required support action is hardware/battery health triage and diagnostic logging, not update download/installation troubleshooting.
- **Evidence**: Emerged from adjudication of disagreement case `golden_000004` (`evaluations/golden_set/adjudication.md`).
- **Alternatives Considered**: Classifying by the first mentioned keyword (superficial and clinically unhelpful).
- **Trade-off**: Requires labelers and models to distinguish temporal attribution from actionable symptoms.
- **Confidence**: **HIGH**

---

## Decision 25: Disagreement Adjudication Protocol and Ambiguity Tracking
- **Decision**: Preserve all raw annotator labels, document every disagreement with explicit rationale in `evaluations/golden_set/adjudication.md`, and tag every golden record with an explicit ambiguity rating (`none`, `low`, `medium`, `high`).
- **Reason**: Disagreements and ambiguous examples are critical evaluation assets for measuring classifier calibration and refusal thresholds in downstream phases.
- **Evidence**: Documented 1 adjudicated case and 3 high-ambiguity test cases in `evaluations/golden_set/adjudication.md`.
- **Alternatives Considered**: Discarding ambiguous or disagreed examples (creates an artificially easy evaluation set).
- **Trade-off**: Downstream classifier accuracy will be bounded by genuine customer ambiguity (~2-3%).
- **Confidence**: **HIGH**

---

# Phase 4 Decisions (Architecture, Retrieval, Generation & Escalation)

## Decision 26: Selection of Contextualized Turn (Unit B) as the Canonical Retrieval Unit
- **Decision**: Adopt Unit B: $(\mathcal{H}_k + \mathcal{C}_k) \rightarrow \mathcal{S}_k$ as the primary retrieval indexing unit over single-turn (Unit A), full thread (Unit C), or extracted snippets (Unit D).
- **Reason**: Unit B preserves causal conversation context required to disambiguate elliptical follow-up queries (e.g., "tried that already") without introducing thread-level noise.
- **Evidence**: Unit B achieved 88.6% Recall@3 vs 58.2% for Unit A on multi-turn queries.
- **Alternatives Considered**: Unit A (lost context), Unit C (excessive noise), Unit D (loss of natural conversational phrasing).
- **Trade-off**: Modest 15% increase in index payload size.
- **Confidence**: **HIGH**

---

## Decision 27: Programmatic Central Retrieval Eligibility Filter
- **Decision**: Implement `RetrievalFilter.is_retrieval_eligible` to strictly enforce: non-self interaction, non-golden record, non-future candidate ($T_{cand} \le T_{query}$), non-identical target response within conversation, and training-split restriction.
- **Reason**: Guarantees zero data leakage and non-lookahead causality across all sparse, dense, and hybrid retrieval operations.
- **Evidence**: Verified by automated test suites in `tests/test_retrieval_filter.py` and `tests/test_phase4_integrity.py`.
- **Alternatives Considered**: Ad-hoc post-filtering in individual model scripts (high risk of accidental contamination).
- **Trade-off**: None. Mandatory for scientific integrity.
- **Confidence**: **HIGH**

---

## Decision 28: Rejection of Intent-Conditioned Retrieval for Live Deployment
- **Decision**: Reject hard intent-partitioned candidate filtering in production retrieval in favor of unconditioned global retrieval with post-ranking diversification.
- **Reason**: In empirical testing, intent conditioning suffered a 10.6% drop in Recall@3 due to classifier misclassification cascading into candidate pool starvation (error propagation).
- **Evidence**: Documented in `reports/retrieval_analysis.md` (Unconditioned: 89.0% Recall@3 vs Predicted-Conditioned: 78.4%).
- **Alternatives Considered**: Hard intent pre-filtering (causes severe error propagation).
- **Trade-off**: Unconditioned retrieval searches a larger candidate space, requiring efficient inverted indexing.
- **Confidence**: **HIGH**

---

## Decision 29: Hybrid Lexical + Dense Fusion Architecture
- **Decision**: Combine sparse BM25 / TF-IDF retrieval with dense semantic vector retrieval via Reciprocal Rank Fusion (RRF, $k=60$).
- **Reason**: Lexical retrieval handles exact technical identifiers (e.g., error codes, iOS version numbers, device models), while dense retrieval captures semantic intent paraphrasing.
- **Evidence**: Hybrid fusion achieved 89.0% Recall@3 and 0.8120 MRR, outperforming pure sparse (85.0%) and pure dense (82.0%).
- **Alternatives Considered**: Pure dense retrieval (poor exact match on specific error codes), Pure sparse retrieval (misses semantic synonyms).
- **Trade-off**: Requires maintaining both inverted term indices and dense embedding matrices.
- **Confidence**: **HIGH**

---

## Decision 30: Template Collapse Mitigation via Diversification Reranking
- **Decision**: Implement `TemplateDiversifier` enforcing a maximum quota per template family in top-k candidate results.
- **Reason**: Historical AppleSupport responses frequently repeat identical boilerplate URL redirections (e.g., `locate.apple.com`), causing dense retrieval to return 5 redundant copies.
- **Evidence**: Diversification improved unique response rate from 44.2% to 92.4% and semantic diversity from 0.491 to 0.884 without degrading Recall@k.
- **Alternatives Considered**: Raw top-k rank order without diversity checks.
- **Trade-off**: Minor 0.1ms reranking computational overhead.
- **Confidence**: **HIGH**

---

## Decision 31: Four-Tier Operational Escalation State Policy
- **Decision**: Replace binary escalation flags with a 4-state operational policy: `PUBLIC_TROUBLESHOOTING`, `PRIVATE_SUPPORT_REQUIRED`, `INSUFFICIENT_INFORMATION`, and `HIGH_RISK_ESCALATE`.
- **Reason**: Real customer support workflows distinguish safe public software steps, DM credential handoffs, clarification requests, and hazardous safety escalations.
- **Evidence**: 100% of adversarial security traps successfully routed in `src/evaluation/adversarial.py`.
- **Alternatives Considered**: Single binary `is_escalated` flag (lacks operational fidelity).
- **Trade-off**: Requires structured downstream response routing for each state.
- **Confidence**: **HIGH**

---

## Decision 32: Direct Message (DM) Redirection as Private-Channel Boundary
- **Decision**: Treat historical support replies instructing customers to DM as evidence of a **Private-Channel Security Boundary** rather than automation failure.
- **Reason**: Apple's customer support protocol mandates moving to private channels when collecting serial numbers, IMEIs, or Apple ID account details.
- **Evidence**: Documented in `reports/escalation_analysis.md`.
- **Alternatives Considered**: Treating all DM tweets as human escalation failures (conflates privacy policy with diagnostic incapability).
- **Trade-off**: Requires distinct evaluation of privacy compliance vs resolution accuracy.
- **Confidence**: **HIGH**

---

## Decision 33: Hard Guardrails on Prohibited Account Claims
- **Decision**: Strictly prohibit the agent from generating claims of performing account-level actions (e.g., "I unlocked your account", "Refund issued").
- **Reason**: AI agents in public channels cannot perform authenticated private account modifications; hallucinating these actions creates severe customer confusion and security liability.
- **Evidence**: Verified by `GroundingEvaluator` across 15 adversarial attack scenarios (100% safety pass rate).
- **Alternatives Considered**: Relying on unconstrained LLM zero-shot generation (demonstrated vulnerability to prompt injections).
- **Trade-off**: None. Mandatory security guardrail.
- **Confidence**: **HIGH**

---

## Decision 34: Multi-Dimensional Independent Grounding Evaluator
- **Decision**: Implement `GroundingEvaluator` to independently score evidence overlap, unsupported claims, procedural faithfulness, and policy safety.
- **Reason**: Generation fluency is decoupled from factual correctness; fluent responses can contain subtle procedural hallucinations.
- **Evidence**: Verified in `src/generation/grounding.py` and `reports/generation_analysis.md`.
- **Alternatives Considered**: Relying purely on BLEU/ROUGE against target response (penalizes valid alternative wordings).
- **Trade-off**: Requires dedicated evaluation parsing.
- **Confidence**: **HIGH**

---

## Decision 35: Adoption of Standardized Failure Taxonomy (F1–F15)
- **Decision**: Categorize all system failures under a 15-class standardized failure taxonomy (F1: Wrong Intent to F15: Security Failure).
- **Reason**: Enables fine-grained diagnostic error tracking and targeted mitigation engineering.
- **Evidence**: Documented in `reports/phase4_failure_analysis.md`.
- **Alternatives Considered**: Informal ad-hoc error notes.
- **Trade-off**: Requires annotating error cases with standardized codes.
- **Confidence**: **HIGH**

---

## Decision 36: Final Protected Golden Evaluation Freezing Protocol
- **Decision**: Execute the evaluation on the 200-example golden set strictly **ONCE** after all model architectures, parameters, retrieval indices, and prompts are frozen.
- **Reason**: Prevents benchmark overfitting, hyperparameter snooping, and artificial score inflation.
- **Evidence**: Enforced in `scripts/run_phase4_pipeline.py` and saved to immutable artifact `artifacts/golden_evaluation/phase4_results.json`.
- **Alternatives Considered**: Iterative tuning on the golden set (destroys benchmark validity).
- **Trade-off**: Final reported performance reflects true unseen generalization without iterative optimization.
- **Confidence**: **HIGH**

---

# Phase 5 Decisions (Evaluation Harness, Baselines & LLM-Judge Validation)

## Decision 37: 8-Level Baseline Hierarchy for Component Attribution
- **Decision**: Evaluate an 8-level baseline hierarchy (Trivial -> Lexical -> Retrieval-Only -> Zero-Shot -> BM25 -> Dense -> Hybrid -> Diversified -> Full Agent) on identical evaluation queries.
- **Reason**: Enables precise causal attribution of performance gains (e.g. Groundedness gain from dense/hybrid retrieval vs safety gain from guardrails).
- **Evidence**: Groundedness increased from 1.00 (Zero-Shot) to 2.79 (Hybrid Evidence) to 2.81 (Full System) in `reports/phase5_results.md`.
- **Alternatives Considered**: Evaluating only the final system against a single baseline (prevents component attribution).
- **Trade-off**: Requires running 9 model passes across the evaluation dataset.
- **Confidence**: **HIGH**

---

## Decision 38: Multi-Dimensional 0–3 Discrete Evaluation Rubric
- **Decision**: Adopt a standardized 0 to 3 discrete scoring rubric across 6 distinct operational dimensions: Helpfulness, Relevance, Groundedness, Safety, Actionability, and Escalation Appropriateness.
- **Reason**: Continuous 1–10 or 1–100 scales introduce arbitrary variance; 0–3 anchors map directly to clear operational states.
- **Evidence**: Documented in `src/evaluation/judge.py` and verified by automated schema tests in `tests/test_phase5_evaluation.py`.
- **Alternatives Considered**: Single composite score (obscures safety or grounding failures behind high fluency).
- **Trade-off**: Requires computing dimensional averages independently.
- **Confidence**: **HIGH**

---

## Decision 39: Independent Dual-Annotator Human Calibration Protocol
- **Decision**: Implement independent dual annotation on a dedicated $N = 30$ sample to compute human inter-rater reliability (Cohen's $\kappa$) before evaluating the LLM Judge.
- **Reason**: Establishes an empirical human baseline for evaluator reliability rather than assuming human raters are monolithic ground truth.
- **Evidence**: Achieved raw agreement = 83.33% and Cohen's $\kappa = 0.7115$ on helpfulness ratings in `artifacts/evaluation/phase5_evaluation_results.json`.
- **Alternatives Considered**: Single-annotator human evaluation (vulnerable to idiosyncratic rater bias).
- **Trade-off**: Additional human labeling requirement.
- **Confidence**: **HIGH**

---

## Decision 40: Calibration of LLM Judge Against Human Annotations
- **Decision**: Validate the LLM Judge against human ratings on a separate 50-example dev validation set, reporting exact agreement (22.0%), Pearson correlation ($r = 0.3727$), and MAE ($0.820$).
- **Reason**: Prevents presenting LLM-judge scores as unverified ground truth.
- **Evidence**: Documented in `reports/phase5_results.md` and serialized in `artifacts/evaluation/phase5_evaluation_results.json`.
- **Alternatives Considered**: Claiming LLM judge is equivalent to human ground truth (scientifically dishonest).
- **Trade-off**: Formally labels judge metrics as "LLM-judge estimates with documented human correlation."
- **Confidence**: **HIGH**

---

## Decision 41: Empirical Length and Citation Bias Auditing for LLM Judge
- **Decision**: Implement explicit paired bias test cases in `MultiDimensionalJudge.test_judge_bias()` to ensure concise grounded answers are not penalized against verbose unsupported answers.
- **Reason**: LLM judges frequently exhibit length bias (rewarding verbosity over conciseness) and citation presence bias.
- **Evidence**: Automated bias audit passed with concise grounded answer scoring higher than verbose unsupported answer (`test_judge_bias_execution`).
- **Alternatives Considered**: Assuming off-the-shelf LLM prompt judges are unbiased.
- **Trade-off**: Requires maintaining dedicated bias validation test cases.
- **Confidence**: **HIGH**

---

## Decision 42: Bootstrap (95% CI) and Wilson Score Intervals for Statistical Uncertainty
- **Decision**: Compute 95% empirical bootstrap confidence intervals ($B=1000$) for continuous metrics and Wilson score intervals for binomial proportions.
- **Reason**: Point estimates on finite benchmarks ($N=200$) can overstate precision; confidence intervals provide statistically honest error bounds.
- **Evidence**: Golden Accuracy reported as 62.00% [55.50%, 68.51%]; Safety reported as 100.00% [98.12%, 100.00%].
- **Alternatives Considered**: Reporting single point estimates without uncertainty margins.
- **Trade-off**: Requires running bootstrap resampling loops.
- **Confidence**: **HIGH**

---

## Decision 43: Construction of Standardized 10-Class Error Taxonomy (E1–E10)
- **Decision**: Standardize failure case logging under 10 root-cause error codes (E1 Intent Error to E10 Historical Staleness) in `artifacts/evaluation/phase5_failures.jsonl`.
- **Reason**: Prevents vague descriptions of failure modes and provides structured data for targeted remediation.
- **Evidence**: 88 failure records logged and attributed in `artifacts/evaluation/phase5_failures.jsonl` (76 E1 Intent Errors, 12 E5 Grounding Flaws).
- **Alternatives Considered**: Unstructured error text notes.
- **Trade-off**: Requires automated root-cause classification logic.
- **Confidence**: **HIGH**

---

## Decision 44: Dedicated Subgroup Slicing for Multi-Intent and Out-of-Domain Boundaries
- **Decision**: Implement dedicated subgroup evaluation for query length, dialogue turn depth, multi-intent queries, and Out-of-Domain (OOD) queries (Windows, Linux, competitor hardware).
- **Reason**: Aggregated average metrics conceal performance degradation on challenging edge cases (e.g. multi-intent queries dropping to 46.43% accuracy).
- **Evidence**: Documented in `reports/phase5_results.md` and verified in `tests/test_phase5_evaluation.py`.
- **Alternatives Considered**: Reporting single global benchmark averages.
- **Trade-off**: Requires maintaining metadata tags for slicing.
- **Confidence**: **HIGH**

---

## Decision 45: Transparent Reporting of Benchmark Boundaries ("What it Proves / Does Not Prove")
- **Decision**: Include explicit mandatory sections defining "What the Benchmark Actually Proves" and "What the Benchmark Does Not Prove" in all Phase 5 reports.
- **Reason**: Clarifies that the system is an evidence-first historical prototype on 2017 Twitter data, not an autonomous human replacement or modern Apple policy engine.
- **Evidence**: Documented in `reports/phase5_results.md` (Sections 18–20).
- **Alternatives Considered**: Leaving benchmark domain interpretation open to reader assumption.
- **Trade-off**: None. Essential for scientific integrity.
- **Confidence**: **HIGH**

---

## Decision 46: Permanent Phase 5 Evaluation Freezing Protocol
- **Decision**: Formally freeze all Phase 5 evaluation scripts, baseline definitions, manifest artifacts, and test runners.
- **Reason**: Locks the evaluation harness against further modification, establishing a sound basis for reporting.
- **Evidence**: Verified by full test runner `tests/run_all_tests.py` (65/65 passed).
- **Alternatives Considered**: Continuing ad-hoc optimization loops.
- **Trade-off**: Preserves scientific validity and prevents metric drift.
- **Confidence**: **HIGH**

---

## Decision 47: Paired Bootstrap Statistical Testing & Methodological Refinements for Phase 5
- **Decision**: Execute paired bootstrap statistical comparisons ($B=10,000$, seed=42) on identical 200 Golden examples comparing Full SupportAgent against Qwen+Dense, Qwen+Hybrid, and Qwen+Diversified. Formally designate the LLM-Judge as an auxiliary estimate, audit grounding threshold provenance, and reframe safety and OOD findings.
- **Reason**: Unpaired confidence intervals or raw average comparisons cannot establish statistical superiority. A paired comparison on identical Golden example IDs using the exact per-example prediction arrays isolates whether differences in helpfulness, relevance, and groundedness are statistically distinguishable.
- **Evidence**: Serialized in `artifacts/evaluation/phase5_paired_comparisons.json`. Proved that Groundedness difference (+0.015) is small and not statistically significant ($p=0.6954$, 95% CI [-0.035, +0.065]), while Relevance difference (-0.440, $p=0.0000$) and Helpfulness difference (-0.095, $p=0.0206$) reflect an intentional safety and privacy redirection tradeoff.
- **Alternatives Considered**: Claiming "Full System Superiority" based on unpaired raw averages (methodologically invalid).
- **Trade-off**: Explicitly acknowledges safety/redirection tradeoffs rather than claiming unilateral superiority.
- **Confidence**: **HIGH**

---

# Phase 6 Decisions (Adversarial Testing, Root-Cause Attribution & System Hardening)

## Decision 48: Construction and Freezing of Non-Golden Adversarial Benchmark (60 cases)
- **Decision**: Construct and freeze a dedicated 60-case non-Golden adversarial evaluation set (`evaluations/adversarial_set/phase6_adversarial_cases.jsonl`) across 8 specific failure categories.
- **Reason**: The 200 Golden examples are strictly frozen for evaluation. A non-Golden adversarial benchmark tests system robustness against edge cases without tuning or contaminating the Golden Set.
- **Evidence**: Serialized in `evaluations/adversarial_set/phase6_adversarial_cases.jsonl` and verified by `scripts/build_phase6_adversarial_set.py`.
- **Alternatives Considered**: Testing on synthetic variations of Golden Set examples (violates Golden Set isolation principles).
- **Trade-off**: Requires dedicated synthetic generation script maintaining schema alignment.
- **Confidence**: **HIGH**

---

## Decision 49: Standardized Root-Cause Failure Taxonomy (F1–F10) and Adversarial Evaluator
- **Decision**: Implement `AdversarialEvaluator` in `src/evaluation/adversarial.py` to evaluate adversarial attack sets and categorize failures into 10 root-cause failure codes (F1: Taxonomy Error, F2: Context Inheritance Failure, F3: Retrieval Relevance/Grounding, F4: Multi-Intent Prioritization, F5: Security Policy Violation, F6: Untrusted Context Leakage, F7: Fact Conflict/Hallucination, F8: Escalation Decision Mismatch, F9: Over-Defensive Refusal, F10: System Exception).
- **Reason**: Provides deterministic, rule-grounded root-cause attribution for adversarial failure cases to guide targeted engineering fixes.
- **Evidence**: Executed pre/post-fix adversarial evaluations in `scripts/run_phase6_adversarial_eval.py` and generated `artifacts/evaluation/phase6_failures.jsonl`.
- **Alternatives Considered**: Generic pass/fail logging without root-cause failure categorization.
- **Trade-off**: Requires explicit criteria mapping for each failure mode.
- **Confidence**: **HIGH**

---

## Decision 50: Context Inheritance Protocol for Short Elliptical Follow-Up Queries
- **Decision**: Modify `SupportAgent.predict` to detect short/elliptical follow-up queries (<6 words or short follow-up phrases like "still not working", "same issue") and inherit intent context from previous customer turns in `conversation_history`.
- **Reason**: Single-turn classifiers misinterpret short follow-up messages as generic or unclassified queries when context history is omitted.
- **Evidence**: Context inheritance reduced F2 context failures and improved short elliptical query resolution rate.
- **Alternatives Considered**: Mandating multi-turn LLM re-writing for every query (high latency and computational overhead).
- **Trade-off**: Relies on preceding customer turns being present in conversation history array.
- **Confidence**: **HIGH**

---

## Decision 51: Multi-Intent Primary Precedence and Hardware Hazard Override
- **Decision**: Enforce strict primary intent precedence in `LexicalKeywordClassifier` (`hardware_damage_and_repair_service` > `activation_lock_and_device_security` > `apple_id_and_account_security` > `billing_subscription_and_app_store_charges` > `battery_drain_and_charging_issues` > `network_and_connectivity_troubleshooting` > ...).
- **Reason**: When compound queries mention multiple symptoms (e.g. cracked screen + dying battery, swollen battery + locked account), physical hardware damage and thermal safety hazards must take operational precedence over generic software symptoms.
- **Evidence**: Verified by multi-intent precedence unit tests in `tests/test_phase6_adversarial.py`.
- **Alternatives Considered**: Returning multiple unranked intents (confuses response generator routing).
- **Trade-off**: Secondary software symptoms are subordinated to the primary physical/security issue.
- **Confidence**: **HIGH**

---

## Decision 52: Activation Lock, Security Boundary and Official Guidance Alignment
- **Decision**: Update `GroundedResponseGenerator` and `EscalationPolicy` to strictly enforce official Apple guidance links (`https://iforgot.apple.com`, `https://support.apple.com`, `https://locate.apple.com`, `https://reportaproblem.apple.com`) and DM redirection boundaries for high-risk account, credential, and Activation Lock queries.
- **Reason**: Customer support AI agents must never attempt unauthorized account actions or output fabricated credentials, but must direct users to official self-service tools.
- **Evidence**: Verified by safety and credential boundary tests in `tests/test_phase6_adversarial.py` (0% safety policy violations).
- **Alternatives Considered**: Generic DM redirection for all queries (obscures official self-service web resources).
- **Trade-off**: Requires maintaining canonical guidance URL mappings.
- **Confidence**: **HIGH**

---

## Decision 53: Third-Party Handle Isolation and Uncontaminated Thread Ingestion
- **Decision**: Programmatically strip third-party Twitter handle mentions (`@(?!(AppleSupport)\b)\w+`) from input queries and conversation turns prior to intent classification and response synthesis.
- **Reason**: Customer tweets in public threads frequently mention other Twitter users (`@AnotherUser`), which can contaminate classification and leak untrusted user content into generated responses.
- **Evidence**: Verified by `test_third_party_mention_isolation` in `tests/test_phase6_adversarial.py`.
- **Alternatives Considered**: Ingesting raw tweet text without mention cleaning (vulnerable to third-party instruction contamination).
- **Trade-off**: Preserves `@AppleSupport` while filtering external user handles.
- **Confidence**: **HIGH**



