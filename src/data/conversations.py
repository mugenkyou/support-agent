"""Conversation reconstruction, graph traversal, and context building."""

import sqlite3
from collections import defaultdict
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple, Any, Set

from src.data.ingest import get_db_connection, SQLITE_DB_PATH


@dataclass
class ConversationTurn:
    tweet_id: int
    author_id: str
    author_type: str  # "customer" | "support"
    inbound: bool
    created_at: str
    created_ts: int
    text: str
    in_response_to_tweet_id: Optional[int]


class ConversationGraph:
    def __init__(self, db_path: str = SQLITE_DB_PATH):
        self.db_path = db_path
        self.tweets: Dict[int, ConversationTurn] = {}
        self.parent_to_children: Dict[int, List[int]] = defaultdict(list)
        self.root_map: Dict[int, int] = {}  # tweet_id -> root_tweet_id
        self._loaded = False

    def load_graph(self, brand: str = "AppleSupport"):
        """Loads all tweets involved in conversations with the target brand."""
        if self._loaded:
            return

        conn = get_db_connection(self.db_path)
        cur = conn.cursor()

        print(f"Loading conversation graph for {brand}...")

        # 1. Fetch all brand outbound tweets and direct customer parent turns
        cur.execute("""
        SELECT tweet_id, author_id, inbound, created_at, created_ts, text, in_response_to_tweet_id
        FROM tweets
        WHERE author_id = ?
           OR tweet_id IN (
               SELECT in_response_to_tweet_id FROM tweets WHERE author_id = ? AND in_response_to_tweet_id IS NOT NULL
           )
           OR in_response_to_tweet_id IN (
               SELECT tweet_id FROM tweets WHERE author_id = ?
           )
        """, (brand, brand, brand))

        relevant_tids = set()
        for row in cur.fetchall():
            tid = int(row["tweet_id"])
            relevant_tids.add(tid)
            aid = row["author_id"]
            inb = bool(row["inbound"])
            auth_type = "support" if aid == brand else "customer"
            in_resp = int(row["in_response_to_tweet_id"]) if row["in_response_to_tweet_id"] else None

            self.tweets[tid] = ConversationTurn(
                tweet_id=tid,
                author_id=aid,
                author_type=auth_type,
                inbound=inb,
                created_at=row["created_at"],
                created_ts=int(row["created_ts"]),
                text=row["text"],
                in_response_to_tweet_id=in_resp,
            )
            if in_resp:
                self.parent_to_children[in_resp].append(tid)

        # 2. Also fetch any second-order ancestor customer turns to ensure complete root traversal
        missing_parents = set()
        for t in self.tweets.values():
            if t.in_response_to_tweet_id and t.in_response_to_tweet_id not in self.tweets:
                missing_parents.add(t.in_response_to_tweet_id)

        if missing_parents:
            # Batch fetch missing parents
            placeholders = ",".join("?" for _ in missing_parents)
            cur.execute(f"""
            SELECT tweet_id, author_id, inbound, created_at, created_ts, text, in_response_to_tweet_id
            FROM tweets WHERE tweet_id IN ({placeholders})
            """, list(missing_parents))
            for row in cur.fetchall():
                tid = int(row["tweet_id"])
                aid = row["author_id"]
                inb = bool(row["inbound"])
                auth_type = "support" if aid == brand else "customer"
                in_resp = int(row["in_response_to_tweet_id"]) if row["in_response_to_tweet_id"] else None
                self.tweets[tid] = ConversationTurn(
                    tweet_id=tid,
                    author_id=aid,
                    author_type=auth_type,
                    inbound=inb,
                    created_at=row["created_at"],
                    created_ts=int(row["created_ts"]),
                    text=row["text"],
                    in_response_to_tweet_id=in_resp,
                )
                if in_resp:
                    self.parent_to_children[in_resp].append(tid)

        # 3. Sort children deterministically using timestamp + parent edge + integer tweet_id tie-breaking rule
        for p_id, children in self.parent_to_children.items():
            children.sort(key=lambda c_id: (self.tweets[c_id].created_ts if c_id in self.tweets else 0, c_id))

        self._loaded = True
        print(f"Graph loaded with {len(self.tweets):,} total nodes.")

    def get_root_tweet_id(self, tweet_id: int) -> int:
        """Finds the root tweet ID for any tweet in a conversation tree."""
        if tweet_id in self.root_map:
            return self.root_map[tweet_id]

        curr = tweet_id
        visited = set()
        while curr in self.tweets:
            visited.add(curr)
            parent_id = self.tweets[curr].in_response_to_tweet_id
            if parent_id is None or parent_id not in self.tweets or parent_id in visited:
                break
            curr = parent_id

        for tid in visited:
            self.root_map[tid] = curr
        return curr

    def get_conversation_id(self, tweet_id: int) -> str:
        """Generates deterministic conversation ID."""
        root_id = self.get_root_tweet_id(tweet_id)
        return f"conv_{root_id}"

    def get_ancestor_path(self, target_tweet_id: int, isolate_customer: bool = True) -> List[ConversationTurn]:
        """
        Reconstructs linear causal path from root to target_tweet_id.
        Enforces:
        1. Causal order: Root -> ... -> Target
        2. Prediction-time boundary: Ancestors strictly have created_ts <= target.created_ts.
        3. Third-party isolation: Excludes tweets from other customer author_ids if isolate_customer=True.
        """
        if target_tweet_id not in self.tweets:
            return []

        target_turn = self.tweets[target_tweet_id]
        target_customer = target_turn.author_id if target_turn.author_type == "customer" else None

        path: List[ConversationTurn] = []
        curr: Optional[int] = target_tweet_id
        visited = set()

        while curr and curr in self.tweets and curr not in visited:
            visited.add(curr)
            turn = self.tweets[curr]
            # Prediction-time check: must be <= target timestamp
            if turn.created_ts <= target_turn.created_ts:
                # Third-party isolation check
                if isolate_customer and target_customer and turn.author_type == "customer":
                    if turn.author_id == target_customer:
                        path.append(turn)
                else:
                    path.append(turn)
            curr = turn.in_response_to_tweet_id

        # Path was collected backwards (target -> root), so reverse to get (root -> target)
        path.reverse()
        return path

    def build_context(
        self,
        target_customer_tweet_id: int,
        context_policy: str = "full_history",
        max_turns: Optional[int] = None,
        max_tokens: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Builds the prediction context for a customer turn.
        Excludes the target customer turn itself from 'preceding context',
        returning only the historical predecessor turns (C_1, S_1, ..., C_{k-1}, S_{k-1}).
        """
        full_path = self.get_ancestor_path(target_customer_tweet_id, isolate_customer=True)
        if not full_path:
            return []

        # Preceding turns are everything before the target turn in the path
        preceding_turns = [t for t in full_path if t.tweet_id != target_customer_tweet_id]

        if context_policy == "last_1_turn":
            # No preceding context (model only sees C_k)
            selected = []
        elif context_policy == "last_2_turns":
            # Preceding support turn S_{k-1} + C_k (so 1 prior turn)
            selected = preceding_turns[-1:] if preceding_turns else []
        elif context_policy == "last_3_turns":
            # (C_{k-1}, S_{k-1})
            selected = preceding_turns[-2:] if preceding_turns else []
        elif context_policy == "token_bounded" and max_tokens:
            # Accumulate from most recent backwards until token limit
            selected = []
            curr_tokens = 0
            for t in reversed(preceding_turns):
                est_tokens = len(t.text.split())
                if curr_tokens + est_tokens <= max_tokens:
                    selected.append(t)
                    curr_tokens += est_tokens
                else:
                    break
            selected.reverse()
        else:  # full_history
            if max_turns:
                selected = preceding_turns[-max_turns:]
            else:
                selected = preceding_turns

        return [
            {
                "tweet_id": t.tweet_id,
                "author_id": t.author_id,
                "author_type": t.author_type,
                "created_at": t.created_at,
                "created_ts": t.created_ts,
                "text": t.text,
            }
            for t in selected
        ]


if __name__ == "__main__":
    graph = ConversationGraph()
    graph.load_graph("AppleSupport")
    print(f"Sample Root for tweet 115712: {graph.get_root_tweet_id(115712)}")
