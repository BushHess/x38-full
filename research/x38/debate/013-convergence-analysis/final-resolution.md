# Final Resolution — Convergence Analysis

**Topic ID**: X38-T-13
**Closed**: 2026-03-28
**Rounds**: 6 (canonical 2-agent debate) + 12 (3-agent JC-debate)
**Participants**: claude_code, codex (canonical); claude_code, codex, chatgpt_pro (JC-debate)

**Binding input**: `judgment-call-decisions.md` (ratified by human researcher, 2026-03-28)
**Codex audit**: `codex/judgment-call-memo.md` (incorporated — 4 cleanup items addressed below)

---

## Round symmetry

Both agents completed 6 rounds each in the canonical debate
(`claude_code/round-1` through `round-6`, `codex/round-1` through `round-6`).
No asymmetry to document per rules.md §14b.

---

## Decisions

| Issue ID | Finding | Resolution | Type | Round closed |
|----------|---------|------------|------|-------------|
| X38-CA-01 | Convergence measurement framework | Accepted (Hybrid C) — measurement law + category semantics + convergence-side prerequisite semantics. Full routing = cross-topic (001x003x010). | Judgment call | 6 |
| X38-CA-02 | Stop conditions & diminishing returns | Accepted (A with 5-tier provenance) — ship v1 bootstrap defaults, per-constant provenance, provisional/recalibration-required. | Judgment call | 6 |
| X38-SSE-09 | Scan-phase correction law default | Accepted (A) — v1 default = Holm at alpha_FWER = 0.05. BH q_FDR = 0.10 = documented upgrade path. Conventional v1 constants. | Judgment call | 6 |
| X38-SSE-04-THR | Equivalence + anomaly thresholds | Accepted (Mixed) — freeze items 1-2, freeze 3a/3b ownership split, freeze item 4 methodology, defer 3a numerics + 3b + item 4 numerics. | Judgment call | 6 |

---

## Key design decisions (for drafts/)

### Decision 1: CA-01 — Convergence Measurement Framework (Hybrid C)

**Accepted position**: Topic 013 freezes:

1. **Measurement law**: Kendall's W as convergence metric, with null distribution
   derivation procedure -> tau_low (noise floor), tau_high (near-identical threshold).
   Category boundaries are parametric on K (number of items being ranked).
   Two-mechanism architecture: ordinal agreement (levels 1-3) + cardinal equivalence
   via SSE-04-THR (level 4). Both agents converged on this in canonical debate.

2. **Multi-level categories**:
   - `NOT_CONVERGED` -- no winner-stability signal.
   - `PARTIALLY_CONVERGED` -- useful agreement signal but does NOT satisfy
     winner-eligibility. Suitable for narrowing, same-data HANDOFF, or continued
     research.
   - `FULLY_CONVERGED` -- convergence-side prerequisite for downstream
     winner-recognition. Not sufficient alone -- additional quality preconditions
     may be imposed by consuming topics (010, 017).

   **Asset-agnostic property**: Kendall's W is inherently asset-agnostic (ordinal
   agreement metric, independent of number of families/candidates). Thresholds
   (tau_low, tau_high) are percentile-based via null distribution, adapting to K
   automatically. No separate asset-specific calibration required.

3. **Convergence-side prerequisite semantics**: `FULLY_CONVERGED` is the
   convergence-side prerequisite for `(winner exists)` in the sense of Topic 010's
   Clean OOS trigger (`debate/010-clean-oos-certification/final-resolution.md:55-57`).
   `PARTIALLY_CONVERGED` does NOT open Clean OOS progression.

4. **Exported outputs**: convergence-state and stall outputs, consumed by downstream
   topics.

Full routing matrix (what action follows from each state) remains cross-topic
integration between Topics 001, 003, 010, and 013.

**Rejected alternatives**:

- **Position A** (Rounds 1-3): "013 only owns measurement law; routing belongs to
  001/003/010." Too narrow -- ignores that 013 must own semantic meaning of its own
  outputs. F-30 directly asks whether PARTIALLY_CONVERGED suffices for Clean OOS
  (`findings-under-review.md:75`). If 013 doesn't answer, 010 must interpret 013's
  output, violating output-owner-owns-semantics principle.

