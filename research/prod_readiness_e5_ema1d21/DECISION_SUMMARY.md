# Decision Summary — E5+EMA1D21 Production Readiness

**Date**: 2026-03-09
**Research period**: 2026-03-05 to 2026-03-09
**Repo**: `btc-spot-claude` (validation), `btc-spot-dev` (research)
**Algorithm**: VTREND E5+EMA1D21 — promoted 2026-03-09, PSR=0.9993, all 7 gates PASS

---

## 1. Triển khai thật: GIU vs BO

### GIU — 5 component da proven

| # | Component | Ly do | Params |
|---|-----------|-------|--------|
| 1 | **VTREND E5+EMA1D21** | PRIMARY, PROMOTE, PSR=0.9993, all 7 gates PASS | slow=120, trail=3.0, vdo=0.0, ema=21d |
| 2 | **Robust ATR (E5)** | E5S simplification REJECTED (Sharpe diff 0.0881 > 0.02) | Q90-capped TR, Wilder EMA(20) |
| 3 | **D1 EMA(21) regime filter** | p=1.5e-5, 16/16 ALL metrics | D1 timeframe, range 15-40d proven |
| 4 | **VDO filter** | 16/16 timescales, DOF-corrected p=0.031 | threshold=0.0 |
| 5 | **Regime Monitor V2 (MDD-Only)** | +0.158 Sharpe, blocks 17 false entries, 0 forced exits | AMBER: 6m>45% or 12m>60%, RED: 6m>55% or 12m>70% |

**Risk Guards R1-R4** — da wired cho PaperRunner (max_exposure, min_notional, kill_switch, max_daily_orders).

### GIU — Infrastructure (can build/wire)

| Component | Trang thai | Can lam |
|-----------|------------|---------|
| Risk Guards (R1-R4) | Wired cho PaperRunner | Wire cho LiveRunner + Backtest |
| LiveRunner | Chua co (v10/cli/live.py placeholder) | Build tu PaperRunner template |
| C4/C5 Testnet validation | Chua chay | Chay tren Binance testnet truoc live |
| DOF Correction context | 93.8% confidence (not 95%) | Document ro: 4.35 effective tests, p=0.0625 |

### BO — Khong dua vao production

| Component | Ly do |
|-----------|-------|
| X0 (E0+EMA1D21) | HOLD, PSR=0.8908 < 0.95 — fails statistical bar |
| X1-X6 toan bo | REDUNDANT hoac CONFLICTING voi E5+EMA1D21 |
| SM | REJECT — alternative profile, not replacement |
| LATCH | REJECT — alternative profile, not replacement |
| E5S (simplified ATR) | REJECTED — Sharpe loss 0.0881 |
| V8 Apex | 40+ params, ZERO value over VTREND 3 params |
| V11-V13 | Legacy, superseded |
| E6, E7, VPULL, VBREAK, VCUSUM, VTWIN, V-RATCH, PE, PE* | All failed to beat E0 on ALL metrics |

### Operational Parameters cho Live

```
Algorithm:    VTREND E5+EMA1D21
Resolution:   H4 bars
Sizing:       f=0.30 (vol-target 15%)
Cost budget:  50 bps RT (harsh — deliberately above real-world)
Bootstrap:    Sharpe 0.54, CAGR 14.2%, MDD 61.0%, P(CAGR>0) 80.3%
Real-data:    Sharpe 1.19, CAGR 52.6%, MDD 61.4%, 226 trades
Monitor:      Regime Monitor V2 (MDD-only, dual-window)
              AMBER -> reduce size or pause new entries
              RED -> halt new entries (no forced exits)
```

---

## 2. Phong chong bo sot thong tin

### Van de goc

prod_readiness research (3 studies quan trong) khong duoc index vao MEMORY.md hoac STRATEGY_STATUS_MATRIX.md -> AI va developer deu bo qua.

3 studies bi bo sot:
- Regime Monitor V2 (PROMOTED, +0.158 Sharpe)
- E5S Validation (KEEP E5, Sharpe loss 0.088)
- DOF Correction (93.8% confidence, 4.35 effective tests)

### 3 bien phap da trien khai (2026-03-09)

