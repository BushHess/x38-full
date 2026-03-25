#!/usr/bin/env python3
"""Double Compression False Exit Analysis for V10.

Measures whether double compression (ATR contraction + multiplier tightening)
causes significantly more false exits than single compression or normal conditions.

Definitions:
- Noise zone: trail distance < median(ATR%) for that regime period.
  Specifically, trail_distance_pct = (mult * ATR) / peak_price < threshold.
  We use a dynamic threshold: rolling median of (3.5 * ATR / close) over 90 bars.
  If trail_distance_pct < threshold, the exit bar is "in noise zone".

- Double compression: exit where BOTH conditions hold:
  1) Tightened multiplier active (peak_profit >= 20% → mult = 2.5)
  2) ATR is compressed (ATR_pct < rolling_median(ATR_pct, 90))

- False exit: trailing stop exit where price continues in favorable direction.
  For long-only: false exit = price rises significantly after exit.
  Measured as: max(close[t+1..t+N]) / exit_price - 1 > continuation_threshold
  Horizon N = 15 bars (60 hours = 2.5 days, ~fast enough to matter on H4).
  Continuation threshold = 3% (meaningful move BTC would have captured).

Output: false exit rates by compression type, per-regime breakdown, visualizations.
"""

import csv
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np

# ── Paths ──────────────────────────────────────────────────────────────────
BASE = Path("/var/www/trading-bots/btc-spot-dev")
BAR_FILE = BASE / "data/bars_btcusdt_2016_now_h1_4h_1d.csv"
TRADE_FILE = BASE / "out_v10_trail_tighten/candidates/baseline_legacy/base/trades.csv"
OUT_DIR = BASE / "out_v10_trail_tighten/double_compression_analysis"

# ── Strategy params ────────────────────────────────────────────────────────
ATR_PERIOD = 14
TRAIL_ATR_MULT = 3.5
TRAIL_TIGHTEN_MULT = 2.5
TRAIL_ACTIVATE_PCT = 0.05
TRAIL_TIGHTEN_PROFIT_PCT = 0.20

# ── Analysis params ────────────────────────────────────────────────────────
FALSE_EXIT_HORIZON = 15          # H4 bars to look ahead (60h)
FALSE_EXIT_THRESHOLD = 0.03     # 3% continuation = false exit
NOISE_ZONE_LOOKBACK = 90        # rolling window for ATR% median
ATR_COMPRESSED_QUANTILE = 0.5   # below median = compressed


# ── Data structures ────────────────────────────────────────────────────────
@dataclass
class Bar:
    open_time: int
    close_time: int
    open: float
    high: float
    low: float
    close: float
    volume: float

@dataclass
class Trade:
    trade_id: int
    entry_time: str
    exit_time: str
    entry_ts_ms: int
    exit_ts_ms: int
    entry_price: float
    exit_price: float
    qty: float
    pnl: float
    return_pct: float
    days_held: float
    entry_reason: str
    exit_reason: str


# ── Regime classifier (standalone, mirrors v10/research/regime.py) ─────────
def _ema(arr, period):
    out = np.empty(len(arr))
    out[0] = arr[0]
    alpha = 2.0 / (period + 1.0)
    for i in range(1, len(arr)):
        out[i] = alpha * arr[i] + (1.0 - alpha) * out[i - 1]
    return out

def _atr(highs, lows, closes, period):
    n = len(closes)
    tr = np.empty(n)
    tr[0] = highs[0] - lows[0]
    for i in range(1, n):
        tr[i] = max(highs[i] - lows[i],
                     abs(highs[i] - closes[i-1]),
                     abs(lows[i] - closes[i-1]))
    out = np.empty(n)
    out[0] = tr[0]
    alpha = 1.0 / period
    for i in range(1, n):
        out[i] = alpha * tr[i] + (1.0 - alpha) * out[i - 1]
    return out

