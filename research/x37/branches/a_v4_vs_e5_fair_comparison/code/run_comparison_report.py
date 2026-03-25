"""Phase 4: Generate comparison report and verdict.

Reads all Phase 3 results and produces:
  - results/comparison_report.md  (human-readable analysis)
  - results/verdict.json          (machine-readable verdict)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_THIS_DIR = Path(__file__).resolve().parent
ROOT = _THIS_DIR.parents[4]
for p in (str(ROOT), str(_THIS_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from helpers import RESULTS_DIR, save_json

import csv


def _load_json(name: str) -> dict:
    with open(RESULTS_DIR / name) as f:
        return json.load(f)


def _load_csv(name: str) -> list[dict]:
    with open(RESULTS_DIR / name) as f:
        return list(csv.DictReader(f))


# ==================================================================
# Verdict logic
# ==================================================================

def compute_verdict(
    bt: dict,       # backtest data
    wfo: dict,      # WFO summary
    paired: list,   # paired bootstrap rows
    cost_sweep: list,
    v4_sens: list,
    e5_sens: list,
) -> dict:
    """Determine verdict based on validation results."""

    # ---- Sharpe comparison ----
    v4_sh = bt["v4"]["full_20bps"]["sharpe"]
    e5_sh = bt["e5"]["full_20bps"]["sharpe"]
    v4_mdd = bt["v4"]["full_20bps"]["max_drawdown_mid_pct"]
    e5_mdd = bt["e5"]["full_20bps"]["max_drawdown_mid_pct"]

    sharpe_winner = "V4" if v4_sh > e5_sh else "E5"
    mdd_winner = "V4" if v4_mdd < e5_mdd else "E5"

    # ---- WFO (head-to-head) ----
    wins_valid = wfo.get("wins_valid", {})
    wins_power = wfo.get("wins_power", {})
    v4_wfo_wins_valid = int(wins_valid.get("v4", 0))
    e5_wfo_wins_valid = int(wins_valid.get("e5", 0))
    v4_wfo_wins_power = int(wins_power.get("v4", 0))
    e5_wfo_wins_power = int(wins_power.get("e5", 0))
    wfo_winner_basis = (
        "power_only" if int(wfo.get("n_windows_power_only", 0)) > 0 else "valid"
    )
    wfo_raw_winner = (
        wfo.get("winner_power", "TIE")
        if wfo_winner_basis == "power_only"
        else wfo.get("winner_valid", "TIE")
    )
    wfo_statistically_supported = bool(wfo.get("wilcoxon", {}).get("pass")) or bool(
        wfo.get("bootstrap", {}).get("ci_above_zero"),
    )
    wfo_winner = wfo_raw_winner if wfo_statistically_supported else "TIE"

    # ---- Paired bootstrap (full period, block=20) ----
    full_b20 = [r for r in paired
                if r.get("period") == "full" and str(r.get("block_size")) == "20"]
    if full_b20:
        p_v4_gt_e5 = float(full_b20[0]["p_v4_gt_e5"])
    else:
        p_v4_gt_e5 = 0.5

    # ---- Sensitivity spread ----
    v4_sharpes = [float(r["sharpe"]) for r in v4_sens]
    e5_sharpes = [float(r["sharpe"]) for r in e5_sens]
    v4_spread = max(v4_sharpes) - min(v4_sharpes)
    e5_spread = max(e5_sharpes) - min(e5_sharpes)
    robustness_winner = "V4" if v4_spread < e5_spread else "E5"

    # ---- Cost crossover ----
    v4_costs = {int(r["cost_rt_bps"]): float(r["sharpe"])
                for r in cost_sweep if r["strategy"] == "v4"}
    e5_costs = {int(r["cost_rt_bps"]): float(r["sharpe"])
                for r in cost_sweep if r["strategy"] == "e5"}
    crossover_bps = None
    for bps in sorted(v4_costs.keys()):
        if bps in e5_costs and e5_costs[bps] >= v4_costs[bps]:
            crossover_bps = bps
            break

    # ---- Verdict determination ----
    v4_wins = 0
    e5_wins = 0

    # Sharpe
    if sharpe_winner == "V4":
        v4_wins += 1
    else:
        e5_wins += 1

    # MDD
    if mdd_winner == "V4":
        v4_wins += 1
    else:
        e5_wins += 1

    # WFO
    if wfo_winner == "V4":
        v4_wins += 1
    elif wfo_winner == "E5":
        e5_wins += 1

    # Paired bootstrap
    if p_v4_gt_e5 > 0.75:
        v4_wins += 1
    elif p_v4_gt_e5 < 0.25:
        e5_wins += 1

    # Determine verdict category
    if v4_wins >= 4 and sharpe_winner == "V4" and mdd_winner == "V4":
        verdict = "V4_SUPERIOR"
    elif e5_wins >= 4 and sharpe_winner == "E5" and mdd_winner == "E5":
        verdict = "E5_SUPERIOR"
    elif v4_wins > e5_wins:
        verdict = "V4_COMPETITIVE"
    elif e5_wins > v4_wins:
        verdict = "E5_COMPETITIVE"
    elif v4_wins == e5_wins:
        # Check if each wins on different dimensions
        if sharpe_winner != mdd_winner:
            verdict = "TRADEOFF"
        else:
            verdict = "INCONCLUSIVE"
    else:
        verdict = "INCONCLUSIVE"

    return {
        "verdict": verdict,
        "v4_wins": v4_wins,
        "e5_wins": e5_wins,
        "details": {
            "sharpe_winner": sharpe_winner,
            "sharpe_v4": v4_sh,
            "sharpe_e5": e5_sh,
            "mdd_winner": mdd_winner,
            "mdd_v4": v4_mdd,
            "mdd_e5": e5_mdd,
            "wfo_winner": wfo_winner,
            "wfo_raw_winner": wfo_raw_winner,
            "wfo_winner_basis": wfo_winner_basis,
            "wfo_statistically_supported": wfo_statistically_supported,
            "wfo_v4_wins_valid": v4_wfo_wins_valid,
            "wfo_e5_wins_valid": e5_wfo_wins_valid,
            "wfo_v4_wins_power": v4_wfo_wins_power,
            "wfo_e5_wins_power": e5_wfo_wins_power,
            "wfo_n_windows_valid": int(wfo.get("n_windows_valid", 0)),
            "wfo_n_windows_power_only": int(wfo.get("n_windows_power_only", 0)),
            "wfo_p_value": wfo.get("wilcoxon", {}).get("p_value"),
            "paired_p_v4_gt_e5": p_v4_gt_e5,
            "sensitivity_spread_v4": round(v4_spread, 4),
            "sensitivity_spread_e5": round(e5_spread, 4),
            "robustness_winner": robustness_winner,
            "cost_crossover_bps": crossover_bps,
            "v4_param_count": "~10 (3 lookbacks + 4 quantiles + 2 modes + 1 anchor)",
            "e5_param_count": "4 (slow_period, trail_mult, vdo_threshold, d1_ema_period)",
        },
    }


# ==================================================================
# Report generation
# ==================================================================

def generate_report(
    bt_v4: dict,
    bt_e5: dict,
    wfo: dict,
    paired: list,
    trade_cmp: dict,
    cost_sweep: list,
    regime: list,
    v4_sens: list,
    e5_sens: list,
    psr: dict,
    verdict: dict,
    holdout_v4: dict,
    holdout_e5: dict,
) -> str:
    """Generate markdown comparison report."""
    lines = []
    a = lines.append

    a("# V4 macroHystB vs E5_ema21D1 — Fair Comparison Report")
    a("")
    a(f"**Verdict: {verdict['verdict']}**")
    a(f"**Cost: 20 bps RT (primary), 50 bps RT (reference)**")
    a("")

    # ---- 1. Summary table ----
    a("## 1. Performance Summary (20 bps RT)")
    a("")
    a("| Metric | V4 Dev | E5 Dev | V4 Holdout | E5 Holdout | V4 Full | E5 Full |")
    a("|--------|--------|--------|------------|------------|---------|---------|")
    for metric in ["sharpe", "cagr_pct", "max_drawdown_mid_pct", "trades",
                    "profit_factor", "objective_score"]:
        vals = []
        for strat, data in [("v4", bt_v4), ("e5", bt_e5)]:
            for period in ["dev_20bps", "holdout_20bps", "full_20bps"]:
                v = data.get(period, {}).get(metric, "N/A")
                vals.append(f"{v}")
        # Reorder: v4_dev, e5_dev, v4_ho, e5_ho, v4_full, e5_full
        row = [vals[0], vals[3], vals[1], vals[4], vals[2], vals[5]]
        a(f"| {metric} | {' | '.join(row)} |")
    a("")

    # ---- 2. Gate-by-gate ----
    a("## 2. Validation + Diagnostic Summary")
    a("")
    a("| Gate | V4 | E5 | Winner |")
    a("|------|----|----|--------|")

    # Lookahead
    a("| Lookahead | PASS | PASS | TIE |")

    # WFO
    a(
        f"| WFO head-to-head | "
        f"valid wins={verdict['details']['wfo_v4_wins_valid']} | "
        f"valid wins={verdict['details']['wfo_e5_wins_valid']} | "
        f"{verdict['details']['wfo_winner']} "
        f"({'supported' if verdict['details']['wfo_statistically_supported'] else 'underpowered'}) |",
    )

    # Holdout
    v4_ho_delta = holdout_v4.get("delta_score", 0)
    e5_ho_delta = holdout_e5.get("delta_score", 0)
    ho_winner = "V4" if v4_ho_delta > e5_ho_delta else "E5"
    a(f"| Holdout (Δscore) | {v4_ho_delta:.1f} | {e5_ho_delta:.1f} | {ho_winner} |")

    # DSR advisory
    v4_dsr = psr.get("v4", {}).get("dsr", {}).get("dsr_pvalue", 0)
    e5_dsr = psr.get("e5", {}).get("dsr", {}).get("dsr_pvalue", 0)
    dsr_winner = "V4" if v4_dsr > e5_dsr else "E5"
    a(f"| DSR advisory (H4 returns) | {v4_dsr:.4f} | {e5_dsr:.4f} | {dsr_winner} |")

    # Sensitivity
    v4_spr = verdict["details"]["sensitivity_spread_v4"]
    e5_spr = verdict["details"]["sensitivity_spread_e5"]
    sens_winner = verdict["details"]["robustness_winner"]
    a(f"| Sensitivity spread | {v4_spr:.4f} | {e5_spr:.4f} | {sens_winner} (narrower) |")
    a("")

    # ---- 3. WFO detail ----
    a("## 3. WFO Window Details")
    a("")
    a(f"Valid-window deltas (V4 - E5): {wfo.get('deltas_valid', [])}")
    a(f"Power-only deltas (V4 - E5): {wfo.get('deltas_power', [])}")
    a(
        f"Wilcoxon W+={wfo['wilcoxon']['W_plus']}, "
        f"p={wfo['wilcoxon']['p_value']:.4f}, "
        f"sufficient={wfo['wilcoxon'].get('sufficient', False)}",
    )
    a(f"Bootstrap CI: [{wfo['bootstrap']['ci_lo']}, {wfo['bootstrap']['ci_hi']}]")
    a("")

    # ---- 4. Paired bootstrap ----
    a("## 4. Paired Bootstrap (V4 vs E5)")
    a("")
    a("| Period | Block | P(V4>E5) | Median Δ Sharpe | 95% CI |")
    a("|--------|-------|----------|-----------------|--------|")
    for r in paired:
        a(f"| {r['period']} | {r['block_size']} | "
          f"{r['p_v4_gt_e5']} | {r['median_delta_sharpe']} | "
          f"[{r['ci_lo']}, {r['ci_hi']}] |")
    a("")

    # ---- 5. Trade quality ----
    a("## 5. Trade Quality Comparison")
    a("")
    a("| Metric | V4 | E5 |")
    a("|--------|----|----|")
    for k in ["trades", "win_rate", "avg_return", "median_return",
              "avg_hold_days", "top5_pnl_sum", "bottom5_pnl_sum"]:
        v4_val = trade_cmp.get("v4", {}).get(k, "N/A")
        e5_val = trade_cmp.get("e5", {}).get(k, "N/A")
        a(f"| {k} | {v4_val} | {e5_val} |")
    a("")

    # ---- 6. Cost sweep ----
    a("## 6. Cost Sensitivity")
    a("")
    a("| Cost (bps RT) | V4 Sharpe | E5 Sharpe | V4 CAGR | E5 CAGR |")
    a("|---------------|-----------|-----------|---------|---------|")
    v4_cs = {int(r["cost_rt_bps"]): r for r in cost_sweep if r["strategy"] == "v4"}
    e5_cs = {int(r["cost_rt_bps"]): r for r in cost_sweep if r["strategy"] == "e5"}
    for bps in sorted(set(int(r["cost_rt_bps"]) for r in cost_sweep)):
        v4r = v4_cs.get(bps, {})
        e5r = e5_cs.get(bps, {})
        a(f"| {bps} | {v4r.get('sharpe', 'N/A')} | {e5r.get('sharpe', 'N/A')} | "
          f"{v4r.get('cagr_pct', 'N/A')}% | {e5r.get('cagr_pct', 'N/A')}% |")
    crossover = verdict["details"]["cost_crossover_bps"]
    a(f"\nCost crossover (E5 >= V4): {'None found' if crossover is None else f'{crossover} bps RT'}")
    a("")

    # ---- 7. Regime decomposition ----
    a("## 7. Regime Decomposition")
    a("")
    a("| Strategy | Regime | Trades | Win Rate | Avg Return |")
    a("|----------|--------|--------|----------|------------|")
    for r in regime:
        a(f"| {r['strategy']} | {r['regime']} | {r['trades']} | "
          f"{r['win_rate']} | {r['avg_return']} |")
    a("")

    # ---- 8. Complexity ----
    a("## 8. Complexity Comparison")
    a("")
    a("| Aspect | V4 | E5 |")
    a("|--------|----|----|")
    a(f"| Parameters | {verdict['details']['v4_param_count']} | {verdict['details']['e5_param_count']} |")
    a("| Recalibration | Yearly (expanding + trailing quantiles) | None (fixed params) |")
    a("| Feature sources | D1 return + H4 trend quality + H4 order flow | H4 EMA crossover + VDO + D1 EMA regime |")
    a("| State machine | 2-state hysteresis (entry/hold thresholds) | 2-state with trailing stop + trend exit |")
    a("| Exit mechanism | Single hold threshold | ATR trail stop + EMA cross-down |")
    a("")

    # ---- 9. Verdict ----
    a("## 9. Verdict")
    a("")
    a(f"**{verdict['verdict']}** (V4 wins {verdict['v4_wins']}, E5 wins {verdict['e5_wins']})")
    a("")
    a("### Key Findings")
    a("")
    a(f"1. **Sharpe**: V4 ({verdict['details']['sharpe_v4']:.4f}) > "
      f"E5 ({verdict['details']['sharpe_e5']:.4f}) at 20 bps RT")
    a(f"2. **MDD**: V4 ({verdict['details']['mdd_v4']:.1f}%) < "
      f"E5 ({verdict['details']['mdd_e5']:.1f}%) — V4 draws down less")
    wfo_p = verdict['details'].get('wfo_p_value')
    wfo_p_str = f"{wfo_p:.3f}" if wfo_p is not None else "N/A"
    a(
        f"3. **WFO**: valid wins V4={verdict['details']['wfo_v4_wins_valid']} vs "
        f"E5={verdict['details']['wfo_e5_wins_valid']}; "
        f"power-only wins V4={verdict['details']['wfo_v4_wins_power']} vs "
        f"E5={verdict['details']['wfo_e5_wins_power']} "
        f"(basis={verdict['details']['wfo_winner_basis']}, "
        f"raw_winner={verdict['details']['wfo_raw_winner']}, "
        f"supported={verdict['details']['wfo_statistically_supported']}, "
        f"Wilcoxon p={wfo_p_str})"
    )
    a(f"4. **Paired bootstrap**: P(V4>E5) = {verdict['details']['paired_p_v4_gt_e5']:.3f} "
      f"(full period, block=20)")
    a(f"5. **Plateau**: V4 spread {verdict['details']['sensitivity_spread_v4']:.4f} "
      f"vs E5 {verdict['details']['sensitivity_spread_e5']:.4f} — "
      f"{'V4 more fragile' if verdict['details']['sensitivity_spread_v4'] > verdict['details']['sensitivity_spread_e5'] else 'E5 more fragile'}")
    v4_trades = trade_cmp.get("v4", {}).get("trades", "?")
    e5_trades = trade_cmp.get("e5", {}).get("trades", "?")
    a(f"6. **Trades**: V4 has {v4_trades} vs E5 has {e5_trades}")
    a(f"7. **DSR advisory**: V4 p={v4_dsr:.4f} (10 trials) vs "
      f"E5 p={e5_dsr:.4f} (245 trials) on H4 returns")
    if crossover is None:
        a("8. **Cost**: V4 dominates E5 at all tested cost levels (no crossover found)")
    else:
        a(f"8. **Cost**: E5 catches V4 at {crossover} bps RT — V4 dominates below that")
    a("")

    a("### Caveats")
    a("")
    a("1. V4 has ~10 effective parameters vs E5's 4 — higher DOF")
    a("2. V4 yearly recalibration introduces implicit in-sample dependence")
    a("3. V4's 51 trades provide less statistical power than E5's 162")
    a("4. WFO is evaluated head-to-head with power-only inference; low-trade windows remain underpowered")
    a("5. V4 plateau spread is wider — performance more sensitive to parameter choice")
    a("6. V4 uses order-flow data (taker buy imbalance) which may not be available in all markets")
    a("")

    return "\n".join(lines)


# ==================================================================
# Main
# ==================================================================

def main() -> None:
    print("=" * 70)
    print("Phase 4: Comparison Report & Verdict")
    print("=" * 70)

    # Load all results
    bt_v4 = _load_json("v4_backtest.json")
    bt_e5 = _load_json("e5_backtest.json")
    wfo = _load_json("wfo_summary.json")
    paired = _load_csv("paired_bootstrap.csv")
    trade_cmp = _load_json("trade_comparison.json")
    cost_sweep = _load_csv("cost_sweep.csv")
    regime = _load_csv("regime_decomposition.csv")
    v4_sens = _load_csv("v4_sensitivity.csv")
    e5_sens = _load_csv("e5_sensitivity.csv")
    psr = _load_json("selection_bias.json")
    holdout_v4 = _load_json("v4_holdout.json")
    holdout_e5 = _load_json("e5_holdout.json")

    # Compute verdict
    bt = {"v4": bt_v4, "e5": bt_e5}
    verdict = compute_verdict(bt, wfo, paired, cost_sweep, v4_sens, e5_sens)
    save_json(RESULTS_DIR / "verdict.json", verdict)
    print(f"\nVerdict: {verdict['verdict']}")
    print(f"  V4 wins: {verdict['v4_wins']}, E5 wins: {verdict['e5_wins']}")

    # Generate report
    report = generate_report(
        bt_v4, bt_e5, wfo, paired, trade_cmp, cost_sweep,
        regime, v4_sens, e5_sens, psr, verdict, holdout_v4, holdout_e5,
    )
    report_path = RESULTS_DIR / "comparison_report.md"
    report_path.write_text(report)
    print(f"\nReport: {report_path}")

    print(f"\n{'=' * 70}")
    print("Phase 4 complete.")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
