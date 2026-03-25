# D1e3 Bootstrap & Final Ranking

- Surviving candidates into bootstrap: 2
- Candidates passing bootstrap LB5 > 0: 2
- Ranking key: adjusted_preference from D1e1; tie-breaks not activated because adjusted_preference values were not tied.

## Bootstrap Check

- `btcsd_20260318_c1_av4h`: block5=0.0000863895, block10/LB5=0.0000393651, block20=-0.0000497382, pass=True
- `btcsd_20260318_c3_trade4h15m`: block5=0.0001804607, block10/LB5=0.0001650301, block20=0.0001794175, pass=True

## Final Ranking

- Rank 1: `btcsd_20260318_c1_av4h` | adjusted_preference=0.935877 | Calmar_50bps=1.065877 | holdout_pass_50bps=False | reserve_cagr_50bps=0.128182
- Rank 2: `btcsd_20260318_c3_trade4h15m` | adjusted_preference=0.889666 | Calmar_50bps=1.039666 | holdout_pass_50bps=True | reserve_cagr_50bps=-0.115998
