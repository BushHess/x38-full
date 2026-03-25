#!/usr/bin/env python3
"""Step 4: Matched-Risk Frontier + Deploy-Oriented Comparison.

External cash-scaling with linearity sanity check, 101-point k frontier,
matched-MDD region, operational risk-budget analysis, pairwise diagnostics,
secondary multi-strategy frontier, and equal-overlay control.

NO modification of any production file.
"""
from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

# ── Path setup ─────────────────────────────────────────────────────────────
_SCRIPT = Path(__file__).resolve()
_SRC = _SCRIPT.parent
_NAMESPACE = _SRC.parent
_REPO = _NAMESPACE.parent.parent

for p in [str(_SRC), str(_REPO)]:
    if p not in sys.path:
        sys.path.insert(0, p)

ARTIFACTS = _NAMESPACE / "artifacts"
ARTIFACTS.mkdir(parents=True, exist_ok=True)

EPS = 1e-12
BARS_PER_YEAR = 2190.0  # H4: 6 × 365.0
ANN_FACTOR = math.sqrt(BARS_PER_YEAR)

# ═══════════════════════════════════════════════════════════════════════════
# RETURN-STREAM RECONSTRUCTION
# ═══════════════════════════════════════════════════════════════════════════

def load_equity_curves() -> dict[str, np.ndarray]:
    """Load Step 3 equity curves from npz."""
    npz = np.load(str(ARTIFACTS / "factorial_equity_curves.npz"))
    return {k: npz[k] for k in npz.files}


def equity_to_returns(eq: np.ndarray) -> np.ndarray:
    """Per-bar simple returns: r[i] = eq[i]/eq[i-1] - 1. r[0] = 0."""
    r = np.zeros_like(eq)
    r[1:] = eq[1:] / np.maximum(eq[:-1], EPS) - 1.0
    return r


# ═══════════════════════════════════════════════════════════════════════════
# EXTERNAL CASH-SCALING
# ═══════════════════════════════════════════════════════════════════════════

def scale_returns(r: np.ndarray, k: float) -> np.ndarray:
    """r_scaled[i] = k * r[i], k ∈ [0, 1]. Cash portion earns 0%."""
    assert 0.0 <= k <= 1.0 + EPS, f"k={k} violates no-leverage constraint"
    return k * r


def returns_to_equity(r_scaled: np.ndarray) -> np.ndarray:
    """Reconstruct equity curve from scaled returns. E[0]=1."""
    eq = np.ones_like(r_scaled)
    for i in range(1, len(r_scaled)):
        eq[i] = eq[i - 1] * (1.0 + r_scaled[i])
    return eq


# ═══════════════════════════════════════════════════════════════════════════
# METRICS COMPUTATION (20+)
# ═══════════════════════════════════════════════════════════════════════════

