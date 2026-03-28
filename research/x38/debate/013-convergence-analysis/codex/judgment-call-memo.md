# Judgment-Call Memo — Topic 013 Closure Audit

**Topic**: `013-convergence-analysis`  
**Date**: 2026-03-28  
**Audited artifact**: `debate/013-convergence-analysis/judgment-call-decisions.md`  
**Audit basis**: canonical 6-round 2-agent debate in `debate/013-convergence-analysis/{claude_code,codex}/`, plus `findings-under-review.md`, `README.md`, `debate/018-search-space-expansion/final-resolution.md`, `debate/017-epistemic-search-policy/findings-under-review.md`, `debate/003-protocol-engine/findings-under-review.md`, `debate/008-architecture-identity/findings-under-review.md`, `debate/001-campaign-model/final-resolution.md`, `debate/010-clean-oos-certification/final-resolution.md`.

This memo audits the ratified judgment-call file against the canonical round record. It does **not** re-decide the issues. Bottom line: the ratified positions are broadly consistent with the direction of the canonical debate, but four cleanup items remain before treating `judgment-call-decisions.md` as a citation-clean closure input:

1. CA-01's asset-agnostic citation points to SSE-04-THR anomaly-threshold text, not to CA-01/Kendall's W.
2. `validation/thresholds.py` is cited as if local to `research/x38/`; the real file is `/var/www/trading-bots/btc-spot-dev/validation/thresholds.py` and should be treated as `[extra-archive]`.
3. SSE-04-THR's `006` taxonomy interaction was listed as an open question in the canonical finding and is neither answered nor explicitly deferred in the ratified file.
4. `judgment-call-decisions.md` internally says SSE-04-THR item 4 is fully deferred in the summary table, but the body/matrix freeze item-4 methodology and defer only exact numerics.

## 1. Decision Audit

| Issue ID | Decision audit | Evidence check | Material gaps |
|---|---|---|---|
| `X38-CA-01` | **Mostly accurate.** Canonical rounds end with a real ownership-boundary judgment call: by round 6 both sides accept that Topic 013 now has a real measurement proposal, while disagreeing about whether 013 owns only measurement/categories or also the convergence-to-action threshold (`codex/round-6_reviewer-reply.md:97-130`). The ratified Hybrid C is a reasonable narrowing of that dispute. | Cross-topic citations to Topic 001, Topic 010, the 013 README, and F-30 match the claims. The **asset-agnostic pointer is wrong**: `claude_code/round-1_opening-critique.md:448` and `claude_code/round-2_author-reply.md:516-530` discuss **anomaly thresholds**, not CA-01/Kendall's W. | The ratified phrase "`convergence-side prerequisite semantics`" is a JC refinement, not an explicit canonical round-6 freeze. Rejected Position B is written broader than the actual round-6 reviewer position, which was "013 must also freeze the threshold for continue/stall/proceed," not "013 owns the full routing matrix." |
| `X38-CA-02` | **Accurate on trajectory.** Canonical round 6 clearly reduces the issue to a bootstrap-policy judgment call: ship provisional defaults with explicit provenance, or freeze only the stop-law structure and wait for offline calibration (`codex/round-6_reviewer-reply.md:132-167`). The ratified acceptance of bootstrap defaults with per-constant provenance matches that trajectory. | `findings-under-review.md:81-140`, `docs/online_vs_offline.md:43-58`, `debate/001-campaign-model/final-resolution.md:164-169`, `claude_code/round-5_author-reply.md:283-289`, and `claude_code/round-6_author-reply.md:266-311` all support the stop-law/provisional-default story. The governance-precedent citation is real, but the path in the ratified file is wrong: the source is `/var/www/trading-bots/btc-spot-dev/validation/thresholds.py:3-8`, not `validation/thresholds.py` under x38. | The 5-tier provenance model is a JC synthesis rather than canonical round language. No material canonical position was dropped, but the ratified file should keep signaling that the exact constants are **conventional/provisional**, not canonically derived. |
| `X38-SSE-09` | **Accurate on the main dispute.** Canonical round 6 resolves the formula/default question to: operational v1 default = Holm; BH = upgrade path contingent on Topic 017 proof-consumption closure (`codex/round-6_reviewer-reply.md:168-195`). The ratified file reflects that correctly. | The cell-elite ordering claim is supported by `claude_code/round-1_opening-critique.md:326-341` and `claude_code/round-3_author-reply.md:271-283`. The routed-ownership pointer to `findings-under-review.md:185-188` is correct. Again, the repo-governance citation should point to `/var/www/trading-bots/btc-spot-dev/validation/thresholds.py:3-8,52-66` and be marked `[extra-archive]`. | Canonical rounds support **Holm as the v1 default formula**, but they do **not** uniquely derive `α_FWER = 0.05` and `q_FDR = 0.10`; those remain conventional JC constants. The ratified file says this in substance, so no material debate position is lost. |
| `X38-SSE-04-THR` | **Partly accurate, but this is the least cleanly audited section.** Canonical round 6 does support a mixed boundary dispute: freeze local semantics now (items 1-2) vs require full routed-surface closure before resolving the issue (`codex/round-6_reviewer-reply.md:197-228`). The ratified mixed position follows that direction. | Ownership/dependency citations to `findings-under-review.md:215-219`, `debate/017-epistemic-search-policy/findings-under-review.md:430-435`, `debate/018-search-space-expansion/final-resolution.md:125-176,206-215`, and `debate/018-search-space-expansion/closure-audit.md:1-4` are valid. But the exact `ρ > 0.95` cutoff and exact hash recipe were **not canonically source-backed**; round 6 reviewer explicitly says so (`codex/round-6_reviewer-reply.md:212-218`). | Two real gaps remain. First, the ratified file does not separately steel-man the rejected full-surface-closure alternative. Second, the open question "How does the structural pre-bucket interact with 006's feature family taxonomy?" from `findings-under-review.md:227` is neither answered nor explicitly deferred. |

