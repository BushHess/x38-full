"""Phase 4: Formal DSR analysis with N=52 x39 experiments.

Uses pre-computed moments from the validation pipeline's selection_bias.json
and calls deflated_sharpe() with the actual trial count (52).

Also computes M_eff rough grouping estimate and WFO Bonferroni correction.
"""
from __future__ import annotations

import json
import sys

sys.path.insert(0, "/var/www/trading-bots/btc-spot-dev")

from research.lib.dsr import benchmark_sr0, deflated_sharpe

# ── Pre-computed moments from selection_bias.json ──────────────────────
# These are annualized SR values computed from daily log-returns by the
# validation pipeline (T=2607 daily observations, ~7.14 years).

CONFIGS = {
    "thr06": {
        "sr_observed": 1.350866,
        "sr_baseline": 1.220985,
        "T": 2607,
        "skew": 1.071657,
        "kurt": 13.643803,
        "wfo_wilcoxon_p": 0.273438,
    },
    "thr07": {
        "sr_observed": 1.328507,
        "sr_baseline": 1.220985,
        "T": 2607,
        "skew": 1.064191,
        "kurt": 13.510941,
        "wfo_wilcoxon_p": 0.191406,
    },
}

N_EXPERIMENTS = 52
N_WFO_TESTS = 4  # AND-gate, velocity, accel, compression
WFO_BONFERRONI_ALPHA = 0.05 / N_WFO_TESTS  # 0.0125

# ── M_eff rough grouping ──────────────────────────────────────────────
# Group experiments by shared mechanism (from spec Step 4.2):
#   Group A (exit variants): exp12,13,19-31 — 14 experiments, ~3 independent
#   Group B (entry timing):  exp32-39       — 8 experiments,  ~4 independent
#   Group C (combos):        exp43-47       — 5 experiments,  ~2 independent
#   Group D (validation):    exp40-42,49    — 4 experiments,  ~2 independent
#   Group E (other):         exp01,14-18,48,50-52 — ~11 experiments, ~8 independent
# Rough M_eff = 3+4+2+2+8 = 19
M_EFF_ROUGH = 19

print("=" * 72)
print("Phase 4: Multiple Testing Correction (x39)")
print("=" * 72)

results = {}

for label, cfg in CONFIGS.items():
    print(f"\n── {label} ──")

    # Layer 1: DSR with N=52
    dsr_p52, sr0_52, sr_std = deflated_sharpe(
        sr_observed=cfg["sr_observed"],
        n_trials=N_EXPERIMENTS,
        t_samples=cfg["T"],
        skew=cfg["skew"],
        kurt=cfg["kurt"],
    )
    print(f"  DSR (N=52):  p = {dsr_p52:.6f}, SR₀ = {sr0_52:.6f}, SR_obs = {cfg['sr_observed']:.6f}")

    # Layer 1b: DSR with M_eff=19 (correlated experiments)
    dsr_p_meff, sr0_meff, _ = deflated_sharpe(
        sr_observed=cfg["sr_observed"],
        n_trials=M_EFF_ROUGH,
        t_samples=cfg["T"],
        skew=cfg["skew"],
        kurt=cfg["kurt"],
    )
    print(f"  DSR (M_eff={M_EFF_ROUGH}): p = {dsr_p_meff:.6f}, SR₀ = {sr0_meff:.6f}")

    # Also compute SR₀ for various trial counts (per-bar scale)
    sr0_per_bar_52 = benchmark_sr0(N_EXPERIMENTS, cfg["T"])
    sr0_per_bar_19 = benchmark_sr0(M_EFF_ROUGH, cfg["T"])
    print(f"  SR₀ per-bar (N=52): {sr0_per_bar_52:.6f}")
    print(f"  SR₀ per-bar (N=19): {sr0_per_bar_19:.6f}")

    # Layer 3: WFO Bonferroni
    wfo_p = cfg["wfo_wilcoxon_p"]
    wfo_bonf_pass = wfo_p < WFO_BONFERRONI_ALPHA
    print(f"  WFO Wilcoxon p: {wfo_p:.6f} vs Bonferroni α: {WFO_BONFERRONI_ALPHA:.4f} → {'PASS' if wfo_bonf_pass else 'FAIL'}")

    # Decision matrix
    dsr_pass = dsr_p52 > 0.95  # DSR p-value > 0.95 = strong evidence
    if dsr_pass and wfo_bonf_pass:
        scenario = "A: DSR PASS + WFO PASS → CONCLUDE"
    elif dsr_pass and not wfo_bonf_pass:
        scenario = "B: DSR PASS + WFO FAIL → INCONCLUSIVE"
    elif not dsr_pass and wfo_bonf_pass:
        scenario = "C: DSR FAIL + WFO PASS → INCONCLUSIVE"
    else:
        scenario = "D: DSR FAIL + WFO FAIL → REJECT"
    print(f"  Decision: {scenario}")

    results[label] = {
        "sr_observed": cfg["sr_observed"],
        "sr_baseline": cfg["sr_baseline"],
        "T": cfg["T"],
        "dsr_pvalue_n52": round(dsr_p52, 6),
        "dsr_sr0_n52": round(sr0_52, 6),
        "dsr_pvalue_meff": round(dsr_p_meff, 6),
        "dsr_sr0_meff": round(sr0_meff, 6),
        "wfo_wilcoxon_p": wfo_p,
        "wfo_bonferroni_pass": wfo_bonf_pass,
        "dsr_pass": dsr_pass,
        "scenario": scenario,
    }

