# P3.4 — Evaluation Report: X0 Phase 3 (Frozen Vol Sizing)

> **SUPERSEDED (2026-03-09):** Strategy recommendations below predate framework
> reform. E5+EMA1D21 is now PRIMARY (PROMOTE). X0 is HOLD (PSR < 0.95).
> See `CHANGELOG.md` (2026-03-09).

## SUMMARY

X0 Phase 3 (vol-sized entry) evaluated against 6 baselines across 3 cost scenarios with 500-path VCBB bootstrap. Phase 3 ranks #1 in Sharpe, MDD, and Calmar at harsh cost, but CAGR drops ~63% due to ~31% average exposure. 6/7 promotion gates PASS; G3 (Calmar all-costs) fails on smart scenario by 2.1%. Verdict: HOLD as alternative risk profile, not strict improvement.

## BACKTEST_COMPARISON_TABLE (harsh scenario)

| Rank | Strategy | Sharpe | CAGR% | MDD% | Calmar | Trades |
|------|----------|--------|-------|------|--------|--------|
| 1 | **X0_VOLSIZE** | **1.6591** | 21.97 | **14.51** | **1.5134** | 199 |
| 2 | E5_EMA21 / X0_E5EXIT | 1.4320 | 59.96 | 41.57 | 1.4422 | 199 |
| 3 | E5 | 1.3647 | 57.04 | 40.26 | 1.4166 | 225 |
| 4 | E0_EMA21 / X0 | 1.3360 | 55.32 | 41.99 | 1.3175 | 186 |
| 5 | E0 | 1.2765 | 52.68 | 41.53 | 1.2684 | 211 |

## BOOTSTRAP_RESULTS_TABLE (500 VCBB paths, block=60)

| Strategy | Sharpe_med | [p5, p95] | CAGR_med% | MDD_med% | P(CAGR>0) | P(Sharpe>0) |
|----------|------------|-----------|-----------|----------|-----------|-------------|
| **X0_VOLSIZE** | **0.3835** | [-0.40, 1.07] | 3.32 | **21.78** | **0.760** | **0.788** |
| E0 | 0.3365 | [-0.38, 0.98] | 5.44 | 70.49 | 0.620 | 0.662 |
| E5 | 0.2907 | [-0.42, 0.94] | 3.79 | 69.42 | 0.590 | 0.632 |
| E0_EMA21 / X0 | 0.2608 | [-0.43, 0.93] | 3.17 | 62.18 | 0.602 | 0.630 |
| E5_EMA21 / X0_E5EXIT | 0.2328 | [-0.47, 0.92] | 2.27 | 62.54 | 0.568 | 0.600 |

X0_VOLSIZE: best bootstrap Sharpe, best MDD (3x lower than next), highest P(CAGR>0) and P(Sharpe>0).

## PHASE3_DELTA_TABLE (P3 - P2, engine-based attribution)

| Scenario | dSharpe | dCAGR% | dMDD% | dCalmar | dTrades | dWR% | dPF | dExpo |
|----------|---------|--------|-------|---------|---------|------|-----|-------|
| smart | +0.2214 | -50.20 | -24.84 | -0.0294 | +0 | +0.00 | +0.6706 | -0.2967 |
| base | +0.2257 | -43.99 | -25.67 | +0.0264 | +0 | +0.00 | +0.6387 | -0.2966 |
| harsh | +0.2302 | -37.80 | -27.14 | +0.0831 | +0 | +0.00 | +0.5993 | -0.2966 |

Timing parity: 186/186 entry+exit timestamps identical. PnL sign parity: 186/186. Win rate parity: 44.6%.
Mechanism: PURE SIZING DELTA (timing unchanged, only position size changes).

## EXPOSURE_STATS_TABLE

| Metric | Value |
|--------|-------|
| Trades | 199 |
| Weight min | 0.0951 |
| Weight p5 | 0.1474 |
| Weight p25 | 0.2250 |
| Weight median | 0.2896 |
| Weight mean | 0.3109 |
| Weight p75 | 0.3834 |
| Weight p95 | 0.5190 |
| Weight max | 0.9055 |
| Weight std | 0.1223 |
| RV min (at entry) | 0.1656 |
| RV median | 0.5179 |
| RV mean | 0.5602 |
| RV max | 1.5773 |
| RV > target_vol | 199/199 (100%) |
| RV < vol_floor | 0/199 (0%) |

Average exposure ~31%: Phase 3 is structurally a low-leverage strategy. All entries have rv > target_vol (0.15), so vol_floor (0.08) is never triggered.

