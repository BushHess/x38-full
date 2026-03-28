#!/usr/bin/env python3
"""Exp 14: E5-ema21D1 vs Gen4 C3 Head-to-Head.

Compares the project's primary algorithm (E5-ema21D1, H4 trend-following)
against Gen4's champion (C3, D1 trade-surprise + H4 rangepos + 15m relvol).

Same data (2019-01-01 to 2026-02-20), same cost (50 bps RT), same capital.

C3 uses 15m decision bars with D1 + H4 + 15m features (no trail stop).
E5 uses H4 decision bars with H4 + D1 features (ATR trail + EMA exit).

Usage:
    python -m research.x39.experiments.exp14_vs_gen4c3
    # or from x39/:
    python experiments/exp14_vs_gen4c3.py
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]  # btc-spot-dev/
sys.path.insert(0, str(ROOT))

from research.x39.explore import compute_features, load_data  # noqa: E402

DATA_15M = ROOT / "data" / "bars_btcusdt_2017_now_15m.csv"
RESULTS_DIR = Path(__file__).resolve().parents[1] / "results"

# ── Shared constants ──────────────────────────────────────────────────
EVAL_START = datetime(2019, 1, 1)
EVAL_END = datetime(2026, 2, 20)
EVAL_START_MS = int(EVAL_START.timestamp() * 1000)
EVAL_END_MS = int(datetime(2026, 2, 20, 23, 59, 59).timestamp() * 1000)
COST_BPS = 50
SIDE_COST = COST_BPS / 20_000  # 0.0025 per side
INITIAL_CASH = 10_000.0

# ── E5-ema21D1 parameters ────────────────────────────────────────────
E5_SLOW = 120
E5_TRAIL = 3.0

# ── C3 parameters (frozen champion cfg_025) ──────────────────────────
C3_ENTRY_THRESH = 0.65   # h4_rangepos168 >= this to enter
C3_HOLD_THRESH = 0.35    # h4_rangepos168 >= this to hold
C3_RELVOL_THRESH = 1.10  # m15_relvol168 >= this to enter
C3_WINDOW = 168           # rolling window for all features

# ── Regime periods ────────────────────────────────────────────────────
REGIMES = {
    "bull_2020_2021": (datetime(2020, 1, 1), datetime(2021, 12, 31)),
    "bear_2022": (datetime(2022, 1, 1), datetime(2022, 12, 31)),
    "recovery_2023_2024": (datetime(2023, 1, 1), datetime(2024, 12, 31)),
    "recent_2025_2026": (datetime(2025, 1, 1), datetime(2026, 2, 20)),
}


# ═══════════════════════════════════════════════════════════════════════
# Data loading
# ═══════════════════════════════════════════════════════════════════════

def load_15m() -> pd.DataFrame:
    """Load 15m bars from CSV."""
    raw = pd.read_csv(DATA_15M)
    raw["datetime"] = pd.to_datetime(raw["open_time"], unit="ms")
    m15 = raw.sort_values("open_time").reset_index(drop=True)
    print(f"Loaded {len(m15):,} 15m bars: {m15['datetime'].iloc[0]} → {m15['datetime'].iloc[-1]}")
    return m15


# ═══════════════════════════════════════════════════════════════════════
# Metrics
# ═══════════════════════════════════════════════════════════════════════

def compute_metrics(
    daily: pd.DataFrame, trades: list[dict], exposure: float,
) -> dict:
    """Compute strategy metrics from daily equity and trade list."""
    eq = daily["equity"].values
    days = len(eq)
    years = days / 365.25

    rets = np.diff(eq) / eq[:-1]

    sharpe = (
        np.mean(rets) / np.std(rets) * np.sqrt(365.25)
        if np.std(rets) > 0 else 0.0
    )
    final_ret = eq[-1] / eq[0]
    cagr = final_ret ** (1 / years) - 1 if years > 0 and final_ret > 0 else 0.0

    cummax = np.maximum.accumulate(eq)
    dd = (eq - cummax) / cummax
    mdd = np.min(dd)

    calmar = cagr / abs(mdd) if abs(mdd) > 1e-10 else 0.0

    n_trades = len(trades)
    if n_trades > 0:
        tdf = pd.DataFrame(trades)
        wins = tdf[tdf["win"] == 1]
        losses = tdf[tdf["win"] == 0]
    else:
        wins = losses = pd.DataFrame()

    return {
        "sharpe": round(sharpe, 4),
        "cagr_pct": round(cagr * 100, 2),
        "mdd_pct": round(abs(mdd) * 100, 2),
        "calmar": round(calmar, 3),
        "trades": n_trades,
        "win_rate_pct": round(len(wins) / n_trades * 100, 1) if n_trades > 0 else 0.0,
        "avg_win_pct": round(wins["net_ret"].mean() * 100, 2) if len(wins) > 0 else np.nan,
        "avg_loss_pct": round(losses["net_ret"].mean() * 100, 2) if len(losses) > 0 else np.nan,
        "exposure_pct": round(exposure * 100, 1),
    }


def compute_regime_metrics(
    daily: pd.DataFrame, trades: list[dict],
) -> dict[str, dict]:
    """Per-regime breakdown of Sharpe, CAGR, MDD, trade count."""
    results = {}
    for name, (start, end) in REGIMES.items():
        mask = (daily["date"] >= pd.Timestamp(start)) & (daily["date"] <= pd.Timestamp(end))
        sub = daily[mask]
        if len(sub) < 10:
            results[name] = {"sharpe": np.nan, "cagr_pct": np.nan, "mdd_pct": np.nan, "trades": 0}
            continue

        eq = sub["equity"].values
        rets = np.diff(eq) / eq[:-1]
        years = len(eq) / 365.25

        sharpe = (
            np.mean(rets) / np.std(rets) * np.sqrt(365.25)
            if np.std(rets) > 0 else 0.0
        )
        final_ret = eq[-1] / eq[0]
        cagr = final_ret ** (1 / years) - 1 if years > 0 and final_ret > 0 else 0.0
        cummax = np.maximum.accumulate(eq)
        dd = (eq - cummax) / cummax
        mdd = np.min(dd)

        start_ms = int(start.timestamp() * 1000)
        end_ms = int(end.timestamp() * 1000) + 86_400_000 - 1
        n_trades = sum(1 for t in trades if start_ms <= t["entry_time_ms"] <= end_ms)

        results[name] = {
            "sharpe": round(sharpe, 4),
            "cagr_pct": round(cagr * 100, 2),
            "mdd_pct": round(abs(mdd) * 100, 2),
            "trades": n_trades,
        }
    return results


def to_daily(open_times: np.ndarray, equity: np.ndarray) -> pd.DataFrame:
    """Resample bar-level equity to end-of-day."""
    valid = pd.DataFrame({"open_time": open_times, "equity": equity}).dropna()
    valid["date"] = pd.to_datetime(valid["open_time"], unit="ms").dt.normalize()
    daily = valid.groupby("date")["equity"].last().reset_index()
    return daily


# ═══════════════════════════════════════════════════════════════════════
# E5-ema21D1 Backtest
# ═══════════════════════════════════════════════════════════════════════

def run_e5(
    h4: pd.DataFrame, d1: pd.DataFrame,
) -> tuple[pd.DataFrame, list[dict], float]:
    """Replay E5-ema21D1 on H4 bars. Returns (daily_equity, trades, exposure)."""
    feat = compute_features(h4, d1)

    c = feat["close"].values
    ema_f = feat["ema_fast"].values
    ema_s = feat["ema_slow"].values
    ratr = feat["ratr"].values
    vdo_arr = feat["vdo"].values
    d1_ok = feat["d1_regime_ok"].values
    ot = h4["open_time"].values
    n = len(c)

    # First tradable bar: warm indicators AND inside eval window
    start_idx = 0
    for i in range(n):
        if ot[i] >= EVAL_START_MS and np.isfinite(ratr[i]):
            start_idx = max(E5_SLOW, i)
            break

    trades: list[dict] = []
    in_pos = False
    peak = 0.0
    entry_bar = 0
    entry_price = 0.0

    equity = np.full(n, np.nan)
    cash = INITIAL_CASH
    pos_units = 0.0
    bars_in_pos = 0
    total_bars = 0

    for i in range(start_idx, n):
        if ot[i] > EVAL_END_MS:
            break
        total_bars += 1

        if np.isnan(ratr[i]):
            equity[i] = cash if not in_pos else pos_units * c[i]
            if in_pos:
                bars_in_pos += 1
            continue

        if not in_pos:
            equity[i] = cash
            if ema_f[i] > ema_s[i] and vdo_arr[i] > 0 and d1_ok[i]:
                in_pos = True
                entry_bar = i
                entry_price = c[i]
                peak = c[i]
                pos_units = cash * (1 - SIDE_COST) / c[i]
                cash = 0.0
        else:
            bars_in_pos += 1
            equity[i] = pos_units * c[i]
            peak = max(peak, c[i])
            trail_stop = peak - E5_TRAIL * ratr[i]
            exit_reason = None

            if c[i] < trail_stop:
                exit_reason = "trail"
            elif ema_f[i] < ema_s[i]:
                exit_reason = "trend"

            if exit_reason:
                cash = pos_units * c[i] * (1 - SIDE_COST)
                gross_ret = (c[i] - entry_price) / entry_price
                net_ret = gross_ret - COST_BPS / 10_000

                trades.append({
                    "entry_time_ms": int(ot[entry_bar]),
                    "exit_time_ms": int(ot[i]),
                    "entry_price": entry_price,
                    "exit_price": c[i],
                    "gross_ret": gross_ret,
                    "net_ret": net_ret,
                    "win": int(net_ret > 0),
                })

                equity[i] = cash
                pos_units = 0.0
                in_pos = False
                peak = 0.0

    exposure = bars_in_pos / total_bars if total_bars > 0 else 0.0
    daily = to_daily(ot, equity)
    return daily, trades, exposure


# ═══════════════════════════════════════════════════════════════════════
# Gen4 C3 Feature Computation
# ═══════════════════════════════════════════════════════════════════════

def compute_c3_d1_trade_surprise(d1: pd.DataFrame) -> np.ndarray:
    """D1 trade_surprise_168 per C3 frozen spec.

    Model fit on all D1 bars with close_time < EVAL_START_MS.
    """
    v = d1["volume"].values.astype(np.float64)
    nt = d1["num_trades"].values.astype(np.float64)
    ct = d1["close_time"].values

    fit_mask = ct < EVAL_START_MS
    if fit_mask.sum() < 2:
        n_fit = min(max(2, len(v)), 365)
        fit_v, fit_nt = v[:n_fit], nt[:n_fit]
    else:
        fit_v, fit_nt = v[fit_mask], nt[fit_mask]

    x = np.log1p(fit_v)
    y = np.log1p(fit_nt)
    x_mean, y_mean = x.mean(), y.mean()
    x_var = ((x - x_mean) ** 2).mean()
    beta = ((x - x_mean) * (y - y_mean)).mean() / x_var if x_var > 0 else 0.0
    alpha = y_mean - beta * x_mean

    print(f"  D1 trade model: alpha={alpha:.4f}, beta={beta:.4f} "
          f"(fit on {fit_mask.sum()} D1 bars before {EVAL_START.date()})")

    eps = np.log1p(nt) - (alpha + beta * np.log1p(v))
    eps_mean = pd.Series(eps).rolling(C3_WINDOW, min_periods=C3_WINDOW).mean().values
    return eps - eps_mean


def compute_c3_h4_rangepos(h4: pd.DataFrame) -> np.ndarray:
    """H4 rangepos_168 per C3 frozen spec."""
    hi = h4["high"].values.astype(np.float64)
    lo = h4["low"].values.astype(np.float64)
    c = h4["close"].values.astype(np.float64)

    roll_hi = pd.Series(hi).rolling(C3_WINDOW, min_periods=C3_WINDOW).max().values
    roll_lo = pd.Series(lo).rolling(C3_WINDOW, min_periods=C3_WINDOW).min().values
    denom = roll_hi - roll_lo
    return np.where(denom > 1e-10, (c - roll_lo) / denom, np.nan)


def compute_c3_m15_relvol(m15: pd.DataFrame) -> np.ndarray:
    """15m relvol_168 per C3 frozen spec."""
    v = m15["volume"].values.astype(np.float64)
    v_mean = pd.Series(v).rolling(C3_WINDOW, min_periods=C3_WINDOW).mean().values
    return np.where((v_mean > 0) & np.isfinite(v_mean), v / v_mean, np.nan)


# ═══════════════════════════════════════════════════════════════════════
# Gen4 C3 Backtest
# ═══════════════════════════════════════════════════════════════════════

def run_c3(
    m15: pd.DataFrame, h4: pd.DataFrame, d1: pd.DataFrame,
) -> tuple[pd.DataFrame, list[dict], float]:
    """Replay Gen4 C3 on 15m decision bars. Returns (daily_equity, trades, exposure)."""
    # ── Compute features ──────────────────────────────────────────────
    d1_ts = compute_c3_d1_trade_surprise(d1)
    h4_rp = compute_c3_h4_rangepos(h4)
    m15_rv = compute_c3_m15_relvol(m15)

    d1_ct = d1["close_time"].values
    h4_ct = h4["close_time"].values
    m15_ct = m15["close_time"].values
    m15_ot = m15["open_time"].values
    m15_close = m15["close"].values.astype(np.float64)
    n = len(m15_close)

    # ── Align D1/H4 features to M15 grid (vectorised) ────────────────
    # For each M15 bar, find latest fully closed D1/H4 bar
    d1_idx = np.clip(np.searchsorted(d1_ct, m15_ct, side="right") - 1, 0, len(d1_ct) - 1)
    d1_ts_m15 = np.where(d1_ct[d1_idx] <= m15_ct, d1_ts[d1_idx], np.nan)

    h4_idx = np.clip(np.searchsorted(h4_ct, m15_ct, side="right") - 1, 0, len(h4_ct) - 1)
    h4_rp_m15 = np.where(h4_ct[h4_idx] <= m15_ct, h4_rp[h4_idx], np.nan)

    print(f"  D1 trade_surprise aligned: {np.isfinite(d1_ts_m15).sum():,}/{n:,} valid")
    print(f"  H4 rangepos aligned:       {np.isfinite(h4_rp_m15).sum():,}/{n:,} valid")
    print(f"  M15 relvol:                {np.isfinite(m15_rv).sum():,}/{n:,} valid")

    # ── Simulation ────────────────────────────────────────────────────
    current_pos = 0
    entry_price = 0.0
    entry_time_ms = 0

    trades: list[dict] = []
    equity = np.full(n, np.nan)
    cash = INITIAL_CASH
    pos_units = 0.0
    bars_in_pos = 0
    total_bars = 0

    for i in range(n):
        # Only trade within eval window (bar close >= start, open <= end)
        if m15_ct[i] < EVAL_START_MS:
            continue
        if m15_ot[i] > EVAL_END_MS:
            break

        total_bars += 1

        d1_perm = d1_ts_m15[i]
        h4_ctx = h4_rp_m15[i]
        m15_vol = m15_rv[i]

        if current_pos == 0:
            equity[i] = cash
            # Entry: all three layers must agree
            if (np.isfinite(d1_perm) and d1_perm > 0.0
                    and np.isfinite(h4_ctx) and h4_ctx >= C3_ENTRY_THRESH
                    and np.isfinite(m15_vol) and m15_vol >= C3_RELVOL_THRESH):
                current_pos = 1
                entry_price = m15_close[i]
                entry_time_ms = int(m15_ct[i])
                pos_units = cash * (1 - SIDE_COST) / entry_price
                cash = 0.0
        else:
            bars_in_pos += 1
            equity[i] = pos_units * m15_close[i]
            # Hold: D1 permission AND H4 context (15m relvol NOT checked for hold)
            hold = (np.isfinite(d1_perm) and d1_perm > 0.0
                    and np.isfinite(h4_ctx) and h4_ctx >= C3_HOLD_THRESH)
            if not hold:
                current_pos = 0
                exit_price = m15_close[i]
                exit_cash = pos_units * exit_price * (1 - SIDE_COST)
                gross_ret = (exit_price - entry_price) / entry_price
                net_ret = gross_ret - COST_BPS / 10_000

                trades.append({
                    "entry_time_ms": entry_time_ms,
                    "exit_time_ms": int(m15_ct[i]),
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "gross_ret": gross_ret,
                    "net_ret": net_ret,
                    "win": int(net_ret > 0),
                })

                cash = exit_cash
                pos_units = 0.0
                equity[i] = cash

    exposure = bars_in_pos / total_bars if total_bars > 0 else 0.0
    daily = to_daily(m15_ot, equity)
    return daily, trades, exposure


# ═══════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════

def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("EXP 14: E5-ema21D1 vs Gen4 C3 — Head-to-Head")
    print("=" * 80)
    print(f"Period: {EVAL_START.date()} → {EVAL_END.date()}")
    print(f"Cost: {COST_BPS} bps RT (harsh)  |  Capital: ${INITIAL_CASH:,.0f}")
    print()

    # ── Load data ─────────────────────────────────────────────────────
    h4, d1 = load_data()
    m15 = load_15m()
    print()

    # ── Run E5-ema21D1 ────────────────────────────────────────────────
    print("── E5-ema21D1 (H4 decision, EMA + ATR trail + VDO + D1 regime) " + "─" * 16)
    e5_daily, e5_trades, e5_exp = run_e5(h4, d1)
    e5 = compute_metrics(e5_daily, e5_trades, e5_exp)
    print(f"  Sharpe={e5['sharpe']}, CAGR={e5['cagr_pct']}%, MDD={e5['mdd_pct']}%, "
          f"Trades={e5['trades']}, WR={e5['win_rate_pct']}%, Exp={e5['exposure_pct']}%")
    print()

    # ── Run Gen4 C3 ───────────────────────────────────────────────────
    print("── Gen4 C3 (15m decision, trade-surprise + rangepos + relvol) " + "─" * 17)
    c3_daily, c3_trades, c3_exp = run_c3(m15, h4, d1)
    c3 = compute_metrics(c3_daily, c3_trades, c3_exp)
    print(f"  Sharpe={c3['sharpe']}, CAGR={c3['cagr_pct']}%, MDD={c3['mdd_pct']}%, "
          f"Trades={c3['trades']}, WR={c3['win_rate_pct']}%, Exp={c3['exposure_pct']}%")
    print()

    # ── Side-by-side comparison ───────────────────────────────────────
    print("=" * 80)
    print("COMPARISON")
    print("=" * 80)

    metrics_order = [
        "sharpe", "cagr_pct", "mdd_pct", "calmar", "trades",
        "win_rate_pct", "avg_win_pct", "avg_loss_pct", "exposure_pct",
    ]
    labels = {
        "sharpe": "Sharpe", "cagr_pct": "CAGR %", "mdd_pct": "MDD %",
        "calmar": "Calmar", "trades": "Trades", "win_rate_pct": "Win Rate %",
        "avg_win_pct": "Avg Win %", "avg_loss_pct": "Avg Loss %",
        "exposure_pct": "Exposure %",
    }

    print(f"\n  {'Metric':<15s}  {'E5-ema21D1':>12s}  {'Gen4 C3':>12s}  {'Delta':>12s}  {'Winner':>10s}")
    print("  " + "-" * 65)
    for m in metrics_order:
        e5v = e5[m]
        c3v = c3[m]
        if np.isnan(e5v) or np.isnan(c3v):
            delta_s = ""
            winner = ""
        else:
            delta = c3v - e5v
            delta_s = f"{delta:+.2f}"
            # For MDD and avg_loss, lower absolute value is better
            if m == "mdd_pct":
                winner = "C3" if c3v < e5v else "E5" if e5v < c3v else "TIE"
            elif m == "avg_loss_pct":
                winner = "C3" if c3v > e5v else "E5" if e5v > c3v else "TIE"  # less negative = better
            elif m in ("sharpe", "cagr_pct", "calmar", "win_rate_pct", "avg_win_pct"):
                winner = "C3" if c3v > e5v else "E5" if e5v > c3v else "TIE"
            else:
                winner = ""
        print(f"  {labels[m]:<15s}  {e5v:>12.2f}  {c3v:>12.2f}  {delta_s:>12s}  {winner:>10s}")

    # ── Regime breakdown ──────────────────────────────────────────────
    print()
    print("=" * 80)
    print("REGIME BREAKDOWN")
    print("=" * 80)

    e5_reg = compute_regime_metrics(e5_daily, e5_trades)
    c3_reg = compute_regime_metrics(c3_daily, c3_trades)

    print(f"\n  {'Regime':<23s}  {'E5 Sh':>7s}  {'C3 Sh':>7s}  "
          f"{'E5 CAGR':>8s}  {'C3 CAGR':>8s}  "
          f"{'E5 MDD':>7s}  {'C3 MDD':>7s}  "
          f"{'E5 #T':>5s}  {'C3 #T':>5s}")
    print("  " + "-" * 85)
    for regime in REGIMES:
        e5r = e5_reg[regime]
        c3r = c3_reg[regime]
        print(f"  {regime:<23s}  {e5r['sharpe']:7.3f}  {c3r['sharpe']:7.3f}  "
              f"{e5r['cagr_pct']:7.1f}%  {c3r['cagr_pct']:7.1f}%  "
              f"{e5r['mdd_pct']:6.1f}%  {c3r['mdd_pct']:6.1f}%  "
              f"{e5r['trades']:5d}  {c3r['trades']:5d}")

    # ── Equity endpoints ──────────────────────────────────────────────
    print(f"\n  Equity: E5 ${e5_daily['equity'].iloc[0]:,.0f} → ${e5_daily['equity'].iloc[-1]:,.0f}"
          f"  |  C3 ${c3_daily['equity'].iloc[0]:,.0f} → ${c3_daily['equity'].iloc[-1]:,.0f}")

    # ── Save results ──────────────────────────────────────────────────
    rows = []
    for name, metrics, reg in [("E5_ema21D1", e5, e5_reg), ("Gen4_C3", c3, c3_reg)]:
        row = {"strategy": name}
        row.update(metrics)
        rows.append(row)
        for regime in REGIMES:
            rrow = {"strategy": f"{name}_{regime}"}
            rrow.update(reg[regime])
            rows.append(rrow)

    out_df = pd.DataFrame(rows)
    out_path = RESULTS_DIR / "exp14_results.csv"
    out_df.to_csv(out_path, index=False)
    print(f"\n  -> Saved to {out_path}")

    # ── Verdict ───────────────────────────────────────────────────────
    print()
    print("=" * 80)
    print("VERDICT")
    print("=" * 80)

    d_sh = c3["sharpe"] - e5["sharpe"]
    d_cagr = c3["cagr_pct"] - e5["cagr_pct"]
    d_mdd = c3["mdd_pct"] - e5["mdd_pct"]

    print(f"  dSharpe (C3 - E5): {d_sh:+.4f}")
    print(f"  dCAGR:             {d_cagr:+.2f} pp")
    print(f"  dMDD:              {d_mdd:+.2f} pp  ({'C3 better' if d_mdd < 0 else 'E5 better'})")

    if d_sh > 0 and d_mdd < 0:
        print("\n  C3 DOMINATES: higher Sharpe AND lower MDD.")
    elif d_sh < 0 and d_mdd > 0:
        print("\n  E5 DOMINATES: higher Sharpe AND lower MDD.")
    elif d_sh > 0:
        print(f"\n  MIXED: C3 higher Sharpe (+{d_sh:.4f}) but worse MDD ({d_mdd:+.2f} pp).")
    elif d_sh < 0:
        print(f"\n  MIXED: E5 higher Sharpe ({abs(d_sh):.4f}) but C3 better MDD ({d_mdd:+.2f} pp).")
    else:
        print("\n  TIE on Sharpe.")

    print(f"\n  Architecture:")
    print(f"    E5:  EMA crossover + ATR trail stop + VDO filter + D1 EMA regime")
    print(f"    C3:  D1 trade-surprise permission + H4 rangepos context + 15m relvol timing")
    print(f"    C3 has NO trail stop. Exit = rangepos < {C3_HOLD_THRESH} OR trade_surprise <= 0.")
    print(f"    E5 decides at H4 ({e5['trades']} trades), C3 at 15m ({c3['trades']} trades).")


if __name__ == "__main__":
    main()
