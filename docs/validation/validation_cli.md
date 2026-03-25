# Validation CLI

Unified command:

```bash
python3 validate_strategy.py \
  --strategy <candidate> \
  --baseline <baseline> \
  --config <cand.yaml> \
  --baseline-config <base.yaml> \
  --out <dir>
```

## Related docs

- [Validation Docs Index](README.md)
- [Decision Policy](decision_policy.md)
- [Output Contract](output_contract.md)
- [Validation Changelog](validation_changelog.md)

## 1) E5_ema21D1 vs E0 baseline — full suite (recommended)

```bash
python3 validate_strategy.py \
  --strategy vtrend_e5_ema21_d1 \
  --baseline vtrend \
  --config configs/vtrend_e5_ema21_d1/vtrend_e5_ema21_d1_default.yaml \
  --baseline-config configs/vtrend/vtrend_default.yaml \
  --out out_validation_e5_ema21d1 \
  --suite full \
  --scenarios smart,base,harsh \
  --bootstrap 2000 \
  --selection-bias deflated \
  --lookahead-check on
```

## 2) Quick suite (basic, no bootstrap)

```bash
python3 validate_strategy.py \
  --strategy vtrend_e5_ema21_d1 \
  --baseline vtrend \
  --config configs/vtrend_e5_ema21_d1/vtrend_e5_ema21_d1_default.yaml \
  --baseline-config configs/vtrend/vtrend_default.yaml \
  --out out_validation_quick \
  --suite basic \
  --bootstrap 0 \
  --lookahead-check off
```

## 3) Trade-only suite

```bash
python3 validate_strategy.py \
  --strategy vtrend_e5_ema21_d1 \
  --baseline vtrend \
  --config configs/vtrend_e5_ema21_d1/vtrend_e5_ema21_d1_default.yaml \
  --baseline-config configs/vtrend/vtrend_default.yaml \
  --out out_validation_trade \
  --suite trade \
  --trade-level on \
  --bootstrap 1000
```

## 4) All suites (includes PSR gate, holdout, sensitivity)

```bash
python3 validate_strategy.py \
  --strategy vtrend_e5_ema21_d1 \
  --baseline vtrend \
  --config configs/vtrend_e5_ema21_d1/vtrend_e5_ema21_d1_default.yaml \
  --baseline-config configs/vtrend/vtrend_default.yaml \
  --out out_validation_all \
  --suite all \
  --scenarios harsh
```

## 5) Quality checks bundle

```bash
python3 validate_strategy.py \
  --strategy v10_baseline \
  --baseline v10_baseline \
  --config v10/configs/baseline_legacy.live.yaml \
  --baseline-config v10/configs/baseline_legacy.live.yaml \
  --out out_validation_quality \
  --force \
  --data-integrity-check on \
  --cost-sweep-bps 0,10,25,50,75,100 \
  --cost-sweep-mode quick \
  --invariant-check on \
  --regression-guard off \
  --churn-metrics on
```

Cost sweep notes:

- `--cost-sweep-bps`: comma-separated round-trip bps list (default `0,10,25,50,75,100`).
- `--cost-sweep-mode quick`: runs recent-history subset for faster runtime.
- `--cost-sweep-mode full`: runs full validation period.
- Output `results/cost_sweep.csv` schema:
  - `bps, strategy_id, final_nav, CAGR, MDD, trades, turnover, total_fees, score_primary`
- `reports/quality_checks.md` includes:
  - breakeven bps (`CAGR <= 0` or `score_primary <= 0`)
  - slope approximation `Δscore/Δbps` for `0->50` and `50->100`.

## 6) Regression guard with golden snapshot

Use this when a baseline/feature is already promoted and future changes must stay within accepted drift.

Golden format:

- File: JSON or YAML (`--golden`)
- Required fields: `dataset_id`, `period`, `scenario`, `strategy_id`, `metrics_expected`, `tolerances`
- Template: `docs/golden_template.yaml`

Create golden from a promoted run:

```bash
python3 - <<'PY'
import csv
from pathlib import Path

import yaml

OUTDIR = Path("out_validation_promoted")
GOLDEN = Path("docs/golden_from_promoted.yaml")

rows = list(csv.DictReader((OUTDIR / "results/full_backtest_summary.csv").open()))
cand = next(r for r in rows if r["label"] == "candidate" and r["scenario"] == "harsh")

payload = {
    "dataset_id": "default",
    "period": {"start": "2019-01-01", "end": "2026-02-20"},
    "scenario": "harsh",
    "strategy_id": "v10_baseline",
    "metrics_expected": {
        "harsh_score": float(cand["score"]),
        "CAGR": float(cand["cagr_pct"]),
        "MDD": float(cand["max_drawdown_mid_pct"]),
        "trades": int(float(cand["trades"])),
        "turnover": float(cand["turnover_per_year"]),
        "fees": float(cand["fees_total"]),
    },
    "tolerances": {
        "harsh_score": 0.25,
        "CAGR": 0.50,
        "MDD": 0.75,
        "trades": 2,
        "turnover": 2.0,
        "fees": 100.0,
    },
}

GOLDEN.write_text(yaml.safe_dump(payload, sort_keys=False))
print(f"wrote {GOLDEN}")
PY
```

Run validation with regression guard ON:

```bash
python3 validate_strategy.py \
  --strategy v10_baseline \
  --baseline v10_baseline \
  --config v10/configs/baseline_legacy.live.yaml \
  --baseline-config v10/configs/baseline_legacy.live.yaml \
  --out out_validation_regression_guard \
  --suite basic \
  --regression-guard on \
  --golden docs/golden_from_promoted.yaml
```

Regression-guard outputs:

- `results/regression_guard.json`
  - `pass` / `status`
  - `checked_metrics`
  - `deltas`
  - `violated_metrics`
- `reports/quality_checks.md` (summary table + violated items)

Policy:

- If `data_integrity` fails, verdict is forced to `ERROR` (exit code `3`).
- If `invariants` fails, verdict is forced to `ERROR` (exit code `3`).
- If `--regression-guard on` and guard fails, verdict is forced to `ERROR` (exit code `3`) (chosen policy: `ERROR`, not `REJECT`).
- `cost_sweep` and `churn_metrics` are non-blocking by default:
  - warnings are written into `reports/decision.json`.
  - they do not force fail/reject on their own.

## Exit codes

- `0`: PROMOTE
- `1`: HOLD
- `2`: REJECT
- `3`: ERROR

## Key outputs

- `logs/run.log`
- `configs/*`
- `results/full_backtest_summary.csv`
- `results/regime_decomposition.csv`
- `results/wfo_per_round_metrics.csv`
- `results/wfo_summary.json`
- `results/final_holdout_metrics.csv`
- `reports/validation_report.md`
- `reports/quality_checks.md`
- `reports/decision.json`
- `reports/discovered_tests.md`
- `index.txt`

`reports/decision.json` includes:

- `verdict`
- `exit_code`
- `reasons`
- `failures`
- `warnings` (non-blocking signals, including cost/churn warnings)
- `errors` (blocking error signals used for `ERROR` verdicts)
- `deltas`
- `key_links`
- `gates[]`
- `metadata`

## Tracking guideline

- Dùng `docs/validation/` cho tài liệu chuẩn, ổn định theo thời gian.
- Dùng `out_*/reports/*` cho kết quả mỗi lần chạy.
- Mỗi khi đổi gate/threshold/output, cập nhật `validation_changelog.md`.
