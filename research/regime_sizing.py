#!/usr/bin/env python3
"""Hướng B: Regime-Dependent Position Sizing.

Part B1: Per-Regime Trade Analysis (real data)
  Extract per-trade returns classified by D1 regime at entry.
  Compute per-regime: n_trades, win_rate, avg_return, Kelly f*.

Part B2: Regime Sizing Functions (real data sweep)
  5 regime-dependent approaches + 4 uniform baselines:
    1. hand_cons   — hand-designed conservative fractions
    2. hand_aggr   — hand-designed aggressive fractions
    3. half_kelly  — per-regime half-Kelly fraction
    4. binary_bull — BULL=0.40, all else=0.15
    5. return_prop — fraction proportional to per-regime avg return
    + regime_vol  — regime-conditional vol targets
  Baselines: f=0.20, f=0.30, f=1.00, vol=15%

Part B3: Bootstrap (2000 paths)
  H4→D1 aggregation, regime classification on synthetic paths.
  Paired test: does regime sizing significantly beat best uniform?
  Key question: P(ΔCalmar > 0) > 97.5% ?

All tests: harsh cost (50 bps RT).
"""

from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from v10.core.data import DataFeed
from v10.core.types import SCENARIOS
from strategies.vtrend.strategy import _ema, _atr, _vdo

# Regime D1 indicator helpers (EMA, ATR, ADX on D1 bars)
from v10.research.regime import (
    _ema as r_ema,
    _atr as r_atr,
    _adx as r_adx,
)

# ── Constants ─────────────────────────────────────────────────────────────

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

SLOW  = 120
FAST  = max(5, SLOW // 4)   # 30
TRAIL = 3.0
VDO_T = 0.0
ATR_P = 14
VDO_F = 12
VDO_S = 28

VOL_WIN = 60
ANN = math.sqrt(6.0 * 365.25)

# Regime integer codes
R_SHOCK   = 0
R_BEAR    = 1
R_CHOP    = 2
R_TOPPING = 3
R_BULL    = 4
R_NEUTRAL = 5

ALL_REGIMES = [R_SHOCK, R_BEAR, R_CHOP, R_TOPPING, R_BULL, R_NEUTRAL]
REGIME_NAMES = {
    R_SHOCK: "SHOCK", R_BEAR: "BEAR", R_CHOP: "CHOP",
    R_TOPPING: "TOPPING", R_BULL: "BULL", R_NEUTRAL: "NEUTRAL",
}

H4_PER_DAY = 6


# ═══════════════════════════════════════════════════════════════════════════
# Data Loading & Path Generation (reused from position_sizing.py)
# ═══════════════════════════════════════════════════════════════════════════

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
    h[1:] = c[:-1] * hr[idx]; l[1:] = c[:-1] * lr[idx]
    v[1:] = vol[idx];         t[1:] = tb[idx]
    np.maximum(h, c, out=h);  np.minimum(l, c, out=l)
    return c, h, l, v, t


def compute_ind(cl, hi, lo, vo, tb):
    """Compute VTREND indicators (H4)."""
    return (
        _ema(cl, FAST),
        _ema(cl, SLOW),
        _atr(hi, lo, cl, ATR_P),
        _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S),
    )


def compute_rolling_vol(cl, window=VOL_WIN):
    """Annualized rolling vol from H4 log returns (vectorized)."""
    n = len(cl)
    lr = np.diff(np.log(cl))
    cum   = np.cumsum(np.concatenate([[0.0], lr]))
    cumsq = np.cumsum(np.concatenate([[0.0], lr ** 2]))
    vol = np.full(n, np.nan)
    if n <= window:
        return vol
    idx = np.arange(window, n)
    s  = cum[idx]   - cum[idx - window]
    sq = cumsq[idx] - cumsq[idx - window]
    var = sq / window - (s / window) ** 2
    np.maximum(var, 0, out=var)
    vol[window:] = np.sqrt(var) * ANN
    return vol


# ═══════════════════════════════════════════════════════════════════════════
# D1 Regime Classification from Raw Arrays
# ═══════════════════════════════════════════════════════════════════════════

def aggregate_h4_to_d1(cl, hi, lo):
    """Aggregate H4 arrays → synthetic D1 arrays (every 6 bars).

    Vectorized: reshape + column ops.
    For bootstrap paths, the 6-bar groups are synthetic "days" — the regime
    classifier responds to price dynamics regardless of calendar time.
    """
    n = len(cl)
    n_d1 = n // H4_PER_DAY
    if n_d1 == 0:
        return np.empty(0), np.empty(0), np.empty(0)
    t = n_d1 * H4_PER_DAY
    cl_r = cl[:t].reshape(n_d1, H4_PER_DAY)
    hi_r = hi[:t].reshape(n_d1, H4_PER_DAY)
    lo_r = lo[:t].reshape(n_d1, H4_PER_DAY)
    return cl_r[:, -1].copy(), hi_r.max(axis=1), lo_r.min(axis=1)


