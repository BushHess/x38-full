# X30 — ML-Based Exit Optimization

## Overview

ML models (logistic regression / Elastic Net) applied to trail-stop exit decisions
in VTREND E5+EMA1D21. Multiple variants tested with progressively refined methodology.

## Version History

| Version | Approach | Model | Verdict | Key Finding |
|---------|----------|-------|---------|-------------|
| V1 | Fractional actuator (partial exit at trail stop) | L2 logistic, 7 features | **REJECT** | WFO 2/4, bootstrap P(ΔSh>0) = 0.436. MDD reduction 85% from exposure, 15% from timing. Enet sensitivity check: l1_ratio=0.0 wins (identical to L2). |
| V2 | *[in progress]* | Logistic / Elastic Net | — | New methodology (Report 21 compliant), multi-layer evidence, consensus-seeking |

## Directory Structure

```
x30/
├── README.md              ← this file
├── v1/                    ← V1: Fractional Actuator (REJECT, 2026-03-11)
│   ├── code/              ← x30_signal.py, x30_actuator.py, x30_validate.py, x30_enet_experiment.py
│   ├── tables/            ← signal_summary.json, actuator_summary.json, validation_summary.json, enet_summary.json
│   ├── figures/
│   └── prompte/           ← 4-phase prompt chain (frozen)
│
└── v2/                    ← V2: [in progress]
    ├── code/
    ├── results/
    ├── figures/
    ├── resource/          ← FROZEN (read-only) — canonical specs & confirmation reports
    └── protocol/          ← research protocol with reformed methodology
```

## V1 Summary (REJECT)

### What was tested
- Train L2 logistic regression on 7 features at trail-stop events
- Use churn score to decide partial exit fraction (keep 0-100% of position)
- 3 actuator designs: discrete (fixed fraction), continuous (score → fraction), rank-based

### Why it failed
1. **WFO 2/4** — insufficient temporal generalization
2. **Bootstrap P(ΔSh>0) = 0.308-0.436** — worse than coin flip on resampled paths
3. **Permutation p = 1.0** — no detectable signal in bootstrap framework
4. **MDD mechanism**: 85% from reduced exposure (trivial), only 15% from timing
5. **Elastic Net**: best l1_ratio = 0.0 (pure L2), score_correlation = 1.0 → L1 sparsity adds nothing

### What was learned
- Signal has OOS AUC = 0.803 (discriminative power exists)
- But discriminative power does NOT translate to portfolio improvement
- Fractional actuator's MDD benefit is mostly trivial exposure reduction
- Cost interaction is "increasing" (cost-saving mechanism, not alpha)

## V2 — New Variant

Protocol: `v2/protocol/`

Key differences from V1:
1. **Reformed methodology** (Report 21 compliant): P(d>0) as diagnostic, multi-layer evidence
2. **Three-category framework**: integrity violations / feasibility prerequisites / evidence layers.
   No single **evidence layer** has veto — but integrity and feasibility checks are hard stops.
3. **Leakage prevention upfront** (§0): pipeline-in-fold mandatory, research vs deployment pipelines distinguished
4. **16 validation techniques**: adds PR-AUC, feature ablation, EPV/class-support, JK, PSR, ε-Pareto frontier, restricted permutation, DOF correction
5. **Economic frontier**: ε-Pareto non-dominance vs Base(f-sweep) replaces single-point MDD matching
6. **V1 priors as observations**, not constraints: V2 evaluates regularization path independently
