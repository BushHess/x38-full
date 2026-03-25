# Forward Decision Policy

This document explains the decision law used in forward evaluation sessions.

## Why this policy exists

A single appended window can be noisy.
If you make promotion or kill decisions on the latest window alone, you will create whipsaw in the candidate lineup.

Therefore the policy separates:
- **incremental window metrics**: what just happened in the latest appended window,
- **cumulative forward metrics**: what has happened since the candidate was frozen or last promoted.

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
- cumulative forward metrics since the candidate was frozen or last promoted.

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

- `INTERNAL_SEED_CANDIDATE`: frozen from seed, no forward window yet.
- `FORWARD_PROVISIONAL`: forward windows have started but cumulative evidence is not yet sufficient for FORWARD_CONFIRMED (requires >= 180 days and >= 6 entries). Promote/kill decisions are allowed once >= 90 days and >= 6 entries, even while the label remains FORWARD_PROVISIONAL.
- `FORWARD_CONFIRMED`: current active champion passes cumulative forward hard constraints and has enough forward evidence.
- `NO_ROBUST_CANDIDATE`: no live candidate survives the hard constraints.

## Why cumulative basis is the right default here

This research domain targets multi-day BTC spot mechanisms.
Trade counts are modest.
A single quarter can be dominated by a few trades or by one macro regime.
Cumulative forward basis is therefore a safer default for promote / keep / kill than latest-window basis alone.