def classify_d1_from_arrays(
    closes, highs, lows,
    ema_fast_p=50, ema_slow_p=200, adx_period=14,
    shock_thr=8.0, chop_atr_pct=3.5, chop_adx=20.0,
    top_dist=1.0, top_adx=25.0,
):
    """Classify D1 regimes from raw arrays.

    Exact same logic as v10.research.regime.classify_d1_regimes,
    but works on numpy arrays directly instead of Bar objects.

    Returns int32 array with regime codes (R_SHOCK..R_NEUTRAL).
    """
    n = len(closes)
    if n == 0:
        return np.array([], dtype=np.int32)

    ema_f = r_ema(closes, ema_fast_p)
    ema_s = r_ema(closes, ema_slow_p)
    atr_arr = r_atr(highs, lows, closes, 14)
    adx_arr = r_adx(highs, lows, closes, adx_period)

    regimes = np.full(n, R_NEUTRAL, dtype=np.int32)
    for i in range(n):
        c = closes[i]
        # SHOCK
        if i > 0:
            daily_ret = abs((c / closes[i - 1] - 1.0) * 100.0)
        else:
            daily_ret = 0.0
        if daily_ret > shock_thr:
            regimes[i] = R_SHOCK
            continue
        # BEAR
        if c < ema_s[i] and ema_f[i] < ema_s[i]:
            regimes[i] = R_BEAR
            continue
        # CHOP
        atr_pct = atr_arr[i] / c * 100.0 if c > 1e-12 else 0.0
        if atr_pct > chop_atr_pct and adx_arr[i] < chop_adx:
            regimes[i] = R_CHOP
            continue
        # TOPPING
        dist_pct = abs(c - ema_f[i]) / ema_f[i] * 100.0 if ema_f[i] > 1e-12 else 0.0
        if dist_pct < top_dist and adx_arr[i] < top_adx:
            regimes[i] = R_TOPPING
            continue
        # BULL
        if c > ema_s[i] and ema_f[i] > ema_s[i]:
            regimes[i] = R_BULL
            continue
        # NEUTRAL: default (already set)

    return regimes


def h4_regime_array(cl, hi, lo):
    """Regime for each H4 bar from the last COMPLETED D1 bar (no lookahead).

    For H4 bar i, uses D1 bar at index (i+1)//6 - 1.
    Vectorized mapping from D1 regimes to H4 bars.
    """
    d1_cl, d1_hi, d1_lo = aggregate_h4_to_d1(cl, hi, lo)
    if len(d1_cl) == 0:
        return np.full(len(cl), R_NEUTRAL, dtype=np.int32)

    d1_reg = classify_d1_from_arrays(d1_cl, d1_hi, d1_lo)

    n = len(cl)
    d1_idx = (np.arange(n) + 1) // H4_PER_DAY - 1
    reg = np.full(n, R_NEUTRAL, dtype=np.int32)
    valid = (d1_idx >= 0) & (d1_idx < len(d1_reg))
    reg[valid] = d1_reg[d1_idx[valid]]
    return reg


# ═══════════════════════════════════════════════════════════════════════════
# Simulation with Pre-computed Per-bar Fractions
# ═══════════════════════════════════════════════════════════════════════════

def sim_with_fracs(cl, ef, es, at, vd, wi, fracs):
    """VTREND sim with pre-computed per-bar entry fractions.

    fracs[i] = fraction of NAV to invest if an entry signal fires at bar i.
    Fraction determined at signal time (no lookahead).
    Fill at next bar open (≈ prev close).
    """
    n = len(cl)
    cash = CASH
    bq = 0.0
    inp = False
    pk = 0.0
    pe = px = False
    nt = 0
    entry_f = 0.25

    navs = []
    fracs_used = []

    for i in range(n):
        p = cl[i]

        # Step 1: fill pending
        if i > 0:
            fp = cl[i - 1]
            if pe:
                pe = False
                nav_now = cash  # flat → cash is full NAV
                invest = entry_f * nav_now
                if invest >= 1.0 and nav_now >= 1.0:
                    bq = invest / (fp * (1.0 + CPS))
                    cash -= invest
                    inp = True
                    pk = p
                    fracs_used.append(entry_f)
            elif px:
                cash += bq * fp * (1.0 - CPS)
                bq = 0.0
                inp = False
                pk = 0.0
                nt += 1
                px = False

        # Step 2: equity
        nav = cash + bq * p
        if i >= wi:
            navs.append(nav)

        # Step 3: signal
        a_val = at[i]
        if math.isnan(a_val) or math.isnan(ef[i]) or math.isnan(es[i]):
            continue

        if not inp:
            if ef[i] > es[i] and vd[i] > VDO_T:
                entry_f = fracs[i]
                if entry_f < 0.01:
                    continue  # too small → skip entry
                pe = True
        else:
            pk = max(pk, p)
            if p < pk - TRAIL * a_val:
                px = True
            elif ef[i] < es[i]:
                px = True

    # Force close
    if inp and bq > 0:
        cash += bq * cl[-1] * (1.0 - CPS)
        bq = 0.0
        nt += 1
        if navs:
            navs[-1] = cash

    # Metrics
    if len(navs) < 2 or navs[0] <= 0:
        return _empty()

    na = np.array(navs, dtype=np.float64)
    tr = na[-1] / na[0] - 1.0
    yrs = (len(na) - 1) / (6.0 * 365.25)
    cagr = (
        ((1.0 + tr) ** (1.0 / yrs) - 1.0) * 100.0
        if yrs > 0 and tr > -1.0 else -100.0
    )
    pk_arr = np.maximum.accumulate(na)
    dd = (pk_arr - na) / pk_arr * 100.0
    mdd = float(dd.max())
    rets = np.diff(na) / na[:-1]
    std = float(np.std(rets, ddof=0))
    sharpe = float(np.mean(rets)) / std * math.sqrt(6.0 * 365.25) if std > 1e-12 else 0.0
    calmar = cagr / mdd if mdd > 0.01 else 0.0
    avg_f = float(np.mean(fracs_used)) if fracs_used else 0.0

    return {
        "cagr": cagr, "mdd": mdd, "sharpe": sharpe, "calmar": calmar,
        "trades": nt, "avg_frac": avg_f,
    }


