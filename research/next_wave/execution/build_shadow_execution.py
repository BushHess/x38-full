#!/usr/bin/env python3
"""E1.2 — Shadow execution analyzer for X0 default.

Computes counterfactual TWAP-1h and VWAP-1h fills for every X0 entry and exit,
then produces paired fill comparisons per the E1.1 frozen spec.

Source of truth:
  - X0 trades: research/next_wave/diagnostics/artifacts/trades_X0_base.csv
  - M15 bars:  data/bars_btcusdt_2017_now_15m.csv
  - Spec:      research/next_wave/execution/E1_1_EXECUTION_SPEC.md

Output:
  - research/next_wave/execution/artifacts/shadow_fills.csv
  - research/next_wave/execution/artifacts/shadow_summary.json
  - research/next_wave/execution/artifacts/shadow_metadata.json
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent.parent  # btc-spot-dev/
DIAG_ARTIFACTS = ROOT / "research" / "next_wave" / "diagnostics" / "artifacts"
EXEC_ARTIFACTS = Path(__file__).resolve().parent / "artifacts"

M15_INTERVAL_MS = 900_000  # 15 minutes
TWAP_BARS = 4              # 1-hour window = 4 x 15m
TWAP_WINDOW_MS = TWAP_BARS * M15_INTERVAL_MS  # 3,600,000

# Base scenario cost parameters (from v10/core/types.py)
BASE_SPREAD_BPS = 5.0
BASE_SLIPPAGE_BPS = 3.0
BASE_TAKER_FEE_PCT = 0.10  # percent


def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load X0 trades and M15 bars."""
    trades = pd.read_csv(DIAG_ARTIFACTS / "trades_X0_base.csv")
    m15 = pd.read_csv(ROOT / "data/bars_btcusdt_2017_now_15m.csv")
    return trades, m15


def build_m15_index(m15: pd.DataFrame) -> dict[int, dict]:
    """Build open_time -> row dict for O(1) M15 bar lookup."""
    idx: dict[int, dict] = {}
    for _, row in m15.iterrows():
        idx[int(row["open_time"])] = {
            "open": float(row["open"]),
            "high": float(row["high"]),
            "low": float(row["low"]),
            "close": float(row["close"]),
            "volume": float(row["volume"]),
        }
    return idx


def get_twap_window(fill_ts_ms: int, m15_idx: dict[int, dict]) -> list[dict]:
    """Return the 4 M15 bars starting at fill_ts_ms.

    fill_ts_ms is the H4 bar open time where the baseline fill occurs.
    The TWAP window covers [fill_ts_ms, fill_ts_ms + 45min].
    """
    bars = []
    for i in range(TWAP_BARS):
        ot = fill_ts_ms + i * M15_INTERVAL_MS
        if ot in m15_idx:
            bars.append(m15_idx[ot])
    return bars


def compute_twap(bars: list[dict]) -> float | None:
    """TWAP = simple mean of M15 bar closes."""
    if not bars:
        return None
    return float(np.mean([b["close"] for b in bars]))


def compute_vwap(bars: list[dict]) -> float | None:
    """VWAP = volume-weighted mean of M15 typical prices.

    typical_price = (high + low + close) / 3
    Bars with zero volume are excluded.
    """
    if not bars:
        return None
    total_vol = 0.0
    total_pv = 0.0
    for b in bars:
        v = b["volume"]
        if v > 0:
            tp = (b["high"] + b["low"] + b["close"]) / 3.0
            total_pv += tp * v
            total_vol += v
    if total_vol <= 0:
        # All bars zero volume: fall back to TWAP per spec
        return compute_twap(bars)
    return total_pv / total_vol


