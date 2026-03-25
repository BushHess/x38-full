#!/usr/bin/env python3
"""X29 Monitor V2 Diagnostic — Conditional Bootstrap Analysis

Question: Is the T3 bootstrap unfair to Monitor V2 because bear markets
are too rare on VCBB paths?

Analysis:
  1. Count RED episodes on each bootstrap path
  2. Compute Monitor delta CONDITIONAL on having RED bars
  3. Compare conditional vs unconditional P(d_sharpe > 0)
  4. Count: how many paths have zero Monitor triggers?
"""

from __future__ import annotations
import math
import sys
import time
from pathlib import Path

import numpy as np
from scipy.signal import lfilter

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from v10.core.data import DataFeed
from v10.core.types import SCENARIOS
from research.lib.vcbb import make_ratios, precompute_vcbb, gen_path_vcbb

# ── constants (from x29_benchmark) ──────────────────────────────────────
DATA = str(ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv")
CASH = 10_000.0
ANN = math.sqrt(6.0 * 365.25)
START, END, WARMUP = "2019-01-01", "2026-02-20", 365
VDO_F, VDO_S, VDO_THR = 12, 28, 0.0
SLOW, D1_EMA_P = 120, 21
RATR_P, RATR_Q, RATR_LB = 20, 0.90, 100
TRAIL = 3.0
ROLL_6M, ROLL_12M = 180, 360
RED_MDD_6M, RED_MDD_12M = 0.55, 0.70
N_BOOT, BLKSZ, SEED = 500, 60, 42
PRIMARY_CPS = 25 / 20_000.0


# ── indicators (exact copies) ──────────────────────────────────────────
def _ema(s, p):
    a = 2.0 / (p + 1)
    out, _ = lfilter([a], [1.0, -(1 - a)], s, zi=[(1 - a) * s[0]])
    return out

def _robust_atr(hi, lo, cl, cap_q=RATR_Q, cap_lb=RATR_LB, period=RATR_P):
    prev = np.empty_like(cl); prev[0] = cl[0]; prev[1:] = cl[:-1]
    tr = np.maximum(hi - lo, np.maximum(np.abs(hi - prev), np.abs(lo - prev)))
    n = len(tr); tr_cap = np.full(n, np.nan)
    for i in range(cap_lb, n):
        q = np.percentile(tr[i - cap_lb:i], cap_q * 100)
        tr_cap[i] = min(tr[i], q)
    ratr = np.full(n, np.nan); s = cap_lb
    if s + period <= n:
        ratr[s + period - 1] = np.nanmean(tr_cap[s:s + period])
        for i in range(s + period, n):
            ratr[i] = (ratr[i - 1] * (period - 1) + tr_cap[i]) / period
    return ratr

def _vdo(cl, hi, lo, vo, tb, fast=VDO_F, slow=VDO_S):
    n = len(cl)
    ts = np.maximum(vo - tb, 0.0); vdr = np.zeros(n)
    m = vo > 1e-12; vdr[m] = (tb[m] - ts[m]) / vo[m]
    return _ema(vdr, fast) - _ema(vdr, slow)


def _rolling_mdd(close, window):
    n = len(close); mdd = np.full(n, np.nan)
    for t in range(window - 1, n):
        seg = close[t - window + 1:t + 1]
        pk = np.maximum.accumulate(seg)
        mdd[t] = np.max(1.0 - seg / pk)
    return mdd


def _compute_h4_monitor(cl_h4):
    """Compute Monitor V2 alerts directly on H4 prices (approximate).

    For bootstrap paths we don't have separate D1 bars, so we compute
    rolling MDD on H4 close with windows scaled to match D1 semantics:
    6M ≈ 180 days × 6 bars/day = 1080 H4 bars
    12M ≈ 360 days × 6 bars/day = 2160 H4 bars
    """
    mdd_6m = _rolling_mdd(cl_h4, 1080)
    mdd_12m = _rolling_mdd(cl_h4, 2160)
    n = len(cl_h4)
    alerts = np.zeros(n, dtype=np.int8)
    for t in range(n):
        m6 = mdd_6m[t] if not np.isnan(mdd_6m[t]) else 0.0
        m12 = mdd_12m[t] if not np.isnan(mdd_12m[t]) else 0.0
        if m6 > RED_MDD_6M or m12 > RED_MDD_12M:
            alerts[t] = 2
    return alerts


def _metrics(nav, wi):
    navs = nav[wi:]
    if len(navs) < 2:
        return {"sharpe": 0.0, "cagr": -100.0, "mdd": 100.0}
    rets = navs[1:] / navs[:-1] - 1.0
    mu = np.mean(rets); std = np.std(rets, ddof=0)
    sharpe = (mu / std * ANN) if std > 1e-12 else 0.0
    tr = navs[-1] / navs[0] - 1.0
    yrs = len(rets) / (6.0 * 365.25)
    cagr = ((1 + tr) ** (1.0 / yrs) - 1.0) * 100 if yrs > 0 and tr > -1 else -100.0
    pk = np.maximum.accumulate(navs); mdd = np.max(1.0 - navs / pk) * 100
    return {"sharpe": sharpe, "cagr": cagr, "mdd": mdd}


def _sim(cl, ef, es, vd, at, regime_h4, monitor_h4, use_monitor, cps):
    """Minimal sim: E5+EMA1D21 with optional Monitor."""
    n = len(cl)
    cash = CASH; bq = 0.0; inp = False; pe = px = False; pk = 0.0
    nav = np.zeros(n); n_blocks = 0

    for i in range(n):
        p = cl[i]
        if i > 0:
            fp = cl[i - 1]
            if pe:
                pe = False; bq = cash / (fp * (1 + cps)); cash = 0.0; inp = True; pk = p
            elif px:
                px = False; cash = bq * fp * (1 - cps); bq = 0.0; inp = False; pk = 0.0
        nav[i] = cash + bq * p
        a = at[i]
        if math.isnan(a) or math.isnan(ef[i]) or math.isnan(es[i]):
            continue
        red = use_monitor and monitor_h4 is not None and monitor_h4[i] == 2
        if not inp:
            if ef[i] > es[i] and vd[i] > VDO_THR and regime_h4[i]:
                if red:
                    n_blocks += 1
                else:
                    pe = True
        else:
            pk = max(pk, p)
            if p < pk - TRAIL * a:
                px = True
            elif ef[i] < es[i]:
                px = True

    if inp and bq > 0:
        cash = bq * cl[-1] * (1 - cps); bq = 0.0; nav[-1] = cash
    return nav, n_blocks


def main():
    t0 = time.time()
    print("=" * 70)
    print("X29 Monitor Diagnostic — Conditional Bootstrap Analysis")
    print("=" * 70)

    # ── Load ────────────────────────────────────────────────────────────
    feed = DataFeed(DATA, start=START, end=END, warmup_days=WARMUP)
    cl = np.array([b.close for b in feed.h4_bars], dtype=np.float64)
    hi = np.array([b.high for b in feed.h4_bars], dtype=np.float64)
    lo = np.array([b.low for b in feed.h4_bars], dtype=np.float64)
    vo = np.array([b.volume for b in feed.h4_bars], dtype=np.float64)
    tb = np.array([b.taker_buy_base_vol for b in feed.h4_bars], dtype=np.float64)
    h4_ct = np.array([b.close_time for b in feed.h4_bars], dtype=np.int64)
    d1_cl = np.array([b.close for b in feed.d1_bars], dtype=np.float64)
    d1_ct = np.array([b.close_time for b in feed.d1_bars], dtype=np.int64)

    n = len(cl); wi = 0
    if feed.report_start_ms:
        for j, b in enumerate(feed.h4_bars):
            if b.close_time >= feed.report_start_ms:
                wi = j; break

    # ── Real data baseline ──────────────────────────────────────────────
    from monitoring.regime_monitor import compute_regime, map_d1_alert_to_h4
    regime_d1 = compute_regime(d1_cl)
    monitor_h4_real = map_d1_alert_to_h4(regime_d1["alerts"], d1_ct, h4_ct)
    n_red_real = int(np.sum(monitor_h4_real[wi:] == 2))
    print(f"\nReal data: {n_red_real} RED H4 bars ({n_red_real / (n - wi) * 100:.1f}%)")

    ef = _ema(cl, max(5, SLOW // 4)); es = _ema(cl, SLOW)
    vd = _vdo(cl, hi, lo, vo, tb); at = _robust_atr(hi, lo, cl)

    # D1 regime mapped to H4
    d1_ema = _ema(d1_cl, D1_EMA_P)
    d1_reg = d1_cl > d1_ema
    regime_h4 = np.zeros(n, dtype=np.bool_)
    d1i = 0; nd1 = len(d1_cl)
    for i in range(n):
        while d1i + 1 < nd1 and d1_ct[d1i + 1] < h4_ct[i]: d1i += 1
        if d1_ct[d1i] < h4_ct[i]: regime_h4[i] = d1_reg[d1i]

    nav_base, _ = _sim(cl, ef, es, vd, at, regime_h4, None, False, PRIMARY_CPS)
    nav_mon, n_blk = _sim(cl, ef, es, vd, at, regime_h4, monitor_h4_real, True, PRIMARY_CPS)
    m_base = _metrics(nav_base, wi); m_mon = _metrics(nav_mon, wi)
    print(f"Real: Base Sh={m_base['sharpe']:.3f}, Mon Sh={m_mon['sharpe']:.3f}, "
          f"Δ={m_mon['sharpe'] - m_base['sharpe']:+.3f}, blocks={n_blk}")

    # ── Bootstrap ───────────────────────────────────────────────────────
    print(f"\nRunning {N_BOOT} VCBB paths with H4-level Monitor computation...")
    cl_pw = cl[wi:]; hi_pw = hi[wi:]; lo_pw = lo[wi:]; vo_pw = vo[wi:]; tb_pw = tb[wi:]
    cr, hr, lr, vol_r, tb_r = make_ratios(cl_pw, hi_pw, lo_pw, vo_pw, tb_pw)
    vcbb = precompute_vcbb(cr, BLKSZ)
    n_trans = len(cl) - wi - 1; p0 = cl[wi]
    rng = np.random.default_rng(SEED)
    reg_pw = regime_h4[wi:]

    d_sharpe_all = []
    d_sharpe_red = []       # paths where Monitor triggered >= 1 block
    d_sharpe_no_red = []    # paths where Monitor triggered 0 blocks
    n_red_bars_list = []
    n_blocks_list = []

    for b in range(N_BOOT):
        bcl, bhi, blo, bvo, btb = gen_path_vcbb(
            cr, hr, lr, vol_r, tb_r, n_trans, BLKSZ, p0, rng, vcbb)
        nb = len(bcl)
        bef = _ema(bcl, max(5, SLOW // 4)); bes = _ema(bcl, SLOW)
        bvd = _vdo(bcl, bhi, blo, bvo, btb)
        bat = _robust_atr(bhi, blo, bcl)
        breg = reg_pw[:nb] if len(reg_pw) >= nb else np.ones(nb, dtype=np.bool_)

        # Compute Monitor on bootstrap H4 prices
        bmon = _compute_h4_monitor(bcl)
        n_red_b = int(np.sum(bmon == 2))
        n_red_bars_list.append(n_red_b)

        # Run sims
        bnav_base, _ = _sim(bcl, bef, bes, bvd, bat, breg, None, False, PRIMARY_CPS)
        bnav_mon, b_blocks = _sim(bcl, bef, bes, bvd, bat, breg, bmon, True, PRIMARY_CPS)
        n_blocks_list.append(b_blocks)

        bm_base = _metrics(bnav_base, 0); bm_mon = _metrics(bnav_mon, 0)
        ds = bm_mon["sharpe"] - bm_base["sharpe"]
        d_sharpe_all.append(ds)

        if b_blocks > 0:
            d_sharpe_red.append(ds)
        else:
            d_sharpe_no_red.append(ds)

        if (b + 1) % 100 == 0:
            print(f"  ... {b + 1}/{N_BOOT}")

    d_all = np.array(d_sharpe_all)
    d_red = np.array(d_sharpe_red)
    d_no = np.array(d_sharpe_no_red)
    n_red_arr = np.array(n_red_bars_list)
    n_blocks_arr = np.array(n_blocks_list)

    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)

    print(f"\n1. RED bar frequency on bootstrap paths:")
    print(f"   Paths with ANY RED bars:   {np.sum(n_red_arr > 0):>4d} / {N_BOOT} "
          f"({np.mean(n_red_arr > 0) * 100:.1f}%)")
    print(f"   Paths with zero RED bars:  {np.sum(n_red_arr == 0):>4d} / {N_BOOT} "
          f"({np.mean(n_red_arr == 0) * 100:.1f}%)")
    print(f"   Mean RED bars per path:    {np.mean(n_red_arr):.1f} "
          f"(real data: {n_red_real})")
    print(f"   Median RED bars per path:  {np.median(n_red_arr):.0f}")
    pcts = [0, 10, 25, 50, 75, 90, 100]
    print(f"   Percentiles: {dict(zip(pcts, [int(np.percentile(n_red_arr, p)) for p in pcts]))}")

    print(f"\n2. Monitor blocks on bootstrap paths:")
    print(f"   Paths with ANY blocks:     {np.sum(n_blocks_arr > 0):>4d} / {N_BOOT} "
          f"({np.mean(n_blocks_arr > 0) * 100:.1f}%)")
    print(f"   Mean blocks per path:      {np.mean(n_blocks_arr):.1f} (real data: {n_blk})")

    print(f"\n3. Unconditional ΔSharpe (all {N_BOOT} paths):")
    print(f"   P(ΔSh > 0):  {np.mean(d_all > 0) * 100:.1f}%")
    print(f"   Median:       {np.median(d_all):+.4f}")
    print(f"   Mean:         {np.mean(d_all):+.4f}")

    if len(d_red) > 0:
        print(f"\n4. CONDITIONAL ΔSharpe ({len(d_red)} paths where Monitor blocked >= 1 entry):")
        print(f"   P(ΔSh > 0):  {np.mean(d_red > 0) * 100:.1f}%")
        print(f"   Median:       {np.median(d_red):+.4f}")
        print(f"   Mean:         {np.mean(d_red):+.4f}")
    else:
        print("\n4. CONDITIONAL: No paths had Monitor blocks!")

    if len(d_no) > 0:
        print(f"\n5. NULL paths ({len(d_no)} paths where Monitor blocked 0 entries):")
        print(f"   P(ΔSh > 0):  {np.mean(d_no > 0) * 100:.1f}%")
        print(f"   Median:       {np.median(d_no):+.4f}")
        print(f"   (Expected: ~50% / ~0.0 since Monitor is a no-op on these paths)")

    # ── Interpretation ──────────────────────────────────────────────────
    print(f"\n{'=' * 70}")
    print("INTERPRETATION")
    print(f"{'=' * 70}")

    pct_active = np.mean(n_blocks_arr > 0) * 100
    if pct_active < 30:
        print(f"\n  Monitor is ACTIVE on only {pct_active:.0f}% of bootstrap paths.")
        print(f"  The unconditional P(ΔSh>0) = {np.mean(d_all > 0) * 100:.1f}% is "
              f"dominated by {100 - pct_active:.0f}% NULL paths (where Δ ≈ 0).")
        print(f"  This confirms the 'sparse guard' problem: bootstrap is structurally")
        print(f"  underpowered for evaluating mechanisms that only activate during")
        print(f"  rare bear market regimes.")
        if len(d_red) > 0:
            cond_p = np.mean(d_red > 0) * 100
            print(f"\n  CONDITIONAL P(ΔSh>0) = {cond_p:.1f}% — this is the relevant metric")
            print(f"  for a sparse guard. {'PASS (>55%)' if cond_p >= 55 else 'STILL FAIL (<55%)'}")
    else:
        print(f"\n  Monitor is active on {pct_active:.0f}% of paths — NOT sparse.")
        print(f"  Unconditional P(ΔSh>0) = {np.mean(d_all > 0) * 100:.1f}% is a fair test.")

    elapsed = time.time() - t0
    print(f"\nDone in {elapsed:.1f}s")


if __name__ == "__main__":
    main()
