#!/usr/bin/env python3
"""Trade-level paired analysis: V10 vs V11.

Matches trades by entry_ts (exact match first, then ±1 bar tolerance),
computes per-trade deltas, and decomposes into exit-effect vs size-effect.

Outputs:
  matched_trades_<scenario>.csv
  match_summary_<scenario>.json
"""

import csv
import json
import math
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

OUTDIR = Path(__file__).resolve().parent
REPORTDIR = OUTDIR.parent / "out_v10_full_validation_stepwise" / "reports"
SCENARIOS = ["harsh", "base"]
# 1 H4 bar = 4 hours = 14_400_000 ms; tolerance = 1 bar
TOLERANCE_MS = 14_400_000
TOLERANCE_H = TOLERANCE_MS / 3_600_000


# ── helpers ────────────────────────────────────────────────────────────────

def _iso_to_ms(s: str) -> int:
    dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    return int(dt.timestamp() * 1000)


def _load_trades(path: Path) -> list[dict]:
    with open(path) as f:
        rows = list(csv.DictReader(f))
    # Convert numeric fields
    for r in rows:
        for k in ["entry_price", "exit_price", "qty", "notional",
                   "gross_pnl", "net_pnl", "fees_total", "return_pct",
                   "days_held", "mfe_pct", "mae_pct"]:
            r[k] = float(r[k])
        for k in ["bars_held", "n_buy_fills", "n_sell_fills"]:
            r[k] = int(r[k])
        r["_entry_ms"] = _iso_to_ms(r["entry_ts"])
        r["_exit_ms"] = _iso_to_ms(r["exit_ts"])
    return rows


def _pct(n: float, d: float) -> str:
    if d == 0:
        return "N/A"
    return f"{n / d * 100:.1f}%"


# ── matching ───────────────────────────────────────────────────────────────

def match_trades(v10: list[dict], v11: list[dict]):
    """Match V10 ↔ V11 trades by entry_ts.

    Pass 1: exact entry_ts match.
    Pass 2: ±1 bar (4h) tolerance for remaining unmatched.
    """
    matched = []
    v10_only = []
    v11_only = []

    v11_by_entry = {}
    for t in v11:
        v11_by_entry[t["entry_ts"]] = t

    v11_used = set()

    # Pass 1: exact match on entry_ts
    unmatched_v10 = []
    for t10 in v10:
        key = t10["entry_ts"]
        if key in v11_by_entry and key not in v11_used:
            matched.append((t10, v11_by_entry[key]))
            v11_used.add(key)
        else:
            unmatched_v10.append(t10)

    # Pass 2: tolerance match for remaining
    remaining_v11 = [t for t in v11 if t["entry_ts"] not in v11_used]
    still_unmatched_v10 = []

    for t10 in unmatched_v10:
        best = None
        best_delta = float("inf")
        for t11 in remaining_v11:
            if t11["entry_ts"] in v11_used:
                continue
            delta = abs(t10["_entry_ms"] - t11["_entry_ms"])
            if delta <= TOLERANCE_MS and delta < best_delta:
                best = t11
                best_delta = delta
        if best is not None:
            matched.append((t10, best))
            v11_used.add(best["entry_ts"])
        else:
            still_unmatched_v10.append(t10)

    v10_only = still_unmatched_v10
    v11_only = [t for t in v11 if t["entry_ts"] not in v11_used]

    return matched, v10_only, v11_only


# ── decomposition ──────────────────────────────────────────────────────────

