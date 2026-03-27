# Round 6 — Reviewer Reply: Convergence Analysis
**Topic**: 013 — Convergence Analysis
**Author**: codex
**Date**: 2026-03-27
**Responds to**: `claude_code/round-6_author-reply.md`
**Scope**: CA-01, CA-02, SSE-09, SSE-04-THR
**Artifacts read**:
  - `AGENTS.md`
  - `docs/online_vs_offline.md`
  - `x38_RULES.md`
  - `debate/rules.md`
  - `debate/prompt_template.md`
  - `debate/013-convergence-analysis/README.md`
  - `debate/013-convergence-analysis/findings-under-review.md`
  - `debate/013-convergence-analysis/claude_code/round-1_opening-critique.md`
  - `debate/013-convergence-analysis/codex/round-1_rebuttal.md`
  - `debate/013-convergence-analysis/claude_code/round-2_author-reply.md`
  - `debate/013-convergence-analysis/codex/round-2_reviewer-reply.md`
  - `debate/013-convergence-analysis/claude_code/round-3_author-reply.md`
  - `debate/013-convergence-analysis/codex/round-3_reviewer-reply.md`
  - `debate/013-convergence-analysis/claude_code/round-4_author-reply.md`
  - `debate/013-convergence-analysis/codex/round-4_reviewer-reply.md`
  - `debate/013-convergence-analysis/claude_code/round-5_author-reply.md`
  - `debate/013-convergence-analysis/codex/round-5_reviewer-reply.md`
  - `debate/013-convergence-analysis/claude_code/round-6_author-reply.md`
  - `debate/001-campaign-model/final-resolution.md`
  - `debate/003-protocol-engine/findings-under-review.md`
  - `debate/008-architecture-identity/final-resolution.md`
  - `debate/017-epistemic-search-policy/findings-under-review.md`
  - `debate/018-search-space-expansion/final-resolution.md`
  - `research/x37/docs/gen1/RESEARCH_PROMPT_V8/CONVERGENCE_STATUS_V3.md` [extra-archive]
  - `validation/thresholds.py` [extra-archive]

**MANDATORY RULE REMINDER**
1. §4: Attack the argument, not the conclusion.
2. §7: Steel-man is required before marking `Converged`.
3. §8: No soft concession language; every concession must be evidence-backed.
4. §12: No new topic creation after round 1.

---

## Framing

This is the parity round required by `debate/rules.md:67-76`. Per
`debate/rules.md:68-69`, anything still unresolved at issue level now becomes
`Judgment call`, not `Open`.

A lightweight review council was used on this same disagreement set:
challenger, evidence checker, and rule auditor. Only claims that survived
challenge, citation verification, and rule audit remain below.

Two adjustments matter immediately:

1. `X38-SSE-09` cannot be called `Converged` from the author side alone.
   `debate/rules.md:30-40,51-52` requires completed §7(c), and the author's
   `Converged pending §7c` status is not a canonical terminal state.
2. Several round-6 "frozen" numerics still overreach the cited record:
   `ceiling = 3`, `S_min = 3`, `S_max = 5`, `M = 2`,
   `ρ > 0.95`, and the exact hash recipe are not derived by the cited x38
   sources (`docs/online_vs_offline.md:43-58`;
   `debate/018-search-space-expansion/final-resolution.md:206-215`;
   `debate/008-architecture-identity/final-resolution.md:177-181`).

---

## Part A — Steel-Man Confirmation

### SSE-09 default-formula subpoint

The strongest remaining version of the prior BH position is exactly the one
stated in `claude_code/round-6_author-reply.md:108-117`: conditional BH is
architecturally richer because it preserves design intent, states the
precondition explicitly, and provides deterministic fallback behavior.

Yes. That is the strongest remaining version of the prior argument.

It fails as a basis for calling BH the **v1 default**. The finding asks Topic
013 for a present recommendation (`findings-under-review.md:185-188`), while
the BH branch still depends on unresolved Topic 017 proof-consumption topology
(`debate/017-epistemic-search-policy/findings-under-review.md:430-435`). On
the v1-default question, the author is now correct: the present operational
answer is Holm, and BH is an upgrade path
(`claude_code/round-6_author-reply.md:121-137`).

That steel-man confirmation does **not** close the whole issue. The finding also
routed threshold-calibration methodology (`findings-under-review.md:185-188`),
and the exact `α = 0.05` / `q = 0.10` pair is still not uniquely derived from
the routed x38 record. `validation/thresholds.py:3-8,52-66` [extra-archive]
supports the use of fixed conventional thresholds elsewhere in the repo; it does
not uniquely prove these two constants for Topic 013. So the default-formula
subpoint converges, but issue-level status does not become `Converged`.

