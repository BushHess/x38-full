# D1e1 Report — Hard Constraint Filter & Surviving Candidates

## 1. Hard Constraint Filter

50 bps RT rows filtered from `d1d_wfo_aggregate.csv`:

- All rows at 50 bps: 38 in → **18 survived** → 20 eliminated
  - base configs: 30 in → 16 survived → 14 eliminated
  - ablation variants: 8 in → 2 survived → 6 eliminated

**Constraint basis:**

- discovery length = 1277 days
- discovery years = 1277 / 365 = 3.4986301369863013
- entries/year = total_entries / 3.4986301369863013

**Elimination reasons across all 50 bps rows:**

| Reason | Count |
|---|---|
| cagr<=0 \| mdd>0.45 \| exposure_out_of_range | 5 |
| cagr<=0 \| mdd>0.45 | 5 |
| mdd>0.45 | 4 |
| cagr<=0 \| exposure_out_of_range | 4 |
| entries_per_year_out_of_range | 2 |

**Key outcome by candidate:**

| Candidate | Survived / Total |
|---|---|
| `btcsd_20260318_c1_av4h` | 4 / 6 |
| `btcsd_20260318_c2_flow1hpb` | 0 / 12 |
| `btcsd_20260318_c3_trade4h15m` | 12 / 12 |

**Notable failures:**

- cfg_004 fails only on MDD > 0.45
- cfg_006 fails only on entries/year < 6
- all `c2_flow1hpb` base configs fail on CAGR ≤ 0, with several also failing MDD and/or exposure

**Files:** `d1e_hard_constraint_filter.csv`

## 2. Ablation Promotion

**No promotion was triggered.**

Per multi-layer candidate with ABLATION_FAIL:

| Parent candidate | Promoted? | Reason |
|---|---|---|
| `btcsd_20260318_c1_av4h` | No | main configs survive Step 1, so promotion path is closed |
| `btcsd_20260318_c2_flow1hpb` | No | zero main configs survive, but best failing ablation variant `d1d_impl_btcsd_20260318_c2_flow1hpb_no_h1_execution` still fails hard constraints (agg_mdd = 0.800599 > 0.45) |
| `btcsd_20260318_c3_trade4h15m` | No | main configs survive Step 1, so promotion path is closed |

**Important nuance:**

- `c1_no_d1_permission` and `c3_no_m15_timing` both pass hard constraints, but they are not eligible for promotion because their parent candidates already have surviving main configs.
- c2 had the only candidate-slot scenario where promotion could have happened, and it failed the rule.

## 3. Representative Configs

Best surviving base config per candidate, ranked by raw Calmar_50bps within each candidate:

| Candidate | Representative config | Agg CAGR | Agg Sharpe | Agg MDD | Entries | Exposure | Calmar_50bps |
|---|---|---|---|---|---|---|---|
| `btcsd_20260318_c1_av4h` | cfg_001 | 0.229900 | 0.976175 | 0.215691 | 22 | 0.182780 | 1.065877 |
| `btcsd_20260318_c3_trade4h15m` | cfg_025 | 0.397348 | 1.010698 | 0.382188 | 65 | 0.370755 | 1.039666 |

**Representative parameter values:**

- **cfg_001:**
  - `q_d1_antivol_rank = 0.35`
  - `q_h4_rangepos_entry = 0.55`
  - `q_h4_rangepos_hold = 0.45`
- **cfg_025:**
  - `q_h4_rangepos_entry = 0.65`
  - `q_h4_rangepos_hold = 0.35`
  - `rho_m15_relvol_min = 1.10`

**File:** `d1e_surviving_candidates.csv`

## 4. Complexity Penalty

**Penalty formula:**

- 0.02 × layers
- 0.03 × tunables
- `adjusted_preference = Calmar_50bps - complexity_penalty`

| Candidate | Layers | Tunables | Penalty | Calmar_50bps | Adjusted preference |
|---|---|---|---|---|---|
| `btcsd_20260318_c1_av4h` | 2 | 3 | 0.13 | 1.065877 | 0.935877 |
| `btcsd_20260318_c3_trade4h15m` | 3 | 3 | 0.15 | 1.039666 | 0.889666 |

**Adjusted-preference ordering at this stage:**

1. `btcsd_20260318_c1_av4h`
2. `btcsd_20260318_c3_trade4h15m`

Both surviving candidates remain flagged for later review because D1d3 found at least one ABLATION_FAIL on each parent candidate.

## 5. Files Saved

- `d1e_hard_constraint_filter.csv`
- `d1e_surviving_candidates.csv`
- `d1e1_summary.md`

---

D1e1 is complete. **Ready for D1e2.**
