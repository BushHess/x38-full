# OH0_D1_TREND40 — Source Reference

## Authoritative source

| Field | Value |
|-------|-------|
| Source spec | `research/x37/resource/gen1/v8_sd1trebd/spec/spec_2_system_S_D1_TREND.md` |
| System ID | `S_D1_TREND` |
| League | `OHLCV_ONLY` |
| x40 role | Control baseline |

## Source snapshot

- Data: native D1 CSV from `data/bars_btcusdt_2016_now_h1_4h_1d.csv` (D1 rows only)
- Coverage: 2017-08-17 through 2026-02-20 (end of current archive)
- D1 rows: 3,134 (as of frozen spec)
- Live start: 2020-01-01

## Data surface used by logic

`close` only. No other field is consumed by the signal.

The raw CSV physically contains 13 columns (OHLCV + taker data), but the strategy
logic touches only `close` for `D1_MOM_RET(40)` and `open` for execution price.

## Verification targets (from frozen spec §11)

| Segment | Cost RT | Sharpe | CAGR | Max DD | trade_count_entries |
|---------|---------|--------|------|--------|---------------------|
| Discovery WFO | 20 bps | 1.6941 | 101.2% | -48.3% | 61 |
| Discovery WFO | 50 bps | 1.6396 | 96.0% | -50.9% | 61 |
| Holdout | 20 bps | 1.0819 | 40.8% | -43.4% | 34 |
| Holdout | 50 bps | 0.9751 | 35.2% | -44.9% | 34 |
| Reserve | 20 bps | 0.8734 | 24.2% | -24.0% | 35 |
| Reserve | 50 bps | 0.7518 | 19.8% | -25.4% | 35 |

`trade_count_entries` = state-transition count (entries + exits), not completed round trips.

## Source metric domain

- Sharpe: `mean(daily_returns) / std(daily_returns, ddof=1) * sqrt(365)`
- CAGR: `equity_end ** (365 / N_days) - 1`
- MDD: peak-to-trough on cumulative equity

These use daily UTC returns (one D1 interval per day).

## Source window profile

| Segment | Period |
|---------|--------|
| Warmup | through 2019-12-31 |
| Discovery WFO | 2020-01-01 to 2023-06-30 (14 folds) |
| Holdout | 2023-07-01 to 2024-09-30 |
| Reserve | 2024-10-01 to snapshot end |

## Cost model

- 10 bps per side / 20 bps round-trip (canonical)
- Also verified at 50 bps RT
- Formula: entry `(1-c) * next_open/open`, exit `(1-c)`, hold `next_open/open`
- c = 0.001

## Implementation notes for x40 replay

OH0 is native D1, long-only, long/flat. The v10 BacktestEngine is H4-native,
so OH0 uses a **vectorized D1 sim** (Pattern B) rather than Pattern A.

The vectorized sim must:
1. Use only D1 bars from the feed
2. Compute `D1_MOM_RET(40) = close_t / close_{t-40} - 1`
3. Signal: long if mom40 > 0.0, flat if <= 0.0
4. Execute at next D1 open
5. No live trades before 2020-01-01
6. Cost: per-side bps applied at entry and exit

## Known non-authoritative documents

The VTREND_BLUEPRINT and production validation artifacts are NOT sources for OH0.
OH0 is derived solely from the x37/gen1 frozen spec.
