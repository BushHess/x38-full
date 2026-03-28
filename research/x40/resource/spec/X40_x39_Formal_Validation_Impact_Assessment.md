# X40 / x39 Formal-Validation Impact Assessment

## Executive verdict

Yes — **targeted changes are needed** to `X40_Baseline_Forge_Durability_Residual_Spec_v3.md` and the downstream operational docs.

No — **a wholesale redesign is not needed**.

The correct response is:
1. keep the x40 baseline-forge architecture,
2. keep `OH0_D1_TREND40` and `PF0_E5_EMA21D1` as the two official league baselines,
3. add a **tracked public-flow challenger lane** for the new x39 finding,
4. add an explicit **low-power HOLD escalation route** to Tier 3 pair review / shadow decision,
5. update the x39 residual playbook so it does **not** keep assuming “entry-side is basically exhausted” before the new challenger is adjudicated.

---

## What the repo now supports clearly

The current x39 repo state supports all of the following:

- x39 ran **52 experiments in 17 categories** around the E5 baseline.
- x39 formal validation was added on **2026-03-28** for the **vol compression gate**.
- In that formal validation, both `thr=0.6` and `thr=0.7` end in **HOLD / INCONCLUSIVE** rather than promotion.
- The formal-validation summary says:
  - `thr=0.6`: Sharpe **1.594**, 6/7 gates, WFO Wilcoxon p **0.273**
  - `thr=0.7`: Sharpe **1.571**, 6/7 gates, WFO Wilcoxon p **0.191**
  - DSR passes
  - the earlier MDD concern is resolved under the formal engine
  - the **recommended threshold is 0.7**, not 0.6.
- x39 also contains an important caution flag: in the mechanism-robustness study, vol compression is labeled **mechanism fragile** because the alternative compression measures fail selectivity.

---

## What is reasonable but still subjective / overclaimed

The AI-coder conclusion overreaches in four places:

### 1) “WFO is the bottleneck, not the algorithm.”
This is **partly true but too strong**.

WFO is clearly the blocking soft gate in the formal pipeline. But the repo also contains a separate caution flag from `exp50`: the compression mechanism is **feature-specific / fragile**, not broadly confirmed by multiple nearby formulations. That means the bottleneck is **not only power**; there is also a legitimate robustness concern.

### 2) “52 experiments mapped the improvement space exhaustively.”
This is **not demonstrated** by the repo.

The repo shows a curated 52-experiment campaign, not a proof of exhaustive search over the public-flow or OHLCV design space.

### 3) “This is the best possible OHLCV algorithm.”
This is **not supported**.

The new challenger is not even OHLCV-only in the first place, because E5 uses `taker_buy_base_vol` for VDO.

### 4) “Tier 3 should simply override HOLD and deploy.”
This is **too casual**.

The repo does allow Tier 3 human deployment decisions when Tier 2 is underresolved, but it does **not** justify skipping structured pair review, explicit reasoning, or shadow/defer options.

---

## Required changes to x40 v3

### Change 1 — Add a tracked challenger lane
Do **not** force the new x39 result into the baseline namespace immediately.

Add a tracked public-flow challenger, e.g.:
- `PF1_E5_VC07` = E5 + vol-compression gate, primary threshold `0.7`
- `PF1_shadow_vc06` = sensitivity/shadow reference only

Rationale:
- the formal validation summary itself recommends `0.7`
- the candidate is stronger than a raw x39 idea
- but it is still **HOLD / INCONCLUSIVE**, so it should not replace `PF0` automatically.

### Change 2 — Add challenger statuses separate from baseline states
Current v3 has strong baseline states (`B0/B1/B2/B_FAIL`) but no clean home for a formally validated challenger.

Add a small challenger namespace, e.g.:
- `C0_TRACKED`
- `C1_CANONICAL_REPLAYED`
- `C2_FORMAL_HOLD`
- `C3_READY_FOR_BASELINE_REVIEW`
- `C_FAIL`

This avoids incorrectly pretending that a strong but unresolved challenger is already a qualified baseline.

### Change 3 — Add low-power HOLD escalation
x40 v3 should explicitly recognize this path:

If a challenger:
- has no hard failures,
- improves the incumbent on canonical metrics,
- passes DSR / reproduction / implementation gates,
- remains `HOLD` only because the decisive soft gate is underpowered,

then x40 must emit a **pair-review / shadow-decision packet** instead of just leaving it in generic limbo.

This is already aligned with the repo’s Tier-3 workflow; x40 should formalize the handoff.

