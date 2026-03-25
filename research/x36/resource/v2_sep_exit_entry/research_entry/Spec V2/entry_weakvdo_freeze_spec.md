# VTREND entry freeze spec — weak positive VDO bounded veto (deployment version)

## 1. Purpose
This document fully specifies the **deployment freeze** of the entry rule derived from the research winner
`weakvdo_q0.5_activity_and_fresh_imb`.

It is self-contained. A competent engineer should be able to reconstruct the entry logic from raw data without
chat history or the original research code.

## 2. Scope lock
This spec changes **entry only**.

Unchanged components:
- exit logic
- D1 regime filter definition
- robust ATR construction
- EMA periods already used by the base strategy
- position sizing
- accounting
- transaction costs
- execution semantics other than the entry veto itself

Exit remains the current base exit during validation:
- robust ATR trail-stop
- EMA30 / EMA120 trend exit

Exit is **not** redefined here.

## 3. Raw data requirements

### 3.1 H4 input file
One H4 CSV with at least these columns:

- `open_time` (Unix ms, UTC)
- `close_time` (Unix ms, UTC)
- `open`
- `high`
- `low`
- `close`
- `volume`
- `quote_volume`
- `taker_buy_base_vol`
- `taker_buy_quote_vol`

### 3.2 D1 input file
One D1 CSV with at least these columns:

- `open_time` (Unix ms, UTC)
- `close_time` (Unix ms, UTC)
- `close`

## 4. Time and bar semantics
- All timestamps are UTC.
- All signals are computed on **closed bars**.
- A decision formed on H4 bar `t` is executed at **open of bar `t+1`**.
- No intrabar peeking.
- No pyramiding.
- Position is either fully flat or fully long.

## 5. Warmup and evaluation cutoff
- Warmup: **365 calendar days** from the first H4 `open_time`
- Strategy becomes eligible only from:
  - `eligible_from = first_h4_open_dt + 365 days`
- Validation cutoff used in research and acceptance:
  - `2026-02-28 23:59:59.999 UTC`

## 6. EMA convention
For any series `x_t` and period `p`:

- `alpha_p = 2 / (p + 1)`
- `EMA_p(x)_0 = x_0`
- `EMA_p(x)_t = alpha_p * x_t + (1 - alpha_p) * EMA_p(x)_(t-1)` for `t >= 1`

This convention must be used everywhere in this spec.

## 7. Base indicators carried over unchanged

### 7.1 H4 trend state
- `ema_fast_t = EMA_30(close)_t`
- `ema_slow_t = EMA_120(close)_t`

Trend-up core condition:
- `trend_up_t = (ema_fast_t > ema_slow_t)`

### 7.2 D1 regime filter
On D1:
- `d1_ema21_t = EMA_21(d1_close)_t`
- `d1_regime_ok_t = (d1_close_t > d1_ema21_t)`

Mapping from D1 to H4:
- For each H4 bar, attach the most recent D1 bar whose `close_time < h4_close_time`
- Use `merge_asof(..., direction="backward")` semantics on `close_time`
- The attached D1 values are:
  - `d1_close`
  - `d1_ema21`
  - `d1_regime_ok`

Regime condition used at H4 bar `t`:
- `regime_ok_t = attached_d1_regime_ok_t`

## 8. Entry signals from volume-flow data

### 8.1 Base imbalance ratio
Define H4 taker-sell base volume:
- `taker_sell_base_t = volume_t - taker_buy_base_vol_t`

Define base imbalance ratio:
- `imbalance_ratio_base_t = (taker_buy_base_vol_t - taker_sell_base_t) / volume_t`
- equivalent:
- `imbalance_ratio_base_t = (2 * taker_buy_base_vol_t - volume_t) / volume_t`

If `volume_t == 0`, set:
- `imbalance_ratio_base_t = 0.0`

### 8.2 VDO
- `vdo_fast_t = EMA_12(imbalance_ratio_base)_t`
- `vdo_slow_t = EMA_28(imbalance_ratio_base)_t`
- `VDO_t = vdo_fast_t - vdo_slow_t`

