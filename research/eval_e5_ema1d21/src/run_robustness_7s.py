#!/usr/bin/env python3
"""6-Strategy Statistical Robustness + Temporal Stability (with E5_plus_EMA1D21).

Hypotheses (all at block lengths 42, 126, 252; 5000 reps):
  H1: Sharpe(E0_EV12)               > Sharpe(E0_plus_EMA1D21_EV12)
  H2: Sharpe(E0_EV12)               > Sharpe(E5_EV12)
  H3: Sharpe(E0_plus_EMA1D21_EV12)  > Sharpe(SM_EV12)
  H4: Sharpe(E0_plus_EMA1D21_EV12)  > Sharpe(LATCH_EV12)
  H5: Sharpe(E5_plus_EMA1D21_EV12)  > Sharpe(E0_plus_EMA1D21_EV12)
  H6: Sharpe(E5_plus_EMA1D21_EV12)  > Sharpe(E5_EV12)
  H7: Sharpe(E5_plus_EMA1D21_EV12)  > Sharpe(E0_EV12)
  H8: Sharpe(LATCH_native)          > Sharpe(SM_native)

Also: all-pairs bootstrap Sharpe diff at Binary_100 (6C2 = 15 pairs)
Also: temporal stability (start-date, rolling-window, calendar slices)

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

from run_robustness import (
    equity_to_returns, sharpe_from_returns, cagr_from_returns,
    mdd_from_returns, calmar_from_returns,
    circular_block_bootstrap_indices, bootstrap_paired_returns,
    bootstrap_sharpe_diff, bootstrap_matched_mdd_cagr_diff,
    holm_adjust, classify_evidence,
    find_k_for_mdd, _clean_row, _safe,
)
from data_align import load_h4_dataframe

ARTIFACTS = _NAMESPACE / "artifacts"
EPS = 1e-12
BARS_PER_YEAR = 2190.0
ANN_FACTOR = math.sqrt(BARS_PER_YEAR)
SEED = 20260306
N_BOOT = 5000
BLOCK_LENGTHS = [42, 126, 252]

STRATEGY_NAMES = ["E0", "E5", "SM", "LATCH", "E0_plus_EMA1D21", "E5_plus_EMA1D21"]


def load_equity_curves() -> dict[str, np.ndarray]:
    npz = np.load(str(ARTIFACTS / "factorial_7s_equity_curves.npz"))
    return {k: npz[k] for k in npz.files}


def load_bar_timestamps() -> np.ndarray:
    df = load_h4_dataframe()
    return df.index.to_numpy(dtype=np.int64)


def main():
    print("6-Strategy Statistical Robustness (with E5_plus_EMA1D21)")
    print("=" * 70)
    t0 = time.time()

    # ── 1. Load data ─────────────────────────────────────────────────────
    curves = load_equity_curves()
    timestamps = load_bar_timestamps()
    df_h4 = load_h4_dataframe()
    btc_close = df_h4["close"].to_numpy(dtype=np.float64)
    n = len(timestamps)
    print(f"Loaded {len(curves)} equity curves, {n} bars")

    returns = {}
    for name in curves:
        returns[name] = equity_to_returns(curves[name])

    # ══════════════════════════════════════════════════════════════════════
    # SECTION A: ALL-PAIRS BOOTSTRAP AT BINARY_100 (15 pairs)
    # ══════════════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("ALL-PAIRS BOOTSTRAP SHARPE DIFF AT BINARY_100 (block=126)")
    print("=" * 70)

    binary_keys = [f"{s}_Binary_100" for s in STRATEGY_NAMES]
    all_pairs = []
    ref_block = 126

    for i, a in enumerate(STRATEGY_NAMES):
        for j, b in enumerate(STRATEGY_NAMES):
            if j <= i:
                continue
            ka = f"{a}_Binary_100"
            kb = f"{b}_Binary_100"
            if ka not in returns or kb not in returns:
                continue
            res = bootstrap_sharpe_diff(returns[ka], returns[kb], ref_block, N_BOOT, SEED)
            res["pair"] = f"{a} - {b}"
            res["a"] = a
            res["b"] = b
            all_pairs.append(res)
            print(f"  {a:>20} - {b:<20}: mean={res['mean']:+.4f}  "
                  f"CI=[{res['ci_lo_95']:+.4f}, {res['ci_hi_95']:+.4f}]  "
                  f"P(A>B)={res['sign_probability']:.3f}  "
                  f"CI_excl_0={res['ci_excludes_zero']}")

    # Holm adjust all 15 pairs
    raw_pvals_pairs = []
    for res in all_pairs:
        sp = res["sign_probability"]
        raw_pvals_pairs.append(2 * min(sp, 1 - sp))
    adj_pairs = holm_adjust(raw_pvals_pairs)
    print("\n  Holm-adjusted p-values:")
    for i, res in enumerate(all_pairs):
        print(f"    {res['pair']:>45}: raw_p={raw_pvals_pairs[i]:.4f}  "
              f"holm_p={adj_pairs[i]:.4f}")

    # ══════════════════════════════════════════════════════════════════════
    # SECTION B: NAMED HYPOTHESES (multi-block)
    # ══════════════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("NAMED HYPOTHESES (5000 reps x 3 block lengths)")
    print("=" * 70)

    hypotheses = [
        ("H1", "E0_EV12 > E0_plus_EMA1D21_EV12",       "E0_EntryVol_12",               "E0_plus_EMA1D21_EntryVol_12"),
        ("H2", "E0_EV12 > E5_EV12",                     "E0_EntryVol_12",               "E5_EntryVol_12"),
        ("H3", "E0_plus_EMA1D21_EV12 > SM_EV12",        "E0_plus_EMA1D21_EntryVol_12", "SM_EntryVol_12"),
        ("H4", "E0_plus_EMA1D21_EV12 > LATCH_EV12",     "E0_plus_EMA1D21_EntryVol_12", "LATCH_EntryVol_12"),
        ("H5", "E5_plus_EMA1D21_EV12 > E0_plus_EMA1D21_EV12", "E5_plus_EMA1D21_EntryVol_12", "E0_plus_EMA1D21_EntryVol_12"),
        ("H6", "E5_plus_EMA1D21_EV12 > E5_EV12",        "E5_plus_EMA1D21_EntryVol_12", "E5_EntryVol_12"),
        ("H7", "E5_plus_EMA1D21_EV12 > E0_EV12",        "E5_plus_EMA1D21_EntryVol_12", "E0_EntryVol_12"),
        ("H8", "LATCH_native > SM_native",               "LATCH_Native",                 "SM_Native"),
    ]

    named_results = {}
    method_sensitivity = []

    for hyp_id, label, key_a, key_b in hypotheses:
        print(f"\n  {hyp_id}: {label}")
        if key_a not in returns or key_b not in returns:
            print(f"    SKIPPED (missing curves)")
            continue
        by_block = {}
        for bl in BLOCK_LENGTHS:
            res = bootstrap_sharpe_diff(returns[key_a], returns[key_b], bl, N_BOOT, SEED)
            res["hypothesis"] = hyp_id
            res["block_length"] = bl
            res["comparison"] = label
            by_block[bl] = res
            print(f"    block={bl:>3}: mean={res['mean']:+.4f}  "
                  f"CI=[{res['ci_lo_95']:+.4f}, {res['ci_hi_95']:+.4f}]  "
                  f"P(>0)={res['sign_probability']:.3f}")
            method_sensitivity.append({
                "hypothesis": hyp_id, "block_length": bl,
                "ci_excludes_zero": res["ci_excludes_zero"],
                "sign_prob": res["sign_probability"],
                "mean": res["mean"],
            })
        named_results[hyp_id] = by_block

    # Holm adjustment on named hypotheses (reference block=126)
    print("\n  Holm-adjusted p-values (block=126):")
    named_raw_pvals = []
    named_ids = []
    for hyp_id, by_block in named_results.items():
        if ref_block in by_block:
            sp = by_block[ref_block]["sign_probability"]
            named_raw_pvals.append(2 * min(sp, 1 - sp))
            named_ids.append(hyp_id)
    if named_raw_pvals:
        named_adj = holm_adjust(named_raw_pvals)
        for i, hyp_id in enumerate(named_ids):
            print(f"    {hyp_id}: raw_p={named_raw_pvals[i]:.4f}  holm_p={named_adj[i]:.4f}")

    # Evidence classification
    print("\n  Evidence classification:")
    evidence_grades = {}
    for hyp_id, by_block in named_results.items():
        excl = [by_block[bl]["ci_excludes_zero"] for bl in BLOCK_LENGTHS if bl in by_block]
        sp = by_block.get(ref_block, {}).get("sign_probability", 0.5)
        grade = classify_evidence(all(excl), sp, excl)
        evidence_grades[hyp_id] = grade
        print(f"    {hyp_id}: {grade}")

    # ══════════════════════════════════════════════════════════════════════
    # SECTION C: MATCHED-MDD BOOTSTRAP (E0 vs each at 5% and 10%)
    # ══════════════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("MATCHED-MDD BOOTSTRAP (E0 vs each strategy)")
    print("=" * 70)

    matched_results = []
    for sname in STRATEGY_NAMES:
        if sname == "E0":
            continue
        key = f"{sname}_Native"
        if key not in returns or "E0_Native" not in returns:
            continue
        for target_mdd in [0.05, 0.10]:
            res = bootstrap_matched_mdd_cagr_diff(
                returns["E0_Native"], returns[key],
                target_mdd, ref_block, N_BOOT, SEED)
            res["comparison"] = f"{sname} vs E0 at {target_mdd:.0%} MDD"
            matched_results.append(res)
            print(f"  {sname} vs E0 at {target_mdd:.0%} MDD: "
                  f"mean={res['mean']:+.4f}  "
                  f"CI=[{res['ci_lo_95']:+.4f}, {res['ci_hi_95']:+.4f}]  "
                  f"P({sname}>E0)={res['sign_probability']:.3f}")

    # ══════════════════════════════════════════════════════════════════════
    # SECTION D: TEMPORAL STABILITY
    # ══════════════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("START-DATE SENSITIVITY")
    print("=" * 70)

    start_dates_ms = {
        "2017-08": int(pd.Timestamp("2017-08-01").timestamp() * 1000),
        "2019-01": int(pd.Timestamp("2019-01-01").timestamp() * 1000),
        "2020-01": int(pd.Timestamp("2020-01-01").timestamp() * 1000),
    }
    sds_rows = []
    for label, start_ms in start_dates_ms.items():
        mask = timestamps >= start_ms
        if mask.sum() < 500:
            continue
        start_idx = np.where(mask)[0][0]
        row = {"start_date": label, "n_bars": int(mask.sum())}
        print(f"\n  Start={label} ({mask.sum()} bars)")

        for sname in STRATEGY_NAMES:
            key = f"{sname}_Native"
            if key not in curves:
                continue
            eq = curves[key]
            eq_sub = eq[start_idx:]
            eq_norm = eq_sub / eq_sub[0]
            r = np.zeros_like(eq_norm)
            r[1:] = eq_norm[1:] / np.maximum(eq_norm[:-1], EPS) - 1.0
            sh = sharpe_from_returns(r)
            c = cagr_from_returns(r)
            m = mdd_from_returns(r)
            row[f"{sname}_sharpe"] = sh
            row[f"{sname}_cagr"] = c
            row[f"{sname}_mdd"] = m
            print(f"    {sname:>20}: Sharpe={sh:.4f}  CAGR={c:.4f}  MDD={m:.4f}")

        sds_rows.append(row)

    # ── Rolling-window stability ─────────────────────────────────────────
    print("\n" + "=" * 70)
    print("ROLLING-WINDOW STABILITY")
    print("=" * 70)
    bars_per_month = int(round(BARS_PER_YEAR / 12))
    step_bars = 6 * bars_per_month
    rw_rows = []

    for window_months in [24, 36]:
        window_bars = window_months * bars_per_month
        if window_bars > n:
            continue
        start = 0
        wins = {s: 0 for s in STRATEGY_NAMES}
        n_windows = 0
        while start + window_bars <= n:
            end = start + window_bars
            n_windows += 1
            row = {"window_months": window_months, "start_bar": start, "end_bar": end}

            best_sharpe = -999
            best_name = ""
            for sname in STRATEGY_NAMES:
                key = f"{sname}_Native"
                if key not in curves:
                    continue
                eq = curves[key][start:end]
                eq_norm = eq / eq[0]
                r = np.zeros_like(eq_norm)
                r[1:] = eq_norm[1:] / np.maximum(eq_norm[:-1], EPS) - 1.0
                sh = sharpe_from_returns(r)
                row[f"{sname}_sharpe"] = sh
                if sh > best_sharpe:
                    best_sharpe = sh
                    best_name = sname

            row["winner_sharpe"] = best_name
            wins[best_name] = wins.get(best_name, 0) + 1
            rw_rows.append(row)
            start += step_bars

        print(f"\n  {window_months}-month windows ({n_windows} windows):")
        for sname in STRATEGY_NAMES:
            w = wins.get(sname, 0)
            print(f"    {sname:>20} wins Sharpe: {w}/{n_windows} ({w/max(n_windows,1)*100:.0f}%)")

    # ── Calendar slices ──────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("CALENDAR-SLICE DIAGNOSTICS")
    print("=" * 70)
    dates = pd.to_datetime(timestamps, unit="ms")
    years = sorted(set(dates.year))
    cal_rows = []

    print(f"\n  {'Year':>6}", end="")
    for sname in STRATEGY_NAMES:
        print(f" {sname:>20}", end="")
    print(f" {'Winner':>20}")

    for yr in years:
        mask = dates.year == yr
        if mask.sum() < 100:
            continue
        idx = np.where(mask)[0]
        s, e = idx[0], idx[-1] + 1
        row = {"year": yr}

        best_sharpe = -999
        best_name = ""
        for sname in STRATEGY_NAMES:
            key = f"{sname}_Native"
            if key not in curves:
                continue
            eq = curves[key][s:e]
            eq_norm = eq / eq[0]
            r = np.zeros_like(eq_norm)
            r[1:] = eq_norm[1:] / np.maximum(eq_norm[:-1], EPS) - 1.0
            sh = sharpe_from_returns(r)
            row[f"{sname}_sharpe"] = sh
            if sh > best_sharpe:
                best_sharpe = sh
                best_name = sname
        row["winner"] = best_name
        cal_rows.append(row)

        print(f"  {yr:>6}", end="")
        for sname in STRATEGY_NAMES:
            print(f" {row.get(f'{sname}_sharpe', 0):>20.3f}", end="")
        print(f" {best_name:>20}")

    # ══════════════════════════════════════════════════════════════════════
    # SAVE ARTIFACTS
    # ══════════════════════════════════════════════════════════════════════
    elapsed = time.time() - t0
    print("\n" + "=" * 70)
    print("SAVING ARTIFACTS")
    print("=" * 70)

    # All-pairs bootstrap
    pairs_clean = [_clean_row(r) for r in all_pairs]
    pd.DataFrame(pairs_clean).to_csv(ARTIFACTS / "bootstrap_7s_all_pairs.csv", index=False)

    # Named hypotheses
    named_clean = []
    for hyp_id, by_block in named_results.items():
        for bl, res in by_block.items():
            named_clean.append(_clean_row(res))
    pd.DataFrame(named_clean).to_csv(ARTIFACTS / "bootstrap_7s_named_hypotheses.csv", index=False)

    # Method sensitivity
    pd.DataFrame(method_sensitivity).to_csv(ARTIFACTS / "bootstrap_7s_method_sensitivity.csv", index=False)

    # Matched MDD
    matched_clean = [_clean_row(r) for r in matched_results]
    pd.DataFrame(matched_clean).to_csv(ARTIFACTS / "bootstrap_7s_matched_mdd.csv", index=False)

    # Temporal
    pd.DataFrame(sds_rows).to_csv(ARTIFACTS / "start_date_7s.csv", index=False)
    pd.DataFrame(rw_rows).to_csv(ARTIFACTS / "rolling_window_7s.csv", index=False)
    pd.DataFrame(cal_rows).to_csv(ARTIFACTS / "calendar_slice_7s.csv", index=False)

    # Holm p-values
    holm_data = {}
    if named_raw_pvals:
        for i, hyp_id in enumerate(named_ids):
            holm_data[hyp_id] = {
                "raw_p": named_raw_pvals[i],
                "holm_p": named_adj[i],
                "evidence": evidence_grades.get(hyp_id, "UNKNOWN"),
            }
    holm_data["_all_pairs"] = {
        f"{all_pairs[i]['pair']}": {"raw_p": raw_pvals_pairs[i], "holm_p": adj_pairs[i]}
        for i in range(len(all_pairs))
    }
    with open(ARTIFACTS / "holm_7s_pvalues.json", "w") as f:
        json.dump(holm_data, f, indent=2)

    # Master JSON
    master = {
        "named_hypotheses": {
            hyp_id: {
                "evidence": evidence_grades.get(hyp_id, "UNKNOWN"),
                "ref_block_mean": by_block.get(ref_block, {}).get("mean"),
                "ref_block_sign_prob": by_block.get(ref_block, {}).get("sign_probability"),
            }
            for hyp_id, by_block in named_results.items()
        },
        "_meta": {
            "elapsed_s": round(elapsed, 1),
            "n_boot": N_BOOT,
            "block_lengths": BLOCK_LENGTHS,
            "seed": SEED,
            "date": "2026-03-06",
            "strategies": STRATEGY_NAMES,
        },
    }
    with open(ARTIFACTS / "step5_7s_master_results.json", "w") as f:
        json.dump(master, f, indent=2)

    print(f"\n{'=' * 70}")
    print(f"COMPLETE in {elapsed:.1f}s")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
