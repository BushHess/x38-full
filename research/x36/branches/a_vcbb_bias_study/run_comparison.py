#!/usr/bin/env python3
"""X36: V3 vs V4 vs E5+EMA21D1 — comprehensive comparison at 20 bps RT.

Outputs all results to research/x36/branches/a_vcbb_bias_study/.
"""

from __future__ import annotations

import json
import math
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from scipy.stats import norm

# ── Project imports ──────────────────────────────────────────────────

ROOT = Path("/var/www/trading-bots/btc-spot-dev")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "research" / "x36" / "branches" / "a_vcbb_bias_study"))

from v10.core.data import DataFeed
from v10.core.engine import BacktestEngine
from v10.core.metrics import PERIODS_PER_YEAR_4H
from v10.core.types import Bar, CostConfig

from v3v4_strategies import V3Strategy, V4Strategy
from strategies.vtrend_e5_ema21_d1.strategy import VTrendE5Ema21D1Strategy
from research.lib.vcbb import gen_path_vcbb, make_ratios, precompute_vcbb

# ── Constants ────────────────────────────────────────────────────────

DATA_PATH = ROOT / "data" / "bars_btcusdt_2016_now_h1_4h_1d.csv"
OUT = ROOT / "research" / "x36" / "branches" / "a_vcbb_bias_study"
RESULTS = OUT / "results"
FIGURES = OUT / "figures"

START = "2019-01-01"
END = "2026-02-20"
WARMUP = 365
SEED = 1337
N_BOOT = 500
BLKSZ = 60
CTX = 90
K_NN = 50

STRAT_NAMES = ["V3", "V4", "E5+EMA21D1"]
COLORS = {"V3": "#e63946", "V4": "#457b9d", "E5+EMA21D1": "#2a9d8f"}

# ── Helpers ──────────────────────────────────────────────────────────


def _date_ms(s: str) -> int:
    return int(
        datetime.strptime(s, "%Y-%m-%d")
        .replace(tzinfo=timezone.utc)
        .timestamp()
        * 1000
    )


def make_cost(rt_bps: float) -> CostConfig:
    ps = rt_bps / 2.0
    return CostConfig(
        spread_bps=ps * 0.5,
        slippage_bps=ps * 0.25,
        taker_fee_pct=ps * 0.005,
    )


COST_20 = make_cost(20)


def make_strategy(name: str):
    if name == "V3":
        return V3Strategy()
    if name == "V4":
        return V4Strategy()
    if name == "E5+EMA21D1":
        return VTrendE5Ema21D1Strategy()
    raise ValueError(name)


class PreloadedFeed:
    """DataFeed-compatible object built from pre-filtered bar lists."""

    def __init__(self, h4, d1, report_start_ms=None):
        self.h4_bars = h4
        self.d1_bars = d1
        self.report_start_ms = report_start_ms


def make_sub_feed(all_h4, all_d1, start, end, warmup=WARMUP):
    start_ms = _date_ms(start)
    end_ms = _date_ms(end) + 86_400_000 - 1
    load_ms = start_ms - warmup * 86_400_000
    h4 = [b for b in all_h4 if load_ms <= b.open_time <= end_ms]
    d1 = [b for b in all_d1 if load_ms <= b.open_time <= end_ms]
    return PreloadedFeed(h4, d1, start_ms)


def run_one(feed, name, cost=COST_20):
    s = make_strategy(name)
    e = BacktestEngine(
        feed=feed, strategy=s, cost=cost,
        initial_cash=10_000.0, warmup_mode="no_trade",
    )
    return e.run()


def extract_metrics(result) -> dict:
    s = result.summary
    return {
        "sharpe": s.get("sharpe"),
        "cagr_pct": s.get("cagr_pct"),
        "max_dd_pct": s.get("max_drawdown_mid_pct"),
        "trades": s.get("trades"),
        "win_rate_pct": s.get("win_rate_pct"),
        "profit_factor": s.get("profit_factor"),
        "avg_exposure": s.get("avg_exposure"),
        "avg_days_held": s.get("avg_days_held"),
        "sortino": s.get("sortino"),
        "calmar": s.get("calmar"),
        "final_nav": s.get("final_nav_mid"),
        "total_return_pct": s.get("total_return_pct"),
        "years": s.get("years"),
    }


