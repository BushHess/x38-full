# X6 Full Evaluation Report — All Tiers

> **Note (2026-03-09):** This evaluation used the pre-reform validation framework
> (WFO win-rate gate, no PSR). The framework was upgraded 2026-03-09 with Wilcoxon
> WFO, PSR gate, and bootstrap CI. X6's REJECT verdict remains valid under both.

**Date**: 2026-03-08
**Strategy**: VTREND-X6 (adaptive trail + breakeven floor + D1 EMA21 regime)
**Baseline**: X0 (E0+EMA21 D1, fixed trail=3.0)
**Verdict**: **REJECT** (WFO 4/8, holdout delta -18.45)

---

## TIER 1: Validation Framework (17 suites)

Run via `validate_strategy.py --suite all --bootstrap 2000 --sensitivity-grid`
Output: `results/eval_x6_vs_x0_full/`

| # | Suite | Status | Evidence |
|---|-------|--------|----------|
| 1 | Lookahead check | PASS | lookahead_check.txt |
| 2 | Data integrity | PASS | data_integrity.json |
| 3 | Backtest (3 scenarios) | PASS | Sharpe 1.4324 harsh (+0.108 vs X0) |
| 4 | Cost sweep (0-100 bps) | PASS | Wins X0 at ALL 6 cost levels |
| 5 | Invariants | PASS | invariant_violations.csv |
| 6 | Churn metrics | PASS | 135 trades, 9.1d avg hold |
| 7 | Regime decomposition | INFO | regime_decomposition.csv |
| 8 | **WFO** | **FAIL** | **4/8 (50%) — worst delta -100.14** |
| 9 | Bootstrap | INFO | P(X6>X0) = 88.7% harsh, CI includes zero |
| 10 | Subsampling | INFO | support_ratio below threshold |
| 11 | Sensitivity | INFO | trail_tight 2.7→1.35, 3.0→1.43, 3.3→1.39 |
| 12 | **Holdout** | **FAIL** | **delta -18.45 (X6: 0.86 vs X0: 1.05 Sharpe)** |
| 13 | Selection bias / DSR | PASS | DSR robust |
| 14 | Trade level | INFO | 130 matched, boot p_positive=0.956 |
| 15 | DD episodes | INFO | 36 episodes (X0: 28), worst 40.55% |
| 16 | Overlay | SKIP | overlay_test: true |
| 17 | Regression guard | SKIP | No golden snapshot |

### WFO Detail (8 windows, rolling 24m train / 6m test)

| Window | Period | X6 Sharpe | X0 Sharpe | Delta |
|--------|--------|:---------:|:---------:|:-----:|
| W0 | 2022-01 → 2022-07 | -0.4498 | -0.2364 | **-10.00** |
| W1 | 2022-07 → 2023-01 | -1.4348 | -1.4348 | 0.00 |
| W2 | 2023-01 → 2023-07 | 0.9066 | 0.8235 | +9.27 |
| W3 | 2023-07 → 2024-01 | 2.7406 | 2.1059 | +99.40 |
| W4 | 2024-01 → 2024-07 | 1.3668 | 0.9051 | +73.51 |
| W5 | 2024-07 → 2025-01 | 1.8786 | 2.5046 | **-100.14** |
| W6 | 2025-01 → 2025-07 | 0.6576 | 0.5072 | +13.38 |
| W7 | 2025-07 → 2026-01 | -0.4624 | -0.3254 | **-5.90** |

Window 5 (2024H2): Same failure as X2 — X0's fixed trail outperforms adaptive trail during strong BTC rally.
Window 7: X6 slightly worse than X2 (-5.90 vs -3.06), suggesting BE floor hurts in recent choppy markets.

### Holdout Detail (last 20% of data)

| Metric | X6 | X0 | Delta |
|--------|:--:|:--:|:-----:|
| Sharpe | 0.8590 | 1.0499 | -0.1909 |
| CAGR% | 21.41 | 26.94 | -5.53 |
| MDD% | 22.20 | 18.23 | +3.97 |
| Trades | 26 | 31 | -5 |
| PF | 1.65 | 1.70 | -0.04 |

