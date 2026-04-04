# Findings Under Review — Data Pipeline Quality

**Topic ID**: X38-T-19E
**Opened**: 2026-04-02
**Author**: human researcher

2 findings about data pipeline quality — whether the raw data is trustworthy
and whether the discovery pipeline itself can detect real signals. Split from
Topic 019 (DFL-13, DFL-17).

Theme: "Is the data trustworthy? Can the pipeline detect real signals?"

These are Tier 4 decisions, INDEPENDENT of the discovery loop architecture
(Tier 1-3). Can be debated in PARALLEL with all other 019 sub-topics.

**Issue ID prefix**: `X38-DFL-` (Discovery Feedback Loop).

**Convergence notes applicable** (full text at `../000-framework-proposal/findings-under-review.md`):
- C-01: MK-17 != primary evidence; firewall = main pillar
- C-02: Shadow-only principle settled
- C-12: Answer priors banned ALWAYS

**Closed topic invariants** (non-negotiable):
- Topic 018 SSE-D-02: Bounded ideation = results-blind, compile-only, OHLCV-only, provenance-tracked
- Topic 018 SSE-D-11: APE v1 = template parameterization only, no code generation
- Topic 018 SSE-D-05: Recognition stack = pre-freeze topology + named working minimum inventory (Judgment call)
- Topic 002 F-04: Contamination firewall typed schema + whitelist
- Topic 004 MK-17: Same-dataset empirical priors = shadow-only
- Topic 007 F-01: "Inherit methodology, not answers"

---

## DFL-13: Data Trustworthiness & Cross-Source Validation

- **issue_id**: X38-DFL-13
- **classification**: Thieu sot
- **opened_at**: 2026-03-31
- **opened_in_round**: 0
- **current_status**: Open

> **Debate scope note**: DFL-13 addresses a layer BELOW statistical analysis —
> whether the raw numbers themselves are trustworthy. Without this foundation,
> DFL-06's 10 analyses and DFL-10's Stage 2.5 profiling operate on potentially
> corrupted inputs. The architecture question: should the framework include a
> data trustworthiness assessment step, and what is its scope?

**Motivation**:

Stage 2 (Data audit, F-05) checks data INTEGRITY: gaps, duplicates, checksums,
anomaly disposition. DFL-10 Stage 2.5 profiles STATISTICAL properties:
distributions, pairwise dependencies, temporal structure. Both assume the
underlying numbers are ACCURATE — that `volume = 15,000 BTC` means 15,000 BTC
actually traded, and `taker_buy_base_vol = 8,000` means 8,000 BTC were bought
by takers.

This assumption is unverified and potentially wrong for crypto exchange data.

**Three categories of data trustworthiness risk**:

### Category A: Exchange-reported metric reliability

Binance reports `volume`, `taker_buy_base_vol`, `taker_buy_quote_vol`, and
`num_trades` per bar. These are exchange-computed aggregates with opaque
methodology:

| Field | Risk | Impact if compromised |
|-------|------|----------------------|
| `volume` | Wash trading inflates volume on crypto exchanges. Bitwise 2019 SEC filing found ~95% of reported BTC volume on 81 surveyed exchanges was fabricated — though Binance was among the ~10 exchanges Bitwise classified as LEGITIMATE. The concern is not that Binance is known to wash-trade, but that exchange-reported volume is OPAQUE and independently unverified for this dataset | VDO filter uses volume as denominator. If volume includes non-economic activity (wash trades, internal transfers), VDO ratio is distorted -> entry signal affected |
| `taker_buy_base_vol` | Binance's taker/maker classification is proprietary. Self-trade (same entity on both sides) classified how? | DFL-06 Analysis 1 derives 6 features from taker fields. All compromised if classification is wrong |
| `num_trades` | May count internal matching engine operations, not independent economic decisions | `avg_trade_size`, `trade_intensity`, `volume_per_trade` (DFL-06 derived features) all use num_trades |
| `quote_volume` | Should equal sum(price x qty) per trade. Rounding, fee inclusion, or aggregation errors possible | `taker_buy_premium`, `quote_per_base` derived features affected |

