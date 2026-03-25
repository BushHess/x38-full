# D1d1 Implementation & Smoke Test Summary
Historical snapshot remains candidate-mining-only. Smoke test restricted to discovery fold 1 (2020-01-01 to 2020-03-31 UTC). No holdout or reserve_internal data is used for entries, exits, or returns.
## Implementation Notes
- Base candidate modules are self-contained and expose `run_candidate(data_by_timeframe, config, cost_rt_bps, start_utc=None, end_utc=None, initial_state=None)`.
- Slow bars are aligned causally with `merge_asof(..., direction="backward")` on `close_time`, so only fully closed slower bars are visible to faster decision bars.
- Gap-aware rolling/shift operations block feature calculations across missing-bar segments; no synthetic repair or fill is performed.
- Execution is next-open only: decision at bar close, trade at next bar open, interval returns marked from that execution open to the next execution open.
- Cost invariance is enforced by construction: `cost_rt_bps` only changes net interval/daily returns, not signal path or trade timestamps.
- Candidate 3 fits the daily trade-surprise regression only on data with `close_time < start_utc` when a test window is supplied.

## Implementation Files
- `d1d_impl_btcsd_20260318_c1_av4h.py`
- `d1d_impl_btcsd_20260318_c2_flow1hpb.py`
- `d1d_impl_btcsd_20260318_c3_trade4h15m.py`

### Ablation Variants
- `d1d_impl_btcsd_20260318_c1_av4h_no_d1_permission.py`
- `d1d_impl_btcsd_20260318_c1_av4h_no_h4_execution.py`
- `d1d_impl_btcsd_20260318_c2_flow1hpb_no_d1_flow_permission.py`
- `d1d_impl_btcsd_20260318_c2_flow1hpb_no_h1_execution.py`
- `d1d_impl_btcsd_20260318_c2_flow1hpb_no_h4_context.py`
- `d1d_impl_btcsd_20260318_c3_trade4h15m_no_d1_participation_permission.py`
- `d1d_impl_btcsd_20260318_c3_trade4h15m_no_h4_context.py`
- `d1d_impl_btcsd_20260318_c3_trade4h15m_no_m15_timing.py`

## Smoke Test Results
### btcsd_20260318_c1_av4h
- Tested config: `cfg_001` with parameters `{"q_d1_antivol_rank": 0.35, "q_h4_rangepos_entry": 0.55, "q_h4_rangepos_hold": 0.45}`
- Fold 1 entries: **1**
- Exposure: **23.8532%**
- Gross return: **8.141038%**
- Net return @ 50 bps RT: **7.600097%**
- Cost invariant check (0 vs 50 bps identical trade path): **PASS**
- Next-open timestamp check: **PASS**
- Terminal state: `{"position_state": "flat", "position_fraction": 0.0, "entry_time_utc": null, "entry_price": null, "trail_state": {}, "custom_state": {"candidate_id": "btcsd_20260318_c1_av4h", "decision_timeframe": "4h", "config_id": "cfg_001", "disabled_layers": []}, "last_signal_time_utc": "2020-03-31T19:59:59.999000+00:00", "reconstructable_from_warmup_only": true}`
- First trade rows:
  - `{"candidate_id": "btcsd_20260318_c1_av4h", "config_id": "cfg_001", "trade_id": 1, "entry_time_utc": "2020-01-29T00:00:00+00:00", "entry_price": 9375.34, "exit_time_utc": "2020-02-19T20:00:00+00:00", "exit_price": 10138.59, "gross_return": 0.08141038085018781, "net_return": 0.07641038085018781, "bars_held": 130, "duration_seconds": 1886400.0}`

### btcsd_20260318_c2_flow1hpb
- Tested config: `cfg_007` with parameters `{"q_h4_rangepos_min": 0.3, "theta_h1_ret168_entry": -0.04, "theta_h1_ret168_hold": 0.01}`
- Fold 1 entries: **1**
- Exposure: **0.6431%**
- Gross return: **-0.433227%**
- Net return @ 50 bps RT: **-0.682475%**
- Cost invariant check (0 vs 50 bps identical trade path): **PASS**
- Next-open timestamp check: **PASS**
- Terminal state: `{"position_state": "long", "position_fraction": 1.0, "entry_time_utc": "2020-03-31T10:00:00+00:00", "entry_price": 6440.04, "trail_state": {}, "custom_state": {"candidate_id": "btcsd_20260318_c2_flow1hpb", "decision_timeframe": "1h", "config_id": "cfg_007", "disabled_layers": []}, "last_signal_time_utc": "2020-03-31T22:59:59.999000+00:00", "reconstructable_from_warmup_only": true}`
- First trade rows:
  - `{"candidate_id": "btcsd_20260318_c2_flow1hpb", "config_id": "cfg_007", "trade_id": 1, "entry_time_utc": "2020-03-31T10:00:00+00:00", "entry_price": 6440.04, "exit_time_utc": null, "exit_price": null, "gross_return": null, "net_return": null, "bars_held": null, "duration_seconds": null}`

### btcsd_20260318_c3_trade4h15m
- Tested config: `cfg_019` with parameters `{"q_h4_rangepos_entry": 0.55, "q_h4_rangepos_hold": 0.35, "rho_m15_relvol_min": 1.1}`
- Fold 1 entries: **4**
- Exposure: **33.7088%**
- Gross return: **13.738786%**
- Net return @ 50 bps RT: **11.483296%**
- Cost invariant check (0 vs 50 bps identical trade path): **PASS**
- Next-open timestamp check: **PASS**
- Terminal state: `{"position_state": "flat", "position_fraction": 0.0, "entry_time_utc": null, "entry_price": null, "trail_state": {}, "custom_state": {"candidate_id": "btcsd_20260318_c3_trade4h15m", "decision_timeframe": "15m", "config_id": "cfg_019", "disabled_layers": []}, "last_signal_time_utc": "2020-03-31T23:44:59.999000+00:00", "reconstructable_from_warmup_only": true}`
- First trade rows:
  - `{"candidate_id": "btcsd_20260318_c3_trade4h15m", "config_id": "cfg_019", "trade_id": 1, "entry_time_utc": "2020-01-01T01:45:00+00:00", "entry_price": 7212.34, "exit_time_utc": "2020-01-03T00:00:00+00:00", "exit_price": 6965.49, "gross_return": -0.034226062553900705, "net_return": -0.0392260625539007, "bars_held": 185, "duration_seconds": 166500.0}`
  - `{"candidate_id": "btcsd_20260318_c3_trade4h15m", "config_id": "cfg_019", "trade_id": 2, "entry_time_utc": "2020-01-17T00:30:00+00:00", "entry_price": 8691.21, "exit_time_utc": "2020-01-20T00:00:00+00:00", "exit_price": 8701.72, "gross_return": 0.0012092677544324193, "net_return": -0.003790732245567581, "bars_held": 286, "duration_seconds": 257400.0}`

## Readiness Confirmation
All 3 base candidates and all 8 required ablation variants were written successfully, imported successfully, and passed fold-1 smoke checks for next-open execution and cost invariance. Ready for D1d2.
