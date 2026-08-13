"""Trace loaders — the seam where real hardware captures plug in later.

Both functions return arrays in the same (n_traces, n_samples) shape that
simulate.py produces, so the TVLA engine never needs to know the source.
"""

import csv

import numpy as np


def load_traces_npy(path: str) -> np.ndarray:
    """Load a trace set from a .npy file, shape (n_traces, n_samples)."""
    traces = np.load(path)
    if traces.ndim != 2:
        raise ValueError(f"expected 2D array (n_traces, n_samples), got shape {traces.shape}")
    return traces


def load_traces_csv(path: str) -> np.ndarray:
    """Load a trace set from a CSV file, one trace per row."""
    with open(path, newline="") as f:
        rows = list(csv.reader(f))
    traces = np.array(rows, dtype=float)
    if traces.ndim != 2:
        raise ValueError(f"expected 2D array (n_traces, n_samples), got shape {traces.shape}")
    return traces
