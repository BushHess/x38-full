# Round 1 — Opening Critique: Campaign Model

**Topic**: 001-campaign-model
**Author**: claude_code
**Date**: 2026-03-23
**Scope**: All findings — X38-D-03, X38-D-15, X38-D-16

**Input documents**:
- `docs/online_vs_offline.md` — online vs offline paradigm distinction (mandatory)
- `docs/design_brief.md` — §4 Campaign → Session model (author's proposal)
- `x38_RULES.md` — authority order, participants, evidence types
- `debate/rules.md` — debate rules incl. steel-man (§7), burden of proof (§5), cross-topic tensions (§21-24)
- `debate/001-campaign-model/README.md` — topic scope, dependencies, debate plan
- `debate/001-campaign-model/findings-under-review.md` — F-03, F-15, F-16
- `debate/000-framework-proposal/findings-under-review.md` — convergence notes C-04, C-06, C-12
- `debate/007-philosophy-mission/final-resolution.md` — upstream dependency (CLOSED 2026-03-23)
- `debate/debate-index.md` — topic status, wave plan, dependency graph

---

## Preamble

I am the architect of the campaign model proposed in `design_brief.md:93-147`. Per
`rules.md` §5, burden of proof lies with the party proposing change. Since the
campaign model IS the current design (authority tier 3, `x38_RULES.md:90`), the
burden falls on anyone arguing it should be replaced — for example, by flat sessions.
Conversely, for F-15 and F-16 which propose ADDITIONS to the design (metric scoping,
transition guardrails), the burden falls on them to demonstrate the additions are
necessary.

The upstream dependency is now satisfied: Topic 007 CLOSED today (4/4 Converged).
Key constraint inherited: `NO_ROBUST_IMPROVEMENT` must be a valid campaign exit
(`final-resolution.md:60-61`). The 3-tier claim model — Mission (charter, no
verdict), Campaign (research verdicts), Certification (Clean OOS) — defines the
semantic space within which this topic operates.

This critique covers three findings spanning the full campaign lifecycle: F-03 (the
model itself), F-15 (metric scoping within the model), and F-16 (transition
guardrails between campaigns). My positions below are informed by the critical
distinction in `online_vs_offline.md`: gen1-4 evidence describes PROBLEMS worth
solving, but their SOLUTIONS are online-specific unless proven paradigm-independent.
I apply this filter rigorously to F-15 and F-16, which both import gen4 patterns.

---

## X38-D-03: Campaign → Session model — ACCEPT with amendments

### Position

The campaign model is the correct abstraction for organizing offline research.
The hierarchy Campaign → Session provides three properties that flat sessions lack:

**Key argument**: Flat sessions have no natural boundary for methodology evolution.
V4→V8 history (`design_brief.md:12-16`) demonstrates that research over the same
dataset requires periodic methodology review — V6's 2,219-config scan missed
candidates that V8's refined protocol found. Each round = one methodology version.
Without a formal campaign boundary, there is no mechanism to ask "should we change
HOW we search?" as distinct from "what did we find?". The campaign model captures
this distinction by construction: sessions within a campaign share protocol; protocol
changes require a new campaign with formal HANDOFF.

**Evidence**:
- `CONVERGENCE_STATUS_V3.md` [extra-archive]: V4/V5/V6/V7 sessions diverge at
  family/architecture level despite identical data. The divergence is NOT random —
  it correlates with protocol differences. This is precisely the pattern campaigns
  are designed to track.
- `design_brief.md:115-118`: Same-data campaigns under MK-17 shadow-only are
  effectively "batches of sessions with methodology audit". This is a feature, not
  over-engineering — the campaign boundary is lightweight when methodology doesn't
  change, but becomes critical when it does.
- `x37_RULES.md` §6 [extra-archive]: Session lifecycle PLANNED→ACTIVE→DONE|ABANDONED
  already exists. Campaigns add the missing layer above.
- Topic 007 Decision 2 (`final-resolution.md:56-62`): Campaign tier bears verdict
  `INTERNAL_ROBUST_CANDIDATE` or `NO_ROBUST_IMPROVEMENT`. This verdict requires
  convergence analysis across sessions — impossible without a grouping construct.

**However**, the design brief leaves four operational questions unanswered:

1. **Stop conditions**: How many `NO_ROBUST_IMPROVEMENT` campaigns before halting
   Phase 1? The design brief says "lặp cho đến khi hội tụ hoặc dừng"
   (`design_brief.md:113`) but defines no concrete stop rule. C-04 confirms this gap.
2. **N sessions per campaign**: Fixed or flexible? The minimum for meaningful
   convergence analysis is 3 (for pairwise agreement checks), but the design brief
   is silent.
3. **Minimum data for Clean OOS**: "6 tháng, hoặc khi thị trường thay đổi lớn"
   (`findings-under-review.md:63`) — this belongs to Topic 010, not here.
4. **Same-data campaign utility**: Under MK-17, C2 on same data ≈ more sessions
   for C1. The design brief acknowledges this (`design_brief.md:115-118`) but
   doesn't formalize WHEN a same-data new campaign is justified vs. simply adding
   sessions to the current campaign.

**Proposed amendments**:
- **Stop rule**: After K consecutive campaigns yield `NO_ROBUST_IMPROVEMENT`,
  Phase 1 halts. Propose K=2, configurable per mission. Consistent with F-01
  constraint: `NO_ROBUST_IMPROVEMENT` is a valid exit, not failure.
- **Minimum sessions**: N ≥ 3 per campaign (for convergence analysis to be
  meaningful). No upper bound — campaigns may add sessions until convergence or
  stall.
- **Same-data campaign trigger**: New same-data campaign justified ONLY when
  (a) methodology bug found, or (b) convergence stall after N sessions suggests
  protocol inadequacy. Otherwise, add sessions to current campaign.
- **Clean OOS minimum**: DEFER to Topic 010 (clean-oos-certification).

### Classification: Judgment call

The campaign model vs. flat sessions is a design choice, not a correctness issue.
Both can work; the question is which provides better methodology evolution tracking
with acceptable complexity. I argue campaigns are superior but acknowledge flat
sessions with metadata tagging could approximate the same properties.

---

## X38-D-15: Two cumulative scopes — ACCEPT problem, REJECT gen4 framing

### Position

The finding correctly identifies a real problem: mixing metrics from different scopes
leads to wrong conclusions. A session-level "winner" (best candidate within one
session) is not the same as a campaign-level "convergent leader" (candidate that
multiple sessions agree on). This distinction is paradigm-independent and Alpha-Lab
must formalize it.

**Key argument**: Gen4's specific two-scope model (version-scoped for eligibility,
candidate-scoped for ranking) is online-specific and does NOT translate directly.
`online_vs_offline.md:89-93` identifies gen4's forward decision law as "judgment
zone" requiring debate. More fundamentally:

- **Version-scoped** (`freeze_cutoff_utc`, never reset, for `FORWARD_CONFIRMED`
  eligibility): This scope tracks how long a candidate has survived in production
  forward eval. Alpha-Lab has no forward eval in Phase 1 — it runs deterministic
  backtests on frozen data. There is nothing to "accumulate" over calendar time.
- **Candidate-scoped** (`cumulative_anchor_utc`, reset on promote): This scope
  tracks champion/challenger comparison in live operation. Alpha-Lab's offline
  analog is session-level comparison — but "reset on promote" makes no sense when
  there's no live champion to dethrone.

**Evidence**:
- `online_vs_offline.md:73-75`: "Redesign guardrails giải quyết vấn đề online:
  AI reactive redesign. Offline không có vấn đề này — campaign model tự isolation."
  The same logic applies to cumulative scope resets.
- `gen4/core/FORWARD_DECISION_POLICY_EN.md` §2.1 [extra-archive]: The two scopes
  exist to reconcile eligibility (time-in-forward) with ranking (since-promote).
  Both concepts presuppose a forward evaluation environment.
- Topic 007 Decision 2 (`final-resolution.md:56-62`): Campaign and Certification
  are the two verdict-bearing tiers. This directly suggests two natural metric scopes
  aligned with these tiers, not with gen4's online concepts.

**However**, the underlying problem IS real and the finding's open questions are
well-posed. Alpha-Lab needs metric scoping — just not gen4's version.

**Proposed amendment**: Two offline-native scopes aligned with Topic 007's tier model:

1. **Session-scoped metrics**: Candidate ranking within a single deterministic
   session. Gate pass/fail, Sharpe, MDD, trade count, WFO results. Reset per
   session by definition (each session is independent). Used for: "which candidate
   is best in this session?"