## 2. Corrections Log Audit

### (a) `ρ > 0.95` pseudo-derivation

**Verdict**: Correction valid.

Canonical origin is `claude_code/round-6_author-reply.md:353-362`, which states:

- `ρ > 0.95` for v1
- "`ρ > 0.95` implies < 5% independent variance"
- the cutoff sits above an uncited `ρ = 0.92` comparison point

That variance rationale is mathematically wrong if interpreted as `1 - ρ^2`: `1 - 0.95^2 = 0.0975`, i.e. about `9.75%`, not `<5%`. The ratified file correctly removes the pseudo-derivation and reclassifies the cutoff as a conventional v1 choice.

### (b) `M = 2` provenance / "`M = 3` incompatible with `S_max = 5`"

**Verdict**: Substance correct, attribution imprecise.

What the canonical record actually shows:

- `claude_code/round-5_author-reply.md:283-289` explicitly derives `M ≤ S_max - S_min + 1`, with example `S_max = 5`, `S_min = 3` giving `M ≤ 3`.
- The same file then gives a **different mechanical error** at `claude_code/round-5_author-reply.md:315-318`, claiming `M = 2` can fire after sessions 2 and 3.
- That example is corrected in `claude_code/round-6_author-reply.md:268-278`.

I do **not** find the exact claim "`M = 3` requires `S_max ≥ 6`" anywhere in the canonical round-1 to round-6 record. That stronger incompatibility claim appears in the later JC debate, not in the canonical 6-round debate. So:

- the correction "`M = 3` is compatible with `S_max = 5`" is right;
- the ratified corrections log overstates its canonical provenance.

### (c) CA-01 false dichotomy (A/B -> Hybrid C)

**Verdict**: Correction valid in substance.

Canonical round 6 reduces CA-01 to a two-way ownership dispute:

- Position A: 013 is complete once measurement law/categories/procedure are frozen; 001/003 own routing (`codex/round-6_reviewer-reply.md:122-126`)
- Position B: 013 is not complete until it also freezes the threshold that triggers continue/stall/proceed decisions (`codex/round-6_reviewer-reply.md:126-130`)

