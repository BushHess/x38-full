# Report 35: VTREND-SM Integration

> **Phase**: 5 — Implement VTREND-SM from canonical design contract
> **Date**: 2026-03-04
> **Status**: Complete
> **Prerequisite reports**: 34 (survey), 34b (pre-integration audit), 34c (canonical design contract)

---

## 1. Scope

Port VTREND-SM (state-machine trend-following strategy) from Latch into btc-spot-dev,
implementing per the canonical design contract (Report 34c), not as a blind source port.

**Authority order applied**: 34c contract > 34b audit > 34 survey > Latch source (reference only).

---

## 2. Implementation Summary

### 2.1 Files Created

| File | Purpose | Lines |
|------|---------|-------|
| `strategies/vtrend_sm/__init__.py` | Module exports (STRATEGY_ID, VTrendSMConfig, VTrendSMStrategy) | 13 |
| `strategies/vtrend_sm/strategy.py` | Strategy implementation per canonical contract | 364 |
| `tests/test_vtrend_sm.py` | 47 tests covering T1–T21 acceptance criteria + D2 canonical test | ~550 |

### 2.2 Files Modified (Registration)

| File | Change |
|------|--------|
| `v10/core/config.py` | +import, +_VTREND_SM_FIELDS, +"vtrend_sm" in _KNOWN_STRATEGIES, +strategy_fields_by_name, +validate_config branch |
| `v10/research/candidates.py` | +import, +_VTREND_SM_FIELDS, +load_candidates branch, +build_strategy branch |
| `validation/strategy_factory.py` | +import, +"vtrend_sm" in STRATEGY_REGISTRY |
| `v10/cli/backtest.py` | +import, +"vtrend_sm" in STRATEGY_REGISTRY |

### 2.3 Canonical Contract Adherence

Two fixes applied to pre-existing draft implementation:

| Fix | Detail | Contract Reference |
|-----|--------|-------------------|
| F1 | `BARS_PER_YEAR_4H`: 2191.5 → 2190.0 | D1: matches source AND metrics.py |
| F2 | Config field ordering: positions 7-9 reordered to match source | D15: target_vol, vol_lookback, slope_lookback |

All other canonical behaviors were already correctly implemented in the draft:
- D2: Entry requires `weight > 0.0` (line 331)
- D3/D4: Rebalance gating strategy-side, close-price basis (lines 350-358)
- D5: VDO OHLC proxy fallback (since removed — VDO now requires taker data)
- D6: VDO NaN → return None
- D7: `_clip_weight` character-identical to source
- D8: Mutable @dataclass
- D9: Validation in `__post_init__`
- D10: Warmup = first finite index

---

## 3. Test Results

### 3.1 VTREND-SM Tests

**47/47 passed** (0.43s)

| Category | Tests | Status |
|----------|-------|--------|
| T1: Config defaults match source | 2 | PASS |
| T2: Config resolved() auto-derivation | 4 | PASS |
| T3: _ema numerical correctness | 2 | PASS |
| T4: _atr numerical correctness | 1 | PASS |
| T5: _rolling_high_shifted | 1 | PASS |
| T6: _rolling_low_shifted | 1 | PASS |
| T7: _realized_vol | 2 | PASS |
| T8: _clip_weight all branches | 10 | PASS |
| T9: Entry signal conditions | 1 | PASS |
| T10: No entry during warmup | 1 | PASS |
| T11: Exit on floor break | 1 | PASS |
| T12: Exit on regime break (enabled) | 1 | PASS |
| T13: No regime exit when disabled | 1 | PASS |
| T14: Vol-targeted sizing | 2 | PASS |
| T15-T16: Rebalance threshold | 2 | PASS |
| T17: Weights bounded [0,1] | 1 | PASS |
| T18: VDO filter blocks entry | 1 | PASS |
| T19: slope_lookback affects signals | 1 | PASS |
| T20: Engine integration smoke test | 1 | PASS |
| T21: BARS_PER_YEAR_4H = 2190.0 | 1 | PASS |
| D2: min_weight>0 blocks entry | 2 | PASS |
| Registration (4 integration points) | 5 | PASS |
| Invariants (I12, I13) | 3 | PASS |

### 3.2 Full Test Suite

**689/689 passed, 0 failed, 34 pre-existing warnings** (84.64s)

No regressions introduced.

---

## 4. Backtest Results

