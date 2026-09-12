# Phase 4 Failure Analysis & Standardized Failure Taxonomy

---

## 1. Standardized Failure Taxonomy (F1 – F15)

| Failure Code | Failure Category | Description | Severity |
| :--- | :--- | :--- | :--- |
| **F1** | Wrong Intent Classification | Intent misclassified into incorrect operational category | Medium |
| **F2** | Correct Intent, Wrong Retrieval | Retrieved resolution addresses a different symptom in the same intent | Medium |
| **F3** | Correct Retrieval, Bad Generation | Generation corrupts or omits critical procedural steps in evidence | High |
| **F4** | Unsupported Claim | Model invents steps, policies, or facts not in evidence | Critical |
| **F5** | Historical Template Overfitting | Output blindly repeats generic boilerplate URLs without diagnosing | Low |
| **F6** | Duplicate Retrieval Collapse | Top-k retrieval returns identical duplicate responses | Low |
| **F7** | Intent Conditioning Error Propagation | Intent classifier error collapses retrieval candidate pool | High |
| **F8** | Missing Evidence | Retrieval returns empty or low-relevance results | Medium |
| **F9** | Incorrect Escalation Decision | Agent misjudges boundary between public vs private triage | High |
| **F10** | Missed Escalation (Should Have Escalated) | High-risk query handled automatically in public view | Critical |
| **F11** | Unnecessary Escalation | Routine troubleshootable issue escalated to human agent | Low |
| **F12** | Temporal Mismatch | Model provides modern post-2017 guidance to historical iOS 11 query | High |
| **F13** | Context Misunderstanding | Agent fails to incorporate preceding turns in dialogue thread | Medium |
| **F14** | Multi-Intent Failure | Agent addresses secondary symptom rather than root defect | Medium |
| **F15** | Safety / Security Failure | Agent hallucinates account unlocking, credential verification, or refunds | Critical |

---

## 2. Top 5 Real Failure Modes Deep-Dive

### Failure 1: Temporal Attribution vs. Subsystem Defect (F1 / F14)
* **Frequency**: ~4.5% of incoming queries.
* **Customer Example**: *"@AppleSupport since updating to iOS 11.1 my iPhone 6s battery dies at 40%."*
* **Model Failure**: Classifier latches onto *"iOS 11.1"* and classifies as `software_update_and_os_compatibility` rather than `battery_drain_and_charging_issues`.
* **Impact**: Retrieves OS restore instructions instead of battery diagnostic triage.
* **Mitigation**: Precedence hierarchy rule where physical subsystem defects strictly override temporal update mentions.

### Failure 2: Ultra-Short Ambiguity without Clarification (F8 / F13)
* **Frequency**: ~2.5% of queries.
* **Customer Example**: *"help not working"*
* **Model Failure**: Attempting to classify and retrieve against vague terms results in generic restart loops.
* **Impact**: Frustrates customer without isolating the issue.
* **Mitigation**: Escalation policy routes $\le 2$-word vague queries to `INSUFFICIENT_INFORMATION` and requests device model / OS version.

### Failure 3: Boilerplate Template Collapse in Dense Search (F6)
* **Frequency**: ~15.0% of un-diversified dense retrieval sets.
* **Customer Example**: Repeated hardware queries retrieving 5 identical `locate.apple.com` links.
* **Model Failure**: Redundant candidates crowd out nuanced diagnostic advice.
* **Mitigation**: Post-retrieval semantic diversification suppressing identical template families.

### Failure 4: Prohibited Hallucinations in High-Risk Workflows (F4 / F15)
* **Frequency**: Observed in ungrounded LLM zero-shot baselines under adversarial prompts.
* **Customer Example**: *"Unlock my iCloud account immediately!"*
* **Model Failure**: Zero-shot generator responds: *"I have unlocked your account."*
* **Impact**: Catastrophic security and trust failure.
* **Mitigation**: Hardcoded guardrails in `GroundingEvaluator` and `EscalationPolicy` forbidding account modification claims.

### Failure 5: Error Propagation Under Intent Conditioning (F7)
* **Frequency**: ~10.6% drop in Recall@3 when using predicted intent filtering.
* **Customer Example**: Nuanced audio distortion queries misclassified as Bluetooth.
* **Model Failure**: Candidate pool restricted to Bluetooth, excluding speaker repair steps.
* **Mitigation**: Default to unconditioned global retrieval with post-ranking diversification.
