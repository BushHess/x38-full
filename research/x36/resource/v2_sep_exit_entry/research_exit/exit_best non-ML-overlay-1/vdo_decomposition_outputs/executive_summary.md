# Executive summary: candidate-signal + VDO decomposition

## Candidate-signal protocol
- Core entry universe = trend-up + D1 regime-on, no volume gate.
- Each candidate signal was replayed as a 1D entry filter on the same architecture under the same 4 expanding WFO folds.
- Ungated core aggregate WFO OOS Sharpe = **0.742**.

## What survives in WFO
- Current VDO gate (`vdo >= 0`) remains the strongest robust first-principles rule: Sharpe **1.131**, positive folds **3/4**.
- Train-tuned VDO threshold does **not** improve OOS: Sharpe **1.097**. Mean selected threshold stays near zero.
- Quote-ratio oscillator is effectively the same signal as VDO in strategy-space: Sharpe **1.131**, trade-level correlation with VDO **0.999993**, sign disagreement **0.4049%**.
- Normalized net-flow oscillator has real but smaller standalone value: Sharpe **1.081**, positive folds **4/4**.
- Smoothed volume-surprise carries information, but only after extraction/tuning: `ema12(volume_surprise_quote_28)` reaches Sharpe **1.102**, while natural `volume_surprise >= 1` is much weaker.

## Layer-by-layer read
- Measurement: base-ratio and quote-ratio are practically equivalent once you run the same oscillator on them; switching to quote ratio is not a real new edge.
- Operator: on imbalance measurements, the EMA-difference oscillator dominates level, EMA-level, and persistence. This is the cleanest evidence that VDO works because it extracts momentum of imbalance, not just raw imbalance.
- Decision: the useful threshold for VDO is already around zero. Threshold optimization mostly adds complexity, not edge.
- Extra information: volume-surprise and normalized net flow contain some predictive content, but the content is weaker/more fragile than VDO when forced into a hard entry gate.

## Independent information beyond price state
- In trade-level expanding WFO logistic tests, adding VDO to price-only baseline raises AUC by **0.038** and improves log loss by **0.004**.
- Volume-surprise adds a similar AUC bump (**0.037**), but that information does not translate cleanly into a robust natural hard gate.
- Slow imbalance level (`ema28_imbalance_ratio_base`) has signal-only AUC > 0.52, yet fails as a standalone gate. That means some information exists, but its natural use is not an always-on veto.

## Best practical use right now
- Keep `entry_core = trend_up AND regime_ok AND VDO > 0` as the default architecture.
- Treat volume surprise and normalized net flow as secondary context signals, not replacements for VDO.
- Do not replace VDO with quote-ratio VDO; it is essentially the same thing.
- Do not spend cycles on threshold tuning around zero first; the bigger room, if any, is in companion/context usage, not actuator tweaking.
- In the tested companion-gate sweep, no VDO + companion combination beat plain VDO on aggregate OOS Sharpe.

## Research implication
- The next worthwhile branch is not inventing another VDO bundle. It is: keep VDO as the core hard gate, then test whether secondary signals belong in continuation/hold context or bounded conditional vetoes with stronger structural priors.