def compute_metrics(eq: np.ndarray, r: np.ndarray,
                    k: float, native_exposure: float,
                    native_turnover: float,
                    native_fee_drag: float,
                    btc_eq: np.ndarray | None = None) -> dict:
    """Compute 20+ metrics for a single (strategy, k) point."""
    n = len(eq)
    core = r[1:]  # skip first zero-return bar
    years = max((n - 1) / BARS_PER_YEAR, EPS)

    # Terminal wealth
    terminal = float(eq[-1])
    total_return = terminal - 1.0

    # CAGR
    if terminal > 0.0:
        cagr = float(terminal ** (1.0 / years) - 1.0)
    else:
        cagr = -1.0

    # MDD
    running_max = np.maximum.accumulate(eq)
    dd_arr = 1.0 - eq / np.maximum(running_max, EPS)
    mdd = float(np.max(dd_arr))

    # Sharpe (ddof=0, population)
    mean_r = float(np.mean(core))
    std_r = float(np.std(core, ddof=0))
    sharpe = float(ANN_FACTOR * mean_r / max(std_r, EPS)) if std_r > EPS else 0.0

    # Sortino
    down = core[core < 0]
    if len(down) > 0:
        ds = float(np.std(down, ddof=0))
        sortino = float(ANN_FACTOR * mean_r / max(ds, EPS)) if ds > EPS else 0.0
    else:
        sortino = 0.0

    # Calmar
    calmar = float(cagr / max(mdd, EPS)) if mdd > EPS else 0.0

    # Ulcer Index: RMS of drawdowns
    ulcer = float(np.sqrt(np.mean(dd_arr ** 2)))

    # Realized vol (annualized)
    real_vol = float(std_r * ANN_FACTOR)

    # Avg exposure (scaled by k from native)
    avg_exposure = k * native_exposure

    # Time in market (unchanged by k)
    time_in_market = native_exposure  # position fraction same, notional scaled

    # Turnover (scales with k)
    turnover = k * native_turnover

    # Fee drag (scales with k)
    fee_drag = k * native_fee_drag

    # Longest drawdown duration
    in_dd = dd_arr > 0.001
    longest_dd_bars = 0
    current_dd_bars = 0
    for d in in_dd:
        if d:
            current_dd_bars += 1
            longest_dd_bars = max(longest_dd_bars, current_dd_bars)
        else:
            current_dd_bars = 0
    longest_dd_days = longest_dd_bars / 6.0  # H4 bars → days

    # Recovery time: from peak at max DD to next new equity high
    max_dd_idx = int(np.argmax(dd_arr))
    # Find start of this drawdown (peak)
    peak_idx = max_dd_idx
    while peak_idx > 0 and dd_arr[peak_idx - 1] > 0.001:
        peak_idx -= 1
    # Find recovery (next new high after max DD point)
    recovery_bars = 0
    for j in range(max_dd_idx, n):
        if eq[j] >= running_max[max_dd_idx]:
            recovery_bars = j - max_dd_idx
            break
    else:
        recovery_bars = n - max_dd_idx  # never recovered
    recovery_days = recovery_bars / 6.0

    # Budget utilization
    budget_util = float(k)

    # Beta, alpha, correlation vs BTC buy-and-hold
    beta = np.nan
    alpha = np.nan
    corr = np.nan
    if btc_eq is not None and len(btc_eq) == n:
        btc_r = np.zeros(n)
        btc_r[1:] = btc_eq[1:] / np.maximum(btc_eq[:-1], EPS) - 1.0
        btc_core = btc_r[1:]
        if np.std(btc_core, ddof=0) > EPS:
            cov_mat = np.cov(core, btc_core, ddof=0)
            var_btc = cov_mat[1, 1]
            if var_btc > EPS:
                beta = float(cov_mat[0, 1] / var_btc)
                # Annualized alpha
                alpha = float((mean_r - beta * np.mean(btc_core)) * BARS_PER_YEAR)
                corr_mat = np.corrcoef(core, btc_core)
                corr = float(corr_mat[0, 1])

    return {
        "k": k,
        "terminal_wealth": terminal,
        "total_return": total_return,
        "cagr": cagr,
        "mdd": mdd,
        "sharpe": sharpe,
        "sortino": sortino,
        "calmar": calmar,
        "ulcer_index": ulcer,
        "realized_vol": real_vol,
        "avg_exposure": avg_exposure,
        "time_in_market": time_in_market,
        "turnover": turnover,
        "fee_drag": fee_drag,
        "longest_dd_days": longest_dd_days,
        "recovery_days": recovery_days,
        "budget_utilization": budget_util,
        "beta_vs_btc": beta,
        "alpha_vs_btc": alpha,
        "corr_vs_btc": corr,
    }


# ═══════════════════════════════════════════════════════════════════════════
# LINEARITY SANITY CHECK
# ═══════════════════════════════════════════════════════════════════════════

def linearity_check(r: np.ndarray, native_exposure: float,
                    native_turnover: float, native_fee_drag: float,
                    btc_eq: np.ndarray | None = None) -> dict:
    """Verify that external scaling behaves as expected at k=0.25, 0.50, 0.75.

    For Sharpe, we expect: Sharpe(k) ≈ Sharpe(1) for all k > 0.
    This is because scaling returns by k scales both mean and std by k → ratio constant.
    (Small deviations from compounding effects.)

    For MDD: MDD(k) should be monotonically increasing with k.
    For CAGR: CAGR(k) should be monotonically increasing with k.
    """
    results = {}
    test_ks = [0.25, 0.50, 0.75, 1.00]

    for k in test_ks:
        rs = scale_returns(r, k)
        eq_k = returns_to_equity(rs)
        m = compute_metrics(eq_k, rs, k, native_exposure, native_turnover,
                           native_fee_drag, btc_eq)
        results[k] = m

    # Sharpe should be approximately constant (compound effect creates small drift)
    sharpes = [results[k]["sharpe"] for k in test_ks]
    sharpe_range = max(sharpes) - min(sharpes)
    sharpe_pct_range = sharpe_range / max(abs(sharpes[0]), EPS) * 100

    # MDD monotonicity
    mdds = [results[k]["mdd"] for k in test_ks]
    mdd_monotonic = all(mdds[i] <= mdds[i+1] + EPS for i in range(len(mdds)-1))

    # CAGR monotonicity
    cagrs = [results[k]["cagr"] for k in test_ks]
    cagr_monotonic = all(cagrs[i] <= cagrs[i+1] + EPS for i in range(len(cagrs)-1))

    return {
        "test_ks": test_ks,
        "sharpes": sharpes,
        "sharpe_pct_range": sharpe_pct_range,
        "sharpe_quasi_constant": sharpe_pct_range < 15.0,  # allow 15% range from compounding
        "mdds": mdds,
        "mdd_monotonic": mdd_monotonic,
        "cagrs": cagrs,
        "cagr_monotonic": cagr_monotonic,
        "pass": mdd_monotonic and cagr_monotonic,
    }