The ratified Hybrid C is a reasonable correction to that over-binary framing: Topic 013 cannot own **nothing but measurement**, because F-30 explicitly asks what `PARTIALLY_CONVERGED` means for forward movement (`findings-under-review.md:72-76`), but canonical rounds also do not justify pushing the full routing matrix into 013.

### Additional errors not listed in the corrections log

1. **CA-01 asset-agnostic citation error**: the cited lines are from SSE-04-THR anomaly-threshold discussion, not CA-01/Kendall's W.
2. **Repo-root source pointer error**: `validation/thresholds.py` is cited with an x38-local path and without `[extra-archive]`.
3. **SSE-04-THR internal summary drift**: decision table row 43 says item 4 is deferred wholesale, but the body and ownership matrix freeze methodology and defer only exact numerics.

## 3. Ownership Matrix Audit

The ownership matrix contains **26 rows**, and the count checks out (`judgment-call-decisions.md:361-386`).

Most ownership rows are supported by one of three surfaces:

- 013's own routed scope in `findings-under-review.md:215-219`
- 017's consumption ownership in `debate/017-epistemic-search-policy/findings-under-review.md:430-435`
- 018's routed handoff in `debate/018-search-space-expansion/final-resolution.md:125-176,206-215`

Rows needing qualification:

| Matrix item | Audit |
|---|---|
| `Asset-agnostic property (Kendall's W + percentile thresholds)` | Not cleanly supported. The cited canonical lines are about anomaly-threshold methodology, not the CA-01 convergence metric. The row also conflates CA-01 ordinal convergence with SSE-04-THR percentile logic. |
| `Hash granularity (design-contract)` | Supported only at a high level. Canonical rounds support "013 owns hash granularity semantics" and a disputed normalized-AST recipe, but the specific invariance surface "`whitespace/comments/import order`" is JC-added detail, not explicit canonical source text. |
| `Item 4 (anomaly thresholds methodology)` | Supported directionally: round 1 proposes relative thresholds, round 2 corrects to hybrid relative/absolute with sparsity guard (`claude_code/round-2_author-reply.md:513-540`), and no later canonical round reopens that directional methodology. |

Missing ownership note:

- No matrix row captures the open `006` interaction that the original finding raised at `findings-under-review.md:227`. If the ratified file intends that interaction to be deferred or superseded by 017's mechanism taxonomy, it should say so explicitly.

## 4. Cross-Topic Impact Check

### Topic 017 (epistemic search policy)

**Audit**: Yes, CA-01 and CA-02 materially affect 017.

- 013's own README records the overlap directly: coverage metrics overlap CA-01, and 017's budget governor interacts with CA-02 stop conditions (`README.md:44-48`).
- 017's finding makes the same dependency explicit, especially at `debate/017-epistemic-search-policy/findings-under-review.md:316-317,358-359`.
- Canonical debate corrected the stronger early idea that 017 has a stop veto; by rounds 3-6 the cleaner boundary is: 013 owns convergence/stop signals, 017 owns coverage obligations and may extend campaigns when coverage floors are not met.

The ratified file captures this correctly enough.

### Topic 003 (protocol engine)

**Audit**: Yes, 013 affects 003 directly, not merely indirectly.

- `debate/013-convergence-analysis/README.md:30-31` already marks 003 as downstream of 013.
- `debate/003-protocol-engine/findings-under-review.md:135-140` shows 003 consuming routed field-5 obligations and stage ordering around the scan/correction interface.

The ratified cross-topic table understates this by calling 003 "`Indirect via 017`" while also saying 003 consumes convergence-state output. The dependency is direct on stop logic / convergence outputs, even if some stage-shape details also depend on 017.

### Topic 008 (architecture identity)

**Audit**: Yes, SSE-04-THR must remain compatible with SSE-04-IDV.

- 008 froze the split: 008 owns interface + structural pre-bucket fields; 013 owns equivalence semantics; 017 owns consumption (`debate/008-architecture-identity/final-resolution.md:129-165`).
- 018's 7-field contract keeps `identity_vocabulary` and `equivalence_method` distinct (`debate/018-search-space-expansion/final-resolution.md:86-99,206-215`).

No contradiction found. The ratified file is directionally correct here.

## 5. Status Drift Check

