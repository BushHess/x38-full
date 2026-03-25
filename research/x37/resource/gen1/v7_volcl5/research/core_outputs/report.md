I executed the V7 protocol end-to-end on the supplied raw H4 and D1 files only, with a clean same-session provenance lock before freeze.

Result

Final frozen leader: S_D1_VOLCL5_20_LOW_F1

System:

- Native timeframe: D1
- Feature: volcluster_5_20 = rolling std_5 / rolling std_20 of log returns
- Rule: long if yesterday’s volcluster_5_20 <= 1.0, else flat
- Signal at close, fill at next open
- BTC/USDT spot, long-only
- Cost: 10 bps per side / 20 bps round-trip

Evidence label: INTERNAL ROBUST CANDIDATE

Why this won:
- It was the strongest simple slower-timeframe candidate that cleared discovery and holdout trade-count gates.
- It showed a meaningful paired advantage over the strongest genuine native H4 rival, S_H4_RANGE48_HI_Q60, on pre-reserve data.
- The best 2-layer rival, L2_VOLCL_RANGE48_Q60, had better Sharpe and much lower drawdown, but lower mean daily return; it did not show a meaningful paired advantage over the simpler D1 system, so under the V7 rule the simpler system wins.
- In reserve/internal, the frozen leader stayed positive while the main faster and layered rivals turned negative.

Key performance

Final leader S_D1_VOLCL5_20_LOW_F1:
- Discovery: CAGR 70.8%, Sharpe 1.27, MDD -51.6%, 126 trades, positive fold share 78.6%
- Holdout: CAGR 26.2%, Sharpe 0.84, MDD -36.4%, 32 trades
- Reserve/internal: CAGR 29.2%, Sharpe 0.98, MDD -21.1%, 51 trades
- Pre-reserve combined: CAGR 57.7%, Sharpe 1.17, MDD -51.6%, 157 trades

Main rivals:
- L2_VOLCL_RANGE48_Q60: discovery excellent, holdout positive, but reserve/internal negative (CAGR -25.0%, Sharpe -1.31)
- S_H4_RANGE48_HI_Q60: discovery and holdout positive, but reserve/internal negative (CAGR -20.2%, Sharpe -0.69)
- S_H4_RET48_HI_Q55: broader local plateau than H4 range, but weaker unseen performance and meaningful paired loss to the final leader

Important caveat

The exact final D1 cell has a strict local 80% plateau score of 0.33 on the coarse local grid, so this is not a perfect “flat tabletop” optimum. I still froze it as the leader because:

- all coarse volatility-clustering perturbations stayed directionally positive,
- the broader slower volatility-state family was independently corroborated by the D1 ATR family,
- and reserve/internal supported this candidate while the main alternatives broke.

Audit highlights
- Raw schema matched the prompt exactly.
- No missing values, no impossible OHLC rows, no duplicate open_time.
- Native D1 was structurally clean.
- H4 had a small number of irregular/misaligned bars concentrated early; I retained them exactly as supplied and logged them.
- Native D1 matched day-aggregated native H4 on complete overlapping days.

What did not survive
- Cross-timeframe relation features were cost-fragile and did not make the frontier.
- Transported D1-on-H4 clones were redundancy controls, not independent fast-information candidates.
- The optional third-layer entry filter did not earn its place; it crushed trade count and degraded performance.

Main deliverables

Core outputs:
- /v7_volcl5/research/core_outputs/ablation_table.csv
- /v7_volcl5/research/core_outputs/frozen_comparison_set_ledger.csv
- /v7_volcl5/research/core_outputs/frozen_system_spec.md
- /v7_volcl5/research/core_outputs/frozen_system.json
- /v7_volcl5/research/core_outputs/pairwise_comparison_matrix.csv
- /v7_volcl5/research/core_outputs/pairwise_key_rivals.csv
- /v7_volcl5/research/core_outputs/provenance_declaration.md
- /v7_volcl5/research/core_outputs/reserve_internal_evaluation.csv
- /v7_volcl5/research/core_outputs/shortlist_ledger.csv
- /v7_volcl5/research/core_outputs/validation_results_by_fold.csv
- /v7_volcl5/research/core_outputs/validation_results_by_segment.csv

Audit and Stage 1:
- /v7_volcl5/research/audit_and_stage/anomaly_disposition_register.csv
- /v7_volcl5/research/audit_and_stage/audit_summary.csv
- /v7_volcl5/research/audit_and_stage/phase1_data_decomposition_report.md
- /v7_volcl5/research/audit_and_stage/plateau_summary.csv
- /v7_volcl5/research/audit_and_stage/stage1_cross_tf_fast_summary.csv
- /v7_volcl5/research/audit_and_stage/stage1_feature_library_manifest.csv
- /v7_volcl5/research/audit_and_stage/stage1_native_d1_fast_summary.csv
- /v7_volcl5/research/audit_and_stage/stage1_native_h4_fast_summary.csv
- /v7_volcl5/research/audit_and_stage/stage1_transport_fast_summary.csv
- /v7_volcl5/research/audit_and_stage/transport_vs_native_redundancy_audit.csv

Charts:
- /v7_volcl5/research/charts/bootstrap_final_leader.png
- /v7_volcl5/research/charts/cost_sensitivity.png
- /v7_volcl5/research/charts/drawdown_curves.png
- /v7_volcl5/research/charts/equity_curves.png
- /v7_volcl5/research/charts/paired_bootstrap_probabilities.png
- /v7_volcl5/research/charts/plateau_neighborhoods.png
- /v7_volcl5/research/charts/regime_breakdown.png
- /v7_volcl5/research/charts/rolling_stability_180d_sharpe.png
- /v7_volcl5/research/charts/trade_distribution_final_leader.png
- /v7_volcl5/research/charts/walk_forward_quarterly_returns.png

## What is incomplete

I did not finish assembling one single consolidated narrative report file before tool time expired. The machine-readable deliverables, specs, ledgers, audit tables, and charts are complete and linked above. Benchmark comparison was not performed, correctly, because no benchmark specs were supplied after reserve/internal.