### 8.3 Activity support
Define quote-volume normalization:
- `ema28_quote_volume_t = EMA_28(quote_volume)_t`
- `vol_surprise_quote_28_t = quote_volume_t / ema28_quote_volume_t`

Then:
- `activity_score_t = EMA_12(vol_surprise_quote_28)_t`
- `activity_support_t = (activity_score_t >= 1.0)`

### 8.4 Freshness support
- `freshness_score_t = EMA_28(imbalance_ratio_base)_t`
- `freshness_support_t = (freshness_score_t <= 0.0)`

Interpretation:
- `activity_support` asks whether recent quote-volume participation is at or above its slow norm.
- `freshness_support` asks whether slow base imbalance has not already become positively late / extended.

## 9. Frozen weak-VDO boundary

### 9.1 Deployment constant
Use the hard-coded constant:

- `WEAK_VDO_THR = 0.0065`

This is the deployment freeze.

### 9.2 Provenance
The constant comes from rounding the causal pre-live estimate:

- pre-live sample end: `2021-06-30 23:59:59.999 UTC`
- estimate definition:
  - median of `VDO_t`
  - over bars where:
    - `close_dt >= eligible_from`
    - `close_dt <= 2021-06-30 23:59:59.999 UTC`
    - `trend_up_t == True`
    - `regime_ok_t == True`
    - `VDO_t > 0`
- resulting exact pre-live median:
  - `0.00648105072393846`
- deployment freeze rounds this to:
  - `0.0065`

On the validation sample, `0.0065` is decision-equivalent to the exact pre-live value.

## 10. Entry rule

### 10.1 Core gate
At H4 close bar `t`, define:
- `core_t = trend_up_t AND regime_ok_t`

### 10.2 Weak-positive-VDO veto logic
When flat, an entry is scheduled at next open `t+1` if and only if all conditions below are true:

1. `core_t == True`
2. `VDO_t > 0`
3. and one of:

   **Case A — strong positive VDO**
   - `VDO_t > WEAK_VDO_THR`

   **Case B — weak positive VDO**
   - `0 < VDO_t <= WEAK_VDO_THR`
   - `activity_support_t == True`
   - `freshness_support_t == True`

Compact equivalent:
- `enter_t = core_t AND [ (VDO_t > 0.0065) OR (0 < VDO_t <= 0.0065 AND activity_support_t AND freshness_support_t) ]`

## 11. Pseudocode for entry decision

```python
def should_enter_long_at_close_t(t):
    if not flat:
        return False

    trend_up = ema_fast[t] > ema_slow[t]
    regime_ok = d1_regime_ok_mapped_to_h4[t]

    if not (trend_up and regime_ok):
        return False

    vdo = VDO[t]
    if vdo <= 0.0:
        return False

    if vdo > 0.0065:
        return True

    activity_support = EMA12(quote_volume / EMA28(quote_volume))[t] >= 1.0
    freshness_support = EMA28(imbalance_ratio_base)[t] <= 0.0

    return activity_support and freshness_support
```

Execution:
- if `should_enter_long_at_close_t(t)` is `True`, submit one full long entry at `open[t+1]`

## 12. Interaction with unchanged exit logic
This entry spec does **not** alter exit logic.

After entry fill, the strategy hands control to the unchanged exit stack:
- robust ATR trail-stop
- EMA30 / EMA120 cross-down trend exit

No entry-specific exception or override is added to exit.

## 13. Position sizing and accounting (unchanged)
Keep the original base accounting exactly:

- per-side cost: **12.5 bps**
- full-entry quantity:
  - `qty = cash_before / (open_price * (1 + side_cost))`
- full-exit cash:
  - `cash_after = cash_before + qty_before * open_price * (1 - side_cost)`

No leverage.
No partial fills.
No pyramiding.

## 14. Validation protocol used to accept this freeze

### 14.1 WFO OOS folds
The same 4 expanding folds used in entry research:

1. Fold 1 OOS:
   - `2021-07-01 00:00:00 UTC` to `2022-12-31 23:59:59.999 UTC`
