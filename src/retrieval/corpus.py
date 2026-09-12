"""Historical Retrieval Corpus Construction and Candidate Unit Definitions.

Supports 4 candidate retrieval units:
- Unit A: Single turn (Customer Query -> Support Response)
- Unit B: Contextualized turn (Context History + Customer Query -> Support Response)
- Unit C: Full conversation thread representation
- Unit D: Extracted troubleshooting action snippets
"""

import json
import os
from typing import Any, Dict, List, Optional
from src.retrieval.filter import RetrievalFilter


class RetrievalCorpus:
    """Historical knowledge corpus for retrieval."""

    def __init__(
        self,
        interactions_path: str = "data/processed/interactions.jsonl",
        splits_path: str = "data/processed/splits.json",
        golden_set_path: str = "evaluations/golden_set/golden_set.jsonl",
        unit_type: str = "unit_b",
    ):
        self.interactions_path = interactions_path
        self.splits_path = splits_path
        self.unit_type = unit_type
        self.filter = RetrievalFilter(golden_set_path)
        self.candidates: List[Dict[str, Any]] = []
        self._load_corpus()

    def _load_corpus(self):
        # Identify train interactions
        train_ids = set()
        if os.path.exists(self.splits_path):
            with open(self.splits_path, "r", encoding="utf-8") as f:
                splits_data = json.load(f)
                temp_split = splits_data.get("temporal_split", {})
                parts = temp_split.get("partitions", temp_split)
                train_ids = set(parts.get("train", []))


        if not os.path.exists(self.interactions_path):
            return

        with open(self.interactions_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                item = json.loads(line)
                iid = item.get("interaction_id")
                if train_ids and iid not in train_ids:
                    continue

                # Exclude golden set
                if iid in self.filter.golden_interaction_ids:
                    continue

                # Build candidate representations
                query_text = item.get("customer_message_raw", "")
                context_history = item.get("context", [])
                response_text = item.get("historical_response_raw", "")

                if self.unit_type == "unit_a":
                    # Unit A: Query only
                    searchable_text = query_text
                elif self.unit_type == "unit_c":
                    # Unit C: Full thread
                    ctx_lines = [f"{t.get('author_id', '')}: {t.get('text', '')}" for t in context_history]
                    searchable_text = "\n".join(ctx_lines + [f"Customer: {query_text}", f"AppleSupport: {response_text}"])
                elif self.unit_type == "unit_d":
                    # Unit D: Resolution snippet
                    searchable_text = f"Issue: {query_text} | Action: {response_text}"
                else:
                    # Unit B: Contextualized query (Default)
                    ctx_str = " ".join(t.get("text", "") for t in context_history[-2:])
                    searchable_text = f"{ctx_str} {query_text}".strip() if ctx_str else query_text

                candidate = {
                    "retrieval_id": f"ret_{iid}",
                    "interaction_id": iid,
                    "conversation_id": item.get("conversation_id"),
                    "created_ts": item.get("created_ts"),
                    "customer_message_raw": query_text,
                    "searchable_text": searchable_text,
                    "historical_response_raw": response_text,
                    "split": "train",
                }
                self.candidates.append(candidate)

    def __len__(self):
        return len(self.candidates)

    def get_candidate(self, idx: int) -> Dict[str, Any]:
        return self.candidates[idx]
