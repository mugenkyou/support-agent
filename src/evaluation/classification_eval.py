"""Classification Evaluation Harness.

Evaluates:
- Baseline 0: Majority Class
- Baseline 1: TF-IDF + Logistic Regression
- Baseline 2: Lexical / Keyword Matcher
- Baseline 3: Semantic Taxonomy Matcher
"""

import json
import os
from typing import Any, Dict, List, Tuple
from src.classification.baselines import (
    LexicalKeywordClassifier,
    MajorityClassifier,
    SemanticTaxonomyClassifier,
    TFIDFLogisticRegressionClassifier,
)
from src.classification.metrics import compute_classification_metrics
from src.taxonomy.loader import load_taxonomy


def evaluate_classifiers(
    train_data: List[Dict[str, Any]],
    eval_data: List[Dict[str, Any]],
    taxonomy_path: str = "src/taxonomy/taxonomy.yaml",
) -> Dict[str, Any]:
    taxonomy = load_taxonomy(yaml_path=taxonomy_path)
    classes = [i.name for i in taxonomy.intents]


    train_texts = [d.get("customer_message_raw", d.get("customer_message", "")) for d in train_data]
    train_labels = [d.get("intent", "software_update_and_os_compatibility") for d in train_data]

    eval_texts = [d.get("customer_message_raw", d.get("customer_message", "")) for d in eval_data]
    eval_labels = [d.get("intent", "software_update_and_os_compatibility") for d in eval_data]
    eval_metadata = [
        {
            "customer_message": t,
            "ambiguity": d.get("ambiguity", "none"),
            "is_multi_intent": d.get("is_multi_intent", False),
        }
        for t, d in zip(eval_texts, eval_data)
    ]

    results = {}

    # 1. Majority
    majority = MajorityClassifier()
    majority.fit(train_texts, train_labels)
    maj_preds = majority.predict(eval_texts)
    results["majority"] = compute_classification_metrics(eval_labels, maj_preds, classes, eval_metadata)

    # 2. TF-IDF + LogReg
    if train_texts and train_labels:
        logreg = TFIDFLogisticRegressionClassifier()
        logreg.fit(train_texts, train_labels)
        lr_preds = logreg.predict(eval_texts)
        results["tfidf_logreg"] = compute_classification_metrics(eval_labels, lr_preds, classes, eval_metadata)

    # 3. Lexical / Keyword
    keyword = LexicalKeywordClassifier()
    kw_preds = keyword.predict(eval_texts)
    results["lexical_keyword"] = compute_classification_metrics(eval_labels, kw_preds, classes, eval_metadata)

    # 4. Semantic Taxonomy
    semantic = SemanticTaxonomyClassifier(taxonomy_path)
    sem_preds = semantic.predict(eval_texts)
    results["semantic_taxonomy"] = compute_classification_metrics(eval_labels, sem_preds, classes, eval_metadata)

    return results
