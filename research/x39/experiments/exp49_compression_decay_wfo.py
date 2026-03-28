#!/usr/bin/env python3
"""Exp 49: Compression + Maturity Decay Combo Walk-Forward Validation.

Tests if compression (thr=0.7, WFO-validated in exp42) "cleans" the trade
population enough that maturity decay becomes WFO-stable on the filtered set.

Compression threshold is FIXED (0.7, NOT swept). Only decay params swept in training.

Usage:
    python -m research.x39.experiments.exp49_compression_decay_wfo
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
TRAIL_BASE = 3.0
COST_BPS = 50
INITIAL_CASH = 10_000.0
WARMUP_DAYS = 365

# ── Compression (fixed, WFO-validated in exp42) ─────────────────────────
COMPRESSION_THR = 0.7

# ── Decay parameter grid (same as exp40) ────────────────────────────────
TRAIL_MINS = [1.5, 2.0, 2.5]
DECAY_STARTS = [30, 60]       # H4 bars
DECAY_ENDS = [120, 180, 240]  # H4 bars

# ── Anchored WFO Windows (identical to exp40/42) ───────────────────────
WFO_WINDOWS = [
    {"train_start": "2019-01-01", "train_end": "2021-06-30",
     "test_start": "2021-07-01", "test_end": "2023-06-30"},
    {"train_start": "2019-01-01", "train_end": "2022-06-30",
     "test_start": "2022-07-01", "test_end": "2024-06-30"},
    {"train_start": "2019-01-01", "train_end": "2023-06-30",
     "test_start": "2023-07-01", "test_end": "2025-06-30"},
    {"train_start": "2019-01-01", "train_end": "2024-06-30",
     "test_start": "2024-07-01", "test_end": "2026-02-28"},
]


# ── Reused from exp38/exp44 ─────────────────────────────────────────────

def compute_trend_age(ema_fast: np.ndarray, ema_slow: np.ndarray) -> np.ndarray:
    """Bars since most recent EMA crossover (fast > slow)."""
    n = len(ema_fast)
    age = np.zeros(n, dtype=np.int32)
    for i in range(1, n):
        if ema_fast[i] > ema_slow[i]:
            age[i] = age[i - 1] + 1
    return age


def calc_effective_trail(
    trend_age: int,
    trail_min: float,
    decay_start: int,
    decay_end: int,
) -> float:
    """Linear decay from TRAIL_BASE to trail_min between decay_start and decay_end."""
    if trend_age < decay_start:
        return TRAIL_BASE
    if trend_age >= decay_end:
        return trail_min
    progress = (trend_age - decay_start) / (decay_end - decay_start)
    return TRAIL_BASE - (TRAIL_BASE - trail_min) * progress


# ── Date -> bar index (from exp42) ──────────────────────────────────────

def find_bar_idx(datetimes: pd.DatetimeIndex, date_str: str, side: str) -> int:
    """Map a date boundary to a bar index."""
    dt = pd.Timestamp(date_str)
    if side == "start":
        mask = datetimes >= dt
        if not mask.any():
            return len(datetimes)
        return int(np.argmax(mask))
    else:
        end_dt = dt + pd.Timedelta(days=1)
        mask = datetimes >= end_dt
        if not mask.any():
            return len(datetimes)
        return int(np.argmax(mask))


# ── Backtest engine ──────────────────────────────────────────────────────

def run_backtest(
    feat: pd.DataFrame,
    trend_age: np.ndarray,
    start_bar: int,
    end_bar: int,
    *,
    compression_thr: float | None = None,
    trail_min: float | None = None,
    decay_start: int | None = None,
    decay_end: int | None = None,
) -> dict:
    """Replay E5-ema21D1 with optional compression gate + maturity decay.

    compression_thr=None -> no compression gate (baseline entry).
    trail_min=None -> fixed trail (3.0, no decay).
    Both set -> combo.
    """
    c = feat["close"].values
    ema_f = feat["ema_fast"].values
    ema_s = feat["ema_slow"].values
    ratr = feat["ratr"].values
    vdo_arr = feat["vdo"].values
    d1_ok = feat["d1_regime_ok"].values
    vol_ratio = feat["vol_ratio_5_20"].values

    has_compression = compression_thr is not None
    has_decay = trail_min is not None
    cost = COST_BPS / 10_000

    trades: list[dict] = []
    blocked_entries: list[int] = []
    in_pos = False
    peak = 0.0
    entry_bar = 0
    entry_price = 0.0

    n_bars = end_bar - start_bar
    equity = np.full(n_bars, np.nan)
    cash = INITIAL_CASH
    position_size = 0.0

    trail_at_exit: list[float] = []
    age_at_exit: list[int] = []

    for i in range(start_bar, end_bar):
        ei = i - start_bar
        if np.isnan(ratr[i]):
            equity[ei] = cash if not in_pos else position_size * c[i]
            continue

        if not in_pos:
            equity[ei] = cash

            base_ok = ema_f[i] > ema_s[i] and vdo_arr[i] > 0 and d1_ok[i]

            if base_ok:
                compression_ok = True
                if has_compression:
                    if np.isfinite(vol_ratio[i]):
                        compression_ok = vol_ratio[i] < compression_thr
                    else:
                        compression_ok = False

                if compression_ok:
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
            equity[ei] = position_size * c[i]
            peak = max(peak, c[i])

            if has_decay:
                current_trail = calc_effective_trail(
                    trend_age[i], trail_min, decay_start, decay_end,
                )
            else:
                current_trail = TRAIL_BASE

            trail_stop = peak - current_trail * ratr[i]
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

                trail_at_exit.append(current_trail)
                age_at_exit.append(int(trend_age[i]))

                trades.append({
                    "entry_bar": entry_bar,
                    "exit_bar": i,
                    "bars_held": i - entry_bar,
                    "net_ret": net_ret,
                    "win": int(net_ret > 0),
                    "exit_reason": exit_reason,
                })

                equity[ei] = cash
                position_size = 0.0
                in_pos = False
                peak = 0.0

    # Force-close any open position at window end
    if in_pos:
        last = end_bar - 1
        ei = last - start_bar
        half_cost = (COST_BPS / 2) / 10_000
        cash = position_size * c[last] * (1 - half_cost)
        gross_ret = (c[last] - entry_price) / entry_price
        net_ret = gross_ret - cost

        current_trail = (
            calc_effective_trail(trend_age[last], trail_min, decay_start, decay_end)
            if has_decay
            else TRAIL_BASE
        )
        trail_at_exit.append(current_trail)
        age_at_exit.append(int(trend_age[last]))

        trades.append({
            "entry_bar": entry_bar,
            "exit_bar": last,
            "bars_held": last - entry_bar,
            "net_ret": net_ret,
            "win": int(net_ret > 0),
            "exit_reason": "window_end",
        })
        equity[ei] = cash

    # ── Compute metrics ───────────────────────────────────────────────
    eq = pd.Series(equity).dropna()
    if len(eq) < 2 or len(trades) == 0:
        return _empty_result()

    rets = eq.pct_change().dropna()
    bars_per_year = 365.25 * 24 / 4

    sharpe = rets.mean() / rets.std() * np.sqrt(bars_per_year) if rets.std() > 0 else 0.0

    total_bars = len(eq)
    years = total_bars / bars_per_year
    final_ret = eq.iloc[-1] / eq.iloc[0]
    cagr = final_ret ** (1 / years) - 1 if years > 0 and final_ret > 0 else 0.0

    cummax = eq.cummax()
    dd = (eq - cummax) / cummax
    mdd = dd.min()

    tdf = pd.DataFrame(trades)
    n_wins = int(tdf["win"].sum())
    win_rate = n_wins / len(trades) * 100

    total_bars_held = sum(t["bars_held"] for t in trades)
    exposure = total_bars_held / total_bars

    return {
        "sharpe": round(sharpe, 4),
        "cagr_pct": round(cagr * 100, 2),
        "mdd_pct": round(abs(mdd) * 100, 2),
        "trades": len(trades),
        "win_rate": round(win_rate, 1),
        "exposure_pct": round(exposure * 100, 1),
        "blocked": len(blocked_entries),
        "avg_trend_age_exit": round(np.mean(age_at_exit), 1) if age_at_exit else np.nan,
        "avg_eff_trail_exit": round(np.mean(trail_at_exit), 3) if trail_at_exit else np.nan,
    }


def _empty_result() -> dict:
    return {
        "sharpe": np.nan, "cagr_pct": np.nan, "mdd_pct": np.nan,
        "trades": 0, "win_rate": np.nan, "exposure_pct": np.nan,
        "blocked": 0, "avg_trend_age_exit": np.nan, "avg_eff_trail_exit": np.nan,
    }


# ═══════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════

def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    # Build decay config grid (constraint: decay_start < decay_end)
    decay_configs = [
        (tm, ds, de)
        for tm in TRAIL_MINS
        for ds in DECAY_STARTS
        for de in DECAY_ENDS
        if ds < de
    ]

    print("=" * 80)
    print("EXP 49: Compression + Maturity Decay Combo Walk-Forward Validation")
    print(f"  Compression threshold: {COMPRESSION_THR} (FIXED, WFO-validated in exp42)")
    print(f"  Decay grid: trail_min={TRAIL_MINS}, decay_start={DECAY_STARTS}, decay_end={DECAY_ENDS}")
    print(f"  Valid decay configs: {len(decay_configs)}")
    print(f"  Fixed A: thr={COMPRESSION_THR} + min=1.5/60/180 (exp44 combo_B optimum)")
    print(f"  Fixed B: thr={COMPRESSION_THR} + min=2.0/60/180 (less aggressive decay)")
    print(f"  Fixed C: thr={COMPRESSION_THR}, no decay (exp42 compression-only)")
    print(f"  Windows: {len(WFO_WINDOWS)} (anchored)")
    print(f"  Cost: {COST_BPS} bps RT, warmup: {WARMUP_DAYS} days")
    print("=" * 80)

    h4, d1 = load_data()
    feat = compute_features(h4, d1)
    datetimes = pd.DatetimeIndex(feat["datetime"])

    ema_f = feat["ema_fast"].values
    ema_s = feat["ema_slow"].values
    trend_age = compute_trend_age(ema_f, ema_s)
    print(f"\nTrend age computed: max={trend_age.max()}")

    bars_per_day = 24 / 4
    warmup_bars = int(WARMUP_DAYS * bars_per_day)

    window_results: list[dict] = []

    for w_idx, w in enumerate(WFO_WINDOWS):
        print(f"\n{'=' * 80}")
        print(f"WINDOW {w_idx + 1}/{len(WFO_WINDOWS)}")
        print(f"  Train: {w['train_start']} -> {w['train_end']}")
        print(f"  Test:  {w['test_start']} -> {w['test_end']}")

        raw_train_start = find_bar_idx(datetimes, w["train_start"], "start")
        train_end = find_bar_idx(datetimes, w["train_end"], "end")
        test_start = find_bar_idx(datetimes, w["test_start"], "start")
        test_end = find_bar_idx(datetimes, w["test_end"], "end")

        # Apply warmup within train window
        train_start = raw_train_start + warmup_bars
        if train_start >= train_end:
            print("  WARNING: warmup exceeds train window, skipping")
            continue

        print(f"  Raw train start:    bar {raw_train_start}")
        print(f"  Warmup train start: bar {train_start} (+{warmup_bars} warmup)")
        print(f"  Train bars: [{train_start}, {train_end}) = {train_end - train_start}")
        print(f"  Test bars:  [{test_start}, {test_end}) = {test_end - test_start}")
        if train_start < len(datetimes) and test_end - 1 < len(datetimes):
            print(f"  Train actual: {datetimes[train_start].date()} -> {datetimes[train_end - 1].date()}")
            print(f"  Test actual:  {datetimes[test_start].date()} -> {datetimes[test_end - 1].date()}")

        # ── Step 1: Train — fix thr=0.7, sweep 18 decay configs ─────
        print(f"\n  [TRAIN] Sweeping {len(decay_configs)} decay configs "
              f"(compression thr={COMPRESSION_THR} fixed)...")

        best_train_sharpe = -np.inf
        best_decay: tuple[float, int, int] = decay_configs[0]
        train_grid: list[tuple[float, int, int, float]] = []

        for trail_min, decay_start, decay_end in decay_configs:
            r = run_backtest(
                feat, trend_age, train_start, train_end,
                compression_thr=COMPRESSION_THR,
                trail_min=trail_min, decay_start=decay_start, decay_end=decay_end,
            )
            train_grid.append((trail_min, decay_start, decay_end, r["sharpe"]))
            if np.isfinite(r["sharpe"]) and r["sharpe"] > best_train_sharpe:
                best_train_sharpe = r["sharpe"]
                best_decay = (trail_min, decay_start, decay_end)

        train_comp_only = run_backtest(
            feat, trend_age, train_start, train_end,
            compression_thr=COMPRESSION_THR,
        )
        train_baseline = run_backtest(feat, trend_age, train_start, train_end)

        print(f"  Train baseline:   Sharpe={train_baseline['sharpe']}, "
              f"trades={train_baseline['trades']}")
        print(f"  Train comp-only:  Sharpe={train_comp_only['sharpe']}, "
              f"trades={train_comp_only['trades']}")
        print(f"  Best train combo: min={best_decay[0]}, start={best_decay[1]}, "
              f"end={best_decay[2]}, Sharpe={best_train_sharpe:.4f}")

        print("  Train grid (top 5 by Sharpe):")
        sorted_grid = sorted(
            train_grid,
            key=lambda x: x[3] if np.isfinite(x[3]) else -999,
            reverse=True,
        )
        for tm, ds, de, sh in sorted_grid[:5]:
            marker = " *" if (tm, ds, de) == best_decay else "  "
            print(f"    min={tm}, start={ds:>3d}, end={de:>3d}  "
                  f"Sharpe={sh:.4f}{marker}")

        # ── Step 2: Test — selected + fixed A/B/C + baseline ─────────
        print(f"\n  [TEST] Running on test period...")

        test_baseline = run_backtest(feat, trend_age, test_start, test_end)

        test_selected = run_backtest(
            feat, trend_age, test_start, test_end,
            compression_thr=COMPRESSION_THR,
            trail_min=best_decay[0],
            decay_start=best_decay[1],
            decay_end=best_decay[2],
        )

        # Fixed A: thr=0.7 + min=1.5/60/180 (exp44 combo_B optimum)
        test_fixed_a = run_backtest(
            feat, trend_age, test_start, test_end,
            compression_thr=COMPRESSION_THR,
            trail_min=1.5, decay_start=60, decay_end=180,
        )

        # Fixed B: thr=0.7 + min=2.0/60/180 (less aggressive decay)
        test_fixed_b = run_backtest(
            feat, trend_age, test_start, test_end,
            compression_thr=COMPRESSION_THR,
            trail_min=2.0, decay_start=60, decay_end=180,
        )

        # Fixed C: thr=0.7, no decay (exp42 compression-only)
        test_comp_only = run_backtest(
            feat, trend_age, test_start, test_end,
            compression_thr=COMPRESSION_THR,
        )

        def delta(a: float, b: float) -> float:
            return round(a - b, 4) if np.isfinite(a) and np.isfinite(b) else np.nan

        # Deltas vs baseline
        d_sh_sel = delta(test_selected["sharpe"], test_baseline["sharpe"])
        d_mdd_sel = delta(test_selected["mdd_pct"], test_baseline["mdd_pct"])
        d_sh_fa = delta(test_fixed_a["sharpe"], test_baseline["sharpe"])
        d_mdd_fa = delta(test_fixed_a["mdd_pct"], test_baseline["mdd_pct"])
        d_sh_fb = delta(test_fixed_b["sharpe"], test_baseline["sharpe"])
        d_mdd_fb = delta(test_fixed_b["mdd_pct"], test_baseline["mdd_pct"])
        d_sh_comp = delta(test_comp_only["sharpe"], test_baseline["sharpe"])
        d_mdd_comp = delta(test_comp_only["mdd_pct"], test_baseline["mdd_pct"])

        # Marginal decay value = combo - compression-only
        marg_sel = delta(test_selected["sharpe"], test_comp_only["sharpe"])
        marg_fa = delta(test_fixed_a["sharpe"], test_comp_only["sharpe"])
        marg_fb = delta(test_fixed_b["sharpe"], test_comp_only["sharpe"])

        print(f"  Test baseline:    Sharpe={test_baseline['sharpe']:>8.4f}, "
              f"CAGR={test_baseline['cagr_pct']:>7.2f}%, "
              f"MDD={test_baseline['mdd_pct']:>5.2f}%, "
              f"trades={test_baseline['trades']}")
        print(f"  Test comp-only:   Sharpe={test_comp_only['sharpe']:>8.4f} "
              f"(d={d_sh_comp:+.4f}), "
              f"MDD={test_comp_only['mdd_pct']:>5.2f}% (d={d_mdd_comp:+.2f}pp), "
              f"trades={test_comp_only['trades']}, "
              f"blocked={test_comp_only['blocked']}")
        print(f"  Test selected:    Sharpe={test_selected['sharpe']:>8.4f} "
              f"(d={d_sh_sel:+.4f}, marg={marg_sel:+.4f}), "
              f"MDD={test_selected['mdd_pct']:>5.2f}% (d={d_mdd_sel:+.2f}pp), "
              f"trades={test_selected['trades']}, "
              f"blocked={test_selected['blocked']}, "
              f"avg_trail={test_selected['avg_eff_trail_exit']}")
        print(f"  Test fixed A:     Sharpe={test_fixed_a['sharpe']:>8.4f} "
              f"(d={d_sh_fa:+.4f}, marg={marg_fa:+.4f}), "
              f"MDD={test_fixed_a['mdd_pct']:>5.2f}% (d={d_mdd_fa:+.2f}pp), "
              f"trades={test_fixed_a['trades']}, "
              f"blocked={test_fixed_a['blocked']}, "
              f"avg_trail={test_fixed_a['avg_eff_trail_exit']}")
        print(f"  Test fixed B:     Sharpe={test_fixed_b['sharpe']:>8.4f} "
              f"(d={d_sh_fb:+.4f}, marg={marg_fb:+.4f}), "
              f"MDD={test_fixed_b['mdd_pct']:>5.2f}% (d={d_mdd_fb:+.2f}pp), "
              f"trades={test_fixed_b['trades']}, "
              f"blocked={test_fixed_b['blocked']}, "
              f"avg_trail={test_fixed_b['avg_eff_trail_exit']}")

        sel_wins_sh = int(np.isfinite(d_sh_sel) and d_sh_sel > 0)
        fa_wins_sh = int(np.isfinite(d_sh_fa) and d_sh_fa > 0)
        fb_wins_sh = int(np.isfinite(d_sh_fb) and d_sh_fb > 0)
        comp_wins_sh = int(np.isfinite(d_sh_comp) and d_sh_comp > 0)
        marg_sel_win = int(np.isfinite(marg_sel) and marg_sel > 0)
        marg_fa_win = int(np.isfinite(marg_fa) and marg_fa > 0)
        marg_fb_win = int(np.isfinite(marg_fb) and marg_fb > 0)

        window_results.append({
            "window": w_idx + 1,
            "train_period": f"{w['train_start']} -> {w['train_end']}",
            "test_period": f"{w['test_start']} -> {w['test_end']}",
            "train_bars": train_end - train_start,
            "test_bars": test_end - test_start,
            # Train
            "train_baseline_sharpe": train_baseline["sharpe"],
            "train_comp_only_sharpe": train_comp_only["sharpe"],
            "train_best_combo_sharpe": round(best_train_sharpe, 4),
            "selected_trail_min": best_decay[0],
            "selected_decay_start": best_decay[1],
            "selected_decay_end": best_decay[2],
            # Test baseline
            "test_baseline_sharpe": test_baseline["sharpe"],
            "test_baseline_cagr": test_baseline["cagr_pct"],
            "test_baseline_mdd": test_baseline["mdd_pct"],
            "test_baseline_trades": test_baseline["trades"],
            # Test comp-only (Fixed C)
            "test_comp_only_sharpe": test_comp_only["sharpe"],
            "test_comp_only_cagr": test_comp_only["cagr_pct"],
            "test_comp_only_mdd": test_comp_only["mdd_pct"],
            "test_comp_only_trades": test_comp_only["trades"],
            "test_comp_only_blocked": test_comp_only["blocked"],
            "d_sharpe_comp_only": d_sh_comp,
            "d_mdd_comp_only": d_mdd_comp,
            "comp_only_wins_sharpe": comp_wins_sh,
            # Test selected combo
            "test_selected_sharpe": test_selected["sharpe"],
            "test_selected_cagr": test_selected["cagr_pct"],
            "test_selected_mdd": test_selected["mdd_pct"],
            "test_selected_trades": test_selected["trades"],
            "test_selected_blocked": test_selected["blocked"],
            "test_selected_avg_trail": test_selected["avg_eff_trail_exit"],
            "test_selected_avg_age": test_selected["avg_trend_age_exit"],
            "d_sharpe_selected": d_sh_sel,
            "d_mdd_selected": d_mdd_sel,
            "selected_wins_sharpe": sel_wins_sh,
            "marginal_decay_selected": marg_sel,
            "marginal_decay_selected_win": marg_sel_win,
            # Test fixed A
            "test_fixedA_sharpe": test_fixed_a["sharpe"],
            "test_fixedA_cagr": test_fixed_a["cagr_pct"],
            "test_fixedA_mdd": test_fixed_a["mdd_pct"],
            "test_fixedA_trades": test_fixed_a["trades"],
            "test_fixedA_blocked": test_fixed_a["blocked"],
            "test_fixedA_avg_trail": test_fixed_a["avg_eff_trail_exit"],
            "d_sharpe_fixedA": d_sh_fa,
            "d_mdd_fixedA": d_mdd_fa,
            "fixedA_wins_sharpe": fa_wins_sh,
            "marginal_decay_fixedA": marg_fa,
            "marginal_decay_fixedA_win": marg_fa_win,
            # Test fixed B
            "test_fixedB_sharpe": test_fixed_b["sharpe"],
            "test_fixedB_cagr": test_fixed_b["cagr_pct"],
            "test_fixedB_mdd": test_fixed_b["mdd_pct"],
            "test_fixedB_trades": test_fixed_b["trades"],
            "test_fixedB_blocked": test_fixed_b["blocked"],
            "test_fixedB_avg_trail": test_fixed_b["avg_eff_trail_exit"],
            "d_sharpe_fixedB": d_sh_fb,
            "d_mdd_fixedB": d_mdd_fb,
            "fixedB_wins_sharpe": fb_wins_sh,
            "marginal_decay_fixedB": marg_fb,
            "marginal_decay_fixedB_win": marg_fb_win,
        })

    # ═══════════════════════════════════════════════════════════════════
    # Aggregate
    # ═══════════════════════════════════════════════════════════════════
    df = pd.DataFrame(window_results)
    n_windows = len(df)

    print("\n" + "=" * 80)
    print("AGGREGATE RESULTS")
    print("=" * 80)

    # ── Compression-only (Fixed C) ───────────────────────────────────
    comp_wins = int(df["comp_only_wins_sharpe"].sum())
    comp_wr = comp_wins / n_windows
    comp_mean = df["d_sharpe_comp_only"].mean()
    comp_mdd_mean = df["d_mdd_comp_only"].mean()

    print(f"\n  COMPRESSION-ONLY (thr={COMPRESSION_THR}, no decay):")
    print(f"    WFO win rate:       {comp_wins}/{n_windows} = {comp_wr * 100:.0f}%")
    print(f"    Mean d_Sharpe:      {comp_mean:+.4f}")
    print(f"    d_Sharpe per window: {[round(x, 4) for x in df['d_sharpe_comp_only']]}")
    print(f"    Mean d_MDD:         {comp_mdd_mean:+.2f} pp")
    print(f"    d_MDD per window:    {[round(x, 2) for x in df['d_mdd_comp_only']]}")

    # ── Train-selected combo ─────────────────────────────────────────
    sel_wins = int(df["selected_wins_sharpe"].sum())
    sel_wr = sel_wins / n_windows
    sel_mean = df["d_sharpe_selected"].mean()
    sel_mdd_mean = df["d_mdd_selected"].mean()
    sel_marg_wins = int(df["marginal_decay_selected_win"].sum())
    sel_marg_mean = df["marginal_decay_selected"].mean()

    print(f"\n  TRAIN-SELECTED COMBO:")
    print(f"    WFO win rate (vs base):  {sel_wins}/{n_windows} = {sel_wr * 100:.0f}%")
    print(f"    Mean d_Sharpe (vs base): {sel_mean:+.4f}")
    print(f"    d_Sharpe per window:     {[round(x, 4) for x in df['d_sharpe_selected']]}")
    print(f"    Mean d_MDD:              {sel_mdd_mean:+.2f} pp")
    print(f"    Marginal decay wins:     {sel_marg_wins}/{n_windows}")
    print(f"    Mean marginal decay:     {sel_marg_mean:+.4f}")
    print(f"    Marginal per window:     {[round(x, 4) for x in df['marginal_decay_selected']]}")

    # ── Fixed A ──────────────────────────────────────────────────────
    fa_wins = int(df["fixedA_wins_sharpe"].sum())
    fa_wr = fa_wins / n_windows
    fa_mean = df["d_sharpe_fixedA"].mean()
    fa_mdd_mean = df["d_mdd_fixedA"].mean()
    fa_marg_wins = int(df["marginal_decay_fixedA_win"].sum())
    fa_marg_mean = df["marginal_decay_fixedA"].mean()

    print(f"\n  FIXED A (thr={COMPRESSION_THR}, min=1.5, start=60, end=180):")
    print(f"    WFO win rate (vs base):  {fa_wins}/{n_windows} = {fa_wr * 100:.0f}%")
    print(f"    Mean d_Sharpe (vs base): {fa_mean:+.4f}")
    print(f"    d_Sharpe per window:     {[round(x, 4) for x in df['d_sharpe_fixedA']]}")
    print(f"    Mean d_MDD:              {fa_mdd_mean:+.2f} pp")
    print(f"    Marginal decay wins:     {fa_marg_wins}/{n_windows}")
    print(f"    Mean marginal decay:     {fa_marg_mean:+.4f}")
    print(f"    Marginal per window:     {[round(x, 4) for x in df['marginal_decay_fixedA']]}")

    # ── Fixed B ──────────────────────────────────────────────────────
    fb_wins = int(df["fixedB_wins_sharpe"].sum())
    fb_wr = fb_wins / n_windows
    fb_mean = df["d_sharpe_fixedB"].mean()
    fb_mdd_mean = df["d_mdd_fixedB"].mean()
    fb_marg_wins = int(df["marginal_decay_fixedB_win"].sum())
    fb_marg_mean = df["marginal_decay_fixedB"].mean()

    print(f"\n  FIXED B (thr={COMPRESSION_THR}, min=2.0, start=60, end=180):")
    print(f"    WFO win rate (vs base):  {fb_wins}/{n_windows} = {fb_wr * 100:.0f}%")
    print(f"    Mean d_Sharpe (vs base): {fb_mean:+.4f}")
    print(f"    d_Sharpe per window:     {[round(x, 4) for x in df['d_sharpe_fixedB']]}")
    print(f"    Mean d_MDD:              {fb_mdd_mean:+.2f} pp")
    print(f"    Marginal decay wins:     {fb_marg_wins}/{n_windows}")
    print(f"    Mean marginal decay:     {fb_marg_mean:+.4f}")
    print(f"    Marginal per window:     {[round(x, 4) for x in df['marginal_decay_fixedB']]}")

    # ── Parameter stability ──────────────────────────────────────────
    print(f"\n  PARAMETER STABILITY (train-selected decay params):")
    for _, row in df.iterrows():
        print(f"    W{int(row['window'])}: min={row['selected_trail_min']}, "
              f"start={int(row['selected_decay_start'])}, "
              f"end={int(row['selected_decay_end'])}")
    unique_cfgs = df[
        ["selected_trail_min", "selected_decay_start", "selected_decay_end"]
    ].drop_duplicates()
    n_unique = len(unique_cfgs)
    stability = (
        "STABLE" if n_unique <= 2
        else "MODERATE" if n_unique <= 3
        else "UNSTABLE"
    )
    print(f"    Unique configs: {n_unique}/{n_windows} -> {stability}")

    # ── Bear vs bull regime ──────────────────────────────────────────
    print(f"\n  BEAR vs BULL REGIME (Fixed A marginal decay):")
    regime_labels = ["bear", "bear->bull", "bull", "bull"]
    for idx, row in df.iterrows():
        w_num = int(row["window"])
        label = regime_labels[w_num - 1] if w_num <= len(regime_labels) else "?"
        print(f"    W{w_num} ({label:>10s}): "
              f"combo d_Sh={row['d_sharpe_fixedA']:+.4f}, "
              f"comp d_Sh={row['d_sharpe_comp_only']:+.4f}, "
              f"marginal={row['marginal_decay_fixedA']:+.4f}")

    bear_marg = df[df["window"].isin([1, 2])]["marginal_decay_fixedA"].mean()
    bull_marg = df[df["window"].isin([3, 4])]["marginal_decay_fixedA"].mean()
    print(f"    Bear mean marginal: {bear_marg:+.4f}")
    print(f"    Bull mean marginal: {bull_marg:+.4f}")

    if bear_marg > 0 and bull_marg > 0:
        regime_pattern = "BOTH (decay helps in both regimes after compression)"
    elif bear_marg > 0:
        regime_pattern = "BEAR-ONLY (same as standalone decay)"
    elif bull_marg > 0:
        regime_pattern = "BULL-ONLY"
    else:
        regime_pattern = "NEITHER (decay hurts after compression)"
    print(f"    Regime pattern: {regime_pattern}")

    # ═══════════════════════════════════════════════════════════════════
    # CRITICAL ANALYSIS: Marginal decay value
    # ═══════════════════════════════════════════════════════════════════
    print("\n" + "=" * 80)
    print("CRITICAL ANALYSIS: Does decay add value on top of compression?")
    print("=" * 80)

    for label, marg_col, marg_win_col in [
        ("Selected", "marginal_decay_selected", "marginal_decay_selected_win"),
        ("Fixed A", "marginal_decay_fixedA", "marginal_decay_fixedA_win"),
        ("Fixed B", "marginal_decay_fixedB", "marginal_decay_fixedB_win"),
    ]:
        mw = int(df[marg_win_col].sum())
        mm = df[marg_col].mean()
        pass_marg = mw >= 3 and mm > 0

        print(f"\n  {label}:")
        print(f"    Marginal wins:  {mw}/{n_windows} (need >=3)")
        print(f"    Mean marginal:  {mm:+.4f}")
        print(f"    Per window:     {[round(x, 4) for x in df[marg_col]]}")
        print(f"    -> Marginal test: {'PASS' if pass_marg else 'FAIL'}")

    # ═══════════════════════════════════════════════════════════════════
    # VERDICT
    # ═══════════════════════════════════════════════════════════════════
    print("\n" + "=" * 80)
    print("VERDICT")
    print("=" * 80)

    combo_verdicts = []
    for label, wins_col, d_sh_col in [
        ("Selected", "selected_wins_sharpe", "d_sharpe_selected"),
        ("Fixed A", "fixedA_wins_sharpe", "d_sharpe_fixedA"),
        ("Fixed B", "fixedB_wins_sharpe", "d_sharpe_fixedB"),
    ]:
        w = int(df[wins_col].sum())
        wr = w / n_windows
        mean_d = df[d_sh_col].mean()
        pass_wr = wr >= 0.75
        pass_mean = mean_d > 0
        overall = "PASS" if pass_wr and pass_mean else "FAIL"
        combo_verdicts.append((label, overall))

        print(f"\n  {label} (combo vs baseline):")
        print(f"    WFO win rate >= 75%:  {'PASS' if pass_wr else 'FAIL'} ({wr * 100:.0f}%)")
        print(f"    Mean d_Sharpe > 0:    {'PASS' if pass_mean else 'FAIL'} ({mean_d:+.4f})")
        print(f"    Overall:              {overall}")

    # Compression-only WFO (exp42 reproduction)
    comp_pass_wr = comp_wr >= 0.75
    comp_pass_mean = comp_mean > 0
    comp_overall = "PASS" if comp_pass_wr and comp_pass_mean else "FAIL"

    print(f"\n  Compression-only (exp42 reproduction):")
    print(f"    WFO win rate >= 75%:  {'PASS' if comp_pass_wr else 'FAIL'} ({comp_wr * 100:.0f}%)")
    print(f"    Mean d_Sharpe > 0:    {'PASS' if comp_pass_mean else 'FAIL'} ({comp_mean:+.4f})")
    print(f"    Overall:              {comp_overall}")

    # Marginal decay verdict (Fixed A as primary)
    fa_marg_pass = fa_marg_wins >= 3 and fa_marg_mean > 0

    print(f"\n  Parameter stability:    {stability} ({n_unique} unique)")

    any_combo_pass = any(v == "PASS" for _, v in combo_verdicts)

    print(f"\n  {'=' * 62}")
    if any_combo_pass and fa_marg_pass:
        verdict = "COMBO_PASS"
        print(f"  VERDICT: COMBO PASS")
        print(f"  -> Deploy compression + decay. Compression cleans trade")
        print(f"     population enough for decay to be WFO-stable.")
        print(f"  -> Combo dominates compression-only (marginal value confirmed).")
    elif any_combo_pass and not fa_marg_pass:
        verdict = "COMPRESSION_ONLY"
        print(f"  VERDICT: COMPRESSION ONLY")
        print(f"  -> Combo passes WFO vs baseline, but decay adds no marginal")
        print(f"     value on top of compression. Deploy compression alone (thr={COMPRESSION_THR}).")
        print(f"  -> Maturity decay is fundamentally regime-dependent regardless")
        print(f"     of entry population.")
    else:
        verdict = "FAIL"
        print(f"  VERDICT: FAIL")
        print(f"  -> Combo not WFO-robust vs baseline.")
    print(f"  {'=' * 62}")

    # ── Save ──────────────────────────────────────────────────────────
    out_path = RESULTS_DIR / "exp49_results.csv"
    df.to_csv(out_path, index=False)
    print(f"\n-> Saved to {out_path}")


if __name__ == "__main__":
    main()
