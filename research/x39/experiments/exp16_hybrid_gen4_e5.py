#!/usr/bin/env python3
"""Exp 16: Hybrid — Gen4 C3 Entry + E5 Exit.

Gen4 C3 entry logic (trade_surprise_168 > 0 + rangepos_168 > threshold)
combined with E5's proven exit mechanism (ATR trail + EMA cross-down).
D1 EMA(21) regime kept from E5 for cleaner comparison.

Sweeps entry_thresh in [0.50, 0.55, 0.65].

Usage:
    python -m research.x39.experiments.exp16_hybrid_gen4_e5
    # or from x39/:
    python experiments/exp16_hybrid_gen4_e5.py
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

# ── Hybrid entry thresholds ──────────────────────────────────────────────
ENTRY_THRESHOLDS = [0.50, 0.55, 0.65]

# ── Gen4 C3 reference (from exp14) ──────────────────────────────────────
C3_REF = {"sharpe": 0.8569, "cagr_pct": 30.2, "mdd_pct": 41.86, "trades": 110}


def run_backtest(
    feat: pd.DataFrame,
    entry_thresh: float | None,
    warmup_bar: int,
) -> dict:
    """Run E5-ema21D1 with optional Gen4 C3-style entry gate.

    entry_thresh=None → pure E5-ema21D1 baseline.
    entry_thresh=float → hybrid: trade_surprise_168 > 0 AND rangepos_168 > entry_thresh.
    """
    c = feat["close"].values
    ema_f = feat["ema_fast"].values
    ema_s = feat["ema_slow"].values
    ratr = feat["ratr"].values
    vdo_arr = feat["vdo"].values
    d1_ok = feat["d1_regime_ok"].values
    ts = feat["trade_surprise_168"].values
    rp = feat["rangepos_168"].values
    n = len(c)

    trades: list[dict] = []
    in_pos = False
    peak = 0.0
    entry_bar = 0
    entry_price = 0.0
    cost = COST_BPS / 10_000

    # Equity tracking
    equity = np.full(n, np.nan)
    cash = INITIAL_CASH
    position_size = 0.0

    for i in range(warmup_bar, n):
        if np.isnan(ratr[i]):
            equity[i] = cash
            continue

        if not in_pos:
            equity[i] = cash

            # E5 entry conditions
            entry_ok = (
                ema_f[i] > ema_s[i]
                and vdo_arr[i] > 0
                and d1_ok[i]
            )
            # Hybrid gate: Gen4 C3-style entry conditions
            if entry_thresh is not None:
                entry_ok = (
                    entry_ok
                    and np.isfinite(ts[i])
                    and ts[i] > 0
                    and np.isfinite(rp[i])
                    and rp[i] > entry_thresh
                )

            if entry_ok:
                in_pos = True
                entry_bar = i
                entry_price = c[i]
                peak = c[i]
                half_cost = (COST_BPS / 2) / 10_000
                position_size = cash * (1 - half_cost) / c[i]
                cash = 0.0
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
                gross_ret = (c[i] - entry_price) / entry_price
                net_ret = gross_ret - cost

                trades.append({
                    "entry_bar": entry_bar,
                    "exit_bar": i,
                    "bars_held": i - entry_bar,
                    "entry_price": entry_price,
                    "exit_price": c[i],
                    "gross_ret": gross_ret,
                    "net_ret": net_ret,
                    "exit_reason": exit_reason,
                    "win": int(net_ret > 0),
                })

                equity[i] = cash
                position_size = 0.0
                in_pos = False
                peak = 0.0

    # ── Compute metrics ───────────────────────────────────────────────
    eq = pd.Series(equity[warmup_bar:]).dropna()
    if len(eq) < 2 or len(trades) == 0:
        return {
            "config": "baseline" if entry_thresh is None else f"thresh={entry_thresh}",
            "sharpe": np.nan, "cagr_pct": np.nan, "mdd_pct": np.nan,
            "trades": 0, "win_rate": np.nan, "avg_win": np.nan,
            "avg_loss": np.nan, "exposure_pct": np.nan,
        }

    rets = eq.pct_change().dropna()
    bars_per_year = 365.25 * 24 / 4  # ~2191.5

    if rets.std() > 0:
        sharpe = rets.mean() / rets.std() * np.sqrt(bars_per_year)
    else:
        sharpe = 0.0

    total_bars = len(eq)
    years = total_bars / bars_per_year
    final_ret = eq.iloc[-1] / eq.iloc[0]
    cagr = final_ret ** (1 / years) - 1 if years > 0 and final_ret > 0 else 0.0

    cummax = eq.cummax()
    dd = (eq - cummax) / cummax
    mdd = dd.min()

    total_bars_held = sum(t["bars_held"] for t in trades)
    exposure = total_bars_held / total_bars

    tdf = pd.DataFrame(trades)
    wins = tdf[tdf["win"] == 1]
    losses = tdf[tdf["win"] == 0]

    return {
        "config": "baseline" if entry_thresh is None else f"thresh={entry_thresh}",
        "sharpe": round(sharpe, 4),
        "cagr_pct": round(cagr * 100, 2),
        "mdd_pct": round(abs(mdd) * 100, 2),
        "trades": len(trades),
        "win_rate": round(len(wins) / len(trades) * 100, 1),
        "avg_win": round(wins["net_ret"].mean() * 100, 2) if len(wins) > 0 else np.nan,
        "avg_loss": round(losses["net_ret"].mean() * 100, 2) if len(losses) > 0 else np.nan,
        "exposure_pct": round(exposure * 100, 1),
    }


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("EXP 16: Hybrid — Gen4 C3 Entry + E5 Exit")
    print("=" * 80)

    h4, d1 = load_data()
    feat = compute_features(h4, d1)

    # ── Feature diagnostics ───────────────────────────────────────────
    ts = feat["trade_surprise_168"].values
    rp = feat["rangepos_168"].values

    ts_valid = ts[np.isfinite(ts)]
    rp_valid = rp[np.isfinite(rp)]
    print(f"\ntrade_surprise_168: {len(ts_valid)}/{len(ts)} valid, "
          f"mean={ts_valid.mean():.4f}, std={ts_valid.std():.4f}")
    print(f"  Bars with ts > 0: {np.mean(ts_valid > 0) * 100:.1f}%")

    print(f"rangepos_168: {len(rp_valid)}/{len(rp)} valid, "
          f"mean={rp_valid.mean():.4f}")
    for t in ENTRY_THRESHOLDS:
        pct = np.mean(rp_valid > t) * 100
        print(f"  Bars with rp > {t}: {pct:.1f}%")

    # Joint condition: ts > 0 AND rp > threshold (on valid bars)
    both_valid = np.isfinite(ts) & np.isfinite(rp)
    for t in ENTRY_THRESHOLDS:
        joint = both_valid & (ts > 0) & (rp > t)
        pct = joint.sum() / both_valid.sum() * 100 if both_valid.sum() > 0 else 0
        print(f"  Joint (ts>0 & rp>{t}): {pct:.1f}%")

    # Warmup: need both features valid + EMA warmup
    first_valid = 0
    for i in range(len(ts)):
        if np.isfinite(ts[i]) and np.isfinite(rp[i]):
            first_valid = i
            break
    warmup_bar = max(SLOW_PERIOD, first_valid)
    print(f"\nWarmup bar: {warmup_bar} (first valid features at {first_valid})")

    # ── Run baseline + 3 hybrid configs ───────────────────────────────
    configs: list[float | None] = [None] + ENTRY_THRESHOLDS
    results = []

    for thresh in configs:
        label = "baseline (E5-ema21D1)" if thresh is None else f"hybrid thresh={thresh}"
        print(f"\nRunning {label}...")
        r = run_backtest(feat, thresh, warmup_bar)
        results.append(r)
        print(f"  Sharpe={r['sharpe']}, CAGR={r['cagr_pct']}%, MDD={r['mdd_pct']}%, "
              f"trades={r['trades']}, win_rate={r['win_rate']}%, exposure={r['exposure_pct']}%")

    # ── Results table ─────────────────────────────────────────────────
    df = pd.DataFrame(results)

    base = df.iloc[0]
    df["d_sharpe"] = df["sharpe"] - base["sharpe"]
    df["d_cagr"] = df["cagr_pct"] - base["cagr_pct"]
    df["d_mdd"] = df["mdd_pct"] - base["mdd_pct"]  # negative = MDD improvement

    print("\n" + "=" * 80)
    print("RESULTS (vs E5-ema21D1 baseline)")
    print("=" * 80)
    print(df.to_string(index=False))

    # ── Gen4 C3 reference ─────────────────────────────────────────────
    print("\n" + "-" * 80)
    print("REFERENCE: Gen4 C3 (from exp14)")
    print(f"  Sharpe={C3_REF['sharpe']}, CAGR={C3_REF['cagr_pct']}%, "
          f"MDD={C3_REF['mdd_pct']}%, trades={C3_REF['trades']}")
    print(f"  Delta vs E5 baseline: d_sharpe={C3_REF['sharpe'] - base['sharpe']:.4f}, "
          f"d_cagr={C3_REF['cagr_pct'] - base['cagr_pct']:.2f}, "
          f"d_mdd={C3_REF['mdd_pct'] - base['mdd_pct']:.2f}")

    # Save
    out_path = RESULTS_DIR / "exp16_results.csv"
    df.to_csv(out_path, index=False)
    print(f"\n→ Saved to {out_path}")

    # ── Verdict ───────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("VERDICT")
    print("=" * 80)

    hybrids = df.iloc[1:]

    # Check: any hybrid beats E5 on BOTH Sharpe AND MDD?
    strict_wins = hybrids[(hybrids["d_sharpe"] > 0) & (hybrids["d_mdd"] < 0)]
    if not strict_wins.empty:
        best = strict_wins.loc[strict_wins["d_sharpe"].idxmax()]
        print(f"PASS: {best['config']} improves BOTH Sharpe ({best['d_sharpe']:+.4f}) "
              f"and MDD ({best['d_mdd']:+.2f} pp) vs E5 baseline.")
        print(f"  Hybrid entry (C3 + E5 exit) strictly dominates pure E5.")
    else:
        # Check Sharpe-only improvement
        sharpe_wins = hybrids[hybrids["d_sharpe"] > 0]
        if not sharpe_wins.empty:
            best = sharpe_wins.loc[sharpe_wins["d_sharpe"].idxmax()]
            print(f"MIXED: {best['config']} improves Sharpe ({best['d_sharpe']:+.4f}) "
                  f"but MDD changes {best['d_mdd']:+.2f} pp.")
        else:
            print("FAIL: No hybrid config improves Sharpe over E5 baseline.")
            print("  Gen4 C3 entry conditions do NOT improve E5 when combined with E5 exit.")

    # Compare best hybrid vs pure C3
    best_hybrid = hybrids.loc[hybrids["sharpe"].idxmax()]
    c3_sharpe = C3_REF["sharpe"]
    print(f"\nBest hybrid ({best_hybrid['config']}): Sharpe {best_hybrid['sharpe']} "
          f"vs pure C3: {c3_sharpe}")
    if best_hybrid["sharpe"] > c3_sharpe:
        print(f"  Hybrid beats pure C3 by {best_hybrid['sharpe'] - c3_sharpe:+.4f} Sharpe.")
        print("  → E5 exit mechanism rescues C3 entry.")
    else:
        print(f"  Hybrid loses to pure C3 by {best_hybrid['sharpe'] - c3_sharpe:+.4f} Sharpe.")


if __name__ == "__main__":
    main()
