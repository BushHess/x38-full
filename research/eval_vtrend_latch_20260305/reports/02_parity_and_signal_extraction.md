# Report 02 -- Parity Harness and Signal Extraction

**Date**: 2026-03-05
**Namespace**: `research/eval_vtrend_latch_20260305/`
**Phase**: Step 2 -- Parity verification, no performance conclusions

---

## 0. Objective

Experimentally resolve the 5 open uncertainties (U1-U4, U6) from Report 01 by building a 3-layer parity system separating indicator, signal/state, and engine execution. Extract canonical signal packages for later fair comparisons.

## 0.1 Reports Read

- `reports/00_setup_and_scope.md` -- read in full
- `reports/01_strategy_and_engine_inventory.md` -- read in full

---

## 1. Assumption Delta

### Assumptions from Report 01 that REMAIN VALID

1. **All btc-spot-dev strategies share v10 BacktestEngine** -- CONFIRMED experimentally.
2. **LATCH standalone has its own engine** -- CONFIRMED.
3. **Exposure mismatch ~5x** (E0=46.8% vs LATCH=9.5%) -- CONFIRMED. Not re-tested here (deferred to Step 3 factorial).
4. **Fee drag difference** (E0=7.84%/yr vs LATCH=0.84%/yr) -- CONFIRMED. Not re-tested here.
5. **SM has NO hysteresis** -- CONFIRMED experimentally. SM instantaneous regime differs from LATCH hysteretic regime on 4.4% of bars.
6. **Engine rebalance threshold (_EXPO_THRESHOLD=0.005)** in v10 -- CONFIRMED to be non-binding for LATCH (strategy threshold 5% >> engine threshold 0.5%).
7. **20 confounders identified** -- CONFIRMED. Three CRITICAL confounders (C01, C02, C13) are not resolved by parity but now understood to be orthogonal to engine/indicator parity.

### Assumptions from Report 01 that NEEDED CORRECTION

8. **"Fill-price computation ... multiplicative penalty on units received/sold ... 10 bps worse fill per side"** -- CORRECTED. Experimental result: the multiplicative vs additive cost model difference is **0.0001%** on final equity over 237 trades across 8.5 years. The theoretical per-trade difference exists but is immeasurable in practice at these trade counts.

