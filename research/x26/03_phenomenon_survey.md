# Phase 3: Phenomenon Survey & Scoring

**Date**: 2026-03-11
**Inputs**: 01_audit_state_map.md, 02_flat_period_eda.md (Obs01–Obs29)
**Method**: 5-criterion scoring (S1–S5) per Phase 3 protocol

---

## 3.1 Observation Filter

### EXCLUDED (15 observations)

| Obs | Description | Exclusion Reason |
|-----|-------------|------------------|
| Obs11 | FLAT mean -2.05 bps | Mechanical consequence of VTREND filtering out trends |
| Obs12 | FLAT kurtosis 22.49 | Known/universal: fat tails in all financial returns |
| Obs13 | FLAT skew -0.126 | Mechanical: trail stop truncates IN_TRADE tails asymmetrically |
| Obs15 | \|return\| ACF 0.278 | Known/universal: vol clustering (GARCH) present everywhere |
| Obs16 | PACF lag-6 | Subsumed by Obs14 (same 24h phenomenon) |
| Obs18 | Hurst mixed | Ambiguous/unreliable; subsumed by Obs17 (VR test) |
| Obs19 | FLAT vol > IN_TRADE | Descriptive property, not structured phenomenon |
| Obs20 | Vol elevated mid-period | Mechanical: vol compression at boundaries IS the entry/exit condition |
| Obs21 | No flat→trade predict | Null result — no structure to score |
| Obs22 | Pre-entry drift +1.03% | Mechanical: EMA crossover requires prior price rise |
| Obs24 | Post-exit vol decay | Known microstructure effect at trade exits |
| Obs25 | H1 reproduces H4 | Confirms Obs14/17, not independent phenomenon |
| Obs26 | D1 Hurst 0.467 | Subsumed by Obs17 (mean-reversion) |
| Obs27 | Cross-TF consistency | Confirms Obs14/17, not independent |
| Obs29 | Stability confirmation | Meta-observation about Obs28 |

### KEPT for scoring (4 phenomena)

| ID | Name | Source | Key Statistic |
|----|------|--------|---------------|
| P1 | Mean-Reversion within FLAT | Obs17 | Per-period VR(2)=0.762, p<1e-23 |
| P2 | Return Autocorrelation / 24h Periodicity | Obs14 | Per-period ACF(6)=-0.077, ACF(1)=-0.132 |
| P3 | Post-Exit Asymmetry | Obs23 | Winners +0.91%, Losers +0.58% post-exit |
| P4 | Calendar Return Effect | Obs28 | Hourly return KW p=0.0001, range 10.8 bps |

**Note on P1/P2 relationship**: Mean-reversion (VR<1) and negative lag-1 autocorrelation are mathematically linked: VR(2) ≈ 1 + ρ(1). P2's lag-6 (24h) component adds specific harmonic structure beyond P1's general mean-reversion. They are related but not identical — P2 captures a periodicity P1 does not distinguish.

---

## 3.2 Scoring Results

### P1: Mean-Reversion within FLAT periods (Obs17)

**S1: SIGNAL STRENGTH → STRONG**
- Cohen's d = -0.866 (vs VR=1 null), t = -11.68, p = 7.7e-24
- N = 182 flat periods with ≥3 bars
- Mean per-period VR(2) = 0.762 (well below random walk VR=1)

**S2: TEMPORAL STABILITY → STABLE**
| Block | N | Mean VR(2) | t | p | Significant |
|-------|---|-----------|---|---|-------------|
| 1 | 47 | 0.798 | -5.11 | <0.0001 | YES |
| 2 | 49 | 0.712 | -7.86 | <0.0001 | YES |
| 3 | 43 | 0.781 | -4.95 | <0.0001 | YES |
| 4 | 43 | 0.762 | -5.50 | <0.0001 | YES |

All 4 blocks same sign (VR<1), all 4 significant.

