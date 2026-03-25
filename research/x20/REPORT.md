# X20: Cross-Asset VTREND Portfolio — REPORT

**Date**: 2026-03-10
**Script**: `research/x20/benchmark.py`
**Verdict**: **CLOSE** — Multi-asset portfolio degrades performance vs BTC-only

---

## Executive Summary

A 14-coin VTREND portfolio with EMA(21d) regime filter was tested using three
analytical weighting schemes (EW, IV, BTC-capped). Despite meaningful cross-asset
diversification (mean ρ = 0.343), the portfolio Sharpe (best: 0.259 BC) is far
worse than BTC-only (0.735). Root cause: most altcoins have weak trend-following
alpha (Sharpe 0.28-0.65 at 50 bps) that dilutes BTC's strong signal.

**Key finding**: VTREND trend-following alpha is BTC-concentrated. Cross-asset
breadth expansion does NOT improve portfolio Sharpe at current cost assumptions.

---

## Gate Results

| Gate | Test | Condition | Result | Status |
|------|------|-----------|--------|--------|
| G0 | T0 | ≥ 3 coins pass screens | 14/14 pass | **PASS** |
| G1 | T2 | Best portfolio Sharpe > BTC-only | 0.259 < 0.735 | **FAIL** |
| G2 | T3 | WFO ≥ 75%, mean d > 0 | 1/4 wins, mean d = -0.341 | **FAIL** |
| G3 | T4 | P(d_sharpe > 0) > 60% | 88.4% | PASS* |
| G4 | T4 | Median d_mdd ≤ +5pp | -3.7pp | PASS* |

*G3/G4 pass but are **unreliable** — see Bootstrap Caveat below.

