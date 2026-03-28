#!/usr/bin/env python3
"""Exp 15: E5-ema21D1 vs Gen1 V6 (S3_H4_RET168_Z0) Head-to-Head.

Compares the project's primary algorithm (E5-ema21D1, H4 trend-following)
against Gen1's frozen winner (V6, single-feature ret_168 momentum).

Same data (2019-01-01 to 2026-02-20), same cost (50 bps RT), same capital.

V6 is maximally simple: ret_168 > 0 → long, else flat. One feature, zero threshold.
No trail stop. No VDO. No D1 regime. Just 168-bar return momentum on H4.

Usage:
    python -m research.x39.experiments.exp15_vs_gen1v6
    # or from x39/:
    python experiments/exp15_vs_gen1v6.py
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

# ── Gen1 V6 parameters ───────────────────────────────────────────────
V6_LOOKBACK = 168  # H4 bars for ret_168

# ── Regime periods ────────────────────────────────────────────────────
REGIMES = {
    "bull_2020_2021": (datetime(2020, 1, 1), datetime(2021, 12, 31)),
    "bear_2022": (datetime(2022, 1, 1), datetime(2022, 12, 31)),
    "recovery_2023_2024": (datetime(2023, 1, 1), datetime(2024, 12, 31)),
    "recent_2025_2026": (datetime(2025, 1, 1), datetime(2026, 2, 20)),
}


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
# Gen1 V6 Backtest
# ═══════════════════════════════════════════════════════════════════════

def run_v6(
    h4: pd.DataFrame,
) -> tuple[pd.DataFrame, list[dict], float]:
    """Replay Gen1 V6 (S3_H4_RET168_Z0) on H4 bars.

    Signal: ret_168 = close_t / close_(t-168) - 1
    Long if ret_168 > 0, else flat.
    Entry/exit at next bar open (simulated as bar close here, same as E5).

    Returns (daily_equity, trades, exposure).
    """
    c = h4["close"].values.astype(np.float64)
    ot = h4["open_time"].values
    n = len(c)

    # Compute ret_168
    ret168 = np.full(n, np.nan)
    for i in range(V6_LOOKBACK, n):
        ret168[i] = c[i] / c[i - V6_LOOKBACK] - 1

    # Signal: 1 if ret168 > 0, else 0
    signal = np.where(np.isfinite(ret168) & (ret168 > 0), 1, 0)

    # Find first bar with valid signal inside eval window
    start_idx = 0
    for i in range(n):
        if ot[i] >= EVAL_START_MS and np.isfinite(ret168[i]):
            start_idx = i
            break

    trades: list[dict] = []
    in_pos = False
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

        if not in_pos:
            equity[i] = cash
            # Entry: signal goes to 1
            if signal[i] == 1:
                in_pos = True
                entry_bar = i
                entry_price = c[i]
                pos_units = cash * (1 - SIDE_COST) / c[i]
                cash = 0.0
        else:
            bars_in_pos += 1
            equity[i] = pos_units * c[i]
            # Exit: signal goes to 0
            if signal[i] == 0:
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

    exposure = bars_in_pos / total_bars if total_bars > 0 else 0.0
    daily = to_daily(ot, equity)
    return daily, trades, exposure


# ═══════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════

def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("EXP 15: E5-ema21D1 vs Gen1 V6 (S3_H4_RET168_Z0) — Head-to-Head")
    print("=" * 80)
    print(f"Period: {EVAL_START.date()} → {EVAL_END.date()}")
    print(f"Cost: {COST_BPS} bps RT (harsh)  |  Capital: ${INITIAL_CASH:,.0f}")
    print(f"V6 spec: ret_168 = close_t / close_(t-168) - 1, long if > 0")
    print()

    # ── Load data ─────────────────────────────────────────────────────
    h4, d1 = load_data()
    print()

    # ── Run E5-ema21D1 ────────────────────────────────────────────────
    print("── E5-ema21D1 (H4 decision, EMA + ATR trail + VDO + D1 regime) " + "─" * 16)
    e5_daily, e5_trades, e5_exp = run_e5(h4, d1)
    e5 = compute_metrics(e5_daily, e5_trades, e5_exp)
    print(f"  Sharpe={e5['sharpe']}, CAGR={e5['cagr_pct']}%, MDD={e5['mdd_pct']}%, "
          f"Trades={e5['trades']}, WR={e5['win_rate_pct']}%, Exp={e5['exposure_pct']}%")
    print()

    # ── Run Gen1 V6 ──────────────────────────────────────────────────
    print("── Gen1 V6 (H4 decision, ret_168 > 0 → long) " + "─" * 33)
    v6_daily, v6_trades, v6_exp = run_v6(h4)
    v6 = compute_metrics(v6_daily, v6_trades, v6_exp)
    print(f"  Sharpe={v6['sharpe']}, CAGR={v6['cagr_pct']}%, MDD={v6['mdd_pct']}%, "
          f"Trades={v6['trades']}, WR={v6['win_rate_pct']}%, Exp={v6['exposure_pct']}%")
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

    print(f"\n  {'Metric':<15s}  {'E5-ema21D1':>12s}  {'Gen1 V6':>12s}  {'Delta':>12s}  {'Winner':>10s}")
    print("  " + "-" * 65)
    for m in metrics_order:
        e5v = e5[m]
        v6v = v6[m]
        if np.isnan(e5v) or np.isnan(v6v):
            delta_s = ""
            winner = ""
        else:
            delta = v6v - e5v
            delta_s = f"{delta:+.2f}"
            # For MDD and avg_loss, lower absolute value is better
            if m == "mdd_pct":
                winner = "V6" if v6v < e5v else "E5" if e5v < v6v else "TIE"
            elif m == "avg_loss_pct":
                winner = "V6" if v6v > e5v else "E5" if e5v > v6v else "TIE"  # less negative = better
            elif m in ("sharpe", "cagr_pct", "calmar", "win_rate_pct", "avg_win_pct"):
                winner = "V6" if v6v > e5v else "E5" if e5v > v6v else "TIE"
            else:
                winner = ""
        print(f"  {labels[m]:<15s}  {e5v:>12.2f}  {v6v:>12.2f}  {delta_s:>12s}  {winner:>10s}")

    # ── Regime breakdown ──────────────────────────────────────────────
    print()
    print("=" * 80)
    print("REGIME BREAKDOWN")
    print("=" * 80)

    e5_reg = compute_regime_metrics(e5_daily, e5_trades)
    v6_reg = compute_regime_metrics(v6_daily, v6_trades)

    print(f"\n  {'Regime':<23s}  {'E5 Sh':>7s}  {'V6 Sh':>7s}  "
          f"{'E5 CAGR':>8s}  {'V6 CAGR':>8s}  "
          f"{'E5 MDD':>7s}  {'V6 MDD':>7s}  "
          f"{'E5 #T':>5s}  {'V6 #T':>5s}")
    print("  " + "-" * 85)
    for regime in REGIMES:
        e5r = e5_reg[regime]
        v6r = v6_reg[regime]
        print(f"  {regime:<23s}  {e5r['sharpe']:7.3f}  {v6r['sharpe']:7.3f}  "
              f"{e5r['cagr_pct']:7.1f}%  {v6r['cagr_pct']:7.1f}%  "
              f"{e5r['mdd_pct']:6.1f}%  {v6r['mdd_pct']:6.1f}%  "
              f"{e5r['trades']:5d}  {v6r['trades']:5d}")

    # ── Equity endpoints ──────────────────────────────────────────────
    print(f"\n  Equity: E5 ${e5_daily['equity'].iloc[0]:,.0f} → ${e5_daily['equity'].iloc[-1]:,.0f}"
          f"  |  V6 ${v6_daily['equity'].iloc[0]:,.0f} → ${v6_daily['equity'].iloc[-1]:,.0f}")

    # ── Save results ──────────────────────────────────────────────────
    rows = []
    for name, metrics, reg in [("E5_ema21D1", e5, e5_reg), ("Gen1_V6", v6, v6_reg)]:
        row = {"strategy": name}
        row.update(metrics)
        rows.append(row)
        for regime in REGIMES:
            rrow = {"strategy": f"{name}_{regime}"}
            rrow.update(reg[regime])
            rows.append(rrow)

    out_df = pd.DataFrame(rows)
    out_path = RESULTS_DIR / "exp15_results.csv"
    out_df.to_csv(out_path, index=False)
    print(f"\n  -> Saved to {out_path}")

    # ── Verdict ───────────────────────────────────────────────────────
    print()
    print("=" * 80)
    print("VERDICT")
    print("=" * 80)

    d_sh = v6["sharpe"] - e5["sharpe"]
    d_cagr = v6["cagr_pct"] - e5["cagr_pct"]
    d_mdd = v6["mdd_pct"] - e5["mdd_pct"]

    print(f"  dSharpe (V6 - E5): {d_sh:+.4f}")
    print(f"  dCAGR:             {d_cagr:+.2f} pp")
    print(f"  dMDD:              {d_mdd:+.2f} pp  ({'V6 better' if d_mdd < 0 else 'E5 better'})")

    if d_sh > 0 and d_mdd < 0:
        print("\n  V6 DOMINATES: higher Sharpe AND lower MDD.")
    elif d_sh < 0 and d_mdd > 0:
        print("\n  E5 DOMINATES: higher Sharpe AND lower MDD.")
    elif d_sh > 0:
        print(f"\n  MIXED: V6 higher Sharpe (+{d_sh:.4f}) but worse MDD ({d_mdd:+.2f} pp).")
    elif d_sh < 0:
        print(f"\n  MIXED: E5 higher Sharpe ({abs(d_sh):.4f}) but V6 better MDD ({d_mdd:+.2f} pp).")
    else:
        print("\n  TIE on Sharpe.")

    print(f"\n  Architecture:")
    print(f"    E5:  EMA crossover + ATR trail stop + VDO filter + D1 EMA regime (4 params)")
    print(f"    V6:  ret_168 > 0 → long (1 param, zero threshold)")
    print(f"    V6 has NO trail stop. Exit = ret_168 crosses zero.")
    print(f"    Both decide at H4. E5: {e5['trades']} trades, V6: {v6['trades']} trades.")
    print(f"    V6 gen1 default cost was 20 bps RT; here run at 50 bps for fair comparison.")


if __name__ == "__main__":
    main()
