# X33: Execution Cost Analysis Report

**Signals analyzed**: 372
**With aggTrades data**: 372

## 1. Effective Spread (±1 min window)

| Metric | Entry | Exit | All |
|--------|-------|------|-----|
| Median | 0.28 bps | 0.33 bps | 0.31 bps |
| Mean | 0.52 bps | 0.80 bps | 0.66 bps |
| P75 | 1.25 bps | 1.46 bps | 1.33 bps |
| P95 | 3.96 bps | 6.27 bps | 4.81 bps |

## 2. VWAP Slippage by Order Size

| Size | Entry median | Entry P75 | Exit median | Exit P75 |
|------|-------------|-----------|-------------|----------|
| $10k | -0.27 bps | 1.46 bps | -1.96 bps | 0.47 bps |
| $50k | -0.41 bps | 1.24 bps | -1.54 bps | 0.65 bps |
| $100k | -0.54 bps | 1.30 bps | -1.51 bps | 0.87 bps |

## 3. Total Estimated Cost Per Side (commission + spread/2 + slippage)

| Size | Entry median | Exit median | RT median | RT P75 |
|------|-------------|-------------|-----------|--------|
| $10k | 8.1 bps | 8.0 bps | 16.8 bps | 19.0 bps |
| $50k | 8.1 bps | 8.0 bps | 16.8 bps | 18.9 bps |
| $100k | 8.1 bps | 8.1 bps | 16.9 bps | 18.9 bps |

## 4. Entry vs Exit Asymmetry

| Metric | Entry | Exit | Ratio (Exit/Entry) |
|--------|-------|------|-------------------|
| Spread | 0.28 bps | 0.33 bps | 1.17x |
| Volatility | 0.19 bps | 0.27 bps | 1.44x |

## 5. Overlay Implications (X22 Re-evaluation)

Using median RT cost from Section 3 above, look up X22 cost curve:

| Cost RT (bps) | E5+EMA1D21 Sh | X18 ΔSh | X14D ΔSh | Verdict |
|---------------|---------------|---------|----------|---------|
| 15 | 1.670 | -0.032 | -0.174 | Skip both |
| 20 | 1.636 | -0.023 | -0.157 | Skip both |
| 25 | 1.602 | -0.013 | -0.140 | Skip both |
| 30 | 1.568 | -0.004 | -0.123 | Skip both |
| 35 | 1.534 | +0.000 | -0.089 | X18 neutral |
| 40 | 1.500 | +0.015 | -0.089 | X18 helps |
| 50 | 1.432 | +0.034 | -0.054 | X18 helps |
| 75 | 1.261 | +0.082 | +0.031 | Both help |

**Compare your median RT from Section 3 against this table to determine overlay recommendation.**
