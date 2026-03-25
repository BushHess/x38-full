# P0.4 Stretch Gate Validation Protocol

## Objective

Validate whether `X0E5_CHOP_STRETCH18` is robust enough to deserve promotion from
research candidate to integration candidate.

This phase does **not** search new parameters. The candidate is frozen:

- reference: `X0_E5EXIT`
- candidate: `X0E5_CHOP_STRETCH18`
- direct gate: `entry_context == chop` and `entry_price_to_slow_atr > 1.8`

## Important Caveat

This is a **post-selection stability validation**, not a pristine pre-registered
holdout study. The stretch threshold came from the earlier forensics branch.

Therefore this phase must be interpreted conservatively:

- pass = candidate looks stable enough to justify integration as a formal repo candidate
- fail = candidate is too fragile even after a narrow, mechanism-first search

## Validation Layers

1. Full-period backtest
   - `2019-01-01` to `2026-02-20`
   - scenarios: `smart`, `base`, `harsh`

2. Recent holdout slice
   - pre-holdout: `2019-01-01` to `2023-12-31`
   - holdout: `2024-01-01` to `2026-02-20`
   - scenarios: `smart`, `base`, `harsh`

3. Rolling OOS windows
   - test window: `6 months`
   - step: `3 months`
   - first test starts after `24 months` of history
   - scenario: `harsh`

4. Paired bootstrap on actual engine equity
   - metrics: `Sharpe`, `CAGR`, `-MDD`
   - paired circular block bootstrap on full-period harsh equity

5. Pair diagnostic
   - classification, subsampling, directional bootstrap, DSR caveats
   - full-period harsh equity only

## Promotion Logic

There is no single magic gate, but the candidate should satisfy most of:

- full-period harsh remains better than reference
- recent holdout does not collapse
- rolling OOS windows are not one-sided against the candidate
- paired bootstrap direction is supportive rather than random
- pair diagnostic does not show instability or anomaly

If these fail, the stretch gate stays as a research artifact only.