2. **Campaign-scoped metrics**: Aggregated across sessions within one campaign.
   Convergence statistics (how many sessions agree on leader, margin stability,
   pairwise agreement rate). Used for: "has the campaign converged on a robust
   candidate?"

A third scope (cross-campaign) may be needed for HANDOFF decisions but is
intrinsically tied to Topic 016 (bounded recalibration). I propose DEFERRING the
third scope question there — F-15 should own only the session/campaign distinction.

### Classification: Judgment call

The number of scopes and their alignment (gen4-native vs. offline-native) is a
design choice. The finding's classification is correct. The disagreement is on
framing (gen4 transplant vs. offline-native), not on whether scoping is needed.

---

## X38-D-16: Campaign transition guardrails — ACCEPT (adapted)

### Position

The finding correctly identifies a genuine gap: `design_brief.md:108-113` describes
"N campaigns HANDOFF" but specifies NO guardrails for when, how, or under what
constraints a transition occurs. C-06 confirms: "Transition-law gap thật". This is
a Thiếu sót that must be addressed.

**Key argument**: The finding's own mapping table (`findings-under-review.md:174-180`)
is largely correct, but must be evaluated more rigorously through the
`online_vs_offline.md` §5 checklist. I evaluate each gen4 guardrail:

**1. Cooldown (180 days)** → REJECT.
Online-specific. The 180-day cooldown prevents reactive AI redesign after forward
eval disappointment (`online_vs_offline.md:54`: "campaign model: new campaign =
fresh start, meta-knowledge only flows at principle level"). Offline campaigns
don't suffer reactive redesign — the researcher reviews convergence analysis, not
live PnL. The finding already notes this (`findings-under-review.md:176`).
Replacement: **minimum sessions per campaign** (offline-native equivalent ensuring
adequate convergence evidence before transition).

**2. Single hypothesis rule** → ACCEPT.
Paradigm-independent. The principle "change one thing at a time to attribute cause"
is scientific method, not an online governance artifact. Gen3→gen4 evolution
(`KIT_REVIEW_AND_FIXLOG_EN.md` [extra-archive]: 18 fixes) demonstrates what happens
without this discipline — changes become entangled and attribution is lost.
Adaptation: each HANDOFF changes **at most one methodology rule** (e.g., add a new
pruning heuristic, OR change the convergence threshold, not both).

**3. Change budget** → ACCEPT with adaptation.
Paradigm-independent in principle (bounding change scope prevents accidental
contamination), but gen4's specific numbers (max 1 logic block, 3 tunables, 1
execution semantics, 20 configs) are online-calibrated for AI chat sessions. Offline
campaigns need different granularity: methodology rules (firewall whitelist
categories, pipeline stage configuration, search space definition) rather than
logic blocks/tunables.
Proposed budget: max 1 methodology rule change + max 3 search heuristic updates +
max 1 pipeline stage modification per HANDOFF.

**4. Redesign dossier** → ACCEPT as HANDOFF dossier.
Paradigm-independent. The requirement to document WHY a transition happens is
fundamental to scientific methodology and audit. Without it, campaigns degenerate
into undocumented ad-hoc restarts.
Required fields: (a) convergence summary of outgoing campaign, (b) identified
methodology gap or stall evidence, (c) proposed change with justification,
(d) change budget accounting, (e) do-not-touch list.

**5. Allowed triggers** → ACCEPT adapted.
Gen4's triggers (2 consecutive hard constraint failures, emergency breach, proven
bug, structural deficiency) presuppose forward eval. Offline-native triggers:
- **Convergence stall**: N ≥ min_sessions completed, no convergent leader emerges
  (pairwise agreement below threshold)
- **Methodology gap identified**: Formal evidence that a protocol limitation
  prevented discovery (analogous to gen3's 4 structural gaps →
  `governance_failure_dossier.md` [extra-archive])
- **Pipeline bug**: Proven bug affecting reproducibility or correctness
- **Data integrity failure**: Snapshot corruption or schema violation detected

**Evidence**:
- `online_vs_offline.md:54`: Redesign control online = "guardrails (trigger +
  cooldown + dossier)"; offline = "campaign model: new campaign = fresh start".
  The finding correctly maps the gap but the finding's open question ("Guardrails
  strict như gen4 hay lighter?") requires the answer: **different, not lighter** —
  offline guardrails address different failure modes.
