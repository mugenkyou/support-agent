# Data Construction & Canonical Modeling Example Report

**Target Brand**: `AppleSupport`  
**Phase**: Phase 2 — Conversation Reconstruction & Dataset Construction  
**Generated On**: September 2026  
**Status**: Verified & Reproducible  

---

## 1. What Exactly Is One Modeling Example?

An atomic modeling example in this dataset is formally defined as a **Contextualized Support Turn Pair**:

$$\mathcal{E}_k = \Big( \mathcal{H}_k, C_k, S_k \Big)$$

Where:
- $C_k$: The current incoming customer problem statement (either a standalone tweet or an aggregated same-author multipart message).
- $\mathcal{H}_k = (C_1, S_1, C_2, S_2, \dots, C_{k-1}, S_{k-1})$: The preceding historical conversation turns on the direct causal ancestor path, strictly satisfying $T(\text{turn}) \le T(C_k)$.
- $S_k$: The ground-truth historical `AppleSupport` response directly paired with $C_k$.

### Canonical JSON Schema
```json
{
  "interaction_id": "app_123456_115712",
  "conversation_id": "conv_115710",
  "customer_id": "115712",
  "brand": "AppleSupport",
  "timestamp": "Tue Oct 31 22:11:45 +0000 2017",
  "created_ts": 1509487905,
  "customer_message_raw": "@AppleSupport why is my battery draining so fast on iOS 11?",
  "customer_message_normalized": "<user> why is my battery draining so fast on ios 11?",
  "context": [
    {
      "tweet_id": 115710,
      "author_id": "AppleSupport",
      "author_type": "support",
      "created_at": "Tue Oct 31 22:08:00 +0000 2017",
      "created_ts": 1509487680,
      "text": "What device model are you using?"
    }
  ],
  "historical_response_raw": "@115712 We'd love to help with your battery concerns. What iPhone model do you have?",
  "historical_response_normalized": "<user> we'd love to help with your battery concerns. what iphone model do you have?",
  "target_support_tweet_id": 123456,
  "source_customer_tweet_ids": [115712],
  "multipart_aggregated": false,
  "latency_seconds": 225,
  "lifecycle_state": "USABLE_RESPONSE_EXAMPLE"
}
```

---

## 2. Why Was This Definition Selected?

1. **Multi-Turn Dependency**: Over 29.40% (31,350 turns) of `AppleSupport` interactions are conversational follow-ups (e.g., *"I tried that and it didn't work"* or *"iPhone 7 Plus"*). A single-turn framing ($C_k \rightarrow S_k$) lacks the antecedent questions necessary to resolve references.
2. **Causal Autoregressive Alignment**: In a live support deployment, an AI agent receives the conversation history up to the user's latest query and must predict the subsequent response $S_k$ without seeing future dialogue.
3. **Traceability**: Every modeling example preserves explicit integer `tweet_id`s, `customer_id`, and `conversation_id`, enabling exact provenance mapping back to `data/raw/twcs.csv`.

---

## 3. Information-Time Boundary

To prevent future lookahead leakage, we strictly enforce:

$$\text{Input}(\mathcal{E}_k) \subseteq \text{InformationAvailableAt}\Big( T(C_k) \Big)$$

- **Permitted in Input Context**:
  - $C_k$ (Current customer message)
  - Preceding conversation turns $(C_1, S_1, \dots, C_{k-1}, S_{k-1})$ where $\forall t \in \text{context}, \text{created\_ts}(t) \le \text{created\_ts}(C_k)$.
- **Strictly Prohibited from Input Context**:
  - Target response $S_k$.
  - Subsequent customer follow-ups $C_{k+1}, C_{k+2}, \dots$.
  - Subsequent support messages $S_{k+1}, \dots$.
  - Any external post-2017 documentation or future global events.

---

## 4. Conversation Reconstruction & Graph Traversal

Conversation trees are reconstructed using explicit relational parent pointers:
1. **Root Identification**: A root tweet is defined as any tweet where `in_response_to_tweet_id` is `NULL` or points to an ID outside the dataset.
2. **Conversation ID Assignment**: Every node in a tree is deterministically assigned `conversation_id = f"conv_{root_tweet_id}"`.
3. **Timestamp Tie Breaking**: If $T(\text{parent}) == T(\text{child})$, the directed edge (`child.in_response_to == parent.id`) places the parent strictly before the child. If sibling turns share identical timestamps, they are sorted by integer `tweet_id`.

---

## 5. Inbound $\rightarrow$ Inbound Handling & Multipart Merging

Empirical auditing of the 188,447 Inbound $\rightarrow$ Inbound links revealed:
- **54.67% (103,028 links)** are **Third-Party Customer Interjections** (different customer authors commenting on a public thread).
- **45.33% (85,419 links)** are **Same-Author Chains**.

### Multipart Aggregation Rule
Two consecutive inbound turns $C_a$ and $C_b$ from the same customer are merged into a unified turn if:
1. `author_id(Ca) == author_id(Cb)` AND
2. `Cb.in_response_to_tweet_id == Ca.tweet_id` (or direct parent) AND
3. $\Delta t = T(C_b) - T(C_a) \le 120\text{ seconds}$ AND
4. (Linguistic continuation detected: `...`, `1/2`, `Part 1`, `-`, `+` OR $\Delta t \le 60\text{s}$).

Across the `AppleSupport` corpus, this rule merged **1,929 genuine multipart queries**, collating split character-limit tweets while protecting against false merges of delayed follow-up turns.

---

## 6. Third-Party Comment Isolation

When third-party customers reply to a public customer thread:
- The third-party turns are excluded from the target customer's context path.
- The context builder isolates turns where `(author_id == target_customer) OR (author_id == AppleSupport)`.
- Automated Test Q verifies that zero third-party customer messages leak into a user's context.

---

## 7. Lifecycle States & Data Reconciliation

Every candidate tweet in the dataset is deterministically classified into an explicit lifecycle state:

| Lifecycle State | Count | Description | Action in Pipeline |
| :--- | :--- | :--- | :--- |
| **`USABLE_RESPONSE_EXAMPLE`** | **106,646** | Inbound customer turn with direct `AppleSupport` reply | Ingested into `interactions.jsonl` |
| **`NO_OBSERVED_RESPONSE`** | **19,490** | Inbound customer query mentioning brand with no reply in CSV | Logged in `exclusion_log.jsonl` |
| **`TEMPORAL_INVERSION`** | **0** | Child timestamp earlier than parent timestamp | None found |
| **`AMBIGUOUS_CONTEXT`** | **0** | Unresolvable cycle or invalid parent | None found |

**Total Reconciled Records**: $106,646 + 19,490 = 126,136$ customer inbound queries addressed to `AppleSupport`. Zero unexplained dropped rows.
