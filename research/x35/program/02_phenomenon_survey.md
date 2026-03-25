# X35 Phase 2 — Phenomenon Survey

**Status**: DONE  
**Current evidence base**: repo priors + branches `a_`, `c_`, `d_`, `e_`, `f_`, `g_`

---

## 1. What Has Already Been Learned Outside X35

### Known constraints

- Entry-time features near the signal bar have little or no predictive power for trade quality.
- Direct slower daily regime replacements (`63d`, `126d`, `200d`) help MDD but do not justify adoption as strict improvements.
- Volume/microstructure residuals at entry are near-exhausted.

These constraints imply the outer-state hypothesis, if real, must be:

- slower than the current D1 inner gate;
- not just another tuned daily threshold;
- orthogonal enough to avoid collapsing into known slow-filter tradeoffs.

## 2. What the Current Pilot Probe Established

The pilot branch `a_state_diagnostic` tested a narrow heuristic menu:

- `wk_close_above_ema26`
- `wk_ema13_above_ema26`
- `mo_close_above_ema6`

Result:

- persistence and support were adequate;
- loss concentration in `risk_off` was weak;
- chronological stability was weak;
- two candidates showed positive mean return in both states.

Interpretation:

- a slow state can exist mechanically;
- but this particular menu does not yet show the kind of hostile/off state needed for a useful overlay.

## 3. What the Stress / Drawdown Scan Established

Branch `c_stress_state_diagnostic` tested Family F3 using:

- `dd63_depth`
- `dd126_depth`
- `vol_shock_30_180`

Result:

- none of the three features produced a useful monotonic degradation in baseline trade quality;
- deeper drawdown did not concentrate losses strongly enough;
- vol shock did not behave like a hostile state, and the highest-stress quartile actually had the strongest mean return in the current scan.

Interpretation:

- crude multi-week drawdown depth is not, by itself, the slow hostile state we need;
- “stress” defined this way may be too coarse, or may not be adverse for a trend-following engine that benefits from expansion after turbulence.

## 4. What The Remaining Families Established

### Family F2 — Multi-Horizon Trend State

Branch `d_multi_horizon_trend_diagnostic` tested:

- `wk_gap_13_26`
- `wk_gap_26_52`
- `wk_alignment_score_13_26_52`

Result:

- no feature produced a strong or stable hostile-vs-favorable split;
- the best rho was only `+0.0355`;
- the best mean-return delta was only `0.46 pp`;
- the score feature segmented eras more than it isolated a truly hostile state.

Interpretation:

- simple weekly trend agreement is too weak for an entry overlay;
- this family is `NO_GO_F2_TREND_FAMILY`.

### Family F4 — Transition / Instability State

Branch `e_transition_instability_diagnostic` tested:

- `wk_mixed_structure_flag`
- `wk_flip_count_8w_ge_2`
- `wk_score_range_8w_ge_2`

Result:

- instability states did not produce negative mean return;
- loss did not concentrate in the unstable state;
- some specs showed lower unstable mean return, but not in the hostile-state way required by the protocol.

Interpretation:

- ambiguity/choppiness is not the missing outer-state explanation for bad entries;
- this family is `NO_GO_F4_TRANSITION_FAMILY`.

### Residual Family F1 — Signed Distance To Slow Anchor

Branch `f_price_level_state_diagnostic` tested:

- `wk_dist_to_ema26`
- `wk_dist_to_ema52`
- `mo_dist_to_ema6`

Result:

- all three features had non-positive Spearman rho;
- top-vs-bottom quartiles did not produce strong concentration;
- weak top-quartile mean improvement did not survive stability logic.

Interpretation:

- the remaining price-level-distance angle also fails;
- this residual family is `NO_GO_F1_PRICE_LEVEL_FAMILY`.

## 5. Survey Objective Before Design

Before freezing any new candidate, `x35` should answer:

- Which slow-state family, if any, actually separates baseline utility?
- Is the effect on **entry quality**, **mid-trade hazard**, or both?
- Is the effect concentrated in tail losses, right-tail opportunity, or neither?

Only after that should a concrete overlay be designed.

## 6. Survey Conclusion

Given current evidence:

- F1 pilot menu: `NO_GO_CURRENT_MENU`
- residual F1 signed distance: `NO_GO_F1_PRICE_LEVEL_FAMILY`
- F2 minimal weekly structure: `NO_GO_F2_TREND_FAMILY`
- F3 coarse stress scan: `NO_GO_STRESS_FAMILY`
- F4 transition / instability: `NO_GO_F4_TRANSITION_FAMILY`

the basic entry-state survey space is now effectively exhausted.

Correct implication:

- do **not** open `b_entry_overlay`
- do **not** keep searching nearby OHLCV outer-state menus for entry blocking

## 7. Hazard Continuation Result

The only admissible continuation was then tested in branch `g_mid_trade_hazard_diagnostic`.

Result:

- weekly instability hazard hits occur too rarely (`1.6%–2.7%` of trades);
- the best spec still fails selectivity threshold;
- two specs either help winners or fail to help losers;
- therefore the Class B continuation is also `NO_GO`.

Interpretation:

- the current OHLCV outer-state program is negative not only for entry blocking,
  but also for the only remaining low-DOF mid-trade continuation.
- therefore Phase 2 is complete and does not support any further candidate search inside `x35`.
