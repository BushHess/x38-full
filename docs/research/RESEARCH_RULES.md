# Research Rules — btc-spot-dev

**Quy định chi tiết cho mọi code trong `research/`.**
**Kế thừa từ [`CLAUDE.md`](../../CLAUDE.md) — xem đó trước để hiểu tổng quan dự án.**
**Mọi agent (claude_code, codex, hoặc khác) phải tuân thủ.**

---

## 0. Môi trường

Xem [CLAUDE.md §Environment](../../CLAUDE.md) cho Python venv, tooling, test config.

### Path setup trong mọi script

```python
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[N]  # N tùy depth từ file tới repo root
sys.path.insert(0, str(ROOT))
```

---

## 1. Quy tắc ghi file

### Được phép ghi (write zone)

```
research/xNN/**/*          ← toàn bộ code, data, results cho study xNN
```

Mỗi study tự chứa trong thư mục riêng. Không ghi ra ngoài.

### KHÔNG được phép ghi

```
validation/*               ← strategy_factory.py, runner.py, decision.py, ...
v10/*                      ← core engine, types, data, strategies/base
strategies/*               ← registered strategies (chỉ khi PROMOTE chính thức)
tests/*                    ← test suite hệ thống
```

### Lý do

- Research code thay đổi liên tục, system code phải ổn định.
- Đăng ký strategy vào `strategy_factory.py` gây coupling giữa research và production.
- `validation/` **không có plugin mechanism** — `STRATEGY_REGISTRY` là static dict,
  thêm strategy bắt buộc phải sửa file. Đây là lý do kỹ thuật buộc research phải
  dùng standalone runner thay vì hook vào pipeline.
- Nếu research cần chức năng mới từ framework → đề xuất riêng, không tự sửa.

---

## 2. Hai pattern chạy backtest (đều hợp lệ)

### Pattern A — Dùng BacktestEngine + Strategy class

Dùng khi strategy kế thừa `v10.strategies.base.Strategy` và muốn tận dụng engine
có sẵn (cost scenarios, fill logic, equity tracking).

**Ví dụ thực tế**: `research/x32/a_vp1_baseline/code/full_evaluation.py`

```python
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[N]  # N tùy depth
sys.path.insert(0, str(ROOT))

from v10.core.data import DataFeed
from v10.core.engine import BacktestEngine
from v10.core.types import SCENARIOS, BacktestResult

# Import strategy TRỰC TIẾP, không qua factory
from research.xNN.code.my_strategy import MyStrategy, MyConfig

feed = DataFeed(
    str(ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv"),
    start="2019-01-01",
    end="2026-02-20",
    warmup_days=365,
)
strategy = MyStrategy(MyConfig())
engine = BacktestEngine(
    feed=feed,
    strategy=strategy,
    cost=SCENARIOS["harsh"],   # 50 bps RT
    initial_cash=10_000.0,
    warmup_mode="no_trade",
)
result = engine.run()

# Metrics có sẵn
print(result.summary)  # dict: sharpe, cagr_pct, max_dd_pct, n_trades, ...
# result.trades: list[Trade]
# result.equity: list[EquitySnap]
# result.fills: list[Fill]
```

**Pattern A KHÔNG dùng YAML config**. Strategy được instantiate trực tiếp trong code.
YAML config chỉ cần cho `validation/runner.py` (yêu cầu factory registration).

### Pattern B — Vectorized sim tự viết

Dùng khi muốn kiểm soát hoàn toàn logic sim, hoặc cần tốc độ cao cho nhiều configs.
Nhanh hơn Pattern A đáng kể.

**Ví dụ thực tế**: `research/x14/benchmark.py`