- **Position B** (implicit): "013 must own full routing matrix including governance
  thresholds within [tau_low, tau_high]." Too broad -- governance threshold depends
  on cost-of-continuing (003), cost-of-false-stop (001's HANDOFF), and quality gates
  (010, 017). 013 cannot unilaterally decide these.

**Rationale**:
- `013 README.md:11-15`: scope includes algorithm + stop logic, not just measurement.
- `findings-under-review.md:72-76`: F-30 open question on PARTIALLY vs FULLY.
- `010 final-resolution.md:55-57`: auto-trigger requires `(winner exists) AND (enough new data)`.
- `001 final-resolution.md:119`: "exact numbers to Topic 013" -- Topic 001 routes numeric thresholds to 013.
- `design_brief.md:133-136`: "PENDING_CLEAN_OOS khi (winner chinh thuc) AND (du data moi)."

**Convergence history**: Rounds 1-3: Position A. Rounds 4-5: shifted to Hybrid C
(CodeX broke false dichotomy). Round 6: Claude Code self-corrected. Rounds 7-12
(JC): confirmed. Direction stable from Round 7.

---

### Decision 2: CA-02 — Stop Conditions & Diminishing Returns

**Accepted position**: Ship v1 with bootstrap defaults to break the calibration
chicken-and-egg problem. All defaults explicitly marked provisional /
human-overridable / recalibration-required after first genuine offline campaign
evidence.

**Stop-law structure** (frozen):

- Stall detection: `|delta_W_N| < max(epsilon_noise, epsilon_cost)` for M consecutive
  sessions, where `delta_W_N = W(1..N+1) - W(1..N)`.
- delta_W observations begin at session 3 (first marginal-gain observation).
- Cross-campaign ceiling bounds same-dataset repetition.

**Bootstrap defaults** (frozen as v1, with per-constant provenance):

| Constant | Value | Provenance tier | Rationale |
|----------|-------|----------------|-----------|
| `S_min` | 3 | **Structure-implied** | First delta_W observation arrives after session 3. Structural consequence of stop-law definition, not a tunable parameter. |
| `epsilon_cost = epsilon_noise` | (equal) | **V1 simplifying default** | Internalizes stop-law fully within Topic 013. Avoids externalizing half the stopping criterion. |
| `M` | 2 | **Early-stop convention** | M=3 IS compatible with S_max=5 (formula: M <= S_max - S_min + 1 = 3). M=2 chosen as operational preference for earlier detection, NOT geometric necessity. Requires 2 consecutive stalls; earliest stop at session 4, latest at session 5. |
| `S_max` | 5 | **Weak paradigm heuristic** | Inferred from V4->V8 session count. Directional inference, not evidence-backed calibration. |
| `same_data_ceiling` | 3 | **Weak cross-archive heuristic** | Based on post-hoc grouping of V4->V8 into 3 "campaigns." Weakest provenance in the entire set. |

**5-tier provenance model**:
1. **Structure-implied**: derived mechanically from stop-law definition (S_min).
2. **V1 simplifying default**: chosen for v1 simplicity, not calibrated (epsilon equality).
3. **Early-stop convention**: compatible but not required; operational preference (M).
4. **Weak paradigm heuristic**: directional inference from V4->V8 (S_max).
5. **Weak cross-archive heuristic**: weakest tier, unit/archive mapping not clean (same_data_ceiling).

**Coupling constraint** (frozen): `M <= (S_max - S_min + 1)`. If S_max revised
upward, M must be re-evaluated. At current values, M=2 < ceiling (3).

**Cross-topic interaction** (noted): If Topic 017 closes a coverage floor
obligation, coverage obligation may delay stop suggestion. Recorded as 013x017
cross-topic tension.

**Rejected alternative**: Wait for genuine offline calibration evidence before
committing to any defaults. Bootstrap trap -- you need numbers to start running,
and running produces the evidence. Repo precedent:
`/var/www/trading-bots/btc-spot-dev/validation/thresholds.py` [extra-archive]
already uses `CONV:UNCALIBRATED` governance class for exactly this situation.

**Rationale**:
- `findings-under-review.md:81-140`: stop-law gap analysis.
- `docs/online_vs_offline.md:43-58,82-92`: paradigm-inference boundary.
- `001 final-resolution.md:168`: stop thresholds routed to 013.
- `claude_code/round-5_author-reply.md:283-289`: M <= S_max - S_min + 1 formula.
- `claude_code/round-6_author-reply.md:266-311`: delta_W timing, S_min structure, epsilon rationale.
- `/var/www/trading-bots/btc-spot-dev/validation/thresholds.py:3-8` [extra-archive]: provenance class governance.

**Convergence history**: Rounds 1-3: Position A (flat). Round 3: coupling flagged.
Round 4: provenance tiers introduced. Round 9: same_data_ceiling weakness flagged.
Round 11: M=2 arithmetic corrected. Direction stable throughout.

---

### Decision 3: SSE-09 — Scan-Phase Correction Law Default

**Accepted position**:

- **v1 operational default**: Holm (step-down) procedure.
- **Holm alpha_FWER = 0.05**: Conservative family-wise error rate. Stricter than
  per-test alpha = 0.10 because family-wise errors compound across scan phase --
  one false discovery can redirect an entire cell's probe budget.
- **BH q_FDR = 0.10**: Documented upgrade path, activated only after Topic 017
  closes the required proof-consumption guarantee.
- **Provenance**: Fixed conventional v1 constants, not x38-derived calibration.

**Clarifications** (from JC-debate):
- alpha_FWER = 0.05 does NOT numerically "align" with per-test alpha = 0.10 --
  they are different error-control layers.
- BH cannot be called a v1 default when its activation depends on Topic 017's
  proof-consumption guarantee, which is not yet closed.

**Cell-elite diversity interaction**: Correction precedes diversity preservation,
not vice versa. Holm correction filters candidates at scan-phase entry (Stage 4);
cell-elite diversity operates on post-correction survivors within cells. Ordering:
scan -> correct -> admit to cell -> within-cell competition -> diversity preservation.

**Convergence note**: The default formula subpoint (v1 = Holm) **converged in
canonical debate** (Claude Code proposed `Converged pending section 7c` at Round 6,
line 167). The Judgment call resolves the threshold part; the formula choice itself
was not disputed after Round 3.

**Rejected alternative**: "Leave exact constants to human." Insufficient. Repo
already has governance for conventional thresholds
(`/var/www/trading-bots/btc-spot-dev/validation/thresholds.py:3-8,52-66`
[extra-archive] provenance classes + fixed statistical constants).

**Rationale**:
- `findings-under-review.md:185-188`: Topic 013 owns default formula, v1 default, threshold calibration methodology.
- `018 final-resolution.md`: SSE-D-09 routing.
- `/var/www/trading-bots/btc-spot-dev/validation/thresholds.py:1-15` [extra-archive]: provenance class governance.

**Convergence history**: Converged from Round 3. Only refinement: alpha_FWER !=
alpha_per-test acknowledgment (Round 3), remove false "align" rationalization (Round 7).

---

### Decision 4: SSE-04-THR — Equivalence + Anomaly Thresholds

**Accepted position** (Mixed -- freeze items 1-2, split + defer item 3-4):

**Item 1 -- Behavioral equivalence threshold: FREEZE**

- `rho > 0.95` as conventional v1 high-similarity cutoff.
- **Provenance** (honest): conventional engineering choice, informed by but NOT
  derived from E5 cross-timescale rho ~ 0.92 observation. Placed above 0.92
  (timescale variants that should remain distinct).
- The pseudo-derivation "1-R^2 ~ 0.0975 < 5%" is **incorrect arithmetic**
  (0.0975 ~ 9.75%, not <5%) and does NOT appear in this resolution.
- Does NOT claim variance-decomposition justification.

**Item 2 -- Structural hash granularity: FREEZE (design-contract level)**

- Minimum invariance surface:
  - Invariant with whitespace, comments, import order.
  - Bucket by structure of signal-generation logic (entry + exit) + sorted parameter
    schema (names + types).
  - Exclude parameter values from hash bucket.
  - Behavioral audit handles cross-bucket functional equivalence.
- Compatible with Topic 008 (interface + structural pre-bucket fields) and Topic 018
  (AST-hash subset as hybrid method component).
- Exact normalization algebra (alpha-equivalence, control-flow collapse, etc.) is
  **implementation-defined for v1** -- not settled here.

**Item 3 -- Robustness bundle minimum requirements: SPLIT 3a/3b**

- **Item 3a -- Numeric production floor (013 owns)**:
  - Ownership FROZEN: Topic 013 owns "what 'minimum' means numerically."
  - Exact numerics DEFERRED: canonical debate did not produce specific minimums.
    **Structural dependency block**: 013 needs to know what 017's consumption framework
    requires to set meaningful floors; 017 needs to know what 013 produces to set
    passing criteria. Circular dependency prevents unilateral resolution.
  - Upstream input: Topic 018's working minimum inventory (5 proof components, 5
    anomaly axes) at judgment-call authority -- working handoff, not authoritative
    numeric law (`018 final-resolution.md:125-136`).