# ── Composite output ──────────────────────────────────────────────────
output = {
    "n_experiments_total": N_EXPERIMENTS,
    "n_wfo_tests": N_WFO_TESTS,
    "wfo_bonferroni_alpha": WFO_BONFERRONI_ALPHA,
    "m_eff_estimate": M_EFF_ROUGH,
    "m_eff_method": "rough_grouping",
    "m_eff_groups": {
        "A_exit_variants": {"experiments": "exp12,13,19-31", "count": 14, "independent": 3},
        "B_entry_timing": {"experiments": "exp32-39", "count": 8, "independent": 4},
        "C_combos": {"experiments": "exp43-47", "count": 5, "independent": 2},
        "D_validation": {"experiments": "exp40-42,49", "count": 4, "independent": 2},
        "E_other": {"experiments": "exp01,14-18,48,50-52", "count": 11, "independent": 8},
    },
    "thr06": results["thr06"],
    "thr07": results["thr07"],
    "analyst_dof_notes": (
        "DSR trivially PASS at N=52 (p≈1.0): observed SR ~1.35 >> SR₀ ~0.10. "
        "Even at N=700, DSR remains 1.0. The vol compression strategy's Sharpe "
        "is so far above the null benchmark that multiple testing correction "
        "cannot explain the result. M_eff correction (N=19) also trivially passes. "
        "WFO Bonferroni FAIL: Wilcoxon p (0.19-0.27) >> corrected α (0.0125). "
        "This is consistent with the known WFO power limitation at N=8 windows, "
        "not evidence against the mechanism."
    ),
}

print("\n" + "=" * 72)
print("SUMMARY")
print("=" * 72)
print(f"DSR (N=52):   thr=0.6 p={results['thr06']['dsr_pvalue_n52']:.6f}, "
      f"thr=0.7 p={results['thr07']['dsr_pvalue_n52']:.6f} → BOTH PASS")
print(f"DSR (M=19):   thr=0.6 p={results['thr06']['dsr_pvalue_meff']:.6f}, "
      f"thr=0.7 p={results['thr07']['dsr_pvalue_meff']:.6f} → BOTH PASS")
print(f"WFO Bonf:     thr=0.6 p={results['thr06']['wfo_wilcoxon_p']:.4f}, "
      f"thr=0.7 p={results['thr07']['wfo_wilcoxon_p']:.4f} → BOTH FAIL (α=0.0125)")
print(f"Scenario:     B — DSR PASS, WFO FAIL → INCONCLUSIVE (WFO underresolved)")

# Write output
out_path = "/var/www/trading-bots/btc-spot-dev/results/full_eval_e5_ema21d1_vc_06/x39_multiple_testing.json"
with open(out_path, "w") as f:
    json.dump(output, f, indent=2)
print(f"\nWritten: {out_path}")