def _adx(highs, lows, closes, period=14):
    n = len(closes)
    if n < 2:
        return np.zeros(n)
    pdm = np.zeros(n)
    ndm = np.zeros(n)
    for i in range(1, n):
        up = highs[i] - highs[i-1]
        down = lows[i-1] - lows[i]
        if up > down and up > 0: pdm[i] = up
        if down > up and down > 0: ndm[i] = down
    atr_arr = _atr(highs, lows, closes, period)
    alpha = 1.0 / period
    s_pdm = np.empty(n); s_ndm = np.empty(n)
    s_pdm[0] = pdm[0]; s_ndm[0] = ndm[0]
    for i in range(1, n):
        s_pdm[i] = alpha * pdm[i] + (1.0 - alpha) * s_pdm[i-1]
        s_ndm[i] = alpha * ndm[i] + (1.0 - alpha) * s_ndm[i-1]
    with np.errstate(divide='ignore', invalid='ignore'):
        pdi = np.where(atr_arr > 1e-12, 100 * s_pdm / atr_arr, 0)
        ndi = np.where(atr_arr > 1e-12, 100 * s_ndm / atr_arr, 0)
    di_sum = pdi + ndi
    with np.errstate(divide='ignore', invalid='ignore'):
        dx = np.where(di_sum > 1e-12, 100 * np.abs(pdi - ndi) / di_sum, 0)
    adx_out = np.empty(n); adx_out[0] = dx[0]
    for i in range(1, n):
        adx_out[i] = alpha * dx[i] + (1.0 - alpha) * adx_out[i-1]
    return adx_out

def classify_d1_regimes(d1_bars):
    """Classify D1 bars into regimes. Returns list of regime strings."""
    n = len(d1_bars)
    closes = np.array([b.close for b in d1_bars])
    highs = np.array([b.high for b in d1_bars])
    lows = np.array([b.low for b in d1_bars])
    ema_f = _ema(closes, 50)
    ema_s = _ema(closes, 200)
    atr_arr = _atr(highs, lows, closes, 14)
    adx_arr = _adx(highs, lows, closes, 14)
    regimes = []
    for i in range(n):
        c = closes[i]
        daily_ret_pct = abs((c / closes[i-1] - 1) * 100) if i > 0 else 0
        if daily_ret_pct > 8.0:
            regimes.append("SHOCK"); continue
        if c < ema_s[i] and ema_f[i] < ema_s[i]:
            regimes.append("BEAR"); continue
        atr_pct = (atr_arr[i] / c * 100) if c > 1e-12 else 0
        if atr_pct > 3.5 and adx_arr[i] < 20:
            regimes.append("CHOP"); continue
        dist_pct = abs(c - ema_f[i]) / ema_f[i] * 100 if ema_f[i] > 1e-12 else 0
        if dist_pct < 1.0 and adx_arr[i] < 25:
            regimes.append("TOPPING"); continue
        if c > ema_s[i] and ema_f[i] > ema_s[i]:
            regimes.append("BULL"); continue
        regimes.append("NEUTRAL")
    return regimes


# ── Load data ──────────────────────────────────────────────────────────────
def load_h4_bars():
    bars = []
    with open(BAR_FILE) as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["interval"] != "4h":
                continue
            bars.append(Bar(
                open_time=int(row["open_time"]),
                close_time=int(row["close_time"]),
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=float(row["volume"]),
            ))
    bars.sort(key=lambda b: b.open_time)
    return bars

def load_d1_bars():
    bars = []
    with open(BAR_FILE) as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["interval"] != "1d":
                continue
            bars.append(Bar(
                open_time=int(row["open_time"]),
                close_time=int(row["close_time"]),
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=float(row["volume"]),
            ))
    bars.sort(key=lambda b: b.open_time)
    return bars

def load_trades():
    trades = []
    with open(TRADE_FILE) as f:
        reader = csv.DictReader(f)
        for row in reader:
            trades.append(Trade(
                trade_id=int(row["trade_id"]),
                entry_time=row["entry_time"],
                exit_time=row["exit_time"],
                entry_ts_ms=int(row["entry_ts_ms"]),
                exit_ts_ms=int(row["exit_ts_ms"]),
                entry_price=float(row["entry_price"]),
                exit_price=float(row["exit_price"]),
                qty=float(row["qty"]),
                pnl=float(row["pnl"]),
                return_pct=float(row["return_pct"]),
                days_held=float(row["days_held"]),
                entry_reason=row["entry_reason"],
                exit_reason=row["exit_reason"],
            ))
    return trades


