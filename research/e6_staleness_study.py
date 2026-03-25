#!/usr/bin/env python3
"""E6 Staleness Exit Study.

E6 = E0 + one additional exit condition (OR logic):
  After a trade reaches MFE >= MFE_THRESHOLD (in ATR units),
  if no new peak close within STALENESS_BARS bars, exit.

Hypothesis: Trends that stall after a significant move are about to
reverse.  Exiting early (before ATR trail triggers) preserves profit.

Risk: Same as ratcheting — premature exit during consolidation phases
that precede trend continuation. BTC trends commonly consolidate 2-5
days before resuming.

Method:
  Phase 1: Real data screen — 64 combos × 16 timescales (~1 sec)
  Phase 2: Bootstrap sensitivity — 500 paths × N=120 × 64 combos (~15 min)
  Phase 3: Full validation — 2000 paths × 16 timescales × top combos (~1-2 hr)

Acceptance: dual pass (real + bootstrap), binomial p<0.05, plateau,
no edge effect.

Primary metric: final NAV (as specified by user).
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

# E6 search space
STALENESS_BARS = [6, 12, 18, 24, 30, 36, 48, 60]
MFE_THRESHOLDS = [0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 5.0, 6.0]

OUTDIR = Path(__file__).resolve().parent / "results" / "e6_staleness"


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
# Simulation: E0 baseline (from sim_fast in timescale_robustness.py)
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

    # Force close
    if inp and bq > 0:
        cash = bq * cl[-1] * (1.0 - CPS)
        bq = 0.0
        nt += 1
        navs_end = cash

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
# Simulation: E6 staleness exit (E0 + staleness OR condition)
# ═══════════════════════════════════════════════════════════════════════

def sim_e6(cl, ef, es, at, vd, wi, stale_bars, mfe_thr):
    """VTREND E6: E0 + staleness exit.

    After a trade reaches MFE >= mfe_thr (in ATR units from entry),
    if price doesn't make a new peak close within stale_bars bars, exit.

    All E0 exits (ATR trail, EMA cross-down) remain via OR logic.
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
    entry_atr = 0.0
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

        a_val = at[i]
        if math.isnan(a_val) or math.isnan(ef[i]) or math.isnan(es[i]):
            continue

        if not inp:
            if ef[i] > es[i] and vd[i] > VDO_THR:
                pe = True
        else:
            # Track peak (same as E0)
            if p > pk:
                pk = p
                pk_bar = i

            # E0 exits (unchanged)
            if p < pk - TRAIL * a_val:
                px = True
            elif ef[i] < es[i]:
                px = True

            # E6 staleness exit (OR logic, only if E0 hasn't already triggered)
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
# Phase 1: Real data screen
# ═══════════════════════════════════════════════════════════════════════

