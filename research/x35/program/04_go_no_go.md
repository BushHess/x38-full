# X35 Phase 4 — Go / No-Go Logic

**Status**: DONE  
**Purpose**: Define when x35 may advance from survey to candidate design.

---

## 1. Go / No-Go Units

`x35` has two levels of go/no-go:

1. **Menu-level**: a specific heuristic menu or state family fails.
2. **Program-level**: the broader longer-horizon regime hypothesis is no longer worth pursuing inside BTC spot OHLCV.

These two levels must not be conflated.

## 2. Menu-Level No-Go

A specific probe is `NO_GO_CURRENT_MENU` if:

- it fails to separate favorable vs hostile state utility;
- it does not concentrate left-tail damage;
- or it is not stable across time.

This is exactly the current status of branch `a_state_diagnostic`.

## 3. Program-Level Go to Design

`x35` may open a candidate design branch only if at least one state family shows:

- adequate persistence and support;
- directional separation of baseline trade utility OR left-tail concentration;
- acceptable time stability;
- an effect large enough to justify low-DOF action.

## 4. Program-Level Stop

`x35` should only stop at the program level if:

1. at least 2 distinct state families are examined, not just one heuristic menu;
2. both entry-quality and mid-trade-hazard angles are checked where applicable;
3. all admissible low-DOF action classes collapse into:
   - MDD-only tradeoff,
   - unstable time segmentation,
   - or economically negligible deltas.

That bar is now met for the current scope.

## 5. Current Status

Current correct status is:

- `PROGRAM_COMPLETE`
- `NO_GO_CURRENT_MENU`
- `NO_GO_STRESS_FAMILY`
- `NO_GO_F2_TREND_FAMILY`
- `NO_GO_F4_TRANSITION_FAMILY`
- `NO_GO_F1_PRICE_LEVEL_FAMILY`
- `NO_BASIC_ENTRY_STATE_SIGNAL`
- `NO_GO_MID_TRADE_HAZARD_FAMILY`
- `STOP_WHOLE_X35_CURRENT_SCOPE`

Not:

- `OPEN_CANDIDATE_DESIGN`

## 6. Practical Consequence

At the current state of evidence:

- `b_entry_overlay` should remain closed;
- entry-prevention-only is negative inside BTC spot OHLCV;
- the newly formalized mid-trade-hazard continuation is also negative;
- therefore current `x35` should close without candidate design or validation.