# ═══════════════════════════════════════════════════════════════════════════
# FRONTIER GRID (101 POINTS)
# ═══════════════════════════════════════════════════════════════════════════

def build_frontier(name: str, r: np.ndarray, native_exposure: float,
                   native_turnover: float, native_fee_drag: float,
                   btc_eq: np.ndarray | None = None,
                   n_points: int = 101) -> list[dict]:
    """Build 101-point k frontier for a single strategy."""
    ks = np.linspace(0.0, 1.0, n_points)
    rows = []
    for k in ks:
        rs = scale_returns(r, k)
        eq_k = returns_to_equity(rs)
        m = compute_metrics(eq_k, rs, k, native_exposure, native_turnover,
                           native_fee_drag, btc_eq)
        m["strategy"] = name
        rows.append(m)
    return rows


# ═══════════════════════════════════════════════════════════════════════════
# MATCHED-MDD ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════

def find_k_for_target_mdd(r: np.ndarray, target_mdd: float,
                          tol: float = 0.001) -> float:
    """Binary search for k that produces target MDD."""
    lo, hi = 0.0, 1.0
    for _ in range(100):
        mid = (lo + hi) / 2.0
        rs = scale_returns(r, mid)
        eq = returns_to_equity(rs)
        rm = np.maximum.accumulate(eq)
        dd = 1.0 - eq / np.maximum(rm, EPS)
        mdd = float(np.max(dd))
        if mdd < target_mdd - tol:
            lo = mid
        elif mdd > target_mdd + tol:
            hi = mid
        else:
            return mid
    return (lo + hi) / 2.0


def find_k_for_target_exposure(native_exposure: float,
                               target_exposure: float) -> float:
    """k such that k * native_exposure = target_exposure."""
    if native_exposure < EPS:
        return 0.0
    k = target_exposure / native_exposure
    return min(max(k, 0.0), 1.0)


def matched_mdd_analysis(strategies: dict[str, dict]) -> dict:
    """Find common feasible MDD region and compute matched comparisons."""
    # Find min native MDD across strategies
    native_mdds = {name: s["native_mdd"] for name, s in strategies.items()}
    min_mdd = min(native_mdds.values())
    max_mdd = max(native_mdds.values())

    # Common feasible region: 0 ≤ target_mdd ≤ min(native_mdd_all)
    # In this region, ALL strategies can be scaled DOWN to match
    budget_targets = [0.05, 0.10, 0.125, 0.15, 0.20, 0.25, 0.30]
    feasible_targets = [t for t in budget_targets if t <= min_mdd + 0.001]

    results = {"native_mdds": native_mdds, "min_native_mdd": min_mdd,
               "max_native_mdd": max_mdd, "feasible_targets": feasible_targets}

    matched = []
    for target in feasible_targets:
        row = {"target_mdd": target}
        for name, s in strategies.items():
            k = find_k_for_target_mdd(s["returns"], target)
            rs = scale_returns(s["returns"], k)
            eq = returns_to_equity(rs)
            m = compute_metrics(eq, rs, k, s["native_exposure"],
                              s["native_turnover"], s["native_fee_drag"],
                              s.get("btc_eq"))
            m["strategy"] = name
            row[f"{name}_k"] = k
            row[f"{name}_cagr"] = m["cagr"]
            row[f"{name}_sharpe"] = m["sharpe"]
            row[f"{name}_sortino"] = m["sortino"]
            row[f"{name}_calmar"] = m["calmar"]
            row[f"{name}_mdd"] = m["mdd"]
            row[f"{name}_exposure"] = m["avg_exposure"]
        matched.append(row)

    results["matched_table"] = matched
    return results


# ═══════════════════════════════════════════════════════════════════════════
# OPERATIONAL RISK-BUDGET REGION
# ═══════════════════════════════════════════════════════════════════════════

def operational_risk_budget(strategies: dict[str, dict]) -> list[dict]:
    """Compute metrics at standard risk-budget MDD targets."""
    targets = [0.125, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.50, 0.60]
    rows = []
    for target in targets:
        row = {"target_mdd": target}
        for name, s in strategies.items():
            native_mdd = s["native_mdd"]
            if target <= native_mdd + 0.001:
                k = find_k_for_target_mdd(s["returns"], target)
            else:
                # Cannot reach target without leverage; mark as infeasible
                k = 1.0  # max allocation
            rs = scale_returns(s["returns"], k)
            eq = returns_to_equity(rs)
            m = compute_metrics(eq, rs, k, s["native_exposure"],
                              s["native_turnover"], s["native_fee_drag"],
                              s.get("btc_eq"))
            row[f"{name}_k"] = k
            row[f"{name}_cagr"] = m["cagr"]
            row[f"{name}_sharpe"] = m["sharpe"]
            row[f"{name}_mdd"] = m["mdd"]
            row[f"{name}_calmar"] = m["calmar"]
            row[f"{name}_exposure"] = m["avg_exposure"]
            feasible = target <= native_mdd + 0.001
            row[f"{name}_feasible"] = feasible
        rows.append(row)
    return rows