def compute_pair_deltas(t10: dict, t11: dict) -> dict:
    """Compute deltas and decomposition for a matched pair.

    Decomposition (additive, exact for proportional changes):

    Total delta = net_pnl_v11 - net_pnl_v10

    Exit effect (hold V10 size, apply V11 exit):
      = v10_qty × (v11_exit_price - v10_exit_price)
      Captures: different trailing stop trigger, different exit timing

    Size effect (hold V10 exit, apply V11 size):
      = (v11_qty - v10_qty) × (v10_exit_price - v10_entry_price)
      Captures: different position sizing from aggression/cap

    Fee effect:
      = -(v11_fees - v10_fees)
      Captures: cost difference from different notional

    Interaction (residual):
      = total - exit_effect - size_effect - fee_effect
      Captures: cross-term (size × exit price change)
    """
    d = {}

    # Basic deltas
    d["delta_net_pnl"] = t11["net_pnl"] - t10["net_pnl"]
    d["delta_gross_pnl"] = t11["gross_pnl"] - t10["gross_pnl"]
    d["delta_return_pct"] = t11["return_pct"] - t10["return_pct"]
    d["delta_fees"] = t11["fees_total"] - t10["fees_total"]
    d["delta_days_held"] = t11["days_held"] - t10["days_held"]
    d["delta_bars_held"] = t11["bars_held"] - t10["bars_held"]

    d["delta_exit_price"] = t11["exit_price"] - t10["exit_price"]
    d["delta_exit_ts"] = t11["exit_ts"]  # store both for reference

    d["size_ratio"] = t11["notional"] / t10["notional"] if t10["notional"] > 0 else 1.0
    d["delta_notional"] = t11["notional"] - t10["notional"]

    d["delta_mfe_pct"] = t11["mfe_pct"] - t10["mfe_pct"]
    d["delta_mae_pct"] = t11["mae_pct"] - t10["mae_pct"]

    d["same_exit_reason"] = t10["exit_reason"] == t11["exit_reason"]
    d["same_entry_regime"] = t10["entry_regime"] == t11["entry_regime"]

    # ── Decomposition ──
    # Exit effect: V10 size × (V11 exit price − V10 exit price)
    exit_effect = t10["qty"] * (t11["exit_price"] - t10["exit_price"])
    d["exit_effect"] = round(exit_effect, 2)

    # Size effect: (V11 qty − V10 qty) × (V10 exit price − V10 entry price)
    # Uses V10's return per unit to isolate pure sizing contribution
    size_effect = (t11["qty"] - t10["qty"]) * (t10["exit_price"] - t10["entry_price"])
    d["size_effect"] = round(size_effect, 2)

    # Fee effect: negative because higher fees reduce PnL
    fee_effect = -(t11["fees_total"] - t10["fees_total"])
    d["fee_effect"] = round(fee_effect, 2)

    # Interaction: residual
    d["interaction"] = round(d["delta_net_pnl"] - exit_effect - size_effect - fee_effect, 2)

    return d


# ── statistics ─────────────────────────────────────────────────────────────

def compute_stats(values: list[float]) -> dict:
    if not values:
        return {"n": 0}
    arr = np.array(values)
    return {
        "n": len(arr),
        "mean": round(float(arr.mean()), 4),
        "median": round(float(np.median(arr)), 4),
        "std": round(float(arr.std(ddof=1)), 4) if len(arr) > 1 else 0.0,
        "p10": round(float(np.percentile(arr, 10)), 4),
        "p90": round(float(np.percentile(arr, 90)), 4),
        "min": round(float(arr.min()), 4),
        "max": round(float(arr.max()), 4),
        "sum": round(float(arr.sum()), 2),
    }


# ── CSV export ─────────────────────────────────────────────────────────────

