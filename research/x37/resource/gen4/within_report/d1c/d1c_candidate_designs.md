# D1c Candidate Designs & Config Matrix

Historical snapshot usage: candidate-mining-only. No clean external OOS claim.  
This step designs mechanisms and configuration sets only. No backtest, scoring, or candidate selection is performed here.

## Candidate 1 — `btcsd_20260318_c1_av4h`

**Mechanism description**  
Exploit 4h continuation only when the daily environment is both orderly and non-adverse:
1. daily range-based volatility is in a relatively low trailing state; and  
2. daily price is not in the lower half of its 168-day rolling range.

This targets the strongest integrated slow filter from D1b (`D1 anti-vol`) combined with the cleanest mid-frequency directional engine (`4h rangepos_168 / ret_168 continuation`). D1b4 showed that daily low-vol materially strengthens 4h trend, and weak daily trend can flip 4h trend negative. The design therefore keeps the daily trend sign as a fixed non-tuned permission and searches only the anti-vol intensity plus the 4h entry/hold cutoffs.

**Market behavior exploited**  
Orderly, non-chaotic BTC trend extension. The thesis is that a large share of medium-horizon upside is earned when volatility has compressed at the daily scale but 4h structure is already leaning toward the top of its rolling range.

**Why it may persist**  
BTC trend phases often transition from high-vol discovery to lower-vol directional persistence. In that state, 4h strength is less likely to be immediately mean-reverted.

**What should cause it to fail**  
If daily low-vol stops being bullish and instead becomes complacent/fragile, or if 4h range-position stops behaving as a continuation state and starts mean-reverting.

**Observable falsification evidence**  
- Daily anti-vol no longer improves 4h continuation versus unconditional 4h trend.
- The conditional 4h continuation spread under daily low-vol falls to approximately zero or turns negative.
- Low daily trend no longer degrades 4h continuation.

**Timeframes used**  
`1d`, `4h`

**Feature formulas**  
- `d1_range1_t = (high_t - low_t) / close_t`
- `d1_rangevol84_t = mean(d1_range1_{t-83:t})`
- `d1_rangevol84_rank365_t = pct_rank(d1_rangevol84_t within trailing 365 closed D1 bars, inclusive)`
- `d1_rangepos168_t = (close_t - min(low_{t-167:t})) / (max(high_{t-167:t}) - min(low_{t-167:t}))`
- `h4_rangepos168_t = (close_t - min(low_{t-167:t})) / (max(high_{t-167:t}) - min(low_{t-167:t}))`

**Signal logic**  
Decision timeframe: `4h`.  
Daily features are read from the most recent fully closed D1 bar with `close_time <= current 4h close_time`.

- **Entry condition** (when flat):  
  `d1_rangevol84_rank365_t <= q_d1_antivol_rank`  
  AND `d1_rangepos168_t >= 0.50`  
  AND `h4_rangepos168_t >= q_h4_rangepos_entry`
- **Hold condition** (when long):  
  `d1_rangevol84_rank365_t <= q_d1_antivol_rank`  
  AND `d1_rangepos168_t >= 0.50`  
  AND `h4_rangepos168_t >= q_h4_rangepos_hold`
- **Exit condition**: otherwise.

**Calibration method**  
- Daily anti-vol threshold: trailing percentile-rank cutoff.
- Daily trend permission: fixed midpoint (`0.50`) on daily range position.
- 4h trend thresholds: fixed raw range-position cutoffs with hysteresis.

**Tunable quantities**  
1. `q_d1_antivol_rank` — continuous cutoff, selected from `[0.35, 0.50, 0.65]`
2. `q_h4_rangepos_entry` — continuous cutoff, selected from `[0.55, 0.65]`
3. `q_h4_rangepos_hold` — continuous cutoff, selected from `[0.35, 0.45]`

**Fixed quantities**  
- Daily range-vol window = `84`
- Daily range-position window = `168`
- 4h range-position window = `168`
- Daily trend midpoint = `0.50`

**Layer count**  
`2` logical layers  
- Layer 1: combined D1 permission  
- Layer 2: 4h execution state

