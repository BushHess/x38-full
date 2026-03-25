#!/usr/bin/env python3
"""Block Bootstrap Robustness + Regime-Conditional Analysis.

Part 1: Block Bootstrap (2000 paths)
  Resample H4 bars in contiguous blocks of 60 (~10 days), preserving
  intra-block price-volume-microstructure joint distribution.
  Run 4 VTREND variants per path, record risk-adjusted metrics.

  Variants:
    base     — EMA(30/120) + VDO + ATR trail + EMA exit
    gate360  — + entry gate at EMA(360) ≈ 60-day trend
    gate500  — + entry gate at EMA(500) ≈ 83-day trend
    gate360x — + entry AND exit gate at EMA(360)

  Outputs:
    - Distribution of CAGR, MDD, Sharpe, Calmar per variant
    - P(profitable), P(MDD < 30%), etc.
    - Paired bootstrap test: does gate significantly improve metrics?

Part 2: Regime-Conditional P&L (real data)
  Run variants through the full engine on real data.
  Decompose equity by D1 regime (BULL/BEAR/CHOP/SHOCK/TOPPING/NEUTRAL).
  Answer: does the gate protect in bear markets without killing bull gains?

All tests use harsh cost (50 bps round-trip, 25 bps per side).
Block bootstrap is model-free: no parametric assumptions about return
distributions, volatility clustering, or price-volume relationships.
"""

from __future__ import annotations

import json
import math
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from v10.core.data import DataFeed
from v10.core.engine import BacktestEngine
from v10.core.types import SCENARIOS
from v10.research.objective import compute_objective
from v10.research.regime import (
    AnalyticalRegime,
    classify_d1_regimes,
    compute_regime_returns,
)
from strategies.vtrend.strategy import (
    VTrendConfig,
    VTrendStrategy,
    Signal,
    _ema,
    _atr,
    _vdo,
)

# ── Constants ─────────────────────────────────────────────────────────────

