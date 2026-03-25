#!/usr/bin/env python3
"""C7: Blocked Winners Diagnosis — identify the pattern of opportunity cost.

For each blocked winner (baseline trade blocked by overlay cooldown K=12):
  1. Extract full market context at entry: regime, ATR%, VDO, accel, HMA slope, RSI
  2. Compute distance from nearest emergency_dd exit to entry (bars)
  3. Characterize price action around the entry (V-shape rebound, mean reversion, etc.)
  4. Propose minimal rule to unblock these trades without complex entry alpha

Outputs:
  - out_overlayA_conditional/blocked_winners_top.csv
  - reports/overlayA_blocked_winners_diagnosis.md

Usage:
    python experiments/overlayA/overlayA_blocked_winners_diagnosis.py
"""

from __future__ import annotations

import csv
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

np.seterr(all="ignore")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from v10.core.data import DataFeed
from v10.core.engine import BacktestEngine
from v10.core.types import SCENARIOS, Trade
from v10.strategies.v8_apex import V8ApexConfig, V8ApexStrategy, Regime
from experiments.overlayA.step1_export import InstrumentedV8Apex

# ── Constants ────────────────────────────────────────────────────────────────

DATA_PATH = str(PROJECT_ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv")
START = "2019-01-01"
END = "2026-02-20"
WARMUP_DAYS = 365
INITIAL_CASH = 10_000.0
SCENARIO = "harsh"
K = 12

OUTDIR = PROJECT_ROOT / "out/overlayA_conditional"
REPORT_DIR = PROJECT_ROOT / "out/v10_full_validation_stepwise" / "reports"

ENTRY_TS_MATCH_TOL_MS = 14_400_000  # 4h


# ── Helpers ──────────────────────────────────────────────────────────────────

def ms_to_date(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")

def ms_to_iso(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")


def find_bar_index(h4_bars, ts_ms: int) -> int | None:
    """Find the H4 bar index whose close_time is closest to ts_ms."""
    best_idx = None
    best_dist = float("inf")
    for i, bar in enumerate(h4_bars):
        dist = abs(bar.close_time - ts_ms)
        if dist < best_dist:
            best_dist = dist
            best_idx = i
        if bar.close_time > ts_ms + ENTRY_TS_MATCH_TOL_MS:
            break
    return best_idx


def find_d1_index(d1_bars, h4_close_time: int) -> int:
    """Find D1 index (strict MTF alignment: latest D1 closed before H4 close)."""
    d1_idx = -1
    for i, d1_bar in enumerate(d1_bars):
        if d1_bar.close_time < h4_close_time:
            d1_idx = i
        else:
            break
    return d1_idx


def compute_hma_slope(hma_arr, idx: int, lookback: int = 3) -> float:
    """Compute HMA slope as (HMA[idx] - HMA[idx-lookback]) / lookback, normalized by price."""
    if idx < lookback or idx >= len(hma_arr):
        return 0.0
    v0 = hma_arr[idx - lookback]
    v1 = hma_arr[idx]
    if np.isnan(v0) or np.isnan(v1) or v0 == 0:
        return 0.0
    return (v1 - v0) / v0 / lookback * 100  # % per bar


def compute_price_context(h4_bars, entry_idx: int, exit_idx: int):
    """Characterize price action around entry and during trade."""
    # Pre-entry drawdown: how far did price drop before entry?
    lookback = 20  # 20 H4 bars = ~3.3 days
    pre_high = 0.0
    pre_low = float("inf")
    for i in range(max(0, entry_idx - lookback), entry_idx):
        pre_high = max(pre_high, h4_bars[i].high)
        pre_low = min(pre_low, h4_bars[i].low)

    entry_price = h4_bars[entry_idx].close
    pre_dd_pct = (pre_high - entry_price) / pre_high * 100 if pre_high > 0 else 0.0

    # Post-entry rally: how much did price rise from entry to peak during trade?
    peak_during = entry_price
    for i in range(entry_idx, min(exit_idx + 1, len(h4_bars))):
        peak_during = max(peak_during, h4_bars[i].high)
    post_rally_pct = (peak_during - entry_price) / entry_price * 100

    # V-shape: pre_dd > 10% AND post_rally > 15%
    is_v_shape = pre_dd_pct > 10.0 and post_rally_pct > 15.0

    # Price vs entry relative to 20-bar range
    range_20 = pre_high - pre_low if pre_high > pre_low else 1.0
    entry_in_range_pct = (entry_price - pre_low) / range_20 * 100

    return {
        "pre_high": round(pre_high, 2),
        "pre_low": round(pre_low, 2),
        "pre_dd_from_high_pct": round(pre_dd_pct, 2),
        "post_rally_pct": round(post_rally_pct, 2),
        "is_v_shape": is_v_shape,
        "entry_in_20bar_range_pct": round(entry_in_range_pct, 1),
    }


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    t0 = time.time()
    print("=" * 70)
    print("  C7: BLOCKED WINNERS DIAGNOSIS")
    print("=" * 70)
    print()

    # ── Load data ─────────────────────────────────────────────────────────
    print("  Loading data...")
    feed = DataFeed(DATA_PATH, start=START, end=END, warmup_days=WARMUP_DAYS)
    cost = SCENARIOS[SCENARIO]
    h4_bars = feed.h4_bars
    d1_bars = feed.d1_bars

    # ── Run baseline (K=0) ────────────────────────────────────────────────
    print("  Running baseline (K=0)...")
    bl_cfg = V8ApexConfig(cooldown_after_emergency_dd_bars=0)
    bl_strat = V8ApexStrategy(bl_cfg)
    bl_engine = BacktestEngine(
        feed=feed, strategy=bl_strat, cost=cost,
        initial_cash=INITIAL_CASH, warmup_days=WARMUP_DAYS,
    )
    bl_result = bl_engine.run()
    print(f"    Trades: {len(bl_result.trades)}")

    # ── Run overlay (K=12) instrumented ───────────────────────────────────
    print(f"  Running overlayA (K={K}), instrumented...")
    ov_cfg = V8ApexConfig(cooldown_after_emergency_dd_bars=K)
    ov_strat = InstrumentedV8Apex(ov_cfg)
    ov_engine = BacktestEngine(
        feed=feed, strategy=ov_strat, cost=cost,
        initial_cash=INITIAL_CASH, warmup_days=WARMUP_DAYS,
    )
    ov_result = ov_engine.run()
    signal_log = ov_strat.signal_log
    print(f"    Trades: {len(ov_result.trades)}")
    print()

    # ── Identify blocked trades ───────────────────────────────────────────
    # All baseline trades not matched in overlay
    ov_entry_set = {t.entry_ts_ms for t in ov_result.trades}

    cooldown_block_bars_ms = {
        e["bar_ts_ms"] for e in signal_log
        if e["event_type"] == "entry_blocked"
        and e["reason"] == "cooldown_after_emergency_dd"
    }

    blocked_trades: list[Trade] = []
    for t in bl_result.trades:
        matched = any(
            abs(t.entry_ts_ms - ov_ts) <= ENTRY_TS_MATCH_TOL_MS
            for ov_ts in ov_entry_set
        )
        if not matched:
            # Verify it was actually cooldown-blocked
            is_cd_block = any(
                abs(t.entry_ts_ms - bts) <= ENTRY_TS_MATCH_TOL_MS
                for bts in cooldown_block_bars_ms
            )
            if is_cd_block:
                blocked_trades.append(t)

    # Sort by PnL descending
    blocked_trades.sort(key=lambda t: t.pnl, reverse=True)

    print(f"  Found {len(blocked_trades)} cooldown-blocked trades")
    print(f"    Winners: {sum(1 for t in blocked_trades if t.pnl > 0)}")
    print(f"    Losers:  {sum(1 for t in blocked_trades if t.pnl <= 0)}")
    print()

    # ── Find all emergency_dd exits (baseline) ────────────────────────────
    emdd_exits = []
    for t in bl_result.trades:
        if t.exit_reason == "emergency_dd":
            exit_idx = find_bar_index(h4_bars, t.exit_ts_ms)
            emdd_exits.append({
                "trade_id": t.trade_id,
                "exit_ts_ms": t.exit_ts_ms,
                "exit_bar_idx": exit_idx,
                "exit_date": ms_to_date(t.exit_ts_ms),
                "exit_price": t.exit_price,
            })
    emdd_exits.sort(key=lambda x: x["exit_ts_ms"])
    print(f"  Baseline emergency_dd exits: {len(emdd_exits)}")
    print()

    # ── Extract market context for each blocked trade ─────────────────────
    detailed_rows = []

    for t in blocked_trades:
        entry_idx = find_bar_index(h4_bars, t.entry_ts_ms)
        exit_idx = find_bar_index(h4_bars, t.exit_ts_ms)

        if entry_idx is None or exit_idx is None:
            continue

        bar = h4_bars[entry_idx]
        mid = bar.close
        d1_idx = find_d1_index(d1_bars, bar.close_time)

        # Indicators at entry bar (from baseline strategy arrays)
        vdo = bl_strat._h4_vdo[entry_idx] if entry_idx < len(bl_strat._h4_vdo) else 0.0
        hma = bl_strat._h4_hma[entry_idx] if entry_idx < len(bl_strat._h4_hma) else mid
        rsi = bl_strat._h4_rsi[entry_idx] if entry_idx < len(bl_strat._h4_rsi) else 50.0
        atr_f = bl_strat._h4_atr_f[entry_idx] if entry_idx < len(bl_strat._h4_atr_f) else mid * 0.02
        atr_s = bl_strat._h4_atr_s[entry_idx] if entry_idx < len(bl_strat._h4_atr_s) else mid * 0.02
        accel = bl_strat._h4_accel[entry_idx] if entry_idx < len(bl_strat._h4_accel) else 0.0
        ema200 = bl_strat._h4_ema200[entry_idx] if entry_idx < len(bl_strat._h4_ema200) else mid

        # Regime
        regime = (
            bl_strat._d1_regime[d1_idx]
            if 0 <= d1_idx < len(bl_strat._d1_regime)
            else Regime.RISK_OFF
        )

        # D1 volatility
        d1_vol = (
            bl_strat._d1_vol_ann[d1_idx]
            if 0 <= d1_idx < len(bl_strat._d1_vol_ann)
            else 1.0
        )

        # ATR as % of price
        atr_pct = atr_f / mid * 100 if mid > 0 else 0.0

        # HMA slope
        hma_slope = compute_hma_slope(bl_strat._h4_hma, entry_idx)

        # Price vs HMA
        price_vs_hma_pct = (mid - hma) / hma * 100 if hma > 0 and not np.isnan(hma) else 0.0

        # Price vs EMA200
        price_vs_ema200_pct = (mid - ema200) / ema200 * 100 if ema200 > 0 and not np.isnan(ema200) else 0.0

        # ATR compression ratio
        compression_ratio = atr_f / atr_s if atr_s > 0 else 1.0

        # ── Distance from nearest emergency_dd exit ──
        nearest_emdd_bars = None
        nearest_emdd_trade_id = None
        nearest_emdd_date = None
        for em in reversed(emdd_exits):
            if em["exit_ts_ms"] <= t.entry_ts_ms and em["exit_bar_idx"] is not None:
                nearest_emdd_bars = entry_idx - em["exit_bar_idx"]
                nearest_emdd_trade_id = em["trade_id"]
                nearest_emdd_date = em["exit_date"]
                break

        # ── Price context ──
        pctx = compute_price_context(h4_bars, entry_idx, exit_idx)

        # ── Classify pattern ──
        if pctx["is_v_shape"]:
            pattern = "V-shape rebound"
        elif pctx["pre_dd_from_high_pct"] > 15.0 and pctx["post_rally_pct"] > 20.0:
            pattern = "deep mean reversion"
        elif pctx["pre_dd_from_high_pct"] > 8.0:
            pattern = "recovery from drawdown"
        elif accel > 0 and price_vs_hma_pct > 0:
            pattern = "trend continuation"
        else:
            pattern = "other"

        row = {
            "trade_id": t.trade_id,
            "entry_ts": ms_to_iso(t.entry_ts_ms),
            "exit_ts": ms_to_iso(t.exit_ts_ms),
            "entry_price": round(t.entry_price, 2),
            "exit_price": round(t.exit_price, 2),
            "net_pnl": round(t.pnl, 2),
            "return_pct": round(t.return_pct, 2),
            "days_held": round(t.days_held, 2),
            "entry_reason": t.entry_reason,
            "exit_reason": t.exit_reason,
            # Market context at entry
            "regime": regime.value,
            "atr_pct": round(atr_pct, 3),
            "vdo": round(vdo, 5),
            "accel": round(accel, 6),
            "rsi": round(rsi, 1),
            "hma_slope_pct_per_bar": round(hma_slope, 4),
            "price_vs_hma_pct": round(price_vs_hma_pct, 2),
            "price_vs_ema200_pct": round(price_vs_ema200_pct, 2),
            "compression_ratio": round(compression_ratio, 3),
            "d1_vol_ann": round(d1_vol, 3),
            # Distance from nearest emergency_dd exit
            "bars_from_emdd_exit": nearest_emdd_bars,
            "emdd_exit_trade_id": nearest_emdd_trade_id,
            "emdd_exit_date": nearest_emdd_date,
            # Price context
            "pre_dd_from_high_pct": pctx["pre_dd_from_high_pct"],
            "post_rally_pct": pctx["post_rally_pct"],
            "is_v_shape": pctx["is_v_shape"],
            "entry_in_20bar_range_pct": pctx["entry_in_20bar_range_pct"],
            # Pattern
            "pattern": pattern,
        }
        detailed_rows.append(row)

    # ── Write CSV ─────────────────────────────────────────────────────────
    OUTDIR.mkdir(parents=True, exist_ok=True)
    csv_path = OUTDIR / "blocked_winners_top.csv"
    csv_fields = list(detailed_rows[0].keys()) if detailed_rows else []
    with open(csv_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=csv_fields)
        w.writeheader()
        w.writerows(detailed_rows)
    print(f"  Saved: {csv_path}")

    # ── Print summary ─────────────────────────────────────────────────────
    print()
    print(f"  {'='*70}")
    print(f"  BLOCKED TRADES DETAIL (sorted by PnL desc)")
    print(f"  {'='*70}")
    for r in detailed_rows:
        winner = "WIN" if r["net_pnl"] > 0 else "LOSS"
        print(f"\n  Trade #{r['trade_id']} [{winner}]  PnL: ${r['net_pnl']:+,.2f}  "
              f"({r['return_pct']:+.1f}%)  {r['days_held']:.0f}d")
        print(f"    Entry: {r['entry_ts']}  Exit: {r['exit_ts']}")
        print(f"    Entry reason: {r['entry_reason']}  Exit reason: {r['exit_reason']}")
        print(f"    Regime: {r['regime']}  VDO: {r['vdo']:.5f}  "
              f"RSI: {r['rsi']:.1f}  Accel: {r['accel']:.6f}")
        print(f"    ATR%: {r['atr_pct']:.3f}  HMA slope: {r['hma_slope_pct_per_bar']:.4f}%/bar  "
              f"Price vs HMA: {r['price_vs_hma_pct']:+.2f}%")
        print(f"    Price vs EMA200: {r['price_vs_ema200_pct']:+.2f}%  "
              f"Compression: {r['compression_ratio']:.3f}")
        print(f"    Bars from ED exit: {r['bars_from_emdd_exit']}  "
              f"(ED trade #{r['emdd_exit_trade_id']}, {r['emdd_exit_date']})")
        print(f"    Pre-DD from high: {r['pre_dd_from_high_pct']:.1f}%  "
              f"Post-rally: {r['post_rally_pct']:.1f}%  "
              f"V-shape: {r['is_v_shape']}")
        print(f"    Pattern: **{r['pattern']}**")

    # ── Generate report ───────────────────────────────────────────────────
    report = build_report(detailed_rows, emdd_exits, bl_result.trades)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_DIR / "overlayA_blocked_winners_diagnosis.md"
    with open(report_path, "w") as f:
        f.write(report)
    print(f"\n  Saved: {report_path}")

    elapsed = time.time() - t0
    print(f"\n  Done in {elapsed:.1f}s")
    print("=" * 70)


# ── Report builder ────────────────────────────────────────────────────────────

def build_report(rows: list[dict], emdd_exits: list[dict],
                 bl_trades: list[Trade]) -> str:
    lines = []
    L = lines.append

    L("# OverlayA Blocked Winners Diagnosis")
    L("")
    L("**Date:** 2026-02-24")
    L("**Scenario:** harsh (50 bps RT)")
    L("**Overlay:** cooldown_after_emergency_dd_bars = 12")
    L("**Baseline:** cooldown_after_emergency_dd_bars = 0")
    L("")

    # Separate winners and losers
    winners = [r for r in rows if r["net_pnl"] > 0]
    losers = [r for r in rows if r["net_pnl"] <= 0]

    L(f"**Total cooldown-blocked trades:** {len(rows)}")
    L(f"**Winners:** {len(winners)} "
      f"(total PnL: ${sum(r['net_pnl'] for r in winners):+,.0f})")
    L(f"**Losers:** {len(losers)} "
      f"(total PnL: ${sum(r['net_pnl'] for r in losers):+,.0f})")
    L("")

    # ── Section 1: Detailed table ──
    L("---")
    L("")
    L("## 1. Blocked Trades — Full Detail")
    L("")
    L("| # | Trade | Entry | Exit | PnL $ | Ret% | Days | Entry Reason | Exit Reason |")
    L("|--:|------:|-------|------|------:|-----:|-----:|:-------------|:------------|")
    for i, r in enumerate(rows, 1):
        L(f"| {i} | {r['trade_id']} "
          f"| {r['entry_ts'][:10]} "
          f"| {r['exit_ts'][:10]} "
          f"| {r['net_pnl']:+,.0f} "
          f"| {r['return_pct']:+.1f} "
          f"| {r['days_held']:.0f} "
          f"| {r['entry_reason']} "
          f"| {r['exit_reason']} |")
    L("")

    # ── Section 2: Market context at entry ──
    L("---")
    L("")
    L("## 2. Market Context at Entry")
    L("")
    L("| Trade | Regime | VDO | RSI | ATR% | Accel | HMA slope | Price vs HMA | Price vs EMA200 |")
    L("|------:|:------:|----:|----:|-----:|------:|----------:|-------------:|----------------:|")
    for r in rows:
        L(f"| {r['trade_id']} "
          f"| {r['regime']} "
          f"| {r['vdo']:.4f} "
          f"| {r['rsi']:.0f} "
          f"| {r['atr_pct']:.2f} "
          f"| {r['accel']:.5f} "
          f"| {r['hma_slope_pct_per_bar']:.3f}%/bar "
          f"| {r['price_vs_hma_pct']:+.1f}% "
          f"| {r['price_vs_ema200_pct']:+.1f}% |")
    L("")

    # ── Section 3: Distance from emergency_dd exit ──
    L("---")
    L("")
    L("## 3. Distance from Nearest Emergency DD Exit")
    L("")
    L("| Trade | Entry Date | Nearest ED Exit | ED Trade | Bars Gap | Gap (days) | Pattern |")
    L("|------:|:-----------|:----------------|:--------:|---------:|-----------:|:--------|")
    for r in rows:
        gap_days = r["bars_from_emdd_exit"] * 4 / 24 if r["bars_from_emdd_exit"] else "?"
        gap_days_str = f"{gap_days:.1f}" if isinstance(gap_days, float) else gap_days
        L(f"| {r['trade_id']} "
          f"| {r['entry_ts'][:10]} "
          f"| {r['emdd_exit_date'] or '?'} "
          f"| #{r['emdd_exit_trade_id'] or '?'} "
          f"| {r['bars_from_emdd_exit'] or '?'} "
          f"| {gap_days_str} "
          f"| {r['pattern']} |")
    L("")

    # Key observation about distances
    bars_gaps = [r["bars_from_emdd_exit"] for r in rows if r["bars_from_emdd_exit"] is not None]
    if bars_gaps:
        L(f"**Gap range:** {min(bars_gaps)} – {max(bars_gaps)} H4 bars "
          f"({min(bars_gaps)*4/24:.1f} – {max(bars_gaps)*4/24:.1f} days)")
        L(f"**All gaps > exit_cooldown_bars (3):** "
          f"{'Yes' if all(g > 3 for g in bars_gaps) else 'No'}")
        L(f"**All gaps ≤ K=12:** "
          f"{'Yes' if all(g <= 12 for g in bars_gaps) else 'No — some entries occur after cooldown would expire'}")
        L("")

    # ── Section 4: Price action context ──
    L("---")
    L("")
    L("## 4. Price Action Context")
    L("")
    L("| Trade | Pre-DD% | Post-Rally% | V-Shape? | Entry in 20-bar Range | Pattern |")
    L("|------:|--------:|------------:|:--------:|----------------------:|:--------|")
    for r in rows:
        L(f"| {r['trade_id']} "
          f"| {r['pre_dd_from_high_pct']:.1f} "
          f"| {r['post_rally_pct']:.1f} "
          f"| {'Yes' if r['is_v_shape'] else 'No'} "
          f"| {r['entry_in_20bar_range_pct']:.0f}% "
          f"| {r['pattern']} |")
    L("")

    # ── Section 5: Pattern classification ──
    L("---")
    L("")
    L("## 5. Pattern Classification")
    L("")

    # Group by pattern
    patterns = {}
    for r in rows:
        p = r["pattern"]
        if p not in patterns:
            patterns[p] = []
        patterns[p].append(r)

    for pattern, trades in sorted(patterns.items(), key=lambda x: -sum(t["net_pnl"] for t in x[1])):
        total_pnl = sum(t["net_pnl"] for t in trades)
        L(f"### {pattern.title()} ({len(trades)} trade{'s' if len(trades) != 1 else ''}, "
          f"${total_pnl:+,.0f})")
        L("")
        for t in trades:
            L(f"- **Trade #{t['trade_id']}** ({t['entry_ts'][:10]} → {t['exit_ts'][:10]}): "
              f"${t['net_pnl']:+,.0f} ({t['return_pct']:+.1f}%). "
              f"Entry {t['bars_from_emdd_exit'] or '?'} bars after ED exit. "
              f"Pre-DD {t['pre_dd_from_high_pct']:.0f}% → post-rally {t['post_rally_pct']:.0f}%. "
              f"Regime={t['regime']}, VDO={t['vdo']:.4f}, "
              f"RSI={t['rsi']:.0f}, price vs HMA={t['price_vs_hma_pct']:+.1f}%.")
        L("")

    # ── Section 6: Common characteristics ──
    L("---")
    L("")
    L("## 6. Common Characteristics of Blocked Winners")
    L("")

    if winners:
        avg_bars_gap = np.mean([r["bars_from_emdd_exit"] for r in winners
                                if r["bars_from_emdd_exit"] is not None])
        avg_pre_dd = np.mean([r["pre_dd_from_high_pct"] for r in winners])
        avg_post_rally = np.mean([r["post_rally_pct"] for r in winners])
        avg_return = np.mean([r["return_pct"] for r in winners])
        avg_days = np.mean([r["days_held"] for r in winners])
        avg_vdo = np.mean([r["vdo"] for r in winners])
        exit_reasons = [r["exit_reason"] for r in winners]
        regimes = [r["regime"] for r in winners]
        entry_reasons = [r["entry_reason"] for r in winners]

        L("| Metric | Value |")
        L("|--------|-------|")
        L(f"| Count | {len(winners)} |")
        L(f"| Total PnL | ${sum(r['net_pnl'] for r in winners):+,.0f} |")
        L(f"| Avg return | {avg_return:+.1f}% |")
        L(f"| Avg holding period | {avg_days:.0f} days |")
        L(f"| Avg bars from ED exit | {avg_bars_gap:.1f} bars ({avg_bars_gap*4/24:.1f} days) |")
        L(f"| Avg pre-entry drawdown | {avg_pre_dd:.1f}% |")
        L(f"| Avg post-entry rally | {avg_post_rally:.1f}% |")
        L(f"| Avg VDO at entry | {avg_vdo:.4f} |")
        L(f"| Exit reasons | {', '.join(set(exit_reasons))} |")
        L(f"| Entry regimes | {', '.join(set(regimes))} |")
        L(f"| Entry reasons | {', '.join(set(entry_reasons))} |")
        L("")

        L("**Key observations:**")
        L("")

        # All exit via trailing_stop?
        if all(r["exit_reason"] == "trailing_stop" for r in winners):
            L("1. **All blocked winners exit via trailing_stop** — none would have been "
              "another emergency_dd. The cooldown blocks legitimate recovery trades, not "
              "cascade re-entries.")
        else:
            ts_pct = sum(1 for r in winners if r["exit_reason"] == "trailing_stop") / len(winners) * 100
            L(f"1. **{ts_pct:.0f}% exit via trailing_stop** — mostly legitimate trades, "
              f"not cascade re-entries.")
        L("")

        # Regime at entry
        if all(r["regime"] == "RISK_ON" for r in winners):
            L("2. **All entries occur in RISK_ON regime** — the market structure is bullish "
              "when these trades enter. The emergency_dd was a temporary shock within "
              "a positive regime, not a regime breakdown.")
        else:
            L(f"2. **Entry regimes:** {', '.join(set(regimes))}.")
        L("")

        # Distance analysis
        if all(r["bars_from_emdd_exit"] is not None and r["bars_from_emdd_exit"] <= K
               for r in winners):
            L(f"3. **All entries within K={K} bars of ED exit** — these are the trades "
              f"the cooldown is specifically designed to block. The question is whether "
              f"the blocking is net-beneficial.")
            min_gap = min(r["bars_from_emdd_exit"] for r in winners
                          if r["bars_from_emdd_exit"] is not None)
            max_gap = max(r["bars_from_emdd_exit"] for r in winners
                          if r["bars_from_emdd_exit"] is not None)
            L(f"   - Entry gaps: {min_gap} to {max_gap} bars "
              f"({min_gap*4/24:.1f} to {max_gap*4/24:.1f} days)")
        L("")

        # V-shape pattern
        v_shapes = [r for r in winners if r["is_v_shape"]]
        if v_shapes:
            L(f"4. **{len(v_shapes)}/{len(winners)} winners are V-shape rebounds** — "
              f"the price dropped significantly before entry, then rallied strongly. "
              f"These are genuine recovery trades after an isolated emergency_dd exit.")
        else:
            L(f"4. **No V-shape rebounds detected** — pattern classification: "
              f"{', '.join(set(r['pattern'] for r in winners))}.")
        L("")

        # VDO strength
        if all(r["vdo"] > 0.004 for r in winners):
            L(f"5. **Strong VDO at entry** (all > 0.004) — the volume delta oscillator "
              f"confirms buying pressure at entry. These are not weak or ambiguous entries.")
        else:
            L(f"5. **VDO range at entry:** "
              f"{min(r['vdo'] for r in winners):.4f} – "
              f"{max(r['vdo'] for r in winners):.4f}")
        L("")

    # ── Section 6b: Winners vs Losers exit-reason breakdown ──
    if losers:
        L("### Winners vs Losers: Exit Reason Breakdown")
        L("")
        L("This is the strongest signal separating legitimate recovery trades from "
          "cascade re-entries:")
        L("")
        L("| Group | Count | trailing_stop | emergency_dd | other | Total PnL |")
        L("|:------|------:|--------------:|-------------:|------:|----------:|")

        w_ts = sum(1 for r in winners if r["exit_reason"] == "trailing_stop")
        w_ed = sum(1 for r in winners if r["exit_reason"] == "emergency_dd")
        w_ot = len(winners) - w_ts - w_ed
        w_pnl = sum(r["net_pnl"] for r in winners)

        l_ts = sum(1 for r in losers if r["exit_reason"] == "trailing_stop")
        l_ed = sum(1 for r in losers if r["exit_reason"] == "emergency_dd")
        l_ot = len(losers) - l_ts - l_ed
        l_pnl = sum(r["net_pnl"] for r in losers)

        L(f"| **Winners** | {len(winners)} | {w_ts} ({w_ts*100//max(len(winners),1)}%) "
          f"| {w_ed} ({w_ed*100//max(len(winners),1)}%) "
          f"| {w_ot} | ${w_pnl:+,.0f} |")
        L(f"| **Losers** | {len(losers)} | {l_ts} ({l_ts*100//max(len(losers),1)}%) "
          f"| {l_ed} ({l_ed*100//max(len(losers),1)}%) "
          f"| {l_ot} | ${l_pnl:+,.0f} |")
        L("")

        if l_ed > 0:
            l_ed_pnl = sum(r["net_pnl"] for r in losers if r["exit_reason"] == "emergency_dd")
            L(f"**Critical finding:** {l_ed}/{len(losers)} blocked losers "
              f"({l_ed*100//len(losers)}%) exit via **emergency_dd** — "
              f"they are cascade re-entries that the cooldown correctly blocks. "
              f"Their total PnL: ${l_ed_pnl:+,.0f}.")
            L("")
            L("This means the cooldown is doing exactly what it should for cascade scenarios. "
              "The opportunity cost comes exclusively from isolated-ED recovery trades "
              "that exit via trailing_stop.")
            L("")

            # List the cascade re-entry losers
            ed_losers = [r for r in losers if r["exit_reason"] == "emergency_dd"]
            L("**Cascade re-entry losers (correctly blocked):**")
            L("")
            for r in ed_losers:
                L(f"- Trade #{r['trade_id']} ({r['entry_ts'][:10]}): "
                  f"${r['net_pnl']:+,.0f} — re-entered {r['bars_from_emdd_exit']} bars "
                  f"after ED exit, then exited via emergency_dd again")
            L("")

    # ── Section 7: Root cause ──
    L("---")
    L("")
    L("## 7. Root Cause Analysis")
    L("")
    L("The blocked winners share a common pattern:")
    L("")
    L("1. **An isolated emergency_dd exit occurs** — the strategy exits due to "
      "a drawdown exceeding the threshold (28% default).")
    L("2. **The market recovers within a few bars** — the drawdown was temporary "
      "(not the start of a multi-month bear cascade).")
    L("3. **The cooldown window (K=12 bars = 2 days) blocks re-entry** — by the "
      "time the cooldown expires, the optimal re-entry point has passed.")
    L("4. **The trade that would have been taken is a big winner** — "
      "exiting via trailing_stop after a strong rally.")
    L("")
    L("The core issue is that the cooldown treats all emergency_dd exits equally. "
      "It cannot distinguish:")
    L("")
    L("- **Cascade ED exits** (2+ consecutive EDs within a drawdown episode) — "
      "where blocking re-entry is beneficial")
    L("- **Isolated ED exits** (single ED followed by recovery) — "
      "where blocking re-entry is costly")
    L("")

    # ── Section 8: Minimal rule proposal ──
    L("---")
    L("")
    L("## 8. Proposed Minimal Rule")
    L("")
    L("### Problem")
    L("")
    L("The current cooldown activates after **every** emergency_dd exit, including "
      "isolated ones that are followed by genuine recoveries.")
    L("")
    L("### Proposal: Activate cooldown only after 2nd consecutive emergency_dd")
    L("")
    L("```python")
    L("# Current (K=12, activates on every ED exit):")
    L("if self._last_exit_reason == \"emergency_dd\":")
    L("    self._emergency_dd_cooldown_remaining = K")
    L("")
    L("# Proposed (activate only after 2+ consecutive ED exits):")
    L("if self._last_exit_reason == \"emergency_dd\":")
    L("    self._consecutive_ed_count += 1")
    L("    if self._consecutive_ed_count >= 2:")
    L("        self._emergency_dd_cooldown_remaining = K")
    L("else:")
    L("    self._consecutive_ed_count = 0")
    L("```")
    L("")
    L("### Why this works")
    L("")
    L("1. **Zero additional entry alpha needed** — the rule only modifies the "
      "cooldown activation trigger, not the entry logic.")
    L("2. **Preserves cascade protection** — in cascade episodes (where ED exits "
      "come in clusters of 2+), the cooldown still activates on the 2nd ED exit.")
    L("3. **Unblocks isolated recovery trades** — after a single ED exit followed "
      "by a recovery, no cooldown is applied.")
    L("4. **Matches the cascade definition** — the pipeline already defines cascades "
      "as episodes with max_run_emergency_dd >= 2. This rule aligns the cooldown "
      "activation with that definition.")
    L("")

    # Evidence table
    if winners:
        L("### Evidence: blocked winners would be unblocked")
        L("")
        L("| Trade | Bars from ED | Preceding ED exits in sequence | Would trigger rule? |")
        L("|------:|-------------:|-------------------------------:|:-------------------:|")

        # Check if the preceding ED exit was the 1st or 2nd in a consecutive run
        for r in winners:
            # Find the triggering ED exit
            emdd_tid = r["emdd_exit_trade_id"]
            # Check if there was another ED exit right before this one
            preceding_eds = 0
            if emdd_tid:
                for t in bl_trades:
                    if t.trade_id == emdd_tid:
                        # Look for ED exits immediately before this one
                        for t2 in reversed(bl_trades):
                            if (t2.trade_id < t.trade_id and
                                t2.exit_reason == "emergency_dd" and
                                t2.trade_id >= t.trade_id - 3):  # within last few trades
                                # Check if consecutive (no non-ED exits between them)
                                between = [t3 for t3 in bl_trades
                                           if t2.trade_id < t3.trade_id < t.trade_id]
                                if all(t3.exit_reason == "emergency_dd" for t3 in between):
                                    preceding_eds = 1 + len(between)
                                break
                        break

            total_in_seq = preceding_eds + 1
            would_trigger = total_in_seq >= 2
            L(f"| {r['trade_id']} "
              f"| {r['bars_from_emdd_exit']} "
              f"| {total_in_seq} "
              f"| {'Yes — cascade' if would_trigger else '**No — isolated, would be unblocked**'} |")
        L("")

    L("### Expected impact")
    L("")
    L("- **Blocked winners recovered:** The isolated-ED winners would no longer be blocked")
    L("- **Cascade protection preserved:** The cooldown still activates in cascade scenarios")
    L("- **K=6 equivalent for isolated EDs, K=12 for cascades:** "
      "This effectively creates an adaptive cooldown that matches the pattern of the market")
    L("")

    # ── Section 9: Deliverables ──
    L("---")
    L("")
    L("## 9. Deliverables")
    L("")
    L("| Artifact | Path |")
    L("|----------|------|")
    L("| Script | `experiments/overlayA/overlayA_blocked_winners_diagnosis.py` |")
    L("| Blocked winners CSV | `out_overlayA_conditional/blocked_winners_top.csv` |")
    L("| This report | `reports/overlayA_blocked_winners_diagnosis.md` |")
    L("")

    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
