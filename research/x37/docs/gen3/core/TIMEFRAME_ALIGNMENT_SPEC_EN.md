# Timeframe Alignment Specification

This document defines the exact rules for multi-timeframe (MTF) data alignment in gen3 research.
These rules are derived from the btc-spot-dev engine (`v10/core/engine.py`) and locked by its test suite (`v10/tests/test_mtf_alignment.py`).

## Core rule

At each evaluation bar on timeframe T_fast, the latest available bar on timeframe T_slow is the most recent T_slow bar whose `close_time` is **strictly less than** the current T_fast bar's `close_time`.

```
visible_slow_bar = latest bar where slow.close_time < fast.close_time
```

Strict `<` (not `<=`) prevents same-candle lookahead at period boundaries.

## H4 → D1 alignment (primary production case)

The engine iterates over H4 bars. For each H4 bar, the latest D1 bar visible satisfies:

```
d1.close_time < h4.close_time
```

### Concrete example (UTC, Binance kline timestamps)

| Day | H4 slot | H4 close_time | Latest visible D1 | D1 close_time |
|-----|---------|---------------|-------------------|---------------|
| 0 | 0–5 | 04h–24h (−1ms) | None | — |
| 1 | 0–5 | 28h–48h (−1ms) | D1 day 0 | 24h (−1ms) |
| 2 | 0–5 | 52h–72h (−1ms) | D1 day 1 | 48h (−1ms) |

**Key boundary**: The last H4 bar of day N and the D1 bar of day N share the same `close_time` (both close at midnight UTC minus 1ms). Strict `<` means the last H4 of day N does **not** see D1 of day N — it sees D1 of day N−1.

**Effective rule in plain language**: A D1 bar completed today becomes visible to H4 bars starting from the first H4 bar of tomorrow. There is always a 1-bar (4-hour) minimum lag at boundaries.

### Day 0 special case

On the first day of data (day 0), no D1 bar has closed yet. The engine sets `d1_index = -1`. Strategies must handle `d1_index < 0` gracefully (e.g., skip signals until D1 context is available).

## General rule for any T_fast → T_slow pair

The same `slow.close_time < fast.close_time` rule applies to all timeframe pairs:

| Fast | Slow | Rule |
|------|------|------|
| H4 | D1 | `d1.close_time < h4.close_time` |
| 1h | H4 | `h4.close_time < h1.close_time` |
| 1h | D1 | `d1.close_time < h1.close_time` |
| 15m | 1h | `h1.close_time < m15.close_time` |
| 15m | H4 | `h4.close_time < m15.close_time` |
| 15m | D1 | `d1.close_time < m15.close_time` |

## Timestamp conventions

- All timestamps are integer milliseconds since Unix epoch, UTC.
- Binance `close_time` = `open_time + interval_ms - 1` (inclusive of the last millisecond).
- `open_time` is the start of the bar; `close_time` is the end.
- No timezone conversion is applied; all computation uses UTC.

## Pending signals at evaluation window boundaries

When a signal fires on the last bar of an evaluation window:

1. The signal is **recorded** (it happened during this window).
2. The corresponding fill has **not yet occurred** (next-open execution: fill happens at the open of the next bar, which is in the next window).
3. The next session reconstructs this pending state by replaying warmup bars that overlap the signal bar, or by loading it from `portfolio_state.json` field `additional_state`.
4. The `reconstructable_from_warmup_only` flag indicates whether warmup replay alone is sufficient.

## What this spec does NOT cover

- **Feature computation lookback**: Rolling features (e.g., EMA, ATR) computed on a single timeframe do not involve MTF alignment — they use the bar's own history. This spec only governs cross-timeframe data access.
- **Signal-to-fill timing**: Next-open execution semantics are specified in the constitution, not here. This spec only governs which slow-TF bar is visible at which fast-TF bar.

## Verification

The engine's MTF alignment is tested by `v10/tests/test_mtf_alignment.py` (6 test classes, 8 test methods) covering:
- No D1 visible on day 0
- Day boundary strict `<` enforcement
- Full d1_index mapping across multiple days
- mtf_map output consistency
- Graceful handling when no D1 bars exist
- Lookahead-sensitive strategy proving lagged D1 access

Any gen3 candidate implementation must comply with these rules. The D1d1 smoke test should verify that cross-timeframe access follows strict `<` alignment.
