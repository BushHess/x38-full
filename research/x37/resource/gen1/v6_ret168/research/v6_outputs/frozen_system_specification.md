# Frozen system specification

## Frozen winner before reserve/internal
**S3_H4_RET168_Z0**

## Exact logic
- Timeframe: native H4.
- Feature: 168-bar H4 return.
- Formula: `close_t / close_(t-168) - 1`.
- Signal at H4 close: long when feature > 0, else flat.
- Execution: next H4 open.
- Position sizing: 100% long or 100% cash.
- Costs: 10 bps per side, 20 bps round-trip base; 50 bps round-trip stress test used in validation.
- Warmup/live rule: no live trading before 2020-01-01.

## Why this won pre-reserve
- It beat or matched the strongest simple internal rivals on discovery + holdout with a broad plateau.
- `L2_D1RET40_Z0_AND_H4RET168_Z0` had slightly better headline pre-reserve metrics, but the more complex system did **not** show a meaningful paired-bootstrap advantage over `S3_H4_RET168_Z0`; per protocol the simpler candidate wins.
- `S1_D1_RET40_Z0` remained a serious simple rival and reserve/internal later treated it better, but pre-reserve the H4 trend frontier had slightly better Sharpe/CAGR and lower drawdown.

## Important reserve/internal caveat
Reserve/internal is reported honestly as internal evidence only. It materially weakened confidence in the frozen winner and exposed a bear-regime vulnerability that was not clear in pre-reserve evidence.
