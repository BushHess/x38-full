
# White-page full-history research (2018–2026)

## Scope

Fresh research from raw BTCUSDT H4/D1 bars only. Goal: decompose entry, stop, and exit for a long-only system and identify whether a **single design** can be defended on the **entire 2018–2026 history**, not only in one regime.

This report does **not** replace prior WFO/OOS work. It answers a different question:

> Is there a design that looks defensible on the whole history, and if yes, what is the most robust way to use the information in the data?

## Raw ingredients used

From H4:
- OHLC
- volume
- quote_volume
- taker_buy_base_vol
- taker_buy_quote_vol

From D1:
- close

Indicators rebuilt from raw data:
- H4 EMA30 / EMA120
- D1 EMA21 mapped by last completed D1 close
- robust ATR(20) with 100-bar 90th percentile TR cap and Wilder smoothing
- base imbalance ratio
- VDO = EMA12(imbalance_ratio_base) - EMA28(imbalance_ratio_base)
- freshness proxy = EMA28(imbalance_ratio_base)
- activity proxy = EMA12(quote_volume / EMA28(quote_volume))

## What the data contains

### Entry information

Within bars where `trend_up = EMA30 > EMA120` and D1 regime is on, the raw flow states are not equal.

Using `weak_vdo_thr = 0.0065`:

- `strong_pos`: `VDO > 0.0065`
- `weak_pos_fresh`: `0 < VDO <= 0.0065` and `EMA28(imbalance_ratio_base) <= 0`
- `weak_pos_stale`: `0 < VDO <= 0.0065` and `EMA28(imbalance_ratio_base) > 0`
- `vdo_nonpos`: `VDO <= 0`

Full-history 60-bar forward return means:
- `strong_pos`: **3.77%**
- `weak_pos_fresh`: **1.79%**
- `weak_pos_stale`: **2.19%**
- `vdo_nonpos`: **2.59%**

Post-2021 the ranking changes more sharply:
- `strong_pos`: **1.94%**
- `weak_pos_fresh`: **0.74%**
- `weak_pos_stale`: **-0.04%**
- `vdo_nonpos`: **0.80%**

Interpretation:
- **Strong positive VDO is consistently useful.**
- **Weak positive VDO only deserves trust when the slower imbalance backdrop is still fresh / not already extended.**
- The activity proxy is less timeless than freshness. It helps in some subperiods but is not the clean universal discriminator.

See:
- `entry_state_forward_returns_full.csv`
- `entry_state_forward_returns_pre2021.csv`
- `entry_state_forward_returns_post2021.csv`
- `entry_activity_state_forward_returns_full.csv`
- `entry_activity_state_forward_returns_post2021.csv`

### Exit / lifecycle information

The exit-side information is not “volume alpha” first. It is mostly:
- trade **age**
- **post-exit recycle risk**
- whether the trade is already protected by a trail, making slow trend exits redundant

The strongest full-history family shares these traits:
- close-anchored ATR trail
- **no EMA trend exit**
- a **short cooldown**
- a **long but finite time stop**

This is very different from the post-2021-only winner, which preferred a much shorter life cap and a longer cooldown.

## Search design

The search was intentionally restricted to interpretable families.

### Entry families
- trend only
- original `VDO > 0`
- weak-positive bounded veto:
  - activity only
  - freshness only
  - activity + freshness
- quote-VDO
- global hard-AND variants

### Exit families
Grid over:
- trail multiplier: `2.7, 3.0, 3.3, 3.6`
- peak anchor: `close / high`
- ATR mode: `current / lagged`
- trail confirmation: `1 / 2`
- trend exit: `ema / none`
- cooldown: `0, 3, 6, 9`
- time stop: `None, 24, 30, 36, 48`

Then a focused fine search around the best full-history families:
- trail multiplier `2.6 .. 3.2`
- cooldown `0 .. 6`
- time stop `36 .. 72` plus `None`
- close peak, confirm1, no-trend core

## Main result

## High-Sharpe but rejected as too peaky
A higher full-history peak exists:

- **Entry**: weak-VDO with **activity-only**
- **Exit**: `trail 2.8, close peak, lagged ATR, confirm1, no trend exit, cooldown6, time stop42`
- Full-history Sharpe: **1.747**
- But its middle epoch (`2021–2023`) Sharpe falls to **1.069**, which is **below** the original baseline's **1.147**
- Sensitivity is also too peaky around `cooldown=6` and `time_stop=42`

This violates the “not just one regime” / “wide plateau” requirement.

## Selected full-history winner
The best defensible winner under the stricter criterion is:

### Entry
`trend_up AND regime_ok AND weak_f_vdo`

where:

- `trend_up = EMA30(close_H4) > EMA120(close_H4)`
- `regime_ok = D1_close > D1_EMA21`
- `weak_f_vdo` means:
  - if `VDO <= 0`: reject
  - if `VDO > 0.0065`: accept
  - if `0 < VDO <= 0.0065`: accept **only if**
    - `EMA28(imbalance_ratio_base) <= 0`

