# E1.2 Shadow Execution Artifacts — Schema

## shadow_fills.csv (186 rows, one per X0 base-scenario trade)

### Identification
| Column | Type | Description |
|--------|------|-------------|
| trade_id | int | X0 trade ID (1-indexed) |
| entry_ts_ms | int | Entry fill timestamp (epoch ms) = H4 bar open_time |
| exit_ts_ms | int | Exit fill timestamp (epoch ms) = H4 bar open_time |
| qty | float | BTC quantity filled |
| entry_notional_usd | float | qty * baseline_entry_mid (for IS weighting) |

### Baseline fills (from BacktestEngine)
| Column | Type | Description |
|--------|------|-------------|
| baseline_entry_mid | float | H4 bar open price at entry (mid, no cost) |
| baseline_exit_mid | float | H4 bar open price at exit (mid, no cost) |
| baseline_entry_fill | float | Engine entry fill = mid * (1 + spread/2 + slip) |
| baseline_exit_fill | float | Engine exit fill = mid * (1 - spread/2 - slip) |
| baseline_pnl_usd | float | Net PnL from BacktestEngine (includes all costs) |
| baseline_net_return_pct | float | Net return % from BacktestEngine |

### Shadow fills — TWAP (raw price, no cost added)
| Column | Type | Description |
|--------|------|-------------|
| twap_entry_price | float | Mean of 4 M15 closes starting at entry_ts_ms |
| twap_exit_price | float | Mean of 4 M15 closes starting at exit_ts_ms |

### Shadow fills — VWAP (raw price, no cost added)
| Column | Type | Description |
|--------|------|-------------|
| vwap_entry_price | float | Volume-weighted typical price of 4 M15 bars |
| vwap_exit_price | float | Volume-weighted typical price of 4 M15 bars |

### Primary path: price-only deltas (bps, vs baseline mid)
| Column | Type | Description |
|--------|------|-------------|
| twap_entry_delta_bps | float | (twap_entry / baseline_mid - 1) * 10000 |
| twap_exit_delta_bps | float | (twap_exit / baseline_mid - 1) * 10000 |
| twap_combined_delta_bps | float | -entry_delta + exit_delta (positive = improved) |
| vwap_entry_delta_bps | float | Same for VWAP |
| vwap_exit_delta_bps | float | Same for VWAP |
| vwap_combined_delta_bps | float | Same for VWAP |

### Secondary path: scenario re-pricing
| Column | Type | Description |
|--------|------|-------------|
| twap_shadow_entry_fill | float | twap_entry * (1 + slip_bps/10000) |
| twap_shadow_exit_fill | float | twap_exit * (1 - slip_bps/10000) |
| twap_shadow_pnl_usd | float | Re-priced PnL using shadow fills + base fee |
| twap_pnl_delta_usd | float | twap_shadow_pnl - baseline_pnl |
| vwap_shadow_entry_fill | float | Same for VWAP |
| vwap_shadow_exit_fill | float | Same for VWAP |
| vwap_shadow_pnl_usd | float | Same for VWAP |
| vwap_pnl_delta_usd | float | Same for VWAP |

### Quality flags
| Column | Type | Description |
|--------|------|-------------|
| entry_m15_count | int | Number of M15 bars found in entry window (expect 4) |
| exit_m15_count | int | Number of M15 bars found in exit window (expect 4) |
| entry_fallback | bool | True if entry TWAP fell back to baseline mid |
| exit_fallback | bool | True if exit TWAP fell back to baseline mid |

## shadow_summary.json

Top-level keys: `twap`, `vwap`. Each contains:

| Key | Description |
|-----|-------------|
| D1_implementation_shortfall | total_is_bps, total_is_usd |
| D2_entry_delta | mean, median, std, p5, p25, p75, p95 |
| D3_exit_delta | mean, median, std, p5, p25, p75, p95 |
| D4_combined_delta | mean, median, std, p5, p95 |
| D5_improved_vs_worsened | improved, worsened, neutral, frac_improved, mean_improved_bps, mean_worsened_bps |
| D6_concentration | yearly_mean_delta_bps, years_positive, total_years, max_single_year_pct, notional_delta_correlation, reentry/nonreentry means |
| D7_secondary_path | total_pnl_delta_usd, mean_pnl_delta_usd, sign_consistent_with_primary |
| D8_reference | baseline_total_pnl_usd |
| GO_HOLD_gates | 6 boolean gates + verdict |

## shadow_metadata.json

Provenance: spec version, strategy, scenario, data counts, cost params, fallback counts.

## Sign Conventions

- **entry_delta_bps**: positive = shadow bought HIGHER than baseline (worse for buyer)
- **exit_delta_bps**: positive = shadow sold HIGHER than baseline (better for seller)
- **combined_delta_bps**: positive = trade IMPROVED (bought cheaper and/or sold higher)
- **pnl_delta_usd**: positive = shadow trade earned MORE than baseline
