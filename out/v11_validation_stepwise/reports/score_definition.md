# Score Definition — Trích xuất từ code

## 1. Objective Score Formula

**File:** `v10/research/objective.py:31-37`

```python
score = (
    2.5 * cagr
    - 0.60 * max_dd
    + 8.0 * max(0.0, sharpe)
    + 5.0 * max(0.0, min(pf, 3.0) - 1.0)
    + min(n_trades / 50.0, 1.0) * 5.0
)
```

### Thành phần và weights:

| # | Thành phần | Weight | Input key | Đơn vị | Ghi chú |
|---|-----------|--------|-----------|--------|---------|
| 1 | CAGR | +2.5 | `cagr_pct` | % | CAGR tính trên toàn kỳ |
| 2 | Max Drawdown | -0.60 | `max_drawdown_mid_pct` | % | Penalty, mid-price DD |
| 3 | Sharpe | +8.0 | `sharpe` | annualized | `max(0, sharpe)` — chỉ thưởng, không phạt |
| 4 | Profit Factor | +5.0 | `profit_factor` | ratio | `max(0, min(pf, 3)-1)` — cap tại 3.0, shift -1 |
| 5 | Trade count | +5.0 | `trades` | count | `min(n/50, 1)*5` — ramp từ 0→5, bão hòa ≥50 trades |

### Rejection:

`v10/research/objective.py:21` — Nếu `n_trades < 10`: return `-1,000,000.0`

### Không có trong score:
- **Không có** regime-specific penalty (TOPPING, BULL, etc.)
- **Không có** turnover/fees penalty
- **Không có** Sortino, Calmar
- Regime check nằm trong Decision Gate (`v10/research/decision.py`), không phải objective score

## 2. Cost Scenarios — "Harsh" = 50 bps round-trip

**File:** `v10/core/types.py:46-77`

### CostConfig formula (`types.py:53-55`):

```python
per_side_bps = spread_bps / 2.0 + slippage_bps + taker_fee_pct * 100.0
round_trip_bps = per_side_bps * 2.0
```

### 3 scenarios (`types.py:66-70`):

| Scenario | spread_bps | slippage_bps | taker_fee_pct | per_side_bps | **round_trip_bps** |
|----------|-----------|-------------|--------------|-------------|-------------------|
| **smart** | 3.0 | 1.5 | 0.035% | 6.5 | **13.0 bps (0.13%)** |
| **base** | 5.0 | 3.0 | 0.100% | 15.5 | **31.0 bps (0.31%)** |
| **harsh** | 10.0 | 5.0 | 0.150% | 25.0 | **50.0 bps (0.50%)** |

### Vì sao "harsh" = 50 bps:

- `spread_bps=10`: giả định spread rộng (thin orderbook, volatile market)
- `slippage_bps=5`: market order slip cao (aggressive taker)
- `taker_fee_pct=0.150%` = 15 bps: fee tier cao nhất trên Binance taker

Tổng: `2 × (10/2 + 5 + 15) = 2 × 25 = 50 bps per round trip`

Đây là worst-case execution cost. Nếu strategy profitable dưới 50 bps/RT, nó có buffer lớn cho thực tế (Binance VIP taker ~ 7.5 bps).

## 3. Score decomposition example

Lấy V10 baseline, harsh scenario (score = 88.94):

```
CAGR component:    2.5 × 37.26          = +93.15
MDD penalty:      -0.60 × 36.28         = -21.77
Sharpe bonus:      8.0 × max(0, 1.151)  = +9.21
PF bonus:          5.0 × max(0, min(1.669,3)-1) = +3.35
Trade bonus:       min(103/50, 1) × 5   = +5.00
                                    TOTAL = +88.94  ✓
```

V11 WFO-opt, harsh scenario (score = 90.52):

```
CAGR component:    2.5 × 37.83          = +94.58
MDD penalty:      -0.60 × 36.28         = -21.77
Sharpe bonus:      8.0 × max(0, 1.168)  = +9.34
PF bonus:          5.0 × max(0, min(1.675,3)-1) = +3.37
Trade bonus:       min(103/50, 1) × 5   = +5.00
                                    TOTAL = +90.52  ✓
```

Delta phân tích:
- CAGR: +1.43 (+94.58 - 93.15)
- Sharpe: +0.13
- PF: +0.02
- MDD: 0.00 (giống hệt)
- Trades: 0.00
- **Total: +1.58** (khớp với observed +1.59, sai số rounding)
