#!/usr/bin/env python3
"""X36 VCBB Bias Test Battery — resolves V3 vs E5 debate empirically.

Test 1: Block-size sensitivity (5 blksz × 3 strategies × 500 paths)
        → Does bootstrap Sharpe change with block size?
Test 2: Regime-conditioned bootstrap (500 paths × 3 strategies)
        → Does regime conditioning help V3 disproportionately?
Test 3: Time-stop/cooldown ablation on E5 (500 paths × 5 variants)
        → Do V3's mechanisms improve or hurt E5's bootstrap?

Expected runtime: ~2.5 hours
Output: research/x36/branches/a_vcbb_bias_study/test_battery/{results,figures}/
"""

from __future__ import annotations

import json
import math
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ── Project imports ──────────────────────────────────────────────────

ROOT = Path("/var/www/trading-bots/btc-spot-dev")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "research" / "x36" / "branches" / "a_vcbb_bias_study"))

from v10.core.engine import BacktestEngine
from v10.core.types import Bar, CostConfig, Side, Signal, Fill, MarketState
from v10.strategies.base import Strategy

from strategies.vtrend_e5_ema21_d1.strategy import (
    VTrendE5Ema21D1Strategy,
    VTrendE5Ema21D1Config,
)
from v3v4_strategies import V3Strategy, V4Strategy
from research.lib.vcbb import (
    make_ratios, precompute_vcbb, gen_path_vcbb, _build_path_5ch,
)
from run_comparison import (
    _fast_load_bars, PreloadedFeed, make_sub_feed,
    extract_metrics, make_cost,
    _build_synthetic_feed, _date_ms,
    COST_20, BASE_TS, H4_MS, D1_MS,
)

# ── Constants ────────────────────────────────────────────────────────

DATA_PATH = ROOT / "data" / "bars_btcusdt_2016_now_h1_4h_1d.csv"
OUT = ROOT / "research" / "x36" / "branches" / "a_vcbb_bias_study" / "test_battery"
RESULTS = OUT / "results"
FIGURES = OUT / "figures"

START = "2019-01-01"
END = "2026-02-20"
WARMUP = 365
N_BOOT = 500
CTX = 90
K_NN = 50
SEED = 42  # Different from X36's 1337

BLOCK_SIZES = [30, 60, 120, 180, 360]

STRAT_NAMES_3 = ["V3", "V4", "E5+EMA21D1"]
ABLATION_NAMES = ["E5_base", "E5+TS30", "E5+CD6", "E5+TS30+CD6", "V3"]

COLORS = {
    "V3": "#e63946", "V4": "#457b9d", "E5+EMA21D1": "#2a9d8f",
    "E5_base": "#2a9d8f", "E5+TS30": "#e9c46a",
    "E5+CD6": "#f4a261", "E5+TS30+CD6": "#264653",
}

EPOCHS = [
    ("Pre-2021", "2019-01-01", "2020-12-31"),
    ("2021-2022", "2021-01-01", "2022-12-31"),
    ("2023-2024", "2023-01-01", "2024-12-31"),
    ("2025+", "2025-01-01", "2026-02-20"),
]


# ═══════════════════════════════════════════════════════════════════════
# SHARED HELPERS
# ═══════════════════════════════════════════════════════════════════════


def _ema_np(series: np.ndarray, period: int) -> np.ndarray:
    """EMA for numpy arrays (used for regime computation)."""
    alpha = 2.0 / (period + 1)
    out = np.empty_like(series)
    out[0] = series[0]
    for i in range(1, len(series)):
        out[i] = alpha * series[i] + (1 - alpha) * out[i - 1]
    return out


def _extract_arrays(h4_bars):
    """Extract numpy arrays from H4 bars."""
    cl = np.array([b.close for b in h4_bars], dtype=np.float64)
    hi = np.array([b.high for b in h4_bars], dtype=np.float64)
    lo = np.array([b.low for b in h4_bars], dtype=np.float64)
    vo = np.array([b.volume for b in h4_bars], dtype=np.float64)
    tb = np.array([b.taker_buy_base_vol for b in h4_bars], dtype=np.float64)
    return cl, hi, lo, vo, tb


def _boot_summary(metrics_list: list[dict], key: str) -> dict:
    """Compute bootstrap summary statistics for a metric."""
    vals = [d[key] for d in metrics_list if d.get(key) is not None]
    vals = [v for v in vals if v is not None and np.isfinite(v)]
    if not vals:
        return {"median": None, "mean": None, "p5": None, "p95": None,
                "p_gt_0": None, "n_valid": 0}
    arr = np.array(vals, dtype=np.float64)
    return {
        "median": float(np.median(arr)),
        "mean": float(np.mean(arr)),
        "p5": float(np.percentile(arr, 5)),
        "p95": float(np.percentile(arr, 95)),
        "p_gt_0": float(np.mean(arr > 0)),
        "n_valid": len(arr),
    }


# ═══════════════════════════════════════════════════════════════════════
# E5 ABLATION STRATEGY (for Test 3)
# ═══════════════════════════════════════════════════════════════════════


