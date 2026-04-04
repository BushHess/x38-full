# Topic 019E — Data Quality Validation

**Topic ID**: X38-T-19E
**Opened**: 2026-04-02
**Status**: OPEN
**Author**: human researcher
**Origin**: Split from Topic 019 (2026-04-02). Regrouped 2026-04-02 to fix
DFL-14/DFL-18 cross-boundary tension. DFL-14 moved to 019F (Regime Dynamics).
019E now contains 2 DATA PIPELINE QUALITY findings (Tier 4 decisions) that are
INDEPENDENT of the discovery loop architecture.

Theme: "Is the data trustworthy? Can the pipeline detect real signals?"

## Problem statement

These 2 findings address whether the DATA ITSELF is trustworthy and whether the
PIPELINE can be validated — concerns that are orthogonal to how the discovery
loop is designed (019A-D), what data scope to acquire (019G), or how data
changes over time (019F):

1. **DFL-13** (Data Trustworthiness): Are the raw numbers from Binance accurate?
   Exchange-reported volume, taker classification, and num_trades are opaque
   aggregates. Without cross-source validation, every analysis downstream
   operates on potentially corrupted inputs.

2. **DFL-17** (Pipeline Validation via Synthetic Data): Can the pipeline
   detect a real pattern? Synthetic known-signal injection tests pipeline
   sensitivity, specificity, and ecological validity (VDO reconstruction).

Both are Tier 4 decisions — independent of Tier 1-3 (discovery loop
architecture, mechanisms, budget). They can be debated in PARALLEL with all
other 019 sub-topics.

## Scope

2 findings, 4 decisions (Tier 4, independent):

| ID | Finding | Decision(s) |
|----|---------|-------------|
| DFL-13 | Data trustworthiness & cross-source validation | D-15: Framework stage? D-16: Acquire cross-exchange data? D-22: Category C owner (019E or 003)? |
| DFL-17 | Pipeline validation via synthetic known-signal injection | D-20: Before or after DFL-06? |

This topic does NOT own:
- Discovery loop architecture (019A)
- AI analysis and reporting (019B)
- Systematic data exploration (019C)
- Discovery governance and budget (019D)
- Regime dynamics: non-stationarity protocol, regime-conditional profiling (019F)
- Data scope: resolution gaps, cross-asset context (019G)
- Pipeline stage design (003)
- Automated epistemic infrastructure (017)
- Bounded ideation rules (018, CLOSED)
- Contamination firewall content rules (002, CLOSED)

## Dependencies

- **Upstream (CLOSED)**: 018 (bounded ideation, recognition stack), 002 (contamination firewall), 004 (meta-knowledge, MK-17 shadow-only)
- **Scheduling**: NONE from other 019 sub-topics — independent cluster, does not depend on 019A outcomes.
- **Content**: 019G (DFL-15 gates DFL-13 Category B scope — whether cross-exchange external data enters the framework). Informational, not scheduling blocker.

**Wave placement**: Wave 2.5 parallel (can debate simultaneously with 019A and
all other 019 sub-topics). All hard deps satisfied (018, 002, 004 CLOSED).
Tier 4 decisions are independent of Tier 1-3 foundational decisions.

## Cross-topic tensions

| Topic | Finding | Tension | Resolution path |
|-------|---------|---------|-----------------|
| 009 | F-10 | Data integrity audit scope — DFL-13 proposes trustworthiness layer BELOW integrity | DFL-13 validates data accuracy, F-10 validates data completeness. Complementary, not competing |
| 003 | F-05 | Pipeline stages — DFL-13 trustworthiness + DFL-10 Stage 2.5 | 003 owns pipeline stage design. DFL-13 proposes; 003 decides staging |
| 019F | DFL-14, DFL-18 | DFL-13 Category A (volume trustworthiness) affects DFL-14 Layer 2 DGP detection and DFL-18 volume regime definitions | If volume is unreliable, both regime-detection methods are compromised. DFL-13 validation should precede or run in parallel |
| 019G | DFL-15 | DFL-13 Category B (cross-exchange validation) requires external data — DFL-15 scopes whether external data enters the framework | 019G scopes the general acquisition policy; 019E scopes the specific validation need. D-18 outcome gates Category B feasibility |

## Files

| File | Purpose |
|------|---------|
| `findings-under-review.md` | 2 findings (DFL-13, DFL-17) + decision summary (4 Tier 4 decisions) |
| `final-resolution.md` | Created upon closure |
