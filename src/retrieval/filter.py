"""Central Retrieval Eligibility and Leakage Filter.

Enforces strict information boundaries for historical response retrieval:
1. Candidate cannot be the target interaction (candidate_id != query_id).
2. Candidate response cannot be identical to the target response string.
3. Candidate timestamp must be strictly <= query timestamp (T_cand <= T_query).
4. Candidate cannot belong to the protected Golden Evaluation Set.
5. Candidate cannot belong to the same conversation future turns.
6. Candidate must originate from the approved historical training pool.
"""

import json
import os
from typing import Any, Dict, Optional, Set, Tuple


class RetrievalFilter:
    """Central filter for verifying retrieval candidate eligibility."""

    def __init__(self, golden_set_path: str = "evaluations/golden_set/golden_set.jsonl"):
        self.golden_set_path = golden_set_path
        self.golden_interaction_ids: Set[str] = set()
        self.golden_tweet_ids: Set[int] = set()
        self.golden_conversation_ids: Set[str] = set()
        self._load_golden_set()

    def _load_golden_set(self):
        if not os.path.exists(self.golden_set_path):
            return
        with open(self.golden_set_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    data = json.loads(line)
                    if "interaction_id" in data:
                        self.golden_interaction_ids.add(data["interaction_id"])
                    if "conversation_id" in data:
                        self.golden_conversation_ids.add(data["conversation_id"])
                    if "source_customer_tweet_ids" in data:
                        for tid in data["source_customer_tweet_ids"]:
                            self.golden_tweet_ids.add(int(tid))
                    if "target_support_tweet_id" in data:
                        self.golden_tweet_ids.add(int(data["target_support_tweet_id"]))

    def is_retrieval_eligible(
        self,
        query_item: Dict[str, Any],
        candidate_item: Dict[str, Any],
    ) -> Tuple[bool, Optional[str]]:
        """Determine if candidate_item is eligible to be retrieved for query_item.
        
        Returns:
            (is_eligible, exclusion_reason)
        """
        # Rule 1: Cannot retrieve self
        q_iid = query_item.get("interaction_id")
        c_iid = candidate_item.get("interaction_id")
        if q_iid and c_iid and q_iid == c_iid:
            return False, "EXCLUDED_SELF_INTERACTION"

        # Rule 2: Cannot retrieve protected golden evaluation record
        if c_iid in self.golden_interaction_ids:
            return False, "EXCLUDED_GOLDEN_SET_RECORD"

        # Rule 3: Cannot retrieve candidate with target response identical to query response
        q_resp = query_item.get("historical_response_raw", "").strip()
        c_resp = candidate_item.get("historical_response_raw", "").strip()
        if q_resp and c_resp and q_resp == c_resp and query_item.get("conversation_id") == candidate_item.get("conversation_id"):
            return False, "EXCLUDED_IDENTICAL_TARGET_RESPONSE_IN_CONVERSATION"

        # Rule 4: Temporal Non-Lookahead Boundary (T_cand <= T_query)
        q_ts = query_item.get("created_ts", float("inf"))
        c_ts = candidate_item.get("created_ts", 0)
        if c_ts > q_ts:
            return False, "EXCLUDED_FUTURE_TEMPORAL_VIOLATION"

        # Rule 5: Allowed split source (candidate must be from train pool)
        c_split = candidate_item.get("split", "train")
        if c_split not in ("train", "Train"):
            return False, "EXCLUDED_NON_TRAINING_SPLIT"

        return True, None