def _empty():
    return {
        "cagr": -100.0, "mdd": 100.0, "sharpe": 0.0, "calmar": 0.0,
        "trades": 0, "avg_frac": 0.0,
    }


# ═══════════════════════════════════════════════════════════════════════════
# Fraction Map Builders
# ═══════════════════════════════════════════════════════════════════════════

def build_uniform_fracs(n, frac):
    """Uniform fraction for every bar."""
    return np.full(n, frac, dtype=np.float64)


def build_regime_fracs(regimes_h4, frac_map):
    """Map each H4 bar to its regime fraction via lookup table."""
    lookup = np.array([frac_map.get(r, 0.20) for r in range(6)],
                      dtype=np.float64)
    return lookup[regimes_h4]


def build_vol_fracs(rvol, vol_target):
    """Uniform vol-target → per-bar fraction."""
    n = len(rvol)
    fracs = np.zeros(n, dtype=np.float64)
    valid = (~np.isnan(rvol)) & (rvol > 1e-8)
    fracs[valid] = np.minimum(1.0, vol_target / rvol[valid])
    return fracs


def build_regime_vol_fracs(regimes_h4, vt_map, rvol):
    """Per-bar fraction from regime-specific vol targets."""
    # Build vol target array from regime map
    vt_lookup = np.array([vt_map.get(r, 0.15) for r in range(6)],
                         dtype=np.float64)
    vt_arr = vt_lookup[regimes_h4]
    # Compute fraction
    valid = (~np.isnan(rvol)) & (rvol > 1e-8)
    fracs = np.zeros(len(regimes_h4), dtype=np.float64)
    fracs[valid] = np.minimum(1.0, vt_arr[valid] / rvol[valid])
    return fracs


# ═══════════════════════════════════════════════════════════════════════════
# B1: Per-Regime Trade Analysis
# ═══════════════════════════════════════════════════════════════════════════

def extract_trades_with_regime(cl, ef, es, at, vd, wi, regimes_h4):
    """Run binary VTREND → list of (trade_return, regime_at_entry).

    trade_return = exit_fill_price / entry_fill_price - 1 (includes costs).
    regime_at_entry = integer regime code at the bar where entry signal fired.
    """
    n = len(cl)
    pe = px = inp = False
    pk = entry_fp = 0.0
    entry_regime = R_NEUTRAL
    trades = []

    for i in range(n):
        p = cl[i]

        if i > 0:
            fp = cl[i - 1]
            if pe:
                entry_fp = fp * (1.0 + CPS)
                inp = True
                pk = p
                pe = False
            elif px:
                exit_fp = fp * (1.0 - CPS)
                trades.append((exit_fp / entry_fp - 1.0, entry_regime))
                inp = False
                pk = 0.0
                px = False

        a_val = at[i]
        if math.isnan(a_val) or math.isnan(ef[i]) or math.isnan(es[i]):
            continue

        if not inp:
            if i >= wi and ef[i] > es[i] and vd[i] > VDO_T:
                entry_regime = int(regimes_h4[i])
                pe = True
        else:
            pk = max(pk, p)
            if p < pk - TRAIL * a_val:
                px = True
            elif ef[i] < es[i]:
                px = True

    # Force close
    if inp and entry_fp > 0:
        exit_fp = cl[-1] * (1.0 - CPS)
        trades.append((exit_fp / entry_fp - 1.0, entry_regime))

    return trades


def empirical_kelly_single(returns, n_pts=200):
    """f* that maximizes g(f) = E[log(1 + f*r)]. Range [0.01, 1.0]."""
    if len(returns) < 3:
        return 0.0
    r = np.array(returns, dtype=np.float64)
    fracs = np.linspace(0.01, 1.0, n_pts)
    g = np.empty(n_pts)
    for k, f in enumerate(fracs):
        vals = np.maximum(1.0 + f * r, 1e-100)
        g[k] = np.mean(np.log(vals))
    best = int(np.argmax(g))
    return float(fracs[best])