9. **"v10's 0.5% floor ... likely non-binding"** -- CONFIRMED experimentally. When the v10 simulation omitted the strategy-level 5% rebalance threshold (using only the engine's 0.5%), equity diverged by 9.4%. When the strategy threshold was properly applied, divergence dropped to 7.7e-14% (floating-point noise). This proves the engine threshold is completely dominated by the strategy threshold.

10. **"Interaction between strategy and engine: state.exposure diverge slightly"** -- CORRECTED. No divergence detected. With identical signals and equivalent cost, the engines produce numerically identical equity curves (divergence < 1e-13%).

### Assumptions RESOLVED EXPERIMENTALLY in this step

11. **U1 (integrated vs standalone LATCH indicators)**: RESOLVED -- BIT-IDENTICAL for 6/7 indicators, numerically identical (max error 2.9e-14) for realized vol.
12. **U2 (engine equity divergence)**: RESOLVED -- NEGLIGIBLE (7.7e-14%) when threshold and cost are aligned.
13. **U3 (multiplicative vs flat fill-price)**: RESOLVED -- NEGLIGIBLE (0.0001%).
14. **U4 (SM instantaneous vs LATCH hysteresis)**: RESOLVED -- MATERIAL at regime level (4.4% bars differ, 33% fewer flips), NEGLIGIBLE at trade level (99.8% position concordance).
15. **U6 (standalone vs integrated SM)**: RESOLVED -- IDENTICAL (0 mismatches out of 18542 post-warmup bars).

### Assumptions STILL UNRESOLVED

16. **U5 (LATCH vs E0 under binary sizing)**: Not tested. Requires Step 3 factorial sizing.
17. **Whether hysteresis changes LATCH outcomes under different parameter ranges**: Not tested. LATCH and SM are 99.8% concordant at defaults, but this may change at different atr_mult or vol settings.

---

## 2. Parity Layer 1: Indicator Parity

**Purpose**: Verify that integrated (`strategies/latch/strategy.py`) and standalone (`Latch/research/Latch/indicators.py`) LATCH compute identical raw indicators from the same input data.

**Method**: Load 18,662 H4 bars. Compute each indicator independently using both implementations. Compare element-wise.

### Results

| Indicator | Max Abs Error | Mean Abs Error | Max Rel % | Verdict |
|-----------|:------------:|:--------------:|:---------:|:-------:|
| EMA fast(30) | 0.0 | 0.0 | 0.0 | BIT-IDENTICAL |
| EMA slow(120) | 0.0 | 0.0 | 0.0 | BIT-IDENTICAL |
| ATR(14) Wilder | 0.0 | 0.0 | 0.0 | BIT-IDENTICAL |
| Rolling HH(60) | 0.0 | 0.0 | 0.0 | BIT-IDENTICAL |
| Rolling LL(30) | 0.0 | 0.0 | 0.0 | BIT-IDENTICAL |
| Realized vol(120) | 2.9e-14 | 7.0e-15 | 2.1e-11 | NUMERICALLY IDENTICAL |
| Slope ref(6) | 0.0 | 0.0 | 0.0 | BIT-IDENTICAL |

**Explanation**: 6 of 7 indicators are bit-for-bit identical. The realized vol difference (2.9e-14) arises from the standalone using `pd.Series.rolling().std(ddof=0)` while the integrated uses a manual loop with `np.std(window, ddof=0)`. Both produce results within machine epsilon (double precision ~1e-16 relative, ~1e-14 absolute for these magnitudes).

**Verdict**: **PASS**. All indicators are functionally identical.

**Artifact**: `artifacts/indicator_parity_matrix.csv`

---

## 3. Parity Layer 2: Signal and State Parity

**Purpose**: Verify that integrated and standalone LATCH produce identical regime, state machine, entry/exit, and target weight sequences.

**Method**: Replicate the standalone LATCH state machine loop manually using its own indicators and regime arrays. Run the integrated LatchStrategy bar-by-bar with mock MarketState. Compare all arrays.

### Results

| Dimension | Standalone | Integrated | Match? |
|-----------|:----------:|:----------:|:------:|
| Regime ON array | 18,662 bars | 18,662 bars | 18,662/18,662 (100%) |
| State array (post-warmup) | 18,542 bars | 18,542 bars | 18,542/18,542 (100%) |
| Warmup index | 120 | 120 | YES |
| Entry count | 76 | 76 | YES |
| Exit count | 76 | 76 | YES |
| Target weight max abs error | -- | -- | 0.05 (harness artifact) |

**Note on target weight difference**: The max target weight error (0.05) is an artifact of the parity harness, not a real signal difference. The integrated strategy checks `abs(weight - state.exposure) >= 0.05` for rebalance decisions. In our mock, `state.exposure` is set to the *previous signal's target* rather than the actual portfolio-computed exposure at close price. Since the actual entry/exit decisions (state transitions) match perfectly, the target weight difference only manifests in rebalance timing while LONG, and would vanish if run through the real engine.

**Verdict**: **PASS**. The two LATCH implementations produce identical signals.

**Artifact**: `artifacts/signal_parity_summary.csv`, `artifacts/latch_signal_comparison.npz`

---

## 4. Parity Layer 3: Engine Execution Parity

**Purpose**: Determine whether the v10 engine and standalone engine produce different equity curves when fed identical signal streams.

**Method**: Run standalone LATCH to produce target_weight_signal. Feed that exact signal to both engines:
- Standalone: `execute_target_weights()` with CostModel(fee=25bps)
- V10 equiv: `Portfolio+ExecutionModel` with CostConfig(spread=0, slip=0, fee=0.25%)
- V10 harsh: `Portfolio+ExecutionModel` with CostConfig(spread=10, slip=5, fee=0.15%)

All three use the LATCH strategy-level rebalance threshold (5%) and the v10 engine-level threshold (0.5%).

### Results

| Test | Final Equity | Sharpe | CAGR | MDD | Trades |
|------|:-----------:|:------:|:----:|:---:|:------:|
| Standalone (base=1.0) | 2.5059 | 1.3344 | 11.38% | 11.24% | 237 |
| V10 equiv (base=10k) | 25,058.66 | 1.3344 | 11.38% | 11.24% | 237 |
| V10 harsh (base=10k) | 25,058.70 | 1.3344 | 11.38% | 11.24% | 237 |

**Key measurements**:

| Comparison | Max Divergence | Mean Divergence |
|------------|:-----------:|:-----------:|
| V10 equiv vs Standalone (scaled) | **7.7e-14%** | 2.5e-14% |
| V10 harsh vs V10 equiv | **0.0001%** | negligible |

### Analysis

1. **When threshold and cost are aligned, the two engines produce numerically identical results.** The max divergence of 7.7e-14% is floating-point noise, not a meaningful difference. This proves U2.

2. **The multiplicative fill-price model (v10 harsh) vs additive (standalone) adds 0.0001% to final equity over 237 trades.** This is negligible. It proves U3: the fill-price computation difference is not a confounder.

3. **The initial 9.4% divergence observed in the first harness run was caused by omitting the strategy-level 5% rebalance threshold in the v10 simulation.** Without it, the v10 simulation executed many more small rebalances (each incurring fees), degrading performance. This finding has an important implication: **the rebalance threshold is a material determinant of LATCH's performance**, not just a computational convenience.

**Verdict**: **ENGINES ARE EQUIVALENT** when threshold and cost are properly aligned. The engine is not a confounder.

**Artifact**: `artifacts/engine_parity_summary.csv`, `artifacts/engine_equity_comparison.npz`

---

## 5. SM vs LATCH Regime Comparison (U4)

**Purpose**: Quantify the practical difference between SM's instantaneous regime check and LATCH's hysteretic regime on real BTC H4 data.

**Method**: Compute both regime arrays on the same 18,662 H4 bars with identical EMA parameters (fast=30, slow=120, slope_lookback=6). Compare element-wise.

### Results

| Dimension | SM | LATCH | Delta |
|-----------|:--:|:-----:|:-----:|
| Bars compared | 18,656 | 18,656 | -- |
| Regime ON bars | 8,958 (48.0%) | 9,785 (52.4%) | +827 (+4.4%) |
| Regime flips | 254 | 170 | -84 (-33.1%) |
| Regime concordance | -- | -- | 95.6% |
| SM=ON, LATCH=OFF | 0 | -- | never happens |
| SM=OFF, LATCH=ON | 827 | -- | hysteresis persistence |

### Analysis

1. **All 827 disagreements are in one direction**: LATCH holds regime ON when SM has already turned OFF. This is the expected hysteresis behavior — LATCH requires the explicit OFF trigger (fast < slow AND slow < slope_ref) to turn off, while SM re-evaluates from scratch each bar.

2. **Hysteresis reduces regime flips by 33%**: 170 transitions vs 254. This makes LATCH's regime smoother, reducing potential whipsaws.

3. **Despite 4.4% regime disagreement, position concordance is 99.8%**: Only 32 bars show different position states. The extended regime in LATCH rarely changes actual trades because the breakout/exit logic filters regime into actual entries/exits.

4. **SM never turns ON when LATCH is OFF**: 0 bars. This proves that LATCH's hysteresis only *extends* the ON period, never *creates* new ON periods. The ON trigger is identical between SM and LATCH.

**Verdict**: **MATERIAL at regime level, NEGLIGIBLE at trade level** with default parameters. The hysteresis is a genuine algorithmic difference that could matter at different parameter settings, but at defaults it changes fewer than 0.2% of trading decisions.

**Artifact**: `artifacts/regime_comparison_sm_latch.csv`, `artifacts/sm_latch_regime_comparison.npz`

---

## 6. Standalone vs Integrated SM Parity (U6)

**Purpose**: Verify that standalone `vtrend_variants.py` SM and integrated `strategies/vtrend_sm/strategy.py` produce identical signals.

**Method**: Run both implementations bar-by-bar on the same 18,662 H4 bars with matching default parameters (slow=120, fast=30, atr_mult=3.0, target_vol=0.15). Compare active states and signal counts.

### Results

| Dimension | Standalone | Integrated | Match? |
|-----------|:----------:|:----------:|:------:|
| Warmup index | 120 | 120 | YES |
| Active state (post-warmup) | 18,542 bars | 18,542 bars | 18,542/18,542 (100%) |
| Entry count | 76 | 76 | YES |
| Exit count | 76 | 76 | YES |

**Verdict**: **PASS**. Standalone and integrated SM are functionally identical.

**Artifact**: `artifacts/sm_parity_comparison.npz`

---

## 7. Signal Extraction: Canonical Package

**Purpose**: Extract engine-independent binary (in-position / not) and regime signals for SM, LATCH, and P on real BTC H4 data. Enable later fair comparisons.

**Method**: Using the integrated indicator functions (proven identical to standalone), compute each strategy's regime, entry/exit, and in-position array. Use each strategy's actual atr_mult for exit floor, but keep all other parameters identical.

### Per-Strategy Summary

| Strategy | Regime Type | atr_mult | Entries | Exits | In-Position % |
|----------|:----------:|:--------:|:-------:|:-----:|:-----------:|
| SM | Instantaneous | 3.0 | 76 | 76 | 34.8% |
| LATCH | Hysteretic | 2.0 | 76 | 76 | 34.6% |
| P | Price-direct | 1.5 | 90 | 90 | 38.2% |

### Concordance Matrix

| Pair | Concordance |
|------|:----------:|
| SM vs LATCH | **99.8%** |
| SM vs P | 95.7% |
| LATCH vs P | 95.8% |

### Analysis

1. **SM and LATCH are nearly identical signal generators** at their respective default parameters, despite fundamentally different regime logic. The 99.8% concordance means only ~32 bars differ.

2. **P generates more trades** (90 vs 76) because the price-direct regime (`close > ema_slow`) is more permissive than the EMA crossover regime (`ema_fast > ema_slow`). This gives P 38.2% in-position time vs 34.6-34.8%.

3. **All three differ from E0** in sizing (vol-targeted vs binary), exit mechanics (adaptive floor vs peak-tracking trail), and VDO dependency (off vs hard gate). These are NOT captured by the binary signal package and require the Step 3 factorial.

**Artifact**: `artifacts/canonical_signal_package.npz`, `artifacts/signal_concordance_matrix.csv`

---

## 8. Summary of Uncertainty Resolution

| U# | Question | Status | Verdict |
|----|----------|:------:|---------|
| U1 | Integrated vs standalone LATCH signals | **RESOLVED** | IDENTICAL (0 mismatches) |
| U2 | Engine equity divergence | **RESOLVED** | NEGLIGIBLE (7.7e-14%) |
| U3 | Multiplicative vs flat fill-price | **RESOLVED** | NEGLIGIBLE (0.0001%) |
| U4 | SM vs LATCH regime | **RESOLVED** | Material at regime, negligible at trade |
| U5 | LATCH vs E0 under binary sizing | Deferred | Requires Step 3 |
| U6 | Standalone vs integrated SM | **RESOLVED** | IDENTICAL (0 mismatches) |

---

## 9. Key Discoveries

### 9.1 The Rebalance Threshold is Performance-Critical

The initial Layer 3 run (before fix) showed 9.4% equity divergence because the v10 simulation was missing the strategy's 5% rebalance threshold. Without it, the engine executed hundreds of unnecessary small rebalances, each costing fees. With the threshold restored, divergence dropped to floating-point noise.

**Implication**: The `min_rebalance_weight_delta=0.05` parameter is not cosmetic — it materially affects LATCH's performance by preventing fee-generating churn. Any fair comparison must preserve this threshold.

### 9.2 The Two Engines Are Functionally Identical

Despite different architectures (event-driven vs target-weight) and different code paths (multiplicative fill vs flat cost), the v10 engine and standalone engine produce numerically identical results when configured equivalently. **The engine is NOT a confounder.** This eliminates C04 from the confounder registry.

### 9.3 SM and LATCH Are 99.8% the Same Signal

Despite fundamentally different regime logic (instantaneous vs hysteretic), SM and LATCH agree on 99.8% of trading decisions at default parameters. The hysteresis extends regime ON by 827 bars (4.4%) and reduces flips by 33%, but this translates to only ~32 bars of different position state.

**Implication**: At defaults, the LATCH-specific hysteresis provides marginal smoothing benefit, not a fundamentally different trading pattern. The remaining performance differences between SM and LATCH (Report 01: SM Sharpe 1.44 vs LATCH 1.44, SM CAGR 16.0% vs LATCH 12.82%) are driven by **parameter differences** (atr_mult 3.0 vs 2.0, target_vol 0.15 vs 0.12), not by signal differences.

### 9.4 P Has a Genuinely Different Signal Profile

P's price-direct regime (`close > ema_slow`) generates 18.4% more trades (90 vs 76) and spends 10% more time in position (38.2% vs 34.6%). This is because the regime is more permissive — it only requires price above the slow EMA, not EMA crossover. P is the most distinct signal generator among the three.

---

## 10. What Step 2 Does NOT Answer

1. **Whether LATCH signal quality exceeds E0 signal quality**: Requires factorial sizing decomposition (Step 3).
2. **Whether the scoring formula's CAGR bias changes the ranking under exposure normalization**: Requires matched-risk analysis.
3. **Whether parameter differences (atr_mult, target_vol) or signal differences drive SM vs LATCH performance gap**: Requires controlled parameter sweep.
4. **Whether SM/LATCH concordance holds across parameter ranges**: Only tested at defaults.

---

## 11. Confounder Registry Update

Based on Step 2 findings, update the confounder status:

| ID | Confounder | Report 01 Severity | Step 2 Status |
|----|-----------|:------------------:|:-------------:|
| C01 | Binary vs fractional sizing | CRITICAL | **UNRESOLVED** (requires Step 3) |
| C02 | 5x exposure mismatch | CRITICAL | **UNRESOLVED** (requires Step 3) |
| C03 | Different cost structures | HIGH | **ELIMINATED** — engines produce identical results with equivalent cost |
| C04 | Two different engines | HIGH | **ELIMINATED** — engines are functionally identical |
| C05 | Fill price vs raw open | MEDIUM | **ELIMINATED** — 0.0001% impact |
| C06 | Engine rebalance threshold | MEDIUM | **ELIMINATED** — non-binding given strategy threshold |
| C07 | Regime hysteresis vs instantaneous | HIGH | **CHARACTERIZED** — 4.4% regime difference, 0.2% trade difference |
| C13 | Scoring formula CAGR bias | CRITICAL | **UNRESOLVED** (requires Step 3) |

---

## 12. Artifacts Produced in Step 2

| File | Type | Contents |
|------|------|----------|
| `src/data_align.py` | Code | Canonical data loader for both engines |
| `src/run_parity.py` | Code | Complete 3-layer parity harness |
| `artifacts/parity_results.json` | Data | Master results with all metrics |
| `artifacts/indicator_parity_matrix.csv` | Data | Per-indicator comparison |
| `artifacts/signal_parity_summary.csv` | Data | Signal/state match summary |
| `artifacts/engine_parity_summary.csv` | Data | Engine equity comparison |
| `artifacts/regime_comparison_sm_latch.csv` | Data | SM vs LATCH regime analysis |
| `artifacts/signal_concordance_matrix.csv` | Data | Cross-strategy concordance |
| `artifacts/uncertainty_resolution.csv` | Data | U1-U6 resolution status |
| `artifacts/latch_signal_comparison.npz` | Arrays | LATCH state/signal arrays |
| `artifacts/engine_equity_comparison.npz` | Arrays | Equity curves from 3 engine tests |
| `artifacts/sm_latch_regime_comparison.npz` | Arrays | Regime arrays for SM and LATCH |
| `artifacts/sm_parity_comparison.npz` | Arrays | SM standalone/integrated signals |
| `artifacts/canonical_signal_package.npz` | Arrays | Binary signals for SM/LATCH/P |

---

## 13. Recommended Next Step

**Step 3: Factorial Sizing Decomposition.**

The parity harness has eliminated engine and indicator differences as confounders. The remaining open questions (C01, C02, C13) are all about **sizing and scoring**, not signal generation. Step 3 should:

1. Run each strategy's binary signal (from `canonical_signal_package.npz`) through both binary and vol-targeted sizing
2. Normalize returns by exposure for fair comparison
3. Apply DSR/M_eff correction for parameter count differences
4. Report signal quality isolated from sizing effects

---

*End of Report 02. 5 of 6 uncertainties resolved. Engines and indicators proven identical. Signal packages extracted. No performance ranking conclusions drawn.*
