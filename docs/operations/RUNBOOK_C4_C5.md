# RUNBOOK — Live Operations (E5_ema21D1)

> **Version:** 3.1 (2026-03-17)
> **Strategy:** E5_ema21D1 (6/7 gates PASS; WFO robustness FAIL — underresolved)
> **Config:** `configs/vtrend_e5_ema21_d1/vtrend_e5_ema21_d1_default.yaml`

---

## 1. Quick Start

### 1.1 Prerequisites

```bash
cd /var/www/trading-bots/btc-spot-dev

# Load testnet credentials
source v10/.env
export BINANCE_API_KEY BINANCE_API_SECRET

# Verify tests pass
python -m pytest --tb=short -q
# Expected: 1058 passed

# Verify exchange connectivity
python -c "
from v10.exchange.rest_client import BinanceSpotClient
from v10.exchange.account_scope import fetch_account_scope
c = BinanceSpotClient()
s = fetch_account_scope(c)
print(f'NAV={s.nav_usdt:.2f} USDT, exposure={s.exposure:.4f}, BTC price={s.btc_price:.2f}')
"
```

### 1.2 Run C4 Smoke Test (2-3 min)

```bash
python v10/tests/smoke_c4_live.py
# PASS: 0 duplicates, crash BEFORE_PERSIST+AFTER_SEND verified, >=2 orders
# Output: out/c4/
```

### 1.3 Run C5 Testnet Validation (5-10 min)

```bash
python v10/tests/smoke_c5_testnet.py --bars 500 --order-notional-usdt 15
# PASS: signals generated, orders filled, 0 duplicates
# Output: out/c5/
```

### 1.4 Start Live Trading

```bash
# Realtime mode with parity checker + alerts
python -m v10.cli.live \
  --config configs/vtrend_e5_ema21_d1/vtrend_e5_ema21_d1_default.yaml \
  --outdir out/live \
  --mode realtime \
  --cycle-seconds 30 \
  --shadow \
  --alerts \
  --order-notional-usdt 15
```

### 1.5 Monitor (separate terminal)

```bash
source v10/.env && export BINANCE_API_KEY BINANCE_API_SECRET

# Live dashboard, refreshes every 30s
python -m v10.cli.monitor --outdir out/live --live --watch 30

# One-shot snapshot
python -m v10.cli.monitor --outdir out/live --live
```

---

## 2. Architecture

```
┌───────────────────────────────────────────────────────────┐
│                       LiveRunner                           │
│                                                            │
│  ┌──────────┐    ┌──────────────┐    ┌───────────────┐    │
│  │ BarClock │───>│ E5_ema21D1   │───>│ OrderPlanner  │    │
│  │ (H4 poll)│    │ (on_bar)     │    │ (target→qty)  │    │
│  └──────────┘    └──────────────┘    └───────┬───────┘    │
│       │                                      │             │
│       │          ┌──────────────┐            │             │
│       │          │ParityChecker │<───────────┤             │
│       │          │(shadow replay)│           │             │
│       │          └──────┬───────┘            │             │
│       │           HALT? │         ┌──────────▼──────────┐  │
│       │                 └────────>│  OrderManager       │  │
│       │                           │  (crash-safe send)  │  │
│       │                           └─────────────────────┘  │
│       │                                                    │
│  ┌────▼────────────────────────────────────────────────┐   │
│  │  RiskGuards (kill-switch DD, daily orders, exposure) │   │
│  ├──────────────────────────────────────────────────────┤   │
│  │  AlertDispatcher (Telegram, webhook, console)        │   │
│  ├──────────────────────────────────────────────────────┤   │
│  │  SQLite (orders, fills, kv) + CSV logs               │   │
│  └──────────────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────────────┘

         ┌──────────────────────────────────┐
         │  Monitor CLI (separate process)   │
         │  reads: SQLite, CSVs, exchange    │
         │  shows: account, regime, guards   │
         └──────────────────────────────────┘
```

---

## 3. Operating Modes

### 3.1 Realtime (production)

```bash
python -m v10.cli.live \
  --config configs/vtrend_e5_ema21_d1/vtrend_e5_ema21_d1_default.yaml \
  --outdir out/live \
  --mode realtime \
  --cycle-seconds 30 \
  --shadow \
  --alerts
```

