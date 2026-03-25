# Step 2 Method & Regression Notes

## Profile Source Modes

| Candidate | Mode | Notes |
|-----------|------|-------|
| E0 | imported | From `results/trade_profile_8x5/E0/profile.json` |
| E5 | imported | From `results/trade_profile_8x5/E5/profile.json` |
| SM | imported | From `results/trade_profile_8x5/SM/profile.json` |
| LATCH | imported | From `results/trade_profile_8x5/LATCH/profile.json` |
| E0_plus_EMA1D21 | imported | From `results/trade_profile_8x5/E0_plus_EMA1D21/profile.json` |
| E5_plus_EMA1D21 | **computed_step2** | Gap closure. Profile computed from trade CSV + H4 bars. |

## E0 Regression Check

13/13 checks PASS. Step 2 E0 outputs reproduce Step 1 exactly:
- Trade count: 192
- Giveback valid count: 188, median: 1.206
- Native zero-cross: index 6 (CAGR < 0 at 3.1% removal)
- Unit-size zero-cross: index 11 (CAGR < 0 at 5.7% removal)
- Native cliff flags: terminal=True, cagr=True
- Unit-size cliff flags: terminal=True, cagr=True
- Skip-after-N delta Sharpe: all 4 N values match within tolerance 0.02

## Method Conventions (all frozen from Step 1)

- Sharpe: mean/std(ddof=0) * sqrt(trades_per_year)
- CAGR (native): ((NAV0 + sum(pnl_usd)) / NAV0)^(1/6.5) - 1
- CAGR (unit-size): prod(1 + r/100)^(1/6.5) - 1
- Giveback: (MFE_pct - realized_return_pct) / MFE_pct where MFE > 0; NA otherwise
- Cliff threshold: 3.0 (score = |marginal_damage| / avg_damage)
- Skip-after-N: N in {2,3,4,5}; skip next after N consecutive losses (return_pct <= 0); reset after skip

## E5_plus_EMA1D21 Gap Closure

E5_plus_EMA1D21 had no entry in `results/trade_profile_8x5/`. Step 2 computed the full T1-T8 profile from:
- Trade CSV: `results/parity_20260306/eval_e5_ema21d1_vs_e0/results/trades_candidate.csv` (186 trades)
- MFE/MAE: computed from H4 bars using the same `bisect_left/right` method as trade_profile_8x5.py
- Gini: same formula as trade_profile_8x5 (on |pnl_usd|)

The computed profile uses the same conventions but is NOT saved to the canonical `trade_profile_8x5/` directory. It exists only within Step 2 artifacts.
