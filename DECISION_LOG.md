# Project Decision Log

This document records the foundational architectural, analytical, and problem-framing decisions made across project phases.

---

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
- **Confidence**: **HIGH** (Justified by leading customer diversity, rich multi-turn troubleshooting, and clear domain boundaries).

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
- **Confidence**: **HIGH** (Empirically grounded in conversation topology and multi-turn dependency).

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
- **Confidence**: **HIGH** (Standard ML practice for temporal sequence tasks with policy/software drift).

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
- **Confidence**: **HIGH** (Accurately reflects real-world multi-channel support boundaries).

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
- **Confidence**: **MEDIUM** (Empirically grounded on same-author breakdown; exact multi-modal threshold will be finalized in Phase 2).