**Execution semantics**  
Signal evaluated at 4h bar close. Fill at next 4h bar open. UTC alignment. Long-only / long-flat. Binary `0% / 100%` notional. No leverage. No pyramiding. No lookahead from incomplete daily bars.

**Viability gate**  
Most permissive config tested on discovery year `2020`:  
`q_d1_antivol_rank=0.65, q_h4_rangepos_entry=0.55, q_h4_rangepos_hold=0.35`  
Observed entry count in 2020: **7**.

**Selected configs**  
6 configs: `cfg_001`–`cfg_006`

---

## Candidate 2 — `btcsd_20260318_c2_flow1hpb`

**Mechanism description**  
Exploit recovery from 1h multi-day pullbacks only when:
1. daily taker-buy pressure has already cooled to non-positive territory; and  
2. the 4h backdrop is constructive.

This is a pullback/recovery mechanism, not a trend-chasing mechanism. It combines the strongest slow flow block from D1b (`D1 flow exhaustion`) with the most complementary directional channel (`1h ret_168 reversal`). D1b4 showed that positive 4h trend materially improves the 1h reversal channel, so 4h trend is used as a permission layer instead of buying every oversold 1h condition.

**Market behavior exploited**  
Recovery after aggressive-buying exhaustion has faded. The design aims to enter after a bullish market has cooled off, not while order-flow pressure is still fully extended.

**Why it may persist**  
In persistent bull phases, multi-day pullbacks often mean-revert when slower order-flow excess has already been worked off. The 4h trend layer is there to separate constructive pullbacks from structurally weak tape.

**What should cause it to fail**  
If daily flow sign loses its exhaustion meaning, or if 1h 168-bar pullbacks stop recovering even when the 4h backdrop is positive.

**Observable falsification evidence**  
- D1 flow sign split stops showing long-horizon reversal.
- The 1h `ret_168` conditional reversal spread under positive 4h trend drops to approximately zero or turns negative.
- Extreme pullbacks behave worse than moderate pullbacks with no stability gain.

**Timeframes used**  
`1d`, `4h`, `1h`

**Feature formulas**  
- `d1_flow12_t = 2 * sum(taker_buy_base_vol_{t-11:t}) / sum(volume_{t-11:t}) - 1`
- `h4_rangepos168_t = (close_t - min(low_{t-167:t})) / (max(high_{t-167:t}) - min(low_{t-167:t}))`
- `h1_ret168_t = close_t / close_{t-168} - 1`

**Signal logic**  
Decision timeframe: `1h`.  
Daily and 4h features are read from the most recent fully closed slower bar with `close_time <= current 1h close_time`.

- **Entry condition** (when flat):  
  `d1_flow12_t <= 0.0`  
  AND `h4_rangepos168_t >= q_h4_rangepos_min`  
  AND `h1_ret168_t <= theta_h1_ret168_entry`
- **Hold condition** (when long):  
  `d1_flow12_t <= 0.0`  
  AND `h4_rangepos168_t >= q_h4_rangepos_min`  
  AND `h1_ret168_t <= theta_h1_ret168_hold`
- **Exit condition**: otherwise.

**Calibration method**  
- Daily flow permission: fixed sign split at `0.0` (chosen because D1b measured the strongest usable effect as positive-vs-negative imbalance, not extreme-tail quantiles).
- 4h trend threshold: fixed raw range-position cutoff.
- 1h pullback thresholds: fixed raw 168-bar return thresholds with hysteresis.

**Tunable quantities**  
1. `q_h4_rangepos_min` — continuous cutoff, selected from `[0.30, 0.45, 0.60]`
2. `theta_h1_ret168_entry` — arithmetic-return threshold, selected from `[-0.04, -0.01]`
3. `theta_h1_ret168_hold` — arithmetic-return threshold, selected from `[0.01, 0.04]`

**Fixed quantities**  
- Daily flow window = `12`
- 4h range-position window = `168`
- 1h pullback lookback = `168`
- Daily flow sign threshold = `0.0`

**Layer count**  
`3` logical layers  
- Layer 1: D1 flow permission  
- Layer 2: 4h context  
- Layer 3: 1h execution

