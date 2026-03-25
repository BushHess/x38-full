"""E2E orchestration tests for ValidationRunner.run() (Report 29).

Uses a minimal stubbed harness that exercises the REAL run() loop with
fake suite classes and stubbed heavy dependencies (DataFeed, load_config,
strategy factories).  Proves orchestration behaviors on the actual code path.

Harness design:
- _import_suite monkeypatched → returns FakeSuite classes
- FakeSuites return preset SuiteResult objects and record execution order
- Heavy I/O (DataFeed, load_config, make_factory) is stubbed
- Report generators write empty placeholder files (so output contract passes)
- evaluate_decision, write_decision_json, _verify_output_contract remain REAL

Test IDs (Report 29):
  WFO1: test_wfo_low_power_auto_enables_trade_level
  WFO2: test_wfo_normal_power_no_auto_enable
  WFO3: test_no_duplicate_when_trade_level_already_queued
  SC1:  test_data_integrity_hard_fail_aborts_remaining_suites
  SC2:  test_suite_exception_becomes_error_result
  SC3:  test_clean_run_all_suites_complete
  OC1:  test_output_contract_failure_produces_error_and_overwrites
  ZA1:  test_advisory_suite_fail_does_not_veto
  ZA2:  test_churn_fail_does_not_veto
  PD1:  test_quality_policy_elevates_on_real_run_path
  PD2:  test_config_usage_policy_elevates_on_real_run_path
  PD3:  test_decision_json_matches_returned_verdict
  PD4:  test_both_policies_cumulate_on_real_path
  PD5:  test_reject_not_downgraded_on_real_path
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

# Files each suite is expected to write (mirrors _verify_output_contract checks)
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
    "regime": ["results/regime_decomposition.csv"],
    "holdout": [
        "results/final_holdout_metrics.csv",
        "results/score_breakdown_holdout.csv",
    ],
    "bootstrap": ["results/bootstrap_paired_test.csv"],
    "churn_metrics": ["results/churn_metrics.csv"],
    "lookahead": ["results/lookahead_check.txt"],
    "selection_bias": ["results/selection_bias.json"],
    "regression_guard": ["results/regression_guard.json"],
    "subsampling": ["results/subsampling_paired_test.csv"],
    "sensitivity": ["results/sensitivity_grid.csv"],
}


def _run_fake_suite(name: str, ctx) -> SuiteResult:
    """Execute a fake suite: record order, optionally raise, return preset result."""
    _suite_run_order.append(name)
    payload = _suite_payloads.get(name)
    if isinstance(payload, Exception):
        raise payload
    result = payload if payload is not None else SuiteResult(
        name=name, status="pass", data={},
    )
    # Write placeholder output files so output contract passes (unless opted out)
    if name not in _skip_output_write and result.status not in ("skip", "error"):
        for rel in _SUITE_ARTIFACTS.get(name, []):
            p = ctx.outdir / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            if not p.exists():
                p.write_text("")
    return result


def _make_fake_suite_cls(suite_name: str):
    """Create a fake suite class that delegates to _run_fake_suite."""
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


# ── Recursive attribute stub for heavy dependencies ───────────────────

class _Stub:
    """Returns itself for any attribute/call — safe for duck-typed dependencies."""

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
    """Clear fake suite state before each test."""
    _suite_payloads.clear()
    _suite_run_order.clear()
    _skip_output_write.clear()
    yield


@pytest.fixture
def harness(tmp_path, monkeypatch):
    """Build a stubbed ValidationRunner that exercises the real run() loop.

    Stubs: DataFeed, load_config, make_factory, report generators, etc.
    Real:  suite loop, evaluate_decision, quality/config/output-contract policies,
           write_decision_json, write_index.
    """
    # Create fake config YAML files (needed by copy_configs)
    config_path = tmp_path / "candidate.yaml"
    config_path.write_text("")
    baseline_path = tmp_path / "baseline.yaml"
    baseline_path.write_text("")

    # Minimal config: all optional suite toggles disabled
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

    # ── Stub heavy dependencies ──
    # load_config must return an object whose strategy.name matches the
    # CLI label so the label guard (Fix 3) passes.
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

    # ── Controllable usage payload (for config_usage_policy tests) ──
    _usage = {"used": {}, "unused": {}, "has_unused": False}
    monkeypatch.setattr(
        _rm,
        "build_usage_payloads",
        lambda **kw: (_usage["used"], _usage["unused"], _usage["has_unused"]),
    )

    # ── Report generators: write empty files so output contract passes ──
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

    # ── Monkeypatch _import_suite → return fake suite classes ──
    orig_classes = dict(_rm._SUITE_CLASSES)

    def _fake_import(dotted_path):
        for name, path in orig_classes.items():
            if path == dotted_path:
                return _make_fake_suite_cls(name)
        raise ImportError(f"No fake suite for {dotted_path}")

    monkeypatch.setattr(_rm, "_import_suite", _fake_import)

    runner = ValidationRunner(cfg)

    # ── Per-test control helpers ──
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


# ── Helpers for common WFO payloads ──────────────────────────────────


def _wfo_low_power_payload() -> SuiteResult:
    """WFO result that triggers wfo_low_power=True (power=1, ratio=1.0)."""
    return SuiteResult(
        name="wfo",
        status="pass",
        data={
            "summary": {
                "n_windows": 2,
                "n_windows_valid": 2,
                "positive_delta_windows": 0,
                "win_rate": 0.0,
                "low_trade_windows_count": 2,
                "stats_power_only": {"n_windows": 1},
            },
        },
    )


def _wfo_normal_payload() -> SuiteResult:
    """WFO result with normal power, passing threshold."""
    return SuiteResult(
        name="wfo",
        status="pass",
        data={
            "summary": {
                "n_windows": 10,
                "n_windows_valid": 10,
                "positive_delta_windows": 8,
                "win_rate": 0.80,
                "low_trade_windows_count": 0,
                "stats_power_only": {"n_windows": 10},
            },
        },
    )


def _trade_level_healthy_payload() -> SuiteResult:
    """Trade-level result with healthy bootstrap CI (no zero crossing)."""
    return SuiteResult(
        name="trade_level",
        status="info",
        data={
            "trade_level_bootstrap": {
                "ci95_low": 0.001,
                "ci95_high": 0.005,
                "mean_diff": 0.003,
                "p_gt_0": 0.95,
                "block_len": 10,
            },
        },
    )


# ── WFO Auto-Enable Tests ────────────────────────────────────────────


class TestWFOAutoEnable:
    def test_wfo_low_power_auto_enables_trade_level(self, harness) -> None:
        """WFO1: Low-power WFO appends trade_level, sets auto_trade_level=True,
        and trade_level actually runs later in the same run() call."""
        harness.set_queue(["wfo"])
        _suite_payloads["wfo"] = _wfo_low_power_payload()
        _suite_payloads["trade_level"] = _trade_level_healthy_payload()

        results, verdict = harness.runner.run()

        # trade_level was auto-appended and ran after wfo
        assert _suite_run_order == ["wfo", "trade_level"]
        assert harness.cfg.auto_trade_level is True
        assert "trade_level" in results
        assert results["trade_level"].status == "info"
        # Healthy bootstrap → PROMOTE
        assert verdict.tag == "PROMOTE"
        assert verdict.exit_code == 0

    def test_wfo_normal_power_no_auto_enable(self, harness) -> None:
        """WFO2: Normal-power WFO does NOT append trade_level."""
        harness.set_queue(["wfo"])
        _suite_payloads["wfo"] = _wfo_normal_payload()

        results, verdict = harness.runner.run()

        assert _suite_run_order == ["wfo"]
        assert harness.cfg.auto_trade_level is False
        assert "trade_level" not in results
        assert verdict.tag == "PROMOTE"

    def test_no_duplicate_when_trade_level_already_queued(self, harness) -> None:
        """WFO3: trade_level already in queue → no duplicate enqueue.

        Runner checks 'trade_level not in suite_queue'; since it IS in queue,
        the auto-enable branch is skipped entirely.
        """
        harness.set_queue(["wfo", "trade_level"])
        _suite_payloads["wfo"] = _wfo_low_power_payload()
        _suite_payloads["trade_level"] = _trade_level_healthy_payload()

        results, verdict = harness.runner.run()

        # trade_level runs exactly once
        assert _suite_run_order == ["wfo", "trade_level"]
        assert _suite_run_order.count("trade_level") == 1
        # auto_trade_level NOT set (condition short-circuited on queue check)
        assert harness.cfg.auto_trade_level is False


# ── Short-Circuit / Early Abort Tests ─────────────────────────────────


class TestShortCircuit:
    def test_data_integrity_hard_fail_aborts_remaining_suites(self, harness) -> None:
        """SC1: data_integrity hard_fail=True → break loop; later suites do NOT run."""
        harness.set_queue(["data_integrity", "wfo"])
        _suite_payloads["data_integrity"] = SuiteResult(
            name="data_integrity",
            status="fail",
            data={"hard_fail": True, "hard_fail_reasons": ["test_abort"]},
        )
        _suite_payloads["wfo"] = _wfo_normal_payload()

        results, verdict = harness.runner.run()

        # Only data_integrity ran; wfo was aborted
        assert _suite_run_order == ["data_integrity"]
        assert "wfo" not in results
        assert verdict.tag == "ERROR"
        assert verdict.exit_code == 3

    def test_suite_exception_becomes_error_result(self, harness) -> None:
        """SC2: Suite crash (exception) → status='error' in results, final ERROR(3)."""
        harness.set_queue(["cost_sweep"])
        _suite_payloads["cost_sweep"] = RuntimeError("engine crash")

        results, verdict = harness.runner.run()

        assert "cost_sweep" in results
        assert results["cost_sweep"].status == "error"
        assert "engine crash" in (results["cost_sweep"].error_message or "")
        assert verdict.tag == "ERROR"
        assert verdict.exit_code == 3

    def test_clean_run_all_suites_complete(self, harness) -> None:
        """SC3: All suites pass → all run in order, PROMOTE(0)."""
        harness.set_queue(["wfo"])
        _suite_payloads["wfo"] = _wfo_normal_payload()

        results, verdict = harness.runner.run()

        assert _suite_run_order == ["wfo"]
        assert results["wfo"].status == "pass"
        assert verdict.tag == "PROMOTE"
        assert verdict.exit_code == 0


# ── Output Contract Tests ─────────────────────────────────────────────


class TestOutputContract:
    def test_output_contract_failure_produces_error_and_overwrites(
        self, harness
    ) -> None:
        """OC1: Missing suite output files → ERROR(3), decision.json overwritten.

        Proves double-write behavior:
        - First write at line 345: PROMOTE with gates (backtest harsh gate passed)
        - Second write at line 362: ERROR with empty gates (contract created new verdict)
        - Final JSON on disk has ERROR, gates=[], proving overwrite occurred
        - Gates are INTENTIONALLY lost: pipeline is incomplete when contract fails
        """
        harness.set_queue(["backtest"])
        _suite_payloads["backtest"] = SuiteResult(
            name="backtest",
            status="pass",
            data={"deltas": {"harsh": {"score_delta": 0.5}}},
        )
        _skip_output_write.add("backtest")  # Don't write output files → contract fails

        results, verdict = harness.runner.run()

        # In-memory verdict is ERROR from contract failure
        assert verdict.tag == "ERROR"
        assert verdict.exit_code == 3
        assert any("missing:" in f for f in verdict.failures)

        # Gates are lost (new verdict object created without gates)
        assert verdict.gates == []

        # Verify decision.json on disk matches
        decision_path = harness.outdir / "reports" / "decision.json"
        assert decision_path.exists()
        payload = json.loads(decision_path.read_text())
        assert payload["verdict"] == "ERROR"
        assert payload["exit_code"] == 3
        assert payload["gates"] == []
        assert any("full_backtest_summary.csv" in f for f in payload["failures"])


# ── Zero-Authority Suite Tests ────────────────────────────────────────


class TestZeroAuthority:
    def test_advisory_suite_fail_does_not_veto(self, harness) -> None:
        """ZA1: cost_sweep status=fail → PROMOTE(0), no veto at any layer.

        status=fail for zero-authority suites produces warnings only.
        Crash (status=error) → ERROR(3) is proven separately by SC2.
        """
        harness.set_queue(["cost_sweep"])
        _suite_payloads["cost_sweep"] = SuiteResult(
            name="cost_sweep",
            status="fail",
            data={"issues": ["row_count_mismatch"]},
        )

        results, verdict = harness.runner.run()

        assert verdict.tag == "PROMOTE"
        assert verdict.exit_code == 0
        assert not any("cost_sweep" in f for f in verdict.failures)
        assert any("Cost sweep" in w for w in verdict.warnings)

    def test_churn_fail_does_not_veto(self, harness) -> None:
        """ZA2: churn_metrics status=fail → PROMOTE(0), no veto."""
        harness.set_queue(["churn_metrics"])
        _suite_payloads["churn_metrics"] = SuiteResult(
            name="churn_metrics",
            status="fail",
            data={"warnings": ["high fee drag"], "issues": ["churn detected"]},
        )

        results, verdict = harness.runner.run()

        assert verdict.tag == "PROMOTE"
        assert verdict.exit_code == 0
        assert not any("churn" in f for f in verdict.failures)


# ── Precedence / Policy Override Tests ────────────────────────────────


class TestPrecedenceOnRealPath:
    def test_quality_policy_elevates_on_real_run_path(self, harness) -> None:
        """PD1: data_integrity soft-fail (hard_fail=False) → ERROR(3) via quality policy.

        Exercises the real path: evaluate_decision misses it (only catches hard_fail),
        _apply_quality_policy catches status=fail and elevates to ERROR.
        """
        harness.set_queue(["data_integrity"])
        _suite_payloads["data_integrity"] = SuiteResult(
            name="data_integrity",
            status="fail",
            data={"hard_fail": False},
        )

        results, verdict = harness.runner.run()

        assert verdict.tag == "ERROR"
        assert verdict.exit_code == 3
        assert any("data_integrity" in f for f in verdict.failures)

    def test_config_usage_policy_elevates_on_real_run_path(self, harness) -> None:
        """PD2: Unused config fields → ERROR(3) via config usage policy on real path."""
        harness.set_queue(["wfo"])
        _suite_payloads["wfo"] = _wfo_normal_payload()
        harness.set_usage(
            has_unused=True,
            unused_payload={
                "candidate": {"unused_fields": ["dead_param"]},
                "baseline": {"unused_fields": []},
            },
        )

        results, verdict = harness.runner.run()

        assert verdict.tag == "ERROR"
        assert verdict.exit_code == 3
        assert any("unused_config" in f for f in verdict.failures)

    def test_decision_json_matches_returned_verdict(self, harness) -> None:
        """PD3: Final decision.json on disk matches in-memory verdict exactly."""
        harness.set_queue(["wfo"])
        _suite_payloads["wfo"] = _wfo_normal_payload()

        results, verdict = harness.runner.run()

        decision_path = harness.outdir / "reports" / "decision.json"
        payload = json.loads(decision_path.read_text())

        assert payload["verdict"] == verdict.tag
        assert payload["exit_code"] == verdict.exit_code
        assert payload["failures"] == verdict.failures
        assert payload["warnings"] == verdict.warnings
        assert len(payload["gates"]) == len(verdict.gates)

    def test_both_policies_cumulate_on_real_path(self, harness) -> None:
        """PD4: quality + config both fail → ERROR(3) with failures from both sources."""
        harness.set_queue(["data_integrity"])
        _suite_payloads["data_integrity"] = SuiteResult(
            name="data_integrity",
            status="fail",
            data={"hard_fail": False},
        )
        harness.set_usage(
            has_unused=True,
            unused_payload={"candidate": {"unused_fields": ["stale"]}},
        )

        results, verdict = harness.runner.run()

        assert verdict.tag == "ERROR"
        assert verdict.exit_code == 3
        assert any("data_integrity" in f for f in verdict.failures)
        assert any("unused_config" in f for f in verdict.failures)

    def test_reject_not_downgraded_on_real_path(self, harness) -> None:
        """PD5: Hard gate REJECT → stays REJECT through all clean runner policies."""
        harness.set_queue(["backtest"])
        _suite_payloads["backtest"] = SuiteResult(
            name="backtest",
            status="pass",
            data={"deltas": {"harsh": {"score_delta": -0.3}}},
        )

        results, verdict = harness.runner.run()

        assert verdict.tag == "REJECT"
        assert verdict.exit_code == 2
        assert "full_harsh_delta_below_tolerance" in verdict.failures
