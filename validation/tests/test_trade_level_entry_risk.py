from __future__ import annotations

from validation.report import _append_trade_level
from validation.suites.base import SuiteResult
from validation.suites.trade_level import _build_trade_level_analysis_report
from validation.suites.trade_level import _entry_risk_summary_rows
from validation.suites.trade_level import _parse_entry_risk


def test_parse_entry_risk_extracts_suffix_and_defaults_untagged() -> None:
    assert _parse_entry_risk("x0_entry|risk=high_chop_stretch") == "high_chop_stretch"
    assert _parse_entry_risk("x0_entry") == "untagged"
    assert _parse_entry_risk("") == "untagged"


def test_entry_risk_summary_rows_aggregates_by_label_and_risk() -> None:
    rows = [
        {"label": "candidate", "entry_risk_level": "low_non_chop", "pnl_usd": 10.0},
        {"label": "candidate", "entry_risk_level": "low_non_chop", "pnl_usd": -5.0},
        {"label": "candidate", "entry_risk_level": "high_chop_stretch", "pnl_usd": -7.0},
        {"label": "baseline", "entry_risk_level": "untagged", "pnl_usd": 3.0},
    ]

    summary = _entry_risk_summary_rows(rows)

    assert summary == [
        {
            "label": "baseline",
            "entry_risk_level": "untagged",
            "n_trades": 1,
            "share_trades": 1.0,
            "total_pnl": 3.0,
            "avg_pnl": 3.0,
            "win_rate": 1.0,
            "loss_rate": 0.0,
        },
        {
            "label": "candidate",
            "entry_risk_level": "low_non_chop",
            "n_trades": 2,
            "share_trades": 0.666667,
            "total_pnl": 5.0,
            "avg_pnl": 2.5,
            "win_rate": 0.5,
            "loss_rate": 0.5,
        },
        {
            "label": "candidate",
            "entry_risk_level": "high_chop_stretch",
            "n_trades": 1,
            "share_trades": 0.333333,
            "total_pnl": -7.0,
            "avg_pnl": -7.0,
            "win_rate": 0.0,
            "loss_rate": 1.0,
        },
    ]


def test_trade_level_analysis_report_includes_entry_risk_section_when_tagged() -> None:
    report = _build_trade_level_analysis_report(
        scenario="harsh",
        matched_rows=[],
        candidate_only=[],
        baseline_only=[],
        entry_risk_rows=[
            {
                "label": "candidate",
                "entry_risk_level": "high_chop_stretch",
                "n_trades": 3,
                "share_trades": 0.2,
                "avg_pnl": -1.5,
                "total_pnl": -4.5,
                "win_rate": 0.0,
                "loss_rate": 1.0,
            }
        ],
    )

    assert "## Entry risk cohorts" in report
    assert "| candidate | high_chop_stretch | 3 | 0.200000 | -1.500000 | -4.500000 | 0.000000 | 1.000000 |" in report


def test_validation_report_trade_level_appends_entry_risk_lines() -> None:
    lines: list[str] = []
    result = SuiteResult(
        name="trade_level",
        status="info",
        data={
            "candidate_trades": 10,
            "baseline_trades": 9,
            "matched_trades": 8,
            "candidate_only_trades": 2,
            "baseline_only_trades": 1,
            "matched_delta_pnl_mean": 1.23,
            "entry_risk_summary": [
                {
                    "label": "candidate",
                    "entry_risk_level": "high_chop_stretch",
                    "n_trades": 2,
                    "share_trades": 0.1,
                    "avg_pnl": -3.0,
                    "win_rate": 0.0,
                }
            ],
        },
    )

    _append_trade_level(lines, result)

    joined = "\n".join(lines)
    assert "Entry risk cohorts:" in joined
    assert "candidate:high_chop_stretch trades=2 share=0.1 avg_pnl=-3.0 win_rate=0.0" in joined