```python
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from v10.core.data import DataFeed
from v10.core.types import SCENARIOS

feed = DataFeed(DATA, start=START, end=END, warmup_days=WARMUP)

# Extract numpy arrays từ feed
cl = np.array([b.close for b in feed.h4_bars])
hi = np.array([b.high for b in feed.h4_bars])
lo = np.array([b.low for b in feed.h4_bars])
vo = np.array([b.volume for b in feed.h4_bars])
tb = np.array([b.taker_buy_base_vol for b in feed.h4_bars])

# Tự implement sim bằng numpy
def _run_sim(cl, hi, lo, vo, tb, ..., cost_f):
    # Vectorized indicators + trading logic
    # Returns: (trades, bar_ret, in_pos)
    ...

# Tự compute metrics
ANN = math.sqrt(6.0 * 365.25)  # annualization factor cho H4
cost_f = SCENARIOS["harsh"].per_side_bps / 10_000.0
```

### Khi nào dùng Pattern nào?

| Tiêu chí | Pattern A | Pattern B |
|----------|-----------|-----------|
| Strategy kế thừa base.Strategy | Phù hợp | Không cần |
| Cần cost scenarios chính xác | Có sẵn (SCENARIOS) | Tự implement (dùng SCENARIOS constants) |
| Cần tốc độ cao / nhiều configs | Chậm hơn | Nhanh hơn |
| So sánh 1:1 với validation results | Bit-identical | Có thể lệch nhẹ |
| Metrics | `result.summary` (có sẵn) | Tự compute từ bar_ret array |

---

## 3. Import được phép

### OK — đọc từ v10 (không sửa)

```python
# Core
from v10.core.data import DataFeed
from v10.core.engine import BacktestEngine
from v10.core.types import (
    SCENARIOS, BacktestResult, Bar, Side, Signal, Order,
    MarketState, Fill, Trade, CostConfig, EquitySnap,
)
from v10.strategies.base import Strategy  # ABC cho Pattern A strategies
```

### OK — đọc từ research/lib

```python
# Bootstrap
from research.lib.vcbb import make_ratios, precompute_vcbb, gen_path_vcbb

# Selection bias / significance
from research.lib.dsr import compute_dsr, compute_psr, deflated_sharpe, benchmark_sr0

# Multiple-test correction (correlated timescales)
from research.lib.effective_dof import compute_meff, corrected_binomial

# Pair diagnostic (automated comparison)
from research.lib.pair_diagnostic import run_pair_diagnostic, render_review_template
```

### OK — import strategy có sẵn làm baseline (READ-ONLY)

```python
from strategies.vtrend.strategy import VTrendStrategy, VTrendConfig
from strategies.vtrend_e5_ema21_d1.strategy import VTrendE5Ema21D1Strategy
```

### KHÔNG OK — validation pipeline

```python
from validation.strategy_factory import STRATEGY_REGISTRY   # KHÔNG
from validation.runner import ValidationRunner               # KHÔNG
from validation.decision import evaluate_decision            # KHÔNG
from validation.suites.wfo import WFOSuite                   # KHÔNG
```

---

## 4. Tham chiếu nhanh: v10 API

### DataFeed

```python
feed = DataFeed(path, start=None, end=None, warmup_days=0)
feed.h4_bars          # list[Bar] — H4 bars (sorted by open_time)
feed.d1_bars          # list[Bar] — D1 bars (sorted by open_time)
feed.n_h4             # int — số H4 bars
feed.n_d1             # int — số D1 bars
feed.report_start_ms  # int | None — boundary giữa warmup và reporting
```

### Bar (frozen dataclass)

```python
bar.open_time, bar.close_time     # int (ms)
bar.open, bar.high, bar.low, bar.close  # float
bar.volume                        # float (base currency)
bar.taker_buy_base_vol            # float
bar.quote_volume                  # float (quote currency, USDT)
bar.taker_buy_quote_vol           # float
bar.interval                      # str: '1h', '4h', '1d'
```

### SCENARIOS (cost configs)

| Scenario | spread_bps | slippage_bps | taker_fee_pct | RT bps |
|----------|-----------|-------------|--------------|--------|
| `"smart"` | 3.0 | 1.5 | 0.035 | 13.0 |
| `"base"` | 5.0 | 3.0 | 0.100 | 31.0 |
| `"harsh"` | 10.0 | 5.0 | 0.150 | 50.0 |

