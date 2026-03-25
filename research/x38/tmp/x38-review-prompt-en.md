Role: Codex (Lead Auditor — Multi-Agent Governance Review)

Output:
- Write the final audit report in English.
- Persist the final report to `audits/x38-audit-YYYY-MM-DD.md` using the audit run
  date, and return the same report in chat/output.
- Do NOT modify x38 governance source files. Creating/updating this audit
  artifact in `audits/` is required and allowed.

Objective:
Audit governance integrity of the x38 architecture-design debate project.
Find real problems that block debate, drafting, or publication — not cosmetic
noise. Use multi-agent reasoning for epistemic control: independent discovery,
adversarial falsification, authority audit, and selective reproduction. The
goal is accuracy, not procedural theater.

Scope: /var/www/trading-bots/btc-spot-dev/research/x38

---

BOOTSTRAP (mandatory, read in order)

1. AGENTS.md — read first if not already loaded by the environment.
2. docs/online_vs_offline.md — confusing Online vs Offline is the most
   critical x38 error.
3. x38_RULES.md — especially §4 authority, §5 participants, §6 x38-specific
   debate addenda, §7 references.
4. docs/design_brief.md — authoritative input; overrides PLAN.md on conflict.
5. PLAN.md — master plan, vision, and narrative context.
6. EXECUTION_PLAN.md — current phase, dependencies, and wave structure.
7. debate/rules.md — debate conventions, evidence hierarchy, classifications,
   steel-man requirements, `extra-archive`, cross-topic tensions, context loading.
8. debate/debate-index.md — topic registry, statuses, waves, and finding assignments.

These documents define the project state. Build understanding from them, not
from summaries in this wrapper. Skipping bootstrap invalidates the audit.

---

KEY PRINCIPLES

- Source-of-truth precedence is defined in x38_RULES.md §4. When sources
  conflict, the higher-authority document wins.
- debate-index.md is authoritative for waves and dependencies. For topic
  status and finding truth, topic artifacts (`findings-under-review.md`,
  `final-resolution.md`) are authoritative; verify the index against artifacts
  when drift appears.
- Two status systems exist and must not be conflated:
  - Issue-level (debate/rules.md): Open / Converged / Judgment call
  - Topic-level (debate/debate-index.md): OPEN / CLOSED / SPLIT
- Separate two objects of review:
  - x38 governance findings: statements about repository state, workflow state,
    topic state, or publication state; these use workflow-impact labels.
  - Meta-audit observations: statements about the audit process itself
    (mis-scoping, missing artifact trail, self-adjudication, vocabulary gaps,
    interpretive disputes); do NOT force these into workflow-impact labels.
- Audit is hypothesis-driven, not checklist-driven. After bootstrap, identify
  the 2-4 highest-leverage uncertainty clusters or drift zones and investigate
  those first. Expand scope only when evidence forces expansion.
- Representative examples do not prove exhaustive scope. Before publishing any
  cohort-wide, wave-wide, or class-wide claim, establish the denominator and
  known exceptions with a fast completeness sweep.
- Before assigning any `[BLOCK-*]` label, explicitly test transition clauses,
  trigger conditions, and concurrency wording (`before`, `at`, `when starting`,
  etc.). If the trigger has not fired, default to readiness debt / non-blocking
  unless the authority text makes the present-tense block explicit.
- Internal multi-agent roles are control surfaces, not an output template. The
  final report should read like an expert audit, not an agent transcript.
- Prefer fewer, stronger findings over broad noisy coverage.

---

MULTI-AGENT REASONING (mandatory, adaptive)

Use the smallest set of genuinely independent passes that reduces error on the
same audit problem. Independence matters more than role count.

Minimum required functions:

1. Lead Investigator
   - Reads bootstrap sources.
   - Forms initial hypotheses about likely governance drift.
   - Produces candidate findings from primary evidence.

2. Independent Challenger
   - Tests the strongest surviving claims.
   - Looks for false positives, alternate readings, by-design behavior,
     duplicate findings, omitted context, and stronger competing explanations.
   - At least one challenge pass should also look for important omissions the
     lead investigation may have missed.

3. Authority / Citation Auditor
   - Checks source hierarchy, exact citations, topic-vs-registry authority,
     `extra-archive` labeling, and x38-only scope.
   - Rejects any claim that depends on an unread or lower-authority source.

Escalate when needed:

4. Second Independent Discoverer
   - Required for broad audits, blocker claims, or evidence-conflicted areas.
   - Investigates the SAME problem space without relying on the Lead's final
     finding wording or issue grouping.

5. Blind Reproducer
   - Required for every `[BLOCK-*]` finding, every cross-topic claim, and any
     claim whose truth depends on precise file:line reconstruction.
   - Uses only the cited evidence plus authoritative documents. If the claim
     cannot be reconstructed from those citations, it is not report-ready.

6. Systems Synthesizer
   - Required when a claim touches dependencies, wave readiness, cross-topic
     tensions, or publication readiness.
   - Distinguishes local inconsistency from system-level governance drift.

7. Lead Adjudicator
   - Resolves disagreements and writes the final report.
   - Evidence and authority win; headcount never does.

Recommended workflow:

1. Shared bootstrap.
2. Triage:
   - Identify 2-4 high-leverage drift zones, contradiction clusters, or
     workflow risks from authoritative docs.
   - Do NOT convert the whole repo into a uniform checklist scan.
   - If a serious claim appears to generalize to a cohort, wave, or topic
     class, do a quick denominator/exceptions sweep before finalizing scope.
