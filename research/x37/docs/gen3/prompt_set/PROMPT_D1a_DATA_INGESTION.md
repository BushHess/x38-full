# PROMPT D1a - Data Ingestion & Quality Check (Use this after D0 GO in the same chat)

You have completed the D0 precheck and received GO FOR D1.

Your job in this turn is **only** to ingest, canonicalize, and validate the raw data.
Do **not** design strategies yet.
Do **not** run backtests.
Do **not** propose candidates.

## Hard instructions (apply to all D1 prompts in this chat)
- Use only the admitted raw historical snapshot and the constitution.
- Treat the historical snapshot as **candidate-mining-only**.
- Do not claim clean external OOS from this snapshot.
- Do not import prior winners or prior reports.
- Do not exceed the constitution hard caps.
- Do not change the constitution.
- Design candidates from measured signal strength, not from predefined templates.
- Do not output more than 3 live candidates total.

## What to do

1. **Load all 4 raw CSV files** into dataframes:
   - `spot_btcusdt_15m.csv`
   - `spot_btcusdt_1h.csv`
   - `spot_btcusdt_4h.csv`
   - `spot_btcusdt_1d.csv`

2. **Canonicalize and validate the 13-column schema** for each file:
   - Required columns (exact order): symbol, interval, open_time, close_time, open, high, low, close, volume, quote_volume, num_trades, taker_buy_base_vol, taker_buy_quote_vol
   - If raw Binance kline exports contain an unused final column, drop it during canonicalization.
   - Inject `symbol` and `interval` columns if not present in raw data.
   - Rename quote/taker fields into the canonical names if needed.
   - open_time and close_time: integer milliseconds UTC
   - symbol = "BTCUSDT"
   - interval matches file (15m, 1h, 4h, 1d)
   - No synthetic bar repair is allowed.

3. **Run data quality checks** per timeframe:
   - row count
   - date range (first bar, last bar)
   - missing bars (gaps in expected open_time sequence)
   - duplicate open_time values
   - zero or negative prices
   - zero volume bars
   - NaN or null values
   - bars where high < low
   - bars where close or open is outside [low, high]
   - taker_buy_base_vol > volume (impossible)

4. **Log anomalies without repairing them.**
   Do not invent synthetic bars. Do not fill gaps. Do not modify any data.
   If anomalies are found, record them and proceed.

5. **Compute basic per-timeframe summary statistics:**
   - total bars, date range, expected vs actual bar count
   - price range (min low, max high)
   - median daily volume, median daily num_trades
   - percentage of bars with zero volume

6. **Confirm the data splits** match the constitution:
   - warmup: first available bar → 2019-12-31
   - discovery: 2020-01-01 → 2023-06-30
   - holdout: 2023-07-01 → 2024-09-30
   - reserve_internal: 2024-10-01 → snapshot end
   - count bars per split per timeframe

7. **Save results to a file** named `d1a_quality_report.md` for reference in later turns.

## Practical notes
- If the 15m CSV exceeds the upload size limit (~20MB), compress it as `.csv.gz` before uploading. Pandas can read gzipped CSV directly with `pd.read_csv('file.csv.gz')`.
- If the 15m file is too large to load in full, compute quality checks in chunked fashion. Summary statistics can use a sample if necessary, but anomaly detection must scan all rows.

## Required output sections
1. `Schema Validation` — pass/fail per file
2. `Anomaly Log` — list of anomalies found (or "none")
3. `Summary Statistics` — table per timeframe
4. `Split Coverage` — bar counts per split per timeframe
5. `Data Quality Verdict` — PASS (data usable) or FAIL (blocking issues found)

   **Blocking issue examples** (warrant FAIL):
   - More than 5% of expected bars missing in any timeframe
   - Systematic data corruption (e.g. all prices zero for an entire day)
   - Schema validation failure (wrong column count, unparseable timestamps)
   - Timeframe mismatch (file labeled 4h but bars are 1h apart)

   **Non-blocking anomaly examples** (record and PASS):
   - Isolated missing bars (< 5% of expected)
   - Sporadic zero-volume bars (common in low-liquidity early history)
   - Minor duplicate bars (< 0.1% of total)
   - taker_buy_base_vol > volume on isolated bars

## What not to do
- Do not compute indicators, features, or signals.
- Do not design or propose any strategy.
- Do not analyze market regimes.
- Do not touch the constitution.
