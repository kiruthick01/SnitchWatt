"""Welch's t-test TVLA core: two trace arrays in, t-statistics and pass/fail out."""

import numpy as np
from scipy import stats

TVLA_THRESHOLD = 4.5


def welch_t_test(traces_a: np.ndarray, traces_b: np.ndarray) -> np.ndarray:
    """Per-sample Welch's t-test between two trace sets.

    traces_a, traces_b: shape (n_traces, n_samples). n_traces may differ
    between the two groups; n_samples must match.

    Returns t-statistics, shape (n_samples,).
    """
    traces_a = np.asarray(traces_a)
    traces_b = np.asarray(traces_b)

    if traces_a.ndim != 2 or traces_b.ndim != 2:
        raise ValueError(
            f"traces must be 2D (n_traces, n_samples); got shapes "
            f"{traces_a.shape} and {traces_b.shape}"
        )
    if traces_a.shape[1] != traces_b.shape[1]:
        raise ValueError(
            f"trace length mismatch: traces_a has {traces_a.shape[1]} samples, "
            f"traces_b has {traces_b.shape[1]} samples"
        )

    t_stats, _ = stats.ttest_ind(traces_a, traces_b, axis=0, equal_var=False)
    return t_stats


def evaluate_leakage(t_stats: np.ndarray, threshold: float = TVLA_THRESHOLD):
    """Apply the TVLA pass/fail threshold to a t-statistic trace.

    Returns (leaks: bool, leak_indices: np.ndarray, max_abs_t: float).
    """
    t_stats = np.asarray(t_stats)
    abs_t = np.abs(t_stats)
    leak_indices = np.flatnonzero(abs_t > threshold)
    leaks = leak_indices.size > 0
    max_abs_t = float(np.max(abs_t)) if abs_t.size else 0.0
    return leaks, leak_indices, max_abs_t
