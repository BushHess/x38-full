# PROMPT D1c - Candidate Design & Config Matrix (Use this after D1b in the same chat)

You have completed D1b. Feature measurements and signal analysis are available.

Your job in this turn is **only** to design candidate strategies and define their parameter configurations.
Do **not** run backtests.
Do **not** score or rank candidates.
Do **not** select any champion or challenger.

## Constitution hard caps (must not exceed)

- Max candidates after seed: 3 (1 champion + up to 2 challengers)
- Max challengers after seed: 2
- Max logical layers per candidate: 3 (1 slow context + 1 fast state + 1 optional entry)
- Max tunable quantities per candidate: 4
- Max discovery configs per archetype: 20
- Max total seed configs: 60
- Allowed position sizing: binary 0% or 100% notional
- Disallowed: leverage, pyramiding, regime-specific parameter sets, discretionary overrides

## What to do

### 1. Review D1b measurements
Load `d1b_measurements.md` saved in D1b. Identify which primitives have measurable signal. Focus candidate design on primitives with demonstrated signal, not on all theoretical possibilities.

### 2. Design candidates for each archetype

For each of the three archetypes (A, B, C), design candidate strategies using only the admitted primitives from the constitution:

**For each candidate, define exactly:**
- **Archetype** (A, B, or C)
- **Candidate ID** (short, unique, descriptive)
- **Layers** (which D1/H4/1h primitives are used, max 3 layers)
- **Signal logic** (exact entry condition, exact exit condition)
- **Tunable quantities** (name, type, range — max 4 per candidate)
- **Fixed quantities** (values that are not tuned)
- **Execution semantics** (signal at bar close, fill at next bar open)

### 3. Define parameter configurations

For each candidate, define up to 20 parameter configurations (grid or selected points) within the tunable ranges. Each configuration is a specific set of parameter values to be tested in the walk-forward.

### 4. Build the config matrix

Create a structured config matrix with columns:
- config_id (unique across all archetypes)
- archetype
- candidate_id
- param_1_name, param_1_value
- param_2_name, param_2_value
- param_3_name, param_3_value
- param_4_name, param_4_value

Total rows must not exceed 60.

### 5. Verify compliance
- Each candidate: max 3 layers, max 4 tunables
- Each archetype: max 20 configs
- Total: max 60 configs
- All primitives are from the constitution's admitted list
- No lookback into holdout or reserve_internal periods
- Execution model: next-open fill, UTC alignment, no lookahead

### 6. Save results
Save two files:
- `d1c_candidate_designs.md` — human-readable candidate descriptions with exact signal logic
- `d1c_config_matrix.csv` — machine-readable config matrix

## Required output sections
1. `Archetype A Candidates` — candidate designs for slow trend state
2. `Archetype B Candidates` — candidate designs for pullback continuation
3. `Archetype C Candidates` — candidate designs for compression breakout
4. `Config Matrix Summary` — total configs per archetype, total overall
5. `Hard Cap Compliance Check` — explicit pass/fail for each cap

## Important notes
- It is acceptable if an archetype produces zero candidates because D1b measurements showed no signal for its primitives. Document the reason.
- Prefer fewer well-motivated candidates over many speculative ones.
- Use D1b measurements to justify design choices, not intuition.
- If fewer than 60 total configs are sufficient, that is preferred over padding to fill the cap.

## What not to do
- Do not run any backtest or simulation.
- Do not use holdout or reserve_internal data.
- Do not claim any candidate is better than another without evidence.
- Do not exceed the hard caps.
- Do not modify the constitution.