- **Item 3b -- Consumption sufficiency (shared 013x017)**:
  - Whether item 3a's minimums are SUFFICIENT for 017's consumption framework.
  - Topic 017 owns: "proof bundle consumption rules -- what constitutes 'passing' a
    proof component" (`017 findings-under-review.md:424-435`).
  - DEFERRED to 013x017 integration surface.

**Item 4 -- Anomaly axis thresholds: methodology FROZEN, numerics DEFERRED**

- Shared surface per both findings files.
- Topic 013 owns threshold methodology: hybrid relative/absolute approach with
  sparsity guard for small cell populations (FROZEN).
- Topic 017 owns exact per-axis numeric values and categories (DEFERRED).
- Open question "absolute or relative to cell population?" resolved directionally:
  hybrid approach where thresholds are relative to cell population but fall back to
  absolute minimums below a population-size floor (sparsity guard). Exact numerics
  deferred to 013x017 integration.

**Topic 006 interaction** (explicitly deferred): The open question "How does the
structural pre-bucket interact with 006's feature family taxonomy?"
(`findings-under-review.md:227`) is deferred to the 006x013 integration surface.
013 freezes hash granularity at design-contract level (item 2); 006 owns feature
family taxonomy. Compatibility to be confirmed when Topic 006 closes.

