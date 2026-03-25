# Spec Request Prompt

Write two separate spec documents, each self-contained enough for an engineer to rebuild everything from scratch without access to chat history, original code, or any other documentation beyond these specs and the two input data files (raw H4 CSV and raw D1 CSV — specify the expected schema, column names, and format of each file within the spec).

---

## Spec 1 — Research Reproduction Spec (Full research process)

Describe every step taken to go from raw data to the frozen winner. No step may be omitted. Each step must specify: **input → logic → output → decision rule**.

### Mandatory requirements

- **Data pipeline & anomaly handling:** Specify how each logged anomaly type was handled (19 shortened bars, 8 timing gaps, 1 duplicate `close_time` zero-duration row) — retained as-is, removed, or adjusted, and the rationale. Specify the exact order of processing steps.

- **Data splits:** Specify exact date ranges (or bar index ranges) for each partition: discovery, candidate-selection holdout, reserve/internal. Specify the split ratios and the logic behind them.

- **Feature engineering:** List every feature computed, the exact formula, and all lookback periods scanned.

- **Stage 1 screening:** Specify all thresholds and filter criteria (minimum Sharpe, minimum trade count, where and how the 20 bps cost assumption is applied, etc.).

- **Candidate comparison & elimination:** Specify the criteria used to compare candidates, including paired-bootstrap configuration (number of bootstrap samples, significance level, null hypothesis, test statistic). Explain specifically why `L2_D1RET40_Z0_AND_H4RET168_Z0` was eliminated and `S3_H4_RET168_Z0` was selected.

- **Plateau analysis:** Specify how the local plateau was assessed, which metric was used, and the acceptance threshold.

- **Reserve/internal evaluation:** Specify the reserve/internal results of the frozen winner (CAGR −5.8%) and other candidates, and explain why the V6 protocol does not permit redesign after the freeze.

- **Provenance:** Specify all hyperparameters, random seeds (if any), and software versions/libraries used, sufficient for deterministic reproduction.

---

## Spec 2 — System Specification (Frozen winner `S3_H4_RET168_Z0`)

Describe the final system from `final_practical_system.json` with enough precision for an engineer to reimplement it and achieve bit-level matching output.

### Mandatory requirements

- **Signal logic:** The exact signal formula (H4 168-bar return > 0), which price is used (close), and which bar the calculation is performed on.

- **Entry/exit rules:** Entry condition (next H4 open after signal), exit condition, and position direction (long-only / long-flat).

- **Position sizing:** Exact sizing rule; if fixed, specify the size explicitly.

- **Regime gate:** If a regime filter exists, specify the logic, parameters, and behavior when the regime gate triggers.

- **Cost model:** How the 20 bps transaction cost is calculated — per-trade, per-side, or round-trip.

- **Edge cases:** Specify handling for: shortened bars, gaps between bars, missing data, insufficient history (fewer than 168 bars) to compute the signal, and duplicate rows.

- **Conventions:** Timezone, bar open/close semantics, rounding rules (if any), and how H4 bars align with D1 (if relevant to this system).

- **Test vectors:** Include at least 10 test cases with specific input rows (timestamp, OHLC) and expected output (signal value, trade direction, entry price, exit price, PnL after cost) so an engineer can verify bit-level implementation correctness.

---

## General requirements

Both specs must be fully self-contained, written in clear and unambiguous technical language, and must never use phrases like "as described above" — repeat in full wherever needed. The goal: a person who has never seen this research should be able to read the spec, rerun everything from the raw CSVs, and arrive at exactly the same results.