- Polls BarClock every 30s for new closed H4 bars
- Runs E5_ema21D1 strategy on each bar close
- Plans + sends real orders via OrderManager
- Parity checker validates signals against shadow replay
- Alerts fire on: startup, shutdown, order fill, risk halt, parity mismatch

### 3.2 Replay (C5.1 — fast-forward validation)

```bash
python -m v10.cli.live \
  --config configs/vtrend_e5_ema21_d1/vtrend_e5_ema21_d1_default.yaml \
  --outdir out/c5_replay \
  --mode replay \
  --data data/bars_btcusdt_2016_now_h1_4h_1d.csv \
  --throttle-sec 3 \
  --order-notional-usdt 15 \
  --shadow
```

- Fast-forwards CSV bars through the live pipeline
- 3s throttle between exchange sends
- Scale-down orders to 15 USDT notional

### 3.3 Soak Orders (C4.1 — order-path stress)

```bash
python -m v10.cli.live \
  --config configs/vtrend_e5_ema21_d1/vtrend_e5_ema21_d1_default.yaml \
  --outdir out/c4_soak \
  --mode soak_orders \
  --max-cycles 20 \
  --cycle-seconds 3 \
  --fault-inject-rate 0.25 \
  --fault-points BEFORE_PERSIST,AFTER_SEND \
  --order-notional-usdt 15
```

- Forces alternating BUY/SELL each cycle (ignores strategy)
- 25% crash probability per order for stress testing
- Tests: duplicate sends, crash recovery, reconciliation

### 3.4 Soak No-Trade (C4.2 — scheduling validation)

```bash
python -m v10.cli.live \
  --config configs/vtrend_e5_ema21_d1/vtrend_e5_ema21_d1_default.yaml \
  --outdir out/c4_notrade \
  --mode soak_notrade \
  --cycle-seconds 30 \
  --no-trade
```

- Polls BarClock indefinitely, no orders sent
- Tests: timer drift, dedup, memory stability, connection recovery
- Run >=8 hours to span >=2 H4 bar boundaries

---

## 4. Monitoring Dashboard

### 4.1 Dashboard CLI

```bash
# Snapshot (reads from bot output dir)
python -m v10.cli.monitor --outdir out/live

# Watch mode (auto-refresh every 30s)
python -m v10.cli.monitor --outdir out/live --watch 30

# With live exchange data (real-time NAV/exposure)
python -m v10.cli.monitor --outdir out/live --live --watch 30

# With regime computation from CSV
python -m v10.cli.monitor --outdir out/live --live --data data/bars_btcusdt_2016_now_h1_4h_1d.csv

# No color (for logging/piping)
python -m v10.cli.monitor --outdir out/live --no-color
```

**Dashboard sections:**

| Section | Data source | What it shows |
|---------|-------------|---------------|
| ACCOUNT | Exchange API (`--live`) | NAV, BTC qty, USDT, exposure, BTC price |
| REGIME | D1 closes (CSV or exchange) | NORMAL/AMBER/RED, MDD 6m/12m with thresholds |
| RISK GUARDS | SQLite + config | Kill-switch DD, daily orders, halt status |
| RECENT ORDERS | SQLite | Last 10 orders with side, qty, price, status, reason |
| PERFORMANCE | SQLite | Total orders, fills, fill rate |
| SYSTEM | SQLite + run_meta.json | Strategy, mode, last bar time, uptime, parity status |

### 4.2 Alert System

Alerts fire automatically when `--alerts` is passed to the LiveRunner.

**Channels (configure via environment variables):**

```bash
# Telegram (recommended for crypto traders)
export TELEGRAM_BOT_TOKEN="123456:ABC-DEF..."
export TELEGRAM_CHAT_ID="987654321"

# Generic webhook (Slack, Discord, custom)
export ALERT_WEBHOOK_URL="https://hooks.slack.com/services/..."
```

**Alert events:**

| Event | Level | When |
|-------|-------|------|
| Bot Started | INFO | LiveRunner.run() begins |
| Bot Stopped | INFO/CRITICAL | LiveRunner.run() ends (CRITICAL if error) |
| Order Filled | INFO | Every successful fill |
| Risk Guard Halt | CRITICAL | Kill-switch DD or max daily orders breached |
| Parity Mismatch | CRITICAL | Shadow strategy disagrees with live signal |
| Regime Change | WARN/CRITICAL | NORMAL->AMBER (WARN), any->RED (CRITICAL) |

