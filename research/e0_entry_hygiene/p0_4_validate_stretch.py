#!/usr/bin/env python3
"""P0.4 -- Full validation for X0E5_CHOP_STRETCH18."""

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

from research.e0_entry_hygiene.p0_1_entry_hygiene_benchmark import (
    EntryGateConfig,
    X0EntryHygieneStrategy,
)
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


def make_candidate():
    return X0EntryHygieneStrategy(
        EntryGateConfig(
            strategy_id="x0e5_chop_stretch18",
            use_robust_exit=True,
            chop_max_price_to_slow_atr=1.8,
        )
    )


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


def backtest_table() -> tuple[list[dict], dict]:
    rows: list[dict] = []
    results: dict[str, dict] = {"reference": {}, "candidate": {}}
    for scenario in ("smart", "base", "harsh"):
        ref_res = run_one(make_reference, START, END, scenario)
        cand_res = run_one(make_candidate, START, END, scenario)
        results["reference"][scenario] = ref_res
        results["candidate"][scenario] = cand_res
        for label, res in (("reference", ref_res), ("candidate", cand_res)):
            s = res.summary
            rows.append({
                "slice": "full",
                "strategy": label,
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


def holdout_table() -> tuple[list[dict], dict]:
    windows = [
        ("pre_holdout", START, PRE_HOLDOUT_END),
        ("holdout", HOLDOUT_START, END),
    ]
    rows: list[dict] = []
    results: dict[str, dict] = {}
    for slice_id, start, end in windows:
        results[slice_id] = {"reference": {}, "candidate": {}}
        for scenario in ("smart", "base", "harsh"):
            ref_res = run_one(make_reference, start, end, scenario)
            cand_res = run_one(make_candidate, start, end, scenario)
            results[slice_id]["reference"][scenario] = ref_res
            results[slice_id]["candidate"][scenario] = cand_res
            for label, res in (("reference", ref_res), ("candidate", cand_res)):
                s = res.summary
                rows.append({
                    "slice": slice_id,
                    "strategy": label,
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


def run_wfo() -> tuple[list[dict], dict]:
    windows = generate_wfo_windows(START, END)
    rows: list[dict] = []
    summary = {
        "windows": len(windows),
        "candidate_sharpe_wins": 0,
        "candidate_cagr_wins": 0,
        "candidate_mdd_wins": 0,
        "candidate_calmar_wins": 0,
    }
    for wid, start, end in windows:
        ref_res = run_one(make_reference, start, end, "harsh")
        cand_res = run_one(make_candidate, start, end, "harsh")
        r = ref_res.summary
        c = cand_res.summary
        if (c["sharpe"] or 0.0) > (r["sharpe"] or 0.0):
            summary["candidate_sharpe_wins"] += 1
        if (c["cagr_pct"] or 0.0) > (r["cagr_pct"] or 0.0):
            summary["candidate_cagr_wins"] += 1
        if (c["max_drawdown_mid_pct"] or 0.0) < (r["max_drawdown_mid_pct"] or 0.0):
            summary["candidate_mdd_wins"] += 1
        if (c["calmar"] or 0.0) > (r["calmar"] or 0.0):
            summary["candidate_calmar_wins"] += 1
        rows.append({
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


def build_report(full_rows, holdout_rows, wfo_rows, wfo_summary, bootstrap_rows, pair_diag) -> str:
    full_harsh = {r["strategy"]: r for r in full_rows if r["scenario"] == "harsh"}
    holdout_harsh = {r["strategy"]: r for r in holdout_rows if r["slice"] == "holdout" and r["scenario"] == "harsh"}
    pre_harsh = {r["strategy"]: r for r in holdout_rows if r["slice"] == "pre_holdout" and r["scenario"] == "harsh"}
    boot_by_metric = {r["metric"]: r for r in bootstrap_rows}

    holdout_good = (holdout_harsh["candidate"]["calmar"] or 0.0) >= (holdout_harsh["reference"]["calmar"] or 0.0)
    wfo_good = wfo_summary["candidate_calmar_wins"] >= math.ceil(wfo_summary["windows"] / 2)
    boot_good = boot_by_metric["sharpe"]["p_candidate_better"] > 0.55 and boot_by_metric["neg_mdd"]["p_candidate_better"] > 0.55
    pair_ok = pair_diag["suggested_route"] != "escalate_full_manual_review"
    verdict = "INTEGRATION_CANDIDATE" if holdout_good and wfo_good and boot_good and pair_ok else "HOLD_RESEARCH_ONLY"

    lines = [
        "# P0.4 Stretch Validation Report",
        "",
        "## Candidate",
        "",
        "- Reference: `X0_E5EXIT`",
        "- Candidate: `X0E5_CHOP_STRETCH18`",
        "",
        "## Verdict",
        "",
        f"- `{verdict}`",
        "",
        "## Full Period (harsh)",
        "",
        f"- reference: Sharpe={full_harsh['reference']['sharpe']:.4f}, CAGR={full_harsh['reference']['cagr_pct']:.2f}%, MDD={full_harsh['reference']['mdd_pct']:.2f}%, Calmar={full_harsh['reference']['calmar']:.4f}",
        f"- candidate: Sharpe={full_harsh['candidate']['sharpe']:.4f}, CAGR={full_harsh['candidate']['cagr_pct']:.2f}%, MDD={full_harsh['candidate']['mdd_pct']:.2f}%, Calmar={full_harsh['candidate']['calmar']:.4f}",
        "",
        "## Recent Holdout (2024-01-01 to 2026-02-20, harsh)",
        "",
        f"- pre-holdout delta: dSharpe={pre_harsh['candidate']['sharpe'] - pre_harsh['reference']['sharpe']:+.4f}, dCAGR={pre_harsh['candidate']['cagr_pct'] - pre_harsh['reference']['cagr_pct']:+.2f}pp, dMDD={pre_harsh['candidate']['mdd_pct'] - pre_harsh['reference']['mdd_pct']:+.2f}pp",
        f"- holdout delta: dSharpe={holdout_harsh['candidate']['sharpe'] - holdout_harsh['reference']['sharpe']:+.4f}, dCAGR={holdout_harsh['candidate']['cagr_pct'] - holdout_harsh['reference']['cagr_pct']:+.2f}pp, dMDD={holdout_harsh['candidate']['mdd_pct'] - holdout_harsh['reference']['mdd_pct']:+.2f}pp",
        "",
        "## Rolling OOS Windows (harsh)",
        "",
        f"- windows={wfo_summary['windows']}",
        f"- Sharpe wins={wfo_summary['candidate_sharpe_wins']}/{wfo_summary['windows']}",
        f"- CAGR wins={wfo_summary['candidate_cagr_wins']}/{wfo_summary['windows']}",
        f"- MDD wins={wfo_summary['candidate_mdd_wins']}/{wfo_summary['windows']}",
        f"- Calmar wins={wfo_summary['candidate_calmar_wins']}/{wfo_summary['windows']}",
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

    if holdout_good and wfo_good and boot_good:
        lines.append("- Validation is supportive. The candidate looks strong enough to formalize as the next repo candidate.")
    else:
        lines.append("- Validation is mixed. The candidate is interesting, but not yet strong enough for unconditional promotion.")

    lines.append("- Because this is post-selection validation, even a good result should be treated as `integration-candidate`, not as final champion proof.")
    return "\n".join(lines) + "\n"


def main() -> None:
    t0 = time.time()

    full_rows, full_results = backtest_table()
    holdout_rows, holdout_results = holdout_table()
    wfo_rows, wfo_summary = run_wfo()

    full_harsh_ref = full_results["reference"]["harsh"]
    full_harsh_cand = full_results["candidate"]["harsh"]
    bootstrap_rows = run_bootstrap_pair(full_harsh_cand.equity, full_harsh_ref.equity)

    pair_diag = run_pair_diagnostic(
        equity_a=full_harsh_cand.equity,
        equity_b=full_harsh_ref.equity,
        label_a="X0E5_CHOP_STRETCH18",
        label_b="X0_E5EXIT",
        block_sizes=(10, 20, 40),
        n_bootstrap=2000,
        seed=1337,
    )
    pair_diag_dict = asdict(pair_diag)
    pair_diag_md = render_review_template(pair_diag)

    report = build_report(
        full_rows,
        holdout_rows,
        wfo_rows,
        wfo_summary,
        bootstrap_rows,
        pair_diag_dict,
    )

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
        "wfo_summary": wfo_summary,
        "bootstrap_rows": bootstrap_rows,
        "pair_diagnostic": pair_diag_dict,
        "verdict": "INTEGRATION_CANDIDATE" if (
            (holdout_results["holdout"]["candidate"]["harsh"].summary.get("calmar") or 0.0)
            >= (holdout_results["holdout"]["reference"]["harsh"].summary.get("calmar") or 0.0)
            and wfo_summary["candidate_calmar_wins"] >= math.ceil(wfo_summary["windows"] / 2)
            and next(r for r in bootstrap_rows if r["metric"] == "sharpe")["p_candidate_better"] > 0.55
            and next(r for r in bootstrap_rows if r["metric"] == "neg_mdd")["p_candidate_better"] > 0.55
            and pair_diag_dict["suggested_route"] != "escalate_full_manual_review"
        ) else "HOLD_RESEARCH_ONLY",
    }

    OUTDIR.mkdir(parents=True, exist_ok=True)
    with (OUTDIR / "p0_4_results.json").open("w") as f:
        json.dump(payload, f, indent=2)
    save_csv(
        OUTDIR / "p0_4_backtest_table.csv",
        full_rows,
        ["slice", "strategy", "scenario", "sharpe", "cagr_pct", "mdd_pct", "calmar", "trades", "win_rate_pct", "profit_factor", "avg_exposure", "total_return_pct"],
    )
    save_csv(
        OUTDIR / "p0_4_holdout_table.csv",
        holdout_rows,
        ["slice", "strategy", "scenario", "start", "end", "sharpe", "cagr_pct", "mdd_pct", "calmar", "trades", "win_rate_pct", "profit_factor", "avg_exposure", "total_return_pct"],
    )
    save_csv(
        OUTDIR / "p0_4_wfo_table.csv",
        wfo_rows,
        ["window_id", "start", "end", "ref_sharpe", "cand_sharpe", "d_sharpe", "ref_cagr_pct", "cand_cagr_pct", "d_cagr_pct", "ref_mdd_pct", "cand_mdd_pct", "d_mdd_pct", "ref_calmar", "cand_calmar", "d_calmar", "ref_trades", "cand_trades", "d_trades"],
    )
    save_csv(
        OUTDIR / "p0_4_bootstrap_table.csv",
        bootstrap_rows,
        ["metric", "observed_candidate", "observed_reference", "observed_delta", "mean_delta", "ci_lower", "ci_upper", "p_candidate_better", "block_size", "n_bootstrap"],
    )
    (OUTDIR / "p0_4_pair_diagnostic.json").write_text(json.dumps(pair_diag_dict, indent=2))
    (OUTDIR / "p0_4_pair_diagnostic.md").write_text(pair_diag_md)
    (OUTDIR / "P0_4_VALIDATION_REPORT.md").write_text(report)

    print(f"Saved P0.4 validation artifacts to {OUTDIR}")


if __name__ == "__main__":
    main()
