"""Comprehensive Evaluation Metrics for Intent Classification.

Calculates:
- Overall Accuracy
- Macro F1, Macro Precision, Macro Recall
- Weighted F1, Weighted Precision, Weighted Recall
- Per-Intent Precision, Recall, F1, Support
- Confusion Matrix
- Subgroup Slice Evaluations:
  - By Customer Message Length (Short, Medium, Long)
  - By Ambiguity Level (none, low, medium, high)
  - By Intent Frequency (Head, Torso, Tail)
"""

from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional, Tuple
import numpy as np


def compute_classification_metrics(
    y_true: List[str],
    y_pred: List[str],
    classes: List[str],
    metadata_list: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Compute detailed evaluation metrics across classes and slices."""
    assert len(y_true) == len(y_pred), "y_true and y_pred must have identical length"
    n_samples = len(y_true)
    if n_samples == 0:
        return {"accuracy": 0.0, "macro_f1": 0.0, "total_samples": 0}

    # Accuracy
    correct = sum(1 for yt, yp in zip(y_true, y_pred) if yt == yp)
    accuracy = correct / n_samples

    # Confusion matrix
    class_to_idx = {c: i for i, c in enumerate(classes)}
    cm = np.zeros((len(classes), len(classes)), dtype=int)
    for yt, yp in zip(y_true, y_pred):
        if yt in class_to_idx and yp in class_to_idx:
            cm[class_to_idx[yt]][class_to_idx[yp]] += 1

    # Per-class metrics
    per_class: Dict[str, Dict[str, float]] = {}
    macro_p, macro_r, macro_f1 = 0.0, 0.0, 0.0
    weighted_p, weighted_r, weighted_f1 = 0.0, 0.0, 0.0

    for idx, c in enumerate(classes):
        tp = cm[idx, idx]
        fp = cm[:, idx].sum() - tp
        fn = cm[idx, :].sum() - tp
        support = cm[idx, :].sum()

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

        per_class[c] = {
            "precision": round(float(precision), 4),
            "recall": round(float(recall), 4),
            "f1_score": round(float(f1), 4),
            "support": int(support),
        }

        macro_p += precision
        macro_r += recall
        macro_f1 += f1

        weighted_p += precision * support
        weighted_r += recall * support
        weighted_f1 += f1 * support

    num_classes = len(classes)
    macro_metrics = {
        "accuracy": round(float(accuracy), 4),
        "macro_precision": round(float(macro_p / num_classes), 4),
        "macro_recall": round(float(macro_r / num_classes), 4),
        "macro_f1": round(float(macro_f1 / num_classes), 4),
        "weighted_precision": round(float(weighted_p / n_samples), 4),
        "weighted_recall": round(float(weighted_r / n_samples), 4),
        "weighted_f1": round(float(weighted_f1 / n_samples), 4),
        "total_samples": int(n_samples),
        "per_class": per_class,
        "confusion_matrix": cm.tolist(),
        "classes": classes,
    }

    # Slice evaluation if metadata provided
    if metadata_list and len(metadata_list) == n_samples:
        macro_metrics["slices"] = _compute_slice_metrics(y_true, y_pred, metadata_list)

    return macro_metrics


def _compute_slice_metrics(
    y_true: List[str],
    y_pred: List[str],
    metadata_list: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Compute performance sliced by message length, ambiguity, and multi-intent."""
    slices: Dict[str, Any] = {
        "by_length": {},
        "by_ambiguity": {},
        "by_multi_intent": {},
    }

    # Length slices
    length_buckets = {"short (<50 chars)": [], "medium (50-150 chars)": [], "long (>150 chars)": []}
    ambiguity_buckets = defaultdict(list)
    multi_intent_buckets = {"single_intent": [], "multi_intent": []}

    for yt, yp, meta in zip(y_true, y_pred, metadata_list):
        text = meta.get("customer_message", meta.get("text", ""))
        length = len(text)
        if length < 50:
            length_buckets["short (<50 chars)"].append((yt, yp))
        elif length <= 150:
            length_buckets["medium (50-150 chars)"].append((yt, yp))
        else:
            length_buckets["long (>150 chars)"].append((yt, yp))

        ambiguity = meta.get("ambiguity", "none")
        ambiguity_buckets[ambiguity].append((yt, yp))

        is_multi = meta.get("is_multi_intent", False)
        if is_multi:
            multi_intent_buckets["multi_intent"].append((yt, yp))
        else:
            multi_intent_buckets["single_intent"].append((yt, yp))

    for name, pairs in length_buckets.items():
        if pairs:
            acc = sum(1 for yt, yp in pairs if yt == yp) / len(pairs)
            slices["by_length"][name] = {"accuracy": round(acc, 4), "count": len(pairs)}

    for name, pairs in ambiguity_buckets.items():
        if pairs:
            acc = sum(1 for yt, yp in pairs if yt == yp) / len(pairs)
            slices["by_ambiguity"][name] = {"accuracy": round(acc, 4), "count": len(pairs)}

    for name, pairs in multi_intent_buckets.items():
        if pairs:
            acc = sum(1 for yt, yp in pairs if yt == yp) / len(pairs)
            slices["by_multi_intent"][name] = {"accuracy": round(acc, 4), "count": len(pairs)}

    return slices