def run_b1(cl, hi, lo, vo, tb, wi):
    """Part B1: Per-regime trade analysis on real data."""
    print("\n" + "=" * 70)
    print("PART B1: PER-REGIME TRADE ANALYSIS (real data)")
    print("=" * 70)

    ef, es, at, vd = compute_ind(cl, hi, lo, vo, tb)
    regimes_h4 = h4_regime_array(cl, hi, lo)

    # Regime distribution on H4 bars (post-warmup)
    print(f"\n  H4 regime distribution (post-warmup, bars {wi}+):")
    for rc in ALL_REGIMES:
        mask = regimes_h4[wi:] == rc
        cnt = int(mask.sum())
        total = len(regimes_h4) - wi
        pct = cnt / total * 100.0
        print(f"    {REGIME_NAMES[rc]:10s}  {cnt:5d} bars  ({pct:5.1f}%)")

    # Extract trades with regime at entry
    trades = extract_trades_with_regime(cl, ef, es, at, vd, wi, regimes_h4)
    print(f"\n  Total trades: {len(trades)}")

    # Per-regime analysis
    per_regime = {}
    all_returns = [t[0] for t in trades]
    overall_avg = float(np.mean(all_returns)) if all_returns else 0.0

    print(f"\n  {'Regime':>10s}  {'N':>4s}  {'WinR':>6s}  {'AvgRet':>8s}  "
          f"{'AvgWin':>8s}  {'AvgLoss':>8s}  {'Payoff':>7s}  {'Kelly':>6s}")
    print("  " + "-" * 70)

    for rc in ALL_REGIMES:
        rname = REGIME_NAMES[rc]
        rets = [t[0] for t in trades if t[1] == rc]
        n_t = len(rets)
        if n_t == 0:
            per_regime[rname] = {"n_trades": 0}
            print(f"  {rname:>10s}  {0:4d}  {'--':>6s}  {'--':>8s}  "
                  f"{'--':>8s}  {'--':>8s}  {'--':>7s}  {'--':>6s}")
            continue

        r = np.array(rets, dtype=np.float64)
        wins = r[r > 0]
        losses = r[r <= 0]
        wr = len(wins) / n_t * 100
        avg_r = float(r.mean()) * 100
        avg_w = float(wins.mean()) * 100 if len(wins) > 0 else 0.0
        avg_l = float(losses.mean()) * 100 if len(losses) > 0 else 0.0
        if len(losses) > 0 and losses.mean() != 0 and len(wins) > 0:
            payoff = float(wins.mean() / abs(losses.mean()))
        elif len(wins) > 0:
            payoff = 99.0
        else:
            payoff = 0.0
        kelly = empirical_kelly_single(rets)

        per_regime[rname] = {
            "n_trades": n_t,
            "win_rate": wr / 100,
            "avg_return": float(r.mean()),
            "avg_win": float(wins.mean()) if len(wins) > 0 else 0.0,
            "avg_loss": float(losses.mean()) if len(losses) > 0 else 0.0,
            "payoff_ratio": payoff,
            "empirical_kelly": kelly,
        }

        payoff_str = f"{payoff:7.2f}" if payoff < 90 else "    inf"
        flag = " ⚠" if n_t < 10 else ""
        print(f"  {rname:>10s}  {n_t:4d}  {wr:5.1f}%  {avg_r:+7.2f}%  "
              f"{avg_w:+7.2f}%  {avg_l:+7.2f}%  {payoff_str}  {kelly:5.3f}{flag}")

    print(f"\n  Overall avg return: {overall_avg * 100:+.2f}%")
    print("  ⚠ = fewer than 10 trades (Kelly estimate unreliable)")

    # Entry regime distribution
    entry_regimes = [t[1] for t in trades]
    print(f"\n  Entry regime distribution:")
    for rc in ALL_REGIMES:
        cnt = sum(1 for r in entry_regimes if r == rc)
        pct = cnt / len(trades) * 100 if trades else 0
        print(f"    {REGIME_NAMES[rc]:10s}  {cnt:4d} entries  ({pct:5.1f}%)")

    return {
        "per_regime": per_regime,
        "overall_avg_return": overall_avg,
        "total_trades": len(trades),
    }


# ═══════════════════════════════════════════════════════════════════════════
# B2: Regime Sizing Functions (real data sweep)
# ═══════════════════════════════════════════════════════════════════════════