class E5Ablation(VTrendE5Ema21D1Strategy):
    """E5+EMA21D1 with optional time_stop and cooldown for ablation study.

    Inherits all E5 indicator computation and entry/exit logic.
    Adds V3-style time_stop and/or cooldown as gating mechanisms.
    """

    def __init__(self, time_stop_bars: int = 0, cooldown_bars: int = 0):
        super().__init__()
        self._time_stop_bars = time_stop_bars
        self._cooldown_bars = cooldown_bars
        self._entry_fill_bar: int | None = None
        self._last_exit_bar: int | None = None

    def name(self) -> str:
        parts = ["e5"]
        if self._time_stop_bars > 0:
            parts.append(f"ts{self._time_stop_bars}")
        if self._cooldown_bars > 0:
            parts.append(f"cd{self._cooldown_bars}")
        return "_".join(parts) if len(parts) > 1 else "e5_base"

    def on_bar(self, state: MarketState) -> Signal | None:
        i = state.bar_index

        # Cooldown gate (before E5 entry logic)
        if not self._in_position and self._cooldown_bars > 0:
            if self._last_exit_bar is not None:
                if (i + 1) <= self._last_exit_bar + self._cooldown_bars:
                    return None

        # Standard E5 logic (entry, trail stop, trend exit)
        signal = super().on_bar(state)

        # Time stop (if E5 didn't already exit and we're in position)
        if signal is None and self._in_position and self._time_stop_bars > 0:
            if self._entry_fill_bar is not None:
                if (i + 1) >= self._entry_fill_bar + self._time_stop_bars:
                    self._in_position = False
                    self._peak_price = 0.0
                    return Signal(
                        target_exposure=0.0,
                        reason=f"{self.name()}_time_stop",
                    )

        return signal

    def on_after_fill(self, state: MarketState, fill: Fill) -> None:
        super().on_after_fill(state, fill)
        if fill.side == Side.BUY:
            self._entry_fill_bar = state.bar_index
        else:
            self._last_exit_bar = state.bar_index
            self._entry_fill_bar = None


# ═══════════════════════════════════════════════════════════════════════
# STRATEGY FACTORY
# ═══════════════════════════════════════════════════════════════════════


def _make_strat(name: str) -> Strategy:
    if name == "V3":
        return V3Strategy()
    if name == "V4":
        return V4Strategy()
    if name in ("E5+EMA21D1", "E5_base"):
        return VTrendE5Ema21D1Strategy()
    if name == "E5+TS30":
        return E5Ablation(time_stop_bars=30)
    if name == "E5+CD6":
        return E5Ablation(cooldown_bars=6)
    if name == "E5+TS30+CD6":
        return E5Ablation(time_stop_bars=30, cooldown_bars=6)
    raise ValueError(f"Unknown strategy: {name}")


def _run_one(feed, name: str, cost=COST_20):
    s = _make_strat(name)
    e = BacktestEngine(
        feed=feed, strategy=s, cost=cost,
        initial_cash=10_000.0, warmup_mode="no_trade",
    )
    return e.run()


def _safe_run(feed, name: str, cost=COST_20) -> dict:
    """Run backtest with error handling for degenerate paths."""
    try:
        r = _run_one(feed, name, cost)
        return extract_metrics(r)
    except Exception:
        return {"sharpe": None, "cagr_pct": None, "max_dd_pct": None,
                "trades": None}


# ═══════════════════════════════════════════════════════════════════════
# TEST 1: BLOCK-SIZE SENSITIVITY
# ═══════════════════════════════════════════════════════════════════════


def test1_blocksize(all_h4: list) -> dict:
    """Run VCBB bootstrap with 5 different block sizes.

    Returns dict[blksz] -> dict[strategy] -> list[metric_dicts]
    """
    print("\n" + "=" * 70)
    print("TEST 1: Block-Size Sensitivity")
    print(f"  Block sizes: {BLOCK_SIZES}")
    print(f"  Strategies: {STRAT_NAMES_3}")
    print(f"  Paths per config: {N_BOOT}")
    print(f"  Total backtests: {len(BLOCK_SIZES) * N_BOOT * len(STRAT_NAMES_3)}")
    print("=" * 70)

    cl, hi, lo, vo, tb = _extract_arrays(all_h4)
    cr, hr, lr, vol_r, tb_r = make_ratios(cl, hi, lo, vo, tb)
    n_trans = len(cr)
    p0 = cl[0]
    src_base_ts = all_h4[0].open_time

    results = {}
    t0_total = time.time()

    for blksz in BLOCK_SIZES:
        print(f"\n  --- blksz={blksz} ({blksz * 4 / 24:.0f} days) ---")
        vcbb = precompute_vcbb(cr, blksz, CTX)
        rng = np.random.default_rng(SEED + blksz)

        boot: dict[str, list[dict]] = {n: [] for n in STRAT_NAMES_3}
        t0 = time.time()

        for pi in range(N_BOOT):
            if pi % 100 == 0:
                elapsed = time.time() - t0
                print(f"    Path {pi}/{N_BOOT}  ({elapsed:.0f}s)")

            c, h, l, v, t = gen_path_vcbb(
                cr, hr, lr, vol_r, tb_r, n_trans, blksz, p0, rng,
                vcbb=vcbb, K=K_NN,
            )
            qv = c * v
            feed = _build_synthetic_feed(c, h, l, v, t, qv, base_ts=src_base_ts)

            for name in STRAT_NAMES_3:
                boot[name].append(_safe_run(feed, name))

        elapsed = time.time() - t0
        print(f"    blksz={blksz} done in {elapsed:.0f}s")

        # Print quick summary
        for name in STRAT_NAMES_3:
            s = _boot_summary(boot[name], "sharpe")
            print(f"      {name}: med_Sh={s['median']:.3f}, "
                  f"P(Sh>0)={s['p_gt_0']:.1%}")

        results[blksz] = boot

    total_elapsed = time.time() - t0_total
    print(f"\n  Test 1 total: {total_elapsed:.0f}s ({total_elapsed/60:.1f}min)")

    # Save raw results
    _save_test1(results)
    return results


def _save_test1(results: dict):
    """Save Test 1 results to JSON."""
    out = {}
    for blksz, boot in results.items():
        out[str(blksz)] = {}
        for name, metrics_list in boot.items():
            out[str(blksz)][name] = {
                "sharpe": _boot_summary(metrics_list, "sharpe"),
                "cagr_pct": _boot_summary(metrics_list, "cagr_pct"),
                "max_dd_pct": _boot_summary(metrics_list, "max_dd_pct"),
                "trades": _boot_summary(metrics_list, "trades"),
            }
    with open(RESULTS / "test1_blocksize.json", "w") as f:
        json.dump(out, f, indent=2)
    print(f"  Saved: {RESULTS / 'test1_blocksize.json'}")


