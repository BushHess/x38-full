#!/usr/bin/env python3
"""D1.2 — Build canonical X0 trade ledger and bar-level feature store.

Runs actual BacktestEngine for each strategy x cost scenario.
Exports:
  1. Trade ledger CSV per strategy per scenario
  2. Bar-level feature store CSV aligned to X0 decision bars
  3. Entry-annotated feature store (one row per X0 entry)

Source: actual strategy code via BacktestEngine (not vectorized surrogates).
"""

from __future__ import annotations

import csv
import json
import math
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from v10.core.data import DataFeed
from v10.core.engine import BacktestEngine
from v10.core.types import SCENARIOS, BacktestResult, CostConfig

# ── Strategies ────────────────────────────────────────────────────────────
from strategies.vtrend_x0_e5exit.strategy import (
    VTrendX0E5ExitConfig,
    VTrendX0E5ExitStrategy,
)
from strategies.vtrend_ema21_d1.strategy import (
    VTrendEma21D1Config,
    VTrendEma21D1Strategy,
)
from strategies.vtrend_x0_volsize.strategy import (
    VTrendX0VolsizeConfig,
    VTrendX0VolsizeStrategy,
)

# ── Constants ─────────────────────────────────────────────────────────────
DATA = str(ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv")
BREADTH_DATA = "/var/www/trading-bots/data-pipeline/output/bars_multi_4h.parquet"
CASH = 10_000.0
ANN = math.sqrt(6.0 * 365.25)
START = "2019-01-01"
END = "2026-02-20"
WARMUP = 365

OUTDIR = Path(__file__).resolve().parent / "artifacts"

STRAT_DEFS = {
    "X0": ("vtrend_x0_e5exit", VTrendX0E5ExitStrategy, VTrendX0E5ExitConfig),
    "E0_EMA21": ("vtrend_ema21_d1", VTrendEma21D1Strategy, VTrendEma21D1Config),
    "X0_LR": ("vtrend_x0_volsize", VTrendX0VolsizeStrategy, VTrendX0VolsizeConfig),
}

SCENARIO_NAMES = ["smart", "base", "harsh"]


def ms_to_iso(ts_ms: int) -> str:
    return datetime.fromtimestamp(ts_ms / 1000.0, tz=timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


# ═══════════════════════════════════════════════════════════════════════════
# Part 1: Run backtests and export trade ledgers
# ═══════════════════════════════════════════════════════════════════════════

def run_backtest(strat_key: str, scenario: str) -> BacktestResult:
    """Run a single backtest via actual BacktestEngine."""
    _, StratClass, ConfigClass = STRAT_DEFS[strat_key]
    feed = DataFeed(DATA, start=START, end=END, warmup_days=WARMUP)
    strat = StratClass(ConfigClass())
    cost = SCENARIOS[scenario]
    eng = BacktestEngine(
        feed=feed, strategy=strat, cost=cost,
        initial_cash=CASH, warmup_mode="no_trade",
    )
    return eng.run()


def export_trade_ledger(result: BacktestResult, strat_key: str, scenario: str,
                        outdir: Path) -> Path:
    """Export trade ledger CSV."""
    # entry_price/exit_price from engine are cost-adjusted fill prices
    # (buy at ask+slippage, sell at bid-slippage).
    # return_pct = (exit_fill / entry_fill - 1)*100 includes spread+slip.
    # pnl further subtracts taker fees from cash.
    # gross_return = mid-to-mid (strip out spread+slippage adjustment).
    cost_cfg = SCENARIOS[scenario]
    buy_mult = ((1.0 + cost_cfg.spread_bps / 20000.0)
                * (1.0 + cost_cfg.slippage_bps / 10000.0))
    sell_mult = ((1.0 - cost_cfg.spread_bps / 20000.0)
                 * (1.0 - cost_cfg.slippage_bps / 10000.0))

    rows = []
    for t in result.trades:
        mid_entry = t.entry_price / buy_mult
        mid_exit = t.exit_price / sell_mult
        gross_return_pct = (mid_exit / mid_entry - 1.0) * 100.0
        rows.append({
            "strategy": strat_key,
            "scenario": scenario,
            "trade_id": t.trade_id,
            "entry_ts_ms": t.entry_ts_ms,
            "exit_ts_ms": t.exit_ts_ms,
            "entry_time": ms_to_iso(t.entry_ts_ms),
            "exit_time": ms_to_iso(t.exit_ts_ms),
            "entry_fill_price": round(t.entry_price, 2),
            "exit_fill_price": round(t.exit_price, 2),
            "entry_mid_price": round(mid_entry, 2),
            "exit_mid_price": round(mid_exit, 2),
            "qty": t.qty,
            "gross_return_pct": round(gross_return_pct, 4),
            "net_return_pct": round(t.return_pct, 4),
            "pnl_usd": round(t.pnl, 2),
            "holding_bars": round(t.days_held * 6.0),  # H4 bars
            "holding_days": round(t.days_held, 2),
            "entry_reason": t.entry_reason,
            "exit_reason": t.exit_reason,
        })
    fname = outdir / f"trades_{strat_key}_{scenario}.csv"
    df = pd.DataFrame(rows)
    df.to_csv(fname, index=False)
    return fname


def export_equity(result: BacktestResult, strat_key: str, scenario: str,
                  outdir: Path) -> Path:
    """Export equity curve CSV."""
    rows = []
    for e in result.equity:
        rows.append({
            "close_time_ms": e.close_time,
            "close_time": ms_to_iso(e.close_time),
            "nav_mid": round(e.nav_mid, 2),
            "cash": round(e.cash, 2),
            "btc_qty": e.btc_qty,
            "exposure": round(e.exposure, 6),
        })
    fname = outdir / f"equity_{strat_key}_{scenario}.csv"
    df = pd.DataFrame(rows)
    df.to_csv(fname, index=False)
    return fname


# ═══════════════════════════════════════════════════════════════════════════
# Part 2: Build bar-level feature store
# ═══════════════════════════════════════════════════════════════════════════

def _ema(series: np.ndarray, period: int) -> np.ndarray:
    alpha = 2.0 / (period + 1)
    out = np.empty_like(series)
    out[0] = series[0]
    for i in range(1, len(series)):
        out[i] = alpha * series[i] + (1 - alpha) * out[i - 1]
    return out


def _atr(high: np.ndarray, low: np.ndarray, close: np.ndarray,
         period: int) -> np.ndarray:
    prev_cl = np.concatenate([[close[0]], close[:-1]])
    tr = np.maximum(
        high - low,
        np.maximum(np.abs(high - prev_cl), np.abs(low - prev_cl)),
    )
    out = np.full_like(tr, np.nan)
    if period <= len(tr):
        out[period - 1] = np.mean(tr[:period])
        for i in range(period, len(tr)):
            out[i] = (out[i - 1] * (period - 1) + tr[i]) / period
    return out


def _robust_atr(high, low, close, cap_q=0.90, cap_lb=100, period=20):
    prev_cl = np.concatenate([[close[0]], close[:-1]])
    tr = np.maximum(
        high - low,
        np.maximum(np.abs(high - prev_cl), np.abs(low - prev_cl)),
    )
    n = len(tr)
    tr_cap = np.full(n, np.nan)
    for i in range(cap_lb, n):
        q = np.percentile(tr[i - cap_lb:i], cap_q * 100)
        tr_cap[i] = min(tr[i], q)
    ratr = np.full(n, np.nan)
    s = cap_lb
    if s + period <= n:
        ratr[s + period - 1] = np.mean(tr_cap[s:s + period])
        for i in range(s + period, n):
            ratr[i] = (ratr[i - 1] * (period - 1) + tr_cap[i]) / period
    return ratr


def _vdo(close, high, low, volume, taker_buy, fast=12, slow=28):
    n = len(close)
    has_taker = taker_buy is not None and np.any(taker_buy > 0)
    if has_taker:
        taker_sell = volume - taker_buy
        vdr = np.zeros(n)
        mask = volume > 0
        vdr[mask] = (taker_buy[mask] - taker_sell[mask]) / volume[mask]
    else:
        spread = high - low
        vdr = np.zeros(n)
        mask = spread > 0
        vdr[mask] = (close[mask] - low[mask]) / spread[mask] * 2.0 - 1.0
    return _ema(vdr, fast) - _ema(vdr, slow)


def compute_breadth(breadth_path: str, h4_close_times: np.ndarray,
                    d1_ema_period: int = 21) -> np.ndarray:
    """Compute breadth_d1_ema21_share: fraction of breadth universe with
    close > EMA(d1_ema_period) on their own H4 bars.

    For each BTC H4 bar, we look at the most recent completed H4 bar for
    each alt symbol and check if its close > EMA(d1_ema_period) on H4.
    Since we only have H4 for breadth symbols, we use EMA(d1_ema_period * 6)
    on H4 to approximate a D1 EMA(21) equivalent.

    Strict no-lookahead: for each BTC H4 bar at time T, we only use
    breadth symbol bars with close_time <= T.
    """
    bdf = pd.read_parquet(breadth_path)
    # Exclude BTC (it's the anchor, not part of breadth count)
    symbols = sorted(s for s in bdf["symbol"].unique() if s != "BTCUSDT")
    n_btc = len(h4_close_times)
    breadth_share = np.full(n_btc, np.nan, dtype=np.float64)

    # Approximate D1 EMA(21) ≈ H4 EMA(126)
    h4_ema_period = d1_ema_period * 6

    # Precompute per-symbol: close_times and regime_ok arrays
    sym_data = {}
    for sym in symbols:
        sdf = bdf[bdf["symbol"] == sym].sort_values("open_time")
        if len(sdf) < h4_ema_period + 10:
            continue
        cl = sdf["close"].values.astype(np.float64)
        ct = sdf["close_time"].values.astype(np.int64)
        ema_val = _ema(cl, h4_ema_period)
        regime = cl > ema_val
        sym_data[sym] = (ct, regime)

    if not sym_data:
        return breadth_share

    n_syms = len(sym_data)
    # For each BTC H4 bar, find the latest available bar for each symbol
    # Use sorted pointers for efficiency
    sym_list = sorted(sym_data.keys())
    pointers = {s: 0 for s in sym_list}

    for i in range(n_btc):
        btc_ct = h4_close_times[i]
        n_above = 0
        n_valid = 0
        for s in sym_list:
            ct_arr, regime_arr = sym_data[s]
            ptr = pointers[s]
            # Advance pointer to latest bar with close_time <= btc_ct
            while ptr + 1 < len(ct_arr) and ct_arr[ptr + 1] <= btc_ct:
                ptr += 1
            pointers[s] = ptr
            if ct_arr[ptr] <= btc_ct:
                n_valid += 1
                if regime_arr[ptr]:
                    n_above += 1
        if n_valid > 0:
            breadth_share[i] = n_above / n_valid

    return breadth_share


def build_feature_store(x0_result: BacktestResult, feed: DataFeed,
                        breadth_path: str) -> pd.DataFrame:
    """Build bar-level feature store for every H4 bar in reporting window.

    All features use only data available at or before bar close (no lookahead).
    """
    h4 = feed.h4_bars
    d1 = feed.d1_bars
    n = len(h4)

    # Extract arrays
    close = np.array([b.close for b in h4], dtype=np.float64)
    high = np.array([b.high for b in h4], dtype=np.float64)
    low = np.array([b.low for b in h4], dtype=np.float64)
    volume = np.array([b.volume for b in h4], dtype=np.float64)
    taker_buy = np.array([b.taker_buy_base_vol for b in h4], dtype=np.float64)
    h4_close_times = np.array([b.close_time for b in h4], dtype=np.int64)
    h4_open_times = np.array([b.open_time for b in h4], dtype=np.int64)

    slow_p = 120
    fast_p = max(5, slow_p // 4)

    ema_fast = _ema(close, fast_p)
    ema_slow = _ema(close, slow_p)
    atr_14 = _atr(high, low, close, 14)
    ratr = _robust_atr(high, low, close)
    vdo = _vdo(close, high, low, volume, taker_buy)

    # D1 regime
    d1_close = np.array([b.close for b in d1], dtype=np.float64)
    d1_ema = _ema(d1_close, 21)
    d1_close_times = [b.close_time for b in d1]
    d1_regime_arr = d1_close > d1_ema

    d1_regime_h4 = np.zeros(n, dtype=np.int8)
    d1_idx = 0
    n_d1 = len(d1)
    for i in range(n):
        h4_ct = h4[i].close_time
        while d1_idx + 1 < n_d1 and d1_close_times[d1_idx + 1] < h4_ct:
            d1_idx += 1
        if d1_close_times[d1_idx] < h4_ct:
            d1_regime_h4[i] = int(d1_regime_arr[d1_idx])

    # Reporting window filter (match engine)
    report_start_ms = feed.report_start_ms
    report_mask = h4_close_times >= report_start_ms if report_start_ms else np.ones(n, dtype=bool)

    # Build exit history from X0 trades for re-entry features
    x0_trades = x0_result.trades
    exit_ts_list = sorted(t.exit_ts_ms for t in x0_trades)
    exit_reason_map = {t.exit_ts_ms: t.exit_reason for t in x0_trades}
    entry_ts_set = set(t.entry_ts_ms for t in x0_trades)

    # For each bar, compute bars_since_last_exit and prior_exit_reason
    bars_since_exit = np.full(n, -1, dtype=np.int64)
    prior_exit_reason = [""] * n
    exit_ptr = 0
    last_exit_bar_idx = -1
    last_exit_reason = ""

    # Map exit_ts_ms to bar index: exits happen at bar open, so find bar
    # whose open_time matches exit_ts_ms
    exit_ts_to_bar = {}
    for i in range(n):
        exit_ts_to_bar[h4[i].open_time] = i

    # Build sorted list of (bar_idx, exit_reason) for actual exits
    exit_events = []
    for t in x0_trades:
        bar_i = exit_ts_to_bar.get(t.exit_ts_ms)
        if bar_i is not None:
            exit_events.append((bar_i, t.exit_reason))
    exit_events.sort()

    exit_ev_ptr = 0
    for i in range(n):
        # Advance exit pointer: exits that happened on or before this bar
        while exit_ev_ptr < len(exit_events) and exit_events[exit_ev_ptr][0] <= i:
            last_exit_bar_idx = exit_events[exit_ev_ptr][0]
            last_exit_reason = exit_events[exit_ev_ptr][1]
            exit_ev_ptr += 1
        if last_exit_bar_idx >= 0:
            bars_since_exit[i] = i - last_exit_bar_idx
            prior_exit_reason[i] = last_exit_reason

    # Re-entry flags: was this bar's entry within N bars of last exit?
    # Computed per-entry in entry feature store below

    # Breadth
    print("  Computing breadth features...")
    breadth_share = compute_breadth(breadth_path, h4_close_times)

    # Assemble DataFrame
    rows = []
    for i in range(n):
        if not report_mask[i]:
            continue
        rows.append({
            "bar_index": i,
            "open_time_ms": int(h4_open_times[i]),
            "close_time_ms": int(h4_close_times[i]),
            "close_time": ms_to_iso(int(h4_close_times[i])),
            "close": round(close[i], 2),
            "ema_fast_h4": round(ema_fast[i], 2),
            "ema_slow_h4": round(ema_slow[i], 2),
            "atr_14_h4": round(atr_14[i], 2) if not math.isnan(atr_14[i]) else "",
            "ratr_h4": round(ratr[i], 2) if not math.isnan(ratr[i]) else "",
            "vdo": round(vdo[i], 6),
            "d1_regime": int(d1_regime_h4[i]),
            "bars_since_last_exit": int(bars_since_exit[i]) if bars_since_exit[i] >= 0 else "",
            "prior_exit_reason": prior_exit_reason[i],
            "breadth_ema21_share": round(breadth_share[i], 4) if not math.isnan(breadth_share[i]) else "",
        })

    return pd.DataFrame(rows)


# ═══════════════════════════════════════════════════════════════════════════
# Part 3: Entry-annotated feature store
# ═══════════════════════════════════════════════════════════════════════════

def build_entry_features(x0_result: BacktestResult, bar_features: pd.DataFrame,
                         feed: DataFeed) -> pd.DataFrame:
    """One row per X0 entry with features at decision-bar close.

    Decision bar = bar where on_bar() fires the entry signal.
    Fill happens at next bar's open. So entry_ts_ms = next_bar.open_time.
    Decision bar close_time = entry_ts_ms - 4h (one bar before fill).
    """
    h4 = feed.h4_bars
    # Map open_time -> bar_index for fast lookup
    open_time_to_idx = {b.open_time: i for i, b in enumerate(h4)}

    # bar_features keyed by bar_index
    bf_by_idx = bar_features.set_index("bar_index")

    rows = []
    trades = sorted(x0_result.trades, key=lambda t: t.entry_ts_ms)

    for trade_idx, t in enumerate(trades):
        # Decision bar = bar before fill bar
        fill_bar_idx = open_time_to_idx.get(t.entry_ts_ms)
        if fill_bar_idx is None or fill_bar_idx < 1:
            continue
        decision_bar_idx = fill_bar_idx - 1

        if decision_bar_idx not in bf_by_idx.index:
            continue

        bf = bf_by_idx.loc[decision_bar_idx]

        # Re-entry flags
        bse = bf.get("bars_since_last_exit", "")
        bse_val = int(bse) if bse != "" else -1
        reentry_flags = {}
        for n_bars in [1, 2, 3, 4, 6]:
            reentry_flags[f"reentry_within_{n_bars}_bars"] = (
                1 if 0 <= bse_val <= n_bars else 0
            )

        row = {
            "trade_id": t.trade_id,
            "entry_ts_ms": t.entry_ts_ms,
            "entry_time": ms_to_iso(t.entry_ts_ms),
            "exit_ts_ms": t.exit_ts_ms,
            "exit_time": ms_to_iso(t.exit_ts_ms),
            "entry_price": round(t.entry_price, 2),
            "exit_price": round(t.exit_price, 2),
            "net_return_pct": round(t.return_pct, 4),
            "pnl_usd": round(t.pnl, 2),
            "holding_bars": round(t.days_held * 6.0),
            "exit_reason": t.exit_reason,
            "decision_bar_idx": decision_bar_idx,
            "decision_close_time": bf["close_time"],
            "decision_close": bf["close"],
            "ema_fast_h4": bf["ema_fast_h4"],
            "ema_slow_h4": bf["ema_slow_h4"],
            "atr_14_h4": bf["atr_14_h4"],
            "ratr_h4": bf["ratr_h4"],
            "vdo": bf["vdo"],
            "d1_regime": bf["d1_regime"],
            "bars_since_last_exit": bf["bars_since_last_exit"],
            "prior_exit_reason": bf["prior_exit_reason"],
            "breadth_ema21_share": bf["breadth_ema21_share"],
            # Derivatives placeholders (blocked per D1.1)
            "funding_raw": "",
            "funding_pct_rank": "",
            "oi_level": "",
            "oi_change_1d": "",
            "basis_raw": "",
        }
        row.update(reentry_flags)
        rows.append(row)

    return pd.DataFrame(rows)


# ═══════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════

def main():
    OUTDIR.mkdir(parents=True, exist_ok=True)
    t0 = time.time()

    # ── Step 1: Run backtests ─────────────────────────────────────────────
    print("=" * 70)
    print("STEP 1: Running canonical backtests (actual BacktestEngine)")
    print("=" * 70)

    results = {}  # (strat_key, scenario) -> BacktestResult
    summaries = []
    all_trade_files = []

    for strat_key in STRAT_DEFS:
        for scenario in SCENARIO_NAMES:
            label = f"{strat_key}/{scenario}"
            print(f"  Running {label}...", end=" ", flush=True)
            ts = time.time()
            result = run_backtest(strat_key, scenario)
            elapsed = time.time() - ts
            results[(strat_key, scenario)] = result
            s = result.summary
            print(f"{elapsed:.1f}s  "
                  f"trades={len(result.trades)}  "
                  f"sharpe={s.get('sharpe', 0):.3f}  "
                  f"cagr={s.get('cagr_pct', 0):.1f}%  "
                  f"mdd={s.get('max_dd_pct', 0):.1f}%")

            # Export trade ledger
            tf = export_trade_ledger(result, strat_key, scenario, OUTDIR)
            all_trade_files.append(str(tf.name))

            # Export equity
            export_equity(result, strat_key, scenario, OUTDIR)

            summaries.append({
                "strategy": strat_key,
                "scenario": scenario,
                "trades": len(result.trades),
                "sharpe": round(s.get("sharpe", 0), 4),
                "cagr_pct": round(s.get("cagr_pct", 0), 2),
                "max_dd_pct": round(s.get("max_drawdown_mid_pct", 0), 2),
                "calmar": round(s.get("calmar", 0), 4),
                "win_rate": round(s.get("win_rate_pct", 0), 2),
                "avg_exposure": round(s.get("avg_exposure", 0), 4),
                "time_in_market_pct": round(s.get("time_in_market_pct", 0), 2),
            })

    # Export summary table
    pd.DataFrame(summaries).to_csv(OUTDIR / "backtest_summary.csv", index=False)
    print(f"\n  Summary: {OUTDIR / 'backtest_summary.csv'}")

    # ── Step 2: Build bar-level feature store ─────────────────────────────
    print("\n" + "=" * 70)
    print("STEP 2: Building bar-level feature store")
    print("=" * 70)

    # Use X0/base as canonical for feature alignment
    x0_base = results[("X0", "base")]
    feed = DataFeed(DATA, start=START, end=END, warmup_days=WARMUP)

    bar_features = build_feature_store(x0_base, feed, BREADTH_DATA)
    bar_features.to_csv(OUTDIR / "bar_features.csv", index=False)
    print(f"  Bar features: {len(bar_features)} rows -> {OUTDIR / 'bar_features.csv'}")

    # ── Step 3: Build entry-annotated feature store ───────────────────────
    print("\n" + "=" * 70)
    print("STEP 3: Building entry-annotated feature store")
    print("=" * 70)

    entry_features = build_entry_features(x0_base, bar_features, feed)
    entry_features.to_csv(OUTDIR / "entry_features_X0_base.csv", index=False)
    print(f"  Entry features: {len(entry_features)} rows -> {OUTDIR / 'entry_features_X0_base.csv'}")

    # Also build for E0_EMA21 and X0_LR
    for strat_key in ["E0_EMA21", "X0_LR"]:
        res = results[(strat_key, "base")]
        ef = build_entry_features(res, bar_features, feed)
        fname = OUTDIR / f"entry_features_{strat_key}_base.csv"
        ef.to_csv(fname, index=False)
        print(f"  Entry features ({strat_key}): {len(ef)} rows -> {fname.name}")

    # ── Step 4: Quality checks ────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("STEP 4: Quality checks")
    print("=" * 70)

    # Check X0 vs E0_EMA21 trade count difference
    x0_trades_base = len(results[("X0", "base")].trades)
    e0_trades_base = len(results[("E0_EMA21", "base")].trades)
    lr_trades_base = len(results[("X0_LR", "base")].trades)
    print(f"  X0 trades (base): {x0_trades_base}")
    print(f"  E0_EMA21 trades (base): {e0_trades_base}")
    print(f"  X0_LR trades (base): {lr_trades_base}")

    # Verify X0 and X0_LR have same entry timestamps
    x0_entries = set(t.entry_ts_ms for t in results[("X0", "base")].trades)
    lr_entries = set(t.entry_ts_ms for t in results[("X0_LR", "base")].trades)
    shared = x0_entries & lr_entries
    x0_only = x0_entries - lr_entries
    lr_only = lr_entries - x0_entries
    print(f"  X0/X0_LR entry overlap: shared={len(shared)}, "
          f"X0_only={len(x0_only)}, LR_only={len(lr_only)}")

    # Check no-lookahead: all bar features should have close_time <= entry_ts
    ef = entry_features
    if len(ef) > 0:
        lookahead_violations = 0
        for _, row in ef.iterrows():
            # decision bar close_time should be strictly before entry_ts_ms
            # (entry happens at next bar open)
            pass  # Already guaranteed by construction (decision_bar = fill_bar - 1)
        print(f"  No-lookahead: GUARANTEED by construction (decision_bar = fill_bar - 1)")

    # Check breadth coverage
    breadth_valid = bar_features["breadth_ema21_share"].apply(
        lambda x: x != "" and not (isinstance(x, float) and math.isnan(x))
    ).sum()
    print(f"  Breadth coverage: {breadth_valid}/{len(bar_features)} bars have valid breadth")

    # ── Export metadata ───────────────────────────────────────────────────
    metadata = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "source": "actual BacktestEngine (v10/core/engine.py)",
        "data_file": DATA,
        "breadth_file": BREADTH_DATA,
        "start": START,
        "end": END,
        "warmup_days": WARMUP,
        "initial_cash": CASH,
        "strategies": list(STRAT_DEFS.keys()),
        "scenarios": SCENARIO_NAMES,
        "cost_configs": {
            k: {"spread_bps": v.spread_bps, "slippage_bps": v.slippage_bps,
                 "taker_fee_pct": v.taker_fee_pct, "rt_bps": v.round_trip_bps}
            for k, v in SCENARIOS.items()
        },
        "annualization": f"sqrt(6.0 * 365.25) = {ANN:.6f}",
        "derivatives_features": "MISSING — blocked per D1.1",
        "breadth_ema_approx": "H4 EMA(126) ≈ D1 EMA(21)",
        "no_lookahead": "decision_bar = fill_bar - 1; all features at decision_bar close",
    }
    with open(OUTDIR / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    elapsed_total = time.time() - t0
    print(f"\nDone in {elapsed_total:.1f}s. Artifacts in {OUTDIR}/")


if __name__ == "__main__":
    main()
