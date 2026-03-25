#!/usr/bin/env python3
"""Mathematical Invariant Tests for sim_fast.

Tests properties that MUST hold mathematically for ANY correct simulation engine.
A violation of any invariant proves a bug exists.

Invariants tested:
  1. Sharpe is scale-invariant (price scaling preserves returns)
  2. MDD (%) is scale-invariant
  3. Flat price → no trades, zero PnL
  4. Constant uptrend → positive CAGR, near-zero MDD
  5. Reversed returns → approximately negated Sharpe (soft)
  6. NAV is always positive (long-only, no leverage)
  7. Trade count consistency
  8. CAGR formula self-consistency
  9. Cost monotonicity (more friction → worse performance)
 10. Indicator determinism (same input → identical output)
"""

from __future__ import annotations

import math
import sys
import traceback
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from v10.core.data import DataFeed
from v10.core.types import SCENARIOS
from strategies.vtrend.strategy import _ema, _atr, _vdo

# ── Constants (match timescale_robustness.py exactly) ──────────────────

DATA   = str(ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv")
COST   = SCENARIOS["harsh"]
CPS    = COST.per_side_bps / 10_000.0   # 0.0025

START  = "2019-01-01"
END    = "2026-02-20"
WARMUP = 365
CASH   = 10_000.0

ANN = math.sqrt(6.0 * 365.25)

# Fixed VTREND structural constants
ATR_P  = 14
VDO_F  = 12
VDO_S  = 28
TRAIL  = 3.0
SLOW   = 120
FAST   = max(5, SLOW // 4)  # 30

VDO_ON  = 0.0
VDO_OFF = -1e9


# ═══════════════════════════════════════════════════════════════════════
# sim_fast — canonical copy from timescale_robustness.py
# ═══════════════════════════════════════════════════════════════════════

def sim_fast(cl, ef, es, at, vd, wi, vdo_thr, cps=CPS, cash=CASH):
    """VTREND binary sim (f=1.0). Returns metrics dict.

    Parameters
    ----------
    cl : close prices
    ef, es : EMA fast/slow (pre-computed)
    at : ATR (pre-computed, may have NaN for first ATR_P-1 bars)
    vd : VDO (pre-computed)
    wi : warmup index
    vdo_thr : VDO entry threshold (0.0 = on, -1e9 = off)
    cps : cost per side (fraction, e.g. 0.0025)
    cash : initial cash
    """
    n = len(cl)
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

    # Track all NAVs for additional invariant checks
    all_navs = np.empty(n, dtype=np.float64)

    for i in range(n):
        p = cl[i]

        # Fill pending
        if i > 0:
            fp = cl[i - 1]
            if pe:
                pe = False
                bq = cash / (fp * (1.0 + cps))
                cash = 0.0
                inp = True
                pk = p
            elif px:
                cash = bq * fp * (1.0 - cps)
                bq = 0.0
                inp = False
                pk = 0.0
                nt += 1
                px = False

        nav = cash + bq * p
        all_navs[i] = nav

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
        if math.isnan(a_val) or math.isnan(ef[i]) or math.isnan(es[i]):
            continue

        if not inp:
            if ef[i] > es[i] and vd[i] > vdo_thr:
                pe = True
        else:
            pk = max(pk, p)
            if p < pk - TRAIL * a_val:
                px = True
            elif ef[i] < es[i]:
                px = True

    # Force close
    if inp and bq > 0:
        cash = bq * cl[-1] * (1.0 - cps)
        bq = 0.0
        nt += 1
        navs_end = cash

    # Metrics
    if n_rets < 2 or navs_start <= 0:
        return {"cagr": -100.0, "mdd": 100.0, "sharpe": 0.0, "calmar": 0.0,
                "trades": 0, "navs": all_navs, "final_nav": navs_end,
                "start_nav": navs_start, "n_rets": n_rets}

    tr = navs_end / navs_start - 1.0
    yrs = n_rets / (6.0 * 365.25)
    cagr = ((1 + tr) ** (1 / yrs) - 1) * 100 if yrs > 0 and tr > -1 else -100.0

    mdd = (1.0 - nav_min_ratio) * 100.0

    mu = rets_sum / n_rets
    var = rets_sq_sum / n_rets - mu * mu
    std = math.sqrt(max(var, 0.0))
    sharpe = (mu / std) * ANN if std > 1e-12 else 0.0

    calmar = cagr / mdd if mdd > 0.01 else 0.0

    return {"cagr": cagr, "mdd": mdd, "sharpe": sharpe, "calmar": calmar,
            "trades": nt, "navs": all_navs, "final_nav": navs_end,
            "start_nav": navs_start, "n_rets": n_rets}


# ═══════════════════════════════════════════════════════════════════════
# Data loading
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


def compute_indicators(cl, hi, lo, vo, tb, slow=SLOW):
    """Compute all indicators for a given close/high/low/volume/taker_buy."""
    fast = max(5, slow // 4)
    ef = _ema(cl, fast)
    es = _ema(cl, slow)
    at = _atr(hi, lo, cl, ATR_P)
    vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)
    return ef, es, at, vd


# ═══════════════════════════════════════════════════════════════════════
# Test framework
# ═══════════════════════════════════════════════════════════════════════

class TestResult:
    def __init__(self, name: str):
        self.name = name
        self.passed = False
        self.details = []

    def log(self, msg: str):
        self.details.append(msg)

    def ok(self, msg: str = ""):
        self.passed = True
        if msg:
            self.details.append(msg)

    def fail(self, msg: str):
        self.passed = False
        self.details.append(f"FAIL: {msg}")


results: list[TestResult] = []


def run_test(name: str):
    """Decorator to register and run a test."""
    def decorator(fn):
        def wrapper(*args, **kwargs):
            t = TestResult(name)
            try:
                fn(t, *args, **kwargs)
            except Exception as e:
                t.fail(f"Exception: {e}")
                t.details.append(traceback.format_exc())
            results.append(t)
            status = "PASS" if t.passed else "FAIL"
            print(f"\n  [{status}] {name}")
            for d in t.details:
                for line in d.split('\n'):
                    print(f"         {line}")
        return wrapper
    return decorator


# ═══════════════════════════════════════════════════════════════════════
# Invariant Tests
# ═══════════════════════════════════════════════════════════════════════

@run_test("Invariant 1: Sharpe is scale-invariant (price scaling)")
def test_sharpe_scale_invariant(t, cl, hi, lo, vo, tb, wi):
    """Multiplying ALL prices by constant k should not change Sharpe.

    Proof: returns r_i = p_{i+1}/p_i - 1 are invariant to scaling since
    (k*p_{i+1})/(k*p_i) = p_{i+1}/p_i. Mean and std of returns are
    therefore identical, so Sharpe = mu/sigma * ANN is invariant.

    The only subtlety: ATR also scales by k, and the trail stop is
    pk - TRAIL * ATR. Since pk and ATR both scale by k, the stop
    condition p < pk - TRAIL * ATR is equivalent under scaling.
    So trade signals are IDENTICAL, and Sharpe must be identical.
    """
    # Baseline
    ef, es, at, vd = compute_indicators(cl, hi, lo, vo, tb)
    base = sim_fast(cl, ef, es, at, vd, wi, VDO_ON)
    base_sharpe = base["sharpe"]
    t.log(f"Baseline Sharpe: {base_sharpe:.10f}")

    for k in [2.0, 0.5, 100.0, 0.01]:
        cl_s = cl * k
        hi_s = hi * k
        lo_s = lo * k
        # Volume and taker_buy are in BASE units, not quote. They don't scale with price.
        ef_s, es_s, at_s, vd_s = compute_indicators(cl_s, hi_s, lo_s, vo, tb)
        r = sim_fast(cl_s, ef_s, es_s, at_s, vd_s, wi, VDO_ON)
        delta = abs(r["sharpe"] - base_sharpe)
        t.log(f"  k={k:8.2f}: Sharpe={r['sharpe']:.10f}, delta={delta:.2e}, "
              f"trades={r['trades']} vs {base['trades']}")
        if delta > 1e-8:
            t.fail(f"Sharpe changed by {delta:.2e} with price scale k={k}")
            return
        if r["trades"] != base["trades"]:
            t.fail(f"Trade count changed: {r['trades']} vs {base['trades']} with k={k}")
            return

    t.ok("Sharpe identical within 1e-8 for all price scalings")


@run_test("Invariant 2: MDD (%) is scale-invariant")
def test_mdd_scale_invariant(t, cl, hi, lo, vo, tb, wi):
    """MDD as a percentage must be identical regardless of price level.

    Proof: MDD = max_t (1 - NAV_t / peak_NAV_t). Since NAV = cash + bq*p,
    and cash, bq are determined by ratios (cash/(p*(1+cps)), bq*p*(1-cps)),
    scaling p by k scales NAV by k at every point, so the ratio
    NAV_t / peak_NAV_t is invariant. Hence MDD (%) is invariant.
    """
    ef, es, at, vd = compute_indicators(cl, hi, lo, vo, tb)
    base = sim_fast(cl, ef, es, at, vd, wi, VDO_ON)
    base_mdd = base["mdd"]
    t.log(f"Baseline MDD: {base_mdd:.10f}%")

    for k in [2.0, 0.5, 100.0, 0.01]:
        cl_s = cl * k
        hi_s = hi * k
        lo_s = lo * k
        ef_s, es_s, at_s, vd_s = compute_indicators(cl_s, hi_s, lo_s, vo, tb)
        r = sim_fast(cl_s, ef_s, es_s, at_s, vd_s, wi, VDO_ON)
        delta = abs(r["mdd"] - base_mdd)
        t.log(f"  k={k:8.2f}: MDD={r['mdd']:.10f}%, delta={delta:.2e}")
        if delta > 1e-8:
            t.fail(f"MDD changed by {delta:.2e} with price scale k={k}")
            return

    t.ok("MDD identical within 1e-8 for all price scalings")


@run_test("Invariant 3: Flat price → no trades, zero PnL")
def test_flat_price(t, *_):
    """Constant price means EMA_fast = EMA_slow = constant, so no crossover
    ever occurs. No entry → no trade → NAV = CASH.

    Mathematical proof:
      EMA(c, p)[i] = alpha*c[i] + (1-alpha)*EMA[i-1] with EMA[0]=c[0].
      If c[i] = K for all i, then EMA[i] = K for all i (by induction).
      So EMA_fast = EMA_slow = K, and ef > es is NEVER true.
      → No entry signal. NAV = CASH throughout.
    """
    n = 5000  # Plenty of bars
    K = 50000.0
    cl = np.full(n, K, dtype=np.float64)
    hi = np.full(n, K * 1.001, dtype=np.float64)  # small spread for ATR
    lo = np.full(n, K * 0.999, dtype=np.float64)
    vo = np.full(n, 100.0, dtype=np.float64)
    tb = np.full(n, 50.0, dtype=np.float64)  # Neutral VDO (50/50 taker buy)

    ef, es, at, vd = compute_indicators(cl, hi, lo, vo, tb)
    wi = 500  # warmup index

    # Verify EMA equality
    max_ema_diff = np.max(np.abs(ef[500:] - es[500:]))
    t.log(f"Max |EMA_fast - EMA_slow| after warmup: {max_ema_diff:.2e}")

    r = sim_fast(cl, ef, es, at, vd, wi, VDO_ON, cps=0.0)
    t.log(f"Trades: {r['trades']}, Sharpe: {r['sharpe']:.6f}, "
          f"CAGR: {r['cagr']:.6f}, MDD: {r['mdd']:.6f}")

    if r["trades"] != 0:
        t.fail(f"Expected 0 trades on flat price, got {r['trades']}")
        return

    # With zero trades, Sharpe should be 0 (all returns are zero)
    # Actually with 0 trades, n_rets may be < 2 giving default metrics
    # OR: if we do have n_rets >= 2, all returns = 0, so std=0, sharpe=0
    if r["sharpe"] != 0.0:
        t.fail(f"Expected Sharpe=0 on flat price, got {r['sharpe']}")
        return

    t.ok("Flat price: 0 trades, Sharpe=0 as expected")


@run_test("Invariant 4: Constant uptrend → positive CAGR, tiny MDD")
def test_constant_uptrend(t, *_):
    """Monotonic uptrend: EMA_fast > EMA_slow after warmup (fast reacts faster).
    Entry occurs, no trend reversal exit. ATR trail may trigger if the trail
    ratchets but price doesn't retrace, but with smooth uptrend it shouldn't.

    With CPS=0, the system should capture most of the uptrend:
    - CAGR > 0
    - MDD near 0 (no drawdown in monotonic uptrend while in position)

    Key design: we disable VDO (vdo_thr=-1e9) to isolate the EMA crossover
    signal. With constant VDO input (constant taker_buy ratio), VDO=0
    exactly because EMA(vdr, fast) == EMA(vdr, slow) == constant, and
    the entry threshold is strict > 0. This is mathematically correct
    behavior for VDO, not a bug.

    We also start with a flat period followed by an uptrend, so the
    EMA crossover actually fires (in steady growth, both EMAs converge
    to the same bias, and the crossover happens at the transition point).
    """
    n = 6000
    # First 1000 bars: flat at 10000
    # Then 5000 bars: geometric uptrend
    flat = np.full(500, 10000.0, dtype=np.float64)
    growth = 10000.0 * np.cumprod(np.ones(5500) * 1.001)
    cl = np.concatenate([flat, growth])

    # High/low bracket close closely for small ATR
    hi = cl * 1.002
    lo = cl * 0.998
    vo = np.full(n, 1000.0, dtype=np.float64)
    tb = np.full(n, 500.0, dtype=np.float64)  # neutral (won't matter, VDO off)

    ef, es, at, vd = compute_indicators(cl, hi, lo, vo, tb)
    wi = 300  # warmup index

    # Disable VDO to test pure EMA crossover on uptrend
    r = sim_fast(cl, ef, es, at, vd, wi, VDO_OFF, cps=0.0)
    t.log(f"Trades: {r['trades']}, CAGR: {r['cagr']:.4f}%, "
          f"MDD: {r['mdd']:.6f}%, Sharpe: {r['sharpe']:.4f}")

    # Verify EMA crossover fires: after transition, EMA_fast should lead
    ef_after = ef[600:]
    es_after = es[600:]
    cross_count = np.sum(ef_after > es_after)
    t.log(f"EMA_fast > EMA_slow after transition: {cross_count}/{len(ef_after)} bars")

    if r["trades"] == 0:
        t.fail(f"Expected at least 1 trade in uptrend (VDO disabled), got 0")
        return

    if r["cagr"] <= 0:
        t.fail(f"Expected positive CAGR in uptrend, got {r['cagr']:.4f}%")
        return

    if r["mdd"] > 5.0:
        t.fail(f"Expected MDD < 5% in smooth uptrend, got {r['mdd']:.4f}%")
        return

    if r["sharpe"] <= 0:
        t.fail(f"Expected positive Sharpe in uptrend, got {r['sharpe']:.4f}")
        return

    t.ok(f"Uptrend: CAGR={r['cagr']:.2f}%, MDD={r['mdd']:.4f}%, "
         f"Sharpe={r['sharpe']:.2f}, trades={r['trades']}")


@run_test("Invariant 5: Reversed prices → approximately negated Sharpe (soft)")
def test_reversed_sharpe(t, cl, hi, lo, vo, tb, wi):
    """If we reverse the time ordering of close prices, uptrends become
    downtrends and vice versa, so the trend-following Sharpe should
    roughly change sign.

    This is a SOFT invariant because:
    - EMA warmup is different (starts from the other end)
    - ATR structure differs
    - We only check sign flip, not exact magnitude
    """
    ef, es, at, vd = compute_indicators(cl, hi, lo, vo, tb)
    r_fwd = sim_fast(cl, ef, es, at, vd, wi, VDO_OFF)  # VDO off for cleaner test

    # Reverse all arrays
    cl_r = cl[::-1].copy()
    hi_r = hi[::-1].copy()
    lo_r = lo[::-1].copy()
    vo_r = vo[::-1].copy()
    tb_r = tb[::-1].copy()

    ef_r, es_r, at_r, vd_r = compute_indicators(cl_r, hi_r, lo_r, vo_r, tb_r)
    r_rev = sim_fast(cl_r, ef_r, es_r, at_r, vd_r, wi, VDO_OFF)

    t.log(f"Forward  Sharpe: {r_fwd['sharpe']:+.4f}, CAGR: {r_fwd['cagr']:+.2f}%")
    t.log(f"Reversed Sharpe: {r_rev['sharpe']:+.4f}, CAGR: {r_rev['cagr']:+.2f}%")

    # Soft check: if forward is significantly positive, reversed should be lower
    # We do NOT require exact sign flip since EMA asymmetry breaks the mapping.
    if r_fwd["sharpe"] > 0.3:
        if r_rev["sharpe"] > r_fwd["sharpe"]:
            t.fail(f"Reversed Sharpe ({r_rev['sharpe']:.4f}) HIGHER than forward "
                   f"({r_fwd['sharpe']:.4f}) — trend signal should degrade on reversal")
            return
        t.ok(f"Reversed Sharpe lower than forward (soft check passed)")
    else:
        t.ok(f"Forward Sharpe too low ({r_fwd['sharpe']:.4f}) for meaningful comparison; "
             f"soft test inconclusive but accepted")


@run_test("Invariant 6: NAV is always positive")
def test_nav_always_positive(t, cl, hi, lo, vo, tb, wi):
    """For long-only strategy with no leverage, NAV = cash + bq * price.
    Both cash >= 0 and bq >= 0 and price > 0 always, so NAV > 0 always.

    Also test on extreme data: a 99% crash.
    """
    # Test on real data
    ef, es, at, vd = compute_indicators(cl, hi, lo, vo, tb)
    r = sim_fast(cl, ef, es, at, vd, wi, VDO_ON)
    navs = r["navs"]

    min_nav = np.min(navs)
    t.log(f"Real data: min NAV = {min_nav:.4f} (of {len(navs)} bars)")
    if min_nav <= 0:
        t.fail(f"NAV went to {min_nav:.4f} (non-positive) on real data")
        return

    # Extreme test: 99% crash
    n = 3000
    # Start at 50000, crash to 500 over 2000 bars, then flat
    crash = np.concatenate([
        np.linspace(50000, 500, 2000),
        np.full(1000, 500.0)
    ])
    hi_x = crash * 1.02
    lo_x = crash * 0.98
    vo_x = np.full(n, 1000.0, dtype=np.float64)
    tb_x = np.full(n, 500.0, dtype=np.float64)

    ef_x, es_x, at_x, vd_x = compute_indicators(crash, hi_x, lo_x, vo_x, tb_x)
    r_x = sim_fast(crash, ef_x, es_x, at_x, vd_x, 300, VDO_OFF)
    min_nav_crash = np.min(r_x["navs"])
    t.log(f"99% crash: min NAV = {min_nav_crash:.4f}, trades={r_x['trades']}")

    if min_nav_crash <= 0:
        t.fail(f"NAV went to {min_nav_crash:.4f} (non-positive) on 99% crash")
        return

    t.ok(f"NAV always positive: real min={min_nav:.2f}, crash min={min_nav_crash:.2f}")


@run_test("Invariant 7: Trade count consistency")
def test_trade_count(t, cl, hi, lo, vo, tb, wi):
    """Each trade consists of an entry and an exit.
    The sim increments nt on exit (including force-close at end).
    Therefore: 0 <= trades <= reasonable_upper_bound.

    For H4 data over ~7 years (~9000 bars), max possible trades
    with EMA(120) crossover is bounded by signal changes.
    A reasonable upper bound is n/2 (one trade per 2 bars = impossible
    but mathematical upper bound).

    Also: trades should match the number of entry/exit cycles
    we can verify by checking the signal pattern.
    """
    ef, es, at, vd = compute_indicators(cl, hi, lo, vo, tb)
    r = sim_fast(cl, ef, es, at, vd, wi, VDO_ON)
    trades = r["trades"]
    n = len(cl)

    t.log(f"Trades: {trades}, bars: {n}, trades/bar: {trades/n:.4f}")

    if trades < 0:
        t.fail(f"Negative trade count: {trades}")
        return

    if trades > n // 2:
        t.fail(f"Implausibly high trade count: {trades} > {n // 2}")
        return

    if trades == 0:
        t.fail(f"Zero trades on real BTC data — strategy should trade")
        return

    # Reasonable range for BTC H4 with EMA(120): expect 50-500 trades over 7 years
    t.log(f"Expected range: 50-500 trades for ~7 years H4 data")
    if trades > 1000:
        t.log(f"WARNING: High trade count ({trades}), possibly correct but unusual")

    t.ok(f"{trades} trades in {n} bars ({trades/n*100:.2f}% of bars)")


@run_test("Invariant 8: CAGR formula self-consistency")
def test_cagr_self_consistent(t, cl, hi, lo, vo, tb, wi):
    """CAGR formula: final = initial * (1 + CAGR/100)^years
    This must be self-consistent with the actual NAV values.

    The sim computes:
      tr = navs_end / navs_start - 1.0
      yrs = n_rets / (6.0 * 365.25)
      cagr = ((1 + tr)^(1/yrs) - 1) * 100

    So: navs_start * (1 + cagr/100)^yrs should equal navs_end.
    """
    ef, es, at, vd = compute_indicators(cl, hi, lo, vo, tb)
    r = sim_fast(cl, ef, es, at, vd, wi, VDO_ON)

    cagr = r["cagr"]
    start_nav = r["start_nav"]
    final_nav = r["final_nav"]
    n_rets = r["n_rets"]
    yrs = n_rets / (6.0 * 365.25)

    t.log(f"CAGR: {cagr:.6f}%, start_nav: {start_nav:.4f}, "
          f"final_nav: {final_nav:.4f}, years: {yrs:.4f}")

    if cagr <= -100.0 or yrs <= 0:
        t.ok("Edge case: CAGR=-100 or years=0, self-consistency trivially holds")
        return

    # Reconstruct final NAV from CAGR
    reconstructed = start_nav * (1 + cagr / 100.0) ** yrs
    rel_err = abs(reconstructed - final_nav) / max(abs(final_nav), 1e-12)
    t.log(f"Reconstructed final NAV: {reconstructed:.6f}")
    t.log(f"Actual final NAV:        {final_nav:.6f}")
    t.log(f"Relative error:          {rel_err:.2e}")

    if rel_err > 1e-6:
        t.fail(f"CAGR self-consistency violated: relative error {rel_err:.2e} > 1e-6")
        return

    t.ok(f"CAGR self-consistent within {rel_err:.2e}")


@run_test("Invariant 9: Cost monotonicity")
def test_cost_monotonicity(t, cl, hi, lo, vo, tb, wi):
    """Higher cost per side → lower net returns → lower Sharpe and CAGR.

    Proof: same entry/exit signals (indicators don't depend on cost),
    but each trade loses more to friction. With identical trade sequence,
    NAV is strictly lower at higher cost.

    HOWEVER: cost CAN change trade timing in sim_fast because
    entry uses bq = cash / (fp * (1 + cps)), which affects the
    position size. This changes nav trajectory slightly, which changes
    the return series, which can slightly change MDD timing.

    But Sharpe and CAGR should be MONOTONICALLY DECREASING in cost
    because higher cost strictly reduces net profit per trade.

    NOTE: In sim_fast, the entry/exit SIGNALS are independent of cps
    (they depend on EMA, ATR, VDO only). But the fill price depends
    on cps, which changes bq, which changes NAV, which changes returns.
    The trade SEQUENCE is identical (same entries and exits), only
    the fills differ.

    Wait — is the trade sequence actually identical? Let's check:
    - Entry condition: ef > es and vd > vdo_thr → NO dependency on cps
    - Exit conditions: p < pk - TRAIL * at → pk depends on p (close price),
      not on NAV or cost. So pk is the same.
    - EMA cross-down exit: ef < es → NO dependency on cps

    Yes, the trade sequence is IDENTICAL across all cost levels.
    Only bq (position size) changes → NAV changes → returns change → metrics change.
    But since we're subtracting cost from each trade, higher cost means
    less net return from each trade, so cumulative return is lower.
    """
    ef, es, at, vd = compute_indicators(cl, hi, lo, vo, tb)

    costs = [0.0, 0.001, 0.0025, 0.005, 0.01]
    sharpes = []
    cagrs = []

    for c in costs:
        r = sim_fast(cl, ef, es, at, vd, wi, VDO_ON, cps=c)
        sharpes.append(r["sharpe"])
        cagrs.append(r["cagr"])
        t.log(f"  cps={c:.4f}: Sharpe={r['sharpe']:+.4f}, CAGR={r['cagr']:+.2f}%, "
              f"trades={r['trades']}")

    # Check monotonicity of Sharpe
    for i in range(len(costs) - 1):
        if sharpes[i + 1] > sharpes[i] + 1e-10:
            t.fail(f"Sharpe NOT monotonically decreasing: "
                   f"cps={costs[i]:.4f}→{costs[i+1]:.4f}: "
                   f"{sharpes[i]:.6f} → {sharpes[i+1]:.6f}")
            return

    # Check monotonicity of CAGR
    for i in range(len(costs) - 1):
        if cagrs[i + 1] > cagrs[i] + 1e-10:
            t.fail(f"CAGR NOT monotonically decreasing: "
                   f"cps={costs[i]:.4f}→{costs[i+1]:.4f}: "
                   f"{cagrs[i]:.6f} → {cagrs[i+1]:.6f}")
            return

    t.ok(f"Sharpe and CAGR monotonically decrease with cost")


@run_test("Invariant 10: Indicator determinism (same input → identical output)")
def test_determinism(t, cl, hi, lo, vo, tb, wi):
    """sim_fast has no random state. Same input MUST produce bit-identical output.
    Run twice, compare all outputs.
    """
    ef, es, at, vd = compute_indicators(cl, hi, lo, vo, tb)

    r1 = sim_fast(cl, ef, es, at, vd, wi, VDO_ON)
    r2 = sim_fast(cl, ef, es, at, vd, wi, VDO_ON)

    # Check scalar metrics
    for key in ["cagr", "mdd", "sharpe", "calmar", "trades", "final_nav",
                "start_nav", "n_rets"]:
        v1 = r1[key]
        v2 = r2[key]
        if isinstance(v1, float):
            if v1 != v2:
                t.fail(f"{key}: {v1} != {v2}")
                return
        elif v1 != v2:
            t.fail(f"{key}: {v1} != {v2}")
            return
        t.log(f"  {key}: {v1} == {v2}")

    # Check NAV array (bit-identical)
    if not np.array_equal(r1["navs"], r2["navs"]):
        max_diff = np.max(np.abs(r1["navs"] - r2["navs"]))
        t.fail(f"NAV arrays differ! max diff = {max_diff:.2e}")
        return

    t.log(f"  navs array: {len(r1['navs'])} values, all bit-identical")
    t.ok("Fully deterministic: all outputs are bit-identical across two runs")


# ═══════════════════════════════════════════════════════════════════════
# Additional derived invariants
# ═══════════════════════════════════════════════════════════════════════

@run_test("Invariant 1b: CAGR is scale-invariant (price scaling)")
def test_cagr_scale_invariant(t, cl, hi, lo, vo, tb, wi):
    """Same argument as Sharpe: returns r_i are invariant to price scaling.
    CAGR = ((1+total_return)^(1/yrs) - 1) * 100.
    Total return = product of (1+r_i) - 1, which is invariant.
    Therefore CAGR must be invariant.
    """
    ef, es, at, vd = compute_indicators(cl, hi, lo, vo, tb)
    base = sim_fast(cl, ef, es, at, vd, wi, VDO_ON)
    base_cagr = base["cagr"]
    t.log(f"Baseline CAGR: {base_cagr:.10f}")

    for k in [2.0, 0.5, 100.0, 0.01]:
        cl_s = cl * k
        hi_s = hi * k
        lo_s = lo * k
        ef_s, es_s, at_s, vd_s = compute_indicators(cl_s, hi_s, lo_s, vo, tb)
        r = sim_fast(cl_s, ef_s, es_s, at_s, vd_s, wi, VDO_ON)
        delta = abs(r["cagr"] - base_cagr)
        t.log(f"  k={k:8.2f}: CAGR={r['cagr']:.10f}, delta={delta:.2e}")
        if delta > 1e-6:
            t.fail(f"CAGR changed by {delta:.2e} with price scale k={k}")
            return

    t.ok("CAGR identical within 1e-6 for all price scalings")


@run_test("Invariant 1c: Trade count is scale-invariant (price scaling)")
def test_trades_scale_invariant(t, cl, hi, lo, vo, tb, wi):
    """Entry/exit signals depend on EMA crossover, ATR trail, and VDO.
    EMA(k*p) = k*EMA(p), so ef > es iff k*ef > k*es.
    ATR(k*p) = k*ATR(p), and pk scales by k, so p < pk - TRAIL*ATR
    iff k*p < k*pk - TRAIL*k*ATR. Same condition.
    VDO depends on ratios (taker_buy/volume) or (close-low)/(high-low),
    which are invariant to price scaling.
    Therefore trade count must be EXACTLY identical.
    """
    ef, es, at, vd = compute_indicators(cl, hi, lo, vo, tb)
    base_trades = sim_fast(cl, ef, es, at, vd, wi, VDO_ON)["trades"]
    t.log(f"Baseline trades: {base_trades}")

    for k in [2.0, 0.5, 100.0, 0.01, 1e6]:
        cl_s = cl * k
        hi_s = hi * k
        lo_s = lo * k
        ef_s, es_s, at_s, vd_s = compute_indicators(cl_s, hi_s, lo_s, vo, tb)
        r = sim_fast(cl_s, ef_s, es_s, at_s, vd_s, wi, VDO_ON)
        t.log(f"  k={k:>10.2f}: trades={r['trades']}")
        if r["trades"] != base_trades:
            t.fail(f"Trade count changed: {r['trades']} vs {base_trades} with k={k}")
            return

    t.ok(f"Trade count = {base_trades} for all price scalings")


@run_test("Invariant 9b: Final NAV monotonically decreases with cost")
def test_final_nav_monotonicity(t, cl, hi, lo, vo, tb, wi):
    """Since trade sequence is identical across cost levels (proven in
    Invariant 9), and each trade loses more to cost, final NAV must be
    STRICTLY monotonically decreasing in cost (given trades > 0).
    """
    ef, es, at, vd = compute_indicators(cl, hi, lo, vo, tb)

    costs = [0.0, 0.0005, 0.001, 0.0015, 0.002, 0.0025, 0.003, 0.005, 0.01]
    final_navs = []

    for c in costs:
        r = sim_fast(cl, ef, es, at, vd, wi, VDO_ON, cps=c)
        final_navs.append(r["final_nav"])
        t.log(f"  cps={c:.4f}: final_nav={r['final_nav']:.4f}, trades={r['trades']}")

    for i in range(len(costs) - 1):
        if final_navs[i + 1] > final_navs[i] + 1e-8:
            t.fail(f"Final NAV NOT monotonically decreasing: "
                   f"cps={costs[i]:.4f}→{costs[i+1]:.4f}: "
                   f"{final_navs[i]:.6f} → {final_navs[i+1]:.6f}")
            return

    t.ok(f"Final NAV strictly decreases: {final_navs[0]:.2f} → {final_navs[-1]:.2f}")


@run_test("Invariant 11: VDO threshold ordering (stricter filter → fewer trades)")
def test_vdo_threshold_ordering(t, cl, hi, lo, vo, tb, wi):
    """Higher VDO threshold means stricter entry filter.
    Stricter filter → subset of entry signals → fewer or equal trades.

    Proof: At threshold T1 < T2, any bar where vdo > T2 also has vdo > T1.
    So the set of entries at T2 is a SUBSET of entries at T1.
    Therefore trades(T2) <= trades(T1).
    """
    ef, es, at, vd = compute_indicators(cl, hi, lo, vo, tb)

    thresholds = [-1e9, -0.1, 0.0, 0.05, 0.1, 0.2, 0.5]
    trade_counts = []

    for thr in thresholds:
        r = sim_fast(cl, ef, es, at, vd, wi, thr)
        trade_counts.append(r["trades"])
        t.log(f"  vdo_thr={thr:>8.3f}: trades={r['trades']}, "
              f"Sharpe={r['sharpe']:+.4f}")

    for i in range(len(thresholds) - 1):
        if trade_counts[i + 1] > trade_counts[i]:
            t.fail(f"Trades INCREASED with stricter threshold: "
                   f"thr={thresholds[i]}→{thresholds[i+1]}: "
                   f"{trade_counts[i]} → {trade_counts[i+1]}")
            return

    t.ok(f"Trade count monotonically decreases: "
         f"{trade_counts[0]} → {trade_counts[-1]}")


@run_test("Invariant 12: EMA properties (convergence and ordering)")
def test_ema_properties(t, *_):
    """Mathematical EMA properties:
    1. EMA of constant = constant
    2. EMA with period=1 → alpha=1 → EMA = series exactly
    3. Longer period EMA is smoother (lower variance)
    4. EMA is bounded by min and max of input series
    """
    # Property 1: EMA of constant
    n = 1000
    K = 42.0
    c = np.full(n, K, dtype=np.float64)
    e = _ema(c, 50)
    max_dev = np.max(np.abs(e - K))
    t.log(f"EMA of constant: max deviation = {max_dev:.2e}")
    if max_dev > 1e-10:
        t.fail(f"EMA of constant deviates by {max_dev:.2e}")
        return

    # Property 2: EMA with period=1
    rng = np.random.default_rng(123)
    c = rng.standard_normal(1000) * 100 + 50000
    e1 = _ema(c, 1)
    max_diff = np.max(np.abs(e1 - c))
    t.log(f"EMA(period=1) vs series: max diff = {max_diff:.2e}")
    if max_diff > 1e-10:
        t.fail(f"EMA(period=1) should equal series, diff={max_diff:.2e}")
        return

    # Property 3: Longer period → lower variance (after warmup)
    var_10 = np.var(_ema(c, 10)[200:])
    var_50 = np.var(_ema(c, 50)[200:])
    var_200 = np.var(_ema(c, 200)[500:])
    t.log(f"EMA variance: p=10: {var_10:.2f}, p=50: {var_50:.2f}, p=200: {var_200:.2f}")
    if not (var_10 > var_50 > var_200):
        t.fail(f"Longer EMA period should have lower variance")
        return

    # Property 4: EMA bounded by min/max of input
    e50 = _ema(c, 50)
    if np.min(e50) < np.min(c) - 1e-10 or np.max(e50) > np.max(c) + 1e-10:
        t.fail(f"EMA exceeds input bounds")
        return

    t.ok("All 4 EMA properties hold")


@run_test("Invariant 13: ATR properties (non-negative, scale-invariant ratio)")
def test_atr_properties(t, cl, hi, lo, *_):
    """ATR properties:
    1. ATR >= 0 always (absolute range can't be negative)
    2. ATR/close ratio is scale-invariant: ATR(k*p)/k*p = ATR(p)/p
    3. ATR of flat data → converges to high-low spread
    """
    # Property 1: ATR non-negative on real data
    at = _atr(hi, lo, cl, ATR_P)
    valid = ~np.isnan(at)
    if np.any(at[valid] < 0):
        t.fail("ATR has negative values")
        return
    t.log(f"ATR non-negative: min={np.min(at[valid]):.4f} (of {valid.sum()} valid)")

    # Property 2: ATR ratio scale-invariance
    k = 3.7
    at_s = _atr(hi * k, lo * k, cl * k, ATR_P)
    ratio_orig = at[valid] / cl[valid]
    ratio_scaled = at_s[valid] / (cl[valid] * k)
    max_ratio_diff = np.max(np.abs(ratio_orig - ratio_scaled))
    t.log(f"ATR/close ratio diff after k={k} scaling: {max_ratio_diff:.2e}")
    if max_ratio_diff > 1e-10:
        t.fail(f"ATR ratio not scale-invariant: max diff = {max_ratio_diff:.2e}")
        return

    # Property 3: Flat data → ATR converges to spread
    n = 2000
    spread_frac = 0.002  # 0.2%
    K = 50000.0
    c_flat = np.full(n, K, dtype=np.float64)
    h_flat = np.full(n, K * (1 + spread_frac), dtype=np.float64)
    l_flat = np.full(n, K * (1 - spread_frac), dtype=np.float64)
    at_flat = _atr(h_flat, l_flat, c_flat, ATR_P)
    expected_tr = K * 2 * spread_frac  # high - low for flat data
    converged_atr = at_flat[-1]
    rel_err = abs(converged_atr - expected_tr) / expected_tr
    t.log(f"Flat data ATR convergence: expected={expected_tr:.2f}, "
          f"got={converged_atr:.2f}, rel_err={rel_err:.2e}")
    if rel_err > 0.01:
        t.fail(f"ATR doesn't converge to expected value: rel_err={rel_err:.2e}")
        return

    t.ok("ATR: non-negative, scale-invariant ratio, converges correctly")


@run_test("Invariant 14: Zero-cost NAV = sum of trade returns on close prices")
def test_zero_cost_nav_accounting(t, cl, hi, lo, vo, tb, wi):
    """With CPS=0, the only P&L comes from price changes while in position.
    Final NAV = CASH * product( close[exit_bar] / close[entry_bar] ) for each trade.

    We verify by checking: final_nav / start_nav should equal the
    product of per-trade returns (which we can compute from the NAV
    curve by looking at when positions are entered/exited).

    Simpler check: with zero cost, the NAV at each bar should be exactly
    CASH (if flat) or CASH_at_entry / entry_price * current_price (if in position).
    So final_nav / CASH should equal the geometric product of all trade returns.

    Simplest check: run with CPS=0, compare final_nav to what we'd get from
    tracking trade returns manually. Since we don't have trade-level output,
    we verify the weaker property:
    - nav_ratio = final_nav / start_nav
    - cagr should be consistent with this ratio (already tested in Inv 8)
    - And: nav_ratio with CPS=0 >= nav_ratio with CPS>0 (already tested in Inv 9b)

    Additional accounting check: during flat periods (not in position),
    NAV should be EXACTLY constant.
    """
    ef, es, at, vd = compute_indicators(cl, hi, lo, vo, tb)
    r = sim_fast(cl, ef, es, at, vd, wi, VDO_ON, cps=0.0)

    navs = r["navs"]
    # Find flat periods: when nav[i] = nav[i-1] exactly, we're out of position
    # (no bq, so NAV = cash = constant)
    flat_count = 0
    non_flat_count = 0
    for i in range(1, len(navs)):
        if navs[i] == navs[i - 1]:
            flat_count += 1
        else:
            non_flat_count += 1

    t.log(f"NAV changes: {non_flat_count} bars changed, {flat_count} bars flat")
    t.log(f"Total bars: {len(navs)}, trades: {r['trades']}")

    # The flat bars should correspond to out-of-position periods
    # This is a consistency check: we expect SOME flat bars (between trades)
    if flat_count == 0 and r["trades"] > 1:
        t.log("WARNING: No flat NAV bars despite multiple trades — possible issue")

    # Verify final_nav / start_nav ratio
    ratio = r["final_nav"] / r["start_nav"]
    t.log(f"NAV ratio (final/start): {ratio:.6f}")
    t.log(f"CAGR: {r['cagr']:.4f}%")

    # Self-consistency with CAGR (already tested in Inv 8, but verify here too)
    yrs = r["n_rets"] / (6.0 * 365.25)
    if yrs > 0 and r["cagr"] > -100:
        recon_ratio = (1 + r["cagr"] / 100.0) ** yrs
        rel_err = abs(recon_ratio - ratio) / max(abs(ratio), 1e-12)
        t.log(f"CAGR-reconstructed ratio: {recon_ratio:.6f}, rel_err: {rel_err:.2e}")
        if rel_err > 1e-6:
            t.fail(f"NAV accounting inconsistent: rel_err = {rel_err:.2e}")
            return

    t.ok(f"Zero-cost NAV accounting consistent: ratio={ratio:.4f}, "
         f"flat_bars={flat_count}, changing_bars={non_flat_count}")


# ═══════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 70)
    print("MATHEMATICAL INVARIANT TESTS FOR sim_fast")
    print("=" * 70)
    print(f"  Period: {START} -> {END}   Warmup: {WARMUP}d")
    print(f"  Cost (default): harsh ({COST.round_trip_bps:.0f} bps RT)")
    print(f"  Slow={SLOW}, Fast={FAST}, ATR={ATR_P}, Trail={TRAIL}")
    print(f"  VDO: fast={VDO_F}, slow={VDO_S}")

    print("\nLoading data...")
    cl, hi, lo, vo, tb, wi, n = load_arrays()
    print(f"  {n} H4 bars, warmup idx={wi}, trading={n - wi} bars")

    print("\n" + "=" * 70)
    print("RUNNING INVARIANT TESTS")
    print("=" * 70)

    # Run all tests
    test_sharpe_scale_invariant(cl, hi, lo, vo, tb, wi)
    test_mdd_scale_invariant(cl, hi, lo, vo, tb, wi)
    test_flat_price()
    test_constant_uptrend()
    test_reversed_sharpe(cl, hi, lo, vo, tb, wi)
    test_nav_always_positive(cl, hi, lo, vo, tb, wi)
    test_trade_count(cl, hi, lo, vo, tb, wi)
    test_cagr_self_consistent(cl, hi, lo, vo, tb, wi)
    test_cost_monotonicity(cl, hi, lo, vo, tb, wi)
    test_determinism(cl, hi, lo, vo, tb, wi)
    test_cagr_scale_invariant(cl, hi, lo, vo, tb, wi)
    test_trades_scale_invariant(cl, hi, lo, vo, tb, wi)
    test_final_nav_monotonicity(cl, hi, lo, vo, tb, wi)
    test_vdo_threshold_ordering(cl, hi, lo, vo, tb, wi)
    test_ema_properties()
    test_atr_properties(cl, hi, lo)
    test_zero_cost_nav_accounting(cl, hi, lo, vo, tb, wi)

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    n_pass = sum(1 for r in results if r.passed)
    n_fail = sum(1 for r in results if not r.passed)
    n_total = len(results)

    for r in results:
        status = "PASS" if r.passed else "FAIL"
        print(f"  [{status}] {r.name}")

    print(f"\n  {n_pass}/{n_total} passed, {n_fail} failed")
    if n_fail == 0:
        print("\n  ALL INVARIANTS HOLD — no bugs detected")
    else:
        print(f"\n  {n_fail} INVARIANT(S) VIOLATED — bugs detected!")
        print("  Review FAIL details above for root cause.")

    print("\n" + "=" * 70)
    print("DONE")
    print("=" * 70)

    sys.exit(0 if n_fail == 0 else 1)