MATCHED_COLUMNS = [
    # V10 trade
    "v10_trade_id", "v10_entry_ts", "v10_exit_ts",
    "v10_entry_price", "v10_exit_price", "v10_qty", "v10_notional",
    "v10_net_pnl", "v10_gross_pnl", "v10_fees_total", "v10_return_pct",
    "v10_bars_held", "v10_days_held", "v10_mfe_pct", "v10_mae_pct",
    "v10_entry_reason", "v10_exit_reason",
    "v10_entry_regime", "v10_exit_regime", "v10_holding_regime_mode", "v10_worst_regime",
    "v10_n_buy_fills",
    # V11 trade
    "v11_trade_id", "v11_entry_ts", "v11_exit_ts",
    "v11_entry_price", "v11_exit_price", "v11_qty", "v11_notional",
    "v11_net_pnl", "v11_gross_pnl", "v11_fees_total", "v11_return_pct",
    "v11_bars_held", "v11_days_held", "v11_mfe_pct", "v11_mae_pct",
    "v11_entry_reason", "v11_exit_reason",
    "v11_entry_regime", "v11_exit_regime", "v11_holding_regime_mode", "v11_worst_regime",
    "v11_n_buy_fills",
    # Deltas
    "delta_net_pnl", "delta_gross_pnl", "delta_return_pct", "delta_fees",
    "delta_days_held", "delta_bars_held", "delta_exit_price",
    "size_ratio", "delta_notional",
    "delta_mfe_pct", "delta_mae_pct",
    "same_exit_reason", "same_entry_regime",
    # Decomposition
    "exit_effect", "size_effect", "fee_effect", "interaction",
]


def _make_matched_row(t10: dict, t11: dict, deltas: dict) -> dict:
    row = {}
    for k in ["trade_id", "entry_ts", "exit_ts", "entry_price", "exit_price",
              "qty", "notional", "net_pnl", "gross_pnl", "fees_total", "return_pct",
              "bars_held", "days_held", "mfe_pct", "mae_pct",
              "entry_reason", "exit_reason",
              "entry_regime", "exit_regime", "holding_regime_mode", "worst_regime",
              "n_buy_fills"]:
        row[f"v10_{k}"] = t10[k]
        row[f"v11_{k}"] = t11[k]
    for k, v in deltas.items():
        if k == "delta_exit_ts":
            continue  # skip complex field
        row[k] = v
    return row


def write_matched_csv(rows: list[dict], path: Path):
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=MATCHED_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


# ── main analysis ──────────────────────────────────────────────────────────