### Strategy ABC (Pattern A)

```python
class MyStrategy(Strategy):
    def on_init(self, h4_bars, d1_bars):
        """Gọi 1 lần trước backtest. Pre-compute indicators ở đây."""
        ...

    def on_bar(self, state: MarketState) -> Signal | None:
        """Gọi mỗi H4 bar close. Return Signal hoặc None (giữ position)."""
        # state.bar          — Bar hiện tại
        # state.h4_bars      — toàn bộ H4 bars (dùng state.bar_index để bound look-back)
        # state.d1_bars      — toàn bộ D1 bars (dùng state.d1_index)
        # state.cash, state.btc_qty, state.nav, state.exposure
        # state.entry_price_avg, state.position_entry_nav
        return Signal(target_exposure=1.0, reason="entry")  # 0.0=flat, 1.0=full

    def on_after_fill(self, state: MarketState, fill: Fill):
        """Gọi sau mỗi fill. Optional."""
        ...
```

**Timing**: Signal trả về ở bar close → execute ở bar TIẾP THEO open (next-open fill).
**MTF**: D1 bar được chọn là bar gần nhất có `close_time < H4 close_time` (no lookahead).

---

## 5. Metrics và validation

### Pattern A — metrics có sẵn

```python
result = engine.run()
s = result.summary
# s["sharpe"], s["cagr_pct"], s["max_drawdown_mid_pct"], s["trades"],
# s["avg_exposure"], s["profit_factor"], s["win_rate_pct"], ...
```

### Pattern B — tự compute

```python
ANN = math.sqrt(6.0 * 365.25)  # H4 annualization
r = bar_ret[warmup:]            # log returns sau warmup
sharpe = (np.mean(r) / np.std(r)) * ANN if np.std(r) > 0 else 0.0

eq = np.exp(np.cumsum(r))
cm = np.maximum.accumulate(eq)
dd = (cm - eq) / cm
mdd = float(np.max(dd) * 100)
```

### Validation mở rộng (nếu vượt GO threshold)

```python
from research.lib.vcbb import make_ratios, precompute_vcbb, gen_path_vcbb  # bootstrap
from research.lib.dsr import compute_psr                                    # selection bias
from research.lib.effective_dof import compute_meff                         # DOF correction
```

WFO: tự implement (expanding window, xem X14 hoặc X27 làm mẫu).

---

## 6. Output format

- **JSON**: metrics summary, verdict, gate results
- **CSV**: comparison tables, per-window results
- **Markdown**: human-readable report trong `results/`
- Tất cả output nằm trong thư mục study tương ứng

---

## 7. Checklist trước khi chạy

- [ ] Code chỉ nằm trong `research/xNN/`
- [ ] Không sửa file nào trong `validation/`, `v10/`, `strategies/`, `tests/`
- [ ] Import từ v10/strategies chỉ để ĐỌC (baseline comparison)
- [ ] Runner tự chứa (standalone), chạy được bằng `python script.py`
- [ ] Strategy kế thừa đúng `v10.strategies.base.Strategy` (nếu Pattern A)
- [ ] Signal timing đúng: return ở bar close, execute ở next bar open
- [ ] Dùng Python venv tại `/var/www/trading-bots/.venv`

---

## Tham khảo — các study mẫu

| Study | Pattern | File mẫu | Mô tả |
|-------|---------|----------|-------|
| X14 | B (vectorized) | `research/x14/benchmark.py` | Churn filter, 6-gate validation, 1850+ lines |
| X16 | B (vectorized) | `research/x16/benchmark.py` | Stateful exit, WATCH state machine |
| X18 | B (vectorized) | `research/x18/benchmark.py` | α-percentile static mask |
| X27 | B (custom sim) | `research/x27/code/phase7_validation.py` | Alt mechanisms, phase-based |
| X32 | A (BacktestEngine) | `research/x32/a_vp1_baseline/code/full_evaluation.py` | VP1 evaluation |
| X33 | Không dùng engine | `research/x33/analyze_execution_cost.py` | Execution cost measurement |