### Exit
`trail2.8_close_lagged_confirm1 + no_trend_exit + cooldown3 + time_stop60`

Exact components:
- trail multiplier = **2.8**
- peak anchor = **close**
- ATR mode = **lagged robust ATR**
- trail confirmation = **1**
- EMA cross-down exit = **removed**
- cooldown after every exit fill = **3 bars**
- hard time stop = **60 H4 bars**

## Why this one is selected
Because it is the strongest candidate that satisfies **all three**:
1. better full-history aggregate performance
2. better broad-epoch behavior than the original baseline
3. a materially wider plateau than the sharper local peak

### Full-history continuous metrics
- Baseline (`orig_vdo + base_exit`): Sharpe **1.465**, CAGR **60.760%**, MDD **-38.9%**
- Winner (`weak_f_0065 + trail2.8 lagged no-trend cd3 ts60`): Sharpe **1.685**, CAGR **69.707%**, MDD **-34.0%**

### Broad epochs
Winner vs baseline Sharpe:
- pre-2021: **2.181** vs **2.020**
- 2021–2023: **1.388** vs **1.147**
- 2024–2026: **1.217** vs **1.149**

### Plateau checks

#### Entry plateau
Holding the selected exit fixed, the freshness-only weak-VDO family stays competitive across roughly:
- `weak_vdo_thr ≈ 0.006 .. 0.009`

Representative full-history Sharpe values:
- `0.0060`: **1.623**
- `0.0065`: **1.685**
- `0.0070`: **1.661**
- `0.0075`: **1.671**
- `0.0080`: **1.666**

That is a real plateau, not a single-point spike.

#### Exit plateau
Holding the selected entry fixed:

Trail multiplier with `cooldown=3, time_stop=60`:
- `2.8`: **1.685**
- `2.9`: **1.604**
- `3.0`: **1.644**
- `3.1`: **1.623**

Cooldown with `trail=2.8, time_stop=60`:
- `2`: **1.663**
- `3`: **1.685**
- `4`: **1.673**

Time stop with `trail=2.8, cooldown=3`:
- `54`: **1.604**
- `60`: **1.685**
- `66`: **1.634**

This is wide enough to defend as a plateau family:
- `trail ≈ 2.8–3.1`
- `cooldown ≈ 2–4`
- `time_stop ≈ 54–66`

## Validation of selected winner vs original baseline (full continuous history)

### Bootstrap
Paired circular block bootstrap on full-history bar returns:

|   block_len |   prob_delta_gt0 |          p05 |   median |      p95 |
|------------:|-----------------:|-------------:|---------:|---------:|
|          12 |         0.9475   | -0.00576894  | 0.225168 | 0.452403 |
|          24 |         0.943333 | -0.0106655   | 0.227398 | 0.457391 |
|          48 |         0.9475   | -0.00198698  | 0.222812 | 0.45101  |
|          72 |         0.9425   | -0.00976858  | 0.209124 | 0.432044 |
|         144 |         0.949167 | -0.000293271 | 0.218326 | 0.434577 |
|         288 |         0.946667 | -0.00416283  | 0.228193 | 0.444367 |

Interpretation:
- probability that the winner's Sharpe exceeds baseline is about **94–95%** across block lengths
- the edge is not a single-block artifact

### Cost sweep
|   cost_side |   baseline_sharpe |   winner_sharpe |     delta |   baseline_cagr |   winner_cagr |   baseline_mdd |   winner_mdd |
|------------:|------------------:|----------------:|----------:|----------------:|--------------:|---------------:|-------------:|
|     0       |          1.63426  |        1.87375  | 0.239494  |       0.712103  |     0.812774  |      -0.368811 |    -0.320121 |
|     0.0005  |          1.56649  |        1.7985   | 0.232016  |       0.669511  |     0.765574  |      -0.376651 |    -0.327895 |
|     0.001   |          1.4986   |        1.7231   | 0.224496  |       0.627978  |     0.719604  |      -0.384629 |    -0.335832 |
|     0.00125 |          1.46462  |        1.68534  | 0.220723  |       0.607601  |     0.69707   |      -0.388616 |    -0.339805 |
|     0.0025  |          1.29444  |        1.49619  | 0.201748  |       0.509477  |     0.58875   |      -0.415497 |    -0.359317 |
|     0.005   |          0.953611 |        1.11715  | 0.163539  |       0.33083   |     0.392411  |      -0.501079 |    -0.396628 |
|     0.0075  |          0.614046 |        0.739612 | 0.125566  |       0.173323  |     0.220332  |      -0.595465 |    -0.446961 |
|     0.01    |          0.277932 |        0.366415 | 0.0884836 |       0.0344539 |     0.0695148 |      -0.707693 |    -0.558844 |

Interpretation:
- winner stays ahead from **0 bps** to **100 bps per side**
- the edge is not a fee artifact

