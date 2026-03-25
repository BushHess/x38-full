"""Tests for v10.research.decision — gate evaluation logic."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import pytest

from v10.research.decision import evaluate, write_decision_json
from v10.core.meta import get_git_hash, fingerprint_file, stamp_run_meta


# ---------------------------------------------------------------------------
# Helpers — write synthetic fixtures to tmp_path
# ---------------------------------------------------------------------------

_SCENARIO_COLS = [
    "candidate", "scenario", "score", "cagr_pct", "max_drawdown_mid_pct",
    "sharpe", "sortino", "profit_factor", "win_rate_pct", "avg_trade_pnl",
    "fees_total", "trades", "turnover_per_year", "fee_drag_pct_per_year",
]


def _row(
    candidate: str = "baseline_legacy",
    scenario: str = "base",
    score: float = 80.0,
    cagr: float = 30.0,
    mdd: float = 25.0,
    trades: int = 50,
    turnover: float = 3.0,
    fee_drag: float = 1.5,
    **kw: Any,
) -> dict[str, Any]:
    """Build one scenario_table row with sensible defaults."""
    d = {
        "candidate": candidate,
        "scenario": scenario,
        "score": score,
        "cagr_pct": cagr,
        "max_drawdown_mid_pct": mdd,
        "sharpe": kw.get("sharpe", 1.2),
        "sortino": kw.get("sortino", 1.8),
        "profit_factor": kw.get("profit_factor", 2.0),
        "win_rate_pct": kw.get("win_rate_pct", 60.0),
        "avg_trade_pnl": kw.get("avg_trade_pnl", 100.0),
        "fees_total": kw.get("fees_total", 500.0),
        "trades": trades,
        "turnover_per_year": turnover,
        "fee_drag_pct_per_year": fee_drag,
    }
    return d


def _write_scenario_csv(tmp_path: Path, rows: list[dict]) -> None:
    with open(tmp_path / "scenario_table.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=_SCENARIO_COLS)
        writer.writeheader()
        writer.writerows(rows)


def _write_regime_json(
    tmp_path: Path,
    candidate: str,
    topping_ret: float = -10.0,
    shock_ret: float = -5.0,
) -> None:
    data = {
        "BULL": {"total_return_pct": 50.0, "max_dd_pct": 15.0, "n_bars": 1000, "n_days": 166.7, "sharpe": 1.5},
        "BEAR": {"total_return_pct": -5.0, "max_dd_pct": 20.0, "n_bars": 500, "n_days": 83.3, "sharpe": -0.5},
        "TOPPING": {"total_return_pct": topping_ret, "max_dd_pct": 12.0, "n_bars": 300, "n_days": 50.0, "sharpe": -0.3},
        "SHOCK": {"total_return_pct": shock_ret, "max_dd_pct": 8.0, "n_bars": 100, "n_days": 16.7, "sharpe": -1.0},
        "NEUTRAL": {"total_return_pct": 2.0, "max_dd_pct": 5.0, "n_bars": 200, "n_days": 33.3, "sharpe": 0.2},
        "CHOP": {"total_return_pct": -1.0, "max_dd_pct": 3.0, "n_bars": 50, "n_days": 8.3, "sharpe": -0.1},
    }
    with open(tmp_path / f"regime_returns_{candidate}.json", "w") as f:
        json.dump(data, f)


def _write_dd_csv(tmp_path: Path, candidate: str, n_episodes: int = 3) -> None:
    fieldnames = [
        "peak_date", "peak_nav", "trough_date", "trough_nav",
        "recovery_date", "drawdown_pct", "bars_to_trough",
        "bars_to_recovery", "days_to_trough", "days_to_recovery",
    ]
    with open(tmp_path / f"dd_episodes_{candidate}.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for i in range(n_episodes):
            writer.writerow({
                "peak_date": f"2022-0{i+1}-01T00:00:00Z",
                "peak_nav": 15000 - i * 1000,
                "trough_date": f"2022-0{i+1}-15T00:00:00Z",
                "trough_nav": 12000 - i * 1000,
                "recovery_date": f"2022-0{i+2}-01T00:00:00Z",
                "drawdown_pct": 20.0 + i * 5,
                "bars_to_trough": 90,
                "bars_to_recovery": 150,
                "days_to_trough": 14.0,
                "days_to_recovery": 30.0,
            })


def _baseline_rows(
    mdd_harsh: float = 30.0,
    score_harsh: float = 70.0,
    turnover_base: float = 3.0,
) -> list[dict]:
    """3 scenario rows for baseline_legacy."""
    return [
        _row("baseline_legacy", "smart", score=90.0, mdd=22.0, turnover=turnover_base),
        _row("baseline_legacy", "base", score=80.0, mdd=25.0, turnover=turnover_base),
        _row("baseline_legacy", "harsh", score=score_harsh, mdd=mdd_harsh, turnover=turnover_base),
    ]


def _setup_fixtures(
    tmp_path: Path,
    extra_rows: list[dict] | None = None,
    baseline_topping_ret: float = -10.0,
    baseline_mdd_harsh: float = 30.0,
    baseline_score_harsh: float = 70.0,
    baseline_turnover: float = 3.0,
) -> None:
    """Write baseline + optional extra candidate rows & regime/dd files."""
    rows = _baseline_rows(baseline_mdd_harsh, baseline_score_harsh, baseline_turnover)
    if extra_rows:
        rows.extend(extra_rows)

    _write_scenario_csv(tmp_path, rows)
    _write_regime_json(tmp_path, "baseline_legacy", topping_ret=baseline_topping_ret)
    _write_dd_csv(tmp_path, "baseline_legacy")

    # Write regime/dd for extra candidates
    if extra_rows:
        extra_names = sorted({r["candidate"] for r in extra_rows})
        for name in extra_names:
            if not (tmp_path / f"regime_returns_{name}.json").exists():
                _write_regime_json(tmp_path, name)
            if not (tmp_path / f"dd_episodes_{name}.csv").exists():
                _write_dd_csv(tmp_path, name)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestDecision:
    def test_reject_few_trades(self, tmp_path: Path) -> None:
        """Candidate with trades < 10 in any scenario -> REJECT."""
        cand_rows = [
            _row("new_cand", "smart", trades=8, score=90.0),
            _row("new_cand", "base", trades=40, score=85.0),
            _row("new_cand", "harsh", trades=40, score=75.0),
        ]
        _setup_fixtures(tmp_path, extra_rows=cand_rows)

        result = evaluate(tmp_path, baseline_name="baseline_legacy")

        cand_gate = next(g for g in result.gates if g.name == "new_cand")
        assert cand_gate.tag == "REJECT"
        assert any("trades" in r and "< 10" in r for r in cand_gate.reasons)
        assert result.selected == "baseline_legacy"

    def test_reject_harsh_mdd_exceeds_baseline(self, tmp_path: Path) -> None:
        """Candidate harsh MDD > baseline harsh MDD + 5 -> REJECT."""
        cand_rows = [
            _row("new_cand", "smart", mdd=25.0, score=90.0),
            _row("new_cand", "base", mdd=28.0, score=85.0),
            _row("new_cand", "harsh", mdd=36.0, score=75.0),  # baseline harsh=30, 36 > 35
        ]
        _setup_fixtures(tmp_path, extra_rows=cand_rows, baseline_mdd_harsh=30.0)

        result = evaluate(tmp_path, baseline_name="baseline_legacy")

        cand_gate = next(g for g in result.gates if g.name == "new_cand")
        assert cand_gate.tag == "REJECT"
        assert any("MDD" in r for r in cand_gate.reasons)
        assert result.selected == "baseline_legacy"

    def test_promote_meets_all_criteria(self, tmp_path: Path) -> None:
        """Candidate with harsh score >= baseline, TOPPING >= baseline,
        turnover <= 1.2x baseline -> PROMOTE and selected."""
        cand_rows = [
            _row("better_cand", "smart", score=95.0, mdd=20.0, turnover=3.0),
            _row("better_cand", "base", score=85.0, mdd=24.0, turnover=3.0),
            _row("better_cand", "harsh", score=75.0, mdd=29.0, turnover=3.0),
        ]
        _setup_fixtures(
            tmp_path,
            extra_rows=cand_rows,
            baseline_score_harsh=70.0,
            baseline_topping_ret=-10.0,
            baseline_turnover=3.0,
        )
        # better_cand TOPPING return must be >= baseline (-10.0)
        _write_regime_json(tmp_path, "better_cand", topping_ret=-8.0)

        result = evaluate(tmp_path, baseline_name="baseline_legacy")

        cand_gate = next(g for g in result.gates if g.name == "better_cand")
        assert cand_gate.tag == "PROMOTE"
        assert result.selected == "better_cand"

    def test_hold_when_not_promoted(self, tmp_path: Path) -> None:
        """Candidate passes reject gates but fails PROMOTE
        (worse TOPPING) -> HOLD, baseline selected."""
        cand_rows = [
            _row("mediocre", "smart", score=92.0, mdd=22.0, turnover=3.0),
            _row("mediocre", "base", score=82.0, mdd=26.0, turnover=3.0),
            _row("mediocre", "harsh", score=72.0, mdd=32.0, turnover=3.0),
        ]
        _setup_fixtures(
            tmp_path,
            extra_rows=cand_rows,
            baseline_score_harsh=70.0,
            baseline_topping_ret=-10.0,
            baseline_mdd_harsh=30.0,
        )
        # mediocre has WORSE topping return than baseline
        _write_regime_json(tmp_path, "mediocre", topping_ret=-15.0)

        result = evaluate(tmp_path, baseline_name="baseline_legacy")

        cand_gate = next(g for g in result.gates if g.name == "mediocre")
        assert cand_gate.tag == "HOLD"
        assert any("TOPPING" in r for r in cand_gate.reasons)
        assert result.selected == "baseline_legacy"

    def test_decision_json_has_required_fields(self, tmp_path: Path) -> None:
        """Verify decision.json structure: selected_candidate, metadata, candidates."""
        _setup_fixtures(tmp_path)
        result = evaluate(tmp_path, baseline_name="baseline_legacy")
        write_decision_json(result, tmp_path)

        with open(tmp_path / "decision.json") as f:
            data = json.load(f)

        assert "selected_candidate" in data
        assert data["selected_candidate"] == "baseline_legacy"

        assert "metadata" in data
        assert "timestamp" in data["metadata"]
        assert "scenarios" in data["metadata"]
        assert isinstance(data["metadata"]["scenarios"], list)

        assert "candidates" in data
        assert len(data["candidates"]) >= 1
        cand = data["candidates"][0]
        assert "name" in cand
        assert "tag" in cand
        assert cand["tag"] in ("PROMOTE", "HOLD", "REJECT")
        assert "reasons" in cand
        assert "worst" in cand

    def test_decision_json_git_hash_not_null(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """decision.json must have a non-null git_hash (mocked)."""
        monkeypatch.setattr("v10.research.decision.get_git_hash", lambda: "abc1234")

        _setup_fixtures(tmp_path)
        result = evaluate(tmp_path, baseline_name="baseline_legacy")
        write_decision_json(result, tmp_path)

        with open(tmp_path / "decision.json") as f:
            data = json.load(f)

        assert data["metadata"]["git_hash"] == "abc1234"
        assert data["metadata"]["git_hash"] is not None


class TestMeta:
    def test_get_git_hash_returns_string(self) -> None:
        h = get_git_hash()
        assert isinstance(h, str)
        assert len(h) > 0

    def test_fingerprint_file(self, tmp_path: Path) -> None:
        p = tmp_path / "test.txt"
        p.write_text("hello world")
        fp = fingerprint_file(p)
        assert isinstance(fp, str)
        assert len(fp) == 64  # SHA-256 hex

    def test_fingerprint_deterministic(self, tmp_path: Path) -> None:
        p = tmp_path / "test.txt"
        p.write_text("same content")
        assert fingerprint_file(p) == fingerprint_file(p)

    def test_stamp_run_meta(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("v10.core.meta.get_git_hash", lambda: "deadbeef")
        data_file = tmp_path / "data.csv"
        data_file.write_text("a,b\n1,2\n")

        path = stamp_run_meta(
            tmp_path,
            argv=["test", "--foo"],
            config={"key": "value"},
            data_path=data_file,
        )
        assert path.exists()

        with open(path) as f:
            meta = json.load(f)

        assert meta["git_hash"] == "deadbeef"
        assert "timestamp_utc" in meta
        assert meta["timestamp_utc"].endswith("Z")
        assert meta["argv"] == ["test", "--foo"]
        assert meta["config"] == {"key": "value"}
        assert meta["data_fingerprint"] is not None
        assert len(meta["data_fingerprint"]) == 64
