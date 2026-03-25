# Frozen system specification — S_D1_TREND

## Evidence label
**INTERNAL ROBUST CANDIDATE**

## Architecture
- Layers: 1
- Logic type: single-feature state system
- Execution timeframe: native D1
- Long-only BTC/USDT spot
- Position sizing: 100% long when active, otherwise flat
- No leverage, no pyramiding, no discretionary overrides

## Feature
- Feature ID: `D1_MOM_RET`
- Family: `directional_persistence`
- Formula: `close_t / close_(t-40) - 1`
- Lookback: 40 D1 bars
- Tail: `high`
- Threshold mode: `sign`
- Threshold value: `0.0`
- Calibration mode: `fixed_structural`

## State machine
1. Compute the feature on the completed D1 close.
2. If the feature is greater than 0, set state to **long**.
3. Otherwise set state to **flat**.
4. Execute the resulting state at the **next D1 open**.
5. Deduct 10 bps per side whenever position changes.

## Execution assumptions
- Market: BTC/USDT spot
- Signal timing: bar close
- Fill model: next bar open
- Trading cost: 10 bps per side, 20 bps round-trip
- Warmup: no live trading before 2020-01-01
- Timestamps interpreted as UTC

## Why this system won pre-reserve
- `S_H4_TREND_Q` did **not** show a meaningful paired daily-return advantage over simpler `S_H4_TREND`.
- `S_XR_D1ROLL` did **not** show a meaningful paired daily-return advantage over simpler `S_XR_D1EMA`.
- Neither retained more operationally complex rival (`S_H4_TREND`, `S_XR_D1EMA`) showed a meaningful paired daily-return advantage over `S_D1_TREND` on the pre-reserve common daily domain.
- `S_D1_TREND` remained the simplest native single-timeframe leader, had the highest pre-reserve mean daily return among cluster winners, and showed the strongest cost resilience.

## Key results
### Discovery walk-forward (2020-01-01 to 2023-06-30)
- Daily Sharpe: 1.6941
- CAGR: 1.0123
- Max drawdown: -0.4832
- Trades: 61
- Positive discovery-fold share: 0.6429

### Candidate-selection holdout (2023-07-01 to 2024-09-30)
- Daily Sharpe: 1.0819
- CAGR: 0.4082
- Max drawdown: -0.4337
- Trades: 34

### Reserve/internal (2024-10-01 to dataset end)
- Daily Sharpe: 0.8734
- CAGR: 0.2416
- Max drawdown: -0.2401
- Trades: 35

## Finality
This V8 run is the final same-file audit on the current BTC/USDT file pair. After reserve/internal evaluation is reported, same-file prompt iteration stops; stronger claims require appended future data.