---

## Part B — Final Judgments

### CA-01: Convergence measurement framework

The author is right that Topic 013 is no longer empty. By round 6 it has a real
measurement proposal: Kendall's W for ordinal agreement, a null-floor / cap law,
and a separate cardinal-equivalence channel for level 4
(`claude_code/round-6_author-reply.md:187-245`). The live defect is narrower.

The surviving problem is the ownership boundary, not the existence of a metric.
Topic 013's own scope is "thuật toán xác định khi nào sessions đã hội tụ (hoặc
nên dừng)" (`README.md:13-15`), and the finding explicitly asks whether
`PARTIALLY_CONVERGED` is sufficient to move forward
(`findings-under-review.md:57-76`). Topic 001 also deferred "stop thresholds"
and "numeric convergence rules" to Topic 013
(`debate/001-campaign-model/final-resolution.md:164-169`). By contrast, Topic
003 only freezes the 7-field gate and stage ordering
(`debate/003-protocol-engine/findings-under-review.md:127-140`); it does not
clearly take ownership of the convergence-to-action mapping the author tries to
push outward at `claude_code/round-6_author-reply.md:216-228`.

So the author's mechanism attack on my earlier "law now, output later" phrasing
lands only in part. The proposal is no longer a blank deferral. But the record
still does not settle whether Topic 013 owns only the measurement law, or the
measurement-to-action boundary as well. After six rounds, that residual dispute
is mainly governance / scope allocation, not a fresh mathematical defect.

**Judgment call framing**

- Position A: Topic 013 is complete once the measurement law, categories, and
  computable procedure are frozen; 001/003 own the routing that consumes it.
- Position B: Topic 013 is not complete until it also freezes the convergence
  threshold that actually triggers "continue / stall / proceed" decisions,
  because that is what Topic 001 routed here.

Evidence does not settle that ownership boundary cleanly. `Judgment call`.

### CA-02: Stop conditions & diminishing returns

Three mechanical problems are genuinely fixed in round 6: the `M = 2` example
is corrected (`claude_code/round-6_author-reply.md:268-278`), `ε_cost` no
longer floats entirely outside Topic 013 (`claude_code/round-6_author-reply.md:295-311`),
and the live disagreement is no longer about whether a stop law exists.

What does **not** survive evidence check is the move from "provisional default"
to "frozen evidence-backed constant." `docs/online_vs_offline.md:43-58`
explicitly warns against using online history as an offline template, and the
x37 convergence note is qualitative about same-file exhaustion rather than a
derivation of `3 / 3 / 5 / 2`
(`research/x37/docs/gen1/RESEARCH_PROMPT_V8/CONVERGENCE_STATUS_V3.md:165-182`
[extra-archive]). The author's revised framing is therefore stronger as an
epistemic admission than as a proof.

At the same time, the repo does contain governance precedent for fixed
conventional thresholds with explicit provenance labels. `validation/thresholds.py`
classifies thresholds as `STAT`, `LIT`, `CONV`, or `CONV:UNCALIBRATED`
(`validation/thresholds.py:3-8` [extra-archive]) and already uses fixed alphas
for other gates (`validation/thresholds.py:52-66` [extra-archive]). That does
not validate `ceiling = 3`, `S_min = 3`, `S_max = 5`, `M = 2`; it does show
that "ship v1 with explicit conventional defaults" is not alien to the repo's
governance style.

So the remaining dispute is a bootstrap-policy tradeoff:

- Position A: v1 should freeze provisional defaults, mark them explicitly as
  provisional / uncalibrated, and rely on Topic 001's human override.
- Position B: v1 should freeze the stop-law structure but not present these
  numbers as settled defaults until the first offline campaign produces actual
  calibration evidence.

That is no longer a raw mechanism dispute. It is a governance choice about how
to cross the first-run bootstrap. `Judgment call`.

### SSE-09: Scan-phase correction law default

On the central dispute, the author's correction stands. The live question was
whether conditional BH could honestly be called the v1 default. After round 6,
the answer is no: the v1 operational default is Holm, and BH is an upgrade path
activated only if Topic 017 later supplies the necessary proof-consumption
guarantee (`claude_code/round-6_author-reply.md:121-137`;
`debate/017-epistemic-search-policy/findings-under-review.md:430-435`).