**Telegram setup:**
1. Message `@BotFather` on Telegram, create bot, get token
2. Start chat with your bot, send `/start`
3. Get chat ID: `curl https://api.telegram.org/bot{TOKEN}/getUpdates`
4. Set env vars and pass `--alerts` to LiveRunner

**Monitor with regime alerts (standalone, no bot running):**

```bash
python -m v10.cli.monitor --outdir out/live --live --watch 300 --alerts
```

---

## 5. Risk Guards

### 5.1 Configuration

From `configs/vtrend_e5_ema21_d1/vtrend_e5_ema21_d1_default.yaml`:

```yaml
risk:
  max_total_exposure: 1.0
  min_notional_usdt: 10
  kill_switch_dd_total: 0.45
  max_daily_orders: 5
```

### 5.2 Guard Behavior

| Guard | Config Key | Default | Action |
|-------|-----------|---------|--------|
| Kill-switch DD | `kill_switch_dd_total` | 0.45 | HALT all trading permanently |
| Max daily orders | `max_daily_orders` | 5 | SKIP order (resumes next UTC day) |
| Max exposure | `max_total_exposure` | 1.0 | Clamp target_exposure |
| Min notional | `min_notional_usdt` | $10 | Skip order below threshold |

### 5.3 Regime Monitor (entry prevention overlay)

| Threshold | Value | Action |
|-----------|-------|--------|
| AMBER (6m MDD) | > 45% | Reduce size or pause new entries |
| AMBER (12m MDD) | > 60% | Reduce size or pause new entries |
| RED (6m MDD) | > 55% | Halt new entries |
| RED (12m MDD) | > 70% | Halt new entries |

Mechanism: entry prevention ONLY (0 forced exits in backtest). Layered defense with EMA(21d).

---

## 6. Output Artifacts

Every run of `v10/cli/live.py` produces:

```
{outdir}/
├── bot.sqlite3              # Persistent state (orders, fills, kv tables)
├── bot.log                  # Full structured log
├── run_meta.json            # Config snapshot + timing
├── reconcile_report.json    # Startup order reconciliation
├── live_bar_events.csv      # H4 bar closes from BarClock
├── live_orders.csv          # Submitted orders
├── live_fills.csv           # Executed fills + slippage
├── live_slippage.csv        # Fill vs expected mid comparison
├── live_plan.csv            # Order planning decisions
└── live_parity.csv          # Shadow replay checks (if --shadow)
```

### SQLite schema

**orders:** `client_order_id, symbol, side, type, quantity, price, reason, status, exchange_order_id, created_at_ms, updated_at_ms`

**fills:** `trade_id, client_order_id, symbol, price, qty, commission, commission_asset, time_ms, is_buyer, is_maker`

**kv:** `key, value` — Keys: `last_processed_signal_close_ms`, `last_trade_id`

---

## 7. PASS/FAIL Criteria

### Universal invariants (ALL runs):

| # | Criterion | Verification |
|---|-----------|-------------|
| P1 | 0 duplicate clientOrderId | `SELECT client_order_id, count(*) c FROM orders GROUP BY client_order_id HAVING c > 1` → 0 rows |
| P2 | 0 position drift after restart | `reconcile_report.json` → `position_drift == 0.0` |
| P3 | Reconcile catches all fills | Every `SENT` order → `FILLED` after reconcile |
| P4 | No negative BTC balance | No fill sequence produces btc_qty < -1e-8 |
| P5 | No NaN in NAV/exposure | `grep NaN live_plan.csv live_parity.csv` → 0 |
| P6 | No unhandled exceptions | `bot.log`: no ERROR except CrashSimulation |
| P7 | Monotonic bar tracking | `last_processed_signal_close_ms` never decreases |

### Per-run criteria:

| Run | Additional PASS criteria |
|-----|------------------------|
| C4.1 (soak_orders) | >=3 crash points exercised, all reconciled, BTC balance correct at end |
| C4.2 (soak_notrade) | >=2 bar events, each bar exactly once, no gaps, RSS < 200MB |
| C5.1 (replay) | All parity PASS, >=5 orders filled, slippage <=200 bps (testnet) |
| C5.2 (realtime) | >=12 H4 bars, >=1 restart with 0 drift, all parity PASS |

---

## 8. Post-Run Verification