Data: `data/bars_btcusdt_2016_now_h1_4h_1d.csv` (2017-08 to 2026-02, 18662 H4 bars)
Config: default VTrendSMConfig (slow=120, target_vol=0.15, atr_mult=3.0)
Warmup: 365 days, mode=no_trade

| Metric | Base (31 bps) | Harsh (50 bps) | Extreme (60 bps) |
|--------|---------------|----------------|-------------------|
| **CAGR %** | 14.80 | 14.11 | 13.75 |
| **Sharpe** | 1.3895 | 1.3302 | 1.2995 |
| **Sortino** | 1.1623 | 1.1142 | 1.0894 |
| **MDD %** | 14.23 | 15.09 | 15.54 |
| **Calmar** | 1.0402 | 0.9348 | 0.8850 |
| Trades | 76 | 76 | 76 |
| Win Rate % | 39.47 | 39.47 | 39.47 |
| Profit Factor | 2.6627 | 2.5512 | 2.4780 |
| Avg Exposure | 0.1065 | 0.1065 | 0.1065 |
| Time in Market % | 34.56 | 34.56 | 34.56 |
| Fees Total $ | 1224.60 | 1782.77 | 1755.65 |
| Fee Drag %/yr | 0.68 | 1.02 | 1.02 |
| Turnover/yr | 6.83 | 6.81 | 6.80 |

**Observations**:
- Trade count, exposure, and time-in-market are cost-invariant (as expected: cost does not affect signal generation)
- CAGR degrades smoothly with cost: 14.80% → 14.11% → 13.75%
- Sharpe degrades smoothly: 1.39 → 1.33 → 1.30
- MDD worsens slightly with cost: 14.23% → 15.09% → 15.54%
- Calmar stays above 0.88 even at 60 bps extreme
- Low average exposure (10.65%) reflects vol-targeted sizing

---

## 5. Cross-Validation vs Latch

### 5.1 Methodology

Both implementations run on identical data (`data/bars_btcusdt_2016_now_h1_4h_1d.csv`, H4 bars only) with matched cost models:
- btc-spot-dev: `CostConfig(spread_bps=5.0, slippage_bps=3.0, taker_fee_pct=0.10)` → 31 bps RT
- Latch: `CostModel(fee_bps=10.0, half_spread_bps=2.5, slippage_bps=3.0)` → 15.5 bps per side → 31 bps RT

Default parameters used for both (VTrendSMConfig defaults = VTrendStateMachineParams defaults).

### 5.2 Results

| Metric | Latch | btc-spot-dev | Delta | Tolerance | Status |
|--------|-------|-------------|-------|-----------|--------|
| **CAGR %** | 14.7923 | 14.8000 | 0.0077 | < 2% | PASS |
| **Sharpe** | 1.3895 | 1.3895 | 0.0000 | < 0.05 | PASS |
| **MDD %** | 14.2313 | 14.2300 | 0.0013 | < 2% | PASS |
| **Calmar** | 1.0394 | 1.0402 | 0.0008 | < 0.05 | PASS |
| **Entries** | 76 | 76 | 0 | < 5% | PASS |
| **Avg Exposure** | 0.1065 | 0.1065 | 0.0000 | < 0.01 | PASS |
| **Total Return %** | 223.978 | 223.980 | 0.002 | < 2% | PASS |

### 5.3 Analysis

- **Sharpe**: Identical to 4 decimal places (1.3895). No divergence.
- **CAGR**: Delta 0.0077% — within rounding precision (btc-spot-dev rounds to 2 decimal places in summary.json).
- **MDD**: Delta 0.0013% — negligible.
- **Trade count**: Identical (76 entries, 76 exits). Zero entry/exit divergence.
- **Exposure**: Identical (0.1065). Vol-targeting produces same sizing.

### 5.4 Expected Differences (D4 Adaptation)

The canonical contract predicted possible rebalance differences (D4: close-price vs open-price comparison basis).
With default parameters, **zero divergence observed** because:
1. Entry/exit always bypass the rebalance threshold (separate code paths)
2. Rebalance gating uses default 5% threshold
3. With tight vol-targeted sizing and 5% threshold, boundary cases are rare in this data

The 262 trade events reported by Latch include rebalances. btc-spot-dev reports 76 trades (entry/exit pairs). The difference is architectural (btc-spot-dev counts round-trip trades, Latch counts all fill events).

---

## 6. Acceptance Criteria Verification

### 6.1 Invariants (I1–I16)