- `design_brief.md:78-82`: Meta-Updater only updates methodology, never answer
  priors. HANDOFF guardrails enforce this at the transition boundary.
- C-12 (Topic 000): "Bounded recalibration prima facie bất tương thích với current
  firewall." Transition guardrails must respect firewall constraints — they constrain
  WHAT can change, while the firewall constrains WHAT can flow.

**However**, the interaction between HANDOFF guardrails (this topic) and bounded
recalibration (Topic 016) is a known tension. This topic should define the HANDOFF
mechanism; Topic 016 should define whether/how methodology evolution is allowed to
incorporate empirical priors across campaigns.

**Proposed amendment**: Define a HANDOFF Protocol as formal part of the campaign
model spec:

```
HANDOFF Protocol = {
    trigger:         one of {convergence_stall, methodology_gap, pipeline_bug, data_integrity_fail},
    single_hypothesis: exactly one methodology change,
    change_budget:   {max_methodology_rules: 1, max_search_heuristics: 3, max_pipeline_stages: 1},
    dossier:         {convergence_summary, gap_evidence, proposed_change, budget_accounting, do_not_touch},
    minimum_sessions: N >= 3 (configurable)
}
```

### Classification: Thiếu sót

I agree with the finding's classification. The gap is real: HANDOFF without
guardrails is a genuine deficiency in the current design, not a judgment call
about design alternatives. The debate is about WHICH guardrails, not WHETHER
guardrails are needed.

---

## Summary

### Accepted (near-convergence candidates)

- **X38-D-03**: Campaign model is the correct abstraction. Amendments needed for
  stop conditions (K=2 consecutive NO_ROBUST), minimum sessions (N ≥ 3), and
  same-data campaign trigger rules.
- **X38-D-16**: Transition guardrails are a genuine gap. Proposed HANDOFF Protocol
  adapts gen4 patterns through the `online_vs_offline.md` filter. Cooldown rejected
  (online-specific); single hypothesis, change budget, dossier, and adapted triggers
  accepted.

### Challenged (need debate)

- **X38-D-15**: The PROBLEM is accepted (metric scoping needed), but the gen4
  FRAMING (version-scoped vs. candidate-scoped) is rejected as online-specific.
  Proposed alternative: two offline-native scopes (session + campaign) aligned with
  Topic 007's tier model. Third scope (cross-campaign) deferred to Topic 016.
  The reviewer should challenge whether 2 scopes suffice or 3 are needed within
  this topic's scope.

---

## Cross-topic tensions

| Topic | Finding | Tension | Resolution path |
|-------|---------|---------|-----------------|
| 007 (philosophy) | X38-D-01 | F-01 constrains campaign stop conditions: `NO_ROBUST_IMPROVEMENT` must be valid exit | 007 CLOSED; constraint inherited, 001 owns operationalization |
| 002 (firewall) | X38-D-04 | Firewall determines what can flow at HANDOFF — F-16 guardrails constrain WHEN, firewall constrains WHAT | 002 owns firewall rules; 001 owns HANDOFF trigger/budget |
| 010 (clean-oos) | X38-D-12, X38-D-21 | Clean OOS (Phase 2) depends on campaign model defining Phase 1 exit criteria and winner verdict | 010 owns certification; 001 defines campaign-level verdicts |
| 016 (bounded-recalibration) | C-04, C-12 | Cross-campaign methodology evolution overlaps with bounded recalibration; F-15 third scope question deferred there | 016 owns decision; 001 provides HANDOFF mechanism |
| 013 (convergence) | F-15 scoping | Metric scoping (F-15) determines what convergence analysis measures | 013 owns convergence methodology; 001 provides scope definitions |

---

## Status table

| Issue ID | Finding | Classification | Status | Steel-man for opposing position | Rebuttal of steel-man |
|----------|---------|---------------|--------|------|------|
| X38-D-03 | Campaign → Session model | Judgment call | Open | Flat sessions with metadata tags (campaign_id, protocol_version) give the same grouping without a new abstraction layer — simpler, fewer concepts to maintain | — (awaiting reviewer challenge) |
| X38-D-15 | Two cumulative scopes | Judgment call | Open | Gen4's scopes are battle-tested in production; designing new offline-native scopes risks missing edge cases gen4 already handles | — (awaiting reviewer challenge) |
| X38-D-16 | Campaign transition guardrails | Thiếu sót | Open | — | — |