def compute_psr(navs: np.ndarray, sr_bench: float = 0.0) -> float:
    """Probabilistic Sharpe Ratio: P(true SR > sr_bench)."""
    if len(navs) < 10:
        return float("nan")
    rets = np.diff(navs) / navs[:-1]
    n = len(rets)
    mu = float(rets.mean())
    sigma = float(rets.std(ddof=0))
    if sigma < 1e-12:
        return float("nan")
    sr = (mu / sigma) * math.sqrt(PERIODS_PER_YEAR_4H)
    skew = float(pd.Series(rets).skew())
    kurt = float(pd.Series(rets).kurtosis() + 3)
    denom_sq = 1.0 - skew * sr + (kurt - 1.0) / 4.0 * sr ** 2
    if denom_sq <= 0:
        return float("nan")
    z = (sr - sr_bench) * math.sqrt(n - 1) / math.sqrt(denom_sq)
    return float(norm.cdf(z))


# ═══════════════════════════════════════════════════════════════════════
# 1. FULL-SAMPLE BACKTEST
# ═══════════════════════════════════════════════════════════════════════


def run_full_sample(feed) -> dict:
    results = {}
    for name in STRAT_NAMES:
        r = run_one(feed, name)
        results[name] = r
    return results


# ═══════════════════════════════════════════════════════════════════════
# 2. WFO (Walk-Forward Out-of-Sample)
# ═══════════════════════════════════════════════════════════════════════

WFO_WINDOWS = [
    ("2019-07-01", "2019-12-31"),
    ("2020-01-01", "2020-06-30"),
    ("2020-07-01", "2020-12-31"),
    ("2021-01-01", "2021-06-30"),
    ("2021-07-01", "2021-12-31"),
    ("2022-01-01", "2022-06-30"),
    ("2022-07-01", "2022-12-31"),
    ("2023-01-01", "2023-06-30"),
    ("2023-07-01", "2023-12-31"),
    ("2024-01-01", "2024-06-30"),
    ("2024-07-01", "2024-12-31"),
    ("2025-01-01", "2026-02-20"),
]


def run_wfo(all_h4, all_d1) -> pd.DataFrame:
    rows = []
    for ws, we in WFO_WINDOWS:
        feed = make_sub_feed(all_h4, all_d1, ws, we)
        for name in STRAT_NAMES:
            r = run_one(feed, name)
            m = extract_metrics(r)
            m["window"] = f"{ws[:7]}"
            m["strategy"] = name
            rows.append(m)
    return pd.DataFrame(rows)


# ═══════════════════════════════════════════════════════════════════════
# 3. HOLDOUT
# ═══════════════════════════════════════════════════════════════════════


def run_holdout(all_h4, all_d1) -> dict:
    feed = make_sub_feed(all_h4, all_d1, "2024-01-01", END)
    results = {}
    for name in STRAT_NAMES:
        r = run_one(feed, name)
        results[name] = extract_metrics(r)
    return results


# ═══════════════════════════════════════════════════════════════════════
# 4. COST SWEEP
# ═══════════════════════════════════════════════════════════════════════

COST_LEVELS = [5, 10, 15, 20, 25, 30, 40, 50]


def run_cost_sweep(feed) -> pd.DataFrame:
    rows = []
    for rt in COST_LEVELS:
        cost = make_cost(rt)
        for name in STRAT_NAMES:
            r = run_one(feed, name, cost)
            m = extract_metrics(r)
            m["cost_bps"] = rt
            m["strategy"] = name
            rows.append(m)
    return pd.DataFrame(rows)


# ═══════════════════════════════════════════════════════════════════════
# 5. REGIME DECOMPOSITION
# ═══════════════════════════════════════════════════════════════════════

EPOCHS = [
    ("Pre-2021", "2019-01-01", "2020-12-31"),
    ("2021-2022", "2021-01-01", "2022-12-31"),
    ("2023-2024", "2023-01-01", "2024-12-31"),
    ("2025+", "2025-01-01", "2026-02-20"),
]


def run_regime(all_h4, all_d1) -> pd.DataFrame:
    rows = []
    for label, rs, re in EPOCHS:
        feed = make_sub_feed(all_h4, all_d1, rs, re)
        for name in STRAT_NAMES:
            r = run_one(feed, name)
            m = extract_metrics(r)
            m["epoch"] = label
            m["strategy"] = name
            rows.append(m)
    return pd.DataFrame(rows)


