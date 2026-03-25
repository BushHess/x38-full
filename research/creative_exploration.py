#!/usr/bin/env python3
"""
Creative Exploration: Learn from 10 failures, test remaining hypotheses.

Meta-lesson: All 10 alternatives tried to MODIFY the proven signal.
             None tried to COMBINE the unchanged signal across timescales.

Hypothesis A: Multi-timescale ensemble portfolio
  - Run K independent VTREND instances at different slow_periods
  - Each gets 1/K of capital, fully independent
  - Portfolio NAV = sum of individual NAVs
  - Diversification from ENTRY/EXIT TIMING differences across timescales
  - Math: Sharpe_p = S * sqrt(K / (1 + (K-1)*rho))
  - If rho < 1.0, portfolio Sharpe > individual Sharpe

Hypothesis B: Trail-only exit (E7)
  - Remove EMA cross-down exit, keep ONLY ATR trail
  - Rationale: EMA cross-down may exit too early during temporary dips
  - Simplification (1 exit vs 2) — aligns with "complexity hurts" finding
  - Counter: EMA cross-down is proven as entry signal, cross-down = valid exit

Both tested: real data first, then bootstrap paired comparison.
"""

import sys, os, time, math
import numpy as np
from scipy.stats import binomtest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from timescale_robustness import load_arrays, _atr, _ema, _vdo, SLOW_PERIODS
from research.lib.vcbb import make_ratios, precompute_vcbb, gen_path_vcbb

# ═══════════════════════════════════════════════════════════════════
# Constants (identical to all studies)
# ═══════════════════════════════════════════════════════════════════
CASH   = 10_000.0
CPS    = 0.0025       # 50 bps round-trip → 25 bps per side
TRAIL  = 3.0
VDO_THR = 0.0
ATR_P  = 14
VDO_F, VDO_S = 12, 28
ANN    = math.sqrt(6.0 * 365.25)
BLKSZ  = 60
SEED   = 42

# ═══════════════════════════════════════════════════════════════════
# Simulation: returns NAV time series (needed for portfolio)
# ═══════════════════════════════════════════════════════════════════

def sim_nav_series(cl, ef, es, at, vd, wi, trail_only=False):
    """Run E0 (or trail-only E7) and return per-bar NAV array.

    Returns: numpy array of length len(cl), NAV at each bar.
    """
    n = len(cl)
    cash = CASH
    bq = 0.0
    inp = False
    pe = False
    px = False
    pk = 0.0
    nt = 0

    navs = np.full(n, CASH)

    for i in range(n):
        p = cl[i]

        if i > 0:
            fp = cl[i - 1]  # fill price
            if pe:
                pe = False
                bq = cash / (fp * (1.0 + CPS))
                cash = 0.0
                inp = True
                pk = p
            elif px:
                px = False
                cash = bq * fp * (1.0 - CPS)
                bq = 0.0
                inp = False
                nt += 1

        # NAV
        nav = cash + bq * p if inp else cash
        navs[i] = nav

        a_val = at[i]
        if math.isnan(a_val) or math.isnan(ef[i]) or math.isnan(es[i]):
            continue

        if i < wi:
            continue

        if not inp:
            if ef[i] > es[i] and vd[i] > VDO_THR:
                pe = True
        else:
            pk = max(pk, p)
            if p < pk - TRAIL * a_val:
                px = True
            elif not trail_only and ef[i] < es[i]:
                px = True

    # Force close
    if inp and bq > 0:
        cash = bq * cl[-1] * (1.0 - CPS)
        navs[-1] = cash
        nt += 1

    return navs, nt