# ═══════════════════════════════════════════════════════════════════════
# TEST 2: REGIME-CONDITIONED BOOTSTRAP
# ═══════════════════════════════════════════════════════════════════════


def _compute_regime_segments(h4_bars, d1_bars):
    """Compute D1 EMA(21) regime labels → contiguous segments.

    Returns:
        segments: list of (start, length, is_bull) in ratio-space
        ratio_regime: bool array of length len(h4_bars) - 1
    """
    n_h4 = len(h4_bars)

    # D1 EMA(21) regime
    d1_close = np.array([b.close for b in d1_bars], dtype=np.float64)
    d1_ema = _ema_np(d1_close, 21)
    d1_regime = d1_close > d1_ema  # True = bull
    d1_ct = [b.close_time for b in d1_bars]

    # Map D1 regime to H4 bars
    h4_regime = np.zeros(n_h4, dtype=np.bool_)
    d1_idx = 0
    n_d1 = len(d1_bars)
    for i in range(n_h4):
        h4_ct = h4_bars[i].close_time
        while d1_idx + 1 < n_d1 and d1_ct[d1_idx + 1] < h4_ct:
            d1_idx += 1
        if d1_ct[d1_idx] < h4_ct:
            h4_regime[i] = d1_regime[d1_idx]

    # Regime for ratios: ratio[i] = bar[i] → bar[i+1], use regime at bar[i]
    ratio_regime = h4_regime[:-1]

    # Find contiguous segments
    segments: list[tuple[int, int, bool]] = []
    i = 0
    n = len(ratio_regime)
    while i < n:
        is_bull = bool(ratio_regime[i])
        j = i + 1
        while j < n and bool(ratio_regime[j]) == is_bull:
            j += 1
        segments.append((i, j - i, is_bull))
        i = j

    return segments, ratio_regime


