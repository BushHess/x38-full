#!/usr/bin/env python3
"""Fundamental Algorithm Component Analysis — Mathematical Proof.

Three independent questions, each answered by permutation testing:

A. EMA Timescale: At which period does the EMA trend signal have genuine alpha?
   Method: sweep periods × circular-shift permutation.

B. VDO: Genuine predictive alpha or just a cost-reduction filter?
   Method: VDO vs random filter at calibrated skip rates.

C. Exit Mechanism: Does ATR trailing add alpha over pure EMA exit?
   Method: compare exit variants + ATR shuffle permutation.

All tests use harsh cost (50 bps RT).
Each conclusion stands alone with a p-value.
"""

from __future__ import annotations

import math
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from v10.core.data import DataFeed
from v10.core.engine import BacktestEngine
from v10.core.types import SCENARIOS
from v10.research.objective import compute_objective
from strategies.vtrend.strategy import (
    VTrendConfig, VTrendStrategy, Signal, _ema, _atr, _vdo,
)

DATA = str(ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv")
COST = SCENARIOS["harsh"]
WARMUP = 365
CASH = 10_000.0
START = "2019-01-01"
END = "2026-02-20"
N_PERM = 200


# ── Shared helpers ───────────────────────────────────────────────────────

def _feed():
    return DataFeed(DATA, start=START, end=END, warmup_days=WARMUP)


def _run(feed, strategy) -> tuple[float, dict]:
    engine = BacktestEngine(
        feed=feed, strategy=strategy, cost=COST,
        initial_cash=CASH, warmup_mode="no_trade",
    )
    r = engine.run()
    return compute_objective(r.summary), r.summary


def _block_shuffle(arr, block_size, rng):
    n = len(arr)
    nb = n // block_size
    if nb <= 1:
        return arr.copy()
    idx = np.arange(nb)
    rng.shuffle(idx)
    parts = [arr[i * block_size:(i + 1) * block_size] for i in idx]
    tail = arr[nb * block_size:]
    if len(tail):
        parts.append(tail)
    return np.concatenate(parts)


def _m(s, k):
    """Extract metric from summary, default 0."""
    v = s.get(k, 0)
    return v if v is not None else 0


# ═════════════════════════════════════════════════════════════════════════
# Part A — EMA Timescale Analysis
# ═════════════════════════════════════════════════════════════════════════

class _CircularShiftEMA(VTrendStrategy):
    """EMA arrays shifted by random offset — breaks price alignment,
    preserves all temporal structure (smoothness, transition count)."""

    def __init__(self, config, offset):
        super().__init__(config)
        self._offset = offset

    def on_init(self, h4, d1):
        super().on_init(h4, d1)
        self._ema_fast = np.roll(self._ema_fast, self._offset)
        self._ema_slow = np.roll(self._ema_slow, self._offset)


def part_a(feed):
    print("=" * 72)
    print("PART A: EMA TIMESCALE ANALYSIS")
    print("  VDO disabled (isolate EMA). Circular-shift permutation per period.")
    print("=" * 72)

    # H4 bars equivalent: period × 4h. E.g., 120 H4 = 20 days, 1200 H4 = 200 days.
    periods = [30, 48, 72, 96, 120, 180, 240, 360, 500, 720, 1000, 1200]
    n_bars = feed.n_h4

    # A1: Period sweep
    print(f"\nA1. Period sweep (VDO disabled, {len(periods)} periods)")
    hdr = (f"{'Period':>7} {'~Days':>6} {'Score':>8} {'CAGR%':>7} {'MDD%':>6} "
           f"{'Calmar':>7} {'Sharpe':>7} {'Trades':>7}")
    print(hdr)
    print("-" * len(hdr))

    sweep = []
    for p in periods:
        cfg = VTrendConfig(slow_period=float(p), vdo_threshold=-999.0)
        sc, s = _run(feed, VTrendStrategy(cfg))
        days_eq = p * 4 / 24
        row = dict(
            period=p, days=round(days_eq), score=sc,
            cagr=_m(s, "cagr_pct"), mdd=_m(s, "max_drawdown_mid_pct"),
            calmar=_m(s, "calmar"), sharpe=_m(s, "sharpe"),
            trades=_m(s, "trades"),
        )
        sweep.append(row)
        print(f"{p:>7} {days_eq:>5.0f}d {sc:>8.1f} {row['cagr']:>6.1f}% "
              f"{row['mdd']:>5.1f}% {row['calmar']:>7.2f} "
              f"{row['sharpe']:>7.2f} {row['trades']:>7}")

    # A2: Circular-shift permutation test for each period
    print(f"\nA2. Circular-shift permutation test ({N_PERM} shifts per period)")
    print(f"  Null: same EMA shape, random timing. Offset range [500, {n_bars-500}]")
    hdr2 = f"{'Period':>7} {'~Days':>6} {'Real':>8} {'Null mean':>10} {'Null std':>9} {'p-value':>8} {'Sig':>12}"
    print(hdr2)
    print("-" * len(hdr2))

    offsets = np.random.RandomState(42).randint(500, max(501, n_bars - 500), size=N_PERM)

    perm_results = []
    for row in sweep:
        p = row["period"]
        real_sc = row["score"]
        cfg = VTrendConfig(slow_period=float(p), vdo_threshold=-999.0)
        null_scores = []
        for off in offsets:
            sc, _ = _run(feed, _CircularShiftEMA(cfg, int(off)))
            null_scores.append(sc)
        null_arr = np.array(null_scores)
        pval = float(np.mean(null_arr >= real_sc))
        sig = "***" if pval < 0.01 else "**" if pval < 0.05 else "*" if pval < 0.10 else ""
        print(f"{p:>7} {row['days']:>5}d {real_sc:>8.1f} {np.mean(null_arr):>10.1f} "
              f"{np.std(null_arr):>9.1f} {pval:>8.4f} {sig:>12}")
        perm_results.append(dict(period=p, days=row["days"], real=real_sc,
                                  null_mean=float(np.mean(null_arr)),
                                  null_std=float(np.std(null_arr)),
                                  pval=pval))

    # A3: Interpretation
    sig_periods = [r for r in perm_results if r["pval"] < 0.05]
    best = max(sweep, key=lambda r: r["calmar"] if r["calmar"] else 0)
    print(f"\nA3. Findings:")
    print(f"  Significant periods (p<0.05): "
          f"{[r['period'] for r in sig_periods] if sig_periods else 'NONE'}")
    print(f"  Best Calmar: period={best['period']} (~{best['days']}d) "
          f"Calmar={best['calmar']:.2f}")
    if sig_periods:
        best_sig = min(sig_periods, key=lambda r: r["pval"])
        print(f"  Most significant: period={best_sig['period']} "
              f"(~{best_sig['days']}d) p={best_sig['pval']:.4f}")

    return sweep, perm_results


# ═════════════════════════════════════════════════════════════════════════
# Part B — VDO Alpha Test
# ═════════════════════════════════════════════════════════════════════════

class _RandomFilter(VTrendStrategy):
    """EMA crossover entry with random skip (VDO disabled).
    Skip probability calibrated to match VDO's trade reduction."""

    def __init__(self, config, skip_rate, seed):
        cfg_copy = VTrendConfig(
            slow_period=config.slow_period,
            trail_mult=config.trail_mult,
            vdo_threshold=-999.0,  # VDO disabled
        )
        super().__init__(cfg_copy)
        self._skip = skip_rate
        self._seed = seed
        self._rng = None

    def on_init(self, h4, d1):
        super().on_init(h4, d1)
        self._rng = np.random.RandomState(self._seed)

    def on_bar(self, state):
        i = state.bar_index
        if self._ema_fast is None or self._atr is None or i < 1:
            return None
        ef, es = self._ema_fast[i], self._ema_slow[i]
        atr_v = self._atr[i]
        price = state.bar.close
        if math.isnan(atr_v) or math.isnan(ef) or math.isnan(es):
            return None
        if not self._in_position:
            if ef > es:
                if self._rng.random() < self._skip:
                    return None  # randomly skip this entry
                self._in_position = True
                self._peak_price = price
                return Signal(target_exposure=1.0, reason="entry")
        else:
            self._peak_price = max(self._peak_price, price)
            if price < self._peak_price - self._c.trail_mult * atr_v:
                self._in_position = False
                self._peak_price = 0.0
                return Signal(target_exposure=0.0, reason="trail_stop")
            if ef < es:
                self._in_position = False
                self._peak_price = 0.0
                return Signal(target_exposure=0.0, reason="ema_exit")
        return None


def part_b(feed):
    print("\n\n" + "=" * 72)
    print("PART B: VDO ALPHA TEST")
    print("  Is VDO a genuine predictive signal or just a cost filter?")
    print("=" * 72)

    cfg = VTrendConfig()

    # B1: Baselines
    print("\nB1. Baselines")
    sc_vdo, s_vdo = _run(feed, VTrendStrategy(cfg))
    sc_ema, s_ema = _run(feed, VTrendStrategy(VTrendConfig(vdo_threshold=-999.0)))
    tr_vdo, tr_ema = s_vdo["trades"], s_ema["trades"]
    skip_rate = 1.0 - tr_vdo / tr_ema if tr_ema > 0 else 0.0

    print(f"  VDO enabled:   score={sc_vdo:.1f}  CAGR={_m(s_vdo,'cagr_pct'):.1f}%  "
          f"MDD={_m(s_vdo,'max_drawdown_mid_pct'):.1f}%  trades={tr_vdo}")
    print(f"  VDO disabled:  score={sc_ema:.1f}  CAGR={_m(s_ema,'cagr_pct'):.1f}%  "
          f"MDD={_m(s_ema,'max_drawdown_mid_pct'):.1f}%  trades={tr_ema}")
    print(f"  VDO blocks {tr_ema - tr_vdo} entries ({100*skip_rate:.1f}% skip rate)")

    # B2: Random filter curve — score vs skip rate
    skip_rates = [0.0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50]
    n_seeds = 50
    print(f"\nB2. Random filter curve ({n_seeds} seeds per rate)")
    print(f"{'Skip%':>6} {'Mean sc':>8} {'Std sc':>7} {'Mean tr':>8} {'VDO ref':>8}")
    print("-" * 45)

    curve = []
    for sr in skip_rates:
        scores, trades = [], []
        for seed in range(n_seeds):
            sc, s = _run(feed, _RandomFilter(cfg, sr, seed))
            scores.append(sc)
            trades.append(s["trades"])
        m_sc, s_sc = np.mean(scores), np.std(scores)
        m_tr = np.mean(trades)
        marker = " ← VDO skip rate" if abs(sr - skip_rate) < 0.03 else ""
        print(f"{100*sr:>5.0f}% {m_sc:>8.1f} {s_sc:>7.1f} {m_tr:>8.1f}{marker}")
        curve.append(dict(skip=sr, mean_sc=m_sc, std_sc=s_sc, mean_tr=m_tr))

    # B3: Compare VDO to random filter at matched skip rate
    print(f"\nB3. VDO vs random filter at matched skip rate ({100*skip_rate:.1f}%)")
    matched = []
    for seed in range(N_PERM):
        sc, s = _run(feed, _RandomFilter(cfg, skip_rate, seed))
        matched.append(sc)
    matched_arr = np.array(matched)
    p_vdo = float(np.mean(matched_arr >= sc_vdo))

    print(f"  VDO score:         {sc_vdo:.1f}")
    print(f"  Random mean:       {np.mean(matched_arr):.1f} ± {np.std(matched_arr):.1f}")
    print(f"  Random [5%, 95%]:  [{np.percentile(matched_arr,5):.1f}, "
          f"{np.percentile(matched_arr,95):.1f}]")
    print(f"  p-value:           {p_vdo:.4f}")

    if p_vdo < 0.05:
        print("  → VDO is SIGNIFICANTLY better than random filter (p<0.05)")
        print("  → VDO identifies genuinely BAD entry times, not just reducing costs")
    elif p_vdo < 0.10:
        print("  → VDO is MARGINALLY better than random (p<0.10)")
    else:
        print("  → VDO is NOT better than random filter")
        print("  → VDO's benefit comes purely from reducing trade frequency (cost savings)")

    return dict(sc_vdo=sc_vdo, sc_ema=sc_ema, tr_vdo=tr_vdo, tr_ema=tr_ema,
                skip_rate=skip_rate, p_vdo=p_vdo,
                matched_mean=float(np.mean(matched_arr)))


# ═════════════════════════════════════════════════════════════════════════
# Part C — Exit Mechanism Analysis
# ═════════════════════════════════════════════════════════════════════════

class _TrailOnly(VTrendStrategy):
    """Exit: trail stop ONLY (no EMA cross exit)."""
    def on_bar(self, state):
        i = state.bar_index
        if self._ema_fast is None or self._atr is None or self._vdo is None or i < 1:
            return None
        ef, es = self._ema_fast[i], self._ema_slow[i]
        atr_v, vdo_v = self._atr[i], self._vdo[i]
        price = state.bar.close
        if math.isnan(atr_v) or math.isnan(ef) or math.isnan(es):
            return None
        if not self._in_position:
            if ef > es and vdo_v > self._c.vdo_threshold:
                self._in_position = True
                self._peak_price = price
                return Signal(target_exposure=1.0, reason="entry")
        else:
            self._peak_price = max(self._peak_price, price)
            if price < self._peak_price - self._c.trail_mult * atr_v:
                self._in_position = False
                self._peak_price = 0.0
                return Signal(target_exposure=0.0, reason="trail_stop")
        return None


class _EMAOnly(VTrendStrategy):
    """Exit: EMA cross-down ONLY (no trail stop)."""
    def on_bar(self, state):
        i = state.bar_index
        if self._ema_fast is None or self._vdo is None or i < 1:
            return None
        ef, es = self._ema_fast[i], self._ema_slow[i]
        vdo_v = self._vdo[i]
        if math.isnan(ef) or math.isnan(es):
            return None
        if not self._in_position:
            if ef > es and vdo_v > self._c.vdo_threshold:
                self._in_position = True
                return Signal(target_exposure=1.0, reason="entry")
        else:
            if ef < es:
                self._in_position = False
                return Signal(target_exposure=0.0, reason="ema_exit")
        return None


class _TimeExit(VTrendStrategy):
    """Exit: fixed holding period (N H4 bars)."""
    def __init__(self, config, hold_bars):
        super().__init__(config)
        self._hold = hold_bars
        self._bars_in = 0

    def on_bar(self, state):
        i = state.bar_index
        if self._ema_fast is None or self._vdo is None or i < 1:
            return None
        ef, es = self._ema_fast[i], self._ema_slow[i]
        vdo_v = self._vdo[i]
        if math.isnan(ef) or math.isnan(es):
            return None
        if not self._in_position:
            if ef > es and vdo_v > self._c.vdo_threshold:
                self._in_position = True
                self._bars_in = 0
                return Signal(target_exposure=1.0, reason="entry")
        else:
            self._bars_in += 1
            if self._bars_in >= self._hold:
                self._in_position = False
                self._bars_in = 0
                return Signal(target_exposure=0.0, reason="time_exit")
        return None


class _ShuffledATR(VTrendStrategy):
    """Trail stop with block-shuffled ATR — tests if ATR scaling matters."""
    def __init__(self, config, block, seed):
        super().__init__(config)
        self._blk = block
        self._seed = seed

    def on_init(self, h4, d1):
        super().on_init(h4, d1)
        if self._atr is not None:
            self._atr = _block_shuffle(
                self._atr, self._blk, np.random.RandomState(self._seed))


def part_c(feed):
    print("\n\n" + "=" * 72)
    print("PART C: EXIT MECHANISM ANALYSIS")
    print("  Same entry (EMA cross + VDO). Compare exit methods.")
    print("=" * 72)

    cfg = VTrendConfig()

    # C1: Exit variant comparison
    print("\nC1. Exit variant comparison")
    variants = [
        ("Trail+EMA (default)", VTrendStrategy(cfg)),
        ("Trail only",          _TrailOnly(cfg)),
        ("EMA only",            _EMAOnly(cfg)),
    ]
    # Time-based exits at different holding periods
    hold_bars = [12, 24, 36, 48, 72, 96, 120, 180]
    for hb in hold_bars:
        days = hb * 4 / 24
        variants.append((f"Time exit {hb}b (~{days:.0f}d)", _TimeExit(cfg, hb)))

    hdr = f"{'Exit method':>25} {'Score':>8} {'CAGR%':>7} {'MDD%':>6} {'Calmar':>7} {'Sharpe':>7} {'Trades':>7}"
    print(hdr)
    print("-" * len(hdr))

    variant_rows = []
    for name, strat in variants:
        sc, s = _run(feed, strat)
        r = dict(name=name, score=sc, cagr=_m(s, "cagr_pct"),
                 mdd=_m(s, "max_drawdown_mid_pct"),
                 calmar=_m(s, "calmar"), sharpe=_m(s, "sharpe"),
                 trades=_m(s, "trades"))
        variant_rows.append(r)
        print(f"{name:>25} {sc:>8.1f} {r['cagr']:>6.1f}% {r['mdd']:>5.1f}% "
              f"{r['calmar']:>7.2f} {r['sharpe']:>7.2f} {r['trades']:>7}")

    # C2: ATR shuffle permutation test
    # Tests: does the SPECIFIC ATR-based stop distance matter?
    print(f"\nC2. ATR shuffle permutation test ({N_PERM} permutations)")
    real_row = variant_rows[0]  # Trail+EMA default
    real_sc = real_row["score"]

    atr_null = []
    t0 = time.time()
    for i in range(N_PERM):
        sc, _ = _run(feed, _ShuffledATR(cfg, block=40, seed=i))
        atr_null.append(sc)
        if (i + 1) % 50 == 0:
            print(f"  {i+1}/{N_PERM} ({time.time()-t0:.0f}s)")
    atr_arr = np.array(atr_null)
    p_atr = float(np.mean(atr_arr >= real_sc))

    print(f"\n  Real (ATR-scaled trail):  score={real_sc:.1f}")
    print(f"  Shuffled ATR mean:       {np.mean(atr_arr):.1f} ± {np.std(atr_arr):.1f}")
    print(f"  p-value:                 {p_atr:.4f}")
    if p_atr < 0.05:
        print("  → ATR scaling is SIGNIFICANT — volatility-adaptive stops add alpha")
    else:
        print("  → ATR scaling is NOT significant — a fixed-distance stop works equally well")

    # C3: Trail vs no-trail (is trailing itself valuable?)
    trail_sc = variant_rows[1]["score"]  # Trail only
    ema_sc = variant_rows[2]["score"]  # EMA only
    delta = trail_sc - ema_sc
    print(f"\nC3. Trail stop value")
    print(f"  Trail only:  score={trail_sc:.1f}")
    print(f"  EMA only:    score={ema_sc:.1f}")
    print(f"  Delta:       {delta:+.1f}")
    if delta > 10:
        print("  → Trail stop adds meaningful value over pure EMA exit")
    elif delta > 0:
        print("  → Trail stop adds marginal value")
    else:
        print("  → Trail stop does NOT add value — EMA exit is sufficient")

    best_time = max(variant_rows[3:], key=lambda r: r["calmar"] if r["calmar"] else 0)
    print(f"\nC4. Best time-based exit: {best_time['name']} "
          f"(Calmar={best_time['calmar']:.2f})")
    print(f"  Compare: Trail+EMA Calmar={variant_rows[0]['calmar']:.2f}")

    return variant_rows, p_atr


# ═════════════════════════════════════════════════════════════════════════
# MAIN
# ═════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    t_all = time.time()
    feed = _feed()
    print(f"Data loaded: {feed.n_h4} H4 bars, {feed.n_d1} D1 bars\n")

    a_sweep, a_perm = part_a(feed)
    b_result = part_b(feed)
    c_variants, c_p_atr = part_c(feed)

    # ── Final Summary ──
    print("\n\n" + "=" * 72)
    print("FINAL SUMMARY — What is proven, what is not")
    print("=" * 72)

    sig_a = [r for r in a_perm if r["pval"] < 0.05]
    best_calmar = max(a_sweep, key=lambda r: r["calmar"] if r["calmar"] else 0)

    print(f"\nA. EMA TREND SIGNAL")
    if sig_a:
        periods_str = ", ".join(f"{r['period']}({r['days']}d)" for r in sig_a)
        print(f"   PROVEN: significant at periods: {periods_str}")
        print(f"   Best Calmar: period={best_calmar['period']} "
              f"(~{best_calmar['days']}d)")
    else:
        print("   NOT PROVEN at any individual period tested")

    print(f"\nB. VDO SIGNAL")
    print(f"   p-value vs random filter: {b_result['p_vdo']:.4f}")
    if b_result["p_vdo"] < 0.05:
        print("   PROVEN: VDO has genuine predictive alpha beyond cost reduction")
    elif b_result["p_vdo"] < 0.10:
        print("   MARGINAL: some evidence but not conclusive (p<0.10)")
    else:
        print("   NOT PROVEN: VDO is equivalent to random filtering")

    print(f"\nC. EXIT MECHANISM")
    print(f"   ATR trail scaling p-value: {c_p_atr:.4f}")
    trail_row = next(r for r in c_variants if r["name"] == "Trail only")
    ema_row = next(r for r in c_variants if r["name"] == "EMA only")
    print(f"   Trail only: Calmar={trail_row['calmar']:.2f}")
    print(f"   EMA only:   Calmar={ema_row['calmar']:.2f}")

    total = time.time() - t_all
    print(f"\n\nTotal runtime: {total:.0f}s ({total/60:.1f} min)")
