# Frozen system specification

## Candidate

- Candidate ID: **S_D1_VOLCL5_20_LOW_F1**
- Evidence label: **INTERNAL ROBUST CANDIDATE**

## Logic

- Native timeframe: D1
- Feature: `volcluster_5_20 = rolling std_5 / rolling std_20 of log returns`
- Threshold mode: fixed one
- Signal rule on previous completed D1 bar: long if `volcluster_5_20 <= 1.0`, else flat
- Signal timing: compute at bar close
- Fill model: next bar open
- Position sizing: 100% long or 0% flat
- Trading cost: 10 bps per side, 20 bps round-trip
- Warmup only before 2020-01-01; no live scoring before that date

## Selection rationale

- Best simple slower-state candidate that passed discovery and holdout trade-count gates
- Meaningful paired advantage over strongest genuine native faster rival S_H4_RANGE48_HI_Q60 on pre-reserve data
- Nearest serious complex rival L2_VOLCL_RANGE48_Q60 did not show meaningful paired advantage despite better Sharpe; complexity rule therefore favored the simpler system
- Reserve/internal slice stayed positive for the frozen leader while the main faster and layered rivals turned negative

## Caveats

- Strict local 80% plateau score for the exact volcluster 5/20 cell is only 0.33 on the coarse local grid
- Broader slower volatility-regime evidence is corroborated by the separate D1 ATR family, reducing the risk that the final leader is a lone accidental spike
