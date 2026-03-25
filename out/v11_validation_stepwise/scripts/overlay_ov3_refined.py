#!/usr/bin/env python3
"""OV3 Regularization: wider grid + HMA on/off + sizing sweep.

Goal: Find OV3 settings with WFO consistency >= 60% and no cliff risk.

Axes:
  - accel_neg_bars: [5, 6, 7, 8, 9, 10]
  - trail_tighten_mult: [2.0, 2.5, 3.0]
  - require_hma_break: [True, False]
  - sizing_mult: [0.50, 1.00]  (reduce adds vs no change)

Grid: 6 × 3 × 2 × 2 = 72 variants
Full backtest: 72 × harsh = 72
WFO: 72 × 10 windows = 720
Total: 792 backtests
"""

import csv
import json
import sys
from itertools import product
from pathlib import Path

import numpy as np

np.seterr(all="ignore")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from v10.core.data import DataFeed
from v10.core.engine import BacktestEngine
from v10.core.types import SCENARIOS
from v10.research.objective import compute_objective
from v10.research.regime import classify_d1_regimes, compute_regime_returns
from v10.research.wfo import generate_windows
from v10.strategies.v8_apex import V8ApexConfig, V8ApexStrategy
from v10.strategies.v11_hybrid import V11HybridConfig, V11HybridStrategy

DATA_PATH = "data/bars_btcusdt_2016_now_h1_4h_1d.csv"
WARMUP_DAYS = 365
START = "2019-01-01"
END = "2026-02-20"
OUTDIR = Path("out_v11_validation_stepwise")


def compute_score_no_reject(summary: dict) -> float:
    cagr = summary.get("cagr_pct", 0.0)
    max_dd = summary.get("max_drawdown_mid_pct", 0.0)
    sharpe = summary.get("sharpe") or 0.0
    pf = summary.get("profit_factor", 0.0) or 0.0
    if isinstance(pf, str):
        pf = 3.0
    n_trades = summary.get("trades", 0)
    return (
        2.5 * cagr - 0.60 * max_dd + 8.0 * max(0.0, sharpe)
        + 5.0 * max(0.0, min(pf, 3.0) - 1.0)
        + min(n_trades / 50.0, 1.0) * 5.0
    )


def _v11_base_cfg():
    cfg = V11HybridConfig()
    cfg.enable_cycle_phase = True
    cfg.cycle_early_aggression = 1.0
    cfg.cycle_early_trail_mult = 3.5
    cfg.cycle_late_aggression = 0.95
    cfg.cycle_late_trail_mult = 2.8
    cfg.cycle_late_max_exposure = 0.90
    return cfg


def make_ov3(bars, trail, hma, sizing):
    cfg = _v11_base_cfg()
    cfg.enable_overlay_decel = True
    cfg.ov3_accel_neg_bars = bars
    cfg.ov3_trail_tighten_mult = trail
    cfg.ov3_require_hma_break = hma
    cfg.ov3_sizing_mult = sizing
    return V11HybridStrategy(cfg)


def run_bt(strategy, scenario, start=START, end=END):
    cost = SCENARIOS[scenario]
    feed = DataFeed(DATA_PATH, start=start, end=end, warmup_days=WARMUP_DAYS)
    engine = BacktestEngine(feed=feed, strategy=strategy, cost=cost,
                            initial_cash=10_000.0)
    result = engine.run()
    return result, feed


# ── Grid definition ───────────────────────────────────────────────────────

BARS_RANGE = [5, 6, 7, 8, 9, 10]
TRAIL_RANGE = [2.0, 2.5, 3.0]
HMA_RANGE = [True, False]
SIZING_RANGE = [0.50, 1.00]

GRID = list(product(BARS_RANGE, TRAIL_RANGE, HMA_RANGE, SIZING_RANGE))


