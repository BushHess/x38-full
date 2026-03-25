#!/usr/bin/env python3
"""E7 Study: Robust ATR Trail (E5) + Staleness Exit (E6).

E7 = E5 + E6 combined:
  - Trail stop uses ROBUST ATR (cap TR at Q90/100 bars, Wilder period=20)
  - Staleness exit: after MFE >= threshold (in STANDARD ATR units),
    if no new peak close within stale_bars bars → exit (OR logic)
  - EMA cross-down exit: unchanged from E0

Interaction hypothesis: E5's robust ATR smooths the trail (less noise-
triggered exits), while E6's staleness catches genuine stalls. Together,
better risk-adjusted exits than either alone.

Prior results:
  E5 alone: PROVEN MDD reduction (16/16), LOSES CAGR (0/16) → REJECTED
  E6 alone: REJECTED (P(NAV+)=32.4%, consistently reduces NAV in bootstrap)

Method:
  Phase 1: Real data screen — E7 grid × 16 timescales (~1 sec)
  Phase 2: Bootstrap sensitivity — 500 paths × N=120 × grid (~15 min)
  Phase 3: Full validation — 2000 paths × 16 timescales × top combos

Acceptance: dual pass (real + bootstrap), binomial p<0.05.
Primary metric: final NAV.
"""

from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import numpy as np
from scipy import stats as sp_stats

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

N_BOOT_P2 = 500    # Phase 2: sensitivity
N_BOOT_P3 = 2000   # Phase 3: full validation
BLKSZ  = 60
SEED   = 42

ANN = math.sqrt(6.0 * 365.25)

# Fixed VTREND structural constants
ATR_P  = 14
VDO_F  = 12
VDO_S  = 28
TRAIL  = 3.0
VDO_THR = 0.0

# Timescale grid (H4 bars)
SLOW_PERIODS = [30, 48, 60, 72, 84, 96, 108, 120, 144, 168, 200, 240, 300, 360, 500, 720]

# E6 staleness search space (same as e6_staleness_study.py)
STALENESS_BARS = [6, 12, 18, 24, 30, 36, 48, 60]
MFE_THRESHOLDS = [0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 5.0, 6.0]

OUTDIR = Path(__file__).resolve().parent / "results" / "e7_study"


# ═══════════════════════════════════════════════════════════════════════
# Data loading & path generation
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
# Robust ATR computation (from e5_validation.py)
# ═══════════════════════════════════════════════════════════════════════

def _robust_atr(hi, lo, cl, cap_q=0.90, cap_lb=100, period=20):
    """Robust ATR: cap TR at rolling Q90, then Wilder EMA."""
    prev_cl = np.concatenate([[cl[0]], cl[:-1]])
    tr = np.maximum(
        hi - lo,
        np.maximum(np.abs(hi - prev_cl), np.abs(lo - prev_cl)),
    )
    n = len(tr)
    tr_cap = np.full(n, np.nan)
    for i in range(cap_lb, n):
        q = np.percentile(tr[i - cap_lb : i], cap_q * 100)
        tr_cap[i] = min(tr[i], q)
    ratr = np.full(n, np.nan)
    s = cap_lb
    if s + period <= n:
        ratr[s + period - 1] = np.mean(tr_cap[s : s + period])
        for i in range(s + period, n):
            ratr[i] = (ratr[i - 1] * (period - 1) + tr_cap[i]) / period
    return ratr


# ═══════════════════════════════════════════════════════════════════════
# Metrics helper
# ═══════════════════════════════════════════════════════════════════════

def _compute_metrics(navs_start, navs_end, nav_min_ratio, rets_sum, rets_sq_sum, n_rets, nt):
    if n_rets < 2 or navs_start <= 0:
        return {"sharpe": 0.0, "cagr": -100.0, "mdd": 100.0, "calmar": 0.0,
                "trades": nt, "final_nav": navs_end}

    tr = navs_end / navs_start - 1.0
    yrs = n_rets / (6.0 * 365.25)
    cagr = ((1 + tr) ** (1.0 / yrs) - 1.0) * 100 if yrs > 0 and tr > -1 else -100.0
    mdd = (1.0 - nav_min_ratio) * 100.0

    mu = rets_sum / n_rets
    var = rets_sq_sum / n_rets - mu * mu
    std = math.sqrt(max(var, 0.0))
    sharpe = (mu / std * ANN) if std > 1e-12 else 0.0
    calmar = cagr / mdd if mdd > 0.01 else 0.0

    return {
        "sharpe": sharpe,
        "cagr": cagr,
        "mdd": mdd,
        "calmar": calmar,
        "trades": nt,
        "final_nav": navs_end,
    }


# ═══════════════════════════════════════════════════════════════════════
# Simulation: E0 baseline
# ═══════════════════════════════════════════════════════════════════════

def sim_e0(cl, ef, es, at, vd, wi):
    """VTREND E0: standard ATR trail + EMA cross-down."""
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
                nav_peak = nav
                prev_nav = nav
                started = True
            else:
                if prev_nav > 0:
                    r = nav / prev_nav - 1.0
                    rets_sum += r
                    rets_sq_sum += r * r
                    n_rets += 1
                prev_nav = nav
            navs_end = nav
            if nav > nav_peak:
                nav_peak = nav
            ratio = nav / nav_peak if nav_peak > 0 else 1.0
            if ratio < nav_min_ratio:
                nav_min_ratio = ratio

        a_val = at[i]
        if math.isnan(a_val) or math.isnan(ef[i]) or math.isnan(es[i]):
            continue

        if not inp:
            if ef[i] > es[i] and vd[i] > VDO_THR:
                pe = True
        else:
            pk = max(pk, p)
            if p < pk - TRAIL * a_val:
                px = True
            elif ef[i] < es[i]:
                px = True

    if inp and bq > 0:
        cash = bq * cl[-1] * (1.0 - CPS)
        bq = 0.0
        nt += 1
        navs_end = cash

    return _compute_metrics(navs_start, navs_end, nav_min_ratio,
                            rets_sum, rets_sq_sum, n_rets, nt)


