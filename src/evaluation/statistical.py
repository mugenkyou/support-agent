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