def define_approaches(b1):
    """Define regime sizing approaches based on B1 results."""
    pr = b1["per_regime"]
    approaches = {}

    # 1. Hand-designed conservative
    approaches["hand_cons"] = {
        R_SHOCK: 0.05, R_BEAR: 0.15, R_CHOP: 0.10,
        R_TOPPING: 0.15, R_BULL: 0.40, R_NEUTRAL: 0.25,
    }

    # 2. Hand-designed aggressive
    approaches["hand_aggr"] = {
        R_SHOCK: 0.10, R_BEAR: 0.25, R_CHOP: 0.15,
        R_TOPPING: 0.25, R_BULL: 0.50, R_NEUTRAL: 0.30,
    }

    # 3. Per-regime half-Kelly (capped [0.05, 0.50])
    hk = {}
    for rc in ALL_REGIMES:
        rn = REGIME_NAMES[rc]
        if rn in pr and pr[rn].get("n_trades", 0) >= 5:
            fk = pr[rn].get("empirical_kelly", 0.10)
            hk[rc] = max(0.05, min(0.50, fk / 2))
        else:
            hk[rc] = 0.10  # default for sparse data
        # Safety cap: if avg return is negative, floor at 0.05
        if rn in pr and pr[rn].get("avg_return", 0) < 0:
            hk[rc] = 0.05
    approaches["half_kelly"] = hk

    # 4. Binary bull/non-bull (simple 2-state)
    approaches["binary_bull"] = {
        R_SHOCK: 0.15, R_BEAR: 0.15, R_CHOP: 0.15,
        R_TOPPING: 0.15, R_BULL: 0.40, R_NEUTRAL: 0.15,
    }

    # 5. Return-proportional (data-driven)
    rp = {}
    base_f = 0.25
    for rc in ALL_REGIMES:
        rn = REGIME_NAMES[rc]
        if rn in pr and pr[rn].get("n_trades", 0) >= 3:
            avg_r = pr[rn].get("avg_return", 0.0)
            # Scale: positive avg return → higher fraction
            scale = max(0.2, min(2.0, 1.0 + avg_r * 10.0))
            rp[rc] = max(0.05, min(0.50, base_f * scale))
        else:
            rp[rc] = 0.15
    approaches["return_prop"] = rp

    return approaches


def run_b2(cl, hi, lo, vo, tb, wi, b1):
    """Part B2: Regime sizing sweep on real data."""
    print("\n" + "=" * 70)
    print("PART B2: REGIME SIZING FUNCTIONS (real data)")
    print("=" * 70)

    ef, es, at, vd = compute_ind(cl, hi, lo, vo, tb)
    regimes_h4 = h4_regime_array(cl, hi, lo)
    rvol = compute_rolling_vol(cl)

    approaches = define_approaches(b1)

    # Print fraction maps
    print("\n  Fraction maps per regime:")
    for name, fmap in approaches.items():
        parts = [f"{REGIME_NAMES[rc][:4]}={fmap[rc]:.2f}" for rc in ALL_REGIMES]
        print(f"    {name:14s}  {' '.join(parts)}")

    # Regime-conditional vol targets
    regime_vt = {
        R_SHOCK: 0.08, R_BEAR: 0.10, R_CHOP: 0.12,
        R_TOPPING: 0.12, R_BULL: 0.25, R_NEUTRAL: 0.15,
    }
    parts = [f"{REGIME_NAMES[rc][:4]}={regime_vt[rc]:.0%}" for rc in ALL_REGIMES]
    print(f"    {'regime_vol':14s}  {' '.join(parts)}")

    # Build all fraction arrays
    n = len(cl)
    all_variants = {}

    # Uniform baselines
    all_variants["f=0.20"] = build_uniform_fracs(n, 0.20)
    all_variants["f=0.30"] = build_uniform_fracs(n, 0.30)
    all_variants["f=1.00"] = build_uniform_fracs(n, 1.00)
    all_variants["vol=15%"] = build_vol_fracs(rvol, 0.15)

    # Regime-based fractions
    for name, fmap in approaches.items():
        all_variants[name] = build_regime_fracs(regimes_h4, fmap)

    # Regime-based vol targets
    all_variants["regime_vol"] = build_regime_vol_fracs(regimes_h4, regime_vt, rvol)

    # Run all
    results = {}
    print(f"\n  {'Variant':>14s}  {'avgF':>5s}  {'CAGR':>7s}  {'MDD':>6s}  "
          f"{'Sharpe':>7s}  {'Calmar':>7s}  {'Trades':>6s}")
    print("  " + "-" * 62)

    for vname, fracs in all_variants.items():
        r = sim_with_fracs(cl, ef, es, at, vd, wi, fracs)
        results[vname] = r
        tag = " ←base" if vname in ("f=0.20", "f=0.30", "f=1.00", "vol=15%") else ""
        print(f"  {vname:>14s}  {r['avg_frac']:5.2f}  {r['cagr']:+6.1f}%  "
              f"{r['mdd']:5.1f}%  {r['sharpe']:7.2f}  {r['calmar']:7.3f}  "
              f"{r['trades']:5d}{tag}")

    # Find best regime approach
    regime_names = [k for k in results
                    if k not in ("f=0.20", "f=0.30", "f=1.00", "vol=15%")]
    best_cal_r = max(regime_names, key=lambda k: results[k]["calmar"])
    best_sh_r = max(regime_names, key=lambda k: results[k]["sharpe"])

    print(f"\n  Best regime Calmar  : {best_cal_r} "
          f"(Calmar={results[best_cal_r]['calmar']:.3f})")
    print(f"  Best regime Sharpe  : {best_sh_r} "
          f"(Sharpe={results[best_sh_r]['sharpe']:.2f})")
    print(f"\n  Comparison vs uniform baselines:")
    for base in ("f=0.30", "f=0.20", "vol=15%"):
        print(f"    {base:10s}  Calmar={results[base]['calmar']:.3f}  "
              f"Sharpe={results[base]['sharpe']:.2f}  "
              f"CAGR={results[base]['cagr']:+.1f}%  MDD={results[base]['mdd']:.1f}%")

    return results, approaches, regime_vt


