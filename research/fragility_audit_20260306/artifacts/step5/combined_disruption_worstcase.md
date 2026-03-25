# Combined Disruptions: Sharpe Impact

**File**: `combined_disruption_worstcase.png`

Bar chart showing delta Sharpe for each combined disruption scenario across 5 candidates.

Scenarios tested:
- baseline (0,0,0): no disruption
- entry_only_D2 (2,0,0): entry delay 2 bars only
- exit_only_D2 (0,2,0): exit delay 2 bars only
- entry_D2_exit_D1 (2,1,0): entry D2 + exit D1
- entry_D2_exit_D2 (2,2,0): entry D2 + exit D2
- entry_D4_exit_D2 (4,2,0): entry D4 + exit D2 (extreme)
- full_LT2_sim (2,1,1): entry D2 + exit D1 + 1 random miss

Key observations:
- SM bars are barely visible — compound disruptions have minimal effect
- E5/E5_plus have the worst compound response (>-0.39 at entry_D2_exit_D1)
- E0/E0_plus survive entry_D2_exit_D1 within GO_WITH_GUARDS threshold (-0.35)
- Red dashed line: GO threshold (-0.20). Orange dashed line: GO_WITH_GUARDS threshold (-0.35)
- Only SM stays above GO threshold at all scenarios
- Only E0/E0_plus stay above GO_WITH_GUARDS threshold at LT1-appropriate scenarios
