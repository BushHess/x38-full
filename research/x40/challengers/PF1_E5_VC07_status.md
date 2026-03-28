# PF1_E5_VC07 — Challenger Status

## Identity

| Field | Value |
|-------|-------|
| Challenger ID | `PF1_E5_VC07` |
| League | `PUBLIC_FLOW` |
| Incumbent | `PF0_E5_EMA21D1` |
| Source | x39 exp42 formal validation (2026-03-28) |
| Mechanism | Vol compression entry gate (`vol_ratio_5_20 < 0.7`) |

## Description

Adds a single entry filter to E5_ema21D1: suppress entry when 5-bar/20-bar
volume ratio exceeds threshold (high volume = compression regime).

Single parameter: threshold. Recommended: **0.7** (better WFO stability).

## Formal validation results (v10 engine, harsh 50 bps)

| Metric | thr=0.7 | thr=0.6 | E5_ema21D1 baseline |
|--------|---------|---------|---------------------|
| Sharpe | 1.571 | 1.594 | 1.455 |
| CAGR | ~67% | ~70% | 61.6% |
| MDD | ~38.5% | ~38.5% | 41.0% |
| Trades | ~160 | ~155 | 188 |
| d_Sharpe | +0.116 | +0.140 | — |

## Gate results

| Gate | thr=0.7 | thr=0.6 |
|------|---------|---------|
| G1: Lookahead | PASS | PASS |
| G2: Full harsh delta | PASS (+17.48) | PASS (+20.76) |
| G3: Holdout harsh delta | PASS (+18.42) | PASS (+20.39) |
| G4: WFO robustness | **FAIL** (p=0.191) | **FAIL** (p=0.273) |
| G5: Trade-level bootstrap | PASS | PASS |
| G6: Selection bias (DSR) | PASS | PASS |

## Verdict

**HOLD / INCONCLUSIVE**

Same blocking issue as E5_ema21D1: WFO Wilcoxon p > 0.10 (insufficient power
at N=8 windows). Does NOT introduce new failure modes.

DSR passes (p=1.0) — selection bias from 52 x39 experiments is cleared.

## Why thr=0.7 over thr=0.6

- Better WFO stability (p=0.191 vs 0.273)
- Smaller worst-window loss (-30.52 vs -47.76)
- Less aggressive parameter choice
- thr=0.6 has higher full-sample Sharpe but wider variance

## Mechanism concern

Vol compression is labeled **mechanism-fragile** in x39 exp50: alternative
compression measures (ATR ratio, range ratio) fail selectivity. The mechanism
is feature-specific, not broadly confirmed.

## Next action

- Wait for WFO power resolution (more OOS data, or methodology reform)
- Do NOT replace PF0 with PF1 automatically
- Do NOT open generic PUBLIC_FLOW residual sprint while PF1 is pending
- Re-evaluate when 6+ months of appended data is available

## Path to baseline candidacy

1. WFO p < 0.10 on extended data
2. Mechanism robustness confirmed by at least one alternative formulation
3. Formal pair review vs PF0 under x40 qualification constitution
