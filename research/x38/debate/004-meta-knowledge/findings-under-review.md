# Findings Under Review — Meta-Knowledge Governance

**Topic ID**: X38-T-04
**Opened**: 2026-03-18
**Author**: claude_code (analysis of V6→V7→V8 prompt lineage, conversation 2026-03-18)
**Source**: Conversation between human researcher and Claude Code analyzing
meta-knowledge inheritance patterns across research prompt versions

---

## F-MK-01: Maturity pipeline — the de facto mechanism in V6→V7→V8

- **issue_id**: X38-MK-01
- **classification**: Thiếu sót
- **opened_at**: 2026-03-18
- **opened_in_round**: 0 (pre-debate)
- **current_status**: **Converged** (Stage 1A, R2)

**Observation**:

Analysis of V6, V7, V8 meta-knowledge sections reveals a consistent pattern:

| Version | Meta-knowledge lessons | Protocol body length | What happened to prior lessons |
|---------|----------------------|---------------------|-------------------------------|
| V6 | 8 lessons | 447 lines | (first version with formal meta-knowledge) |
| V7 | 4 lessons (all new) | 586 lines | V6's 8 lessons absorbed into protocol body |
| V8 | 5 lessons (all new) | 643 lines | V7's 4 lessons absorbed into protocol body |

The meta-knowledge section **resets** each version — it only contains new lessons.
Old lessons are absorbed into binding protocol rules. Protocol body **grows**
monotonically. This is a **maturity pipeline**:

```
Observation during session → Lesson (meta-knowledge section) → Binding rule (protocol body)
```

Analogous to: bug report → known issue → permanent fix.

**Examples of absorption**:

- V6 lesson: "Layering is a hypothesis, not a default"
  → V8: Stage 3 binding rule (line 324) + 7 sub-rules
- V7 lesson: "Divergent same-file winners = frontier instability, not to reconcile"
  → V8: Fresh Re-derivation Rule #4 (line 627)
- V7 lesson: "Internal reserve slices don't create new independent proof"
  → V8: meta-knowledge lesson #5 (kept but made more specific)

**Design question**: Should alpha-lab formalize this pipeline explicitly, or
use a different mechanism?

