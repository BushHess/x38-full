# Task B: Port Vol Compression to v10 Strategy + Full Validation

## Overview

x39 exp42 showed vol compression (vol_ratio_5_20 < 0.7) passes WFO 4/4 in
simplified replay. This task ports the mechanism to a real v10 strategy and
runs the authoritative 7-gate validation pipeline.

x39's result is DIAGNOSTIC. This validation is AUTHORITATIVE.

## Step 1: Create strategy — `vtrend_e5_ema21_d1_vc`

### 1a. Create directory

```bash
mkdir -p /var/www/trading-bots/btc-spot-dev/strategies/vtrend_e5_ema21_d1_vc
touch /var/www/trading-bots/btc-spot-dev/strategies/vtrend_e5_ema21_d1_vc/__init__.py
```

### 1b. Create strategy.py

Copy from `strategies/vtrend_e5_ema21_d1/strategy.py` and add:

**Config changes** — add ONE parameter:
```python
@dataclass
class VTrendE5Ema21D1VCConfig:
    # Tunable (5 parameters — 4 original + 1 new)
    slow_period: float = 120.0
    trail_mult: float = 3.0
    vdo_threshold: float = 0.0
    d1_ema_period: int = 21
    vc_threshold: float = 0.7          # NEW: vol compression gate

    # Structural constants (unchanged)
    vdo_fast: int = 12
    vdo_slow: int = 28
    ratr_cap_q: float = 0.90
    ratr_cap_lb: int = 100
    ratr_period: int = 20
    vc_short_window: int = 5           # NEW: structural
    vc_long_window: int = 20           # NEW: structural
    enable_regime_monitor: bool = False
```

**on_init() changes** — add vol_ratio computation:
```python
def on_init(self, h4_bars: list, d1_bars: list) -> None:
    # ... existing code unchanged ...

    # Vol compression: rolling std ratio
    self._vol_ratio = _vol_ratio(close, self._c.vc_short_window,
                                  self._c.vc_long_window)
```

**on_bar() entry change** — add compression gate:
```python
if not self._in_position:
    regime_ok = bool(self._d1_regime_ok[i])
    vol_ok = (
        self._vol_ratio is not None
        and not math.isnan(self._vol_ratio[i])
        and self._vol_ratio[i] < self._c.vc_threshold
    )
    if trend_up and vdo_val > self._c.vdo_threshold and regime_ok and vol_ok and not monitor_red:
        self._in_position = True
        self._peak_price = price
        return Signal(target_exposure=1.0, reason="vtrend_e5_ema21_d1_vc_entry")
```

**New helper function** — add at bottom of file:
```python
def _vol_ratio(close: np.ndarray, short_w: int, long_w: int) -> np.ndarray:
    """Rolling std ratio: std(close, short) / std(close, long).

    Low values indicate volatility compression (short-term vol < long-term).
    """
    n = len(close)
    result = np.full(n, np.nan)
    for i in range(long_w - 1, n):
        if i >= short_w - 1:
            std_short = np.std(close[i - short_w + 1:i + 1], ddof=1)
            std_long = np.std(close[i - long_w + 1:i + 1], ddof=1)
            if std_long > 1e-10:
                result[i] = std_short / std_long
    return result
```

**All exit logic**: UNCHANGED (trail_stop, trend_exit, monitor_exit).

**name() method**: return `"vtrend_e5_ema21_d1_vc"`

**All exit reason strings**: prefix with `vtrend_e5_ema21_d1_vc_` instead of `vtrend_e5_ema21_d1_`.

### 1c. Verification checklist

After writing strategy.py:
- [ ] Config has 5 tunable params (slow_period, trail_mult, vdo_threshold, d1_ema_period, vc_threshold)
- [ ] vc_threshold default = 0.7 (matches exp42 WFO-validated threshold)
- [ ] vc_short_window=5, vc_long_window=20 (structural, not tunable)
- [ ] _vol_ratio computed in on_init() using close prices
- [ ] Entry condition: `trend_up AND vdo > threshold AND regime_ok AND vol_ok AND NOT monitor_red`
- [ ] vol_ok checks for NaN (early bars before rolling std is available)
- [ ] All exit logic identical to E5-ema21D1 (trail_stop, trend_exit, monitor_exit)
- [ ] No other changes vs E5-ema21D1

## Step 2: Create config YAML

Create `/var/www/trading-bots/btc-spot-dev/configs/vtrend_e5_ema21_d1_vc/vtrend_e5_ema21_d1_vc_default.yaml`:

```yaml
engine:
  symbol: BTCUSDT
  timeframe_h4: 4h
  timeframe_d1: 1d
  warmup_days: 365
  warmup_mode: no_trade
  scenario_eval: base
  initial_cash: 10000.0

strategy:
  name: vtrend_e5_ema21_d1_vc
  slow_period: 120.0
  trail_mult: 3.0
  vdo_threshold: 0.0
  d1_ema_period: 21
  vc_threshold: 0.7

risk:
  max_total_exposure: 1.0
  min_notional_usdt: 10
  kill_switch_dd_total: 0.45
  max_daily_orders: 5
```

## Step 3: Register strategy

Edit `/var/www/trading-bots/btc-spot-dev/validation/strategy_factory.py`:

### 3a. Add import (after the vtrend_e5_ema21_d1 import block):
```python
from strategies.vtrend_e5_ema21_d1_vc.strategy import (
    VTrendE5Ema21D1VCConfig,
    VTrendE5Ema21D1VCStrategy,
)
```

### 3b. Add to STRATEGY_REGISTRY (after the vtrend_e5_ema21_d1 entry):
```python
"vtrend_e5_ema21_d1_vc": (VTrendE5Ema21D1VCStrategy, VTrendE5Ema21D1VCConfig),
```

## Step 4: Quick sanity test

```bash
cd /var/www/trading-bots/btc-spot-dev

# Verify import works
python -c "from strategies.vtrend_e5_ema21_d1_vc.strategy import VTrendE5Ema21D1VCStrategy, VTrendE5Ema21D1VCConfig; print('OK')"

# Verify registry
python -c "from validation.strategy_factory import STRATEGY_REGISTRY; assert 'vtrend_e5_ema21_d1_vc' in STRATEGY_REGISTRY; print('Registered')"

# Quick backtest (should run without error)
python -m v10.cli.backtest \
  --config configs/vtrend_e5_ema21_d1_vc/vtrend_e5_ema21_d1_vc_default.yaml \
  --scenario harsh \
  --start 2019-01-01 --end 2026-02-20
```

Expected: Sharpe close to E5-ema21D1 baseline (~1.45) but with fewer trades
(compression blocks ~30% of entries) and slightly different Sharpe/CAGR/MDD.

## Step 5: Run full validation

```bash
cd /var/www/trading-bots/btc-spot-dev

python validation/validate_strategy.py \
  --strategy vtrend_e5_ema21_d1_vc \
  --baseline vtrend_e5_ema21_d1 \
  --config configs/vtrend_e5_ema21_d1_vc/vtrend_e5_ema21_d1_vc_default.yaml \
  --baseline-config configs/vtrend_e5_ema21_d1/vtrend_e5_ema21_d1_default.yaml \
  --out results/full_eval_e5_ema21d1_vc/ \
  --suite full
```

### Exit code interpretation

| Exit | Verdict | Meaning |
|------|---------|---------|
| 0 | PROMOTE | All 7 gates pass — vol compression is a validated improvement |
| 1 | HOLD | Some soft gates fail (likely WFO Wilcoxon) — underresolved |
| 2 | REJECT | Hard gates fail — vol compression HURTS in v10 engine |
| 3 | ERROR | Code bug — fix and re-run |

### Key gates to watch

| Gate | What to expect |
|------|---------------|
| lookahead | PASS (no future data used) |
| full_harsh_delta | PASS (x39 showed +0.18 Sharpe) |
| holdout_harsh_delta | Uncertain — depends on holdout period |
| wfo_robustness | CRITICAL — this is the authoritative WFO test (Wilcoxon p ≤ 0.10) |
| selection_bias (PSR) | Info only |

### If WFO PASS (exit 0)
Vol compression is the first x39 mechanism to pass authoritative validation.
Strategy E5-ema21D1-VC becomes the new primary candidate.
Record the result in `results/full_eval_e5_ema21d1_vc/`.

### If WFO FAIL (exit 1 with wfo_robustness fail)
Same situation as E5-ema21D1: underresolved, not rejected.
The simplified replay WFO (exp42, 4/4) was more optimistic than v10's
proper WFO. This is expected — simplified replay lacks position sizing,
execution slippage, and proper cost model.
Record the result and note the gap between x39 and v10 WFO.

### If REJECT (exit 2)
Vol compression HURTS in v10 engine. The simplified replay was misleading.
This would be an important negative result. Document why.

## Step 6: Record results

After validation completes:
1. Record exit code and all gate results
2. Compare v10 full-sample metrics vs x39 exp34 full-sample metrics
3. Note any discrepancies between simplified replay and v10 engine
4. If PROMOTE: update STRATEGY_STATUS_MATRIX.md

## Files to create/modify

| Action | Path |
|--------|------|
| CREATE | `strategies/vtrend_e5_ema21_d1_vc/__init__.py` |
| CREATE | `strategies/vtrend_e5_ema21_d1_vc/strategy.py` |
| CREATE | `configs/vtrend_e5_ema21_d1_vc/vtrend_e5_ema21_d1_vc_default.yaml` |
| MODIFY | `validation/strategy_factory.py` (add import + registry entry) |
| CREATE | `results/full_eval_e5_ema21d1_vc/` (output dir, created by pipeline) |

## Session prompt

```
Read /var/www/trading-bots/btc-spot-dev/research/x39/specs/task_b_port_compression_to_v10.md

This spec describes how to:
1. Create a new strategy vtrend_e5_ema21_d1_vc (E5-ema21D1 + vol compression gate)
2. Register it in the validation pipeline
3. Run full 7-gate validation against E5-ema21D1 baseline

Follow the steps exactly. The strategy is a COPY of vtrend_e5_ema21_d1 with ONE change:
entry requires vol_ratio_5_20 < 0.7 (volatility compression gate).

Background: x39 exp42 showed this gate passes WFO 4/4 in simplified replay.
This task tests whether it holds up in the authoritative v10 validation pipeline.
```