# ═══════════════════════════════════════════════════════════════════════════
# PAIRWISE DIAGNOSTICS
# ═══════════════════════════════════════════════════════════════════════════

def pairwise_diagnostics(strats: dict[str, dict]) -> dict:
    """E0 scaled to match LATCH MDD, E0 scaled to match LATCH exposure, etc."""
    results = {}

    if "E0_Native" not in strats or "LATCH_Native" not in strats:
        return results

    e0 = strats["E0_Native"]
    la = strats["LATCH_Native"]

    # A. E0 scaled to match LATCH native MDD
    k_mdd = find_k_for_target_mdd(e0["returns"], la["native_mdd"])
    rs = scale_returns(e0["returns"], k_mdd)
    eq = returns_to_equity(rs)
    m_mdd = compute_metrics(eq, rs, k_mdd, e0["native_exposure"],
                            e0["native_turnover"], e0["native_fee_drag"],
                            e0.get("btc_eq"))
    m_mdd["match_type"] = "E0_at_LATCH_MDD"
    m_mdd["match_target"] = la["native_mdd"]
    results["E0_at_LATCH_MDD"] = m_mdd

    # B. E0 scaled to match LATCH native exposure
    k_expo = find_k_for_target_exposure(e0["native_exposure"],
                                        la["native_exposure"])
    rs = scale_returns(e0["returns"], k_expo)
    eq = returns_to_equity(rs)
    m_expo = compute_metrics(eq, rs, k_expo, e0["native_exposure"],
                             e0["native_turnover"], e0["native_fee_drag"],
                             e0.get("btc_eq"))
    m_expo["match_type"] = "E0_at_LATCH_exposure"
    m_expo["match_target"] = la["native_exposure"]
    results["E0_at_LATCH_exposure"] = m_expo

    # C. LATCH native reference
    eq_la = returns_to_equity(la["returns"])
    m_la = compute_metrics(eq_la, la["returns"], 1.0, la["native_exposure"],
                           la["native_turnover"], la["native_fee_drag"],
                           la.get("btc_eq"))
    m_la["match_type"] = "LATCH_Native"
    results["LATCH_Native_ref"] = m_la

    # D. Reverse: can LATCH reach E0 native MDD? Only if no leverage
    latch_native_mdd = la["native_mdd"]
    e0_native_mdd = e0["native_mdd"]
    results["reverse_feasible"] = latch_native_mdd < e0_native_mdd
    if latch_native_mdd < e0_native_mdd:
        # LATCH at k=1 has MDD << E0, cannot scale UP without leverage
        results["reverse_note"] = (
            f"LATCH native MDD={latch_native_mdd:.4f} < E0 native MDD={e0_native_mdd:.4f}. "
            f"LATCH cannot reach E0-level MDD without leverage >1."
        )

    return results


# ═══════════════════════════════════════════════════════════════════════════
# EQUAL-OVERLAY CONTROL
# ═══════════════════════════════════════════════════════════════════════════

def equal_overlay_control(curves: dict[str, np.ndarray],
                          step3: dict) -> dict | None:
    """Compare E0_EntryVol_12 vs LATCH_EntryVol_12 from Step 3.

    These already use identical sizing (EntryVol, tv=0.12, no rebal).
    This is the purest same-overlay comparison.
    """
    e0_key = "E0_EntryVol_12"
    la_key = "LATCH_EntryVol_12"
    if e0_key not in curves or la_key not in curves:
        return None

    e0_m = step3[e0_key]
    la_m = step3[la_key]

    return {
        "e0": {
            "cagr": e0_m["cagr"], "mdd": e0_m["mdd"], "sharpe": e0_m["sharpe"],
            "sortino": e0_m["sortino"], "calmar": e0_m["calmar"],
            "exposure": e0_m["exposure"], "score": e0_m["score"],
        },
        "latch": {
            "cagr": la_m["cagr"], "mdd": la_m["mdd"], "sharpe": la_m["sharpe"],
            "sortino": la_m["sortino"], "calmar": la_m["calmar"],
            "exposure": la_m["exposure"], "score": la_m["score"],
        },
        "delta_sharpe": la_m["sharpe"] - e0_m["sharpe"],
        "delta_cagr": la_m["cagr"] - e0_m["cagr"],
        "delta_mdd": la_m["mdd"] - e0_m["mdd"],
        "delta_score": la_m["score"] - e0_m["score"],
    }