**S3: ECONOMIC MAGNITUDE → NEGLIGIBLE**
- Per-period ρ(1) ≈ -0.238, σ_bar = 157 bps
- Gross per reversal trade: 37.4 bps
- Net after 50 bps RT cost: **-12.6 bps** (negative)
- ΔSharpe = -0.045
- The mean-reversion effect is real but too small to overcome transaction costs.

**S4: COMPLEMENTARITY → COMPLEMENTARY**
- Operates 100% during FLAT (by construction)
- ρ with VTREND returns = 0.00 (non-overlapping time windows)

**S5: SAMPLE ADEQUACY → ADEQUATE**
- N = 182, MDE = 0.208, Observed |d| = 0.866
- Ratio = 4.17× (well above 1.5× threshold)

---

### P2: Return Autocorrelation / 24h Periodicity (Obs14)

**S1: SIGNAL STRENGTH → STRONG**
- Lag-6 per-period: d = -0.560, t = -6.38, p = 2.9e-9
- Lag-1 per-period: d = -0.593, t = -8.00, p < 1e-12
- Best |d| = 0.593

**S2: TEMPORAL STABILITY → STABLE**
| Block | N | Mean ACF(6) | t | p | Significant |
|-------|---|------------|---|---|-------------|
| 1 | 37 | -0.087 | -3.56 | 0.001 | YES |
| 2 | 37 | -0.072 | -3.37 | 0.002 | YES |
| 3 | 26 | -0.077 | -3.22 | 0.004 | YES |
| 4 | 30 | -0.072 | -2.58 | 0.015 | YES |

All 4 blocks negative, all 4 significant.

**S3: ECONOMIC MAGNITUDE → NEGLIGIBLE**
- Mean |ACF(6)| = 0.077
- Gross per lag-6 reversal: 12.1 bps
- Net after 50 bps cost: **-37.9 bps** (deeply negative)
- ΔSharpe = -0.128
- The 24h periodicity is far too small to trade at 50 bps RT.

**S4: COMPLEMENTARITY → COMPLEMENTARY**
- FLAT-only: 100%, ρ = 0.00

**S5: SAMPLE ADEQUACY → ADEQUATE**
- N = 130, MDE = 0.246, Observed |d| = 0.560
- Ratio = 2.28×

---

### P3: Post-Exit Asymmetry (Obs23)

**S1: SIGNAL STRENGTH → WEAK**
- Winners post-exit (n=95): mean +0.91%
- Losers post-exit (n=122): mean +0.58%
- Difference: +0.33%, Cohen's d = 0.057
- Mann-Whitney p = 0.386 (NOT significant)

**S2: TEMPORAL STABILITY → MIXED**
| Block | N_w | N_l | Diff | p | Significant |
|-------|-----|-----|------|---|-------------|
| 1 | 23 | 30 | +0.30% | 0.647 | no |
| 2 | 26 | 30 | +2.18% | 0.221 | no |
| 3 | 15 | 36 | -0.59% | 0.476 | no |
| 4 | 31 | 26 | -1.03% | 0.325 | no |

Sign flips in blocks 3-4. Zero blocks significant.

**S3: ECONOMIC MAGNITUDE → MARGINAL**
- ΔSharpe ≈ 0.20 if perfectly exploited
- **CAVEAT**: Requires knowing trade outcome at exit time (look-ahead bias). Without a model predicting win/loss at exit, this is NOT directly tradeable.

**S4: COMPLEMENTARITY → COMPLEMENTARY**
- FLAT-only: 100%, but conditioned on VTREND outcome

**S5: SAMPLE ADEQUACY → UNDERPOWERED**
- N = 95 (winners), MDE = 0.287, Observed |d| = 0.057
- Ratio = 0.20× (well below 1.0×)

---

### P4: Calendar Return Effect (Obs28)

**S1: SIGNAL STRENGTH → WEAK**
- KW H = 57.09, p = 9.95e-5 (significant)
- η² = 0.0008 (tiny), Cohen's f = 0.028
- Hourly mean range: 10.8 bps (max - min)
- The KW test is significant due to the enormous sample size (N=42,883), but the effect size is minuscule.