# ═══════════════════════════════════════════════════════════════════════
# 6. VCBB BOOTSTRAP (500 paths @ 20 bps)
# ═══════════════════════════════════════════════════════════════════════

BASE_TS = 1502928000000  # 2017-08-17 00:00:00 UTC (ms)
H4_MS = 4 * 3600 * 1000
D1_MS = 24 * 3600 * 1000


def _build_synthetic_feed(c, h, l, v, tb, qv, warmup_days=WARMUP, base_ts=None):
    """Build DataFeed-compatible object from VCBB arrays."""
    ts0 = base_ts if base_ts is not None else BASE_TS
    n = len(c)
    h4_bars = []
    for i in range(n):
        ot = ts0 + i * H4_MS
        ct = ot + H4_MS - 1
        op = c[i - 1] if i > 0 else c[0]
        h4_bars.append(Bar(
            open_time=ot, open=float(op), high=float(h[i]),
            low=float(l[i]), close=float(c[i]), volume=float(v[i]),
            close_time=ct, taker_buy_base_vol=float(tb[i]),
            interval="4h", quote_volume=float(qv[i]),
        ))

    # Aggregate D1: every 6 H4 bars
    d1_bars = []
    for j in range(0, n, 6):
        chunk = h4_bars[j : j + 6]
        if not chunk:
            break
        d1_bars.append(Bar(
            open_time=chunk[0].open_time,
            open=chunk[0].open,
            high=max(b.high for b in chunk),
            low=min(b.low for b in chunk),
            close=chunk[-1].close,
            volume=sum(b.volume for b in chunk),
            close_time=chunk[-1].close_time,
            taker_buy_base_vol=sum(b.taker_buy_base_vol for b in chunk),
            interval="1d",
            quote_volume=sum(b.quote_volume for b in chunk),
        ))

    report_start_ms = ts0 + warmup_days * D1_MS
    return PreloadedFeed(h4_bars, d1_bars, report_start_ms)


def run_bootstrap(h4_bars, base_ts: int | None = None) -> dict[str, list[dict]]:
    """Run VCBB bootstrap: 500 paths, 3 strategies, 20 bps."""
    src_base_ts = base_ts if base_ts is not None else h4_bars[0].open_time
    cl = np.array([b.close for b in h4_bars], dtype=np.float64)
    hi = np.array([b.high for b in h4_bars], dtype=np.float64)
    lo = np.array([b.low for b in h4_bars], dtype=np.float64)
    vo = np.array([b.volume for b in h4_bars], dtype=np.float64)
    tb = np.array([b.taker_buy_base_vol for b in h4_bars], dtype=np.float64)
    qv_orig = np.array([b.quote_volume for b in h4_bars], dtype=np.float64)

    cr, hr, lr, vol_r, tb_r = make_ratios(cl, hi, lo, vo, tb)
    vcbb = precompute_vcbb(cr, BLKSZ, CTX)

    n_trans = len(cr)
    p0 = cl[0]
    rng = np.random.default_rng(SEED)

    # Also compute qv ratios (same shift as make_ratios)
    qv_shifted = qv_orig[1:].copy()

    boot: dict[str, list[dict]] = {n: [] for n in STRAT_NAMES}

    t0 = time.time()
    for pi in range(N_BOOT):
        if pi % 50 == 0:
            elapsed = time.time() - t0
            print(f"  Bootstrap path {pi}/{N_BOOT}  ({elapsed:.0f}s)")

        c, h, l, v, t = gen_path_vcbb(
            cr, hr, lr, vol_r, tb_r, n_trans, BLKSZ, p0, rng,
            vcbb=vcbb, K=K_NN,
        )
        # Quote volume approx: price * base_volume
        qv = c * v

        feed = _build_synthetic_feed(c, h, l, v, t, qv, base_ts=src_base_ts)

        for name in STRAT_NAMES:
            try:
                r = run_one(feed, name)
                boot[name].append(extract_metrics(r))
            except Exception:
                # Strategy may fail on degenerate paths
                boot[name].append({"sharpe": None, "cagr_pct": None, "max_dd_pct": None})

    elapsed = time.time() - t0
    print(f"  Bootstrap done: {N_BOOT} paths x {len(STRAT_NAMES)} strats in {elapsed:.0f}s")
    return boot


# ═══════════════════════════════════════════════════════════════════════
# 7. TRADE-LEVEL STATS
# ═══════════════════════════════════════════════════════════════════════