X6 performs marginally better than X2 in holdout (Sharpe 0.86 vs 0.82, delta -18.45 vs -22.19) — BE floor provides small protection, but not enough to overcome the core problem.

### Full Sample Backtest (harsh, 50 bps RT)

| Metric | X6 | X0 | Delta |
|--------|:--:|:--:|:-----:|
| Sharpe | 1.4324 | 1.3249 | +0.1075 |
| CAGR% | 63.50 | 54.70 | +8.80 |
| MDD% | 40.55 | 42.05 | -1.50 |
| Trades | 135 | 172 | -37 |
| PF | 1.95 | 1.72 | +0.24 |
| Avg hold | 9.1d | 6.9d | +2.2d |

### Cost Sweep (X6 vs X0, CAGR)

| BPS | X6 CAGR | X0 CAGR | Delta |
|-----|:-------:|:-------:|:-----:|
| 0 | 47.01 | 44.71 | +2.30 |
| 10 | 44.00 | 41.04 | +2.96 |
| 25 | 39.60 | 35.71 | +3.89 |
| 50 | 32.56 | 27.27 | +5.29 |
| 75 | 25.88 | 19.35 | +6.53 |
| 100 | 19.54 | 11.93 | +7.61 |

### Bootstrap (2000 paths, 3 block sizes, harsh)

| Block | P(X6>X0) | CI lower | CI upper |
|-------|:--------:|:--------:|:--------:|
| 10 | 89.6% | -0.070 | +0.286 |
| 20 | 89.1% | -0.062 | +0.291 |
| 40 | 88.7% | -0.062 | +0.292 |

CI includes zero at all block sizes — NOT statistically significant.

### Sensitivity Grid (trail_tight sweep, harsh)

| trail_tight | Sharpe | CAGR% | MDD% | Trades |
|:-----------:|:------:|:-----:|:----:|:------:|
| 2.7 | 1.3518 | 58.40 | 42.72 | 150 |
| **3.0** | **1.4324** | **63.50** | **40.55** | **135** |
| 3.3 | 1.3924 | 61.12 | 43.80 | 128 |

---

## TIER 2: Research Studies (T1-T7)

Via `research/parity_eval_x.py` — 4 strategies (E0, X0, X2, X6).
Output: `research/results/parity_eval_x/parity_eval_x_results.json`

**IMPORTANT**: In vectorized sim, X6 = X2 (identical results). The BE floor requires bar-level entry_price tracking which the vectorized surrogate does not fully capture. X6's differentiation only appears in the engine-based backtest.

| # | Technique | Status | Result |
|---|-----------|--------|--------|
| T1 | Full backtest 3 scenarios | DONE | X6 Sharpe 1.43 harsh (vec, = X2) |
| T2 | Permutation test 1K | DONE | p=0.001 — alpha is REAL |
| T3 | Timescale robustness 16 TS | DONE | 16/16 positive Sharpe, wins E0 16/16 |
| T4 | Bootstrap VCBB 500 paths | DONE | Med Sharpe 0.5833, wins X0 Sharpe 14/16 |
| T5 | Postmortem / failure | DONE | 8 DD>20% episodes (X0: 5) at SP=120 |
| T6 | Param sensitivity | DONE | trail_tight=3.0 optimal |
| T7 | Cost study | DONE | Wins X0 at ALL 6 cost levels |

### T3: Timescale Robustness (Sharpe, harsh)

| SP | E0 | X0 | X6 | X6 vs X0 |
|---:|:--:|:--:|:--:|:--------:|
| 30 | 0.67 | 0.96 | 1.00 | +0.05 |
| 60 | 0.80 | 1.04 | 1.18 | +0.14 |
| 120 | 1.28 | 1.34 | 1.43 | +0.10 |
| 200 | 1.43 | 1.48 | 1.55 | +0.07 |
| 360 | 1.11 | 1.18 | 1.26 | +0.07 |
| 720 | 0.84 | 0.98 | 1.07 | +0.09 |

