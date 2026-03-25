"""Unit tests for the 5-gate absolute comparative sign-off framework.

Tests verify:
  (a) E5+EMA1D21 PASS all 5 gates with current data (vs X0 as alternative)
  (b) X0 (E0+EMA1D21) FAIL G1 and G2 with current data (vs E5+ as alternative)
  (c) A fake strategy with very high baseline but collapse under stress FAIL G4

Run: cd research/fragility_audit_20260306/code/step5 && python -m pytest test_comparative_signoff.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Make the step5 module importable
sys.path.insert(0, str(Path(__file__).parent))

from run_step5_live_signoff import (
    COMPARATIVE_GATE_THRESHOLDS,
    TIER_MAX_DELAY,
    CandidateProfile,
    ComparativeVerdict,
    DisruptionScenario,
    GateResult,
    evaluate_comparative_gates,
)

# ---------------------------------------------------------------------------
# Fixtures: real-data scenario Sharpes from DEPLOYMENT_SPEC_E5_EMA1D21_LT1.yaml
# crossover_analysis section
# ---------------------------------------------------------------------------

# E5+EMA1D21 absolute Sharpe under each disruption scenario
E5_PLUS_SCENARIOS = {
    "baseline":          (0, 0, 1.270),
    "entry_only_D1":     (1, 0, 1.189),
    "entry_only_D2":     (2, 0, 0.961),
    "exit_only_D1":      (0, 1, 1.145),
    "exit_only_D2":      (0, 2, 1.141),
    "entry_D1_exit_D1":  (1, 1, 1.084),
    "entry_D1_exit_D2":  (1, 2, 1.060),   # estimated from crossover trend
    "entry_D2_exit_D1":  (2, 1, 0.874),   # binding LT1 scenario
    "entry_D2_exit_D2":  (2, 2, 0.883),
    "entry_D4_exit_D2":  (4, 2, 0.695),
}
E5_PLUS_STOCHASTIC = {"LT1": 1.235, "LT2": 1.089, "LT3": 0.741}
E5_PLUS_BASELINE = 1.270
E5_PLUS_D1D1 = 1.084

# X0 (E0+EMA1D21) absolute Sharpe under each disruption scenario
X0_SCENARIOS = {
    "baseline":          (0, 0, 1.175),
    "entry_only_D1":     (1, 0, 1.128),
    "entry_only_D2":     (2, 0, 0.973),
    "exit_only_D1":      (0, 1, 0.988),
    "exit_only_D2":      (0, 2, 1.069),
    "entry_D1_exit_D1":  (1, 1, 0.976),
    "entry_D1_exit_D2":  (1, 2, 0.950),   # estimated from crossover trend
    "entry_D2_exit_D1":  (2, 1, 0.857),
    "entry_D2_exit_D2":  (2, 2, 0.889),
    "entry_D4_exit_D2":  (4, 2, 0.763),
}
X0_STOCHASTIC = {"LT1": 1.141, "LT2": 1.019, "LT3": 0.794}
X0_BASELINE = 1.175
X0_D1D1 = 0.976


def _make_profile(
    label: str,
    scenarios: dict[str, tuple[int, int, float]],
    stochastic: dict[str, float],
    baseline: float,
    d1_d1: float,
) -> CandidateProfile:
    """Build a CandidateProfile from scenario data."""
    sc_list = []
    for name, (ed, xd, sharpe) in scenarios.items():
        sc_list.append(DisruptionScenario(
            name=name, sharpe=sharpe,
            entry_delay=ed, exit_delay=xd, has_miss=False,
        ))
    return CandidateProfile(
        label=label,
        baseline_sharpe=baseline,
        scenarios=sc_list,
        stochastic_means=stochastic,
        d1_d1_sharpe=d1_d1,
    )


@pytest.fixture
def e5_plus() -> CandidateProfile:
    return _make_profile(
        "E5_plus_EMA1D21", E5_PLUS_SCENARIOS, E5_PLUS_STOCHASTIC,
        E5_PLUS_BASELINE, E5_PLUS_D1D1,
    )


@pytest.fixture
def x0() -> CandidateProfile:
    return _make_profile(
        "E0_plus_EMA1D21", X0_SCENARIOS, X0_STOCHASTIC,
        X0_BASELINE, X0_D1D1,
    )


# ===================================================================
# (a) E5+EMA1D21 passes ALL 5 gates vs X0
# ===================================================================

class TestE5PlusPassesAllGates:
    """E5+EMA1D21 should PASS all 5 gates with X0 as alternative."""

    def test_overall_verdict_is_go(self, e5_plus, x0):
        verdict = evaluate_comparative_gates(e5_plus, x0)
        assert verdict.status == "GO", f"Expected GO, got {verdict.status}"
        assert verdict.all_pass

    def test_g1_absolute_dominance_pass(self, e5_plus, x0):
        verdict = evaluate_comparative_gates(e5_plus, x0)
        g1 = verdict.gates[0]
        assert g1.gate == "G1_absolute_dominance"
        assert g1.passed, f"G1 FAIL: {g1.detail}"
        # E5+ worst LT1 (max_delay=2) should be 0.874 > X0's 0.857
        assert g1.value > g1.threshold

    def test_g2_state_dominance_pass(self, e5_plus, x0):
        verdict = evaluate_comparative_gates(e5_plus, x0)
        g2 = verdict.gates[1]
        assert g2.gate == "G2_state_dominance"
        assert g2.passed, f"G2 FAIL: {g2.detail}"
        # E5+ should win majority of scenarios
        assert g2.value > 0.50

    def test_g3_fractional_loss_pass(self, e5_plus, x0):
        verdict = evaluate_comparative_gates(e5_plus, x0)
        g3 = verdict.gates[2]
        assert g3.gate == "G3_fractional_loss"
        assert g3.passed, f"G3 FAIL: {g3.detail}"
        # (1.270 - 0.874) / 1.270 = 31.2% < 35%
        assert g3.value < 0.35

    def test_g4_absolute_floor_pass(self, e5_plus, x0):
        verdict = evaluate_comparative_gates(e5_plus, x0)
        g4 = verdict.gates[3]
        assert g4.gate == "G4_absolute_floor"
        assert g4.passed, f"G4 FAIL: {g4.detail}"
        # 0.874 > 0.50
        assert g4.value > 0.50

    def test_g5_infra_conditioned_pass(self, e5_plus, x0):
        verdict = evaluate_comparative_gates(e5_plus, x0)
        g5 = verdict.gates[4]
        assert g5.gate == "G5_infra_conditioned"
        assert g5.passed, f"G5 FAIL: {g5.detail}"
        # D1+D1 delta = 1.084 - 1.270 = -0.186 > -0.20
        assert g5.value > -0.20

    def test_e5_worst_lt1_sharpe_matches_spec(self, e5_plus):
        # DEPLOYMENT_SPEC: E5+ worst LT1 Sharpe = 0.874 (at D2+D1)
        worst = e5_plus.worst_sharpe(max_delay=TIER_MAX_DELAY["LT1"])
        assert abs(worst - 0.874) < 0.001, f"Expected ~0.874, got {worst}"

    def test_e5_d1_d1_delta_matches_spec(self, e5_plus):
        # DEPLOYMENT_SPEC: D1+D1 delta = -0.186
        delta = e5_plus.d1_d1_delta
        assert abs(delta - (-0.186)) < 0.001, f"Expected ~-0.186, got {delta}"


# ===================================================================
# (b) X0 (E0+EMA1D21) FAIL G1 and G2 vs E5+
# ===================================================================

class TestX0FailsG1G2:
    """X0 should FAIL G1 (absolute dominance) and G2 (state dominance) vs E5+."""

    def test_overall_verdict_not_go(self, e5_plus, x0):
        verdict = evaluate_comparative_gates(x0, e5_plus)
        assert verdict.status != "GO", f"Expected non-GO, got {verdict.status}"

    def test_g1_absolute_dominance_fail(self, e5_plus, x0):
        verdict = evaluate_comparative_gates(x0, e5_plus)
        g1 = verdict.gates[0]
        assert g1.gate == "G1_absolute_dominance"
        assert not g1.passed, f"G1 should FAIL: {g1.detail}"
        # X0 worst LT1 = 0.857 < E5+ worst LT1 = 0.874
        assert g1.value < g1.threshold

    def test_g2_state_dominance_fail(self, e5_plus, x0):
        verdict = evaluate_comparative_gates(x0, e5_plus)
        g2 = verdict.gates[1]
        assert g2.gate == "G2_state_dominance"
        assert not g2.passed, f"G2 should FAIL: {g2.detail}"
        # X0 wins < 50% of scenarios
        assert g2.value <= 0.50

    def test_g3_fractional_loss_still_passes(self, e5_plus, x0):
        verdict = evaluate_comparative_gates(x0, e5_plus)
        g3 = verdict.gates[2]
        assert g3.gate == "G3_fractional_loss"
        # (1.175 - 0.857) / 1.175 = 27.1% < 35%
        assert g3.passed, f"G3 should PASS for X0: {g3.detail}"

    def test_g4_absolute_floor_still_passes(self, e5_plus, x0):
        verdict = evaluate_comparative_gates(x0, e5_plus)
        g4 = verdict.gates[3]
        assert g4.gate == "G4_absolute_floor"
        # 0.857 > 0.50
        assert g4.passed, f"G4 should PASS for X0: {g4.detail}"

    def test_g5_infra_conditioned_still_passes(self, e5_plus, x0):
        verdict = evaluate_comparative_gates(x0, e5_plus)
        g5 = verdict.gates[4]
        assert g5.gate == "G5_infra_conditioned"
        # D1+D1 delta = 0.976 - 1.175 = -0.199 > -0.20
        assert g5.passed, f"G5 should PASS for X0: {g5.detail}"

    def test_x0_verdict_is_fallback(self, e5_plus, x0):
        """G1+G2 fail but G3+G4+G5 pass → FALLBACK."""
        verdict = evaluate_comparative_gates(x0, e5_plus)
        assert verdict.status == "FALLBACK"

    def test_x0_worst_lt1_sharpe_matches_spec(self, x0):
        # DEPLOYMENT_SPEC: X0 worst LT1 Sharpe = 0.857
        worst = x0.worst_sharpe(max_delay=TIER_MAX_DELAY["LT1"])
        assert abs(worst - 0.857) < 0.001, f"Expected ~0.857, got {worst}"


# ===================================================================
# (c) Fake strategy: high baseline, collapses under stress → FAIL G4
# ===================================================================

class TestFakeStrategyFailsG4:
    """A strategy with high baseline but collapse under stress should FAIL G4.

    Design: baseline=0.70, worst=0.48.
    - G3: (0.70 - 0.48) / 0.70 = 31.4% < 35% → PASS
    - G4: 0.48 < 0.50 → FAIL
    This proves G4 catches strategies that survive G3 but fall below the
    absolute floor — the case where a low-baseline strategy has modest
    fractional degradation but ends up at an unacceptable absolute level.
    """

    @pytest.fixture
    def fake_candidate(self) -> CandidateProfile:
        """Low-baseline strategy that degrades to below floor.

        Design: LT1 worst = 0.48 (D2+D1). All other LT1-eligible scenarios
        (max_delay <= 2) have Sharpe >= 0.49, so D2+D1 is the binding worst.
        G3: (0.70 - 0.48) / 0.70 = 31.4% < 35% → PASS
        G4: 0.48 < 0.50 → FAIL
        """
        return _make_profile(
            "FAKE_COLLAPSE",
            {
                "baseline":          (0, 0, 0.70),
                "entry_only_D1":     (1, 0, 0.65),
                "entry_only_D2":     (2, 0, 0.55),
                "exit_only_D1":      (0, 1, 0.60),
                "exit_only_D2":      (0, 2, 0.58),
                "entry_D1_exit_D1":  (1, 1, 0.52),
                "entry_D1_exit_D2":  (1, 2, 0.49),
                "entry_D2_exit_D1":  (2, 1, 0.48),   # worst LT1: below floor
                "entry_D2_exit_D2":  (2, 2, 0.49),   # above D2+D1 to keep D2+D1 as LT1 worst
                "entry_D4_exit_D2":  (4, 2, 0.25),   # beyond LT1 scope
            },
            stochastic={"LT1": 0.62, "LT2": 0.50, "LT3": 0.35},
            baseline=0.70,
            d1_d1=0.52,
        )

    @pytest.fixture
    def fake_alternative(self) -> CandidateProfile:
        """Weaker alternative (so G1 passes for the fake)."""
        return _make_profile(
            "WEAK_ALT",
            {
                "baseline":          (0, 0, 0.55),
                "entry_only_D1":     (1, 0, 0.50),
                "entry_only_D2":     (2, 0, 0.42),
                "exit_only_D1":      (0, 1, 0.48),
                "exit_only_D2":      (0, 2, 0.45),
                "entry_D1_exit_D1":  (1, 1, 0.40),
                "entry_D1_exit_D2":  (1, 2, 0.38),
                "entry_D2_exit_D1":  (2, 1, 0.35),
                "entry_D2_exit_D2":  (2, 2, 0.30),
                "entry_D4_exit_D2":  (4, 2, 0.15),
            },
            stochastic={"LT1": 0.48, "LT2": 0.38, "LT3": 0.22},
            baseline=0.55,
            d1_d1=0.40,
        )

    def test_g4_absolute_floor_fails(self, fake_candidate, fake_alternative):
        verdict = evaluate_comparative_gates(fake_candidate, fake_alternative)
        g4 = verdict.gates[3]
        assert g4.gate == "G4_absolute_floor"
        assert not g4.passed, f"G4 should FAIL: {g4.detail}"
        assert g4.value < 0.50

    def test_g3_fractional_loss_still_passes(self, fake_candidate, fake_alternative):
        """G3 passes because fractional loss is only 31.4% < 35%."""
        verdict = evaluate_comparative_gates(fake_candidate, fake_alternative)
        g3 = verdict.gates[2]
        assert g3.gate == "G3_fractional_loss"
        assert g3.passed, f"G3 should PASS: {g3.detail}"
        # (0.70 - 0.48) / 0.70 = 0.314
        assert g3.value < 0.35

    def test_g1_passes_because_alternative_worse(self, fake_candidate, fake_alternative):
        """G1 passes because fake dominates the weaker alternative."""
        verdict = evaluate_comparative_gates(fake_candidate, fake_alternative)
        g1 = verdict.gates[0]
        assert g1.passed, f"G1 should PASS: {g1.detail}"

    def test_overall_verdict_is_no_go(self, fake_candidate, fake_alternative):
        """G4 fail prevents GO; G4 fail also prevents FALLBACK."""
        verdict = evaluate_comparative_gates(fake_candidate, fake_alternative)
        assert verdict.status == "NO_GO", f"Expected NO_GO, got {verdict.status}"


# ===================================================================
# Edge cases and invariants
# ===================================================================

class TestGateInvariants:
    """Structural invariants for the 5-gate framework."""

    def test_always_5_gates(self, e5_plus, x0):
        verdict = evaluate_comparative_gates(e5_plus, x0)
        assert len(verdict.gates) == 5

    def test_gate_names_ordered(self, e5_plus, x0):
        verdict = evaluate_comparative_gates(e5_plus, x0)
        names = [g.gate for g in verdict.gates]
        assert names == [
            "G1_absolute_dominance",
            "G2_state_dominance",
            "G3_fractional_loss",
            "G4_absolute_floor",
            "G5_infra_conditioned",
        ]

    def test_to_dict_roundtrip(self, e5_plus, x0):
        verdict = evaluate_comparative_gates(e5_plus, x0)
        d = verdict.to_dict()
        assert d["candidate"] == "E5_plus_EMA1D21"
        assert d["alternative"] == "E0_plus_EMA1D21"
        assert d["status"] == "GO"
        assert len(d["gates"]) == 5

    def test_symmetry_one_go_one_not(self, e5_plus, x0):
        """If A beats B → GO, then B should NOT be GO vs A."""
        v_e5 = evaluate_comparative_gates(e5_plus, x0)
        v_x0 = evaluate_comparative_gates(x0, e5_plus)
        assert v_e5.status == "GO"
        assert v_x0.status != "GO"

    def test_comparison_dict_excludes_miss_scenarios(self):
        """Scenarios with has_miss=True should be excluded from G2 comparison."""
        profile = CandidateProfile(
            label="test",
            baseline_sharpe=1.0,
            scenarios=[
                DisruptionScenario("clean", 0.9, 0, 0, False),
                DisruptionScenario("miss", 0.8, 2, 1, True),
            ],
            stochastic_means={},
            d1_d1_sharpe=0.9,
        )
        d = profile.comparison_dict()
        assert "clean" in d
        assert "miss" not in d

    def test_worst_sharpe_tier_filtering(self):
        """worst_sharpe should respect max_delay for tier filtering."""
        profile = CandidateProfile(
            label="test",
            baseline_sharpe=1.5,
            scenarios=[
                DisruptionScenario("close", 0.9, 1, 1, False),   # max_delay=1
                DisruptionScenario("far", 0.3, 4, 2, False),     # max_delay=4
            ],
            stochastic_means={"LT1": 0.95},
            d1_d1_sharpe=0.9,
        )
        # LT1 max_delay=2: only "close" (max=1) and LT1 stochastic (max_d=2) qualify
        worst_lt1 = profile.worst_sharpe(max_delay=2)
        assert worst_lt1 == 0.9, f"Expected 0.9, got {worst_lt1}"
        # Global: "far" (0.3) is worst
        worst_global = profile.worst_sharpe(max_delay=99)
        assert worst_global == 0.3, f"Expected 0.3, got {worst_global}"

    def test_thresholds_match_deployment_spec(self):
        """Verify gate thresholds match DEPLOYMENT_SPEC values."""
        assert COMPARATIVE_GATE_THRESHOLDS["G2_state_dominance_min_ratio"] == 0.50
        assert COMPARATIVE_GATE_THRESHOLDS["G3_fractional_loss_max"] == 0.35
        assert COMPARATIVE_GATE_THRESHOLDS["G4_absolute_floor"] == 0.50
        assert COMPARATIVE_GATE_THRESHOLDS["G5_infra_delta_threshold"] == -0.20
