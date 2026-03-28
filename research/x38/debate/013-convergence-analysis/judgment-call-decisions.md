# Judgment-Call Decisions — Topic 013: Convergence Analysis

**Purpose**: Self-contained intermediate file for Mode C closure of Topic 013.
Contains the converged positions from 12 rounds of 3-agent JC-debate
(Claude Code, CodeX, ChatGPT Pro) plus human researcher ratification.
All decisions below are binding input for `final-resolution.md`.

**Date**: 2026-03-28
**Decision owner**: Human researcher (ratified 3-agent consensus)

---

## Prerequisites checklist (Mode C)

- [x] All 4 issues are Judgment call (confirmed: Round 6 canonical debate,
      both agents)
- [x] Human researcher has decided all Judgment calls (ratified 3-agent
      consensus, 2026-03-28)
- [x] Round symmetry: both agents completed 6 rounds each
      (`claude_code/round-1` through `round-6`, `codex/round-1` through
      `round-6`). §14b satisfied.
- [ ] Codex closure audit (judgment-call-memo.md) — **to be produced by
      Codex using Mode C of `x38-debate-prompt-en.md`**
- [ ] `final-resolution.md` created (Step 1)
- [ ] `findings-under-review.md` updated (Step 2)
- [ ] `debate-index.md` + `README.md` updated (Step 3)
- [ ] Global files synced: `PLAN.md`, `EXECUTION_PLAN.md`,
      `docs/evidence_coverage.md` (Step 3b)
- [ ] Downstream unblocking checked: Topic 017 hard-dep on 013 (Step 3c)
- [ ] Draft spec created/updated in `drafts/` (Step 4)
- [ ] Status drift verification (Step 5)

---

## Decisions table (for final-resolution.md)

| Issue ID | Finding | Resolution | Type | Round closed |
|----------|---------|------------|------|-------------|
| X38-CA-01 | Convergence measurement framework | Accepted (Hybrid C) — measurement law + category semantics + convergence-side prerequisite semantics. Full routing = cross-topic (001×003×010). | Judgment call | 6 |
| X38-CA-02 | Stop conditions & diminishing returns | Accepted (A with 5-tier provenance) — ship v1 bootstrap defaults, per-constant provenance, provisional/recalibration-required. | Judgment call | 6 |
| X38-SSE-09 | Scan-phase correction law default | Accepted (A) — v1 default = Holm at α_FWER = 0.05. BH q_FDR = 0.10 = documented upgrade path. Conventional v1 constants. | Judgment call | 6 |
| X38-SSE-04-THR | Equivalence + anomaly thresholds | Accepted (Mixed) — freeze items 1–2, freeze 3a/3b ownership split, defer 3a numerics + 3b + 4. | Judgment call | 6 |

---

## Decision 1: CA-01 — Convergence Measurement Framework

### Accepted position (Hybrid C)

Topic 013 freezes:

1. **Measurement law**: Kendall's W as convergence metric, with null
   distribution derivation procedure → τ_low (noise floor), τ_high
   (near-identical threshold). Category boundaries are parametric on K
   (number of items being ranked). Two-mechanism architecture: ordinal
   agreement (levels 1–3 below) + cardinal equivalence via SSE-04-THR
   (level 4). Both agents converged on this in canonical debate.

2. **Multi-level categories**:
   - `NOT_CONVERGED` — no winner-stability signal.
   - `PARTIALLY_CONVERGED` — useful agreement signal but does NOT satisfy
     winner-eligibility. Suitable for narrowing, same-data HANDOFF, or
     continued research.
   - `FULLY_CONVERGED` — convergence-side prerequisite for downstream
     winner-recognition. Not sufficient alone — additional quality
     preconditions may be imposed by consuming topics (010, 017).

   **Asset-agnostic property**: Kendall's W is inherently asset-agnostic
   (ordinal agreement metric, independent of number of families/candidates).
   Thresholds (τ_low, τ_high) are percentile-based via null distribution,
   adapting to K automatically. No separate asset-specific calibration
   required. (`claude_code/round-1_opening-critique.md:448`;
   `round-2_author-reply.md:516-530`).