def _gen_regime_path_idx(
    segments: list[tuple[int, int, bool]],
    n_trans: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """Generate index array for regime-conditioned bootstrap.

    For each segment in the original regime sequence, draws replacement
    data from a randomly chosen segment of the SAME regime type.
    Conditions on: source regime type (bull→bull, bear→bear).
    Preserves in sampling: segment sequence and durations.
    Does NOT preserve realized regime on output paths (~38% match
    due to path-dependent EMA accumulation).
    Randomizes: which specific within-regime realization is used.
    """
    bull_segs = [(s, l) for s, l, b in segments if b]
    bear_segs = [(s, l) for s, l, b in segments if not b]

    # Fallback if one type is empty
    if not bull_segs:
        bull_segs = bear_segs
    if not bear_segs:
        bear_segs = bull_segs

    idx: list[int] = []
    for _seg_start, seg_len, is_bull in segments:
        pool = bull_segs if is_bull else bear_segs
        remaining = seg_len
        while remaining > 0:
            # Pick random donor segment from same regime type
            donor_start, donor_len = pool[int(rng.integers(0, len(pool)))]
            # Random offset within donor
            max_offset = max(0, donor_len - 1)
            offset = int(rng.integers(0, max_offset + 1))
            take = min(remaining, donor_len - offset)
            idx.extend(range(donor_start + offset, donor_start + offset + take))
            remaining -= take

    return np.array(idx[:n_trans], dtype=np.int64)


def test2_regime_bootstrap(all_h4: list, all_d1: list) -> dict:
    """Run regime-conditioned bootstrap and compare with standard VCBB.

    Returns dict with keys "regime" and "vcbb", each containing
    dict[strategy] -> list[metric_dicts]
    """
    print("\n" + "=" * 70)
    print("TEST 2: Regime-Conditioned Bootstrap")
    print(f"  Strategies: {STRAT_NAMES_3}")
    print(f"  Paths: {N_BOOT} (regime-conditioned) + {N_BOOT} (VCBB control)")
    print(f"  Total backtests: {2 * N_BOOT * len(STRAT_NAMES_3)}")
    print("=" * 70)

    cl, hi, lo, vo, tb = _extract_arrays(all_h4)
    cr, hr, lr, vol_r, tb_r = make_ratios(cl, hi, lo, vo, tb)
    n_trans = len(cr)
    p0 = cl[0]
    src_base_ts = all_h4[0].open_time

    # Compute regime segments
    segments, ratio_regime = _compute_regime_segments(all_h4, all_d1)
    n_bull = sum(l for _, l, b in segments if b)
    n_bear = sum(l for _, l, b in segments if not b)
    print(f"  Regime segments: {len(segments)} "
          f"(bull: {n_bull} bars, bear: {n_bear} bars)")

    results = {}

    # --- Part A: Regime-conditioned bootstrap ---
    print("\n  --- Regime-Conditioned Bootstrap ---")
    rng_regime = np.random.default_rng(SEED + 10000)
    boot_regime: dict[str, list[dict]] = {n: [] for n in STRAT_NAMES_3}
    t0 = time.time()

    for pi in range(N_BOOT):
        if pi % 100 == 0:
            print(f"    Path {pi}/{N_BOOT}  ({time.time() - t0:.0f}s)")

        idx = _gen_regime_path_idx(segments, n_trans, rng_regime)
        c, h, l, v, t = _build_path_5ch(cr, hr, lr, vol_r, tb_r, idx, p0)
        qv = c * v
        feed = _build_synthetic_feed(c, h, l, v, t, qv, base_ts=src_base_ts)

        for name in STRAT_NAMES_3:
            boot_regime[name].append(_safe_run(feed, name))

    elapsed = time.time() - t0
    print(f"    Regime bootstrap done in {elapsed:.0f}s")
    for name in STRAT_NAMES_3:
        s = _boot_summary(boot_regime[name], "sharpe")
        print(f"      {name}: med_Sh={s['median']:.3f}, "
              f"P(Sh>0)={s['p_gt_0']:.1%}")

    results["regime"] = boot_regime

    # --- Part B: Standard VCBB control (blksz=60) ---
    print("\n  --- Standard VCBB Control (blksz=60) ---")
    vcbb = precompute_vcbb(cr, 60, CTX)
    rng_vcbb = np.random.default_rng(SEED + 20000)
    boot_vcbb: dict[str, list[dict]] = {n: [] for n in STRAT_NAMES_3}
    t0 = time.time()

    for pi in range(N_BOOT):
        if pi % 100 == 0:
            print(f"    Path {pi}/{N_BOOT}  ({time.time() - t0:.0f}s)")

        c, h, l, v, t = gen_path_vcbb(
            cr, hr, lr, vol_r, tb_r, n_trans, 60, p0, rng_vcbb,
            vcbb=vcbb, K=K_NN,
        )
        qv = c * v
        feed = _build_synthetic_feed(c, h, l, v, t, qv, base_ts=src_base_ts)

        for name in STRAT_NAMES_3:
            boot_vcbb[name].append(_safe_run(feed, name))

    elapsed = time.time() - t0
    print(f"    VCBB control done in {elapsed:.0f}s")
    for name in STRAT_NAMES_3:
        s = _boot_summary(boot_vcbb[name], "sharpe")
        print(f"      {name}: med_Sh={s['median']:.3f}, "
              f"P(Sh>0)={s['p_gt_0']:.1%}")

    results["vcbb"] = boot_vcbb

    # Save results
    _save_test2(results)
    return results


def _save_test2(results: dict):
    """Save Test 2 results to JSON."""
    out = {}
    for boot_type, boot_data in results.items():
        out[boot_type] = {}
        for name, metrics_list in boot_data.items():
            out[boot_type][name] = {
                "sharpe": _boot_summary(metrics_list, "sharpe"),
                "cagr_pct": _boot_summary(metrics_list, "cagr_pct"),
                "max_dd_pct": _boot_summary(metrics_list, "max_dd_pct"),
            }
    with open(RESULTS / "test2_regime_boot.json", "w") as f:
        json.dump(out, f, indent=2)
    print(f"  Saved: {RESULTS / 'test2_regime_boot.json'}")


# ═══════════════════════════════════════════════════════════════════════
# TEST 3: TIME-STOP / COOLDOWN ABLATION
# ═══════════════════════════════════════════════════════════════════════


def test3_ablation(all_h4: list, all_d1: list, boot_h4: list) -> dict:
    """Test V3's time_stop and cooldown mechanisms on E5.

    Runs full-sample + VCBB bootstrap + regime decomposition for:
    - E5_base (control, identical to E5+EMA21D1)
    - E5+TS30 (E5 + time stop 30 bars)
    - E5+CD6 (E5 + cooldown 6 bars)
    - E5+TS30+CD6 (E5 + both)
    - V3 (reference)
    """
    print("\n" + "=" * 70)
    print("TEST 3: Time-Stop / Cooldown Ablation")
    print(f"  Variants: {ABLATION_NAMES}")
    print(f"  Components: full-sample + {N_BOOT} bootstrap + 4 epochs")
    print("=" * 70)

    results: dict = {"full_sample": {}, "bootstrap": {}, "epochs": {}}

    # --- Part A: Full-sample ---
    print("\n  --- Full-Sample Backtest ---")
    feed_full = make_sub_feed(all_h4, all_d1, START, END)
    for name in ABLATION_NAMES:
        r = _run_one(feed_full, name)
        m = extract_metrics(r)
        results["full_sample"][name] = m
        print(f"    {name}: Sh={m['sharpe']:.3f}, "
              f"CAGR={m['cagr_pct']:.1f}%, MDD={m['max_dd_pct']:.1f}%, "
              f"trades={m['trades']}")

    # --- Part B: Regime decomposition ---
    print("\n  --- Regime Decomposition ---")
    for label, rs, re in EPOCHS:
        feed_ep = make_sub_feed(all_h4, all_d1, rs, re)
        results["epochs"][label] = {}
        for name in ABLATION_NAMES:
            m = _safe_run(feed_ep, name)
            results["epochs"][label][name] = m
        sharpes = {n: results["epochs"][label][n].get("sharpe", 0)
                   for n in ABLATION_NAMES}
        best = max(sharpes, key=lambda k: sharpes[k] or -999)
        print(f"    {label}: best={best} "
              f"({', '.join(f'{n}={sharpes[n]:.2f}' if sharpes[n] else f'{n}=N/A' for n in ABLATION_NAMES)})")

    # --- Part C: VCBB Bootstrap ---
    print("\n  --- VCBB Bootstrap (blksz=60) ---")
    cl, hi, lo, vo, tb = _extract_arrays(boot_h4)
    cr, hr, lr, vol_r, tb_r = make_ratios(cl, hi, lo, vo, tb)
    n_trans = len(cr)
    p0 = cl[0]
    src_base_ts = boot_h4[0].open_time
    vcbb = precompute_vcbb(cr, 60, CTX)
    rng = np.random.default_rng(SEED + 30000)

    boot: dict[str, list[dict]] = {n: [] for n in ABLATION_NAMES}
    t0 = time.time()

    for pi in range(N_BOOT):
        if pi % 100 == 0:
            print(f"    Path {pi}/{N_BOOT}  ({time.time() - t0:.0f}s)")

        c, h, l, v, t = gen_path_vcbb(
            cr, hr, lr, vol_r, tb_r, n_trans, 60, p0, rng,
            vcbb=vcbb, K=K_NN,
        )
        qv = c * v
        feed = _build_synthetic_feed(c, h, l, v, t, qv, base_ts=src_base_ts)

        for name in ABLATION_NAMES:
            boot[name].append(_safe_run(feed, name))

    elapsed = time.time() - t0
    print(f"    Bootstrap done in {elapsed:.0f}s")
    for name in ABLATION_NAMES:
        s = _boot_summary(boot[name], "sharpe")
        print(f"      {name}: med_Sh={s['median']:.3f}, "
              f"P(Sh>0)={s['p_gt_0']:.1%}")

    results["bootstrap"] = boot

    # Save results
    _save_test3(results)
    return results


def _save_test3(results: dict):
    """Save Test 3 results to JSON."""
    out = {
        "full_sample": results["full_sample"],
        "epochs": results["epochs"],
        "bootstrap": {},
    }
    for name, metrics_list in results["bootstrap"].items():
        out["bootstrap"][name] = {
            "sharpe": _boot_summary(metrics_list, "sharpe"),
            "cagr_pct": _boot_summary(metrics_list, "cagr_pct"),
            "max_dd_pct": _boot_summary(metrics_list, "max_dd_pct"),
            "trades": _boot_summary(metrics_list, "trades"),
        }
    with open(RESULTS / "test3_ablation.json", "w") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"  Saved: {RESULTS / 'test3_ablation.json'}")


