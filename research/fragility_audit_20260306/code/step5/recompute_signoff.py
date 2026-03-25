#!/usr/bin/env python3
"""Recompute sign-off gates from existing Step 5 artifacts.

Fixes: tier-aware combined scenario filtering + numpy bool serialization.
No replays needed — pure arithmetic from JSON artifacts.
"""
import json
from pathlib import Path

ARTIFACT_DIR = Path("/var/www/trading-bots/btc-spot-dev/research/fragility_audit_20260306/artifacts/step5")

CANDIDATES = ["E0", "E5", "SM", "E0_plus_EMA1D21", "E5_plus_EMA1D21"]

BASELINE_METRICS = {
    "E0": {"sharpe": 1.2653, "cagr": 0.5204, "mdd": 0.4161},
    "E5": {"sharpe": 1.3573, "cagr": 0.5662, "mdd": 0.4037},
    "SM": {"sharpe": 1.4437, "cagr": 0.1600, "mdd": 0.1509},
    "E0_plus_EMA1D21": {"sharpe": 1.3249, "cagr": 0.5470, "mdd": 0.4205},
    "E5_plus_EMA1D21": {"sharpe": 1.4300, "cagr": 0.5985, "mdd": 0.4164},
}

SIGNOFF_GATES = {
    "GO": {
        "p95_delta_sharpe": -0.15,
        "p_cagr_le_0": 0.10,
        "p95_delta_mdd_frac": 0.25,
        "worst_combo_delta_sharpe": -0.20,
    },
    "GO_WITH_GUARDS": {
        "p95_delta_sharpe": -0.30,
        "p_cagr_le_0": 0.20,
        "p95_delta_mdd_frac": 0.50,
        "worst_combo_delta_sharpe": -0.35,
    },
}

TIER_MAX_DELAY = {
    "LT1": 2,
    "LT2": 4,
    "LT3": 99,
}


