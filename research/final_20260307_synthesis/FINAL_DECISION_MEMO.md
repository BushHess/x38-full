# Final Decision Memo

## Scope

This memo consolidates the current state of the following research branches:

- `research/ml0_feasibility`
- `research/e0_forensics`
- `research/e0_entry_hygiene`
- `research/e0_reentry`
- `research/e0_exit_floor`
- `research/e0_exit_event_gate`
- `research/x0`

All results referenced below use the current engine with next-open fills and the
BTC H4/D1 dataset ending `2026-02-20`.

## Final Conclusions

### 1. ML / XGBoost is not justified for this project state

The ML feasibility branch is a kill.

- verdict: `KILL_STACK`
- source: `research/ml0_feasibility/P0_1_INITIAL_REPORT.md`
- best compact soft model logloss gain: `2.36%`
- best compact hard model logloss gain: `2.20%`
- effective sample size after thinning / dependence control was too low:
  - soft ESS: `54.15`
  - hard ESS: `44.31`

Conclusion:

- There is not enough independent incremental signal in the current state /
  feature set to justify an ML overlay.
- Do not continue XGBoost or similar tabular ML on this dataset unless new
  independent information is added.

### 2. E0 failure modes are understood well enough to guide mechanism work

The E0 forensics branch produced a clear diagnosis.

- source: `research/e0_forensics/P0_1_INITIAL_REPORT.md`
- primary losing mode: `false_breakout` with `41.2%` of total loss
- second losing mode: `trail_stop_noise` with `39.5%` of total loss
- worst context: `chop + D1 on` with `62.5%` of total loss

Conclusion:

- Entry hygiene in chop was the correct next mechanism to test.
- This branch justified the stretch-gate hypothesis.

### 3. Stretch gate is a real mechanism, but not strong enough for promotion

The best mechanism discovered was:

- `X0E5_CHOP_STRETCH18`
- rule: block entry when `entry_context == chop` and
  `entry_price_to_slow_atr > 1.8`

Evidence:

- source: `research/e0_entry_hygiene/P0_1_INITIAL_REPORT.md`
- source: `research/e0_entry_hygiene/P0_3_MATCHED_ATTRIBUTION_REPORT.md`
- source: `research/e0_entry_hygiene/P0_4_VALIDATION_REPORT.md`

Full-period harsh vs `X0_E5EXIT`:

- Sharpe: `1.5029` vs `1.4300`
- CAGR: `62.29%` vs `59.85%`
- MDD: `40.29%` vs `41.64%`
- Calmar: `1.5462` vs `1.4373`

But post-selection validation was mixed:

- verdict: `HOLD_RESEARCH_ONLY`
- recent holdout `2024-01-01` to `2026-02-20`:
  - dSharpe: `-0.0042`
  - dCAGR: `-1.17pp`
  - dMDD: `+1.39pp`
- rolling OOS MDD wins: only `10/21`
- paired bootstrap direction was positive, but confidence intervals crossed `0`
- pair diagnostic class: `borderline`

Mechanism attribution:

- uplift did not come from better exits on matched trades
- uplift came from:
  - avoiding weak stretched-chop entries
  - preserving capital
  - compounding later on shared trades

Conclusion:

- Keep this as a research-side candidate only.
- Do not promote it as the main deployable variant.

### 4. Re-entry / recovery did not improve the stretch baseline

The recovery branch tested the only re-entry variants that were still
mechanistically meaningful after the stretch baseline was defined:

- stretched override
- delayed stretched confirmation

Evidence:

- source: `research/e0_reentry/P0_1_BENCHMARK_REPORT.md`
- verdict: `KILL_RECOVERY_MECHANICS`

None of the recovery candidates beat `X0E5_CHOP_STRETCH18` cleanly on both:

- full-period harsh
- recent holdout harsh

Best holdout-only result:

- `X0E5_RE6_IMPULSE` improved holdout, but still lost to stretch baseline on
  full-period harsh

Conclusion:

- Re-entry / recovery should not be extended further in this family.
- This closes the current entry/re-entry research loop.

### 5. Exit-floor family is promising but still not promotable

A final low-DOF exit branch was tested directly on top of `X0_E5EXIT`.

Best candidate:

- `X0E5_FLOOR_LATCH`
- rule: add early exit when `close < max(ll30, ema_slow - 2.0 * robust_ATR)`

Evidence:

- source: `research/e0_exit_floor/P0_1_BENCHMARK_REPORT.md`
- source: `research/e0_exit_floor/P0_2_VALIDATION_REPORT.md`
- source: `research/e0_exit_floor/P0_3_EVENT_REVIEW_REPORT.md`

Benchmark was good:

- full-period harsh vs `X0_E5EXIT`
  - Sharpe: `1.4730` vs `1.4300`
  - CAGR: `62.18%` vs `59.85%`
  - MDD: `36.19%` vs `41.64%`
  - Calmar: `1.7179` vs `1.4373`

But validation did not clear promotion:

- branch verdict: `HOLD_RESEARCH_ONLY`
- holdout delta was only marginal:
  - dSharpe: `+0.0068`
  - dCAGR: `+0.24pp`
  - dMDD: `+0.05pp`
- rolling OOS breadth was weak:
  - Sharpe wins: `7/21`
  - CAGR wins: `7/21`
  - MDD wins: `7/21`
  - Calmar wins: `6/21`
- pair diagnostic class: `near_identical`

Event review changed the interpretation materially:

- matched-trade delta was negative: `-24,063 USD`
- candidate-only sequencing delta was strongly positive: `+59,173.77 USD`
- top 5 positive matched contributors explained `72.11%` of total delta

Conclusion:

- The mechanism is real enough to deserve respect.
- But the observed uplift is too dependent on sequencing spillover and too weak
  in rolling OOS breadth to justify promotion.
- Keep this branch as research-only.

### 6. Current anchor should remain `X0_E5EXIT`

Given the evidence above, the clean operational anchor remains:

- `X0_E5EXIT`

Evidence:

- source: `research/x0/p2_4_backtest_table.csv`
- source: `research/x0/p2_4_delta_table.csv`
- source: `research/e0_entry_hygiene/P0_4_VALIDATION_REPORT.md`
- source: `research/e0_reentry/P0_1_BENCHMARK_REPORT.md`

Why `X0_E5EXIT`:

- it has clear full-period improvement over `X0`
- it survived as the strongest clean member of this family
- the stretch variant did not clear promotion
- recovery / re-entry did not add robust value
- exit-floor variants did not clear promotion either
- event-conditioned floor gating did not rescue the floor family

Operational note:

- In the current research outputs, `X0_E5EXIT` and `E5_EMA21` have identical
  reported metrics. Treat them as the same behavior unless a later parity check
  proves otherwise.

## Recommended Actions

### Immediate

1. Freeze `X0_E5EXIT` as the family anchor.
2. Mark `X0E5_CHOP_STRETCH18` as `research-only`.
3. Mark `X0E5_FLOOR_LATCH` as `research-only`.
4. Close the current ML, re-entry, exit-floor, and exit-event-gate branches.

### What not to do next

1. Do not continue XGBoost / ML overlay work on the current state/features.
2. Do not continue stretching the entry-gate family with more re-entry rules.
3. Do not continue the current exit-floor family without new evidence.
4. Do not add more parameterized variants in this mechanism family.
5. Do not continue event-conditioned rescue attempts on the current floor family.

### If work continues

The current evidence no longer supports opening another alpha branch on the same
state/data space.

The justified next work is engineering work, not more alpha search:

1. freeze `X0_E5EXIT`
2. simplify / retire redundant aliases where possible
3. add stronger regression tests and parity checks around the chosen anchor
4. prepare deployment / monitoring / paper execution infrastructure

Only reopen alpha research if one of these changes:

- a genuinely new data source is added
- a new market set is added
- or a new mechanism is motivated by evidence outside the already exhausted
  entry / re-entry / floor / event-gate families

## Bottom Line

The strongest current conclusion is:

- `X0_E5EXIT` is the clean anchor.
- `X0E5_CHOP_STRETCH18` is interesting but not promotable.
- `X0E5_FLOOR_LATCH` is interesting but not promotable.
- re-entry / recovery is not worth continuing in this family.
- ML / XGBoost is not justified on the current data and state space.
- event-gated rescue of the floor family is also not justified.