# ── Core analysis ──────────────────────────────────────────────────────────
def compute_h4_atr(h4_bars):
    """Compute ATR(14) on H4 bars. Returns array same length as h4_bars."""
    highs = np.array([b.high for b in h4_bars])
    lows = np.array([b.low for b in h4_bars])
    closes = np.array([b.close for b in h4_bars])
    return _atr(highs, lows, closes, ATR_PERIOD)

def find_bar_index(h4_bars, ts_ms):
    """Find the H4 bar index closest to a given timestamp (ms)."""
    # Binary search on close_time
    lo, hi = 0, len(h4_bars) - 1
    best = 0
    while lo <= hi:
        mid = (lo + hi) // 2
        if h4_bars[mid].close_time <= ts_ms:
            best = mid
            lo = mid + 1
        else:
            hi = mid - 1
    return best

def find_d1_bar_index(d1_bars, ts_ms):
    """Find the D1 bar index for a given timestamp."""
    lo, hi = 0, len(d1_bars) - 1
    best = 0
    while lo <= hi:
        mid = (lo + hi) // 2
        if d1_bars[mid].close_time <= ts_ms:
            best = mid
            lo = mid + 1
        else:
            hi = mid - 1
    return best


def analyze():
    print("Loading H4 bars...")
    h4_bars = load_h4_bars()
    print(f"  Loaded {len(h4_bars)} H4 bars")

    print("Loading D1 bars...")
    d1_bars = load_d1_bars()
    print(f"  Loaded {len(d1_bars)} D1 bars")

    print("Classifying D1 regimes...")
    d1_regimes = classify_d1_regimes(d1_bars)

    print("Loading trades...")
    trades = load_trades()
    print(f"  Loaded {len(trades)} trades")

    print("Computing H4 ATR...")
    h4_atr = compute_h4_atr(h4_bars)
    h4_closes = np.array([b.close for b in h4_bars])

    # ATR as % of price
    atr_pct = h4_atr / h4_closes * 100

    # Rolling median of "normal trail distance %" = (3.5 * ATR) / close * 100
    normal_trail_pct = TRAIL_ATR_MULT * h4_atr / h4_closes * 100

    # Rolling median of ATR%
    rolling_atr_pct_median = np.full(len(h4_bars), np.nan)
    for i in range(NOISE_ZONE_LOOKBACK, len(h4_bars)):
        window = atr_pct[i - NOISE_ZONE_LOOKBACK:i]
        rolling_atr_pct_median[i] = np.median(window)

    # ── Classify each trailing_stop exit ───────────────────────────────────
    trail_exits = [t for t in trades if t.exit_reason == "trailing_stop"]
    print(f"\nTrailing stop exits: {len(trail_exits)} / {len(trades)} total trades")

    results = []
    for trade in trail_exits:
        exit_idx = find_bar_index(h4_bars, trade.exit_ts_ms)
        entry_idx = find_bar_index(h4_bars, trade.entry_ts_ms)

        if exit_idx >= len(h4_bars) - 1:
            continue  # can't look ahead

        # Reconstruct peak_profit from trade data
        # We need to trace through bars to find peak_price during the trade
        peak_price = trade.entry_price
        for i in range(entry_idx, min(exit_idx + 1, len(h4_bars))):
            # Use high of each bar as proxy for potential peak
            peak_price = max(peak_price, h4_bars[i].high)

        peak_profit = (peak_price - trade.entry_price) / trade.entry_price

        # Determine which multiplier was active at exit
        if peak_profit >= TRAIL_TIGHTEN_PROFIT_PCT:
            mult_used = TRAIL_TIGHTEN_MULT
            tightened = True
        else:
            mult_used = TRAIL_ATR_MULT
            tightened = False

        # ATR at exit bar
        atr_at_exit = h4_atr[exit_idx]
        atr_pct_at_exit = atr_pct[exit_idx]

        # Trail distance at exit
        trail_dist = mult_used * atr_at_exit
        trail_dist_pct = trail_dist / peak_price * 100 if peak_price > 0 else 0

        # Is ATR compressed? (below rolling median)
        atr_compressed = False
        if not np.isnan(rolling_atr_pct_median[exit_idx]):
            atr_compressed = atr_pct_at_exit < rolling_atr_pct_median[exit_idx]

        # Compression category
        if tightened and atr_compressed:
            compression = "DOUBLE"      # both mult tightened + ATR compressed
        elif tightened:
            compression = "MULT_ONLY"   # only mult tightened (high profit)
        elif atr_compressed:
            compression = "ATR_ONLY"    # only ATR compressed (vol low)
        else:
            compression = "NONE"        # neither

        # Noise zone: trail distance % below rolling median of normal trail %
        in_noise_zone = False
        if not np.isnan(rolling_atr_pct_median[exit_idx]):
            # Compare actual trail distance % to what "normal" trail would be
            normal_trail_at_exit = TRAIL_ATR_MULT * h4_atr[exit_idx] / h4_closes[exit_idx] * 100
            # noise zone = trail dist < 50th percentile of recent normal trail
            median_normal = np.nan
            if exit_idx >= NOISE_ZONE_LOOKBACK:
                window = normal_trail_pct[exit_idx - NOISE_ZONE_LOOKBACK:exit_idx]
                median_normal = np.median(window)
            if not np.isnan(median_normal):
                in_noise_zone = trail_dist_pct < median_normal

        # Look-ahead: was this a false exit?
        # Check max close in next N bars
        ahead_end = min(exit_idx + 1 + FALSE_EXIT_HORIZON, len(h4_bars))
        if ahead_end > exit_idx + 1:
            future_closes = h4_closes[exit_idx + 1:ahead_end]
            future_highs = np.array([h4_bars[i].high for i in range(exit_idx + 1, ahead_end)])
            max_future_close = float(np.max(future_closes))
            max_future_high = float(np.max(future_highs))
            continuation = max_future_close / trade.exit_price - 1
            continuation_high = max_future_high / trade.exit_price - 1
        else:
            continuation = 0.0
            continuation_high = 0.0

        is_false_exit = continuation >= FALSE_EXIT_THRESHOLD

        # Get regime at exit
        d1_idx = find_d1_bar_index(d1_bars, trade.exit_ts_ms)
        regime = d1_regimes[d1_idx] if 0 <= d1_idx < len(d1_regimes) else "UNKNOWN"

        # Forgone profit: how much more the trade could have made
        forgone_pct = continuation_high * 100  # % above exit price

        results.append({
            "trade_id": trade.trade_id,
            "exit_time": trade.exit_time,
            "entry_price": trade.entry_price,
            "exit_price": trade.exit_price,
            "peak_price": round(peak_price, 2),
            "peak_profit_pct": round(peak_profit * 100, 2),
            "return_pct": trade.return_pct,
            "mult_used": mult_used,
            "tightened": tightened,
            "atr_at_exit": round(atr_at_exit, 2),
            "atr_pct": round(atr_pct_at_exit, 3),
            "atr_compressed": atr_compressed,
            "trail_dist_pct": round(trail_dist_pct, 3),
            "in_noise_zone": in_noise_zone,
            "compression": compression,
            "continuation_pct": round(continuation * 100, 2),
            "continuation_high_pct": round(continuation_high * 100, 2),
            "is_false_exit": is_false_exit,
            "forgone_pct": round(forgone_pct, 2),
            "regime": regime,
            "days_held": trade.days_held,
        })

    # ── Print results ──────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("DOUBLE COMPRESSION FALSE EXIT ANALYSIS — V10 BASELINE")
    print("=" * 80)

    print(f"\nParameters:")
    print(f"  False exit horizon: {FALSE_EXIT_HORIZON} H4 bars ({FALSE_EXIT_HORIZON * 4}h)")
    print(f"  False exit threshold: {FALSE_EXIT_THRESHOLD * 100:.0f}% continuation")
    print(f"  ATR compressed: below rolling {NOISE_ZONE_LOOKBACK}-bar median")
    print(f"  Trail tightened: peak_profit >= {TRAIL_TIGHTEN_PROFIT_PCT * 100:.0f}%")

    total_trail = len(results)
    total_false = sum(1 for r in results if r["is_false_exit"])
    print(f"\nTotal trailing stop exits analyzed: {total_trail}")
    print(f"Total false exits (>{FALSE_EXIT_THRESHOLD*100:.0f}% continuation): {total_false} ({total_false/total_trail*100:.1f}%)")

    # ── By compression type ────────────────────────────────────────────────
    print(f"\n{'─' * 80}")
    print("FALSE EXIT RATE BY COMPRESSION TYPE")
    print(f"{'─' * 80}")
    print(f"{'Type':<15} {'Exits':>6} {'False':>6} {'Rate':>8} {'Avg Forg%':>10} {'Avg Trail%':>11}")
    print(f"{'─' * 15} {'─' * 6} {'─' * 6} {'─' * 8} {'─' * 10} {'─' * 11}")

    for ctype in ["DOUBLE", "MULT_ONLY", "ATR_ONLY", "NONE"]:
        subset = [r for r in results if r["compression"] == ctype]
        n = len(subset)
        if n == 0:
            print(f"{ctype:<15} {'0':>6} {'—':>6} {'—':>8} {'—':>10} {'—':>11}")
            continue
        false_n = sum(1 for r in subset if r["is_false_exit"])
        rate = false_n / n * 100
        avg_forgone = np.mean([r["forgone_pct"] for r in subset if r["is_false_exit"]]) if false_n > 0 else 0
        avg_trail = np.mean([r["trail_dist_pct"] for r in subset])
        print(f"{ctype:<15} {n:>6} {false_n:>6} {rate:>7.1f}% {avg_forgone:>9.1f}% {avg_trail:>10.2f}%")

    # ── By noise zone ──────────────────────────────────────────────────────
    print(f"\n{'─' * 80}")
    print("FALSE EXIT RATE: NOISE ZONE vs NORMAL")
    print(f"{'─' * 80}")
    for zone_name, zone_filter in [("In noise zone", True), ("Outside noise zone", False)]:
        subset = [r for r in results if r["in_noise_zone"] == zone_filter]
        n = len(subset)
        if n == 0:
            print(f"  {zone_name}: no exits")
            continue
        false_n = sum(1 for r in subset if r["is_false_exit"])
        rate = false_n / n * 100
        avg_forgone = np.mean([r["forgone_pct"] for r in subset if r["is_false_exit"]]) if false_n > 0 else 0
        print(f"  {zone_name}: {n} exits, {false_n} false ({rate:.1f}%), avg forgone {avg_forgone:.1f}%")

    # ── Per regime breakdown ───────────────────────────────────────────────
    print(f"\n{'─' * 80}")
    print("FALSE EXIT RATE BY REGIME × COMPRESSION")
    print(f"{'─' * 80}")
    regimes_seen = sorted(set(r["regime"] for r in results))
    print(f"{'Regime':<10} {'Comp Type':<12} {'Exits':>6} {'False':>6} {'Rate':>8} {'Avg Cont%':>10}")
    print(f"{'─' * 10} {'─' * 12} {'─' * 6} {'─' * 6} {'─' * 8} {'─' * 10}")
    for regime in regimes_seen:
        regime_subset = [r for r in results if r["regime"] == regime]
        for ctype in ["DOUBLE", "MULT_ONLY", "ATR_ONLY", "NONE"]:
            subset = [r for r in regime_subset if r["compression"] == ctype]
            n = len(subset)
            if n == 0:
                continue
            false_n = sum(1 for r in subset if r["is_false_exit"])
            rate = false_n / n * 100
            avg_cont = np.mean([r["continuation_pct"] for r in subset])
            print(f"{regime:<10} {ctype:<12} {n:>6} {false_n:>6} {rate:>7.1f}% {avg_cont:>9.1f}%")

    # ── Sensitivity analysis: different thresholds ─────────────────────────
    print(f"\n{'─' * 80}")
    print("SENSITIVITY: FALSE EXIT RATE AT DIFFERENT CONTINUATION THRESHOLDS")
    print(f"{'─' * 80}")
    for thresh in [0.02, 0.03, 0.05, 0.08, 0.10]:
        print(f"\n  Threshold: {thresh*100:.0f}%")
        for ctype in ["DOUBLE", "MULT_ONLY", "ATR_ONLY", "NONE"]:
            subset = [r for r in results if r["compression"] == ctype]
            n = len(subset)
            if n == 0:
                continue
            false_n = sum(1 for r in subset if r["continuation_pct"] >= thresh * 100)
            rate = false_n / n * 100
            print(f"    {ctype:<15} {false_n:>3}/{n:<3} = {rate:>6.1f}%")

    # ── Worst false exits (biggest forgone %) ──────────────────────────────
    print(f"\n{'─' * 80}")
    print("TOP 10 WORST FALSE EXITS (by forgone profit)")
    print(f"{'─' * 80}")
    false_exits = sorted(
        [r for r in results if r["is_false_exit"]],
        key=lambda r: -r["forgone_pct"]
    )[:10]
    print(f"{'ID':>4} {'Exit Time':<22} {'ExitPx':>10} {'PeakProf%':>10} {'Comp':>8} {'Forgone%':>9} {'Regime':<8}")
    for r in false_exits:
        print(f"{r['trade_id']:>4} {r['exit_time']:<22} {r['exit_price']:>10.2f} "
              f"{r['peak_profit_pct']:>9.1f}% {r['compression']:>8} {r['forgone_pct']:>8.1f}% {r['regime']:<8}")

    # ── Damage estimate: total forgone PnL from false exits ────────────────
    print(f"\n{'─' * 80}")
    print("DAMAGE ESTIMATE: FORGONE PROFIT FROM FALSE EXITS")
    print(f"{'─' * 80}")
    for ctype in ["DOUBLE", "MULT_ONLY", "ATR_ONLY", "NONE"]:
        false_subset = [r for r in results if r["compression"] == ctype and r["is_false_exit"]]
        if not false_subset:
            print(f"  {ctype:<15} no false exits")
            continue
        total_forgone = sum(r["forgone_pct"] for r in false_subset)
        avg_forgone = np.mean([r["forgone_pct"] for r in false_subset])
        print(f"  {ctype:<15} {len(false_subset)} false exits, "
              f"sum forgone {total_forgone:.1f}%, avg {avg_forgone:.1f}%")

    # ── Summary verdict ────────────────────────────────────────────────────
    double_subset = [r for r in results if r["compression"] == "DOUBLE"]
    double_n = len(double_subset)
    double_false = sum(1 for r in double_subset if r["is_false_exit"])
    double_rate = double_false / double_n * 100 if double_n > 0 else 0

    none_subset = [r for r in results if r["compression"] == "NONE"]
    none_n = len(none_subset)
    none_false = sum(1 for r in none_subset if r["is_false_exit"])
    none_rate = none_false / none_n * 100 if none_n > 0 else 0

    overall_rate = total_false / total_trail * 100 if total_trail > 0 else 0

    print(f"\n{'=' * 80}")
    print("VERDICT")
    print(f"{'=' * 80}")
    print(f"  Double compression false exit rate: {double_rate:.1f}% ({double_false}/{double_n})")
    print(f"  No compression false exit rate:     {none_rate:.1f}% ({none_false}/{none_n})")
    print(f"  Overall false exit rate:            {overall_rate:.1f}% ({total_false}/{total_trail})")

    if double_rate < 10:
        print(f"\n  → DOUBLE compression false exit rate < 10%: IGNORE (not a real problem)")
    elif double_rate < 20:
        print(f"\n  → DOUBLE compression false exit rate 10-20%: MONITOR")
    else:
        print(f"\n  → DOUBLE compression false exit rate > 20%: NEEDS FIX")

    if double_n > 0 and none_n > 0:
        ratio = double_rate / none_rate if none_rate > 0 else float('inf')
        print(f"  → Double vs None ratio: {ratio:.2f}x")

    # ── Save detailed results ──────────────────────────────────────────────
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(OUT_DIR / "exit_analysis.csv", "w", newline="") as f:
        if results:
            writer = csv.DictWriter(f, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)

    summary = {
        "total_trail_exits": total_trail,
        "total_false_exits": total_false,
        "overall_false_rate_pct": round(overall_rate, 2),
        "by_compression": {},
        "by_regime": {},
    }
    for ctype in ["DOUBLE", "MULT_ONLY", "ATR_ONLY", "NONE"]:
        subset = [r for r in results if r["compression"] == ctype]
        n = len(subset)
        false_n = sum(1 for r in subset if r["is_false_exit"])
        summary["by_compression"][ctype] = {
            "exits": n,
            "false_exits": false_n,
            "false_rate_pct": round(false_n / n * 100, 2) if n > 0 else 0,
        }
    for regime in regimes_seen:
        subset = [r for r in results if r["regime"] == regime]
        n = len(subset)
        false_n = sum(1 for r in subset if r["is_false_exit"])
        summary["by_regime"][regime] = {
            "exits": n,
            "false_exits": false_n,
            "false_rate_pct": round(false_n / n * 100, 2) if n > 0 else 0,
        }

    with open(OUT_DIR / "summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\n  Results saved to {OUT_DIR}/")

    # ── Generate visualization ─────────────────────────────────────────────
    generate_charts(results, h4_bars, h4_atr, atr_pct, rolling_atr_pct_median)

    return results