def trade_stats(full_results: dict) -> pd.DataFrame:
    rows = []
    for name in STRAT_NAMES:
        r = full_results[name]
        trades = r.trades
        n = len(trades)
        if n == 0:
            rows.append({"strategy": name})
            continue

        rets = [t.return_pct for t in trades]
        days = [t.days_held for t in trades]
        winners = [t for t in trades if t.pnl > 0]
        losers = [t for t in trades if t.pnl <= 0]

        # Churn: re-entry within N bars
        entry_times = sorted(t.entry_ts_ms for t in trades)
        gaps = []
        for i in range(1, len(entry_times)):
            gap_h = (entry_times[i] - entry_times[i - 1]) / (3600 * 1000)
            gaps.append(gap_h)

        churn_12h = sum(1 for g in gaps if g <= 12) if gaps else 0
        churn_24h = sum(1 for g in gaps if g <= 24) if gaps else 0

        rows.append({
            "strategy": name,
            "trades": n,
            "wins": len(winners),
            "losses": len(losers),
            "win_rate": f"{len(winners) / n * 100:.1f}%",
            "avg_return": f"{np.mean(rets):.2f}%",
            "median_return": f"{np.median(rets):.2f}%",
            "avg_days_held": f"{np.mean(days):.1f}",
            "median_days_held": f"{np.median(days):.1f}",
            "best_trade": f"{max(rets):.1f}%",
            "worst_trade": f"{min(rets):.1f}%",
            "churn_le_12h": churn_12h,
            "churn_le_24h": churn_24h,
        })
    return pd.DataFrame(rows)


# ═══════════════════════════════════════════════════════════════════════
# 8. CHARTS
# ═══════════════════════════════════════════════════════════════════════


def _pct_fmt(x, _):
    return f"{x:.0f}%"


def chart_equity_dd(full_results: dict):
    """Equity curves + drawdown on two-panel figure."""
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), sharex=True)

    for name in STRAT_NAMES:
        eq = full_results[name].equity
        ts = pd.to_datetime([e.close_time for e in eq], unit="ms", utc=True)
        navs = np.array([e.nav_mid for e in eq])
        ax1.plot(ts, navs, label=name, color=COLORS[name], linewidth=1.0)

        peak = np.maximum.accumulate(navs)
        dd = (navs / peak - 1.0) * 100
        ax2.fill_between(ts, dd, 0, alpha=0.3, color=COLORS[name], label=name)
        ax2.plot(ts, dd, color=COLORS[name], linewidth=0.7)

    ax1.set_yscale("log")
    ax1.set_ylabel("NAV (log)")
    ax1.set_title("Equity Curves — 20 bps RT", fontsize=13)
    ax1.legend(fontsize=10)
    ax1.grid(True, alpha=0.3)

    ax2.set_ylabel("Drawdown (%)")
    ax2.set_title("Drawdown", fontsize=13)
    ax2.yaxis.set_major_formatter(FuncFormatter(_pct_fmt))
    ax2.legend(fontsize=10)
    ax2.grid(True, alpha=0.3)

    fig.tight_layout()
    fig.savefig(FIGURES / "equity_drawdown.png", dpi=150)
    plt.close(fig)


def chart_bootstrap(boot: dict):
    """Bootstrap Sharpe / CAGR / MDD distributions."""
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    metrics_cfg = [
        ("sharpe", "Sharpe Ratio", axes[0]),
        ("cagr_pct", "CAGR (%)", axes[1]),
        ("max_dd_pct", "Max Drawdown (%)", axes[2]),
    ]
    for key, label, ax in metrics_cfg:
        for name in STRAT_NAMES:
            vals = [d[key] for d in boot[name] if d.get(key) is not None]
            if not vals:
                continue
            vals = np.array(vals, dtype=np.float64)
            vals = vals[np.isfinite(vals)]
            if len(vals) == 0:
                continue
            ax.hist(
                vals, bins=40, alpha=0.45, color=COLORS[name],
                label=f"{name} (med={np.median(vals):.2f})",
                density=True, edgecolor="none",
            )
        ax.set_xlabel(label)
        ax.set_ylabel("Density")
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)

    fig.suptitle("VCBB Bootstrap (500 paths, 20 bps RT)", fontsize=13)
    fig.tight_layout()
    fig.savefig(FIGURES / "bootstrap_distributions.png", dpi=150)
    plt.close(fig)


