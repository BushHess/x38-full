"""Unit tests for Q-VDO-RH Mode A indicator.

Tests per PLAN.md Phase 1:
- Constant input → output = 0
- Monotonic buy pressure → momentum > 0, trigger fires
- Sudden spike → scale adapts, threshold rises
- Hysteresis: trigger → hold → release sequence
- NaN/zero/missing data handling
- Range check: x_t doesn't blow up when quote_volume ≈ 0
- Empty input
"""

import numpy as np
import pytest

from research.x34.shared.indicators.q_vdo_rh import QVDOResult, _ema, q_vdo_rh


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _const_arrays(n: int, qv: float = 1e6, frac: float = 0.5):
    """Create constant taker/quote arrays. frac=0.5 means balanced."""
    quote_volume = np.full(n, qv)
    taker_buy_quote = np.full(n, qv * frac)
    return taker_buy_quote, quote_volume


# ---------------------------------------------------------------------------
# 1. Constant input → output = 0
# ---------------------------------------------------------------------------

class TestConstantInput:
    def test_balanced_flow_zero_momentum(self):
        """50% buy / 50% sell → delta=0 → x=0 → m=0."""
        tbq, qv = _const_arrays(200, qv=1e6, frac=0.5)
        r = q_vdo_rh(tbq, qv, fast=12, slow=28)
        # After warmup, momentum should converge to 0
        assert np.allclose(r.momentum[100:], 0.0, atol=1e-10)
        assert np.allclose(r.level[100:], 0.0, atol=1e-10)

    def test_no_triggers_on_balanced(self):
        tbq, qv = _const_arrays(200, qv=1e6, frac=0.5)
        r = q_vdo_rh(tbq, qv, fast=12, slow=28)
        assert not np.any(r.long_trigger[50:])


# ---------------------------------------------------------------------------
# 2. Monotonic buy pressure → momentum > 0, trigger fires
# ---------------------------------------------------------------------------

class TestBuyPressure:
    def test_increasing_buy_positive_momentum(self):
        """Increasing buy fraction → x rising → fast EMA > slow EMA → m > 0."""
        n = 200
        qv = np.full(n, 1e6)
        # Ramp buy fraction from 0.5 to 0.9 over the series
        frac = np.linspace(0.5, 0.9, n)
        tbq = qv * frac
        r = q_vdo_rh(tbq, qv, fast=12, slow=28)
        # After warmup, momentum should be positive (x is rising)
        assert np.all(r.momentum[60:] > 0)

    def test_step_buy_triggers(self):
        """Step from balanced to strong buy should trigger."""
        n = 300
        qv = np.full(n, 1e6)
        tbq = np.full(n, 0.5e6)  # balanced
        tbq[100:] = 0.85e6       # step to strong buy
        r = q_vdo_rh(tbq, qv, fast=12, slow=28, k=1.0)
        # After step, fast EMA rises before slow → positive momentum
        # Scale is still small from the balanced period → trigger fires
        assert np.any(r.long_trigger[100:150])

    def test_decreasing_buy_no_long_trigger(self):
        """Decreasing buy fraction → falling x → negative momentum."""
        n = 200
        qv = np.full(n, 1e6)
        frac = np.linspace(0.5, 0.1, n)
        tbq = qv * frac
        r = q_vdo_rh(tbq, qv, fast=12, slow=28)
        assert np.all(r.momentum[60:] < 0)
        assert not np.any(r.long_trigger[60:])

    def test_constant_buy_zero_momentum(self):
        """Constant buy fraction (even high) → x constant → m → 0.
        This is correct: momentum measures CHANGE in flow, not level."""
        n = 200
        tbq, qv = _const_arrays(n, qv=1e6, frac=0.8)
        r = q_vdo_rh(tbq, qv, fast=12, slow=28)
        assert np.allclose(r.momentum[60:], 0.0, atol=1e-10)


# ---------------------------------------------------------------------------
# 3. Sudden spike → scale adapts, threshold rises
# ---------------------------------------------------------------------------

