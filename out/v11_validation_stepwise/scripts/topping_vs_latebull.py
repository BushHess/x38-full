#!/usr/bin/env python3
"""Nhiệm vụ E: TOPPING regime vs LATE_BULL cycle phase — overlap & lead-lag.

Computes:
  1. D1 regime labels using classify_d1_regimes() (TOPPING from regime.py)
  2. D1 cycle phase labels using V11's _compute_cycle_phases() (LATE_BULL)
  3. Overlap statistics:
     - % TOPPING days that are also LATE_BULL
     - % LATE_BULL days that are also TOPPING
  4. Confusion matrix (TOPPING x LATE_BULL)
  5. Lead-lag distribution: when does LATE_BULL trigger relative to TOPPING?

Definitions:
  TOPPING (regime.py:170-174):
    |close - EMA50| / EMA50 < 1% AND ADX < 25
    Priority: checked AFTER SHOCK, BEAR, CHOP

  LATE_BULL (v11_hybrid.py:393-394):
    (close - EMA200) / EMA200 >= 0.40 AND RSI(14) >= 70
    With 5-bar hysteresis

Output:
  - overlap_topping_latebull.csv
  - reports/topping_vs_latebull.md
"""

import csv
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

import numpy as np

np.seterr(all="ignore")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from v10.core.data import DataFeed
from v10.research.regime import classify_d1_regimes, AnalyticalRegime

# We need V11's cycle phase computation — import and instantiate minimally
from v10.strategies.v11_hybrid import (
    V11HybridConfig, V11HybridStrategy, CyclePhase,
)

DATA_PATH = "data/bars_btcusdt_2016_now_h1_4h_1d.csv"
WARMUP_DAYS = 365
EVAL_START = "2019-01-01"
EVAL_END = "2026-02-20"
OUTDIR = Path("out_v11_validation_stepwise")