# ═══════════════════════════════════════════════════════════════════════════
# RESOLUTION MATRIX D1-D6
# ═══════════════════════════════════════════════════════════════════════════

def resolution_matrix(matched: dict, pairwise: dict,
                      risk_budget: list[dict],
                      equal_ctrl: dict | None,
                      frontiers: dict[str, list[dict]]) -> list[dict]:
    """Build resolution matrix D1-D6."""
    resolutions = []

    # D1: At matched MDD (LATCH-level), which strategy has higher CAGR?
    d1_detail = ""
    if matched.get("matched_table"):
        # Use the target closest to LATCH native MDD
        tbl = matched["matched_table"]
        if tbl:
            row = tbl[-1]  # highest feasible target ≈ LATCH native MDD
            e0_cagr = row.get("E0_Native_cagr", np.nan)
            la_cagr = row.get("LATCH_Native_cagr", np.nan)
            target = row["target_mdd"]
            if e0_cagr > la_cagr:
                d1_v = f"E0 wins at MDD≈{target:.1%}: CAGR {e0_cagr:.2%} vs {la_cagr:.2%}"
            elif la_cagr > e0_cagr:
                d1_v = f"LATCH wins at MDD≈{target:.1%}: CAGR {la_cagr:.2%} vs {e0_cagr:.2%}"
            else:
                d1_v = "Tied"
            d1_detail = f"target_mdd={target:.1%}"
    else:
        d1_v = "No feasible matched MDD targets"
    resolutions.append(("D1", "At matched MDD, which strategy has higher CAGR?",
                        d1_v, d1_detail))

    # D2: At matched MDD, which has higher Sharpe?
    if matched.get("matched_table"):
        tbl = matched["matched_table"]
        if tbl:
            row = tbl[-1]
            e0_sh = row.get("E0_Native_sharpe", np.nan)
            la_sh = row.get("LATCH_Native_sharpe", np.nan)
            target = row["target_mdd"]
            if e0_sh > la_sh:
                d2_v = f"E0 wins at MDD≈{target:.1%}: Sharpe {e0_sh:.4f} vs {la_sh:.4f}"
            elif la_sh > e0_sh:
                d2_v = f"LATCH wins at MDD≈{target:.1%}: Sharpe {la_sh:.4f} vs {e0_sh:.4f}"
            else:
                d2_v = "Tied"
    else:
        d2_v = "No data"
    resolutions.append(("D2", "At matched MDD, which has higher Sharpe?",
                        d2_v, ""))

    # D3: E0 scaled to LATCH MDD — head-to-head
    if "E0_at_LATCH_MDD" in pairwise and "LATCH_Native_ref" in pairwise:
        e0_m = pairwise["E0_at_LATCH_MDD"]
        la_m = pairwise["LATCH_Native_ref"]
        d3_v = (f"E0(k={e0_m['k']:.3f}): CAGR={e0_m['cagr']:.2%}, Sharpe={e0_m['sharpe']:.4f} | "
                f"LATCH: CAGR={la_m['cagr']:.2%}, Sharpe={la_m['sharpe']:.4f}")
    else:
        d3_v = "Pairwise data unavailable"
    resolutions.append(("D3", "E0 scaled to LATCH MDD: head-to-head",
                        d3_v, ""))

    # D4: Can LATCH reach E0-level MDD without leverage?
    if "reverse_feasible" in pairwise:
        d4_v = pairwise.get("reverse_note", "Yes, LATCH can match E0 MDD")
    else:
        d4_v = "No data"
    resolutions.append(("D4", "Can LATCH reach E0-level MDD without leverage?",
                        d4_v, ""))

    # D5: Equal-overlay control (EntryVol_12)
    if equal_ctrl:
        d5_v = (f"E0 Sharpe={equal_ctrl['e0']['sharpe']:.4f}, "
                f"LATCH Sharpe={equal_ctrl['latch']['sharpe']:.4f}, "
                f"ΔSharpe={equal_ctrl['delta_sharpe']:+.4f}, "
                f"ΔScore={equal_ctrl['delta_score']:+.2f}")
    else:
        d5_v = "No data"
    resolutions.append(("D5", "Equal-overlay control (EntryVol_12)",
                        d5_v, "Same signal extraction, same sizing, same cost"))

    # D6: Overall deploy-oriented verdict
    d6_v = "See report narrative"
    resolutions.append(("D6", "Overall deploy-oriented comparison",
                        d6_v, "Matched-risk analysis resolves exposure bias"))

    return [{"id": r[0], "question": r[1], "verdict": r[2], "detail": r[3]}
            for r in resolutions]


# ═══════════════════════════════════════════════════════════════════════════
# ARTIFACT SAVING
# ═══════════════════════════════════════════════════════════════════════════

