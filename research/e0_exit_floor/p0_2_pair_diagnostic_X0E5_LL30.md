# Pair Diagnostic: X0E5_LL30 vs X0_E5EXIT

## Section 1: Machine Diagnostic (auto-filled)

**Classification**: near_identical
  near_equal_1bp=99.2%, corr=0.994
  subsampling_reliable=False

**Pair Profile** (n_bars=15647):
  equal_rate_tol=99.2%
  near_equal_1bp=99.2%
  near_equal_10bp=99.3%
  same_direction=99.3%
  return_correlation=0.994
  exposure_agreement=99.3%

**Bootstrap (Sharpe)**: p=0.477, CI=[-0.099, +0.093], width=0.192
**Bootstrap (geo growth)**: p=0.433, CI=[-0.000018, +0.000015]
**Subsampling**: p=0.018, CI=[-0.003, -0.003], support=0.00
**Consensus**: gap=41.5pp — FAILED

**DSR (X0E5_LL30)**: {27: 0.97, 54: 0.94, 100: 0.91, 200: 0.87, 500: 0.80, 700: 0.77}  (advisory only)
**DSR (X0_E5EXIT)**: {27: 0.97, 54: 0.94, 100: 0.91, 200: 0.87, 500: 0.80, 700: 0.77}  (advisory only)

**Caveats**:
  - Subsampling unreliable: near_equal_1bp_rate=99.2% > 80% threshold
  - Subsampling support=0.00 (expected for available effect sizes)
  - Very high return correlation (0.994) — strategies may be near-equivalent

**Suggested route**: no_action_default
  Reason: near_identical pair, no anomalous signal

**Generated**: 2026-03-16T20:40:59.892101+00:00
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
