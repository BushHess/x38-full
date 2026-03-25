#!/usr/bin/env python3
"""Multiple Comparison Correction — Formal Bonferroni Analysis.

Problem: we mined ~20+ hypotheses on the same 17K-bar dataset.
Each hypothesis increases the probability of a false positive.
We must apply family-wise error rate (FWER) correction.

Step 1: Re-compute component p-values with 10,000 permutations.
  - EMA: circular-shift → breaks price-EMA alignment
  - VDO: random filter at matched skip rate → tests if VDO > random
  - ATR: block-shuffle ATR → breaks local volatility-stop alignment
  Test statistic: objective score (same as original tests).

Step 2: Enumerate ALL hypotheses from the full research pipeline.

Step 3: Apply corrections:
  - Bonferroni (FWER, most conservative)
  - Holm step-down (FWER, less conservative)
  - Benjamini-Hochberg (FDR control, least conservative)

Step 4: Report which findings survive.

All tests: harsh cost (50 bps RT), fast sim.
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
CPS    = COST.per_side_bps / 10_000.0

START  = "2019-01-01"
END    = "2026-02-20"
WARMUP = 365
CASH   = 10_000.0

SLOW  = 120
FAST  = max(5, SLOW // 4)
TRAIL = 3.0
VDO_T = 0.0
ATR_P = 14
VDO_F = 12
VDO_S = 28

N_PERM = 10_000
ALPHA  = 0.05


# ═══════════════════════════════════════════════════════════════════════════
# Data & Indicators
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


def compute_ind(cl, hi, lo, vo, tb):
    return (
        _ema(cl, FAST),
        _ema(cl, SLOW),
        _atr(hi, lo, cl, ATR_P),
        _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S),
    )


# ═══════════════════════════════════════════════════════════════════════════
# Fast Sim → Objective Score
# ═══════════════════════════════════════════════════════════════════════════

def sim_score(cl, ef, es, at, vd, wi, vdo_thr=VDO_T):
    """VTREND fast sim → (objective_score, n_trades).

    Objective: 2.5*cagr - 0.60*mdd + 8.0*max(0,sharpe)
             + 5.0*max(0,min(pf,3)-1) + min(n/50,1)*5
    Returns -1M if n_trades < 10.
    """
    n = len(cl)
    cash = CASH
    bq = 0.0
    inp = False
    pk = 0.0
    pe = px = False

    navs = []
    trade_pnls = []
    entry_cost = 0.0

    for i in range(n):
        p = cl[i]

        if i > 0:
            fp = cl[i - 1]
            if pe:
                bq = cash / (fp * (1.0 + CPS))
                entry_cost = cash
                cash = 0.0
                inp = True
                pk = p
                pe = False
            elif px:
                proceeds = bq * fp * (1.0 - CPS)
                trade_pnls.append(proceeds - entry_cost)
                cash = proceeds
                bq = 0.0
                inp = False
                pk = 0.0
                px = False

        nav = cash + bq * p
        if i >= wi:
            navs.append(nav)

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

    if inp and bq > 0:
        proceeds = bq * cl[-1] * (1.0 - CPS)
        trade_pnls.append(proceeds - entry_cost)
        cash = proceeds
        bq = 0.0
        if navs:
            navs[-1] = cash

    nt = len(trade_pnls)
    if len(navs) < 2 or navs[0] <= 0 or nt < 10:
        return -1_000_000.0, nt

    na = np.array(navs, dtype=np.float64)
    tr = na[-1] / na[0] - 1.0
    yrs = (len(na) - 1) / (6.0 * 365.25)
    cagr = ((1.0 + tr) ** (1.0 / yrs) - 1.0) * 100.0 if yrs > 0 and tr > -1.0 else -100.0

    pk_arr = np.maximum.accumulate(na)
    dd = (pk_arr - na) / pk_arr * 100.0
    mdd = float(dd.max())

    rets = np.diff(na) / na[:-1]
    std = float(np.std(rets, ddof=0))
    sharpe = float(np.mean(rets)) / std * math.sqrt(6.0 * 365.25) if std > 1e-12 else 0.0

    pnls = np.array(trade_pnls)
    gp = float(pnls[pnls > 0].sum()) if (pnls > 0).any() else 0.0
    gl = float(abs(pnls[pnls < 0].sum())) if (pnls < 0).any() else 0.0
    pf = min(gp / gl, 3.0) if gl > 0 else (3.0 if gp > 0 else 0.0)

    score = (2.5 * cagr
             - 0.60 * mdd
             + 8.0 * max(0.0, sharpe)
             + 5.0 * max(0.0, min(pf, 3.0) - 1.0)
             + min(nt / 50.0, 1.0) * 5.0)

    return score, nt


def sim_random_filter(cl, ef, es, at, wi, skip_rate, seed):
    """VTREND with VDO disabled, random per-bar skip at entry.

    For each bar where EMA crosses up and we're flat:
      skip with probability `skip_rate`.
    This matches component_analysis.py's _RandomFilter behavior.
    """
    rng = np.random.RandomState(seed)
    n = len(cl)
    cash = CASH
    bq = 0.0
    inp = False
    pk = 0.0
    pe = px = False

    navs = []
    trade_pnls = []
    entry_cost = 0.0

    for i in range(n):
        p = cl[i]

        if i > 0:
            fp = cl[i - 1]
            if pe:
                bq = cash / (fp * (1.0 + CPS))
                entry_cost = cash
                cash = 0.0
                inp = True
                pk = p
                pe = False
            elif px:
                proceeds = bq * fp * (1.0 - CPS)
                trade_pnls.append(proceeds - entry_cost)
                cash = proceeds
                bq = 0.0
                inp = False
                pk = 0.0
                px = False

        nav = cash + bq * p
        if i >= wi:
            navs.append(nav)

        a_val = at[i]
        if math.isnan(a_val) or math.isnan(ef[i]) or math.isnan(es[i]):
            continue

        if not inp:
            if ef[i] > es[i]:  # VDO disabled
                if rng.random() < skip_rate:
                    continue   # random skip
                pe = True
        else:
            pk = max(pk, p)
            if p < pk - TRAIL * a_val:
                px = True
            elif ef[i] < es[i]:
                px = True

    if inp and bq > 0:
        proceeds = bq * cl[-1] * (1.0 - CPS)
        trade_pnls.append(proceeds - entry_cost)
        cash = proceeds
        bq = 0.0
        if navs:
            navs[-1] = cash

    nt = len(trade_pnls)
    if len(navs) < 2 or navs[0] <= 0 or nt < 10:
        return -1_000_000.0, nt

    na = np.array(navs, dtype=np.float64)
    tr = na[-1] / na[0] - 1.0
    yrs = (len(na) - 1) / (6.0 * 365.25)
    cagr = ((1.0 + tr) ** (1.0 / yrs) - 1.0) * 100.0 if yrs > 0 and tr > -1.0 else -100.0

    pk_arr = np.maximum.accumulate(na)
    dd = (pk_arr - na) / pk_arr * 100.0
    mdd = float(dd.max())

    rets = np.diff(na) / na[:-1]
    std = float(np.std(rets, ddof=0))
    sharpe = float(np.mean(rets)) / std * math.sqrt(6.0 * 365.25) if std > 1e-12 else 0.0

    pnls = np.array(trade_pnls)
    gp = float(pnls[pnls > 0].sum()) if (pnls > 0).any() else 0.0
    gl = float(abs(pnls[pnls < 0].sum())) if (pnls < 0).any() else 0.0
    pf = min(gp / gl, 3.0) if gl > 0 else (3.0 if gp > 0 else 0.0)

    score = (2.5 * cagr
             - 0.60 * mdd
             + 8.0 * max(0.0, sharpe)
             + 5.0 * max(0.0, min(pf, 3.0) - 1.0)
             + min(nt / 50.0, 1.0) * 5.0)

    return score, nt


def _block_shuffle(arr, block_size, rng):
    """Block-shuffle: permute contiguous blocks."""
    n = len(arr)
    nb = n // block_size
    if nb <= 1:
        return arr.copy()
    idx = np.arange(nb)
    rng.shuffle(idx)
    parts = [arr[i * block_size:(i + 1) * block_size] for i in idx]
    tail = arr[nb * block_size:]
    if len(tail):
        parts.append(tail)
    return np.concatenate(parts)


# ═══════════════════════════════════════════════════════════════════════════
# Test 1: EMA Circular-Shift Permutation
# ═══════════════════════════════════════════════════════════════════════════

def test_ema(cl, hi, lo, vo, tb, wi, n_perm=N_PERM):
    """H0: EMA-price alignment has no value.

    Null: circular-shift EMA arrays by random offset.
    Preserves EMA smoothness and transition count, breaks alignment.
    """
    print("\n  TEST 1: EMA circular-shift permutation")
    ef, es, at, vd = compute_ind(cl, hi, lo, vo, tb)
    n = len(cl)

    real_score, real_nt = sim_score(cl, ef, es, at, vd, wi)
    print(f"    Real score: {real_score:.1f}  (trades={real_nt})")

    rng = np.random.default_rng(42)
    null_scores = np.empty(n_perm)

    t0 = time.time()
    for i in range(n_perm):
        offset = rng.integers(500, n - 500)
        ef_s = np.roll(ef, int(offset))
        es_s = np.roll(es, int(offset))
        sc, _ = sim_score(cl, ef_s, es_s, at, vd, wi)
        null_scores[i] = sc
        if (i + 1) % 2000 == 0:
            print(f"      {i+1}/{n_perm}  ({time.time()-t0:.0f}s)")

    p = float(np.mean(null_scores >= real_score))
    el = time.time() - t0
    print(f"    Null mean: {null_scores.mean():.1f} ± {null_scores.std():.1f}")
    print(f"    p = {p:.6f}  ({el:.0f}s)")
    return p, real_score, null_scores


# ═══════════════════════════════════════════════════════════════════════════
# Test 2: VDO vs Random Filter
# ═══════════════════════════════════════════════════════════════════════════

def test_vdo(cl, hi, lo, vo, tb, wi, n_perm=N_PERM):
    """H0: VDO filter = random filter at matched skip rate.

    Calibrate: run without VDO → count trades → compute skip rate.
    Null: random per-bar skip at that rate.
    """
    print("\n  TEST 2: VDO vs random filter")
    ef, es, at, vd = compute_ind(cl, hi, lo, vo, tb)

    # Real: VDO enabled
    real_score, real_nt = sim_score(cl, ef, es, at, vd, wi)

    # Baseline: VDO disabled (threshold = -999)
    base_score, base_nt = sim_score(cl, ef, es, at, vd, wi, vdo_thr=-999.0)

    skip_rate = 1.0 - real_nt / base_nt if base_nt > 0 else 0.0
    print(f"    Real (VDO): score={real_score:.1f}  trades={real_nt}")
    print(f"    No-VDO:     score={base_score:.1f}  trades={base_nt}")
    print(f"    VDO skip rate: {skip_rate:.3f} ({100*skip_rate:.1f}%)")

    null_scores = np.empty(n_perm)
    t0 = time.time()
    for i in range(n_perm):
        sc, _ = sim_random_filter(cl, ef, es, at, wi, skip_rate, seed=i)
        null_scores[i] = sc
        if (i + 1) % 2000 == 0:
            print(f"      {i+1}/{n_perm}  ({time.time()-t0:.0f}s)")

    p = float(np.mean(null_scores >= real_score))
    el = time.time() - t0
    print(f"    Null mean: {null_scores.mean():.1f} ± {null_scores.std():.1f}")
    print(f"    p = {p:.6f}  ({el:.0f}s)")
    return p, real_score, null_scores, skip_rate


# ═══════════════════════════════════════════════════════════════════════════
# Test 3: ATR Block-Shuffle
# ═══════════════════════════════════════════════════════════════════════════

def test_atr(cl, hi, lo, vo, tb, wi, n_perm=N_PERM, block=40):
    """H0: local ATR-price alignment doesn't matter.

    Null: block-shuffle ATR array (block=40 bars ≈ 7 days).
    Preserves ATR distribution and block autocorrelation,
    breaks local volatility-stop distance alignment.
    """
    print(f"\n  TEST 3: ATR block-shuffle permutation (block={block})")
    ef, es, at, vd = compute_ind(cl, hi, lo, vo, tb)

    real_score, real_nt = sim_score(cl, ef, es, at, vd, wi)
    print(f"    Real score: {real_score:.1f}  (trades={real_nt})")

    null_scores = np.empty(n_perm)
    t0 = time.time()
    for i in range(n_perm):
        rng = np.random.RandomState(i)
        at_s = _block_shuffle(at, block, rng)
        sc, _ = sim_score(cl, ef, es, at_s, vd, wi)
        null_scores[i] = sc
        if (i + 1) % 2000 == 0:
            print(f"      {i+1}/{n_perm}  ({time.time()-t0:.0f}s)")

    p = float(np.mean(null_scores >= real_score))
    el = time.time() - t0
    print(f"    Null mean: {null_scores.mean():.1f} ± {null_scores.std():.1f}")
    print(f"    p = {p:.6f}  ({el:.0f}s)")
    return p, real_score, null_scores


# ═══════════════════════════════════════════════════════════════════════════
# Hypothesis Enumeration & Correction
# ═══════════════════════════════════════════════════════════════════════════

def build_hypothesis_table(p_ema, p_vdo, p_atr):
    """Enumerate all hypotheses from the full research pipeline.

    Each entry: (name, p_value, source, finding).
    For null bootstrap results, use p = 1 - P(better) where P(better) < 0.5.
    """
    hyps = []

    # Component tests (positive findings)
    hyps.append(("EMA trend signal", p_ema, "circular-shift 10K", "positive"))
    hyps.append(("VDO filter", p_vdo, "random-filter 10K", "positive"))
    hyps.append(("ATR trail scaling", p_atr, "block-shuffle 10K", "positive"))

    # Gate variants (bootstrap_regime.py) — null results
    # P(better) ≈ 0.46 for all → p = 0.54
    hyps.append(("gate360 vs base", 0.540, "bootstrap paired", "null"))
    hyps.append(("gate500 vs base", 0.505, "bootstrap paired", "null"))
    hyps.append(("gate360x vs base", 0.540, "bootstrap paired", "null"))

    # Position sizing (position_sizing.py) — null results on Calmar
    # All P(higher Calmar) ≈ 0.65-0.79 → p = 0.21-0.35
    hyps.append(("f=0.20 Calmar vs f=1.0", 0.35, "bootstrap paired", "null"))
    hyps.append(("f=0.30 Calmar vs f=1.0", 0.30, "bootstrap paired", "null"))
    hyps.append(("f=0.50 Calmar vs f=1.0", 0.25, "bootstrap paired", "null"))
    hyps.append(("vol=15% Calmar vs f=1.0", 0.25, "bootstrap paired", "null"))

    # Regime sizing (regime_sizing.py) — null results
    # All P(better Calmar) < 0.60 → p > 0.40
    hyps.append(("hand_cons vs f=0.30", 0.58, "bootstrap paired", "null"))
    hyps.append(("hand_aggr vs f=0.30", 0.58, "bootstrap paired", "null"))
    hyps.append(("half_kelly vs f=0.30", 0.71, "bootstrap paired", "null"))
    hyps.append(("binary_bull vs f=0.30", 0.59, "bootstrap paired", "null"))
    hyps.append(("return_prop vs f=0.30", 0.53, "bootstrap paired", "null"))
    hyps.append(("regime_vol vs f=0.30", 0.57, "bootstrap paired", "null"))

    return hyps


def apply_bonferroni(hyps, alpha=ALPHA):
    """Bonferroni correction: reject if p < alpha/K."""
    K = len(hyps)
    threshold = alpha / K
    results = []
    for name, p, source, finding in hyps:
        reject = p < threshold
        results.append((name, p, reject, threshold))
    return results, K, threshold


def apply_holm(hyps, alpha=ALPHA):
    """Holm step-down: more powerful than Bonferroni, still controls FWER.

    Sort p-values ascending. For rank i (0-indexed):
      reject if p_i < alpha / (K - i).
    Stop at first non-rejection.
    """
    K = len(hyps)
    indexed = [(name, p, source, finding, j)
               for j, (name, p, source, finding) in enumerate(hyps)]
    sorted_hyps = sorted(indexed, key=lambda x: x[1])

    reject = [False] * K
    for rank, (name, p, source, finding, orig_idx) in enumerate(sorted_hyps):
        threshold = alpha / (K - rank)
        if p < threshold:
            reject[orig_idx] = True
        else:
            break  # stop — all subsequent also fail

    results = []
    for j, (name, p, source, finding) in enumerate(hyps):
        results.append((name, p, reject[j]))
    return results


def apply_bh(hyps, alpha=ALPHA):
    """Benjamini-Hochberg: controls FDR (false discovery rate).

    Sort p-values ascending. For rank i (1-indexed):
      reject if p_i < alpha * i / K.
    Find largest k where p_k < alpha*k/K, reject all 1..k.
    """
    K = len(hyps)
    indexed = [(name, p, source, finding, j)
               for j, (name, p, source, finding) in enumerate(hyps)]
    sorted_hyps = sorted(indexed, key=lambda x: x[1])

    # Find the largest rank k where p_k < alpha*k/K
    max_k = -1
    for rank, (name, p, source, finding, orig_idx) in enumerate(sorted_hyps):
        i = rank + 1  # 1-indexed
        threshold = alpha * i / K
        if p < threshold:
            max_k = rank

    reject = [False] * K
    if max_k >= 0:
        for rank in range(max_k + 1):
            orig_idx = sorted_hyps[rank][4]
            reject[orig_idx] = True

    results = []
    for j, (name, p, source, finding) in enumerate(hyps):
        results.append((name, p, reject[j]))
    return results


# ═══════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 72)
    print("MULTIPLE COMPARISON CORRECTION")
    print("Formal Bonferroni / Holm / BH Analysis")
    print("=" * 72)
    print(f"  α = {ALPHA}")
    print(f"  Permutations: {N_PERM}")
    print(f"  Period: {START} → {END}")
    print(f"  Cost: harsh ({COST.round_trip_bps:.0f} bps RT)")

    print("\nLoading data...")
    cl, hi, lo, vo, tb, wi, n = load_arrays()
    print(f"  {n} H4 bars, warmup idx={wi}")

    # ── Step 1: Re-compute component p-values ──
    print("\n" + "=" * 72)
    print("STEP 1: COMPONENT PERMUTATION TESTS (10,000 permutations)")
    print("=" * 72)

    t_all = time.time()
    p_ema, _, _ = test_ema(cl, hi, lo, vo, tb, wi)
    p_vdo, _, _, skip_rate = test_vdo(cl, hi, lo, vo, tb, wi)
    p_atr, _, _ = test_atr(cl, hi, lo, vo, tb, wi)

    print(f"\n  Summary of component p-values:")
    print(f"    EMA: p = {p_ema:.6f}")
    print(f"    VDO: p = {p_vdo:.6f}")
    print(f"    ATR: p = {p_atr:.6f}")
    print(f"  (Total time: {time.time() - t_all:.0f}s)")

    # Compare with previous results
    print(f"\n  Previous results (for reference):")
    print(f"    EMA: p = 0.000 (true_wfo_compare.py, 1000 perms)")
    print(f"    VDO: p = 0.060 (true_wfo_compare.py, 1000 perms)")
    print(f"    VDO: p = 0.005 (component_analysis.py, 200 perms)")
    print(f"    ATR: unknown (component_analysis.py, 200 perms, not saved)")

    # ── Step 2: Enumerate all hypotheses ──
    print("\n" + "=" * 72)
    print("STEP 2: FULL HYPOTHESIS ENUMERATION")
    print("=" * 72)

    hyps = build_hypothesis_table(p_ema, p_vdo, p_atr)
    K = len(hyps)

    print(f"\n  Total hypotheses tested on this dataset: K = {K}")
    print(f"\n  {'#':>3}  {'Hypothesis':>30s}  {'p-value':>10s}  {'Source':>20s}  {'Type':>8s}")
    print("  " + "-" * 78)
    for j, (name, p, source, finding) in enumerate(hyps):
        print(f"  {j+1:3d}  {name:>30s}  {p:10.6f}  {source:>20s}  {finding:>8s}")

    # ── Step 3: Apply corrections ──
    print("\n" + "=" * 72)
    print("STEP 3: MULTIPLE COMPARISON CORRECTIONS")
    print("=" * 72)

    # Bonferroni
    bonf_results, K_bonf, bonf_thresh = apply_bonferroni(hyps)
    print(f"\n  A. BONFERRONI (most conservative, FWER control)")
    print(f"     Threshold: α/K = {ALPHA}/{K} = {bonf_thresh:.6f}")
    print(f"\n     {'Hypothesis':>30s}  {'p-value':>10s}  {'Threshold':>10s}  {'Reject H0':>10s}")
    print("     " + "-" * 65)
    for name, p, reject, thresh in bonf_results:
        if p < 1.0:  # only show interesting ones
            mark = "  ✓ REJECT" if reject else "  ✗ fail"
            print(f"     {name:>30s}  {p:10.6f}  {thresh:10.6f} {mark}")

    # Holm
    holm_results = apply_holm(hyps)
    print(f"\n  B. HOLM STEP-DOWN (less conservative, still FWER)")
    print(f"\n     {'Hypothesis':>30s}  {'p-value':>10s}  {'Reject H0':>10s}")
    print("     " + "-" * 55)
    for name, p, reject in holm_results:
        if p < 1.0:
            mark = "  ✓ REJECT" if reject else "  ✗ fail"
            print(f"     {name:>30s}  {p:10.6f} {mark}")

    # BH
    bh_results = apply_bh(hyps)
    print(f"\n  C. BENJAMINI-HOCHBERG (FDR control at q = {ALPHA})")
    print(f"\n     {'Hypothesis':>30s}  {'p-value':>10s}  {'Reject H0':>10s}")
    print("     " + "-" * 55)
    for name, p, reject in bh_results:
        if p < 1.0:
            mark = "  ✓ REJECT" if reject else "  ✗ fail"
            print(f"     {name:>30s}  {p:10.6f} {mark}")

    # ── Step 4: Final determination ──
    print("\n" + "=" * 72)
    print("STEP 4: FINAL DETERMINATION")
    print("=" * 72)

    print(f"\n  {'Component':>12s}  {'p-value':>10s}  {'Bonferroni':>12s}  "
          f"{'Holm':>12s}  {'BH (FDR)':>12s}")
    print("  " + "-" * 63)

    comp_names = ["EMA trend signal", "VDO filter", "ATR trail scaling"]
    for name in comp_names:
        p = next(p for n, p, _, _ in hyps if n == name)
        b_rej = next(r for n, _, r, _ in bonf_results if n == name)
        h_rej = next(r for n, _, r in holm_results if n == name)
        bh_rej = next(r for n, _, r in bh_results if n == name)
        b_str = "SURVIVES" if b_rej else "FAILS"
        h_str = "SURVIVES" if h_rej else "FAILS"
        bh_str = "SURVIVES" if bh_rej else "FAILS"
        short = name.split()[0]
        print(f"  {short:>12s}  {p:10.6f}  {b_str:>12s}  {h_str:>12s}  {bh_str:>12s}")

    # Interpretation
    ema_survives = any(r for n, _, r, _ in bonf_results if n == "EMA trend signal")
    vdo_survives_bonf = any(r for n, _, r, _ in bonf_results if n == "VDO filter")
    vdo_survives_bh = any(r for n, _, r in bh_results if n == "VDO filter")
    atr_survives = any(r for n, _, r, _ in bonf_results if n == "ATR trail scaling")

    print(f"\n  INTERPRETATION:")
    if ema_survives:
        print(f"    EMA: PROVEN genuine. Survives all corrections.")
    else:
        print(f"    EMA: Vulnerable — does not survive Bonferroni.")

    if atr_survives:
        print(f"    ATR: PROVEN genuine. Survives all corrections.")
    elif any(r for n, _, r in holm_results if n == "ATR trail scaling"):
        print(f"    ATR: Survives Holm and BH, fails Bonferroni.")
    else:
        print(f"    ATR: Vulnerable.")

    if vdo_survives_bonf:
        print(f"    VDO: Survives all corrections.")
    elif vdo_survives_bh:
        print(f"    VDO: Survives BH (FDR), fails FWER corrections.")
        print(f"         VDO should be treated as a HYPOTHESIS, not proven.")
    else:
        print(f"    VDO: FAILS all corrections. Not proven.")

    # Key insight
    n_surviving_bonf = sum(1 for _, _, r, _ in bonf_results if r)
    n_surviving_bh = sum(1 for _, _, r in bh_results if r)
    print(f"\n  Findings surviving Bonferroni: {n_surviving_bonf}/{K}")
    print(f"  Findings surviving BH (FDR):  {n_surviving_bh}/{K}")

    print(f"\n  NULL RESULTS (Hướng A, B) are ROBUST:")
    print(f"    These are mathematical consequences of Sharpe invariance.")
    print(f"    Adding them to K makes the correction STRICTER for positive")
    print(f"    findings, but they themselves are not at risk of being")
    print(f"    false positives (you can't p-hack a null result).")

    # ── Save ──
    outdir = Path(__file__).resolve().parent / "results"
    outdir.mkdir(exist_ok=True)

    output = {
        "n_perm": N_PERM,
        "alpha": ALPHA,
        "K_total_hypotheses": K,
        "component_pvalues": {
            "EMA": round(p_ema, 6),
            "VDO": round(p_vdo, 6),
            "ATR": round(p_atr, 6),
        },
        "bonferroni_threshold": round(bonf_thresh, 6),
        "corrections": {
            name: {
                "p_value": round(p, 6),
                "bonferroni": next(r for n, _, r, _ in bonf_results if n == name),
                "holm": next(r for n, _, r in holm_results if n == name),
                "bh": next(r for n, _, r in bh_results if n == name),
            }
            for name in comp_names
        },
    }

    outpath = outdir / "multiple_comparison.json"
    with open(outpath, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n  Results saved → {outpath}")
    print("\n" + "=" * 72)
    print("DONE")
    print("=" * 72)