### Change 4 — x39 integration must distinguish two classes of x39 output
v3 currently treats x39 mainly as a simplified-replay ideation lab. That is still correct for most x39 outputs, but it is now incomplete.

x40 should explicitly distinguish:
- **Class A:** simplified x39 diagnostics → not authoritative
- **Class B:** x39 packages that already include canonical-engine formal validation → eligible for tracked-challenger intake

### Change 5 — Pause new generic PUBLIC_FLOW residual sprints until PF1 adjudication closes
The current docs bias toward “exit-first” for the next x39 sprint.

That was reasonable before the new formal-validation result. It is now too aggressive.

New rule:
- in `PUBLIC_FLOW`, if a tracked challenger like `PF1_E5_VC07` exists,
- **do not** open a fresh generic residual sprint in the same lane
- until challenger adjudication is closed.

After adjudication, the old exit-first bias may still be appropriate — but not before.

### Change 6 — A04 must stop over-reading unconditional entry nulls
A04 and downstream docs should add a caveat:

> unconditional entry-residual nulls do **not** fully rule out conditional entry mechanisms inside an existing strategy context.

That is exactly what the compression result claims to have shown.

### Change 7 — Keep A01/A02/A03/A05/A07 intact
Do **not** weaken these studies just because x39 found a promising challenger.

The new result is about:
- candidate intake,
- challenger adjudication,
- low-power escalation,

not about removing the need for:
- decay audit,
- half-life compression audit,
- crowding audit,
- canary drift,
- league-pivot logic.

### Change 8 — Keep OH0 and PF0 as official baselines
Do **not** replace the official baseline pair.

`OH0` remains the `OHLCV_ONLY` control baseline.
`PF0` remains the official `PUBLIC_FLOW` incumbent.

The new object is a **challenger to PF0**, not a new official baseline by default.

---

## Required changes to the operational docs

### 1. Master runbook
Add a new step after baseline qualification:
- `R4.5 — tracked challenger adjudication`

If `PF1_E5_VC07` exists, the first-cycle output cannot jump directly to a generic x39 sprint. It must first decide:
- promote to tracked challenger,
- escalate to pair review / shadow,
- reject,
- or defer pending appended evidence.

### 2. First-cycle checklist
Add checklist items for:
- `research/x40/challengers/PF1_E5_VC07/source_reference.md`
- canonical result pack import
- comparison against `PF0`
- pair-review packet generation if status = `C2_FORMAL_HOLD`

### 3. Decision tree
Add a new highest-precedence branch:
- `ADJUDICATE_TRACKED_CHALLENGER`

Precedence should become:
1. hard failure / broken / severe decay
2. **tracked challenger awaiting adjudication**
3. pivot need
4. exit-vs-entry attribution
5. league selection
6. x37 escalation

### 4. x39 residual sprint playbook
Change the default guidance from:
- “first sprint should prioritize exit-focused”

to:
- “if no tracked PUBLIC_FLOW challenger is awaiting adjudication, default to exit-focused”
- “if `PF1_E5_VC07` is pending, adjudicate it first”

### 5. Monthly / quarterly operations manual
Add a monitored challenger cadence:
- `PF1_E5_VC07`: monthly while unresolved

### 6. Artifacts & templates
Add:
- challenger manifest template
- pair-review packet template
- challenger adjudication summary template

---

## Changes that should NOT be made

### Do not change 1 — Do not rewrite x40 around the claim that x39 is “exhaustive”
That claim is not established.

### Do not change 2 — Do not declare WFO obsolete
The formal validation summary still uses WFO as the decisive soft gate; the right response is a low-power escalation route, not deleting the gate.

### Do not change 3 — Do not accept `thr=0.6` as the official default just because it has the highest Sharpe
The repo’s own formal summary recommends `0.7` for stability / worst-window reasons.

### Do not change 4 — Do not convert `PF1` into the official baseline automatically
The machine verdict is still HOLD / INCONCLUSIVE.

### Do not change 5 — Do not drop the richer-data pivot idea
If the public-flow league later shows sustained decay / crowding, A07 must still be free to recommend a league pivot.

---

## Bottom line

The new x39 result **does matter**.

It means v3 and the current docs are now **missing a formal challenger-adjudication lane**.

But it does **not** invalidate the whole x40 architecture.

The right update is:
- keep the baseline-forge design,
- add a tracked challenger workflow,
- add low-power HOLD escalation to Tier 3 pair review,
- and temporarily suspend generic PUBLIC_FLOW residual ideation until the new challenger is adjudicated.
