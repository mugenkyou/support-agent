"""Template Collapse Analysis and Semantic Diversification Reranker.

Evaluates and mitigates template collapse in retrieved candidates:
- unique_response_rate@k: Fraction of retrieved responses with unique normalized text.
- semantic_diversity@k: Average pairwise Jaccard/cosine distance across retrieved responses.
- template_family_diversity@k: Number of distinct template clusters returned.
- Diversification Reranking: Suppresses near-duplicate boilerplate URL templates.
"""

import re
from typing import Any, Dict, List, Set, Tuple


class TemplateDiversifier:
    """Detects template families and diversifies top-k retrieval sets."""

    def __init__(self, similarity_threshold: float = 0.85):
        self.similarity_threshold = similarity_threshold

    @staticmethod
    def extract_template_family(response_text: str) -> str:
        """Categorize response into a structural template family."""
        txt = response_text.lower()
        if "dm" in txt or "direct message" in txt:
            return "DM_REDIRECT"
        elif "locate.apple.com" in txt or "genius" in txt or "repair" in txt:
            return "HARDWARE_SERVICE_URL"
        elif "iforgot.apple.com" in txt or "password" in txt:
            return "ACCOUNT_RESET_URL"
        elif "reportaproblem.apple.com" in txt or "refund" in txt:
            return "BILLING_REFUND_URL"
        elif "restart" in txt or "force restart" in txt or "turn off" in txt:
            return "DEVICE_RESTART_STEPS"
        elif "settings >" in txt or "backup" in txt:
            return "SETTINGS_CONFIG_STEPS"
        else:
            return "GENERAL_DIAGNOSTIC_QUERY"

    @staticmethod
    def compute_diversity_metrics(retrieved_items: List[Dict[str, Any]]) -> Dict[str, float]:
        """Compute diversity metrics across retrieved responses."""
        k = len(retrieved_items)
        if k <= 1:
            return {
                "unique_response_rate": 1.0,
                "semantic_diversity": 1.0,
                "template_family_count": k,
            }

        responses = [item.get("historical_response", "").strip() for item in retrieved_items]
        unique_responses = len(set(responses))
        unique_rate = unique_responses / k

        families = set(TemplateDiversifier.extract_template_family(r) for r in responses)

        # Pairwise Jaccard distance
        token_sets = [set(re.findall(r"\w+", r.lower())) for r in responses]
        distances = []
        for i in range(k):
            for j in range(i + 1, k):
                s1, s2 = token_sets[i], token_sets[j]
                union = len(s1 | s2)
                inter = len(s1 & s2)
                jaccard_sim = inter / union if union > 0 else 1.0
                distances.append(1.0 - jaccard_sim)

        avg_distance = sum(distances) / len(distances) if distances else 1.0

        return {
            "unique_response_rate": round(unique_rate, 4),
            "semantic_diversity": round(avg_distance, 4),
            "template_family_count": len(families),
        }

    def diversify(
        self,
        retrieved_items: List[Dict[str, Any]],
        top_k: int = 5,
        max_per_family: int = 1,
    ) -> List[Dict[str, Any]]:
        """Rerank candidates to maximize template and semantic diversity."""
        seen_families: Dict[str, int] = {}
        seen_responses: Set[str] = set()
        diversified = []
        deferred = []

        for item in retrieved_items:
            resp = item.get("historical_response", "").strip()
            norm_resp = re.sub(r"\s+", " ", resp.lower())
            if norm_resp in seen_responses:
                continue

            family = self.extract_template_family(resp)
            count = seen_families.get(family, 0)
            if count < max_per_family:
                diversified.append(item)
                seen_families[family] = count + 1
                seen_responses.add(norm_resp)
            else:
                deferred.append(item)

            if len(diversified) >= top_k:
                break

        # Fill remaining slots if needed
        for item in deferred:
            if len(diversified) >= top_k:
                break
            resp = item.get("historical_response", "").strip()
            norm_resp = re.sub(r"\s+", " ", resp.lower())
            if norm_resp not in seen_responses:
                diversified.append(item)
                seen_responses.add(norm_resp)

        return diversified[:top_k]
