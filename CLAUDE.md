# CLAUDE.md — AI Context for btc-spot-dev

## Project Overview

BTC/USDT spot long-only trading system. Backtest engine, validation framework,
research pipeline, monitoring, and live execution infrastructure.

**Primary algorithm**: E5_ema21D1 (VTREND E5 + D1 EMA(21) regime filter) — 4-parameter trend-following strategy.
Status: **HOLD** (2026-03-17 re-validation, 6/7 gates PASS, WFO robustness FAIL:
Wilcoxon p=0.125 > α=0.10, Bootstrap CI [-3.44, 29.28] crosses zero).
WFO result is **underresolved** (insufficient OOS power), not negative-confirmed.

**Current phase**: Algorithm discovery & mathematical proof.
Do NOT propose deployment, paper trading, or "ship it" — every suggestion must be
grounded in statistical proof or mathematical argument.

---

## Environment

```
Python       : 3.12.11
Venv         : /var/www/trading-bots/.venv
Activate     : source /var/www/trading-bots/.venv/bin/activate
Repo root    : /var/www/trading-bots/btc-spot-dev
Pkg manager  : uv (lock: /var/www/trading-bots/uv.lock)
Config       : /var/www/trading-bots/pyproject.toml (ruff, mypy, pyright)
Test config  : /var/www/trading-bots/btc-spot-dev/pytest.ini
Git          : NOT a git repository
```

**Tooling**:
- `ruff 0.15.2` — line 124, indent 4, rules E/F/W/I/B/UP
- `mypy 1.19.1` — strict mode, Python 3.12
- `pytest 9.0.2` — paths: `tests`, `v10/tests`, `validation/tests`, `research/tests`

**Run tests**: `cd /var/www/trading-bots/btc-spot-dev && python -m pytest`

---

## Architecture

```
btc-spot-dev/
├── v10/                    # Core engine (FROZEN)
│   ├── core/               #   engine, data, execution, metrics, types, config
│   ├── strategies/         #   Strategy ABC (base.py), BuyAndHold, V8Apex, V11Hybrid
│   ├── exchange/           #   Binance REST, order manager, bar clock, filters
│   ├── research/           #   bootstrap, WFO, candidates, decision, regime, objective
│   ├── cli/                #   backtest, paper, research, compare, live, monitor
│   └── tests/              #   ~370 tests
├── strategies/             # Registered strategies (29 dirs, one per strategy)
├── validation/             # Validation pipeline (19 suites, 7 gates)
│   ├── strategy_factory.py #   STRATEGY_REGISTRY (static dict, NO plugin mechanism)
│   ├── runner.py           #   Main orchestrator
│   ├── decision.py         #   Gate logic → PROMOTE/HOLD/REJECT/ERROR
│   ├── thresholds.py       #   Authority-bearing constants
│   ├── suites/             #   19 pluggable suites
│   └── tests/              #   22 test modules
├── research/               # Research studies
│   ├── lib/                #   vcbb, dsr, effective_dof, pair_diagnostic
│   └── x0/ .. x37/        #   39 x-series dirs (each self-contained)
├── configs/                # YAML configs (23 subdirs, one per strategy)
├── monitoring/             # regime_monitor.py, alerts.py
├── tests/                  # System tests (14 files)
├── data/                   # Current data feeds (15m, 1h, 4h, 1d CSVs)
├── docs/                   # Organized documentation (see docs/README.md)
│   ├── algorithm/          #   VTREND_BLUEPRINT, LATENCY_TIER_DEPLOYMENT_GUIDE
│   ├── validation/         #   decision policy, output contract, CLI, governance
│   ├── operations/         #   RUNBOOK_C4_C5
│   ├── research/           #   RESEARCH_RULES, strategy versioning
│   └── archive/            #   Historical documents (pre-VTREND)
├── scripts/                # Utility scripts
├── experiments/            # Exploratory analysis
├── out/                    # Backtest output artifacts
├── results/                # Validation results (full_eval_*, parity_*)
├── reports/                # Summary reports
├── research_reports/       # Sequential audit trail (01-37)
└── legacy/                 # Orphaned files from V10/V11 era (safe to delete)
```

