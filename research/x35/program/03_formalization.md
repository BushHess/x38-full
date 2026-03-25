# X35 Phase 3 — Formalization

**Status**: DONE  
**Protocol**: Derive the admissible research space from first principles before freezing candidates.

---

## 1. Decision Problem

Let `t` index H4 bars where the frozen baseline system `E5+EMA21D1` could act.

Define:

- `E_t`: baseline entry event at bar `t`
- `Q_t`: latent trade quality of baseline if entry is taken at `t`
- `S_t`: slow outer state observable causally at `t`
- `A_t`: outer overlay action chosen at `t`

The research question is not “is a weekly EMA useful?” but:

> Can a causal slow state `S_t` improve expected utility by changing the action `A_t`
> of the baseline engine?

## 2. Action Space

The earlier phrase “mode nào” refers to the **action space**, not to a proven plan.

Admissible action classes, in order of intervention cost:

### Class A — Entry Permission

`A_t ∈ {ALLOW, BLOCK_NEW_ENTRY}`

- lowest intervention;
- easiest to validate;
- first candidate class if evidence only concerns entry quality.

### Class B — Risk-Off Flat

`A_t ∈ {ALLOW, BLOCK_NEW_ENTRY, FORCE_FLAT}`

- admissible only if evidence shows the slow state affects **mid-trade hazard**, not just entry quality;
- higher risk of repeating prior exit-geometry failures.

### Class C — Exposure Mode

`A_t ∈ {OFF, DEFENSIVE, NORMAL}`

- admissible only after Classes A/B show real state dependence;
- not allowed in the first validation pass.

Therefore:

- “mode nào” is a **theoretical action space**;
- `entry_prevention_only` is the **first concrete validation class**, chosen because it is the least assumption-heavy.

## 3. Information Families

`S_t` may only be built from BTC spot OHLCV already in repo. Admissible slow-state families:

### Family F1 — Price-Level State

Questions:

- Is price structurally above or below a slow anchor?
- Is the distance to that anchor informative about hostile vs favorable regime?

### Family F2 — Multi-Horizon Trend State

Questions:

- Are slow horizons aligned or in disagreement?
- Do transition zones between aligned and non-aligned states concentrate bad E5 entries?

### Family F3 — Stress / Drawdown State

Questions:

- After large multi-week drawdowns or volatility shocks, does baseline quality degrade enough to justify turning E5 off?

### Family F4 — Transition / Instability State

Questions:

- Are frequent slow-state flips themselves a hostile environment?
- Does regime ambiguity, not absolute bull/bear direction, explain low-quality entries?

## 4. What Counts as Evidence

For a slow state to matter, it must do at least one of the following:

1. Separate baseline entry utility:
   - `E[Q_t | S_t = favorable]` materially exceeds `E[Q_t | S_t = hostile]`
2. Concentrate damage:
   - left-tail losses cluster in one state
3. Change mid-trade hazard:
   - trades entered in one state or crossing into one state deteriorate materially faster

If none of these are true, no overlay should be designed.

## 5. Admissible Candidate Design Rules

These rules exist to stop `x35` from degenerating into another tuning exercise:

- maximum 3 candidate overlays in any design pass;
- maximum 2 new free parameters per candidate beyond the frozen baseline;
- candidate must come from a previously observed phenomenon, not from arbitrary search;
- direct slow-daily substitution is inadmissible as a “longer-horizon regime breakthrough”.

## 6. Interpretation of the Pilot Branch

`a_state_diagnostic` tested one narrow subset of **Family F1**:

- weekly/monthly close-vs-EMA and EMA-cross states.

That branch was a valid pilot probe, but it was **not** a complete test of the formalized
research space above.

Correct inference at that stage:

- current heuristic menu is weak;
- broader first-principles space remained open and required survey of the other families.
