# Forward Decision Policy

This document explains the decision law used in forward evaluation sessions.

## Why this policy exists

A single appended window can be noisy.
If you make promotion or kill decisions on the latest window alone, you will create whipsaw in the candidate lineup.

Therefore the policy separates:
- **incremental window metrics**: what just happened in the latest appended window,
- **cumulative forward metrics**: what has happened since the candidate's version was frozen.

## Evidence is version-scoped

All forward metrics are scoped to the `system_version_id` being evaluated.
Only data with timestamps > `freeze_cutoff_utc` of that version counts as clean forward evidence.

If forward results from one version were used to inform a redesign, those results are NOT
clean evidence for the redesigned version. The new version's evidence starts from zero.

## Two cumulative scopes and how they relate

There are two distinct cumulative windows in the system. They serve different purposes:

1. **Version-scoped evidence** (anchored at `freeze_cutoff_utc`):
   Used for `FORWARD_CONFIRMED` label eligibility (180 days + 6 entries since freeze).
   This clock never resets within a `system_version_id`.

2. **Candidate-scoped cumulative metrics** (anchored at `cumulative_anchor_utc`):
   Used for ranking, paired bootstrap, promote/kill decisions.
   This resets on promotion: a newly promoted champion starts fresh cumulative metrics
   from its promotion date, so that its performance as champion is tracked separately.

**Reconciliation rule**: When checking whether a candidate qualifies for `FORWARD_CONFIRMED`,
count total calendar days and entries since `freeze_cutoff_utc` of the version (scope 1),
not since `cumulative_anchor_utc` (scope 2). When computing cumulative forward metrics for
ranking and decision-making, use `cumulative_anchor_utc` (scope 2). These are complementary,
not contradictory: one gates label eligibility, the other drives operational decisions.

## Standard review cadence

Standard forward review should happen on this cadence:
- at least every 180 calendar days,
- normally every 90 calendar days,
- earlier only when an emergency trigger fires.

## Emergency review triggers

An early forward review is allowed if any of the following occurs:
- data integrity failure in the appended delta,
- operational inability to reconstruct deterministic state,
- active champion cumulative forward drawdown at 50 bps exceeds the constitution hard cap.

## Reported metrics

Every forward evaluation session must report for each live candidate:
- incremental metrics for the latest appended window,
- cumulative forward metrics since the candidate's `cumulative_anchor_utc` (set at freeze; reset on promotion — see "Two cumulative scopes" above).
- `system_version_id` for every reported metric.

## Decision basis

### Promotion / kill / confirmation decisions
These decisions use the **cumulative forward basis**, not the latest window alone.

### Minimum evidence threshold
Promotion or kill is not allowed unless both of these are true:
- cumulative forward calendar days >= 90
- cumulative forward entries >= 6

If the threshold is not met:
- only provisional labeling is allowed,
- emergency breach handling is still allowed.

## Champion retention rule

The champion remains champion unless:
- an eligible challenger ranks above the champion on cumulative forward objective,
- and the challenger shows meaningful paired advantage over the champion,
- or the champion fails cumulative hard constraints while the challenger passes.

## Challenger promotion rule

A challenger may be promoted only if all of the following hold:
- minimum cumulative evidence threshold is met,
- challenger passes cumulative hard constraints,
- challenger ranks above the champion on cumulative forward objective,
- challenger shows meaningful paired advantage over the champion on cumulative forward daily returns,
  or the champion fails cumulative hard constraints while the challenger passes.

## Challenger kill rule

A challenger may be retired if any of the following hold:
- after at least 180 cumulative forward days, it fails cumulative hard constraints in two consecutive standard reviews,
- after at least 180 cumulative forward days, its cumulative 50 bps CAGR is non-positive and it has no meaningful paired advantage over the champion,
- after at least 360 cumulative forward days, it has fewer than two entries and no explicit low-turnover exception in its frozen spec.

## Labels

- `INTERNAL_SEED_CANDIDATE`: frozen under a system_version_id, no forward window yet for that version.
- `FORWARD_PROVISIONAL`: forward windows have started but cumulative evidence is not yet sufficient for FORWARD_CONFIRMED. Promote/kill decisions are allowed once >= 90 days and >= 6 entries.
- `FORWARD_CONFIRMED`: current active champion passes cumulative forward hard constraints and has enough forward evidence (>= 180 days, >= 6 entries), all scoped to this system_version_id.
- `NO_ROBUST_CANDIDATE`: no live candidate survives the hard constraints.

### Checking FORWARD_CONFIRMED after a promotion

When a candidate is promoted, its candidate-scoped `cumulative_forward_metrics` are reset to zero
(scope 2). However, `FORWARD_CONFIRMED` eligibility uses version-scoped evidence (scope 1).

To check eligibility after a promotion:

1. **Count version-scoped days and entries** from `forward_evaluation_ledger.csv`:
   filter rows where `system_version_id` matches the active version and `candidate_id` matches
   the current champion, then sum `incremental_days` and `incremental_entries` across all windows.
   All candidates (including former challengers) are evaluated on every forward window, so the
   current champion has ledger rows spanning the entire version even if it was promoted mid-version.

2. **Recompute version-scoped cumulative metrics** from `forward_daily_returns.csv`:
   filter rows where `system_version_id` matches the active version, `candidate_id` matches the
   current champion, and `date_utc` falls after `freeze_cutoff_utc`. Compute Sharpe, MDD, and
   hard constraint checks from this full daily series. This file must retain the champion's
   complete daily series for the active version (see retention rule in STATE_PACK_SPEC).

3. **Check cumulative hard constraints** against the version-scoped metrics from step 2.

Do not use the candidate-scoped `cumulative_forward_metrics` from `candidate_registry.json` for
this check — those were reset on promotion and reflect only post-promotion performance.

## Forward evaluation does NOT trigger redesign

A forward evaluation chat must NEVER initiate a redesign. If the researcher sees results that
motivate a redesign:

1. Complete and package the forward evaluation normally.
2. Close the forward evaluation chat.
3. Optionally explore in sandbox (non-lineage).
4. Prepare a redesign dossier.
5. Open a redesign_freeze chat only if all guardrail conditions are met.

## Why cumulative basis is the right default here

This research domain targets multi-day BTC spot mechanisms.
Trade counts are modest.
A single quarter can be dominated by a few trades or by one macro regime.
Cumulative forward basis is therefore a safer default for promote / keep / kill than latest-window basis alone.

## Series-level artifacts

Forward evaluation must produce path-level artifacts (daily returns, optionally equity curve)
per candidate per version, not just summary statistics. Without the raw series:
- cumulative Sharpe cannot be correctly recomputed across windows,
- cumulative MDD requires the full equity path,
- paired bootstrap requires the raw daily return series.

These artifacts are append-only in `forward_daily_returns.csv` with `system_version_id` per row.
The active file retains the full version-scoped daily series since `freeze_cutoff_utc`; candidate-scoped
cumulative metrics anchored at `cumulative_anchor_utc` are computed as filtered views over that retained series,
not by truncating the stored file on promotion.
