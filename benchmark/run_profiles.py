"""Report-card layer: run TVLA across a family of simulated device profiles
and produce a comparison table. Stands in for "test multiple real
components" until real hardware capture exists (ROADMAP.md §7, Phase 4).
"""

import os

from snitchwatt import simulate_traces, welch_t_test, evaluate_leakage

COMMON = dict(n_traces=3000, n_samples=200, leak_sample=100, seed=7)

PROFILES = [
    dict(
        name="unprotected_high_snr",
        leaky=True, signal_strength=1.5, noise_std=1.0,
        notes="Obviously broken implementation, strong leak.",
    ),
    dict(
        name="unprotected_low_snr",
        leaky=True, signal_strength=0.035, noise_std=1.0,
        notes="Borderline case: weak but real leak, tests detector sensitivity.",
    ),
    dict(
        name="masked_implementation",
        leaky=False, signal_strength=0.0, noise_std=1.0,
        notes="Clean countermeasure, no data-dependent component anywhere.",
    ),
    dict(
        name="masked_implementation_with_residual_leak",
        leaky=True, signal_strength=0.032, noise_std=1.0,
        notes="Imperfect countermeasure: small residual leak survives masking.",
    ),
]

OUT_PATH = os.path.join(os.path.dirname(__file__), "report_card.md")


def run_profile(profile):
    traces_fixed, traces_random = simulate_traces(
        n_traces=COMMON["n_traces"],
        n_samples=COMMON["n_samples"],
        leak_sample=COMMON["leak_sample"],
        leaky=profile["leaky"],
        signal_strength=profile["signal_strength"],
        noise_std=profile["noise_std"],
        seed=COMMON["seed"],
    )
    t_stats = welch_t_test(traces_fixed, traces_random)
    leaks, leak_indices, max_abs_t = evaluate_leakage(t_stats)
    return leaks, max_abs_t


def main():
    rows = []
    for profile in PROFILES:
        leaks, max_abs_t = run_profile(profile)
        rows.append((profile["name"], leaks, max_abs_t, profile["notes"]))

    lines = [
        "# Snitchwatt Report Card",
        "",
        "TVLA run across simulated device profiles "
        f"(n_traces={COMMON['n_traces']}, n_samples={COMMON['n_samples']}, "
        f"leak_sample={COMMON['leak_sample']}, seed={COMMON['seed']}).",
        "",
        "| Profile | Verdict | max \\|t\\| | Notes |",
        "|---|---|---|---|",
    ]
    for name, leaks, max_abs_t, notes in rows:
        verdict = "FLAGGED" if leaks else "PASS"
        lines.append(f"| `{name}` | {verdict} | {max_abs_t:.2f} | {notes} |")

    table = "\n".join(lines) + "\n"
    with open(OUT_PATH, "w") as f:
        f.write(table)

    print(table)
    print(f"report card saved: {OUT_PATH}")


if __name__ == "__main__":
    main()
