#!/usr/bin/env python3
"""Exp 29: AND-Gate Trail Tightener.

E5-ema21D1 with AND-gated trail tightening instead of immediate exit:
  When rangepos_84 < rp_threshold AND trendq_84 < tq_threshold,
  tighten trail_mult from 3.0 to tight_mult (one-way latch).

Entry logic UNCHANGED. Trail tightening replaces exp22's binary exit.
The trade may survive (price stays above tighter trail) or exit later.

Sweep:
  A) Fix rp=0.20, tq=-0.10 → tight_mult in [1.0, 1.5, 2.0, 2.5]  (4 configs)
  B) Fix rp=0.20, tight_mult=1.5 → tq in [-0.20, -0.10, 0.00, 0.10]  (3 new + 1 overlap)
  + baseline + exp22 reproduction = 9 total runs

Usage:
    python -m research.x39.experiments.exp29_and_gate_trail_tightener
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]  # btc-spot-dev/
sys.path.insert(0, str(ROOT))

from research.x39.explore import compute_features, load_data  # noqa: E402

RESULTS_DIR = Path(__file__).resolve().parents[1] / "results"

# ── Strategy constants (match E5-ema21D1) ─────────────────────────────────
SLOW_PERIOD = 120
TRAIL_MULT = 3.0
COST_BPS = 50
INITIAL_CASH = 10_000.0

# Exp22 optimum (fixed for AND gate)
RP_THRESHOLD = 0.20
TQ_THRESHOLD = -0.10


def run_backtest(
    feat: pd.DataFrame,
    warmup_bar: int,
    *,
    tight_mult: float | None = None,
    rp_threshold: float = RP_THRESHOLD,
    tq_threshold: float = TQ_THRESHOLD,
    binary_exit: bool = False,
) -> dict:
    """Replay E5-ema21D1 with optional AND-gated trail tightening.

    - tight_mult=None, binary_exit=False: baseline (no AND gate).
    - tight_mult=None, binary_exit=True: exp22 reproduction (immediate exit).
    - tight_mult set: trail tightening mode (one-way latch).
    """
    c = feat["close"].values
    ema_f = feat["ema_fast"].values
    ema_s = feat["ema_slow"].values
    ratr = feat["ratr"].values
    vdo_arr = feat["vdo"].values
    d1_ok = feat["d1_regime_ok"].values
    rangepos = feat["rangepos_84"].values
    trendq = feat["trendq_84"].values
    n = len(c)

    mode_tighten = tight_mult is not None and not binary_exit

    trades: list[dict] = []
    exit_counts = {"trail": 0, "trend": 0, "and_gate": 0, "tight_trail": 0}
    tighten_events: list[dict] = []

    in_pos = False
    peak = 0.0
    entry_bar = 0
    entry_price = 0.0
    current_trail_mult = TRAIL_MULT
    tightened = False
    tighten_bar = -1

    equity = np.full(n, np.nan)
    cash = INITIAL_CASH
    position_size = 0.0

    for i in range(warmup_bar, n):
        if np.isnan(ratr[i]):
            equity[i] = cash
            continue

        if not in_pos:
            equity[i] = cash

            entry_ok = (
                ema_f[i] > ema_s[i]
                and vdo_arr[i] > 0
                and d1_ok[i]
            )

            if entry_ok:
                in_pos = True
                entry_bar = i
                entry_price = c[i]
                peak = c[i]
                current_trail_mult = TRAIL_MULT
                tightened = False
                tighten_bar = -1
                half_cost = (COST_BPS / 2) / 10_000
                position_size = cash * (1 - half_cost) / c[i]
                cash = 0.0
        else:
            equity[i] = position_size * c[i]
            peak = max(peak, c[i])

            # ── Check AND gate ────────────────────────────────────
            and_fires = (
                np.isfinite(rangepos[i])
                and rangepos[i] < rp_threshold
                and np.isfinite(trendq[i])
                and trendq[i] < tq_threshold
            )

            # Binary exit mode (exp22 reproduction)
            if binary_exit and and_fires:
                exit_reason = "and_gate"
            else:
                # Trail tightening (one-way latch)
                if mode_tighten and not tightened and and_fires:
                    current_trail_mult = tight_mult
                    tightened = True
                    tighten_bar = i

                trail_stop = peak - current_trail_mult * ratr[i]
                exit_reason = None

                if c[i] < trail_stop:
                    exit_reason = "tight_trail" if tightened else "trail"
                elif ema_f[i] < ema_s[i]:
                    exit_reason = "trend"

            if exit_reason:
                half_cost = (COST_BPS / 2) / 10_000
                cash = position_size * c[i] * (1 - half_cost)
                gross_ret = (c[i] - entry_price) / entry_price
                net_ret = gross_ret - COST_BPS / 10_000

                trade_rec = {
                    "entry_bar": entry_bar,
                    "exit_bar": i,
                    "bars_held": i - entry_bar,
                    "entry_price": entry_price,
                    "exit_price": c[i],
                    "gross_ret": gross_ret,
                    "net_ret": net_ret,
                    "exit_reason": exit_reason,
                    "win": int(net_ret > 0),
                    "tightened": tightened,
                    "tighten_bar": tighten_bar if tightened else -1,
                }
                trades.append(trade_rec)

                # Record tightening event outcome
                if tightened:
                    survived = exit_reason != "tight_trail"
                    tighten_events.append({
                        "entry_bar": entry_bar,
                        "tighten_bar": tighten_bar,
                        "exit_bar": i,
                        "bars_after_tighten": i - tighten_bar,
                        "exit_reason": exit_reason,
                        "survived": survived,
                        "win": int(net_ret > 0),
                        "net_ret": net_ret,
                    })

                exit_counts[exit_reason] = exit_counts.get(exit_reason, 0) + 1
                equity[i] = cash
                position_size = 0.0
                in_pos = False
                peak = 0.0

    # ── Compute metrics ───────────────────────────────────────────────
    eq = pd.Series(equity[warmup_bar:]).dropna()

    # Config label
    if binary_exit:
        config = f"exp22_binary_rp={rp_threshold}_tq={tq_threshold}"
    elif mode_tighten:
        config = f"tight={tight_mult}_rp={rp_threshold}_tq={tq_threshold}"
    else:
        config = "baseline"

    if len(eq) < 2 or len(trades) == 0:
        return {
            "config": config, "tight_mult": tight_mult,
            "rp_threshold": rp_threshold, "tq_threshold": tq_threshold,
            "sharpe": np.nan, "cagr_pct": np.nan, "mdd_pct": np.nan,
            "trades": 0, "win_rate": np.nan, "exposure_pct": np.nan,
            "exit_trail": 0, "exit_trend": 0, "exit_and_gate": 0,
            "exit_tight_trail": 0,
            "tighten_count": 0, "survived": 0, "triggered": 0,
            "survived_winners": 0, "survived_losers": 0,
            "triggered_winners": 0, "triggered_losers": 0,
        }

    rets = eq.pct_change().dropna()
    bars_per_year = 365.25 * 24 / 4

    sharpe = rets.mean() / rets.std() * np.sqrt(bars_per_year) if rets.std() > 0 else 0.0

    total_bars = len(eq)
    years = total_bars / bars_per_year
    final_ret = eq.iloc[-1] / eq.iloc[0]
    cagr = final_ret ** (1 / years) - 1 if years > 0 and final_ret > 0 else 0.0

    cummax = eq.cummax()
    dd = (eq - cummax) / cummax
    mdd = dd.min()

    total_bars_held = sum(t["bars_held"] for t in trades)
    exposure = total_bars_held / total_bars

    tdf = pd.DataFrame(trades)
    wins = tdf[tdf["win"] == 1]

    # Tightening outcome stats
    n_tighten = len(tighten_events)
    n_survived = sum(1 for e in tighten_events if e["survived"])
    n_triggered = n_tighten - n_survived
    survived_winners = sum(1 for e in tighten_events if e["survived"] and e["win"])
    survived_losers = sum(1 for e in tighten_events if e["survived"] and not e["win"])
    triggered_winners = sum(1 for e in tighten_events if not e["survived"] and e["win"])
    triggered_losers = sum(1 for e in tighten_events if not e["survived"] and not e["win"])

    return {
        "config": config,
        "tight_mult": tight_mult,
        "rp_threshold": rp_threshold,
        "tq_threshold": tq_threshold,
        "sharpe": round(sharpe, 4),
        "cagr_pct": round(cagr * 100, 2),
        "mdd_pct": round(abs(mdd) * 100, 2),
        "trades": len(trades),
        "win_rate": round(len(wins) / len(trades) * 100, 1),
        "exposure_pct": round(exposure * 100, 1),
        "exit_trail": exit_counts.get("trail", 0),
        "exit_trend": exit_counts.get("trend", 0),
        "exit_and_gate": exit_counts.get("and_gate", 0),
        "exit_tight_trail": exit_counts.get("tight_trail", 0),
        "tighten_count": n_tighten,
        "survived": n_survived,
        "triggered": n_triggered,
        "survived_winners": survived_winners,
        "survived_losers": survived_losers,
        "triggered_winners": triggered_winners,
        "triggered_losers": triggered_losers,
        "_tighten_events": tighten_events,
        "_trades": trades,
    }


def winner_preservation_analysis(
    baseline_result: dict,
    exp22_result: dict,
    tighten_results: list[dict],
) -> None:
    """Match trades by entry_bar to check if exp22's false-positive winners survive."""
    print("\n" + "=" * 80)
    print("WINNER PRESERVATION ANALYSIS")
    print("  Trades killed by exp22 (binary exit) that were winners:")
    print("  Do they survive under trail tightening?")
    print("=" * 80)

    # Find exp22 AND-gate exits that were winners
    exp22_trades = exp22_result["_trades"]
    and_gate_winners = [
        t for t in exp22_trades
        if t["exit_reason"] == "and_gate" and t["win"]
    ]

    if not and_gate_winners:
        print("  No AND-gate exits on winners in exp22 — nothing to preserve.")
        return

    print(f"  exp22 AND-gate exits on WINNERS: {len(and_gate_winners)}")
    for t in and_gate_winners:
        print(f"    entry_bar={t['entry_bar']}, exit_bar={t['exit_bar']}, "
              f"net_ret={t['net_ret']*100:+.2f}%")

    # For each tighten config, find matching trades by entry_bar
    winner_entry_bars = {t["entry_bar"] for t in and_gate_winners}

    for tr in tighten_results:
        config = tr["config"]
        matching = [t for t in tr["_trades"] if t["entry_bar"] in winner_entry_bars]
        if not matching:
            print(f"\n  {config}: no matching trades found (entry shifted)")
            continue

        survived = [t for t in matching if t["exit_reason"] != "tight_trail"]
        still_win = [t for t in matching if t["win"]]
        print(f"\n  {config}:")
        for m in matching:
            status = "SURVIVED" if m["exit_reason"] != "tight_trail" else "TRIGGERED"
            outcome = "WIN" if m["win"] else "LOSS"
            print(f"    entry={m['entry_bar']}: {status} ({m['exit_reason']}), "
                  f"{outcome} net_ret={m['net_ret']*100:+.2f}%, "
                  f"bars_held={m['bars_held']}")
        print(f"    → {len(survived)}/{len(matching)} survived, "
              f"{len(still_win)}/{len(matching)} still winners")


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("EXP 29: AND-Gate Trail Tightener")
    print(f"  AND gate: rp < {RP_THRESHOLD} AND tq < {TQ_THRESHOLD} (exp22 optimum)")
    print(f"  Sweep A: tight_mult in [1.0, 1.5, 2.0, 2.5] (fixed rp/tq)")
    print(f"  Sweep B: tq in [-0.20, -0.10, 0.00, 0.10] (fixed tight_mult=1.5)")
    print(f"  + baseline + exp22 reproduction = 9 runs")
    print(f"  trail_mult: {TRAIL_MULT}, cost: {COST_BPS} bps RT")
    print("=" * 80)

    h4, d1 = load_data()
    feat = compute_features(h4, d1)

    warmup_bar = SLOW_PERIOD
    print(f"Warmup bar: {warmup_bar}")

    results: list[dict] = []
    tighten_results: list[dict] = []
    run_num = 1

    # ── 1. Baseline ───────────────────────────────────────────────────
    print(f"\n[{run_num}/9] Baseline (no AND gate)...")
    r_baseline = run_backtest(feat, warmup_bar)
    results.append(r_baseline)
    print(f"  Sharpe={r_baseline['sharpe']}, CAGR={r_baseline['cagr_pct']}%, "
          f"MDD={r_baseline['mdd_pct']}%, trades={r_baseline['trades']}")
    run_num += 1

    # ── 2. Exp22 reproduction (binary exit) ───────────────────────────
    print(f"\n[{run_num}/9] Exp22 reproduction (binary exit rp={RP_THRESHOLD}, tq={TQ_THRESHOLD})...")
    r_exp22 = run_backtest(feat, warmup_bar, binary_exit=True)
    results.append(r_exp22)
    print(f"  Sharpe={r_exp22['sharpe']}, CAGR={r_exp22['cagr_pct']}%, "
          f"MDD={r_exp22['mdd_pct']}%, trades={r_exp22['trades']}, "
          f"and_exits={r_exp22['exit_and_gate']}")
    run_num += 1

    # ── 3. Sweep A: vary tight_mult (fixed rp=0.20, tq=-0.10) ────────
    seen_configs: set[str] = set()
    for tm in [1.0, 1.5, 2.0, 2.5]:
        key = f"tm={tm}_tq={TQ_THRESHOLD}"
        if key in seen_configs:
            continue
        seen_configs.add(key)

        print(f"\n[{run_num}/9] Trail tighten tight_mult={tm}, "
              f"rp={RP_THRESHOLD}, tq={TQ_THRESHOLD}...")
        r = run_backtest(feat, warmup_bar, tight_mult=tm)
        results.append(r)
        tighten_results.append(r)
        print(f"  Sharpe={r['sharpe']}, CAGR={r['cagr_pct']}%, "
              f"MDD={r['mdd_pct']}%, trades={r['trades']}, "
              f"tightened={r['tighten_count']}, "
              f"survived={r['survived']}, triggered={r['triggered']}")
        run_num += 1

    # ── 4. Sweep B: vary tq (fixed tight_mult=1.5, rp=0.20) ─────────
    for tq in [-0.20, -0.10, 0.00, 0.10]:
        key = f"tm=1.5_tq={tq}"
        if key in seen_configs:
            continue
        seen_configs.add(key)

        print(f"\n[{run_num}/9] Trail tighten tight_mult=1.5, "
              f"rp={RP_THRESHOLD}, tq={tq}...")
        r = run_backtest(feat, warmup_bar, tight_mult=1.5, tq_threshold=tq)
        results.append(r)
        tighten_results.append(r)
        print(f"  Sharpe={r['sharpe']}, CAGR={r['cagr_pct']}%, "
              f"MDD={r['mdd_pct']}%, trades={r['trades']}, "
              f"tightened={r['tighten_count']}, "
              f"survived={r['survived']}, triggered={r['triggered']}")
        run_num += 1

    # ── Results table ─────────────────────────────────────────────────
    clean = [{k: v for k, v in r.items() if not k.startswith("_")} for r in results]
    df = pd.DataFrame(clean)

    base_sharpe = df.iloc[0]["sharpe"]
    base_mdd = df.iloc[0]["mdd_pct"]
    df["d_sharpe"] = df["sharpe"] - base_sharpe
    df["d_mdd"] = df["mdd_pct"] - base_mdd  # negative = improvement

    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)
    print(df.to_string(index=False))

    out_path = RESULTS_DIR / "exp29_results.csv"
    df.to_csv(out_path, index=False)
    print(f"\n-> Saved to {out_path}")

    # ── Tightening event analysis ─────────────────────────────────────
    print("\n" + "=" * 80)
    print("TIGHTENING EVENT ANALYSIS")
    print("  For each config: events, survival rate, winner/loser breakdown")
    print("=" * 80)
    for r in results:
        if r["tighten_count"] == 0:
            continue
        n_t = r["tighten_count"]
        n_s = r["survived"]
        n_tr = r["triggered"]
        pct_s = n_s / n_t * 100 if n_t > 0 else 0
        print(f"\n  {r['config']}:")
        print(f"    Tightened: {n_t}")
        print(f"    Survived (exited by normal trail/trend): {n_s} ({pct_s:.0f}%)")
        print(f"      → winners: {r['survived_winners']}, losers: {r['survived_losers']}")
        print(f"    Triggered (hit tight trail): {n_tr} ({100-pct_s:.0f}%)")
        print(f"      → winners: {r['triggered_winners']}, losers: {r['triggered_losers']}")

    # ── Winner preservation analysis ──────────────────────────────────
    winner_preservation_analysis(r_baseline, r_exp22, tighten_results)

    # ── d_Sharpe vs tight_mult (monotonic or inverted-U?) ─────────────
    print("\n" + "=" * 80)
    print("d_SHARPE vs tight_mult (Sweep A: fixed rp=0.20, tq=-0.10)")
    print("  Monotonic → binary exit optimal. Inverted-U → graduated response wins.")
    print("=" * 80)
    sweep_a = df[
        (df["config"].str.startswith("tight="))
        & (df["tq_threshold"] == TQ_THRESHOLD)
    ].sort_values("tight_mult")
    for _, row in sweep_a.iterrows():
        bar = "█" * max(0, int((row["d_sharpe"] + 0.1) * 100))
        print(f"  tight_mult={row['tight_mult']:.1f}  d_sharpe={row['d_sharpe']:+.4f}  "
              f"d_mdd={row['d_mdd']:+.2f}  {bar}")

    # Also show exp22 for comparison
    exp22_row = df[df["config"].str.startswith("exp22_")]
    if not exp22_row.empty:
        row = exp22_row.iloc[0]
        print(f"  exp22 (binary)  d_sharpe={row['d_sharpe']:+.4f}  "
              f"d_mdd={row['d_mdd']:+.2f}")

    # ── d_Sharpe vs tq_threshold (Sweep B: fixed tight_mult=1.5) ─────
    print("\n" + "=" * 80)
    print("d_SHARPE vs tq_threshold (Sweep B: fixed tight_mult=1.5, rp=0.20)")
    print("=" * 80)
    sweep_b = df[
        (df["tight_mult"] == 1.5)
    ].sort_values("tq_threshold")
    for _, row in sweep_b.iterrows():
        bar = "█" * max(0, int((row["d_sharpe"] + 0.1) * 100))
        print(f"  tq={row['tq_threshold']:+.2f}  d_sharpe={row['d_sharpe']:+.4f}  "
              f"d_mdd={row['d_mdd']:+.2f}  tightened={row['tighten_count']}  {bar}")

    # ── Verdict ───────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("VERDICT")
    print("=" * 80)

    tighten_rows = df[df["config"].str.startswith("tight=")]
    exp22_ds = exp22_row.iloc[0]["d_sharpe"] if not exp22_row.empty else 0.0
    exp22_dm = exp22_row.iloc[0]["d_mdd"] if not exp22_row.empty else 0.0

    improvements = tighten_rows[(tighten_rows["d_sharpe"] > 0) & (tighten_rows["d_mdd"] < 0)]

    if not improvements.empty:
        best = improvements.loc[improvements["d_sharpe"].idxmax()]
        beats_exp22_sharpe = best["d_sharpe"] > exp22_ds
        beats_exp22_mdd = best["d_mdd"] < exp22_dm

        print(f"PASS: {best['config']} improves both Sharpe ({best['d_sharpe']:+.4f}) "
              f"and MDD ({best['d_mdd']:+.2f} pp)")
        print(f"  Sharpe {best['sharpe']}, CAGR {best['cagr_pct']}%, "
              f"MDD {best['mdd_pct']}%, trades {int(best['trades'])}")
        print(f"  Tightened: {int(best['tighten_count'])}, "
              f"survived: {int(best['survived'])}, triggered: {int(best['triggered'])}")
        print(f"\n  vs exp22 (binary exit):")
        print(f"    exp22:  d_sharpe={exp22_ds:+.4f}, d_mdd={exp22_dm:+.2f}")
        print(f"    best:   d_sharpe={best['d_sharpe']:+.4f}, d_mdd={best['d_mdd']:+.2f}")
        print(f"    Trail tighten {'BETTER' if beats_exp22_sharpe else 'WORSE'} on Sharpe, "
              f"{'BETTER' if beats_exp22_mdd else 'WORSE'} on MDD")

        # Recovery rate
        if best["tighten_count"] > 0:
            recovery_pct = best["survived"] / best["tighten_count"] * 100
            print(f"\n  Recovery rate: {int(best['survived'])}/{int(best['tighten_count'])} "
                  f"= {recovery_pct:.0f}%")
            if recovery_pct > 30:
                print("    → >30% recovery confirms graduated response hypothesis")
            else:
                print("    → <30% recovery — binary exit may be equivalent")
    else:
        # Check if any improve at least one metric
        sharpe_up = tighten_rows[tighten_rows["d_sharpe"] > 0]
        mdd_down = tighten_rows[tighten_rows["d_mdd"] < 0]
        if not sharpe_up.empty or not mdd_down.empty:
            best_s = sharpe_up.loc[sharpe_up["d_sharpe"].idxmax()] if not sharpe_up.empty else None
            best_m = mdd_down.loc[mdd_down["d_mdd"].idxmin()] if not mdd_down.empty else None
            print("MIXED: No config improves BOTH Sharpe and MDD vs baseline.")
            if best_s is not None:
                print(f"  Best Sharpe: {best_s['config']} d_sharpe={best_s['d_sharpe']:+.4f}, "
                      f"d_mdd={best_s['d_mdd']:+.2f}")
            if best_m is not None:
                print(f"  Best MDD:    {best_m['config']} d_sharpe={best_m['d_sharpe']:+.4f}, "
                      f"d_mdd={best_m['d_mdd']:+.2f}")
        else:
            print("FAIL: No trail-tightening config improves Sharpe or MDD over baseline.")

        print(f"\n  exp22 (binary exit): d_sharpe={exp22_ds:+.4f}, d_mdd={exp22_dm:+.2f}")
        if exp22_ds > 0 and exp22_dm < 0:
            print("  Binary exit still beats baseline — graduated response adds no value.")
        else:
            print("  Neither approach improves on baseline.")

    # ── Exit reason breakdown ─────────────────────────────────────────
    print("\n" + "-" * 60)
    print("Exit reason breakdown:")
    for _, row in df.iterrows():
        total_exits = (
            row["exit_trail"] + row["exit_trend"]
            + row["exit_and_gate"] + row["exit_tight_trail"]
        )
        if total_exits == 0:
            continue
        parts = [f"trail={int(row['exit_trail'])}"]
        parts.append(f"trend={int(row['exit_trend'])}")
        if row["exit_and_gate"] > 0:
            parts.append(f"and_gate={int(row['exit_and_gate'])}")
        if row["exit_tight_trail"] > 0:
            parts.append(f"tight_trail={int(row['exit_tight_trail'])}")
        print(f"  {row['config']:45s}  {', '.join(parts)}")


if __name__ == "__main__":
    main()