3. Primary discovery.
4. Independent falsification:
   - Challenge the best current version of each serious claim.
   - Search for disconfirming evidence and important omissions.
   - For any blocker candidate, explicitly search for transition clauses,
     trigger conditions, and by-design exceptions before keeping blocker
     severity.
5. Authority audit.
6. Escalate by impact:
   - Local `[NOTE]` or `[WARNING]` findings: authority-clean + survived
     challenge may be sufficient.
   - `[BLOCK-*]` findings or cross-topic claims: require second independent
     discovery and blind reproduction.
7. Systems synthesis when workflow, dependency, or wave impact is implicated.
8. Adjudication:
   - keep it
   - downgrade it
   - mark it `[UNVERIFIABLE-WITHIN-X38]`
   - mark it `[AMBIGUOUS-AUTHORITY]`
   - retain it as `Resolved Meta-Issue`
   - retain it as `Open Interpretive Disagreement`
   - retain it as `Methodological Limitation`
   - drop it as not proven

Publication standard:

- Every published finding needs authoritative evidence with file:line.
- Every published finding must survive a good-faith disconfirming pass.
- Every `[BLOCK-*]` finding must be reproduced from citations and justified by
  concrete workflow impact.
- Every cohort-wide or blocker claim must state denominator, known exceptions,
  and trigger state.
- Proven meta-audit observations may be retained without workflow-impact labels
  if they are clearly separated from x38 governance findings.
- Non-overlap findings are allowed if they are authority-clean and undefeated.
- Agreement between passes raises confidence but never substitutes for proof.

Independence rules:

- Do not use multi-agent mode as topic sharding or coverage theater.
- Do not let a single summary define the ontology too early.
- Do not force all findings through identical mini-templates.
- If runtime does not support multiple agents, emulate the same stances
  sequentially: discovery -> challenge -> authority audit -> selective
  reproduction -> synthesis -> adjudication.

---

SCOPE LIMITATION

This audit operates WITHIN x38 only. You may verify that x37 file paths exist,
but you may NOT verify x38's interpretation of x37 content. Flag critical
interpretation-dependent claims as `[UNVERIFIABLE-WITHIN-X38]`.

When checking debate rounds that cite files outside `research/x38/` (for
example `x37/`, `v10/`, or `CLAUDE.md`), verify that the citation uses the
`[extra-archive]` label required by debate/rules.md §18.

---

CONSTRAINTS

- No modification of x38 governance source files. The audit artifact in `audits/`
  may and should be created/updated.
- No hallucinated sources — if you cannot point to it, do not report it
- Every published finding must cite evidence (`file:line`)
- Do not confuse Online (gen1-4) with Offline (Alpha-Lab)
- Challenge your own claim before publishing it

---

AVOID

- Do not inventory the whole repo upfront
- Do not shallow-scan all topics equally — follow the evidence
- Do not hardcode or assume dependency maps — read debate-index.md
- Do not check for Python/code artifacts — x38 is blueprint-only
- Do not use severity `[CRITICAL]` — use workflow-specific impact
- Do not verify x37 interpretation correctness — flag scope limits instead
- Do not treat overlap count as proof
- Do not let multiple internal roles emit unreconciled final findings
- Do not pad easy findings with ritual counterarguments just to satisfy format

---

INCREMENTAL MODE

If a prior audit report exists in `audits/` (pattern: `x38-audit-*.md`, choose the
most recent by filename date), compare findings and classify them as
`NEW / RESOLVED / PERSISTING / REGRESSION`. Prioritize regressions and new
blockers. If no prior audit exists, treat all findings as `NEW`.

Persist the current final report to `audits/x38-audit-YYYY-MM-DD.md` using the
audit run date. If a claim changes materially during challenge or adjudication,
retain the correction history in `Resolved Meta-Issues`,
`Open Interpretive Disagreements`, or `Methodological Limitations` rather than
silently overwriting the trail.

---

OUTPUT

Group findings by workflow impact:

  [BLOCK-DEBATE]   — blocks debate rounds
  [BLOCK-DRAFT]    — blocks spec drafting
  [BLOCK-PUBLISH]  — blocks publication
  [WARNING]        — should fix, non-blocking
  [NOTE]           — informational

If applicable, add a separate meta-audit section after governance findings:
  - `Resolved Meta-Issues`
  - `Open Interpretive Disagreements`
  - `Methodological Limitations`
Use these sections for audit-process observations. Do not force meta-audit
observations into `[BLOCK-*]`, `[WARNING]`, or `[NOTE]` unless they are
themselves x38 governance findings.

Write the report in English. Preserve canonical Vietnamese rule terms when
quoting or citing x38_RULES.md or debate/rules.md.

Report style:

- Vary depth by importance; do not give every finding identical space.
- For each finding, include only what is needed to make it provable and
  actionable:
  - what is wrong
  - where (`file:line`)
  - the authoritative basis
  - the workflow impact
  - what should be synced or fixed
  - a short verification note when material (for example: independently
    surfaced, reproduced, authority ambiguity, or scope limitation)
- For any cohort-wide or blocker finding, state the denominator, known
  exceptions, and whether the blocking trigger has already fired.
- If a strong counterargument mattered, explain briefly why it failed. Do not
  add ritual rebuttal text for obvious cases.
- If the same actor both produced the original findings and adjudicated
  challenges, disclose self-adjudication in `Methodological Limitations` or the
  final `Coverage note`.

End with:
1. Sync table — actionable fixes (`file | issue | fix | source`)
2. System health — blocking counts, drift hotspots, wave readiness
3. Coverage note — what you deliberately did NOT verify and why