def save_artifacts(frontiers: dict[str, list[dict]],
                   linearity: dict[str, dict],
                   matched: dict,
                   risk_budget: list[dict],
                   pairwise: dict,
                   equal_ctrl: dict | None,
                   resolutions: list[dict],
                   elapsed: float):
    """Save all Step 4 artifacts."""

    # 1. Frontier grids (one CSV per strategy)
    all_frontier_rows = []
    for name, rows in frontiers.items():
        for r in rows:
            r2 = {k: v for k, v in r.items() if not isinstance(v, np.ndarray)}
            all_frontier_rows.append(r2)
    pd.DataFrame(all_frontier_rows).to_csv(
        ARTIFACTS / "frontier_grid.csv", index=False)
    print(f"  frontier_grid.csv ({len(all_frontier_rows)} rows)")

    # 2. Linearity check
    with open(ARTIFACTS / "linearity_check.json", "w") as f:
        json.dump({k: _convert_dict(v) for k, v in linearity.items()}, f, indent=2)
    print("  linearity_check.json")

    # 3. Matched-MDD table
    if matched.get("matched_table"):
        pd.DataFrame(matched["matched_table"]).to_csv(
            ARTIFACTS / "matched_mdd.csv", index=False)
        print("  matched_mdd.csv")

    # 4. Matched summary
    matched_summary = {k: v for k, v in matched.items() if k != "matched_table"}
    with open(ARTIFACTS / "matched_mdd_summary.json", "w") as f:
        json.dump(_convert_dict(matched_summary), f, indent=2)
    print("  matched_mdd_summary.json")

    # 5. Operational risk budget
    pd.DataFrame(risk_budget).to_csv(
        ARTIFACTS / "risk_budget.csv", index=False)
    print("  risk_budget.csv")

    # 6. Pairwise diagnostics
    pw_clean = {}
    for k, v in pairwise.items():
        if isinstance(v, dict):
            pw_clean[k] = {kk: vv for kk, vv in v.items()
                          if not isinstance(vv, np.ndarray)}
        else:
            pw_clean[k] = v
    with open(ARTIFACTS / "pairwise_diagnostics.json", "w") as f:
        json.dump(_convert_dict(pw_clean), f, indent=2)
    print("  pairwise_diagnostics.json")

    # 7. Equal-overlay control
    if equal_ctrl:
        with open(ARTIFACTS / "equal_overlay_control.json", "w") as f:
            json.dump(_convert_dict(equal_ctrl), f, indent=2)
        print("  equal_overlay_control.json")

    # 8. Resolution matrix D1-D6
    pd.DataFrame(resolutions).to_csv(
        ARTIFACTS / "resolution_matrix_d.csv", index=False)
    print("  resolution_matrix_d.csv")

    # 9. Step 4 master results
    master = {
        "linearity": {k: _convert_dict(v) for k, v in linearity.items()},
        "matched_mdd_summary": _convert_dict(matched_summary),
        "pairwise": _convert_dict(pw_clean),
        "equal_overlay": _convert_dict(equal_ctrl) if equal_ctrl else None,
        "resolutions": resolutions,
        "_meta": {
            "elapsed_s": round(elapsed, 1),
            "n_frontier_points": 101,
            "date": "2026-03-05",
        },
    }
    with open(ARTIFACTS / "step4_master_results.json", "w") as f:
        json.dump(master, f, indent=2, default=_json_default)
    print("  step4_master_results.json")


def _convert_dict(d):
    if d is None:
        return None
    if not isinstance(d, dict):
        return _safe_val(d)
    return {k: _safe_val(v) if not isinstance(v, dict) else _convert_dict(v)
            for k, v in d.items()}


def _safe_val(v):
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        return float(v)
    if isinstance(v, np.bool_):
        return bool(v)
    if isinstance(v, np.ndarray):
        return v.tolist()
    if isinstance(v, float) and math.isnan(v):
        return None
    if isinstance(v, list):
        return [_safe_val(x) for x in v]
    return v


def _json_default(obj):
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, float) and math.isnan(obj):
        return None
    raise TypeError(f"Not serializable: {type(obj)}")


# ═══════════════════════════════════════════════════════════════════════════
# BTC BUY-AND-HOLD
# ═══════════════════════════════════════════════════════════════════════════