| # | Invariant | Status |
|---|-----------|--------|
| I1 | Signal timing: close → next open | PASS (engine enforces) |
| I2 | Target exposure [0, 1] | PASS (T17) |
| I3 | Two states only (FLAT, LONG) | PASS (code review) |
| I4 | Entry requires ALL conditions + weight > 0 | PASS (T9, D2 tests) |
| I5 | Exit on floor_break OR regime_break | PASS (T11, T12) |
| I6 | Adaptive floor = max(rolling_low, ema_slow - atr_mult * ATR) | PASS (T11) |
| I7 | Regime includes slope check | PASS (T19) |
| I8 | Breakout = close > rolling_high_shifted | PASS (T9) |
| I9 | Vol-target sizing = clip(target_vol / rv) | PASS (T14) |
| I10 | No signals during warmup | PASS (T10) |
| I11 | _clip_weight: NaN→0, clamp, min_weight | PASS (T8, 10 tests) |
| I12 | No cost handling in strategy | PASS (code review) |
| I13 | on_after_fill is no-op | PASS (test) |
| I14 | BARS_PER_YEAR_4H = 2190.0 | PASS (T21) |
| I15 | Config defaults match source (16 fields) | PASS (T1) |
| I16 | Auto-derivation matches source (4 formulas) | PASS (T2) |

### 6.2 Behavioral Matches (B1–B9)

| # | Behavior | Status |
|---|----------|--------|
| B1 | _ema output | PASS (T3) |
| B2 | _atr output | PASS (T4) |
| B3 | _rolling_high_shifted | PASS (T5) |
| B4 | _rolling_low_shifted | PASS (T6) |
| B5 | _realized_vol | PASS (T7) |
| B7 | _clip_weight | PASS (T8) |
| B8 | State transitions (default params) | PASS (cross-validation: 76/76) |
| B9 | Target weights (default params) | PASS (cross-validation: exposure 0.1065/0.1065) |

### 6.3 Permitted Differences (E1–E5)

| # | Permitted Difference | Observed |
|---|---------------------|----------|
| E1 | Rebalance trade count | 0 difference (with default params) |
| E2 | Rebalance bar indices | Not observable (no divergence) |
| E3 | Entry blocked at weight=0 | N/A (default min_weight=0.0) |
| E4 | VDO OHLC proxy values | N/A (VDO disabled by default) |
| E5 | slope_lookback=0 error timing | N/A (not triggered) |

---

## 7. Residual Uncertainties

| # | Uncertainty | Status |
|---|-----------|--------|
| U1 | Close-price vs open-price rebalance | **Resolved**: zero divergence with default params. |
| U2 | OHLC proxy VDO fidelity | **Deferred**: VDO disabled by default. Not relevant unless explicitly enabled. |
| U3 | min_weight>0 entry guard impact | **Tested**: D2 test confirms guard works. No impact with default min_weight=0.0. |

---

## 8. CLI Usage

```bash
# Base scenario (31 bps RT)
python -m v10.cli.backtest \
    --data data/bars_btcusdt_2016_now_h1_4h_1d.csv \
    --strategy vtrend_sm \
    --scenario base \
    --outdir out/vtrend_sm_base \
    --warmup-days 365
```

---

## 9. Bootstrap Analysis (VCBB, 2000 paths)

### 9.1 Methodology

- **Bootstrap**: Vol-Conditioned Block Bootstrap (VCBB) — preserves BTC volatility clustering
- **Paths**: 2000, block size 60, context 90, K=50 nearest neighbors
- **Cost**: harsh (50 bps RT) — same as all prior studies
- **Data**: standard research range (2019-01-01 to 2026-02-20, 365d warmup)
- **Seed**: 42 (reproducible)
- **Script**: `research/vtrend_sm_bootstrap.py`

### 9.2 Bootstrap Results

| Metric | Mean | Median | Std | 2.5% | 97.5% |
|--------|------|--------|-----|------|-------|
| **Sharpe** | 0.7767 | 0.7806 | 0.4251 | -0.0957 | 1.5830 |
| **CAGR %** | 7.77 | 7.52 | 4.86 | -1.31 | 17.75 |
| **MDD %** | 18.46 | 17.38 | 5.52 | 10.72 | 32.35 |
| **Calmar** | 0.5006 | 0.4296 | 0.3845 | -0.0443 | 1.4344 |
| **Trades** | 69.5 | 70 | 5.7 | 58 | 81 |