def metrics_from_navs(navs, wi):
    """Compute standard metrics from a NAV time series."""
    # Skip warmup
    active = navs[wi:]
    n = len(active)
    if n < 10:
        return {"sharpe": 0, "cagr": -100, "mdd": 100, "calmar": 0,
                "trades": 0, "final_nav": active[-1] if n > 0 else CASH}

    # Returns
    rets = active[1:] / active[:-1] - 1.0
    n_rets = len(rets)
    if n_rets < 2:
        return {"sharpe": 0, "cagr": -100, "mdd": 100, "calmar": 0,
                "trades": 0, "final_nav": active[-1]}

    # Sharpe
    mu = np.mean(rets)
    std = np.std(rets, ddof=0)
    sharpe = (mu / std * ANN) if std > 1e-12 else 0.0

    # CAGR
    tr = active[-1] / active[0] - 1.0
    yrs = n_rets / (6.0 * 365.25)
    cagr = ((1 + tr) ** (1.0 / yrs) - 1.0) * 100 if yrs > 0 and tr > -1 else -100.0

    # MDD
    peak = np.maximum.accumulate(active)
    dd = 1.0 - active / peak
    mdd = np.max(dd) * 100.0

    calmar = cagr / mdd if mdd > 0.01 else 0.0

    return {
        "sharpe": sharpe,
        "cagr": cagr,
        "mdd": mdd,
        "calmar": calmar,
        "final_nav": active[-1],
    }


# ═══════════════════════════════════════════════════════════════════
# Phase 0: Cross-timescale correlation (diagnostic)
# ═══════════════════════════════════════════════════════════════════

