"""Turn TVLA output into a plot and/or a human-readable summary. No statistics here."""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from snitchwatt.tvla import TVLA_THRESHOLD


def plot_tvla(t_stats: np.ndarray, title: str, out_path: str, threshold: float = TVLA_THRESHOLD):
    """Plot the t-statistic trace with horizontal threshold lines at ±threshold."""
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(t_stats, linewidth=0.8, color="tab:blue")
    ax.axhline(threshold, color="red", linestyle="--", linewidth=1)
    ax.axhline(-threshold, color="red", linestyle="--", linewidth=1)
    ax.set_xlabel("Sample index")
    ax.set_ylabel("t-statistic")
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def summarize(name: str, leaks: bool, leak_indices: np.ndarray, max_abs_t: float) -> str:
    """Short human-readable pass/fail text report."""
    verdict = "LEAK DETECTED" if leaks else "no leakage detected"
    lines = [
        f"{name}: {verdict}",
        f"  max |t| = {max_abs_t:.2f} (threshold = {TVLA_THRESHOLD})",
    ]
    if leaks:
        n = len(leak_indices)
        preview = ", ".join(str(i) for i in leak_indices[:10])
        if n > 10:
            preview += f", ... ({n} total)"
        lines.append(f"  leaking sample indices: {preview}")
    return "\n".join(lines)