**Key data file**: `data/bars_btcusdt_2016_now_h1_4h_1d.csv` (repo root, 2017-08→2026-02, H4+D1)

---

## Write Permissions

| Area | Who/When | Notes |
|------|----------|-------|
| `v10/` | **FROZEN** — chỉ sửa khi có explicit approval | Core engine. Mọi thay đổi ảnh hưởng toàn hệ thống. |
| `strategies/` | **Chỉ khi PROMOTE** qua validation gates | Mỗi strategy self-contained (strategy.py + __init__.py). |
| `validation/` | **Chỉ sửa framework logic** | `STRATEGY_REGISTRY` là static dict — thêm strategy bắt buộc sửa file. |
| `research/xNN/` | **Tự do** trong thư mục study | Xem [RESEARCH_RULES.md](docs/research/RESEARCH_RULES.md) cho patterns và API. |
| `tests/` | **Khi sửa code tương ứng** | pytest, match test file với module đang sửa. |
| `configs/` | **Production configs cẩn trọng** | Research configs đặt trong research/. |
| `monitoring/` | **Cẩn trọng** — regime_monitor status UNCERTAIN | Stable code, WFO instability chưa giải quyết. |
| `data/` | **Read-only** | Data pipeline external (`/var/www/trading-bots/data-pipeline/`). |
| `docs/` | Case-by-case | Documentation updates. |
| `scripts/`, `experiments/` | Case-by-case | Utility/exploratory. |

**Nguyên tắc chung**: Research code KHÔNG sửa system files. Research tự chứa trong
`research/xNN/`, dùng standalone runner (Pattern A hoặc B). Xem [RESEARCH_RULES.md](docs/research/RESEARCH_RULES.md).

---

## Core API Quick Reference

### DataFeed

```python
from v10.core.data import DataFeed

feed = DataFeed(path, start="2019-01-01", end="2026-02-20", warmup_days=365)
feed.h4_bars     # list[Bar] — H4 bars
feed.d1_bars     # list[Bar] — D1 bars
```

### BacktestEngine

```python
from v10.core.engine import BacktestEngine
from v10.core.types import SCENARIOS

engine = BacktestEngine(feed=feed, strategy=strategy, cost=SCENARIOS["harsh"],
                        initial_cash=10_000.0, warmup_mode="no_trade")
result = engine.run()
result.summary   # dict: sharpe, cagr_pct, max_drawdown_mid_pct, trades, ...
```

### Strategy ABC

```python
from v10.strategies.base import Strategy
from v10.core.types import MarketState, Signal, Fill

class MyStrategy(Strategy):
    def on_init(self, h4_bars, d1_bars): ...      # pre-compute indicators
    def on_bar(self, state: MarketState) -> Signal | None: ...  # entry/exit logic
    def on_after_fill(self, state: MarketState, fill: Fill): ...  # optional
```

**Signal timing**: return ở bar close → execute ở next bar open (next-open fill).

### Cost Scenarios

| Scenario | RT bps |
|----------|--------|
| `"smart"` | 13 |
| `"base"` | 31 |
| `"harsh"` | 50 |

---

## Validation Pipeline (Tier 2 — Machine Validation)

**Invocation**: `python validate_strategy.py --strategy NAME --baseline NAME --config FILE --baseline-config FILE --out DIR --suite {basic|full|all}`

**Exit codes**: 0=PROMOTE, 1=HOLD, 2=REJECT, 3=ERROR

Machine verdict is **evidence, not final deployment decision**. See 3-tier model
in `STRATEGY_STATUS_MATRIX.md`. HOLD = "automated evidence insufficient", not
"do not deploy". Final authority: human researcher via `reports/deployment_decision.md`.

**Gates** (3 hard + 2 soft + 1 info):

| Gate | Type | Threshold |
|------|------|-----------|
| `lookahead` | hard | zero violations |
| `full_harsh_delta` | hard | ΔScore ≥ -0.2 |
| `holdout_harsh_delta` | hard | ΔScore ≥ -0.2 |
| `wfo_robustness` | soft | Wilcoxon p ≤ 0.10 OR Bootstrap CI > 0 |
| `trade_level_bootstrap` | soft | conditional (low-power WFO) |
| `selection_bias` | soft/info | method_fallback or PBO fail → soft. PSR → info diagnostic |
| `bootstrap` | info | diagnostic only |

