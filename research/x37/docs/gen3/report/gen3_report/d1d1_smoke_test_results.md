# D1d1 Smoke Test Results

Scope: candidate implementation and fold-1 smoke test only. No full WFO. No holdout or reserve data used.

## Implementation files
- `d1d_impl_H4Trend_H1Flow.py`
- `d1d_impl_H4Trend_H1Flow_no_trend4h.py`
- `d1d_impl_H4Trend_H1Flow_no_flow1h.py`
- `d1d_impl_D1Range_H4Flow.py`
- `d1d_impl_D1Range_H4Flow_no_day_range.py`
- `d1d_impl_D1Range_H4Flow_no_flow4h.py`
- `d1d_impl_M15ZRetTrail.py`

## Smoke test setup
- Fold: 1
- Train end (exclusive): 2020-01-01 00:00:00 UTC
- Test window: 2020-01-01 00:00:00 UTC to 2020-03-31 23:59:59 UTC
- Cost: 50 bps round-trip (25 bps per side)
- Execution: signal on bar close, fill on next bar open, UTC, no lookahead

## H4Trend_H1Flow

- Entries: 0
- Exits: 0
- Exposure: 0.000000
- Gross return: 0.000%
- Net return: 0.000%
- Cost events: 0
- Total applied cost: 0.000000
- Expected total cost: 0.000000
- Cost application check: PASS
- Next-open timestamp check: PASS
- No-lookahead check: PASS
- Zero-trade diagnostic: entry threshold 0.066975; max observed test flow 0.033053; max observed flow while permission on 0.033053

## D1Range_H4Flow

- Entries: 0
- Exits: 0
- Exposure: 0.000000
- Gross return: 0.000%
- Net return: 0.000%
- Cost events: 0
- Total applied cost: 0.000000
- Expected total cost: 0.000000
- Cost application check: PASS
- Next-open timestamp check: PASS
- No-lookahead check: PASS
- Zero-trade diagnostic: entry threshold 0.066908; max observed test flow 0.044911; max observed flow while permission on 0.044911

## M15ZRetTrail

- Entries: 92
- Exits: 92
- Exposure: 0.284565
- Gross return: 12.782%
- Net return: -29.036%
- Cost events: 184
- Total applied cost: 0.460000
- Expected total cost: 0.460000
- Cost application check: PASS
- Next-open timestamp check: PASS
- No-lookahead check: PASS
- First trade example: entry signal close `2020-01-01 04:14:59.999000+00:00`, entry fill `2020-01-01 04:15:00+00:00`, exit signal close `2020-01-01 08:14:59.999000+00:00`, exit fill `2020-01-01 08:15:00+00:00`

## Ablation runtime check
- `H4Trend_H1Flow_no_trend4h`: entries=0, exits=0, exposure=0.000000, gross=0.000%, net=0.000%
- `H4Trend_H1Flow_no_flow1h`: entries=5, exits=5, exposure=0.570510, gross=21.773%, net=18.764%
- `D1Range_H4Flow_no_day_range`: entries=0, exits=0, exposure=0.000000, gross=0.000%, net=0.000%
- `D1Range_H4Flow_no_flow4h`: entries=4, exits=4, exposure=0.594495, gross=16.907%, net=14.582%

All implementation files compiled successfully with `python -m py_compile` before smoke testing.