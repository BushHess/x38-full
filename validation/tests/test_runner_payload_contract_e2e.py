"""E2E runner tests for payload contract robustness (Report 30).

Exercises the real run() loop with malformed authoritative payloads
to prove the final verdict on disk is correct.

Reuses the stubbed harness pattern from test_runner_run_loop_e2e.py.

Test IDs (Report 30):
  PC1: test_authoritative_suite_malformed_payload_error_on_disk
  PC2: test_zero_authority_malformed_payload_no_veto
  PC3: test_wfo_empty_summary_auto_enables_trade_level_on_real_path
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

import validation.runner as _rm
from validation.config import ValidationConfig
from validation.runner import ValidationRunner
from validation.suites.base import SuiteResult


# ── Module-level fake-suite state ─────────────────────────────────────

_suite_payloads: dict[str, SuiteResult | Exception] = {}
_suite_run_order: list[str] = []
_skip_output_write: set[str] = set()

_SUITE_ARTIFACTS: dict[str, list[str]] = {
    "backtest": [
        "results/full_backtest_summary.csv",
        "results/score_breakdown_full.csv",
        "results/add_throttle_stats.json",
    ],
    "wfo": [
        "results/wfo_per_round_metrics.csv",
        "results/wfo_summary.json",
        "reports/audit_wfo_invalid_windows.md",
    ],
    "trade_level": [
        "results/trades_candidate.csv",
        "results/trades_baseline.csv",
        "results/matched_trades.csv",
        "results/regime_trade_summary.csv",
        "results/window_trade_counts.csv",
        "results/bootstrap_return_diff.json",
        "reports/trade_level_analysis.md",
    ],
    "data_integrity": [
        "results/data_integrity.json",
        "results/data_integrity_issues.csv",
    ],
    "cost_sweep": ["results/cost_sweep.csv"],
    "invariants": ["results/invariant_violations.csv"],
    "holdout": [
        "results/final_holdout_metrics.csv",
        "results/score_breakdown_holdout.csv",
    ],
    "churn_metrics": ["results/churn_metrics.csv"],
    "lookahead": ["results/lookahead_check.txt"],
    "selection_bias": ["results/selection_bias.json"],
    "regression_guard": ["results/regression_guard.json"],
}


def _run_fake_suite(name: str, ctx) -> SuiteResult:
    _suite_run_order.append(name)
    payload = _suite_payloads.get(name)
    if isinstance(payload, Exception):
        raise payload
    result = payload if payload is not None else SuiteResult(
        name=name, status="pass", data={},
    )
    if name not in _skip_output_write and result.status not in ("skip", "error"):
        for rel in _SUITE_ARTIFACTS.get(name, []):
            p = ctx.outdir / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            if not p.exists():
                p.write_text("")
    return result


def _make_fake_suite_cls(suite_name: str):
    class FakeSuite:
        def name(self):
            return suite_name

        def run(self, ctx):
            return _run_fake_suite(suite_name, ctx)

        def skip_reason(self, ctx):
            return None

    FakeSuite.__name__ = f"Fake_{suite_name}"
    FakeSuite.__qualname__ = f"Fake_{suite_name}"
    return FakeSuite


class _Stub:
    def __getattr__(self, name):
        return _Stub()

    def __call__(self, *a, **kw):
        return _Stub()

    def __iter__(self):
        return iter([])

    def __bool__(self):
        return False

    def __str__(self):
        return "stub"

    def __int__(self):
        return 0


# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _reset_state():
    _suite_payloads.clear()
    _suite_run_order.clear()
    _skip_output_write.clear()
    yield


@pytest.fixture
def harness(tmp_path, monkeypatch):
    config_path = tmp_path / "candidate.yaml"
    config_path.write_text("")
    baseline_path = tmp_path / "baseline.yaml"
    baseline_path.write_text("")

    cfg = ValidationConfig(
        strategy_name="fake",
        baseline_name="fake",
        config_path=config_path,
        baseline_config_path=baseline_path,
        outdir=tmp_path / "out",
        dataset=tmp_path / "data.csv",
        suite="basic",
        bootstrap=0,
        subsampling=False,
        sensitivity_grid=False,
        selection_bias="none",
        lookahead_check=False,
        trade_level=False,
        dd_episodes=False,
        data_integrity_check=False,
        cost_sweep_bps=[],
        invariant_check=False,
        regression_guard=False,
        churn_metrics=False,
    )

    stub = _Stub()

    # load_config must return an object whose strategy.name matches the
    # CLI label so the label guard passes.
    _fake_live = SimpleNamespace(
        strategy=SimpleNamespace(name="fake", params={}),
        engine=stub,
        risk=stub,
    )
    monkeypatch.setattr(_rm, "get_git_hash", lambda: "test-hash")
    monkeypatch.setattr(_rm, "stamp_run_meta", lambda *a, **kw: None)
    monkeypatch.setattr(_rm, "DataFeed", lambda *a, **kw: stub)
    monkeypatch.setattr(_rm, "load_config", lambda path: _fake_live)
    monkeypatch.setattr(_rm, "_build_config_obj", lambda name, params: stub)
    monkeypatch.setattr(_rm, "tracker_for_config_obj", lambda obj, label="": stub)
    monkeypatch.setattr(_rm, "make_factory", lambda live, access_tracker=None: lambda: None)
    monkeypatch.setattr(_rm, "load_raw_yaml", lambda path: {})
    monkeypatch.setattr(_rm, "build_effective_config_payload", lambda **kw: {})
    monkeypatch.setattr(_rm, "build_effective_config_report", lambda **kw: "")
    monkeypatch.setattr(_rm, "build_score_decomposition_report", lambda **kw: "")
    monkeypatch.setattr(_rm, "discover_checks", lambda *a, **kw: {})

    _usage = {"used": {}, "unused": {}, "has_unused": False}
    monkeypatch.setattr(
        _rm,
        "build_usage_payloads",
        lambda **kw: (_usage["used"], _usage["unused"], _usage["has_unused"]),
    )

    def _gen_report(results, decision, cfg, outdir, **kw):
        (outdir / "reports" / "validation_report.md").write_text("")

    def _gen_quality(results, cfg, outdir, **kw):
        (outdir / "reports" / "quality_checks.md").write_text("")

    def _write_disc(discovered, path, **kw):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("")

    monkeypatch.setattr(_rm, "generate_validation_report", _gen_report)
    monkeypatch.setattr(_rm, "generate_quality_checks_report", _gen_quality)
    monkeypatch.setattr(_rm, "write_discovered_tests_report", _write_disc)

    orig_classes = dict(_rm._SUITE_CLASSES)

    def _fake_import(dotted_path):
        for name, path in orig_classes.items():
            if path == dotted_path:
                return _make_fake_suite_cls(name)
        raise ImportError(f"No fake suite for {dotted_path}")

    monkeypatch.setattr(_rm, "_import_suite", _fake_import)

    runner = ValidationRunner(cfg)

    def set_queue(queue: list[str]):
        monkeypatch.setattr(_rm, "resolve_suites", lambda c: list(queue))

    def set_usage(*, has_unused: bool = False, unused_payload: dict | None = None):
        _usage["has_unused"] = has_unused
        _usage["unused"] = unused_payload or {}

    return SimpleNamespace(
        runner=runner,
        cfg=cfg,
        outdir=tmp_path / "out",
        set_queue=set_queue,
        set_usage=set_usage,
    )


# ── Tests ─────────────────────────────────────────────────────────────


class TestPayloadContractE2E:
    def test_authoritative_suite_malformed_payload_error_on_disk(self, harness) -> None:
        """PC1: Backtest returns malformed delta (missing) → ERROR(3) on disk.

        Proves that the contract-breach early exit in evaluate_decision flows
        through the real run() path all the way to decision.json on disk.
        """
        harness.set_queue(["backtest"])
        # Backtest runs but produces empty data (missing score_delta)
        _suite_payloads["backtest"] = SuiteResult(
            name="backtest", status="pass", data={},
        )

        _results, decision = harness.runner.run()

        # Verify on-disk decision.json
        dj = json.loads(
            (harness.outdir / "reports" / "decision.json").read_text()
        )
        assert dj["verdict"] == "ERROR"
        assert dj["exit_code"] == 3
        assert "backtest_payload_contract_breach" in dj["failures"]

        # Verify in-memory verdict matches
        assert decision.tag == "ERROR"
        assert decision.exit_code == 3
        assert "backtest_payload_contract_breach" in decision.failures

    def test_zero_authority_malformed_payload_no_veto(self, harness) -> None:
        """PC2: cost_sweep with malformed data → PROMOTE(0) preserved.

        Zero-authority suites cannot veto even with broken payloads,
        unless they crash (status='error').
        """
        harness.set_queue(["backtest", "cost_sweep"])
        # Backtest: valid passing result
        _suite_payloads["backtest"] = SuiteResult(
            name="backtest",
            status="pass",
            data={"deltas": {"harsh": {"score_delta": 5.0}}},
        )
        # cost_sweep: malformed payload (status=fail with garbage data)
        _suite_payloads["cost_sweep"] = SuiteResult(
            name="cost_sweep",
            status="fail",
            data={"issues": [None, float("nan"), {"broken": True}]},
        )

        _results, decision = harness.runner.run()

        assert decision.tag == "PROMOTE"
        assert decision.exit_code == 0
        # cost_sweep issues should be warnings only
        assert any("cost_sweep" in w.lower() for w in decision.warnings)

    def test_wfo_empty_summary_auto_enables_trade_level_on_real_path(
        self, harness,
    ) -> None:
        """PC3: WFO with empty summary → low_power → auto-enables trade_level.

        Proves that empty WFO payload triggers the auto-enable mechanism
        on the real run() path, and the final verdict reflects the fallback.
        """
        harness.set_queue(["backtest", "wfo"])
        # Backtest: valid passing result
        _suite_payloads["backtest"] = SuiteResult(
            name="backtest",
            status="pass",
            data={"deltas": {"harsh": {"score_delta": 5.0}}},
        )
        # WFO: empty summary (triggers low_power = True since all zeros)
        _suite_payloads["wfo"] = SuiteResult(
            name="wfo",
            status="pass",
            data={"summary": {}},
        )
        # trade_level will be auto-queued; provide an empty payload
        _suite_payloads["trade_level"] = SuiteResult(
            name="trade_level",
            status="info",
            data={},
        )

        _results, decision = harness.runner.run()

        # trade_level should have been auto-enabled and run
        assert "trade_level" in _suite_run_order
        assert harness.cfg.auto_trade_level is True

        # Final verdict: HOLD (missing bootstrap under low-power)
        assert decision.tag == "HOLD"
        assert "wfo_low_power_missing_trade_level_bootstrap" in decision.failures
