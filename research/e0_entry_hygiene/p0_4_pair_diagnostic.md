# Pair Diagnostic: X0E5_CHOP_STRETCH18 vs X0_E5EXIT

## Section 1: Machine Diagnostic (auto-filled)

**Classification**: borderline
  near_equal_1bp=94.8%, corr=0.964
  subsampling_reliable=False

**Pair Profile** (n_bars=15647):
  equal_rate_tol=94.8%
  near_equal_1bp=94.8%
  near_equal_10bp=95.4%
  same_direction=95.1%
  return_correlation=0.964
  exposure_agreement=95.2%

**Bootstrap (Sharpe)**: p=0.821, CI=[-0.108, +0.289], width=0.397
**Bootstrap (geo growth)**: p=0.701, CI=[-0.000025, +0.000043]
**Subsampling**: p=0.951, CI=[-0.056, +0.083], support=0.00
**Consensus**: gap=25.1pp — FAILED

**DSR (X0E5_CHOP_STRETCH18)**: {27: 0.98, 54: 0.97, 100: 0.95, 200: 0.92, 500: 0.86, 700: 0.84}  (advisory only)
**DSR (X0_E5EXIT)**: {27: 0.97, 54: 0.94, 100: 0.91, 200: 0.87, 500: 0.80, 700: 0.77}  (advisory only)

**Caveats**:
  - Subsampling unreliable: near_equal_1bp_rate=94.8% > 80% threshold
  - Subsampling support=0.00 (expected for available effect sizes)
  - Very high return correlation (0.964) — strategies may be near-equivalent

**Suggested route**: escalate_full_manual_review
  Reason: borderline classification — manual review required to determine if differential series is informative

**Generated**: 2026-03-16T20:36:06.883824+00:00
**Bootstrap config**: {'n_bootstrap': 2000, 'block_sizes': [10, 20, 40], 'seed': 1337}

---

## Section 2: Human Review Note (researcher fills in)

**Decision**: _______________
  Options: NO_ACTION | INCONCLUSIVE | PROMOTE | REJECT

**Reasoning**:
  [Explain which diagnostics support this decision and which are
  inconclusive. Cite specific values from Section 1.]

**Tradeoff summary**:
  [If the pair involves a Sharpe/MDD tradeoff, describe it here.]

**Unresolved concerns**:
  [List anything that cannot be resolved with current data.]
