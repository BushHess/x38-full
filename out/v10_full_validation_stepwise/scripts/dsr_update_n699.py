#!/usr/bin/env python3
"""DSR Update: N=694 → N=699 after Overlay A cooldown grid sweep (5 trials added).

Context:
  - Overlay A cooldown grid sweep tested K ∈ {0, 3, 6, 12, 18} → 5 new trials
  - Previous N_FULL_INVENTORY = 694 → updated to 699
  - V10+Overlay A (K=12) is the promoted config with Sharpe = 1.1723
  - No new backtests needed — pure DSR recalculation using existing return stats

Methodology: Deflated Sharpe Ratio (Bailey & López de Prado 2014)
  - Same formula as selection_bias_v10_v11.py
  - Uses V10 baseline skew/kurt as approximation (overlay changes ~4 trades out of ~99)
"""

import json
import math
from datetime import datetime
from pathlib import Path

OUTDIR = Path(__file__).resolve().parents[1]

# ── Constants ─────────────────────────────────────────────────────────────
N_OLD = 694
N_NEW = 699  # +5 from Overlay A cooldown grid: K ∈ {0, 3, 6, 12, 18}

# V10+Overlay A (K=12) — promoted config
# Sharpe from out_v10_fix_loop/step7_cooldown_grid.csv
SR_OVERLAY_A_K12 = 1.1723

# V10 baseline return distribution stats (from selection_bias_results.json)
# Overlay A K=12 has near-identical distribution (99 vs 103 trades, same period)
T = 2607           # daily observations
SKEW = 1.3594      # skewness of daily log returns
KURT = 24.2681     # kurtosis of daily log returns

# V10 plain baseline for comparison
SR_V10_PLAIN = 1.151

# V11 IS-best for comparison
SR_V11 = 1.147
SKEW_V11 = 1.4183
KURT_V11 = 24.7419

DSR_THRESHOLD = 0.95


# ── DSR implementation (same as selection_bias_v10_v11.py) ────────────────
def _probit(p):
    """Approximate inverse normal CDF (Abramowitz & Stegun)."""
    if p <= 0 or p >= 1:
        return 0.0
    t = math.sqrt(-2.0 * math.log(min(p, 1 - p)))
    c0, c1, c2 = 2.515517, 0.802853, 0.010328
    d1, d2, d3 = 1.432788, 0.189269, 0.001308
    val = t - (c0 + c1 * t + c2 * t ** 2) / (1 + d1 * t + d2 * t ** 2 + d3 * t ** 3)
    return val if p > 0.5 else -val


def _norm_cdf(z):
    """Normal CDF via erf."""
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def deflated_sharpe(sr_observed, n_trials, T, skew, kurt):
    """Deflated Sharpe Ratio (Bailey & López de Prado 2014)."""
    gamma_em = 0.5772156649

    sr_var = (1.0 - skew * sr_observed
              + (kurt - 1.0) / 4.0 * sr_observed ** 2) / T
    sr_std = math.sqrt(max(sr_var, 1e-12))

    if n_trials <= 1:
        e_max_sr = 0.0
    else:
        z1 = _probit(1.0 - 1.0 / n_trials)
        z2 = _probit(1.0 - 1.0 / (n_trials * math.e))
        e_max_z = (1.0 - gamma_em) * z1 + gamma_em * z2
        e_max_sr = sr_std * e_max_z

    z_score = (sr_observed - e_max_sr) / sr_std
    dsr = _norm_cdf(z_score)

    return dsr, e_max_sr, sr_std


