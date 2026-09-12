"""Statistical Uncertainty and Confidence Interval Utilities."""

import math
from typing import Any, Dict, List, Tuple
import numpy as np


def compute_bootstrap_ci(
    values: List[float],
    n_bootstrap: int = 1000,
    confidence_level: float = 0.95,
    seed: int = 42,
) -> Tuple[float, float, float]:
    """Compute mean and empirical bootstrap (alpha/2, 1-alpha/2) confidence interval."""
    if not values:
        return 0.0, 0.0, 0.0
    
    rng = np.random.RandomState(seed)
    n = len(values)
    mean_val = float(np.mean(values))
    
    if n == 1:
        return mean_val, mean_val, mean_val

    boot_means = []
    for _ in range(n_bootstrap):
        sample = rng.choice(values, size=n, replace=True)
        boot_means.append(float(np.mean(sample)))
        
    alpha = (1.0 - confidence_level) / 2.0
    lower_bound = float(np.percentile(boot_means, alpha * 100))
    upper_bound = float(np.percentile(boot_means, (1.0 - alpha) * 100))
    
    return round(mean_val, 4), round(lower_bound, 4), round(upper_bound, 4)


def compute_wilson_ci(
    successes: int,
    total: int,
    confidence_level: float = 0.95,
) -> Tuple[float, float, float]:
    """Compute Wilson score interval for binomial proportions."""
    if total <= 0:
        return 0.0, 0.0, 0.0
    
    p = successes / total
    z = 1.95996 if math.isclose(confidence_level, 0.95, abs_tol=0.01) else 1.645
    
    denominator = 1.0 + z * z / total
    centre_adjusted_probability = p + z * z / (2.0 * total)
    adjusted_std_dev = math.sqrt((p * (1.0 - p) + z * z / (4.0 * total)) / total)
    
    lower_bound = (centre_adjusted_probability - z * adjusted_std_dev) / denominator
    upper_bound = (centre_adjusted_probability + z * adjusted_std_dev) / denominator
    
    return round(p, 4), round(max(0.0, lower_bound), 4), round(min(1.0, upper_bound), 4)


def compute_paired_bootstrap_ci(
    scores_a: List[float],
    scores_b: List[float],
    n_bootstrap: int = 10000,
    confidence_level: float = 0.95,
    seed: int = 42,
) -> Dict[str, Any]:
    """Compute paired differences (A - B), mean difference, median difference, 95% paired CI, and p-value."""
    if not scores_a or len(scores_a) != len(scores_b):
        return {
            "mean_difference": 0.0,
            "median_difference": 0.0,
            "ci_95_lower": 0.0,
            "ci_95_upper": 0.0,
            "p_value": 1.0,
            "is_statistically_significant": False,
            "sample_size": 0,
        }

    diffs = np.array(scores_a, dtype=float) - np.array(scores_b, dtype=float)
    n = len(diffs)
    mean_diff = float(np.mean(diffs))
    median_diff = float(np.median(diffs))

    rng = np.random.RandomState(seed)
    boot_means = []
    for _ in range(n_bootstrap):
        sample_indices = rng.choice(n, size=n, replace=True)
        boot_means.append(float(np.mean(diffs[sample_indices])))

    alpha = (1.0 - confidence_level) / 2.0
    lower_bound = float(np.percentile(boot_means, alpha * 100))
    upper_bound = float(np.percentile(boot_means, (1.0 - alpha) * 100))

    # Two-sided empirical p-value via sign-flipping permutation test
    perm_means = []
    for _ in range(n_bootstrap):
        signs = rng.choice([-1.0, 1.0], size=n)
        perm_means.append(float(np.mean(diffs * signs)))
    
    p_val = float(np.mean(np.abs(perm_means) >= np.abs(mean_diff)))

    # CI spanning 0 means no statistically distinguishable difference at alpha=0.05
    is_sig = not (lower_bound <= 0.0 <= upper_bound) and (p_val < 0.05)

    return {
        "mean_difference": round(mean_diff, 4),
        "median_difference": round(median_diff, 4),
        "ci_95_lower": round(lower_bound, 4),
        "ci_95_upper": round(upper_bound, 4),
        "p_value": round(p_val, 4),
        "is_statistically_significant": is_sig,
        "sample_size": n,
    }
