"""VP1 full evaluation — A3 + A4 + A5.

A3: Full-history backtest (all 3 cost scenarios)
A4: Bootstrap confidence intervals (VCBB)
A5: Trade structure analysis
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from v10.core.data import DataFeed
from v10.core.engine import BacktestEngine
from v10.core.types import SCENARIOS, BacktestResult, Side
from strategies.vtrend_vp1.strategy import VP1Config, VP1Strategy


DATA_PATH = Path(__file__).resolve().parents[4] / "data/bars_btcusdt_2016_now_h1_4h_1d.csv"
RESULTS_DIR = Path(__file__).resolve().parents[1] / "results" / "full_eval"


def ms_to_iso(ms: int) -> str:
    dt = datetime.fromtimestamp(ms / 1000, tz=timezone.utc)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


# ======================================================================
# A3: Full-history backtest
# ======================================================================

def run_backtests() -> dict[str, BacktestResult]:
    """Run VP1 across all 3 cost scenarios."""
    print("=" * 70)
    print("  A3: Full-History Backtest — VP1")
    print("=" * 70)

    feed = DataFeed(str(DATA_PATH), warmup_days=365)
    print(f"  Data: {feed}")

    results = {}
    for scenario_name, cost in SCENARIOS.items():
        t0 = time.time()
        strategy = VP1Strategy(VP1Config())
        engine = BacktestEngine(
            feed=feed,
            strategy=strategy,
            cost=cost,
            initial_cash=10_000.0,
            warmup_mode="no_trade",
        )
        result = engine.run()
        dt = time.time() - t0
        results[scenario_name] = result
        s = result.summary
        print(f"\n  [{scenario_name}] ({cost.round_trip_bps:.0f} bps RT, {dt:.1f}s)")
        print(f"    Sharpe: {s.get('sharpe', 0):.4f}  |  "
              f"CAGR: {s.get('cagr_pct', 0):.2f}%  |  "
              f"MDD: {s.get('max_drawdown_mid_pct', 0):.2f}%  |  "
              f"Trades: {s.get('trades', 0)}")

    return results


def save_backtests(results: dict[str, BacktestResult]) -> None:
    """Save backtest results to CSV/JSON."""
    outdir = RESULTS_DIR / "backtests"
    outdir.mkdir(parents=True, exist_ok=True)

    # Summary comparison table
    rows = []
    for name, r in results.items():
        s = r.summary
        rows.append({
            "scenario": name,
            "cost_bps": SCENARIOS[name].round_trip_bps,
            "sharpe": s.get("sharpe"),
            "sortino": s.get("sortino"),
            "calmar": s.get("calmar"),
            "cagr_pct": s.get("cagr_pct"),
            "total_return_pct": s.get("total_return_pct"),
            "max_drawdown_mid_pct": s.get("max_drawdown_mid_pct"),
            "trades": s.get("trades"),
            "win_rate_pct": s.get("win_rate_pct"),
            "profit_factor": s.get("profit_factor"),
            "avg_exposure": s.get("avg_exposure"),
            "avg_days_held": s.get("avg_days_held"),
            "fees_total": s.get("fees_total"),
            "fee_drag_pct_per_year": s.get("fee_drag_pct_per_year"),
        })

    with open(outdir / "scenario_comparison.json", "w") as f:
        json.dump(rows, f, indent=2, default=str)

    # CSV
    with open(outdir / "scenario_comparison.csv", "w") as f:
        headers = list(rows[0].keys())
        f.write(",".join(headers) + "\n")
        for row in rows:
            f.write(",".join(str(row[h]) for h in headers) + "\n")

    # Per-scenario equity, trades, fills
    for name, r in results.items():
        sdir = outdir / name
        sdir.mkdir(exist_ok=True)

        # equity.csv
        with open(sdir / "equity.csv", "w") as f:
            f.write("close_time,nav_mid,nav_liq,exposure\n")
            for e in r.equity:
                f.write(f"{ms_to_iso(e.close_time)},{e.nav_mid:.2f},"
                        f"{e.nav_liq:.2f},{e.exposure:.6f}\n")

        # trades.csv
        with open(sdir / "trades.csv", "w") as f:
            f.write("trade_id,entry_time,exit_time,entry_price,exit_price,"
                    "pnl,return_pct,days_held,entry_reason,exit_reason\n")
            for t in r.trades:
                f.write(f"{t.trade_id},{ms_to_iso(t.entry_ts_ms)},"
                        f"{ms_to_iso(t.exit_ts_ms)},"
                        f"{t.entry_price:.2f},{t.exit_price:.2f},"
                        f"{t.pnl:.2f},{t.return_pct:.2f},{t.days_held:.2f},"
                        f"{t.entry_reason},{t.exit_reason}\n")

        # summary.json
        with open(sdir / "summary.json", "w") as f:
            json.dump(r.summary, f, indent=2, default=str)

    print(f"\n  Saved to {outdir}/")


# ======================================================================
# A4: Bootstrap CIs (VCBB)
# ======================================================================

def run_bootstrap(result: BacktestResult, n_boot: int = 2000) -> dict:
    """Circular Block Bootstrap on the harsh-scenario equity curve."""
    print("\n" + "=" * 70)
    print("  A4: Bootstrap Confidence Intervals (VCBB)")
    print("=" * 70)

    equity = result.equity
    if len(equity) < 100:
        print("  SKIP: insufficient equity points")
        return {}

    # Extract 4H returns
    navs = np.array([e.nav_mid for e in equity])
    returns = np.diff(navs) / navs[:-1]
    n = len(returns)

    # Annualization: 2190 4H bars per year
    bars_per_year = 2190.0

    # Observed metrics
    obs_sharpe = np.mean(returns) / np.std(returns, ddof=0) * np.sqrt(bars_per_year)
    obs_cagr = _cagr_from_navs(navs, bars_per_year)
    obs_mdd = _max_drawdown(navs)

    print(f"  Observed: Sharpe={obs_sharpe:.4f}, CAGR={obs_cagr:.2f}%, MDD={obs_mdd:.2f}%")
    print(f"  Bootstrap: {n_boot} resamples, block sizes [10, 20, 40]...")

    block_sizes = [10, 20, 40]
    all_sharpes = []
    all_cagrs = []
    all_mdds = []

    rng = np.random.default_rng(42)

    for block_len in block_sizes:
        for _ in range(n_boot // len(block_sizes)):
            # Circular block bootstrap
            boot_returns = _circular_block_resample(returns, block_len, rng)
            boot_navs = _returns_to_navs(boot_returns, navs[0])

            s = np.mean(boot_returns) / np.std(boot_returns, ddof=0) * np.sqrt(bars_per_year)
            c = _cagr_from_navs(boot_navs, bars_per_year)
            m = _max_drawdown(boot_navs)

            all_sharpes.append(s)
            all_cagrs.append(c)
            all_mdds.append(m)

    all_sharpes = np.array(all_sharpes)
    all_cagrs = np.array(all_cagrs)
    all_mdds = np.array(all_mdds)

    boot_results = {
        "n_bootstrap": n_boot,
        "n_returns": n,
        "block_sizes": block_sizes,
        "sharpe": {
            "observed": float(obs_sharpe),
            "mean": float(np.mean(all_sharpes)),
            "median": float(np.median(all_sharpes)),
            "std": float(np.std(all_sharpes)),
            "ci_2_5": float(np.percentile(all_sharpes, 2.5)),
            "ci_97_5": float(np.percentile(all_sharpes, 97.5)),
            "p_positive": float(np.mean(all_sharpes > 0)),
        },
        "cagr_pct": {
            "observed": float(obs_cagr),
            "mean": float(np.mean(all_cagrs)),
            "median": float(np.median(all_cagrs)),
            "std": float(np.std(all_cagrs)),
            "ci_2_5": float(np.percentile(all_cagrs, 2.5)),
            "ci_97_5": float(np.percentile(all_cagrs, 97.5)),
            "p_positive": float(np.mean(all_cagrs > 0)),
        },
        "max_drawdown_pct": {
            "observed": float(obs_mdd),
            "mean": float(np.mean(all_mdds)),
            "median": float(np.median(all_mdds)),
            "std": float(np.std(all_mdds)),
            "ci_2_5": float(np.percentile(all_mdds, 2.5)),
            "ci_97_5": float(np.percentile(all_mdds, 97.5)),
        },
    }

    print(f"\n  Sharpe: {obs_sharpe:.4f}  "
          f"[{boot_results['sharpe']['ci_2_5']:.4f}, "
          f"{boot_results['sharpe']['ci_97_5']:.4f}]  "
          f"P(>0)={boot_results['sharpe']['p_positive']:.1%}")
    print(f"  CAGR:   {obs_cagr:.2f}%  "
          f"[{boot_results['cagr_pct']['ci_2_5']:.2f}%, "
          f"{boot_results['cagr_pct']['ci_97_5']:.2f}%]  "
          f"P(>0)={boot_results['cagr_pct']['p_positive']:.1%}")
    print(f"  MDD:    {obs_mdd:.2f}%  "
          f"[{boot_results['max_drawdown_pct']['ci_2_5']:.2f}%, "
          f"{boot_results['max_drawdown_pct']['ci_97_5']:.2f}%]")

    return boot_results


def _circular_block_resample(
    returns: np.ndarray, block_len: int, rng: np.random.Generator,
) -> np.ndarray:
    """Circular block bootstrap (Politis & Romano 1994)."""
    n = len(returns)
    n_blocks = (n + block_len - 1) // block_len
    starts = rng.integers(0, n, size=n_blocks)
    blocks = []
    for s in starts:
        idx = np.arange(s, s + block_len) % n
        blocks.append(returns[idx])
    return np.concatenate(blocks)[:n]


def _returns_to_navs(returns: np.ndarray, initial: float) -> np.ndarray:
    """Convert returns to NAV series."""
    navs = np.empty(len(returns) + 1)
    navs[0] = initial
    for i, r in enumerate(returns):
        navs[i + 1] = navs[i] * (1 + r)
    return navs


def _cagr_from_navs(navs: np.ndarray, bars_per_year: float) -> float:
    """CAGR in percent from NAV series."""
    if navs[0] <= 0 or navs[-1] <= 0:
        return 0.0
    n_bars = len(navs) - 1
    years = n_bars / bars_per_year
    if years <= 0:
        return 0.0
    return ((navs[-1] / navs[0]) ** (1 / years) - 1) * 100


def _max_drawdown(navs: np.ndarray) -> float:
    """Max drawdown in percent."""
    peak = np.maximum.accumulate(navs)
    dd = (peak - navs) / peak * 100
    return float(np.max(dd))


# ======================================================================
# A5: Trade structure analysis
# ======================================================================

def run_trade_analysis(result: BacktestResult) -> dict:
    """Comprehensive trade structure analysis."""
    print("\n" + "=" * 70)
    print("  A5: Trade Structure Analysis")
    print("=" * 70)

    trades = result.trades
    if not trades:
        print("  No trades")
        return {}

    returns = np.array([t.return_pct for t in trades])
    pnls = np.array([t.pnl for t in trades])
    days = np.array([t.days_held for t in trades])

    winners = returns[returns > 0]
    losers = returns[returns <= 0]

    # Exit reason breakdown
    exit_reasons: dict[str, int] = {}
    for t in trades:
        r = t.exit_reason
        exit_reasons[r] = exit_reasons.get(r, 0) + 1

    # Top trades by contribution
    sorted_idx = np.argsort(pnls)[::-1]
    top5_pnl = float(np.sum(pnls[sorted_idx[:5]]))
    total_pnl = float(np.sum(pnls))
    top5_pct = top5_pnl / total_pnl * 100 if total_pnl > 0 else 0

    # Yearly breakdown
    year_stats: dict[int, dict] = {}
    for t in trades:
        year = datetime.fromtimestamp(
            t.entry_ts_ms / 1000, tz=timezone.utc
        ).year
        if year not in year_stats:
            year_stats[year] = {"count": 0, "pnl": 0, "wins": 0}
        year_stats[year]["count"] += 1
        year_stats[year]["pnl"] += t.pnl
        if t.return_pct > 0:
            year_stats[year]["wins"] += 1

    # Exposure analysis
    equity = result.equity
    exposures = np.array([e.exposure for e in equity])

    analysis = {
        "total_trades": len(trades),
        "winners": len(winners),
        "losers": len(losers),
        "win_rate_pct": len(winners) / len(trades) * 100,
        "avg_return_pct": float(np.mean(returns)),
        "median_return_pct": float(np.median(returns)),
        "avg_winner_pct": float(np.mean(winners)) if len(winners) > 0 else 0,
        "avg_loser_pct": float(np.mean(losers)) if len(losers) > 0 else 0,
        "best_trade_pct": float(np.max(returns)),
        "worst_trade_pct": float(np.min(returns)),
        "avg_days_held": float(np.mean(days)),
        "median_days_held": float(np.median(days)),
        "max_days_held": float(np.max(days)),
        "total_pnl": total_pnl,
        "avg_pnl": float(np.mean(pnls)),
        "top5_pnl_contribution_pct": top5_pct,
        "exit_reasons": exit_reasons,
        "avg_exposure": float(np.mean(exposures)),
        "max_exposure": float(np.max(exposures)),
        "yearly_stats": {
            str(y): {
                "trades": s["count"],
                "pnl": round(s["pnl"], 2),
                "win_rate": round(s["wins"] / s["count"] * 100, 1) if s["count"] > 0 else 0,
            }
            for y, s in sorted(year_stats.items())
        },
    }

    print(f"\n  Trades: {analysis['total_trades']}  "
          f"({analysis['winners']}W / {analysis['losers']}L)  "
          f"Win rate: {analysis['win_rate_pct']:.1f}%")
    print(f"  Avg winner: {analysis['avg_winner_pct']:.2f}%  |  "
          f"Avg loser: {analysis['avg_loser_pct']:.2f}%")
    print(f"  Best: {analysis['best_trade_pct']:.2f}%  |  "
          f"Worst: {analysis['worst_trade_pct']:.2f}%")
    print(f"  Avg days held: {analysis['avg_days_held']:.1f}  |  "
          f"Max: {analysis['max_days_held']:.1f}")
    print(f"  Top 5 trades = {analysis['top5_pnl_contribution_pct']:.1f}% of total PnL")
    print(f"  Avg exposure: {analysis['avg_exposure']:.4f}")

    print(f"\n  Exit reasons:")
    for reason, count in sorted(exit_reasons.items(), key=lambda x: -x[1]):
        print(f"    {reason}: {count} ({count/len(trades)*100:.1f}%)")

    print(f"\n  Yearly breakdown:")
    for year, stats in sorted(analysis["yearly_stats"].items()):
        print(f"    {year}: {stats['trades']} trades, "
              f"PnL ${stats['pnl']:,.2f}, "
              f"WR {stats['win_rate']}%")

    return analysis


# ======================================================================
# Main
# ======================================================================

def main():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    # A3: Full-history backtests
    bt_results = run_backtests()
    save_backtests(bt_results)

    # Use harsh scenario for A4 and A5 (benchmark standard)
    harsh_result = bt_results["harsh"]

    # A4: Bootstrap CIs
    boot = run_bootstrap(harsh_result, n_boot=2000)
    with open(RESULTS_DIR / "bootstrap_ci.json", "w") as f:
        json.dump(boot, f, indent=2)
    print(f"\n  Bootstrap saved to {RESULTS_DIR}/bootstrap_ci.json")

    # A5: Trade structure analysis
    analysis = run_trade_analysis(harsh_result)
    with open(RESULTS_DIR / "trade_analysis.json", "w") as f:
        json.dump(analysis, f, indent=2, default=str)
    print(f"\n  Trade analysis saved to {RESULTS_DIR}/trade_analysis.json")

    # Final summary comparison with E5+EMA1D21 reference values
    print("\n" + "=" * 70)
    print("  VP1 vs E5+EMA1D21 — Quick Reference (harsh scenario)")
    print("=" * 70)
    s = harsh_result.summary
    print(f"  {'Metric':<25} {'VP1':>12} {'E5+EMA1D21':>12}")
    print(f"  {'-'*49}")
    print(f"  {'Sharpe':<25} {s.get('sharpe', 0):>12.4f} {'1.1944':>12}")
    print(f"  {'CAGR %':<25} {s.get('cagr_pct', 0):>12.2f} {'52.59':>12}")
    print(f"  {'MDD %':<25} {s.get('max_drawdown_mid_pct', 0):>12.2f} {'61.37':>12}")
    print(f"  {'Trades':<25} {s.get('trades', 0):>12d} {'226':>12}")
    print(f"  {'Win Rate %':<25} {s.get('win_rate_pct', 0):>12.2f} {'~43':>12}")
    print(f"  {'Avg Exposure':<25} {s.get('avg_exposure', 0):>12.4f} {'0.452':>12}")

    # Bootstrap comparison
    if boot:
        print(f"\n  Bootstrap Comparison (harsh):")
        print(f"  {'Metric':<25} {'VP1':>20} {'E5+EMA1D21':>20}")
        print(f"  {'-'*65}")
        print(f"  {'Sharpe (median)':<25} "
              f"{boot['sharpe']['median']:>20.4f} {'0.54':>20}")
        print(f"  {'CAGR % (median)':<25} "
              f"{boot['cagr_pct']['median']:>20.2f} {'14.2':>20}")
        print(f"  {'P(CAGR>0)':<25} "
              f"{boot['cagr_pct']['p_positive']:>20.1%} {'80.3%':>20}")


if __name__ == "__main__":
    main()