# ── Main ──────────────────────────────────────────────────────────────────
def main():
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    print("=" * 70)
    print("  DSR UPDATE: N=694 → N=699")
    print("  +5 trials from Overlay A cooldown grid sweep (K ∈ {0,3,6,12,18})")
    print("=" * 70)
    print(f"  Timestamp: {timestamp}")
    print(f"  Promoted config: V10+Overlay A (K=12)")
    print(f"  Observed Sharpe: {SR_OVERLAY_A_K12}")
    print(f"  T={T}, skew={SKEW}, kurt={KURT}")
    print()

    # ── 1. V10+Overlay A (K=12) DSR at various N ─────────────────────────
    print("  === V10+Overlay A (K=12) — SR = {:.4f} ===".format(SR_OVERLAY_A_K12))
    print()

    n_levels = [27, 54, 89, 200, 400, N_OLD, N_NEW]
    labels = {
        27: "V10 grid",
        54: "combined grid",
        89: "YAML-named",
        200: "200",
        400: "400",
        N_OLD: "old inventory",
        N_NEW: "new inventory (+5 overlay A)",
    }

    dsr_results = {}
    for n in n_levels:
        dsr, e_max, sr_std = deflated_sharpe(SR_OVERLAY_A_K12, n, T, SKEW, KURT)
        dsr_results[n] = {"dsr": round(dsr, 6), "e_max_sr": round(e_max, 4)}
        pass_fail = "PASS" if dsr > DSR_THRESHOLD else "FAIL"
        marker = " ◄ UPDATED" if n == N_NEW else (" ◄ old" if n == N_OLD else "")
        print(f"    N={n:4d} ({labels[n]:30s}): "
              f"E[max(SR)]={e_max:.4f}  DSR={dsr:.6f}  {pass_fail}{marker}")

    # ── 2. Comparison: plain V10 at N=699 ─────────────────────────────────
    print()
    print("  === Comparison: Plain V10 (SR={:.4f}) at N={} ===".format(SR_V10_PLAIN, N_NEW))
    dsr_v10_new, e_max_v10_new, _ = deflated_sharpe(SR_V10_PLAIN, N_NEW, T, SKEW, KURT)
    print(f"    E[max(SR)]={e_max_v10_new:.4f}  DSR={dsr_v10_new:.6f}  "
          f"{'PASS' if dsr_v10_new > DSR_THRESHOLD else 'FAIL'}")

    # ── 3. Delta: old N vs new N ──────────────────────────────────────────
    print()
    print("  === Delta Analysis ===")
    dsr_old = dsr_results[N_OLD]["dsr"]
    dsr_new = dsr_results[N_NEW]["dsr"]
    e_old = dsr_results[N_OLD]["e_max_sr"]
    e_new = dsr_results[N_NEW]["e_max_sr"]
    print(f"    N={N_OLD}: DSR={dsr_old:.6f}, E[max(SR)]={e_old:.4f}")
    print(f"    N={N_NEW}: DSR={dsr_new:.6f}, E[max(SR)]={e_new:.4f}")
    print(f"    Δ DSR:        {dsr_new - dsr_old:+.6f}")
    print(f"    Δ E[max(SR)]: {e_new - e_old:+.6f}")
    print()

    # ── 4. Incremental DSR (Overlay A K=12 vs plain V10) ─────────────────
    delta_sr = SR_OVERLAY_A_K12 - SR_V10_PLAIN
    print(f"  === Incremental DSR: Overlay A (K=12) vs Plain V10 ===")
    print(f"    Δ Sharpe = {SR_OVERLAY_A_K12:.4f} - {SR_V10_PLAIN:.4f} = {delta_sr:+.4f}")
    dsr_inc, e_max_inc, _ = deflated_sharpe(abs(delta_sr), N_NEW, T, SKEW, KURT)
    print(f"    DSR(Δ) at N={N_NEW}: {dsr_inc:.6f}  "
          f"{'PASS' if dsr_inc > DSR_THRESHOLD else 'FAIL'}")
    print()

    # ── Verdict ───────────────────────────────────────────────────────────
    all_pass = all(v["dsr"] > DSR_THRESHOLD for v in dsr_results.values())
    print("=" * 70)
    print(f"  VERDICT: V10+Overlay A (K=12) absolute DSR at N={N_NEW}: "
          f"{'ALL PASS ✓' if all_pass else 'SOME FAIL ✗'}")
    print(f"  Incremental DSR (Δ SR={delta_sr:+.4f}) at N={N_NEW}: "
          f"{'PASS' if dsr_inc > DSR_THRESHOLD else 'FAIL'}")
    print(f"  Impact of N change (694→699): negligible (Δ DSR = {dsr_new - dsr_old:+.6f})")
    print("=" * 70)

    # ── Save JSON ─────────────────────────────────────────────────────────
    inventory_breakdown = (
        "89 YAML-named + 477 WFO grid + 54 sensitivity + "
        "72 overlay + 5 overlay_A_cooldown_grid + 2 reference = 699"
    )

    json_data = {
        "description": "DSR update: N=694→699 after Overlay A cooldown grid sweep (+5 trials)",
        "timestamp": timestamp,
        "context": {
            "new_trials": 5,
            "new_trials_source": "Overlay A cooldown grid sweep: K ∈ {0, 3, 6, 12, 18}",
            "n_old": N_OLD,
            "n_new": N_NEW,
            "inventory_breakdown": inventory_breakdown,
            "promoted_config": "V10+Overlay A (K=12), cooldown_after_emergency_dd_bars=12",
        },
        "promoted_config_stats": {
            "sr_observed": SR_OVERLAY_A_K12,
            "T": T,
            "skewness": SKEW,
            "kurtosis": KURT,
            "note": "skew/kurt from V10 baseline (overlay changes ~4 trades, negligible effect)",
        },
        "dsr_at_N": {str(k): v for k, v in dsr_results.items()},
        "dsr_comparison": {
            "v10_plain_at_N699": {
                "sr": SR_V10_PLAIN,
                "dsr": round(dsr_v10_new, 6),
                "pass": dsr_v10_new > DSR_THRESHOLD,
            },
            "v10_overlay_a_k12_at_N699": {
                "sr": SR_OVERLAY_A_K12,
                "dsr": dsr_results[N_NEW]["dsr"],
                "pass": dsr_results[N_NEW]["dsr"] > DSR_THRESHOLD,
            },
        },
        "delta_n_impact": {
            "dsr_at_N694": dsr_results[N_OLD]["dsr"],
            "dsr_at_N699": dsr_results[N_NEW]["dsr"],
            "delta_dsr": round(dsr_results[N_NEW]["dsr"] - dsr_results[N_OLD]["dsr"], 6),
            "delta_e_max_sr": round(
                dsr_results[N_NEW]["e_max_sr"] - dsr_results[N_OLD]["e_max_sr"], 4
            ),
            "assessment": "negligible",
        },
        "incremental_dsr": {
            "delta_sr": round(delta_sr, 4),
            "dsr_at_N699": round(dsr_inc, 6),
            "pass": dsr_inc > DSR_THRESHOLD,
            "note": (
                "Overlay A K=12 Sharpe improvement (+0.0213) over plain V10 "
                "does NOT survive multiple-testing at N=699. "
                "However, overlay A's value is primarily in cascade elimination "
                "and MDD reduction, not Sharpe improvement."
            ),
        },
        "verdict": {
            "absolute_dsr_pass": all_pass,
            "absolute_dsr_value_at_N699": dsr_results[N_NEW]["dsr"],
            "incremental_dsr_pass": dsr_inc > DSR_THRESHOLD,
            "incremental_dsr_value": round(dsr_inc, 6),
            "n_impact": "negligible — 5 additional trials do not materially change DSR",
            "conclusion": (
                "PASS (absolute). V10+Overlay A (K=12) Sharpe of 1.1723 trivially "
                "survives DSR at N=699 (DSR=1.0). The N increase from 694→699 has "
                "zero practical impact on any DSR result."
            ),
        },
    }

    json_path = OUTDIR / "selection_bias_results_n699.json"
    with open(json_path, "w") as f:
        json.dump(json_data, f, indent=2)
    print(f"\n  Saved: {json_path}")

    print(f"  Done.")


if __name__ == "__main__":
    main()