## Why the selected winner is not the post-2021 winner

The post-2021 winner was:
- shorter life cap
- longer cooldown
- different weak-VDO companion logic

That design is real for the later regime, but it is **not** the best whole-history design.  
On the full 2018–2026 tape, the data wants something else:

- a **longer** lifecycle cap (`~60 bars`, not `30`)
- a **shorter** refractory period (`~3 bars`, not `6`)
- a **freshness** veto for weak positive VDO, not the more regime-specific activity gate

## Mechanism answers (market-structure logic, not “because backtest says so”)

### 1) Short holding vs long holding — when does each win?
A long-only BTC system earns from two very different move archetypes:

#### Persistent trend continuation
This is the environment where longer holds win:
- spot-led trend persists for days/weeks
- pullbacks are shallow enough that a trail should not eject too early
- the market is still under-owned / not yet saturated by same-direction aggressors

In that world, age is not the enemy; cutting too early is the mistake.

#### Reflexive impulse / liquidity cascade
This is where shorter or capped holds win:
- move quality is front-loaded
- the first expansion carries most of the edge
- later bars are increasingly dominated by profit-taking, re-hedging, and mean reversion around liquidity pockets

In that world, the tail of the trade becomes lower-quality than the head.

The whole-history winner chooses a **middle answer**:
- not the very short 30-bar cap that only worked later
- not infinite hold either
- but a **~60-bar max life**, which is long enough to keep persistent trends and short enough to stop overstaying recycled moves

### 2) Fast re-entry after exit — when is it harmful, when is it harmless?
Fast re-entry is harmful when the exit came from **local volatility around the same swing**, not from a true reset:
- you get stopped / timed out
- the market retests the same zone
- you jump back in before a genuinely new impulse forms
- costs and slippage compound with little new information

Fast re-entry is harmless, even useful, when the previous exit really ended one impulse and the market quickly builds **a new directional impulse**.

That is why the full-history winner uses a **short cooldown**, not a long one:
- `cooldown = 0` is too permissive and churns
- `cooldown = 6` blocks too much across the older tape
- `cooldown ≈ 2–4`, centered at **3**, is the durable compromise

This also matches the trade diagnostics:
- baseline re-entry `<=3 bars`: about **23%**
- selected winner re-entry `<=3 bars`: **0%**
- selected winner re-entry `<=6 bars`: still **~29%**, which is fine — because full-history robustness does **not** want a blanket six-bar ban

### 3) Trend-following exits (EMA cross-down) — when do they protect, when do they hurt?
A slow trend exit protects when:
- the market is entering a genuine persistent downshift
- the trade is still largely unprotected by a trailing stop
- there is no better lifecycle control already in place

It hurts when:
- it is **lagging** a move that has already retraced
- it fires near or after the damage is already done
- it ejects a trade just before a reflexive rebound
- other mechanisms already handle the real problem better (trail + finite age + mild cooldown)

The direct diagnostic on baseline trend exits is revealing:
- after baseline EMA trend exits, the next **12 bars** are positive about **81%** of the time
- over **24 bars**, still positive about **69%**

That is exactly what a late, redundant exit looks like: it often sells into the rebound window.

Once the system already has:
- a volatility-sensitive trail
- a finite age cap
- a short refractory period

the EMA cross-down exit stops solving the right problem.  
It becomes a **slow state label**, not the right trade-level actuator.

## Final answer

### Is there extractable information in this data?
Yes.

The durable pieces are:
- **trend state**
- **flow momentum sign**
- **whether weak positive flow is still fresh or already extended**
- **trade age**
- **post-exit recycle risk**

### How should it be used if the requirement is “whole-history, not one regime”?
Use it as:

1. **Entry**
   - keep the trend/regime core
   - keep `VDO > 0` as the main flow gate
   - only add a **freshness veto** inside the **weak positive VDO** zone

2. **Stop / exit**
   - keep a simple close-anchored ATR trail
   - remove EMA cross-down exit
   - add a **short** cooldown
   - add a **long but finite** time stop around **60 H4 bars**

### Selected winner
**`weak_f_0065 + trail2.8_close_lagged_confirm1 + no_trend_exit + cooldown3 + time_stop60`**

### Simpler fallback
If simplicity is weighted more heavily than the last bit of performance:
**`orig_vdo + trail2.8_close_lagged_confirm1 + no_trend_exit + cooldown3 + time_stop48`**

The fallback is simpler and very robust, but the selected winner is still the better whole-history design.

## Caveats

- “Proven on the whole history” does **not** mean “better in every calendar year.” It means the design is supported by the full continuous tape and by broad epoch checks.
- The selected winner is a **research result on this BTCUSDT history**. It is not a claim that the same exact constants will survive a different exchange, a different asset, or a radically different fee model.
- The earlier post-2021 winner remains valid for that regime. It is just **not** the best answer to the stricter whole-history question.

