# Latency Tier Deployment Guide

**Last updated**: 2026-03-14
**Status**: Research specification — algorithm discovery phase
**Research basis**: Fragility audit (2026-03-06), X6-vs-X0 investigation Q1-Q16 (2026-03-08)
**Superseding note**: Step 4/5 verdicts superseded by 2026-03-09 framework reform.
Gate analysis (X6 Q13-Q15) replaces delta-based sign-off with absolute comparative framework.

---

## 1. Latency Tier Definitions

| Tier | Label | Entry Delay | Exit Delay | Probability | Description |
|------|-------|-------------|------------|-------------|-------------|
| **LT1** | Normal | ≤ D1 (4h) | ≤ D1 (4h) | 95% | Fully automated, watchdog-monitored |
| **LT2** | Degraded | D2-D4 (8-16h) | ≤ D2 (8h) | 4% | Infrastructure degraded, extended restart |
| **LT3** | Manual | D4+ (16h+) | D4+ (16h+) | 1% | Manual execution or system down |

**Critical threshold**: The D1→D2 jump is the key non-linearity. At D1: E5_ema21D1 delta -0.186 (PASS).
At D2: E5_ema21D1 delta -0.396 (FAIL). Infrastructure must guarantee ≤ 4h restart.

---

## 2. Strategy Selection by Latency Tier

### Decision Table (post-reform, 2026-03-09)

| Tier | Strategy | Sharpe | Why |
|------|----------|--------|-----|
| **LT1** | **E5_ema21D1** (PRIMARY) | 1.432 | Highest Sharpe, all 7 gates PASS, PSR=0.9993. Requires ≤4h SLA. |
| **LT2** | **E0_ema21D1** (FALLBACK) | 1.325 | Lower delay fragility. E0_ema21D1 helps only at ≥ D2+D2 (Q15). |
| **LT3** | **SM** or flatten+halt | ~0.816 | Only viable candidate: D4 loss = -4% vs -40% for binary. |

### Key Constraints

- **All binary strategies** (E0, E5, E0_ema21D1, E5_ema21D1) lose >29% Sharpe at D4 (16h).
  Binary candidates are NOT viable for manual or semi-manual execution.
- **E5_ema21D1 excluded from LT2+**: Performance crossover with E5 at D3; loses 40.7% at D4.
- **SM** is operationally robust at all tiers (D4: -4.0%) but CAGR = 16.0% (3.3x lower than E5_ema21D1).

---

## 3. Fallback Logic

### Automatic Fallback Trigger

| Event | Condition | Action |
|-------|-----------|--------|
| Sustained degradation | 2 consecutive missed H4 bars (8h) | Switch E5_ema21D1 → E0_ema21D1 |
| Recovery | 1 successful bar processed | Switch back to E5_ema21D1 |
| Deep degradation | 4+ consecutive missed bars (16h+) | Flatten all positions, halt trading |

### Why 2 Bars (Not 1)?

At D2+D1 (8h entry + 4h exit): E5_ema21D1 Sharpe 0.874 > E0_ema21D1 Sharpe 0.857. Fallback is **harmful** here.
At D2+D2 (8h entry + 8h exit): E5_ema21D1 Sharpe 0.883 < E0_ema21D1 Sharpe 0.889. Fallback begins to help.

Trigger at 2 missed bars ensures fallback only activates when it genuinely improves performance.

---

## 4. Infrastructure SLA Requirements

| Requirement | Value | Justification |
|-------------|-------|---------------|
| Max downtime | **4.0 hours** (1 H4 bar) | At D1: delta -0.186 passes GO (-0.20). At D2: delta -0.396 FAILS. |
| Target recovery | 0.5 hours (30 min) | Comfortable margin within SLA |
| Health check interval | 60 seconds | Detect failure promptly |
| Restart method | systemd watchdog | Auto-restart on crash/hang |
| Alert escalation | warn 5m → critical 30m → page 2h | Must resolve before 4h SLA |

---

## 5. Stochastic Delay Performance (Monte Carlo, 1000 draws)

| Candidate | LT1 p50 Sharpe | LT1 p5 | LT2 p50 | LT2 p5 | LT3 p50 | LT3 p5 |
|-----------|----------------|---------|---------|---------|---------|---------|
| E0 | 1.107 | 1.066 | 0.977 | 0.898 | 0.793 | 0.678 |
| E5 | 1.202 | 1.154 | 1.043 | 0.959 | 0.740 | 0.630 |
| SM | 0.820 | 0.798 | 0.797 | 0.751 | 0.713 | 0.652 |
| E0_ema21D1 | 1.142 | 1.100 | 1.020 | 0.941 | 0.793 | 0.683 |
| E5_ema21D1 | 1.235 | 1.185 | 1.091 | 1.001 | 0.740 | 0.621 |

- P(CAGR≤0) = 0.0% for ALL candidates at ALL tiers.
- SM LT1→LT3 spread: -13%. E5_ema21D1 LT1→LT3 spread: **-40%** (5× more fragile).
- E5_ema21D1 dominates at LT1 (Sharpe 1.235 vs next-best E0_ema21D1 1.142).
- SM is most stable across tiers but lowest absolute Sharpe.

---

## 6. Crossover Analysis (X6 Q15)

E5_ema21D1 vs E0_ema21D1 absolute Sharpe comparison:

### E5_ema21D1 Dominates (9/12 scenarios — NO fallback needed)