3. **Convergence-side prerequisite semantics**: `FULLY_CONVERGED` is the
   convergence-side prerequisite for `(winner exists)` in the sense of
   Topic 010's Clean OOS trigger (`final-resolution.md:55-57`).
   `PARTIALLY_CONVERGED` does NOT open Clean OOS progression.

4. **Exported outputs**: convergence-state and stall outputs, consumed by
   downstream topics.

Full routing matrix (what action follows from each state) remains cross-topic
integration between Topics 001, 003, 010, and 013.

### Rejected alternatives

- **Position A** (Rounds 1–3): "013 only owns measurement law; routing belongs
  to 001/003/010." *Too narrow* — ignores that 013 must own semantic meaning
  of its own outputs. F-30 asks directly whether PARTIALLY_CONVERGED suffices
  for Clean OOS (`findings-under-review.md:75`). If 013 doesn't answer, 010
  must interpret 013's output, violating output-owner-owns-semantics principle.

- **Position B** (implicit): "013 must own full routing matrix including
  governance thresholds within [τ_low, τ_high]." *Too broad* — governance
  threshold depends on cost-of-continuing (003), cost-of-false-stop
  (001's HANDOFF), and quality gates (010, 017). 013 cannot unilaterally
  decide these.

### Evidence

- `013 README.md:11-15`: "thuật toán xác định khi nào sessions đã hội tụ
  (hoặc nên dừng)" — algorithm + stop logic, not just measurement.
- `findings-under-review.md:72-76`: F-30 open question on PARTIALLY vs FULLY.
- `010 final-resolution.md:55-57`: auto-trigger requires `(winner exists)
  AND (enough new data)`.
- `001 final-resolution.md:119`: "exact numbers to Topic 013" — Topic 001
  routes numeric thresholds to 013.
- `design_brief.md:133-136`: "PENDING_CLEAN_OOS khi (winner chính thức) AND
  (đủ data mới)."

### Convergence history

- Rounds 1–3: A. Rounds 4–5: shifted to Hybrid C (CodeX broke false
  dichotomy). Round 6: Claude Code self-corrected, accepted Hybrid C. Round 7:
  CodeX narrowed to "convergence-side prerequisite semantics" (not full winner
  semantics). Rounds 8–12: confirmed. Direction stable from Round 7.

---

## Decision 2: CA-02 — Stop Conditions & Diminishing Returns

### Accepted position (A with 5-tier provenance)

Ship v1 with bootstrap defaults to break the calibration chicken-and-egg
problem. All defaults explicitly marked provisional / human-overridable /
recalibration-required after first genuine offline campaign evidence.

**Stop-law structure** (frozen):

- Stall detection: |ΔW_N| < max(ε_noise, ε_cost) for M consecutive sessions,
  where ΔW_N = W(1..N+1) − W(1..N).
- ΔW observations begin at session 3 (first marginal-gain observation).
- Cross-campaign ceiling bounds same-dataset repetition.

**Bootstrap defaults** (frozen as v1, with per-constant provenance):

| Constant | Value | Provenance tier | Rationale |
|----------|-------|----------------|-----------|
| `S_min` | 3 | **Structure-implied** | First ΔW observation arrives after session 3. Structural consequence of stop-law definition, not a tunable parameter. (`claude_code/round-6_author-reply.md:270-278`) |
| `ε_cost = ε_noise` | (equal) | **V1 simplifying default** | Internalizes stop-law fully within Topic 013. Avoids externalizing half the stopping criterion. (`claude_code/round-6_author-reply.md:297-311`) |
| `M` | 2 | **Early-stop convention** | M=3 IS compatible with S_max=5 (formula: M ≤ S_max − S_min + 1 = 3, per `claude_code/round-5_author-reply.md:283-289`). M=2 chosen as operational preference for earlier detection, NOT geometric necessity. Requires 2 consecutive stalls; earliest stop at session 4, latest at session 5. |
| `S_max` | 5 | **Weak paradigm heuristic** | Inferred from V4→V8 session count (`findings-under-review.md:108-139`, `docs/online_vs_offline.md:43-58`). Directional inference, not evidence-backed calibration. |
| `same_data_ceiling` | 3 | **Weak cross-archive heuristic** | Based on post-hoc grouping of V4→V8 into 3 "campaigns" (`claude_code/round-5_author-reply.md:299-307`). Argument exists but is weak: archive evidence uses session units, not campaign units — unit/archive mapping not clean. Weakest provenance in the entire set. |

**Coupling constraint** (frozen): M ≤ (S_max − S_min + 1). If S_max is
revised upward after calibration, M must be re-evaluated. At current values,
M=2 is below ceiling (3), so coupling is not active.

**Cross-topic interaction** (noted): If Topic 017 closes a coverage floor
obligation, coverage obligation may delay stop suggestion. Recorded as
013×017 cross-topic tension.

### Rejected alternative

- **Position B**: Wait for genuine offline calibration evidence before
  committing to any defaults. *Bootstrap trap* — you need numbers to start
  running, and running produces the evidence. Repo precedent:
  `validation/thresholds.py` already uses `CONV:UNCALIBRATED` governance
  class for exactly this situation.

### Evidence

- `findings-under-review.md:81-140`: stop-law gap analysis.
- `docs/online_vs_offline.md:43-58,82-92`: paradigm-inference boundary.
- `001 final-resolution.md:168`: "Stop thresholds, same-data ceiling,
  sessions-per-campaign | Topic 013 (F-31) | 013 owns numeric convergence
  rules" (Deferred table).
- `claude_code/round-5_author-reply.md:283-289`: M ≤ S_max − S_min + 1
  formula (M=3 compatible with S_max=5).
- `claude_code/round-6_author-reply.md:266-311`: ΔW observation timing, S_min
  structure, ε_cost = ε_noise rationale.
- `validation/thresholds.py:3-8`: provenance class governance (STAT, LIT,
  CONV, CONV:UNCALIBRATED).

### Convergence history

- Rounds 1–3: A (flat). Round 3: Claude Code flagged M=2 coupling. Round 4:
  CodeX introduced provenance tiers. Round 7: CodeX separated session vs
  campaign axis. Round 9: Claude Code flagged same_data_ceiling weakness.
  Round 11: ChatGPT Pro caught M=2 arithmetic error (M=3 IS compatible with
  S_max=5). Round 12: Claude Code accepted, reclassified M=2 as early-stop
  convention. Direction stable throughout; provenance model refined iteratively.

### Corrections applied during JC-debate

- **M=2 provenance** (Round 11): Round 3 incorrectly claimed "M=3 requires
  S_max≥6." Corrected: formula M ≤ S_max − S_min + 1 = 3 shows M=3 IS
  compatible. M=2 reclassified from "constrained choice" to "early-stop
  convention." This error propagated uncorrected through Rounds 3–10.

---

## Decision 3: SSE-09 — Scan-Phase Correction Law Default

### Accepted position (A — freeze exact conventional v1 constants)

- **v1 operational default**: Holm (step-down) procedure.
- **Holm α_FWER = 0.05**: Conservative family-wise error rate. Stricter than
  per-test α = 0.10 because family-wise errors compound across scan phase —
  one false discovery can redirect an entire cell's probe budget.
- **BH q_FDR = 0.10**: Documented upgrade path, activated only after Topic 017
  closes the required proof-consumption guarantee.
- **Provenance**: Fixed conventional v1 constants, not x38-derived calibration.

### Rejected alternative

- **"Leave exact constants to human"**: Insufficient. Repo already has
  governance for conventional thresholds (`validation/thresholds.py:3-8`
  provenance classes, `validation/thresholds.py:52-66` fixed statistical
  constants). Leaving constants open applies a stricter standard than the
  repo's own governance permits.

### Clarifications (from JC-debate)

- α_FWER = 0.05 does NOT numerically "align" with per-test α = 0.10 — they
  are different error-control layers. The numeric coincidence of q_FDR = 0.10
  matching per-test α = 0.10 is not a justification; it is a governance
  symmetry, nothing more.
- BH cannot be called a v1 default when its activation depends on Topic 017's
  proof-consumption guarantee, which is not yet closed.

### Cell-elite diversity interaction (open question from findings)

Correction precedes diversity preservation, not vice versa. Holm correction
filters candidates at scan-phase entry (Stage 4); cell-elite diversity
operates on post-correction survivors within cells. No conflict: correction
ensures statistical validity of discoveries → cell-elite diversity ensures
breadth among valid discoveries. The ordering is: scan → correct → admit
to cell → within-cell competition → diversity preservation.
(`claude_code/round-1_opening-critique.md:326-341,500`;
`round-3_author-reply.md:273-283`).

### Convergence note

The default formula subpoint (v1 = Holm) **converged in canonical debate**
(Claude Code proposed `Converged pending §7c` at Round 6, line 167). Codex
did not confirm §7c because exact threshold calibration remained. The
Judgment call resolves the threshold part; the formula choice itself was
not disputed after Round 3.

### Evidence

- `findings-under-review.md:185-188`: Topic 013 owns default formula, v1
  default, threshold calibration methodology.
- `018 final-resolution.md`: SSE-D-09 routing.
- `validation/thresholds.py:1-15`: provenance class governance.
- `validation/thresholds.py:49-66`: existing fixed statistical constants
  precedent.

### Convergence history

- Converged from Round 3. No substantive dissent in 12 rounds. Only
  refinement: acknowledge α_FWER ≠ α_per-test (Round 3), remove false
  "align" rationalization (Round 7).

---

## Decision 4: SSE-04-THR — Equivalence + Anomaly Thresholds

### Accepted position (Mixed — freeze items 1–2, split + defer item 3–4)

**Item 1 — Behavioral equivalence threshold: FREEZE**

- `ρ > 0.95` as conventional v1 high-similarity cutoff.
- **Provenance** (honest): conventional engineering choice, informed by but
  NOT derived from E5 cross-timescale ρ ≈ 0.92 observation. Placed above 0.92
  (timescale variants that should remain distinct). The pseudo-derivation
  "1−R² ≈ 0.0975 < 5%" is **incorrect arithmetic** (0.0975 ≈ 9.75%, not <5%)
  and must not appear in final-resolution.
- Does NOT claim variance-decomposition justification.

**Item 2 — Structural hash granularity: FREEZE (design-contract level)**

- Minimum invariance surface:
  - Invariant with whitespace, comments, import order.
  - Bucket by structure of signal-generation logic (entry + exit) + sorted
    parameter schema (names + types).
  - Exclude parameter values from hash bucket.
  - Behavioral audit handles cross-bucket functional equivalence.
- Compatible with Topic 008 (interface + structural pre-bucket fields) and
  Topic 018 (AST-hash subset as hybrid method component,
  `018 final-resolution.md:206-215`).
- Exact normalization algebra (α-equivalence, control-flow collapse, etc.)
  is **implementation-defined for v1** — not settled here.

**Item 3 — Robustness bundle minimum requirements: SPLIT 3a/3b**

- **Item 3a — Numeric production floor (013 owns)**:
  - Ownership FROZEN: Topic 013 owns "what 'minimum' means numerically"
    (`findings-under-review.md:207-223`).
  - Exact numerics DEFERRED: canonical debate (6 rounds) did not produce
    specific numeric minimums. This is a **structural dependency block**:
    013 needs to know what 017's consumption framework requires to set
    meaningful floors; 017 needs to know what 013 produces to set passing
    criteria. Circular dependency prevents unilateral resolution.
  - NOT "incomplete debate" (could have been resolved with more rounds).
    NOT "empty assignment" (boundary and question-form are defined).
    Accurate label: **defined-but-unfilled numeric slot, structurally
    blocked by 017 dependency**.
  - Upstream input: Topic 018's working minimum inventory (5 proof components,
    5 anomaly axes) at judgment-call authority — working handoff, not
    authoritative numeric law
    (`018 final-resolution.md:125-136`).

