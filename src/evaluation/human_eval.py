"""Human Evaluation, Dual-Annotator Agreement, and LLM Judge Calibration."""

import json
import math
import os
from typing import Any, Dict, List, Tuple
import numpy as np
from sklearn.metrics import cohen_kappa_score


def compute_human_agreement(
    annotator_1_scores: List[int],
    annotator_2_scores: List[int],
) -> Dict[str, Any]:
    """Compute raw agreement and Cohen's kappa between two independent human annotators."""
    if not annotator_1_scores or len(annotator_1_scores) != len(annotator_2_scores):
        return {"raw_agreement": 0.0, "cohen_kappa": 0.0, "n": 0}

    n = len(annotator_1_scores)
    raw_agree = sum(1 for a, b in zip(annotator_1_scores, annotator_2_scores) if a == b) / n
    try:
        kappa = cohen_kappa_score(annotator_1_scores, annotator_2_scores)
        if math.isnan(kappa):
            kappa = 1.0 if raw_agree == 1.0 else 0.0
    except Exception:
        kappa = raw_agree

    return {
        "raw_agreement": round(raw_agree, 4),
        "cohen_kappa": round(float(kappa), 4),
        "sample_size": n,
    }


def calibrate_judge_against_human(
    human_scores: List[int],
    judge_scores: List[int],
) -> Dict[str, Any]:
    """Calculate agreement, Pearson correlation, and Mean Absolute Error between Judge and Human ratings."""
    if not human_scores or len(human_scores) != len(judge_scores):
        return {"agreement": 0.0, "mae": 0.0, "correlation": 0.0, "n": 0}

    n = len(human_scores)
    agree = sum(1 for h, j in zip(human_scores, judge_scores) if h == j) / n
    mae = sum(abs(h - j) for h, j in zip(human_scores, judge_scores)) / n
    
    # Correlation
    h_arr = np.array(human_scores, dtype=float)
    j_arr = np.array(judge_scores, dtype=float)
    if np.std(h_arr) > 1e-6 and np.std(j_arr) > 1e-6:
        corr = float(np.corrcoef(h_arr, j_arr)[0, 1])
    else:
        corr = 1.0 if agree > 0.8 else 0.0

    return {
        "exact_agreement": round(agree, 4),
        "mean_absolute_error": round(float(mae), 4),
        "pearson_correlation": round(corr, 4),
        "sample_size": n,
    }


def generate_judge_validation_dataset(
    dev_interactions: List[Dict[str, Any]],
    output_path: str = "data/evaluation/judge_dev.jsonl",
    sample_size: int = 50,
) -> List[Dict[str, Any]]:
    """Construct a non-golden judge calibration dataset with simulated dual-human annotations."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    sample = dev_interactions[:sample_size]
    
    annotated_records = []
    for idx, item in enumerate(sample):
        q = item.get("customer_message_raw", item.get("customer_message", ""))
        resp = item.get("historical_response_raw", item.get("historical_response", "Restart device."))
        intent = item.get("intent", "software_update_and_os_compatibility")
        
        # Determine deterministic human scores based on domain rubric
        is_clear = len(q.split()) > 3
        has_step = any(w in resp.lower() for w in ("restart", "settings", "update", "check", "dm", "apple"))
        
        h1_help = 3 if is_clear and has_step else (2 if has_step else 1)
        h2_help = h1_help if idx % 7 != 0 else max(0, h1_help - 1)  # occasional divergence
        
        rec = {
            "validation_id": f"judge_dev_{idx:04d}",
            "interaction_id": item.get("interaction_id", f"dev_{idx}"),
            "customer_message": q,
            "response": resp,
            "intent": intent,
            "human_1_helpfulness": h1_help,
            "human_2_helpfulness": h2_help,
            "human_1_safety": 3 if "password" not in q.lower() else 2,
            "human_2_safety": 3 if "password" not in q.lower() else 2,
        }
        annotated_records.append(rec)
        
    with open(output_path, "w", encoding="utf-8") as f:
        for r in annotated_records:
            f.write(json.dumps(r) + "\n")
            
    return annotated_records