# ═══════════════════════════════════════════════════════════════════════
# CHARTS
# ═══════════════════════════════════════════════════════════════════════


def chart_test1(results: dict):
    """Test 1: Median bootstrap Sharpe vs block size."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    # Panel 1: Absolute median Sharpe
    for name in STRAT_NAMES_3:
        bsizes = sorted(results.keys())
        meds = []
        for bs in bsizes:
            s = _boot_summary(results[bs][name], "sharpe")
            meds.append(s["median"])
        ax1.plot(bsizes, meds, "o-", label=name, color=COLORS[name], lw=2)

    ax1.set_xlabel("Block Size (H4 bars)")
    ax1.set_ylabel("Median Bootstrap Sharpe")
    ax1.set_title("Test 1: Bootstrap Sharpe vs Block Size")
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    ax1.set_xticks(BLOCK_SIZES)
    ax1.set_xticklabels([f"{bs}\n({bs*4//24}d)" for bs in BLOCK_SIZES])

    # Panel 2: V3/E5 Sharpe ratio
    bsizes = sorted(results.keys())
    ratios = []
    for bs in bsizes:
        v3_med = _boot_summary(results[bs]["V3"], "sharpe")["median"]
        e5_med = _boot_summary(results[bs]["E5+EMA21D1"], "sharpe")["median"]
        ratios.append(v3_med / e5_med if e5_med and e5_med > 0 else 0)

    ax2.plot(bsizes, ratios, "s-", color="#264653", lw=2, ms=8)
    ax2.axhline(y=1.0, color="gray", ls="--", alpha=0.5)
    ax2.set_xlabel("Block Size (H4 bars)")
    ax2.set_ylabel("V3 / E5 Median Sharpe Ratio")
    ax2.set_title("Test 1: V3/E5 Relative Performance vs Block Size")
    ax2.grid(True, alpha=0.3)
    ax2.set_xticks(BLOCK_SIZES)
    ax2.set_xticklabels([f"{bs}\n({bs*4//24}d)" for bs in BLOCK_SIZES])

    # Annotate: ratio > 1 means V3 wins, < 1 means E5 wins
    ax2.fill_between(bsizes, 1.0, [max(r, 1.0) for r in ratios],
                     alpha=0.1, color="#e63946", label="V3 favored")
    ax2.fill_between(bsizes, [min(r, 1.0) for r in ratios], 1.0,
                     alpha=0.1, color="#2a9d8f", label="E5 favored")
    ax2.legend()

    fig.tight_layout()
    fig.savefig(FIGURES / "test1_blocksize.png", dpi=150)
    plt.close(fig)
    print(f"  Chart: {FIGURES / 'test1_blocksize.png'}")


def chart_test2(results: dict):
    """Test 2: VCBB vs Regime-conditioned comparison."""
    fig, ax = plt.subplots(figsize=(10, 6))

    x = np.arange(len(STRAT_NAMES_3))
    w = 0.35

    vcbb_meds = [_boot_summary(results["vcbb"][n], "sharpe")["median"]
                 for n in STRAT_NAMES_3]
    regime_meds = [_boot_summary(results["regime"][n], "sharpe")["median"]
                   for n in STRAT_NAMES_3]

    bars1 = ax.bar(x - w / 2, vcbb_meds, w, label="VCBB (standard)",
                   color="#457b9d", alpha=0.8)
    bars2 = ax.bar(x + w / 2, regime_meds, w, label="Regime-Conditioned",
                   color="#e9c46a", alpha=0.8)

    # Annotate deltas
    for i in range(len(STRAT_NAMES_3)):
        delta = regime_meds[i] - vcbb_meds[i]
        sign = "+" if delta >= 0 else ""
        ax.text(x[i] + w / 2, regime_meds[i] + 0.02,
                f"{sign}{delta:.3f}", ha="center", fontsize=9, fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels(STRAT_NAMES_3)
    ax.set_ylabel("Median Bootstrap Sharpe")
    ax.set_title("Test 2: VCBB vs Regime-Conditioned Bootstrap")
    ax.legend()
    ax.grid(True, alpha=0.3, axis="y")

    fig.tight_layout()
    fig.savefig(FIGURES / "test2_regime_comparison.png", dpi=150)
    plt.close(fig)
    print(f"  Chart: {FIGURES / 'test2_regime_comparison.png'}")


def chart_test3(results: dict):
    """Test 3: Ablation — full-sample vs bootstrap."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    # Panel 1: Full-sample vs Bootstrap Sharpe
    names = ABLATION_NAMES
    full_sh = [results["full_sample"].get(n, {}).get("sharpe", 0)
               for n in names]
    boot_sh = [_boot_summary(results["bootstrap"][n], "sharpe")["median"]
               for n in names]

    x = np.arange(len(names))
    w = 0.35
    ax1.bar(x - w / 2, full_sh, w, label="Full-Sample", color="#264653", alpha=0.8)
    ax1.bar(x + w / 2, boot_sh, w, label="Bootstrap Median", color="#e9c46a", alpha=0.8)
    ax1.set_xticks(x)
    ax1.set_xticklabels(names, rotation=20, ha="right")
    ax1.set_ylabel("Sharpe Ratio")
    ax1.set_title("Test 3: Full-Sample vs Bootstrap Sharpe")
    ax1.legend()
    ax1.grid(True, alpha=0.3, axis="y")

    # Panel 2: Regime decomposition
    epoch_labels = [e[0] for e in EPOCHS]
    x = np.arange(len(epoch_labels))
    w = 0.15
    for i, name in enumerate(names):
        sharpes = [results["epochs"].get(ep, {}).get(name, {}).get("sharpe", 0)
                   or 0 for ep in epoch_labels]
        ax2.bar(x + i * w - (len(names) - 1) * w / 2, sharpes, w,
                label=name, color=COLORS.get(name, f"C{i}"), alpha=0.8)

    ax2.set_xticks(x)
    ax2.set_xticklabels(epoch_labels)
    ax2.set_ylabel("Sharpe Ratio")
    ax2.set_title("Test 3: Ablation Regime Decomposition")
    ax2.legend(fontsize=8)
    ax2.grid(True, alpha=0.3, axis="y")
    ax2.axhline(y=0, color="black", lw=0.5)

    fig.tight_layout()
    fig.savefig(FIGURES / "test3_ablation.png", dpi=150)
    plt.close(fig)
    print(f"  Chart: {FIGURES / 'test3_ablation.png'}")


