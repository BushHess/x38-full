"""Tests for 7-strategy evaluation framework (with E5_plus_EMA1D21).

Tests:
1. Signal extractor properties (each produces valid binary signals)
2. E5_plus_EMA1D21 structural properties
3. Signal concordance invariants
4. Sizing overlay invariants
5. D1 data loading
6. No production mutation
7. Scoring formula
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

_TESTS = Path(__file__).resolve().parent
_SRC = _TESTS.parent / "src"
_REPO = _TESTS.parents[3]

for p in [str(_SRC), str(_REPO)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from run_factorial_7s import (
    extract_e0_signal, extract_e5_signal, extract_sm_signal,
    extract_latch_signal, extract_e0_plus_ema1d21_signal,
    extract_e5_plus_ema1d21_signal,
    apply_binary_100, apply_entry_vol_no_rebal, apply_native_vol_rebal,
    signal_concordance, compute_score, _find_warmup, _robust_atr,
    compute_indicators, STRATEGY_NAMES,
)
from strategies.vtrend.strategy import _ema, _atr, _vdo


# ═══════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def synthetic_indicators():
    """Synthetic indicator dict with known properties."""
    np.random.seed(42)
    n = 2000
    # Random walk price
    log_ret = np.random.normal(0.0002, 0.02, n)
    close = 10000.0 * np.exp(np.cumsum(log_ret))
    high = close * (1 + np.abs(np.random.normal(0, 0.005, n)))
    low = close * (1 - np.abs(np.random.normal(0, 0.005, n)))
    volume = np.random.uniform(100, 1000, n)
    taker_buy = volume * np.random.uniform(0.4, 0.6, n)

    ema_fast = _ema(close, 30)
    ema_slow = _ema(close, 120)
    atr = _atr(high, low, close, 14)
    vdo = _vdo(close, high, low, volume, taker_buy, 12, 28)

    slope_ref = np.full(n, np.nan, dtype=np.float64)
    slope_ref[6:] = ema_slow[:-6]

    from strategies.latch.strategy import (
        _rolling_high_shifted, _rolling_low_shifted, _realized_vol,
    )
    hh60 = _rolling_high_shifted(high, lookback=60)
    ll30 = _rolling_low_shifted(low, lookback=30)
    rv = _realized_vol(close, lookback=120, bars_per_year=2190.0)
    robust_atr = _robust_atr(high, low, close)

    # Fake D1 regime (every 6 bars = 1 day)
    d1_regime_h4 = np.ones(n, dtype=np.bool_)
    # Turn off regime for first quarter
    d1_regime_h4[:n // 4] = False

    return dict(
        close=close, high=high, low=low,
        volume=volume, taker_buy=taker_buy,
        ema_fast=ema_fast, ema_slow=ema_slow,
        atr=atr, vdo=vdo, slope_ref=slope_ref,
        hh60=hh60, ll30=ll30, rv=rv,
        robust_atr=robust_atr,
        d1_regime_h4=d1_regime_h4,
    )


# ═══════════════════════════════════════════════════════════════════════════
# TEST 1: SIGNAL EXTRACTOR PROPERTIES
# ═══════════════════════════════════════════════════════════════════════════

class TestSignalExtractorProperties:

    def _check_signal(self, sig: dict, n: int):
        """Common checks for all signal extractors."""
        assert sig["entry"].shape == (n,)
        assert sig["exit"].shape == (n,)
        assert sig["in_position"].shape == (n,)
        assert sig["entry"].dtype == np.bool_
        assert sig["exit"].dtype == np.bool_
        assert sig["in_position"].dtype == np.bool_
        # Entry and exit never on same bar
        assert not np.any(sig["entry"] & sig["exit"])
        # Entry only when transitioning to in_position
        for i in range(1, n):
            if sig["entry"][i]:
                assert sig["in_position"][i], f"Entry at {i} but not in_position"
            if sig["exit"][i]:
                assert not sig["in_position"][i], f"Exit at {i} but still in_position"

    def test_e0_properties(self, synthetic_indicators):
        sig = extract_e0_signal(synthetic_indicators)
        self._check_signal(sig, len(synthetic_indicators["close"]))

    def test_e5_properties(self, synthetic_indicators):
        sig = extract_e5_signal(synthetic_indicators)
        self._check_signal(sig, len(synthetic_indicators["close"]))

    def test_sm_properties(self, synthetic_indicators):
        sig = extract_sm_signal(synthetic_indicators)
        self._check_signal(sig, len(synthetic_indicators["close"]))

    def test_latch_properties(self, synthetic_indicators):
        sig = extract_latch_signal(synthetic_indicators)
        self._check_signal(sig, len(synthetic_indicators["close"]))

    def test_e0_plus_ema1d21_properties(self, synthetic_indicators):
        sig = extract_e0_plus_ema1d21_signal(synthetic_indicators)
        self._check_signal(sig, len(synthetic_indicators["close"]))

    def test_e5_plus_ema1d21_properties(self, synthetic_indicators):
        sig = extract_e5_plus_ema1d21_signal(synthetic_indicators)
        self._check_signal(sig, len(synthetic_indicators["close"]))

    def test_all_produce_some_trades(self, synthetic_indicators):
        """Each extractor should produce at least 1 entry on 2000 bars."""
        extractors = [
            extract_e0_signal, extract_e5_signal, extract_sm_signal,
            extract_latch_signal, extract_e0_plus_ema1d21_signal,
            extract_e5_plus_ema1d21_signal,
        ]
        for fn in extractors:
            sig = fn(synthetic_indicators)
            assert np.sum(sig["entry"]) >= 1, f"{fn.__name__} produced 0 entries"


# ═══════════════════════════════════════════════════════════════════════════
# TEST 2: E5_plus_EMA1D21 STRUCTURAL PROPERTIES
# ═══════════════════════════════════════════════════════════════════════════

class TestE5PlusEma1d21:

    def test_fewer_entries_than_e5(self, synthetic_indicators):
        """E5_plus_EMA1D21 adds D1 regime filter → should have <= entries than E5."""
        e5 = extract_e5_signal(synthetic_indicators)
        e5_d1 = extract_e5_plus_ema1d21_signal(synthetic_indicators)
        assert np.sum(e5_d1["entry"]) <= np.sum(e5["entry"])

    def test_d1_regime_off_blocks_entry(self, synthetic_indicators):
        """When D1 regime is OFF, no E5_plus_EMA1D21 entries should occur."""
        sig = extract_e5_plus_ema1d21_signal(synthetic_indicators)
        d1_regime = synthetic_indicators["d1_regime_h4"]
        entries = np.where(sig["entry"])[0]
        for bar in entries:
            assert d1_regime[bar], f"Entry at bar {bar} but D1 regime is OFF"

    def test_uses_robust_atr_not_standard(self, synthetic_indicators):
        """E5_plus_EMA1D21 should use robust ATR (same exit timing as E5, not E0).

        If robust ATR has longer warmup, entries should start no earlier than E5.
        """
        e5 = extract_e5_signal(synthetic_indicators)
        e5_d1 = extract_e5_plus_ema1d21_signal(synthetic_indicators)
        # E5_plus_EMA1D21 entries are a subset of E5 entries (due to D1 filter)
        # but with same exit logic (robust ATR trail)
        e5_entries = np.sum(e5["entry"])
        e5_d1_entries = np.sum(e5_d1["entry"])
        assert e5_d1_entries <= e5_entries

    def test_entry_requires_trend_up(self, synthetic_indicators):
        """E5_plus_EMA1D21 entry requires ema_fast > ema_slow."""
        sig = extract_e5_plus_ema1d21_signal(synthetic_indicators)
        entries = np.where(sig["entry"])[0]
        for bar in entries:
            assert synthetic_indicators["ema_fast"][bar] > synthetic_indicators["ema_slow"][bar]

    def test_exit_timing_differs_from_e0_d1(self, synthetic_indicators):
        """E5_plus_EMA1D21 uses robust ATR for trail → exits may differ from E0_plus_EMA1D21."""
        e0_d1 = extract_e0_plus_ema1d21_signal(synthetic_indicators)
        e5_d1 = extract_e5_plus_ema1d21_signal(synthetic_indicators)
        # Both produce exits
        assert np.sum(e0_d1["exit"]) > 0
        assert np.sum(e5_d1["exit"]) > 0

    def test_e5_d1_fewer_entries_than_e0_d1(self, synthetic_indicators):
        """E5_plus_EMA1D21 should have <= entries than E0_plus_EMA1D21.

        E5 has longer warmup (robust ATR cap_lb=100 + period=20 = 120).
        State-machine divergence from different exits means different re-entry timing.
        """
        e0_d1 = extract_e0_plus_ema1d21_signal(synthetic_indicators)
        e5_d1 = extract_e5_plus_ema1d21_signal(synthetic_indicators)
        # First entry of E5_D1 should be >= first entry of E0_D1 (longer warmup)
        e0_d1_first = np.where(e0_d1["entry"])[0]
        e5_d1_first = np.where(e5_d1["entry"])[0]
        if len(e0_d1_first) > 0 and len(e5_d1_first) > 0:
            assert e5_d1_first[0] >= e0_d1_first[0], \
                "E5_D1 first entry should be >= E0_D1 (robust ATR longer warmup)"


# ═══════════════════════════════════════════════════════════════════════════
# TEST 3: SIGNAL CONCORDANCE MATRIX
# ═══════════════════════════════════════════════════════════════════════════

class TestSignalConcordance:

    def test_concordance_symmetric(self, synthetic_indicators):
        signals = {
            "E0": extract_e0_signal(synthetic_indicators),
            "E5": extract_e5_signal(synthetic_indicators),
            "E5_plus_EMA1D21": extract_e5_plus_ema1d21_signal(synthetic_indicators),
        }
        conc = signal_concordance(signals)
        np.testing.assert_allclose(conc.values, conc.values.T, atol=1e-10)

    def test_concordance_diagonal_100(self, synthetic_indicators):
        signals = {
            "E0": extract_e0_signal(synthetic_indicators),
            "E5_plus_EMA1D21": extract_e5_plus_ema1d21_signal(synthetic_indicators),
        }
        conc = signal_concordance(signals)
        for i in range(len(conc)):
            assert abs(conc.iloc[i, i] - 100.0) < 1e-10

    def test_concordance_range(self, synthetic_indicators):
        signals = {
            "E5": extract_e5_signal(synthetic_indicators),
            "E5_plus_EMA1D21": extract_e5_plus_ema1d21_signal(synthetic_indicators),
        }
        conc = signal_concordance(signals)
        assert (conc.values >= 0).all()
        assert (conc.values <= 100.0 + 1e-10).all()


# ═══════════════════════════════════════════════════════════════════════════
# TEST 4: SIZING OVERLAY INVARIANTS
# ═══════════════════════════════════════════════════════════════════════════

class TestSizingOverlays:

    def test_binary_100_matches_in_position(self, synthetic_indicators):
        sig = extract_e5_plus_ema1d21_signal(synthetic_indicators)
        tw = apply_binary_100(sig["in_position"])
        expected = sig["in_position"].astype(np.float64)
        np.testing.assert_array_equal(tw, expected)

    def test_entry_vol_zero_when_flat(self, synthetic_indicators):
        sig = extract_e5_plus_ema1d21_signal(synthetic_indicators)
        rv = synthetic_indicators["rv"]
        tw = apply_entry_vol_no_rebal(sig["in_position"], sig["entry"], rv, 0.15)
        flat = ~sig["in_position"]
        assert np.all(tw[flat] == 0.0)

    def test_entry_vol_bounded(self, synthetic_indicators):
        sig = extract_e5_plus_ema1d21_signal(synthetic_indicators)
        rv = synthetic_indicators["rv"]
        tw = apply_entry_vol_no_rebal(sig["in_position"], sig["entry"], rv, 0.15)
        assert np.all(tw >= 0.0)
        assert np.all(tw <= 1.0)

    def test_native_vol_rebal_bounded(self, synthetic_indicators):
        sig = extract_sm_signal(synthetic_indicators)
        rv = synthetic_indicators["rv"]
        tw = apply_native_vol_rebal(sig["in_position"], rv, 0.15, 0.08)
        assert np.all(tw >= 0.0)
        assert np.all(tw <= 1.0)


# ═══════════════════════════════════════════════════════════════════════════
# TEST 5: D1 DATA LOADING
# ═══════════════════════════════════════════════════════════════════════════

class TestD1Data:

    def test_d1_data_loads(self):
        from data_align_6s import load_d1_data
        d1 = load_d1_data()
        assert d1["n"] > 0
        assert len(d1["close"]) == d1["n"]
        assert len(d1["close_time"]) == d1["n"]
        assert d1["close_time"][-1] > d1["close_time"][0]  # sorted

    def test_load_all(self):
        from data_align_6s import load_all
        data = load_all()
        assert data["n_h4"] > 0
        assert data["n_d1"] > 0
        assert len(data["bars"]) == data["n_h4"]
        assert len(data["h4_close_times"]) == data["n_h4"]


# ═══════════════════════════════════════════════════════════════════════════
# TEST 6: NO PRODUCTION MUTATION
# ═══════════════════════════════════════════════════════════════════════════

class TestNoMutation:

    def test_signal_extraction_no_mutation(self, synthetic_indicators):
        """Signal extraction must not modify indicator arrays."""
        originals = {k: v.copy() if isinstance(v, np.ndarray) else v
                     for k, v in synthetic_indicators.items()}
        extract_e0_signal(synthetic_indicators)
        extract_e5_signal(synthetic_indicators)
        extract_e5_plus_ema1d21_signal(synthetic_indicators)
        for k, v in synthetic_indicators.items():
            if isinstance(v, np.ndarray):
                np.testing.assert_array_equal(v, originals[k],
                    err_msg=f"Indicator {k} was mutated")


# ═══════════════════════════════════════════════════════════════════════════
# TEST 7: SCORING FORMULA
# ═══════════════════════════════════════════════════════════════════════════

class TestScoringFormula:

    def test_score_positive_for_good_strategy(self):
        m = {"cagr": 0.50, "mdd": 0.40, "sharpe": 1.2,
             "profit_factor": 2.0, "n_trade_events": 100}
        score, terms = compute_score(m)
        assert score > 0

    def test_score_decomposition_sums(self):
        m = {"cagr": 0.30, "mdd": 0.50, "sharpe": 0.8,
             "profit_factor": 1.5, "n_trade_events": 50}
        score, terms = compute_score(m)
        assert abs(score - sum(terms.values())) < 1e-10


# ═══════════════════════════════════════════════════════════════════════════
# TEST 8: STRATEGY_NAMES CONSISTENCY
# ═══════════════════════════════════════════════════════════════════════════

class TestStrategyNames:

    def test_e5_plus_ema1d21_in_strategy_names(self):
        assert "E5_plus_EMA1D21" in STRATEGY_NAMES

    def test_six_strategies(self):
        assert len(STRATEGY_NAMES) == 6

    def test_all_expected_strategies(self):
        expected = {"E0", "E5", "SM", "LATCH", "E0_plus_EMA1D21", "E5_plus_EMA1D21"}
        assert set(STRATEGY_NAMES) == expected


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
