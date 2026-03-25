"""
Step 4 — Final Synthesis and Decision Memo
Generates recommendation_map.png and latency_regime_recommendation.png
from the pre-computed decision artifacts.

All data values are hard-coded from Steps 0-3 artifacts.
No backtests or replays are run.
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import os

ARTIFACTS = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "artifacts", "step4",
)
os.makedirs(ARTIFACTS, exist_ok=True)


# ── Figure 1: Recommendation Map ──────────────────────────────────────

def fig_recommendation_map():
    """
    mandate x latency matrix as a color-coded heatmap with candidate labels.
    """
    mandates = ["M1\nReturn-seeking", "M2\nBalanced", "M3\nResilience-first"]
    latencies = ["LT1\n<4h auto", "LT2\n4-16h degraded", "LT3\n>16h manual"]

    # primary candidate per cell
    primary = [
        ["E5_plus_EMA1D21", "E0",            "SM"],
        ["E0_plus_EMA1D21", "E0",            "SM"],
        ["SM",               "SM",            "SM"],
    ]
    secondary = [
        ["E5",               "E0_plus_EMA1D21", "LATCH"],
        ["E5",               "E0_plus_EMA1D21", "LATCH"],
        ["LATCH",            "LATCH",            "LATCH"],
    ]

    # color map: binary=blue, vol-target=green
    colors = {
        "E0": "#4A90D9",
        "E5": "#2E6EB5",
        "E0_plus_EMA1D21": "#7EB3E0",
        "E5_plus_EMA1D21": "#1A4D8F",
        "SM": "#5CB85C",
        "LATCH": "#8FCC8F",
    }

    fig, ax = plt.subplots(figsize=(10, 6))
    for i, m in enumerate(mandates):
        for j, lt in enumerate(latencies):
            p = primary[i][j]
            s = secondary[i][j]
            rect = mpatches.FancyBboxPatch(
                (j - 0.45, 2 - i - 0.4), 0.9, 0.8,
                boxstyle="round,pad=0.05",
                facecolor=colors[p], alpha=0.7, edgecolor="black", linewidth=1.5,
            )
            ax.add_patch(rect)
            ax.text(j, 2 - i + 0.12, p.replace("_plus_", "+\n"),
                    ha="center", va="center", fontsize=9, fontweight="bold", color="white")
            ax.text(j, 2 - i - 0.18, f"alt: {s.replace('_plus_', '+')}",
                    ha="center", va="center", fontsize=7, color="#DDDDDD")

    ax.set_xlim(-0.6, 2.6)
    ax.set_ylim(-0.6, 2.6)
    ax.set_xticks(range(3))
    ax.set_xticklabels(latencies, fontsize=10)
    ax.set_yticks(range(3))
    ax.set_yticklabels(list(reversed(mandates)), fontsize=10)
    ax.set_xlabel("Latency Tier", fontsize=12, fontweight="bold")
    ax.set_ylabel("Mandate", fontsize=12, fontweight="bold")
    ax.set_title("Step 4 — Mandate x Latency Recommendation Map", fontsize=14, fontweight="bold")
    ax.set_facecolor("#F5F5F5")

    # legend
    binary_patch = mpatches.Patch(color="#2E6EB5", label="Binary (E0-class)")
    voltgt_patch = mpatches.Patch(color="#5CB85C", label="Vol-target (SM/LATCH)")
    ax.legend(handles=[binary_patch, voltgt_patch], loc="lower right", fontsize=9)

    plt.tight_layout()
    plt.savefig(os.path.join(ARTIFACTS, "recommendation_map.png"), dpi=150)
    plt.close()
    print(f"  Wrote recommendation_map.png")


# ── Figure 2: Latency Regime Recommendation ───────────────────────────

def fig_latency_regime():
    """
    Sharpe degradation under delay for all 6 candidates,
    with latency tier boundaries overlaid.
    """
    delays = [0, 1, 2, 3, 4]

    # from Step 3 delay_cross_summary.csv
    sharpe = {
        "E0":              [1.138, 1.106, 0.938, 0.887, 0.802],
        "E5":              [1.230, 1.178, 0.933, 0.866, 0.776],
        "SM":              [0.816, 0.849, 0.828, 0.796, 0.783],
        "LATCH":           [0.825, 0.857, 0.839, 0.802, 0.792],
        "E0_plus_EMA1D21": [1.175, 1.128, 0.973, 0.885, 0.803],
        "E5_plus_EMA1D21": [1.270, 1.189, 0.961, 0.851, 0.753],
    }

    colors_line = {
        "E0": "#4A90D9",
        "E5": "#2E6EB5",
        "SM": "#5CB85C",
        "LATCH": "#8FCC8F",
        "E0_plus_EMA1D21": "#7EB3E0",
        "E5_plus_EMA1D21": "#1A4D8F",
    }
    styles = {
        "E0": "-",
        "E5": "--",
        "SM": "-",
        "LATCH": "--",
        "E0_plus_EMA1D21": "-.",
        "E5_plus_EMA1D21": ":",
    }

    fig, ax = plt.subplots(figsize=(10, 6))
    for cand, vals in sharpe.items():
        ax.plot(delays, vals, styles[cand], color=colors_line[cand],
                linewidth=2, marker="o", markersize=5, label=cand)

    # LT boundaries
    ax.axvspan(0, 1, alpha=0.08, color="green", label="LT1 (<4h)")
    ax.axvspan(1, 4, alpha=0.06, color="orange", label="LT2 (4-16h)")
    ax.axvline(1, color="green", linestyle=":", alpha=0.5)
    ax.axvline(4, color="red", linestyle=":", alpha=0.5)
    ax.text(0.5, 0.72, "LT1", ha="center", fontsize=11, color="green", fontweight="bold")
    ax.text(2.5, 0.72, "LT2", ha="center", fontsize=11, color="orange", fontweight="bold")
    ax.text(4.3, 0.72, "LT3", ha="center", fontsize=11, color="red", fontweight="bold")

    ax.set_xlabel("Entry Delay (H4 bars)", fontsize=12, fontweight="bold")
    ax.set_ylabel("Sharpe Ratio", fontsize=12, fontweight="bold")
    ax.set_title("Step 4 — Sharpe vs Entry Delay with Latency Tier Boundaries", fontsize=13, fontweight="bold")
    ax.set_xticks(delays)
    ax.set_xticklabels(["0\n(baseline)", "1\n(4h)", "2\n(8h)", "3\n(12h)", "4\n(16h)"])
    ax.legend(fontsize=8, loc="upper right", ncol=2)
    ax.grid(True, alpha=0.3)
    ax.set_ylim(0.7, 1.35)

    plt.tight_layout()
    plt.savefig(os.path.join(ARTIFACTS, "latency_regime_recommendation.png"), dpi=150)
    plt.close()
    print(f"  Wrote latency_regime_recommendation.png")


if __name__ == "__main__":
    print("Step 4 — Generating figures...")
    fig_recommendation_map()
    fig_latency_regime()
    print("Done.")
