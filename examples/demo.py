"""End-to-end demo: simulate a leaky profile and a protected profile, run
TVLA on both, save plots to examples/output/, print both summaries.
"""

import os

from snitchwatt import simulate_traces, welch_t_test, evaluate_leakage, plot_tvla, summarize

OUT_DIR = os.path.join(os.path.dirname(__file__), "output")

PROFILES = [
    dict(name="leaky_unprotected", leaky=True),
    dict(name="protected_masked", leaky=False),
]

COMMON = dict(n_traces=2000, n_samples=200, leak_sample=100, signal_strength=1.5, noise_std=1.0, seed=42)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    for profile in PROFILES:
        name = profile["name"]
        traces_fixed, traces_random = simulate_traces(
            n_traces=COMMON["n_traces"],
            n_samples=COMMON["n_samples"],
            leak_sample=COMMON["leak_sample"],
            leaky=profile["leaky"],
            signal_strength=COMMON["signal_strength"],
            noise_std=COMMON["noise_std"],
            seed=COMMON["seed"],
        )

        t_stats = welch_t_test(traces_fixed, traces_random)
        leaks, leak_indices, max_abs_t = evaluate_leakage(t_stats)

        out_path = os.path.join(OUT_DIR, f"{name}.png")
        plot_tvla(t_stats, title=f"TVLA — {name}", out_path=out_path)

        print(summarize(name, leaks, leak_indices, max_abs_t))
        print(f"  plot saved: {out_path}\n")


if __name__ == "__main__":
    main()