- **Item 3b — Consumption sufficiency (shared 013×017)**:
  - Whether item 3a's minimums are SUFFICIENT for 017's consumption framework.
  - Topic 017 owns: "proof bundle consumption rules — what constitutes
    'passing' a proof component" (`017 findings-under-review.md:424-435`).
  - DEFERRED to 013×017 integration surface.

**Item 4 — Anomaly axis thresholds: DEFERRED (shared 013×017)**

- Shared surface per both findings files.
- Topic 013 owns threshold methodology (hybrid relative/absolute approach
  with sparsity guard for small cell populations).
- Topic 017 owns exact per-axis numeric values and categories.
- Open question "absolute or relative to cell population?" — canonical debate
  resolved directionally: hybrid approach where thresholds are relative to
  cell population but fall back to absolute minimums below a population-size
  floor (sparsity guard). Exact numerics deferred to 013×017 integration.
  (`claude_code/round-1_opening-critique.md:444-469`;
  `round-2_author-reply.md:535-550`;
  `round-3_author-reply.md:474`).
- DEFERRED to 013×017 integration.

### Contamination subpoint

Converged in canonical debate (both agents, Round 6). No further action needed.

### Evidence

- `findings-under-review.md:202-229`: SSE-04-THR scope and 013's ownership
  (items 1–4).