**Evidence from btc-spot-dev**: X27 EDA noted volume peaked ~24K BTC/bar in
2022 then dropped to ~3,500-5,900 by 2024-2026. X27 Obs27 attributed this to
market microstructure changes (ETF launch shifting volume to CME/spot ETFs).
This is a plausible explanation, but it is an INTERPRETATION — the raw data
cannot distinguish between (a) genuine volume migration to other venues,
(b) Binance reporting methodology change, or (c) reduced wash-trading after
regulatory pressure. Cross-exchange validation (Category B) would distinguish
these explanations.

### Category B: Cross-exchange validation

If Binance data is trustworthy, similar patterns should appear on independent
exchanges (Coinbase, Bybit, OKX) for the same timestamps. Divergences indicate
exchange-specific artifacts vs genuine market properties.

**Specific tests**:
- Same-timestamp volume correlation: Binance volume vs Coinbase volume at H4.
  High correlation (rho > 0.9) -> volume reflects real market activity.
  Low correlation -> exchange-specific noise or wash trading
- Taker ratio comparison: Does `taker_buy_ratio` on Binance track similarly on
  exchanges that use different matching engines?
- Price-volume relationship: Does the Amihud ratio (DFL-06 Analysis 10) have
  similar magnitude and dynamics across exchanges?
- `num_trades` scaling: If Binance reports 50K trades/H4 bar and Coinbase reports
  5K, the ratio should be roughly proportional to market share. Deviations
  indicate counting methodology differences

**Data requirement**: This is the ONLY DFL finding that requires data NOT in the
current CSV. Cross-exchange comparison requires downloading equivalent OHLCV+
taker data from 2-3 other exchanges for the same period. This is a ONE-TIME
validation exercise, not ongoing pipeline input.

### Category C: ETL pipeline correctness (overlaps Stage 2)

The data pipeline (`/var/www/trading-bots/data-pipeline/`) transforms Binance
API responses into parquet files (`/var/www/trading-bots/data-pipeline/output/`).
Some of these checks overlap with
Stage 2 (integrity audit), but are included here because aggregation-level
errors may not be caught by Stage 2's gap/duplicate/checksum tests:

- Aggregation correctness: 15m -> H1 -> H4 -> D1 aggregation. Is volume SUMMED
  correctly? Is high = MAX(sub-bar highs)? Is open = FIRST sub-bar open?
- Missing bar handling: if a 15m bar is missing, how does H4 aggregation handle
  the gap? (Stage 2 catches missing bars, but not aggregation errors AROUND gaps)
- Historical data consistency: has Binance retroactively adjusted any historical
  bars? (Some exchanges do this for erroneous trades)

**Specific validation** (one-time, may belong in Stage 2 scope):
- Download raw 15m bars for a random 30-day window. Manually aggregate to H1,
  H4, D1. Compare with existing CSV values. Zero tolerance for discrepancies
  in OHLC. Volume aggregation within 0.1% tolerance (rounding)

**Note**: Category C may be better handled as an extension of Stage 2 (integrity
audit) rather than a separate trustworthiness concern. The debate should decide
whether aggregation correctness is an integrity question (Stage 2) or a
trustworthiness question (DFL-13).

**Proposal**: A one-time data trustworthiness assessment covering exchange
metric reliability (Category A), cross-exchange validation (Category B), and
ETL correctness (Category C). The framework should either include this as a
stage or explicitly document the assumption that exchange-reported data is
accurate.

### Interaction with existing findings

| Finding | Interaction |
|---------|------------|
| DFL-06 | Analyses 1, 5, 9, 10 depend on volume/taker fields. If Category A risk is real, these analyses operate on potentially corrupted inputs |
| DFL-10 | Stage 2.5 profiles statistical properties — complements trustworthiness (DFL-13 validates accuracy, DFL-10 profiles distribution) |
| DFL-14 | DGP change detection (Layer 2) runs on volume/taker fields. If those fields are untrustworthy (Category A), detected structural breaks may be data artifacts rather than genuine DGP changes |
| DFL-15 | Data acquisition scope. Category B requires cross-exchange data — DFL-15 scopes whether external data acquisition is in framework |
| DFL-17 | Protocol 3 (VDO reconstruction) uses taker_buy_base_vol. If taker classification is unreliable (Category A), Protocol 3 calibration is affected |
| DFL-18 | Volume regime definitions (Type 2) use rolling volume. If volume is inflated in some periods, regime boundaries are shifted |
| F-05 (003) | Stage 2 integrity audit. Category C overlaps — debate should assign ownership |

