# Task C: Run Formal Validation Pipeline (7 Gates)

## Prerequisites
- Task B completed: `vtrend_e5_ema21_d1_vc` strategy exists and is registered
- Phase 2 reproduction check PASSED (d_Sharpe same sign, within ±30%)

## Session prompt

```
Read /var/www/trading-bots/btc-spot-dev/research/x39/specs/formal_validation_spec.md
Read /var/www/trading-bots/btc-spot-dev/research/x39/specs/task_c_formal_validation.md

Execute Phase 3 of the formal validation spec.
Run the validation pipeline for BOTH thresholds (0.6 and 0.7).
```

## What this task does

Run `validate_strategy.py` twice:
1. `vtrend_e5_ema21_d1_vc` (thr=0.6) vs `vtrend_e5_ema21_d1` (baseline)
2. `vtrend_e5_ema21_d1_vc` (thr=0.7) vs `vtrend_e5_ema21_d1` (baseline)

Baseline is E5-ema21D1 (NOT E0/vtrend), because we're testing whether
vol compression improves E5-ema21D1 specifically.

---

## Step 1: Run validation for thr=0.6

```bash
cd /var/www/trading-bots/btc-spot-dev

python validate_strategy.py \
  --strategy vtrend_e5_ema21_d1_vc \
  --baseline vtrend_e5_ema21_d1 \
  --config configs/vtrend_e5_ema21_d1_vc/vtrend_e5_ema21_d1_vc_default.yaml \
  --baseline-config configs/vtrend_e5_ema21_d1/vtrend_e5_ema21_d1_default.yaml \
  --out results/full_eval_e5_ema21d1_vc_06 \
  --suite all
```

After completion:
1. Read `results/full_eval_e5_ema21d1_vc_06/reports/decision.json` → record verdict
2. Read `results/full_eval_e5_ema21d1_vc_06/results/wfo_summary.json` → record Wilcoxon p, win rate
3. Read `results/full_eval_e5_ema21d1_vc_06/results/full_backtest_summary.csv` → record metrics
4. Read `results/full_eval_e5_ema21d1_vc_06/reports/validation_report.md` → review

---

## Step 2: Run validation for thr=0.7

```bash
python validate_strategy.py \
  --strategy vtrend_e5_ema21_d1_vc \
  --baseline vtrend_e5_ema21_d1 \
  --config configs/vtrend_e5_ema21_d1_vc/vtrend_e5_ema21_d1_vc_07.yaml \
  --baseline-config configs/vtrend_e5_ema21_d1/vtrend_e5_ema21_d1_default.yaml \
  --out results/full_eval_e5_ema21d1_vc_07 \
  --suite all
```

Same review steps as Step 1.

---

## Step 3: Compare results

Fill in this table:

| Metric | thr=0.6 | thr=0.7 | Winner |
|--------|---------|---------|--------|
| Verdict (PROMOTE/HOLD/REJECT) | | | |
| Exit code | | | |
| G1 Lookahead | | | |
| G2 Full harsh delta | | | |
| G3 Holdout harsh delta | | | |
| G4 WFO Wilcoxon p | | | |
| G4 WFO Bootstrap CI | | | |
| G5 Trade-level bootstrap | | | |
| G6 Selection bias (DSR) | | | |
| Full Sharpe | | | |
| Full d_Sharpe vs baseline | | | |
| Full CAGR% | | | |
| Full MDD% | | | |
| Full d_MDD | | | |
| Trades | | | |
| Calmar ratio | | | |
| Holdout d_Sharpe | | | |

---

## Interpretation guide

### If PROMOTE (exit 0)
Vol compression passes all 7 gates. This is strong evidence. Proceed to Task D
for multiple testing correction — if DSR also passes, conclusion is robust.

### If HOLD (exit 1)
Most likely cause: G4 WFO FAIL (Wilcoxon p > 0.10).
This is the SAME situation as current E5-ema21D1 (HOLD since 2026-03-17).
Not a rejection — just insufficient OOS statistical power.

Check:
- Is G4 the only failing gate?
- What is the WFO win rate? (Even if Wilcoxon fails, 7/8 or 8/8 positive is encouraging)
- What does trade-level bootstrap (G5) say?

### If REJECT (exit 2)
Hard gate failure. Serious — means v10 engine shows a fundamental problem.
Check which hard gate failed:
- G1 Lookahead: implementation bug (vol_ratio uses future data somehow)
- G2/G3 Delta: d_Sharpe is negative or very small in formal engine

If REJECT, do NOT proceed to Task D. Diagnose the failure first.

---

## After completion

Write results back to `formal_validation_spec.md` Phase 3 section.
Record the FULL decision.json content for both thresholds.

If either threshold achieves PROMOTE or HOLD → proceed to Task D.
If both REJECT → spec is CLOSED, vol compression does not survive formal validation.