# ═══════════════════════════════════════════════════════════════════════════
# B3: Bootstrap
# ═══════════════════════════════════════════════════════════════════════════

def run_b3(cl, hi, lo, vo, tb, wi, approaches, regime_vt):
    """Bootstrap 2000 paths: regime sizing vs uniform baselines."""
    print("\n" + "=" * 70)
    print("PART B3: BOOTSTRAP ROBUSTNESS (2000 paths)")
    print("=" * 70)

    # Define all variants: (label, type, frac, vol_target, map)
    variant_defs = []
    # Uniform baselines
    variant_defs.append(("f=0.20", "uniform", 0.20, None, None))
    variant_defs.append(("f=0.30", "uniform", 0.30, None, None))
    variant_defs.append(("f=1.00", "uniform", 1.00, None, None))
    variant_defs.append(("vol=15%", "vol_uniform", None, 0.15, None))
    # Regime fraction approaches
    for name, fmap in approaches.items():
        variant_defs.append((name, "regime_frac", None, None, fmap))
    # Regime vol target
    variant_defs.append(("regime_vol", "regime_vol", None, None, regime_vt))

    print(f"\n  Testing {len(variant_defs)} variants on {N_BOOT} bootstrap paths:")
    for vname, vtype, *_ in variant_defs:
        print(f"    {vname:14s}  ({vtype})")

    # Prepare data
    cr, hr, lr, vol, tbr = make_ratios(cl, hi, lo, vo, tb)
    n_trans = len(cl) - 1
    p0 = cl[0]
    rng = np.random.default_rng(SEED)

    metrics_list = ["cagr", "mdd", "sharpe", "calmar"]
    boot = {vname: {m: [] for m in metrics_list}
            for vname, *_ in variant_defs}

    t0 = time.time()
    for b in range(N_BOOT):
        if (b + 1) % 200 == 0 or b == 0:
            el = time.time() - t0
            rate = (b + 1) / el if el > 0 else 1
            eta = (N_BOOT - b - 1) / rate
            print(f"    {b + 1:5d}/{N_BOOT}  ({el:.0f}s, ~{eta:.0f}s left)")

        # Generate path
        c, h, l, v, t = gen_path(cr, hr, lr, vol, tbr, n_trans, BLKSZ, p0, rng)

        # Compute VTREND indicators
        ef, es, at, vd = compute_ind(c, h, l, v, t)

        # Compute regime array on synthetic path
        reg = h4_regime_array(c, h, l)

        # Compute rolling vol
        rv = compute_rolling_vol(c)

        n_path = len(c)

        # Run all variants
        for vname, vtype, frac_val, vol_tgt, map_val in variant_defs:
            if vtype == "uniform":
                fracs = build_uniform_fracs(n_path, frac_val)
            elif vtype == "vol_uniform":
                fracs = build_vol_fracs(rv, vol_tgt)
            elif vtype == "regime_frac":
                fracs = build_regime_fracs(reg, map_val)
            elif vtype == "regime_vol":
                fracs = build_regime_vol_fracs(reg, map_val, rv)
            else:
                fracs = build_uniform_fracs(n_path, 0.30)

            r = sim_with_fracs(c, ef, es, at, vd, wi, fracs)
            for m in metrics_list:
                boot[vname][m].append(r[m])

    el = time.time() - t0
    print(f"\n  Done: {el:.1f}s ({N_BOOT / el:.1f} paths/sec)")

    # Convert to numpy
    for vname in boot:
        for m in metrics_list:
            boot[vname][m] = np.array(boot[vname][m])

    return boot, variant_defs