**S2: TEMPORAL STABILITY → STABLE**
| Block | N | KW H | p | Best Hour | Worst Hour | Significant |
|-------|---|------|---|-----------|------------|-------------|
| 1 | 10,720 | 45.4 | 0.004 | 11h | 1h | YES |
| 2 | 10,720 | 41.4 | 0.011 | 21h | 14h | YES |
| 3 | 10,720 | 37.6 | 0.028 | 20h | 1h | YES |
| 4 | 10,723 | 47.9 | 0.002 | 21h | 23h | YES |

Pattern is present in all blocks, but the best/worst hours SHIFT between blocks. This undermines the operational consistency — the specific hours to target are not stable.

**S3: ECONOMIC MAGNITUDE → NEGLIGIBLE**
- Best-worst hourly range: 10.8 bps
- Cost per RT: 50 bps
- Net: **-39.2 bps** (deeply negative)
- ΔSharpe = -0.078

**S4: COMPLEMENTARITY → COMPLEMENTARY**
- FLAT-only: 100%, ρ = 0.00

**S5: SAMPLE ADEQUACY → UNDERPOWERED**
- MDE = 0.067, Observed equiv. d = 0.056
- Ratio = 0.85× (below 1.0×)
- Despite 42,883 bars, the effect is smaller than the MDE because the effect itself is so tiny.

---

## 3.3 Scoring Matrix

| Phenomenon | Obs | S1 | S2 | S3 | S4 | S5 | Total |
|------------|-----|----|----|----|----|----|-------|
| P1 Mean-Reversion | Obs17 | **STRONG** | **STABLE** | NEGLIGIBLE | **COMPLEMENTARY** | **ADEQUATE** | **4** |
| P2 24h Autocorrelation | Obs14 | **STRONG** | **STABLE** | NEGLIGIBLE | **COMPLEMENTARY** | **ADEQUATE** | **4** |
| P4 Calendar Return | Obs28 | WEAK | **STABLE** | NEGLIGIBLE | **COMPLEMENTARY** | UNDERPOWERED | 2 |
| P3 Post-Exit Asymmetry | Obs23 | WEAK | MIXED | MARGINAL | **COMPLEMENTARY** | UNDERPOWERED | 1 |

**Bold** = top-tier score. Total = count of top-tier scores.

---

## 3.4 Supplementary Stability Analysis

Rolling window plots computed for P1, P2, P4 (Total ≥ 2):

**P1** [Fig12a]: Rolling VR(2) on 500-bar FLAT window stays consistently below 1.0 across the entire sample (2017–2026). No period where VR approaches or exceeds 1. The mean-reversion property is structurally persistent.

**P2** [Fig12b]: Rolling ACF(6) on 500-bar FLAT window is predominantly negative throughout. Brief excursions above zero occur but are rare and short-lived. The 24h periodicity is a stable feature of BTC flat-period microstructure.

**P4** [Fig12c]: Rolling hourly η² is consistently near zero (0.0005–0.002 range) with no trend. The calendar effect is present but tiny and stable — it does not strengthen or disappear over time.

---

## 3.5 Critical Interpretation

### The central finding

P1 (mean-reversion) and P2 (24h autocorrelation) are **statistically real, temporally stable, well-sampled, and complementary to VTREND**. They score 4/5 top-tier. The only criterion they fail is the most important one for trading: **economic magnitude**.

The mean-reversion effect within flat periods generates ~37 bps gross per theoretical trade. Under 50 bps RT cost, every reversal trade loses money. Even under the realistic Binance VIP0+BNB cost (~20-30 bps RT from X22), the gross return barely covers cost:
- At 30 bps: net = 37 - 30 = 7 bps/trade → extremely marginal
- At 20 bps: net = 37 - 20 = 17 bps/trade → still small

The 24h periodicity (P2) is worse: 12 bps gross, deeply underwater at any realistic cost.

### Why this is not surprising

