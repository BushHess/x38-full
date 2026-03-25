# PROMPT D1c - Candidate Design & Config Matrix (Use this after D1b4 in the same chat)

You have completed D1b. Data decomposition and signal measurements are available.

Your job in this turn is **only** to design candidate mechanisms and define their parameter configurations.
Do **not** run backtests.
Do **not** score or rank candidates.
Do **not** select any champion or challenger.

## Design philosophy (from constitution v4.0)

Design candidates from the **strongest measured channels** in D1b.
There is no predefined archetype list. Any mechanism that exploits measured signal
is valid, subject only to the complexity budget.

Each candidate must state:
- what market behavior it exploits,
- why that behavior may persist,
- what should cause it to fail,
- what observable evidence would falsify it.

Start from the **smallest defensible design**. Add components only if each one
earns its place (to be validated by ablation in D1d).

## Constitution hard caps (must not exceed)

- Max candidates after seed: 3 (1 champion + up to 2 challengers)
- Max challengers after seed: 2
- Max logical layers per candidate: 3
- Max tunable quantities per candidate: 4
- Max discovery configs per candidate: 20
- Max total seed configs: 60
- Allowed position sizing: binary 0% or 100% notional
- Disallowed: leverage, pyramiding, regime-specific parameter sets, discretionary overrides

**Notes on counting:**
- A "logical layer" is a distinct decision function operating on a specific timeframe.
- A "tunable quantity" is any parameter whose value is selected by search, not derived from data.
- Adaptive thresholds computed from expanding or trailing windows (e.g., yearly quantile) count as ONE tunable (the quantile level), not as N thresholds.
- Fixed mathematical constants (e.g., sqrt, log) are not tunable quantities.
- Single-timeframe systems are allowed. Cross-timeframe systems are allowed.

## What to do

### 1. Review D1b channel ranking
Load `d1b_measurements.md` saved in D1b. Identify the strongest independent channels.
Design candidates to exploit those channels, not to fill a predefined template.

### 2. Design candidate mechanisms

For each candidate, define exactly:
- **Candidate ID** (short, unique, descriptive — must be globally unique across all versions in the lineage; redesigned candidates in R1 must receive a new ID)
- **Mechanism description** (what market behavior it exploits and why)
- **Timeframes used** (which of 15m, 1h, 4h, 1d)
- **Feature formulas** (exact mathematical definitions, e.g., `ret_N = close_t / close_(t-N) - 1`)
- **Signal logic** (exact entry condition, exact hold condition, exact exit condition)
- **Calibration method** (fixed threshold, expanding quantile, trailing window, etc.)
- **Tunable quantities** (name, type, range — max 4 per candidate)
- **Fixed quantities** (values that are not tuned)
- **Layer count** (how many distinct decision functions)
- **Execution semantics** (signal at bar close, fill at next bar open, UTC, no lookahead)

### 3. Define parameter configurations

For each candidate, define up to 20 parameter configurations (grid or selected points)
within the tunable ranges. Each configuration is a specific set of parameter values
to be tested in the walk-forward.

### 4. Build the config matrix

Create a structured config matrix with columns:
- config_id (unique across all candidates)
- candidate_id
- param_1_name, param_1_value
- param_2_name, param_2_value
- param_3_name, param_3_value
- param_4_name, param_4_value

Total rows must not exceed 60.

### 5. Verify compliance
- Each candidate: max 3 layers, max 4 tunables
- Each candidate: max 20 configs
- Total: max 60 configs
- All features use only admitted data surface columns
- No lookahead from incomplete higher-timeframe bars
- No use of holdout or reserve_internal data
- Execution model: next-open fill, UTC alignment

### 6. Save results
Save two files:
- `d1c_candidate_designs.md` — human-readable candidate descriptions with exact formulas and signal logic
- `d1c_config_matrix.csv` — machine-readable config matrix

## Required output sections
1. `Candidate 1` — mechanism, formulas, signal logic, tunables, justification from D1b
2. `Candidate 2` — same structure (if applicable)
3. `Candidate 3` — same structure (if applicable)
4. `Config Matrix Summary` — total configs per candidate, total overall
5. `Hard Cap Compliance Check` — explicit pass/fail for each cap
6. `Design Rationale` — why these mechanisms and not others, based on D1b evidence

## Viability gate (governance patch v4.0.1)

Before finalizing each candidate, verify it is likely to produce sufficient activity
for the WFO evaluation to be meaningful:

- For each candidate, run its **loosest config** (lowest entry threshold, lowest hold threshold)
  on the **warmup period** (→ 2019-12-31) or the **first year of discovery** (2020).
- The candidate must produce **>= 6 entries per year** under this quick check.
- If it produces fewer than 6 entries/year at its loosest config, it will almost certainly
  produce zero trades in short OOS folds. Either redesign the calibration (e.g., lower
  thresholds, wider window) or discard the candidate before it consumes a slot.
- This is a **design-time sanity check**, not a scored evaluation. Do not optimize against it.

## Sub-hourly primary candidate guidance (governance patch v4.0.1)

Candidates whose primary execution timeframe is **15m** face structurally higher
turnover and cost sensitivity. Gen3 session evidence: a 15m vol-normalized continuation
candidate (t=15.40 in D1b) failed WFO at ALL cost levels including 20 bps — the signal
did not generalize out-of-sample.

Guidelines:
- Prefer **1h or higher** as the primary execution timeframe for swing-horizon candidates.
- If 15m is used, it should be as a **timing refinement layer** within a higher-TF mechanism,
  not as the sole decision timeframe.
- If you still design a 15m-primary candidate, explicitly note the higher WFO survival risk
  in the design rationale, and ensure it passes the viability gate above.

## Important notes
- Fewer candidates is better than many speculative ones. 1-2 strong candidates > 3 weak ones.
- Use D1b measurements to justify every design choice. No intuition-only candidates.
- Simpler candidates are preferred unless D1b shows complexity earns its place.
- If D1b found that a single feature on a single timeframe is the strongest channel, a 1-layer 1-tunable candidate is the correct design. Do not add complexity for its own sake.
- If fewer than 60 total configs are sufficient, that is preferred over padding.

## What not to do
- Do not run any backtest or simulation.
- Do not use holdout or reserve_internal data.
- Do not claim any candidate is better than another without evidence.
- Do not exceed the hard caps.
- Do not design candidates around named TA indicators unless D1b measurement specifically supports them.
- Do not modify the constitution.