**Execution semantics**  
Signal evaluated at 1h bar close. Fill at next 1h bar open. UTC alignment. Long-only / long-flat. Binary `0% / 100%` notional. No leverage. No pyramiding. No lookahead from incomplete D1 or 4h bars.

**Viability gate**  
Most permissive config tested on discovery year `2020`:  
`q_h4_rangepos_min=0.30, theta_h1_ret168_entry=-0.01, theta_h1_ret168_hold=0.04`  
Observed entry count in 2020: **30**.

**Selected configs**  
12 configs: `cfg_007`–`cfg_018`

---

## Candidate 3 — `btcsd_20260318_c3_trade4h15m`

**Mechanism description**  
Exploit 4h continuation only when daily participation is unusually strong relative to volume, and use a 15m activity burst to time entry. This candidate exists to test whether the independent slow `D1 trade surprise` block and the independent fast `15m activity` block can improve a 4h directional engine without turning 15m into the primary decision timeframe.

**Market behavior exploited**  
Participation-led continuation. Daily trade-count surprise is treated as a slow background state, while 15m relative-volume acts as a timing event that may help movement delivery once the 4h trend state is already favorable.

**Why it may persist**  
A market attracting more trades than volume alone would imply may reflect broader participation and better follow-through. Short-term activity bursts can then improve entry timing into that slow state.

**What should cause it to fail**  
If daily trade surprise loses its long-horizon bullish meaning, or if 15m activity becomes mostly reactive/late and no longer adds timing value.

**Observable falsification evidence**  
- D1 trade-surprise sign split loses its bullish continuation readout.
- 15m relative-volume stops carrying near-term magnitude/timing information.
- Entry timing arrives predominantly after rather than before the extension leg.

**Timeframes used**  
`1d`, `4h`, `15m`

**Feature formulas**  
Warmup or train-window fit only:
- `log1p(num_trades_t) = alpha + beta * log1p(volume_t) + eps_t`
- `d1_trade_surprise168_t = eps_t - mean(eps_{t-167:t})`

Execution features:
- `h4_rangepos168_t = (close_t - min(low_{t-167:t})) / (max(high_{t-167:t}) - min(low_{t-167:t}))`
- `m15_relvol168_t = volume_t / mean(volume_{t-167:t})`

**Signal logic**  
Decision timeframe: `15m`.  
Daily and 4h features are read only from the most recent fully closed slower bar with `close_time <= current 15m close_time`.

- **Entry condition** (when flat):  
  `d1_trade_surprise168_t > 0.0`  
  AND `h4_rangepos168_t >= q_h4_rangepos_entry`  
  AND `m15_relvol168_t >= rho_m15_relvol_min`
- **Hold condition** (when long):  
  `d1_trade_surprise168_t > 0.0`  
  AND `h4_rangepos168_t >= q_h4_rangepos_hold`
- **Exit condition**: otherwise.

**Calibration method**  
- Daily trade-surprise base model (`alpha`, `beta`) is fit only on available training history; the design-time sanity check used warmup fit only.
- Daily permission: fixed sign split at `0.0`.
- 4h trend thresholds: fixed raw range-position cutoffs with hysteresis.
- 15m timing threshold: fixed raw relative-volume cutoff.

**Tunable quantities**  
1. `q_h4_rangepos_entry` — continuous cutoff, selected from `[0.55, 0.65]`
2. `q_h4_rangepos_hold` — continuous cutoff, selected from `[0.35, 0.45]`
3. `rho_m15_relvol_min` — activity ratio cutoff, selected from `[1.10, 1.30, 1.50]`

**Fixed quantities**  
- Daily trade-surprise window = `168`
- 4h range-position window = `168`
- 15m relative-volume window = `168`
- Daily trade-surprise sign threshold = `0.0`

**Layer count**  
`3` logical layers  
- Layer 1: D1 participation permission  
- Layer 2: 4h context  
- Layer 3: 15m timing refinement

**Execution semantics**  
Signal evaluated at 15m bar close. Fill at next 15m bar open. UTC alignment. Long-only / long-flat. Binary `0% / 100%` notional. No leverage. No pyramiding. No lookahead from incomplete D1 or 4h bars.