def analyze_b3(boot, variant_defs):
    """Print bootstrap distributions and paired comparisons."""
    metrics_list = ["cagr", "mdd", "sharpe", "calmar"]

    # ── Distribution summary ──
    print("\n" + "-" * 70)
    print("BOOTSTRAP DISTRIBUTIONS")
    print("-" * 70)

    print(f"\n  {'variant':>14s}  {'P(CAGR>0)':>10s}  {'P(MDD<30)':>10s}  "
          f"{'medCAGR':>8s}  {'medMDD':>7s}  {'medShrp':>8s}  {'medCalm':>8s}")
    print("  " + "-" * 75)

    for vname, *_ in variant_defs:
        cg = boot[vname]["cagr"]
        md = boot[vname]["mdd"]
        sh = boot[vname]["sharpe"]
        cm = boot[vname]["calmar"]
        print(f"  {vname:>14s}  {np.mean(cg > 0) * 100:9.1f}%  "
              f"{np.mean(md < 30) * 100:9.1f}%  "
              f"{np.median(cg):+7.1f}%  {np.median(md):6.1f}%  "
              f"{np.median(sh):8.3f}  {np.median(cm):8.3f}")

    # ── Full distributions for each variant ──
    print("\n  Detailed percentiles:")
    for vname, *_ in variant_defs:
        print(f"\n    ── {vname} ──")
        for m in metrics_list:
            a = boot[vname][m]
            pct = np.percentile(a, [5, 25, 50, 75, 95])
            print(f"      {m:8s}  p5={pct[0]:+7.2f}  p25={pct[1]:+7.2f}  "
                  f"p50={pct[2]:+7.2f}  p75={pct[3]:+7.2f}  p95={pct[4]:+7.2f}")

    # ── Paired tests vs f=0.30 ──
    base_label = "f=0.30"
    regime_labels = [vn for vn, vt, *_ in variant_defs
                     if vt in ("regime_frac", "regime_vol")]

    print("\n" + "-" * 70)
    print(f"PAIRED TESTS vs {base_label}")
    print("-" * 70)
    print("  P(better) > 97.5% ≈ significant at α=0.05 (one-sided).\n")

    for label in regime_labels:
        print(f"  ── {label} vs {base_label} ──")

        # CAGR: higher is better
        d = boot[label]["cagr"] - boot[base_label]["cagr"]
        ci = np.percentile(d, [2.5, 97.5])
        sig = " ***" if np.mean(d > 0) > 0.975 else ""
        print(f"    ΔCAGR     mean={d.mean():+7.2f}  "
              f"P(higher)={np.mean(d > 0) * 100:5.1f}%  "
              f"CI=[{ci[0]:+.2f}, {ci[1]:+.2f}]{sig}")

        # MDD: lower is better
        d = boot[base_label]["mdd"] - boot[label]["mdd"]
        ci = np.percentile(d, [2.5, 97.5])
        sig = " ***" if np.mean(d > 0) > 0.975 else ""
        print(f"    ΔMDD(red) mean={d.mean():+7.2f}  "
              f"P(lower) ={np.mean(d > 0) * 100:5.1f}%  "
              f"CI=[{ci[0]:+.2f}, {ci[1]:+.2f}]{sig}")

        # Sharpe: higher is better
        d = boot[label]["sharpe"] - boot[base_label]["sharpe"]
        ci = np.percentile(d, [2.5, 97.5])
        sig = " ***" if np.mean(d > 0) > 0.975 else ""
        print(f"    ΔSharpe   mean={d.mean():+7.3f}  "
              f"P(higher)={np.mean(d > 0) * 100:5.1f}%  "
              f"CI=[{ci[0]:+.3f}, {ci[1]:+.3f}]{sig}")

        # Calmar: higher is better
        d = boot[label]["calmar"] - boot[base_label]["calmar"]
        ci = np.percentile(d, [2.5, 97.5])
        sig = " ***" if np.mean(d > 0) > 0.975 else ""
        print(f"    ΔCalmar   mean={d.mean():+7.3f}  "
              f"P(higher)={np.mean(d > 0) * 100:5.1f}%  "
              f"CI=[{ci[0]:+.3f}, {ci[1]:+.3f}]{sig}")

        print()

    # ── Also compare regime approaches against f=0.20 ──
    base2 = "f=0.20"
    print(f"  ── Quick comparison vs {base2} (best MDD control) ──")
    print(f"  {'variant':>14s}  {'ΔCAGR':>7s}  {'P(+)':>6s}  "
          f"{'ΔMDD':>7s}  {'P(↓)':>6s}  {'ΔCalm':>7s}  {'P(+)':>6s}")
    print("  " + "-" * 62)
    for label in regime_labels:
        dc = boot[label]["cagr"] - boot[base2]["cagr"]
        dm = boot[base2]["mdd"] - boot[label]["mdd"]
        dcm = boot[label]["calmar"] - boot[base2]["calmar"]
        print(f"  {label:>14s}  {dc.mean():+6.2f}  {np.mean(dc > 0) * 100:5.1f}%  "
              f"{dm.mean():+6.2f}  {np.mean(dm > 0) * 100:5.1f}%  "
              f"{dcm.mean():+6.3f}  {np.mean(dcm > 0) * 100:5.1f}%")

    # ── Cross-comparison: regime approaches against each other ──
    print(f"\n  ── Regime approaches cross-comparison (Calmar) ──")
    print(f"  {'':14s}", end="")
    for lb in regime_labels:
        print(f"  {lb:>12s}", end="")
    print()
    for la in regime_labels:
        print(f"  {la:>14s}", end="")
        for lb in regime_labels:
            if la == lb:
                print(f"  {'---':>12s}", end="")
            else:
                d = boot[la]["calmar"] - boot[lb]["calmar"]
                p = np.mean(d > 0) * 100
                print(f"  {p:11.1f}%", end="")
        print()


