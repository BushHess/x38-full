#!/usr/bin/env python3
"""VTWIN — Twin-Confirmed Trend: Full 4-Phase Validation Pipeline.

4-phase early-stopping test against VTREND:
  Phase 1: Permutation test for twin signal (10,000 perms)
  Phase 2: Timescale robustness (16 timescales x 2000 bootstrap paths)
  Phase 3: Paired bootstrap vs VTREND (2000 paths, head-to-head)
  Phase 4: Multiple comparison correction (Bonferroni/Holm/BH)

Entry: EMA fast > slow AND close > highest_high(N) AND VDO > 0
       (twin confirmation: both EMA trend AND Donchian breakout required)
Exit:  ATR trailing stop OR EMA cross-down (same as VTREND)

Parameters: slow_period = Donchian lookback (coupled), trail_mult
Total: 2 free params (fewer than VTREND's 3)

Cost: harsh (50 bps round-trip)
"""

from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from v10.core.data import DataFeed
from v10.core.types import SCENARIOS
from strategies.vtrend.strategy import _ema, _atr, _vdo

# ── Constants ─────────────────────────────────────────────────────────

DATA   = str(ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv")
COST   = SCENARIOS["harsh"]
CPS    = COST.per_side_bps / 10_000.0   # 0.0025

START  = "2019-01-01"
END    = "2026-02-20"
WARMUP = 365
CASH   = 10_000.0

N_BOOT = 2000
BLKSZ  = 60
SEED   = 42
N_PERM = 10_000

ANN = math.sqrt(6.0 * 365.25)

# Fixed structural constants
ATR_P  = 14
VDO_F  = 12
VDO_S  = 28
TRAIL  = 3.0

# VDO thresholds
VDO_ON  = 0.0     # standard: VDO > 0 required
VDO_OFF = -1e9    # disabled: always passes

# Timescale grid (H4 bars) — same as VTREND/VBREAK
# N controls BOTH slow EMA period AND Donchian lookback (coupled)
N_GRID = [30, 48, 60, 72, 84, 96, 108, 120, 144, 168, 200, 240, 300, 360, 500, 720]

# VTREND defaults for paired comparison
VT_SLOW = 120
VT_FAST = 30


# ═══════════════════════════════════════════════════════════════════════
# Data loading & bootstrap path generation (same as timescale_robustness)
# ═══════════════════════════════════════════════════════════════════════

def load_arrays():
    feed = DataFeed(DATA, start=START, end=END, warmup_days=WARMUP)
    h4 = feed.h4_bars
    n  = len(h4)
    cl = np.array([b.close for b in h4], dtype=np.float64)
    hi = np.array([b.high  for b in h4], dtype=np.float64)
    lo = np.array([b.low   for b in h4], dtype=np.float64)
    vo = np.array([b.volume for b in h4], dtype=np.float64)
    tb = np.array([b.taker_buy_base_vol for b in h4], dtype=np.float64)
    wi = 0
    if feed.report_start_ms is not None:
        for i, b in enumerate(h4):
            if b.close_time >= feed.report_start_ms:
                wi = i
                break
    return cl, hi, lo, vo, tb, wi, n


def make_ratios(cl, hi, lo, vo, tb):
    pc = cl[:-1]
    return cl[1:] / pc, hi[1:] / pc, lo[1:] / pc, vo[1:].copy(), tb[1:].copy()


def gen_path(cr, hr, lr, vol, tb, n_trans, blksz, p0, rng):
    n_blk = math.ceil(n_trans / blksz)
    mx = len(cr) - blksz
    if mx <= 0:
        idx = np.arange(min(n_trans, len(cr)))
    else:
        starts = rng.integers(0, mx + 1, size=n_blk)
        idx = np.concatenate([np.arange(s, s + blksz) for s in starts])[:n_trans]
    c = np.empty(len(idx) + 1, dtype=np.float64)
    c[0] = p0
    c[1:] = p0 * np.cumprod(cr[idx])
    h = np.empty_like(c); l = np.empty_like(c)
    v = np.empty_like(c); t = np.empty_like(c)
    h[0] = p0 * 1.002;  l[0] = p0 * 0.998
    v[0] = vol[idx[0]];  t[0] = tb[idx[0]]
    h[1:] = c[:-1] * hr[idx];  l[1:] = c[:-1] * lr[idx]
    v[1:] = vol[idx];          t[1:] = tb[idx]
    np.maximum(h, c, out=h);   np.minimum(l, c, out=l)
    return c, h, l, v, t


# ═══════════════════════════════════════════════════════════════════════
# Donchian indicator
# ═══════════════════════════════════════════════════════════════════════

def _highest_high(high, n):
    """Rolling max of high[i-n:i]. NaN for i < n. No lookahead."""
    out = np.full(len(high), np.nan)
    if n <= 0 or n >= len(high):
        return out
    windows = sliding_window_view(high, n)
    out[n:] = np.max(windows[:len(high) - n], axis=1)
    return out


# ═══════════════════════════════════════════════════════════════════════
# VTWIN fast simulation (twin entry: EMA AND Donchian, VTREND exit)
# ═══════════════════════════════════════════════════════════════════════

def sim_vtwin(cl, ef, es, hh, at, vd, wi, vdo_thr, trail=TRAIL):
    """VTWIN binary sim (f=1.0). Returns metrics dict."""
    n = len(cl)
    cash = CASH
    bq = 0.0
    inp = False
    pk = 0.0
    pe = px = False
    nt = 0

    navs_start = 0.0
    navs_end = 0.0
    nav_peak = 0.0
    nav_min_ratio = 1.0
    rets_sum = 0.0
    rets_sq_sum = 0.0
    n_rets = 0
    prev_nav = 0.0
    started = False

    for i in range(n):
        p = cl[i]

        # Fill pending
        if i > 0:
            fp = cl[i - 1]
            if pe:
                pe = False
                bq = cash / (fp * (1.0 + CPS))
                cash = 0.0
                inp = True
                pk = p
            elif px:
                cash = bq * fp * (1.0 - CPS)
                bq = 0.0
                inp = False
                pk = 0.0
                nt += 1
                px = False

        nav = cash + bq * p

        if i >= wi:
            if not started:
                navs_start = nav
                prev_nav = nav
                nav_peak = nav
                started = True
            else:
                if prev_nav > 0:
                    r = nav / prev_nav - 1.0
                    rets_sum += r
                    rets_sq_sum += r * r
                    n_rets += 1
                prev_nav = nav
            nav_peak = max(nav_peak, nav)
            if nav_peak > 0:
                ratio = nav / nav_peak
                if ratio < nav_min_ratio:
                    nav_min_ratio = ratio
            navs_end = nav

        # Signal
        a_val = at[i]
        hh_val = hh[i]
        if math.isnan(a_val) or math.isnan(ef[i]) or math.isnan(es[i]) or math.isnan(hh_val):
            continue

        if not inp:
            # ENTRY: EMA crossover AND Donchian breakout AND VDO
            if ef[i] > es[i] and p > hh_val and vd[i] > vdo_thr:
                pe = True
        else:
            pk = max(pk, p)
            # EXIT 1: ATR trailing stop
            if p < pk - trail * a_val:
                px = True
            # EXIT 2: EMA cross-down
            elif ef[i] < es[i]:
                px = True

    # Force close
    if inp and bq > 0:
        cash = bq * cl[-1] * (1.0 - CPS)
        bq = 0.0
        nt += 1
        navs_end = cash

    if n_rets < 2 or navs_start <= 0:
        return {"cagr": -100.0, "mdd": 100.0, "sharpe": 0.0, "calmar": 0.0, "trades": 0}

    tr = navs_end / navs_start - 1.0
    yrs = n_rets / (6.0 * 365.25)
    cagr = ((1 + tr) ** (1 / yrs) - 1) * 100 if yrs > 0 and tr > -1 else -100.0
    mdd = (1.0 - nav_min_ratio) * 100.0
    mu = rets_sum / n_rets
    var = rets_sq_sum / n_rets - mu * mu
    std = math.sqrt(max(var, 0.0))
    sharpe = (mu / std) * ANN if std > 1e-12 else 0.0
    calmar = cagr / mdd if mdd > 0.01 else 0.0

    return {"cagr": cagr, "mdd": mdd, "sharpe": sharpe, "calmar": calmar, "trades": nt}


def sim_vtrend(cl, ef, es, at, vd, wi, vdo_thr, trail=TRAIL):
    """VTREND binary sim (f=1.0). Same incremental pattern."""
    n = len(cl)
    cash = CASH
    bq = 0.0
    inp = False
    pk = 0.0
    pe = px = False
    nt = 0

    navs_start = 0.0
    navs_end = 0.0
    nav_peak = 0.0
    nav_min_ratio = 1.0
    rets_sum = 0.0
    rets_sq_sum = 0.0
    n_rets = 0
    prev_nav = 0.0
    started = False

    for i in range(n):
        p = cl[i]

        if i > 0:
            fp = cl[i - 1]
            if pe:
                pe = False
                bq = cash / (fp * (1.0 + CPS))
                cash = 0.0
                inp = True
                pk = p
            elif px:
                cash = bq * fp * (1.0 - CPS)
                bq = 0.0
                inp = False
                pk = 0.0
                nt += 1
                px = False

        nav = cash + bq * p

        if i >= wi:
            if not started:
                navs_start = nav
                prev_nav = nav
                nav_peak = nav
                started = True
            else:
                if prev_nav > 0:
                    r = nav / prev_nav - 1.0
                    rets_sum += r
                    rets_sq_sum += r * r
                    n_rets += 1
                prev_nav = nav
            nav_peak = max(nav_peak, nav)
            if nav_peak > 0:
                ratio = nav / nav_peak
                if ratio < nav_min_ratio:
                    nav_min_ratio = ratio
            navs_end = nav

        a_val = at[i]
        if math.isnan(a_val) or math.isnan(ef[i]) or math.isnan(es[i]):
            continue

        if not inp:
            if ef[i] > es[i] and vd[i] > vdo_thr:
                pe = True
        else:
            pk = max(pk, p)
            if p < pk - trail * a_val:
                px = True
            elif ef[i] < es[i]:
                px = True

    if inp and bq > 0:
        cash = bq * cl[-1] * (1.0 - CPS)
        bq = 0.0
        nt += 1
        navs_end = cash

    if n_rets < 2 or navs_start <= 0:
        return {"cagr": -100.0, "mdd": 100.0, "sharpe": 0.0, "calmar": 0.0, "trades": 0}

    tr = navs_end / navs_start - 1.0
    yrs = n_rets / (6.0 * 365.25)
    cagr = ((1 + tr) ** (1 / yrs) - 1) * 100 if yrs > 0 and tr > -1 else -100.0
    mdd = (1.0 - nav_min_ratio) * 100.0
    mu = rets_sum / n_rets
    var = rets_sq_sum / n_rets - mu * mu
    std = math.sqrt(max(var, 0.0))
    sharpe = (mu / std) * ANN if std > 1e-12 else 0.0
    calmar = cagr / mdd if mdd > 0.01 else 0.0

    return {"cagr": cagr, "mdd": mdd, "sharpe": sharpe, "calmar": calmar, "trades": nt}


# ═══════════════════════════════════════════════════════════════════════
# Composite score (for permutation test)
# ═══════════════════════════════════════════════════════════════════════

def composite_score(r):
    """Composite objective from metrics dict (same as objective.py)."""
    nt = r["trades"]
    if nt < 10:
        return -1_000_000.0
    cagr = r["cagr"]
    mdd = r["mdd"]
    sh = r["sharpe"]
    pf = max(0, min(sh * 1.5, 3.0))
    return (2.5 * cagr
            - 0.60 * mdd
            + 8.0 * max(0.0, sh)
            + 5.0 * max(0.0, min(pf, 3.0) - 1.0)
            + min(nt / 50.0, 1.0) * 5.0)


def sim_vtwin_navs(cl, ef, es, hh, at, vd, wi, vdo_thr, trail=TRAIL):
    """VTWIN sim returning NAV array + trades (for score computation)."""
    n = len(cl)
    cash = CASH
    bq = 0.0
    inp = False
    pk = 0.0
    pe = px = False
    nt = 0
    navs = []
    trade_returns = []
    entry_nav = 0.0

    for i in range(n):
        p = cl[i]

        if i > 0:
            fp = cl[i - 1]
            if pe:
                pe = False
                bq = cash / (fp * (1.0 + CPS))
                cash = 0.0
                inp = True
                pk = p
                entry_nav = bq * p
            elif px:
                exit_val = bq * fp * (1.0 - CPS)
                if entry_nav > 0:
                    trade_returns.append(exit_val / entry_nav - 1.0)
                cash = exit_val
                bq = 0.0
                inp = False
                pk = 0.0
                nt += 1
                px = False
                entry_nav = 0.0

        nav = cash + bq * p
        if i >= wi:
            navs.append(nav)

        a_val = at[i]
        hh_val = hh[i]
        if math.isnan(a_val) or math.isnan(ef[i]) or math.isnan(es[i]) or math.isnan(hh_val):
            continue

        if not inp:
            if ef[i] > es[i] and p > hh_val and vd[i] > vdo_thr:
                pe = True
        else:
            pk = max(pk, p)
            if p < pk - trail * a_val:
                px = True
            elif ef[i] < es[i]:
                px = True

    if inp and bq > 0:
        exit_val = bq * cl[-1] * (1.0 - CPS)
        if entry_nav > 0:
            trade_returns.append(exit_val / entry_nav - 1.0)
        cash = exit_val
        bq = 0.0
        nt += 1
        if navs:
            navs[-1] = cash

    return _metrics_from_navs(navs, nt, trade_returns)


def _metrics_from_navs(navs, nt, trade_returns):
    """Full metrics dict including profit_factor."""
    if len(navs) < 2 or navs[0] <= 0:
        return {"cagr": -100.0, "mdd": 100.0, "sharpe": 0.0,
                "calmar": 0.0, "trades": 0, "profit_factor": 0.0}
    na = np.array(navs, dtype=np.float64)
    tr = na[-1] / na[0] - 1.0
    yrs = (len(na) - 1) / (6.0 * 365.25)
    cagr = ((1 + tr) ** (1 / yrs) - 1) * 100 if yrs > 0 and tr > -1 else -100.0
    peak = np.maximum.accumulate(na)
    dd = (peak - na) / peak * 100
    mdd = float(dd.max())
    rets = np.diff(na) / na[:-1]
    std = float(np.std(rets, ddof=0))
    sharpe = float(np.mean(rets)) / std * ANN if std > 1e-12 else 0.0
    calmar = cagr / mdd if mdd > 0.01 else 0.0

    wins = [r for r in trade_returns if r > 0]
    losses = [r for r in trade_returns if r <= 0]
    gross_win = sum(wins) if wins else 0.0
    gross_loss = abs(sum(losses)) if losses else 0.0
    pf = gross_win / gross_loss if gross_loss > 1e-12 else 3.0

    return {"cagr": cagr, "mdd": mdd, "sharpe": sharpe, "calmar": calmar,
            "trades": nt, "profit_factor": pf}


def full_score(r):
    """Full composite score (matches objective.py exactly)."""
    nt = r["trades"]
    if nt < 10:
        return -1_000_000.0
    cagr = r["cagr"]
    mdd = r["mdd"]
    sh = r["sharpe"]
    pf = r.get("profit_factor", 0.0)
    if math.isinf(pf):
        pf = 3.0
    return (2.5 * cagr
            - 0.60 * mdd
            + 8.0 * max(0.0, sh)
            + 5.0 * max(0.0, min(pf, 3.0) - 1.0)
            + min(nt / 50.0, 1.0) * 5.0)


# ═══════════════════════════════════════════════════════════════════════
# PHASE 1: Permutation Test
# ═══════════════════════════════════════════════════════════════════════

def run_permutation_twin(cl, hi, lo, vo, tb, wi):
    """Test H0: Donchian confirmation adds nothing to EMA.

    Circular-shift HH array while keeping EMA/ATR/VDO fixed.
    Tests if the timing of the Donchian breakout relative to price matters.
    """
    print("\n" + "=" * 70)
    print("PHASE 1a: PERMUTATION TEST — TWIN SIGNAL (DONCHIAN CONFIRMATION)")
    print("=" * 70)

    N_def = 120
    fast_p = max(5, N_def // 4)

    ef = _ema(cl, fast_p)
    es = _ema(cl, N_def)
    hh = _highest_high(hi, N_def)
    at = _atr(hi, lo, cl, ATR_P)
    vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)

    real_r = sim_vtwin_navs(cl, ef, es, hh, at, vd, wi, VDO_ON)
    real_score = full_score(real_r)
    print(f"  Real score: {real_score:.2f}  "
          f"(CAGR={real_r['cagr']:+.1f}%, Sharpe={real_r['sharpe']:.3f}, "
          f"MDD={real_r['mdd']:.1f}%, trades={real_r['trades']})")

    rng = np.random.default_rng(42)
    n = len(cl)
    null_scores = np.empty(N_PERM)

    t0 = time.time()
    for i in range(N_PERM):
        if (i + 1) % 2000 == 0:
            el = time.time() - t0
            rate = (i + 1) / el
            eta = (N_PERM - i - 1) / rate
            print(f"    {i+1:6d}/{N_PERM}  ({el:.0f}s, ~{eta:.0f}s left)")

        # Shift HH only (EMA stays fixed) — tests Donchian confirmation value
        offset = int(rng.integers(500, n - 500))
        hh_s = np.roll(hh, offset)

        r = sim_vtwin_navs(cl, ef, es, hh_s, at, vd, wi, VDO_ON)
        null_scores[i] = full_score(r)

    el = time.time() - t0
    p = float(np.mean(null_scores >= real_score))

    print(f"\n  Done: {el:.1f}s ({N_PERM / el:.0f} perms/sec)")
    print(f"  Null: mean={null_scores.mean():.2f}, std={null_scores.std():.2f}")
    print(f"  p-value: {p:.6f}")
    print(f"  Gate: {'PASS' if p < 0.001 else 'FAIL'} (threshold: p < 0.001)")

    return p, real_score, float(null_scores.mean()), float(null_scores.std())


def run_permutation_atr(cl, hi, lo, vo, tb, wi):
    """Test H0: ATR trail is random. Block-shuffle ATR array."""
    print("\n" + "=" * 70)
    print("PHASE 1b: PERMUTATION TEST — ATR TRAILING STOP")
    print("=" * 70)

    N_def = 120
    fast_p = max(5, N_def // 4)

    ef = _ema(cl, fast_p)
    es = _ema(cl, N_def)
    hh = _highest_high(hi, N_def)
    at = _atr(hi, lo, cl, ATR_P)
    vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)

    real_r = sim_vtwin_navs(cl, ef, es, hh, at, vd, wi, VDO_ON)
    real_score = full_score(real_r)

    rng = np.random.default_rng(43)
    n = len(at)
    blk = 40
    null_scores = np.empty(N_PERM)

    t0 = time.time()
    for i in range(N_PERM):
        if (i + 1) % 2000 == 0:
            el = time.time() - t0
            rate = (i + 1) / el
            eta = (N_PERM - i - 1) / rate
            print(f"    {i+1:6d}/{N_PERM}  ({el:.0f}s, ~{eta:.0f}s left)")

        # Block-shuffle ATR
        n_blks = math.ceil(n / blk)
        perm = rng.permutation(n_blks)
        idx = np.concatenate([np.arange(b * blk, min((b + 1) * blk, n)) for b in perm])[:n]
        at_s = at[idx]

        r = sim_vtwin_navs(cl, ef, es, hh, at_s, vd, wi, VDO_ON)
        null_scores[i] = full_score(r)

    el = time.time() - t0
    p = float(np.mean(null_scores >= real_score))

    print(f"\n  Done: {el:.1f}s")
    print(f"  p-value: {p:.6f}")
    print(f"  Gate: {'PASS' if p < 0.001 else 'FAIL'}")

    return p, real_score, float(null_scores.mean()), float(null_scores.std())


# ═══════════════════════════════════════════════════════════════════════
# PHASE 2: Timescale Robustness
# ═══════════════════════════════════════════════════════════════════════

def run_real_data(cl, hi, lo, vo, tb, wi):
    """Sweep timescales on real data, with and without VDO."""
    print("\n" + "=" * 70)
    print("PHASE 2a: REAL DATA TIMESCALE SWEEP")
    print("=" * 70)

    at = _atr(hi, lo, cl, ATR_P)
    vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)

    print(f"\n  {'N':>5s}  {'days':>5s}  "
          f"{'CAGR':>7s} {'MDD':>6s} {'Sharpe':>7s} {'Calmar':>7s} {'Tr':>4s}  |  "
          f"{'CAGR':>7s} {'MDD':>6s} {'Sharpe':>7s} {'Calmar':>7s} {'Tr':>4s}")
    print(f"  {'':>5s}  {'':>4s}  {'':>5s}  "
          f"{'--- WITH VDO ---':^34s}  |  {'--- NO VDO ---':^34s}")
    print("  " + "-" * 90)

    results = {}
    for N in N_GRID:
        days = N * 4 / 24
        fast_p = max(5, N // 4)

        ef = _ema(cl, fast_p)
        es = _ema(cl, N)
        hh = _highest_high(hi, N)

        r_on  = sim_vtwin(cl, ef, es, hh, at, vd, wi, VDO_ON)
        r_off = sim_vtwin(cl, ef, es, hh, at, vd, wi, VDO_OFF)

        results[N] = {"with_vdo": r_on, "no_vdo": r_off}

        print(f"  {N:5d}  {days:5.1f}  "
              f"{r_on['cagr']:+6.1f}% {r_on['mdd']:5.1f}% {r_on['sharpe']:7.3f} "
              f"{r_on['calmar']:7.3f} {r_on['trades']:4d}  |  "
              f"{r_off['cagr']:+6.1f}% {r_off['mdd']:5.1f}% {r_off['sharpe']:7.3f} "
              f"{r_off['calmar']:7.3f} {r_off['trades']:4d}")

    return results


def run_bootstrap(cl, hi, lo, vo, tb, wi):
    """2000 bootstrap paths x 16 timescales x 2 VDO variants."""
    print("\n" + "=" * 70)
    print(f"PHASE 2b: BOOTSTRAP {N_BOOT} PATHS x {len(N_GRID)} TIMESCALES x 2 VDO")
    print("=" * 70)

    cr, hr, lr, vol, tbr = make_ratios(cl, hi, lo, vo, tb)
    n_trans = len(cl) - 1
    p0 = cl[0]
    rng = np.random.default_rng(SEED)

    n_sp = len(N_GRID)
    mkeys = ["cagr", "mdd", "sharpe", "calmar", "trades"]

    boot_on  = {m: np.zeros((N_BOOT, n_sp)) for m in mkeys}
    boot_off = {m: np.zeros((N_BOOT, n_sp)) for m in mkeys}

    t0 = time.time()
    for b in range(N_BOOT):
        if (b + 1) % 200 == 0 or b == 0:
            el = time.time() - t0
            rate = (b + 1) / el if el > 0 else 1
            eta = (N_BOOT - b - 1) / rate
            print(f"    {b+1:5d}/{N_BOOT}  ({el:.0f}s, ~{eta:.0f}s left)")

        c, h, l, v, t = gen_path(cr, hr, lr, vol, tbr, n_trans, BLKSZ, p0, rng)
        at = _atr(h, l, c, ATR_P)
        vd = _vdo(c, h, l, v, t, VDO_F, VDO_S)

        for j, N in enumerate(N_GRID):
            fast_p = max(5, N // 4)
            ef = _ema(c, fast_p)
            es = _ema(c, N)
            hh = _highest_high(h, N)

            r_on  = sim_vtwin(c, ef, es, hh, at, vd, wi, VDO_ON)
            r_off = sim_vtwin(c, ef, es, hh, at, vd, wi, VDO_OFF)

            for m in mkeys:
                boot_on[m][b, j]  = r_on[m]
                boot_off[m][b, j] = r_off[m]

    el = time.time() - t0
    n_total = N_BOOT * n_sp * 2
    print(f"\n  Done: {el:.1f}s ({n_total} sims, {n_total / el:.0f} sims/sec)")

    return boot_on, boot_off


def analyze_timescale(boot_on, boot_off, real_results):
    """Analyze timescale robustness."""
    n_sp = len(N_GRID)

    print("\n" + "=" * 70)
    print("VTWIN TIMESCALE ROBUSTNESS (WITH VDO)")
    print("=" * 70)

    print(f"\n  {'N':>5s} {'days':>5s}  "
          f"{'medSh':>6s} {'p5Sh':>6s} {'p95Sh':>6s}  "
          f"{'medCAGR':>8s} {'medMDD':>7s} {'medCalm':>8s}  "
          f"{'P(C>0)':>7s} {'P(S>0)':>7s}")
    print("  " + "-" * 85)

    productive_min = productive_max = None
    strong_min = strong_max = None
    med_sharpes = []

    for j, N in enumerate(N_GRID):
        days = N * 4 / 24
        sh = boot_on["sharpe"][:, j]
        cg = boot_on["cagr"][:, j]

        p5, med, p95 = np.percentile(sh, [5, 50, 95])
        p_cagr = np.mean(cg > 0) * 100
        p_sh   = np.mean(sh > 0) * 100
        med_sharpes.append(float(med))

        marker = ""
        if med > 0:
            if productive_min is None:
                productive_min = N
            productive_max = N
            marker = " *"
        if p_cagr > 70:
            if strong_min is None:
                strong_min = N
            strong_max = N
            marker = " **"

        print(f"  {N:5d} {days:5.1f}  "
              f"{med:+6.3f} {p5:+6.3f} {p95:+6.3f}  "
              f"{np.median(cg):+7.1f}% {np.median(boot_on['mdd'][:, j]):6.1f}% "
              f"{np.median(boot_on['calmar'][:, j]):+7.3f}  "
              f"{p_cagr:6.1f}% {p_sh:6.1f}%{marker}")

    print("\n  Legend: * = productive (median Sharpe > 0), ** = strong (P(CAGR>0) > 70%)")

    # Width
    print("\n  ROBUSTNESS WIDTH:")
    width = None
    if productive_min is not None and productive_max is not None:
        width = productive_max / productive_min
        days_min = productive_min * 4 / 24
        days_max = productive_max * 4 / 24
        print(f"    Productive region: N={productive_min}-{productive_max} "
              f"({days_min:.0f}-{days_max:.0f} days)")
        print(f"    Width ratio: {width:.1f}x")
    else:
        print("    No productive timescale found!")

    if strong_min is not None and strong_max is not None:
        width_s = strong_max / strong_min
        print(f"    Strong region:     N={strong_min}-{strong_max} "
              f"(width {width_s:.1f}x)")

    # Smoothness
    if n_sp > 2:
        adj_corr = float(np.corrcoef(med_sharpes[:-1], med_sharpes[1:])[0, 1])
        print(f"\n  Adjacent Sharpe correlation: r = {adj_corr:.3f}")

    # VDO contribution
    print("\n" + "-" * 70)
    print("VDO CONTRIBUTION (paired: with VDO - no VDO)")
    print("-" * 70)

    vdo_helps = 0
    for j, N in enumerate(N_GRID):
        days = N * 4 / 24
        d_sh = boot_on["sharpe"][:, j] - boot_off["sharpe"][:, j]
        p_helps = np.mean(d_sh > 0)
        if p_helps > 0.5:
            vdo_helps += 1
        print(f"  N={N:5d} ({days:5.1f}d)  "
              f"meanDSh={d_sh.mean():+.4f}  P(VDO+)={p_helps*100:5.1f}%")

    print(f"\n  VDO helps at {vdo_helps}/{n_sp} timescales")

    # Real data percentile
    print("\n" + "-" * 70)
    print("REAL DATA SHARPE PERCENTILE IN BOOTSTRAP")
    print("-" * 70)

    for j, N in enumerate(N_GRID):
        days = N * 4 / 24
        r_on = real_results[N]["with_vdo"]
        pct = np.mean(boot_on["sharpe"][:, j] <= r_on["sharpe"]) * 100
        flag = " !" if pct > 97.5 else " ?" if pct > 95 else ""
        print(f"  N={N:5d}  realSh={r_on['sharpe']:+.3f}  pctile={pct:.1f}%{flag}")

    # Find peak timescale
    peak_j = int(np.argmax(med_sharpes))
    peak_N = N_GRID[peak_j]
    print(f"\n  Peak median Sharpe: {med_sharpes[peak_j]:.4f} at N={peak_N} "
          f"({peak_N * 4 / 24:.0f}d)")

    return productive_min, productive_max, strong_min, strong_max, peak_N, width


# ═══════════════════════════════════════════════════════════════════════
# PHASE 3: Paired Bootstrap vs VTREND
# ═══════════════════════════════════════════════════════════════════════

def run_paired_bootstrap(cl, hi, lo, vo, tb, wi, best_N):
    """2000 paths, VTWIN vs VTREND on same paths."""
    print("\n" + "=" * 70)
    print(f"PHASE 3: PAIRED BOOTSTRAP — VTWIN(N={best_N}) vs VTREND(slow={VT_SLOW})")
    print("=" * 70)

    best_fast = max(5, best_N // 4)

    cr, hr, lr, vol, tbr = make_ratios(cl, hi, lo, vo, tb)
    n_trans = len(cl) - 1
    p0 = cl[0]
    rng = np.random.default_rng(SEED)

    mkeys = ["cagr", "mdd", "sharpe", "calmar", "trades"]
    tw_boot = {m: np.zeros(N_BOOT) for m in mkeys}
    vt_boot = {m: np.zeros(N_BOOT) for m in mkeys}

    t0 = time.time()
    for b in range(N_BOOT):
        if (b + 1) % 200 == 0 or b == 0:
            el = time.time() - t0
            rate = (b + 1) / el if el > 0 else 1
            eta = (N_BOOT - b - 1) / rate
            print(f"    {b+1:5d}/{N_BOOT}  ({el:.0f}s, ~{eta:.0f}s left)")

        c, h, l, v, t = gen_path(cr, hr, lr, vol, tbr, n_trans, BLKSZ, p0, rng)
        at = _atr(h, l, c, ATR_P)
        vd = _vdo(c, h, l, v, t, VDO_F, VDO_S)

        # VTWIN: uses best_N for both EMA and Donchian
        ef_tw = _ema(c, best_fast)
        es_tw = _ema(c, best_N)
        hh_tw = _highest_high(h, best_N)
        rtw = sim_vtwin(c, ef_tw, es_tw, hh_tw, at, vd, wi, VDO_ON)

        # VTREND: uses VT_SLOW for EMA only (no Donchian)
        ef_vt = _ema(c, VT_FAST)
        es_vt = _ema(c, VT_SLOW)
        rvt = sim_vtrend(c, ef_vt, es_vt, at, vd, wi, VDO_ON)

        for m in mkeys:
            tw_boot[m][b] = rtw[m]
            vt_boot[m][b] = rvt[m]

    el = time.time() - t0
    print(f"\n  Done: {el:.1f}s ({N_BOOT / el:.1f} paths/sec)")

    return tw_boot, vt_boot


def analyze_paired(tw_boot, vt_boot):
    """Paired comparison analysis. Returns gate3_passed."""
    print("\n" + "-" * 70)
    print("BOOTSTRAP DISTRIBUTIONS")
    print("-" * 70)

    for lab, store in [("VTWIN", tw_boot), ("VTREND", vt_boot)]:
        print(f"\n  -- {lab} --")
        for m in ["cagr", "mdd", "sharpe", "calmar"]:
            a = store[m]
            p5, p50, p95 = np.percentile(a, [5, 50, 95])
            pgt0 = np.mean(a > 0) * 100 if m != "mdd" else np.nan
            extra = f"  P(>0)={pgt0:.1f}%" if m != "mdd" else ""
            print(f"    {m:7s}  med={p50:+8.3f}  "
                  f"[p5={p5:+7.3f}, p95={p95:+7.3f}]{extra}")

    print("\n" + "-" * 70)
    print("PAIRED COMPARISONS (same 2000 paths)")
    print("-" * 70)
    print("  P(VTWIN better) > 97.5% = significant at a=0.05 (one-sided).\n")

    gate3_passed = False
    paired_results = {}

    for m, direction in [("cagr", "higher"), ("mdd", "lower"),
                          ("sharpe", "higher"), ("calmar", "higher")]:
        if direction == "lower":
            d = vt_boot[m] - tw_boot[m]  # positive = VTWIN has lower MDD
        else:
            d = tw_boot[m] - vt_boot[m]  # positive = VTWIN is higher

        p_better = float(np.mean(d > 0))
        ci = np.percentile(d, [2.5, 97.5])
        sig = " ***" if p_better > 0.975 else " *" if p_better > 0.95 else ""

        print(f"    D{m:7s}  mean={d.mean():+8.4f}  "
              f"P(VTWIN {direction:6s})={p_better * 100:5.1f}%  "
              f"95%CI=[{ci[0]:+.4f}, {ci[1]:+.4f}]{sig}")

        paired_results[m] = {
            "mean_delta": round(float(d.mean()), 6),
            "p_vtwin_better": round(p_better, 4),
            "ci_lo": round(float(ci[0]), 4),
            "ci_hi": round(float(ci[1]), 4),
        }

        if p_better > 0.975:
            gate3_passed = True

    print(f"\n  Gate 3: {'PASS' if gate3_passed else 'FAIL'} "
          f"(need P > 97.5% on at least 1 metric)")

    return gate3_passed, paired_results


# ═══════════════════════════════════════════════════════════════════════
# PHASE 4: Multiple Comparison Correction
# ═══════════════════════════════════════════════════════════════════════

def run_correction(p_twin, p_atr):
    """Apply Bonferroni/Holm/BH correction."""
    print("\n" + "=" * 70)
    print("PHASE 4: MULTIPLE COMPARISON CORRECTION")
    print("=" * 70)

    # All hypotheses tested in this project
    hyps = [
        ("VTREND EMA trend",           0.0003),
        ("VTREND ATR trail",           0.0003),
        ("VTREND VDO filter",          0.0034),
        ("VTREND gate360",             0.507),
        ("VTREND gate500",             0.538),
        ("VTREND gate360x",            0.674),
        ("VTREND regime return_prop",  0.473),
        ("VTREND regime vol",          0.590),
        ("VTREND regime hand_cons",    0.624),
        ("VTREND regime half_kelly",   0.630),
        ("VTREND V8 comparison",       0.5525),
        ("VPULL pullback",             1.000),
        ("VBREAK breakout signal",     0.0026),
        ("VBREAK ATR trail",           0.0472),
        ("VCUSUM cusum signal",        0.0186),
        ("VCUSUM ATR trail",           0.0062),
        # New VTWIN hypotheses
        ("VTWIN twin signal",          p_twin),
        ("VTWIN ATR trail",            p_atr),
    ]

    K = len(hyps)
    alpha = 0.05
    bonf = alpha / K

    sorted_hyps = sorted(hyps, key=lambda x: x[1])

    print(f"\n  Total hypotheses K = {K}")
    print(f"  Bonferroni threshold: a/K = {bonf:.6f}")
    print(f"\n  {'Hypothesis':<35s} {'p-value':>10s} {'Bonf':>6s} {'Holm':>6s} {'BH':>6s}")
    print("  " + "-" * 70)

    twin_survives = {"bonferroni": False, "holm": False, "bh": False}

    for rank, (name, p) in enumerate(sorted_hyps):
        bonf_pass = p <= bonf
        holm_thresh = alpha / (K - rank)
        holm_pass = p <= holm_thresh
        bh_thresh = alpha * (rank + 1) / K
        bh_pass = p <= bh_thresh

        print(f"  {name:<35s} {p:10.6f} {'Y' if bonf_pass else 'N':>6s} "
              f"{'Y' if holm_pass else 'N':>6s} {'Y' if bh_pass else 'N':>6s}")

        if name == "VTWIN twin signal":
            twin_survives["bonferroni"] = bonf_pass
            twin_survives["holm"] = holm_pass
            twin_survives["bh"] = bh_pass

    print(f"\n  VTWIN twin signal survives:")
    print(f"    Bonferroni: {'PASS' if twin_survives['bonferroni'] else 'FAIL'}")
    print(f"    Holm:       {'PASS' if twin_survives['holm'] else 'FAIL'}")
    print(f"    BH (FDR):   {'PASS' if twin_survives['bh'] else 'FAIL'}")

    gate4_passed = twin_survives["bonferroni"]
    print(f"\n  Gate 4: {'PASS' if gate4_passed else 'FAIL'} (Bonferroni)")

    return gate4_passed, twin_survives, K


# ═══════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 70)
    print("VTWIN — TWIN-CONFIRMED TREND: FULL VALIDATION PIPELINE")
    print("=" * 70)
    print(f"  Entry: EMA crossover AND Donchian breakout AND VDO > 0")
    print(f"  Exit:  ATR trailing stop OR EMA cross-down")
    print(f"  Params: 2 (slow_period=Donchian lookback, trail_mult)")
    print(f"  Period: {START} -> {END}   Warmup: {WARMUP}d")
    print(f"  Cost: harsh ({COST.round_trip_bps:.0f} bps RT)")
    print(f"  Bootstrap: {N_BOOT} paths, block={BLKSZ}, seed={SEED}")
    print(f"  Permutation: {N_PERM} shuffles")
    print(f"  Timescales: {len(N_GRID)} ({N_GRID[0]}-{N_GRID[-1]} H4 bars)")
    print(f"  Pipeline: 4 phases with early stopping")

    print("\nLoading data...")
    cl, hi, lo, vo, tb, wi, n = load_arrays()
    print(f"  {n} H4 bars, warmup idx={wi}, trading={n - wi} bars")

    outdir = Path(__file__).resolve().parent / "results"
    outdir.mkdir(exist_ok=True)

    output = {
        "config": {
            "n_boot": N_BOOT, "n_perm": N_PERM,
            "block_size": BLKSZ, "seed": SEED,
            "n_grid": N_GRID,
            "trail": TRAIL, "atr_period": ATR_P,
            "cost_rt_bps": COST.round_trip_bps,
            "start": START, "end": END, "warmup": WARMUP,
        },
        "phase_reached": 0,
        "determination": "PENDING",
        "fail_reason": None,
    }

    # ══════════════════════════════════════════════════════════════════
    # PHASE 1: Permutation Test
    # ══════════════════════════════════════════════════════════════════

    p_twin, real_sc, null_mean, null_std = run_permutation_twin(cl, hi, lo, vo, tb, wi)
    p_atr, _, atr_null_mean, atr_null_std = run_permutation_atr(cl, hi, lo, vo, tb, wi)

    output["phase_1_permutation"] = {
        "twin_signal": {
            "p_value": round(p_twin, 6),
            "real_score": round(real_sc, 4),
            "null_mean": round(null_mean, 4),
            "null_std": round(null_std, 4),
        },
        "atr": {
            "p_value": round(p_atr, 6),
            "null_mean": round(atr_null_mean, 4),
            "null_std": round(atr_null_std, 4),
        },
    }
    output["phase_reached"] = 1

    if p_twin >= 0.001:
        output["determination"] = "FAIL"
        output["fail_reason"] = f"Phase 1: twin signal not significant (p={p_twin:.6f})"
        outpath = outdir / "vtwin_test.json"
        with open(outpath, "w") as f:
            json.dump(output, f, indent=2, default=str)
        print(f"\nEARLY STOP at Phase 1. Results -> {outpath}")
        sys.exit(0)

    # ══════════════════════════════════════════════════════════════════
    # PHASE 2: Timescale Robustness
    # ══════════════════════════════════════════════════════════════════

    real_results = run_real_data(cl, hi, lo, vo, tb, wi)
    boot_on, boot_off = run_bootstrap(cl, hi, lo, vo, tb, wi)
    p_min, p_max, s_min, s_max, peak_N, prod_width = analyze_timescale(
        boot_on, boot_off, real_results
    )

    # Store Phase 2 results
    phase2 = {"real_data": {}, "bootstrap_with_vdo": {}, "bootstrap_no_vdo": {},
              "vdo_contribution": {}, "robustness": {}}

    for j, N in enumerate(N_GRID):
        key = str(N)
        phase2["real_data"][key] = {
            "with_vdo": {k: round(v, 4) for k, v in real_results[N]["with_vdo"].items()},
            "no_vdo": {k: round(v, 4) for k, v in real_results[N]["no_vdo"].items()},
        }
        for label, store, src in [
            ("bootstrap_with_vdo", phase2["bootstrap_with_vdo"], boot_on),
            ("bootstrap_no_vdo", phase2["bootstrap_no_vdo"], boot_off),
        ]:
            store[key] = {}
            for m in ["cagr", "mdd", "sharpe", "calmar"]:
                a = src[m][:, j]
                p5, p50, p95 = np.percentile(a, [5, 50, 95])
                store[key][m] = {
                    "median": round(float(p50), 4),
                    "p5": round(float(p5), 4),
                    "p95": round(float(p95), 4),
                    "p_positive": round(float(np.mean(a > 0)), 4),
                }
        d_sh = boot_on["sharpe"][:, j] - boot_off["sharpe"][:, j]
        phase2["vdo_contribution"][key] = {
            "mean_delta_sharpe": round(float(d_sh.mean()), 6),
            "p_vdo_helps": round(float(np.mean(d_sh > 0)), 4),
        }

    phase2["robustness"] = {
        "productive_min": p_min,
        "productive_max": p_max,
        "productive_width": round(prod_width, 2) if prod_width else None,
        "strong_min": s_min,
        "strong_max": s_max,
        "peak_N": peak_N,
    }

    output["phase_2_timescale"] = phase2
    output["phase_reached"] = 2

    gate2_passed = prod_width is not None and prod_width >= 20.0
    if not gate2_passed:
        w_str = f"{prod_width:.1f}x" if prod_width else "NONE"
        output["determination"] = "FAIL"
        output["fail_reason"] = f"Phase 2: productive width {w_str} < 20x"
        outpath = outdir / "vtwin_test.json"
        with open(outpath, "w") as f:
            json.dump(output, f, indent=2, default=str)
        print(f"\nEARLY STOP at Phase 2. Results -> {outpath}")
        sys.exit(0)

    # ══════════════════════════════════════════════════════════════════
    # PHASE 3: Paired Bootstrap vs VTREND
    # ══════════════════════════════════════════════════════════════════

    tw_boot, vt_boot = run_paired_bootstrap(cl, hi, lo, vo, tb, wi, peak_N)
    gate3_passed, paired_results = analyze_paired(tw_boot, vt_boot)

    phase3 = {"best_N": peak_N}
    for lab, store in [("vtwin", tw_boot), ("vtrend", vt_boot)]:
        phase3[lab] = {}
        for m in ["cagr", "mdd", "sharpe", "calmar"]:
            a = store[m]
            p5, p50, p95 = np.percentile(a, [5, 50, 95])
            phase3[lab][m] = {
                "median": round(float(p50), 4),
                "p5": round(float(p5), 4),
                "p95": round(float(p95), 4),
                "p_positive": round(float(np.mean(a > 0)), 4),
            }
    phase3["paired"] = paired_results

    output["phase_3_paired"] = phase3
    output["phase_reached"] = 3

    if not gate3_passed:
        output["determination"] = "FAIL"
        output["fail_reason"] = "Phase 3: VTWIN not significantly better than VTREND"
        outpath = outdir / "vtwin_test.json"
        with open(outpath, "w") as f:
            json.dump(output, f, indent=2, default=str)
        print(f"\nEARLY STOP at Phase 3. Results -> {outpath}")
        sys.exit(0)

    # ══════════════════════════════════════════════════════════════════
    # PHASE 4: Multiple Comparison Correction
    # ══════════════════════════════════════════════════════════════════

    gate4_passed, survives, K = run_correction(p_twin, p_atr)

    output["phase_4_correction"] = {
        "K": K,
        "alpha": 0.05,
        "bonferroni_threshold": round(0.05 / K, 6),
        "twin_survives_bonferroni": survives["bonferroni"],
        "twin_survives_holm": survives["holm"],
        "twin_survives_bh": survives["bh"],
    }
    output["phase_reached"] = 4

    if gate4_passed:
        output["determination"] = "PASS"
    else:
        output["determination"] = "FAIL"
        output["fail_reason"] = "Phase 4: twin signal does not survive Bonferroni"

    # ══════════════════════════════════════════════════════════════════
    # SAVE & SUMMARY
    # ══════════════════════════════════════════════════════════════════

    outpath = outdir / "vtwin_test.json"
    with open(outpath, "w") as f:
        json.dump(output, f, indent=2, default=str)

    print("\n" + "=" * 70)
    print("FINAL DETERMINATION")
    print("=" * 70)
    print(f"  Phase reached: {output['phase_reached']}")
    print(f"  Result: {output['determination']}")
    if output["fail_reason"]:
        print(f"  Reason: {output['fail_reason']}")
    print(f"\n  Results saved -> {outpath}")
    print("=" * 70)
    print("DONE")