`findings-under-review.md` still shows all four issues as `Open`, but canonical round parity and the ratified JC file have already moved the topic past that state.

| Issue ID | `findings-under-review.md` | Canonical round-6 parity state | `judgment-call-decisions.md` | Audit |
|---|---|---|---|---|
| `X38-CA-01` | `Open` (`findings-under-review.md:23`) | `Judgment call` (`codex/round-6_reviewer-reply.md:236`) | `Judgment call` (`judgment-call-decisions.md:40`) | Drift |
| `X38-CA-02` | `Open` (`findings-under-review.md:87`) | `Judgment call` (`codex/round-6_reviewer-reply.md:237`) | `Judgment call` (`judgment-call-decisions.md:41`) | Drift |
| `X38-SSE-09` | `Open` (`findings-under-review.md:177`) | `Judgment call` (`codex/round-6_reviewer-reply.md:238`) | `Judgment call` (`judgment-call-decisions.md:42`) | Drift |
| `X38-SSE-04-THR` | `Open` (`findings-under-review.md:208`) | `Judgment call` with contamination subpoint converged (`codex/round-6_reviewer-reply.md:239`) | `Judgment call` (`judgment-call-decisions.md:43`) | Drift |

This is expected pre-closure drift, but it still needs explicit Step-2 synchronization before the topic is treated as closed.

## 6. Open Questions Coverage

The prompt says "13 open questions," but the source file actually enumerates **14** subquestions: `4 + 4 + 3 + 3` (`findings-under-review.md:72-77,135-139,195-198,225-228`).

| Question | Covered in `judgment-call-decisions.md`? | Audit note |
|---|---|---|
| CA-01 granularity | Yes | Answered via two-mechanism architecture + multi-level categories. |
| CA-01 distance metric | Yes | Answered as ordinal agreement via Kendall's W, cardinal equivalence via SSE-04-THR. |
| CA-01 `PARTIALLY` vs `FULLY` | Yes | Answered, but the stronger "`convergence-side prerequisite semantics`" wording is a JC refinement beyond explicit canonical freeze. |
| CA-01 asset-agnostic | Claimed yes | Coverage exists in the ratified file, but the cited evidence is wrong and the support is weaker than presented. |
| CA-02 sessions per campaign | Yes | Answered as `S_min = 3`, `S_max = 5` provisional defaults. |
| CA-02 same-data campaign ceiling | Yes | Answered as `same_data_ceiling = 3`, explicitly weak/provisional. |
| CA-02 `ε` threshold | Yes | Answered as `max(ε_noise, ε_cost)` with v1 default `ε_cost = ε_noise`. |
| CA-02 ceiling breach authority | Yes | Answered as human-overridable per Topic 001 governance. |
| SSE-09 Holm vs BH vs cascade | Yes | Answered: Holm v1 default, BH upgrade path, cascade not the governing default choice. |
| SSE-09 conservative vs balanced | Yes | Answered in favor of conservative v1 default. |
| SSE-09 cell-elite interaction | Yes | Answered: correction precedes diversity preservation. |
| SSE-04-THR `ρ` cutoff | Yes | Answered as `ρ > 0.95`, explicitly conventional. |
| SSE-04-THR interaction with Topic 006 taxonomy | **No** | This question appears in the canonical finding (`findings-under-review.md:227`) and is not answered or explicitly deferred in the ratified file. |
| SSE-04-THR absolute vs relative thresholds | Yes, partially deferred | Answered directionally as hybrid relative/absolute with sparsity guard; exact numerics remain deferred. |

## Conclusion

The ratified file is usable as a closure-input artifact **if** it is read as a human-ratified JC synthesis rather than as a pure restatement of canonical round-6 convergence. The main audit risk is not wrong final direction; it is citation hygiene and boundary hygiene:

- fix the CA-01 asset-agnostic citation,
- fix the repo-root `validation/thresholds.py` citation style,
- reconcile the SSE-04-THR item-4 summary/body mismatch,
- and explicitly answer or defer the missing Topic 006 interaction.

No ratified decision needs to be overturned on this audit. The needed repairs are documentary, provenance, and status-sync repairs.
