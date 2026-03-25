# VP1 — Hidden inheritance report

The prior spec pack was mostly explicit, but these rules still depended implicitly on Baseline lineage for justification.
For a standalone VP1 rebuild, each of them must be promoted into an explicit rule.

| Hidden shorthand / dependency | Why not standalone enough | Expanded explicit rule for VP1 v1.1 |
|---|---|---|
| `fast_period` inherited from Baseline | VP1 artifact does not state it directly | `fast_period = max(5, floor(slow_period / 4)) = 35` |
| ATR period and smoothing inherited from Baseline | VP1 artifact only says “standard ATR” | `ATR period = 20`, `ATR smoothing = Wilder`, `TR = max(high-low, abs(high-prev_close), abs(low-prev_close))`, seed at index 19 using `nanmean(TR[:20])` |
| VDO EMA periods inherited from Baseline | VP1 artifact only says VDO ON | `VDO = EMA_nan_carry(vdr,12) - EMA_nan_carry(vdr,28)` |
| VDO auto path behavior inherited from Baseline code | VP1 artifact only says `vdo_mode=auto` | Per bar: primary VDR if taker finite and volume>0, else fallback VDR if high>low, else NaN |
| D1/VDO entry-only roles inherited from Baseline | VP1 artifact only says D1 ON, VDO ON | D1 and VDO participate in entry only; neither participates in exit |
| Reversal exit priority inherited from Baseline | VP1 artifact only says reversal ON | Exit order is trailing stop first, reversal second |
| Warmup inherited from Baseline | VP1 artifact does not restate it | `warmup_days = 365`, no-trade before warmup cutoff |
| Peak seed inherited from Baseline | VP1 artifact does not restate it | On entry signal at bar i, `peak_seed = close[i]`; on buy fill, `peak_price = peak_seed` |
| Anomaly-bar semantics inherited from shared data loader | VP1 artifact does not restate it | `anomaly_flag = (volume <= 0) OR (num_trades <= 0)`; anomaly bars are non-decision bars |
| EOF/window flatten behavior inherited from benchmark harness | VP1 artifact does not restate it | No intrinsic EOF exit; optional benchmark wrapper may apply synthetic `window_flatten` only at finite-window end |

## Audit conclusion
The problem was **not** that the prior pack said “same as baseline” too often.  
The problem was that a few decisive rules were still justified by lineage rather than promoted into first-class VP1 rules.

v1.1 removes that dependency for implementation purposes.