### What this is NOT

| Concern | Answer |
|---------|--------|
| "Replaces Stage 2 integrity audit" | No. Stage 2 = gaps/duplicates/checksums. DFL-13 Categories A+B = are the NUMBERS accurate and representative? Different layer. Category C may overlap — see note above |
| "Requires continuous cross-exchange monitoring" | No. One-time validation exercise. If Binance data passes, proceed. If it fails, document which fields are unreliable |
| "Blocks all analysis until validated" | Judgment call. Cross-exchange validation could run in parallel with DFL-06 analyses. Results calibrate confidence, not block work |

### Architecture decision for debate

| Decision | Alternatives | Implication |
|----------|-------------|-------------|
| Should trustworthiness assessment be a framework stage? | (a) Yes, Stage 1.5 between lock and audit (b) Part of Stage 2 (c) One-time validation, not in pipeline | (a) adds overhead every campaign. (b) overloads Stage 2. (c) cheapest but no repeat validation |
| Cross-exchange data: acquire or not? | (a) Acquire for validation (b) Document as assumption, skip | (a) costs time. (b) accepts risk |

**Open questions**:
- If Binance volume IS significantly inflated by wash trading, which DFL-06
  analyses are salvageable? (OHLC prices should be unaffected — only volume-
  derived features are at risk)
- Should the framework require cross-exchange validation for EVERY new asset,
  or only for the first campaign (BTC)?
- Is there a way to detect wash trading from the data itself (e.g., unusual
  round-number volume concentrations, perfectly symmetric buy/sell) WITHOUT
  cross-exchange data?
- How does this interact with DFL-10 Stage 2.5? Should `data_profile.json`
  include a trustworthiness section, or is that a separate artifact?

---

## DFL-17: Pipeline Validation via Synthetic Known-Signal Injection

- **issue_id**: X38-DFL-17
- **classification**: Thieu sot
- **opened_at**: 2026-03-31
- **opened_in_round**: 0
- **current_status**: Open

> **Debate scope note**: DFL-07 section E uses synthetic data to test NULL hypotheses
> (is this pattern real?). DFL-17 uses synthetic data to test the PIPELINE
> ITSELF (can it detect a real pattern?). These are complementary: section E validates
> discoveries, DFL-17 validates the discovery machinery.

**Motivation**:

DFL-06 proposes 10 systematic analyses. DFL-07 proposes a 3-phase workflow
(SCAN -> DEEP DIVE -> VALIDATION). DFL-08 proposes a 5-stage graduation path.
DFL-11 proposes a two-tier screening system.

But how do we know the pipeline WORKS? If VDO-like alpha exists in data, will
the pipeline find it? What if a pattern is real but the pipeline's screening
thresholds, null models, or graduation gates filter it out?

**The problem**: The pipeline has never been validated against a KNOWN positive.
DFL-07 section E validates against known NEGATIVES (null models — data with no signal).
But there is no corresponding test against known POSITIVES (data with a planted
signal of known strength).

This is the standard engineering practice of CALIBRATION: before deploying a
measurement instrument, test it against a known reference to verify it measures
correctly.

**Proposal**: A synthetic data validation protocol for the discovery pipeline.

### Protocol 1: Known-signal injection (sensitivity)

**Goal**: Determine the MINIMUM DETECTABLE SIGNAL — the weakest genuine pattern
the pipeline can reliably find.

**Method**:

```
1. Generate base synthetic data:
   - Use DFL-07 section E2 GARCH model fitted to real BTC/USDT data
   - Preserves: volatility clustering, fat tails, serial dependence in |returns|
   - Destroys: any genuine predictive features (by construction)

2. Inject a known signal of controlled strength:
   - Create a synthetic feature X that predicts forward returns
   - Predictive strength parameter: IC = {0.01, 0.02, 0.05, 0.10, 0.15, 0.20}
   - Signal type: linear (X -> return) or threshold (X > threshold -> positive return)

3. Run the pipeline:
   - DFL-06 Analysis (relevant subset) -> detect X?
   - DFL-07 Phase 1 SCAN -> X passes screening?
   - DFL-08 Stage 1 -> X becomes candidate?
   - DFL-08 Stage 2 -> X passes deep dive?
   - DFL-07 Phase 3 VALIDATION -> X passes WFO?

4. Measure detection rate:
   - At each IC level, run 100 synthetic datasets
   - Detection rate = fraction where pipeline detects X at each stage
   - Minimum detectable IC = lowest IC with >80% detection rate
```

