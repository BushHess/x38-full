#!/usr/bin/env python3
"""20 — Win-Count / Multi-Timescale Control Pair Audit.

Audit the multi-timescale win-count procedure on three control pairs:
  Negative:        VTREND_A0 vs VTREND_A1 (ATR 14 → 20, same entry logic)
  Mid positive:    VTREND_A0 vs VBREAK    (EMA cross vs Donchian breakout)
  Strong positive: VTREND_A0 vs VCUSUM    (EMA cross vs CUSUM detection)

Three existing win-count variants:
  V1: Real-data wins at 16 timescales + nominal binomial test
      (Reports 11/11b procedure)
  V2: Bootstrap-then-binomial — VCBB P(win) per timescale + binomial
      (e5_validation.py procedure, 500 VCBB paths)
  V3: DOF-corrected binomial — V2 + Nyholt/Li-Ji/Galwey M_eff adjustment
      (binomial_correction.py procedure)

Canonical timescale grid: 16 H4-bar slow periods
  [30, 48, 60, 72, 84, 96, 108, 120, 144, 168, 200, 240, 300, 360, 500, 720]

Output: research_reports/artifacts/20_win_count_control_pair_audit.json
"""

from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from scipy import stats as sp_stats

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from v10.core.data import DataFeed
from v10.core.types import SCENARIOS
from strategies.vtrend.strategy import _ema, _atr, _vdo
from research.lib.vcbb import make_ratios, precompute_vcbb, gen_path_vcbb
from research.lib.effective_dof import compute_meff, corrected_binomial

# ── Constants ─────────────────────────────────────────────────────

