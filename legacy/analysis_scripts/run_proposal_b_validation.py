#!/usr/bin/env python3
"""Proposal B validation runner — dynamic backtests + analysis.

Runs V10 baseline vs V10+B (Rolling Equity Brake) across:
  - Full period (2019-01-01 → 2026-02-20), harsh + base scenarios
  - Holdout period (2024-10-01 → 2026-02-20), harsh + base scenarios
  - Sensitivity grid: w ∈ {60, 90, 120}, t = derived (emergency_dd_pct / 2)

Outputs:
  results/proposal_b_dynamic_full.csv
  results/proposal_b_dynamic_holdout.csv
  results/proposal_b_sensitivity.csv
  results/proposal_b_conditional.json
  reports/proposal_b_validation.md
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# Pre-load core to break circular import
import v10.core.types  # noqa: F401
from v10.core.data import DataFeed
from v10.core.engine import BacktestEngine
from v10.core.types import SCENARIOS
from v10.core.types import BacktestResult
from v10.core.types import Trade
from v10.strategies.v8_apex import V8ApexStrategy

DATA_FILE = "data/bars_btcusdt_2016_now_h1_4h_1d.csv"
INITIAL_CASH = 10_000.0
WARMUP_DAYS = 365

# ── Period definitions ──────────────────────────────────────────────────────
FULL_PERIOD = ("2019-01-01", "2026-02-20")
HOLDOUT_PERIOD = ("2024-10-01", "2026-02-20")

# ── Sensitivity grid ───────────────────────────────────────────────────────
WINDOW_GRID = [60, 90, 120]


def run_backtest(
    scenario: str,
    start: str,
    end: str,
    cfg_overrides: dict[str, Any] | None = None,
) -> BacktestResult:
    """Run a single backtest and return the result."""
    feed = DataFeed(DATA_FILE, start=start, end=end, warmup_days=WARMUP_DAYS)
    strategy = V8ApexStrategy()
    # Apply overrides
    if cfg_overrides:
        for k, v in cfg_overrides.items():
            setattr(strategy.cfg, k, v)
    # Re-derive brake threshold if it was set to None
    if strategy.cfg.brake_dd_threshold is None:
        strategy.cfg.brake_dd_threshold = strategy.cfg.emergency_dd_pct / 2

    cost = SCENARIOS[scenario]
    engine = BacktestEngine(
        feed=feed,
        strategy=strategy,
        cost=cost,
        initial_cash=INITIAL_CASH,
        entry_nav_pre_cost=True,
        warmup_mode="no_trade",
    )
    return engine.run()


def summary_row(
    label: str,
    scenario: str,
    period: str,
    result: BacktestResult,
    cfg_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    s = result.summary
    row = {
        "label": label,
        "scenario": scenario,
        "period": period,
        "final_nav": s.get("final_nav_mid", 0),
        "total_return_pct": s.get("total_return_pct", 0),
        "cagr_pct": s.get("cagr_pct", 0),
        "mdd_pct": s.get("max_drawdown_mid_pct", 0),
        "sharpe": s.get("sharpe", 0),
        "sortino": s.get("sortino", 0),
        "calmar": s.get("calmar", 0),
        "trades": s.get("trades", 0),
        "wins": s.get("wins", 0),
        "win_rate_pct": s.get("win_rate_pct", 0),
        "profit_factor": s.get("profit_factor", 0),
        "avg_trade_pnl": s.get("avg_trade_pnl", 0),
        "fees_total": s.get("fees_total", 0),
    }
    if cfg_overrides:
        row.update(cfg_overrides)
    return row


def write_csv(rows: list[dict], path: Path) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    keys = list(rows[0].keys())
    with open(path, "w") as f:
        f.write(",".join(keys) + "\n")
        for r in rows:
            vals = [str(r.get(k, "")) for k in keys]
            f.write(",".join(vals) + "\n")
    print(f"  → {path}")


def compute_trade_pnl(trades: list[Trade]) -> list[dict]:
    """Extract trade-level PnL with reasons."""
    return [
        {
            "trade_id": t.trade_id,
            "entry_reason": t.entry_reason,
            "exit_reason": t.exit_reason,
            "pnl": t.pnl,
            "return_pct": t.return_pct,
            "days_held": t.days_held,
        }
        for t in trades
    ]


def conditional_analysis(
    baseline_result: BacktestResult,
    brake_result: BacktestResult,
) -> dict[str, Any]:
    """Compute conditional performance: G1 (ED trades) vs G2 (non-ED)."""

    def split_ed(trades):
        ed = [t for t in trades if t.exit_reason == "emergency_dd"]
        non_ed = [t for t in trades if t.exit_reason != "emergency_dd"]
        return ed, non_ed

    b_ed, b_non = split_ed(baseline_result.trades)
    r_ed, r_non = split_ed(brake_result.trades)

    b_ed_pnl = sum(t.pnl for t in b_ed)
    b_non_pnl = sum(t.pnl for t in b_non)
    r_ed_pnl = sum(t.pnl for t in r_ed)
    r_non_pnl = sum(t.pnl for t in r_non)

    # ED savings (positive = brake helped)
    ed_savings = r_ed_pnl - b_ed_pnl  # less negative = positive savings
    non_ed_cost = r_non_pnl - b_non_pnl  # reduced winner PnL = negative

    # BCR = ED savings / |non-ED cost| (benefit-cost ratio)
    bcr = abs(ed_savings / non_ed_cost) if abs(non_ed_cost) > 1 else float("inf")

    # Net impact
    net = ed_savings + non_ed_cost

    # Concentration: top-N share of net impact
    # Compare trade PnL differences
    b_pnl_by_id = {t.trade_id: t.pnl for t in baseline_result.trades}
    r_pnl_by_id = {t.trade_id: t.pnl for t in brake_result.trades}
    all_ids = set(b_pnl_by_id.keys()) | set(r_pnl_by_id.keys())
    deltas = []
    for tid in all_ids:
        bp = b_pnl_by_id.get(tid, 0)
        rp = r_pnl_by_id.get(tid, 0)
        deltas.append({"trade_id": tid, "delta_pnl": rp - bp})
    deltas.sort(key=lambda x: abs(x["delta_pnl"]), reverse=True)

    total_abs_delta = sum(abs(d["delta_pnl"]) for d in deltas)
    top1_share = abs(deltas[0]["delta_pnl"]) / total_abs_delta if total_abs_delta > 0 else 0
    top5_share = sum(abs(d["delta_pnl"]) for d in deltas[:5]) / total_abs_delta if total_abs_delta > 0 else 0

    # Top-5 winner damage: compare top-5 winners in baseline vs brake
    b_sorted = sorted(baseline_result.trades, key=lambda t: t.pnl, reverse=True)
    top5_winner_ids = [t.trade_id for t in b_sorted[:5]]
    b_top5_pnl = sum(t.pnl for t in b_sorted[:5])
    r_top5_pnl = sum(r_pnl_by_id.get(tid, 0) for tid in top5_winner_ids)
    winner_damage_pct = (r_top5_pnl - b_top5_pnl) / b_top5_pnl * 100 if b_top5_pnl > 0 else 0

    return {
        "baseline_ed_trades": len(b_ed),
        "baseline_ed_pnl": round(b_ed_pnl, 2),
        "baseline_non_ed_trades": len(b_non),
        "baseline_non_ed_pnl": round(b_non_pnl, 2),
        "brake_ed_trades": len(r_ed),
        "brake_ed_pnl": round(r_ed_pnl, 2),
        "brake_non_ed_trades": len(r_non),
        "brake_non_ed_pnl": round(r_non_pnl, 2),
        "ed_savings": round(ed_savings, 2),
        "non_ed_cost": round(non_ed_cost, 2),
        "net_impact": round(net, 2),
        "bcr": round(bcr, 4),
        "top1_concentration_pct": round(top1_share * 100, 1),
        "top5_concentration_pct": round(top5_share * 100, 1),
        "winner_damage_pct": round(winner_damage_pct, 2),
        "top5_delta_trades": deltas[:5],
    }


def decision_gate(
    full_harsh: dict,
    holdout_harsh: dict,
    conditional: dict,
    sensitivity_rows: list[dict],
) -> dict[str, Any]:
    """Evaluate 6 pre-defined criteria → PROMOTE or HOLD."""
    full_net = full_harsh["brake_nav"] - full_harsh["baseline_nav"]
    holdout_net = holdout_harsh["brake_nav"] - holdout_harsh["baseline_nav"]

    criteria = {}
    # C1: Full period net ≥ 0
    criteria["c1_full_net_positive"] = {
        "pass": full_net >= 0,
        "value": round(full_net, 2),
        "desc": f"Full-period NAV delta = ${full_net:,.2f}",
    }
    # C2: Holdout net ≥ 0
    criteria["c2_holdout_net_positive"] = {
        "pass": holdout_net >= 0,
        "value": round(holdout_net, 2),
        "desc": f"Holdout NAV delta = ${holdout_net:,.2f}",
    }
    # C3: BCR > 1.0
    criteria["c3_bcr_above_1"] = {
        "pass": conditional["bcr"] > 1.0,
        "value": conditional["bcr"],
        "desc": f"BCR = {conditional['bcr']:.4f}",
    }
    # C4: Concentration top-1 ≤ 70%
    criteria["c4_concentration_ok"] = {
        "pass": conditional["top1_concentration_pct"] <= 70,
        "value": conditional["top1_concentration_pct"],
        "desc": f"Top-1 concentration = {conditional['top1_concentration_pct']:.1f}%",
    }
    # C5: Winner damage ≤ -10%
    criteria["c5_winner_damage_ok"] = {
        "pass": conditional["winner_damage_pct"] >= -10.0,
        "value": conditional["winner_damage_pct"],
        "desc": f"Top-5 winner damage = {conditional['winner_damage_pct']:.2f}%",
    }
    # C6: Sensitivity ≥ 2/3 grid cells net positive
    net_positive_cells = sum(
        1
        for r in sensitivity_rows
        if r["label"] == "V10+B" and r["final_nav"] > 0  # will compare with baseline below
    )
    # Need to compare each brake cell with the baseline
    baseline_nav = next(r["final_nav"] for r in sensitivity_rows if r["label"] == "baseline")
    positive_cells = sum(1 for r in sensitivity_rows if r["label"] == "V10+B" and r["final_nav"] >= baseline_nav)
    criteria["c6_sensitivity_robust"] = {
        "pass": positive_cells >= 2,
        "value": f"{positive_cells}/3",
        "desc": f"{positive_cells}/3 grid cells net positive",
    }

    all_pass = all(c["pass"] for c in criteria.values())
    return {
        "verdict": "PROMOTE" if all_pass else "HOLD",
        "criteria": criteria,
        "all_pass": all_pass,
        "pass_count": sum(1 for c in criteria.values() if c["pass"]),
        "total_criteria": len(criteria),
    }


def main() -> None:
    results_dir = Path("results")
    reports_dir = Path("reports")
    results_dir.mkdir(exist_ok=True)
    reports_dir.mkdir(exist_ok=True)

    # ── 1. Full-period backtests ────────────────────────────────────────────
    print("=" * 60)
    print("  STEP 1: Full-period backtests (2019-01 → 2026-02)")
    print("=" * 60)

    full_rows = []
    full_results = {}

    for scenario in ["harsh", "base"]:
        print(f"\n  [{scenario}] V10 baseline ...")
        r_base = run_backtest(scenario, *FULL_PERIOD)
        full_rows.append(summary_row("baseline", scenario, "full", r_base))
        full_results[f"baseline_{scenario}"] = r_base

        print(f"  [{scenario}] V10+B (w=90, t=14%) ...")
        r_brake = run_backtest(
            scenario,
            *FULL_PERIOD,
            {
                "enable_equity_brake": True,
                "brake_window_bars": 90,
            },
        )
        full_rows.append(
            summary_row(
                "V10+B",
                scenario,
                "full",
                r_brake,
                {
                    "enable_equity_brake": True,
                    "brake_window_bars": 90,
                    "brake_dd_threshold": r_brake.summary.get("_brake_dd_threshold", 0.14),
                },
            )
        )
        full_results[f"brake_{scenario}"] = r_brake

        # Print comparison
        b_nav = r_base.summary["final_nav_mid"]
        r_nav = r_brake.summary["final_nav_mid"]
        delta = r_nav - b_nav
        print(f"    Baseline NAV: ${b_nav:,.2f}  |  Brake NAV: ${r_nav:,.2f}  |  Δ: ${delta:+,.2f}")

    write_csv(full_rows, results_dir / "proposal_b_dynamic_full.csv")

    # ── 2. Holdout-period backtests ─────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  STEP 2: Holdout-period backtests (2024-10 → 2026-02)")
    print("=" * 60)

    holdout_rows = []
    holdout_results = {}

    for scenario in ["harsh", "base"]:
        print(f"\n  [{scenario}] V10 baseline ...")
        r_base = run_backtest(scenario, *HOLDOUT_PERIOD)
        holdout_rows.append(summary_row("baseline", scenario, "holdout", r_base))
        holdout_results[f"baseline_{scenario}"] = r_base

        print(f"  [{scenario}] V10+B (w=90, t=14%) ...")
        r_brake = run_backtest(
            scenario,
            *HOLDOUT_PERIOD,
            {
                "enable_equity_brake": True,
                "brake_window_bars": 90,
            },
        )
        holdout_rows.append(
            summary_row(
                "V10+B",
                scenario,
                "holdout",
                r_brake,
                {
                    "enable_equity_brake": True,
                    "brake_window_bars": 90,
                },
            )
        )
        holdout_results[f"brake_{scenario}"] = r_brake

        b_nav = r_base.summary["final_nav_mid"]
        r_nav = r_brake.summary["final_nav_mid"]
        delta = r_nav - b_nav
        print(f"    Baseline NAV: ${b_nav:,.2f}  |  Brake NAV: ${r_nav:,.2f}  |  Δ: ${delta:+,.2f}")

    write_csv(holdout_rows, results_dir / "proposal_b_dynamic_holdout.csv")

    # ── 3. Conditional analysis ─────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  STEP 3: Conditional performance analysis (harsh, full)")
    print("=" * 60)

    cond = conditional_analysis(
        full_results["baseline_harsh"],
        full_results["brake_harsh"],
    )
    with open(results_dir / "proposal_b_conditional.json", "w") as f:
        json.dump(cond, f, indent=2, default=str)
    print(f"  → {results_dir / 'proposal_b_conditional.json'}")
    print(f"  ED savings: ${cond['ed_savings']:+,.2f}")
    print(f"  Non-ED cost: ${cond['non_ed_cost']:+,.2f}")
    print(f"  NET impact: ${cond['net_impact']:+,.2f}")
    print(f"  BCR: {cond['bcr']:.4f}")
    print(f"  Top-1 concentration: {cond['top1_concentration_pct']:.1f}%")
    print(f"  Winner damage: {cond['winner_damage_pct']:.2f}%")

    # ── 4. Sensitivity grid ────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  STEP 4: Sensitivity grid (w={60,90,120}, harsh, full)")
    print("=" * 60)

    sens_rows = []
    # Baseline (already computed)
    sens_rows.append(summary_row("baseline", "harsh", "full", full_results["baseline_harsh"]))

    for w in WINDOW_GRID:
        print(f"  w={w} ...")
        r = run_backtest(
            "harsh",
            *FULL_PERIOD,
            {
                "enable_equity_brake": True,
                "brake_window_bars": w,
            },
        )
        sens_rows.append(
            summary_row(
                "V10+B",
                "harsh",
                "full",
                r,
                {
                    "brake_window_bars": w,
                },
            )
        )
        delta = r.summary["final_nav_mid"] - full_results["baseline_harsh"].summary["final_nav_mid"]
        print(f"    NAV: ${r.summary['final_nav_mid']:,.2f}  |  Δ vs baseline: ${delta:+,.2f}")

    write_csv(sens_rows, results_dir / "proposal_b_sensitivity.csv")

    # ── 5. Decision gate ───────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  STEP 5: Decision gate")
    print("=" * 60)

    gate_input_full = {
        "baseline_nav": full_results["baseline_harsh"].summary["final_nav_mid"],
        "brake_nav": full_results["brake_harsh"].summary["final_nav_mid"],
    }
    gate_input_holdout = {
        "baseline_nav": holdout_results["baseline_harsh"].summary["final_nav_mid"],
        "brake_nav": holdout_results["brake_harsh"].summary["final_nav_mid"],
    }

    gate = decision_gate(gate_input_full, gate_input_holdout, cond, sens_rows)

    print(f"\n  ┌{'─' * 56}┐")
    print(f"  │  VERDICT: {gate['verdict']:>43} │")
    print(f"  │  Criteria passed: {gate['pass_count']}/{gate['total_criteria']:>33} │")
    print(f"  └{'─' * 56}┘\n")

    for name, c in gate["criteria"].items():
        status = "✓ PASS" if c["pass"] else "✗ FAIL"
        print(f"    {status}  {name}: {c['desc']}")

    # ── 6. Validation report ───────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  STEP 6: Writing validation report")
    print("=" * 60)

    report = _build_report(
        full_rows,
        holdout_rows,
        cond,
        sens_rows,
        gate,
        full_results,
        holdout_results,
    )
    report_path = reports_dir / "proposal_b_validation.md"
    report_path.write_text(report)
    print(f"  → {report_path}")
    print("\nDone.")


def _build_report(
    full_rows,
    holdout_rows,
    cond,
    sens_rows,
    gate,
    full_results,
    holdout_results,
) -> str:
    lines = []
    lines.append("# Proposal B Validation Report: Rolling Equity Brake\n")
    lines.append("## 1. Summary\n")
    lines.append(f"**Verdict: {gate['verdict']}** ({gate['pass_count']}/{gate['total_criteria']} criteria passed)\n")
    lines.append(f"**Mechanism:** Block all pyramiding adds when rolling {90}-bar equity DD ≥ 14% (= emergency_dd/2).\n")

    # Decision gate table
    lines.append("\n## 2. Decision Gate\n")
    lines.append("| # | Criterion | Threshold | Value | Result |")
    lines.append("|---|-----------|-----------|-------|--------|")
    for i, (name, c) in enumerate(gate["criteria"].items(), 1):
        status = "PASS" if c["pass"] else "**FAIL**"
        lines.append(f"| {i} | {name} | see spec | {c['value']} | {status} |")

    # Full period comparison
    lines.append("\n## 3. Full-Period Backtest (2019-01 → 2026-02)\n")
    lines.append("| Metric | Baseline (harsh) | V10+B (harsh) | Baseline (base) | V10+B (base) |")
    lines.append("|--------|-------------------|---------------|-----------------|--------------|")
    metrics = [
        "final_nav",
        "cagr_pct",
        "mdd_pct",
        "sharpe",
        "sortino",
        "calmar",
        "trades",
        "win_rate_pct",
        "profit_factor",
        "fees_total",
    ]
    for m in metrics:
        vals = [str(round(r[m], 2)) if isinstance(r[m], float) else str(r[m]) for r in full_rows]
        lines.append(f"| {m} | {vals[0]} | {vals[1]} | {vals[2]} | {vals[3]} |")

    # Holdout comparison
    lines.append("\n## 4. Holdout-Period Backtest (2024-10 → 2026-02)\n")
    lines.append("| Metric | Baseline (harsh) | V10+B (harsh) | Baseline (base) | V10+B (base) |")
    lines.append("|--------|-------------------|---------------|-----------------|--------------|")
    for m in metrics:
        vals = [str(round(r[m], 2)) if isinstance(r[m], float) else str(r[m]) for r in holdout_rows]
        lines.append(f"| {m} | {vals[0]} | {vals[1]} | {vals[2]} | {vals[3]} |")

    # Conditional analysis
    lines.append("\n## 5. Conditional Performance (G1=ED vs G2=non-ED, harsh full)\n")
    lines.append("| Metric | Baseline | V10+B | Delta |")
    lines.append("|--------|----------|-------|-------|")
    lines.append(
        f"| ED trades | {cond['baseline_ed_trades']} | {cond['brake_ed_trades']} | {cond['brake_ed_trades'] - cond['baseline_ed_trades']:+d} |"
    )
    lines.append(
        f"| ED PnL | ${cond['baseline_ed_pnl']:,.2f} | ${cond['brake_ed_pnl']:,.2f} | ${cond['ed_savings']:+,.2f} |"
    )
    lines.append(
        f"| Non-ED trades | {cond['baseline_non_ed_trades']} | {cond['brake_non_ed_trades']} | {cond['brake_non_ed_trades'] - cond['baseline_non_ed_trades']:+d} |"
    )
    lines.append(
        f"| Non-ED PnL | ${cond['baseline_non_ed_pnl']:,.2f} | ${cond['brake_non_ed_pnl']:,.2f} | ${cond['non_ed_cost']:+,.2f} |"
    )
    lines.append(f"| **NET** | | | **${cond['net_impact']:+,.2f}** |")
    lines.append(f"| BCR | | | **{cond['bcr']:.4f}** |")
    lines.append(f"| Top-1 concentration | | | {cond['top1_concentration_pct']:.1f}% |")
    lines.append(f"| Top-5 winner damage | | | {cond['winner_damage_pct']:.2f}% |")

    # Sensitivity grid
    lines.append("\n## 6. Sensitivity Grid (harsh, full period)\n")
    lines.append("| Window | Final NAV | CAGR | MDD | Sharpe | Δ NAV vs baseline |")
    lines.append("|--------|-----------|------|-----|--------|-------------------|")
    base_nav = next(r["final_nav"] for r in sens_rows if r["label"] == "baseline")
    for r in sens_rows:
        w = r.get("brake_window_bars", "—")
        delta = r["final_nav"] - base_nav
        lines.append(
            f"| {r['label']} (w={w}) | ${r['final_nav']:,.2f} | {r['cagr_pct']:.2f}% | {r['mdd_pct']:.2f}% | {r['sharpe']:.4f} | ${delta:+,.2f} |"
        )

    lines.append("\n---\n*Report generated by run_proposal_b_validation.py*\n")
    return "\n".join(lines)


if __name__ == "__main__":
    main()