# ═══════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 70)
    print("HƯỚNG B: REGIME-DEPENDENT POSITION SIZING")
    print("=" * 70)
    print(f"  Period: {START} → {END}   Warmup: {WARMUP}d")
    print(f"  Cost: harsh ({COST.round_trip_bps:.0f} bps RT)")
    print(f"  Bootstrap: {N_BOOT} paths, block={BLKSZ}")
    print(f"  Regimes: {', '.join(REGIME_NAMES.values())}")

    print("\nLoading data...")
    cl, hi, lo, vo, tb, wi, n = load_arrays()
    print(f"  {n} H4 bars, warmup idx={wi}, trading={n - wi} bars")

    # B1: Per-regime trade analysis
    b1 = run_b1(cl, hi, lo, vo, tb, wi)

    # B2: Regime sizing sweep (real data)
    b2_results, approaches, regime_vt = run_b2(cl, hi, lo, vo, tb, wi, b1)

    # B3: Bootstrap
    boot, variant_defs = run_b3(cl, hi, lo, vo, tb, wi, approaches, regime_vt)
    analyze_b3(boot, variant_defs)

    # ── Final Summary ──
    print("\n" + "=" * 70)
    print("FINAL SUMMARY")
    print("=" * 70)

    # Find the best regime approach by median bootstrap Calmar
    regime_labels = [vn for vn, vt, *_ in variant_defs
                     if vt in ("regime_frac", "regime_vol")]
    all_labels = [vn for vn, *_ in variant_defs]

    best_regime = max(regime_labels,
                      key=lambda k: np.median(boot[k]["calmar"]))
    best_overall = max(all_labels,
                       key=lambda k: np.median(boot[k]["calmar"]))

    print(f"\n  Best regime approach   : {best_regime}")
    print(f"    median Calmar={np.median(boot[best_regime]['calmar']):.3f}  "
          f"median CAGR={np.median(boot[best_regime]['cagr']):+.1f}%  "
          f"median MDD={np.median(boot[best_regime]['mdd']):.1f}%")

    print(f"\n  Best overall (by Calmar): {best_overall}")
    print(f"    median Calmar={np.median(boot[best_overall]['calmar']):.3f}  "
          f"median CAGR={np.median(boot[best_overall]['cagr']):+.1f}%  "
          f"median MDD={np.median(boot[best_overall]['mdd']):.1f}%")

    # Does any regime approach significantly beat f=0.30?
    sig_found = False
    for label in regime_labels:
        d = boot[label]["calmar"] - boot["f=0.30"]["calmar"]
        p = np.mean(d > 0)
        if p > 0.975:
            print(f"\n  *** {label} significantly beats f=0.30 on Calmar "
                  f"(P={p:.3f}) ***")
            sig_found = True

    if not sig_found:
        print("\n  NO regime approach significantly beats f=0.30 on Calmar "
              "(all P < 97.5%)")

    # Sharpe comparison
    print(f"\n  Sharpe comparison (median bootstrap):")
    for label in ["f=0.30", "f=0.20", "vol=15%"] + regime_labels:
        med_sh = np.median(boot[label]["sharpe"])
        print(f"    {label:>14s}  Sharpe={med_sh:.3f}")

    # ── Save ──
    outdir = Path(__file__).resolve().parent / "results"
    outdir.mkdir(exist_ok=True)

    output = {
        "settings": {
            "n_boot": N_BOOT, "block_size": BLKSZ,
            "cost_rt_bps": COST.round_trip_bps,
            "start": START, "end": END, "warmup_days": WARMUP,
        },
        "b1_per_regime": b1,
        "b2_real_data": {k: v for k, v in b2_results.items()},
        "b2_approaches": {
            name: {REGIME_NAMES[rc]: fmap[rc] for rc in ALL_REGIMES}
            for name, fmap in approaches.items()
        },
        "b2_regime_vol": {REGIME_NAMES[rc]: regime_vt[rc] for rc in ALL_REGIMES},
        "b3_bootstrap": {},
        "b3_paired_tests": {},
    }

    metrics_list = ["cagr", "mdd", "sharpe", "calmar"]
    for vname, *_ in variant_defs:
        output["b3_bootstrap"][vname] = {}
        for m in metrics_list:
            a = boot[vname][m]
            pct = np.percentile(a, [5, 25, 50, 75, 95]).tolist()
            output["b3_bootstrap"][vname][m] = {
                "mean": round(float(a.mean()), 4),
                "std": round(float(a.std()), 4),
                "p5": round(pct[0], 4), "p25": round(pct[1], 4),
                "p50": round(pct[2], 4), "p75": round(pct[3], 4),
                "p95": round(pct[4], 4),
            }

    # Paired test results
    base_label = "f=0.30"
    for label in regime_labels:
        output["b3_paired_tests"][label] = {}
        for m in ["cagr", "sharpe", "calmar"]:
            d = boot[label][m] - boot[base_label][m]
            ci = np.percentile(d, [2.5, 97.5]).tolist()
            output["b3_paired_tests"][label][m] = {
                "mean_diff": round(float(d.mean()), 4),
                "p_better": round(float(np.mean(d > 0)), 4),
                "ci_lo": round(ci[0], 4), "ci_hi": round(ci[1], 4),
            }
        d = boot[base_label]["mdd"] - boot[label]["mdd"]
        ci = np.percentile(d, [2.5, 97.5]).tolist()
        output["b3_paired_tests"][label]["mdd_reduction"] = {
            "mean_diff": round(float(d.mean()), 4),
            "p_lower": round(float(np.mean(d > 0)), 4),
            "ci_lo": round(ci[0], 4), "ci_hi": round(ci[1], 4),
        }

    outpath = outdir / "regime_sizing.json"
    with open(outpath, "w") as f:
        json.dump(output, f, indent=2, default=str)

    print(f"\n  Results saved → {outpath}")
    print("\n" + "=" * 70)
    print("DONE")
    print("=" * 70)
