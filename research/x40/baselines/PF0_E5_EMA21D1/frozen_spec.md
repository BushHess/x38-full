# PF0_E5_EMA21D1 — Frozen Specification

Source: `research/x40/pf0_strategy.py` (self-contained, Pattern B).
Lineage: `strategies/vtrend_e5_ema21_d1/strategy.py` (original, parity verified 2026-03-28).

## Identity

- Strategy name: `vtrend_e5_ema21_d1`
- x40 baseline ID: `PF0_E5_EMA21D1`
- League: `PUBLIC_FLOW`
- Asset: BTC/USDT spot
- Direction: long-only (long/flat)
- Execution timeframe: H4 (signal at H4 close, fill at next H4 open)
- Tunable parameters: 4

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `slow_period` | 120.0 | EMA slow period on H4 (fast = slow // 4 = 30) |
| `trail_mult` | 3.0 | Robust ATR multiplier for trailing stop |
| `vdo_threshold` | 0.0 | Minimum VDO for entry (0.0 = any positive flow) |
| `d1_ema_period` | 21 | EMA period on D1 bars for regime filter |

## Entry conditions (ALL must be true)

1. `EMA(close, 30) > EMA(close, 120)` — H4 trend up
2. `VDO > 0.0` — taker buy pressure (EMA(vdr, 12) - EMA(vdr, 28))
3. `D1_close > D1_EMA(21)` — D1 regime filter (bullish regime)
4. Not in position

VDO requires real `taker_buy_base_vol` data. Raises RuntimeError without it.

## Exit conditions (ANY triggers exit)

1. **Trail stop**: `price < peak_price - 3.0 * robust_ATR`
2. **Trend reversal**: `EMA(close, 30) < EMA(close, 120)`

Robust ATR: cap TR at rolling 90th percentile (100-bar lookback), then Wilder EMA(20).

## D1→H4 mapping

For each H4 bar, use the most recent D1 bar whose `close_time < H4 close_time`.
Strict inequality prevents lookahead.

## Cost model

Simple per-side fraction (same model as OH0_D1_TREND40).

| Scenario | Per-side bps | RT bps | `cost_per_side` |
|----------|-------------|--------|-----------------|
| **default** | **10** | **20** | **0.001** |
| sweep: VIP | 5 | 10 | 0.0005 |
| sweep: base | 15 | 30 | 0.0015 |
| sweep: harsh | 25 | 50 | 0.0025 |
| sweep: extreme | 37.5 | 75 | 0.00375 |
| sweep: stress | 50 | 100 | 0.005 |

Default 20 bps RT is synchronized with OH0_D1_TREND40 for fair cross-baseline
comparison. Cost sweep [10, 20, 30, 50, 75, 100] bps RT for sensitivity analysis.

This is a **different cost model** from v10's spread+slippage+fee (CostConfig).
Signals are cost-independent (same 188 trades). Metrics differ slightly due to
multiplicative vs component-based cost application (< 2% at 50 bps).

## What this system requires

- H4 bars: close, high, low, open, volume, taker_buy_base_vol
- D1 bars: close, close_time (for EMA regime filter + D1→H4 mapping)
- Self-contained simulator (`research/x40/pf0_strategy.py`, Pattern B)