def load_btc_equity() -> np.ndarray:
    """Load BTC close prices and normalize to equity curve starting at 1.0."""
    from data_align import load_h4_dataframe
    df = load_h4_dataframe()
    close = df["close"].to_numpy(dtype=np.float64)
    return close / close[0]


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main():
    print("Step 4: Matched-Risk Frontier + Deploy-Oriented Comparison")
    print("=" * 70)
    t0 = time.time()

    # ── 1. Load Step 3 equity curves and master results ───────────────────
    curves = load_equity_curves()
    with open(ARTIFACTS / "step3_master_results.json") as f:
        step3 = json.load(f)

    btc_eq = load_btc_equity()
    n = len(btc_eq)
    print(f"Loaded {len(curves)} equity curves, {n} bars")

    # ── 2. Extract per-bar returns and native metadata ────────────────────
    # Primary strategies for frontier: E0_Native, SM_Native, P_Native, LATCH_Native
    primary_names = ["E0_Native", "SM_Native", "P_Native", "LATCH_Native"]
    strategies = {}
    for name in primary_names:
        eq = curves[name]
        r = equity_to_returns(eq)
        s3 = step3[name]
        strategies[name] = {
            "returns": r,
            "equity": eq,
            "native_exposure": s3["exposure"],
            "native_turnover": s3["turnover"],
            "native_fee_drag": s3["total_cost"] / max(s3["ending_equity"], EPS),
            "native_mdd": s3["mdd"],
            "btc_eq": btc_eq,
        }
    print(f"Prepared {len(strategies)} strategy return streams")

    # ── 3. Linearity sanity check ─────────────────────────────────────────
    print("\n" + "=" * 70)
    print("LINEARITY SANITY CHECK")
    print("=" * 70)
    linearity = {}
    for name, s in strategies.items():
        lc = linearity_check(s["returns"], s["native_exposure"],
                            s["native_turnover"], s["native_fee_drag"], btc_eq)
        linearity[name] = lc
        status = "PASS" if lc["pass"] else "FAIL"
        print(f"  {name:<15} {status}  Sharpe range={lc['sharpe_pct_range']:.1f}%  "
              f"MDD mono={lc['mdd_monotonic']}  CAGR mono={lc['cagr_monotonic']}")
        print(f"    k=0.25: Sharpe={lc['sharpes'][0]:.4f} MDD={lc['mdds'][0]:.4f} CAGR={lc['cagrs'][0]:.4f}")
        print(f"    k=0.50: Sharpe={lc['sharpes'][1]:.4f} MDD={lc['mdds'][1]:.4f} CAGR={lc['cagrs'][1]:.4f}")
        print(f"    k=0.75: Sharpe={lc['sharpes'][2]:.4f} MDD={lc['mdds'][2]:.4f} CAGR={lc['cagrs'][2]:.4f}")
        print(f"    k=1.00: Sharpe={lc['sharpes'][3]:.4f} MDD={lc['mdds'][3]:.4f} CAGR={lc['cagrs'][3]:.4f}")

    all_pass = all(lc["pass"] for lc in linearity.values())
    if not all_pass:
        print("\n  WARNING: Linearity check failed for one or more strategies.")
        print("  Proceeding but results should be interpreted with caution.")

    # ── 4. Build 101-point frontiers ──────────────────────────────────────
    print("\n" + "=" * 70)
    print("BUILDING 101-POINT FRONTIERS")
    print("=" * 70)
    frontiers = {}
    for name, s in strategies.items():
        rows = build_frontier(name, s["returns"], s["native_exposure"],
                             s["native_turnover"], s["native_fee_drag"], btc_eq)
        frontiers[name] = rows
        # Print some key points
        for k_idx in [0, 25, 50, 75, 100]:
            r = rows[k_idx]
            print(f"  {name:<15} k={r['k']:.2f}  CAGR={r['cagr']:.4f}  "
                  f"MDD={r['mdd']:.4f}  Sharpe={r['sharpe']:.4f}")

    # ── 5. Matched-MDD analysis ───────────────────────────────────────────
    print("\n" + "=" * 70)
    print("MATCHED-MDD ANALYSIS")
    print("=" * 70)
    matched = matched_mdd_analysis(strategies)
    print(f"  Native MDDs:")
    for name, mdd in matched["native_mdds"].items():
        print(f"    {name:<15} MDD={mdd:.4f} ({mdd*100:.2f}%)")
    print(f"  Min native MDD: {matched['min_native_mdd']:.4f}")
    print(f"  Feasible targets: {[f'{t:.1%}' for t in matched['feasible_targets']]}")

    if matched.get("matched_table"):
        print(f"\n  Matched-MDD comparison table:")
        hdr = f"  {'Target':>8}"
        for name in primary_names:
            hdr += f"  {name.split('_')[0]:>8}k  {name.split('_')[0]:>8}CAGR  {name.split('_')[0]:>8}Shrp"
        print(hdr)
        for row in matched["matched_table"]:
            line = f"  {row['target_mdd']:>8.1%}"
            for name in primary_names:
                k = row.get(f"{name}_k", np.nan)
                c = row.get(f"{name}_cagr", np.nan)
                sh = row.get(f"{name}_sharpe", np.nan)
                line += f"  {k:>8.3f}  {c:>8.4f}  {sh:>8.4f}"
            print(line)

    # ── 6. Operational risk-budget region ──────────────────────────────────
    print("\n" + "=" * 70)
    print("OPERATIONAL RISK-BUDGET REGION")
    print("=" * 70)
    risk_budget = operational_risk_budget(strategies)
    print(f"  {'Target':>8}", end="")
    for name in primary_names:
        short = name.split("_")[0]
        print(f"  {short:>5}k  {short:>5}CAGR  {short:>5}MDD  {'ok':>3}", end="")
    print()
    for row in risk_budget:
        line = f"  {row['target_mdd']:>8.1%}"
        for name in primary_names:
            k = row.get(f"{name}_k", np.nan)
            c = row.get(f"{name}_cagr", np.nan)
            mdd = row.get(f"{name}_mdd", np.nan)
            ok = row.get(f"{name}_feasible", False)
            line += f"  {k:>5.3f}  {c:>5.4f}  {mdd:>5.4f}  {'Y' if ok else 'N':>3}"
        print(line)

    # ── 7. Pairwise diagnostics ───────────────────────────────────────────
    print("\n" + "=" * 70)
    print("PAIRWISE DIAGNOSTICS")
    print("=" * 70)
    pairwise = pairwise_diagnostics(strategies)

    if "E0_at_LATCH_MDD" in pairwise:
        m = pairwise["E0_at_LATCH_MDD"]
        print(f"\n  A. E0 scaled to LATCH native MDD ({m['match_target']:.4f}):")
        print(f"     k={m['k']:.4f}  CAGR={m['cagr']:.4f} ({m['cagr']*100:.2f}%)  "
              f"MDD={m['mdd']:.4f}  Sharpe={m['sharpe']:.4f}")

    if "E0_at_LATCH_exposure" in pairwise:
        m = pairwise["E0_at_LATCH_exposure"]
        print(f"\n  B. E0 scaled to LATCH native exposure ({m['match_target']:.4f}):")
        print(f"     k={m['k']:.4f}  CAGR={m['cagr']:.4f} ({m['cagr']*100:.2f}%)  "
              f"MDD={m['mdd']:.4f}  Sharpe={m['sharpe']:.4f}")

    if "LATCH_Native_ref" in pairwise:
        m = pairwise["LATCH_Native_ref"]
        print(f"\n  C. LATCH native reference:")
        print(f"     k=1.000  CAGR={m['cagr']:.4f} ({m['cagr']*100:.2f}%)  "
              f"MDD={m['mdd']:.4f}  Sharpe={m['sharpe']:.4f}")

    if "reverse_note" in pairwise:
        print(f"\n  D. Reverse match: {pairwise['reverse_note']}")

    # ── 8. Equal-overlay control ──────────────────────────────────────────
    print("\n" + "=" * 70)
    print("EQUAL-OVERLAY CONTROL (EntryVol_12)")
    print("=" * 70)
    equal_ctrl = equal_overlay_control(curves, step3)
    if equal_ctrl:
        print(f"  E0_EntryVol_12:    Sharpe={equal_ctrl['e0']['sharpe']:.4f}  "
              f"CAGR={equal_ctrl['e0']['cagr']:.4f}  MDD={equal_ctrl['e0']['mdd']:.4f}  "
              f"Score={equal_ctrl['e0']['score']:.2f}")
        print(f"  LATCH_EntryVol_12: Sharpe={equal_ctrl['latch']['sharpe']:.4f}  "
              f"CAGR={equal_ctrl['latch']['cagr']:.4f}  MDD={equal_ctrl['latch']['mdd']:.4f}  "
              f"Score={equal_ctrl['latch']['score']:.2f}")
        print(f"  ΔSharpe={equal_ctrl['delta_sharpe']:+.4f}  "
              f"ΔCAGR={equal_ctrl['delta_cagr']:+.4f}  "
              f"ΔMDD={equal_ctrl['delta_mdd']:+.4f}  "
              f"ΔScore={equal_ctrl['delta_score']:+.2f}")

    # ── 9. Resolution matrix D1-D6 ───────────────────────────────────────
    print("\n" + "=" * 70)
    print("RESOLUTION MATRIX D1-D6")
    print("=" * 70)
    resolutions = resolution_matrix(matched, pairwise, risk_budget,
                                    equal_ctrl, frontiers)
    for r in resolutions:
        print(f"\n  {r['id']}: {r['question']}")
        print(f"       → {r['verdict']}")
        if r["detail"]:
            print(f"         ({r['detail']})")

    # ── 10. Save artifacts ────────────────────────────────────────────────
    elapsed = time.time() - t0
    print("\n" + "=" * 70)
    print("SAVING ARTIFACTS")
    print("=" * 70)
    save_artifacts(frontiers, linearity, matched, risk_budget, pairwise,
                   equal_ctrl, resolutions, elapsed)

    print(f"\n{'=' * 70}")
    print(f"COMPLETE in {elapsed:.1f}s. Artifacts saved to {ARTIFACTS}/")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
