# Task B: Implement vtrend_e5_ema21_d1_vc & Reproduce x39 Results

## Session prompt

```
Read /var/www/trading-bots/btc-spot-dev/research/x39/specs/formal_validation_spec.md
Read /var/www/trading-bots/btc-spot-dev/research/x39/specs/task_b_implement_and_reproduce.md

Execute Phase 1 + Phase 2 of the formal validation spec.
```

## What this task does

1. **Phase 1**: Create `vtrend_e5_ema21_d1_vc` strategy (vol compression gate variant)
2. **Phase 2**: Run v10 backtest, compare d_Sharpe with x39 simplified replay

## Phase 1: Strategy Implementation

### Step 1.1 — Create strategy directory

```
strategies/vtrend_e5_ema21_d1_vc/
├── __init__.py
└── strategy.py
```

Fork from `strategies/vtrend_e5_ema21_d1/strategy.py`. Changes:

**Config dataclass** — add 3 fields:
```python
@dataclass
class VTrendE5Ema21D1VCConfig:
    # ... all existing E5-ema21D1 fields ...

    # Vol compression gate (x39 exp34/42/52)
    compression_threshold: float = 0.6
    compression_fast: int = 5       # structural, not tunable
    compression_slow: int = 20      # structural, not tunable
```

**on_init()** — add vol_ratio computation after existing indicators:
```python
self._vol_ratio = _rolling_std(close, self._c.compression_fast) / np.where(
    (std_slow := _rolling_std(close, self._c.compression_slow)) > 1e-10,
    std_slow, np.nan
)
```

**on_bar() entry** — add gate (one extra condition):
```python
if not self._in_position:
    regime_ok = bool(self._d1_regime_ok[i])
    vol_r = self._vol_ratio[i]
    compression_ok = not math.isnan(vol_r) and vol_r < self._c.compression_threshold
    if trend_up and vdo_val > self._c.vdo_threshold and regime_ok and compression_ok and not monitor_red:
        ...
```

**Exit logic** — UNCHANGED. Copy verbatim from E5-ema21D1.

**Helper function** — add `_rolling_std`:
```python
def _rolling_std(series: np.ndarray, window: int) -> np.ndarray:
    """Rolling sample std (ddof=1), matching pandas rolling().std()."""
    n = len(series)
    out = np.full(n, np.nan)
    for i in range(window - 1, n):
        out[i] = np.std(series[i - window + 1 : i + 1], ddof=1)
    return out
```

**reason strings**: use `"vtrend_e5_ema21_d1_vc_entry"`, `"..._trail_stop"`, `"..._trend_exit"`, `"..._monitor_exit"`.

**name()**: return `"vtrend_e5_ema21_d1_vc"`

### Step 1.2 — Create config files

**File**: `configs/vtrend_e5_ema21_d1_vc/vtrend_e5_ema21_d1_vc_default.yaml`
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
  compression_threshold: 0.6

risk:
  max_total_exposure: 1.0
  min_notional_usdt: 10
  kill_switch_dd_total: 0.45
  max_daily_orders: 5
```

**File**: `configs/vtrend_e5_ema21_d1_vc/vtrend_e5_ema21_d1_vc_07.yaml`
Same but `compression_threshold: 0.7`

### Step 1.3 — Register in STRATEGY_REGISTRY

**File**: `validation/strategy_factory.py`

Add import + registry entry:
```python
from strategies.vtrend_e5_ema21_d1_vc.strategy import (
    VTrendE5Ema21D1VCStrategy,
    VTrendE5Ema21D1VCConfig,
)

STRATEGY_REGISTRY = {
    ...
    "vtrend_e5_ema21_d1_vc": (VTrendE5Ema21D1VCStrategy, VTrendE5Ema21D1VCConfig),
}
```

### Step 1.4 — Run tests

```bash
cd /var/www/trading-bots/btc-spot-dev && python -m pytest -x -q
```

All existing tests must pass. No new tests needed for this task.

---

## Phase 2: Reproduction Check

### Step 2.1 — Write reproduction script

Write to `research/x39/experiments/formal_reproduction.py`.

This script runs BOTH the x39 simplified replay AND the v10 formal engine
side-by-side, for baseline and compression (thr=0.6), then compares.

```python
# Pseudocode structure:
# 1. Run x39 replay (import explore.py helpers) → get x39 baseline + x39 compression metrics
# 2. Run v10 BacktestEngine with E5-ema21D1 → get v10 baseline metrics
# 3. Run v10 BacktestEngine with E5-ema21D1-VC (thr=0.6) → get v10 compression metrics
# 4. Compute deltas, print comparison table
```

**v10 runs** (Pattern A from RESEARCH_RULES.md):
```python
from v10.core.data import DataFeed
from v10.core.engine import BacktestEngine
from v10.core.types import SCENARIOS
from strategies.vtrend_e5_ema21_d1.strategy import VTrendE5Ema21D1Strategy, VTrendE5Ema21D1Config
from strategies.vtrend_e5_ema21_d1_vc.strategy import VTrendE5Ema21D1VCStrategy, VTrendE5Ema21D1VCConfig

DATA = "data/bars_btcusdt_2016_now_h1_4h_1d.csv"
feed = DataFeed(DATA, start="2019-01-01", end="2026-02-20", warmup_days=365)

# Baseline
base_strat = VTrendE5Ema21D1Strategy(VTrendE5Ema21D1Config())
base_engine = BacktestEngine(feed=feed, strategy=base_strat,
                             cost=SCENARIOS["harsh"], initial_cash=10_000.0,
                             warmup_mode="no_trade")
base_result = base_engine.run()

# Compression thr=0.6
vc_strat = VTrendE5Ema21D1VCStrategy(VTrendE5Ema21D1VCConfig(compression_threshold=0.6))
vc_engine = BacktestEngine(feed=DataFeed(DATA, start="2019-01-01", end="2026-02-20", warmup_days=365),
                           strategy=vc_strat, cost=SCENARIOS["harsh"],
                           initial_cash=10_000.0, warmup_mode="no_trade")
vc_result = vc_engine.run()

# Compare
print("v10 baseline:", base_result.summary)
print("v10 compression:", vc_result.summary)
print("d_Sharpe:", vc_result.summary["sharpe"] - base_result.summary["sharpe"])
```

### Step 2.2 — Run and record

Run the script. Record results in the formal_validation_spec.md under Phase 2.

### Acceptance criteria

| Check | Pass condition |
|-------|---------------|
| Tests pass | `pytest` exit 0 |
| v10 baseline runs | No errors, Sharpe ~1.45 |
| v10 compression runs | No errors |
| d_Sharpe same sign | v10 d_Sharpe > 0 (like x39's +0.19) |
| d_Sharpe magnitude | Within ±30% of x39 value |
| d_Trades | Compression has fewer trades than baseline |
| Blocked WR | Not required here (counterfactual not in v10) |

### If discrepancy > 30%

Diagnose by comparing trade lists:
1. Export both v10 trade lists (entry bar, exit bar, net return)
2. Identify divergent trades
3. Check if fill timing or cost model causes the difference
4. Document the root cause in the spec

---

## After completion

Update `formal_validation_spec.md`:
- Fill in Phase 2 comparison table with actual numbers
- Note any discrepancies and root causes
- Confirm Phase 2 acceptance: PASS or FAIL (with reason)

If Phase 2 PASS → proceed to Task C (formal validation pipeline).
If Phase 2 FAIL → diagnose and fix before proceeding.