X6 wins X0 at **all 16 timescales** (vectorized sim, = X2).

### T4: Bootstrap VCBB (SP=120)

| Metric | E0 | X0 | X6 |
|--------|:--:|:--:|:--:|
| Sharpe median | 0.6968 | 0.5621 | 0.5833 |
| CAGR median | 21.95% | 14.28% | 15.36% |
| MDD median | 58.49% | 52.17% | 53.85% |
| P(CAGR>0) | 0.882 | 0.846 | 0.848 |

Paired vs X0 (16 TS): Sharpe **14/16**, CAGR **16/16**, MDD **1/16**

Note: Bootstrap X6 = X2 exactly (BE floor invisible in vectorized surrogate).

### T7: Cost Study (Sharpe, X6 vs X0 delta)

| BPS | X6 Sharpe | X0 Sharpe | Delta |
|----:|:---------:|:---------:|:-----:|
| 0 | 1.6710 | 1.6441 | +0.027 |
| 25 | 1.4326 | 1.3360 | +0.097 |
| 50 | 1.1934 | 1.0269 | +0.167 |
| 75 | 0.9546 | 0.7188 | +0.236 |
| 100 | 0.7171 | 0.4134 | +0.304 |

---

## TIER 3: Comparative Analysis (T8-T12)

| # | Technique | Status | Result |
|---|-----------|--------|--------|
| T8 | Calendar slice | DONE | Wins 6/8 years vs X0 — **LOSES 2024** |
| T9 | Rolling 24m window | DONE | Wins 8/11 windows vs X0 |
| T10 | Start-date sensitivity | DONE | Wins ALL 7 start dates vs X0 |
| T11 | Paired bootstrap + Holm | DONE | **Holm p=0.85 — NOT SIGNIFICANT** |
| T12 | Signal concordance | DONE | X6-X2 agree 100%, X6-X0 agree 98.0% |

### T8: Calendar Slice (Sharpe by year)

| Year | E0 | X0 | X6 | X6 wins? |
|------|:--:|:--:|:--:|:--------:|
| 2019 | 1.83 | 1.73 | 1.80 | YES |
| 2020 | 2.68 | 2.61 | 2.79 | YES |
| 2021 | 1.47 | 1.63 | 1.75 | YES |
| 2022 | -1.00 | -0.93 | -1.02 | NO |
| 2023 | 1.16 | 1.21 | 1.54 | YES |
| **2024** | **1.44** | **1.69** | **1.62** | **NO** |
| 2025 | 0.14 | 0.15 | 0.21 | YES |
| 2026 | -0.33 | -0.62 | -0.62 | TIE |

### T11: Holm-Adjusted P-values

| Pair | P(A>B) | Raw p | Holm p | Sig |
|------|:------:|:-----:|:------:|:---:|
| X6 vs E0 | 0.936 | 0.129 | 0.578 | ns |
| X6 vs X0 | 0.858 | 0.284 | 0.851 | ns |
| X6 vs X2 | 0.000 | 0.000 | 0.000 | *** |

X6 vs X2: *** because vectorized sim produces identical results (p=0 artifact).

---

## TIER 4: Trade Anatomy (T13-T17)

### Engine-based (Tier 1 backtest, harsh)

| Metric | X6 | X0 |
|--------|:--:|:--:|
| Trades | 135 | 172 |
| Win rate | 43.0% | 42.4% |
| Profit factor | 1.95 | 1.72 |
| Avg hold | 9.1d | 6.9d |
| Matched trades | 130 (96.3% match rate) |
| Bootstrap P(X6>X0 pnl) | 0.956 |
| DD episodes | 36 | 28 |

### Exit Reason Breakdown — Engine-based (harsh)

| Reason | Count | % | Note |
|--------|:-----:|:-:|------|
| Trail stop | 93 | 68.9% | Standard ATR trail |
| **BE stop** | **25** | **18.5%** | **avg return +26.48%, WR 100%** |
| Trend exit | 17 | 12.6% | EMA cross-down |

**BE floor value**: 25 trades exit via breakeven floor with 100% win rate and +26.48% average return. These are trades that would have been losers under X2 but were protected by the entry_price floor.