DATA   = str(ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv")
COST   = SCENARIOS["harsh"]
CPS    = COST.per_side_bps / 10_000.0
CASH   = 10_000.0

START  = "2019-01-01"
END    = "2026-02-20"
WARMUP = 365

ANN = math.sqrt(6.0 * 365.25)

ATR_P  = 14
VDO_F  = 12
VDO_S  = 28
TRAIL  = 3.0

SLOW_PERIODS = [30, 48, 60, 72, 84, 96, 108, 120, 144, 168, 200, 240, 300, 360, 500, 720]
N_SP = len(SLOW_PERIODS)

# VCBB bootstrap parameters (matching canonical procedure)
# Canonical N_BOOT=2000; 500 gives ±2.2pp precision on P(win), sufficient for audit
N_BOOT = 500
BLKSZ  = 60
SEED   = 42
CTX    = 90
K_VCBB = 50

OUTDIR = Path(__file__).resolve().parent

# Control pairs: (strategy_a, strategy_b, control_type)
PAIRS = [
    ("VTREND_A0", "VTREND_A1", "negative_control"),
    ("VTREND_A0", "VBREAK",    "mid_positive_control"),
    ("VTREND_A0", "VCUSUM",    "strong_positive_control"),
]

STRATEGIES = ["VTREND_A0", "VTREND_A1", "VBREAK", "VCUSUM"]
METRICS    = ["sharpe", "cagr", "mdd"]


# ═══════════════════════════════════════════════════════════════════
# Indicator helpers (self-contained, matching Report 17)
# ═══════════════════════════════════════════════════════════════════

def _highest_high(high, n):
    out = np.full(len(high), np.nan)
    if n <= 0 or n >= len(high):
        return out
    windows = sliding_window_view(high, n)
    out[n:] = np.max(windows[:len(high) - n], axis=1)
    return out

def _lowest_low(low, m):
    out = np.full(len(low), np.nan)
    if m <= 0 or m >= len(low):
        return out
    windows = sliding_window_view(low, m)
    out[m:] = np.min(windows[:len(low) - m], axis=1)
    return out

def _log_returns(close):
    r = np.zeros(len(close), dtype=np.float64)
    r[1:] = np.log(close[1:] / close[:-1])
    return r

def _rolling_zscore_vec(returns, window):
    """Vectorized rolling z-score — O(n) instead of O(n*w)."""
    n = len(returns)
    z = np.zeros(n, dtype=np.float64)
    if window < 2 or window >= n:
        return z
    cs = np.zeros(n + 1)
    cs[1:] = np.cumsum(returns)
    cs2 = np.zeros(n + 1)
    cs2[1:] = np.cumsum(returns ** 2)
    idx = np.arange(window, n)
    ref_sum = cs[idx] - cs[idx - window]
    ref_ss  = cs2[idx] - cs2[idx - window]
    ref_mean = ref_sum / window
    ref_var  = (ref_ss - ref_sum ** 2 / window) / (window - 1)
    ref_std  = np.sqrt(np.maximum(ref_var, 0.0))
    mask = ref_std > 1e-12
    z[window:] = np.where(mask, (returns[window:] - ref_mean) / ref_std, 0.0)
    return z

def _cusum(z, k):
    n = len(z)
    cup = np.zeros(n)
    cdn = np.zeros(n)
    for i in range(1, n):
        cup[i] = max(0, cup[i-1] + z[i] - k)
        cdn[i] = max(0, cdn[i-1] - z[i] - k)
    return cup, cdn

def _atr_p(hi, lo, cl, period):
    """Standard ATR with arbitrary period."""
    prev_cl = np.concatenate([[cl[0]], cl[:-1]])
    tr = np.maximum(hi - lo, np.maximum(np.abs(hi - prev_cl), np.abs(lo - prev_cl)))
    out = np.full_like(tr, np.nan)
    if period <= len(tr):
        out[period - 1] = np.mean(tr[:period])
        for i in range(period, len(tr)):
            out[i] = (out[i - 1] * (period - 1) + tr[i]) / period
    return out


# ═══════════════════════════════════════════════════════════════════
# Simulation with inline metrics (no array storage)
# ═══════════════════════════════════════════════════════════════════

def sim_metrics(cl, entry, exit_s, exit_atr, wi):
    """Run simulation, return (sharpe, cagr, mdd). No array storage."""
    n = len(cl)
    cash = CASH; bq = 0.0; inp = False; pk = 0.0
    pe = px = False
    prev_nav = 0.0; started = False
    navs_start = navs_end = nav_peak = 0.0; nav_min_ratio = 1.0
    rets_sum = rets_sq_sum = 0.0; n_rets = 0

    for i in range(n):
        p = cl[i]
        if i > 0:
            fp = cl[i - 1]
            if pe:
                pe = False
                bq = cash / (fp * (1.0 + CPS))
                cash = 0.0; inp = True; pk = p
            elif px:
                cash = bq * fp * (1.0 - CPS)
                bq = 0.0; inp = False; pk = 0.0; px = False
        nav = cash + bq * p
        if i >= wi:
            if not started:
                navs_start = nav; prev_nav = nav; nav_peak = nav; started = True
            else:
                if prev_nav > 0:
                    r = nav / prev_nav - 1.0
                    rets_sum += r; rets_sq_sum += r * r; n_rets += 1
                prev_nav = nav
            nav_peak = max(nav_peak, nav)
            if nav_peak > 0:
                ratio = nav / nav_peak
                if ratio < nav_min_ratio:
                    nav_min_ratio = ratio
            navs_end = nav

        ea = exit_atr[i]
        if math.isnan(ea):
            continue
        if not inp:
            if entry[i]:
                pe = True
        else:
            pk = max(pk, p)
            if p < pk - TRAIL * ea:
                px = True
            elif exit_s[i]:
                px = True

    if inp and bq > 0:
        cash = bq * cl[-1] * (1.0 - CPS)
        navs_end = cash
    if n_rets < 2 or navs_start <= 0:
        return 0.0, -100.0, 100.0
    mu = rets_sum / n_rets
    var = rets_sq_sum / n_rets - mu * mu
    std = math.sqrt(max(var, 0.0))
    sharpe = (mu / std) * ANN if std > 1e-12 else 0.0
    tr = navs_end / navs_start - 1.0
    yrs = n_rets / (6.0 * 365.25)
    cagr = ((1 + tr) ** (1.0 / yrs) - 1.0) * 100 if yrs > 0 and tr > -1 else -100.0
    mdd = (1.0 - nav_min_ratio) * 100.0
    return sharpe, cagr, mdd


# ═══════════════════════════════════════════════════════════════════
# Vectorized signal building
# ═══════════════════════════════════════════════════════════════════

def build_all_signals(cl, hi, lo, at14, at20, vd, ll40, log_ret, slow):
    """Build entry/exit signals for all 4 strategies at given slow_period.

    Pre-computed (caller must supply):
      at14, at20: ATR arrays
      vd: VDO array
      ll40: _lowest_low(lo, 40) — VBREAK exit
      log_ret: _log_returns(cl) — VCUSUM input

    Per-timescale (computed here):
      EMA(fast), EMA(slow), Donchian(slow), rolling z-score, CUSUM

    Returns dict[strategy_name] → (entry, exit_s, exit_atr).
    """
    n = len(cl)
    fast_p = max(5, slow // 4)
    ef = _ema(cl, fast_p)
    es = _ema(cl, slow)

    # ── A0: EMA cross + VDO, gate on at14 ──
    valid_a0 = ~(np.isnan(ef) | np.isnan(es) | np.isnan(at14))
    valid_a0[0] = False
    entry_a0 = valid_a0 & (ef > es) & (vd > 0.0)
    exit_a0 = valid_a0 & (ef < es)

    # ── A1: same conditions, also gate on at20 ──
    valid_a1 = valid_a0 & ~np.isnan(at20)
    entry_a1 = valid_a1 & (ef > es) & (vd > 0.0)
    exit_a1 = valid_a1 & (ef < es)

    # ── VBREAK: Donchian(slow) breakout, Donchian(40) exit ──
    hh = _highest_high(hi, slow)
    valid_vb = ~(np.isnan(hh) | np.isnan(ll40) | np.isnan(at14))
    valid_vb[0] = False
    entry_vb = valid_vb & (cl > hh) & (vd > 0.0)
    exit_vb = valid_vb & (cl < ll40)

    # ── VCUSUM: CUSUM(slow, k=0.5, h=4.0) ──
    z = _rolling_zscore_vec(log_ret, slow)
    cup, cdn = _cusum(z, 0.5)
    valid_vc = ~np.isnan(at14)
    valid_vc[0] = False
    entry_vc = valid_vc & (cup > 4.0) & (vd > 0.0)
    exit_vc = valid_vc & (cdn > 4.0)

    return {
        "VTREND_A0": (entry_a0, exit_a0, at14),
        "VTREND_A1": (entry_a1, exit_a1, at20),
        "VBREAK":    (entry_vb, exit_vb, at14),
        "VCUSUM":    (entry_vc, exit_vc, at14),
    }


def verdict(p):
    """Verdict scale matching binomial_correction.py."""
    if p < 0.001: return "PROVEN ***"
    if p < 0.01:  return "PROVEN **"
    if p < 0.025: return "PROVEN *"
    if p < 0.05:  return "STRONG"
    if p < 0.10:  return "MARGINAL"
    return "NOT SIG"


# ═══════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════

def main():
    t0_total = time.time()
    print("=" * 80)
    print("20 — WIN-COUNT / MULTI-TIMESCALE CONTROL PAIR AUDIT")
    print("=" * 80)
    print(f"  Timescales: {N_SP} ({SLOW_PERIODS[0]} .. {SLOW_PERIODS[-1]})")
    print(f"  Strategies: {', '.join(STRATEGIES)}")
    print(f"  Pairs: {len(PAIRS)}")
    print(f"  Cost: {COST.round_trip_bps} bps RT (harsh)")
    print(f"  Bootstrap: {N_BOOT} VCBB paths, block={BLKSZ}")

    # ── Load data ─────────────────────────────────────────────────
    print("\nLoading data...")
    feed = DataFeed(DATA, start=START, end=END, warmup_days=WARMUP)
    h4 = feed.h4_bars
    n_bars = len(h4)
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
    print(f"  {n_bars} H4 bars, warmup idx={wi}, trading={n_bars - wi} bars")

    # ══════════════════════════════════════════════════════════════
    # VARIANT 1: REAL-DATA WINS
    # ══════════════════════════════════════════════════════════════

    print("\n" + "=" * 80)
    print("VARIANT 1: REAL-DATA WINS AT 16 TIMESCALES")
    print("=" * 80)

    at14 = _atr(hi, lo, cl, ATR_P)
    at20 = _atr_p(hi, lo, cl, 20)
    vd   = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)
    ll40 = _lowest_low(lo, 40)
    log_ret = _log_returns(cl)

    # real_metrics[strategy][timescale_idx] = {"sharpe": ..., "cagr": ..., "mdd": ...}
    real_metrics = {s: {} for s in STRATEGIES}

    print(f"\n  {'SP':>5s}", end="")
    for s in STRATEGIES:
        abbr = s.replace("VTREND_", "")
        print(f"   {abbr + '_Sh':>7s} {abbr + '_CG':>7s} {abbr + '_MD':>7s}", end="")
    print()
    print("  " + "-" * (5 + len(STRATEGIES) * 24))

    t0_v1 = time.time()
    for j, slow in enumerate(SLOW_PERIODS):
        signals = build_all_signals(cl, hi, lo, at14, at20, vd, ll40, log_ret, slow)
        print(f"  {slow:>5d}", end="")
        for s in STRATEGIES:
            entry, exit_s, exit_atr = signals[s]
            sh, cg, md = sim_metrics(cl, entry, exit_s, exit_atr, wi)
            real_metrics[s][j] = {"sharpe": sh, "cagr": cg, "mdd": md}
            print(f"   {sh:>7.3f} {cg:>6.1f}% {md:>6.1f}%", end="")
        print()
    v1_time = time.time() - t0_v1
    print(f"\n  V1 simulations: {v1_time:.1f}s")

    # Count wins per pair per metric
    print(f"\n  Win counts (real data, strict > / < for MDD):")
    print(f"  {'Pair':<28s}  {'Metric':<8s}  {'W':>3s}  {'L':>3s}  "
          f"{'T':>3s}  {'p_binom':>10s}  {'Verdict':>12s}")
    print("  " + "-" * 78)

    v1_results = {}
    for a_name, b_name, ctype in PAIRS:
        pair_key = f"{a_name} vs {b_name}"
        v1_results[pair_key] = {"control_type": ctype}

        for metric in METRICS:
            wins = losses = ties = 0
            win_detail = []
            for j in range(N_SP):
                a_val = real_metrics[a_name][j][metric]
                b_val = real_metrics[b_name][j][metric]
                if metric == "mdd":
                    # Lower MDD is better → A wins if A < B
                    if a_val < b_val:
                        wins += 1; win_detail.append(1)
                    elif a_val > b_val:
                        losses += 1; win_detail.append(0)
                    else:
                        ties += 1; win_detail.append(0)
                else:
                    # Higher Sharpe/CAGR is better → A wins if A > B
                    if a_val > b_val:
                        wins += 1; win_detail.append(1)
                    elif a_val < b_val:
                        losses += 1; win_detail.append(0)
                    else:
                        ties += 1; win_detail.append(0)

            p_binom = sp_stats.binomtest(wins, N_SP, 0.5,
                                          alternative='greater').pvalue
            v = verdict(p_binom)
            print(f"  {pair_key:<28s}  {metric:<8s}  {wins:>3d}  {losses:>3d}  "
                  f"{ties:>3d}  {p_binom:>10.4e}  {v:>12s}")

            v1_results[pair_key][metric] = {
                "wins": wins, "losses": losses, "ties": ties,
                "win_detail": win_detail,
                "p_binomial": float(p_binom),
                "verdict": v,
            }

    # ══════════════════════════════════════════════════════════════
    # VARIANT 2: BOOTSTRAP-THEN-BINOMIAL
    # ══════════════════════════════════════════════════════════════

    print("\n" + "=" * 80)
    print(f"VARIANT 2: BOOTSTRAP-THEN-BINOMIAL ({N_BOOT} VCBB paths)")
    print("=" * 80)

    # Prepare VCBB
    cr, hr, lr, vol_r, tb_r = make_ratios(cl, hi, lo, vo, tb)
    n_trans = len(cr)
    p0 = cl[0]
    vcbb = precompute_vcbb(cr, BLKSZ, ctx=CTX)

    # Storage: boot_metrics[strategy] → {sh, cg, md} each (N_BOOT, N_SP)
    boot_sh = {s: np.zeros((N_BOOT, N_SP)) for s in STRATEGIES}
    boot_cg = {s: np.zeros((N_BOOT, N_SP)) for s in STRATEGIES}
    boot_md = {s: np.zeros((N_BOOT, N_SP)) for s in STRATEGIES}

    t0_boot = time.time()
    for b in range(N_BOOT):
        rng = np.random.default_rng(SEED + b)
        c, h, l, v, t = gen_path_vcbb(
            cr, hr, lr, vol_r, tb_r, n_trans, BLKSZ, p0, rng,
            vcbb=vcbb, K=K_VCBB)

        # Common indicators (once per path)
        _at14 = _atr(h, l, c, ATR_P)
        _at20 = _atr_p(h, l, c, 20)
        _vd   = _vdo(c, h, l, v, t, VDO_F, VDO_S)
        _ll40 = _lowest_low(l, 40)
        _lr   = _log_returns(c)

        for j, slow in enumerate(SLOW_PERIODS):
            sigs = build_all_signals(c, h, l, _at14, _at20, _vd, _ll40, _lr, slow)
            for s in STRATEGIES:
                entry, exit_s, exit_atr = sigs[s]
                sh, cg, md = sim_metrics(c, entry, exit_s, exit_atr, wi)
                boot_sh[s][b, j] = sh
                boot_cg[s][b, j] = cg
                boot_md[s][b, j] = md

        if (b + 1) % 50 == 0:
            elapsed = time.time() - t0_boot
            eta = elapsed / (b + 1) * (N_BOOT - b - 1)
            print(f"  ... {b + 1}/{N_BOOT} ({elapsed:.0f}s, ETA {eta:.0f}s)")

    boot_time = time.time() - t0_boot
    print(f"\n  Bootstrap complete: {boot_time:.0f}s")

    # ── Compute P(win) per timescale per pair per metric ──
    v2_results = {}
    for a_name, b_name, ctype in PAIRS:
        pair_key = f"{a_name} vs {b_name}"
        v2_results[pair_key] = {"control_type": ctype}

        print(f"\n  ── {pair_key} ({ctype}) ──")
        print(f"  {'SP':>5s}  {'P(Sh+)':>8s}  {'P(CG+)':>8s}  {'P(MD-)':>8s}")
        print("  " + "-" * 35)

        # Compute deltas: positive = A better
        d_sh = boot_sh[a_name] - boot_sh[b_name]         # higher Sharpe = better
        d_cg = boot_cg[a_name] - boot_cg[b_name]         # higher CAGR = better
        d_md = boot_md[b_name] - boot_md[a_name]          # lower MDD for A = better

        for metric, delta in [("sharpe", d_sh), ("cagr", d_cg), ("mdd", d_md)]:
            p_win = np.mean(delta > 0, axis=0)  # (N_SP,)
            win_count = int(np.sum(p_win > 0.50))
            p_binom = sp_stats.binomtest(win_count, N_SP, 0.5,
                                          alternative='greater').pvalue
            v = verdict(p_binom)
            v2_results[pair_key][metric] = {
                "p_win_per_timescale": [round(float(pw), 4) for pw in p_win],
                "wins": win_count,
                "p_binomial": float(p_binom),
                "verdict": v,
            }

        # Print P(win) table
        pw_sh = np.mean(d_sh > 0, axis=0)
        pw_cg = np.mean(d_cg > 0, axis=0)
        pw_md = np.mean(d_md > 0, axis=0)
        for j, slow in enumerate(SLOW_PERIODS):
            print(f"  {slow:>5d}  {pw_sh[j]:>7.1%}  {pw_cg[j]:>7.1%}  {pw_md[j]:>7.1%}")

        # Summary
        print(f"\n  {'Metric':<8s}  {'Wins':>5s}  {'p_binom':>10s}  {'Verdict':>12s}")
        print("  " + "-" * 42)
        for metric in METRICS:
            r = v2_results[pair_key][metric]
            print(f"  {metric:<8s}  {r['wins']:>2d}/{N_SP:>2d}  "
                  f"{r['p_binomial']:>10.4e}  {r['verdict']:>12s}")

    # ══════════════════════════════════════════════════════════════
    # VARIANT 3: DOF-CORRECTED BINOMIAL
    # ══════════════════════════════════════════════════════════════

    print("\n" + "=" * 80)
    print("VARIANT 3: DOF-CORRECTED BINOMIAL")
    print("=" * 80)

    v3_results = {}
    for a_name, b_name, ctype in PAIRS:
        pair_key = f"{a_name} vs {b_name}"
        v3_results[pair_key] = {"control_type": ctype}

        print(f"\n  ── {pair_key} ({ctype}) ──")

        for metric in METRICS:
            # Binary win matrix: (N_BOOT, N_SP)
            if metric == "sharpe":
                delta = boot_sh[a_name] - boot_sh[b_name]
            elif metric == "cagr":
                delta = boot_cg[a_name] - boot_cg[b_name]
            else:
                delta = boot_md[b_name] - boot_md[a_name]

            binary_wins = (delta > 0).astype(float)
            p_win = np.mean(binary_wins, axis=0)
            win_count = int(np.sum(p_win > 0.50))

            # Correlation matrix of binary wins across timescales
            col_stds = np.std(binary_wins, axis=0)
            if col_stds.min() > 1e-10:
                corr_mat = np.corrcoef(binary_wins.T)  # (N_SP, N_SP)
            else:
                # Degenerate: some timescales have constant outcome
                corr_mat = np.eye(N_SP)

            meff = compute_meff(corr_mat)
            result = corrected_binomial(win_count, N_SP, corr_mat)

            p_nom = result["p_nominal"]
            p_corr = result["corrected"]["conservative"]["p_value"]
            m_eff_val = result["corrected"]["conservative"]["m_eff"]
            v_nom = verdict(p_nom)
            v_corr = verdict(p_corr)

            adj_r = [float(corr_mat[j, j + 1]) for j in range(N_SP - 1)]
            mean_adj_r = float(np.mean(adj_r))

            v3_results[pair_key][metric] = {
                "wins": win_count,
                "p_nominal": float(p_nom),
                "verdict_nominal": v_nom,
                "p_corrected": float(p_corr),
                "verdict_corrected": v_corr,
                "meff": {k: float(v_) for k, v_ in meff.items()},
                "mean_adj_corr": mean_adj_r,
                "corrected_detail": {
                    method: {
                        "m_eff": float(d["m_eff"]),
                        "wins_scaled": int(d["wins_scaled"]),
                        "p_value": float(d["p_value"]),
                    }
                    for method, d in result["corrected"].items()
                },
            }

        # Print table
        print(f"\n  {'Metric':<8s}  {'Wins':>5s}  {'Nominal':>10s}  "
              f"{'V_nom':>12s}  {'M_eff':>6s}  {'Corrected':>10s}  "
              f"{'V_corr':>12s}  {'Adj_r':>6s}")
        print("  " + "-" * 88)
        for metric in METRICS:
            r = v3_results[pair_key][metric]
            print(f"  {metric:<8s}  {r['wins']:>2d}/{N_SP:>2d}  "
                  f"{r['p_nominal']:>10.4e}  {r['verdict_nominal']:>12s}  "
                  f"{r['meff']['conservative']:>5.1f}  "
                  f"{r['p_corrected']:>10.4e}  {r['verdict_corrected']:>12s}  "
                  f"{r['mean_adj_corr']:>5.3f}")

    # ══════════════════════════════════════════════════════════════
    # TIMESCALE DEPENDENCE ANALYSIS
    # ══════════════════════════════════════════════════════════════

    print("\n" + "=" * 80)
    print("TIMESCALE DEPENDENCE ANALYSIS")
    print("=" * 80)

    ts_dep = {}
    for a_name, b_name, ctype in PAIRS:
        pair_key = f"{a_name} vs {b_name}"
        ts_dep[pair_key] = {}

        print(f"\n  ── {pair_key} ──")

        for metric in ["sharpe", "cagr"]:
            if metric == "sharpe":
                delta = boot_sh[a_name] - boot_sh[b_name]
            else:
                delta = boot_cg[a_name] - boot_cg[b_name]

            binary_wins = (delta > 0).astype(float)
            col_stds = np.std(binary_wins, axis=0)

            # Binary win correlation
            if col_stds.min() > 1e-10:
                corr_bin = np.corrcoef(binary_wins.T)
                adj_r_bin = [corr_bin[j, j + 1] for j in range(N_SP - 1)]
                meff_bin = compute_meff(corr_bin)
            else:
                adj_r_bin = [0.0] * (N_SP - 1)
                meff_bin = {"nyholt": N_SP, "li_ji": N_SP,
                            "galwey": N_SP, "conservative": N_SP}

            # Continuous delta correlation (for reference)
            cont_stds = np.std(delta, axis=0)
            if cont_stds.min() > 1e-10:
                corr_cont = np.corrcoef(delta.T)
                adj_r_cont = [corr_cont[j, j + 1] for j in range(N_SP - 1)]
            else:
                adj_r_cont = [0.0] * (N_SP - 1)

            print(f"\n    {metric.upper()}:")
            print(f"      Binary win:  mean_adj_r={np.mean(adj_r_bin):.3f}  "
                  f"range=[{min(adj_r_bin):.3f}, {max(adj_r_bin):.3f}]  "
                  f"M_eff={meff_bin['conservative']:.1f}/{N_SP}")
            print(f"      Continuous:  mean_adj_r={np.mean(adj_r_cont):.3f}  "
                  f"range=[{min(adj_r_cont):.3f}, {max(adj_r_cont):.3f}]")

            ts_dep[pair_key][metric] = {
                "binary_mean_adj_r": round(float(np.mean(adj_r_bin)), 4),
                "binary_meff_conservative": float(meff_bin["conservative"]),
                "continuous_mean_adj_r": round(float(np.mean(adj_r_cont)), 4),
            }

    # ══════════════════════════════════════════════════════════════
    # COMPARISON WITH CI-BASED GATES (Reports 18/19)
    # ══════════════════════════════════════════════════════════════

    print("\n" + "=" * 80)
    print("COMPARISON: WIN-COUNT vs CI-BASED GATES (Reports 18/19)")
    print("=" * 80)

    # Reference from Report 18 (known results, all FAIL)
    ci_ref = {
        "VTREND_A0 vs VTREND_A1": {"boot_ci": "FAIL", "sub_ci": "FAIL",
                                     "expected": "FAIL"},
        "VTREND_A0 vs VBREAK":    {"boot_ci": "FAIL", "sub_ci": "FAIL",
                                     "expected": "PASS"},
        "VTREND_A0 vs VCUSUM":    {"boot_ci": "FAIL", "sub_ci": "FAIL",
                                     "expected": "PASS"},
    }

    def pf(p_val, threshold=0.05):
        return "PASS" if p_val < threshold else "FAIL"

    comparison = {}
    print(f"\n  {'Pair':<28s}  {'Expect':>6s}  {'BCI':>5s}  {'SCI':>5s}  "
          f"{'V1sh':>5s}  {'V1cg':>5s}  {'V2sh':>5s}  {'V2cg':>5s}  "
          f"{'V3sh':>5s}  {'V3cg':>5s}")
    print("  " + "-" * 100)

    for a_name, b_name, ctype in PAIRS:
        pair_key = f"{a_name} vs {b_name}"
        ci = ci_ref[pair_key]

        v1_sh_pf = pf(v1_results[pair_key]["sharpe"]["p_binomial"])
        v1_cg_pf = pf(v1_results[pair_key]["cagr"]["p_binomial"])
        v2_sh_pf = pf(v2_results[pair_key]["sharpe"]["p_binomial"])
        v2_cg_pf = pf(v2_results[pair_key]["cagr"]["p_binomial"])
        v3_sh_pf = pf(v3_results[pair_key]["sharpe"]["p_corrected"])
        v3_cg_pf = pf(v3_results[pair_key]["cagr"]["p_corrected"])

        print(f"  {pair_key:<28s}  {ci['expected']:>6s}  {ci['boot_ci']:>5s}  "
              f"{ci['sub_ci']:>5s}  {v1_sh_pf:>5s}  {v1_cg_pf:>5s}  "
              f"{v2_sh_pf:>5s}  {v2_cg_pf:>5s}  {v3_sh_pf:>5s}  {v3_cg_pf:>5s}")

        comparison[pair_key] = {
            "expected": ci["expected"],
            "boot_ci": ci["boot_ci"],
            "sub_ci": ci["sub_ci"],
            "v1_sharpe": v1_sh_pf,
            "v1_cagr": v1_cg_pf,
            "v2_sharpe": v2_sh_pf,
            "v2_cagr": v2_cg_pf,
            "v3_sharpe": v3_sh_pf,
            "v3_cagr": v3_cg_pf,
        }

    # ── Score card ──
    print(f"\n  Score card (correct gate decisions):")
    methods = {
        "Boot CI (R18)":     ("boot_ci",),
        "Sub CI (R18)":      ("sub_ci",),
        "V1 (Sharpe)":       ("v1_sharpe",),
        "V1 (CAGR)":         ("v1_cagr",),
        "V2 (Sharpe)":       ("v2_sharpe",),
        "V2 (CAGR)":         ("v2_cagr",),
        "V3 (Sharpe)":       ("v3_sharpe",),
        "V3 (CAGR)":         ("v3_cagr",),
    }
    print(f"  {'Method':<20s}  {'Neg':>5s}  {'Mid+':>5s}  {'Str+':>5s}  {'Score':>5s}")
    print("  " + "-" * 48)
    for method_label, keys in methods.items():
        correct = 0
        results_row = []
        for a_name, b_name, ctype in PAIRS:
            pk = f"{a_name} vs {b_name}"
            expected = ci_ref[pk]["expected"]
            actual = comparison[pk][keys[0]]
            ok = (actual == expected)
            correct += int(ok)
            results_row.append("OK" if ok else "MISS")
        print(f"  {method_label:<20s}  {results_row[0]:>5s}  {results_row[1]:>5s}  "
              f"{results_row[2]:>5s}  {correct}/3")

    # ══════════════════════════════════════════════════════════════
    # SAVE
    # ══════════════════════════════════════════════════════════════

    elapsed = time.time() - t0_total

    # Strategy metrics as serializable dicts
    real_met_save = {}
    for s in STRATEGIES:
        real_met_save[s] = {}
        for j in range(N_SP):
            real_met_save[s][str(SLOW_PERIODS[j])] = {
                k: round(v_, 6) for k, v_ in real_metrics[s][j].items()
            }

    output = {
        "config": {
            "slow_periods": SLOW_PERIODS,
            "n_sp": N_SP,
            "cost_rt_bps": float(COST.round_trip_bps),
            "n_boot": N_BOOT,
            "blksz": BLKSZ,
            "seed": SEED,
            "ctx": CTX,
            "k_vcbb": K_VCBB,
            "start": START,
            "end": END,
            "warmup_days": WARMUP,
            "n_bars": n_bars,
            "warmup_idx": wi,
        },
        "real_data_metrics": real_met_save,
        "v1_real_data_wins": v1_results,
        "v2_bootstrap_binomial": v2_results,
        "v3_dof_corrected": v3_results,
        "timescale_dependence": ts_dep,
        "comparison": comparison,
        "total_time_s": round(elapsed, 1),
        "boot_time_s": round(boot_time, 1),
    }

    out_path = OUTDIR / "20_win_count_control_pair_audit.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\n  Saved: {out_path}")
    print(f"  Total time: {elapsed:.0f}s")


if __name__ == "__main__":
    main()
