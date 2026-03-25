# X36 Program Note 04 — WFO Power and Authority Reform

**Date**: 2026-03-17  
**Scope**: methodology reform spec only; no root-code edits in this note

## Question

How should current repo methodology distinguish:

1. true negative OOS robustness evidence,
2. delegated low-power WFO, and
3. non-low-power but still underresolved WFO cases like `E5+EMA21D1`?

## Current Canonical Facts

Canonical `E5+EMA21D1` WFO (`24m / 6m / last 8`) currently has:

- `n_windows_valid = 8`
- `n_windows_power_only = 8`
- `low_trade_windows_count = 0`
- `wilcoxon_p = 0.125` with one-sided `alpha = 0.10`
- `bootstrap_ci = [-3.4378, 29.2790]`
- `mean_delta = 12.4563`
- `median_delta = 12.9825`
- `positive windows = 5 / 8`

So this run is **not** low-power under the current repo rule, but it also does **not**
provide strong negative evidence that the candidate is worse than baseline.

Additional exact-test detail:

- observed signed-rank `W+ = 27`
- first passing cutoff at current `alpha = 0.10` is `W+ >= 28`
- the case is therefore one exact-rank step short of positive confirmation

This is a small-`N` inferential resolution problem, not a trade-count problem.

## Diagnosis

### 1. Current repo uses one route for low trade power only

Current `wfo_low_power` means:

- `power_windows < 3`, or
- `low_trade_ratio > 0.5`

That route is operationally useful and should remain. It detects when the WFO window
set is too weak to stand on its own and delegates to `trade_level_bootstrap`.

But this is **not the same thing** as inferential underresolution at small `N`.

### 2. Current WFO semantics collapse two different outcomes into one `FAIL`

Today the decision consumer treats:

- `no positive WFO confirmation`, and
- `true evidence candidate is worse OOS`

as the same soft failure bucket.

That is methodologically too coarse for the current strategy family.

### 3. Lowering alpha is the wrong fix

The current repo has already relaxed the binding Wilcoxon threshold to `alpha = 0.10`
for small-`N` WFO.

So the right reform is **not** "make alpha even looser until E5 passes."

The right reform is to separate:

- positive confirmation,
- negative confirmation,
- underresolved non-confirmation,
- delegated low-power.

## Reform Principle

`wfo_robustness` should answer a narrow question:

> What kind of paired OOS evidence do we actually have?

It should not silently reinterpret "failed to confirm delta > 0" as
"proved temporal instability" when the data only support an underresolved result.

## Proposed Evidence-State Model

Future root implementation should emit a first-class WFO evidence state:

1. `positive_confirmed`
2. `negative_confirmed`
3. `underresolved`
4. `delegated_low_power`

### A. `delegated_low_power`

Definition:

- keep the existing repo trigger unchanged:
  - `power_windows < 3`, or
  - `low_trade_ratio > 0.5`

Decision meaning:

- WFO itself is not authority-bearing here.
- Authority delegates to trade-level bootstrap, exactly as current policy intends.

### B. `positive_confirmed`

Definition:

- not low-power, and
- `wilcoxon_greater.p <= alpha`, or
- `bootstrap_ci_lower > 0`

Decision meaning:

- current WFO PASS semantics.

### C. `negative_confirmed`

Definition:

- not low-power, and
- `wilcoxon_less.p <= alpha`, or
- `bootstrap_ci_upper < 0`

Decision meaning:

- this is the case where WFO really supports "candidate worse than baseline" on
  paired OOS evidence.

### D. `underresolved`

Definition:

- not low-power, and
- not `positive_confirmed`, and
- not `negative_confirmed`

Decision meaning:

- WFO does not confirm candidate superiority.
- WFO also does not confirm candidate inferiority.
- Result should be reported as unresolved / underpowered-inference, not as evidence
  of true instability.

`E5+EMA21D1` canonical belongs here.

## Why This Reform Fits X36 Findings

This reform matches the current active branch:

- canonical split fails to confirm positive robustness;
- canonical fail disappears under multiple preregistered alternative segmentations;
- there is no evidence of a WFO code bug;
- there is no paired OOS evidence that `E5+EMA21D1` is actually worse than baseline.

So the best current reading is:

- canonical verdict should remain frozen as produced;
- future root methodology should rename this evidence type more accurately.

## Decision-Level Consequence

The future decision engine should distinguish two HOLD pathways:

1. `wfo_negative_confirmed`
   - meaning WFO supports candidate inferiority
2. `wfo_underresolved`
   - meaning WFO did not confirm superiority, but also did not confirm inferiority

This keeps the exit code conservative while fixing the language and authority model.

## Reporting Consequence

Future reports should stop using wording like:

- "WFO fail implies instability"

for underresolved cases.

They should instead say:

- "WFO did not confirm positive OOS delta"
- "evidence state = underresolved"
- "this is distinct from delegated low-power"

## Non-Goals

- No adaptive split search.
- No retroactive rewrite of frozen artifacts.
- No alpha-retuning to force borderline passes.
- No use of PSR or full-sample bootstrap as a veto substitute for paired WFO evidence.

## Bottom Line

`wfo_low_power` and `underresolved` are not the same concept.

Current repo policy handles the first one, but not the second one.

The next root patch should preserve low-power delegation and add an explicit
underresolved state so that cases like canonical `E5+EMA21D1` are interpreted
correctly: **not positive-confirmed, not negative-confirmed, and not a code bug**.