def phase0_correlation(cl, hi, lo, vo, tb, wi):
    """Compute cross-timescale trade overlap and NAV correlation on real data."""
    print("\n" + "=" * 90)
    print("PHASE 0: CROSS-TIMESCALE CORRELATION DIAGNOSTIC")
    print("=" * 90)

    # Use plateau timescales
    plateau_sps = [60, 84, 96, 120, 144, 168]
    K = len(plateau_sps)

    at = _atr(hi, lo, cl, ATR_P)
    vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)

    # Get NAV series for each timescale
    nav_dict = {}
    trade_dict = {}
    for sp in plateau_sps:
        fp = max(5, sp // 4)
        ef = _ema(cl, fp)
        es = _ema(cl, sp)
        navs, nt = sim_nav_series(cl, ef, es, at, vd, wi)
        nav_dict[sp] = navs
        trade_dict[sp] = nt
        m = metrics_from_navs(navs, wi)
        print(f"  N={sp:4d}: Sharpe={m['sharpe']:6.3f}  CAGR={m['cagr']:6.1f}%  "
              f"MDD={m['mdd']:5.1f}%  trades={nt}")

    # Compute daily return correlations
    print(f"\n  Return correlation matrix (post-warmup):")
    nav_arr = np.array([nav_dict[sp][wi:] for sp in plateau_sps])
    ret_arr = nav_arr[:, 1:] / nav_arr[:, :-1] - 1.0

    corr = np.corrcoef(ret_arr)
    print(f"  {'':>6s}", "  ".join(f"N={sp:3d}" for sp in plateau_sps))
    for i, sp_i in enumerate(plateau_sps):
        row = "  ".join(f"{corr[i,j]:6.3f}" for j in range(K))
        print(f"  N={sp_i:3d}  {row}")

    # Average pairwise correlation
    mask = np.triu(np.ones((K, K), dtype=bool), k=1)
    avg_corr = corr[mask].mean()
    min_corr = corr[mask].min()
    max_corr = corr[mask].max()
    print(f"\n  Average pairwise correlation: {avg_corr:.4f}")
    print(f"  Range: [{min_corr:.4f}, {max_corr:.4f}]")

    # Theoretical portfolio Sharpe improvement
    avg_sharpe = np.mean([metrics_from_navs(nav_dict[sp], wi)['sharpe']
                          for sp in plateau_sps])
    sharpe_ratio = math.sqrt(K / (1 + (K - 1) * avg_corr))
    print(f"\n  Theoretical portfolio Sharpe multiplier: {sharpe_ratio:.4f}")
    print(f"  Individual avg Sharpe: {avg_sharpe:.3f}")
    print(f"  Theoretical portfolio Sharpe: {avg_sharpe * sharpe_ratio:.3f}")
    print(f"  Expected improvement: {(sharpe_ratio - 1) * 100:+.1f}%")

    # Trade overlap: what fraction of bars do instances overlap?
    in_trade = {}
    for sp in plateau_sps:
        navs = nav_dict[sp]
        # Detect in-trade: NAV changes != 0 when price changes
        # Simple proxy: position detection from NAV
        diffs = np.diff(navs[wi:])
        price_diffs = np.diff(cl[wi:])
        # In trade when NAV moves with price
        in_pos = np.abs(diffs) > 1e-6
        in_trade[sp] = in_pos

    # Pairwise trade overlap
    print(f"\n  Trade overlap matrix (fraction of bars both in position):")
    overlaps = np.zeros((K, K))
    for i, sp_i in enumerate(plateau_sps):
        for j, sp_j in enumerate(plateau_sps):
            both = np.mean(in_trade[sp_i] & in_trade[sp_j])
            overlaps[i, j] = both

    print(f"  {'':>6s}", "  ".join(f"N={sp:3d}" for sp in plateau_sps))
    for i, sp_i in enumerate(plateau_sps):
        row = "  ".join(f"{overlaps[i,j]:6.1%}" for j in range(K))
        print(f"  N={sp_i:3d}  {row}")

    avg_overlap = overlaps[mask].mean()
    print(f"\n  Average pairwise overlap: {avg_overlap:.1%}")

    return avg_corr, plateau_sps, nav_dict


# ═══════════════════════════════════════════════════════════════════
# Phase 1: Real data test (E0 vs multi-timescale vs E7)
# ═══════════════════════════════════════════════════════════════════

def phase1_real(cl, hi, lo, vo, tb, wi, plateau_sps, nav_dict):
    """Compare on real data across 16 timescales."""
    print("\n" + "=" * 90)
    print("PHASE 1: REAL DATA — E0 vs MULTI-TIMESCALE vs E7 (TRAIL-ONLY)")
    print("=" * 90)

    at = _atr(hi, lo, cl, ATR_P)
    vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)

    # E7: trail-only exit across 16 timescales
    print(f"\n  {'SP':>5s} {'E0-Sh':>7s} {'E0-CAGR':>8s} {'E0-MDD':>7s} "
          f"{'E7-Sh':>7s} {'E7-CAGR':>8s} {'E7-MDD':>7s}  E7>E0?")
    print("  " + "-" * 75)

    e7_wins_sharpe = 0
    e7_wins_nav = 0

    for sp in SLOW_PERIODS:
        fp = max(5, sp // 4)
        ef = _ema(cl, fp)
        es = _ema(cl, sp)

        navs_e0, nt_e0 = sim_nav_series(cl, ef, es, at, vd, wi, trail_only=False)
        navs_e7, nt_e7 = sim_nav_series(cl, ef, es, at, vd, wi, trail_only=True)

        m0 = metrics_from_navs(navs_e0, wi)
        m7 = metrics_from_navs(navs_e7, wi)

        sh_win = "+" if m7['sharpe'] > m0['sharpe'] else "-"
        if m7['sharpe'] > m0['sharpe']:
            e7_wins_sharpe += 1
        if m7['final_nav'] > m0['final_nav']:
            e7_wins_nav += 1

        print(f"  {sp:5d} {m0['sharpe']:7.3f} {m0['cagr']:7.1f}% {m0['mdd']:6.1f}%  "
              f"{m7['sharpe']:7.3f} {m7['cagr']:7.1f}% {m7['mdd']:6.1f}%  {sh_win}")

    print(f"\n  E7 wins Sharpe: {e7_wins_sharpe}/16")
    print(f"  E7 wins NAV:    {e7_wins_nav}/16")

    # Multi-timescale portfolio on real data at all 16 timescales as "reference"
    # The portfolio itself IS the combination of plateau timescales
    print("\n  --- MULTI-TIMESCALE ENSEMBLE (plateau: {}) ---".format(
        ", ".join(str(s) for s in plateau_sps)))

    K = len(plateau_sps)
    # Portfolio NAV = mean of individual NAVs at plateau timescales
    port_navs = np.mean([nav_dict[sp] for sp in plateau_sps], axis=0)
    m_port = metrics_from_navs(port_navs, wi)

    # Compare to individual timescales in plateau
    print(f"\n  {'Source':>12s} {'Sharpe':>7s} {'CAGR':>7s} {'MDD':>6s} {'FinalNAV':>10s}")
    print("  " + "-" * 50)
    for sp in plateau_sps:
        m = metrics_from_navs(nav_dict[sp], wi)
        print(f"  {'N='+str(sp):>12s} {m['sharpe']:7.3f} {m['cagr']:6.1f}% {m['mdd']:5.1f}% {m['final_nav']:10.0f}")

    print(f"  {'ENSEMBLE':>12s} {m_port['sharpe']:7.3f} {m_port['cagr']:6.1f}% "
          f"{m_port['mdd']:5.1f}% {m_port['final_nav']:10.0f}")

    # Also compare to E0 at N=120 (the default)
    m120 = metrics_from_navs(nav_dict[120], wi)
    print(f"\n  Ensemble vs E0@120:")
    print(f"    Sharpe: {m_port['sharpe']:.3f} vs {m120['sharpe']:.3f} "
          f"({(m_port['sharpe']/m120['sharpe']-1)*100:+.1f}%)")
    print(f"    CAGR:   {m_port['cagr']:.1f}% vs {m120['cagr']:.1f}%")
    print(f"    MDD:    {m_port['mdd']:.1f}% vs {m120['mdd']:.1f}%")

    return e7_wins_sharpe, e7_wins_nav, m_port, m120


# ═══════════════════════════════════════════════════════════════════
# Phase 2: Bootstrap paired comparison
# ═══════════════════════════════════════════════════════════════════

def phase2_bootstrap(cl, hi, lo, vo, tb, wi, n, plateau_sps,
                     test_ensemble, test_e7):
    """Bootstrap: compare strategies across 16 timescales."""
    N_BOOT = 500
    print("\n" + "=" * 90)
    things = []
    if test_ensemble:
        things.append("ENSEMBLE")
    if test_e7:
        things.append("E7")
    print(f"PHASE 2: BOOTSTRAP ({N_BOOT} paths × 16 timescales) — {' & '.join(things)} vs E0")
    print("=" * 90)

    cr, hr, lr, vol, tbb = make_ratios(cl, hi, lo, vo, tb)
    vcbb_state = precompute_vcbb(cr, blksz=BLKSZ, ctx=90)
    n_trans = n - 1
    p0 = cl[0]
    rng = np.random.default_rng(SEED)

    n_sp = len(SLOW_PERIODS)
    K = len(plateau_sps)

    # Storage
    sh_e0 = np.zeros((N_BOOT, n_sp))
    mdd_e0 = np.zeros((N_BOOT, n_sp))
    nav_e0 = np.zeros((N_BOOT, n_sp))
    cagr_e0 = np.zeros((N_BOOT, n_sp))

    if test_e7:
        sh_e7 = np.zeros((N_BOOT, n_sp))
        mdd_e7 = np.zeros((N_BOOT, n_sp))
        nav_e7 = np.zeros((N_BOOT, n_sp))
        cagr_e7 = np.zeros((N_BOOT, n_sp))

    if test_ensemble:
        sh_ens = np.zeros((N_BOOT, n_sp))
        mdd_ens = np.zeros((N_BOOT, n_sp))
        nav_ens = np.zeros((N_BOOT, n_sp))
        cagr_ens = np.zeros((N_BOOT, n_sp))

    t0 = time.time()
    for b in range(N_BOOT):
        if (b + 1) % 50 == 0 or b == 0:
            el = time.time() - t0
            rate = (b + 1) / el if el > 0 else 1
            eta = (N_BOOT - b - 1) / rate
            print(f"  {b+1:5d}/{N_BOOT}  ({el:.0f}s, ~{eta:.0f}s left)")

        c, h, l, v, t = gen_path_vcbb(cr, hr, lr, vol, tbb, n_trans, BLKSZ, p0, rng, vcbb=vcbb_state)
        at = _atr(h, l, c, ATR_P)
        vd = _vdo(c, h, l, v, t, VDO_F, VDO_S)

        # For ensemble: collect NAV series at plateau timescales
        if test_ensemble:
            ensemble_navs_per_sp = {}  # sp -> nav_series

        for j, sp in enumerate(SLOW_PERIODS):
            fp = max(5, sp // 4)
            ef = _ema(c, fp)
            es = _ema(c, sp)

            navs_0, _ = sim_nav_series(c, ef, es, at, vd, wi, trail_only=False)
            m0 = metrics_from_navs(navs_0, wi)
            sh_e0[b, j] = m0['sharpe']
            mdd_e0[b, j] = m0['mdd']
            nav_e0[b, j] = m0['final_nav']
            cagr_e0[b, j] = m0['cagr']

            if test_e7:
                navs_7, _ = sim_nav_series(c, ef, es, at, vd, wi, trail_only=True)
                m7 = metrics_from_navs(navs_7, wi)
                sh_e7[b, j] = m7['sharpe']
                mdd_e7[b, j] = m7['mdd']
                nav_e7[b, j] = m7['final_nav']
                cagr_e7[b, j] = m7['cagr']

            # Collect for ensemble
            if test_ensemble and sp in plateau_sps:
                ensemble_navs_per_sp[sp] = navs_0

        # Compute ensemble metrics at each "reference timescale"
        # Ensemble is ALWAYS the same K instances — we compare it to each single sp
        if test_ensemble and len(ensemble_navs_per_sp) == K:
            port_navs = np.mean([ensemble_navs_per_sp[sp] for sp in plateau_sps], axis=0)
            m_ens = metrics_from_navs(port_navs, wi)
            # Store ensemble vs each timescale
            for j, sp in enumerate(SLOW_PERIODS):
                sh_ens[b, j] = m_ens['sharpe']
                mdd_ens[b, j] = m_ens['mdd']
                nav_ens[b, j] = m_ens['final_nav']
                cagr_ens[b, j] = m_ens['cagr']

    el = time.time() - t0
    print(f"\n  Done: {el:.1f}s")

    # ── E7 results ──
    if test_e7:
        print(f"\n  --- E7 (trail-only) vs E0 ---")
        print(f"  {'SP':>5s} {'P(Sh+)':>8s} {'P(CAGR+)':>8s} {'P(MDD-)':>8s} {'P(NAV+)':>8s}")
        w_sh, w_cagr, w_mdd, w_nav = 0, 0, 0, 0
        for j, sp in enumerate(SLOW_PERIODS):
            p_sh = np.mean(sh_e7[:, j] > sh_e0[:, j])
            p_cagr = np.mean(cagr_e7[:, j] > cagr_e0[:, j])
            p_mdd = np.mean(mdd_e7[:, j] < mdd_e0[:, j])
            p_nav = np.mean(nav_e7[:, j] > nav_e0[:, j])
            if p_sh > 0.5: w_sh += 1
            if p_cagr > 0.5: w_cagr += 1
            if p_mdd > 0.5: w_mdd += 1
            if p_nav > 0.5: w_nav += 1
            print(f"  {sp:5d} {p_sh:8.1%} {p_cagr:8.1%} {p_mdd:8.1%} {p_nav:8.1%}")

        print(f"\n  E7 wins/16: Sharpe={w_sh} CAGR={w_cagr} MDD={w_mdd} NAV={w_nav}")
        for lbl, w in [("Sharpe", w_sh), ("CAGR", w_cagr), ("MDD", w_mdd), ("NAV", w_nav)]:
            bt = binomtest(w, 16, 0.5, alternative='greater')
            print(f"    {lbl}: {w}/16 → binomial p={bt.pvalue:.4f}")

    # ── Ensemble results ──
    if test_ensemble:
        print(f"\n  --- ENSEMBLE ({K} timescales) vs single E0 ---")
        print(f"  {'SP':>5s} {'P(Sh+)':>8s} {'P(CAGR+)':>8s} {'P(MDD-)':>8s} {'P(NAV+)':>8s} "
              f"{'medSh_e':>8s} {'medSh_0':>8s}")
        w_sh, w_cagr, w_mdd, w_nav = 0, 0, 0, 0
        for j, sp in enumerate(SLOW_PERIODS):
            p_sh = np.mean(sh_ens[:, j] > sh_e0[:, j])
            p_cagr = np.mean(cagr_ens[:, j] > cagr_e0[:, j])
            p_mdd = np.mean(mdd_ens[:, j] < mdd_e0[:, j])
            p_nav = np.mean(nav_ens[:, j] > nav_e0[:, j])
            med_sh_e = np.median(sh_ens[:, j])
            med_sh_0 = np.median(sh_e0[:, j])
            if p_sh > 0.5: w_sh += 1
            if p_cagr > 0.5: w_cagr += 1
            if p_mdd > 0.5: w_mdd += 1
            if p_nav > 0.5: w_nav += 1
            print(f"  {sp:5d} {p_sh:8.1%} {p_cagr:8.1%} {p_mdd:8.1%} {p_nav:8.1%} "
                  f"{med_sh_e:8.3f} {med_sh_0:8.3f}")

        print(f"\n  Ensemble wins/16: Sharpe={w_sh} CAGR={w_cagr} MDD={w_mdd} NAV={w_nav}")
        for lbl, w in [("Sharpe", w_sh), ("CAGR", w_cagr), ("MDD", w_mdd), ("NAV", w_nav)]:
            bt = binomtest(w, 16, 0.5, alternative='greater')
            print(f"    {lbl}: {w}/16 → binomial p={bt.pvalue:.4f}")

    return


# ═══════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════

def main():
    print("=" * 90)
    print("CREATIVE EXPLORATION: LEARNING FROM 10 FAILURES")
    print("=" * 90)
    print()
    print("Meta-lesson: All 10 alternatives tried to MODIFY the proven signal.")
    print("Key insight: The signal is IRREDUCIBLE. Only STRUCTURAL changes remain.")
    print()
    print("Two hypotheses derived from failure patterns:")
    print("  A) Multi-timescale ensemble — diversify across TIMING, not signal")
    print("  B) Trail-only exit (E7) — simplify exit (complexity hurts)")

    cl, hi, lo, vo, tb, wi, n = load_arrays()

    # Phase 0: Diagnostic
    avg_corr, plateau_sps, nav_dict = phase0_correlation(cl, hi, lo, vo, tb, wi)

    # Phase 1: Real data
    e7_wins_sh, e7_wins_nav, m_port, m120 = phase1_real(
        cl, hi, lo, vo, tb, wi, plateau_sps, nav_dict)

    # Decision gates
    test_ensemble = True  # Always test — we want to see the result
    test_e7 = e7_wins_sh >= 8  # Only bootstrap if real data promising

    if not test_e7:
        print(f"\n  E7 real-data: {e7_wins_sh}/16 Sharpe wins → SKIP bootstrap (< 8/16)")
    else:
        print(f"\n  E7 real-data: {e7_wins_sh}/16 Sharpe wins → PROCEED to bootstrap")

    # Phase 2: Bootstrap
    phase2_bootstrap(cl, hi, lo, vo, tb, wi, n, plateau_sps,
                     test_ensemble=test_ensemble,
                     test_e7=test_e7)

    print("\n" + "=" * 90)
    print("EXPLORATION COMPLETE")
    print("=" * 90)


if __name__ == "__main__":
    main()
