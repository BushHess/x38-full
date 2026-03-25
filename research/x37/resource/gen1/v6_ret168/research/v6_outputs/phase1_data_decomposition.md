# Phase 1 data decomposition report

## What the raw measurement found
The strongest executable Stage 1 structure came from medium-term trend states and low-volatility regime filters. The discovery leaders were:

- Native D1 trend frontier: `S1_D1_RET40_Z0`
- Native H4 trend frontier: `S3_H4_RET168_Z0`
- Native D1 low-volatility regime: `S2_D1_VCL5_20_LT1.0`
- Native H4 sparse timing anomaly: `S4_H4_UPFR48_LT0.4`

## Orthogonality findings
- Transported slower information did **not** count as independent fast information. The H4-transported clone of D1_RET40 was perfectly redundant with the native D1 system.
- The cross-timeframe relation `H4_vs_D1_MA40` was strong but still too correlated with the native H4 trend frontier to justify separate leadership.
- `H4_UPFR48_LT0.4` was the most genuinely orthogonal native fast candidate, but it was sparse and lower-growth.

## Layering findings
Two-layer systems could improve headline metrics, especially volatility-gated H4 trend and D1-trend-gated H4 trend. But after paired comparisons, the extra layer(s) did not earn enough incremental advantage over the simpler H4 trend frontier to justify final leadership.

## Files
- `tables/phase1_top_features_by_family.csv`
- `tables/phase1_orthogonality_corr_matrix.csv`
- `tables/stage1_feature_registry_full.csv`