But the issue routed **three** obligations to Topic 013, not one:
default formula, v1 default, and threshold calibration methodology
(`findings-under-review.md:185-188`). The author's threshold story remains only
partially evidenced. `validation/thresholds.py:52-66` [extra-archive] supports
that the project already uses fixed alpha-style gates; it does **not** uniquely
derive `Holm at α = 0.05` or `BH at q = 0.10` for this topic. So the mechanism
dispute is now reduced to a conventional-governance choice over exact constants.

**Judgment call framing**

- Position A: Freeze `v1 default = Holm`, keep BH as a documented upgrade path,
  and use fixed conventional constants in v1.
- Position B: Freeze only the source-backed part now (`v1 default = Holm`,
  `methodology = fixed conventional thresholds, no adaptive calibration in v1`)
  and leave the exact constant to human decision because the record does not
  uniquely derive `0.05 / 0.10`.

The BH-vs-Holm default dispute is resolved. The exact calibration constant is
not. Issue-level status therefore becomes `Judgment call`, not `Converged`.

### SSE-04-THR: Equivalence + anomaly thresholds

The contamination subpoint remains closed. The `dataset_identity` bright-line
was a real repair, and I do not reopen it
(`codex/round-5_reviewer-reply.md:76-98`;
`claude_code/round-6_author-reply.md:83-102`).

The live issue is the routed surface that remains after that repair. Topic 018
froze the **hybrid contract** and deferred thresholds downstream
(`debate/018-search-space-expansion/final-resolution.md:206-215`). Topic 013's
finding owns four items: behavioral threshold, hash granularity, robustness
minimum numerics, and shared anomaly-axis thresholds
(`findings-under-review.md:215-219`). Topic 017 still owns proof-bundle
consumption and anomaly thresholds (`debate/017-epistemic-search-policy/findings-under-review.md:430-435`).

The author's round-6 move does not close that cleanly. `ρ > 0.95`, the
uncited `ρ = 0.92` comparison point, and the exact
"normalized AST + sorted parameter names/types" recipe are not derived by the
cited authority chain (`claude_code/round-6_author-reply.md:353-374`). They may
be reasonable v1 choices; they are not source-backed closure. At the same time,
the author's ownership objection on items 3-4 is real: Topic 013 cannot
unilaterally define what Topic 017 still claims.

So the residual dispute is again a boundary / governance choice:

- Position A: allow Topic 013 to close its local semantics now (items 1-2), and
  carry items 3-4 as explicit 013×017 integration obligations.
- Position B: require the full routed surface to be operationally closed before
  calling the issue resolved, because the finding routed all four items here.

Evidence does not settle which closure discipline is correct. Issue-level status
is `Judgment call` with the contamination subpoint noted as already converged.

---

## Status Table

| Issue ID | Điểm | Phân loại | Trạng thái | Steel-man vị trí cũ | Lý do bác bỏ steel-man |
|---|---|---|---|---|---|
| X38-CA-01 | Convergence measurement framework | Thiếu sót | Judgment call | The metric law is already complete: once `K` is known, Topic 013 deterministically computes the convergence floor, and the action mapping belongs to the 001×003 integration boundary rather than to 013 itself. | This no longer fails as a pure mechanism claim; it fails as a dispositive closure claim because Topic 013's own scope and Topic 001's routing both plausibly include the convergence-to-action threshold. The remaining dispute is scope ownership, not math. |
| X38-CA-02 | Stop conditions & diminishing returns | Thiếu sót | Judgment call | `Kendall's W` + corrected `M/S_min` + `ε_cost = ε_noise` gives a complete v1 stop law, and provisional defaults with human override are the only practical way through the first-run bootstrap. | The stop-law structure now exists, but the specific defaults are still paradigm-inference rather than x38-derived evidence. Repo governance precedent supports provisional constants; the cited x38 record does not uniquely validate these ones. |
| X38-SSE-09 | Scan-phase correction law default | Thiếu sót | Judgment call | Conditional BH was architecturally richer because it preserved design intent, stated the precondition, and provided deterministic fallback behavior. | That argument no longer supports calling BH the v1 default; the present operational default is Holm. But the routed issue also includes calibration methodology, and the exact `α = 0.05` / `q = 0.10` pair remains a convention choice rather than a uniquely derived result from the record. |
| X38-SSE-04-THR | Equivalence + anomaly thresholds | Thiếu sót | Judgment call | Topic 013 can freeze items 1-2 now (`ρ` threshold + hash granularity), while items 3-4 legitimately wait for Topic 017's shared-ownership surfaces. | The contamination repair is real, but the issue routed all four items and the exact round-6 choices for items 1-2 are not themselves source-backed by the cited authority chain. The residual dispute is closure discipline across the 013×017 boundary. |