# ═══════════════════════════════════════════════════════════════════════
# Simulation: E7 = E5 (robust ATR trail) + E6 (staleness exit)
# ═══════════════════════════════════════════════════════════════════════

def sim_e7(cl, ef, es, at, vd, wi, ratr, stale_bars, mfe_thr):
    """VTREND E7: robust ATR trail + staleness exit.

    Trail stop: pk - TRAIL * ratr[i]  (robust ATR from E5)
    Staleness: after MFE >= mfe_thr (in STANDARD ATR units from entry),
               if no new peak close within stale_bars bars → exit.
    EMA cross-down: unchanged from E0.

    All exits via OR logic.
    """
    n = len(cl)
    cash = CASH
    bq = 0.0
    inp = False
    pk = 0.0
    pe = px = False
    nt = 0

    # E6-specific state
    entry_price = 0.0
    entry_atr = 0.0  # standard ATR at entry (for MFE calculation)
    pk_bar = 0

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
                pk_bar = i
                entry_price = fp
                # Use STANDARD ATR at entry for MFE (same as E6)
                entry_atr = at[i] if not math.isnan(at[i]) else 0.0
            elif px:
                cash = bq * fp * (1.0 - CPS)
                bq = 0.0
                inp = False
                pk = 0.0
                nt += 1
                px = False
                entry_price = 0.0
                entry_atr = 0.0
                pk_bar = 0

        nav = cash + bq * p

        if i >= wi:
            if not started:
                navs_start = nav
                nav_peak = nav
                prev_nav = nav
                started = True
            else:
                if prev_nav > 0:
                    r = nav / prev_nav - 1.0
                    rets_sum += r
                    rets_sq_sum += r * r
                    n_rets += 1
                prev_nav = nav
            navs_end = nav
            if nav > nav_peak:
                nav_peak = nav
            ratio = nav / nav_peak if nav_peak > 0 else 1.0
            if ratio < nav_min_ratio:
                nav_min_ratio = ratio

        # Need both standard ATR and robust ATR to be valid
        a_val = at[i]
        ra_val = ratr[i]
        if math.isnan(a_val) or math.isnan(ef[i]) or math.isnan(es[i]):
            continue
        if math.isnan(ra_val):
            continue

        if not inp:
            if ef[i] > es[i] and vd[i] > VDO_THR:
                pe = True
        else:
            # Track peak (same as E0/E6)
            if p > pk:
                pk = p
                pk_bar = i

            # EXIT 1: Robust ATR trailing stop (E5)
            trail = pk - TRAIL * ra_val
            if p < trail:
                px = True
            # EXIT 2: EMA cross-down (E0)
            elif ef[i] < es[i]:
                px = True

            # EXIT 3: Staleness exit (E6, OR logic)
            if not px and entry_atr > 1e-12:
                mfe_r = (pk - entry_price) / entry_atr
                if mfe_r >= mfe_thr and (i - pk_bar) >= stale_bars:
                    px = True

    # Force close
    if inp and bq > 0:
        cash = bq * cl[-1] * (1.0 - CPS)
        bq = 0.0
        nt += 1
        navs_end = cash

    return _compute_metrics(navs_start, navs_end, nav_min_ratio,
                            rets_sum, rets_sq_sum, n_rets, nt)


# Also test E5-only for decomposition
def sim_e5(cl, ef, es, at, vd, wi, ratr):
    """VTREND E5: robust ATR trail only (no staleness)."""
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
                nav_peak = nav
                prev_nav = nav
                started = True
            else:
                if prev_nav > 0:
                    r = nav / prev_nav - 1.0
                    rets_sum += r
                    rets_sq_sum += r * r
                    n_rets += 1
                prev_nav = nav
            navs_end = nav
            if nav > nav_peak:
                nav_peak = nav
            ratio = nav / nav_peak if nav_peak > 0 else 1.0
            if ratio < nav_min_ratio:
                nav_min_ratio = ratio

        a_val = at[i]
        ra_val = ratr[i]
        if math.isnan(a_val) or math.isnan(ef[i]) or math.isnan(es[i]):
            continue
        if math.isnan(ra_val):
            continue

        if not inp:
            if ef[i] > es[i] and vd[i] > VDO_THR:
                pe = True
        else:
            pk = max(pk, p)
            trail = pk - TRAIL * ra_val
            if p < trail:
                px = True
            elif ef[i] < es[i]:
                px = True

    if inp and bq > 0:
        cash = bq * cl[-1] * (1.0 - CPS)
        bq = 0.0
        nt += 1
        navs_end = cash

    return _compute_metrics(navs_start, navs_end, nav_min_ratio,
                            rets_sum, rets_sq_sum, n_rets, nt)


# ═══════════════════════════════════════════════════════════════════════
# Phase 1: Real data screen
# ═══════════════════════════════════════════════════════════════════════

