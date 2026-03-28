# OH0_D1_TREND40 — Frozen Specification

Ported verbatim from `research/x37/resource/gen1/v8_sd1trebd/spec/spec_2_system_S_D1_TREND.md`.

## Identity

- System ID: `S_D1_TREND`
- x40 baseline ID: `OH0_D1_TREND40`
- League: `OHLCV_ONLY`
- Asset: BTC/USDT spot
- Direction: long-only (long/flat)
- Execution timeframe: native D1
- Parameters: 0 tunable (lookback=40 is structural)

## Signal

```
D1_MOM_RET(n=40) = close_t / close_{t-40} - 1

signal = LONG  if D1_MOM_RET(40) > 0.0
signal = FLAT  if D1_MOM_RET(40) <= 0.0   (equality = flat)
signal = UNDEF if fewer than 40 prior completed bars
```

## Execution

- Observe signal at D1 bar close
- Apply position at next D1 bar open
- 100% long or 0% flat (no fractional sizing)
- No live trades before 2020-01-01

## Cost model

- 10 bps per side / 20 bps round-trip (canonical)
- Entry: `mult = (1 - 0.001) * (next_open / open)`
- Hold: `mult = next_open / open`
- Exit: `mult = 1 - 0.001`
- Flat: `mult = 1.0`

## What this system does NOT have

- No regime gate
- No volatility filter
- No cross-timeframe dependence
- No parameter calibration from data
- No H4 data dependency
- No VDO / taker data dependency

## Pseudocode (from frozen spec §7)

```python
for i in range(len(rows)):
    if i < 40:
        mom40[i] = NaN
        signal[i] = NaN
    else:
        mom40[i] = close[i] / close[i - 40] - 1.0
        signal[i] = 1 if mom40[i] > 0.0 else 0

for i in range(len(rows)):
    if i == 0:
        position[i] = 0
    else:
        position[i] = 0 if open_time[i] < UTC("2020-01-01") else int(signal[i - 1] == 1)
```
