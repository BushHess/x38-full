# X35 Phase 7 — Final Report

**Status**: FINALIZED  
**Verdict**: `STOP_WHOLE_X35_CURRENT_SCOPE`

## Central Question

Can a slower outer regime state, built only from BTC spot OHLCV, improve the frozen
`E5+EMA21D1` baseline through a low-DOF overlay?

## Final Answer

No, not within the current `x35` scope.

The program tested:

- Class A (`BLOCK_NEW_ENTRY`) through branches `a_`, `c_`, `d_`, `e_`, `f_`
- Class B (`FORCE_FLAT`) through branch `g_`

Both action classes are negative in the current scope.

## What Was Learned

### Entry Blocking (Class A)

The basic outer-state survey is complete and negative:

- pilot F1 menu failed
- residual F1 signed-distance failed
- F2 multi-horizon trend structure failed
- F3 coarse stress/drawdown failed
- F4 transition/instability failed

No branch produced an outer state with adequate separation, concentration, and
time stability to justify `entry_prevention_only`.

### Force-Flat Continuation (Class B)

The only admissible continuation after the negative entry pass was:

- does weekly instability create a usable mid-trade hazard signal?

Branch `g_mid_trade_hazard_diagnostic` answered: **no**.

- coverage only `1.6%–2.7%` of trades
- best spec still failed selectivity threshold
- some specs improved winners instead of protecting losers

This is economically too weak to justify a force-flat branch.

## Relation To Prior Repo Evidence

The negative `g_` result is consistent with prior repo constraints:

- `x31-A`: D1 flip mid-trade exit = low selectivity
- `x31-B`: re-entry oracle ceiling too low
- `x16/x23`: stateful exit and exit geometry fail robustness

So `x35` does not overturn prior evidence; it strengthens it by testing the slower
weekly/monthly outer-state angle directly.

## Final Decision

- Do not open `branches/b_entry_overlay/`
- Do not open a Class B force-flat validation branch inside current `x35`
- Close current `x35` program as negative

## Scope Of Closure

This closure applies to:

- BTC spot
- existing OHLCV only
- frozen baseline `E5+EMA21D1`
- weekly/monthly outer states
- low-DOF action classes A/B

It does **not** claim that every conceivable future research direction is closed.
It claims that the concrete `x35` program, as formalized, has now been answered.
