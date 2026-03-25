# X36 Program Note 03 — Repo-Wide WFO Sanity Check

**Date**: 2026-03-17  
**Scope**: current repo validation behavior relevant to `x36`

## Question

If current full evaluations show that no major candidate clears `wfo_robustness`,
is that more consistent with:

1. a real implementation bug in WFO, or
2. a segmentation / methodology problem in the current gate design?

## Checks Performed

### 1. Validation test suite sanity

Targeted validation tests were executed for:

- WFO invalid-window handling
- WFO power-only summary and seed stability
- WFO summary JSON contract
- holdout/WFO overlap handling
- decision payload / gate authority

Result: `42 passed`.

This materially lowers the probability of a straightforward code bug in the current
`validation/` WFO implementation.

### 2. Current full-eval strategy state

Observed current repo-wide results:

- `E5+EMA21D1`: strong full-sample + holdout, but canonical WFO soft-fail
- `X0 / EMA21D1`: same pattern, weaker than E5
- `X7`, `X8`: not only WFO fail; they also fail hard performance gates

Therefore the fact that `X7/X8` fail WFO does **not** imply the WFO gate is wrong;
those strategies are already inferior on stronger evidence.

### 3. Split-menu sanity beyond E5

`E5+EMA21D1` active branch result:

- `canonical_24_6_last8`: FAIL
- `short_horizon_24_3_last12`: FAIL
- `long_horizon_24_9_last6`: PASS
- `canonical_24_6_all`: PASS

Ad hoc reproduction for `X0 / EMA21D1` under the same split menu:

- `canonical_24_6_last8`: FAIL
- `short_horizon_24_3_last12`: FAIL
- `long_horizon_24_9_last6`: PASS
- `canonical_24_6_all`: FAIL

Interpretation:

- The canonical `24m/6m/last8` design is indeed harsh for both of the repo's two
  strongest current non-baseline candidates.
- But the pattern is not identical across candidates.
- E5 is more design-sensitive than X0.
- X0 still lacks enough cross-split evidence to claim robustness even after relaxing
  coverage.

## Legacy Branch Relevance

`branches/a_vcbb_bias_study/` is **not** decisive evidence for the current WFO gate:

- its main comparison framework is historical and descriptive;
- its Section 4 WFO is not the current validation gate;
- `test_battery/` contains a `PENDING_RERUN.md` warning that several artifacts are
  stale after 2026-03-16 system fixes.

So that branch can support intuition about path robustness, but it cannot by itself
prove a present-day WFO implementation bug.

## Conclusion

Current evidence is **not** consistent with a simple WFO coding bug.

Current evidence **is** consistent with a methodological problem in using one frozen
canonical segmentation (`24m/6m/last8`) as a decisive robustness authority for the
current strategy family, especially because:

- the suite does not retrain per window;
- inference is based on a small number of terminal OOS slices;
- `E5+EMA21D1` changes verdict under alternative preregistered segmentations;
- `X0` also improves under at least one alternative segmentation.

Best current reading:

- WFO code path: likely correct
- Current canonical segmentation authority: likely too brittle as the sole decisive
  pairwise robustness filter for this strategy family
- E5: strongest evidence of segmentation sensitivity
- X0: weaker strategy, but still suggests the canonical split is harsher than its
  label alone implies
