#!/usr/bin/env python3
"""
X33: State-Dependent Execution Cost Analysis

Reads aggTrades windows around E5+EMA1D21 signals and computes:
1. Effective spread at each signal moment (buyer vs seller initiated trades)
2. VWAP slippage for realistic order sizes ($10k, $50k, $100k)
3. Asymmetric cost distribution: entry vs exit
4. Comparison to "average" market conditions (using full window as baseline)
5. Cost-adjusted overlay recommendations (X18/X14D crossover re-evaluation)

Input:
  - signals.csv (from extract_signals.py)
  - aggtrades_windows.parquet (from fetch_binance_aggtrades.py)

Output:
  - cost_per_signal.csv: per-signal cost metrics
  - cost_summary.md: human-readable report with overlay implications
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

RESEARCH_DIR = Path(__file__).resolve().parent
DEFAULT_AGGTRADES = RESEARCH_DIR / "aggtrades_windows.parquet"
DEFAULT_SIGNALS = RESEARCH_DIR / "signals.csv"
DEFAULT_OUT_DIR = RESEARCH_DIR / "results"


def compute_effective_spread(
    trades: pd.DataFrame,
    center_ms: int,
    window_ms: int = 60_000,
) -> dict:
    """
    Compute effective bid-ask spread from aggTrades near a timestamp.

    Effective spread = 2 * |trade_price - mid_price|
    where mid_price = (mean_buyer_price + mean_seller_price) / 2

    Uses a narrow window (default ±1 min) right around the signal.
    """
    mask = (trades["transact_time"] >= center_ms - window_ms) & (
        trades["transact_time"] <= center_ms + window_ms
    )
    near = trades[mask].copy()

    if len(near) < 10:
        return {"effective_spread_bps": np.nan, "n_trades_near": len(near), "mid_price": np.nan}

    # Buyer-initiated (taker buy): is_buyer_maker == False
    # Seller-initiated (taker sell): is_buyer_maker == True
    buyers = near[~near["is_buyer_maker"]]
    sellers = near[near["is_buyer_maker"]]

    if buyers.empty or sellers.empty:
        return {"effective_spread_bps": np.nan, "n_trades_near": len(near), "mid_price": np.nan}

    # Volume-weighted price for each side
    buyer_vwap = np.average(buyers["price"], weights=buyers["quantity"])
    seller_vwap = np.average(sellers["price"], weights=sellers["quantity"])

    mid_price = (buyer_vwap + seller_vwap) / 2.0
    spread = buyer_vwap - seller_vwap  # buyer pays more than seller receives
    spread_bps = (spread / mid_price) * 10_000

    return {
        "effective_spread_bps": spread_bps,
        "n_trades_near": len(near),
        "mid_price": mid_price,
        "buyer_vwap": buyer_vwap,
        "seller_vwap": seller_vwap,
    }


def compute_vwap_slippage(
    trades: pd.DataFrame,
    center_ms: int,
    side: str,
    notional_usd: float,
    window_ms: int = 300_000,
) -> dict:
    """
    Simulate market order execution: walk the aggTrades to fill $notional_usd.

    For BUY (entry): consume seller-initiated trades (taker lifts asks).
    For SELL (exit): consume buyer-initiated trades (taker hits bids).

    Returns VWAP and slippage vs mid price.
    """
    mask = (trades["transact_time"] >= center_ms) & (
        trades["transact_time"] <= center_ms + window_ms
    )
    window = trades[mask].copy()

    if window.empty:
        return {"vwap": np.nan, "slippage_bps": np.nan, "fill_pct": 0.0}

    # For BUY: we consume the ask side = trades where is_buyer_maker == False (taker buys)
    # For SELL: we consume the bid side = trades where is_buyer_maker == True (taker sells)
    # Note: we simulate walking the ORDER BOOK.
    # aggTrades with is_buyer_maker=False means the taker was a buyer (lifting asks).
    # If WE are buying, we'd also be lifting asks, so these trades represent our execution prices.
    if side == "entry":
        available = window[~window["is_buyer_maker"]].copy()
    else:
        available = window[window["is_buyer_maker"]].copy()

    if available.empty:
        return {"vwap": np.nan, "slippage_bps": 0.0, "fill_pct": 0.0}

    available = available.sort_values("transact_time")
    available["notional"] = available["price"] * available["quantity"]

    cum_notional = available["notional"].cumsum()
    total_available = cum_notional.iloc[-1]

    if total_available < notional_usd * 0.1:
        return {"vwap": np.nan, "slippage_bps": np.nan, "fill_pct": total_available / notional_usd}

    # Find fill boundary
    fill_mask = cum_notional <= notional_usd
    if fill_mask.all():
        # Not enough to fill completely — use all available
        filled = available
        fill_pct = total_available / notional_usd
    else:
        # Fill up to notional
        last_idx = fill_mask.idxmax() if not fill_mask.any() else cum_notional[cum_notional >= notional_usd].index[0]
        filled = available.loc[:last_idx]
        fill_pct = 1.0

    vwap = np.average(filled["price"], weights=filled["quantity"])

    # Mid price from all trades in narrow window
    narrow = trades[
        (trades["transact_time"] >= center_ms - 60_000) & (trades["transact_time"] <= center_ms + 60_000)
    ]
    if narrow.empty:
        mid_price = vwap
    else:
        mid_price = np.average(narrow["price"], weights=narrow["quantity"])

    if side == "entry":
        slippage_bps = (vwap - mid_price) / mid_price * 10_000  # positive = we pay more
    else:
        slippage_bps = (mid_price - vwap) / mid_price * 10_000  # positive = we receive less

    return {"vwap": vwap, "slippage_bps": slippage_bps, "fill_pct": fill_pct}


def compute_volatility(trades: pd.DataFrame, center_ms: int, window_ms: int = 300_000) -> dict:
    """Compute price volatility (std of log returns) in window around signal."""
    mask = (trades["transact_time"] >= center_ms - window_ms) & (
        trades["transact_time"] <= center_ms + window_ms
    )
    window = trades[mask]
    if len(window) < 20:
        return {"volatility_bps": np.nan, "price_range_bps": np.nan}

    prices = window["price"].values
    log_returns = np.diff(np.log(prices))
    vol = np.std(log_returns) * 10_000

    price_range = (prices.max() - prices.min()) / np.median(prices) * 10_000

    return {"volatility_bps": vol, "price_range_bps": price_range}


def analyze_all_signals(
    signals_path: Path = DEFAULT_SIGNALS,
    aggtrades_path: Path = DEFAULT_AGGTRADES,
    out_dir: Path = DEFAULT_OUT_DIR,
    order_sizes_usd: list[float] | None = None,
) -> pd.DataFrame:
    if order_sizes_usd is None:
        order_sizes_usd = [10_000, 50_000, 100_000]

    signals = pd.read_csv(signals_path)
    print(f"Loaded {len(signals)} signals")

    if aggtrades_path.suffix == ".parquet":
        aggtrades = pd.read_parquet(aggtrades_path)
    else:
        aggtrades = pd.read_csv(aggtrades_path)
    print(f"Loaded {len(aggtrades):,} aggTrade rows for {aggtrades['signal_id'].nunique()} signals")

    results: list[dict] = []

    for _, sig in signals.iterrows():
        signal_id = int(sig["signal_id"])
        ts_ms = int(sig["ts_ms"])
        signal_type = sig["signal_type"]
        backtest_price = float(sig["backtest_price"])

        # Get this signal's trades
        mask = aggtrades["signal_id"] == signal_id
        trades = aggtrades[mask]

        if trades.empty:
            results.append({
                "signal_id": signal_id,
                "signal_type": signal_type,
                "trade_id": int(sig["trade_id"]),
                "ts_ms": ts_ms,
                "backtest_price": backtest_price,
                "n_aggtrades": 0,
            })
            continue

        row: dict = {
            "signal_id": signal_id,
            "signal_type": signal_type,
            "trade_id": int(sig["trade_id"]),
            "ts_ms": ts_ms,
            "backtest_price": backtest_price,
            "n_aggtrades": len(trades),
        }

        # 1. Effective spread (±1 min)
        spread = compute_effective_spread(trades, ts_ms, window_ms=60_000)
        row.update({f"spread_{k}": v for k, v in spread.items()})

        # 2. VWAP slippage for each order size
        for size in order_sizes_usd:
            slip = compute_vwap_slippage(trades, ts_ms, signal_type, size)
            size_k = f"{int(size / 1000)}k"
            row[f"slippage_{size_k}_bps"] = slip["slippage_bps"]
            row[f"fill_pct_{size_k}"] = slip["fill_pct"]

        # 3. Volatility around signal
        vol = compute_volatility(trades, ts_ms, window_ms=300_000)
        row.update(vol)

        # 4. Commission (Binance VIP0 + BNB discount)
        commission_bps = 7.5  # per side
        row["commission_bps"] = commission_bps

        # 5. Total estimated cost per side
        for size in order_sizes_usd:
            size_k = f"{int(size / 1000)}k"
            slip = row.get(f"slippage_{size_k}_bps", 0) or 0
            half_spread = (row.get("spread_effective_spread_bps", 0) or 0) / 2
            row[f"total_cost_{size_k}_bps"] = commission_bps + max(0, slip) + max(0, half_spread)

        results.append(row)

    df = pd.DataFrame(results)

    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "cost_per_signal.csv"
    df.to_csv(csv_path, index=False)
    print(f"\nSaved per-signal costs to {csv_path}")

    # Generate summary report
    _write_summary(df, order_sizes_usd, out_dir)

    return df


def _write_summary(df: pd.DataFrame, order_sizes: list[float], out_dir: Path) -> None:
    """Generate human-readable summary report."""
    lines: list[str] = []
    lines.append("# X33: Execution Cost Analysis Report")
    lines.append("")
    lines.append(f"**Signals analyzed**: {len(df)}")
    lines.append(f"**With aggTrades data**: {(df['n_aggtrades'] > 0).sum()}")
    lines.append("")

    # Split by signal type
    entries = df[df["signal_type"] == "entry"]
    exits = df[df["signal_type"] == "exit"]

    lines.append("## 1. Effective Spread (±1 min window)")
    lines.append("")
    spread_col = "spread_effective_spread_bps"
    if spread_col in df.columns:
        lines.append("| Metric | Entry | Exit | All |")
        lines.append("|--------|-------|------|-----|")
        for stat_name, fn in [("Median", "median"), ("Mean", "mean"), ("P75", lambda x: x.quantile(0.75)), ("P95", lambda x: x.quantile(0.95))]:
            if callable(fn) and not isinstance(fn, str):
                e_val = fn(entries[spread_col].dropna())
                x_val = fn(exits[spread_col].dropna())
                a_val = fn(df[spread_col].dropna())
            else:
                e_val = getattr(entries[spread_col].dropna(), fn)()
                x_val = getattr(exits[spread_col].dropna(), fn)()
                a_val = getattr(df[spread_col].dropna(), fn)()
            lines.append(f"| {stat_name} | {e_val:.2f} bps | {x_val:.2f} bps | {a_val:.2f} bps |")
    lines.append("")

    lines.append("## 2. VWAP Slippage by Order Size")
    lines.append("")
    lines.append("| Size | Entry median | Entry P75 | Exit median | Exit P75 |")
    lines.append("|------|-------------|-----------|-------------|----------|")
    for size in order_sizes:
        size_k = f"{int(size / 1000)}k"
        col = f"slippage_{size_k}_bps"
        if col in df.columns:
            e_med = entries[col].dropna().median()
            e_p75 = entries[col].dropna().quantile(0.75)
            x_med = exits[col].dropna().median()
            x_p75 = exits[col].dropna().quantile(0.75)
            lines.append(f"| ${size_k} | {e_med:.2f} bps | {e_p75:.2f} bps | {x_med:.2f} bps | {x_p75:.2f} bps |")
    lines.append("")

    lines.append("## 3. Total Estimated Cost Per Side (commission + spread/2 + slippage)")
    lines.append("")
    lines.append("| Size | Entry median | Exit median | RT median | RT P75 |")
    lines.append("|------|-------------|-------------|-----------|--------|")
    for size in order_sizes:
        size_k = f"{int(size / 1000)}k"
        col = f"total_cost_{size_k}_bps"
        if col in df.columns:
            e_med = entries[col].dropna().median()
            x_med = exits[col].dropna().median()
            rt_values = []
            for trade_id in df["trade_id"].unique():
                t = df[df["trade_id"] == trade_id]
                e_row = t[t["signal_type"] == "entry"]
                x_row = t[t["signal_type"] == "exit"]
                if not e_row.empty and not x_row.empty:
                    e_cost = e_row[col].iloc[0]
                    x_cost = x_row[col].iloc[0]
                    if pd.notna(e_cost) and pd.notna(x_cost):
                        rt_values.append(e_cost + x_cost)
            if rt_values:
                rt_arr = np.array(rt_values)
                rt_med = np.median(rt_arr)
                rt_p75 = np.percentile(rt_arr, 75)
                lines.append(f"| ${size_k} | {e_med:.1f} bps | {x_med:.1f} bps | {rt_med:.1f} bps | {rt_p75:.1f} bps |")
    lines.append("")

    lines.append("## 4. Entry vs Exit Asymmetry")
    lines.append("")
    lines.append("| Metric | Entry | Exit | Ratio (Exit/Entry) |")
    lines.append("|--------|-------|------|-------------------|")
    if spread_col in df.columns:
        e_spread = entries[spread_col].dropna().median()
        x_spread = exits[spread_col].dropna().median()
        ratio = x_spread / e_spread if e_spread > 0 else np.nan
        lines.append(f"| Spread | {e_spread:.2f} bps | {x_spread:.2f} bps | {ratio:.2f}x |")
    vol_col = "volatility_bps"
    if vol_col in df.columns:
        e_vol = entries[vol_col].dropna().median()
        x_vol = exits[vol_col].dropna().median()
        ratio = x_vol / e_vol if e_vol > 0 else np.nan
        lines.append(f"| Volatility | {e_vol:.2f} bps | {x_vol:.2f} bps | {ratio:.2f}x |")
    lines.append("")

    lines.append("## 5. Overlay Implications (X22 Re-evaluation)")
    lines.append("")
    lines.append("Using median RT cost from Section 3 above, look up X22 cost curve:")
    lines.append("")
    lines.append("| Cost RT (bps) | E5+EMA1D21 Sh | X18 ΔSh | X14D ΔSh | Verdict |")
    lines.append("|---------------|---------------|---------|----------|---------|")
    x22_table = [
        (15, 1.670, -0.032, -0.174, "Skip both"),
        (20, 1.636, -0.023, -0.157, "Skip both"),
        (25, 1.602, -0.013, -0.140, "Skip both"),
        (30, 1.568, -0.004, -0.123, "Skip both"),
        (35, 1.534, 0.000, -0.089, "X18 neutral"),
        (40, 1.500, 0.015, -0.089, "X18 helps"),
        (50, 1.432, 0.034, -0.054, "X18 helps"),
        (75, 1.261, 0.082, 0.031, "Both help"),
    ]
    for cost, sh, x18, x14, verdict in x22_table:
        lines.append(f"| {cost} | {sh:.3f} | {x18:+.3f} | {x14:+.3f} | {verdict} |")
    lines.append("")
    lines.append("**Compare your median RT from Section 3 against this table to determine overlay recommendation.**")
    lines.append("")

    report_path = out_dir / "cost_summary.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Saved summary report to {report_path}")


def main() -> None:
    import argparse

    p = argparse.ArgumentParser(description="X33: Analyze execution costs from aggTrades")
    p.add_argument("--signals", default=str(DEFAULT_SIGNALS), help="Path to signals.csv")
    p.add_argument("--aggtrades", default=str(DEFAULT_AGGTRADES), help="Path to aggtrades_windows.parquet")
    p.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR), help="Output directory")
    p.add_argument("--sizes", default="10000,50000,100000", help="Order sizes in USD (comma-separated)")
    args = p.parse_args()

    sizes = [float(x) for x in args.sizes.split(",")]
    analyze_all_signals(
        signals_path=Path(args.signals),
        aggtrades_path=Path(args.aggtrades),
        out_dir=Path(args.out_dir),
        order_sizes_usd=sizes,
    )


if __name__ == "__main__":
    main()
