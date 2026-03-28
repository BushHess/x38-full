#!/usr/bin/env python3
"""Exp 39: Dual-Clock EMA Entry.

Replace single-clock EMA (30/120) with dual-clock agreement:
  FAST clock: ema(fast_f) > ema(fast_s) — timing
  SLOW clock: ema(slow_f) > ema(slow_s) — direction confirmation
  Entry: both clocks agree + vdo > 0 + d1_regime_ok

Two exit modes:
  fast_exit — exit when fast clock reverses (fast_f < fast_s)
  any_exit  — exit when EITHER clock reverses

10 preset configs (A1..E2). Trail stop unchanged (3.0 * RATR).

Usage:
    python -m research.x39.experiments.exp39_dual_clock_entry
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]  # btc-spot-dev/
sys.path.insert(0, str(ROOT))

from research.x39.explore import compute_features, ema, load_data  # noqa: E402

RESULTS_DIR = Path(__file__).resolve().parents[1] / "results"

# ── Strategy constants (match E5-ema21D1) ─────────────────────────────────
SLOW_PERIOD = 120
TRAIL_MULT = 3.0
COST_BPS = 50
INITIAL_CASH = 10_000.0

# ── Dual-clock configs ────────────────────────────────────────────────────
CONFIGS = [
    # (name, fast_f, fast_s, slow_f, slow_s, exit_mode)
    ("A1", 15, 60, 30, 120, "fast_exit"),
    ("A2", 15, 60, 30, 120, "any_exit"),
    ("B1", 15, 60, 60, 240, "fast_exit"),
    ("B2", 15, 60, 60, 240, "any_exit"),
    ("C1", 20, 84, 60, 240, "fast_exit"),
    ("C2", 20, 84, 60, 240, "any_exit"),
    ("D1", 30, 120, 60, 240, "fast_exit"),
    ("D2", 30, 120, 60, 240, "any_exit"),
    ("E1", 15, 60, 120, 480, "fast_exit"),
    ("E2", 15, 60, 120, 480, "any_exit"),
]


def run_backtest(
    feat: pd.DataFrame,
    close: np.ndarray,
    warmup_bar: int,
    *,
    fast_ema_f: np.ndarray | None = None,
    fast_ema_s: np.ndarray | None = None,
    slow_ema_f: np.ndarray | None = None,
    slow_ema_s: np.ndarray | None = None,
    exit_mode: str = "fast_exit",
    config_name: str = "baseline",
) -> dict:
    """Replay E5-ema21D1 with optional dual-clock entry/exit."""
    ema_f_base = feat["ema_fast"].values  # 30
    ema_s_base = feat["ema_slow"].values  # 120
    ratr = feat["ratr"].values
    vdo_arr = feat["vdo"].values
    d1_ok = feat["d1_regime_ok"].values
    n = len(close)

    is_dual = fast_ema_f is not None

    trades: list[dict] = []
    in_pos = False
    peak = 0.0
    entry_bar = 0
    entry_price = 0.0

    equity = np.full(n, np.nan)
    cash = INITIAL_CASH
    position_size = 0.0

    # Track blocked entries for analysis
    blocked_entries = 0
    agreed_bars = 0
    total_trend_bars = 0

    for i in range(warmup_bar, n):
        if np.isnan(ratr[i]):
            equity[i] = cash
            continue

        if not in_pos:
            equity[i] = cash

            if is_dual:
                fast_up = fast_ema_f[i] > fast_ema_s[i]
                slow_up = slow_ema_f[i] > slow_ema_s[i]

                # Track agreement stats
                if fast_up or slow_up:
                    total_trend_bars += 1
                if fast_up and slow_up:
                    agreed_bars += 1

                entry_ok = (
                    fast_up
                    and slow_up
                    and vdo_arr[i] > 0
                    and d1_ok[i]
                )

                # Count blocked: would have entered baseline but slow clock blocked
                baseline_entry = (
                    ema_f_base[i] > ema_s_base[i]
                    and vdo_arr[i] > 0
                    and d1_ok[i]
                )
                if baseline_entry and not entry_ok:
                    blocked_entries += 1
            else:
                # Baseline: single clock 30/120
                entry_ok = (
                    ema_f_base[i] > ema_s_base[i]
                    and vdo_arr[i] > 0
                    and d1_ok[i]
                )

            if entry_ok:
                in_pos = True
                entry_bar = i
                entry_price = close[i]
                peak = close[i]
                half_cost = (COST_BPS / 2) / 10_000
                position_size = cash * (1 - half_cost) / close[i]
                cash = 0.0
        else:
            equity[i] = position_size * close[i]
            peak = max(peak, close[i])

            trail_stop = peak - TRAIL_MULT * ratr[i]
            exit_reason = None

            if close[i] < trail_stop:
                exit_reason = "trail"
            elif is_dual:
                fast_down = fast_ema_f[i] < fast_ema_s[i]
                slow_down = slow_ema_f[i] < slow_ema_s[i]
                if exit_mode == "fast_exit":
                    if fast_down:
                        exit_reason = "fast_clock"
                else:  # any_exit
                    if fast_down or slow_down:
                        exit_reason = "any_clock"
            else:
                if ema_f_base[i] < ema_s_base[i]:
                    exit_reason = "trend"

            if exit_reason:
                half_cost = (COST_BPS / 2) / 10_000
                cash = position_size * close[i] * (1 - half_cost)
                cost = COST_BPS / 10_000
                gross_ret = (close[i] - entry_price) / entry_price
                net_ret = gross_ret - cost

                trades.append({
                    "entry_bar": entry_bar,
                    "exit_bar": i,
                    "bars_held": i - entry_bar,
                    "entry_price": entry_price,
                    "exit_price": close[i],
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
            "config": config_name, "sharpe": np.nan, "cagr_pct": np.nan,
            "mdd_pct": np.nan, "trades": 0, "win_rate": np.nan,
            "avg_bars_held": np.nan, "exposure_pct": np.nan,
            "blocked_entries": blocked_entries,
            "agreement_pct": np.nan,
        }

    rets = eq.pct_change().dropna()
    bars_per_year = 365.25 * 24 / 4

    sharpe = (
        rets.mean() / rets.std() * np.sqrt(bars_per_year)
        if rets.std() > 0 else 0.0
    )

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

    agreement_pct = (
        round(agreed_bars / total_trend_bars * 100, 1)
        if total_trend_bars > 0 else np.nan
    )

    return {
        "config": config_name,
        "sharpe": round(sharpe, 4),
        "cagr_pct": round(cagr * 100, 2),
        "mdd_pct": round(abs(mdd) * 100, 2),
        "trades": len(trades),
        "win_rate": round(len(wins) / len(trades) * 100, 1),
        "avg_bars_held": round(tdf["bars_held"].mean(), 1),
        "exposure_pct": round(exposure * 100, 1),
        "blocked_entries": blocked_entries,
        "agreement_pct": agreement_pct,
    }


def analyze_blocked_trades(
    feat: pd.DataFrame,
    close: np.ndarray,
    warmup_bar: int,
    fast_ema_f: np.ndarray,
    fast_ema_s: np.ndarray,
    slow_ema_f: np.ndarray,
    slow_ema_s: np.ndarray,
) -> dict:
    """Replay baseline and tag each entry: would slow clock have blocked it?

    Returns stats on blocked vs allowed entries in the baseline.
    """
    ema_f_base = feat["ema_fast"].values
    ema_s_base = feat["ema_slow"].values
    ratr = feat["ratr"].values
    vdo_arr = feat["vdo"].values
    d1_ok = feat["d1_regime_ok"].values
    n = len(close)

    in_pos = False
    peak = 0.0
    entry_bar = 0
    entry_price = 0.0

    blocked_trades: list[dict] = []
    allowed_trades: list[dict] = []

    for i in range(warmup_bar, n):
        if np.isnan(ratr[i]):
            continue

        if not in_pos:
            baseline_entry = (
                ema_f_base[i] > ema_s_base[i]
                and vdo_arr[i] > 0
                and d1_ok[i]
            )
            if baseline_entry:
                in_pos = True
                entry_bar = i
                entry_price = close[i]
                peak = close[i]
                # Tag: would slow clock block this?
                slow_up = slow_ema_f[i] > slow_ema_s[i]
                fast_up = fast_ema_f[i] > fast_ema_s[i]
                blocked = not (fast_up and slow_up)
        else:
            peak = max(peak, close[i])
            trail_stop = peak - TRAIL_MULT * ratr[i]
            exit_reason = None
            if close[i] < trail_stop:
                exit_reason = "trail"
            elif ema_f_base[i] < ema_s_base[i]:
                exit_reason = "trend"

            if exit_reason:
                cost = COST_BPS / 10_000
                gross_ret = (close[i] - entry_price) / entry_price
                net_ret = gross_ret - cost
                trade = {"net_ret": net_ret, "win": int(net_ret > 0), "bars_held": i - entry_bar}
                if blocked:
                    blocked_trades.append(trade)
                else:
                    allowed_trades.append(trade)
                in_pos = False
                peak = 0.0

    def _stats(tlist: list[dict]) -> dict:
        if not tlist:
            return {"n": 0, "win_rate": np.nan, "avg_ret": np.nan, "med_ret": np.nan}
        rets = [t["net_ret"] for t in tlist]
        wins = sum(1 for t in tlist if t["win"])
        return {
            "n": len(tlist),
            "win_rate": round(wins / len(tlist) * 100, 1),
            "avg_ret": round(np.mean(rets) * 100, 2),
            "med_ret": round(np.median(rets) * 100, 2),
        }

    return {"blocked": _stats(blocked_trades), "allowed": _stats(allowed_trades)}


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("EXP 39: Dual-Clock EMA Entry")
    print("=" * 80)

    h4, d1 = load_data()
    feat = compute_features(h4, d1)
    close = feat["close"].values

    warmup_bar = SLOW_PERIOD
    # Ensure warmup covers longest EMA period across all configs (480)
    max_ema_period = max(cfg[4] for cfg in CONFIGS)  # slow_slow
    warmup_bar = max(warmup_bar, max_ema_period + 50)
    print(f"Warmup bar: {warmup_bar} (covers max EMA period {max_ema_period})")

    # ── Run baseline ──────────────────────────────────────────────────
    print("\nRunning baseline (single clock 30/120)...")
    baseline = run_backtest(feat, close, warmup_bar, config_name="baseline")
    print(f"  Sharpe={baseline['sharpe']}, CAGR={baseline['cagr_pct']}%, "
          f"MDD={baseline['mdd_pct']}%, trades={baseline['trades']}")

    results = [baseline]

    # ── Pre-compute all EMA arrays ────────────────────────────────────
    periods_needed = sorted({p for cfg in CONFIGS for p in cfg[1:5]})
    ema_cache: dict[int, np.ndarray] = {}
    for p in periods_needed:
        ema_cache[p] = ema(close, p)
    print(f"Pre-computed EMAs for periods: {periods_needed}")

    # ── Run dual-clock configs ────────────────────────────────────────
    for name, ff, fs, sf, ss, exit_mode in CONFIGS:
        print(f"\nRunning {name} (fast={ff}/{fs}, slow={sf}/{ss}, exit={exit_mode})...")
        r = run_backtest(
            feat, close, warmup_bar,
            fast_ema_f=ema_cache[ff],
            fast_ema_s=ema_cache[fs],
            slow_ema_f=ema_cache[sf],
            slow_ema_s=ema_cache[ss],
            exit_mode=exit_mode,
            config_name=name,
        )
        results.append(r)
        print(f"  Sharpe={r['sharpe']}, CAGR={r['cagr_pct']}%, MDD={r['mdd_pct']}%, "
              f"trades={r['trades']}, blocked={r['blocked_entries']}, "
              f"agreement={r['agreement_pct']}%")

    # ── Results table ─────────────────────────────────────────────────
    df = pd.DataFrame(results)
    base = df.iloc[0]
    df["d_sharpe"] = df["sharpe"] - base["sharpe"]
    df["d_cagr"] = df["cagr_pct"] - base["cagr_pct"]
    df["d_mdd"] = df["mdd_pct"] - base["mdd_pct"]  # negative = MDD improved

    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)
    print(df.to_string(index=False))

    out_path = RESULTS_DIR / "exp39_results.csv"
    df.to_csv(out_path, index=False)
    print(f"\n-> Saved to {out_path}")

    # ── Blocked-trade quality analysis ────────────────────────────────
    # Use config D1 (30/120 fast + 60/240 slow) for the deepest analysis
    # because its fast clock matches baseline exactly
    print("\n" + "=" * 80)
    print("BLOCKED-TRADE ANALYSIS (D1 config: fast=30/120, slow=60/240)")
    print("=" * 80)

    analysis = analyze_blocked_trades(
        feat, close, warmup_bar,
        fast_ema_f=ema_cache[30],
        fast_ema_s=ema_cache[120],
        slow_ema_f=ema_cache[60],
        slow_ema_s=ema_cache[240],
    )

    print(f"  Blocked trades: {analysis['blocked']['n']}")
    print(f"    win_rate={analysis['blocked']['win_rate']}%, "
          f"avg_ret={analysis['blocked']['avg_ret']}%, "
          f"med_ret={analysis['blocked']['med_ret']}%")
    print(f"  Allowed trades: {analysis['allowed']['n']}")
    print(f"    win_rate={analysis['allowed']['win_rate']}%, "
          f"avg_ret={analysis['allowed']['avg_ret']}%, "
          f"med_ret={analysis['allowed']['med_ret']}%")

    if analysis["blocked"]["n"] > 0 and analysis["allowed"]["n"] > 0:
        b_avg = analysis["blocked"]["avg_ret"]
        a_avg = analysis["allowed"]["avg_ret"]
        if b_avg < a_avg:
            print(f"  -> Slow clock filters OUT worse trades (blocked avg {b_avg}% < allowed avg {a_avg}%)")
        else:
            print(f"  -> Slow clock filters OUT better trades (blocked avg {b_avg}% > allowed avg {a_avg}%)")

    # ── Verdict ───────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("VERDICT")
    print("=" * 80)

    gated = df.iloc[1:]
    # Strict improvement: Sharpe up AND MDD down (negative d_mdd)
    strict = gated[(gated["d_sharpe"] > 0) & (gated["d_mdd"] < 0)]

    if not strict.empty:
        best = strict.loc[strict["d_sharpe"].idxmax()]
        print(f"PASS: {best['config']} improves both Sharpe ({best['d_sharpe']:+.4f}) "
              f"and MDD ({best['d_mdd']:+.2f} pp)")
        print(f"  Sharpe={best['sharpe']}, CAGR={best['cagr_pct']}%, "
              f"MDD={best['mdd_pct']}%, trades={int(best['trades'])}")
    else:
        sharpe_up = gated[gated["d_sharpe"] > 0]
        if not sharpe_up.empty:
            best = sharpe_up.loc[sharpe_up["d_sharpe"].idxmax()]
            print(f"MIXED: {best['config']} improves Sharpe ({best['d_sharpe']:+.4f}) "
                  f"but MDD changes {best['d_mdd']:+.2f} pp")
        else:
            print("FAIL: No dual-clock config improves Sharpe over single-clock baseline.")
            print("Multi-timescale EMA confirmation does NOT help E5-ema21D1.")
            print("Consistent with ρ=0.92 finding: timescales are too correlated for")
            print("dual-clock to add value — the slower clock is largely redundant.")


if __name__ == "__main__":
    main()
