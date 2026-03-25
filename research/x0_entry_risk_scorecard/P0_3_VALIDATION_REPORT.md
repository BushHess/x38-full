# P0.3 Entry Risk Scorecard Validation

## Verdict

- `WARNING_ONLY`
- Rationale: `risk_bucket_is_real_but_not_clean_enough_for_default_gate`
- Elapsed: `13.79s`
- Need full 47-technique stack now: `False`
- Trigger for full stack: `only_if_promoting_a_new_gated_strategy`

## Parity

- `X0`: fills=True, trades=True, summary=True
- `X0_E5EXIT`: fills=True, trades=True, summary=True

## Cohort Tables

### X0 / full

| Risk | Trades | Share | Avg pnl | Median pnl | Total pnl | Win rate |
|---|---:|---:|---:|---:|---:|---:|
| low_non_chop | 43 | 0.250000 | 2440.317173 | 185.835313 | 104933.638456 | 0.534884 |
| medium_chop | 76 | 0.441860 | 2095.823261 | -245.332213 | 159282.567845 | 0.460526 |
| high_chop_stretch | 53 | 0.308140 | -391.977007 | -1067.351222 | -20774.781395 | 0.283019 |

### X0 / holdout

| Risk | Trades | Share | Avg pnl | Median pnl | Total pnl | Win rate |
|---|---:|---:|---:|---:|---:|---:|
| low_non_chop | 12 | 0.235294 | 349.127851 | 123.187487 | 4189.534215 | 0.750000 |
| medium_chop | 22 | 0.431373 | 208.602125 | -46.009318 | 4589.246755 | 0.454545 |
| high_chop_stretch | 17 | 0.333333 | -59.791899 | -288.894798 | -1016.462287 | 0.352941 |

### X0_E5EXIT / full

| Risk | Trades | Share | Avg pnl | Median pnl | Total pnl | Win rate |
|---|---:|---:|---:|---:|---:|---:|
| low_non_chop | 51 | 0.274194 | 2840.019878 | -87.130027 | 144841.013760 | 0.490196 |
| medium_chop | 78 | 0.419355 | 2090.972230 | -170.646834 | 163095.833918 | 0.461538 |
| high_chop_stretch | 57 | 0.306452 | 51.986890 | -855.428116 | 2963.252709 | 0.350877 |

### X0_E5EXIT / holdout

| Risk | Trades | Share | Avg pnl | Median pnl | Total pnl | Win rate |
|---|---:|---:|---:|---:|---:|---:|
| low_non_chop | 13 | 0.236364 | 407.064545 | 124.507815 | 5291.839083 | 0.692308 |
| medium_chop | 23 | 0.418182 | 155.804808 | -7.657693 | 3583.510580 | 0.478261 |
| high_chop_stretch | 19 | 0.345455 | -2.644312 | -119.402822 | -50.241919 | 0.421053 |

## Bootstrap Gaps

| Strategy | Period | Gap | Left N | Right N | Observed | CI95 Low | CI95 High | p(>0) |
|---|---|---|---:|---:|---:|---:|---:|---:|
| X0 | full | low_non_chop_minus_high_chop_stretch | 43 | 53 | 2832.294181 | -896.363755 | 6935.720459 | 0.9268 |
| X0 | full | medium_chop_minus_high_chop_stretch | 76 | 53 | 2487.800269 | -655.31195 | 5569.504086 | 0.9364 |
| X0 | holdout | low_non_chop_minus_high_chop_stretch | 12 | 17 | 408.91975 | -258.342675 | 1244.859364 | 0.8598 |
| X0 | holdout | medium_chop_minus_high_chop_stretch | 22 | 17 | 268.394024 | -318.428674 | 882.446251 | 0.8218 |
| X0_E5EXIT | full | low_non_chop_minus_high_chop_stretch | 51 | 57 | 2788.032988 | -951.306301 | 7123.667196 | 0.928 |
| X0_E5EXIT | full | medium_chop_minus_high_chop_stretch | 78 | 57 | 2038.98534 | -1185.673173 | 5257.469441 | 0.8974 |
| X0_E5EXIT | holdout | low_non_chop_minus_high_chop_stretch | 13 | 19 | 409.708856 | -188.365357 | 1188.766084 | 0.8974 |
| X0_E5EXIT | holdout | medium_chop_minus_high_chop_stretch | 23 | 19 | 158.449119 | -272.462162 | 636.403668 | 0.7436 |

## WFO Summary

| Strategy | Eligible windows | Total windows | PnL order pass | Win-rate order pass | Both pass |
|---|---:|---:|---:|---:|---:|
| X0 | 4 | 8 | 1.0 | 1.0 | 1.0 |
| X0_E5EXIT | 5 | 8 | 1.0 | 0.8 | 0.8 |

## Final Interpretation

- Running the full 47-technique stack is not necessary for the scorecard itself because this path is instrumentation plus cohort diagnostics, not a promoted trading rule.
- If a gated strategy is promoted from this scorecard, that gated strategy must then go through the full validation framework.
- Prior gate research still matters: `X0_CHOP_STRETCH18` improved `X0`, but `X0E5_CHOP_STRETCH18` stayed research-only after holdout/WFO review.

