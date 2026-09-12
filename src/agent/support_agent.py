"""Unified End-to-End SupportAgent Pipeline.

Combines Intent Classification, Retrieval, Template Diversification, Escalation Policy,
Grounded Response Generation, and Grounding Verification.
"""

from typing import Any, Dict, List, Optional

from src.classification.baselines import (
    LexicalKeywordClassifier,
    TFIDFLogisticRegressionClassifier,
)
from src.escalation.policy import EscalationPolicy
from src.generation.generator import GroundedResponseGenerator
from src.generation.grounding import GroundingEvaluator
from src.retrieval.filter import RetrievalFilter
from src.retrieval.rerank import TemplateDiversifier
from src.retrieval.tfidf import TFIDFRetriever


class SupportAgent:
    """Production-grade, evidence-grounded AppleSupport AI Agent."""

    def __init__(
        self,
        classifier: Optional[Any] = None,
        retriever: Optional[Any] = None,
        escalation_policy: Optional[EscalationPolicy] = None,
        generator: Optional[GroundedResponseGenerator] = None,
        grounding_evaluator: Optional[GroundingEvaluator] = None,
        diversifier: Optional[TemplateDiversifier] = None,
    ):
        self.classifier = classifier or LexicalKeywordClassifier()
        self.retriever = retriever
        self.escalation_policy = escalation_policy or EscalationPolicy()
        self.generator = generator or GroundedResponseGenerator()
        self.grounding_evaluator = grounding_evaluator or GroundingEvaluator()
        self.diversifier = diversifier or TemplateDiversifier()

    def predict(
        self,
        conversation_history: List[Dict[str, Any]],
        customer_message: str,
        query_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute full end-to-end agent decision pipeline."""
        query_meta = query_metadata.copy() if query_metadata else {}
        query_meta["customer_message_raw"] = customer_message
        query_meta.setdefault("created_ts", float("inf"))

        # 1. Intent Classification
        pred_intent, intent_conf = self.classifier.predict_single(customer_message)

        # 2. Escalation Policy Evaluation
        escalation_res = self.escalation_policy.evaluate(
            customer_query=customer_message,
            conversation_history=conversation_history,
            predicted_intent=pred_intent,
            intent_confidence=intent_conf,
        )

        # 3. Evidence Retrieval
        raw_evidence: List[Dict[str, Any]] = []
        if self.retriever:
            raw_evidence = self.retriever.retrieve(query_meta, top_k=5)

        # 4. Diversification Reranking
        diversified_evidence = self.diversifier.diversify(raw_evidence, top_k=3)

        # 5. Grounded Response Generation
        generation_res = self.generator.generate_response(
            customer_query=customer_message,
            conversation_history=conversation_history,
            predicted_intent=pred_intent,
            retrieved_evidence=diversified_evidence,
            escalation_decision=escalation_res["decision"],
        )

        # 6. Grounding Evaluation
        grounding_res = self.grounding_evaluator.evaluate_response(
            draft_response=generation_res["draft_response"],
            retrieved_evidence=diversified_evidence,
            predicted_intent=pred_intent,
        )

        return {
            "intent": pred_intent,
            "intent_confidence": round(float(intent_conf), 4),
            "escalation_decision": escalation_res["decision"],
            "escalation_reason": escalation_res["reason"],
            "retrieval_candidates": [
                {
                    "retrieval_id": c.get("retrieval_id"),
                    "interaction_id": c.get("interaction_id"),
                    "score": c.get("score", 0.0),
                    "historical_response": c.get("historical_response"),
                }
                for c in diversified_evidence
            ],
            "draft_response": generation_res["draft_response"],
            "evidence_citations": generation_res["evidence_citations"],
            "grounding_status": generation_res["grounding_status"],
            "is_grounded": grounding_res["is_grounded"],
            "safety_passed": grounding_res["safety_passed"],
            "model_metadata": {
                "agent_version": "support_agent_v1",
                "classifier_type": type(self.classifier).__name__,
                "retriever_type": type(self.retriever).__name__ if self.retriever else "None",
            },
        }
