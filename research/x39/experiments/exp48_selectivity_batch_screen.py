#!/usr/bin/env python3
"""Exp 48: Selectivity Batch Screen — Pending Entry Filters.

Screens 7 features for selectivity using trade-level analysis.
Only features passing both SELECTIVE (>=3/5 thresholds) and
REGIME-ROBUST (>=3/4 WFO windows) promote to full WFO validation.

NOT a full backtest sweep — selectivity diagnostic only.

Usage:
    python -m research.x39.experiments.exp48_selectivity_batch_screen
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]  # btc-spot-dev/
sys.path.insert(0, str(ROOT))

from research.x39.explore import compute_features, load_data, replay_trades  # noqa: E402

RESULTS_DIR = Path(__file__).resolve().parents[1] / "results"

# ── Features to screen with gate direction ───────────────────────────────────
#   ("feature_name", "gt"|"lt")
#   gt: PASS if feature > threshold   (high = good)
#   lt: PASS if feature < threshold   (low  = good)
FEATURES: list[tuple[str, str]] = [
    ("trendq_84",          "gt"),
    ("vol_per_range",      "gt"),
    ("trade_surprise_168", "gt"),
    ("d1_taker_imbal_12",  "lt"),   # negative = reversal signal
    ("body_consist_6",     "gt"),
    ("relvol_168",         "gt"),
    ("range_vol_84",       "lt"),   # low range-vol = compression
]

PERCENTILES = [25, 33, 50, 67, 75]

# WFO test windows (identical to exp30/40/41/42)
WFO_WINDOWS: list[tuple[str, str, str]] = [
    ("W1", "2021-07-01", "2023-06-30"),
    ("W2", "2022-07-01", "2024-06-30"),
    ("W3", "2023-07-01", "2025-06-30"),
    ("W4", "2024-07-01", "2026-02-28"),
]

MIN_BLOCKED_PER_WINDOW = 15


# ═══════════════════════════════════════════════════════════════════════════════
# Selectivity computation
# ═══════════════════════════════════════════════════════════════════════════════

def compute_sel(
    wins: np.ndarray,
    net_rets: np.ndarray,
    feat_vals: np.ndarray,
    threshold: float,
    gate: str,
    total_years: float,
) -> dict:
    """Compute selectivity metrics at a given threshold.

    Returns: n_total, n_pass, n_blocked, baseline_wr, pass_wr, blocked_wr,
             selectivity, pass_sharpe, base_sharpe.
    """
    pass_mask = (feat_vals > threshold) if gate == "gt" else (feat_vals < threshold)
    blocked_mask = ~pass_mask

    n_pass = int(pass_mask.sum())
    n_blocked = int(blocked_mask.sum())
    n_total = len(wins)

    baseline_wr = float(wins.mean() * 100) if n_total > 0 else np.nan
    pass_wr = float(wins[pass_mask].mean() * 100) if n_pass > 0 else np.nan
    blocked_wr = float(wins[blocked_mask].mean() * 100) if n_blocked > 0 else np.nan
    selectivity = baseline_wr - blocked_wr if n_blocked > 0 else np.nan

    # Rough Sharpe from trade returns (PASS-only group)
    pass_sharpe = np.nan
    if n_pass >= 5 and total_years > 0:
        pr = net_rets[pass_mask]
        if pr.std() > 0:
            pass_sharpe = float(pr.mean() / pr.std() * np.sqrt(n_pass / total_years))

    # Baseline Sharpe for comparison
    base_sharpe = np.nan
    if n_total >= 5 and total_years > 0 and net_rets.std() > 0:
        base_sharpe = float(
            net_rets.mean() / net_rets.std() * np.sqrt(n_total / total_years)
        )

    return {
        "n_total": n_total,
        "n_pass": n_pass,
        "n_blocked": n_blocked,
        "baseline_wr": round(baseline_wr, 1) if np.isfinite(baseline_wr) else np.nan,
        "pass_wr": round(pass_wr, 1) if np.isfinite(pass_wr) else np.nan,
        "blocked_wr": round(blocked_wr, 1) if np.isfinite(blocked_wr) else np.nan,
        "selectivity": round(selectivity, 2) if np.isfinite(selectivity) else np.nan,
        "pass_sharpe": round(pass_sharpe, 4) if np.isfinite(pass_sharpe) else np.nan,
        "base_sharpe": round(base_sharpe, 4) if np.isfinite(base_sharpe) else np.nan,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("EXP 48: Selectivity Batch Screen")
    print(f"  Features: {len(FEATURES)}")
    print(f"  Percentiles: {PERCENTILES}")
    print(f"  WFO windows: {len(WFO_WINDOWS)}")
    print(f"  Min blocked/window: {MIN_BLOCKED_PER_WINDOW}")
    print("=" * 80)

    # ── Step 1-2: Baseline trades ────────────────────────────────────────
    h4, d1 = load_data()
    feat = compute_features(h4, d1)
    trades = replay_trades(feat)

    n_trades = len(trades)
    baseline_wr = trades["win"].mean() * 100
    print(f"\nBaseline: {n_trades} trades, WR={baseline_wr:.1f}%")

    # Total years for Sharpe annualization
    bars_per_year = 365.25 * 24 / 4
    entry_bars = trades["entry_bar"].values.astype(int)
    exit_bars = trades["exit_bar"].values.astype(int)
    total_bars_span = int(exit_bars[-1] - entry_bars[0])
    total_years = total_bars_span / bars_per_year
    print(f"  Span: {total_bars_span} bars = {total_years:.2f} years")

    # Attach entry datetime and feature values
    datetimes = pd.DatetimeIndex(feat["datetime"])
    trades["entry_dt"] = pd.DatetimeIndex([datetimes[eb] for eb in entry_bars])

    for fname, _ in FEATURES:
        arr = feat[fname].values
        trades[f"f_{fname}"] = np.array([arr[eb] for eb in entry_bars])

    # ── Screen each feature ──────────────────────────────────────────────
    detail_rows: list[dict] = []
    verdict_rows: list[dict] = []

    for fname, gate in FEATURES:
        print(f"\n{'=' * 80}")
        gate_sym = ">" if gate == "gt" else "<"
        print(f"FEATURE: {fname}  (PASS: feature {gate_sym} threshold)")
        print(f"{'=' * 80}")

        fv = trades[f"f_{fname}"].values.astype(float)
        valid = np.isfinite(fv)
        n_valid = int(valid.sum())

        if n_valid < 20:
            print(f"  SKIP: {n_valid} valid entries < 20")
            verdict_rows.append({
                "feature": fname, "gate": gate, "n_valid": n_valid,
                "sel_count": 0, "selective": False,
                "rgm_count": 0, "regime_robust": False,
                "verdict": "SKIP",
            })
            continue

        vt = trades[valid].reset_index(drop=True)
        vf = fv[valid]
        vw = vt["win"].values.astype(float)
        vr = vt["net_ret"].values.astype(float)

        print(f"  Valid: {n_valid}/{n_trades}")
        pstats = np.percentile(vf, [0, 25, 50, 75, 100])
        print(f"  Feature: min={pstats[0]:.4f}  P25={pstats[1]:.4f}  "
              f"P50={pstats[2]:.4f}  P75={pstats[3]:.4f}  max={pstats[4]:.4f}")

        # Percentile thresholds from feature values AT entry bars
        pct_thresholds = {p: float(np.percentile(vf, p)) for p in PERCENTILES}

        # ── Full-sample: 5 threshold sweep ───────────────────────────────
        print(f"\n  Full-sample (baseline WR={vw.mean()*100:.1f}%, N={n_valid}):")
        print(f"  {'P':>4s}  {'Thresh':>10s}  {'N_p':>5s}  {'N_b':>5s}  "
              f"{'P_WR':>6s}  {'B_WR':>6s}  {'Sel':>7s}  {'P_Sh':>7s}")

        sel_count = 0
        for p in PERCENTILES:
            t = pct_thresholds[p]
            r = compute_sel(vw, vr, vf, t, gate, total_years)

            is_pos = np.isfinite(r["selectivity"]) and r["selectivity"] > 0
            if is_pos:
                sel_count += 1
            tag = "+" if is_pos else "-"

            print(f"  P{p:<3d}  {t:>10.4f}  {r['n_pass']:>5d}  {r['n_blocked']:>5d}  "
                  f"{r['pass_wr']:>5.1f}%  {r['blocked_wr']:>5.1f}%  "
                  f"{r['selectivity']:>+6.1f}  {r['pass_sharpe']:>7.4f}  [{tag}]")

            detail_rows.append({
                "feature": fname, "gate": gate, "window": "full",
                "percentile": p, "threshold": round(t, 6),
                **r,
            })

        is_selective = sel_count >= 3
        print(f"\n  SELECTIVE: {sel_count}/5 "
              f"{'>=3 -> YES' if is_selective else '< 3 -> NO'}")

        # ── Per-window selectivity (at P50 threshold) ────────────────────
        p50_t = pct_thresholds[50]
        print(f"\n  Per-window selectivity (P50 thresh={p50_t:.4f}):")

        rgm_count = 0
        for wlabel, wstart, wend in WFO_WINDOWS:
            ws = pd.Timestamp(wstart)
            we = pd.Timestamp(wend)
            wm = (vt["entry_dt"] >= ws) & (vt["entry_dt"] <= we)
            wm_arr = wm.values
            n_w = int(wm_arr.sum())

            if n_w < 5:
                print(f"    {wlabel}: {n_w} trades (skip)")
                continue

            ww = vw[wm_arr]
            wfv = vf[wm_arr]
            wr_arr = vr[wm_arr]
            w_years = (we - ws).days / 365.25

            r_w = compute_sel(ww, wr_arr, wfv, p50_t, gate, w_years)

            suf = r_w["n_blocked"] >= MIN_BLOCKED_PER_WINDOW
            sel_ok = np.isfinite(r_w["selectivity"]) and r_w["selectivity"] > 0

            if suf and sel_ok:
                rgm_count += 1

            suf_tag = "" if suf else " (N_b<15!)"
            tag = "+" if sel_ok else "-"
            b_wr_s = f"{r_w['blocked_wr']:.1f}" if np.isfinite(r_w["blocked_wr"]) else "N/A"
            sel_s = f"{r_w['selectivity']:+.1f}" if np.isfinite(r_w["selectivity"]) else "N/A"

            print(f"    {wlabel}: N={n_w}, p={r_w['n_pass']}, "
                  f"b={r_w['n_blocked']}{suf_tag}, "
                  f"B_WR={b_wr_s}%, sel={sel_s} [{tag}]")

            detail_rows.append({
                "feature": fname, "gate": gate, "window": wlabel,
                "percentile": 50, "threshold": round(p50_t, 6),
                **r_w,
            })

        is_regime_robust = rgm_count >= 3
        print(f"\n  REGIME-ROBUST: {rgm_count}/4 "
              f"{'>=3 -> YES' if is_regime_robust else '< 3 -> NO'}")

        # Feature verdict
        if is_selective and is_regime_robust:
            verdict = "PROMOTE"
        else:
            verdict = "CLOSE"

        reasons = []
        if not is_selective:
            reasons.append(f"sel {sel_count}/5")
        if not is_regime_robust:
            reasons.append(f"rgm {rgm_count}/4")
        reason_str = f" ({', '.join(reasons)})" if reasons else ""

        print(f"\n  --> {fname}: {verdict}{reason_str}")

        verdict_rows.append({
            "feature": fname, "gate": gate, "n_valid": n_valid,
            "sel_count": sel_count, "selective": is_selective,
            "rgm_count": rgm_count, "regime_robust": is_regime_robust,
            "verdict": verdict,
        })

    # ═══════════════════════════════════════════════════════════════════════
    # Summary
    # ═══════════════════════════════════════════════════════════════════════
    print("\n" + "=" * 80)
    print("BATCH SCREEN SUMMARY")
    print("=" * 80)

    vdf = pd.DataFrame(verdict_rows)

    print(f"\n  {'Feature':>25s}  {'Gate':>4s}  {'Sel':>5s}  {'Rgm':>5s}  {'Verdict':>8s}")
    print(f"  {'-' * 55}")
    for _, row in vdf.iterrows():
        gs = ">" if row["gate"] == "gt" else "<"
        print(f"  {row['feature']:>25s}  {gs:>4s}  "
              f"{row['sel_count']}/5  {row['rgm_count']}/4  {row['verdict']:>8s}")

    promoted = vdf[vdf["verdict"] == "PROMOTE"]
    closed = vdf[vdf["verdict"] != "PROMOTE"]

    print(f"\n  Promoted: {len(promoted)} -> proceed to WFO validation")
    if len(promoted) > 0:
        for _, row in promoted.iterrows():
            print(f"    [+] {row['feature']}")

    print(f"  Closed: {len(closed)} -> no further testing")
    for _, row in closed.iterrows():
        print(f"    [-] {row['feature']}")

    # ── Save ─────────────────────────────────────────────────────────────
    detail_df = pd.DataFrame(detail_rows)
    out_path = RESULTS_DIR / "exp48_results.csv"
    detail_df.to_csv(out_path, index=False)
    print(f"\n-> Saved to {out_path}")


if __name__ == "__main__":
    main()
