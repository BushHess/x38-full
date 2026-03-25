# Governance Failure Dossier

## Dossier Metadata
- lineage_id: btc_spot_mainline_lineage_001
- current constitution version: 3.0
- session requesting review: session_20260319_seed_001
- dossier author: operator + Claude
- date: 2026-03-20

## Claimed Failure

The constitution's combination of hard constraints and lack of design guidance caused all three seed discovery candidates to fail at 50 bps RT, despite strong measured signal in the underlying data channels.

## Why This Is A Constitution-Level Problem

This is not candidate underperformance. The measurements (D1b) found real, statistically significant structure:
- 4h trend → 1h flow permission: +147.7 bps, t=11.17
- 15m vol-normalized continuation: +36.9 bps, t=15.40
- 1h extreme flow: +102.8 bps, t=10.84

The candidates failed because of **three structural gaps in the constitution**:

### Gap 1: Flow percentile calibration is too aggressive by default

Both cross-timeframe candidates (H4Trend_H1Flow, D1Range_H4Flow) produced effectively zero activity across all 14 main configs. Specifically:
- H4Trend_H1Flow: **0 entries** across all 6 configs at both cost levels
- D1Range_H4Flow: 4 of 8 configs produced **1 entry** in 3.5 years; 4 of 8 produced **0 entries**

The fold-training percentile thresholds for order-flow entry (q_flow_entry = 0.80–0.90) were almost never reached in the OOS test windows. Smoke test diagnostic confirmed: trained threshold 0.067 vs max observed test flow 0.033–0.045.

The constitution allows percentile-rank calibration but provides no guidance on minimum-activity constraints. An AI following measurement-first design naturally gravitates toward high-threshold flow filters (D1b showed extreme flow is the cleanest signal), but this creates a systematic trap: the stronger the measured signal, the rarer it fires, and the more likely it produces near-zero trades in short OOS windows.

This is a **constitution design flaw**, not a candidate design error — the constitution's open search space plus hard entry/exposure constraints creates a systematic conflict for rare-signal mechanisms.

### Gap 2: Ablation variants nearly pass but cannot be promoted

The ablation variants (trend-only, without flow layers) produced meaningful results:
- H4Trend_H1Flow_no_flow1h: Sharpe 1.531, CAGR 85.8%, 109 entries, but **MDD 46.3%** (vs cap 45%)
- D1Range_H4Flow_no_flow4h: Sharpe 0.930, CAGR 38.4%, 72 entries, but **MDD 65.0%**

The first ablation missed the MDD hard cap by only 1.3 percentage points. The constitution has no mechanism to:
- Promote ablation discoveries as new candidates within the same session
- Allow a second design iteration informed by ablation results
- Adjust MDD tolerance for high-Sharpe mechanisms

### Gap 3: Sub-hourly mechanism guidance is missing

M15ZRetTrail (15m volatility-normalized continuation) generated 764–1830 entries over 3.5 years (218–523 entries/year) depending on config.

**Critical finding**: M15ZRetTrail fails at ALL cost levels, not just 50 bps.
- At 50 bps: best config CAGR = -51.7%, Sharpe = -1.94
- At 20 bps: best config CAGR = **-6.7%**, Sharpe = -0.039

This means the 15m continuation signal measured in D1b (t=15.40) does not survive walk-forward validation — the problem is deeper than cost. However, the constitution provides no guidance distinguishing sub-hourly mechanisms from swing-horizon mechanisms. A candidate slot was consumed by a mechanism family that was structurally incompatible with the evaluation framework. The constitution should either:
- Explicitly note that sub-hourly mechanisms face additional WFO survival risk due to high turnover, or
- Exclude sub-hourly from the mainline swing scope, or
- Require a preliminary WFO viability check before consuming a candidate slot

## Evidence