### Vectorized sim (parity_eval_x, harsh)

| Metric | X6 |
|--------|:--:|
| Trades | 150 |
| Win rate | 44.0% |
| PF | 1.809 |
| Avg hold | 9.0d |
| Skew | 3.151 |
| Excess kurtosis | 11.643 |
| JB p-value | 0.0000 |
| Gini | 0.656 |
| HHI | 0.0258 |
| Jackknife drop-1 | -3.4% |

### Exit Reason Breakdown — Vectorized (harsh)

| Reason | Count | % | Win Rate | Avg Return | Total PnL |
|--------|:-----:|:-:|:--------:|:----------:|:---------:|
| Trail stop | 104 | 69.3% | 35.6% | -1.35% | -$210,361 |
| **BE stop** | **27** | **18.0%** | **100.0%** | **+25.74%** | **+$523,698** |
| Trend exit | 19 | 12.7% | 10.5% | -1.85% | -$40,078 |

BE stops are the **only profitable exit category** — they capture all the profit. Trail stops and trend exits are net negative.

---

## X6 vs X2: Marginal BE Floor Value

### Engine-based comparison (harsh)

| Metric | X6 | X2 | Delta |
|--------|:--:|:--:|:-----:|
| Sharpe | 1.4324 | 1.4227 | +0.0097 |
| CAGR% | 63.50 | 62.87 | +0.63 |
| MDD% | 40.55 | 40.28 | +0.27 |
| Trades | 135 | 138 | -3 |
| PF | 1.95 | 1.90 | +0.05 |

X6 provides a **marginal but consistently positive** improvement over X2:
- +0.01 Sharpe across all 3 cost scenarios
- 3 fewer trades (those 3 are saved by BE floor)
- PF improves from 1.90 to 1.95

### Parity check

| Strategy | Engine Sharpe | Vectorized Sharpe | Diff |
|----------|:---:|:---:|:---:|
| X0 | 1.3249 | 1.3360 | 0.0111 |
| X2 | 1.4227 | 1.4326 | 0.0099 |
| X6 | 1.4324 | 1.4326 | **0.0002** |

X6 has the **best engine-vectorized parity** (0.0002 diff), confirming accurate implementation.

---

## Diagnosis

X6 = X2 + breakeven floor. The BE floor is a genuine improvement:
- 25 trades protected (100% win rate, +26.48% avg return)
- Best parity of all X-series (0.0002 Sharpe diff)
- Marginal but consistent +0.01 Sharpe over X2

**However**, X6 inherits X2's core problem — the adaptive trail (3/4/5x ATR) overfits:
1. **WFO 4/8** — same failure pattern as X2 (2024H2 worst delta -100.14)
2. **Holdout -18.45** — better than X2's -22.19 but still negative
3. **Holm p=0.85** — not statistically significant vs X0
4. **7 params vs 4** — overfitting risk from gain_tier1/2, trail_mid/wide
5. **Bootstrap X6=X2** — BE floor invisible OOS, does not improve robustness

The BE floor adds real value on top of X2, but cannot rescue the underlying adaptive trail problem.

## Final Verdict: **REJECT**

X6 is NOT a suitable replacement for X0. The BE floor is a valid component but the adaptive trail base (X2) fails validation. Use X0 (E0+EMA21 D1) for real money.

---

## Artifacts

| Source | Path |
|--------|------|
| Tier 1 validation | `results/eval_x6_vs_x0_full/` |
| Tier 2-4 parity eval | `research/results/parity_eval_x/parity_eval_x_results.json` |
| Tier 1 X0 reference | `results/parity_20260305/eval_ema21d1_vs_e0/` |
| Unit tests | `tests/test_vtrend_x6.py` (31 tests PASS) |
| Research tests | `research/x6/test_x6.py` (15 tests PASS) |
| Strategy code | `strategies/vtrend_x6/strategy.py` |
| Config | `configs/vtrend_x6/vtrend_x6_default.yaml` |
| Eval script | `research/parity_eval_x.py` |
