# Changelog

## 2026-03-17 — Post-Fix Re-validation (All Studies)

Full re-run of ~195 scripts after framework fixes (WFO overlap, Trade.pnl fees,
holdout off-by-one, VDO fallback, PSR demotion, etc.). Results:

- **pytest**: 1284/1284 PASS
- **E5_ema21D1**: HOLD (WFO robustness FAIL: Wilcoxon p=0.125, Bootstrap CI crosses zero)
- **E0_ema21D1**: HOLD (WFO robustness FAIL)
- **All research scripts**: 195 scripts, 0 real failures
- **VCBB bias study**: All 6 tests pass, findings unchanged

E5_ema21D1 post-fix metrics (harsh, 50 bps):
Sharpe 1.4545, CAGR 61.60%, MDD 40.97%, 188 trades.
WFO result is **underresolved** (insufficient OOS power with n=8 windows),
not negative-confirmed. See x36 program note 04_wfo_power_authority_reform.md.

---

## 2026-03-09 — Framework Reform, Re-validation & Strategy Selection

### Framework Bugs Found & Fixed

1. **E5_ema21D1 config: vestigial `atr_period` field**
   - `VTrendE5Ema21D1Config` contained `atr_period: int = 14` (inherited from E0)
   - E5 strategy uses `ratr_period` (robust ATR) — `atr_period` was never accessed
   - Pipeline's `AccessTracker` correctly flagged `unused_config:candidate:atr_period`
   - This caused verdict=ERROR (exit code 3) despite all 7 validation gates passing
   - **Fix**: Removed dead field from dataclass. No parameter values changed.

### Validation Framework Upgrades (pre-existing in this session)

- Wilcoxon signed-rank test for WFO round deltas (replaces binary win-rate as gate)
- Bootstrap CI for WFO deltas
- PSR (Probabilistic Sharpe Ratio) gate in selection_bias suite (threshold=0.95)
- Holdout/WFO overlap detection and reporting

### Re-validation Results (`--suite all`, 50 bps harsh cost)

#### E5_ema21D1 (`vtrend_e5_ema21_d1`) → **HOLD** (exit code 1)

*Note: Originally reported as PROMOTE on 2026-03-09. Re-validation on 2026-03-17
after framework fixes (WFO overlap, Trade.pnl fees, PSR demotion) changed verdict.*

| Gate | Status | Detail |
|------|--------|--------|
| lookahead | PASS | clean |
| full_harsh_delta | PASS | +26.53 vs E0 baseline |
| holdout_harsh_delta | PASS | +5.58 vs E0 baseline |
| wfo_robustness | **FAIL** | Wilcoxon p=0.125 (> α=0.1), Bootstrap CI [-3.44, 29.28] crosses zero |
| bootstrap | INFO | P(better)=97.2% (diagnostic) |
| trade_level_bootstrap | INFO | P(delta>0)=95.0% |
| selection_bias | INFO | PSR=0.9999 (demoted to info, no longer binding) |

- Harsh: Sharpe 1.4545, CAGR 61.60%, MDD 40.97%, 188 trades
- Single failure: WFO soft gate (underresolved, not negative-confirmed)

#### E0_ema21D1 (`vtrend_ema21_d1`) → **HOLD** (exit code 1)

| Gate | Status | Detail |
|------|--------|--------|
| lookahead | PASS | clean |
| full_harsh_delta | PASS | +7.37 vs E0 baseline |
| holdout_harsh_delta | PASS | +5.98 vs E0 baseline |
| wfo_robustness | **FAIL** | Wilcoxon + Bootstrap CI fail (2026-03-17 re-run) |
| bootstrap | INFO | diagnostic |
| trade_level_bootstrap | INFO | diagnostic |
| selection_bias | INFO | PSR demoted to info (2026-03-17) |

- Harsh: Sharpe ~1.37 (2026-03-17 re-run)
- Failure: WFO robustness (was PSR before PSR demotion)

### Strategy Promotion

- **Previous best**: E0_ema21D1, promoted Study #41 (2026-03-05)
- **Primary candidate**: E5_ema21D1, selected 2026-03-09 after framework reform
- **2026-03-17 update**: Both E5_ema21D1 and E0_ema21D1 now HOLD after framework fixes. E5_ema21D1 remains primary candidate (strongest full-sample evidence), but WFO OOS evidence is underresolved.

### Comparative (E5_ema21D1 vs E0_ema21D1)

| Dimension | E5_ema21D1 | E0_ema21D1 | Winner |
|-----------|-----------|-----|--------|
| Verdict (2026-03-17) | HOLD | HOLD | — |
| Full harsh delta | +26.53 | — | E5 |
| Holdout delta | +5.58 | — | E5 |
| PSR (info) | 0.9999 | — | E5 |
| Sharpe (harsh) | 1.4545 | ~1.37 | E5 |
| Bootstrap P(better) | 97.2% | — | E5 |
| WFO win rate | 62.5% | — | — |

E5_ema21D1 has stronger full-sample evidence but both HOLD due to WFO gate.

### Output Artifacts

- `results/full_eval_e5_ema21d1/reports/decision.json` — E5_ema21D1 HOLD
- `results/full_eval_x0_ema21d1/reports/decision.json` — E0_ema21D1 HOLD

### Code Cleanup (from audit, same date)

1. **E5 strategy: removed dead `atr_period` code path**
   - `VTrendE5Config.atr_period`, `self._atr` variable, `_atr()` computation and helper
   - Never used in `on_bar()` — only `self._ratr` was used
   - Created false impression that E5 had a standard ATR(14) fallback

2. **VTREND_BLUEPRINT.md**: added correction header (Section 7 frozen at Study #41)

3. **E1_1_EXECUTION_SPEC.md**: fixed "X0 = E5+EMA21(D1)" error — X0 uses standard ATR(14)

4. **Superseded X0A regime monitor files** moved to `rejected/` subdirectory

5. **Deployment spec**: fallback `strategy_id: vtrend_x0` → `vtrend_ema21_d1` (canonical)

6. **validation_changelog.md**: added 2026-03-09 framework reform entry

### Code Cleanup — Round 2 (same date)

7. **Fragility audit reports**: added SUPERSEDED headers to `step4_report.md`,
   `step5_report.md`, `cross_branch_synthesis_notes.md` — E0_ema21D1 no longer PRIMARY

8. **research/x0/P3_4_EVALUATION_REPORT.md**: added SUPERSEDED header

9. **Dead `atr_period` removed** from `vtrend_x0_e5exit` and `vtrend_x0_volsize` configs
   (SM retains it — SM actually uses `atr_period` for exit floor ATR computation)

10. **RUNBOOK_C4_C5.md**: added OUTDATED header — references `baseline_legacy.live.yaml`,
    must use E5_ema21D1 config for C4/C5

11. **search_log.md**: added naming disambiguation — next-wave "X0" = `vtrend_x0_e5exit`
    (≈ E5_ema21D1), not project-wide "X0" = `vtrend_x0` (= E0_ema21D1)

12. **decision_policy.md**: added nomenclature table (E5_ema21D1/E0_ema21D1/E0 strategy IDs) and PSR gate
    documentation (threshold=0.95, added in framework reform)

13. **README.md**: clarified HOLD ≠ FALLBACK for E0_ema21D1

14. **VTREND_BLUEPRINT.md**: fixed `sqrt(2190)` → `sqrt(6.0 * 365.25)` = sqrt(2191.5)

15. **X6_FULL_EVALUATION_REPORT.md**: added framework reform context note