| Scenario | E5_ema21D1 Sharpe | E0_ema21D1 Sharpe | Diff |
|----------|-----------|-----------|------|
| Baseline (D0) | 1.270 | 1.175 | +0.095 |
| Entry D1 only | 1.189 | 1.128 | +0.062 |
| Exit D1 only | 1.145 | 0.988 | +0.156 |
| Exit D2 only | 1.141 | 1.069 | +0.072 |
| Entry D1 + Exit D1 | 1.084 | 0.976 | +0.108 |
| **Entry D2 + Exit D1** | **0.874** | **0.857** | **+0.017** |
| LT1 stochastic mean | 1.235 | 1.141 | +0.094 |
| LT2 stochastic mean | 1.089 | 1.019 | +0.071 |

### E0_ema21D1 Dominates (3/12 scenarios — fallback helps)

| Scenario | E5_ema21D1 Sharpe | E0_ema21D1 Sharpe | Diff |
|----------|-----------|-----------|------|
| Entry D2 only | 0.961 | 0.973 | -0.012 |
| **Entry D2 + Exit D2** | **0.883** | **0.889** | **-0.006** |
| Entry D4 + Exit D2 | 0.695 | 0.763 | -0.068 |

**Crossover point**: E0_ema21D1 fallback only helps when **BOTH** entry AND exit delay ≥ D2 (8h+).

---

## 7. Combined Disruption Sensitivity

Delta Sharpe from baseline under combined entry+exit delays:

| Scenario | E0 | E5 | SM | E0_ema21D1 | E5_ema21D1 |
|----------|-----|-----|------|--------|--------|
| baseline | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| entry_D2 | -0.200 | -0.297 | +0.012 | -0.202 | -0.310 |
| exit_D2 | -0.091 | -0.125 | -0.062 | -0.106 | -0.129 |
| entry_D2+exit_D1 | -0.322 | -0.402 | -0.000 | -0.318 | **-0.396** |
| entry_D2+exit_D2 | -0.287 | -0.394 | -0.051 | -0.286 | -0.387 |
| entry_D4+exit_D2 | -0.365 | -0.523 | -0.097 | -0.412 | -0.575 |

**Key finding**: Performance-fragility tradeoff is perfectly inversely correlated with baseline Sharpe.
Highest-Sharpe strategy (E5_ema21D1) is most fragile. SM is barely affected by any disruption.

---

## 8. Sign-Off Framework (Absolute Comparative, X6 Q15)

Replaces Step 5's delta-based gate (which had structural flaw: penalizes higher baselines).

| Gate | Test | E5_ema21D1 | Result |
|------|------|-----------|--------|
| G1 Absolute dominance | S(E5_ema21D1, worst_LT1) > S(E0_ema21D1, worst_LT1) | 0.874 > 0.857 | **PASS** |
| G2 State dominance | E5_ema21D1 wins majority of scenarios | 9/12 (75%) | **PASS** |
| G3 Fractional loss | worst-case loss < 35% of baseline | 31.2% < 35% | **PASS** |
| G4 Absolute floor | worst-case Sharpe > 0.50 | 0.874 > 0.50 | **PASS** |
| G5 Infrastructure gate | D1 combined delta > -0.20 | -0.186 > -0.20 | **PASS** |

**Verdict**: E5_ema21D1 = **GO — PRIMARY DEPLOYMENT** (under LT1 with 4h SLA).

---

## 9. Decision Flowchart

```
START
  │
  ├─ Can guarantee ≤4h automated restart? (LT1)
  │   ├─ YES → E5_ema21D1 (PRIMARY)
  │   │         Monitor: 2 consecutive missed bars → switch to E0_ema21D1
  │   │         Recovery: 1 successful bar → switch back to E5_ema21D1
  │   │
  │   └─ NO → Expected downtime 4-16h? (LT2)
  │       ├─ YES → E0_ema21D1 (FALLBACK)
  │       │         Lower delay fragility, still binary all-in/all-out
  │       │
  │       └─ NO → Downtime >16h or manual? (LT3)
  │           ├─ Deploy SM (vol-target, low exposure, 16% CAGR)
  │           └─ OR flatten all positions and halt
```

---

## 10. Source Documents

| Document | Location | Content |
|----------|----------|---------|
| Deployment spec (YAML) | `research/x6/DEPLOYMENT_SPEC_E5_EMA1D21_LT1.yaml` | Canonical tier definitions, fallback logic, sign-off gates |
| Step 4 report | `research/fragility_audit_20260306/reports/step4_report.md` | Mandate × latency matrix (SUPERSEDED verdicts, valid methodology) |
| Step 5 report | `research/fragility_audit_20260306/reports/step5_report.md` | Stochastic Monte Carlo, sign-off gates (SUPERSEDED verdicts) |
| X6 Q14 (infra mitigation) | `research/x6/X6_VS_X0_RESEARCH_Q14_INFRASTRUCTURE_MITIGATION.md` | D1 guarantee rescues E5+ |
| X6 Q15 (hybrid fallback) | `research/x6/X6_VS_X0_RESEARCH_Q15_HYBRID_FALLBACK.md` | Crossover analysis, state dominance |
| Sign-off memo | `research/fragility_audit_20260306/reports/final_live_signoff_memo.md` | Original sign-off (SUPERSEDED) |

---

*This document consolidates latency-tier deployment decisions from multiple research sources
into a single front-facing reference. For algorithm specification, see `E5_EMA21D1_Spec.md`.
For component-level deployment details, see `DEPLOYMENT_CHECKLIST.md`.*
