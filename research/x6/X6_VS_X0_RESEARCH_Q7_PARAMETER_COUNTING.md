# Research Q7: Parameter Counting & Double Standard Analysis

**Date**: 2026-03-08
**Sources**: YAML configs, strategy classes, sensitivity grids, exit_family_study.py, Report 16

---

## 1. Exact Parameter Listing

### Shared Base (all 6 strategies)
These are structural constants, identical across ALL strategies:

| Parameter | Value | Role |
|-----------|:-----:|------|
| atr_period | 14 | Wilder standard for ATR |
| vdo_fast | 12 | VDO fast EMA |
| vdo_slow | 28 | VDO slow EMA |
| fast_period | max(5, slow//4) | Derived from slow_period |

### Strategy-Specific Parameters

#### E0 (Base VTREND)
**Config**: `configs/vtrend/vtrend_default.yaml`

| Parameter | Value | Source | Searched? |
|-----------|:-----:|:------:|:---------:|
| slow_period | 120 | yaml | YES (16 TS, plateau 60-144) |
| trail_mult | 3.0 | yaml | YES (sweep 2.0-5.0) |
| vdo_threshold | 0.0 | yaml | YES (boundary optimal) |

**YAML params: 3** | **Class params: 3**

#### X0 (E0 + D1 Regime)
**Config**: `configs/vtrend_x0/vtrend_x0_default.yaml`

| Parameter | Value | Source | Searched? |
|-----------|:-----:|:------:|:---------:|
| slow_period | 120 | yaml | YES |
| trail_mult | 3.0 | yaml | YES |
| vdo_threshold | 0.0 | yaml | YES (boundary) |
| **d1_ema_period** | **21** | **yaml** | **YES (range 15-40d proven)** |

**YAML params: 4** | **Class params: 4**

#### E5 (Robust ATR Trail)
**Config**: `configs/vtrend_e5/vtrend_e5_default.yaml`

| Parameter | Value | Source | Searched? |
|-----------|:-----:|:------:|:---------:|
| slow_period | 120 | yaml | YES |
| trail_mult | 3.0 | yaml | YES |
| vdo_threshold | 0.0 | yaml | YES (boundary) |
| **ratr_cap_q** | **0.90** | **yaml** | **YES (0.85, 0.90, 0.95)** |
| **ratr_cap_lb** | **100** | **yaml** | **YES (50, 100, 200)** |
| **ratr_period** | **20** | **yaml** | **NO (convention)** |

**YAML params: 6** | **Class params: 6**

#### E5+EMA1D21 (Robust ATR + D1 Regime)
**Config**: `configs/vtrend_e5_ema21_d1/vtrend_e5_ema21_d1_default.yaml`

| Parameter | Value | Source | Searched? |
|-----------|:-----:|:------:|:---------:|
| slow_period | 120 | yaml | YES |
| trail_mult | 3.0 | yaml | YES |
| vdo_threshold | 0.0 | yaml | YES (boundary) |
| d1_ema_period | 21 | yaml | YES |
| **ratr_cap_q** | **0.90** | **default** | **YES (in exit_family_study)** |
| **ratr_cap_lb** | **100** | **default** | **YES (in exit_family_study)** |
| **ratr_period** | **20** | **default** | **NO (convention)** |

**YAML params: 4** | **Class params: 7**

The 3 ratr params are exposed in the `VTrendE5Ema21D1Config` dataclass (lines 44-46 of strategy.py) but **NOT listed in the YAML config**. They take effect via class defaults.

#### X2 (X0 + Adaptive Trail)
**Config**: `configs/vtrend_x2/vtrend_x2_default.yaml`

| Parameter | Value | Source | Searched? |
|-----------|:-----:|:------:|:---------:|
| slow_period | 120 | yaml | YES |
| **trail_tight** | **3.0** | **yaml** | **YES (2.7, 3.0, 3.3 in validation)** |
| **trail_mid** | **4.0** | **yaml** | **NO (convention)** |
| **trail_wide** | **5.0** | **yaml** | **NO (convention)** |
| **gain_tier1** | **0.05** | **yaml** | **NO (convention)** |
| **gain_tier2** | **0.15** | **yaml** | **NO (convention)** |
| vdo_threshold | 0.0 | yaml | YES (boundary) |
| d1_ema_period | 21 | yaml | YES |

**YAML params: 8** | **Class params: 8**

#### X6 (X2 + Breakeven Floor)
**Config**: `configs/vtrend_x6/vtrend_x6_default.yaml`

| Parameter | Value | Source | Searched? |
|-----------|:-----:|:------:|:---------:|
| (identical to X2) | | | |

**YAML params: 8** | **Class params: 8**

X6 adds NO new parameters. The breakeven floor reuses `gain_tier1` as threshold and `entry_price` (runtime state, not a parameter) as the floor level. It's a **code change**, not a parameter addition.

---

## 2. Parameter Count Summary

| Strategy | YAML params | Class params | Incremental vs E0 (class) |
|----------|:-----------:|:------------:|:-------------------------:|
| E0 | 3 | 3 | — |
| X0 | 4 | 4 | +1 |
| E5 | **6** | 6 | +3 |
| E5+EMA1D21 | **4** | **7** | **+4** |
| X2 | 8 | 8 | +5 |
| X6 | 8 | 8 | +5 |

### The Accounting Discrepancy

E5+EMA1D21's YAML shows **4 params** (matching X0), but its strategy class has **7 params**. The 3 ratr params are hidden as class defaults, absent from the config file. This creates the illusion of equivalent complexity to X0.

By contrast, X2/X6 explicitly list ALL 8 params in YAML. No hiding.

---

## 3. Which Parameters Were Actually Optimized?

| Parameter | When searched | Search space | Found at |
|-----------|:------------:|:-------------|:--------:|
| slow_period | Study #3+ | 16 TS [30..720] | 120 (plateau 60-144) |
| trail_mult | Study #7 | sweep 2.0-5.0 | 3.0 (balanced) |
| vdo_threshold | Study #4 | tested 0.0 vs positive | 0.0 (boundary) |
| d1_ema_period | Study #41 | range 15-40d | 21 (convention) |
| ratr_cap_q | exit_family_study | 0.85, 0.90, 0.95 | 0.90 (convention) |
| ratr_cap_lb | exit_family_study | 50, 100, 200 | 100 (convention) |
| ratr_period | never | — | 20 (convention) |
| trail_tight | X2 validation | 2.7, 3.0, 3.3 | 3.0 |
| trail_mid | never | — | 4.0 (convention) |
| trail_wide | never | — | 5.0 (convention) |
| gain_tier1 | never | — | 0.05 (convention) |
| gain_tier2 | never | — | 0.15 (convention) |

---

## 4. Effective Degrees of Freedom

Naive parameter counting overstates complexity because:
1. **Boundary values** (vdo_threshold=0.0) consume ~0 DOF — they're at the trivial edge
2. **Ordered constraints** (trail_tight < trail_mid < trail_wide) reduce independent DOF
3. **Convention values** never searched are not optimized DOF
4. **Plateaus** (slow_period 60-144 all equivalent) mean less DOF consumed

### Effective DOF Estimation

| Strategy | Nominal | Convention params | Boundary params | Ordering constraints | Effective DOF |
|----------|:-------:|:-----------------:|:---------------:|:-------------------:|:-------------:|
| **E0** | 3 | 0 | 1 (vdo=0) | 0 | **~2.0** |
| **X0** | 4 | 1 (d1_ema) | 1 (vdo=0) | 0 | **~2.5** |
| **E5** | 6 | 1 (ratr_period) | 1 (vdo=0) | 0 | **~3.5** |
| **E5+EMA1D21** | 7 | 2 (ratr_period, d1_ema) | 1 (vdo=0) | 0 | **~4.0** |
| **X2** | 8 | 4 (mid, wide, t1, t2) | 1 (vdo=0) | 2 sets ordered | **~3.5** |
| **X6** | 8 | 4 (mid, wide, t1, t2) | 1 (vdo=0) | 2 sets ordered | **~3.5** |

### Reasoning for X2/X6 ordering correction

The adaptive trail has 5 new parameters (trail_tight, trail_mid, trail_wide, gain_tier1, gain_tier2) replacing 1 (trail_mult). But:

- **{tight, mid, wide} must be ordered**: 3 values with constraint tight ≤ mid ≤ wide. This is equivalent to choosing 1 base value + 2 spreads. The base (tight=3.0) was searched; the spreads (mid−tight=1.0, wide−tight=2.0) were set by convention. Effective DOF: **~1.5** (searched base + 2 half-DOF convention spreads)

- **{tier1, tier2} must be ordered**: 2 values with constraint tier1 < tier2. Equivalent to 1 location + 1 spread. Both convention. Effective DOF: **~0.5** (1 convention pair)

- Total incremental DOF from adaptive trail: ~2.0
- Total X2 DOF: E0 base (~2.0) + d1_ema (~0.5) + adaptive trail (~2.0) = ~**3.5 on the trail component** (but we should count from X0, not E0)
- X2 vs X0: +2.0 effective DOF from adaptive trail

### Reasoning for E5+EMA1D21

- ratr_cap_q: searched 3 values → ~0.7 DOF
- ratr_cap_lb: searched 3 values → ~0.7 DOF
- ratr_period: convention only → ~0.3 DOF
- d1_ema_period: broad range proven → ~0.5 DOF
- Total incremental over E0: ~2.2 effective DOF

---

## 5. Is There a Double Standard?

### YES — on three levels:

### Level 1: Accounting sleight-of-hand

E5+EMA1D21's YAML config shows 4 params. X2's YAML shows 8. But E5+EMA1D21's **class** has 7 params. The 3 ratr params are hidden as defaults.

| | YAML count | True count | Presented as |
|---|:---------:|:----------:|:------------:|
| E5+EMA1D21 | 4 | 7 | "4 params" |
| X2 | 8 | 8 | "7 params vs X0's 4" |

The X2 evaluation report explicitly cited "7 params vs 4" as a rejection reason. If the same standard applied to E5+EMA1D21, it would be "7 params vs E0's 3" — an even larger gap.

### Level 2: E5's mechanism was RETIRED

Report 16 (2026-03-03) proved E5's robust ATR is a **scale-mismatch artifact**:
- MDD wins: 16/16 → 6/16 when scale-matched (trail=3.14 for E5)
- Cap effect: 8/16 (chance)
- Cap × period interaction: 2/16 (harmful)
- Conclusion: "No provable advantage over E0"

Yet E5+EMA1D21 was PROMOTED on 2026-03-06 (3 days later) carrying the exact same retired ratr mechanism. The 3 ratr params add **zero proven value** but still consume DOF.

### Level 3: Effective DOF is comparable

| Strategy | Nominal params | Effective DOF | Verdict |
|----------|:--------------:|:-------------:|:-------:|
| E5+EMA1D21 | 7 (4 shown) | ~4.0 | **PROMOTE** |
| X2 | 8 (8 shown) | ~3.5 | **REJECT** |
| X6 | 8 (8 shown) | ~3.5 | **REJECT** |

X2/X6 actually have LOWER effective DOF than E5+EMA1D21 because ordering constraints reduce independence. Yet X2/X6 were penalized for complexity while E5+EMA1D21 was not.

---

## 6. Why This Double Standard Exists

The double standard is not deliberate fraud — it's a consequence of:

1. **Different evaluation baselines**: X2 was evaluated vs X0 (δ=+3 params), while E5+EMA1D21 was evaluated vs E0 (δ=+4 params but 3 hidden as defaults)

2. **YAML-based presentation**: The validation framework counts YAML-exposed params. E5+EMA1D21's hidden defaults escape the count.

3. **Outcome-based reasoning**: E5+EMA1D21 passed all validation gates (WFO 5/8, holdout positive). X2/X6 failed WFO and holdout. When a strategy passes, param count is noted but not penalized. When it fails, param count becomes a cited reason.

4. **Temporal separation**: E5's retirement (Report 16, March 3) and E5+EMA1D21's promotion (Study #43, March 6) happened days apart. The ratr retirement wasn't propagated to the E5+EMA1D21 evaluation.

---

## 7. Fair Comparison Matrix

| Criterion | E5+EMA1D21 | X2 | X6 |
|-----------|:----------:|:--:|:--:|
| YAML params | 4 | 8 | 8 |
| True class params | **7** | 8 | 8 |
| Effective DOF | **~4.0** | ~3.5 | ~3.5 |
| Params searched | 5/7 | 4/8 | 4/8 |
| Convention-only params | 2 | 4 | 4 |
| Contains retired mechanism? | **YES (ratr)** | no | no |
| WFO | 5/8 | 4/8 | 4/8 |
| Holdout | positive | negative | negative |
| Verdict | PROMOTE | REJECT | REJECT |

---

## 8. Summary

| Question | Answer |
|----------|--------|
| E0 params? | **3** (slow_period, trail_mult, vdo_threshold) |
| X0 params? | **4** (+d1_ema_period) |
| E5 params? | **6** (+ratr_cap_q, ratr_cap_lb, ratr_period) |
| E5+EMA1D21 params? | **7** (4 in YAML, 3 hidden as class defaults) |
| X2 params? | **8** (all in YAML) |
| X6 params? | **8** (same as X2, BE floor is code not param) |
| Effective DOF? | E5+EMA1D21 ≈ 4.0 > X2/X6 ≈ 3.5 |
| Double standard? | **YES** — E5+EMA1D21 has more effective DOF but was PROMOTED. X2/X6 have less effective DOF but complexity was cited as rejection reason. E5's ratr mechanism was retired 3 days before E5+EMA1D21's promotion. |
| Intentional? | **NO** — caused by YAML-only counting, different baselines, and outcome-biased attribution |
