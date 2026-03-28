# PF0_E5_EMA21D1 — Source Reference

## Authoritative implementation

| Field | Value |
|-------|-------|
| Implementation | `research/x40/pf0_strategy.py` (self-contained, Pattern B) |
| League | `PUBLIC_FLOW` |
| x40 role | Incumbent |

`pf0_strategy.py` is the **sole authoritative code** for PF0 within x40.
It does NOT import from `strategies/` or `v10/core/engine.py`.

## Lineage

| Field | Value |
|-------|-------|
| Original source | `strategies/vtrend_e5_ema21_d1/strategy.py` |
| Original SHA256 | `d9d1a10bd1b6bc9ec14e6cbee12f8f52a68905b83deb39d6411901bdaa49b4d9` |
| Parity verified | 2026-03-28 |
| Parity method | Trade count exact (188), signal timing identical |
| Parity note | Metrics differ slightly at 50 bps due to cost model (simple per-side vs v10 spread+slip+fee) |

The lineage source hash is checked informally in A00 for drift detection.
If `strategies/vtrend_e5_ema21_d1/strategy.py` changes, A00 logs a NOTE but
does NOT fail — x40 is self-contained.

## Source snapshot

- Data: `data/bars_btcusdt_2016_now_h1_4h_1d.csv` (H4 + D1)
- Coverage: 2017-08 through 2026-02-20
- Start: 2019-01-01 (with 365-day warmup)
- End: 2026-02-20

## Data surface used by logic

OHLCV + `taker_buy_base_vol` (for VDO computation).

This is NOT OHLCV-only. The VDO oscillator requires real taker data and will
raise RuntimeError if taker data is missing (fail-closed by design).

## Cost model

Simple per-side fraction, **default 20 bps RT** (10 bps/side).
Synchronized with OH0_D1_TREND40 for fair cross-baseline comparison.
See `frozen_spec.md` for full sweep table.

## Verification targets (default 20 bps RT, pf0_strategy.py)

These are the reference numbers at the default cost. Updated after initial
parity run. Exact values depend on pf0_strategy.py — re-run A00 to refresh.

### At 20 bps RT (default)

| Metric | Value |
|--------|-------|
| Sharpe | 1.6634 |
| CAGR | 74.88% |
| MDD | 36.30% |
| Trades | 188 |
| Win rate | 44.15% |
| Avg exposure | 0.4448 |
| Profit factor | 1.8965 |

### At 50 bps RT (lineage parity reference)

| Metric | v10 target | pf0_strategy | diff |
|--------|-----------|--------------|------|
| Trades | 188 | 188 | exact |
| Sharpe | 1.4545 | 1.4541 | 0.03% |
| CAGR | 61.60% | 61.57% | 0.04% |
| MDD | 40.97% | 40.98% | 0.02% |
| Win rate | 42.02% | 42.02% | 0.00% |

Near-perfect parity despite different cost models. Trade count exact because
signals are cost-independent.

## Source metric domain

- Sharpe: H4 NAV returns, `mean/std(ddof=0) * sqrt(2190)` — matches v10
- CAGR: `(final_nav/start_nav)^(1/years) - 1`
- MDD: `(1 - nav/peak).max()` on NAV series

## Parameters (frozen)

| Parameter | Value | Type |
|-----------|-------|------|
| slow_period | 120 | tunable |
| trail_mult | 3.0 | tunable |
| vdo_threshold | 0.0 | tunable |
| d1_ema_period | 21 | tunable |
| fast_period | 30 | derived (slow // 4) |
| vdo_fast | 12 | structural |
| vdo_slow | 28 | structural |
| ratr_cap_q | 0.90 | structural |
| ratr_cap_lb | 100 | structural |
| ratr_period | 20 | structural |

## Implementation notes for x40

PF0 uses **Pattern B** (vectorized indicators + sequential position loop),
same pattern as OH0. This replaced the previous Pattern A (BacktestEngine +
VTrendE5Ema21D1Strategy import) to achieve full self-containment.

Key implementation details:
- Indicators (_ema, _robust_atr, _vdo, _map_d1_regime) copied from original
  strategy code for self-containment — no import from `strategies/`.
- Signal generation matches v10 on_bar logic: evaluate at bar close, pending
  signal executes at next bar open.
- Warmup handling: indicators computed on all bars, signals only from first
  bar where close_time >= report_start (default 2019-01-01, matching v10).
- NAV tracking: cash + btc * close_price at each bar close.

## Known non-authoritative documents

The VTREND_BLUEPRINT and production validation artifacts are historical context.
`pf0_strategy.py` is the single source of truth for PF0 behavior within x40.