DATA   = str(ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv")
COST   = SCENARIOS["harsh"]
CPS    = COST.per_side_bps / 10_000.0   # 0.0025 for harsh

START  = "2019-01-01"
END    = "2026-02-20"
WARMUP = 365    # calendar days of extra data before START
CASH   = 10_000.0

# Bootstrap
N_BOOT = 2000
BLKSZ  = 60    # H4 bars per block (~10 days)
SEED   = 42

# VTREND defaults
SLOW  = 120
FAST  = max(5, SLOW // 4)   # 30
TRAIL = 3.0
VDO_T = 0.0
ATR_P = 14
VDO_F = 12
VDO_S = 28

# Gate EMA periods (H4 bars)
G360  = 360    # ≈60 days
G500  = 500    # ≈83 days

VARIANTS = ["base", "gate360", "gate500", "gate360x"]
METRICS  = ["cagr", "mdd", "sharpe", "calmar", "trades"]


# ═══════════════════════════════════════════════════════════════════════════
# Part 1: Block Bootstrap
# ═══════════════════════════════════════════════════════════════════════════

def load_arrays():
    """Load real H4 data as numpy arrays.

    Returns (close, high, low, volume, taker_buy, warmup_idx, n_bars, feed).
    warmup_idx = first bar index in the reporting window.
    """
    feed = DataFeed(DATA, start=START, end=END, warmup_days=WARMUP)
    h4 = feed.h4_bars
    n  = len(h4)

    cl = np.array([b.close for b in h4], dtype=np.float64)
    hi = np.array([b.high  for b in h4], dtype=np.float64)
    lo = np.array([b.low   for b in h4], dtype=np.float64)
    vo = np.array([b.volume for b in h4], dtype=np.float64)
    tb = np.array([b.taker_buy_base_vol for b in h4], dtype=np.float64)

    # Find warmup→reporting boundary
    wi = 0
    if feed.report_start_ms is not None:
        for i, b in enumerate(h4):
            if b.close_time >= feed.report_start_ms:
                wi = i
                break

    return cl, hi, lo, vo, tb, wi, n, feed


def make_ratios(cl, hi, lo, vo, tb):
    """Compute per-transition ratios for path reconstruction.

    For transition j  (bar j → bar j+1):
      cr[j] = close[j+1] / close[j]       close-to-close return
      hr[j] = high[j+1]  / close[j]       high  relative to prev close
      lr[j] = low[j+1]   / close[j]       low   relative to prev close
      vol[j], tb[j] = absolute volume/taker_buy of bar j+1

    Length = N-1.  Preserves intra-bar structure:
      hr[j] >= cr[j] >= lr[j]  (high >= close >= low relative to prev close)
    """
    pc = cl[:-1]
    return cl[1:] / pc, hi[1:] / pc, lo[1:] / pc, vo[1:].copy(), tb[1:].copy()


def gen_path(cr, hr, lr, vol, tb, n_trans, blksz, p0, rng):
    """Generate one bootstrap path via block resampling.

    Draws ceil(n_trans/blksz) contiguous blocks from the original
    transition arrays, with replacement.  Reconstructs price path
    via cumulative products of resampled return ratios.

    Returns (close, high, low, volume, taker_buy) of length n_trans+1.
    """
    n_avail = len(cr)
    n_blk   = math.ceil(n_trans / blksz)
    mx      = n_avail - blksz

    if mx <= 0:
        idx = np.arange(min(n_trans, n_avail))
    else:
        starts = rng.integers(0, mx + 1, size=n_blk)
        idx = np.concatenate(
            [np.arange(s, s + blksz) for s in starts]
        )[:n_trans]

    # Reconstruct close via cumulative product (fully vectorized)
    c = np.empty(len(idx) + 1, dtype=np.float64)
    c[0] = p0
    c[1:] = p0 * np.cumprod(cr[idx])

    # High / low via ratio × prev close (vectorized)
    h = np.empty_like(c)
    l = np.empty_like(c)
    v = np.empty_like(c)
    t = np.empty_like(c)

    h[0] = p0 * 1.002
    l[0] = p0 * 0.998
    v[0] = vol[idx[0]]
    t[0] = tb[idx[0]]

    h[1:] = c[:-1] * hr[idx]
    l[1:] = c[:-1] * lr[idx]
    v[1:] = vol[idx]
    t[1:] = tb[idx]

    # Safety: enforce h >= c and l <= c (automatic from ratio construction,
    # but guard against floating-point edge cases)
    np.maximum(h, c, out=h)
    np.minimum(l, c, out=l)

    return c, h, l, v, t


def compute_ind(cl, hi, lo, vo, tb):
    """Compute all indicators once for a path (shared across variants)."""
    return (
        _ema(cl, FAST),          # ema_fast
        _ema(cl, SLOW),          # ema_slow
        _atr(hi, lo, cl, ATR_P), # atr
        _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S),  # vdo
        _ema(cl, G360),          # gate_360
        _ema(cl, G500),          # gate_500
    )


def sim(cl, ef, es, at, vd, wi, gate=None, gx=False):
    """Fast VTREND simulation → metrics dict.

    Matches engine semantics: signal at bar close → fill at next bar's
    open (approximated by previous close).

    Parameters
    ----------
    cl, ef, es, at, vd : arrays of length N
        Close, EMA fast/slow, ATR, VDO.
    wi : int
        Warmup index — first bar in reporting window.
    gate : array or None
        Gate EMA array.  Entry blocked when close <= gate.
    gx : bool
        If True, gate also triggers exit when close < gate.

    Returns dict with cagr, mdd, sharpe, calmar, trades.
    """
    n    = len(cl)
    cash = CASH
    bq   = 0.0       # btc qty
    inp  = False      # in position
    pk   = 0.0        # peak price for trailing stop
    pe   = False      # pending entry
    px   = False      # pending exit
    nt   = 0          # trade count

    navs = []

    for i in range(n):
        p = cl[i]

        # ── Step 1: fill pending at this bar's open (≈ prev close) ──
        if i > 0:
            fp = cl[i - 1]
            if pe:
                bq   = cash / (fp * (1.0 + CPS))
                cash = 0.0
                inp  = True
                pk   = p
                pe   = False
            elif px:
                cash = bq * fp * (1.0 - CPS)
                bq   = 0.0
                inp  = False
                pk   = 0.0
                nt  += 1
                px   = False

        # ── Step 2: equity snapshot at close ──
        nav = cash + bq * p
        if i >= wi:
            navs.append(nav)

        # ── Step 3: signal at close ──
        a_val = at[i]
        if math.isnan(a_val) or math.isnan(ef[i]) or math.isnan(es[i]):
            continue

        if not inp:
            if ef[i] > es[i] and vd[i] > VDO_T:
                if gate is not None and p <= gate[i]:
                    continue
                pe = True
        else:
            pk = max(pk, p)
            ts = pk - TRAIL * a_val
            if p < ts:
                px = True
            elif ef[i] < es[i]:
                px = True
            elif gx and gate is not None and p < gate[i]:
                px = True

    # ── Force-close any open position at end ──
    if inp and bq > 0:
        cash = bq * cl[-1] * (1.0 - CPS)
        bq   = 0.0
        nt  += 1
        if navs:
            navs[-1] = cash

    # ── Compute metrics ──
    if len(navs) < 2 or navs[0] <= 0:
        return {"cagr": -100.0, "mdd": 100.0, "sharpe": 0.0,
                "calmar": 0.0, "trades": 0}

    na  = np.array(navs, dtype=np.float64)
    tr  = na[-1] / na[0] - 1.0
    yrs = (len(na) - 1) / (6.0 * 365.25)

    cagr = (
        ((1.0 + tr) ** (1.0 / yrs) - 1.0) * 100.0
        if yrs > 0 and tr > -1.0 else -100.0
    )

    peak = np.maximum.accumulate(na)
    dd   = (peak - na) / peak * 100.0
    mdd  = float(dd.max())

    rets = np.diff(na) / na[:-1]
    std  = float(np.std(rets, ddof=0))
    sharpe = (
        float(np.mean(rets)) / std * math.sqrt(6.0 * 365.25)
        if std > 1e-12 else 0.0
    )

    calmar = cagr / mdd if mdd > 0.01 else 0.0

    return {"cagr": cagr, "mdd": mdd, "sharpe": sharpe,
            "calmar": calmar, "trades": nt}


# ---------------------------------------------------------------------------

def run_bootstrap():
    """Main bootstrap loop.  Returns (boot_dict, real_dict, feed)."""
    print("\n" + "=" * 70)
    print("PART 1: BLOCK BOOTSTRAP ROBUSTNESS TEST")
    print("=" * 70)
    print(f"  N={N_BOOT}, block={BLKSZ} bars (~{BLKSZ/6:.0f}d), "
          f"cost={COST.round_trip_bps:.0f}bps RT")

    # Load
    cl, hi, lo, vo, tb, wi, n, feed = load_arrays()
    print(f"  {n} H4 bars total, warmup idx={wi}, "
          f"trading bars={n - wi} (~{(n - wi) / 6 / 365.25:.1f}y)")

    cr, hr, lr, vol, tbr = make_ratios(cl, hi, lo, vo, tb)
    n_trans = n - 1
    p0 = cl[0]

    # ── Real-data reference (fast sim) ──
    print("\n  Real-data reference (fast sim):")
    ef, es, at, vd, g3, g5 = compute_ind(cl, hi, lo, vo, tb)
    real = {}
    real["base"]     = sim(cl, ef, es, at, vd, wi)
    real["gate360"]  = sim(cl, ef, es, at, vd, wi, gate=g3)
    real["gate500"]  = sim(cl, ef, es, at, vd, wi, gate=g5)
    real["gate360x"] = sim(cl, ef, es, at, vd, wi, gate=g3, gx=True)

    for v in VARIANTS:
        r = real[v]
        print(f"    {v:12s}  CAGR={r['cagr']:+6.1f}%  MDD={r['mdd']:5.1f}%  "
              f"Sharpe={r['sharpe']:.2f}  Calmar={r['calmar']:.3f}  "
              f"Trades={r['trades']}")

    # ── Bootstrap loop ──
    print(f"\n  Running {N_BOOT} bootstrap paths...")
    rng  = np.random.default_rng(SEED)
    boot = {v: {m: [] for m in METRICS} for v in VARIANTS}

    t0 = time.time()
    for b in range(N_BOOT):
        if (b + 1) % 200 == 0 or b == 0:
            el   = time.time() - t0
            rate = (b + 1) / el if el > 0 else 1
            eta  = (N_BOOT - b - 1) / rate
            print(f"    {b + 1:5d}/{N_BOOT}  "
                  f"({el:.0f}s elapsed, ~{eta:.0f}s left)")

        # Synthetic path
        c, h, l, v, t = gen_path(cr, hr, lr, vol, tbr, n_trans, BLKSZ, p0, rng)
        ef, es, at, vd, g3, g5 = compute_ind(c, h, l, v, t)

        # 4 variants on same path
        results = [
            sim(c, ef, es, at, vd, wi),
            sim(c, ef, es, at, vd, wi, gate=g3),
            sim(c, ef, es, at, vd, wi, gate=g5),
            sim(c, ef, es, at, vd, wi, gate=g3, gx=True),
        ]
        for vn, r in zip(VARIANTS, results):
            for m in METRICS:
                boot[vn][m].append(r[m])

    el = time.time() - t0
    print(f"\n  Done: {el:.1f}s ({N_BOOT / el:.1f} paths/sec)")

    # Convert to numpy
    for v in VARIANTS:
        for m in METRICS:
            boot[v][m] = np.array(boot[v][m])

    return boot, real, feed


def analyze(boot, real):
    """Print bootstrap distribution summaries and paired tests."""

    # ── Distributions ──
    print("\n" + "-" * 70)
    print("DISTRIBUTION SUMMARY")
    print("-" * 70)

    for v in VARIANTS:
        print(f"\n  ── {v} ──")
        for m in METRICS:
            a   = boot[v][m]
            pct = np.percentile(a, [5, 25, 50, 75, 95])
            rv  = real[v][m]
            print(f"    {m:8s}  mean={a.mean():+8.2f}  "
                  f"[p5={pct[0]:+7.2f}  p50={pct[2]:+7.2f}  "
                  f"p95={pct[4]:+7.2f}]  real={rv:+7.2f}")

    # ── Robustness probabilities ──
    print("\n" + "-" * 70)
    print("ROBUSTNESS PROBABILITIES")
    print("-" * 70)

    for v in VARIANTS:
        cg = boot[v]["cagr"]
        md = boot[v]["mdd"]
        cm = boot[v]["calmar"]
        sh = boot[v]["sharpe"]
        print(f"\n  {v}:")
        print(f"    P(CAGR > 0)     = {np.mean(cg > 0) * 100:5.1f}%"
              f"    median CAGR = {np.median(cg):+.1f}%")
        print(f"    P(MDD < 30%)    = {np.mean(md < 30) * 100:5.1f}%"
              f"    median MDD  = {np.median(md):.1f}%")
        print(f"    P(Calmar > 0.5) = {np.mean(cm > 0.5) * 100:5.1f}%"
              f"    median Calmar = {np.median(cm):.3f}")
        print(f"    P(Sharpe > 0.5) = {np.mean(sh > 0.5) * 100:5.1f}%"
              f"    median Sharpe = {np.median(sh):.2f}")

    # ── Paired tests: gate vs base ──
    print("\n" + "-" * 70)
    print("PAIRED BOOTSTRAP TESTS: GATE vs BASE")
    print("-" * 70)
    print("  Paired difference on same path → eliminates path-level noise.")
    print("  P(better) > 97.5% ≈ significant at α=0.05 (one-sided).")
    print()

    for gv in ["gate360", "gate500", "gate360x"]:
        print(f"  ── {gv} vs base ──")

        for m in ["cagr", "sharpe", "calmar"]:
            d  = boot[gv][m] - boot["base"][m]
            ci = np.percentile(d, [2.5, 97.5])
            pb = np.mean(d > 0) * 100
            print(f"    Δ{m:8s}  mean={d.mean():+7.3f}  "
                  f"P(better)={pb:5.1f}%  "
                  f"95%CI=[{ci[0]:+.3f}, {ci[1]:+.3f}]")

        # MDD: lower is better → test base_mdd - gated_mdd > 0
        dm = boot["base"]["mdd"] - boot[gv]["mdd"]
        ci = np.percentile(dm, [2.5, 97.5])
        pb = np.mean(dm > 0) * 100
        print(f"    ΔMDD(red)  mean={dm.mean():+7.3f}  "
              f"P(lower) ={pb:5.1f}%  "
              f"95%CI=[{ci[0]:+.3f}, {ci[1]:+.3f}]")
        print()


# ═══════════════════════════════════════════════════════════════════════════
# Part 2: Regime-Conditional Analysis (real data, full engine)
# ═══════════════════════════════════════════════════════════════════════════

class _VTrendGate(VTrendStrategy):
    """VTREND + regime gate: entry blocked when close ≤ EMA(gate_period).

    If gate_exit=True, also forces exit when close < gate EMA.
    """

    def __init__(self, config, gate_period, gate_exit=False):
        super().__init__(config)
        self._gp = gate_period
        self._gx = gate_exit
        self._ge = None

    def name(self):
        s = "x" if self._gx else ""
        return f"vtrend_g{self._gp}{s}"

    def on_init(self, h4, d1):
        super().on_init(h4, d1)
        cl = np.array([b.close for b in h4], dtype=np.float64)
        self._ge = _ema(cl, self._gp)

    def on_bar(self, state):
        i = state.bar_index
        p = state.bar.close

        if (self._ema_fast is None or self._atr is None
                or self._vdo is None or self._ge is None or i < 1):
            return None

        ef = self._ema_fast[i]
        es = self._ema_slow[i]
        at = self._atr[i]
        vd = self._vdo[i]

        if math.isnan(at) or math.isnan(ef) or math.isnan(es):
            return None

        gok = p > self._ge[i]

        if not self._in_position:
            if ef > es and vd > self._c.vdo_threshold and gok:
                self._in_position = True
                self._peak_price = p
                return Signal(target_exposure=1.0, reason="vtrend_gate_entry")
        else:
            self._peak_price = max(self._peak_price, p)
            ts = self._peak_price - self._c.trail_mult * at

            if p < ts:
                self._in_position = False
                self._peak_price = 0.0
                return Signal(target_exposure=0.0, reason="vtrend_trail_stop")
            if ef < es:
                self._in_position = False
                self._peak_price = 0.0
                return Signal(target_exposure=0.0, reason="vtrend_trend_exit")
            if self._gx and not gok:
                self._in_position = False
                self._peak_price = 0.0
                return Signal(target_exposure=0.0, reason="vtrend_gate_exit")

        return None

    def on_after_fill(self, state, fill):
        pass


def run_regime(feed):
    """Run VTREND variants on real data, decompose P&L by D1 regime."""

    print("\n\n" + "=" * 70)
    print("PART 2: REGIME-CONDITIONAL P&L DECOMPOSITION (real data)")
    print("=" * 70)

    d1 = feed.d1_bars
    regimes = classify_d1_regimes(d1)

    rc  = Counter(r.value for r in regimes)
    tot = len(regimes)
    print("\n  D1 Regime Distribution:")
    for rg in AnalyticalRegime:
        c = rc.get(rg.value, 0)
        print(f"    {rg.value:10s}  {c:4d} days  ({c / tot * 100:.1f}%)")

    # Strategy factories (fresh instance each run — strategy has state)
    strats = [
        ("base",     lambda: VTrendStrategy(VTrendConfig())),
        ("gate360",  lambda: _VTrendGate(VTrendConfig(), G360)),
        ("gate500",  lambda: _VTrendGate(VTrendConfig(), G500)),
        ("gate360x", lambda: _VTrendGate(VTrendConfig(), G360, gate_exit=True)),
    ]

    bt_results = {}
    print("\n  Full-engine backtest results:")
    for name, mk in strats:
        eng = BacktestEngine(
            feed=feed, strategy=mk(), cost=COST,
            initial_cash=CASH, warmup_mode="no_trade",
        )
        bt = eng.run()
        bt_results[name] = bt
        s  = bt.summary
        sc = compute_objective(s)
        print(f"    {name:12s}  CAGR={s.get('cagr_pct', 0):+.1f}%  "
              f"MDD={s.get('max_drawdown_mid_pct', 0):.1f}%  "
              f"Sharpe={s.get('sharpe', 0):.2f}  "
              f"Score={sc:.1f}  "
              f"Trades={s.get('trades', 0)}")

    # Per-regime decomposition
    print("\n" + "-" * 70)
    print("PER-REGIME RETURN DECOMPOSITION")
    print("-" * 70)

    regime_data = {}
    for name in VARIANTS:
        bt = bt_results[name]
        rr = compute_regime_returns(bt.equity, d1, regimes)
        regime_data[name] = rr
        print(f"\n  ── {name} ──")
        for rg in AnalyticalRegime:
            rd = rr.get(rg.value)
            if rd is None:
                continue
            sh = rd.get("sharpe")
            sh_str = f"{sh:+.2f}" if sh is not None else "  N/A"
            print(f"    {rg.value:10s}  Ret={rd['total_return_pct']:+8.1f}%  "
                  f"MDD={rd['max_dd_pct']:5.1f}%  "
                  f"Days={rd['n_days']:6.0f}  "
                  f"Sharpe={sh_str}")

    # Focused comparison: BEAR regime
    print("\n" + "-" * 70)
    print("BEAR MARKET COMPARISON (key question)")
    print("-" * 70)
    print("  Does the regime gate protect against bear-market losses?")
    print()
    for name in VARIANTS:
        rd_bear = regime_data[name].get("BEAR", {})
        rd_bull = regime_data[name].get("BULL", {})
        bear_ret = rd_bear.get("total_return_pct", "N/A")
        bear_mdd = rd_bear.get("max_dd_pct", "N/A")
        bull_ret = rd_bull.get("total_return_pct", "N/A")
        print(f"    {name:12s}  "
              f"BEAR ret={bear_ret:>8}%  BEAR MDD={bear_mdd:>6}%  "
              f"BULL ret={bull_ret:>8}%")

    return bt_results, regime_data


# ═══════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 70)
    print("BLOCK BOOTSTRAP ROBUSTNESS + REGIME ANALYSIS")
    print("=" * 70)
    print(f"  Period: {START} → {END}   Warmup: {WARMUP}d")
    print(f"  Cost: harsh ({COST.round_trip_bps:.0f} bps RT)")
    print(f"  Bootstrap: {N_BOOT} paths, block={BLKSZ} bars (~{BLKSZ/6:.0f}d)")
    print(f"  Gate EMAs: {G360} ({G360/6:.0f}d), {G500} ({G500/6:.0f}d)")

    # Part 1: Block Bootstrap
    boot, real, feed = run_bootstrap()
    analyze(boot, real)

    # Part 2: Regime Analysis
    bt_results, regime_data = run_regime(feed)

    # ── Verification: fast sim vs engine on real data ──
    print("\n" + "-" * 70)
    print("VERIFICATION: FAST SIM vs FULL ENGINE (real data)")
    print("-" * 70)
    print("  Small differences expected (fill price approximation).")
    print()
    for name in VARIANTS:
        sim_cagr = real[name]["cagr"]
        eng_cagr = bt_results[name].summary.get("cagr_pct", 0)
        sim_mdd  = real[name]["mdd"]
        eng_mdd  = bt_results[name].summary.get("max_drawdown_mid_pct", 0)
        print(f"    {name:12s}  "
              f"sim CAGR={sim_cagr:+.1f}% / eng CAGR={eng_cagr:+.1f}%  |  "
              f"sim MDD={sim_mdd:.1f}% / eng MDD={eng_mdd:.1f}%")

    # ── Save results ──
    outdir = Path(__file__).resolve().parent / "results"
    outdir.mkdir(exist_ok=True)

    output = {
        "settings": {
            "n_boot": N_BOOT, "block_size": BLKSZ,
            "cost_rt_bps": COST.round_trip_bps,
            "start": START, "end": END, "warmup_days": WARMUP,
            "variants": VARIANTS,
            "params": {
                "slow": SLOW, "fast": FAST, "trail": TRAIL,
                "vdo_threshold": VDO_T, "atr_period": ATR_P,
                "vdo_fast": VDO_F, "vdo_slow": VDO_S,
                "gate_360": G360, "gate_500": G500,
            },
        },
        "real_data_fast_sim": real,
        "real_data_engine": {
            name: {
                "cagr_pct": bt_results[name].summary.get("cagr_pct", 0),
                "max_drawdown_mid_pct": bt_results[name].summary.get(
                    "max_drawdown_mid_pct", 0),
                "sharpe": bt_results[name].summary.get("sharpe", 0),
                "trades": bt_results[name].summary.get("trades", 0),
            }
            for name in VARIANTS
        },
        "bootstrap": {},
        "paired_tests": {},
        "regime_analysis": {},
    }

    # Bootstrap distributions
    for v in VARIANTS:
        output["bootstrap"][v] = {}
        for m in METRICS:
            a   = boot[v][m]
            pct = np.percentile(a, [5, 25, 50, 75, 95]).tolist()
            output["bootstrap"][v][m] = {
                "mean": round(float(a.mean()), 4),
                "std":  round(float(a.std()), 4),
                "p5": round(pct[0], 4), "p25": round(pct[1], 4),
                "p50": round(pct[2], 4), "p75": round(pct[3], 4),
                "p95": round(pct[4], 4),
            }

    # Paired tests
    for gv in ["gate360", "gate500", "gate360x"]:
        output["paired_tests"][gv] = {}
        for m in ["cagr", "sharpe", "calmar"]:
            d  = boot[gv][m] - boot["base"][m]
            ci = np.percentile(d, [2.5, 97.5]).tolist()
            output["paired_tests"][gv][m] = {
                "mean_diff": round(float(d.mean()), 4),
                "p_better":  round(float(np.mean(d > 0)), 4),
                "ci_95_lo":  round(ci[0], 4),
                "ci_95_hi":  round(ci[1], 4),
            }
        dm = boot["base"]["mdd"] - boot[gv]["mdd"]
        ci = np.percentile(dm, [2.5, 97.5]).tolist()
        output["paired_tests"][gv]["mdd_reduction"] = {
            "mean_diff":  round(float(dm.mean()), 4),
            "p_lower_mdd": round(float(np.mean(dm > 0)), 4),
            "ci_95_lo":   round(ci[0], 4),
            "ci_95_hi":   round(ci[1], 4),
        }

    # Regime analysis
    for name in VARIANTS:
        output["regime_analysis"][name] = regime_data.get(name, {})

    outpath = outdir / "bootstrap_regime.json"
    with open(outpath, "w") as f:
        json.dump(output, f, indent=2, default=str)

    print(f"\n  Results saved → {outpath}")
    print("\n" + "=" * 70)
    print("DONE")
    print("=" * 70)