def compute_shadow_fills(
    trades: pd.DataFrame,
    m15_idx: dict[int, dict],
) -> pd.DataFrame:
    """Compute shadow TWAP/VWAP fills for all X0 trades."""

    rows = []
    for _, t in trades.iterrows():
        trade_id = int(t["trade_id"])
        entry_ts = int(t["entry_ts_ms"])
        exit_ts = int(t["exit_ts_ms"])
        baseline_entry_mid = float(t["entry_mid_price"])
        baseline_exit_mid = float(t["exit_mid_price"])
        baseline_entry_fill = float(t["entry_fill_price"])
        baseline_exit_fill = float(t["exit_fill_price"])
        qty = float(t["qty"])
        baseline_pnl = float(t["pnl_usd"])
        baseline_net_ret = float(t["net_return_pct"])

        # Get M15 windows
        entry_bars = get_twap_window(entry_ts, m15_idx)
        exit_bars = get_twap_window(exit_ts, m15_idx)

        # Compute shadow fills
        entry_twap = compute_twap(entry_bars)
        entry_vwap = compute_vwap(entry_bars)
        exit_twap = compute_twap(exit_bars)
        exit_vwap = compute_vwap(exit_bars)

        # Fallback to baseline mid if missing (spec: flag but use baseline)
        entry_twap_flag = entry_twap is None
        exit_twap_flag = exit_twap is None
        if entry_twap is None:
            entry_twap = baseline_entry_mid
        if entry_vwap is None:
            entry_vwap = baseline_entry_mid
        if exit_twap is None:
            exit_twap = baseline_exit_mid
        if exit_vwap is None:
            exit_vwap = baseline_exit_mid

        # M15 bar counts (for quality reporting)
        entry_m15_count = len(entry_bars)
        exit_m15_count = len(exit_bars)

        # PRIMARY PATH: price-only delta vs baseline mid
        entry_delta_twap_bps = (entry_twap / baseline_entry_mid - 1) * 10000
        entry_delta_vwap_bps = (entry_vwap / baseline_entry_mid - 1) * 10000
        exit_delta_twap_bps = (exit_twap / baseline_exit_mid - 1) * 10000
        exit_delta_vwap_bps = (exit_vwap / baseline_exit_mid - 1) * 10000

        # combined_delta: positive = trade improved
        # BUY entry: negative entry_delta = better -> negate
        # SELL exit: positive exit_delta = better -> add
        combined_twap_bps = -entry_delta_twap_bps + exit_delta_twap_bps
        combined_vwap_bps = -entry_delta_vwap_bps + exit_delta_vwap_bps

        # SECONDARY PATH: scenario re-pricing
        # Shadow fill = shadow_price * (1 + slip) for BUY, * (1 - slip) for SELL
        slip_mult = BASE_SLIPPAGE_BPS / 10000
        fee_rate = BASE_TAKER_FEE_PCT / 100

        for cand_name, e_shadow, x_shadow in [
            ("twap", entry_twap, exit_twap),
            ("vwap", entry_vwap, exit_vwap),
        ]:
            shadow_entry_fill = e_shadow * (1 + slip_mult)
            shadow_exit_fill = x_shadow * (1 - slip_mult)
            shadow_entry_notional = qty * shadow_entry_fill
            shadow_entry_fee = shadow_entry_notional * fee_rate
            shadow_entry_cost = shadow_entry_notional + shadow_entry_fee
            shadow_exit_notional = qty * shadow_exit_fill
            shadow_exit_fee = shadow_exit_notional * fee_rate
            shadow_exit_proceeds = shadow_exit_notional - shadow_exit_fee
            shadow_pnl = shadow_exit_proceeds - shadow_entry_cost
            if cand_name == "twap":
                twap_shadow_pnl = shadow_pnl
                twap_shadow_entry_fill = shadow_entry_fill
                twap_shadow_exit_fill = shadow_exit_fill
            else:
                vwap_shadow_pnl = shadow_pnl
                vwap_shadow_entry_fill = shadow_entry_fill
                vwap_shadow_exit_fill = shadow_exit_fill

        twap_pnl_delta = twap_shadow_pnl - baseline_pnl
        vwap_pnl_delta = vwap_shadow_pnl - baseline_pnl

        # Entry notional for IS weighting
        entry_notional = qty * baseline_entry_mid

        rows.append({
            "trade_id": trade_id,
            "entry_ts_ms": entry_ts,
            "exit_ts_ms": exit_ts,
            "qty": qty,
            "entry_notional_usd": entry_notional,
            # Baseline
            "baseline_entry_mid": baseline_entry_mid,
            "baseline_exit_mid": baseline_exit_mid,
            "baseline_entry_fill": baseline_entry_fill,
            "baseline_exit_fill": baseline_exit_fill,
            "baseline_pnl_usd": baseline_pnl,
            "baseline_net_return_pct": baseline_net_ret,
            # TWAP shadow fills (raw price, no cost)
            "twap_entry_price": entry_twap,
            "twap_exit_price": exit_twap,
            # VWAP shadow fills (raw price, no cost)
            "vwap_entry_price": entry_vwap,
            "vwap_exit_price": exit_vwap,
            # Primary path: price-only deltas (bps)
            "twap_entry_delta_bps": entry_delta_twap_bps,
            "twap_exit_delta_bps": exit_delta_twap_bps,
            "twap_combined_delta_bps": combined_twap_bps,
            "vwap_entry_delta_bps": entry_delta_vwap_bps,
            "vwap_exit_delta_bps": exit_delta_vwap_bps,
            "vwap_combined_delta_bps": combined_vwap_bps,
            # Secondary path: scenario re-pricing
            "twap_shadow_entry_fill": twap_shadow_entry_fill,
            "twap_shadow_exit_fill": twap_shadow_exit_fill,
            "twap_shadow_pnl_usd": twap_shadow_pnl,
            "twap_pnl_delta_usd": twap_pnl_delta,
            "vwap_shadow_entry_fill": vwap_shadow_entry_fill,
            "vwap_shadow_exit_fill": vwap_shadow_exit_fill,
            "vwap_shadow_pnl_usd": vwap_shadow_pnl,
            "vwap_pnl_delta_usd": vwap_pnl_delta,
            # Quality flags
            "entry_m15_count": entry_m15_count,
            "exit_m15_count": exit_m15_count,
            "entry_fallback": entry_twap_flag,
            "exit_fallback": exit_twap_flag,
        })

    return pd.DataFrame(rows)


