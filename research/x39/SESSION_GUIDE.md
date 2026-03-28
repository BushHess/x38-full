# x39 Session Guide

## How to run an experiment in a new session

Give the new session this prompt:

```
Read /var/www/trading-bots/btc-spot-dev/research/x39/specs/exp{NN}_{name}.md

This is a self-contained experiment spec. Do exactly what it says:
1. Read the spec completely
2. Read x39/explore.py for reusable helpers (ema, robust_atr, vdo, map_d1_to_h4, compute_features)
3. Write the experiment script to x39/experiments/exp{NN}_{name}.py
4. Run it
5. Write results back to the spec file under ## Result
6. Update x39/PLAN.md results table with the verdict
```

## Directory structure

```
x39/
├── PLAN.md              # Master plan + results summary table
├── SESSION_GUIDE.md     # This file
├── README.md            # What x39 is
├── explore.py           # Feature computation + residual scan (reusable code)
├── specs/               # One spec per experiment (read-only input)
│   ├── exp01_d1_antivol_gate.md
│   ├── exp02_trendq_gate.md
│   └── ...
├── experiments/         # Scripts (written by each session)
│   ├── exp01_d1_antivol_gate.py
│   └── ...
├── results/             # CSV output from experiments
│   ├── exp01_results.csv
│   └── ...
└── output/              # explore.py output (bar_features.csv etc.)
```

## Reusable code in explore.py

Each experiment script can import or copy these helpers:
- `ema(series, period)` — exact match with strategy code
- `robust_atr(high, low, close, ...)` — E5's robust ATR
- `vdo(volume, taker_buy, ...)` — VDO indicator
- `map_d1_to_h4(d1_arr, d1_ct, h4_ct, n)` — D1→H4 bar mapping
- `compute_features(h4, d1)` — computes ALL features (53 columns)
- `load_data()` — loads H4 + D1 DataFrames from CSV

## Baseline reference

E5-ema21D1 at 50 bps RT:
- Sharpe: 1.4545
- CAGR: 61.60%
- MDD: 40.97%
- Trades: 188
- Exposure: 44.5%

## Order recommendation

No strict order required, but suggested grouping:
1. Category A (filters): exp01-06 — fastest to implement, clearest signal
2. Category D (head-to-head): exp14-15 — establishes whether alternatives are competitive
3. Category B (replacements): exp07-10 — more structural changes
4. Category C (exits): exp11-13 — exit modifications
5. Category E (ensembles): exp17-18 — depends on knowing individual system performance
6. Category J (entry logic): exp32-35 — new entry mechanics (pullback, accel, compression, D1 slope)
7. Category K (regime adapt): exp36-39 — adaptive parameters (trail split, EMA period, maturity, dual-clock)