def chart_wfo(wfo_df: pd.DataFrame):
    """WFO Sharpe per window, grouped bar chart."""
    fig, ax = plt.subplots(figsize=(14, 5))
    windows = wfo_df["window"].unique()
    x = np.arange(len(windows))
    w = 0.25

    for i, name in enumerate(STRAT_NAMES):
        sub = wfo_df[wfo_df["strategy"] == name]
        vals = [sub[sub["window"] == win]["sharpe"].values[0]
                if len(sub[sub["window"] == win]) > 0 else 0
                for win in windows]
        vals = [v if v is not None else 0 for v in vals]
        ax.bar(x + i * w, vals, w, label=name, color=COLORS[name], alpha=0.8)

    ax.set_xticks(x + w)
    ax.set_xticklabels(windows, rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("Sharpe Ratio")
    ax.set_title("WFO: Sharpe per 6-Month Window (20 bps RT)", fontsize=13)
    ax.legend()
    ax.axhline(0, color="gray", linewidth=0.5)
    ax.grid(True, alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig(FIGURES / "wfo_sharpe.png", dpi=150)
    plt.close(fig)


def chart_cost_sweep(cost_df: pd.DataFrame):
    """Sharpe vs cost for all 3 strategies."""
    fig, ax = plt.subplots(figsize=(10, 5))
    for name in STRAT_NAMES:
        sub = cost_df[cost_df["strategy"] == name].sort_values("cost_bps")
        ax.plot(sub["cost_bps"], sub["sharpe"], "o-", label=name,
                color=COLORS[name], linewidth=1.5, markersize=5)
    ax.set_xlabel("Round-Trip Cost (bps)")
    ax.set_ylabel("Sharpe Ratio")
    ax.set_title("Cost Sensitivity", fontsize=13)
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIGURES / "cost_sensitivity.png", dpi=150)
    plt.close(fig)


def chart_regime(regime_df: pd.DataFrame):
    """Sharpe per epoch, grouped bar chart."""
    fig, ax = plt.subplots(figsize=(10, 5))
    epochs = regime_df["epoch"].unique()
    x = np.arange(len(epochs))
    w = 0.25

    for i, name in enumerate(STRAT_NAMES):
        sub = regime_df[regime_df["strategy"] == name]
        vals = []
        for ep in epochs:
            r = sub[sub["epoch"] == ep]["sharpe"].values
            vals.append(float(r[0]) if len(r) > 0 and r[0] is not None else 0)
        ax.bar(x + i * w, vals, w, label=name, color=COLORS[name], alpha=0.8)

    ax.set_xticks(x + w)
    ax.set_xticklabels(epochs, fontsize=10)
    ax.set_ylabel("Sharpe Ratio")
    ax.set_title("Regime/Epoch Decomposition (20 bps RT)", fontsize=13)
    ax.legend()
    ax.axhline(0, color="gray", linewidth=0.5)
    ax.grid(True, alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig(FIGURES / "regime_decomposition.png", dpi=150)
    plt.close(fig)


# ═══════════════════════════════════════════════════════════════════════
# 9. REPORT
# ═══════════════════════════════════════════════════════════════════════


def write_report(
    full_results, full_metrics, psr_vals,
    holdout, wfo_df, cost_df, regime_df,
    boot, trade_df,
):
    lines = []
    a = lines.append
    a("# X36: V3 vs V4 vs E5+EMA21D1 — Comprehensive Comparison\n")
    a(f"**Cost**: 20 bps RT | **Bootstrap**: {N_BOOT} VCBB paths | "
      f"**Data**: {START} to {END}\n")

    # ── Full-sample summary table ──
    a("## 1. Full-Sample Backtest (20 bps RT)\n")
    a("| Metric | V3 | V4 | E5+EMA21D1 |")
    a("|--------|----|----|------------|")
    keys = [
        ("Sharpe", "sharpe", ".4f"),
        ("CAGR (%)", "cagr_pct", ".2f"),
        ("Max DD (%)", "max_dd_pct", ".2f"),
        ("Trades", "trades", "d"),
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
            if v is None:
                vals.append("—")
            elif isinstance(v, str):
                vals.append(v)
            else:
                vals.append(f"{v:{fmt}}")
        a(f"| {label} | {vals[0]} | {vals[1]} | {vals[2]} |")

    # ── PSR ──
    a("\n## 2. Probabilistic Sharpe Ratio (PSR > 0)\n")
    a("| Strategy | PSR |")
    a("|----------|-----|")
    for name in STRAT_NAMES:
        a(f"| {name} | {psr_vals[name]:.4f} |")

    # ── Holdout ──
    a("\n## 3. Holdout (2024-01 to 2026-02, 20 bps RT)\n")
    a("| Metric | V3 | V4 | E5+EMA21D1 |")
    a("|--------|----|----|------------|")
    for label, k, fmt in keys[:6]:
        vals = []
        for name in STRAT_NAMES:
            v = holdout[name].get(k)
            if v is None:
                vals.append("—")
            elif isinstance(v, str):
                vals.append(v)
            else:
                vals.append(f"{v:{fmt}}")
        a(f"| {label} | {vals[0]} | {vals[1]} | {vals[2]} |")

    # ── WFO summary ──
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

    # ── Bootstrap summary ──
    a(f"\n## 5. VCBB Bootstrap ({N_BOOT} paths, 20 bps RT)\n")
    a("| Metric | V3 | V4 | E5+EMA21D1 |")
    a("|--------|----|----|------------|")
    for key, label in [
        ("sharpe", "Median Sharpe"),
        ("cagr_pct", "Median CAGR (%)"),
        ("max_dd_pct", "Median MDD (%)"),
    ]:
        vals = []
        for name in STRAT_NAMES:
            arr = [d[key] for d in boot[name]
                   if d.get(key) is not None]
            arr = [x for x in arr if x is not None and np.isfinite(x)]
            if arr:
                vals.append(f"{np.median(arr):.3f}")
            else:
                vals.append("—")
        a(f"| {label} | {vals[0]} | {vals[1]} | {vals[2]} |")

    a("\n### P(Sharpe > 0)\n")
    a("| Strategy | P(Sharpe > 0) |")
    a("|----------|---------------|")
    for name in STRAT_NAMES:
        arr = [d["sharpe"] for d in boot[name]
               if d.get("sharpe") is not None]
        arr = [x for x in arr if x is not None and np.isfinite(x)]
        if arr:
            p = np.mean(np.array(arr) > 0)
            a(f"| {name} | {p:.1%} |")
        else:
            a(f"| {name} | — |")

    # ── Regime ──
    a("\n## 6. Epoch Decomposition (Sharpe, 20 bps RT)\n")
    a("| Epoch | V3 | V4 | E5+EMA21D1 |")
    a("|-------|----|----|------------|")
    for ep in regime_df["epoch"].unique():
        vals = []
        for name in STRAT_NAMES:
            sub = regime_df[(regime_df["epoch"] == ep) & (regime_df["strategy"] == name)]
            if len(sub) > 0 and sub["sharpe"].values[0] is not None:
                vals.append(f"{sub['sharpe'].values[0]:.4f}")
            else:
                vals.append("—")
        a(f"| {ep} | {vals[0]} | {vals[1]} | {vals[2]} |")

    # ── Cost sweep ──
    a("\n## 7. Cost Sensitivity (Sharpe)\n")
    a("| Cost (bps RT) | V3 | V4 | E5+EMA21D1 |")
    a("|---------------|----|----|------------|")
    for rt in COST_LEVELS:
        vals = []
        for name in STRAT_NAMES:
            sub = cost_df[(cost_df["cost_bps"] == rt) & (cost_df["strategy"] == name)]
            if len(sub) > 0 and sub["sharpe"].values[0] is not None:
                vals.append(f"{sub['sharpe'].values[0]:.4f}")
            else:
                vals.append("—")
        a(f"| {rt} | {vals[0]} | {vals[1]} | {vals[2]} |")

    # ── Trade stats ──
    a("\n## 8. Trade-Level Statistics\n")
    # Manual markdown table (no tabulate dependency)
    cols = list(trade_df.columns)
    a("| " + " | ".join(cols) + " |")
    a("| " + " | ".join(["---"] * len(cols)) + " |")
    for _, row in trade_df.iterrows():
        a("| " + " | ".join(str(row[c]) for c in cols) + " |")

    # ── Charts ──
    a("\n## 9. Charts\n")
    a("![Equity & Drawdown](../figures/equity_drawdown.png)\n")
    a("![Bootstrap Distributions](../figures/bootstrap_distributions.png)\n")
    a("![WFO Sharpe](../figures/wfo_sharpe.png)\n")
    a("![Cost Sensitivity](../figures/cost_sensitivity.png)\n")
    a("![Regime Decomposition](../figures/regime_decomposition.png)\n")

    report_path = RESULTS / "comparison_report.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  Report written: {report_path}")


# ═══════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════


def _fast_load_bars(path: Path):
    """Load CSV and convert to Bar lists ~10x faster than DataFeed iterrows."""
    df = pd.read_csv(path)
    h4_df = df[df["interval"] == "4h"].sort_values("open_time").reset_index(drop=True)
    d1_df = df[df["interval"] == "1d"].sort_values("open_time").reset_index(drop=True)

    def _to_bars(sub: pd.DataFrame) -> list[Bar]:
        bars = []
        for row in sub.itertuples(index=False):
            bars.append(Bar(
                open_time=int(row.open_time),
                open=float(row.open),
                high=float(row.high),
                low=float(row.low),
                close=float(row.close),
                volume=float(row.volume),
                close_time=int(row.close_time),
                taker_buy_base_vol=float(getattr(row, "taker_buy_base_vol", 0.0)),
                interval=str(row.interval),
                quote_volume=float(getattr(row, "quote_volume", 0.0)),
                taker_buy_quote_vol=float(getattr(row, "taker_buy_quote_vol", 0.0)),
            ))
        return bars

    return _to_bars(h4_df), _to_bars(d1_df)


def main():
    RESULTS.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    t_start = time.time()

    # ── Load data ────────────────────────────────────────────────────
    print("Loading data...")
    all_h4, all_d1 = _fast_load_bars(DATA_PATH)
    print(f"  H4: {len(all_h4)} bars, D1: {len(all_d1)} bars  ({time.time()-t_start:.1f}s)")

    feed_full = make_sub_feed(all_h4, all_d1, START, END)
    print(f"  Full-sample feed: {len(feed_full.h4_bars)} H4, {len(feed_full.d1_bars)} D1")

    # ── 1. Full-sample backtest ──────────────────────────────────────
    print("\n=== 1. Full-Sample Backtest (20 bps) ===")
    full_results = run_full_sample(feed_full)
    full_metrics = {}
    for name in STRAT_NAMES:
        m = extract_metrics(full_results[name])
        full_metrics[name] = m
        print(f"  {name:14s}  Sharpe={m['sharpe']:.4f}  CAGR={m['cagr_pct']:.1f}%  "
              f"MDD={m['max_dd_pct']:.1f}%  Trades={m['trades']}")

    # ── 2. PSR ───────────────────────────────────────────────────────
    print("\n=== 2. PSR ===")
    psr_vals = {}
    for name in STRAT_NAMES:
        navs = np.array([e.nav_mid for e in full_results[name].equity])
        psr_vals[name] = compute_psr(navs)
        print(f"  {name:14s}  PSR={psr_vals[name]:.4f}")

    # ── 3. Holdout ───────────────────────────────────────────────────
    print("\n=== 3. Holdout (2024-01 to 2026-02) ===")
    holdout = run_holdout(all_h4, all_d1)
    for name in STRAT_NAMES:
        h = holdout[name]
        print(f"  {name:14s}  Sharpe={h['sharpe']:.4f}  CAGR={h['cagr_pct']:.1f}%  "
              f"MDD={h['max_dd_pct']:.1f}%")

    # ── 4. WFO ───────────────────────────────────────────────────────
    print("\n=== 4. WFO (12 x 6-month windows) ===")
    wfo_df = run_wfo(all_h4, all_d1)
    for name in STRAT_NAMES:
        sub = wfo_df[wfo_df["strategy"] == name]
        n_pos = (sub["sharpe"].dropna() > 0).sum()
        med_sh = sub["sharpe"].dropna().median()
        print(f"  {name:14s}  {n_pos}/{len(sub)} positive  median Sharpe={med_sh:.3f}")

    # ── 5. Cost sweep ────────────────────────────────────────────────
    print("\n=== 5. Cost Sweep ===")
    cost_df = run_cost_sweep(feed_full)
    for rt in [10, 20, 50]:
        row = cost_df[cost_df["cost_bps"] == rt]
        vals = {n: row[row["strategy"] == n]["sharpe"].values[0]
                for n in STRAT_NAMES}
        print(f"  {rt:3d} bps:  " + "  ".join(
            f"{n}={v:.3f}" for n, v in vals.items()))

    # ── 6. Regime ────────────────────────────────────────────────────
    print("\n=== 6. Regime Decomposition ===")
    regime_df = run_regime(all_h4, all_d1)
    for _, row in regime_df.iterrows():
        sh = row["sharpe"] if row["sharpe"] is not None else 0
        print(f"  {row['epoch']:12s}  {row['strategy']:14s}  Sharpe={sh:.3f}")

    # ── 7. Trade stats ───────────────────────────────────────────────
    print("\n=== 7. Trade Stats ===")
    trade_df = trade_stats(full_results)
    print(trade_df.to_string(index=False))

    # ── 8. Bootstrap ─────────────────────────────────────────────────
    print(f"\n=== 8. VCBB Bootstrap ({N_BOOT} paths, 20 bps) ===")
    # Use the full-sample feed's H4 bars (with warmup) for bootstrap
    boot = run_bootstrap(feed_full.h4_bars)

    # Save bootstrap raw data
    boot_summary = {}
    for name in STRAT_NAMES:
        arr_sh = [d["sharpe"] for d in boot[name]
                  if d.get("sharpe") is not None and np.isfinite(d["sharpe"])]
        arr_cagr = [d["cagr_pct"] for d in boot[name]
                    if d.get("cagr_pct") is not None and np.isfinite(d["cagr_pct"])]
        arr_mdd = [d["max_dd_pct"] for d in boot[name]
                   if d.get("max_dd_pct") is not None and np.isfinite(d["max_dd_pct"])]
        boot_summary[name] = {
            "n_valid": len(arr_sh),
            "sharpe_median": float(np.median(arr_sh)) if arr_sh else None,
            "sharpe_mean": float(np.mean(arr_sh)) if arr_sh else None,
            "sharpe_p5": float(np.percentile(arr_sh, 5)) if arr_sh else None,
            "sharpe_p95": float(np.percentile(arr_sh, 95)) if arr_sh else None,
            "cagr_median": float(np.median(arr_cagr)) if arr_cagr else None,
            "mdd_median": float(np.median(arr_mdd)) if arr_mdd else None,
            "p_sharpe_gt_0": float(np.mean(np.array(arr_sh) > 0)) if arr_sh else None,
        }
        bs = boot_summary[name]
        print(f"  {name:14s}  n={bs['n_valid']}  "
              f"Sharpe med={bs['sharpe_median']:.3f}  "
              f"P(Sh>0)={bs['p_sharpe_gt_0']:.1%}")

    # ── Save CSVs ────────────────────────────────────────────────────
    print("\n=== Saving results ===")
    pd.DataFrame([{**full_metrics[n], "strategy": n} for n in STRAT_NAMES]).to_csv(
        RESULTS / "full_sample_metrics.csv", index=False)

    wfo_df.to_csv(RESULTS / "wfo_results.csv", index=False)

    pd.DataFrame([{**holdout[n], "strategy": n} for n in STRAT_NAMES]).to_csv(
        RESULTS / "holdout_metrics.csv", index=False)

    cost_df.to_csv(RESULTS / "cost_sweep.csv", index=False)
    regime_df.to_csv(RESULTS / "regime_decomposition.csv", index=False)
    trade_df.to_csv(RESULTS / "trade_stats.csv", index=False)

    with open(RESULTS / "bootstrap_summary.json", "w") as f:
        json.dump(boot_summary, f, indent=2)

    with open(RESULTS / "psr.json", "w") as f:
        json.dump(psr_vals, f, indent=2)

    # ── Charts ───────────────────────────────────────────────────────
    print("\n=== Generating charts ===")
    chart_equity_dd(full_results)
    chart_bootstrap(boot)
    chart_wfo(wfo_df)
    chart_cost_sweep(cost_df)
    chart_regime(regime_df)
    print("  Charts saved to figures/")

    # ── Report ───────────────────────────────────────────────────────
    print("\n=== Writing report ===")
    write_report(
        full_results, full_metrics, psr_vals,
        holdout, wfo_df, cost_df, regime_df,
        boot, trade_df,
    )

    elapsed = time.time() - t_start
    print(f"\n=== Done in {elapsed:.0f}s ===")


if __name__ == "__main__":
    main()