**Interpretation**:
- If minimum detectable IC = 0.02 -> pipeline can find weak signals (good)
- If minimum detectable IC = 0.15 -> pipeline only finds strong signals (bad —
  VDO's IC is only ~0.10-0.15, and weaker-but-real signals would be missed)

### Protocol 2: No-signal false positive rate (specificity)

**Goal**: Determine how many FALSE POSITIVES the pipeline produces when NO
genuine signal exists.

**Method**:

```
1. Generate 100 synthetic datasets with ZERO signal
   (same GARCH base, no injected features)

2. Create 13 synthetic fields mimicking the CSV structure
   (correlated with returns ONLY through known GARCH properties)

3. Run the full pipeline on each dataset

4. Count false positives:
   - Features that pass DFL-08 Stage 1 (candidate)
   - Features that pass DFL-08 Stage 2 (deep dive)
   - Features that pass DFL-08 Stage 5 (validation)

5. False positive rate at each stage:
   - FPR_stage1 = mean candidates per no-signal dataset
   - FPR_stage5 = mean validated features per no-signal dataset
```

**Interpretation**:
- FPR_stage5 = 0.02 -> 2% of no-signal datasets produce a false validated
  feature -> acceptable
- FPR_stage5 = 0.20 -> 20% -> pipeline is too permissive, gates need tightening

**Relationship to DFL-07 section E**: Protocol 2 and DFL-07 section E4 both run the pipeline
on null-signal data. The difference: section E4 tests per-analysis null rejection
(1000 datasets, one analysis at a time), Protocol 2 tests END-TO-END pipeline
false positive rate (100 datasets, all stages). Section E4 answers "does Analysis N
produce false discoveries?" Protocol 2 answers "does the FULL pipeline
(screening -> deep dive -> validation) produce false validated features?" If both
are implemented, section E4 results are per-stage inputs; Protocol 2 is the aggregate
system-level test. The smaller N (100 vs 1000) is a compute compromise — the
95% CI on FPR at N=100 spans +/-7.8 percentage points, which may be insufficient
for precise calibration.

### Protocol 3: VDO reconstruction test (ecological validity)

**Goal**: Test whether the pipeline's DFL-06 ANALYSIS PATH (not grammar scan)
would have found VDO — using VDO as a KNOWN POSITIVE calibration target.

**Critical scope constraint**: VDO uses `taker_buy_base_vol`, which is NOT an
OHLCV field. The grammar (SSE-D-02) is OHLCV-only. Therefore VDO CANNOT be
found by grammar enumeration — by construction, not by pipeline failure.
Protocol 3 tests ONLY the DFL-06 analysis path (which has access to all 13
fields per DFL-09).

**Method**:

```
1. Use real BTC/USDT data
2. Compute actual VDO signal (taker_buy_ratio)
3. Verify VDO's known properties: DOF-corrected p=0.031 (Sharpe), p=0.004 (MDD)
   (Note: VDO's trade-level IC has not been formally measured — the p-values
   above are from strategy-level 16-timescale tests, not direct IC estimation.
   IC ~ 0.10-0.15 is an ASSUMPTION that should be verified as part of Protocol 3)
4. Run the DFL-06 analysis path AS IF VDO were unknown:
   - DFL-06 Analysis 1 -> would MI/IC screening rank taker_buy_ratio highly?
   - DFL-07 Phase 1 SCAN -> would it pass top-N screening at N=200?
   - DFL-08 Stage 2 -> would it pass deep dive + null model test?
   - DFL-11 budget -> would it survive Holm correction at current K?

5. Result:
   - Pipeline finds VDO -> PASS (pipeline works for known positives)
   - Pipeline misses VDO -> FAIL (pipeline is filtering out real signals)
```

**This is the single most important test**: if the DFL-06 analysis path
CANNOT surface VDO as a candidate — the project's only validated alpha
source — then the analysis methodology (DFL-07) needs recalibration before
running the full DFL-06 suite. Note: a FAIL here does NOT mean "fundamental
redesign" — it means the screening thresholds or methodology need tuning,
not that the architecture is wrong. Some discoveries may inherently require
human intuition and cannot be fully systematized.

### Integration with existing findings

| Finding | Interaction |
|---------|------------|
| DFL-06 | Pipeline to be validated. Protocol 1-2 test DFL-06's ability to detect signals |
| DFL-07 section E | Complementary: section E tests discoveries against nulls, DFL-17 tests pipeline against knowns |
| DFL-08 | Graduation path stages are tested end-to-end |
| DFL-11 | Budget constraints: does the two-tier screening survive Protocol 2 (false positives)? |
| DFL-12 | Depth-2 grammar: can pipeline detect depth-2 signals (e.g., ratio features)? |
| DFL-13 | Protocol 3 uses taker_buy_base_vol — if taker classification is unreliable (DFL-13 Category A), calibration is affected |

**Open questions**:
- Should Protocol 1-3 run BEFORE or AFTER DFL-06 analyses? Before = validates
  pipeline first. After = DFL-06 results calibrate what "detectable" means
- Compute cost: 100 synthetic datasets x full pipeline = significant compute.
  Can be reduced with faster proxy pipeline (skip visualization, use summary
  statistics only)
- Protocol 3 scope RESOLVED in body: all 13 fields via DFL-06 analysis path
  (VDO uses taker_buy_base_vol which is non-OHLCV, so grammar path is
  structurally excluded — not a meaningful test target)
- If Protocol 3 fails, what is the fix? Loosen screening thresholds? Change
  methodology? Accept that some discoveries require human intuition and
  cannot be systematized?

---

## Cross-topic tensions relevant to 019E

| Topic | Finding | Tension | Resolution path |
|-------|---------|---------|-----------------|
| 009 | F-10 | Data integrity audit scope — DFL-13 proposes trustworthiness layer BELOW integrity | DFL-13 validates data accuracy, F-10 validates data completeness. Complementary, not competing |
| 003 | F-05 | Pipeline stages — DFL-13 trustworthiness + DFL-10 Stage 2.5 | 003 owns pipeline stage design. DFL-13 proposes; 003 decides staging |
| 019F | DFL-14, DFL-18 | DFL-13 Category A (volume trustworthiness) affects DFL-14 Layer 2 DGP detection and DFL-18 volume regime definitions | If volume is unreliable, both regime-detection methods are compromised. DFL-13 validation should precede or run in parallel |
| 019G | DFL-15 | DFL-13 Category B (cross-exchange validation) requires external data — DFL-15 scopes whether external data enters the framework | 019G scopes the general acquisition policy; 019E scopes the specific validation need. D-18 outcome gates Category B feasibility |

---

## Decision summary — what debate must resolve

Debate for Topic 019E must produce decisions on these 4 questions. All are
Tier 4 — independent of discovery loop architecture (Tier 1-3). Can resolve
in any order.

**Tier 4 — Data pipeline quality (independent)**:

| ID | Decision | Finding | Alternatives |
|----|----------|---------|-------------|
| D-15 | Should data trustworthiness be a framework stage? | DFL-13 | Stage 1.5 (before audit) / Part of Stage 2 / One-time validation |
| D-16 | Cross-exchange data: acquire for validation or document as assumption? | DFL-13 | Acquire (one-time) / Skip (accept risk) |
| D-20 | Pipeline validation via synthetic data: before or after DFL-06? | DFL-17 | Before (validate pipeline first) / After (calibrate from real results) / In parallel |
| D-22 | DFL-13 Category C owner: trustworthiness layer (019E) or Stage 2 integrity audit (003)? | DFL-13 | Stay in 019E (trustworthiness) / Route to 003 (Stage 2 extension) / Split (ETL correctness → 003, aggregation validation → 019E) |

---

## Summary table

| Issue ID | Finding | Classification | Status |
|----------|---------|---------------|--------|
| X38-DFL-13 | Data trustworthiness & cross-source validation | Thieu sot | Open |
| X38-DFL-17 | Pipeline validation via synthetic known-signal injection | Thieu sot | Open |
