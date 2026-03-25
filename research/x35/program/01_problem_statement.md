# X35 Phase 1 — Problem Statement

**Status**: DONE  
**Protocol**: First-principles definition before candidate design.

---

## 1. What This Is, and What It Is Not

`Longer-horizon regime research` was originally a **research direction**, not a concrete
validated plan. It pointed to a possibility:

> There may exist a slower market-state layer, orthogonal to H4 entry timing, that changes
> whether the E5 engine should be active at all.

`x35` exists to turn that possibility into a falsifiable research program.

This study is **not**:

- a tweak of `D1 EMA21` strength;
- a direct replacement by `EMA63d/126d/200d`;
- an exit-modification branch;
- a perp/on-chain/data-expansion branch.

## 2. Concrete Research Question

For BTC spot OHLCV only:

> Does there exist a slow outer market state, observable causally from weekly/monthly or
> multi-week price structure, such that the expected utility of E5 entries and/or E5 being
> active differs materially across states?

This breaks into two sub-questions:

1. **State existence**: Is there a slow state with real explanatory power over baseline trade quality?
2. **Actionability**: If yes, is that power strong enough to support a low-DOF overlay without repeating the MDD-only tradeoff of slow daily filters?

## 3. Why This Question Is Reasonable

Prior repo evidence already says:

- entry-time microstructure is exhausted;
- direct slow daily replacements mostly buy MDD at the expense of returns;
- the next marginal information, if it exists inside spot OHLCV, is more likely to live in
  a slower outer state than in another H4 entry tweak.

What is **not** yet established is whether that outer state is:

- real;
- causally usable;
- economically large enough.

## 4. Success Condition

`x35` succeeds only if it produces a state/action pair that is:

- causally defined;
- low-DOF;
- stable across time;
- economically material after cost;
- not reducible to “just use a slower daily EMA”.

If the research only finds:

- better MDD but not Sharpe;
- slight Sharpe gain with severe CAGR loss;
- a state that works only for one frozen menu;

then the correct outcome is a negative verdict, not a forced design.
