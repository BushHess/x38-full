#!/usr/bin/env python3
"""
X33 Step 1: Extract entry/exit signal timestamps from E5+EMA1D21 trade log.

Output: signals.csv with columns:
  signal_id, ts_ms, signal_type (entry|exit), trade_id, backtest_price, qty_btc

This file is the input for the aggTrades downloader in data-pipeline/.
"""

from __future__ import annotations

import pandas as pd
from pathlib import Path

TRADE_LOG = Path(__file__).resolve().parents[2] / "results" / "full_eval_e5_ema21d1" / "results" / "trades_candidate.csv"
OUT_DIR = Path(__file__).resolve().parent


def main() -> None:
    df = pd.read_csv(TRADE_LOG)
    print(f"Loaded {len(df)} trades from {TRADE_LOG.name}")

    rows: list[dict] = []
    for _, t in df.iterrows():
        rows.append({
            "signal_id": len(rows),
            "ts_ms": int(t["entry_ts_ms"]),
            "signal_type": "entry",
            "trade_id": int(t["trade_id"]),
            "backtest_price": float(t["entry_price"]),
            "qty_btc": float(t["qty"]),
        })
        rows.append({
            "signal_id": len(rows),
            "ts_ms": int(t["exit_ts_ms"]),
            "signal_type": "exit",
            "trade_id": int(t["trade_id"]),
            "backtest_price": float(t["exit_price"]),
            "qty_btc": float(t["qty"]),
        })

    signals = pd.DataFrame(rows)
    signals["ts_utc"] = pd.to_datetime(signals["ts_ms"], unit="ms", utc=True)
    signals["date"] = signals["ts_utc"].dt.date
    signals = signals.sort_values("ts_ms").reset_index(drop=True)

    out_path = OUT_DIR / "signals.csv"
    signals.to_csv(out_path, index=False)
    print(f"Wrote {len(signals)} signals to {out_path}")
    print(f"  Entries: {(signals['signal_type'] == 'entry').sum()}")
    print(f"  Exits:   {(signals['signal_type'] == 'exit').sum()}")
    print(f"  Unique dates: {signals['date'].nunique()}")
    print(f"  Date range: {signals['date'].min()} to {signals['date'].max()}")


if __name__ == "__main__":
    main()
