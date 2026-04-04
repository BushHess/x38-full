# Topic 019G — Data Scope

**Topic ID**: X38-T-19G
**Opened**: 2026-04-02
**Status**: OPEN
**Author**: human researcher
**Origin**: Created 2026-04-02 during regrouping of 019E/019F to fix DFL-14/DFL-18
cross-boundary tension. DFL-15 and DFL-16 moved here from 019F (formerly "Data
Scope & Profiling"). 019G is a NEW topic containing 2 DATA SCOPE findings that
form a natural pair (DFL-16 depends on DFL-15's scope decision).

Theme: "What data do we need? What's in scope?"

## Problem statement

These 2 findings address what data the framework considers IN SCOPE — a
boundary decision that is orthogonal to how the discovery loop is designed
(019A-D), whether the data is trustworthy (019E), or how data changes over
time (019F):

1. **DFL-15** (Resolution Gap Assessment): What data does the framework
   consider in-scope vs out-of-scope? The framework currently operates on a
   13-field CSV at 4 resolutions — a SUBSET of available market data. No
   explicit scope boundary exists. Proposes a documented data acquisition
   policy (framework-level vs per-campaign).

2. **DFL-16** (Cross-Asset Context Signals): Does data FROM other assets
   (BTC dominance, altcoin correlation, ETH/BTC) contain information that
   IMPROVES a BTC-only strategy? Different question from X20 (which tested
   TRADING multiple assets -> CLOSE). DFL-16 is about SIGNAL, not
   DIVERSIFICATION.

DFL-16 depends on DFL-15: cross-asset data requires external data not in the
current CSV. DFL-15's scope decision determines whether such data enters the
framework at all. This dependency makes them a natural pair.

Both are Tier 4 decisions — independent of Tier 1-3 (discovery loop
architecture, mechanisms, budget). They can be debated in PARALLEL with all
other 019 sub-topics.

## Scope

2 findings, 2 decisions (Tier 4, with internal dependency D-19 -> D-18):

| ID | Finding | Decision(s) |
|----|---------|-------------|
| DFL-15 | Resolution gap assessment & data acquisition scope decision | D-18: Framework-level or per-campaign scope? |
| DFL-16 | Cross-asset context signals for single-asset strategy | D-19: In-scope for first campaign or deferred? |

This topic does NOT own:
- Discovery loop architecture (019A)
- AI analysis and reporting (019B)
- Systematic data exploration (019C)
- Discovery governance and budget (019D)
- Data pipeline quality: trustworthiness, synthetic validation (019E)
- Regime dynamics: non-stationarity protocol, regime-conditional profiling (019F)
- Pipeline stage design (003)
- Automated epistemic infrastructure (017)
- Bounded ideation rules (018, CLOSED)
- Contamination firewall content rules (002, CLOSED)

## Dependencies

- **Upstream (CLOSED)**: 018 (bounded ideation — SSE-D-02 OHLCV-only rule relevant
  to DFL-16 cross-asset signals), 002 (contamination firewall)
- **NONE from other 019 sub-topics**. Independent cluster.
- **Internal**: D-19 depends on D-18 (if scope excludes external data, cross-asset
  is automatically out of scope)

**Wave placement**: Wave 2.5 parallel (can debate simultaneously with 019A and
all other 019 sub-topics). All hard deps satisfied (018, 002, 004 CLOSED).
Tier 4 decisions are independent of Tier 1-3 foundational decisions.

## Cross-topic tensions

| Topic | Finding | Tension | Resolution path |
|-------|---------|---------|-----------------|
| 018 | SSE-D-02 (rule 3) | OHLCV-only grammar vs cross-asset context signals (DFL-16) | DFL-16 signals enter via human templates only (DFL-03 channel 1), not grammar. Consistent with DFL-09 |
| 019E | DFL-13 | Cross-exchange validation (DFL-13 Category B) requires external data — DFL-15 scopes whether this is in framework | DFL-13 one-time validation vs framework-level acquisition are different questions. 019G scopes the general policy; 019E scopes the specific validation need |
| 019F | DFL-14 | DFL-14 Layer 2 detection quality depends on available data resolution | Higher-resolution data (019G scope decision) improves DGP detection power, but DFL-14 can operate on current resolution |

## Debate plan

- Estimated: 1-2 rounds (2 decisions with internal dependency)
- Key battles:
  - D-18: Framework-level data boundary vs per-campaign declaration. DFL-15
    recommends hybrid (agnostic architecture, bounded campaign). Tension with
    simplicity (Option A: current data only).
  - D-19: Cross-asset context timing. DFL-16 recommends deferral (after DFL-06
    exhausts intra-BTC). X20 WFO 1/4 is circumstantial evidence of temporal
    instability. Lowest priority of 019 data findings. Depends on D-18 outcome.

## Files

| File | Purpose |
|------|---------|
| `findings-under-review.md` | 2 findings (DFL-15, DFL-16) + decision summary (2 Tier 4 decisions) |
| `final-resolution.md` | Created upon closure |