class TestScaleAdaptation:
    def test_spike_raises_scale(self):
        """A sudden jump in buy pressure should increase scale."""
        n = 200
        tbq, qv = _const_arrays(n, qv=1e6, frac=0.5)
        # Inject a spike at bar 100
        tbq[100:110] = 0.95 * qv[100:110]

        r = q_vdo_rh(tbq, qv, fast=12, slow=28)

        # Scale after spike should be higher than before
        scale_before = r.scale[90]
        scale_after_peak = np.max(r.scale[110:150])
        assert scale_after_peak > scale_before * 2.0

    def test_theta_tracks_volatility(self):
        """Theta = k * scale, so theta should move with scale."""
        n = 200
        tbq, qv = _const_arrays(n, qv=1e6, frac=0.5)
        tbq[100:110] = 0.9 * qv[100:110]

        r = q_vdo_rh(tbq, qv, fast=12, slow=28, k=2.0)
        np.testing.assert_allclose(r.theta, 2.0 * r.scale)


# ---------------------------------------------------------------------------
# 4. Hysteresis: trigger → hold → release
# ---------------------------------------------------------------------------

class TestHysteresis:
    def test_hold_wider_than_trigger(self):
        """long_hold should be True whenever long_trigger is True,
        plus bars where 0.5*theta < m <= theta."""
        n = 300
        tbq, qv = _const_arrays(n, qv=1e6, frac=0.5)
        # Ramp up then gradually decay
        tbq[80:120] = 0.9 * qv[80:120]   # strong buy
        tbq[120:160] = 0.6 * qv[120:160]  # mild buy (decaying)

        r = q_vdo_rh(tbq, qv, fast=12, slow=28, k=1.0)

        # Wherever trigger is True, hold must also be True
        assert np.all(r.long_hold[r.long_trigger])

        # Hold should extend beyond trigger in some cases
        # (hold requires m > 0.5*theta, trigger requires m > theta)
        n_trigger = np.sum(r.long_trigger)
        n_hold = np.sum(r.long_hold)
        assert n_hold >= n_trigger

    def test_trigger_subset_of_hold(self):
        """long_trigger ⊆ long_hold by construction."""
        n = 200
        np.random.seed(42)
        qv = np.random.uniform(5e5, 2e6, n)
        tbq = qv * np.random.uniform(0.3, 0.7, n)
        r = q_vdo_rh(tbq, qv, fast=12, slow=28)
        # Every trigger bar must also be a hold bar
        assert np.all(r.long_hold | ~r.long_trigger)


# ---------------------------------------------------------------------------
# 5. NaN / zero / edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_zero_quote_volume_no_blow_up(self):
        """quote_volume = 0 should not produce inf or nan (eps protects)."""
        n = 100
        qv = np.zeros(n)
        tbq = np.zeros(n)
        r = q_vdo_rh(tbq, qv, fast=12, slow=28)
        assert np.all(np.isfinite(r.x))
        assert np.all(np.isfinite(r.momentum))
        assert np.all(np.isfinite(r.scale))
        assert np.all(np.isfinite(r.theta))

    def test_very_small_quote_volume(self):
        """Near-zero quote_volume shouldn't blow up x."""
        n = 100
        qv = np.full(n, 1e-15)
        tbq = np.full(n, 0.5e-15)
        r = q_vdo_rh(tbq, qv, fast=12, slow=28)
        assert np.all(np.isfinite(r.x))
        assert np.all(np.isfinite(r.momentum))

    def test_empty_input(self):
        """Empty arrays should return empty result without error."""
        r = q_vdo_rh(np.array([]), np.array([]))
        assert len(r.momentum) == 0
        assert len(r.long_trigger) == 0
        assert isinstance(r, QVDOResult)

    def test_single_bar(self):
        """Single bar should produce valid output."""
        r = q_vdo_rh(np.array([500_000.0]), np.array([1_000_000.0]))
        assert len(r.momentum) == 1
        assert np.isfinite(r.momentum[0])
        assert np.isfinite(r.scale[0])


# ---------------------------------------------------------------------------
# 6. EMA correctness
# ---------------------------------------------------------------------------

