import numpy as np
import pytest

from snitchwatt.tvla import welch_t_test, evaluate_leakage, TVLA_THRESHOLD
from snitchwatt.simulate import simulate_traces


def test_identical_distributions_no_leak():
    rng = np.random.default_rng(0)
    a = rng.normal(0.0, 1.0, size=(500, 200))
    b = rng.normal(0.0, 1.0, size=(500, 200))
    t_stats = welch_t_test(a, b)
    leaks, leak_indices, max_abs_t = evaluate_leakage(t_stats)
    assert leaks is False
    assert leak_indices.size == 0


def test_injected_mean_difference_detected():
    rng = np.random.default_rng(1)
    a = rng.normal(0.0, 1.0, size=(500, 200))
    b = rng.normal(0.0, 1.0, size=(500, 200))
    leak_index = 42
    a[:, leak_index] += 5.0  # large, obvious mean shift
    t_stats = welch_t_test(a, b)
    leaks, leak_indices, max_abs_t = evaluate_leakage(t_stats)
    assert leaks is True
    assert leak_index in leak_indices
    assert max_abs_t > TVLA_THRESHOLD


def test_mismatched_sample_length_raises():
    a = np.zeros((10, 50))
    b = np.zeros((10, 60))
    with pytest.raises(ValueError):
        welch_t_test(a, b)


def test_non_2d_input_raises():
    a = np.zeros(50)
    b = np.zeros((10, 50))
    with pytest.raises(ValueError):
        welch_t_test(a, b)


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_simulate_shapes(seed):
    a, b = simulate_traces(
        n_traces=200, n_samples=100, leak_sample=10,
        leaky=True, signal_strength=1.0, noise_std=1.0, seed=seed,
    )
    assert a.shape == (200, 100)
    assert b.shape == (200, 100)


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_simulate_leaky_profile_detected(seed):
    a, b = simulate_traces(
        n_traces=1000, n_samples=100, leak_sample=10,
        leaky=True, signal_strength=1.0, noise_std=1.0, seed=seed,
    )
    t_stats = welch_t_test(a, b)
    leaks, leak_indices, _ = evaluate_leakage(t_stats)
    assert leaks is True
    assert 10 in leak_indices


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_simulate_protected_profile_clean(seed):
    a, b = simulate_traces(
        n_traces=1000, n_samples=100, leak_sample=10,
        leaky=False, signal_strength=1.0, noise_std=1.0, seed=seed,
    )
    t_stats = welch_t_test(a, b)
    leaks, leak_indices, _ = evaluate_leakage(t_stats)
    assert leaks is False