def compute_summary(sf: pd.DataFrame) -> dict:
    """Compute summary diagnostics per E1.1 spec (D1-D8)."""

    result = {}

    for cand in ["twap", "vwap"]:
        entry_col = f"{cand}_entry_delta_bps"
        exit_col = f"{cand}_exit_delta_bps"
        comb_col = f"{cand}_combined_delta_bps"
        pnl_delta_col = f"{cand}_pnl_delta_usd"

        entry_d = sf[entry_col]
        exit_d = sf[exit_col]
        comb_d = sf[comb_col]
        pnl_d = sf[pnl_delta_col]

        # D1: Implementation Shortfall (notional-weighted combined delta)
        notional = sf["entry_notional_usd"]
        total_is_bps = (comb_d * notional).sum() / notional.sum()
        total_is_usd = pnl_d.sum()

        # D2: Entry fill delta distribution
        entry_stats = {
            "mean": float(entry_d.mean()),
            "median": float(entry_d.median()),
            "std": float(entry_d.std()),
            "p5": float(entry_d.quantile(0.05)),
            "p25": float(entry_d.quantile(0.25)),
            "p75": float(entry_d.quantile(0.75)),
            "p95": float(entry_d.quantile(0.95)),
        }

        # D3: Exit fill delta distribution
        exit_stats = {
            "mean": float(exit_d.mean()),
            "median": float(exit_d.median()),
            "std": float(exit_d.std()),
            "p5": float(exit_d.quantile(0.05)),
            "p25": float(exit_d.quantile(0.25)),
            "p75": float(exit_d.quantile(0.75)),
            "p95": float(exit_d.quantile(0.95)),
        }

        # D4: Combined trade delta
        combined_stats = {
            "mean": float(comb_d.mean()),
            "median": float(comb_d.median()),
            "std": float(comb_d.std()),
            "p5": float(comb_d.quantile(0.05)),
            "p95": float(comb_d.quantile(0.95)),
        }

        # D5: Improved vs worsened
        improved = int((comb_d > 0.5).sum())
        worsened = int((comb_d < -0.5).sum())
        neutral = int(len(comb_d) - improved - worsened)
        frac_improved = improved / len(comb_d)
        mean_improved = float(comb_d[comb_d > 0.5].mean()) if improved > 0 else 0.0
        mean_worsened = float(comb_d[comb_d < -0.5].mean()) if worsened > 0 else 0.0

        # D6: Broad-based vs concentrated
        # By year
        sf_copy = sf.copy()
        sf_copy["year"] = pd.to_datetime(sf_copy["entry_ts_ms"], unit="ms").dt.year
        yearly = sf_copy.groupby("year")[comb_col].mean()
        years_positive = int((yearly > 0).sum())
        total_years = len(yearly)
        yearly_dict = {int(k): float(v) for k, v in yearly.items()}

        # Notional-delta correlation
        notional_corr = float(np.corrcoef(notional, comb_d)[0, 1])

        # Re-entry vs non-re-entry
        # Load re-entry flags from entry features
        ef = pd.read_csv(DIAG_ARTIFACTS / "entry_features_X0_base.csv")
        re_mask = ef["reentry_within_6_bars"].values.astype(bool)
        re_mean = float(comb_d[re_mask].mean()) if re_mask.sum() > 0 else 0.0
        nre_mean = float(comb_d[~re_mask].mean()) if (~re_mask).sum() > 0 else 0.0

        # D7: Secondary path summary
        secondary_total_pnl_delta = float(pnl_d.sum())
        secondary_mean_pnl_delta = float(pnl_d.mean())
        secondary_sign_consistent = (
            (total_is_bps > 0 and secondary_total_pnl_delta > 0)
            or (total_is_bps < 0 and secondary_total_pnl_delta < 0)
            or (abs(total_is_bps) < 0.1 and abs(secondary_total_pnl_delta) < 10)
        )

        # D8: Reference comparison (just report baseline PnL)
        baseline_total_pnl = float(sf["baseline_pnl_usd"].sum())

        # Max single-year contribution
        if len(yearly_dict) > 0:
            yearly_abs_sum = sum(abs(v) for v in yearly_dict.values())
            max_year_pct = (
                max(abs(v) for v in yearly_dict.values()) / yearly_abs_sum * 100
                if yearly_abs_sum > 0 else 0.0
            )
        else:
            max_year_pct = 0.0

        # GO/HOLD gate evaluation
        go_magnitude = abs(combined_stats["mean"]) > 1.0
        go_consistency = frac_improved > 0.55
        go_broad = years_positive >= 5
        go_symmetric = abs(entry_stats["mean"]) > 0.3 and abs(exit_stats["mean"]) > 0.3
        go_secondary = secondary_sign_consistent
        go_concentrated = abs(notional_corr) < 0.30

        go_all = all([
            go_magnitude, go_consistency, go_broad,
            go_symmetric, go_secondary, go_concentrated,
        ])

        result[cand] = {
            "D1_implementation_shortfall": {
                "total_is_bps": round(total_is_bps, 4),
                "total_is_usd": round(total_is_usd, 2),
            },
            "D2_entry_delta": entry_stats,
            "D3_exit_delta": exit_stats,
            "D4_combined_delta": combined_stats,
            "D5_improved_vs_worsened": {
                "improved": improved,
                "worsened": worsened,
                "neutral": neutral,
                "frac_improved": round(frac_improved, 4),
                "mean_improved_bps": round(mean_improved, 4),
                "mean_worsened_bps": round(mean_worsened, 4),
            },
            "D6_concentration": {
                "yearly_mean_delta_bps": yearly_dict,
                "years_positive": years_positive,
                "total_years": total_years,
                "max_single_year_pct": round(max_year_pct, 1),
                "notional_delta_correlation": round(notional_corr, 4),
                "reentry_mean_delta_bps": round(re_mean, 4),
                "nonreentry_mean_delta_bps": round(nre_mean, 4),
            },
            "D7_secondary_path": {
                "total_pnl_delta_usd": round(secondary_total_pnl_delta, 2),
                "mean_pnl_delta_usd": round(secondary_mean_pnl_delta, 2),
                "sign_consistent_with_primary": secondary_sign_consistent,
            },
            "D8_reference": {
                "baseline_total_pnl_usd": round(baseline_total_pnl, 2),
            },
            "GO_HOLD_gates": {
                "magnitude_gt_1bps": go_magnitude,
                "consistency_gt_55pct": go_consistency,
                "broad_5of7_years": go_broad,
                "symmetric_both_sides": go_symmetric,
                "secondary_confirms": go_secondary,
                "not_concentrated": go_concentrated,
                "verdict": "GO" if go_all else "HOLD",
            },
        }

    return result