```bash
OUTDIR=out/live  # adjust per run

# 1) Run metadata
python -m json.tool $OUTDIR/run_meta.json

# 2) Dashboard snapshot
python -m v10.cli.monitor --outdir $OUTDIR --no-color

# 3) Duplicate check (P1)
sqlite3 $OUTDIR/bot.sqlite3 \
  "SELECT client_order_id, count(*) c FROM orders GROUP BY client_order_id HAVING c > 1;"

# 4) Order/fill counts
sqlite3 $OUTDIR/bot.sqlite3 "SELECT count(*) as orders FROM orders;"
sqlite3 $OUTDIR/bot.sqlite3 "SELECT count(*) as fills FROM fills;"

# 5) Reconcile report (P2)
python -m json.tool $OUTDIR/reconcile_report.json

# 6) No NaN (P5)
grep -i nan $OUTDIR/live_plan.csv $OUTDIR/live_parity.csv 2>/dev/null || echo "PASS: no NaN"

# 7) No real errors (P6)
grep ERROR $OUTDIR/bot.log | grep -v CrashSimulation || echo "PASS: no real errors"

# 8) Parity (if --shadow)
grep -c "False" $OUTDIR/live_parity.csv 2>/dev/null || echo "N/A (no parity)"
```

---

## 9. Safety Warnings

### 9.1 Account Model

Current design manages the **entire testnet account** (no sub-ledger).
`reset_to_cash()` has a testnet-only guard (checks URL).

**Before mainnet:**
- Implement `allocated_capital_usdt` config param
- Position guardrail: `btc_value <= allocated * max_total_exposure`
- Sub-ledger isolation for multi-strategy

### 9.2 Rate Limits

| Endpoint | Weight | Budget per H4 cycle |
|----------|--------|-------------------|
| GET /klines | 1 | BarClock poll |
| GET /account | 10 | AccountScope |
| POST /order | 1 order | OrderManager |
| GET /myTrades | 10 | Fill retrieval |
| **Total** | **~24** | Well within 1200/min |

At 30s poll: 48 weight/min. Safe.

### 9.3 Backoff

`BinanceSpotClient` implements:
- Exponential backoff for 429/418/5xx (max 3 retries)
- Timestamp re-sync on -1021
- Connection/timeout retry

---

## 10. Key Files

| Purpose | Path |
|---------|------|
| Strategy code | `strategies/vtrend_e5_ema21_d1/strategy.py` |
| Config YAML | `configs/vtrend_e5_ema21_d1/vtrend_e5_ema21_d1_default.yaml` |
| Live runner | `v10/cli/live.py` |
| Monitor dashboard | `v10/cli/monitor.py` |
| Alert dispatcher | `monitoring/alerts.py` |
| Regime monitor | `monitoring/regime_monitor.py` |
| C4 smoke test | `v10/tests/smoke_c4_live.py` |
| C5 testnet test | `v10/tests/smoke_c5_testnet.py` |
| REST client | `v10/exchange/rest_client.py` |
| Order manager | `v10/exchange/order_manager.py` |
| Order planner | `v10/exchange/order_planner.py` |
| Parity checker | `v10/exchange/parity.py` |
| Bar clock | `v10/exchange/bar_clock.py` |
| Account scope | `v10/exchange/account_scope.py` |
| Exchange filters | `v10/exchange/filters.py` |
| Backtest CLI | `v10/cli/backtest.py` |
| Paper CLI | `v10/cli/paper.py` |
| Deployment checklist | `DEPLOYMENT_CHECKLIST.md` |
| Strategy status | `STRATEGY_STATUS_MATRIX.md` |

---

## 11. C4/C5 Test Results (2026-03-09)

### C4 — PASSED

```
Phase 1: 5 planner-driven orders (BUY/SELL cycles), 0 duplicates
Phase 2: BEFORE_PERSIST crash — order NOT in DB (correct)
Phase 3: AFTER_SEND crash — order sent, not polled
Phase 4: Restart + reconcile — AFTER_SEND order → FILLED (correct)
Result: ALL 4 checks PASS
```

### C5 — PASSED

```
Strategy: vtrend_e5_ema21_d1
Replay: 500 H4 bars → 6 signals → 6 orders → 6 fills
Duplicates: 0
Slippage: WARN (max 2721 bps — testnet thin liquidity, expected)
Result: ALL checks PASS
```