def main():
    print("=" * 72)
    print("Nhiệm vụ E: TOPPING regime vs LATE_BULL cycle phase alignment")
    print("=" * 72)

    # ── Load D1 bars ──────────────────────────────────────────────────────
    print("\n[1] Loading data...")
    feed = DataFeed(DATA_PATH, start=EVAL_START, end=EVAL_END,
                    warmup_days=WARMUP_DAYS)
    d1_bars = feed.d1_bars
    print(f"    D1 bars (incl warmup): {len(d1_bars)}")
    print(f"    First: {d1_bars[0].open_time}  Last: {d1_bars[-1].open_time}")

    # Determine eval window (skip warmup) using report_start_ms
    report_start_ms = feed.report_start_ms
    eval_indices = []
    for i, b in enumerate(d1_bars):
        if report_start_ms is None or b.open_time >= report_start_ms:
            eval_indices.append(i)

    warmup_end_idx = eval_indices[0] if eval_indices else 0
    print(f"    Eval bars (post-warmup): {len(eval_indices)} (idx {warmup_end_idx} to {len(d1_bars)-1})")

    # ── Compute TOPPING regime labels ─────────────────────────────────────
    print("\n[2] Computing regime labels (classify_d1_regimes)...")
    regimes = classify_d1_regimes(d1_bars)
    assert len(regimes) == len(d1_bars)

    # ── Compute LATE_BULL cycle phase labels ──────────────────────────────
    print("[3] Computing cycle phase labels (V11 _compute_cycle_phases)...")

    # Extract arrays from d1_bars
    d1c = np.array([b.close for b in d1_bars], dtype=np.float64)
    d1h = np.array([b.high for b in d1_bars], dtype=np.float64)
    d1l = np.array([b.low for b in d1_bars], dtype=np.float64)

    # Instantiate V11 with default cycle params to call _compute_cycle_phases
    cfg = V11HybridConfig()
    cfg.enable_cycle_phase = True
    # Use WFO-optimal params (same as used in validation)
    cfg.cycle_late_aggression = 0.95
    cfg.cycle_late_trail_mult = 2.8
    cfg.cycle_late_max_exposure = 0.90

    strat = V11HybridStrategy(cfg)
    phases = strat._compute_cycle_phases(d1c, d1h, d1l)
    assert len(phases) == len(d1_bars)

    # ── Restrict to eval window ───────────────────────────────────────────
    eval_regimes = [regimes[i] for i in eval_indices]
    eval_phases = [phases[i] for i in eval_indices]
    eval_dates = []
    eval_closes = []
    for i in eval_indices:
        b = d1_bars[i]
        # open_time is epoch ms
        ts = b.open_time / 1000.0
        eval_dates.append(datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d"))
        eval_closes.append(d1_bars[i].close)

    N = len(eval_indices)
    print(f"\n[4] Eval window: {N} D1 bars ({eval_dates[0]} to {eval_dates[-1]})")

    # ── Per-day classification ────────────────────────────────────────────
    is_topping = [r == AnalyticalRegime.TOPPING for r in eval_regimes]
    is_late_bull = [p == CyclePhase.LATE_BULL for p in eval_phases]

    n_topping = sum(is_topping)
    n_late_bull = sum(is_late_bull)
    n_both = sum(a and b for a, b in zip(is_topping, is_late_bull))
    n_neither = sum(not a and not b for a, b in zip(is_topping, is_late_bull))
    n_topping_only = sum(a and not b for a, b in zip(is_topping, is_late_bull))
    n_late_only = sum(not a and b for a, b in zip(is_topping, is_late_bull))

    print(f"\n{'='*60}")
    print("OVERLAP STATISTICS")
    print(f"{'='*60}")
    print(f"  Total eval days:          {N}")
    print(f"  TOPPING days:             {n_topping} ({n_topping/N*100:.1f}%)")
    print(f"  LATE_BULL days:           {n_late_bull} ({n_late_bull/N*100:.1f}%)")
    print(f"  Both (overlap):           {n_both} ({n_both/N*100:.1f}%)")
    print(f"  TOPPING only:             {n_topping_only}")
    print(f"  LATE_BULL only:           {n_late_only}")
    print(f"  Neither:                  {n_neither}")

    overlap_given_topping = n_both / n_topping * 100 if n_topping > 0 else 0.0
    overlap_given_late = n_both / n_late_bull * 100 if n_late_bull > 0 else 0.0
    jaccard = n_both / (n_topping + n_late_bull - n_both) * 100 if (n_topping + n_late_bull - n_both) > 0 else 0.0

    print(f"\n  P(LATE_BULL | TOPPING):   {overlap_given_topping:.1f}%")
    print(f"  P(TOPPING | LATE_BULL):   {overlap_given_late:.1f}%")
    print(f"  Jaccard index:            {jaccard:.1f}%")

    # ── Confusion matrix ──────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("CONFUSION MATRIX")
    print(f"{'='*60}")
    print(f"                     LATE_BULL=True  LATE_BULL=False   Total")
    print(f"  TOPPING=True       {n_both:>10}     {n_topping_only:>10}     {n_topping:>6}")
    print(f"  TOPPING=False      {n_late_only:>10}     {n_neither:>10}     {N - n_topping:>6}")
    print(f"  Total              {n_late_bull:>10}     {N - n_late_bull:>10}     {N:>6}")

    # ── Full regime × cycle phase cross-tabulation ────────────────────────
    print(f"\n{'='*60}")
    print("FULL CROSS-TABULATION: Regime × CyclePhase")
    print(f"{'='*60}")

    regime_names = ["SHOCK", "BEAR", "CHOP", "TOPPING", "BULL", "NEUTRAL"]
    phase_names = ["BEAR", "EARLY_BULL", "MID_BULL", "LATE_BULL"]

    cross = Counter()
    for r, p in zip(eval_regimes, eval_phases):
        cross[(r.value, p.value)] += 1

    # Header
    hdr = f"{'Regime':<12}" + "".join(f"{p:>12}" for p in phase_names) + f"{'Total':>8}"
    print(hdr)
    print("-" * len(hdr))
    for rn in regime_names:
        row_vals = [cross.get((rn, pn), 0) for pn in phase_names]
        row_total = sum(row_vals)
        row_str = f"{rn:<12}" + "".join(f"{v:>12}" for v in row_vals) + f"{row_total:>8}"
        print(row_str)
    # Totals
    col_totals = [sum(cross.get((rn, pn), 0) for rn in regime_names) for pn in phase_names]
    print("-" * len(hdr))
    print(f"{'Total':<12}" + "".join(f"{v:>12}" for v in col_totals) + f"{sum(col_totals):>8}")

    # ── Lead-lag analysis ─────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("LEAD-LAG ANALYSIS")
    print(f"{'='*60}")

    # Find episodes (contiguous blocks) of TOPPING and LATE_BULL
    def find_episodes(flags):
        """Return list of (start_idx, end_idx) for contiguous True blocks."""
        eps = []
        in_ep = False
        for i, f in enumerate(flags):
            if f and not in_ep:
                start = i
                in_ep = True
            elif not f and in_ep:
                eps.append((start, i - 1))
                in_ep = False
        if in_ep:
            eps.append((start, len(flags) - 1))
        return eps

    topping_eps = find_episodes(is_topping)
    late_bull_eps = find_episodes(is_late_bull)

    print(f"\n  TOPPING episodes:    {len(topping_eps)}")
    for i, (s, e) in enumerate(topping_eps):
        print(f"    [{i+1}] {eval_dates[s]} → {eval_dates[e]} ({e-s+1} days, close: ${eval_closes[s]:,.0f}→${eval_closes[e]:,.0f})")

    print(f"\n  LATE_BULL episodes:  {len(late_bull_eps)}")
    for i, (s, e) in enumerate(late_bull_eps):
        print(f"    [{i+1}] {eval_dates[s]} → {eval_dates[e]} ({e-s+1} days, close: ${eval_closes[s]:,.0f}→${eval_closes[e]:,.0f})")

    # Lead-lag: for each TOPPING episode, find nearest LATE_BULL episode
    # Positive lag = LATE_BULL starts AFTER TOPPING starts (TOPPING leads)
    # Negative lag = LATE_BULL starts BEFORE TOPPING starts (LATE_BULL leads)
    lags_topping_to_late = []
    for ts, te in topping_eps:
        best_lag = None
        for ls, le in late_bull_eps:
            lag = ls - ts  # days between starts
            if best_lag is None or abs(lag) < abs(best_lag):
                best_lag = lag
        if best_lag is not None:
            lags_topping_to_late.append(best_lag)

    lags_late_to_topping = []
    for ls, le in late_bull_eps:
        best_lag = None
        for ts, te in topping_eps:
            lag = ts - ls  # days between starts
            if best_lag is None or abs(lag) < abs(best_lag):
                best_lag = lag
        if best_lag is not None:
            lags_late_to_topping.append(best_lag)

    if lags_topping_to_late:
        lags = np.array(lags_topping_to_late)
        print(f"\n  Lead-lag: TOPPING start → nearest LATE_BULL start (days)")
        print(f"    Mean:   {np.mean(lags):+.1f}")
        print(f"    Median: {np.median(lags):+.1f}")
        print(f"    P10:    {np.percentile(lags, 10):+.1f}")
        print(f"    P90:    {np.percentile(lags, 90):+.1f}")
        print(f"    Min:    {np.min(lags):+d}")
        print(f"    Max:    {np.max(lags):+d}")
        print(f"    (Positive = LATE_BULL follows TOPPING; Negative = LATE_BULL precedes)")
    else:
        print("\n  No lead-lag data (one or both have zero episodes)")

    if lags_late_to_topping:
        lags2 = np.array(lags_late_to_topping)
        print(f"\n  Lead-lag: LATE_BULL start → nearest TOPPING start (days)")
        print(f"    Mean:   {np.mean(lags2):+.1f}")
        print(f"    Median: {np.median(lags2):+.1f}")
        print(f"    P10:    {np.percentile(lags2, 10):+.1f}")
        print(f"    P90:    {np.percentile(lags2, 90):+.1f}")
        print(f"    Min:    {np.min(lags2):+d}")
        print(f"    Max:    {np.max(lags2):+d}")

    # ── Coincidence during episodes ───────────────────────────────────────
    print(f"\n{'='*60}")
    print("EPISODE COINCIDENCE")
    print(f"{'='*60}")

    # For each TOPPING episode: what % of its days are also LATE_BULL?
    print("\n  Per TOPPING episode: % days also LATE_BULL")
    for i, (s, e) in enumerate(topping_eps):
        dur = e - s + 1
        overlap_days = sum(1 for j in range(s, e + 1) if is_late_bull[j])
        phases_in_ep = [eval_phases[j].value for j in range(s, e + 1)]
        phase_dist = Counter(phases_in_ep)
        print(f"    [{i+1}] {eval_dates[s]}-{eval_dates[e]}: {overlap_days}/{dur} = {overlap_days/dur*100:.0f}% LATE_BULL"
              f"  (phases: {dict(phase_dist)})")

    print("\n  Per LATE_BULL episode: % days also TOPPING")
    for i, (s, e) in enumerate(late_bull_eps):
        dur = e - s + 1
        overlap_days = sum(1 for j in range(s, e + 1) if is_topping[j])
        regimes_in_ep = [eval_regimes[j].value for j in range(s, e + 1)]
        regime_dist = Counter(regimes_in_ep)
        print(f"    [{i+1}] {eval_dates[s]}-{eval_dates[e]}: {overlap_days}/{dur} = {overlap_days/dur*100:.0f}% TOPPING"
              f"  (regimes: {dict(regime_dist)})")

    # ── Yearly breakdown ──────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("YEARLY BREAKDOWN")
    print(f"{'='*60}")
    years = sorted(set(d[:4] for d in eval_dates))
    print(f"\n  {'Year':<6} {'Days':>6} {'TOPPING':>8} {'LATE_BULL':>10} {'Both':>6} {'P(LB|TOP)':>10} {'P(TOP|LB)':>10}")
    print(f"  {'-'*56}")
    for yr in years:
        yr_mask = [d.startswith(yr) for d in eval_dates]
        yr_n = sum(yr_mask)
        yr_top = sum(a and b for a, b in zip(yr_mask, is_topping))
        yr_late = sum(a and b for a, b in zip(yr_mask, is_late_bull))
        yr_both = sum(a and b and c for a, b, c in zip(yr_mask, is_topping, is_late_bull))
        p_lb_top = yr_both / yr_top * 100 if yr_top > 0 else 0.0
        p_top_lb = yr_both / yr_late * 100 if yr_late > 0 else 0.0
        print(f"  {yr:<6} {yr_n:>6} {yr_top:>8} {yr_late:>10} {yr_both:>6} {p_lb_top:>9.1f}% {p_top_lb:>9.1f}%")

    # ── Write CSV ─────────────────────────────────────────────────────────
    csv_path = OUTDIR / "overlap_topping_latebull.csv"
    print(f"\n[5] Writing CSV: {csv_path}")
    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "close", "regime", "cycle_phase", "is_topping", "is_late_bull", "is_both"])
        for i in range(N):
            w.writerow([
                eval_dates[i],
                f"{eval_closes[i]:.2f}",
                eval_regimes[i].value,
                eval_phases[i].value if hasattr(eval_phases[i], 'value') else str(eval_phases[i]),
                int(is_topping[i]),
                int(is_late_bull[i]),
                int(is_topping[i] and is_late_bull[i]),
            ])

    # ── Write JSON summary ────────────────────────────────────────────────
    json_path = OUTDIR / "topping_vs_latebull.json"
    summary = {
        "eval_days": N,
        "n_topping": n_topping,
        "n_late_bull": n_late_bull,
        "n_both": n_both,
        "n_topping_only": n_topping_only,
        "n_late_only": n_late_only,
        "n_neither": n_neither,
        "pct_topping": round(n_topping / N * 100, 2),
        "pct_late_bull": round(n_late_bull / N * 100, 2),
        "overlap_given_topping": round(overlap_given_topping, 2),
        "overlap_given_late_bull": round(overlap_given_late, 2),
        "jaccard_pct": round(jaccard, 2),
        "topping_episodes": len(topping_eps),
        "late_bull_episodes": len(late_bull_eps),
        "lead_lag_topping_to_late": {
            "mean": round(float(np.mean(lags_topping_to_late)), 1) if lags_topping_to_late else None,
            "median": round(float(np.median(lags_topping_to_late)), 1) if lags_topping_to_late else None,
            "p10": round(float(np.percentile(lags_topping_to_late, 10)), 1) if lags_topping_to_late else None,
            "p90": round(float(np.percentile(lags_topping_to_late, 90)), 1) if lags_topping_to_late else None,
        },
        "cross_tabulation": {f"{rn}_{pn}": cross.get((rn, pn), 0) for rn in regime_names for pn in phase_names},
    }
    with open(json_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"    JSON: {json_path}")

    print(f"\n{'='*72}")
    print("DONE — Nhiệm vụ E data collection complete.")
    print(f"{'='*72}")


if __name__ == "__main__":
    main()