2. Fold 2 OOS:
   - `2023-01-01 00:00:00 UTC` to `2024-06-30 23:59:59.999 UTC`
3. Fold 3 OOS:
   - `2024-07-01 00:00:00 UTC` to `2025-06-30 23:59:59.999 UTC`
4. Fold 4 OOS:
   - `2025-07-01 00:00:00 UTC` to `2026-02-28 23:59:59.999 UTC`

Protocol rules:
- indicator history is available from the start of the raw dataset
- each fold starts **flat**
- only OOS bars inside the fold count toward fold metrics

### 14.2 Baseline comparator
Baseline entry:
- `enter_baseline_t = trend_up_t AND regime_ok_t AND (VDO_t > 0)`

Everything else unchanged.

### 14.3 Acceptance targets for this frozen deployment form
Against the baseline, with base exit unchanged, the frozen rule should reproduce approximately:

Aggregate OOS:
- Sharpe: **1.3404104321**
- CAGR: **0.4127141953**
- MDD: **-0.2856178361**
- Trades: **104**
- Exposure: **0.3745109546**

Baseline aggregate OOS for reference:
- Sharpe: **1.1307598000**
- CAGR: **0.3504215910**
- MDD: **-0.3709393067**
- Trades: **118**
- Exposure: **0.4092331768**

Fold-level OOS Sharpe for the frozen rule:
- Fold 1: **1.1196934806**
- Fold 2: **1.5075440738**
- Fold 3: **1.8753474413**
- Fold 4: **0.3222358854**

Fold-level OOS Sharpe for the baseline:
- Fold 1: **0.6066794596**
- Fold 2: **1.5375055975**
- Fold 3: **1.8185733333**
- Fold 4: **-0.0221573053**

Additional comparison points:
- positive folds vs baseline: **3 / 4**
- direct bootstrap edge vs baseline:
  - probability delta Sharpe > 0 roughly **0.926 to 0.959**
  - depending on circular block length 24 to 288 H4 bars
- cost sweep:
  - frozen rule beats baseline on aggregate Sharpe from **0 to 100 bps per side**

### 14.4 Relationship to the research winner
The fold-adaptive research winner remains stronger:
- research winner Sharpe: **1.3740835418**

But the deployment freeze keeps the same motif while dropping fold-adaptive threshold logic.
On the study sample:
- same number of trades (**104**)
- **101 / 104** entry timestamps shared with the research winner
- only **3** entries are retimed

This is why the frozen form was accepted.

## 15. Known caveats

### 15.1 Post-2021 structure caveat
This entry edge should be read as a **post-2021 OOS improvement**.
Do not describe it as a timeless full-history law.

### 15.2 Exit-coupling caveat
This freeze was validated with the current base exit only.
If exit later changes, especially toward the same flow / activity family, entry must be re-validated.

### 15.3 No renewed threshold tuning
The lesson of the research remains:
- the main edge is the **bounded weak-VDO veto motif**
- not endless tuning of `VDO > 0` into another global threshold game

## 16. Minimal implementation checklist
A rebuild is correct only if all of the following hold:

1. EMA convention matches Section 6 exactly
2. D1-to-H4 mapping uses backward-asof on `close_time`
3. `imbalance_ratio_base` uses base taker flow and total base volume
4. `activity_support` uses `EMA12(quote_volume / EMA28(quote_volume)) >= 1.0`
5. `freshness_support` uses `EMA28(imbalance_ratio_base) <= 0.0`
6. `WEAK_VDO_THR` is hard-coded to `0.0065`
7. entries are decided on H4 close and filled next open
8. exit stack remains unchanged
9. OOS acceptance metrics match Section 14.3 within normal floating-point tolerance

## 17. One-line summary
The deployment entry rule is:

**Enter on `VDO > 0` only when trend and regime are on; accept all strong positive-VDO bars, but for weak positive-VDO bars require both above-normal quote-volume activity and non-late slow base-imbalance context, using a fixed weak-VDO boundary of `0.0065`.**
