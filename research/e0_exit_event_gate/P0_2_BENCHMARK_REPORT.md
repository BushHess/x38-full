# P0.2 Event-Gate Benchmark Report

## Verdict

- `KILL_EVENT_GATE`

## Survivors

- none

## Full Period (harsh)

- `X0_E5EXIT`: Sharpe=1.4545, CAGR=61.60%, MDD=40.97%, Calmar=1.5037, Trades=188
- `X0E5_FLOOR_LATCH`: Sharpe=1.4560, CAGR=61.28%, MDD=35.46%, Calmar=1.7282, Trades=195
- `X0E5_FLOOR_BSLOW`: Sharpe=1.4391, CAGR=60.32%, MDD=37.10%, Calmar=1.6259, Trades=193
- `X0E5_FLOOR_PEAK3`: Sharpe=1.4736, CAGR=62.48%, MDD=36.87%, Calmar=1.6947, Trades=193

## Holdout (harsh)

- `X0_E5EXIT`: Sharpe=1.0057, CAGR=28.22%, MDD=25.60%, Calmar=1.1023, Trades=57
- `X0E5_FLOOR_LATCH`: Sharpe=0.9426, CAGR=25.72%, MDD=25.66%, Calmar=1.0023, Trades=59
- `X0E5_FLOOR_BSLOW`: Sharpe=0.9577, CAGR=26.27%, MDD=25.66%, Calmar=1.0238, Trades=58
- `X0E5_FLOOR_PEAK3`: Sharpe=1.0320, CAGR=29.19%, MDD=25.60%, Calmar=1.1400, Trades=57

## Interpretation

- No simple event gate improved both the anchor and the raw floor variant cleanly enough.