def phase1_real_screen(cl, hi, lo, vo, tb, wi):
    """Run E0 and all 64 E6 combos on real data at 16 timescales.

    Returns:
      e0_navs: dict sp -> final_nav
      wins_heatmap: (8, 8) array of wins/16 for each (sb, mt) combo
      e6_navs: dict (sb, mt) -> dict sp -> final_nav
    """
    print("\n" + "=" * 70)
    print("PHASE 1: REAL DATA SCREEN (64 combos × 16 timescales)")
    print("=" * 70)

    at = _atr(hi, lo, cl, ATR_P)
    vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)

    n_sb = len(STALENESS_BARS)
    n_mt = len(MFE_THRESHOLDS)
    wins = np.zeros((n_sb, n_mt), dtype=int)

    e0_navs = {}
    e0_results = {}
    e6_navs = {}

    for sp in SLOW_PERIODS:
        fp = max(5, sp // 4)
        ef = _ema(cl, fp)
        es = _ema(cl, sp)

        r0 = sim_e0(cl, ef, es, at, vd, wi)
        e0_navs[sp] = r0["final_nav"]
        e0_results[sp] = r0

        for si, sb in enumerate(STALENESS_BARS):
            for mi, mt in enumerate(MFE_THRESHOLDS):
                r6 = sim_e6(cl, ef, es, at, vd, wi, sb, mt)
                key = (sb, mt)
                if key not in e6_navs:
                    e6_navs[key] = {}
                e6_navs[key][sp] = r6["final_nav"]
                if r6["final_nav"] > r0["final_nav"]:
                    wins[si, mi] += 1

    # Print heatmap
    n_sp = len(SLOW_PERIODS)
    print(f"\n  Wins/{n_sp} heatmap (rows=STALENESS_BARS, cols=MFE_THRESHOLD):")
    header = "  sb\\mt"
    for mt in MFE_THRESHOLDS:
        header += f"  {mt:5.1f}"
    print(header)
    print("  " + "-" * (7 + 7 * n_mt))
    for si, sb in enumerate(STALENESS_BARS):
        row = f"  {sb:4d} "
        for mi in range(n_mt):
            w = wins[si, mi]
            marker = " *" if w >= n_sp // 2 else "  "
            row += f"  {w:3d}{marker}"
        print(row)

    # Survivors: combos with >= 8/16 wins
    survivors = []
    for si, sb in enumerate(STALENESS_BARS):
        for mi, mt in enumerate(MFE_THRESHOLDS):
            if wins[si, mi] >= n_sp // 2:
                survivors.append((sb, mt, int(wins[si, mi])))

    print(f"\n  Survivors (>= {n_sp // 2}/{n_sp} wins): {len(survivors)}")
    for sb, mt, w in survivors:
        print(f"    sb={sb:3d}, mt={mt:.1f}: {w}/{n_sp} wins")

    # E0 summary
    print(f"\n  E0 baseline across timescales:")
    for sp in SLOW_PERIODS:
        r = e0_results[sp]
        print(f"    sp={sp:4d}: NAV=${r['final_nav']:>10,.0f}  "
              f"Sharpe={r['sharpe']:+.3f}  CAGR={r['cagr']:+.1f}%  MDD={r['mdd']:.1f}%")

    # Verification: E6 with extreme params should match E0 closely
    sb_max, mt_max = STALENESS_BARS[-1], MFE_THRESHOLDS[-1]
    key_extreme = (sb_max, mt_max)
    if key_extreme in e6_navs:
        print(f"\n  Verification: E6(sb={sb_max}, mt={mt_max}) vs E0")
        n_match = 0
        for sp in SLOW_PERIODS:
            nav_e0 = e0_navs[sp]
            nav_e6 = e6_navs[key_extreme][sp]
            diff_pct = abs(nav_e6 - nav_e0) / max(nav_e0, 1) * 100
            if diff_pct < 1.0:
                n_match += 1
        print(f"    {n_match}/{n_sp} timescales within 1% of E0 "
              f"(extreme params rarely activate)")

    return e0_navs, wins, e6_navs, survivors


# ═══════════════════════════════════════════════════════════════════════
# Phase 2: Bootstrap sensitivity at N=120
# ═══════════════════════════════════════════════════════════════════════

def phase2_sensitivity(cl, hi, lo, vo, tb, wi, n):
    """500 paths × N=120 × 64 combos + E0. Build sensitivity heatmaps."""
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

    # Storage: final_nav for E0 and each E6 combo
    nav_e0 = np.zeros(N_BOOT_P2)
    nav_e6 = np.zeros((N_BOOT_P2, n_sb, n_mt))
    sh_e0 = np.zeros(N_BOOT_P2)
    sh_e6 = np.zeros((N_BOOT_P2, n_sb, n_mt))

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
        ef = _ema(c, FP)
        es = _ema(c, SP)

        r0 = sim_e0(c, ef, es, at, vd, wi)
        nav_e0[b] = r0["final_nav"]
        sh_e0[b] = r0["sharpe"]

        for si, sb in enumerate(STALENESS_BARS):
            for mi, mt in enumerate(MFE_THRESHOLDS):
                r6 = sim_e6(c, ef, es, at, vd, wi, sb, mt)
                nav_e6[b, si, mi] = r6["final_nav"]
                sh_e6[b, si, mi] = r6["sharpe"]

    el = time.time() - t0
    print(f"\n  Done: {el:.1f}s ({N_BOOT_P2 * (1 + n_sb * n_mt)} sims)")

    # Build heatmaps
    p_nav_plus = np.zeros((n_sb, n_mt))
    median_nav_delta = np.zeros((n_sb, n_mt))
    median_sh_delta = np.zeros((n_sb, n_mt))

    for si in range(n_sb):
        for mi in range(n_mt):
            d_nav = nav_e6[:, si, mi] - nav_e0
            d_sh = sh_e6[:, si, mi] - sh_e0
            p_nav_plus[si, mi] = float(np.mean(d_nav > 0))
            median_nav_delta[si, mi] = float(np.median(d_nav))
            median_sh_delta[si, mi] = float(np.median(d_sh))

    # Print P(NAV+) heatmap
    print(f"\n  P(E6 NAV > E0 NAV) heatmap:")
    header = "  sb\\mt"
    for mt in MFE_THRESHOLDS:
        header += f"  {mt:5.1f}"
    print(header)
    print("  " + "-" * (7 + 7 * n_mt))
    for si, sb in enumerate(STALENESS_BARS):
        row = f"  {sb:4d} "
        for mi in range(n_mt):
            pv = p_nav_plus[si, mi] * 100
            row += f"  {pv:5.1f}"
        print(row)

    # Print median Sharpe delta heatmap
    print(f"\n  Median Sharpe delta (E6 - E0) heatmap:")
    header = "  sb\\mt"
    for mt in MFE_THRESHOLDS:
        header += f"  {mt:5.1f}"
    print(header)
    print("  " + "-" * (7 + 7 * n_mt))
    for si, sb in enumerate(STALENESS_BARS):
        row = f"  {sb:4d} "
        for mi in range(n_mt):
            dsh = median_sh_delta[si, mi]
            row += f" {dsh:+6.4f}" if abs(dsh) < 1 else f" {dsh:+6.2f}"
        print(row)

    # Plateau detection: adjacent parameter correlation
    # Row correlation (adjacent staleness bars)
    row_corrs = []
    for si in range(n_sb - 1):
        r = np.corrcoef(p_nav_plus[si, :], p_nav_plus[si + 1, :])[0, 1]
        if not np.isnan(r):
            row_corrs.append(r)
    # Column correlation (adjacent MFE thresholds)
    col_corrs = []
    for mi in range(n_mt - 1):
        r = np.corrcoef(p_nav_plus[:, mi], p_nav_plus[:, mi + 1])[0, 1]
        if not np.isnan(r):
            col_corrs.append(r)

    mean_adj_corr = 0.0
    all_corrs = row_corrs + col_corrs
    if all_corrs:
        mean_adj_corr = float(np.mean(all_corrs))

    print(f"\n  Plateau analysis:")
    print(f"    Row adj corr (staleness):  "
          f"{np.mean(row_corrs):.3f}" if row_corrs else "    Row adj corr: N/A")
    print(f"    Col adj corr (MFE thr):    "
          f"{np.mean(col_corrs):.3f}" if col_corrs else "    Col adj corr: N/A")
    print(f"    Overall adj corr:          {mean_adj_corr:.3f}")
    if mean_adj_corr > 0.5:
        print(f"    → SMOOTH PLATEAU (corr > 0.5)")
    else:
        print(f"    → FRAGILE / NOISY surface (corr <= 0.5)")

    # Edge check: is the best combo at the grid boundary?
    best_idx = np.unravel_index(np.argmax(p_nav_plus), p_nav_plus.shape)
    best_sb = STALENESS_BARS[best_idx[0]]
    best_mt = MFE_THRESHOLDS[best_idx[1]]
    at_edge = (best_idx[0] == 0 or best_idx[0] == n_sb - 1 or
               best_idx[1] == 0 or best_idx[1] == n_mt - 1)

    print(f"\n  Best combo: sb={best_sb}, mt={best_mt} "
          f"(P(NAV+)={p_nav_plus[best_idx]*100:.1f}%)")
    print(f"  At grid edge: {'YES — FLAG FOR EXPANSION' if at_edge else 'NO — interior'}")

    # Select top combos for Phase 3 (from plateau center, P(NAV+) > 50%)
    candidates = []
    for si in range(n_sb):
        for mi in range(n_mt):
            if p_nav_plus[si, mi] > 0.50:
                candidates.append((si, mi, p_nav_plus[si, mi]))

    # Sort by P(NAV+), take top 5
    candidates.sort(key=lambda x: x[2], reverse=True)
    top_combos = [(STALENESS_BARS[si], MFE_THRESHOLDS[mi])
                  for si, mi, _ in candidates[:5]]

    print(f"\n  Top combos for Phase 3 ({len(candidates)} with P(NAV+)>50%):")
    for si, mi, pv in candidates[:5]:
        print(f"    sb={STALENESS_BARS[si]:3d}, mt={MFE_THRESHOLDS[mi]:.1f}: "
              f"P(NAV+)={pv*100:.1f}%, medΔSh={median_sh_delta[si, mi]:+.4f}")

    return {
        "p_nav_plus": p_nav_plus,
        "median_nav_delta": median_nav_delta,
        "median_sh_delta": median_sh_delta,
        "mean_adj_corr": mean_adj_corr,
        "best_combo": (best_sb, best_mt),
        "at_edge": at_edge,
        "top_combos": top_combos,
        "all_p_nav_plus_above_50": len(candidates) > 0,
    }


# ═══════════════════════════════════════════════════════════════════════
# Phase 3: Full bootstrap validation
# ═══════════════════════════════════════════════════════════════════════

def phase3_validation(cl, hi, lo, vo, tb, wi, n, top_combos, e0_real_navs, e6_real_navs):
    """2000 paths × 16 timescales × selected combos + E0."""
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

    # Storage
    boot_e0 = {m: np.zeros((N_BOOT_P3, n_sp)) for m in mkeys}
    boot_e6 = {k: {m: np.zeros((N_BOOT_P3, n_sp)) for m in mkeys}
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

        for j, sp in enumerate(SLOW_PERIODS):
            fp = max(5, sp // 4)
            ef = _ema(c, fp)
            es = _ema(c, sp)

            r0 = sim_e0(c, ef, es, at, vd, wi)
            for m in mkeys:
                boot_e0[m][b, j] = r0[m]

            for combo in top_combos:
                sb, mt = combo
                r6 = sim_e6(c, ef, es, at, vd, wi, sb, mt)
                for m in mkeys:
                    boot_e6[combo][m][b, j] = r6[m]

    el = time.time() - t0
    n_total = N_BOOT_P3 * n_sp * (1 + n_combos)
    print(f"\n  Done: {el:.1f}s ({n_total} sims, {n_total / el:.0f} sims/sec)")

    # ── Per-combo analysis ──
    combo_results = {}
    for combo in top_combos:
        sb, mt = combo
        combo_key = f"sb{sb}_mt{mt}"
        print(f"\n  {'─' * 60}")
        print(f"  E6 combo: sb={sb}, mt={mt}")
        print(f"  {'─' * 60}")

        print(f"\n  {'sp':>5}  {'days':>5}  "
              f"{'P(NAV+)':>8}  {'P(Sh+)':>7}  {'P(CAGR+)':>9}  {'P(MDD-)':>8}  "
              f"{'medΔNAV%':>9}  real_ΔNAV%")
        print("  " + "-" * 75)

        win_nav = 0
        win_sharpe = 0
        win_cagr = 0
        win_mdd = 0
        win_real = 0

        per_ts = []
        for j, sp in enumerate(SLOW_PERIODS):
            days = sp * 4 / 24

            d_nav = boot_e6[combo]["final_nav"][:, j] - boot_e0["final_nav"][:, j]
            d_sh = boot_e6[combo]["sharpe"][:, j] - boot_e0["sharpe"][:, j]
            d_cg = boot_e6[combo]["cagr"][:, j] - boot_e0["cagr"][:, j]
            d_md = boot_e0["mdd"][:, j] - boot_e6[combo]["mdd"][:, j]

            p_nav = float(np.mean(d_nav > 0))
            p_sh = float(np.mean(d_sh > 0))
            p_cg = float(np.mean(d_cg > 0))
            p_md = float(np.mean(d_md > 0))

            if p_nav > 0.50: win_nav += 1
            if p_sh > 0.50: win_sharpe += 1
            if p_cg > 0.50: win_cagr += 1
            if p_md > 0.50: win_mdd += 1

            # Real data comparison
            nav_e0_real = e0_real_navs.get(sp, 0)
            nav_e6_real = e6_real_navs.get((sb, mt), {}).get(sp, 0)
            real_delta = (nav_e6_real / max(nav_e0_real, 1) - 1) * 100
            if real_delta > 0:
                win_real += 1

            # Ratio-based median ΔNAV%
            nav_ratio = boot_e6[combo]["final_nav"][:, j] / np.maximum(boot_e0["final_nav"][:, j], 1)
            med_nav_pct = float((np.median(nav_ratio) - 1) * 100)

            print(f"  {sp:5d}  {days:5.0f}  "
                  f"{p_nav*100:7.1f}%  {p_sh*100:6.1f}%  {p_cg*100:8.1f}%  "
                  f"{p_md*100:7.1f}%  {med_nav_pct:+8.2f}%  {real_delta:+.1f}%")

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

        # Dual pass check
        boot_pass = binom["P(NAV+)>50%"]["p_binom"] < 0.05
        real_pass = win_real >= 9  # at least 9/16

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

    print("E6 STALENESS EXIT STUDY")
    print("=" * 70)
    print(f"  E6 = E0 + staleness exit:")
    print(f"    After MFE >= threshold (ATR units), if no new peak")
    print(f"    close within N bars → exit.")
    print(f"  Search space: {len(STALENESS_BARS)} × {len(MFE_THRESHOLDS)} = "
          f"{len(STALENESS_BARS) * len(MFE_THRESHOLDS)} combos")
    print(f"  Primary metric: final NAV")

    # ── Load data ──
    cl, hi, lo, vo, tb, wi, n = load_arrays()
    print(f"\n  Data: {n} H4 bars, warmup index={wi}")

    # ── Phase 1 ──
    e0_navs, wins_heatmap, e6_navs, survivors = phase1_real_screen(
        cl, hi, lo, vo, tb, wi
    )

    if not survivors:
        print("\n" + "=" * 70)
        print("EARLY TERMINATION: Zero survivors in Phase 1")
        print("No E6 combo wins at >= 8/16 timescales on real data.")
        print("VERDICT: REJECT E6")
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
            },
            "phase1_real_screen": {
                "wins_heatmap": wins_heatmap.tolist(),
                "survivors": [],
            },
            "overall_verdict": "REJECT E6",
            "overall_reason": "Zero survivors in Phase 1 real data screen",
        }
        OUTDIR.mkdir(parents=True, exist_ok=True)
        with open(OUTDIR / "e6_staleness.json", "w") as f:
            json.dump(output, f, indent=2)
        print(f"\n  Saved: {OUTDIR / 'e6_staleness.json'}")
        sys.exit(0)

    # ── Phase 2 ──
    p2 = phase2_sensitivity(cl, hi, lo, vo, tb, wi, n)

    if not p2["all_p_nav_plus_above_50"]:
        print("\n" + "=" * 70)
        print("EARLY TERMINATION: All P(NAV+) < 50% in Phase 2")
        print("VERDICT: REJECT E6")
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
            },
            "phase1_real_screen": {
                "wins_heatmap": wins_heatmap.tolist(),
                "survivors": [(sb, mt, w) for sb, mt, w in survivors],
            },
            "phase2_sensitivity": {
                "p_nav_plus": p2["p_nav_plus"].tolist(),
                "median_sh_delta": p2["median_sh_delta"].tolist(),
                "mean_adj_corr": p2["mean_adj_corr"],
                "best_combo": list(p2["best_combo"]),
                "at_edge": bool(p2["at_edge"]),
            },
            "overall_verdict": "REJECT E6",
            "overall_reason": "All P(NAV+) < 50% in Phase 2 bootstrap sensitivity",
        }
        OUTDIR.mkdir(parents=True, exist_ok=True)
        with open(OUTDIR / "e6_staleness.json", "w") as f:
            json.dump(output, f, indent=2)
        print(f"\n  Saved: {OUTDIR / 'e6_staleness.json'}")
        sys.exit(0)

    top_combos = p2["top_combos"]
    if not top_combos:
        top_combos = [(survivors[0][0], survivors[0][1])]

    # ── Phase 3 ──
    combo_results = phase3_validation(
        cl, hi, lo, vo, tb, wi, n, top_combos, e0_navs, e6_navs
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
        overall = f"ACCEPT E6 — {best_verdict}"
        reason = (f"Best combo sb={bc['sb']}, mt={bc['mt']}: "
                  f"NAV binomial p={bc['binomial_tests']['P(NAV+)>50%']['p_binom']:.6f}, "
                  f"real {bc['binomial_tests']['Real ΔNAV>0']['wins']}/{len(SLOW_PERIODS)} wins")
        print(f"  {overall}")
        print(f"  {reason}")
    else:
        overall = "REJECT E6"
        reasons = []
        for ck, cr in combo_results.items():
            reasons.append(f"  {ck}: boot={'PASS' if cr['boot_pass'] else 'FAIL'}, "
                           f"real={'PASS' if cr['real_pass'] else 'FAIL'}")
        reason = "No combo passes dual (real + bootstrap) test"
        print(f"  {overall}")
        print(f"  {reason}")
        for r in reasons:
            print(r)

    # Plateau and edge summary
    print(f"\n  Plateau (adj corr): {p2['mean_adj_corr']:.3f} "
          f"({'smooth' if p2['mean_adj_corr'] > 0.5 else 'fragile'})")
    print(f"  Best at edge: {'YES' if p2['at_edge'] else 'NO'}")

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
        },
        "phase1_real_screen": {
            "wins_heatmap": wins_heatmap.tolist(),
            "survivors": [(sb, mt, w) for sb, mt, w in survivors],
            "e0_navs": {str(sp): nav for sp, nav in e0_navs.items()},
        },
        "phase2_sensitivity": {
            "p_nav_plus": [[round(float(v), 4) for v in row] for row in p2["p_nav_plus"]],
            "median_sh_delta": [[round(float(v), 6) for v in row] for row in p2["median_sh_delta"]],
            "median_nav_delta": [[round(float(v), 2) for v in row] for row in p2["median_nav_delta"]],
            "mean_adj_corr": round(p2["mean_adj_corr"], 4),
            "best_combo": list(p2["best_combo"]),
            "at_edge": bool(p2["at_edge"]),
            "top_combos": [list(c) for c in top_combos],
        },
        "phase3_validation": combo_results,
        "overall_verdict": overall,
        "overall_reason": reason,
    }

    OUTDIR.mkdir(parents=True, exist_ok=True)
    outfile = OUTDIR / "e6_staleness.json"
    with open(outfile, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n  Saved: {outfile}")