def main():
    EXEC_ARTIFACTS.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("E1.2 -- Shadow Execution Analyzer for X0 Default")
    print("=" * 60)

    # Load data
    print("\n[1/4] Loading data...")
    trades, m15 = load_data()
    print(f"  X0 trades: {len(trades)}")
    print(f"  M15 bars: {len(m15)}")

    # Build M15 index
    print("\n[2/4] Building M15 index...")
    m15_idx = build_m15_index(m15)
    print(f"  Indexed {len(m15_idx)} M15 bars")

    # Compute shadow fills
    print("\n[3/4] Computing shadow fills...")
    sf = compute_shadow_fills(trades, m15_idx)
    print(f"  Shadow fills computed for {len(sf)} trades")

    # Quality checks
    fallback_entry = sf["entry_fallback"].sum()
    fallback_exit = sf["exit_fallback"].sum()
    print(f"  Entry fallbacks: {fallback_entry}")
    print(f"  Exit fallbacks: {fallback_exit}")
    print(f"  Entry M15 bar counts: min={sf['entry_m15_count'].min()}, "
          f"max={sf['entry_m15_count'].max()}")
    print(f"  Exit M15 bar counts: min={sf['exit_m15_count'].min()}, "
          f"max={sf['exit_m15_count'].max()}")

    # Compute summary
    print("\n[4/4] Computing diagnostics...")
    summary = compute_summary(sf)

    # Print key results
    for cand in ["twap", "vwap"]:
        s = summary[cand]
        print(f"\n  --- {cand.upper()} ---")
        print(f"  IS: {s['D1_implementation_shortfall']['total_is_bps']:.2f} bps "
              f"(${s['D1_implementation_shortfall']['total_is_usd']:,.0f})")
        print(f"  Entry delta: {s['D2_entry_delta']['mean']:.2f} bps")
        print(f"  Exit delta: {s['D3_exit_delta']['mean']:.2f} bps")
        print(f"  Combined: {s['D4_combined_delta']['mean']:.2f} bps")
        print(f"  Improved: {s['D5_improved_vs_worsened']['frac_improved']:.1%} "
              f"({s['D5_improved_vs_worsened']['improved']}/{len(sf)})")
        print(f"  Years positive: {s['D6_concentration']['years_positive']}/"
              f"{s['D6_concentration']['total_years']}")
        print(f"  Secondary PnL delta: ${s['D7_secondary_path']['total_pnl_delta_usd']:,.0f}")
        print(f"  Verdict: {s['GO_HOLD_gates']['verdict']}")

    # Save artifacts
    sf.to_csv(EXEC_ARTIFACTS / "shadow_fills.csv", index=False)

    with open(EXEC_ARTIFACTS / "shadow_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    metadata = {
        "created": datetime.now(timezone.utc).isoformat(),
        "spec": "E1_1_EXECUTION_SPEC.md",
        "strategy": "X0 default (vtrend_x0_e5exit)",
        "scenario": "base",
        "trades": len(trades),
        "m15_bars": len(m15),
        "twap_window_bars": TWAP_BARS,
        "twap_window_ms": TWAP_WINDOW_MS,
        "cost_params": {
            "spread_bps": BASE_SPREAD_BPS,
            "slippage_bps": BASE_SLIPPAGE_BPS,
            "taker_fee_pct": BASE_TAKER_FEE_PCT,
        },
        "fallbacks": {
            "entry": int(fallback_entry),
            "exit": int(fallback_exit),
        },
    }
    with open(EXEC_ARTIFACTS / "shadow_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"\nSaved to {EXEC_ARTIFACTS}/")
    print(f"  shadow_fills.csv: {len(sf)} rows")
    print(f"  shadow_summary.json")
    print(f"  shadow_metadata.json")


if __name__ == "__main__":
    main()