- `017 findings-under-review.md:424-435`: Topic 017 owns proof-bundle
  consumption rules.
- `018 final-resolution.md:125-176`: working minimum inventory (5+5),
  judgment-call authority, "NOT described as immutable historically-converged
  exact label set."
- `018 closure-audit.md:1-4`: "SUPERSEDED" — document versioning artifact from
  reopening, not substantive contradiction. Standard 2-agent debate is
  authoritative.

### Convergence history

- Rounds 1–3: A (freeze 1–2, carry 3–4 to 017). Round 4: CodeX broke false
  completeness — item 3 cannot be swept entirely to 017. Round 5: ChatGPT Pro
  caught ρ arithmetic error. Round 6: Claude Code split item 3→3a/3b. Round 7:
  CodeX cautioned against premature numeric closure. Round 9: Claude Code
  identified 3a as gap. Round 10: CodeX corrected "empty assignment" →
  "defined-but-unfilled numeric slot." Round 11: ChatGPT Pro confirmed split.
  Round 12: Claude Code reframed gap as structural dependency block.

---

## Ownership / status matrix (for final-resolution.md)

| Item | Status | Owner after 013 closes | Provenance |
|------|--------|----------------------|------------|
| Measurement law (Kendall's W) | FROZEN | 013 (complete) | Converged in canonical debate |
| Two-mechanism architecture (ordinal + cardinal) | FROZEN | 013 (complete) | Converged in canonical debate |
| Derivation procedure (τ_low, τ_high) | FROZEN (parametric on K) | 013 (awaits K from comparison domain) | Converged |
| Multi-level categories (NOT/PARTIALLY/FULLY) | FROZEN | 013 (complete) | Converged |
| Asset-agnostic property (Kendall's W + percentile thresholds) | FROZEN | 013 (complete) | Converged (inherent to metric choice) |
| Convergence-side prerequisite semantics | FROZEN | 013 (complete) | Judgment call (Hybrid C) |
| Governance threshold within [τ_low, τ_high] | DEFERRED | 001×003×010×013 integration | Decision-theoretic, needs cost inputs |
| Stop-law structure (ΔW stall detection) | FROZEN | 013 (complete) | Converged |
| S_min = 3 | FROZEN | 013 (complete) | Structure-implied |
| ε_cost = ε_noise | FROZEN | 013 (complete) | V1 simplifying default |
| M = 2 | FROZEN (provisional) | 013 (recalibrate after first offline campaign) | Early-stop convention |
| S_max = 5 | FROZEN (provisional) | 013 (recalibrate) | Weak paradigm heuristic |
| same_data_ceiling = 3 | FROZEN (provisional) | 013 (recalibrate) | Weak cross-archive heuristic |
| Holm α_FWER = 0.05 | FROZEN (conventional) | 013 (complete) | Conventional v1 constant |
| BH q_FDR = 0.10 upgrade path | FROZEN (contingent on 017) | 013×017 | Conventional, activation requires 017 |
| ρ > 0.95 behavioral equivalence | FROZEN (conventional) | 013 (complete) | Conventional cutoff, not variance-derived |
| Hash granularity (design-contract) | FROZEN | 013 (complete) | Design-level minimum invariance |
| Item 3a ownership (numeric minimums) | FROZEN | 013 | Ownership clear |
| Item 3a exact numerics | DEFERRED | 013 (structurally blocked by 017) | Circular dependency |
| Item 3b (consumption sufficiency) | DEFERRED | 013×017 shared | 017 owns consumption rules |
| Item 4 (anomaly thresholds methodology) | FROZEN | 013 (hybrid relative/absolute + sparsity guard) | Converged directionally |
| Item 4 (anomaly thresholds exact numerics) | DEFERRED | 013×017 shared | 017 owns per-axis values |
| Contamination subpoint (SSE-04-THR) | CONVERGED | 013 (complete) | Converged in canonical debate, Round 6 |
| Correction → cell-elite ordering (SSE-09) | FROZEN | 013 (complete) | Converged: correction precedes diversity |
| Holm as default formula (SSE-09) | FROZEN | 013 (complete) | Converged in canonical debate (formula, not thresholds) |
| 017 coverage floor → stop interaction | NOTED | 013×017 cross-topic tension | Recorded, no action needed now |

---

## Cross-topic impact (for final-resolution.md)

| Topic | Dependency | Impact of 013 closure |
|-------|-----------|----------------------|
| 017 (Epistemic Search Policy) | **Hard-dep on 013** | 013 closure unblocks 017. Items 3a numerics, 3b, 4 become 013×017 integration obligations within 017's debate. BH upgrade path contingent on 017. |
| 003 (Protocol Engine) | Indirect via 017 | Stop-law structure and defaults inform pipeline stop logic. 003 consumes convergence-state output. |
| 001 (Campaign Model) | Soft-dep (CLOSED) | 001 routed stop thresholds/ceiling to 013 — now resolved. HANDOFF routing contract consumes convergence-side prerequisite semantics. |
| 008 (Architecture Identity) | Indirect | Hash granularity (item 2) compatible with 008's identity schema. No conflict. |
| 010 (Clean OOS Certification) | Soft-dep (CLOSED) | 010's `(winner exists)` predicate now has convergence-side prerequisite: FULLY_CONVERGED required. |

---

## Draft impact (for final-resolution.md)

| Draft | Sections affected | Action needed |
|-------|------------------|---------------|
| `methodology_spec.md` | Convergence algorithm (Kendall's W, categories, prerequisite semantics) | Create |
| `methodology_spec.md` | Stop conditions (stop-law structure, bootstrap defaults, provenance tiers) | Create |
| `architecture_spec.md` | Scan-phase correction law (Holm default, BH upgrade path) | Create |
| `architecture_spec.md` | Equivalence thresholds (ρ cutoff, hash granularity) | Create |

---

## Corrections log (errors caught during JC-debate)

These errors were present in the canonical debate or early JC-rounds and were
corrected during the 12-round JC-debate process:

1. **ρ > 0.95 pseudo-derivation** (caught Round 5, accepted Round 6):
   "1−R² ≈ 0.0975 implies < 5% independent variance" — arithmetic error
   (0.0975 ≈ 9.75%, not < 5%). Pseudo-derivation removed.

2. **M=2 provenance inflation** (caught Round 11, accepted Round 12):
   "M=3 requires S_max≥6, so M=2 is the largest compatible value" — incorrect.
   Formula M ≤ S_max − S_min + 1 = 3 shows M=3 IS compatible with S_max=5.
   M=2 reclassified from "constrained choice" to "early-stop convention."

3. **CA-01 false dichotomy** (caught Round 4, accepted Round 6):
   Original A/B framing forced choice between "013 owns only measurement" and
   "013 owns full routing." Hybrid C resolved: 013 owns convergence-side
   prerequisite semantics, not full downstream routing.

---

## Next steps (Mode C closure process)

1. **Codex judgment-call-memo.md**: Run Codex Mode C
   (`x38-debate-prompt-en.md` MODE C) to produce advisory memo. Input: this
   file + all 12 round files. Output:
   `debate/013-convergence-analysis/codex/judgment-call-memo.md`

2. **Claude Code Mode C closure**: Run Claude Code Mode C
   (`x38-author-prompt-en.md` Mode C) to execute Steps 1–5:
   - Step 1: Create `final-resolution.md` using decisions above
   - Step 2: Update `findings-under-review.md` statuses
   - Step 3: Update `debate-index.md` + `README.md` → CLOSED
   - Step 3b: Sync `PLAN.md`, `EXECUTION_PLAN.md`, `docs/evidence_coverage.md`
   - Step 3c: Check downstream unblocking (Topic 017 hard-dep)
   - Step 4: Create/update draft specs in `drafts/`
   - Step 5: Verify no status drift

3. **Order**: Codex memo first (advisory, read-only), then Claude Code closure
   (writes all files). Human researcher reviews final artifacts.