**A. Cap nhat MEMORY.md** — them section "Production Readiness Research" voi operational values cu the (AMBER/RED thresholds, E5S rejection, DOF p-values).

**B. Tao DEPLOYMENT_CHECKLIST.md** — single source of truth cho deployment, tap hop TAT CA operational parameters tu moi research study. File: `btc-spot-claude/DEPLOYMENT_CHECKLIST.md`.

**C. Quy tac Cross-Reference** — moi research output PHAI duoc index vao it nhat 1 trong 3 files:
1. `STRATEGY_STATUS_MATRIX.md` — verdicts va key findings
2. `MEMORY.md` — operational values va parameters
3. `DEPLOYMENT_CHECKLIST.md` — neu deployment-relevant

Neu study tao ra operational parameters -> BAT BUOC phai co trong deployment checklist.

---

## 3. Production Readiness Studies — Chi tiet

### Study 1: Regime Monitor V2 (PROMOTED)

- **Code**: `regime_monitor_v2.py` -> promoted to `monitoring/regime_monitor.py`
- **Report**: `E5A_REGIME_MONITOR_V2_REPORT.md`
- **Mechanism**: Entry prevention ONLY (not exit forcing). Layered defense with EMA(21) regime filter.
- **V1 REJECTED**: raw ATR structurally broken (71.6% false RED rate)

| Threshold | Value | Action |
|-----------|-------|--------|
| AMBER (6m MDD) | > 45% | Reduce size or pause new entries |
| AMBER (12m MDD) | > 60% | Reduce size or pause new entries |
| RED (6m MDD) | > 55% | Halt new entries |
| RED (12m MDD) | > 70% | Halt new entries |

Performance impact (harsh, 50 bps RT):

| Metric | E5 Vanilla | E5+Monitor-V2 | Delta |
|--------|----------:|-------------:|------:|
| Sharpe | 1.0909 | 1.2487 | +0.1578 |
| CAGR % | 40.72 | 47.96 | +7.25 |
| MDD % | 50.13 | 44.46 | -5.67 |
| Trades | 199 | 182 | -17 |
| Monitor exits | -- | 0 | -- |

### Study 2: E5S Validation (KEEP E5)

- **Code**: `e5s_validation.py`
- **Report**: `E5S_VALIDATION_REPORT.md`
- **Question**: Can robust ATR (3 extra params) be simplified to standard ATR(20)?
- **Answer**: NO. Sharpe diff = 0.0881 (threshold < 0.02). E5S does not qualify.

| Metric | E5 | E5S | Delta |
|--------|---:|----:|------:|
| Sharpe | 1.4300 | 1.3419 | -0.0881 |
| CAGR % | 59.85 | 55.16 | -4.69 |
| MDD % | 41.64 | 42.30 | +0.66 |

### Study 3: DOF Correction (SUGGESTIVE)

- **Code**: `e5_dof_correction.py`
- **Report**: `E5_DOF_CORRECTION_REPORT.md`
- **Problem**: 16 timescales are NOT independent (mean adjacent rho = 0.976)
- **Nyholt M_eff**: 4.35 effective independent tests (out of 16)

| Comparison | Nominal p | Nyholt p | Confidence |
|------------|-----------|----------|------------|
| E5 vs X0 | 1.5e-5 | 0.0625 | 93.8% |
| E5 vs E5S | 1.5e-5 | 0.0312 | 96.9% |

Effect size: +0.089 Sharpe, consistent at ALL 16 timescales (min +0.042, max +0.134).

---

## 4. Key File References

| Purpose | Path |
|---------|------|
| Strategy code | `strategies/vtrend_e5_ema21_d1/strategy.py` |
| Config | `configs/vtrend_e5_ema21_d1/vtrend_e5_ema21_d1_default.yaml` |
| Regime monitor (production) | `monitoring/regime_monitor.py` |
| Validation results | `results/full_eval_e5_ema21d1/` |
| Deployment checklist | `DEPLOYMENT_CHECKLIST.md` |
| Strategy status matrix | `STRATEGY_STATUS_MATRIX.md` |
| Full research registry | `btc-spot-dev/research/results/COMPLETE_RESEARCH_REGISTRY.md` |