---

## Key Files

**Algorithm**:
- `strategies/vtrend_e5_ema21_d1/strategy.py` — PRIMARY strategy (E5_ema21D1)
- `strategies/vtrend/strategy.py` — E0 baseline
- `configs/vtrend_e5_ema21_d1/vtrend_e5_ema21_d1_default.yaml` — primary config

**Engine**:
- `v10/core/engine.py` — BacktestEngine (event loop)
- `v10/core/types.py` — Bar, Signal, Trade, MarketState, SCENARIOS
- `v10/core/data.py` — DataFeed (CSV loader)
- `v10/core/metrics.py` — compute_metrics()
- `v10/core/execution.py` — ExecutionModel, Portfolio
- `v10/strategies/base.py` — Strategy ABC

**Validation**:
- `validation/strategy_factory.py` — STRATEGY_REGISTRY
- `validation/runner.py` — orchestrator
- `validation/decision.py` — gate logic
- `validation/thresholds.py` — authority-bearing constants

**Research libs**:
- `research/lib/vcbb.py` — Volatility-Conditioned Block Bootstrap
- `research/lib/dsr.py` — Deflated Sharpe Ratio (selection bias correction)
- `research/lib/effective_dof.py` — Nyholt M_eff (correlated timescales)
- `research/lib/pair_diagnostic.py` — automated pair comparison

**Documentation** (`docs/README.md` for full index):
- `docs/algorithm/VTREND_BLUEPRINT.md` — complete algorithm spec (760 lines)
- `docs/algorithm/LATENCY_TIER_DEPLOYMENT_GUIDE.md` — latency tier decisions (LT1/LT2/LT3)
- `STRATEGY_STATUS_MATRIX.md` — all 40+ strategies & verdicts
- `DEPLOYMENT_CHECKLIST.md` — component-level deployment reference
- `docs/research/RESEARCH_RULES.md` — research patterns, v10 API reference, import rules
- `docs/validation/decision_policy.md` — gate definitions
- `docs/validation/output_contract.md` — required artifacts per suite
- `docs/operations/RUNBOOK_C4_C5.md` — testnet validation runbook

**Results**:
- `results/full_eval_e5_ema21d1/` — E5_ema21D1 HOLD verdict (WFO underresolved)
- `results/full_eval_x0_ema21d1/` — E0_ema21D1 HOLD verdict (dir uses legacy "x0" alias)

---

## Related Files (Outside Repo)

| Path | Purpose |
|------|---------|
| `/var/www/trading-bots/.venv/` | Shared Python venv |
| `/var/www/trading-bots/pyproject.toml` | Monorepo config (ruff, mypy) |
| `/var/www/trading-bots/uv.lock` | Dependency lock (45 packages) |
| `/var/www/trading-bots/mise.toml` | Python 3.12 + uv orchestration |
| `/var/www/trading-bots/data-pipeline/` | Binance data fetching |
| `/var/www/trading-bots/vtrend/` | VTREND strategy library |
| `/var/www/trading-bots/btc-spot/` | Previous production bot (has own CLAUDE.md) |

---

## Conventions

- **Strategy naming**: See [`docs/NAMING_CONVENTION.md`](docs/NAMING_CONVENTION.md) for canonical IDs.
  Short IDs: E0, E5, E0_ema21D1, E5_ema21D1. Code names: `vtrend`, `vtrend_e5`, `vtrend_ema21_d1`, `vtrend_e5_ema21_d1`.
  X0 = E0_ema21D1 (duplicate). X0_E5exit ≈ E5_ema21D1 (near-duplicate).
- `from __future__ import annotations` in mọi file (nếu viết mới).
- Dataclasses with type hints cho structured data.
- Line length 124, indent 4 spaces (Ruff formatter).
- Private helpers prefixed `_`.
- Mỗi strategy tự chứa — KHÔNG shared utility modules trong strategies/.
- Research study tự chứa trong `research/xNN/` — xem [RESEARCH_RULES.md](docs/research/RESEARCH_RULES.md).
- Research study riêng có thể có rules riêng (ví dụ: `research/x34/x34_RULES.md`).