| Source | Finding |
|--------|---------|
| d1d_wfo_aggregate.csv | H4Trend_H1Flow: 0 entries across all 6 configs at both cost levels |
| d1d_wfo_aggregate.csv | D1Range_H4Flow: 0–1 entries across all 8 configs at both cost levels |
| d1d_wfo_aggregate.csv | M15ZRetTrail: negative CAGR at both 20 bps and 50 bps, entries/year 218–523 |
| d1d_wfo_aggregate.csv | M15ZRetTrail best config (CFG019) at 20 bps: CAGR -6.7%, Sharpe -0.039 |
| d1e_hard_constraint_filter.csv | 0/20 main configs pass all 4 hard constraints |
| d1e_hard_constraint_filter.csv | 2/4 ablation variants pass 3/4 constraints (fail MDD only) |
| d1d1_smoke_test_results.md | Flow thresholds 0.067 vs max observed test flow 0.033–0.045 |
| meta_knowledge_registry.json | NOTE_MULTI_LAYER_ABLATION_FAILURES, NOTE_FAST_15M_CONTINUATION_TOO_COST_SENSITIVE |

## Candidate Impact

All three mechanism families were harmed:
- **Cross-TF trend×flow**: Killed by over-restrictive flow thresholds (near-zero activity)
- **Fast continuation (15m)**: Fails WFO at all cost levels — signal does not generalize out-of-sample
- **Ablation trend-only**: Nearly viable but blocked by MDD cap (1.3% margin for best variant)

## Proposed Changes

### Change 1: Add minimum-activity soft constraint to D1c design guidance
Require that each candidate, at its loosest config, produces >= 6 entries/year on the warmup or early discovery period before entering the WFO batch. This prevents near-zero-trade configs from consuming evaluation budget.

### Change 2: Raise MDD hard cap from 45% to 50%
BTC spot swing trading has structurally higher drawdowns than traditional assets. The ablation trend-only variant (Sharpe 1.531, CAGR 85.8%) was rejected by 1.3 pp — this is too tight. Calmar ranking already penalizes high MDD continuously; the hard cap should be a safety net, not a binding constraint for strong mechanisms.

### Change 3: Add explicit sub-hourly guidance
The constitution currently admits 15m as a timeframe without noting the structural risks for sub-hourly mechanisms in a swing-horizon evaluation framework. Options:
- (a) Require a preliminary WFO viability check (1 fold) for any candidate using sub-hourly as its primary execution timeframe, before it consumes a candidate slot
- (b) Explicitly state that sub-hourly is outside the swing-horizon mainline scope
- (c) Add a note in D1c guidance that sub-hourly candidates face additional WFO survival risk due to turnover

Note: Even at 20 bps, the 15m candidate was negative — this is not purely a cost issue. The measured D1b signal (t=15.40) did not survive walk-forward, suggesting that sub-hourly continuation may be measurement-period-specific.

### Change 4: Allow one intra-session design revision after ablation
If ablation reveals that a layer degrades performance (ABLATION_FAIL), permit the AI to redesign that candidate as a reduced-layer variant and re-enter it into the remaining WFO configs. Current protocol freezes designs at D1c with no revision path.

## Why Minor Clarification Is Not Enough

These are structural gaps that affect the discovery pipeline's ability to find viable candidates:
- Gap 1 (zero-trade trap) will recur in any session using rare-signal mechanisms
- Gap 2 (MDD cap) will reject BTC swing mechanisms that are fundamentally sound
- Gap 3 (sub-hourly) will waste candidate slots on mechanisms with low WFO survival probability
- Gap 4 (no revision after ablation) wastes discovery budget when a simple fix is available

A session note (Tier 3) cannot fix these — they require constitution-level changes.

## Risks If Changed

- Raising MDD cap to 50% admits mechanisms with larger drawdowns — operator must be comfortable with this risk profile for live deployment
- Allowing intra-session revision after ablation adds one iteration cycle within the discovery snapshot: the AI uses ablation results (part of discovery data) to inform redesign, which means the revised candidate has seen one additional piece of evidence from the same data. This is mild contamination (ablation is diagnostic, not new data), but it does violate strict blind-from-D1c design. Mitigation: limit to exactly one revision, require the revision to be strictly simpler (fewer layers/tunables), and flag the revised candidate with a `post_ablation_revision: true` marker
- Sub-hourly exclusion (option b) permanently reduces search breadth. Options (a) and (c) are less restrictive alternatives

## Risks If Not Changed

- Future sessions on the same or similar snapshots will likely repeat the same failure pattern
- Strong measured signal (t > 10) in cross-TF trend×flow goes unexploited due to the zero-trade trap
- Ablation discoveries (trend-only, Sharpe 1.53) are systematically wasted
- Candidate slots continue to be consumed by sub-hourly mechanisms with low WFO survival probability
