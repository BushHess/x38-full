#!/usr/bin/env python3
"""P0.2 -- Validation for exit-floor survivors."""

from __future__ import annotations

import csv
import json
import math
import sys
import time
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from dateutil.relativedelta import relativedelta

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from research.e0_exit_floor.p0_1_exit_floor_benchmark import ExitFloorConfig, X0ExitFloorStrategy
from research.lib.pair_diagnostic import render_review_template, run_pair_diagnostic
from strategies.vtrend_x0_e5exit.strategy import VTrendX0E5ExitConfig, VTrendX0E5ExitStrategy
from v10.core.data import DataFeed
from v10.core.engine import BacktestEngine
from v10.core.types import SCENARIOS
from v10.research.bootstrap import (
    calc_cagr,
    calc_max_drawdown,
    calc_sharpe,
    paired_block_bootstrap,
)


DATA = str(ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv")
OUTDIR = Path(__file__).resolve().parent

START = "2019-01-01"
END = "2026-02-20"
WARMUP = 365
INITIAL_CASH = 10_000.0

HOLDOUT_START = "2024-01-01"
PRE_HOLDOUT_END = "2023-12-31"

WFO_TRAIN_MO = 24
WFO_TEST_MO = 6
WFO_STEP_MO = 3

PAIR_BOOTSTRAP_N = 2000
PAIR_BOOTSTRAP_BLOCK = 20
PAIR_BOOTSTRAP_SEED = 42


def make_reference():
    return VTrendX0E5ExitStrategy(VTrendX0E5ExitConfig())


def candidate_factories():
    return {
        "X0E5_LL30": lambda: X0ExitFloorStrategy(
            ExitFloorConfig(strategy_id="x0e5_ll30", floor_mode="ll")
        ),
        "X0E5_FLOOR_LATCH": lambda: X0ExitFloorStrategy(
            ExitFloorConfig(
                strategy_id="x0e5_floor_latch",
                floor_mode="floor",
                floor_atr_mult=2.0,
            )
        ),
    }


def run_one(strategy_factory, start: str, end: str, scenario: str):
    feed = DataFeed(DATA, start=start, end=end, warmup_days=WARMUP)
    engine = BacktestEngine(
        feed=feed,
        strategy=strategy_factory(),
        cost=SCENARIOS[scenario],
        initial_cash=INITIAL_CASH,
        warmup_days=WARMUP,
        warmup_mode="no_trade",
    )
    return engine.run()


def backtest_table(candidates: dict[str, callable]) -> tuple[list[dict], dict]:
    rows: list[dict] = []
    results: dict[str, dict] = {"reference": {}}
    for cid in candidates:
        results[cid] = {}

    for scenario in ("smart", "base", "harsh"):
        ref_res = run_one(make_reference, START, END, scenario)
        results["reference"][scenario] = ref_res
        s = ref_res.summary
        rows.append({
            "slice": "full",
            "strategy": "reference",
            "candidate_id": "",
            "scenario": scenario,
            "sharpe": s["sharpe"],
            "cagr_pct": s["cagr_pct"],
            "mdd_pct": s["max_drawdown_mid_pct"],
            "calmar": s["calmar"],
            "trades": s["trades"],
            "win_rate_pct": s["win_rate_pct"],
            "profit_factor": s["profit_factor"],
            "avg_exposure": s["avg_exposure"],
            "total_return_pct": s["total_return_pct"],
        })
        for cid, factory in candidates.items():
            cand_res = run_one(factory, START, END, scenario)
            results[cid][scenario] = cand_res
            s = cand_res.summary
            rows.append({
                "slice": "full",
                "strategy": "candidate",
                "candidate_id": cid,
                "scenario": scenario,
                "sharpe": s["sharpe"],
                "cagr_pct": s["cagr_pct"],
                "mdd_pct": s["max_drawdown_mid_pct"],
                "calmar": s["calmar"],
                "trades": s["trades"],
                "win_rate_pct": s["win_rate_pct"],
                "profit_factor": s["profit_factor"],
                "avg_exposure": s["avg_exposure"],
                "total_return_pct": s["total_return_pct"],
            })
    return rows, results


def holdout_table(candidates: dict[str, callable]) -> tuple[list[dict], dict]:
    windows = [
        ("pre_holdout", START, PRE_HOLDOUT_END),
        ("holdout", HOLDOUT_START, END),
    ]
    rows: list[dict] = []
    results: dict[str, dict] = {}
    for slice_id, start, end in windows:
        results[slice_id] = {"reference": {}}
        for cid in candidates:
            results[slice_id][cid] = {}
        for scenario in ("smart", "base", "harsh"):
            ref_res = run_one(make_reference, start, end, scenario)
            results[slice_id]["reference"][scenario] = ref_res
            s = ref_res.summary
            rows.append({
                "slice": slice_id,
                "strategy": "reference",
                "candidate_id": "",
                "scenario": scenario,
                "start": start,
                "end": end,
                "sharpe": s["sharpe"],
                "cagr_pct": s["cagr_pct"],
                "mdd_pct": s["max_drawdown_mid_pct"],
                "calmar": s["calmar"],
                "trades": s["trades"],
                "win_rate_pct": s["win_rate_pct"],
                "profit_factor": s["profit_factor"],
                "avg_exposure": s["avg_exposure"],
                "total_return_pct": s["total_return_pct"],
            })
            for cid, factory in candidates.items():
                cand_res = run_one(factory, start, end, scenario)
                results[slice_id][cid][scenario] = cand_res
                s = cand_res.summary
                rows.append({
                    "slice": slice_id,
                    "strategy": "candidate",
                    "candidate_id": cid,
                    "scenario": scenario,
                    "start": start,
                    "end": end,
                    "sharpe": s["sharpe"],
                    "cagr_pct": s["cagr_pct"],
                    "mdd_pct": s["max_drawdown_mid_pct"],
                    "calmar": s["calmar"],
                    "trades": s["trades"],
                    "win_rate_pct": s["win_rate_pct"],
                    "profit_factor": s["profit_factor"],
                    "avg_exposure": s["avg_exposure"],
                    "total_return_pct": s["total_return_pct"],
                })
    return rows, results


def generate_wfo_windows(start: str, end: str) -> list[tuple[str, str, str]]:
    s = datetime.strptime(start, "%Y-%m-%d")
    e = datetime.strptime(end, "%Y-%m-%d")
    windows: list[tuple[str, str, str]] = []
    test_s = s + relativedelta(months=WFO_TRAIN_MO)
    wid = 0
    while test_s < e:
        test_e = min(test_s + relativedelta(months=WFO_TEST_MO), e)
        if test_e <= test_s:
            break
        windows.append((f"w{wid}", test_s.strftime("%Y-%m-%d"), test_e.strftime("%Y-%m-%d")))
        wid += 1
        test_s = test_s + relativedelta(months=WFO_STEP_MO)
    return windows


def run_wfo(candidates: dict[str, callable]) -> tuple[list[dict], dict]:
    windows = generate_wfo_windows(START, END)
    rows: list[dict] = []
    summary: dict[str, dict] = {}
    for cid in candidates:
        summary[cid] = {
            "windows": len(windows),
            "candidate_sharpe_wins": 0,
            "candidate_cagr_wins": 0,
            "candidate_mdd_wins": 0,
            "candidate_calmar_wins": 0,
        }

    for wid, start, end in windows:
        ref_res = run_one(make_reference, start, end, "harsh")
        r = ref_res.summary
        for cid, factory in candidates.items():
            cand_res = run_one(factory, start, end, "harsh")
            c = cand_res.summary
            if (c["sharpe"] or 0.0) > (r["sharpe"] or 0.0):
                summary[cid]["candidate_sharpe_wins"] += 1
            if (c["cagr_pct"] or 0.0) > (r["cagr_pct"] or 0.0):
                summary[cid]["candidate_cagr_wins"] += 1
            if (c["max_drawdown_mid_pct"] or 0.0) < (r["max_drawdown_mid_pct"] or 0.0):
                summary[cid]["candidate_mdd_wins"] += 1
            if (c["calmar"] or 0.0) > (r["calmar"] or 0.0):
                summary[cid]["candidate_calmar_wins"] += 1
            rows.append({
                "candidate_id": cid,
                "window_id": wid,
                "start": start,
                "end": end,
                "ref_sharpe": r["sharpe"],
                "cand_sharpe": c["sharpe"],
                "d_sharpe": round((c["sharpe"] or 0.0) - (r["sharpe"] or 0.0), 4),
                "ref_cagr_pct": r["cagr_pct"],
                "cand_cagr_pct": c["cagr_pct"],
                "d_cagr_pct": round((c["cagr_pct"] or 0.0) - (r["cagr_pct"] or 0.0), 2),
                "ref_mdd_pct": r["max_drawdown_mid_pct"],
                "cand_mdd_pct": c["max_drawdown_mid_pct"],
                "d_mdd_pct": round((c["max_drawdown_mid_pct"] or 0.0) - (r["max_drawdown_mid_pct"] or 0.0), 2),
                "ref_calmar": r["calmar"],
                "cand_calmar": c["calmar"],
                "d_calmar": round((c["calmar"] or 0.0) - (r["calmar"] or 0.0), 4),
                "ref_trades": r["trades"],
                "cand_trades": c["trades"],
                "d_trades": c["trades"] - r["trades"],
            })
    return rows, summary


def run_bootstrap_pair(equity_candidate, equity_reference) -> list[dict]:
    def neg_mdd(returns):
        return -calc_max_drawdown(returns)

    metrics = [
        ("sharpe", calc_sharpe),
        ("cagr_pct", calc_cagr),
        ("neg_mdd", neg_mdd),
    ]
    rows: list[dict] = []
    for metric_name, metric_fn in metrics:
        res = paired_block_bootstrap(
            equity_a=equity_candidate,
            equity_b=equity_reference,
            metric_fn=metric_fn,
            metric_name=metric_name,
            n_bootstrap=PAIR_BOOTSTRAP_N,
            block_size=PAIR_BOOTSTRAP_BLOCK,
            seed=PAIR_BOOTSTRAP_SEED,
        )
        rows.append({
            "metric": metric_name,
            "observed_candidate": res.observed_a,
            "observed_reference": res.observed_b,
            "observed_delta": res.observed_delta,
            "mean_delta": res.mean_delta,
            "ci_lower": res.ci_lower,
            "ci_upper": res.ci_upper,
            "p_candidate_better": res.p_a_better,
            "block_size": res.block_size,
            "n_bootstrap": res.n_bootstrap,
        })
    return rows


def save_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_candidate_report(
    candidate_id: str,
    full_rows: list[dict],
    holdout_rows: list[dict],
    wfo_summary: dict,
    bootstrap_rows: list[dict],
    pair_diag: dict,
) -> tuple[str, str]:
    full_harsh_ref = next(r for r in full_rows if r["strategy"] == "reference" and r["scenario"] == "harsh")
    full_harsh_cand = next(r for r in full_rows if r["strategy"] == "candidate" and r["candidate_id"] == candidate_id and r["scenario"] == "harsh")
    holdout_harsh_ref = next(r for r in holdout_rows if r["slice"] == "holdout" and r["strategy"] == "reference" and r["scenario"] == "harsh")
    holdout_harsh_cand = next(r for r in holdout_rows if r["slice"] == "holdout" and r["strategy"] == "candidate" and r["candidate_id"] == candidate_id and r["scenario"] == "harsh")
    pre_harsh_ref = next(r for r in holdout_rows if r["slice"] == "pre_holdout" and r["strategy"] == "reference" and r["scenario"] == "harsh")
    pre_harsh_cand = next(r for r in holdout_rows if r["slice"] == "pre_holdout" and r["strategy"] == "candidate" and r["candidate_id"] == candidate_id and r["scenario"] == "harsh")
    boot_by_metric = {r["metric"]: r for r in bootstrap_rows}
    wfo = wfo_summary[candidate_id]

    holdout_good = (holdout_harsh_cand["calmar"] or 0.0) >= (holdout_harsh_ref["calmar"] or 0.0)
    wfo_good = wfo["candidate_calmar_wins"] >= math.ceil(wfo["windows"] / 2)
    boot_good = boot_by_metric["sharpe"]["p_candidate_better"] > 0.55 and boot_by_metric["neg_mdd"]["p_candidate_better"] > 0.55
    pair_ok = pair_diag["suggested_route"] != "escalate_full_manual_review"
    verdict = "INTEGRATION_CANDIDATE" if holdout_good and wfo_good and boot_good and pair_ok else "HOLD_RESEARCH_ONLY"

    lines = [
        f"# {candidate_id} Validation Report",
        "",
        "## Candidate",
        "",
        "- Reference: `X0_E5EXIT`",
        f"- Candidate: `{candidate_id}`",
        "",
        "## Verdict",
        "",
        f"- `{verdict}`",
        "",
        "## Full Period (harsh)",
        "",
        f"- reference: Sharpe={full_harsh_ref['sharpe']:.4f}, CAGR={full_harsh_ref['cagr_pct']:.2f}%, MDD={full_harsh_ref['mdd_pct']:.2f}%, Calmar={full_harsh_ref['calmar']:.4f}",
        f"- candidate: Sharpe={full_harsh_cand['sharpe']:.4f}, CAGR={full_harsh_cand['cagr_pct']:.2f}%, MDD={full_harsh_cand['mdd_pct']:.2f}%, Calmar={full_harsh_cand['calmar']:.4f}",
        "",
        "## Recent Holdout (2024-01-01 to 2026-02-20, harsh)",
        "",
        f"- pre-holdout delta: dSharpe={pre_harsh_cand['sharpe'] - pre_harsh_ref['sharpe']:+.4f}, dCAGR={pre_harsh_cand['cagr_pct'] - pre_harsh_ref['cagr_pct']:+.2f}pp, dMDD={pre_harsh_cand['mdd_pct'] - pre_harsh_ref['mdd_pct']:+.2f}pp",
        f"- holdout delta: dSharpe={holdout_harsh_cand['sharpe'] - holdout_harsh_ref['sharpe']:+.4f}, dCAGR={holdout_harsh_cand['cagr_pct'] - holdout_harsh_ref['cagr_pct']:+.2f}pp, dMDD={holdout_harsh_cand['mdd_pct'] - holdout_harsh_ref['mdd_pct']:+.2f}pp",
        "",
        "## Rolling OOS Windows (harsh)",
        "",
        f"- windows={wfo['windows']}",
        f"- Sharpe wins={wfo['candidate_sharpe_wins']}/{wfo['windows']}",
        f"- CAGR wins={wfo['candidate_cagr_wins']}/{wfo['windows']}",
        f"- MDD wins={wfo['candidate_mdd_wins']}/{wfo['windows']}",
        f"- Calmar wins={wfo['candidate_calmar_wins']}/{wfo['windows']}",
        "",
        "## Paired Bootstrap (full harsh actual engine equity)",
        "",
        f"- Sharpe: delta={boot_by_metric['sharpe']['observed_delta']:+.4f}, CI=[{boot_by_metric['sharpe']['ci_lower']:+.4f}, {boot_by_metric['sharpe']['ci_upper']:+.4f}], P(candidate better)={boot_by_metric['sharpe']['p_candidate_better']:.3f}",
        f"- CAGR: delta={boot_by_metric['cagr_pct']['observed_delta']:+.4f}, CI=[{boot_by_metric['cagr_pct']['ci_lower']:+.4f}, {boot_by_metric['cagr_pct']['ci_upper']:+.4f}], P(candidate better)={boot_by_metric['cagr_pct']['p_candidate_better']:.3f}",
        f"- -MDD: delta={boot_by_metric['neg_mdd']['observed_delta']:+.4f}, CI=[{boot_by_metric['neg_mdd']['ci_lower']:+.4f}, {boot_by_metric['neg_mdd']['ci_upper']:+.4f}], P(candidate better)={boot_by_metric['neg_mdd']['p_candidate_better']:.3f}",
        "",
        "## Pair Diagnostic",
        "",
        f"- class={pair_diag['classification']['pair_class']}",
        f"- boot_sharpe_p={pair_diag['boot_sharpe_p']:.3f}",
        f"- boot_geo_p={pair_diag['boot_geo_p']:.3f}",
        f"- sub_p={pair_diag['sub_p']:.3f}",
        f"- consensus_gap_pp={pair_diag['consensus_gap_pp']:.2f}",
        f"- route={pair_diag['suggested_route']}",
        "",
        "## Interpretation",
        "",
    ]
    if verdict == "INTEGRATION_CANDIDATE":
        lines.append("- Validation is supportive enough to formalize this as the next integration candidate.")
    else:
        lines.append("- Validation is mixed. This candidate should remain research-only.")
    return "\n".join(lines) + "\n", verdict


def main() -> None:
    t0 = time.time()
    candidates = candidate_factories()

    full_rows, full_results = backtest_table(candidates)
    holdout_rows, holdout_results = holdout_table(candidates)
    wfo_rows, wfo_summary = run_wfo(candidates)

    bootstrap_payload: dict[str, list[dict]] = {}
    pair_payload: dict[str, dict] = {}
    pair_md_payload: dict[str, str] = {}
    candidate_verdicts: dict[str, str] = {}

    full_harsh_ref = full_results["reference"]["harsh"]
    for cid in candidates:
        full_harsh_cand = full_results[cid]["harsh"]
        bootstrap_rows = run_bootstrap_pair(full_harsh_cand.equity, full_harsh_ref.equity)
        bootstrap_payload[cid] = bootstrap_rows

        pair_diag = run_pair_diagnostic(
            equity_a=full_harsh_cand.equity,
            equity_b=full_harsh_ref.equity,
            label_a=cid,
            label_b="X0_E5EXIT",
            block_sizes=(10, 20, 40),
            n_bootstrap=2000,
            seed=1337,
        )
        pair_diag_dict = asdict(pair_diag)
        pair_payload[cid] = pair_diag_dict
        pair_md_payload[cid] = render_review_template(pair_diag)

        report, verdict = build_candidate_report(
            cid,
            full_rows,
            holdout_rows,
            wfo_summary,
            bootstrap_rows,
            pair_diag_dict,
        )
        candidate_verdicts[cid] = verdict
        (OUTDIR / f"P0_2_{cid}_VALIDATION_REPORT.md").write_text(report)

    passing = [cid for cid, verdict in candidate_verdicts.items() if verdict == "INTEGRATION_CANDIDATE"]
    if passing:
        full_harsh_rows = {
            cid: next(r for r in full_rows if r["strategy"] == "candidate" and r["candidate_id"] == cid and r["scenario"] == "harsh")
            for cid in passing
        }
        champion = max(passing, key=lambda cid: (full_harsh_rows[cid]["calmar"], full_harsh_rows[cid]["sharpe"]))
        branch_verdict = "INTEGRATION_CANDIDATE"
    else:
        champion = max(
            candidates,
            key=lambda cid: next(
                r for r in full_rows if r["strategy"] == "candidate" and r["candidate_id"] == cid and r["scenario"] == "harsh"
            )["calmar"],
        )
        branch_verdict = "HOLD_RESEARCH_ONLY"

    summary_lines = [
        "# P0.2 Exit-Floor Validation Report",
        "",
        "## Scope",
        "",
        "- Reference: `X0_E5EXIT`",
        "- Candidates: `X0E5_LL30`, `X0E5_FLOOR_LATCH`",
        "- Duplicate note: `X0E5_FLOOR_SM` was not validated because it matched `X0E5_LL30` on P0.1 benchmark outputs.",
        "",
        "## Candidate Verdicts",
        "",
    ]
    for cid, verdict in candidate_verdicts.items():
        summary_lines.append(f"- `{cid}`: `{verdict}`")
    summary_lines.extend([
        "",
        "## Branch Verdict",
        "",
        f"- `{branch_verdict}`",
        f"- Best candidate under current evidence: `{champion}`",
        "",
        "## Next Interpretation",
        "",
    ])
    if branch_verdict == "INTEGRATION_CANDIDATE":
        summary_lines.append("- The exit-floor family produced at least one candidate strong enough to move past research-only status.")
    else:
        summary_lines.append("- The exit-floor family is interesting but still not clean enough for unconditional promotion.")

    payload = {
        "settings": {
            "data": DATA,
            "start": START,
            "end": END,
            "warmup_days": WARMUP,
            "holdout_start": HOLDOUT_START,
            "wfo_train_months": WFO_TRAIN_MO,
            "wfo_test_months": WFO_TEST_MO,
            "wfo_step_months": WFO_STEP_MO,
            "pair_bootstrap_n": PAIR_BOOTSTRAP_N,
            "pair_bootstrap_block": PAIR_BOOTSTRAP_BLOCK,
        },
        "elapsed_seconds": round(time.time() - t0, 2),
        "candidate_verdicts": candidate_verdicts,
        "branch_verdict": branch_verdict,
        "champion_candidate": champion,
        "wfo_summary": wfo_summary,
        "bootstrap_rows": bootstrap_payload,
        "pair_diagnostics": pair_payload,
    }

    OUTDIR.mkdir(parents=True, exist_ok=True)
    with (OUTDIR / "p0_2_results.json").open("w") as f:
        json.dump(payload, f, indent=2)
    save_csv(
        OUTDIR / "p0_2_backtest_table.csv",
        full_rows,
        ["slice", "strategy", "candidate_id", "scenario", "sharpe", "cagr_pct", "mdd_pct", "calmar", "trades", "win_rate_pct", "profit_factor", "avg_exposure", "total_return_pct"],
    )
    save_csv(
        OUTDIR / "p0_2_holdout_table.csv",
        holdout_rows,
        ["slice", "strategy", "candidate_id", "scenario", "start", "end", "sharpe", "cagr_pct", "mdd_pct", "calmar", "trades", "win_rate_pct", "profit_factor", "avg_exposure", "total_return_pct"],
    )
    save_csv(
        OUTDIR / "p0_2_wfo_table.csv",
        wfo_rows,
        ["candidate_id", "window_id", "start", "end", "ref_sharpe", "cand_sharpe", "d_sharpe", "ref_cagr_pct", "cand_cagr_pct", "d_cagr_pct", "ref_mdd_pct", "cand_mdd_pct", "d_mdd_pct", "ref_calmar", "cand_calmar", "d_calmar", "ref_trades", "cand_trades", "d_trades"],
    )
    for cid, rows in bootstrap_payload.items():
        save_csv(
            OUTDIR / f"p0_2_bootstrap_{cid}.csv",
            rows,
            ["metric", "observed_candidate", "observed_reference", "observed_delta", "mean_delta", "ci_lower", "ci_upper", "p_candidate_better", "block_size", "n_bootstrap"],
        )
        (OUTDIR / f"p0_2_pair_diagnostic_{cid}.json").write_text(json.dumps(pair_payload[cid], indent=2))
        (OUTDIR / f"p0_2_pair_diagnostic_{cid}.md").write_text(pair_md_payload[cid])
    (OUTDIR / "P0_2_VALIDATION_REPORT.md").write_text("\n".join(summary_lines) + "\n")

    print(f"Saved P0.2 validation artifacts to {OUTDIR}")


if __name__ == "__main__":
    main()
