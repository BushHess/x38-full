# E0 Step 1 Method Notes

## Ledger Views

### Fill Ledger
Source: `results/parity_20260305/eval_e0_vs_e0/results/trades_candidate.csv` (192 trades, 22 columns). Produced by `validate_strategy.py --trade-level on` with `--cost-scenario harsh` (50 bps RT). Period: 2019-01-01 to 2026-02-20, initial cash $10,000.

### Native Episode Ledger
Derived from Fill Ledger. Sorted by `pnl_usd` descending for jackknife and sensitivity curve operations. Adds:
- `native_positive_contribution_rank`: 1-based rank among trades with pnl_usd > 0 (80 trades)
- `cum_share_of_total_pnl`: cumulative percentage of total net PnL from top trades
- `is_top_10_native`: flag for top-10 trades by pnl_usd
- `giveback_ratio`, `mfe_pct`, `mae_pct`: joined from MFE/MAE computation

### Unit-Size Episode Ledger
Same derivation but sorted by `return_pct` descending. Uses return_pct for ranking and compounded terminal wealth:
- `unit_size_terminal = NAV0 * product(1 + r/100 for r in included_returns)`
- `unit_size_positive_contribution_rank`: 1-based rank among trades with return_pct > 0

## Conventions

### T7 Jackknife (from trade_profile_8x5.py)
- `Sharpe = mean(return_pct) / std(return_pct, ddof=0) * sqrt(trades_per_year)`
- `CAGR = ((NAV0 + sum(pnl_usd)) / NAV0)^(1/BACKTEST_YEARS) - 1`
- `BACKTEST_YEARS = 6.5`, `NAV0 = 10000`
- `trades_per_year = n_remaining / BACKTEST_YEARS`

### Giveback Ratio
- `MFE_pct = (max(H4_highs during hold) - entry_price) / entry_price * 100`
- `giveback_ratio = (MFE_pct - realized_return_pct) / MFE_pct` where MFE_pct > 0
- Trades with MFE_pct <= 0: giveback = NA (4 trades)
- Range: [0, infinity). Value > 1 means trade lost money despite positive MFE.

### Sensitivity Curve
- Native: sort trades by pnl_usd desc; remove top-K one at a time; recompute terminal = NAV0 + sum(remaining pnl_usd), CAGR, Sharpe
- Unit-size: sort trades by return_pct desc; remove top-K one at a time; recompute terminal = NAV0 * product(1 + r/100), CAGR from terminal, Sharpe from remaining returns
- Window: 0 to ~20% of trades (39 removal steps for 192 trades)
- Anchor checks: sensitivity curve at K={1,3,5,10} reproduces T7 jackknife points exactly (tolerance: Sharpe 1e-6, CAGR 1e-6, PnL 0.01)

### Cliff-Edge Detection
- `deltas[k] = |remaining_metric[k] - remaining_metric[k-1]|`
- `avg_delta = mean(|deltas|)` over entire removal window
- `cliff_score[k] = |deltas[k]| / avg_delta`
- Cliff detected if `max(cliff_score) > 3.0` (Step 0 frozen threshold)
- Computed independently for terminal_value, cagr, and sharpe in both native and unit-size views

### Skip-After-N-Losses
- Walk trades in entry_ts order
- Track consecutive losses (return_pct <= 0)
- When consecutive_losses >= N, skip the NEXT trade (mark removed)
- Reset loss counter after a skip (skipped trade not counted toward streak)
- Recompute Sharpe and terminal from remaining trades
- N tested: {2, 3, 4, 5}

## Key Implementation Decisions

1. **Native terminal uses additive PnL**: `terminal = NAV0 + sum(pnl_usd)`. This matches the T7 jackknife convention. It is an approximation since actual compounding means sum(pnl) != terminal_wealth - NAV0, but it is the convention frozen in trade_profile_8x5.py.

2. **Unit-size terminal uses compounded returns**: `terminal = NAV0 * product(1 + return_pct/100)`. This gives the exposure-neutral view of what the strategy would return with equal-size bets.

3. **Giveback uses pre-existing MFE from trade_profile_8x5**: The MFE/MAE per-trade CSV (`mfe_mae_per_trade.csv`) was computed from H4 bar highs/lows during each trade's holding period using `bisect_left/right` for efficient indexing. Giveback extends this computation.

4. **Sensitivity curve step size**: removal_pct increments are 1/n_trades (one trade per step), not fixed 1% steps. This gives exact trade-by-trade resolution.

## Reproduction

```bash
cd /var/www/trading-bots/btc-spot-dev
python3 research/fragility_audit_20260306/code/step1/run_step1_e0.py
```

All outputs written to `research/fragility_audit_20260306/artifacts/step1/`.
