#!/usr/bin/env python3
"""Exp 33: Momentum Acceleration Gate.

Adds ema_spread_roc > min_accel to E5-ema21D1 entry.
  ema_spread = (ema_fast - ema_slow) / ema_slow
  ema_spread_roc = ema_spread[i] - ema_spread[i - lookback]

Sweeps lookback ∈ [3, 6, 12, 24] × min_accel ∈ [0.0, 0.001, 0.002] + baseline.
(4 × 3 = 12 configs + 1 baseline = 13 runs)

Usage:
    python -m research.x39.experiments.exp33_momentum_accel_gate
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]  # btc-spot-dev/
sys.path.insert(0, str(ROOT))

from research.x39.explore import compute_features, load_data  # noqa: E402

RESULTS_DIR = Path(__file__).resolve().parents[1] / "results"

# ── Strategy constants (match E5-ema21D1) ─────────────────────────────────
SLOW_PERIOD = 120
TRAIL_MULT = 3.0
COST_BPS = 50
INITIAL_CASH = 10_000.0

# ── Sweep grid ────────────────────────────────────────────────────────────
LOOKBACKS = [3, 6, 12, 24]
MIN_ACCELS = [0.0, 0.001, 0.002]


def run_backtest(
    feat: pd.DataFrame,
    lookback: int | None,
    min_accel: float | None,
    warmup_bar: int,
) -> dict:
    """Replay E5-ema21D1 with optional momentum acceleration gate."""
    c = feat["close"].values
    ema_f = feat["ema_fast"].values
    ema_s = feat["ema_slow"].values
    ratr = feat["ratr"].values
    vdo_arr = feat["vdo"].values
    d1_ok = feat["d1_regime_ok"].values
    n = len(c)

    # Compute ema_spread and ema_spread_roc
    with np.errstate(divide="ignore", invalid="ignore"):
        ema_spread = np.where(ema_s != 0, (ema_f - ema_s) / ema_s, np.nan)

    ema_spread_roc = np.full(n, np.nan)
    if lookback is not None and lookback < n:
        ema_spread_roc[lookback:] = ema_spread[lookback:] - ema_spread[: n - lookback]

    trades: list[dict] = []
    blocked_entries: list[int] = []  # bar indices of blocked entries
    in_pos = False
    peak = 0.0
    entry_bar = 0
    entry_price = 0.0

    equity = np.full(n, np.nan)
    cash = INITIAL_CASH
    position_size = 0.0

    for i in range(warmup_bar, n):
        if np.isnan(ratr[i]):
            equity[i] = cash if not in_pos else position_size * c[i]
            continue

        if not in_pos:
            equity[i] = cash

            base_ok = ema_f[i] > ema_s[i] and vdo_arr[i] > 0 and d1_ok[i]

            if base_ok:
                accel_ok = True
                if lookback is not None:
                    if np.isfinite(ema_spread_roc[i]):
                        accel_ok = ema_spread_roc[i] > min_accel
                    else:
                        accel_ok = False

                if accel_ok:
                    in_pos = True
                    entry_bar = i
                    entry_price = c[i]
                    peak = c[i]
                    half_cost = (COST_BPS / 2) / 10_000
                    position_size = cash * (1 - half_cost) / c[i]
                    cash = 0.0
                else:
                    blocked_entries.append(i)
        else:
            equity[i] = position_size * c[i]
            peak = max(peak, c[i])
            trail_stop = peak - TRAIL_MULT * ratr[i]
            exit_reason = None

            if c[i] < trail_stop:
                exit_reason = "trail"
            elif ema_f[i] < ema_s[i]:
                exit_reason = "trend"

            if exit_reason:
                half_cost = (COST_BPS / 2) / 10_000
                cash = position_size * c[i] * (1 - half_cost)
                cost_rt = COST_BPS / 10_000
                gross_ret = (c[i] - entry_price) / entry_price
                net_ret = gross_ret - cost_rt

                trades.append({
                    "entry_bar": entry_bar,
                    "exit_bar": i,
                    "bars_held": i - entry_bar,
                    "net_ret": net_ret,
                    "win": int(net_ret > 0),
                })

                equity[i] = cash
                position_size = 0.0
                in_pos = False
                peak = 0.0

    # ── Metrics ───────────────────────────────────────────────────────
    eq = pd.Series(equity[warmup_bar:]).dropna()
    if len(eq) < 2 or len(trades) == 0:
        return _empty_result(lookback, min_accel)

    rets = eq.pct_change().dropna()
    bars_per_year = 365.25 * 24 / 4

    sharpe = (rets.mean() / rets.std() * np.sqrt(bars_per_year)) if rets.std() > 0 else 0.0

    total_bars = len(eq)
    years = total_bars / bars_per_year
    final_ret = eq.iloc[-1] / eq.iloc[0]
    cagr = final_ret ** (1 / years) - 1 if years > 0 and final_ret > 0 else 0.0

    cummax = eq.cummax()
    dd = (eq - cummax) / cummax
    mdd = dd.min()

    total_bars_held = sum(t["bars_held"] for t in trades)
    exposure = total_bars_held / total_bars
    avg_bars_held = np.mean([t["bars_held"] for t in trades])

    tdf = pd.DataFrame(trades)
    n_wins = int(tdf["win"].sum())
    win_rate = n_wins / len(trades) * 100

    # ── Blocked entry analysis (simulate each as independent trade) ───
    blocked_wins = 0
    blocked_total = len(blocked_entries)

    for b_i in blocked_entries:
        b_entry = c[b_i]
        b_peak = b_entry
        b_exited = False
        for j in range(b_i + 1, n):
            if np.isnan(ratr[j]):
                continue
            b_peak = max(b_peak, c[j])
            b_trail = b_peak - TRAIL_MULT * ratr[j]
            if c[j] < b_trail or ema_f[j] < ema_s[j]:
                cost_rt = COST_BPS / 10_000
                if (c[j] - b_entry) / b_entry - cost_rt > 0:
                    blocked_wins += 1
                b_exited = True
                break
        if not b_exited:
            cost_rt = COST_BPS / 10_000
            if (c[-1] - b_entry) / b_entry - cost_rt > 0:
                blocked_wins += 1

    blocked_wr = (blocked_wins / blocked_total * 100) if blocked_total > 0 else np.nan

    return {
        "lookback": lookback if lookback is not None else "baseline",
        "min_accel": min_accel if min_accel is not None else "baseline",
        "sharpe": round(sharpe, 4),
        "cagr_pct": round(cagr * 100, 2),
        "mdd_pct": round(abs(mdd) * 100, 2),
        "trades": len(trades),
        "win_rate": round(win_rate, 1),
        "avg_bars_held": round(avg_bars_held, 1),
        "exposure_pct": round(exposure * 100, 1),
        "blocked": blocked_total,
        "blocked_win_rate": round(blocked_wr, 1) if np.isfinite(blocked_wr) else np.nan,
    }


def _empty_result(
    lookback: int | None,
    min_accel: float | None,
) -> dict:
    return {
        "lookback": lookback if lookback is not None else "baseline",
        "min_accel": min_accel if min_accel is not None else "baseline",
        "sharpe": np.nan, "cagr_pct": np.nan, "mdd_pct": np.nan,
        "trades": 0, "win_rate": np.nan, "avg_bars_held": np.nan,
        "exposure_pct": np.nan, "blocked": 0, "blocked_win_rate": np.nan,
    }


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("EXP 33: Momentum Acceleration Gate")
    print("=" * 80)

    h4, d1 = load_data()
    feat = compute_features(h4, d1)

    warmup_bar = SLOW_PERIOD
    print(f"Warmup bar: {warmup_bar}")

    # Build config grid: baseline + 12 configs
    configs: list[tuple[int | None, float | None]] = [(None, None)]
    for lb in LOOKBACKS:
        for ma in MIN_ACCELS:
            configs.append((lb, ma))

    results = []
    for lb, ma in configs:
        if lb is None:
            label = "baseline"
        else:
            label = f"lb={lb}, min_accel={ma}"
        print(f"\nRunning {label}...")
        r = run_backtest(feat, lb, ma, warmup_bar)
        results.append(r)
        print(
            f"  Sharpe={r['sharpe']}, CAGR={r['cagr_pct']}%, MDD={r['mdd_pct']}%, "
            f"trades={r['trades']}, blocked={r['blocked']}, "
            f"blocked_wr={r['blocked_win_rate']}"
        )

    # ── Results table ─────────────────────────────────────────────────
    df = pd.DataFrame(results)

    base = df.iloc[0]
    df["d_sharpe"] = df["sharpe"] - base["sharpe"]
    df["d_cagr"] = df["cagr_pct"] - base["cagr_pct"]
    df["d_mdd"] = df["mdd_pct"] - base["mdd_pct"]  # negative = improvement

    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)
    print(df.to_string(index=False))

    out_path = RESULTS_DIR / "exp33_results.csv"
    df.to_csv(out_path, index=False)
    print(f"\n-> Saved to {out_path}")

    # ── Verdict ───────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("VERDICT")
    print("=" * 80)

    gated = df.iloc[1:]
    improvements = gated[(gated["d_sharpe"] > 0) & (gated["d_mdd"] < 0)]

    if not improvements.empty:
        best = improvements.loc[improvements["d_sharpe"].idxmax()]
        print(
            f"PASS: lb={best['lookback']}, min_accel={best['min_accel']} "
            f"improves Sharpe ({best['d_sharpe']:+.4f}) AND MDD ({best['d_mdd']:+.2f} pp)"
        )
        print(
            f"  {best['trades']} trades, {best['blocked']} blocked "
            f"(blocked WR: {best['blocked_win_rate']:.1f}% vs baseline WR: {base['win_rate']:.1f}%)"
        )
    else:
        sharpe_up = gated[gated["d_sharpe"] > 0]
        if not sharpe_up.empty:
            best = sharpe_up.loc[sharpe_up["d_sharpe"].idxmax()]
            print(
                f"MIXED: lb={best['lookback']}, min_accel={best['min_accel']} "
                f"improves Sharpe ({best['d_sharpe']:+.4f}) but MDD {best['d_mdd']:+.2f} pp"
            )
        else:
            print("FAIL: No config improves Sharpe over baseline.")
            print("Momentum acceleration gate does NOT help E5-ema21D1.")

    # Blocked entry analysis summary
    print(f"\nBlocked entry analysis (baseline WR: {base['win_rate']:.1f}%):")
    for _, row in gated.iterrows():
        if row["blocked"] > 0:
            selectivity = "GOOD" if row["blocked_win_rate"] < base["win_rate"] else "BAD"
            print(
                f"  lb={row['lookback']:>2}, min_accel={row['min_accel']}: "
                f"blocked {row['blocked']:>4}, blocked WR {row['blocked_win_rate']:5.1f}% [{selectivity}]"
            )


if __name__ == "__main__":
    main()
