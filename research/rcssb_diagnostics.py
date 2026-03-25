#!/usr/bin/env python3
"""RC-SSB Diagnostics: Empirical tests on BTC H4 data.

Tests whether the problems RC-SSB claims to solve actually exist
and matter for our VTREND paired comparison methodology.

Tests:
  1. Seasonality: does H4 BTC have significant hour/day patterns?
  2. Invariant representation: current ratios vs proposed log-invariants
  3. Volume scale mismatch: does raw vol bootstrap break VDO?
  4. Regime structure: how many regimes? How persistent?
  5. Block seam impact: how bad are fixed-block seams under VCBB?
  6. Calendar continuity: does destroying calendar order matter for VTREND?
"""

from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path
from datetime import datetime, timezone

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from v10.core.data import DataFeed
from v10.core.types import SCENARIOS

DATA = str(ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv")
START = "2019-01-01"
END = "2026-02-20"
WARMUP = 365


def load_h4():
    feed = DataFeed(DATA, start=START, end=END, warmup_days=WARMUP)
    h4 = feed.h4_bars
    n = len(h4)
    cl = np.array([b.close for b in h4], dtype=np.float64)
    hi = np.array([b.high for b in h4], dtype=np.float64)
    lo = np.array([b.low for b in h4], dtype=np.float64)
    op = np.array([b.open for b in h4], dtype=np.float64)
    vo = np.array([b.volume for b in h4], dtype=np.float64)
    tb = np.array([b.taker_buy_base_vol for b in h4], dtype=np.float64)
    # Extract timestamps
    ts = np.array([b.close_time for b in h4], dtype=np.int64)
    wi = 0
    if feed.report_start_ms is not None:
        for i, b in enumerate(h4):
            if b.close_time >= feed.report_start_ms:
                wi = i
                break
    return cl, hi, lo, op, vo, tb, ts, wi, n


def main():
    print("=" * 80)
    print("RC-SSB DIAGNOSTICS: Empirical Analysis of BTC H4 Data")
    print("=" * 80)

    cl, hi, lo, op, vo, tb, ts, wi, n = load_h4()
    print(f"  H4 bars: {n}, warmup: {wi}, eval: {n - wi}")

    # ══════════════════════════════════════════════════════════════════════════
    # TEST 1: Seasonality — Does H4 BTC have significant hour/day patterns?
    # ══════════════════════════════════════════════════════════════════════════
    print("\n" + "=" * 80)
    print("TEST 1: SEASONALITY (hour-of-day, day-of-week)")
    print("=" * 80)

    log_r = np.log(cl[1:] / cl[:-1])
    abs_r = np.abs(log_r)

    # Extract hour and day-of-week from close timestamps
    hours = np.array([datetime.fromtimestamp(t / 1000, tz=timezone.utc).hour for t in ts[1:]])
    days = np.array([datetime.fromtimestamp(t / 1000, tz=timezone.utc).weekday() for t in ts[1:]])

    # H4 has 6 slots per day: 0,4,8,12,16,20
    unique_hours = sorted(set(hours))
    unique_days = sorted(set(days))

    # 1a. Volatility by hour
    print("\n  1a. Volatility (|return|) by H4 slot:")
    overall_vol = np.mean(abs_r[wi:])
    hour_vols = {}
    for h in unique_hours:
        mask = (hours[wi:] == h)
        if mask.sum() > 10:
            hour_vols[h] = np.mean(abs_r[wi:][mask])

    max_h = max(hour_vols.values())
    min_h = min(hour_vols.values())
    ratio_h = max_h / min_h if min_h > 0 else 0
    for h in unique_hours:
        v = hour_vols.get(h, 0)
        bar = "█" * int(v / overall_vol * 30)
        print(f"    {h:02d}:00  {v:.6f}  {v/overall_vol:.2f}x  {bar}")
    print(f"    Max/Min ratio: {ratio_h:.2f}x")

    # 1b. Volatility by day-of-week
    print("\n  1b. Volatility by day-of-week:")
    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    day_vols = {}
    for d in unique_days:
        mask = (days[wi:] == d)
        if mask.sum() > 10:
            day_vols[d] = np.mean(abs_r[wi:][mask])

    max_d = max(day_vols.values())
    min_d = min(day_vols.values())
    ratio_d = max_d / min_d if min_d > 0 else 0
    for d in unique_days:
        v = day_vols.get(d, 0)
        bar = "█" * int(v / overall_vol * 30)
        print(f"    {day_names[d]}  {v:.6f}  {v/overall_vol:.2f}x  {bar}")
    print(f"    Max/Min ratio: {ratio_d:.2f}x")

    # 1c. Volume (turnover) by hour
    print("\n  1c. Volume by H4 slot:")
    overall_v = np.mean(vo[wi + 1:])
    hour_volumes = {}
    for h in unique_hours:
        mask = (hours[wi:] == h)
        if mask.sum() > 10:
            hour_volumes[h] = np.mean(vo[wi + 1:][mask[:len(vo[wi + 1:])]])

    max_hv = max(hour_volumes.values())
    min_hv = min(hour_volumes.values())
    ratio_hv = max_hv / min_hv if min_hv > 0 else 0
    for h in unique_hours:
        v = hour_volumes.get(h, 0)
        bar = "█" * int(v / overall_v * 20)
        print(f"    {h:02d}:00  {v:>12,.0f}  {v/overall_v:.2f}x  {bar}")
    print(f"    Max/Min ratio: {ratio_hv:.2f}x")

    # 1d. Weekend vs weekday
    print("\n  1d. Weekend vs Weekday:")
    wkday = np.isin(days[wi:], [0, 1, 2, 3, 4])
    wkend = np.isin(days[wi:], [5, 6])
    vol_wkday = np.mean(abs_r[wi:][wkday])
    vol_wkend = np.mean(abs_r[wi:][wkend])
    vol_ratio_we = vol_wkend / vol_wkday
    print(f"    Weekday vol: {vol_wkday:.6f}")
    print(f"    Weekend vol: {vol_wkend:.6f}")
    print(f"    Weekend/Weekday: {vol_ratio_we:.3f}x")

    # 1e. Statistical significance: F-test (ANOVA) across hours
    from scipy import stats as sp_stats
    groups_by_hour = [abs_r[wi:][hours[wi:] == h] for h in unique_hours if (hours[wi:] == h).sum() > 10]
    f_stat, f_pval = sp_stats.f_oneway(*groups_by_hour)
    print(f"\n  1e. ANOVA F-test (vol across hours): F={f_stat:.2f}, p={f_pval:.4e}")
    print(f"      {'SIGNIFICANT' if f_pval < 0.01 else 'NOT SIGNIFICANT'} at 1%")

    # 1f. Does seasonality affect VDO?
    # VDO = (2*tb/vol - 1), check buy-share by hour
    print("\n  1f. Taker buy share (tb/vol) by H4 slot:")
    buy_share = tb[wi + 1:] / np.maximum(vo[wi + 1:], 1e-12)
    for h in unique_hours:
        mask = (hours[wi:] == h)
        bs_h = buy_share[mask[:len(buy_share)]]
        if len(bs_h) > 10:
            print(f"    {h:02d}:00  mean={np.mean(bs_h):.4f}  std={np.std(bs_h):.4f}")
    groups_bs = [buy_share[hours[wi:][:len(buy_share)] == h] for h in unique_hours if (hours[wi:][:len(buy_share)] == h).sum() > 10]
    f_bs, p_bs = sp_stats.f_oneway(*groups_bs)
    print(f"    ANOVA (buy_share across hours): F={f_bs:.2f}, p={p_bs:.4e}")
    print(f"    {'SIGNIFICANT' if p_bs < 0.01 else 'NOT SIGNIFICANT'} at 1%")

    # ══════════════════════════════════════════════════════════════════════════
    # TEST 2: Invariant Representation — Current vs Proposed
    # ══════════════════════════════════════════════════════════════════════════
    print("\n" + "=" * 80)
    print("TEST 2: INVARIANT REPRESENTATION")
    print("=" * 80)

    # Current representation
    cr = cl[1:] / cl[:-1]  # close ratio
    hr = hi[1:] / cl[:-1]  # high ratio
    lr = lo[1:] / cl[:-1]  # low ratio

    # Proposed representation
    o_t = cl[:-1]  # open = prev close (same assumption)
    r_t = np.log(cl[1:] / o_t)  # log return
    u_t = np.log(hi[1:] / np.maximum(o_t, cl[1:]))  # upper wick (>= 0)
    d_t = np.log(np.minimum(o_t, cl[1:]) / lo[1:])  # lower wick (>= 0)

    # Check: are u_t, d_t always >= 0?
    u_neg = np.sum(u_t < -1e-10)
    d_neg = np.sum(d_t < -1e-10)
    print(f"\n  2a. Wick non-negativity:")
    print(f"    u_t < 0: {u_neg}/{len(u_t)} ({u_neg/len(u_t)*100:.2f}%)")
    print(f"    d_t < 0: {d_neg}/{len(d_t)} ({d_neg/len(d_t)*100:.2f}%)")

    # Check: clamp frequency in current system
    h_synth = cl[:-1] * hr
    l_synth = cl[:-1] * lr
    clamp_h = np.sum(h_synth < cl[1:])
    clamp_l = np.sum(l_synth > cl[1:])
    print(f"\n  2b. Current system clamp frequency:")
    print(f"    high < close (needs clamp): {clamp_h}/{len(cr)} ({clamp_h/len(cr)*100:.2f}%)")
    print(f"    low > close (needs clamp): {clamp_l}/{len(cr)} ({clamp_l/len(cr)*100:.2f}%)")

    # Check: reconstruction equivalence
    # Current: c' = p0 * cumprod(cr), h' = c_prev * hr, l' = c_prev * lr
    # Proposed: c' = o * exp(r), h' = max(o,c) * exp(u), l' = min(o,c) * exp(-d)
    # Both should reconstruct same OHLC from same data
    c_curr = cl[0] * np.cumprod(cr)
    h_curr = cl[:-1] * hr
    l_curr = cl[:-1] * lr
    h_curr = np.maximum(h_curr, c_curr)  # clamp
    l_curr = np.minimum(l_curr, c_curr)

    c_prop = cl[0] * np.exp(np.cumsum(r_t))
    h_prop = np.maximum(cl[:-1], c_prop) * np.exp(u_t)
    l_prop = np.minimum(cl[:-1], c_prop) * np.exp(-d_t)

    c_diff = np.max(np.abs(c_curr - c_prop))
    h_diff = np.max(np.abs(h_curr[wi:] - h_prop[wi:]))
    l_diff = np.max(np.abs(l_curr[wi:] - l_prop[wi:]))
    print(f"\n  2c. Reconstruction equivalence (max abs diff):")
    print(f"    Close: {c_diff:.2e}")
    print(f"    High:  {h_diff:.2e} (after warmup)")
    print(f"    Low:   {l_diff:.2e} (after warmup)")

    # ══════════════════════════════════════════════════════════════════════════
    # TEST 3: Volume Scale Mismatch — Does it actually break VDO?
    # ══════════════════════════════════════════════════════════════════════════
    print("\n" + "=" * 80)
    print("TEST 3: VOLUME SCALE MISMATCH — Impact on VDO")
    print("=" * 80)

    # VDO = EMA(vdr, fast) - EMA(vdr, slow), where vdr = (2*tb/vol - 1)
    # This is a RATIO — absolute volume cancels
    # But let's verify empirically: how much does raw volume vary across eras?

    # Split into yearly segments
    years_start = {}
    for i, t in enumerate(ts):
        yr = datetime.fromtimestamp(t / 1000, tz=timezone.utc).year
        if yr not in years_start:
            years_start[yr] = i

    print("\n  3a. Raw volume by year:")
    vol_by_year = {}
    for yr in sorted(years_start.keys()):
        start = years_start[yr]
        end = years_start.get(yr + 1, n)
        med_vol = np.median(vo[start:end])
        vol_by_year[yr] = med_vol
        print(f"    {yr}: median vol = {med_vol:>12,.0f} BTC")

    max_vol = max(vol_by_year.values())
    min_vol = min(vol_by_year.values())
    print(f"    Max/Min ratio across years: {max_vol/min_vol:.1f}x")

    # VDO buy-share (the only thing VDO uses)
    print("\n  3b. Buy share (tb/vol) by year:")
    for yr in sorted(years_start.keys()):
        start = years_start[yr]
        end = years_start.get(yr + 1, n)
        bs = tb[start:end] / np.maximum(vo[start:end], 1e-12)
        print(f"    {yr}: mean={np.mean(bs):.4f}  std={np.std(bs):.4f}  "
              f"range=[{np.percentile(bs, 5):.3f}, {np.percentile(bs, 95):.3f}]")

    # Quote turnover variation
    print("\n  3c. Quote turnover (price × volume) by year:")
    qt = cl * vo  # approximate quote turnover
    for yr in sorted(years_start.keys()):
        start = years_start[yr]
        end = years_start.get(yr + 1, n)
        med_qt = np.median(qt[start:end])
        print(f"    {yr}: median quote turnover = ${med_qt:>16,.0f}")

    # ══════════════════════════════════════════════════════════════════════════
    # TEST 4: Regime Structure
    # ══════════════════════════════════════════════════════════════════════════
    print("\n" + "=" * 80)
    print("TEST 4: REGIME STRUCTURE")
    print("=" * 80)

    # Simple 4-regime classification via median split on rv24 × ret24
    rv24 = np.array([np.sqrt(np.sum(log_r[max(0, i - 24):i] ** 2))
                     for i in range(24, len(log_r))])
    ret24 = np.array([np.sum(log_r[max(0, i - 24):i])
                      for i in range(24, len(log_r))])

    rv_med = np.median(rv24)
    ret_med = 0.0  # neutral threshold

    regime = np.zeros(len(rv24), dtype=int)
    regime[(rv24 <= rv_med) & (ret24 >= ret_med)] = 0  # calm-up
    regime[(rv24 <= rv_med) & (ret24 < ret_med)] = 1   # calm-down
    regime[(rv24 > rv_med) & (ret24 >= ret_med)] = 2   # storm-up
    regime[(rv24 > rv_med) & (ret24 < ret_med)] = 3    # storm-down

    regime_names = ["calm-up", "calm-down", "storm-up", "storm-down"]

    # Regime distribution
    print("\n  4a. Regime distribution:")
    for r in range(4):
        cnt = np.sum(regime == r)
        pct = cnt / len(regime) * 100
        print(f"    {regime_names[r]:<12s}: {cnt:>5d} bars ({pct:.1f}%)")

    # Regime persistence (average dwell time)
    print("\n  4b. Regime persistence (average run length):")
    for r in range(4):
        runs = []
        current_run = 0
        for i in range(len(regime)):
            if regime[i] == r:
                current_run += 1
            else:
                if current_run > 0:
                    runs.append(current_run)
                current_run = 0
        if current_run > 0:
            runs.append(current_run)
        if runs:
            print(f"    {regime_names[r]:<12s}: mean={np.mean(runs):.1f} bars "
                  f"({np.mean(runs)*4/24:.1f} days), "
                  f"median={np.median(runs):.0f}, max={max(runs)}")

    # Transition matrix
    print("\n  4c. Transition matrix P(next | current):")
    trans = np.zeros((4, 4))
    for i in range(len(regime) - 1):
        trans[regime[i], regime[i + 1]] += 1
    # Normalize rows
    for r in range(4):
        s = trans[r].sum()
        if s > 0:
            trans[r] /= s
    print(f"    {'':>12s}  {'calm-up':>9s} {'calm-dn':>9s} {'storm-up':>9s} {'storm-dn':>9s}")
    for r in range(4):
        vals = "  ".join(f"{trans[r, c]:.3f}" for c in range(4))
        print(f"    {regime_names[r]:<12s}  {vals}")

    # Self-transition probability (persistence)
    diag = [trans[r, r] for r in range(4)]
    print(f"\n    Self-transition (persistence): {[f'{d:.3f}' for d in diag]}")
    print(f"    Mean persistence: {np.mean(diag):.3f}")
    print(f"    If independent (25%): {0.25:.3f}")
    print(f"    Persistence excess over random: {(np.mean(diag) - 0.25) / 0.25 * 100:.0f}%")

    # ══════════════════════════════════════════════════════════════════════════
    # TEST 5: Does VCBB already handle seam continuity adequately?
    # ══════════════════════════════════════════════════════════════════════════
    print("\n" + "=" * 80)
    print("TEST 5: VCBB SEAM QUALITY (already implemented)")
    print("=" * 80)

    # Load VCBB validation results
    vcbb_path = ROOT / "research" / "results" / "vcbb_validation.json"
    if vcbb_path.exists():
        with open(vcbb_path) as f:
            vcbb = json.load(f)
        t1 = vcbb.get("test1_vol_clustering", {})
        print("\n  VCBB vol clustering recovery (from validation):")
        for k in ["abs_acf_60", "abs_acf_120", "abs_acf_180", "cond_vol_ratio", "rolling_vol_acf_60"]:
            if k in t1:
                r = t1[k]
                rec = r.get("recovery", 0)
                print(f"    {k:<25s}: recovery={rec:.0%}, pass={r.get('pass', '?')}")
    else:
        print("  [VCBB validation results not found]")

    # ══════════════════════════════════════════════════════════════════════════
    # TEST 6: Does calendar destruction affect VTREND conclusions?
    # ══════════════════════════════════════════════════════════════════════════
    print("\n" + "=" * 80)
    print("TEST 6: VTREND SENSITIVITY TO CALENDAR FEATURES")
    print("=" * 80)

    # VTREND uses: EMA(close), ATR(high,low,close), VDO(close,high,low,vol,tb)
    # None of these indicators use timestamps or calendar information
    # Check: does VTREND performance differ by day-of-week on real data?

    from strategies.vtrend.strategy import _ema, _atr, _vdo
    TRAIL = 3.0
    ATR_P = 14
    VDO_F = 12
    VDO_S = 28
    SLOW = 120
    FAST = max(5, SLOW // 4)
    CPS = 0.0025

    ef = _ema(cl, FAST)
    es = _ema(cl, SLOW)
    at = _atr(hi, lo, cl, ATR_P)
    vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)

    # Track per-bar returns when in position, by day-of-week
    inp = False
    pk = 0.0
    pe = px = False
    bar_returns_by_day = {d: [] for d in range(7)}

    for i in range(1, n):
        fp = cl[i - 1]
        if pe:
            pe = False
            inp = True
            pk = cl[i]
        elif px:
            inp = False
            pk = 0.0
            px = False

        if i >= wi and inp:
            r = cl[i] / cl[i - 1] - 1.0
            day = datetime.fromtimestamp(ts[i] / 1000, tz=timezone.utc).weekday()
            bar_returns_by_day[day].append(r)

        a_val = at[i]
        if math.isnan(a_val) or math.isnan(ef[i]) or math.isnan(es[i]):
            continue

        if not inp:
            if ef[i] > es[i] and vd[i] > 0.0:
                pe = True
        else:
            pk = max(pk, cl[i])
            if cl[i] < pk - TRAIL * a_val:
                px = True
            elif ef[i] < es[i]:
                px = True

    print("\n  6a. VTREND per-bar return while in position, by day:")
    for d in range(7):
        rets = bar_returns_by_day[d]
        if rets:
            r_arr = np.array(rets)
            print(f"    {day_names[d]}: n={len(rets):>4d}, mean={np.mean(r_arr)*1e4:>+5.1f} bps, "
                  f"std={np.std(r_arr)*1e4:>5.1f} bps, Sharpe_contrib={np.mean(r_arr)/np.std(r_arr)*np.sqrt(6*365.25):.3f}")

    # ANOVA on in-position returns by day
    day_groups = [np.array(bar_returns_by_day[d]) for d in range(7) if len(bar_returns_by_day[d]) > 10]
    if len(day_groups) >= 2:
        f_ret, p_ret = sp_stats.f_oneway(*day_groups)
        print(f"\n  6b. ANOVA (in-position returns by day): F={f_ret:.2f}, p={p_ret:.4f}")
        print(f"      {'SIGNIFICANT' if p_ret < 0.05 else 'NOT SIGNIFICANT'} at 5%")

    # ══════════════════════════════════════════════════════════════════════════
    # TEST 7: How much data budget does RC-SSB consume?
    # ══════════════════════════════════════════════════════════════════════════
    print("\n" + "=" * 80)
    print("TEST 7: DATA BUDGET")
    print("=" * 80)

    total_bars = n - wi
    print(f"\n  Total eval bars: {total_bars}")
    print(f"  Seasonality slots (6 hours × 7 days): {6*7} = 42 slots")
    print(f"  Bars per slot: {total_bars / 42:.0f}")

    # With 4 regimes × 4 transition probabilities × N eras
    n_eras_est = 5  # rough estimate
    regime_params = 4 * 4  # transition matrix
    era_params = n_eras_est * regime_params
    seasonal_params = 42 * 3  # μ_q, μ_b, σ_r per slot
    total_params = era_params + seasonal_params
    print(f"  RC-SSB parameters estimate:")
    print(f"    Seasonal: 42 slots × 3 = {42*3}")
    print(f"    Regime: {n_eras_est} eras × 4×4 transition = {era_params}")
    print(f"    Total: ~{total_params}")
    print(f"    Data/param ratio: {total_bars / total_params:.0f}:1")

    # For comparison: VTREND has 3 params, bootstrap has 2 (blksz, ctx)
    print(f"\n  Current system parameters:")
    print(f"    VTREND: 3 (slow, trail, vdo_threshold)")
    print(f"    VCBB: 2 (blksz=60, ctx=90)")
    print(f"    Total: 5")
    print(f"    Data/param ratio: {total_bars / 5:.0f}:1")

    # ══════════════════════════════════════════════════════════════════════════
    # SUMMARY
    # ══════════════════════════════════════════════════════════════════════════
    print("\n" + "=" * 80)
    print("SUMMARY: Which RC-SSB claims are empirically supported?")
    print("=" * 80)

    findings = {
        "seasonality_vol_significant": f_pval < 0.01,
        "seasonality_vol_magnitude": f"{ratio_h:.2f}x",
        "seasonality_buy_share_significant": p_bs < 0.01,
        "weekend_effect": f"{vol_ratio_we:.3f}x",
        "clamp_frequency_pct": round((clamp_h + clamp_l) / len(cr) * 100, 2),
        "volume_cross_year_ratio": round(max_vol / min_vol, 1),
        "regime_persistence_excess": f"{(np.mean(diag) - 0.25) / 0.25 * 100:.0f}%",
        "calendar_affects_vtrend": p_ret < 0.05 if 'p_ret' in dir() else "unknown",
        "data_param_ratio_rcssb": round(total_bars / total_params, 0),
        "data_param_ratio_current": round(total_bars / 5, 0),
    }

    for k, v in findings.items():
        print(f"  {k}: {v}")

    # Save
    out_dir = Path(__file__).parent / "results"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "rcssb_diagnostics.json"
    with open(out_path, "w") as f:
        json.dump(findings, f, indent=2, default=str)
    print(f"\n  Results saved to {out_path}")


if __name__ == "__main__":
    main()