**Contamination subpoint**: Converged in canonical debate (both agents, Round 6).
No further action needed.

**Rejected alternative**: Full-surface-closure: freeze all items (1-4) including
exact numerics before closing 013. Insufficient basis -- canonical debate (6 rounds)
did not produce numeric minimums for items 3a/4, and the structural dependency on
Topic 017's consumption framework prevents unilateral resolution.

**Rationale**:
- `findings-under-review.md:202-229`: SSE-04-THR scope and 013's ownership.
- `017 findings-under-review.md:424-435`: Topic 017 owns proof-bundle consumption rules.
- `018 final-resolution.md:125-176`: working minimum inventory (5+5).
- `018 closure-audit.md:1-4`: "SUPERSEDED" is document versioning artifact, not substantive contradiction.

**Convergence history**: Rounds 1-3: freeze 1-2, carry 3-4 to 017. Round 4: CodeX
broke false completeness. Round 5: rho arithmetic corrected. Round 6: item 3 split
into 3a/3b. Round 10: "empty assignment" corrected to "defined-but-unfilled numeric
slot." Round 12: gap reframed as structural dependency block.

---

## Codex audit incorporation

Codex closure audit (`codex/judgment-call-memo.md`, 2026-03-28) identified 4 cleanup
items. Resolution:

1. **CA-01 asset-agnostic citation error**: The cited lines
   (`claude_code/round-1_opening-critique.md:448`, `round-2_author-reply.md:516-530`)
   discuss anomaly thresholds, not CA-01/Kendall's W. Asset-agnostic property is
   inherent to Kendall's W metric choice (ordinal, K-parametric) -- no separate
   citation needed. Corrected in this document by removing specific line citations
   for the asset-agnostic claim.

2. **`validation/thresholds.py` citation style**: All references now use full path
   (`/var/www/trading-bots/btc-spot-dev/validation/thresholds.py`) with
   `[extra-archive]` marker per x38_RULES.md.

3. **SSE-04-THR item 4 summary/body mismatch**: Decisions table (above) now correctly
   states "freeze item 4 methodology, defer item 4 numerics" -- reconciling the
   summary with the body and ownership matrix.

4. **Missing Topic 006 interaction**: Explicitly deferred in Decision 4 above
   (006x013 integration surface).