def main():
    print("=" * 72)
    print("OV3 Regularization Grid")
    print(f"Grid: {len(BARS_RANGE)}×{len(TRAIL_RANGE)}×{len(HMA_RANGE)}×{len(SIZING_RANGE)} = {len(GRID)} variants")
    print(f"Full backtests: {len(GRID)} | WFO: {len(GRID)*10} | Total: {len(GRID)*11}")
    print("=" * 72)

    # ── Run V10 + V11 baselines first ─────────────────────────────────────
    print("\n[0] Running baselines...")
    v10_strat = V8ApexStrategy(V8ApexConfig())
    result_v10, feed_v10 = run_bt(v10_strat, "harsh")
    s_v10 = result_v10.summary
    regimes_v10 = classify_d1_regimes(feed_v10.d1_bars)
    rr_v10 = compute_regime_returns(result_v10.equity, feed_v10.d1_bars, regimes_v10,
                                     report_start_ms=feed_v10.report_start_ms)
    v10_score = compute_objective(s_v10)
    v10_bull = rr_v10.get("BULL", {}).get("total_return_pct", 0.0)
    v10_top = rr_v10.get("TOPPING", {}).get("total_return_pct", 0.0)
    v10_mdd = s_v10.get("max_drawdown_mid_pct", 0.0)
    print(f"  V10: score={v10_score:.1f}  bull={v10_bull:.1f}%  top={v10_top:.1f}%  mdd={v10_mdd:.1f}%")

    v11_strat = V11HybridStrategy(_v11_base_cfg())
    result_v11, feed_v11 = run_bt(v11_strat, "harsh")
    s_v11 = result_v11.summary
    v11_score = compute_objective(s_v11)
    print(f"  V11: score={v11_score:.1f}")

    # V11 WFO baseline
    windows = generate_windows(START, END, train_months=24, test_months=6, slide_months=6)
    v11_wfo = {}
    for w in windows:
        strat = V11HybridStrategy(_v11_base_cfg())
        res, fd = run_bt(strat, "harsh", start=w.test_start, end=w.test_end)
        v11_wfo[w.window_id] = compute_score_no_reject(res.summary)
    print(f"  V11 WFO baseline: {[round(v, 1) for v in v11_wfo.values()]}")

    # ── Full-period grid ──────────────────────────────────────────────────
    print(f"\n[1] Full-period grid ({len(GRID)} backtests)...")
    full_rows = []

    for gi, (bars, trail, hma, sizing) in enumerate(GRID):
        tag = f"b{bars}_t{trail}_h{'Y' if hma else 'N'}_s{sizing}"
        print(f"  [{gi+1}/{len(GRID)}] {tag}...", end=" ", flush=True)

        strat = make_ov3(bars, trail, hma, sizing)
        result, feed = run_bt(strat, "harsh")
        s = result.summary
        score = compute_objective(s)
        regimes = classify_d1_regimes(feed.d1_bars)
        rr = compute_regime_returns(result.equity, feed.d1_bars, regimes,
                                     report_start_ms=feed.report_start_ms)

        row = {
            "bars": bars, "trail": trail, "hma": hma, "sizing": sizing,
            "tag": tag,
            "score": round(score, 2),
            "d_v10": round(score - v10_score, 2),
            "d_v11": round(score - v11_score, 2),
            "cagr_pct": round(s.get("cagr_pct", 0.0), 2),
            "total_return_pct": round(s.get("total_return_pct", 0.0), 2),
            "mdd_pct": round(s.get("max_drawdown_mid_pct", 0.0), 2),
            "sharpe": round(s.get("sharpe") or 0.0, 3),
            "trades": s.get("trades", 0),
            "turnover": round(s.get("turnover_per_year", 0.0), 2),
            "bull_return_pct": round(rr.get("BULL", {}).get("total_return_pct", 0.0), 2),
            "topping_return_pct": round(rr.get("TOPPING", {}).get("total_return_pct", 0.0), 2),
        }
        full_rows.append(row)
        print(f"score={score:.1f} Δv11={score - v11_score:+.1f}  "
              f"bull={row['bull_return_pct']:.0f}%  mdd={row['mdd_pct']:.1f}%")

    # ── WFO for grid points that beat V11 on full-period ──────────────────
    # Only run WFO for variants where score > v11_score (save time)
    candidates = [r for r in full_rows if r["score"] >= v11_score]
    print(f"\n[2] WFO for {len(candidates)} candidates beating V11 ({len(candidates)*10} backtests)...")

    wfo_results = {}
    for ci, row in enumerate(candidates):
        tag = row["tag"]
        wins = 0
        wscores = []
        for w in windows:
            strat = make_ov3(row["bars"], row["trail"], row["hma"], row["sizing"])
            res, fd = run_bt(strat, "harsh", start=w.test_start, end=w.test_end)
            ws = compute_score_no_reject(res.summary)
            wscores.append(ws)
            if ws > v11_wfo[w.window_id]:
                wins += 1
        win_pct = wins / len(windows) * 100
        wfo_results[tag] = {"wins": wins, "win_pct": win_pct, "scores": wscores}
        row["wfo_win_pct"] = round(win_pct, 1)
        row["wfo_wins"] = wins
        print(f"  [{ci+1}/{len(candidates)}] {tag}: {wins}/10 = {win_pct:.0f}%  "
              f"scores={[round(s,0) for s in wscores]}")

    # Mark non-candidates
    for r in full_rows:
        if "wfo_win_pct" not in r:
            r["wfo_win_pct"] = None
            r["wfo_wins"] = None

    # ── Write CSV ─────────────────────────────────────────────────────────
    csv_path = OUTDIR / "ov3_refined_grid.csv"
    fields = list(full_rows[0].keys())
    with open(csv_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(full_rows)
    print(f"\n  → {csv_path} ({len(full_rows)} rows)")

    # ── Promotion analysis ────────────────────────────────────────────────
    print(f"\n{'='*72}")
    print("PROMOTION ANALYSIS")
    print(f"{'='*72}")
    print(f"\nBaselines: V10={v10_score:.1f}  V11={v11_score:.1f}")
    print(f"Thresholds: C1(score≥V11)={v11_score:.1f}  "
          f"C2(top≥V10)={v10_top:.1f}%  C3(bull≥90%V10)={v10_bull*0.9:.0f}%  "
          f"C4(mdd≤V10)={v10_mdd:.1f}%  C5(wfo≥60%)")

    print(f"\n{'Tag':<28} {'Score':>6} {'ΔV11':>6} {'BULL':>7} {'TOP':>6} "
          f"{'MDD':>6} {'WFO%':>5} {'C1':>3} {'C2':>3} {'C3':>3} {'C4':>3} {'C5':>3} {'ALL':>4}")
    print("-" * 95)

    promoted = []
    for r in sorted(full_rows, key=lambda x: x["score"], reverse=True):
        if r["wfo_win_pct"] is None:
            continue  # didn't qualify for WFO

        c1 = r["score"] >= v11_score
        c2 = r["topping_return_pct"] >= v10_top
        c3 = r["bull_return_pct"] >= v10_bull * 0.90
        c4 = r["mdd_pct"] <= v10_mdd * 1.001
        c5 = r["wfo_win_pct"] >= 60.0
        all_pass = c1 and c2 and c3 and c4 and c5

        print(f"{r['tag']:<28} {r['score']:>6.1f} {r['d_v11']:>+6.1f} "
              f"{r['bull_return_pct']:>7.0f} {r['topping_return_pct']:>6.1f} "
              f"{r['mdd_pct']:>6.1f} {r['wfo_win_pct']:>5.0f} "
              f"{'✓' if c1 else '✗':>3} {'✓' if c2 else '✗':>3} "
              f"{'✓' if c3 else '✗':>3} {'✓' if c4 else '✗':>3} "
              f"{'✓' if c5 else '✗':>3} {'PASS' if all_pass else 'FAIL':>4}")
        if all_pass:
            promoted.append(r)

    # ── Cliff risk: check neighbors ───────────────────────────────────────
    if promoted:
        print(f"\n{'='*72}")
        print(f"CLIFF RISK CHECK for {len(promoted)} promoted variants")
        print(f"{'='*72}")
        for p in promoted:
            b, t, h, s = p["bars"], p["trail"], p["hma"], p["sizing"]
            neighbors = []
            for r in full_rows:
                # Neighbor = differs by exactly 1 axis step
                db = abs(r["bars"] - b)
                dt = abs(r["trail"] - t)
                dh = int(r["hma"] != h)
                ds = abs(r["sizing"] - s)
                if (db <= 1 and dt <= 0.5 and dh <= 1 and ds <= 0.5
                        and (db + int(dt > 0) + dh + int(ds > 0)) == 1):
                    neighbors.append(r)
            n_pass = sum(1 for n in neighbors
                        if n["score"] >= v11_score and n["mdd_pct"] <= v10_mdd * 1.001)
            print(f"  {p['tag']}: {n_pass}/{len(neighbors)} neighbors also beat V11 + MDD constraint")
            for n in neighbors:
                ok = "✓" if (n["score"] >= v11_score and n["mdd_pct"] <= v10_mdd * 1.001) else "✗"
                print(f"    {ok} {n['tag']}: score={n['score']:.1f} mdd={n['mdd_pct']:.1f}")

    # ── Summary ───────────────────────────────────────────────────────────
    n_beat_v11 = sum(1 for r in full_rows if r["score"] >= v11_score)
    n_beat_v10 = sum(1 for r in full_rows if r["score"] >= v10_score)
    print(f"\n{'='*72}")
    print(f"SUMMARY: {len(GRID)} grid points")
    print(f"  Beat V11 (score): {n_beat_v11}/{len(GRID)} = {n_beat_v11/len(GRID)*100:.0f}%")
    print(f"  Beat V10 (score): {n_beat_v10}/{len(GRID)} = {n_beat_v10/len(GRID)*100:.0f}%")
    print(f"  Fully promoted:   {len(promoted)}/{len(GRID)}")
    if promoted:
        print(f"  Best: {promoted[0]['tag']} score={promoted[0]['score']:.1f}")
    print(f"{'='*72}")

    # ── JSON ──────────────────────────────────────────────────────────────
    def _c(o):
        if isinstance(o, (np.integer,)): return int(o)
        if isinstance(o, (np.floating,)): return float(o)
        if isinstance(o, (np.bool_,)): return bool(o)
        if isinstance(o, np.ndarray): return o.tolist()
        raise TypeError(f"Not serializable: {type(o)}")

    json_path = OUTDIR / "ov3_refined_grid.json"
    with open(json_path, "w") as f:
        json.dump({
            "grid_size": len(GRID),
            "n_beat_v11": n_beat_v11,
            "n_beat_v10": n_beat_v10,
            "n_promoted": len(promoted),
            "v10_score": round(v10_score, 2),
            "v11_score": round(v11_score, 2),
            "promoted": [r["tag"] for r in promoted],
            "candidates_wfo": {tag: d for tag, d in wfo_results.items()},
        }, f, indent=2, default=_c)
    print(f"  → {json_path}")


if __name__ == "__main__":
    main()