class TestEMA:
    def test_ema_constant_input(self):
        """EMA of constant = constant."""
        c = 42.0
        arr = np.full(100, c)
        out = _ema(arr, 20)
        np.testing.assert_allclose(out, c)

    def test_ema_step_response(self):
        """EMA should approach step value asymptotically."""
        n = 200
        arr = np.zeros(n)
        arr[50:] = 1.0
        out = _ema(arr, 10)
        # Before step
        assert out[49] < 0.01
        # Well after step
        assert out[199] > 0.99
        # Monotonically increasing after step
        assert np.all(np.diff(out[50:]) > 0)


# ---------------------------------------------------------------------------
# 7. Output shape and type contracts
# ---------------------------------------------------------------------------

class TestContracts:
    def test_output_shapes_match_input(self):
        n = 150
        tbq, qv = _const_arrays(n)
        r = q_vdo_rh(tbq, qv, fast=12, slow=28)
        assert r.x.shape == (n,)
        assert r.momentum.shape == (n,)
        assert r.level.shape == (n,)
        assert r.scale.shape == (n,)
        assert r.theta.shape == (n,)
        assert r.long_trigger.shape == (n,)
        assert r.long_hold.shape == (n,)
        assert r.high_confidence.shape == (n,)

    def test_trigger_dtype_bool(self):
        tbq, qv = _const_arrays(100)
        r = q_vdo_rh(tbq, qv)
        assert r.long_trigger.dtype == bool
        assert r.long_hold.dtype == bool
        assert r.high_confidence.dtype == bool

    def test_scale_always_positive(self):
        """scale = EMA(|...|) + eps, must be > 0."""
        n = 200
        np.random.seed(123)
        qv = np.random.uniform(1e5, 5e6, n)
        tbq = qv * np.random.uniform(0.2, 0.8, n)
        r = q_vdo_rh(tbq, qv)
        assert np.all(r.scale > 0)
        assert np.all(r.theta > 0)

    def test_theta_equals_k_times_scale(self):
        tbq, qv = _const_arrays(100)
        for k_val in [0.5, 1.0, 2.0, 3.0]:
            r = q_vdo_rh(tbq, qv, k=k_val)
            np.testing.assert_allclose(r.theta, k_val * r.scale)


# ---------------------------------------------------------------------------
# 8. High confidence alignment
# ---------------------------------------------------------------------------

class TestHighConfidence:
    def test_increasing_buy_high_confidence(self):
        """Increasing buy → both m>0 and l>0 → high confidence."""
        n = 200
        qv = np.full(n, 1e6)
        frac = np.linspace(0.55, 0.9, n)  # gradually increasing buy
        tbq = qv * frac
        r = q_vdo_rh(tbq, qv, fast=12, slow=28)
        # After warmup: x > 0 and rising → level > 0 and momentum > 0
        assert np.all(r.high_confidence[80:])

    def test_transition_low_confidence(self):
        """During regime transition, m and l may disagree."""
        n = 200
        tbq, qv = _const_arrays(n, frac=0.5)
        # First half: strong buy
        tbq[:100] = 0.9 * qv[:100]
        # Second half: strong sell
        tbq[100:] = 0.1 * qv[100:]
        r = q_vdo_rh(tbq, qv, fast=12, slow=28)
        # Around the transition, momentum (fast) flips before level (slow)
        # so there should be some bars with low confidence
        assert not np.all(r.high_confidence[90:130])


# ---------------------------------------------------------------------------
# 9. No lookahead
# ---------------------------------------------------------------------------

class TestNoLookahead:
    def test_output_at_bar_i_uses_only_0_to_i(self):
        """Changing future bars must not affect past output."""
        n = 200
        tbq1, qv1 = _const_arrays(n, frac=0.6)
        tbq2, qv2 = _const_arrays(n, frac=0.6)
        # Diverge after bar 100
        tbq2[100:] = 0.3 * qv2[100:]

        r1 = q_vdo_rh(tbq1, qv1, fast=12, slow=28)
        r2 = q_vdo_rh(tbq2, qv2, fast=12, slow=28)

        # Bars 0..99 must be identical
        np.testing.assert_array_equal(r1.momentum[:100], r2.momentum[:100])
        np.testing.assert_array_equal(r1.scale[:100], r2.scale[:100])
        np.testing.assert_array_equal(r1.long_trigger[:100], r2.long_trigger[:100])
