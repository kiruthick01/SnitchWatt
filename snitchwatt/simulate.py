"""Synthetic power-trace generator: Hamming-weight leak model + Gaussian noise.

Simplified textbook CMOS power model used to validate the TVLA analysis
logic — not a claim about real device behavior. See ROADMAP.md §5.
"""

import numpy as np


def _hamming_weight(values: np.ndarray) -> np.ndarray:
    return np.array([bin(int(v)).count("1") for v in values], dtype=float)


def simulate_traces(
    n_traces: int,
    n_samples: int,
    leak_sample: int,
    leaky: bool,
    signal_strength: float,
    noise_std: float,
    seed: int,
):
    """Simulate a fixed-vs-random TVLA trace pair.

    Group A ("fixed"): every trace uses the same fixed 8-bit intermediate
    value (0x00, the canonical TVLA fixed input). Group B ("random"): every
    trace uses a fresh uniformly random 8-bit intermediate value. If
    leaky=True, sample index `leak_sample` carries an added
    Hamming-weight-proportional component; otherwise no data-dependent
    component is added anywhere.

    Returns (traces_fixed, traces_random), each shape (n_traces, n_samples).
    """
    if not (0 <= leak_sample < n_samples):
        raise ValueError(f"leak_sample {leak_sample} out of range for n_samples {n_samples}")

    rng = np.random.default_rng(seed)

    traces_fixed = rng.normal(0.0, noise_std, size=(n_traces, n_samples))
    traces_random = rng.normal(0.0, noise_std, size=(n_traces, n_samples))

    if leaky:
        fixed_values = np.zeros(n_traces, dtype=int)
        random_values = rng.integers(0, 256, size=n_traces)

        traces_fixed[:, leak_sample] += signal_strength * _hamming_weight(fixed_values)
        traces_random[:, leak_sample] += signal_strength * _hamming_weight(random_values)

    return traces_fixed, traces_random