def recompute():
    all_signoff = {}

    for label in CANDIDATES:
        cdir = ARTIFACT_DIR / "candidates" / label
        with open(cdir / "stochastic_delay_summary.json") as f:
            stochastic = json.load(f)
        with open(cdir / "combined_disruption_summary.json") as f:
            combined = json.load(f)

        baseline_mdd = BASELINE_METRICS[label]["mdd"]
        signoff = {}

        for lt in ["LT1", "LT2", "LT3"]:
            st = stochastic.get(lt, {})
            if not st:
                signoff[lt] = {"status": "NO_GO", "reason": "no stochastic data"}
                continue

            p5_ds = st.get("delta_sharpe_p5", -999)
            p_cagr_le_0 = st.get("p_cagr_le_0", 1.0)
            p95_delta_mdd = st.get("delta_mdd_p95", 999)
            p95_delta_mdd_frac = p95_delta_mdd / baseline_mdd if baseline_mdd > 0 else 999

            # Tier-filtered worst combined disruption
            max_delay = TIER_MAX_DELAY.get(lt, 99)
            worst_combo_ds = 0.0
            for sc_name, sc_data in combined.items():
                ed = sc_data.get("entry_delay", 0)
                xd = sc_data.get("exit_delay", 0)
                if max(ed, xd) > max_delay:
                    continue
                ds = sc_data.get("delta_sharpe", 0.0)
                worst_combo_ds = min(worst_combo_ds, ds)

            gate_results = {}
            for gate_name in ["GO", "GO_WITH_GUARDS"]:
                thresholds = SIGNOFF_GATES[gate_name]
                passes = {
                    "p95_delta_sharpe": bool(p5_ds >= thresholds["p95_delta_sharpe"]),
                    "p_cagr_le_0": bool(p_cagr_le_0 <= thresholds["p_cagr_le_0"]),
                    "p95_delta_mdd_frac": bool(p95_delta_mdd_frac <= thresholds["p95_delta_mdd_frac"]),
                    "worst_combo_delta_sharpe": bool(worst_combo_ds > thresholds["worst_combo_delta_sharpe"]),
                }
                gate_results[gate_name] = {
                    "all_pass": all(passes.values()),
                    "checks": passes,
                    "values": {
                        "p95_delta_sharpe": p5_ds,
                        "p_cagr_le_0": p_cagr_le_0,
                        "p95_delta_mdd_frac": p95_delta_mdd_frac,
                        "worst_combo_delta_sharpe": worst_combo_ds,
                    },
                }

            if gate_results["GO"]["all_pass"]:
                status = "GO"
            elif gate_results["GO_WITH_GUARDS"]["all_pass"]:
                status = "GO_WITH_GUARDS"
            elif st.get("cagr_p50", 0) > 0:
                status = "HOLD"
            else:
                status = "NO_GO"

            guardrails = []
            if status == "GO_WITH_GUARDS":
                if not gate_results["GO"]["checks"]["p95_delta_sharpe"]:
                    guardrails.append(f"Sharpe degradation: p5_delta={p5_ds:.3f}")
                if not gate_results["GO"]["checks"]["p_cagr_le_0"]:
                    guardrails.append(f"P(CAGR<=0)={p_cagr_le_0:.3f}")
                if not gate_results["GO"]["checks"]["p95_delta_mdd_frac"]:
                    guardrails.append(f"MDD degradation: {p95_delta_mdd_frac:.3f}x baseline")
                if not gate_results["GO"]["checks"]["worst_combo_delta_sharpe"]:
                    guardrails.append(f"Worst combo delta_sharpe: {worst_combo_ds:.3f}")

            signoff[lt] = {
                "status": status,
                "gate_results": gate_results,
                "guardrails": guardrails,
                "metrics": {
                    "p5_delta_sharpe": p5_ds,
                    "p_cagr_le_0": p_cagr_le_0,
                    "p95_delta_mdd_frac": p95_delta_mdd_frac,
                    "worst_combo_delta_sharpe": worst_combo_ds,
                    "stochastic_sharpe_p50": st.get("sharpe_p50", 0),
                    "stochastic_cagr_p50": st.get("cagr_p50", 0),
                },
            }

        # Write updated signoff gates
        with open(cdir / "signoff_gates.json", "w") as f:
            json.dump(signoff, f, indent=2)

        all_signoff[label] = signoff
        print(f"{label}: LT1={signoff['LT1']['status']} LT2={signoff['LT2']['status']} LT3={signoff['LT3']['status']}")

    # Rewrite signoff_matrix.csv
    import csv
    rows = []
    for label in CANDIDATES:
        for lt in ["LT1", "LT2", "LT3"]:
            sg = all_signoff[label][lt]
            row = {
                "candidate": label,
                "latency_tier": lt,
                "status": sg["status"],
            }
            for mk, mv in sg["metrics"].items():
                row[mk] = f"{mv:.4f}" if isinstance(mv, float) else mv
            row["guardrails"] = "; ".join(sg.get("guardrails", []))
            rows.append(row)

    with open(ARTIFACT_DIR / "signoff_matrix.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)

    # Rewrite step5_summary.json signoff matrix
    with open(ARTIFACT_DIR / "step5_summary.json") as f:
        summary = json.load(f)
    summary["signoff_matrix"] = {
        label: {lt: all_signoff[label][lt]["status"] for lt in ["LT1", "LT2", "LT3"]}
        for label in CANDIDATES
    }
    with open(ARTIFACT_DIR / "step5_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    # Rewrite live_signoff_matrix.png
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.colors import ListedColormap

        labels_list = CANDIDATES
        tiers = ["LT1", "LT2", "LT3"]
        import numpy as np
        status_map = {"GO": 3, "GO_WITH_GUARDS": 2, "HOLD": 1, "NO_GO": 0}
        matrix = np.zeros((len(labels_list), len(tiers)))
        for i, label in enumerate(labels_list):
            for j, lt in enumerate(tiers):
                matrix[i, j] = status_map.get(all_signoff[label][lt]["status"], 0)

        fig, ax = plt.subplots(1, 1, figsize=(8, 6))
        cmap = ListedColormap(["#d62728", "#ffdd57", "#ff7f0e", "#2ca02c"])
        im = ax.imshow(matrix, cmap=cmap, vmin=0, vmax=3, aspect="auto")
        ax.set_xticks(range(len(tiers)))
        ax.set_xticklabels(tiers)
        ax.set_yticks(range(len(labels_list)))
        ax.set_yticklabels(labels_list)
        for i, label in enumerate(labels_list):
            for j, lt in enumerate(tiers):
                status = all_signoff[label][lt]["status"]
                ax.text(j, i, status, ha="center", va="center",
                        fontsize=9, fontweight="bold",
                        color="white" if status in ("GO", "NO_GO") else "black")
        ax.set_title("Live Sign-Off Matrix: Candidate x Latency Tier")
        fig.tight_layout()
        fig.savefig(ARTIFACT_DIR / "live_signoff_matrix.png", dpi=150)
        plt.close(fig)
        print("\nFigure updated.")
    except ImportError:
        pass

    print("\n=== FINAL SIGN-OFF MATRIX (CORRECTED) ===")
    print(f"{'Candidate':<25} {'LT1':<20} {'LT2':<20} {'LT3':<20}")
    print("-" * 85)
    for label in CANDIDATES:
        lt1 = all_signoff[label]["LT1"]["status"]
        lt2 = all_signoff[label]["LT2"]["status"]
        lt3 = all_signoff[label]["LT3"]["status"]
        print(f"{label:<25} {lt1:<20} {lt2:<20} {lt3:<20}")


if __name__ == "__main__":
    recompute()
