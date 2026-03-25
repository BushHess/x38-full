#!/usr/bin/env python3
"""Hướng A: Position Sizing — Kelly Criterion, Fixed Fraction, Vol-Targeting.

Part A1: Kelly Criterion Estimation
  Extract per-trade returns from binary VTREND on real data.
  Empirical Kelly: maximize g(f) = E[log(1 + f*r)].
  Bernoulli Kelly: f* = (p*b - q) / b.

Part A2: Fixed Fraction Sweep (real data)
  Fractions: 0.10 to 1.00.
  CAGR, MDD, Sharpe, Calmar for each.
  Find optimal fraction for each metric.

Part A3: Volatility Targeting (real data)
  Target annual vols: 10% to 50%.
  Dynamic fraction = min(1, target / realized_vol).
  Rolling vol: 60-bar std of H4 log returns, annualized.

Part A4: Bootstrap (2000 paths)
  Selected sizing variants vs f=1.0 baseline.
  Paired test: does sizing improve Calmar? Reduce MDD?

Key question: can position sizing transform
  median MDD=64% → MDD<30%  while preserving meaningful CAGR?

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

FRACS = [0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50, 0.60, 0.80, 1.00]
VOL_TARGETS = [0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50]
VOL_WIN = 60     # bars for rolling vol
ANN = math.sqrt(6.0 * 365.25)  # annualization factor for H4


# ═══════════════════════════════════════════════════════════════════════════
# Data Loading & Path Generation (same as bootstrap_regime.py)
# ═══════════════════════════════════════════════════════════════════════════

def load_arrays():
    """Load real H4 data as numpy arrays."""
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


def compute_ind(cl, hi, lo, vo, tb):
    """Compute VTREND indicators (no gate EMAs — not needed here)."""
    return (
        _ema(cl, FAST),
        _ema(cl, SLOW),
        _atr(hi, lo, cl, ATR_P),
        _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S),
    )


# ═══════════════════════════════════════════════════════════════════════════
# Rolling Volatility
# ═══════════════════════════════════════════════════════════════════════════

def compute_rolling_vol(cl, window=VOL_WIN):
    """Annualized rolling vol from H4 log returns (vectorized).

    vol[i] = std(log_returns[i-window:i]) * sqrt(6*365.25)
    Valid for i >= window.  NaN for i < window.
    """
    n = len(cl)
    lr = np.diff(np.log(cl))   # length N-1

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
# Trade Return Extraction (for Kelly)
# ═══════════════════════════════════════════════════════════════════════════

def extract_trade_returns(cl, ef, es, at, vd, wi):
    """Run binary VTREND, return list of per-trade decimal returns.

    Each return r = exit_fill_price / entry_fill_price - 1.
    Includes cost (spread + slippage + fee) on both sides.
    """
    n = len(cl)
    pe = px = inp = False
    pk = entry_fp = 0.0
    returns = []

    for i in range(n):
        p = cl[i]

        # Fill pending
        if i > 0:
            fp = cl[i - 1]
            if pe:
                entry_fp = fp * (1.0 + CPS)
                inp = True
                pk = p
                pe = False
            elif px:
                exit_fp = fp * (1.0 - CPS)
                returns.append(exit_fp / entry_fp - 1.0)
                inp = False
                pk = 0.0
                px = False

        # Signal — only after warmup with valid indicators
        a_val = at[i]
        if math.isnan(a_val) or math.isnan(ef[i]) or math.isnan(es[i]):
            continue

        if not inp:
            if i >= wi and ef[i] > es[i] and vd[i] > VDO_T:
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
        returns.append(exit_fp / entry_fp - 1.0)

    return returns


# ═══════════════════════════════════════════════════════════════════════════
# Kelly Criterion
# ═══════════════════════════════════════════════════════════════════════════

def empirical_kelly(returns, n_pts=300):
    """Find f* that maximizes g(f) = E[log(1 + f*r)].

    Returns (f_star, g_star, fracs_array, g_curve_array).
    """
    r = np.array(returns, dtype=np.float64)
    fracs = np.linspace(0.01, 2.0, n_pts)
    g = np.empty(n_pts)
    for k, f in enumerate(fracs):
        vals = 1.0 + f * r
        # Ruin if any val <= 0 → clamp to small positive
        np.maximum(vals, 1e-100, out=vals)
        g[k] = np.mean(np.log(vals))
    best = int(np.argmax(g))
    return float(fracs[best]), float(g[best]), fracs, g


def bernoulli_kelly(returns):
    """Bernoulli Kelly: f* = (p*b - q) / b."""
    r = np.array(returns, dtype=np.float64)
    wins = r[r > 0]
    losses = r[r <= 0]
    if len(wins) == 0 or len(losses) == 0:
        return 0.0
    p = len(wins) / len(r)
    q = 1.0 - p
    b = np.mean(wins) / abs(np.mean(losses))
    return max(0.0, p - q / b)


# ═══════════════════════════════════════════════════════════════════════════
# Core Simulation with Position Sizing
# ═══════════════════════════════════════════════════════════════════════════

def sim_sized(cl, ef, es, at, vd, wi,
              frac=1.0, vol_target=None, rvol=None):
    """VTREND with position sizing.

    Parameters
    ----------
    frac : float
        Fixed fraction of NAV to invest (used when vol_target is None).
    vol_target : float or None
        If set, dynamic sizing: entry_f = min(1, vol_target / rvol[i]).
    rvol : array or None
        Pre-computed rolling annualized vol.

    Returns metrics dict.
    """
    n = len(cl)
    cash = CASH
    bq = 0.0       # btc qty
    inp = False     # in position
    pk = 0.0        # peak for trail stop
    pe = False      # pending entry
    px = False      # pending exit
    nt = 0          # trade count
    entry_f = frac  # fraction to use at fill (set at signal time)

    navs = []       # equity curve (post-warmup)
    fracs_used = [] # entry fractions (for diagnostics)

    for i in range(n):
        p = cl[i]

        # ── Step 1: fill pending ──
        if i > 0:
            fp = cl[i - 1]
            if pe:
                pe = False
                nav_now = cash   # bq=0 when flat
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

        # ── Step 2: equity ──
        nav = cash + bq * p
        if i >= wi:
            navs.append(nav)

        # ── Step 3: signal ──
        a_val = at[i]
        if math.isnan(a_val) or math.isnan(ef[i]) or math.isnan(es[i]):
            continue

        if not inp:
            if ef[i] > es[i] and vd[i] > VDO_T:
                # Determine sizing at signal time (no lookahead)
                if vol_target is not None and rvol is not None:
                    rv = rvol[i]
                    if math.isnan(rv) or rv < 1e-8:
                        continue   # can't compute vol → skip entry
                    entry_f = min(1.0, vol_target / rv)
                else:
                    entry_f = frac
                pe = True
        else:
            pk = max(pk, p)
            ts = pk - TRAIL * a_val
            if p < ts:
                px = True
            elif ef[i] < es[i]:
                px = True

    # ── Force close ──
    if inp and bq > 0:
        cash += bq * cl[-1] * (1.0 - CPS)
        bq = 0.0
        nt += 1
        if navs:
            navs[-1] = cash

    # ── Compute metrics ──
    if len(navs) < 2 or navs[0] <= 0:
        return _empty_metrics()

    na = np.array(navs, dtype=np.float64)
    tr = na[-1] / na[0] - 1.0
    yrs = (len(na) - 1) / (6.0 * 365.25)

    cagr = (
        ((1.0 + tr) ** (1.0 / yrs) - 1.0) * 100.0
        if yrs > 0 and tr > -1.0 else -100.0
    )

    peak = np.maximum.accumulate(na)
    dd = (peak - na) / peak * 100.0
    mdd = float(dd.max())

    rets = np.diff(na) / na[:-1]
    std = float(np.std(rets, ddof=0))
    sharpe = float(np.mean(rets)) / std * math.sqrt(6.0 * 365.25) if std > 1e-12 else 0.0

    calmar = cagr / mdd if mdd > 0.01 else 0.0

    # Geometric growth rate (annualized %)
    geo = math.log(na[-1] / na[0]) / len(na) * (6.0 * 365.25) * 100.0 if na[-1] > 0 else -100.0

    # Min NAV as % of initial
    min_nav = float(na.min() / na[0]) * 100.0

    # Average entry fraction
    avg_f = float(np.mean(fracs_used)) if fracs_used else frac

    return {
        "cagr": cagr, "mdd": mdd, "sharpe": sharpe, "calmar": calmar,
        "trades": nt, "geo_growth": geo, "min_nav_pct": min_nav,
        "avg_frac": avg_f,
    }


def _empty_metrics():
    return {
        "cagr": -100.0, "mdd": 100.0, "sharpe": 0.0, "calmar": 0.0,
        "trades": 0, "geo_growth": -100.0, "min_nav_pct": 0.0,
        "avg_frac": 0.0,
    }


# ═══════════════════════════════════════════════════════════════════════════
# Part A1: Kelly Criterion
# ═══════════════════════════════════════════════════════════════════════════

def run_kelly(cl, hi, lo, vo, tb, wi):
    """Estimate Kelly fraction from real data trade returns."""
    print("\n" + "=" * 70)
    print("PART A1: KELLY CRITERION ESTIMATION")
    print("=" * 70)

    ef, es, at, vd = compute_ind(cl, hi, lo, vo, tb)
    returns = extract_trade_returns(cl, ef, es, at, vd, wi)
    r = np.array(returns, dtype=np.float64)

    n_trades = len(r)
    wins = r[r > 0]
    losses = r[r <= 0]

    print(f"\n  Per-trade return distribution ({n_trades} trades):")
    print(f"    Win rate     : {len(wins)/n_trades*100:.1f}%  "
          f"({len(wins)} wins, {len(losses)} losses)")
    print(f"    Mean return  : {r.mean()*100:+.2f}%")
    print(f"    Median return: {np.median(r)*100:+.2f}%")
    print(f"    Std return   : {r.std()*100:.2f}%")
    print(f"    Avg win      : {wins.mean()*100:+.2f}%")
    print(f"    Avg loss     : {losses.mean()*100:.2f}%")
    print(f"    Payoff ratio : {wins.mean()/abs(losses.mean()):.2f}")
    print(f"    Min return   : {r.min()*100:.2f}%")
    print(f"    Max return   : {r.max()*100:.2f}%")

    # Bernoulli Kelly
    f_bern = bernoulli_kelly(returns)
    print(f"\n  Bernoulli Kelly: f* = {f_bern:.3f}")

    # Empirical Kelly
    f_emp, g_emp, fracs, g_curve = empirical_kelly(returns)
    print(f"  Empirical Kelly: f* = {f_emp:.3f}  "
          f"(growth rate = {g_emp:.6f} per trade)")

    # Growth rate at selected fractions
    print(f"\n  Growth rate g(f) at selected fractions:")
    print(f"    {'f':>6s}  {'g(f)':>10s}  {'ann_g%':>8s}")
    for f_test in [0.10, 0.20, 0.25, 0.30, 0.40, 0.50,
                   f_emp, 0.75, 1.00, 1.50]:
        vals = np.maximum(1.0 + f_test * r, 1e-100)
        g_val = float(np.mean(np.log(vals)))
        # Annualized: assume ~30 trades per year
        trades_per_year = n_trades / 7.14  # ~7 years
        ann_g = g_val * trades_per_year * 100
        label = " *Kelly*" if abs(f_test - f_emp) < 0.01 else ""
        print(f"    {f_test:6.3f}  {g_val:10.6f}  {ann_g:+7.2f}%{label}")

    # Recommended fractions
    f_half = f_emp / 2
    f_quarter = f_emp / 4
    print(f"\n  Recommended fractions:")
    print(f"    Full Kelly   : f = {f_emp:.3f}")
    print(f"    Half Kelly   : f = {f_half:.3f}")
    print(f"    Quarter Kelly: f = {f_quarter:.3f}")

    return {
        "n_trades": n_trades,
        "win_rate": len(wins) / n_trades,
        "avg_win": float(wins.mean()),
        "avg_loss": float(losses.mean()),
        "payoff_ratio": float(wins.mean() / abs(losses.mean())),
        "bernoulli_kelly": f_bern,
        "empirical_kelly": f_emp,
        "half_kelly": f_half,
        "quarter_kelly": f_quarter,
        "trade_returns": returns,
    }


# ═══════════════════════════════════════════════════════════════════════════
# Part A2: Fixed Fraction Sweep
# ═══════════════════════════════════════════════════════════════════════════

def run_fraction_sweep(cl, hi, lo, vo, tb, wi, kelly_info):
    """Sweep fixed fractions on real data."""
    print("\n" + "=" * 70)
    print("PART A2: FIXED FRACTION SWEEP (real data)")
    print("=" * 70)

    ef, es, at, vd = compute_ind(cl, hi, lo, vo, tb)

    # Add Kelly fractions to the sweep
    extra = [kelly_info["quarter_kelly"], kelly_info["half_kelly"],
             kelly_info["empirical_kelly"]]
    all_fracs = sorted(set(FRACS + extra))

    results = {}
    print(f"\n  {'frac':>6s}  {'CAGR':>7s}  {'MDD':>6s}  {'Sharpe':>7s}  "
          f"{'Calmar':>7s}  {'GeoGr':>7s}  {'MinNAV':>7s}  {'Trades':>6s}")
    print("  " + "-" * 68)

    for f in all_fracs:
        r = sim_sized(cl, ef, es, at, vd, wi, frac=f)
        results[f] = r
        label = ""
        if abs(f - kelly_info["empirical_kelly"]) < 0.005:
            label = " ←Kelly"
        elif abs(f - kelly_info["half_kelly"]) < 0.005:
            label = " ←½K"
        elif abs(f - kelly_info["quarter_kelly"]) < 0.005:
            label = " ←¼K"
        print(f"  {f:6.3f}  {r['cagr']:+6.1f}%  {r['mdd']:5.1f}%  "
              f"{r['sharpe']:7.2f}  {r['calmar']:7.3f}  "
              f"{r['geo_growth']:+6.1f}%  {r['min_nav_pct']:6.1f}%  "
              f"{r['trades']:5d}{label}")

    # Find optimal for each metric
    print("\n  Optimal fractions:")
    best_calmar_f = max(results, key=lambda f: results[f]["calmar"])
    best_sharpe_f = max(results, key=lambda f: results[f]["sharpe"])
    best_geo_f    = max(results, key=lambda f: results[f]["geo_growth"])
    best_mdd_f    = min(results, key=lambda f: results[f]["mdd"])
    print(f"    Best Calmar  : f = {best_calmar_f:.3f} "
          f"(Calmar = {results[best_calmar_f]['calmar']:.3f})")
    print(f"    Best Sharpe  : f = {best_sharpe_f:.3f} "
          f"(Sharpe = {results[best_sharpe_f]['sharpe']:.2f})")
    print(f"    Best GeoGrowth: f = {best_geo_f:.3f} "
          f"(geo = {results[best_geo_f]['geo_growth']:+.1f}%)")
    print(f"    Lowest MDD   : f = {best_mdd_f:.3f} "
          f"(MDD = {results[best_mdd_f]['mdd']:.1f}%)")

    return results, all_fracs


# ═══════════════════════════════════════════════════════════════════════════
# Part A3: Volatility Targeting
# ═══════════════════════════════════════════════════════════════════════════

def run_vol_targeting(cl, hi, lo, vo, tb, wi):
    """Sweep vol targets on real data."""
    print("\n" + "=" * 70)
    print("PART A3: VOLATILITY TARGETING (real data)")
    print("=" * 70)

    ef, es, at, vd = compute_ind(cl, hi, lo, vo, tb)
    rvol = compute_rolling_vol(cl)

    # Show realized vol stats
    valid_vol = rvol[~np.isnan(rvol)]
    print(f"\n  Realized annual vol distribution (H4, {VOL_WIN}-bar rolling):")
    pcts = np.percentile(valid_vol, [5, 25, 50, 75, 95])
    print(f"    p5={pcts[0]:.1%}  p25={pcts[1]:.1%}  "
          f"p50={pcts[2]:.1%}  p75={pcts[3]:.1%}  p95={pcts[4]:.1%}")
    print(f"    mean={valid_vol.mean():.1%}  min={valid_vol.min():.1%}  "
          f"max={valid_vol.max():.1%}")

    results = {}
    print(f"\n  {'target':>7s}  {'avgF':>5s}  {'CAGR':>7s}  {'MDD':>6s}  "
          f"{'Sharpe':>7s}  {'Calmar':>7s}  {'GeoGr':>7s}  {'MinNAV':>7s}  "
          f"{'Trades':>6s}")
    print("  " + "-" * 74)

    for vt in VOL_TARGETS:
        r = sim_sized(cl, ef, es, at, vd, wi, vol_target=vt, rvol=rvol)
        results[vt] = r
        print(f"  {vt:6.0%}  {r['avg_frac']:5.2f}  {r['cagr']:+6.1f}%  "
              f"{r['mdd']:5.1f}%  {r['sharpe']:7.2f}  {r['calmar']:7.3f}  "
              f"{r['geo_growth']:+6.1f}%  {r['min_nav_pct']:6.1f}%  "
              f"{r['trades']:5d}")

    # Also add f=1.0 baseline
    r_base = sim_sized(cl, ef, es, at, vd, wi, frac=1.0)
    print(f"  {'f=1.0':>7s}  {'1.00':>5s}  {r_base['cagr']:+6.1f}%  "
          f"{r_base['mdd']:5.1f}%  {r_base['sharpe']:7.2f}  "
          f"{r_base['calmar']:7.3f}  {r_base['geo_growth']:+6.1f}%  "
          f"{r_base['min_nav_pct']:6.1f}%  {r_base['trades']:5d}  ←baseline")

    # Find optimal
    print("\n  Optimal vol targets:")
    best_calmar = max(results, key=lambda v: results[v]["calmar"])
    best_sharpe = max(results, key=lambda v: results[v]["sharpe"])
    best_geo    = max(results, key=lambda v: results[v]["geo_growth"])
    print(f"    Best Calmar  : σ_target = {best_calmar:.0%} "
          f"(Calmar = {results[best_calmar]['calmar']:.3f})")
    print(f"    Best Sharpe  : σ_target = {best_sharpe:.0%} "
          f"(Sharpe = {results[best_sharpe]['sharpe']:.2f})")
    print(f"    Best GeoGrowth: σ_target = {best_geo:.0%} "
          f"(geo = {results[best_geo]['geo_growth']:+.1f}%)")

    return results


# ═══════════════════════════════════════════════════════════════════════════
# Part A4: Bootstrap
# ═══════════════════════════════════════════════════════════════════════════

def run_bootstrap(cl, hi, lo, vo, tb, wi, kelly_info, frac_results, vol_results):
    """Bootstrap 2000 paths for selected sizing variants."""
    print("\n" + "=" * 70)
    print("PART A4: BOOTSTRAP ROBUSTNESS (2000 paths)")
    print("=" * 70)

    # Select variants to bootstrap
    f_kelly = kelly_info["empirical_kelly"]
    f_half  = kelly_info["half_kelly"]
    f_qtr   = kelly_info["quarter_kelly"]

    # Best fixed fraction by Calmar on real data
    f_best_cal = max(frac_results, key=lambda f: frac_results[f]["calmar"])

    # Best vol target by Calmar on real data
    vt_best = max(vol_results, key=lambda v: vol_results[v]["calmar"])

    # Variants: (label, frac_or_None, vol_target_or_None)
    variants = [
        ("f=1.00",   1.00,   None),
        ("f=0.50",   0.50,   None),
        ("f=0.30",   0.30,   None),
        ("f=0.20",   0.20,   None),
        (f"f=Kelly({f_kelly:.2f})", f_kelly, None),
        (f"f=½K({f_half:.2f})",     f_half,  None),
        (f"f=¼K({f_qtr:.2f})",      f_qtr,   None),
        (f"vol={vt_best:.0%}",       None,    vt_best),
        ("vol=20%",  None, 0.20),
        ("vol=30%",  None, 0.30),
    ]

    # Remove duplicates (by label)
    seen = set()
    unique_variants = []
    for label, f, vt in variants:
        key = f"{f}_{vt}"
        if key not in seen:
            seen.add(key)
            unique_variants.append((label, f, vt))
    variants = unique_variants

    print(f"\n  Testing {len(variants)} variants on {N_BOOT} bootstrap paths:")
    for label, f, vt in variants:
        if vt is not None:
            print(f"    {label} (vol-target={vt:.0%})")
        else:
            print(f"    {label} (fixed fraction={f:.3f})")

    # Prepare data
    cr, hr, lr, vol, tbr = make_ratios(cl, hi, lo, vo, tb)
    n_trans = len(cl) - 1
    p0 = cl[0]
    rng = np.random.default_rng(SEED)

    metrics_list = ["cagr", "mdd", "sharpe", "calmar", "geo_growth", "min_nav_pct"]
    boot = {label: {m: [] for m in metrics_list} for label, _, _ in variants}

    t0 = time.time()
    for b in range(N_BOOT):
        if (b + 1) % 200 == 0 or b == 0:
            el = time.time() - t0
            rate = (b + 1) / el if el > 0 else 1
            eta = (N_BOOT - b - 1) / rate
            print(f"    {b+1:5d}/{N_BOOT}  ({el:.0f}s, ~{eta:.0f}s left)")

        # Generate path
        c, h, l, v, t = gen_path(cr, hr, lr, vol, tbr, n_trans, BLKSZ, p0, rng)
        ef, es, at, vd = compute_ind(c, h, l, v, t)
        rv = compute_rolling_vol(c)

        # Run all variants
        for label, frac_val, vt in variants:
            if vt is not None:
                r = sim_sized(c, ef, es, at, vd, wi, vol_target=vt, rvol=rv)
            else:
                r = sim_sized(c, ef, es, at, vd, wi, frac=frac_val)
            for m in metrics_list:
                boot[label][m].append(r[m])

    el = time.time() - t0
    print(f"\n  Done: {el:.1f}s ({N_BOOT / el:.1f} paths/sec)")

    # Convert to numpy
    for label in boot:
        for m in metrics_list:
            boot[label][m] = np.array(boot[label][m])

    return boot, variants


def analyze_bootstrap(boot, variants):
    """Print bootstrap distributions and paired comparisons."""

    metrics_list = ["cagr", "mdd", "sharpe", "calmar", "geo_growth", "min_nav_pct"]
    base_label = "f=1.00"

    # ── Distributions ──
    print("\n" + "-" * 70)
    print("BOOTSTRAP DISTRIBUTIONS")
    print("-" * 70)

    for label, _, _ in variants:
        print(f"\n  ── {label} ──")
        for m in metrics_list:
            a = boot[label][m]
            pct = np.percentile(a, [5, 25, 50, 75, 95])
            print(f"    {m:12s}  med={pct[2]:+8.2f}  "
                  f"[p5={pct[0]:+7.2f}, p95={pct[4]:+7.2f}]")

    # ── Robustness ──
    print("\n" + "-" * 70)
    print("ROBUSTNESS COMPARISON")
    print("-" * 70)
    print(f"\n  {'variant':>20s}  {'P(CAGR>0)':>10s}  {'P(MDD<30)':>10s}  "
          f"{'medCAGR':>8s}  {'medMDD':>7s}  {'medCalm':>8s}  {'medMinNAV':>9s}")
    print("  " + "-" * 80)

    for label, _, _ in variants:
        cg = boot[label]["cagr"]
        md = boot[label]["mdd"]
        cm = boot[label]["calmar"]
        mn = boot[label]["min_nav_pct"]
        print(f"  {label:>20s}  {np.mean(cg>0)*100:9.1f}%  "
              f"{np.mean(md<30)*100:9.1f}%  "
              f"{np.median(cg):+7.1f}%  {np.median(md):6.1f}%  "
              f"{np.median(cm):8.3f}  {np.median(mn):8.1f}%")

    # ── Paired tests vs baseline ──
    print("\n" + "-" * 70)
    print(f"PAIRED TESTS vs {base_label}")
    print("-" * 70)
    print("  P(better) > 97.5% ≈ significant at α=0.05 (one-sided).\n")

    for label, _, _ in variants:
        if label == base_label:
            continue

        print(f"  ── {label} vs {base_label} ──")

        # CAGR: higher is better
        d_cagr = boot[label]["cagr"] - boot[base_label]["cagr"]
        ci = np.percentile(d_cagr, [2.5, 97.5])
        print(f"    ΔCAGR     mean={d_cagr.mean():+7.2f}  "
              f"P(higher)={np.mean(d_cagr>0)*100:5.1f}%  "
              f"CI=[{ci[0]:+.2f}, {ci[1]:+.2f}]")

        # MDD: lower is better → test base - variant > 0
        d_mdd = boot[base_label]["mdd"] - boot[label]["mdd"]
        ci = np.percentile(d_mdd, [2.5, 97.5])
        print(f"    ΔMDD(red) mean={d_mdd.mean():+7.2f}  "
              f"P(lower) ={np.mean(d_mdd>0)*100:5.1f}%  "
              f"CI=[{ci[0]:+.2f}, {ci[1]:+.2f}]")

        # Calmar: higher is better
        d_cal = boot[label]["calmar"] - boot[base_label]["calmar"]
        ci = np.percentile(d_cal, [2.5, 97.5])
        print(f"    ΔCalmar   mean={d_cal.mean():+7.3f}  "
              f"P(higher)={np.mean(d_cal>0)*100:5.1f}%  "
              f"CI=[{ci[0]:+.3f}, {ci[1]:+.3f}]")

        # Sharpe: higher is better
        d_sh = boot[label]["sharpe"] - boot[base_label]["sharpe"]
        ci = np.percentile(d_sh, [2.5, 97.5])
        print(f"    ΔSharpe   mean={d_sh.mean():+7.3f}  "
              f"P(higher)={np.mean(d_sh>0)*100:5.1f}%  "
              f"CI=[{ci[0]:+.3f}, {ci[1]:+.3f}]")

        # Min NAV: higher is better
        d_mn = boot[label]["min_nav_pct"] - boot[base_label]["min_nav_pct"]
        ci = np.percentile(d_mn, [2.5, 97.5])
        print(f"    ΔMinNAV   mean={d_mn.mean():+7.2f}  "
              f"P(higher)={np.mean(d_mn>0)*100:5.1f}%  "
              f"CI=[{ci[0]:+.2f}, {ci[1]:+.2f}]")
        print()


# ═══════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 70)
    print("HƯỚNG A: POSITION SIZING ANALYSIS")
    print("=" * 70)
    print(f"  Period: {START} → {END}   Warmup: {WARMUP}d")
    print(f"  Cost: harsh ({COST.round_trip_bps:.0f} bps RT)")
    print(f"  Bootstrap: {N_BOOT} paths, block={BLKSZ}")

    print("\nLoading data...")
    cl, hi, lo, vo, tb, wi, n = load_arrays()
    print(f"  {n} H4 bars, warmup idx={wi}, trading={n-wi} bars")

    # Part A1: Kelly
    kelly_info = run_kelly(cl, hi, lo, vo, tb, wi)

    # Part A2: Fixed Fraction Sweep
    frac_results, all_fracs = run_fraction_sweep(cl, hi, lo, vo, tb, wi, kelly_info)

    # Part A3: Vol Targeting
    vol_results = run_vol_targeting(cl, hi, lo, vo, tb, wi)

    # Part A4: Bootstrap
    boot, variants = run_bootstrap(cl, hi, lo, vo, tb, wi,
                                   kelly_info, frac_results, vol_results)
    analyze_bootstrap(boot, variants)

    # ── Save ──
    outdir = Path(__file__).resolve().parent / "results"
    outdir.mkdir(exist_ok=True)

    output = {
        "kelly": {
            "n_trades": kelly_info["n_trades"],
            "win_rate": kelly_info["win_rate"],
            "payoff_ratio": kelly_info["payoff_ratio"],
            "bernoulli_kelly": kelly_info["bernoulli_kelly"],
            "empirical_kelly": kelly_info["empirical_kelly"],
            "half_kelly": kelly_info["half_kelly"],
            "quarter_kelly": kelly_info["quarter_kelly"],
        },
        "fraction_sweep": {
            str(f): {k: v for k, v in r.items()} for f, r in frac_results.items()
        },
        "vol_targeting": {
            str(v): {k: val for k, val in r.items()} for v, r in vol_results.items()
        },
        "bootstrap": {},
    }

    metrics_list = ["cagr", "mdd", "sharpe", "calmar", "geo_growth", "min_nav_pct"]
    for label, _, _ in variants:
        output["bootstrap"][label] = {}
        for m in metrics_list:
            a = boot[label][m]
            pct = np.percentile(a, [5, 25, 50, 75, 95]).tolist()
            output["bootstrap"][label][m] = {
                "mean": round(float(a.mean()), 4),
                "std": round(float(a.std()), 4),
                "p5": round(pct[0], 4), "p25": round(pct[1], 4),
                "p50": round(pct[2], 4), "p75": round(pct[3], 4),
                "p95": round(pct[4], 4),
            }

    outpath = outdir / "position_sizing.json"
    with open(outpath, "w") as f:
        json.dump(output, f, indent=2, default=str)

    print(f"\n  Results saved → {outpath}")
    print("\n" + "=" * 70)
    print("DONE")
    print("=" * 70)