**Decision rule**: G1 FAIL → CLOSE (diversification doesn't improve Sharpe).

---

## T0: Per-Asset Full-Sample Backtest

Common period: 2020-09-22 to 2026-02-28 (~5.4 years). All 14 coins pass screens.

| Coin | Strategy | Sharpe | CAGR (%) | MDD (%) | Trades |
|------|----------|--------|----------|---------|--------|
| BTCUSDT | E5+EMA1D | **1.250** | 48.74 | 43.15 | 214 |
| ETHUSDT | E5+EMA1D | **1.153** | 56.48 | 46.86 | 209 |
| BNBUSDT | E0+EMA1D | **1.193** | 67.18 | 57.92 | 203 |
| DOGEUSDT | E0+EMA1D | **1.073** | 94.29 | 86.53 | 141 |
| SOLUSDT | E0+EMA1D | 0.914 | 46.15 | 71.40 | 130 |
| XLMUSDT | E0+EMA1D | 0.647 | 23.81 | 68.74 | 160 |
| TRXUSDT | E0+EMA1D | 0.479 | 11.69 | 74.61 | 221 |
| HBARUSDT | E0+EMA1D | 0.426 | 3.11 | 88.78 | 144 |
| ADAUSDT | E0+EMA1D | 0.418 | 6.27 | 79.84 | 181 |
| LINKUSDT | E0+EMA1D | 0.399 | 4.16 | 84.56 | 177 |
| AVAXUSDT | E0+EMA1D | 0.389 | 5.24 | 69.50 | 115 |
| XRPUSDT | E0+EMA1D | 0.350 | 2.01 | 91.05 | 171 |
| LTCUSDT | E0+EMA1D | 0.336 | 1.66 | 89.03 | 191 |
| BCHUSDT | E0+EMA1D | 0.278 | -2.10 | 78.87 | 152 |

### Distribution

- **Tier 1** (Sharpe > 1.0): BTC, ETH, BNB, DOGE — 4 coins
- **Tier 2** (Sharpe 0.5-1.0): SOL, XLM — 2 coins
- **Tier 3** (Sharpe < 0.5): 8 coins — weak alpha, high MDD

Most altcoins have Sharpe 0.28-0.48 with MDD 69-91%. These coins have positive
but marginal trend-following alpha that is consumed by cost and drawdown.

---

## T1: Cross-Asset Correlation

| Metric | Value |
|--------|-------|
| Mean pairwise ρ | 0.343 |
| Median pairwise ρ | 0.337 |
| Diversification ratio | 1.601 |
| Min ρ | 0.144 (DOGE-TRX) |
| Max ρ (non-self) | 0.597 (BTC-ETH) |

Correlation is moderate — genuine diversification potential exists. The problem
is not correlation (ρ is favorable) but the quality gap between BTC and altcoins.

Highest correlations: BTC-ETH (0.60), XRP-XLM (0.58), BTC-SOL (0.48).
Lowest: TRX vs most coins (0.14-0.24) — TRX is the most independent.

---

## T2: Portfolio Backtest (Common Period)

| Strategy | Sharpe | CAGR (%) | MDD (%) | Calmar |
|----------|--------|----------|---------|--------|
| **BTC-only** | **0.735** | **18.85** | **39.48** | **0.478** |
| BC (BTC 40%) | 0.259 | 3.12 | 54.01 | 0.058 |
| IV (inv-var) | 0.159 | -0.29 | 55.21 | -0.005 |
| EW (equal) | 0.142 | -2.07 | 61.09 | -0.034 |

**BTC-only dominates all portfolio schemes on every metric.** The portfolio
doesn't just underperform — it has higher MDD, lower CAGR, and lower Sharpe.

### Why the portfolio fails

1. **Sharpe dilution**: BTC (Sharpe 1.25) is mixed with coins averaging Sharpe ~0.50.
   Equal-weighting gives BTC only 7.1% allocation (1/14).
2. **MDD amplification**: Altcoins have MDD 69-91% vs BTC's 43%. Even BC (40% BTC)
   cannot compensate for the drawdown contribution of remaining 60%.
3. **Cost drag**: At 50 bps RT, low-alpha coins (Sharpe 0.28-0.42) lose most of their
   gross alpha to transaction costs. Their ~150-220 trades × 50 bps = 750-1100 bps
   total cost over 5.4 years.
4. **Cash drag**: When any asset is in OUT state (no position), its allocated capital
   sits idle. Low-quality coins spend more time out of position.

### BTC-only NAV on common period

BTC Sharpe drops from 1.25 (full 2017-2026 sample) to 0.735 (2020-09 to 2026-02)
because the common period excludes the 2017-2020 bull run. This is expected —
the common period is dictated by AVAX's late start date.

---

## T3: Walk-Forward Validation

| Fold | Year | BTC Sharpe | Portfolio Sharpe | d_Sharpe | d_MDD | Win? |
|------|------|-----------|-----------------|----------|-------|------|
| 1 | 2022 | -0.978 | -1.525 | -0.547 | +2.99 | NO |
| 2 | 2023 | 1.314 | 1.325 | +0.010 | -3.15 | YES |
| 3 | 2024 | 1.555 | 1.394 | -0.162 | +2.52 | NO |
| 4 | 2025 | 0.048 | -0.617 | -0.665 | +9.34 | NO |

**Win rate: 1/4 (25%). Mean d_sharpe: -0.341. G2 FAIL.**

Portfolio is worse in bear (2022), worse in flat (2025), worse in bull (2024),
and essentially tied in mild bull (2023). No regime favors the portfolio.

---

## T4: Bootstrap (500 VCBB)

| Metric | Value |
|--------|-------|
| P(d_sharpe > 0) | 88.4% |
| Median portfolio Sharpe | 1.228 |
| Median BTC Sharpe | 0.639 |
| Median d_mdd | -3.7 pp |

### Bootstrap Caveat — METHODOLOGY LIMITATION

The bootstrap results **contradict real data**: median portfolio Sharpe (1.228) is
4.7× higher than actual portfolio Sharpe (0.259). P(d_sharpe > 0) = 88.4% while
the real portfolio clearly loses.

**Root cause**: The VCBB block bootstrap samples blocks independently per asset.
Even with shared `path_seed` per iteration, the sampled blocks don't preserve
the real cross-asset crisis correlation structure. In reality:
- During crashes (2022 Q2, 2022 Q4), ALL crypto assets decline simultaneously (ρ → 1)
- The bootstrap breaks this dependency, allowing some assets to be in "good" blocks
  while others are in "bad" blocks, creating artificial diversification

A proper joint bootstrap would sample DATE INDICES first, then extract ALL assets
for those dates (preserving the full cross-sectional correlation). The current
implementation samples VCBB paths independently per coin, which underestimates
crash co-movement.

**G3 and G4 results are therefore unreliable and should be disregarded.**

---

## T5: Drawdown Analysis

| Metric | BTC-only | Portfolio (EW) |
|--------|----------|----------------|
| MDD | 39.48% | 61.09% |
| d_MDD | — | +21.61 pp (worse) |
| Max simultaneous DD | — | 14/14 coins |

All 14 coins reached maximum drawdown simultaneously at some point in the sample.
Crypto drawdowns are near-perfectly correlated during crises — the diversification
benefit vanishes exactly when it's needed most.

Per-coin MDD range: 39.5% (BTC) to 91.1% (XRP). Median altcoin MDD: 74.6%.

---

## T6: Comparison Table

| Strategy | Sharpe | CAGR (%) | MDD (%) | Calmar | Assets |
|----------|--------|----------|---------|--------|--------|
| BTC-only E5+EMA1D | **0.735** | **18.85** | **39.48** | **0.478** | 1 |
| Portfolio EW | 0.142 | -2.07 | 61.09 | -0.034 | 14 |
| Portfolio IV | 0.159 | -0.29 | 55.21 | -0.005 | 14 |
| Portfolio BC (40% BTC) | 0.259 | 3.12 | 54.01 | 0.058 | 14 |

---

## Root Cause Analysis

### Why the Fundamental Law of Active Management doesn't apply here

The FLAM states IR = IC × √BR. Increasing breadth (BR) increases IR *only if*
the new bets have comparable IC (information coefficient) to existing bets.

In this case:
- **BTC IC is high**: Sharpe 1.25 on full sample, 0.735 on common period
- **Altcoin IC is low**: Median Sharpe 0.42 (3× lower than BTC)
- **Adding low-IC bets dilutes portfolio IC**

The FLAM improvement requires √BR scaling to overcome the IC dilution. With
BTC Sharpe 2.9× the median altcoin Sharpe, you'd need BR > 8.4 **independent**
high-IC bets to compensate — but only 4/14 coins have Sharpe > 1.0, and their
pairwise ρ (0.40-0.60) means they aren't truly independent.

### When would multi-asset work?

1. **Lower cost**: At 10-15 bps RT, altcoin Sharpe would increase (X22 will test this)
2. **Better altcoin strategies**: Per-coin parameter optimization (adds DOF)
3. **Selective portfolio**: Only Tier 1 coins (BTC, ETH, BNB, DOGE) — but still
   requires validation that the subset outperforms BTC-only
4. **Non-crypto assets**: Traditional assets (commodities, FX) with trend-following
   alpha and lower correlation to BTC

---

## Conclusion

**CLOSE** — Cross-asset VTREND portfolio does not improve over BTC-only deployment.

Key findings:
1. All 14 coins have positive trend-following Sharpe with EMA regime filter (G0 PASS)
2. Cross-asset correlation is moderate (mean ρ = 0.343) — diversification potential exists
3. Despite favorable correlation, altcoin alpha is too weak to survive dilution into portfolio
4. BTC-only Sharpe (0.735) >> best portfolio Sharpe (0.259 BC) — 2.8× gap
5. WFO confirms: portfolio loses in 3/4 folds
6. Portfolio MDD (54-61%) is worse than BTC-only MDD (39.5%)
7. Bootstrap is unreliable due to broken cross-asset correlation structure

**Implication for production**: Deploy BTC-only. The path to higher portfolio Sharpe
is NOT breadth expansion with generic VTREND on altcoins. Focus instead on:
- Cost reduction (X22) to capture more of BTC's gross alpha
- Conviction sizing (X21) to improve geometric growth rate
- Or fundamentally different alpha sources for non-BTC assets
