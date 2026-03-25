# Executive summary

- Locked entry core baseline (base exit): Sharpe **1.131**
- Reconstructed incumbent price-only hold model: Sharpe **1.194**

What passed?
- **Against base exit**: several simple policies passed, mostly **stateful guard** formulations using smoothed imbalance or smoothed normalized net quote flow.
- **Against incumbent price-only hold model**: **nothing passed**. No simple signal policy and no additive one-signal logistic model achieved both higher aggregate WFO OOS Sharpe and `>=3/4` positive folds vs the incumbent.

Best simple policy by aggregate Sharpe:
- `stateful + train-threshold + ema12_net_quote_norm_28`
- Sharpe **1.216**
- Positive folds vs base exit: **3/4**
- Positive folds vs incumbent price model: **1/4**

Plain-language read:
- Secondary volume signals are **more useful as ongoing hold guards than as one-shot continuation gates**.
- The strongest family is **normalized net quote flow** and, secondarily, **smoothed imbalance level**.
- But once the incumbent price-state hold model is present, these signals are **not strong enough to justify promotion** under the same WFO OOS standard.
