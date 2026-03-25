#!/usr/bin/env python3
"""6-Strategy Matched-Risk Frontier.

Extends run_frontier.py Step 4 from 4 to 6 strategies.
Reuses all generic functions from run_frontier.py.

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

_SCRIPT = Path(__file__).resolve()
_SRC = _SCRIPT.parent
_NAMESPACE = _SRC.parent
_REPO = _NAMESPACE.parent.parent

for p in [str(_SRC), str(_REPO)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from run_frontier import (
    equity_to_returns, scale_returns, returns_to_equity,
    compute_metrics, linearity_check, build_frontier,
    matched_mdd_analysis, operational_risk_budget,
    find_k_for_target_mdd, _convert_dict, _safe_val, _json_default,
)

ARTIFACTS = _NAMESPACE / "artifacts"
ARTIFACTS.mkdir(parents=True, exist_ok=True)

EPS = 1e-12
STRATEGY_NAMES = ["E0", "E5", "SM", "LATCH", "EMA21_H4", "E0_plus_EMA1D21"]


def load_btc_equity() -> np.ndarray:
    from data_align import load_h4_dataframe
    df = load_h4_dataframe()
    close = df["close"].to_numpy(dtype=np.float64)
    return close / close[0]


def main():
    print("6-Strategy Matched-Risk Frontier")
    print("=" * 70)
    t0 = time.time()

    # ── 1. Load equity curves from factorial_6s ──────────────────────────
    npz = np.load(str(ARTIFACTS / "factorial_6s_equity_curves.npz"))
    curves = {k: npz[k] for k in npz.files}

    with open(ARTIFACTS / "step3_6s_master_results.json") as f:
        step3 = json.load(f)

    btc_eq = load_btc_equity()
    n = len(btc_eq)
    print(f"Loaded {len(curves)} equity curves, {n} bars")

    # ── 2. Prepare return streams ────────────────────────────────────────
    primary_names = [f"{s}_Native" for s in STRATEGY_NAMES]
    strategies = {}
    for name in primary_names:
        if name not in curves:
            print(f"  WARNING: {name} not found in equity curves, skipping")
            continue
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

    # ── 3. Linearity check ───────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("LINEARITY SANITY CHECK")
    print("=" * 70)
    linearity = {}
    for name, s in strategies.items():
        lc = linearity_check(s["returns"], s["native_exposure"],
                            s["native_turnover"], s["native_fee_drag"], btc_eq)
        linearity[name] = lc
        status = "PASS" if lc["pass"] else "FAIL"
        short = name.replace("_Native", "")
        print(f"  {short:<12} {status}  Sharpe_rng={lc['sharpe_pct_range']:.1f}%  "
              f"MDD_mono={lc['mdd_monotonic']}  CAGR_mono={lc['cagr_monotonic']}")

    # ── 4. Build 101-point frontiers ─────────────────────────────────────
    print("\n" + "=" * 70)
    print("BUILDING 101-POINT FRONTIERS")
    print("=" * 70)
    frontiers = {}
    for name, s in strategies.items():
        rows = build_frontier(name, s["returns"], s["native_exposure"],
                             s["native_turnover"], s["native_fee_drag"], btc_eq)
        frontiers[name] = rows
        r0, r50, r100 = rows[0], rows[50], rows[100]
        short = name.replace("_Native", "")
        print(f"  {short:<12} k=0.50: CAGR={r50['cagr']:.4f} MDD={r50['mdd']:.4f} "
              f"Sharpe={r50['sharpe']:.4f}")

    # ── 5. Matched-MDD analysis ──────────────────────────────────────────
    print("\n" + "=" * 70)
    print("MATCHED-MDD ANALYSIS")
    print("=" * 70)
    matched = matched_mdd_analysis(strategies)
    print(f"  Native MDDs:")
    for name, mdd in matched["native_mdds"].items():
        short = name.replace("_Native", "")
        print(f"    {short:<12} MDD={mdd:.4f} ({mdd*100:.2f}%)")
    print(f"  Min native MDD: {matched['min_native_mdd']:.4f}")
    print(f"  Feasible targets: {[f'{t:.1%}' for t in matched['feasible_targets']]}")

    if matched.get("matched_table"):
        print(f"\n  Matched-MDD comparison table:")
        for row in matched["matched_table"]:
            line = f"  MDD={row['target_mdd']:.1%}"
            for name in strategies:
                short = name.replace("_Native", "")
                c = row.get(f"{name}_cagr", np.nan)
                sh = row.get(f"{name}_sharpe", np.nan)
                line += f"  {short}={c:.4f}/{sh:.4f}"
            print(line)

    # ── 6. Risk-budget region ────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("OPERATIONAL RISK-BUDGET REGION")
    print("=" * 70)
    risk_budget = operational_risk_budget(strategies)
    for row in risk_budget:
        line = f"  MDD={row['target_mdd']:.1%}"
        for name in strategies:
            short = name.replace("_Native", "")
            c = row.get(f"{name}_cagr", np.nan)
            ok = row.get(f"{name}_feasible", False)
            line += f"  {short}={'Y' if ok else 'N'}/{c:.4f}"
        print(line)

    # ── 7. Pairwise: all vs E0 at matched MDD ───────────────────────────
    print("\n" + "=" * 70)
    print("PAIRWISE: ALL vs E0 AT E0-MATCHED RISK")
    print("=" * 70)
    if "E0_Native" in strategies:
        e0 = strategies["E0_Native"]
        for name, s in strategies.items():
            if name == "E0_Native":
                continue
            short = name.replace("_Native", "")
            # Scale E0 to match this strategy's native MDD
            target_mdd = s["native_mdd"]
            if e0["native_mdd"] >= target_mdd:
                k = find_k_for_target_mdd(e0["returns"], target_mdd)
                rs = scale_returns(e0["returns"], k)
                eq_k = returns_to_equity(rs)
                m = compute_metrics(eq_k, rs, k, e0["native_exposure"],
                                   e0["native_turnover"], e0["native_fee_drag"], btc_eq)
                # Compare with native
                eq_s = returns_to_equity(s["returns"])
                m_s = compute_metrics(eq_s, s["returns"], 1.0, s["native_exposure"],
                                     s["native_turnover"], s["native_fee_drag"], btc_eq)
                delta_cagr = m_s["cagr"] - m["cagr"]
                delta_sharpe = m_s["sharpe"] - m["sharpe"]
                print(f"  E0 at {short} MDD ({target_mdd:.2%}): "
                      f"k={k:.3f} CAGR={m['cagr']:.4f} vs {m_s['cagr']:.4f} "
                      f"(delta={delta_cagr:+.4f})")
            else:
                print(f"  E0 native MDD < {short} native MDD: E0 cannot match upward")

    # ── 8. Save artifacts ────────────────────────────────────────────────
    elapsed = time.time() - t0
    print("\n" + "=" * 70)
    print("SAVING ARTIFACTS")
    print("=" * 70)

    # Frontier grid CSV
    all_frontier_rows = []
    for name, rows in frontiers.items():
        for r in rows:
            r2 = {k: v for k, v in r.items() if not isinstance(v, np.ndarray)}
            all_frontier_rows.append(r2)
    pd.DataFrame(all_frontier_rows).to_csv(ARTIFACTS / "frontier_6s_grid.csv", index=False)
    print(f"  frontier_6s_grid.csv ({len(all_frontier_rows)} rows)")

    # Linearity check
    with open(ARTIFACTS / "linearity_6s_check.json", "w") as f:
        json.dump({k: _convert_dict(v) for k, v in linearity.items()}, f, indent=2)

    # Matched MDD
    if matched.get("matched_table"):
        pd.DataFrame(matched["matched_table"]).to_csv(ARTIFACTS / "matched_mdd_6s.csv", index=False)

    # Risk budget
    pd.DataFrame(risk_budget).to_csv(ARTIFACTS / "risk_budget_6s.csv", index=False)

    # Master JSON
    master = {
        "linearity": {k: _convert_dict(v) for k, v in linearity.items()},
        "matched_mdd_summary": _convert_dict({k: v for k, v in matched.items()
                                               if k != "matched_table"}),
        "_meta": {"elapsed_s": round(elapsed, 1), "n_frontier_points": 101,
                  "date": "2026-03-06", "strategies": STRATEGY_NAMES},
    }
    with open(ARTIFACTS / "step4_6s_master_results.json", "w") as f:
        json.dump(master, f, indent=2, default=_json_default)

    print(f"\n{'=' * 70}")
    print(f"COMPLETE in {elapsed:.1f}s")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