def phase1_real_screen(cl, hi, lo, vo, tb, wi):
    """E0 vs E5 vs E7-grid on real data at 16 timescales."""
    print("\n" + "=" * 70)
    print("PHASE 1: REAL DATA SCREEN")
    print("=" * 70)

    at = _atr(hi, lo, cl, ATR_P)
    vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)
    ratr = _robust_atr(hi, lo, cl)

    n_sb = len(STALENESS_BARS)
    n_mt = len(MFE_THRESHOLDS)
    n_sp = len(SLOW_PERIODS)

    # E7 wins over E0 heatmap
    wins_vs_e0 = np.zeros((n_sb, n_mt), dtype=int)
    # E7 wins over E5 heatmap (isolates staleness contribution)
    wins_vs_e5 = np.zeros((n_sb, n_mt), dtype=int)

    e0_results = {}
    e5_results = {}
    e7_navs = {}   # (sb, mt) -> {sp: nav}

    for sp in SLOW_PERIODS:
        fp = max(5, sp // 4)
        ef = _ema(cl, fp)
        es = _ema(cl, sp)

        r0 = sim_e0(cl, ef, es, at, vd, wi)
        r5 = sim_e5(cl, ef, es, at, vd, wi, ratr)
        e0_results[sp] = r0
        e5_results[sp] = r5

        for si, sb in enumerate(STALENESS_BARS):
            for mi, mt in enumerate(MFE_THRESHOLDS):
                r7 = sim_e7(cl, ef, es, at, vd, wi, ratr, sb, mt)
                key = (sb, mt)
                if key not in e7_navs:
                    e7_navs[key] = {}
                e7_navs[key][sp] = r7["final_nav"]
                if r7["final_nav"] > r0["final_nav"]:
                    wins_vs_e0[si, mi] += 1
                if r7["final_nav"] > r5["final_nav"]:
                    wins_vs_e5[si, mi] += 1

    # ── Print E0 vs E5 baseline ──
    print(f"\n  E0 vs E5 baseline across timescales:")
    print(f"  {'sp':>5}  {'E0 NAV':>10}  {'E0 Sh':>7}  {'E5 NAV':>10}  {'E5 Sh':>7}  {'ΔNAV%':>7}")
    print("  " + "-" * 55)
    e5_wins_real = 0
    for sp in SLOW_PERIODS:
        r0 = e0_results[sp]
        r5 = e5_results[sp]
        d = (r5["final_nav"] / max(r0["final_nav"], 1) - 1) * 100
        if d > 0:
            e5_wins_real += 1
        print(f"  {sp:5d}  ${r0['final_nav']:>9,.0f}  {r0['sharpe']:+.3f}  "
              f"${r5['final_nav']:>9,.0f}  {r5['sharpe']:+.3f}  {d:+.1f}%")
    print(f"  E5 wins: {e5_wins_real}/{n_sp}")

    # ── E7 vs E0 heatmap ──
    print(f"\n  E7 vs E0 wins/{n_sp} (rows=stale_bars, cols=mfe_thr):")
    header = "  sb\\mt"
    for mt in MFE_THRESHOLDS:
        header += f"  {mt:5.1f}"
    print(header)
    print("  " + "-" * (7 + 7 * n_mt))
    for si, sb in enumerate(STALENESS_BARS):
        row = f"  {sb:4d} "
        for mi in range(n_mt):
            w = wins_vs_e0[si, mi]
            marker = " *" if w >= n_sp // 2 else "  "
            row += f"  {w:3d}{marker}"
        print(row)

    # ── E7 vs E5 heatmap (staleness contribution) ──
    print(f"\n  E7 vs E5 wins/{n_sp} (staleness contribution beyond robust ATR):")
    header = "  sb\\mt"
    for mt in MFE_THRESHOLDS:
        header += f"  {mt:5.1f}"
    print(header)
    print("  " + "-" * (7 + 7 * n_mt))
    for si, sb in enumerate(STALENESS_BARS):
        row = f"  {sb:4d} "
        for mi in range(n_mt):
            w = wins_vs_e5[si, mi]
            marker = " *" if w >= n_sp // 2 else "  "
            row += f"  {w:3d}{marker}"
        print(row)

    # Survivors
    survivors = []
    for si, sb in enumerate(STALENESS_BARS):
        for mi, mt in enumerate(MFE_THRESHOLDS):
            if wins_vs_e0[si, mi] >= n_sp // 2:
                survivors.append((sb, mt, int(wins_vs_e0[si, mi])))

    print(f"\n  Survivors vs E0 (>= {n_sp // 2}/{n_sp} wins): {len(survivors)}")
    for sb, mt, w in survivors:
        print(f"    sb={sb:3d}, mt={mt:.1f}: {w}/{n_sp} wins")

    return e0_results, e5_results, e7_navs, survivors, wins_vs_e0, wins_vs_e5


# ═══════════════════════════════════════════════════════════════════════
# Phase 2: Bootstrap sensitivity at N=120
# ═══════════════════════════════════════════════════════════════════════

def phase2_sensitivity(cl, hi, lo, vo, tb, wi, n):
    """500 paths × N=120 × 64 E7 combos + E0 + E5."""
    print("\n" + "=" * 70)
    print(f"PHASE 2: BOOTSTRAP SENSITIVITY ({N_BOOT_P2} paths × N=120 × 64 combos)")
    print("=" * 70)

    cr, hr, lr, vol, tbb = make_ratios(cl, hi, lo, vo, tb)
    n_trans = n - 1
    p0 = cl[0]
    rng = np.random.default_rng(SEED)

    SP = 120
    FP = max(5, SP // 4)

    n_sb = len(STALENESS_BARS)
    n_mt = len(MFE_THRESHOLDS)

    nav_e0 = np.zeros(N_BOOT_P2)
    nav_e5 = np.zeros(N_BOOT_P2)
    nav_e7 = np.zeros((N_BOOT_P2, n_sb, n_mt))
    sh_e0 = np.zeros(N_BOOT_P2)
    sh_e5 = np.zeros(N_BOOT_P2)
    sh_e7 = np.zeros((N_BOOT_P2, n_sb, n_mt))
    mdd_e0 = np.zeros(N_BOOT_P2)
    mdd_e5 = np.zeros(N_BOOT_P2)
    mdd_e7 = np.zeros((N_BOOT_P2, n_sb, n_mt))

    t0 = time.time()
    for b in range(N_BOOT_P2):
        if (b + 1) % 100 == 0 or b == 0:
            el = time.time() - t0
            rate = (b + 1) / el if el > 0 else 1
            eta = (N_BOOT_P2 - b - 1) / rate
            print(f"    {b+1:5d}/{N_BOOT_P2}  ({el:.0f}s, ~{eta:.0f}s left)")

        c, h, l, v, t = gen_path(cr, hr, lr, vol, tbb, n_trans, BLKSZ, p0, rng)

        at = _atr(h, l, c, ATR_P)
        vd = _vdo(c, h, l, v, t, VDO_F, VDO_S)
        ratr = _robust_atr(h, l, c)
        ef = _ema(c, FP)
        es = _ema(c, SP)

        r0 = sim_e0(c, ef, es, at, vd, wi)
        r5 = sim_e5(c, ef, es, at, vd, wi, ratr)
        nav_e0[b] = r0["final_nav"]
        nav_e5[b] = r5["final_nav"]
        sh_e0[b] = r0["sharpe"]
        sh_e5[b] = r5["sharpe"]
        mdd_e0[b] = r0["mdd"]
        mdd_e5[b] = r5["mdd"]

        for si, sb in enumerate(STALENESS_BARS):
            for mi, mt in enumerate(MFE_THRESHOLDS):
                r7 = sim_e7(c, ef, es, at, vd, wi, ratr, sb, mt)
                nav_e7[b, si, mi] = r7["final_nav"]
                sh_e7[b, si, mi] = r7["sharpe"]
                mdd_e7[b, si, mi] = r7["mdd"]

    el = time.time() - t0
    print(f"\n  Done: {el:.1f}s ({N_BOOT_P2 * (2 + n_sb * n_mt)} sims)")

    # ── E5 vs E0 at N=120 ──
    p_e5_nav = float(np.mean(nav_e5 > nav_e0))
    p_e5_mdd = float(np.mean(mdd_e5 < mdd_e0))
    print(f"\n  E5 vs E0 at N=120: P(NAV+)={p_e5_nav*100:.1f}%, P(MDD-)={p_e5_mdd*100:.1f}%")

    # ── E7 vs E0 P(NAV+) heatmap ──
    p_nav_vs_e0 = np.zeros((n_sb, n_mt))
    p_mdd_vs_e0 = np.zeros((n_sb, n_mt))
    p_nav_vs_e5 = np.zeros((n_sb, n_mt))
    median_sh_delta_vs_e0 = np.zeros((n_sb, n_mt))

    for si in range(n_sb):
        for mi in range(n_mt):
            p_nav_vs_e0[si, mi] = float(np.mean(nav_e7[:, si, mi] > nav_e0))
            p_mdd_vs_e0[si, mi] = float(np.mean(mdd_e7[:, si, mi] < mdd_e0))
            p_nav_vs_e5[si, mi] = float(np.mean(nav_e7[:, si, mi] > nav_e5))
            d_sh = sh_e7[:, si, mi] - sh_e0
            median_sh_delta_vs_e0[si, mi] = float(np.median(d_sh))

    print(f"\n  E7 vs E0 P(NAV+) heatmap:")
    header = "  sb\\mt"
    for mt in MFE_THRESHOLDS:
        header += f"  {mt:5.1f}"
    print(header)
    print("  " + "-" * (7 + 7 * n_mt))
    for si, sb in enumerate(STALENESS_BARS):
        row = f"  {sb:4d} "
        for mi in range(n_mt):
            pv = p_nav_vs_e0[si, mi] * 100
            row += f"  {pv:5.1f}"
        print(row)

    print(f"\n  E7 vs E0 P(MDD-) heatmap:")
    header = "  sb\\mt"
    for mt in MFE_THRESHOLDS:
        header += f"  {mt:5.1f}"
    print(header)
    print("  " + "-" * (7 + 7 * n_mt))
    for si, sb in enumerate(STALENESS_BARS):
        row = f"  {sb:4d} "
        for mi in range(n_mt):
            pv = p_mdd_vs_e0[si, mi] * 100
            row += f"  {pv:5.1f}"
        print(row)

    print(f"\n  E7 vs E5 P(NAV+) heatmap (staleness adds value to robust ATR?):")
    header = "  sb\\mt"
    for mt in MFE_THRESHOLDS:
        header += f"  {mt:5.1f}"
    print(header)
    print("  " + "-" * (7 + 7 * n_mt))
    for si, sb in enumerate(STALENESS_BARS):
        row = f"  {sb:4d} "
        for mi in range(n_mt):
            pv = p_nav_vs_e5[si, mi] * 100
            row += f"  {pv:5.1f}"
        print(row)

    # Plateau analysis
    row_corrs = []
    for si in range(n_sb - 1):
        r = np.corrcoef(p_nav_vs_e0[si, :], p_nav_vs_e0[si + 1, :])[0, 1]
        if not np.isnan(r):
            row_corrs.append(r)
    col_corrs = []
    for mi in range(n_mt - 1):
        r = np.corrcoef(p_nav_vs_e0[:, mi], p_nav_vs_e0[:, mi + 1])[0, 1]
        if not np.isnan(r):
            col_corrs.append(r)

    all_corrs = row_corrs + col_corrs
    mean_adj_corr = float(np.mean(all_corrs)) if all_corrs else 0.0

    print(f"\n  Plateau analysis:")
    print(f"    Overall adj corr: {mean_adj_corr:.3f} "
          f"({'smooth' if mean_adj_corr > 0.5 else 'fragile'})")

    # Best combo
    best_idx = np.unravel_index(np.argmax(p_nav_vs_e0), p_nav_vs_e0.shape)
    best_sb = STALENESS_BARS[best_idx[0]]
    best_mt = MFE_THRESHOLDS[best_idx[1]]
    at_edge = (best_idx[0] == 0 or best_idx[0] == n_sb - 1 or
               best_idx[1] == 0 or best_idx[1] == n_mt - 1)

    print(f"  Best combo: sb={best_sb}, mt={best_mt} "
          f"(P(NAV+)={p_nav_vs_e0[best_idx]*100:.1f}%)")
    print(f"  At grid edge: {'YES' if at_edge else 'NO'}")

    # Decomposition: is E7's MDD benefit from E5 or staleness?
    print(f"\n  Decomposition at best combo (sb={best_sb}, mt={best_mt}):")
    bi = best_idx
    print(f"    E7 vs E0: P(NAV+)={p_nav_vs_e0[bi]*100:.1f}%, P(MDD-)={p_mdd_vs_e0[bi]*100:.1f}%")
    print(f"    E5 vs E0: P(NAV+)={p_e5_nav*100:.1f}%, P(MDD-)={p_e5_mdd*100:.1f}%")
    print(f"    E7 vs E5: P(NAV+)={p_nav_vs_e5[bi]*100:.1f}% (staleness contribution)")

    # Select top combos for Phase 3
    candidates = []
    for si in range(n_sb):
        for mi in range(n_mt):
            if p_nav_vs_e0[si, mi] > 0.50:
                candidates.append((si, mi, p_nav_vs_e0[si, mi]))

    candidates.sort(key=lambda x: x[2], reverse=True)
    top_combos = [(STALENESS_BARS[si], MFE_THRESHOLDS[mi])
                  for si, mi, _ in candidates[:5]]

    print(f"\n  Top combos for Phase 3 ({len(candidates)} with P(NAV+)>50%):")
    for si, mi, pv in candidates[:5]:
        print(f"    sb={STALENESS_BARS[si]:3d}, mt={MFE_THRESHOLDS[mi]:.1f}: "
              f"P(NAV+)={pv*100:.1f}%, medΔSh={median_sh_delta_vs_e0[si, mi]:+.4f}")

    return {
        "p_nav_vs_e0": p_nav_vs_e0,
        "p_mdd_vs_e0": p_mdd_vs_e0,
        "p_nav_vs_e5": p_nav_vs_e5,
        "median_sh_delta_vs_e0": median_sh_delta_vs_e0,
        "mean_adj_corr": mean_adj_corr,
        "best_combo": (best_sb, best_mt),
        "at_edge": at_edge,
        "top_combos": top_combos,
        "e5_vs_e0_p_nav": p_e5_nav,
        "e5_vs_e0_p_mdd": p_e5_mdd,
        "any_above_50": len(candidates) > 0,
    }


# ═══════════════════════════════════════════════════════════════════════
# Phase 3: Full bootstrap validation
# ═══════════════════════════════════════════════════════════════════════

def phase3_validation(cl, hi, lo, vo, tb, wi, n, top_combos, e0_real, e5_real, e7_real_navs):
    """2000 paths × 16 timescales × selected combos + E0 + E5."""
    print("\n" + "=" * 70)
    print(f"PHASE 3: FULL VALIDATION ({N_BOOT_P3} paths × {len(SLOW_PERIODS)} "
          f"timescales × {len(top_combos)} combos)")
    print("=" * 70)

    cr, hr, lr, vol, tbb = make_ratios(cl, hi, lo, vo, tb)
    n_trans = n - 1
    p0 = cl[0]
    rng = np.random.default_rng(SEED)

    n_sp = len(SLOW_PERIODS)
    n_combos = len(top_combos)
    mkeys = ["sharpe", "cagr", "mdd", "final_nav"]

    boot_e0 = {m: np.zeros((N_BOOT_P3, n_sp)) for m in mkeys}
    boot_e5 = {m: np.zeros((N_BOOT_P3, n_sp)) for m in mkeys}
    boot_e7 = {k: {m: np.zeros((N_BOOT_P3, n_sp)) for m in mkeys}
               for k in top_combos}

    t0 = time.time()
    for b in range(N_BOOT_P3):
        if (b + 1) % 200 == 0 or b == 0:
            el = time.time() - t0
            rate = (b + 1) / el if el > 0 else 1
            eta = (N_BOOT_P3 - b - 1) / rate
            print(f"    {b+1:5d}/{N_BOOT_P3}  ({el:.0f}s, ~{eta:.0f}s left)")

        c, h, l, v, t = gen_path(cr, hr, lr, vol, tbb, n_trans, BLKSZ, p0, rng)

        at = _atr(h, l, c, ATR_P)
        vd = _vdo(c, h, l, v, t, VDO_F, VDO_S)
        ratr = _robust_atr(h, l, c)

        for j, sp in enumerate(SLOW_PERIODS):
            fp = max(5, sp // 4)
            ef = _ema(c, fp)
            es = _ema(c, sp)

            r0 = sim_e0(c, ef, es, at, vd, wi)
            r5 = sim_e5(c, ef, es, at, vd, wi, ratr)
            for m in mkeys:
                boot_e0[m][b, j] = r0[m]
                boot_e5[m][b, j] = r5[m]

            for combo in top_combos:
                sb, mt = combo
                r7 = sim_e7(c, ef, es, at, vd, wi, ratr, sb, mt)
                for m in mkeys:
                    boot_e7[combo][m][b, j] = r7[m]

    el = time.time() - t0
    n_total = N_BOOT_P3 * n_sp * (2 + n_combos)
    print(f"\n  Done: {el:.1f}s ({n_total} sims, {n_total / el:.0f} sims/sec)")

    # ── E5 binomial across timescales (for comparison) ──
    print(f"\n  {'─' * 60}")
    print(f"  E5 vs E0 (reference, robust ATR only)")
    print(f"  {'─' * 60}")

    e5_win_nav = 0
    e5_win_mdd = 0
    for j, sp in enumerate(SLOW_PERIODS):
        d_nav = boot_e5["final_nav"][:, j] - boot_e0["final_nav"][:, j]
        d_mdd = boot_e0["mdd"][:, j] - boot_e5["mdd"][:, j]
        p_nav = float(np.mean(d_nav > 0))
        p_mdd = float(np.mean(d_mdd > 0))
        if p_nav > 0.5: e5_win_nav += 1
        if p_mdd > 0.5: e5_win_mdd += 1

    p_e5_nav = sp_stats.binomtest(e5_win_nav, n_sp, 0.5, alternative='greater').pvalue
    p_e5_mdd = sp_stats.binomtest(e5_win_mdd, n_sp, 0.5, alternative='greater').pvalue
    print(f"  NAV: {e5_win_nav}/{n_sp} timescales, binom p={p_e5_nav:.6f}")
    print(f"  MDD: {e5_win_mdd}/{n_sp} timescales, binom p={p_e5_mdd:.6f}")

    # ── Per-combo E7 analysis ──
    combo_results = {}
    for combo in top_combos:
        sb, mt = combo
        combo_key = f"sb{sb}_mt{mt}"
        print(f"\n  {'─' * 60}")
        print(f"  E7 combo: sb={sb}, mt={mt} (robust ATR + staleness)")
        print(f"  {'─' * 60}")

        print(f"\n  {'sp':>5}  {'days':>5}  "
              f"{'P(NAV+)':>8}  {'P(Sh+)':>7}  {'P(MDD-)':>8}  "
              f"{'medΔNAV%':>9}  {'real_ΔNAV%':>10}")
        print("  " + "-" * 65)

        win_nav = 0
        win_sharpe = 0
        win_cagr = 0
        win_mdd = 0
        win_real = 0

        per_ts = []
        for j, sp in enumerate(SLOW_PERIODS):
            days = sp * 4 / 24

            d_nav = boot_e7[combo]["final_nav"][:, j] - boot_e0["final_nav"][:, j]
            d_sh = boot_e7[combo]["sharpe"][:, j] - boot_e0["sharpe"][:, j]
            d_cg = boot_e7[combo]["cagr"][:, j] - boot_e0["cagr"][:, j]
            d_md = boot_e0["mdd"][:, j] - boot_e7[combo]["mdd"][:, j]

            p_nav = float(np.mean(d_nav > 0))
            p_sh = float(np.mean(d_sh > 0))
            p_cg = float(np.mean(d_cg > 0))
            p_md = float(np.mean(d_md > 0))

            if p_nav > 0.50: win_nav += 1
            if p_sh > 0.50: win_sharpe += 1
            if p_cg > 0.50: win_cagr += 1
            if p_md > 0.50: win_mdd += 1

            # Real data
            nav_e0_real = e0_real.get(sp, {}).get("final_nav", 0)
            nav_e7_real = e7_real_navs.get((sb, mt), {}).get(sp, 0)
            real_delta = (nav_e7_real / max(nav_e0_real, 1) - 1) * 100
            if real_delta > 0:
                win_real += 1

            nav_ratio = boot_e7[combo]["final_nav"][:, j] / np.maximum(boot_e0["final_nav"][:, j], 1)
            med_nav_pct = float((np.median(nav_ratio) - 1) * 100)

            print(f"  {sp:5d}  {days:5.0f}  "
                  f"{p_nav*100:7.1f}%  {p_sh*100:6.1f}%  {p_md*100:7.1f}%  "
                  f"{med_nav_pct:+8.2f}%  {real_delta:+9.1f}%")

            per_ts.append({
                "sp": sp, "days": days,
                "p_nav": round(p_nav, 6), "p_sharpe": round(p_sh, 6),
                "p_cagr": round(p_cg, 6), "p_mdd": round(p_md, 6),
                "med_nav_delta_pct": round(med_nav_pct, 4),
                "real_delta_nav_pct": round(real_delta, 4),
            })

        # Binomial tests
        print(f"\n  {'METRIC':>17}  {'wins':>5}/{n_sp}  {'binom p':>10}  {'verdict':>12}")
        print("  " + "-" * 55)

        binom = {}
        for label, wins in [
            ("P(NAV+)>50%", win_nav),
            ("P(Sharpe+)>50%", win_sharpe),
            ("P(CAGR+)>50%", win_cagr),
            ("P(MDD-)>50%", win_mdd),
            ("Real ΔNAV>0", win_real),
        ]:
            p_binom = sp_stats.binomtest(wins, n_sp, 0.5, alternative='greater').pvalue
            if p_binom < 0.001:
                verdict = "PROVEN ***"
            elif p_binom < 0.01:
                verdict = "PROVEN **"
            elif p_binom < 0.025:
                verdict = "PROVEN *"
            elif p_binom < 0.05:
                verdict = "STRONG"
            elif p_binom < 0.10:
                verdict = "MARGINAL"
            else:
                verdict = "NOT SIG"

            print(f"  {label:>17}  {wins:5d}/{n_sp}  {p_binom:10.6f}  {verdict:>12}")
            binom[label] = {
                "wins": wins, "n": n_sp,
                "p_binom": round(p_binom, 8), "verdict": verdict,
            }

        # Dual pass
        boot_pass = binom["P(NAV+)>50%"]["p_binom"] < 0.05
        real_pass = win_real >= 9

        combo_verdict = "REJECT"
        if boot_pass and real_pass:
            p_val = binom["P(NAV+)>50%"]["p_binom"]
            if p_val < 0.001:
                combo_verdict = "PROVEN ***"
            elif p_val < 0.01:
                combo_verdict = "PROVEN **"
            elif p_val < 0.025:
                combo_verdict = "PROVEN *"
            elif p_val < 0.05:
                combo_verdict = "STRONG"
        elif boot_pass:
            combo_verdict = "BOOT ONLY (real data fails)"
        elif real_pass:
            combo_verdict = "REAL ONLY (bootstrap fails)"

        print(f"\n  Dual pass: boot={'PASS' if boot_pass else 'FAIL'} "
              f"(p={binom['P(NAV+)>50%']['p_binom']:.6f}), "
              f"real={'PASS' if real_pass else 'FAIL'} ({win_real}/{n_sp})")
        print(f"  Verdict: {combo_verdict}")

        combo_results[combo_key] = {
            "sb": sb, "mt": mt,
            "per_timescale": per_ts,
            "binomial_tests": binom,
            "boot_pass": boot_pass,
            "real_pass": real_pass,
            "verdict": combo_verdict,
        }

    return combo_results


# ═══════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    t_start = time.time()

    print("E7 STUDY: ROBUST ATR TRAIL (E5) + STALENESS EXIT (E6)")
    print("=" * 70)
    print(f"  E7 mechanism:")
    print(f"    Trail stop: pk - 3.0 × robust_ATR (cap_q=0.90, cap_lb=100, period=20)")
    print(f"    Staleness: after MFE >= thr (std ATR units), no new peak within N bars → exit")
    print(f"    EMA cross-down: unchanged from E0")
    print(f"  Search space: {len(STALENESS_BARS)} × {len(MFE_THRESHOLDS)} = "
          f"{len(STALENESS_BARS) * len(MFE_THRESHOLDS)} combos")
    print(f"  Primary metric: final NAV")

    # ── Load data ──
    cl, hi, lo, vo, tb, wi, n = load_arrays()
    print(f"\n  Data: {n} H4 bars, warmup index={wi}")

    # ── Phase 1 ──
    e0_real, e5_real, e7_navs, survivors, wins_e0, wins_e5 = phase1_real_screen(
        cl, hi, lo, vo, tb, wi
    )

    if not survivors:
        print("\n" + "=" * 70)
        print("EARLY TERMINATION: Zero survivors in Phase 1")
        print("No E7 combo wins at >= 8/16 timescales on real data.")
        print("VERDICT: REJECT E7")
        print("=" * 70)

        output = {
            "config": {
                "staleness_bars": STALENESS_BARS,
                "mfe_thresholds": MFE_THRESHOLDS,
                "slow_periods": SLOW_PERIODS,
                "n_boot_p2": N_BOOT_P2,
                "n_boot_p3": N_BOOT_P3,
                "seed": SEED,
                "cost_bps_rt": round(CPS * 2 * 10000, 1),
                "trail_mult": TRAIL,
                "e5_cap_q": 0.90, "e5_cap_lb": 100, "e5_period": 20,
            },
            "phase1_real_screen": {
                "wins_vs_e0": wins_e0.tolist(),
                "wins_vs_e5": wins_e5.tolist(),
                "survivors": [],
            },
            "overall_verdict": "REJECT E7",
            "overall_reason": "Zero survivors in Phase 1 real data screen",
        }
        OUTDIR.mkdir(parents=True, exist_ok=True)
        with open(OUTDIR / "e7_study.json", "w") as f:
            json.dump(output, f, indent=2)
        print(f"\n  Saved: {OUTDIR / 'e7_study.json'}")
        el = time.time() - t_start
        print(f"  Total time: {el:.0f}s")
        sys.exit(0)

    # ── Phase 2 ──
    p2 = phase2_sensitivity(cl, hi, lo, vo, tb, wi, n)

    if not p2["any_above_50"]:
        print("\n" + "=" * 70)
        print("EARLY TERMINATION: All P(NAV+) < 50% in Phase 2")
        print("VERDICT: REJECT E7")
        print("=" * 70)

        output = {
            "config": {
                "staleness_bars": STALENESS_BARS,
                "mfe_thresholds": MFE_THRESHOLDS,
                "slow_periods": SLOW_PERIODS,
                "n_boot_p2": N_BOOT_P2,
                "n_boot_p3": N_BOOT_P3,
                "seed": SEED,
                "cost_bps_rt": round(CPS * 2 * 10000, 1),
                "trail_mult": TRAIL,
                "e5_cap_q": 0.90, "e5_cap_lb": 100, "e5_period": 20,
            },
            "phase1_real_screen": {
                "wins_vs_e0": wins_e0.tolist(),
                "wins_vs_e5": wins_e5.tolist(),
                "survivors": [(sb, mt, w) for sb, mt, w in survivors],
            },
            "phase2_sensitivity": {
                "p_nav_vs_e0": [[round(float(v), 4) for v in row] for row in p2["p_nav_vs_e0"]],
                "p_mdd_vs_e0": [[round(float(v), 4) for v in row] for row in p2["p_mdd_vs_e0"]],
                "p_nav_vs_e5": [[round(float(v), 4) for v in row] for row in p2["p_nav_vs_e5"]],
                "mean_adj_corr": round(p2["mean_adj_corr"], 4),
                "best_combo": list(p2["best_combo"]),
                "at_edge": bool(p2["at_edge"]),
                "e5_vs_e0_p_nav": round(p2["e5_vs_e0_p_nav"], 4),
                "e5_vs_e0_p_mdd": round(p2["e5_vs_e0_p_mdd"], 4),
            },
            "overall_verdict": "REJECT E7",
            "overall_reason": "All P(NAV+) < 50% in Phase 2 bootstrap sensitivity",
        }
        OUTDIR.mkdir(parents=True, exist_ok=True)
        with open(OUTDIR / "e7_study.json", "w") as f:
            json.dump(output, f, indent=2)
        print(f"\n  Saved: {OUTDIR / 'e7_study.json'}")
        el = time.time() - t_start
        print(f"  Total time: {el:.0f}s")
        sys.exit(0)

    top_combos = p2["top_combos"]
    if not top_combos:
        top_combos = [(survivors[0][0], survivors[0][1])]

    # ── Phase 3 ──
    combo_results = phase3_validation(
        cl, hi, lo, vo, tb, wi, n, top_combos, e0_real, e5_real, e7_navs
    )

    # ── Overall verdict ──
    print("\n" + "=" * 70)
    print("OVERALL VERDICT")
    print("=" * 70)

    any_accepted = False
    best_verdict = "REJECT"
    best_combo_key = None

    for ck, cr in combo_results.items():
        if cr["boot_pass"] and cr["real_pass"]:
            any_accepted = True
            if best_combo_key is None:
                best_combo_key = ck
                best_verdict = cr["verdict"]
            elif cr["binomial_tests"]["P(NAV+)>50%"]["p_binom"] < \
                 combo_results[best_combo_key]["binomial_tests"]["P(NAV+)>50%"]["p_binom"]:
                best_combo_key = ck
                best_verdict = cr["verdict"]

    if any_accepted:
        bc = combo_results[best_combo_key]
        overall = f"ACCEPT E7 — {best_verdict}"
        reason = (f"Best combo sb={bc['sb']}, mt={bc['mt']}: "
                  f"NAV binomial p={bc['binomial_tests']['P(NAV+)>50%']['p_binom']:.6f}, "
                  f"real {bc['binomial_tests']['Real ΔNAV>0']['wins']}/{len(SLOW_PERIODS)} wins")
        print(f"  {overall}")
        print(f"  {reason}")
    else:
        overall = "REJECT E7"
        reasons = []
        for ck, cr in combo_results.items():
            reasons.append(f"  {ck}: boot={'PASS' if cr['boot_pass'] else 'FAIL'}, "
                           f"real={'PASS' if cr['real_pass'] else 'FAIL'}")
        reason = "No combo passes dual (real + bootstrap) test"
        print(f"  {overall}")
        print(f"  {reason}")
        for r in reasons:
            print(r)

    # Interaction analysis
    print(f"\n  INTERACTION ANALYSIS:")
    print(f"    E5 alone (robust ATR): MDD PROVEN (16/16), NAV LOSES (0/16)")
    print(f"    E6 alone (staleness):  REJECTED (P(NAV+)=32.4%)")
    print(f"    E7 = E5 + E6:          {overall}")
    if not any_accepted:
        print(f"    → No positive interaction. Both components make exits earlier,")
        print(f"      compounding the CAGR loss without sufficient MDD benefit.")
    else:
        print(f"    → Interaction detected. Combined mechanism provides value")
        print(f"      that neither component achieves alone.")

    el_total = time.time() - t_start
    print(f"\n  Total time: {el_total:.0f}s ({el_total/60:.1f} min)")

    # ── Save JSON ──
    output = {
        "config": {
            "staleness_bars": STALENESS_BARS,
            "mfe_thresholds": MFE_THRESHOLDS,
            "slow_periods": SLOW_PERIODS,
            "n_boot_p2": N_BOOT_P2,
            "n_boot_p3": N_BOOT_P3,
            "seed": SEED,
            "cost_bps_rt": round(CPS * 2 * 10000, 1),
            "trail_mult": TRAIL,
            "vdo_threshold": VDO_THR,
            "e5_cap_q": 0.90, "e5_cap_lb": 100, "e5_period": 20,
        },
        "phase1_real_screen": {
            "wins_vs_e0": wins_e0.tolist(),
            "wins_vs_e5": wins_e5.tolist(),
            "survivors": [(sb, mt, w) for sb, mt, w in survivors],
            "e0_real": {str(sp): r for sp, r in e0_real.items()},
            "e5_real": {str(sp): r for sp, r in e5_real.items()},
        },
        "phase2_sensitivity": {
            "p_nav_vs_e0": [[round(float(v), 4) for v in row] for row in p2["p_nav_vs_e0"]],
            "p_mdd_vs_e0": [[round(float(v), 4) for v in row] for row in p2["p_mdd_vs_e0"]],
            "p_nav_vs_e5": [[round(float(v), 4) for v in row] for row in p2["p_nav_vs_e5"]],
            "median_sh_delta_vs_e0": [[round(float(v), 6) for v in row]
                                      for row in p2["median_sh_delta_vs_e0"]],
            "mean_adj_corr": round(p2["mean_adj_corr"], 4),
            "best_combo": list(p2["best_combo"]),
            "at_edge": bool(p2["at_edge"]),
            "e5_vs_e0_p_nav": round(p2["e5_vs_e0_p_nav"], 4),
            "e5_vs_e0_p_mdd": round(p2["e5_vs_e0_p_mdd"], 4),
        },
        "phase3_validation": combo_results,
        "overall_verdict": overall,
        "overall_reason": reason,
    }

    OUTDIR.mkdir(parents=True, exist_ok=True)
    outfile = OUTDIR / "e7_study.json"
    with open(outfile, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n  Saved: {outfile}")
    print("=" * 70)