No ratified decision overturned. All repairs are documentary/provenance fixes.

---

## Ownership / status matrix

| Item | Status | Owner after 013 closes | Provenance |
|------|--------|----------------------|------------|
| Measurement law (Kendall's W) | FROZEN | 013 (complete) | Converged in canonical debate |
| Two-mechanism architecture (ordinal + cardinal) | FROZEN | 013 (complete) | Converged in canonical debate |
| Derivation procedure (tau_low, tau_high) | FROZEN (parametric on K) | 013 (awaits K from comparison domain) | Converged |
| Multi-level categories (NOT/PARTIALLY/FULLY) | FROZEN | 013 (complete) | Converged |
| Asset-agnostic property (Kendall's W + percentile thresholds) | FROZEN | 013 (complete) | Converged (inherent to metric choice) |
| Convergence-side prerequisite semantics | FROZEN | 013 (complete) | Judgment call (Hybrid C) |
| Governance threshold within [tau_low, tau_high] | DEFERRED | 001x003x010x013 integration | Decision-theoretic, needs cost inputs |
| Stop-law structure (delta_W stall detection) | FROZEN | 013 (complete) | Converged |
| S_min = 3 | FROZEN | 013 (complete) | Structure-implied |
| epsilon_cost = epsilon_noise | FROZEN | 013 (complete) | V1 simplifying default |
| M = 2 | FROZEN (provisional) | 013 (recalibrate after first offline campaign) | Early-stop convention |
| S_max = 5 | FROZEN (provisional) | 013 (recalibrate) | Weak paradigm heuristic |
| same_data_ceiling = 3 | FROZEN (provisional) | 013 (recalibrate) | Weak cross-archive heuristic |
| Holm alpha_FWER = 0.05 | FROZEN (conventional) | 013 (complete) | Conventional v1 constant |
| BH q_FDR = 0.10 upgrade path | FROZEN (contingent on 017) | 013x017 | Conventional, activation requires 017 |
| rho > 0.95 behavioral equivalence | FROZEN (conventional) | 013 (complete) | Conventional cutoff, not variance-derived |
| Hash granularity (design-contract) | FROZEN | 013 (complete) | Design-level minimum invariance |
| Item 3a ownership (numeric minimums) | FROZEN | 013 | Ownership clear |
| Item 3a exact numerics | DEFERRED | 013 (structurally blocked by 017) | Circular dependency |
| Item 3b (consumption sufficiency) | DEFERRED | 013x017 shared | 017 owns consumption rules |
| Item 4 (anomaly thresholds methodology) | FROZEN | 013 (hybrid relative/absolute + sparsity guard) | Converged directionally |
| Item 4 (anomaly thresholds exact numerics) | DEFERRED | 013x017 shared | 017 owns per-axis values |
| Contamination subpoint (SSE-04-THR) | CONVERGED | 013 (complete) | Converged in canonical debate, Round 6 |
| Correction -> cell-elite ordering (SSE-09) | FROZEN | 013 (complete) | Converged: correction precedes diversity |
| Holm as default formula (SSE-09) | FROZEN | 013 (complete) | Converged in canonical debate |
| 017 coverage floor -> stop interaction | NOTED | 013x017 cross-topic tension | Recorded, no action needed now |
| 006 pre-bucket interaction | DEFERRED | 006x013 integration surface | Explicitly deferred (Codex audit item 4) |

---

## Corrections applied during JC-debate

These errors were present in the canonical debate or early JC-rounds and were
corrected during the 12-round JC-debate process:

1. **rho > 0.95 pseudo-derivation** (caught Round 5, accepted Round 6):
   "1-R^2 ~ 0.0975 implies < 5% independent variance" -- arithmetic error
   (0.0975 ~ 9.75%, not < 5%). Pseudo-derivation removed. rho > 0.95 reclassified
   as conventional v1 choice.

2. **M=2 provenance inflation** (caught Round 11, accepted Round 12):
   "M=3 requires S_max>=6, so M=2 is the largest compatible value" -- incorrect.
   Formula M <= S_max - S_min + 1 = 3 shows M=3 IS compatible with S_max=5.
   M=2 reclassified from "constrained choice" to "early-stop convention."
   Note (per Codex audit): the stronger incompatibility claim appears in JC debate,
   not in canonical rounds 1-6. Canonical round-5 correctly derives the formula.

3. **CA-01 false dichotomy** (caught Round 4, accepted Round 6):
   Original A/B framing forced choice between "013 owns only measurement" and "013
   owns full routing." Hybrid C resolved: 013 owns convergence-side prerequisite
   semantics, not full downstream routing.

---

## Unresolved tradeoffs (for human review)

- **Governance threshold within [tau_low, tau_high]**: Cross-topic integration
  (001x003x010x013) needed to determine the operational threshold between
  PARTIALLY_CONVERGED and FULLY_CONVERGED. Depends on cost-of-continuing (003),
  cost-of-false-stop (001's HANDOFF), and quality gates (010, 017).

- **M=2 vs M=3**: Both compatible with S_max=5. M=2 chosen as early-stop
  convention; M=3 would detect stalls more conservatively. Recalibration after
  first offline campaign may resolve this.

- **same_data_ceiling provenance**: Weakest constant in the set. Unit/archive
  mapping is not clean (V4->V8 evidence uses session units, not campaign units).
  First real offline campaign should recalibrate.

- **BH upgrade path timing**: BH activation requires Topic 017's proof-consumption
  guarantee. If 017 does not close this, BH remains unavailable indefinitely.

---

## Deferred, not blocked

All items below are DEFERRED -- they do not block Topic 013 closure. Each has a
defined owner and resolution path.

| Item | Owner | Resolution path | Blocked by |
|------|-------|----------------|------------|
| Governance threshold (where in [tau_low, tau_high] to draw the line) | 001x003x010x013 | Cross-topic integration after all 4 close | 003 (OPEN), 010 (already closed) |
| Item 3a exact numerics (robustness bundle minimum) | 013 | Resolve when 017 closes consumption framework | 017 (OPEN) |
| Item 3b consumption sufficiency | 013x017 shared | Resolve in 017 debate or 013x017 integration | 017 (OPEN) |
| Item 4 exact anomaly numerics | 013x017 shared | 017 owns per-axis values; resolve in 017 debate | 017 (OPEN) |
| BH q_FDR = 0.10 activation | 013x017 | 017 must close proof-consumption guarantee | 017 (OPEN) |
| 006 pre-bucket interaction | 006x013 | Confirm compatibility when 006 closes | 006 (OPEN) |
| M, S_max, same_data_ceiling recalibration | 013 (v2) | Recalibrate after first genuine offline campaign | Empirical evidence |

---

## Cross-topic impact

| Topic | Dependency | Impact of 013 closure |
|-------|-----------|----------------------|
| 017 (Epistemic Search Policy) | **Hard-dep on 013** | 013 closure unblocks 017. Items 3a numerics, 3b, 4 become 013x017 integration obligations within 017's debate. BH upgrade path contingent on 017. |
| 003 (Protocol Engine) | Direct (stop logic) + indirect (via 017) | Stop-law structure and defaults inform pipeline stop logic. 003 consumes convergence-state output directly. |
| 001 (Campaign Model) | Soft-dep (CLOSED) | 001 routed stop thresholds/ceiling to 013 -- now resolved. HANDOFF routing contract consumes convergence-side prerequisite semantics. |
| 008 (Architecture Identity) | Indirect | Hash granularity (item 2) compatible with 008's identity schema. No conflict. |
| 010 (Clean OOS Certification) | Soft-dep (CLOSED) | 010's `(winner exists)` predicate now has convergence-side prerequisite: FULLY_CONVERGED required. |
| 006 (Feature Engine) | Deferred interaction | 006 pre-bucket / 013 hash granularity compatibility deferred to 006 closure. |

---

## Draft impact

| Draft | Sections affected | Action needed |
|-------|------------------|---------------|
| `methodology_spec.md` | Convergence algorithm (Kendall's W, categories, prerequisite semantics) | **Create** |
| `methodology_spec.md` | Stop conditions (stop-law structure, bootstrap defaults, provenance tiers) | **Create** |
| `architecture_spec.md` | section 9 — Scan-phase correction law (Holm default, BH upgrade path) | **Update** (was stub) |
| `architecture_spec.md` | section 9 — Equivalence thresholds (rho cutoff, hash granularity) | **Update** (was stub) |