**Viability gate**  
Most permissive config tested on discovery year `2020`:  
`q_h4_rangepos_entry=0.55, q_h4_rangepos_hold=0.35, rho_m15_relvol_min=1.10`  
Observed entry count in 2020: **26**.

**Sub-hourly guidance note**  
This is **not** a 15m-primary directional engine. The directional state remains slow (`D1 + 4h`); `15m` is used only for timing refinement. It is still the most cost-sensitive design in this set and therefore carries higher WFO survival risk than the pure 4h/1h candidates.

**Selected configs**  
12 configs: `cfg_019`–`cfg_030`

---

## Config Matrix Summary

| candidate_id | configs |
|---|---:|
| `btcsd_20260318_c1_av4h` | 6 |
| `btcsd_20260318_c2_flow1hpb` | 12 |
| `btcsd_20260318_c3_trade4h15m` | 12 |
| **Total** | **30** |

The machine-readable config matrix is saved separately as `d1c_config_matrix.csv`.

## Hard Cap Compliance Check

| check | result | note |
|---|---|---|
| Candidates <= 3 | PASS | 3 candidates designed |
| Challengers <= 2 after seed | PASS | Not applicable at D1c; no selection performed |
| Layers per candidate <= 3 | PASS | Candidate 1 = 2; Candidate 2 = 3; Candidate 3 = 3 |
| Tunables per candidate <= 4 | PASS | All candidates use 3 tunables |
| Configs per candidate <= 20 | PASS | 6 / 12 / 12 |
| Total configs <= 60 | PASS | 30 total |
| Binary sizing only | PASS | All designs are long-flat, 0%/100% notional |
| No leverage / no pyramiding / no discretionary overrides | PASS | Explicitly excluded |
| Admitted data surface only | PASS | All formulas use raw OHLCV, quote volume, num_trades, taker_buy_base_vol |
| No holdout or reserve_internal usage | PASS | Design and sanity checks used warmup + 2020 only |
| No incomplete slower-bar lookahead | PASS | Slower-TF features are read only from fully closed bars |
| Next-open fill / UTC alignment | PASS | Explicit in every candidate |

## Design Rationale

These three mechanisms were selected because they are the strongest **measured** and reasonably **independent** blocks from D1b, while staying inside the complexity budget:

1. **Candidate 1** uses the best slow directional filter (`D1 anti-vol`) with the cleanest mid-frequency engine (`4h trend`). It is the smallest defensible continuation design.
2. **Candidate 2** deliberately does **not** chase the same trend block. It uses the independent slow flow-exhaustion state plus the complementary `1h` pullback/recovery channel, with 4h trend only as permission because D1b4 showed that the 4h backdrop materially improves the recovery edge.
3. **Candidate 3** is the only design that intentionally spends complexity on timing. It uses the partly independent `D1 trade surprise` block and the strongest fast activity/timing block (`15m relative volume`) while keeping the directional engine above 15m.

### Why other measured channels were not promoted into separate candidates

- **Daily gaps** were excluded because D1b marked them as noise.
- **Calendar direction** was excluded because the effect was weak and mostly aliased the activity block.
- **Generic compression / breakout release** was excluded because D1b rejected it as a broad claim.
- **Standalone 1h fast continuation** was excluded because it was highly redundant with faster continuation and added little independent information.
- **Standalone 15m continuation (`ret_42`)** was intentionally **not** promoted as a primary candidate because:
  - D1b4 showed blind same-direction stacking from 1h into 15m is weak/negative.
  - The governance patch warns that sub-hourly primaries are structurally more fragile under cost.
- **Multiple lower-timeframe flow variants** were excluded because D1b4 showed they are mostly descendants of the same slow flow-exhaustion block.
- **Extreme 1h pullback thresholds** were not included in Candidate 2’s config set because D1b1 explicitly warned that the 1h `ret_168` channel is not a clean monotone extreme-value state; the selected grid keeps only the moderate region that still passed the activity sanity check.

## Notes for D1d

- No score, ranking, champion, or challenger assignment has been made.
- The next step should test exactly the saved configs with fold-causal calibration only.
- Candidate 3 should receive explicit cost-sensitivity attention in D1d because its 15m timing layer raises turnover risk even though it is not a 15m-primary engine.
