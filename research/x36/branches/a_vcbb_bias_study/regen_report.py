#!/usr/bin/env python3
"""Regenerate just the markdown report from saved CSVs/JSONs."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path("/var/www/trading-bots/btc-spot-dev")
sys.path.insert(0, str(ROOT))

OUT = ROOT / "research" / "x36" / "branches" / "a_vcbb_bias_study"
RESULTS = OUT / "results"

STRAT_NAMES = ["V3", "V4", "E5+EMA21D1"]
N_BOOT = 500
START = "2019-01-01"
END = "2026-02-20"
COST_LEVELS = [5, 10, 15, 20, 25, 30, 40, 50]


def main():
    # Load all saved data
    full_df = pd.read_csv(RESULTS / "full_sample_metrics.csv")
    full_metrics = {row["strategy"]: row.to_dict() for _, row in full_df.iterrows()}

    with open(RESULTS / "psr.json") as f:
        psr_vals = json.load(f)

    holdout_df = pd.read_csv(RESULTS / "holdout_metrics.csv")
    holdout = {row["strategy"]: row.to_dict() for _, row in holdout_df.iterrows()}

    wfo_df = pd.read_csv(RESULTS / "wfo_results.csv")
    cost_df = pd.read_csv(RESULTS / "cost_sweep.csv")
    regime_df = pd.read_csv(RESULTS / "regime_decomposition.csv")
    trade_df = pd.read_csv(RESULTS / "trade_stats.csv")

    with open(RESULTS / "bootstrap_summary.json") as f:
        boot_summary = json.load(f)

    # Build report
    lines = []
    a = lines.append
    a("# X36: V3 vs V4 vs E5+EMA21D1 — Comprehensive Comparison\n")
    a(f"**Cost**: 20 bps RT | **Bootstrap**: {N_BOOT} VCBB paths | "
      f"**Data**: {START} to {END}\n")

    # ── 1. Full-sample ──
    a("## 1. Full-Sample Backtest (20 bps RT)\n")
    a("| Metric | V3 | V4 | E5+EMA21D1 |")
    a("|--------|----|----|------------|")
    keys = [
        ("Sharpe", "sharpe", ".4f"),
        ("CAGR (%)", "cagr_pct", ".2f"),
        ("Max DD (%)", "max_dd_pct", ".2f"),
        ("Trades", "trades", ".0f"),
        ("Win Rate (%)", "win_rate_pct", ".1f"),
        ("Profit Factor", "profit_factor", ".3f"),
        ("Avg Exposure", "avg_exposure", ".3f"),
        ("Sortino", "sortino", ".4f"),
        ("Calmar", "calmar", ".4f"),
        ("Final NAV", "final_nav", ",.0f"),
    ]
    for label, k, fmt in keys:
        vals = []
        for name in STRAT_NAMES:
            v = full_metrics[name].get(k)
            if v is None or (isinstance(v, float) and np.isnan(v)):
                vals.append("—")
            else:
                vals.append(f"{v:{fmt}}")
        a(f"| {label} | {vals[0]} | {vals[1]} | {vals[2]} |")

    # ── 2. PSR ──
    a("\n## 2. Probabilistic Sharpe Ratio (PSR > 0)\n")
    a("| Strategy | PSR |")
    a("|----------|-----|")
    for name in STRAT_NAMES:
        a(f"| {name} | {psr_vals[name]:.4f} |")

    # ── 3. Holdout ──
    a("\n## 3. Holdout (2024-01 to 2026-02, 20 bps RT)\n")
    a("| Metric | V3 | V4 | E5+EMA21D1 |")
    a("|--------|----|----|------------|")
    for label, k, fmt in keys[:6]:
        vals = []
        for name in STRAT_NAMES:
            v = holdout[name].get(k)
            if v is None or (isinstance(v, float) and np.isnan(v)):
                vals.append("—")
            else:
                vals.append(f"{v:{fmt}}")
        a(f"| {label} | {vals[0]} | {vals[1]} | {vals[2]} |")

    # ── 4. WFO ──
    a("\n## 4. Walk-Forward (6-Month Windows)\n")
    a("### Win counts (Sharpe > 0 per window)\n")
    for name in STRAT_NAMES:
        sub = wfo_df[wfo_df["strategy"] == name]
        n_win = (sub["sharpe"].dropna() > 0).sum()
        total = len(sub)
        a(f"- **{name}**: {n_win}/{total} windows positive")

    a("\n### Mean / Median Sharpe across windows\n")
    a("| Strategy | Mean Sharpe | Median Sharpe |")
    a("|----------|-------------|---------------|")
    for name in STRAT_NAMES:
        sub = wfo_df[wfo_df["strategy"] == name]["sharpe"].dropna()
        a(f"| {name} | {sub.mean():.4f} | {sub.median():.4f} |")

    # ── 5. Bootstrap ──
    a(f"\n## 5. VCBB Bootstrap ({N_BOOT} paths, 20 bps RT)\n")
    a("| Metric | V3 | V4 | E5+EMA21D1 |")
    a("|--------|----|----|------------|")
    for key, label in [
        ("sharpe_median", "Median Sharpe"),
        ("cagr_median", "Median CAGR (%)"),
        ("mdd_median", "Median MDD (%)"),
    ]:
        vals = []
        for name in STRAT_NAMES:
            v = boot_summary[name].get(key)
            if v is not None:
                vals.append(f"{v:.3f}")
            else:
                vals.append("—")
        a(f"| {label} | {vals[0]} | {vals[1]} | {vals[2]} |")

    a("\n### Bootstrap CI (5th-95th percentile Sharpe)\n")
    a("| Strategy | P5 Sharpe | P95 Sharpe | P(Sharpe>0) |")
    a("|----------|-----------|------------|-------------|")
    for name in STRAT_NAMES:
        bs = boot_summary[name]
        p5 = f"{bs['sharpe_p5']:.3f}" if bs.get("sharpe_p5") is not None else "—"
        p95 = f"{bs['sharpe_p95']:.3f}" if bs.get("sharpe_p95") is not None else "—"
        pgt0 = f"{bs['p_sharpe_gt_0']:.1%}" if bs.get("p_sharpe_gt_0") is not None else "—"
        a(f"| {name} | {p5} | {p95} | {pgt0} |")

    # ── 6. Regime ──
    a("\n## 6. Epoch Decomposition (Sharpe, 20 bps RT)\n")
    a("| Epoch | V3 | V4 | E5+EMA21D1 |")
    a("|-------|----|----|------------|")
    for ep in regime_df["epoch"].unique():
        vals = []
        for name in STRAT_NAMES:
            sub = regime_df[(regime_df["epoch"] == ep) & (regime_df["strategy"] == name)]
            if len(sub) > 0:
                v = sub["sharpe"].values[0]
                vals.append(f"{v:.4f}" if not np.isnan(v) else "—")
            else:
                vals.append("—")
        a(f"| {ep} | {vals[0]} | {vals[1]} | {vals[2]} |")

    # ── 7. Cost sweep ──
    a("\n## 7. Cost Sensitivity (Sharpe)\n")
    a("| Cost (bps RT) | V3 | V4 | E5+EMA21D1 |")
    a("|---------------|----|----|------------|")
    for rt in COST_LEVELS:
        vals = []
        for name in STRAT_NAMES:
            sub = cost_df[(cost_df["cost_bps"] == rt) & (cost_df["strategy"] == name)]
            if len(sub) > 0:
                v = sub["sharpe"].values[0]
                vals.append(f"{v:.4f}" if not np.isnan(v) else "—")
            else:
                vals.append("—")
        a(f"| {rt} | {vals[0]} | {vals[1]} | {vals[2]} |")

    # ── 8. Trade stats ──
    a("\n## 8. Trade-Level Statistics\n")
    cols = list(trade_df.columns)
    a("| " + " | ".join(cols) + " |")
    a("| " + " | ".join(["---"] * len(cols)) + " |")
    for _, row in trade_df.iterrows():
        a("| " + " | ".join(str(row[c]) for c in cols) + " |")

    # ── 9. Charts ──
    a("\n## 9. Charts\n")
    a("![Equity & Drawdown](../figures/equity_drawdown.png)\n")
    a("![Bootstrap Distributions](../figures/bootstrap_distributions.png)\n")
    a("![WFO Sharpe](../figures/wfo_sharpe.png)\n")
    a("![Cost Sensitivity](../figures/cost_sensitivity.png)\n")
    a("![Regime Decomposition](../figures/regime_decomposition.png)\n")

    report_path = RESULTS / "comparison_report.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Report written: {report_path}")


if __name__ == "__main__":
    main()