## VOLATILITY_BUCKET_ANALYSIS

| Bucket | RV range | N | Avg_Wt | P2_PnL | P3_PnL | Ratio |
|--------|----------|---|--------|--------|--------|-------|
| low | [0.00, 0.30) | 15 | 0.575 | -$12,179 | -$413 | 0.034 |
| medium | [0.30, 0.60) | 113 | 0.348 | $345,327 | $26,880 | 0.078 |
| high | [0.60, 1.00) | 60 | 0.209 | $53,060 | $10,702 | 0.202 |
| crisis | [1.00, inf) | 11 | 0.129 | $40,147 | $921 | 0.023 |

Insights:
1. Medium-vol regime (0.30-0.60 annualized) dominates: 113/199 trades, 81% of P2 PnL.
2. Vol-sizing correctly reduces crisis exposure (weight 0.129) — protective behavior confirmed.
3. Low-vol bucket (15 trades): P2 lost $12K, P3 lost only $413 — vol-sizing reduces both upside AND downside.
4. Crisis bucket shows extreme compression: PnL ratio 0.023 (97.7% reduction).

## PROMOTION_DECISION

### Gates (7)

| # | Gate | Result | Detail |
|---|------|--------|--------|
| G1 | Sharpe > P2 (all costs) | PASS | smart +0.22, base +0.23, harsh +0.23 |
| G2 | MDD < P2 (all costs) | PASS | smart -24.8pp, base -25.7pp, harsh -27.1pp |
| G3 | Calmar > P2 (all costs) | **FAIL** | smart: 1.964 < 2.007 (-2.1%) |
| G4 | Boot P(CAGR>0) >= 70% | PASS | 76.0% |
| G5 | Boot P(Sharpe>0) >= 70% | PASS | 78.8% |
| G6 | Trade count = P2 | PASS | 199 = 199 |
| G7 | Boot MDD med < P2 | PASS | 21.78% < 62.54% |

### G3 Failure Analysis
G3 fails only on smart (lowest cost) scenario: P3 Calmar = 1.9639 vs P2 Calmar = 2.0066.
Root cause: at low costs, P2's CAGR advantage (75.87%) dominates the Calmar ratio despite P2's higher MDD (37.81%). At base and harsh, the MDD improvement is large enough for P3 Calmar to exceed P2.

### Verdict: **HOLD**

Phase 3 is NOT a strict improvement over Phase 2. It represents an **alternative risk profile**:
- **Dominates on**: Sharpe (+0.23), MDD (-27pp), bootstrap robustness (P(CAGR>0) 76% vs 57%)
- **Trades off**: CAGR (-38pp at harsh), Calmar marginal at low cost
- **Structural**: 31% average exposure = low-leverage variant of the same timing signal

Phase 3 is a valid **risk-adjusted allocation layer** but NOT a Phase 2 replacement. Both strategies use identical timing; Phase 3 simply invests less per trade based on ambient volatility.

## RECOMMENDATION_FINAL_X0

1. **Phase 2 (X0_E5EXIT) remains primary**: highest CAGR, proven alpha, identical timing to Phase 3
2. **Phase 3 (X0_VOLSIZE) valid for low-risk allocation**: best Sharpe/MDD profile, bootstrap-robust
3. **Not mutually exclusive**: Phase 3 = Phase 2 + risk overlay. Allocator can switch between them based on target risk budget
4. **No further parameter tuning recommended**: target_vol=0.15 is the natural SM/LATCH default, and vol_floor=0.08 is never triggered on BTC data

## DEVIATION_FROM_SPEC

None. All spec requirements met:
- 7 strategies compared across 3 cost scenarios
- VCBB bootstrap with identical settings (500 paths, block=60, seed=42)
- Engine-based attribution with timing parity confirmation
- Exposure stats and vol bucket analysis
- Automated promotion decision with 7 gates

## OUTPUTS

- `research/x0/p3_4_benchmark.py` (benchmark script)
- `research/x0/p3_4_results.json` (full results)
- `research/x0/p3_4_backtest_table.csv`
- `research/x0/p3_4_bootstrap_table.csv`
- `research/x0/p3_4_delta_table.csv`
- `research/x0/p3_4_exposure_stats.csv`
- `research/x0/p3_4_vol_buckets.csv`
- `research/x0/search_log.md` (updated with P3.4 section)

## COMMANDS_RUN

```
python research/x0/p3_4_benchmark.py    # 240.1s, all T1-T4 + promotion
```

## NEXT_READY

P3.4 evaluation complete. Phase 3 verdict: HOLD (alternative risk profile).
Not proceeding.