def analyze_scenario(scenario: str) -> dict:
    print(f"\n{'='*60}")
    print(f"  Scenario: {scenario}")
    print(f"{'='*60}")

    v10_path = OUTDIR / f"trades_v10_{scenario}.csv"
    v11_path = OUTDIR / f"trades_v11_{scenario}.csv"
    v10 = _load_trades(v10_path)
    v11 = _load_trades(v11_path)

    print(f"  V10: {len(v10)} trades, V11: {len(v11)} trades")

    # Match
    matched, v10_only, v11_only = match_trades(v10, v11)
    n_total = len(v10)
    match_rate = len(matched) / n_total if n_total > 0 else 0

    print(f"  Matched: {len(matched)} ({match_rate*100:.1f}%)")
    print(f"  V10-only: {len(v10_only)}, V11-only: {len(v11_only)}")

    # Compute deltas for matched pairs
    matched_rows = []
    deltas_list = []
    for t10, t11 in matched:
        d = compute_pair_deltas(t10, t11)
        deltas_list.append(d)
        matched_rows.append(_make_matched_row(t10, t11, d))

    # Write matched CSV
    csv_path = OUTDIR / f"matched_trades_{scenario}.csv"
    write_matched_csv(matched_rows, csv_path)
    print(f"  Written: {csv_path.name}")

    # ── Statistics ──
    delta_pnls = [d["delta_net_pnl"] for d in deltas_list]
    delta_returns = [d["delta_return_pct"] for d in deltas_list]
    delta_days = [d["delta_days_held"] for d in deltas_list]
    size_ratios = [d["size_ratio"] for d in deltas_list]
    exit_effects = [d["exit_effect"] for d in deltas_list]
    size_effects = [d["size_effect"] for d in deltas_list]
    fee_effects = [d["fee_effect"] for d in deltas_list]
    interactions = [d["interaction"] for d in deltas_list]

    # P(delta > 0)
    n_positive = sum(1 for x in delta_pnls if x > 0)
    n_negative = sum(1 for x in delta_pnls if x < 0)
    n_zero = sum(1 for x in delta_pnls if x == 0)
    p_positive = n_positive / len(delta_pnls) if delta_pnls else 0

    # Same exit reason rate
    same_exit_rate = sum(1 for d in deltas_list if d["same_exit_reason"]) / len(deltas_list) if deltas_list else 0

    # Exit reason transition matrix
    exit_transitions = defaultdict(int)
    for t10, t11 in matched:
        key = f"{t10['exit_reason']} → {t11['exit_reason']}"
        exit_transitions[key] += 1

    # Top 10 contributors (by abs delta_net_pnl)
    indexed_deltas = [(i, d, matched[i][0], matched[i][1]) for i, d in enumerate(deltas_list)]
    top_positive = sorted(indexed_deltas, key=lambda x: x[1]["delta_net_pnl"], reverse=True)[:10]
    top_negative = sorted(indexed_deltas, key=lambda x: x[1]["delta_net_pnl"])[:10]

    # Regime breakdown: delta_net_pnl by entry_regime
    regime_deltas = defaultdict(list)
    for (t10, t11), d in zip(matched, deltas_list):
        regime_deltas[t10["entry_regime"]].append(d["delta_net_pnl"])

    regime_summary = {}
    for regime, vals in sorted(regime_deltas.items()):
        regime_summary[regime] = {
            "n": len(vals),
            "sum_delta": round(sum(vals), 2),
            "mean_delta": round(sum(vals) / len(vals), 2) if vals else 0,
            "n_positive": sum(1 for v in vals if v > 0),
            "n_negative": sum(1 for v in vals if v < 0),
        }

    # Decomposition totals
    total_delta = sum(delta_pnls)
    total_exit = sum(exit_effects)
    total_size = sum(size_effects)
    total_fee = sum(fee_effects)
    total_interaction = sum(interactions)

    # V10-only / V11-only PnL
    v10_only_pnl = sum(t["net_pnl"] for t in v10_only)
    v11_only_pnl = sum(t["net_pnl"] for t in v11_only)

    # ── Print summary ──
    print(f"\n  Match rate: {match_rate*100:.1f}%")
    print(f"  P(Δ pnl > 0): {p_positive*100:.1f}% ({n_positive}/{len(delta_pnls)})")
    print(f"  Same exit reason: {same_exit_rate*100:.1f}%")
    print(f"\n  Total delta (matched): ${total_delta:+.2f}")
    print(f"    Exit effect:    ${total_exit:+.2f} ({total_exit/total_delta*100:+.1f}%)" if total_delta != 0 else f"    Exit effect:    ${total_exit:+.2f}")
    print(f"    Size effect:    ${total_size:+.2f} ({total_size/total_delta*100:+.1f}%)" if total_delta != 0 else f"    Size effect:    ${total_size:+.2f}")
    print(f"    Fee effect:     ${total_fee:+.2f} ({total_fee/total_delta*100:+.1f}%)" if total_delta != 0 else f"    Fee effect:     ${total_fee:+.2f}")
    print(f"    Interaction:    ${total_interaction:+.2f} ({total_interaction/total_delta*100:+.1f}%)" if total_delta != 0 else f"    Interaction:    ${total_interaction:+.2f}")
    print(f"\n  V10-only PnL: ${v10_only_pnl:+.2f} ({len(v10_only)} trades)")
    print(f"  V11-only PnL: ${v11_only_pnl:+.2f} ({len(v11_only)} trades)")

    # ── Build summary JSON ──
    summary = {
        "scenario": scenario,
        "v10_trades": len(v10),
        "v11_trades": len(v11),
        "matched": len(matched),
        "v10_only": len(v10_only),
        "v11_only": len(v11_only),
        "match_rate": round(match_rate, 4),
        "match_pass": match_rate >= 0.80,
        "p_delta_positive": round(p_positive, 4),
        "n_positive": n_positive,
        "n_negative": n_negative,
        "n_zero": n_zero,
        "same_exit_reason_rate": round(same_exit_rate, 4),
        "delta_net_pnl": compute_stats(delta_pnls),
        "delta_return_pct": compute_stats(delta_returns),
        "delta_days_held": compute_stats(delta_days),
        "size_ratio": compute_stats(size_ratios),
        "decomposition": {
            "total_delta": round(total_delta, 2),
            "exit_effect": round(total_exit, 2),
            "size_effect": round(total_size, 2),
            "fee_effect": round(total_fee, 2),
            "interaction": round(total_interaction, 2),
            "exit_pct_of_total": round(total_exit / total_delta * 100, 1) if total_delta != 0 else None,
            "size_pct_of_total": round(total_size / total_delta * 100, 1) if total_delta != 0 else None,
            "fee_pct_of_total": round(total_fee / total_delta * 100, 1) if total_delta != 0 else None,
            "interaction_pct_of_total": round(total_interaction / total_delta * 100, 1) if total_delta != 0 else None,
        },
        "exit_transitions": dict(sorted(exit_transitions.items(), key=lambda x: -x[1])),
        "regime_breakdown": regime_summary,
        "unmatched": {
            "v10_only_pnl": round(v10_only_pnl, 2),
            "v11_only_pnl": round(v11_only_pnl, 2),
            "v10_only_trades": [
                {"trade_id": t["trade_id"], "entry_ts": t["entry_ts"],
                 "exit_reason": t["exit_reason"], "net_pnl": t["net_pnl"]}
                for t in v10_only
            ],
            "v11_only_trades": [
                {"trade_id": t["trade_id"], "entry_ts": t["entry_ts"],
                 "exit_reason": t["exit_reason"], "net_pnl": t["net_pnl"]}
                for t in v11_only
            ],
        },
        "top10_positive": [
            {"v10_id": tp[2]["trade_id"], "v11_id": tp[3]["trade_id"],
             "entry_ts": tp[2]["entry_ts"], "delta_net_pnl": round(tp[1]["delta_net_pnl"], 2),
             "exit_effect": tp[1]["exit_effect"], "size_effect": tp[1]["size_effect"],
             "v10_exit": tp[2]["exit_reason"], "v11_exit": tp[3]["exit_reason"],
             "entry_regime": tp[2]["entry_regime"]}
            for tp in top_positive
        ],
        "top10_negative": [
            {"v10_id": tn[2]["trade_id"], "v11_id": tn[3]["trade_id"],
             "entry_ts": tn[2]["entry_ts"], "delta_net_pnl": round(tn[1]["delta_net_pnl"], 2),
             "exit_effect": tn[1]["exit_effect"], "size_effect": tn[1]["size_effect"],
             "v10_exit": tn[2]["exit_reason"], "v11_exit": tn[3]["exit_reason"],
             "entry_regime": tn[2]["entry_regime"]}
            for tn in top_negative
        ],
    }

    # Write JSON
    json_path = OUTDIR / f"match_summary_{scenario}.json"
    with open(json_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"  Written: {json_path.name}")

    return summary


# ── main ───────────────────────────────────────────────────────────────────

def main():
    results = {}
    for scenario in SCENARIOS:
        results[scenario] = analyze_scenario(scenario)

    # Print cross-scenario summary
    print(f"\n{'='*60}")
    print("  CROSS-SCENARIO SUMMARY")
    print(f"{'='*60}")
    for sc, s in results.items():
        d = s["decomposition"]
        print(f"\n  {sc}:")
        print(f"    Match rate:     {s['match_rate']*100:.1f}% ({'PASS' if s['match_pass'] else 'FAIL'})")
        print(f"    P(Δ>0):         {s['p_delta_positive']*100:.1f}%")
        print(f"    Total Δ PnL:    ${d['total_delta']:+.2f}")
        print(f"    Exit effect:    ${d['exit_effect']:+.2f} ({d['exit_pct_of_total']:+.1f}%)")
        print(f"    Size effect:    ${d['size_effect']:+.2f} ({d['size_pct_of_total']:+.1f}%)")

    print("\nDone.")


if __name__ == "__main__":
    main()