### 9.3 Key Probabilities

| Probability | Value |
|-------------|-------|
| P(CAGR > 0) | **95.0%** |
| P(Sharpe > 0) | 95.9% |
| P(Sharpe > 0.5) | 75.3% |
| P(MDD < 30%) | **95.7%** |
| P(MDD < 50%) | 100.0% |

### 9.4 Comparison with E0 Bootstrap

| Metric | E0 (VCBB) | SM (VCBB) | Delta | Interpretation |
|--------|-----------|-----------|-------|----------------|
| **Sharpe (median)** | 0.54 | 0.78 | +0.24 | SM higher risk-adjusted return |
| **CAGR % (median)** | 14.2 | 7.5 | -6.7 | SM lower absolute return |
| **MDD % (median)** | 61.0 | 17.4 | -43.6 | SM much lower drawdown |
| **P(CAGR > 0)** | 80.3% | 95.0% | +14.7% | SM more reliable |

**Interpretation**: SM and E0 occupy fundamentally different risk/return profiles.
SM sacrifices absolute return (CAGR 7.5% vs 14.2%) for dramatically better risk management
(MDD 17% vs 61%) and higher risk-adjusted return (Sharpe 0.78 vs 0.54). SM has 95% probability
of positive returns vs E0's 80%.

---

## 10. Sub-Period Analysis

### 10.1 Per-Year Performance

| Year | Sharpe | CAGR % | MDD % | Calmar |
|------|--------|--------|-------|--------|
| 2019 | 2.4578 | 38.08 | 7.96 | 4.7824 |
| 2020 | 2.9727 | 45.12 | 8.23 | 5.4817 |
| 2021 | 0.1695 | 1.21 | 11.16 | 0.1084 |
| 2022 | **-1.3096** | **-7.86** | 8.98 | -0.8754 |
| 2023 | 2.2756 | 28.72 | 7.57 | 3.7956 |
| 2024 | 1.3304 | 14.62 | 9.94 | 1.4712 |
| 2025 | 0.4174 | 3.27 | 6.10 | 0.5368 |

**Observations**:
- Positive Sharpe in **6/7 years** (only 2022 negative: crypto bear market)
- Per-year MDD always < 12% (even 2022 bear: 8.98%)
- Best years are trend-rich environments (2019, 2020, 2023)
- 2022 loss capped at -7.86% — vol-targeting provides drawdown protection

### 10.2 Half-Period Performance

| Period | Bars | Sharpe | CAGR % | MDD % | Calmar |
|--------|------|--------|--------|-------|--------|
| First half | 7824 | 1.7533 | 21.39 | 11.16 | 1.9157 |
| Second half | 7824 | 1.0913 | 10.80 | 9.94 | 1.0873 |

Both halves profitable with Sharpe > 1.0. No regime dependence.

### 10.3 Third-Period Performance

| Period | Bars | Sharpe | CAGR % | MDD % | Calmar |
|--------|------|--------|--------|-------|--------|
| First third | 5216 | 2.2687 | 32.93 | 10.76 | 3.0596 |
| Middle third | 5216 | 0.6124 | 5.11 | 12.03 | 0.4252 |
| Last third | 5216 | 1.1713 | 11.71 | 9.94 | 1.1783 |

All three thirds profitable. Middle third includes the 2022 bear market, which reduces CAGR but MDD remains contained at 12%.

---

## 11. Conclusion

VTREND-SM has been successfully ported from Latch to btc-spot-dev:

- **47/47 tests pass** covering all T1–T21 acceptance criteria
- **689/689 full suite tests pass** (zero regressions)
- **Cross-validation**: Sharpe identical (delta=0.0000), CAGR delta=0.008%, MDD delta=0.001%, trade count identical
- **3 cost scenarios**: Sharpe 1.30–1.39, CAGR 13.75–14.80%, MDD 14.23–15.54%
- All 9 canonical adaptations (D2–D15) implemented per contract
- Registered in all 4 integration points
- **Bootstrap (VCBB, 2000 paths)**: Sharpe median 0.78, CAGR median 7.5%, MDD median 17.4%, P(CAGR>0)=95.0%
- **Sub-period stability**: positive Sharpe in 6/7 years, all halves and thirds profitable, per-year MDD always < 12%
- **vs E0 bootstrap**: higher Sharpe (+0.24), much lower MDD (-43.6%), more reliable (P(CAGR>0) 95% vs 80%)