def generate_charts(results, h4_bars, h4_atr, atr_pct, rolling_median):
    """Generate matplotlib charts for the analysis."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
        from datetime import datetime
    except ImportError:
        print("\n  [matplotlib not available, skipping charts]")
        return

    fig, axes = plt.subplots(3, 2, figsize=(18, 14))
    fig.suptitle("V10 Double Compression False Exit Analysis", fontsize=14, fontweight='bold')

    # 1. Bar chart: false exit rate by compression type
    ax = axes[0, 0]
    ctypes = ["DOUBLE", "MULT_ONLY", "ATR_ONLY", "NONE"]
    rates = []
    counts = []
    for ct in ctypes:
        subset = [r for r in results if r["compression"] == ct]
        n = len(subset)
        fn = sum(1 for r in subset if r["is_false_exit"])
        rates.append(fn / n * 100 if n > 0 else 0)
        counts.append(n)

    colors = ['#e74c3c', '#f39c12', '#3498db', '#2ecc71']
    bars = ax.bar(ctypes, rates, color=colors, edgecolor='black', linewidth=0.5)
    for bar, rate, count in zip(bars, rates, counts):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                f'{rate:.1f}%\n(n={count})', ha='center', va='bottom', fontsize=9)
    ax.set_ylabel("False Exit Rate (%)")
    ax.set_title("False Exit Rate by Compression Type")
    ax.axhline(y=10, color='orange', linestyle='--', alpha=0.7, label='10% threshold')
    ax.axhline(y=20, color='red', linestyle='--', alpha=0.7, label='20% threshold')
    ax.legend(fontsize=8)

    # 2. Scatter: trail distance % vs continuation %
    ax = axes[0, 1]
    for ct, color in zip(ctypes, colors):
        subset = [r for r in results if r["compression"] == ct]
        if not subset:
            continue
        x = [r["trail_dist_pct"] for r in subset]
        y = [r["continuation_pct"] for r in subset]
        ax.scatter(x, y, c=color, label=ct, alpha=0.7, s=40, edgecolors='black', linewidth=0.3)
    ax.axhline(y=FALSE_EXIT_THRESHOLD * 100, color='red', linestyle='--', alpha=0.5, label=f'{FALSE_EXIT_THRESHOLD*100:.0f}% threshold')
    ax.set_xlabel("Trail Distance at Exit (%)")
    ax.set_ylabel("Continuation After Exit (%)")
    ax.set_title("Trail Distance vs Post-Exit Continuation")
    ax.legend(fontsize=7)

    # 3. Per-regime false exit rates (stacked)
    ax = axes[1, 0]
    regimes = sorted(set(r["regime"] for r in results))
    x_pos = np.arange(len(regimes))
    width = 0.2
    for i, ct in enumerate(ctypes):
        rates_regime = []
        for regime in regimes:
            subset = [r for r in results if r["regime"] == regime and r["compression"] == ct]
            n = len(subset)
            fn = sum(1 for r in subset if r["is_false_exit"])
            rates_regime.append(fn / n * 100 if n > 0 else 0)
        ax.bar(x_pos + i * width, rates_regime, width, label=ct, color=colors[i],
               edgecolor='black', linewidth=0.3)
    ax.set_xticks(x_pos + 1.5 * width)
    ax.set_xticklabels(regimes, fontsize=8)
    ax.set_ylabel("False Exit Rate (%)")
    ax.set_title("False Exit Rate by Regime × Compression")
    ax.axhline(y=20, color='red', linestyle='--', alpha=0.5)
    ax.legend(fontsize=7)

    # 4. Timeline: false exits on price chart
    ax = axes[1, 1]
    # Plot BTC price (sampled)
    step = max(1, len(h4_bars) // 2000)
    times = [datetime.utcfromtimestamp(h4_bars[i].close_time / 1000) for i in range(0, len(h4_bars), step)]
    prices = [h4_bars[i].close for i in range(0, len(h4_bars), step)]
    ax.plot(times, prices, color='gray', alpha=0.5, linewidth=0.5)

    # Mark exits
    for r in results:
        t = datetime.fromisoformat(r["exit_time"].replace("Z", "+00:00")).replace(tzinfo=None)
        color = '#e74c3c' if r["compression"] == "DOUBLE" else \
                '#f39c12' if r["compression"] == "MULT_ONLY" else \
                '#3498db' if r["compression"] == "ATR_ONLY" else '#2ecc71'
        marker = 'x' if r["is_false_exit"] else 'o'
        size = 80 if r["is_false_exit"] else 30
        ax.scatter([t], [r["exit_price"]], c=color, marker=marker, s=size,
                   alpha=0.8, edgecolors='black', linewidth=0.3)
    ax.set_ylabel("BTC Price (USD)")
    ax.set_title("Exit Locations on Price (x = false exit)")
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
    ax.tick_params(axis='x', rotation=45)

    # 5. Distribution of continuation % by compression type
    ax = axes[2, 0]
    data_for_box = []
    labels_for_box = []
    for ct in ctypes:
        subset = [r["continuation_pct"] for r in results if r["compression"] == ct]
        if subset:
            data_for_box.append(subset)
            labels_for_box.append(ct)
    if data_for_box:
        bp = ax.boxplot(data_for_box, labels=labels_for_box, patch_artist=True)
        for patch, color in zip(bp['boxes'], colors[:len(data_for_box)]):
            patch.set_facecolor(color)
            patch.set_alpha(0.6)
    ax.axhline(y=FALSE_EXIT_THRESHOLD * 100, color='red', linestyle='--', alpha=0.5)
    ax.set_ylabel("Post-Exit Continuation (%)")
    ax.set_title("Distribution of Continuation by Compression Type")

    # 6. Sensitivity curves
    ax = axes[2, 1]
    thresholds = np.arange(1, 16, 0.5)
    for ct, color in zip(ctypes, colors):
        subset = [r for r in results if r["compression"] == ct]
        if not subset:
            continue
        rates_curve = []
        for th in thresholds:
            fn = sum(1 for r in subset if r["continuation_pct"] >= th)
            rates_curve.append(fn / len(subset) * 100)
        ax.plot(thresholds, rates_curve, color=color, label=ct, linewidth=2)
    ax.axhline(y=10, color='orange', linestyle='--', alpha=0.5, label='10%')
    ax.axhline(y=20, color='red', linestyle='--', alpha=0.5, label='20%')
    ax.set_xlabel("Continuation Threshold (%)")
    ax.set_ylabel("False Exit Rate (%)")
    ax.set_title("Sensitivity: False Exit Rate vs Threshold")
    ax.legend(fontsize=7)

    plt.tight_layout()
    chart_path = OUT_DIR / "double_compression_analysis.png"
    fig.savefig(chart_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"\n  Chart saved to {chart_path}")


if __name__ == "__main__":
    analyze()
