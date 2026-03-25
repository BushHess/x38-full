# VP1 — Contradiction report

## Summary
The prior spec pack did **not** contain a contradiction with the frozen facts that would change VP1's identity.
However, it did contain several internal inconsistencies and audit-quality mismatches that had to be patched before code-readiness.

## A. Contradictions vs VP1 frozen facts
**None found.**
The prior pack stayed aligned with the frozen facts:

- parent core = standard ATR + reversal ON + D1 ON
- slow_period = 140
- trail_mult = 2.5
- vdo_threshold = 0.0
- d1_ema_period = 28
- headline engine law = next-open event accounting
- headline D1 policy = prevday only
- BTC spot only
- H4 main
- long-only
- binary sizing = 100% NAV or 0%

## B. Internal contradictions / audit mismatches

### C-01 — VP1 naming mismatch (legacy)
- `Phase1ParentCore_ATRstandard_REVon_D1ON`
- `Phase1ParentCore_ATRstandard_REVon_D1on`

This is not a strategy-rule contradiction, but it **is** a spec identity contradiction for rebuild traceability.

### C-02 — “real trace” label overstated
The previous pack described a trace as a real rebuild-verification trace, but the indicator values inside that trace were partly recomputed outside the shipped artifact set.  
That is a trace-quality contradiction, not a strategy-rule contradiction.

### C-03 — acceptance tests mixed executable and non-executable expected values
The previous pack presented some full-history first-trade checkpoints as if they were usable acceptance anchors, while also admitting they were inferred from an unpreserved run.  
That is a test-design contradiction for strict audit purposes.

### C-04 — benchmark cost vs strategy cost not separated sharply enough
The previous pack made the headline 50 bps cost explicit, but did not draw a hard enough line between:
- VP1 strategy logic
- benchmark harness accounting / evaluation assumptions

This is not a frozen-fact contradiction, but it is an implementation-boundary contradiction that had to be patched.

## C. Contradictions vs engine law / prevday D1 law
**None found after inspection.**  
The prior pack was consistent on:
- decision at H4 close bar i
- fill at H4 open bar i+1
- fill price = open[i+1]
- valuation clock = H4 open post-fill
- D1 same-day usage forbidden in headline evaluation
- prevday mapping for all H4 bars on date d -> D1 date d-1