**Evidence**:
- RESEARCH_PROMPT_V6.md line 436-447 [extra-archive]: 8 lessons
- RESEARCH_PROMPT_V7.md line 579-586 [extra-archive]: 4 lessons (V6's 8 gone)
- RESEARCH_PROMPT_V8.md line 635-643 [extra-archive]: 5 lessons (V7's 4 gone)
- V8 protocol body [extra-archive]: V6 + V7 lessons now appear as binding rules throughout

---

## F-MK-02: Five harms of the maturity pipeline

- **issue_id**: X38-MK-02
- **classification**: Sai thiết kế
- **opened_at**: 2026-03-18
- **opened_in_round**: 0
- **current_status**: **Converged** (Stage 1A, R2)

**The five harms**:

### Harm 1: Loss of provenance

When a lesson is absorbed into protocol body, the **why** disappears. The rule
says "do X" but not "we learned this because Y happened in session Z."

Example: V6 lesson "A session is not a clean re-derivation if it imports prior
tables" → V8 Fresh Re-derivation Rule #2. Rule says what to do, not why it
exists (which session violated this? what was the consequence?).

A new AI executing V8 complies mechanically but cannot reason about edge cases
that the rule doesn't cover precisely.

### Harm 2: Protocol bloat (complexity tax)

Each absorbed lesson adds sub-rules, conventions, anti-patterns. V8 protocol
is 643 lines, 1.5x V6. Each line is a constraint. Compliance cost grows
linearly while marginal value of each new constraint decreases.

Possible consequences:
- AI spends more effort on **compliance** than **discovery**
- Rules conflict at edge cases nobody tested
- Protocol becomes overly prescriptive — constrains legitimate exploration

### Harm 3: Implicit data leakage through structural rules (FUNDAMENTAL)

This is the most subtle and **irreducible** harm.

The handoff prompt says: "Transfer only meta-knowledge, NOT data-derived
specifics." But the boundary is blurry.

Example: V8 rule "A transported slower-state clone may not be the final leader
without incremental paired evidence" (line 539). This **sounds** like general
methodology, but it exists because in V4/V5, D1 EMA transported to H4
appeared good but merely restated D1 information. This lesson was **derived
from BTC/USDT data**.

A new AI reading this rule will be **more skeptical** of transported features
— even if on this data, a transported feature genuinely has incremental value
that prior sessions missed. The rule encodes old conclusions under the guise
of "universal methodology."

Similarly: "14 quarterly folds" in V8 looks like protocol design, but reflects
V4/V5 experience that quarterly slicing works well for BTC. On a different
asset, monthly or yearly might be better.

**This is information laundering**: data-specific lessons become
universal-looking rules. A new AI cannot distinguish genuine methodology from
data-derived heuristics.

### Harm 4: No unwind mechanism

The protocol only **adds** rules, never removes them. If a V6 lesson was
context-specific (true for BTC 2017-2024 but wrong for other markets or new
regimes), it's already hardcoded into V7→V8 protocol body. Nobody reviews it
again.

### Harm 5: Diminishing returns with increasing cost

Each version adds ~50-100 lines of protocol. Each line is a constraint. But
the marginal value of each new constraint decreases while compliance cost
increases linearly. At some point, more governance **does not improve**
research output, it only slows it down.

**Evidence**:
- RESEARCH_PROMPT_V8.md [extra-archive]: 643 lines, 1.44x V6's 447 lines
- PROMPT_FOR_V8_HANDOFF.md line 7 [extra-archive]: "Transfer only meta-knowledge" — the rule
  that harm #3 argues cannot be perfectly enforced
- V8 line 539 [extra-archive]: transported-clone rule (data-derived lesson disguised as methodology)
- V8 line 186-201 [extra-archive]: 14 quarterly folds (BTC-specific choice disguised as protocol)

**Design question**: Which harms can alpha-lab eliminate, which can it only
reduce, and which must it accept as fundamental?

---

## F-MK-03: Fundamental constraint — learning vs independence

- **issue_id**: X38-MK-03
- **classification**: Judgment call
- **opened_at**: 2026-03-18
- **opened_in_round**: 0
- **current_status**: **Judgment call** (§14 → human researcher)

**The constraint**:

Harm #3 (implicit data leakage) arises from an irreducible tension:

- **Learning requires memory** — encoding lessons as rules
- **Independence requires forgetting** — not biasing future search

This is a bias-variance tradeoff at meta-level:
- More meta-knowledge → fewer repeated mistakes (good bias) but narrower
  search space (reduced variance)
- Zero meta-knowledge → each session starts from scratch, repeats old mistakes
- Maximum meta-knowledge → new session merely confirms old conclusions

The optimal point is **not** at zero meta-knowledge, and **not** at maximum.
It's somewhere in between.

**Implication for alpha-lab**: The framework cannot promise zero leakage while
also promising to learn from experience. It must choose a point on the
tradeoff curve and **make that choice explicit**.

**Evidence**:
- 5 online sessions (V4-V8, 9 rounds total — CONTAMINATION_LOG_V4 [extra-archive] covers 8 through V7):
  each inherited more meta-knowledge, each still produced different winners
  (CONVERGENCE_STATUS_V3.md [extra-archive]). More meta-knowledge did not force convergence —
  but it may have narrowed the search space in ways that are invisible.

**Design question**: Where on the learning-vs-independence curve should
alpha-lab operate? Should it be configurable per campaign?

---

## F-MK-04: Proposed solution — Derivation Test

- **issue_id**: X38-MK-04
- **classification**: Thiếu sót
- **opened_at**: 2026-03-18
- **opened_in_round**: 0
- **current_status**: **Judgment call** (§14 → human researcher)

**The test**:

For each rule that alpha-lab inherits across campaigns, ask one question:

> "Can a researcher who has **never seen any backtest results** on **any data**
> derive this rule from mathematics, statistics, logic, or experimental design
> first principles alone?"

- **Yes** → rule is an axiom, contains zero data leakage
- **Partially** → rule has empirical content, needs controlled handling
- **No** → rule is data-derived, does not belong in the protocol

**Examples**:

| Rule | Derivation test | Classification |
|------|----------------|----------------|
| "No lookahead" | Yes (information theory) | Axiom |
| "Serialize stochastic seeds" | Yes (reproducibility) | Axiom |
| "Common daily-return domain for mixed-TF comparison" | Yes (statistics) | Axiom |
| "No post-freeze retuning" | Yes (experimental design) | Axiom |
| "Layering is a hypothesis, not a default" | Partially (Occam's razor says yes, but conviction strength from BTC data) | Structural prior |
| "Transported clone needs incremental proof" | Partially (redundancy principle, but emphasis from V4/V5 experience) | Structural prior |
| "14 quarterly folds" | No (specific to BTC discovery window length) | Session-specific |
| "Four prior sessions exist" | No (fact about this lineage) | Session-specific |

**Limitation**: The test is not perfectly objective — "partially" is a judgment
call. But it provides an operational, auditable criterion that is strictly
better than the current binary (meta-knowledge vs data-derived specifics).

**Design question**: Is the derivation test operational enough? Who performs
it — the framework code, the human researcher, or both?

---

## F-MK-05: Proposed solution — 3-Tier Rule Taxonomy

- **issue_id**: X38-MK-05
- **classification**: Thiếu sót
- **opened_at**: 2026-03-18
- **opened_in_round**: 0
- **current_status**: **Converged** (Stage 1A, R2)

**The taxonomy**:

Rules inherited across campaigns are classified into three tiers based on
the derivation test (F-MK-04):

### Tier 1 — Axioms

Derivable from math/logic/statistics. Zero data dependency.

- **No provenance needed** — they're provable, not learned
- **No data leakage possible** — they don't come from data
- **No unwind needed** — they're true permanently
- **Accumulate permanently** — adding a new axiom is always beneficial
- **Not challengeable** by sessions (non-negotiable)

Examples: no lookahead, serialize seeds, common daily-return domain for paired
comparison, no post-freeze retuning, holdout sealed until comparison set frozen.

### Tier 2 — Structural Priors

Empirical lessons. May be broadly applicable but conviction comes from data.

- **Provenance required**: which session/campaign, what observation, why promoted
- **Adversarial challenge required**: written argument for why this rule might
  be wrong or context-specific
- **Expiry/review trigger required**: expires when changing dataset, asset, or
  when N consecutive campaigns don't encounter the failure mode it guards against
- **Leakage grade required**: LOW / MODERATE / HIGH — how much this rule
  implicitly narrows future search
- **Challengeable**: new sessions MAY challenge Tier 2 rules if evidence warrants

Example Tier 2 rule (full format):

```markdown
### T2-003: Layering is a hypothesis, not a default

**Rule**: Do not add layers without paired ablation evidence of incremental value.

**Provenance**: V4 rounds — multi-layer systems consistently failed to beat
single-layer EMA crossover on BTC/USDT H4. Absorbed from V6 meta-knowledge.

**First-principles basis**: Occam's razor / MDL principle — complexity must
earn its place.

**Adversarial challenge**: On assets with richer microstructure (equities, FX
with order flow), multi-layer systems routinely outperform. This rule's
STRENGTH may be BTC-specific (thin feature surface, single dominant regime).

**Expiry**: Review when applying to non-BTC asset or when feature surface
expands (e.g., order book data).

**Leakage grade**: MODERATE — implicitly discourages exploration of complex
architectures that might work on different data.
```

### Tier 3 — Session/Campaign-specific rules

Only valid for current session, campaign, or dataset.

- **Do not accumulate** across campaigns — each campaign has its own Tier 3
- **No adversarial challenge needed** — explicitly contextual
- **Auto-expire** when session/campaign ends

Examples: specific split dates, specific fold count, "four prior sessions
exist", "final same-file audit — no V9".

**How this addresses each harm**:

| Harm | Solution | Residual |
|------|----------|----------|
| #1 Provenance loss | Tier 2 requires provenance block | Eliminated |
| #2 Protocol bloat | Tier 1 compact (no metadata); Tier 2 has expiry; Tier 3 non-accumulating | Greatly reduced |
| #3 Implicit data leakage | Tier 2 has leakage grade + challengeable + adversarial challenge | Reduced, made explicit, NOT eliminated |
| #4 No unwind | Tier 2 has expiry; Tier 3 auto-expires | Eliminated |
| #5 Diminishing returns | Tier 2 expires → steady-state size bounded | Greatly reduced |

**Design question**: Is 3 tiers the right number? Is Tier 2 metadata
(provenance, adversarial challenge, expiry, leakage grade) too heavyweight
for a practical framework?

---

## F-MK-06: Three types of leakage

- **issue_id**: X38-MK-06
- **classification**: Thiếu sót
- **opened_at**: 2026-03-18
- **opened_in_round**: 0
- **current_status**: **Converged** (Stage 1A, R2)

**The current binary is too coarse**. F-06 in topic 000 and the V8 handoff
prompt both use a binary: "meta-knowledge (OK) vs data-derived specifics
(BANNED)." But there are three distinct types of leakage with different risk
profiles:

| Type | Description | Example | Acceptable? |
|------|-------------|---------|-------------|
| **Parameter leakage** | Specific values, features, thresholds, winner identities | "[indicator]([period]) on [timeframe] is the best [filter type]" | Must be zero |
| **Structural leakage** | Failure modes to guard against, categories to check, architecture priors | "Transported clones need incremental proof" | Acceptable if explicit (Tier 2 with metadata) |
| **Attention leakage** | Where to look harder, what to measure first | "Check cross-timeframe alignment carefully" | Unavoidable and generally net-positive |

The V8 prompt mixes all three. The taxonomy from F-MK-05 separates them:
- Parameter leakage = zero (contamination firewall, topic 002)
- Structural leakage = Tier 2 with full metadata
- Attention leakage = accepted, no special handling needed

**Design question**: Is this three-way distinction operational enough to
implement in code? Or does it collapse back to a binary in practice?

**Evidence**:
- PROMPT_FOR_V8_HANDOFF.md line 7 [extra-archive]: binary distinction only
- V8 line 539 [extra-archive]: structural leakage example (transported clone rule)
- V8 line 186-201 [extra-archive]: attention leakage example (14 quarterly folds — influences
  where you look but doesn't determine what you find)

---

## F-MK-07: Relationship to F-06 (4-category whitelist)

- **issue_id**: X38-MK-07
- **classification**: Thiếu sót
- **opened_at**: 2026-03-18
- **opened_in_round**: 0
- **current_status**: **Judgment call** (§14 → human researcher)

**F-06** (in topic 000) proposes 4 whitelist categories for inheritable
lessons: PROVENANCE/AUDIT/SERIALIZATION (grouped), SPLIT_HYGIENE,
STOP_DISCIPLINE, ANTI_PATTERN.

**This topic** proposes a different cut: 3 tiers based on the derivation test.

These are not contradictory — they address different dimensions:
- **F-06 categories** answer: "What TOPIC can a lesson be about?"
- **3-tier taxonomy** answers: "How CERTAIN are we that a lesson is universal
  vs data-derived?"

Both dimensions are needed. A lesson could be about SPLIT_HYGIENE (F-06
category) but still be Tier 2 (partially data-derived — e.g., "quarterly folds
work better than semiannual" was learned from BTC sessions).

**Proposed reconciliation**: F-06 categories become the **content filter**
(what topics are allowed). The 3-tier taxonomy becomes the **confidence/governance
filter** (how the lesson is stored, challenged, and expired).

```
Lesson arrives → F-06 category check: is the topic allowed?
    → YES → Derivation test: Tier 1, 2, or 3?
        → Tier 1: store as axiom (compact, permanent)
        → Tier 2: store with full metadata (provenance, challenge, expiry)
        → Tier 3: store in session/campaign scope only (auto-expire)
    → NO → reject as contamination
```

**Design question**: Does this two-dimensional filtering (category + tier)
add clarity or unnecessary complexity?

---

## F-MK-08: Lesson lifecycle — creation to retirement

- **issue_id**: X38-MK-08
- **classification**: Thiếu sót
- **opened_at**: 2026-03-18
- **opened_in_round**: 0
- **current_status**: **Converged** (Stage 1B, R6)

**The gap**: F-MK-05 defines what tiers look like at rest, but not how a lesson
moves through its life. The full lifecycle needs design:

```
Creation → Classification → Review → Active → [Challenge] → [Modify] → Retire
```

**Sub-questions**:

1. **Creation**: Who proposes a new lesson?
   - Option A: AI auto-extracts from campaign results (risk: AI generates
     data-derived lessons disguised as methodology)
   - Option B: Human researcher writes manually (bottleneck, doesn't scale)
   - Option C: AI proposes, human approves (balance, but approval process needed)

2. **Classification**: Who performs the derivation test (F-MK-04)?
   - AI self-classifying its own lessons → conflict of interest (AI may
     unconsciously classify data-derived lessons as "axioms" to preserve them)
   - Human classifies → doesn't scale, requires deep understanding
   - Dual: AI proposes tier, human confirms. Disagreement → default to
     higher tier (more metadata, more scrutiny)

3. **Review gate**: What must a lesson pass before becoming ACTIVE?
   - Tier 1: mathematical proof or reference to established principle
   - Tier 2: provenance + adversarial challenge + expiry condition all filled
   - Tier 3: no review needed (auto-scoped to session)

4. **Modification**: When a lesson is refined (not retired), what happens?
   - Overwrite in place? → loses history
   - Version chain (v1 → v2 → v3)? → audit trail but complexity
   - Append-only log + pointer to current version? → best of both?

5. **Retirement**: What triggers it?
   - Explicit: human decides
   - Auto: N consecutive campaigns don't encounter the failure mode
   - Contradiction: campaign evidence directly contradicts the lesson
   - Expiry trigger fires (Tier 2 expiry condition met)

**Design question**: How much of this lifecycle should be machine-enforced
vs human-governed? Over-automation risks brittleness; under-automation risks
the same "honor system" problem that V4-V8 had.

---

## F-MK-09: Tier 2 challenge process

- **issue_id**: X38-MK-09
- **classification**: Thiếu sót
- **opened_at**: 2026-03-18
- **opened_in_round**: 0
- **current_status**: **Converged** (Stage 1B, R5)

**The problem**: F-MK-05 says Tier 2 rules are "challengeable" by new sessions.
But without a defined process, this is meaningless.

**Key tensions**:

1. **Challenge too easy** → Tier 2 rules get overridden every campaign, providing
   no learning benefit. Equivalent to zero meta-knowledge.

2. **Challenge too hard** → Tier 2 rules become de facto axioms. Equivalent to
   the current V8 protocol where absorbed rules are never questioned.

3. **Challenge timing**: Before discovery (biases the challenge toward confirming
   the rule)? After discovery (biases toward overriding it based on new results)?
   After freeze (too late to act on)?

**Proposed process (for debate)**:

```
Session encounters situation where Tier 2 rule seems wrong
    → Session documents: what evidence contradicts the rule?
    → Session continues following the rule (conservative default)
    → After session closes: challenge is logged in lesson history
    → If K challenges accumulate across M campaigns:
        → Human review triggered
        → Options: modify rule, downgrade confidence, retire, keep
```

**The conservative default is critical**: a session that thinks a rule is wrong
must still follow it, then challenge post-hoc. This prevents mid-session
rule-shopping (the exact problem the protocol lock is designed to prevent).

**Design question**: What are K and M? Is "follow rule, challenge later" always
the right default, or are there cases where a session should be able to
override a Tier 2 rule in real-time?

---

## F-MK-10: Tier 2 expiry mechanism

- **issue_id**: X38-MK-10
- **classification**: Thiếu sót
- **opened_at**: 2026-03-18
- **opened_in_round**: 0
- **current_status**: **Converged** (Stage 1B, R5)

**The problem**: F-MK-05 says Tier 2 rules have "expiry/review triggers" but
doesn't specify the mechanism.

**Possible trigger types**:

| Trigger | Description | Pro | Con |
|---------|-------------|-----|-----|
| **Time-based** | Expire after N campaigns or T months | Simple, predictable | Arbitrary; good rule may expire too soon |
| **Context-change** | Expire when dataset/asset changes | Relevant (new context may invalidate) | How to detect "meaningful" change? |
| **Contradiction-based** | Expire after K contradictions in M campaigns | Evidence-driven | Requires well-defined "contradiction" |
| **Dormancy-based** | Expire if N campaigns pass without the rule being relevant | Prevents cruft | Hard to define "relevant" |
| **Human-triggered** | Human decides to review/expire | Flexible | Doesn't scale, may never happen |

**Proposed**: Combination of context-change (auto-trigger on new asset/dataset)
+ contradiction-based (auto-trigger after K/M threshold) + human override
(always available).

**Design question**: Should expired lessons be deleted or archived? If archived,
can they be re-activated if context returns to the original?

---

## F-MK-11: Conflict resolution between lessons

- **issue_id**: X38-MK-11
- **classification**: Thiếu sót
- **opened_at**: 2026-03-18
- **opened_in_round**: 0
- **current_status**: **Converged** (Stage 1B, R5)

**The problem**: As lessons accumulate, they may conflict.

**Example conflict**:

- Lesson A (from Campaign C1, BTC): "Layering is a hypothesis, not a default —
  single-feature systems won on BTC H4."
- Lesson B (from Campaign C5, ETH): "Two-layer systems consistently outperformed
  single-feature systems on ETH with richer order flow data."

Both are valid Tier 2 structural priors. They don't technically contradict
(different assets), but a new campaign on a third asset receives conflicting
guidance.

**Sub-questions**:

1. **Scope tags**: Should lessons carry scope metadata (asset, timeframe, regime
   type) so that conflict is detectable?
2. **Precedence rules**: When lessons conflict, which wins?
   - More recent? (recency bias risk)
   - Higher confidence? (circular if confidence comes from same mechanism)
   - More conservative? (systematic bias toward caution)
   - Neither — flag conflict, let session decide? (back to honor system)
3. **Contradiction vs complementarity**: Lessons A and B above are complementary
   (different contexts), not contradictory. But the distinction requires semantic
   understanding that code may not achieve.

**Design question**: Is machine-level conflict detection feasible, or should
the framework only provide tools for human-level conflict review?

---

## F-MK-12: Confidence scoring — is it trustworthy?

- **issue_id**: X38-MK-12
- **classification**: Judgment call
- **opened_at**: 2026-03-18
- **opened_in_round**: 0
- **current_status**: **Converged** (Stage 1B, R5)

**F-06** (topic 000) proposes confidence = len(confirmed) / (len(confirmed) +
len(contradicted)). F-MK-05 does not use numeric confidence, relying instead
on the tier system + metadata.

**Problems with numeric confidence**:

1. **Not all confirmations are equal**: A campaign that confirms a lesson on the
   same BTC dataset provides weaker evidence than one confirming it on ETH.
   Simple counting conflates these.

2. **Confirmation bias**: Campaigns inherit the lesson → sessions follow the
   lesson → lesson appears confirmed. This is circular. The lesson was never
   independently tested; it was obeyed.

3. **Contradictions are ambiguous**: Campaign C3 contradicts lesson A. Is this
   because the lesson is wrong, or because C3 used a different protocol, or
   because C3's data has different statistical properties?

4. **Threshold arbitrariness**: Retire at confidence < 0.3? < 0.5? Any threshold
   is arbitrary without a model of the data-generating process.

**Alternative to numeric confidence** (from the 3-tier taxonomy):

Instead of a number, use qualitative states:
- `ACTIVE` — currently applied, no challenges
- `CHALLENGED` — at least one campaign challenge logged, under review
- `CONTESTED` — multiple campaigns disagree, human review required
- `RETIRED` — no longer applied (with reason and archive)

**Design question**: Should the framework use numeric confidence, qualitative
states, or both? If numeric, how to handle the confirmation bias problem?

---

## F-MK-13: Storage format — JSON vs Markdown vs hybrid

- **issue_id**: X38-MK-13
- **classification**: Judgment call
- **opened_at**: 2026-03-18
- **opened_in_round**: 0
- **current_status**: **Converged** (Stage 1B, R6)

**The tradeoff**:

| Format | Machine-processable | Human-readable | Validation | Extensible |
|--------|-------------------|----------------|------------|------------|
| **JSON** | Excellent | Poor for complex content | JSON Schema | Rigid schema |
| **Markdown** | Poor | Excellent | Regex at best | Very flexible |
| **Hybrid** (YAML frontmatter + Markdown body) | Metadata: good; body: poor | Good | Frontmatter: schema; body: free | Balanced |
| **Structured Markdown** (like this findings file) | Moderate (parseable if strict format) | Good | Convention-based | Moderate |

**Consideration for alpha-lab**:

- The contamination firewall (topic 002) needs to **validate** lesson content
  against whitelist categories → needs machine-processable metadata
- The derivation test (F-MK-04) result should be stored as structured data
- The adversarial challenge (Tier 2) is inherently free-text → needs Markdown
- The leakage grade (F-MK-05) is an enum → needs structured field
- Provenance is a mix of structured (campaign ID, date) and free-text (what
  observation, why promoted)

**Proposed**: YAML frontmatter (structured metadata: tier, category, status,
leakage_grade, expiry_trigger, provenance_campaign) + Markdown body (rule text,
first-principles basis, adversarial challenge, full provenance narrative).

This is analogous to the memory file format already used in this project
(`/root/.claude/projects/*/memory/*.md`).

**Design question**: Does the firewall need to parse the Markdown body for
contamination, or is frontmatter metadata sufficient for enforcement?

> **Đã chốt (2026-03-19)**: Semantic leakage là irreducible (MK-03). Giải pháp
> không phải "triệt tiêu" mà là **thu hẹp attack surface**:
>
> 1. Parameter leakage: machine-blocked qua typed schema
> 2. Pre-freeze rule objects consumed bởi search AI phải **gần như hoàn toàn
>    structured** (rule_kind, scope, force_mode, expiry_mode, challenge_mode —
>    enum/template, không phải prose tự do)
> 3. Free-text rationale (provenance narrative, adversarial essay, long-form
>    justification) sống trong **audit artifacts**, KHÔNG trong active pre-freeze
>    rule payload
> 4. Nếu cần text ngắn trong pre-freeze payload → normalized, tightly templated
> 5. Claim "machine-enforced" chỉ áp dụng ở metadata/schema level
>
> **Lưu ý v1 (MK-17 shadow-only)**: Trên same dataset, empirical rules là
> shadow-only → search AI không đọc chúng pre-freeze → semantic leakage qua
> rule content không xảy ra. Vấn đề này chỉ relevant khi empirical priors
> activate (v2+, new dataset).

---

## F-MK-14: Boundary with Contamination Firewall (topic 002)

- **issue_id**: X38-MK-14
- **classification**: Thiếu sót
- **opened_at**: 2026-03-18
- **opened_in_round**: 0
- **current_status**: **Converged** (Stage 1B, R5)

**The problem**: Topic 004 (this topic) designs how meta-knowledge is governed.
Topic 002 designs the contamination firewall. The boundary between them is
the core problem of the entire meta-knowledge system.

**Where they must agree**:

1. **Definition of contamination**: Topic 002 defines what's banned. Topic 004
   defines what's allowed. These must be complementary (no gaps, no overlaps).

2. **Tier 2 structural leakage**: F-MK-06 says structural leakage is
   "acceptable if explicit." But topic 002's firewall may treat ANY
   data-derived content as contamination. These positions must be reconciled.

3. **Category whitelist**: F-06 (topic 000) defines 4 categories. F-MK-07
   proposes these as content filter. Topic 002 must implement the enforcement.
   Topic 004 must define what passes the filter. Both must use the same
   category definitions.

4. **State machine integration**: Topic 002 proposes a state machine for
   protocol transitions. Topic 004's lesson lifecycle (F-MK-08) also has
   states. These state machines must be compatible or unified.

**Proposed resolution**: Joint interface definition between topics 002 and 004
before either closes:

```
Topic 002 exports: ContaminationCheck(lesson) → CLEAN | CONTAMINATED | AMBIGUOUS
Topic 004 exports: LessonSpec(tier, category, metadata, body)
Contract: Topic 002's check operates on Topic 004's spec
```

**Design question**: Should topics 002 and 004 be debated jointly for the
boundary issues, or separately with a reconciliation step?

---

## F-MK-15: Bootstrap problem — seeding the first campaign

- **issue_id**: X38-MK-15
- **classification**: Judgment call
- **opened_at**: 2026-03-18
- **opened_in_round**: 0
- **current_status**: **Converged** (Stage 1B, R5)

**The problem**: Campaign C1 (the first alpha-lab campaign) starts with an
empty `knowledge/` directory. But 5 online research sessions (V4-V8, with
V4 containing 5 internal rounds; CONTAMINATION_LOG_V4 [extra-archive] covers 8 rounds
through V7, V8 itself is round 9) have already produced valuable methodology
lessons. Should C1 inherit them?

**Option A: Start from zero**

- Pro: Cleanest possible independence. C1 is a true blank slate.
- Con: Repeats all mistakes from V4-V8. Wastes 5 sessions (9 rounds) of learning.
  May produce worse results than V6 simply because it lacks governance
  lessons that V6 already had.

**Option B: Seed with V4-V8 lessons (classified by derivation test)**

- Pro: Leverages 5 sessions (9 rounds) of learning. Tier 1 axioms are provably correct
  regardless. Tier 2 structural priors carry metadata for scrutiny.
- Con: **This IS the implicit data leakage problem** (F-MK-02 harm #3) on
  day one. C1 inherits structural priors that were learned from BTC/USDT
  data — the same data C1 will run on.
- Mitigation: Tier 2 rules carry leakage grades. C1 knows exactly which
  rules may be data-biased.

**Option C: Seed Tier 1 only, derive Tier 2 fresh**

- Pro: Axioms have zero data leakage (by definition). C1 must discover its
  own structural priors.
- Con: Loses valuable structural priors (e.g., "full serialization is
  required" — learned from V5's failure, but has strong first-principles
  basis too). Some Tier 2 rules are "almost axioms."
- Risk: Where exactly is the Tier 1/Tier 2 boundary? If drawn too narrowly,
  valuable rules are lost. If drawn too broadly, data-derived rules sneak
  into Tier 1.

**Option D: Seed all, but mark V4-V8 lessons as LEGACY tier**

- Pro: Preserves all knowledge. LEGACY tier = treated like Tier 2 but with
  explicit flag "derived from online sessions on same data."
- Con: Adds a fourth tier. Complexity.
- Variant: LEGACY is a Tier 2 subtype (same metadata requirements, plus
  additional `source: online_v4_v8` tag).

**Evidence**:
- RESEARCH_PROMPT_V6.md §Meta-knowledge [extra-archive]: 8 lessons from V4 rounds
- RESEARCH_PROMPT_V7.md §Meta-knowledge [extra-archive]: 4 lessons from V6
- RESEARCH_PROMPT_V8.md §Meta-knowledge [extra-archive]: 5 lessons from V7
- CONVERGENCE_STATUS_V3.md [extra-archive]: 5 sessions (V4-V8, 9 rounds total), 5 different
  winners — meta-knowledge transfer did not prevent divergence

**Design question**: Which option best balances learning and independence for
C1? Is Option D (LEGACY subtype) pragmatic or over-engineered?

---

## F-MK-16: Ratchet risk — Tier 2 rules can self-protect by limiting disconfirming evidence

- **issue_id**: X38-MK-16
- **classification**: Sai thiết kế
- **opened_at**: 2026-03-19
- **opened_in_round**: 0 (pre-debate, from external review)
- **current_status**: Mitigations converged (v2+ scope)

**The problem**:

MK-09 says sessions must **follow** Tier 2 rules during discovery, then
challenge post-hoc. The solution proposal (§5) allocates suppressed families
only **probe** budget (20% shared across all suppressed families, with minimal
probe = 1 representative + 1 ablation + 1 paired test).

This creates a **self-reinforcing ratchet**:

```
Wrong Tier 2 rule → family demoted to probe
    → minimal budget for probe → weak evidence generated
    → weak evidence insufficient to overturn rule
    → rule survives → family stays in probe
    → repeat
```

The rule **limits the very evidence that would disconfirm it**. A family that
would beat the winner if given full search budget might never get enough budget
to demonstrate that, because the rule suppressing it controls how much budget
it receives.

**Relationship to other findings**:
- MK-09 (challenge process): challenge requires evidence, but evidence
  generation is budget-constrained by the rule being challenged
- MK-03 (fundamental constraint): this is a concrete manifestation of the
  learning-vs-independence tradeoff — learning (keeping rules) actively
  suppresses independence (exploring alternatives)
- Solution proposal §5: "70% prior-guided / 20% challenge probes / 10% novelty"
  — the 20% shared across ALL suppressed families may be too thin for any
  single family to generate compelling evidence

**Possible mitigations** (for debate):

1. **Higher minimum probe budget**: instead of shared 20%, guarantee each
   suppressed family a minimum absolute budget (e.g., 5% of total per family)
2. **Escalating probes**: if probe results are borderline (not clearly
   confirming or disconfirming), escalate to fuller search in next campaign
3. **Periodic full-budget audit**: every K campaigns, one suppressed family
   gets full frontier budget regardless of rule status
4. **Asymmetric burden**: rule must re-earn its place periodically by showing
   the suppressed family STILL underperforms with adequate budget

**Design question**: How to ensure probe budget is sufficient to generate
evidence strong enough to overturn a wrong rule? Is there a principled minimum?

**Converged mitigations (2026-03-19)**: Pour v2+ (v1 = shadow-only, ratchet
risk ne s'applique pas):
- **Primary**: Asymmetric burden — rule suppressing a family must periodically
  re-earn its place by showing the suppressed family STILL underperforms with
  adequate budget
- **Secondary**: Periodic full-budget audit — every K campaigns, one suppressed
  family gets full frontier budget regardless of rule status
- **Sufficiency definition**: Not "X% of budget" but **coverage obligation** —
  a suppressing rule is only valid if the suppressed family receives enough
  search to test at least one strong representative, one ablation, and one
  paired comparison under a pre-registered threshold. If the family is too
  broad for this → family definition must split, or rule auto-downgrades.

**Source**: External architectural review (codex, 2026-03-19)

---

## F-MK-17: Central question — same-dataset empirical priors pre-freeze influence

- **issue_id**: X38-MK-17
- **classification**: Judgment call
- **opened_at**: 2026-03-19
- **opened_in_round**: 0 (pre-debate, from external review)
- **current_status**: **RESOLVED — Position A (shadow-only on same dataset)**
- **resolved_at**: 2026-03-19 (converged: claude_code + codex + human researcher)

**The question**:

> In same-dataset mode, should empirical cross-campaign priors have **any**
> pre-freeze influence at all?

This is the root question behind multiple downstream design decisions:

| Downstream issue | If YES (priors influence pre-freeze) | If NO (priors shadow-only) |
|-----------------|--------------------------------------|---------------------------|
| Overlap guard (C4) | Needs precise scoping (eval-data-only?) | Trivially resolved (all shadow) |
| Tier 2 challenge policy (MK-09, MK-16) | Needs anti-ratchet mechanism | Not needed (no pre-freeze rules) |
| Active cap (C5) | Needed to prevent attention overload | Not needed |
| Budget split (C3) | Needed to allocate frontier/probe/novelty | Not needed (all frontier) |
| Authority model (§4) | Needed for promote/demote/override | Simplified |
| Ontology/policy separation (§2) | Central invariant | Not needed |

**Arguments for YES** (controlled pre-freeze influence):
- Zero meta-knowledge = repeat all mistakes from V4→V8 every campaign
- Empirical priors (with metadata) save budget by deprioritizing known dead ends
- This IS what "learning across campaigns" means

**Arguments for NO** (shadow-only on same dataset):
- Same-dataset priors are contamination through governance channel
- Shadow-only is simpler, no ratchet risk, no overlap ambiguity
- Clean re-derivation means clean — any prior influence violates the premise
- V4→V8 showed 5 sessions with increasing meta-knowledge but NO convergence

**Possible middle ground**:
- Same-dataset: shadow-only (priors exist but don't shape discovery)
- New-dataset: priors activate with full Tier 2 governance
- This cleanly separates "learning" (cross-dataset) from "re-derivation" (same-dataset)

**Design question**: Which position best serves the mission "tìm cho bằng được
thuật toán tốt nhất"? The answer to this question should be resolved FIRST in
debate Phase 1, as it determines the shape of most downstream mechanisms.

**Source**: External architectural review (codex, 2026-03-19)

---

## Summary Table

| Issue ID | Finding | Classification | Status |
|----------|---------|---------------|--------|
| X38-MK-01 | Maturity pipeline (V6→V7→V8 de facto mechanism) | Thiếu sót | **Converged** (Stage 1A, R2) |
| X38-MK-02 | Five harms of the maturity pipeline | Sai thiết kế | **Converged** (Stage 1A, R2) |
| X38-MK-03 | Fundamental constraint: learning vs independence | Judgment call | **Judgment call** (§14, human researcher) |
| X38-MK-04 | Proposed: Derivation Test | Thiếu sót | **Judgment call** (§14, human researcher) |
| X38-MK-05 | Proposed: 3-Tier Rule Taxonomy | Thiếu sót | **Converged** (Stage 1A, R2) |
| X38-MK-06 | Three types of leakage (parameter / structural / attention) | Thiếu sót | **Converged** (Stage 1A, R2) |
| X38-MK-07 | Reconciliation with F-06 (4-category whitelist) | Thiếu sót | **Judgment call** (§14, human researcher) |
| X38-MK-08 | Lesson lifecycle: creation → classification → review → active → retire | Thiếu sót | **Converged** (Stage 1B, R6) |
| X38-MK-09 | Tier 2 challenge process (when, how, limits) | Thiếu sót | **Converged** (Stage 1B, R5) |
| X38-MK-10 | Tier 2 expiry mechanism (triggers, timing) | Thiếu sót | **Converged** (Stage 1B, R5) |
| X38-MK-11 | Conflict resolution between lessons | Thiếu sót | **Converged** (Stage 1B, R5) |
| X38-MK-12 | Confidence scoring — numeric vs qualitative | Judgment call | **Converged** (Stage 1B, R5) |
| X38-MK-13 | Storage format (JSON / Markdown / hybrid) | Judgment call | **Converged** (Stage 1B, R6) |
| X38-MK-14 | Boundary with Contamination Firewall (topic 002) | Thiếu sót | **Converged** (Stage 1B, R5) |
| X38-MK-15 | Bootstrap problem — seeding first campaign | Judgment call | **Converged** (Stage 1B, R5) |
| X38-MK-16 | Ratchet risk — Tier 2 rules self-protect by limiting evidence | Sai thiết kế | Mitigations converged (v2+) |
| X38-MK-17 | Central question — same-dataset priors pre-freeze influence | Judgment call | **RESOLVED: Position A (shadow-only on same dataset)** |
| C1 | Policy compiler boundary — deterministic vs epistemic | Thiếu sót | **Judgment call** (§14, human researcher) |
| C2 | Auditor agent — bounded authority and criteria | Thiếu sót | **Judgment call** (§14, human researcher) |
| C3 | Budget split 70/20/10 arbitrary | Thiếu sót | **Converged** (Stage 1B, R5) |
| C4 | Overlap guard quá mạnh | Sai thiết kế | **Converged** (Stage 1B, superseded by MK-17) |
| C5 | Active cap selection = pre-campaign bias | Thiếu sót | **Converged** (Stage 1B, R5) |
| C6 | Complexity tổng thể quá nhiều cho V1 | Thiếu sót | **Converged** (Stage 1B, R5) |

> **Topic 004 CLOSED (2026-03-21)**. 23/23 issues resolved. See `../004-meta-knowledge/final-resolution.md`
> for full decisions and `judgment-call-deliberation.md` for 5 judgment-call reasoning.