From the prior knowledge base (Phase 0 §C):
- **X22 (Cost Sensitivity)** proved that cost is the biggest lever (Sharpe 1.19→1.67 at 50→15 bps)
- **entry_filter_lab** proved that microstructure information ceiling ≈ 0 at entry
- VTREND itself extracts alpha from **persistent trends**, not mean-reversion

Flat-period mean-reversion is the inverse of VTREND's alpha source. BTC trends when moving (VTREND captures this). When BTC is not trending (FLAT), it mean-reverts — but the mean-reversion effect is too small relative to per-bar volatility (157 bps) to overcome even modest transaction costs.

### P3 and P4: not viable

P3 (post-exit asymmetry) is statistically insignificant (d=0.057, p=0.39), unstable across blocks (sign flips), underpowered, and requires look-ahead information. Not viable.

P4 (calendar effect) is statistically significant only due to sample size — the actual effect (η²=0.0008) is negligible. The best/worst hours shift between blocks, making it operationally useless. And the 10.8 bps range is dwarfed by 50 bps cost.

---

## 3.6 Gate Decision

**Mechanical gate rule**: P1 and P2 both have ≥3 top-tier scores → **PASS_TO_NEXT_PHASE**

**Selected for Phase 4**: P1 (Mean-Reversion) and P2 (24h Autocorrelation)

**Important caveat**: Both selected phenomena have NEGLIGIBLE economic magnitude at 50 bps RT cost. Phase 4 formalization should assess whether:
1. Lower-cost execution (15-30 bps) changes the conclusion
2. The mean-reversion signal can be used as a FILTER (not a standalone strategy) to improve VTREND timing
3. Combining P1+P2 creates a stronger composite signal

If Phase 4 cannot identify a viable exploitation mechanism that overcomes the cost barrier, the research should stop with conclusion: **BTC spot flat periods contain statistically real mean-reversion that is economically negligible under realistic transaction costs.**

---

## 3.7 Verification Artifacts

### Code
- `code/phase3_scoring.py` — full 5-criterion scoring for 4 phenomena

### Figures
- `figures/Fig12_rolling_stability.png` — Rolling VR(2), ACF(6), and η² for P1/P2/P4

### Tables
- `tables/Tbl_scoring_matrix.csv` — 4×7 scoring matrix with totals
- `tables/Tbl_stability_blocks.csv` — 4-block stability for all 4 phenomena

---

## END-OF-PHASE CHECKLIST

### 1. Files created/updated
- `03_phenomenon_survey.md` (this file)
- `code/phase3_scoring.py`
- `figures/Fig12_rolling_stability.png`
- `tables/Tbl_scoring_matrix.csv`
- `tables/Tbl_stability_blocks.csv`

### 2. Key observations
- **P1**: Mean-reversion d=-0.87, p<1e-23, 4/4 blocks significant, NEGLIGIBLE after cost
- **P2**: 24h ACF d=-0.56, p<1e-8, 4/4 blocks significant, NEGLIGIBLE after cost
- **P3**: Post-exit asymmetry d=0.06, p=0.39 — NOT significant, UNDERPOWERED
- **P4**: Calendar η²=0.0008 — statistically significant by sample size only, UNDERPOWERED for the effect

### 3. Blockers / uncertainties
- P1 and P2 are mathematically related (VR captures autocorrelation structure). They are not fully independent phenomena. Phase 4 should treat them as a single mean-reversion complex.
- The economic magnitude estimates assume a naive reversal strategy. A filter-based approach (using mean-reversion state to modify VTREND behavior) might extract value differently — this is Phase 4's question.
- The per-period VR(2)=0.762 is the mean; individual periods range widely (std=0.274). Some periods have strong mean-reversion, others do not.

### 4. Gate status
**PASS_TO_NEXT_PHASE**

Rationale: P1 and P2 both achieve 4/5 top-tier scores, exceeding the ≥3 threshold. However, the NEGLIGIBLE economic magnitude (S3) for both is a severe constraint. Phase 4 should formalize the mean-reversion property and determine if any exploitation mechanism can overcome the cost barrier. If not, the research terminates with a definitive negative result: BTC flat-period microstructure is real but untradeable.