# ═══════════════════════════════════════════════════════════════════════
# ANALYSIS REPORT
# ═══════════════════════════════════════════════════════════════════════


def write_report(t1: dict, t2: dict, t3: dict):
    """Write comprehensive markdown analysis report."""
    a = []

    a.append("# X36 VCBB Bias Test Battery — Results\n")
    a.append(f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    a.append(f"**Bootstrap paths**: {N_BOOT} per configuration")
    a.append(f"**Cost**: 20 bps RT | **Seed**: {SEED}\n")

    # ── Test 1 ──
    a.append("## Test 1: Block-Size Sensitivity\n")
    a.append("**Question**: Does bootstrap Sharpe change with block size? "
             "If V3 improves disproportionately → VCBB was unfairly penalizing V3.\n")

    a.append("### Median Bootstrap Sharpe by Block Size\n")
    a.append("| Block Size | Days | V3 | V4 | E5+EMA21D1 | V3/E5 Ratio |")
    a.append("|-----------|------|----|----|------------|-------------|")
    for blksz in sorted(t1.keys()):
        days = blksz * 4 // 24
        v3 = _boot_summary(t1[blksz]["V3"], "sharpe")
        v4 = _boot_summary(t1[blksz]["V4"], "sharpe")
        e5 = _boot_summary(t1[blksz]["E5+EMA21D1"], "sharpe")
        ratio = v3["median"] / e5["median"] if e5["median"] and e5["median"] > 0 else 0
        a.append(f"| {blksz} | {days}d | {v3['median']:.3f} | {v4['median']:.3f} "
                 f"| {e5['median']:.3f} | {ratio:.3f} |")

    a.append("\n### P(Sharpe > 0) by Block Size\n")
    a.append("| Block Size | V3 | V4 | E5+EMA21D1 |")
    a.append("|-----------|----|----|------------|")
    for blksz in sorted(t1.keys()):
        v3 = _boot_summary(t1[blksz]["V3"], "sharpe")
        v4 = _boot_summary(t1[blksz]["V4"], "sharpe")
        e5 = _boot_summary(t1[blksz]["E5+EMA21D1"], "sharpe")
        a.append(f"| {blksz} | {v3['p_gt_0']:.1%} | {v4['p_gt_0']:.1%} "
                 f"| {e5['p_gt_0']:.1%} |")

    # Test 1 interpretation
    bsizes = sorted(t1.keys())
    ratios = []
    for bs in bsizes:
        v3m = _boot_summary(t1[bs]["V3"], "sharpe")["median"]
        e5m = _boot_summary(t1[bs]["E5+EMA21D1"], "sharpe")["median"]
        ratios.append(v3m / e5m if e5m and e5m > 0 else 0)

    # Check if ratio increases monotonically with blksz
    increasing = all(ratios[i] <= ratios[i + 1] for i in range(len(ratios) - 1))
    ratio_range = max(ratios) - min(ratios) if ratios else 0

    a.append(f"\n### Test 1 Interpretation\n")
    a.append(f"- V3/E5 ratio range: {min(ratios):.3f} — {max(ratios):.3f} "
             f"(spread: {ratio_range:.3f})")
    a.append(f"- Monotonically increasing: {'YES' if increasing else 'NO'}")

    if ratio_range < 0.05:
        a.append("- **VERDICT**: Ratio is STABLE across block sizes (spread < 0.05). "
                 "Ranking is NOT an artifact of block size. "
                 "VCBB does not unfairly penalize V3.")
    elif increasing and ratio_range >= 0.05:
        a.append("- **VERDICT**: V3 improves disproportionately with larger blocks "
                 f"(spread {ratio_range:.3f}). VCBB regime destruction "
                 "DOES bias against V3. Larger block sizes give fairer comparison.")
    else:
        a.append("- **VERDICT**: Non-monotonic pattern — relationship is complex. "
                 "No clear regime destruction bias.")

    # ── Test 2 ──
    a.append("\n---\n")
    a.append("## Test 2: Regime-Conditioned Bootstrap\n")
    a.append("**Question**: Does sampling from same-regime source data help V3 "
             "disproportionately?\n")
    a.append("*Note: This method samples ratios from same-regime segments of the original data. "
             "The realized regime on synthetic paths (as measured by D1 EMA(21)) may differ "
             "from the source regime due to path-dependent EMA accumulation.*\n")

    a.append("### VCBB vs Regime-Conditioned: Median Sharpe\n")
    a.append("| Strategy | VCBB | Regime-Conditioned | Delta | % Change |")
    a.append("|----------|------|-------------------|-------|----------|")
    for name in STRAT_NAMES_3:
        vcbb_s = _boot_summary(t2["vcbb"][name], "sharpe")
        regime_s = _boot_summary(t2["regime"][name], "sharpe")
        delta = (regime_s["median"] or 0) - (vcbb_s["median"] or 0)
        pct = delta / abs(vcbb_s["median"]) * 100 if vcbb_s["median"] else 0
        a.append(f"| {name} | {vcbb_s['median']:.3f} | {regime_s['median']:.3f} "
                 f"| {delta:+.3f} | {pct:+.1f}% |")

    a.append("\n### P(Sharpe > 0) Comparison\n")
    a.append("| Strategy | VCBB P(Sh>0) | Regime P(Sh>0) |")
    a.append("|----------|-------------|----------------|")
    for name in STRAT_NAMES_3:
        vcbb_s = _boot_summary(t2["vcbb"][name], "sharpe")
        regime_s = _boot_summary(t2["regime"][name], "sharpe")
        a.append(f"| {name} | {vcbb_s['p_gt_0']:.1%} | {regime_s['p_gt_0']:.1%} |")

    # Test 2 interpretation
    v3_vcbb = _boot_summary(t2["vcbb"]["V3"], "sharpe")["median"] or 0
    v3_regime = _boot_summary(t2["regime"]["V3"], "sharpe")["median"] or 0
    e5_vcbb = _boot_summary(t2["vcbb"]["E5+EMA21D1"], "sharpe")["median"] or 0
    e5_regime = _boot_summary(t2["regime"]["E5+EMA21D1"], "sharpe")["median"] or 0

    v3_gain = v3_regime - v3_vcbb
    e5_gain = e5_regime - e5_vcbb
    differential = v3_gain - e5_gain

    a.append(f"\n### Test 2 Interpretation\n")
    a.append(f"- V3 gain from regime-conditioned source: {v3_gain:+.3f}")
    a.append(f"- E5 gain from regime-conditioned source: {e5_gain:+.3f}")
    a.append(f"- Differential (V3 gain - E5 gain): {differential:+.3f}")

    if differential > 0.03:
        a.append(f"- **VERDICT**: V3 gains MORE from regime-conditioned source "
                 f"(differential {differential:+.3f}). "
                 "Confirms that VCBB regime destruction hurts V3 more than E5. "
                 "V3's regime-related alpha is partially real.")
    elif differential < -0.03:
        a.append(f"- **VERDICT**: E5 gains MORE from regime-conditioned source "
                 f"(differential {differential:+.3f}). "
                 "V3's bootstrap weakness is NOT caused by regime destruction.")
    else:
        a.append(f"- **VERDICT**: Both strategies gain similarly "
                 f"(differential {differential:+.3f}). "
                 "Regime-conditioned source does not differentially affect V3 vs E5.")

    # ── Test 3 ──
    a.append("\n---\n")
    a.append("## Test 3: Time-Stop / Cooldown Ablation\n")
    a.append("**Question**: Do V3's time_stop (30 bars) and cooldown (6 bars) "
             "improve or hurt E5's performance?\n")

    a.append("### Full-Sample Results\n")
    a.append("| Variant | Sharpe | CAGR% | MDD% | Trades |")
    a.append("|---------|--------|-------|------|--------|")
    for name in ABLATION_NAMES:
        m = t3["full_sample"].get(name, {})
        a.append(f"| {name} | {m.get('sharpe', 0):.3f} | "
                 f"{m.get('cagr_pct', 0):.1f} | {m.get('max_dd_pct', 0):.1f} | "
                 f"{m.get('trades', 0)} |")

    a.append("\n### Bootstrap Results (blksz=60, 500 paths)\n")
    a.append("| Variant | Med Sharpe | P(Sh>0) | Med CAGR% | Med MDD% |")
    a.append("|---------|-----------|---------|-----------|----------|")
    for name in ABLATION_NAMES:
        s_sh = _boot_summary(t3["bootstrap"][name], "sharpe")
        s_cagr = _boot_summary(t3["bootstrap"][name], "cagr_pct")
        s_mdd = _boot_summary(t3["bootstrap"][name], "max_dd_pct")
        a.append(f"| {name} | {s_sh['median']:.3f} | {s_sh['p_gt_0']:.1%} | "
                 f"{s_cagr['median']:.1f} | {s_mdd['median']:.1f} |")

    a.append("\n### Regime Decomposition (Sharpe)\n")
    epoch_labels = [e[0] for e in EPOCHS]
    header = "| Variant | " + " | ".join(epoch_labels) + " |"
    sep = "|---------|" + "|".join(["-------"] * len(epoch_labels)) + "|"
    a.append(header)
    a.append(sep)
    for name in ABLATION_NAMES:
        vals = []
        for ep in epoch_labels:
            sh = t3["epochs"].get(ep, {}).get(name, {}).get("sharpe")
            vals.append(f"{sh:.2f}" if sh is not None else "N/A")
        a.append(f"| {name} | " + " | ".join(vals) + " |")

    # Test 3 interpretation
    e5_base_boot = _boot_summary(t3["bootstrap"]["E5_base"], "sharpe")["median"] or 0
    e5_ts30_boot = _boot_summary(t3["bootstrap"]["E5+TS30"], "sharpe")["median"] or 0
    e5_cd6_boot = _boot_summary(t3["bootstrap"]["E5+CD6"], "sharpe")["median"] or 0
    e5_both_boot = _boot_summary(t3["bootstrap"]["E5+TS30+CD6"], "sharpe")["median"] or 0
    v3_boot = _boot_summary(t3["bootstrap"]["V3"], "sharpe")["median"] or 0

    a.append(f"\n### Test 3 Interpretation\n")
    a.append(f"- E5_base bootstrap: {e5_base_boot:.3f}")
    a.append(f"- E5+TS30: {e5_ts30_boot:.3f} (delta: {e5_ts30_boot - e5_base_boot:+.3f})")
    a.append(f"- E5+CD6: {e5_cd6_boot:.3f} (delta: {e5_cd6_boot - e5_base_boot:+.3f})")
    a.append(f"- E5+TS30+CD6: {e5_both_boot:.3f} (delta: {e5_both_boot - e5_base_boot:+.3f})")
    a.append(f"- V3 reference: {v3_boot:.3f}")

    if e5_both_boot < e5_base_boot - 0.02:
        a.append("\n- **VERDICT**: Time-stop and/or cooldown HURT E5's bootstrap Sharpe. "
                 "V3's regime stability comes at the COST of robustness. "
                 "These mechanisms are NOT free improvements — they trade "
                 "fat-tail alpha for per-epoch consistency.")
    elif e5_both_boot > e5_base_boot + 0.02:
        a.append("\n- **VERDICT**: Time-stop and/or cooldown IMPROVE E5's bootstrap. "
                 "Consider adopting these mechanisms in E5.")
    else:
        a.append("\n- **VERDICT**: Time-stop and cooldown have NEGLIGIBLE effect on "
                 "E5's bootstrap (delta < 0.02). V3's different bootstrap performance "
                 "must come from other mechanism differences "
                 "(weak VDO, activity/freshness, trail params, no trend exit).")

    # ── Overall Conclusion ──
    a.append("\n---\n")
    a.append("## Overall Conclusion\n")
    a.append("The three tests empirically answer: "
             "\"Does VCBB unfairly penalize V3?\"\n")

    # Summarize all three tests
    a.append("| Test | Question | Answer |")
    a.append("|------|----------|--------|")

    # Test 1 summary
    if ratio_range < 0.05:
        t1_answer = "NO — ranking stable across block sizes"
    elif increasing:
        t1_answer = f"PARTIALLY — V3/E5 ratio increases (spread {ratio_range:.3f})"
    else:
        t1_answer = "UNCLEAR — non-monotonic pattern"
    a.append(f"| Block-size sensitivity | Ranking changes with blksz? | {t1_answer} |")

    # Test 2 summary
    if differential > 0.03:
        t2_answer = f"YES — V3 gains {differential:+.3f} more than E5"
    elif differential < -0.03:
        t2_answer = f"NO — E5 gains more ({differential:+.3f})"
    else:
        t2_answer = f"NO — equal effect ({differential:+.3f})"
    a.append(f"| Regime conditioning | V3 helped more than E5? | {t2_answer} |")

    # Test 3 summary
    ts_delta = e5_both_boot - e5_base_boot
    if ts_delta < -0.02:
        t3_answer = f"HURT bootstrap ({ts_delta:+.3f} Sharpe)"
    elif ts_delta > 0.02:
        t3_answer = f"HELP bootstrap ({ts_delta:+.3f} Sharpe)"
    else:
        t3_answer = f"NEGLIGIBLE ({ts_delta:+.3f} Sharpe)"
    a.append(f"| Time-stop/cooldown ablation | V3's mechanisms help E5? | {t3_answer} |")

    report_text = "\n".join(a)
    with open(RESULTS / "ANALYSIS.md", "w") as f:
        f.write(report_text)
    print(f"\n  Report: {RESULTS / 'ANALYSIS.md'}")
    return report_text


# ═══════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════


def main():
    RESULTS.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("X36 VCBB BIAS TEST BATTERY")
    print("=" * 70)

    # Load data
    print("\nLoading data...")
    all_h4, all_d1 = _fast_load_bars(DATA_PATH)
    print(f"  {len(all_h4)} H4 bars, {len(all_d1)} D1 bars")

    # Filter bars to match full-sample period (with warmup)
    start_ms = _date_ms(START)
    end_ms = _date_ms(END) + 86_400_000 - 1
    load_ms = start_ms - WARMUP * 86_400_000
    boot_h4 = [b for b in all_h4 if load_ms <= b.open_time <= end_ms]
    boot_d1 = [b for b in all_d1 if load_ms <= b.open_time <= end_ms]
    print(f"  Bootstrap source: {len(boot_h4)} H4 bars "
          f"(filtered to {START} with {WARMUP}d warmup)")

    t_start = time.time()

    # Test 1: Block-size sensitivity
    t1_results = test1_blocksize(boot_h4)

    # Test 2: Regime-conditioned bootstrap
    t2_results = test2_regime_bootstrap(boot_h4, boot_d1)

    # Test 3: Ablation (needs both all and filtered bars)
    t3_results = test3_ablation(all_h4, all_d1, boot_h4)

    # Charts
    print("\n" + "=" * 70)
    print("GENERATING CHARTS")
    print("=" * 70)
    chart_test1(t1_results)
    chart_test2(t2_results)
    chart_test3(t3_results)

    # Report
    print("\n" + "=" * 70)
    print("GENERATING REPORT")
    print("=" * 70)
    report = write_report(t1_results, t2_results, t3_results)

    total_time = time.time() - t_start
    print(f"\n{'=' * 70}")
    print(f"DONE — Total time: {total_time:.0f}s ({total_time/60:.1f}min)")
    print(f"{'=' * 70}")

    # Print key findings to stdout
    print("\n" + "=" * 70)
    print("KEY FINDINGS")
    print("=" * 70)
    for line in report.split("\n"):
        if "**VERDICT**" in line:
            print(f"  {line.strip()}")


if __name__ == "__main__":
    main()
