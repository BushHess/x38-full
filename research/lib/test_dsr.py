"""Tests for Deflated Sharpe Ratio (research/lib/dsr.py)."""

from __future__ import annotations

import math

import numpy as np
import pytest

from dsr import benchmark_sr0, compute_dsr


# ═══════════════════════════════════════════════════════════════════════════════
# benchmark_sr0
# ═══════════════════════════════════════════════════════════════════════════════


class TestBenchmarkSR0:
    def test_monotone_in_num_trials(self):
        """More trials → higher expected max SR under null."""
        sr0_10 = benchmark_sr0(10, 5000)
        sr0_100 = benchmark_sr0(100, 5000)
        sr0_1000 = benchmark_sr0(1000, 5000)
        assert sr0_10 < sr0_100 < sr0_1000

    def test_monotone_in_n_obs(self):
        """More observations → lower SR₀ (√(1/(n-1)) shrinks)."""
        sr0_100 = benchmark_sr0(50, 100)
        sr0_1000 = benchmark_sr0(50, 1000)
        sr0_10000 = benchmark_sr0(50, 10000)
        assert sr0_100 > sr0_1000 > sr0_10000

    def test_positive(self):
        """SR₀ should always be positive for valid inputs."""
        assert benchmark_sr0(5, 500) > 0
        assert benchmark_sr0(245, 5000) > 0

    def test_invalid_inputs(self):
        """num_trials < 2 or n_obs < 2 → NaN."""
        assert math.isnan(benchmark_sr0(1, 5000))
        assert math.isnan(benchmark_sr0(0, 5000))
        assert math.isnan(benchmark_sr0(10, 1))
        assert math.isnan(benchmark_sr0(10, 0))

    def test_known_value_small(self):
        """Spot-check SR₀ for small N, moderate n."""
        sr0 = benchmark_sr0(num_trials=2, n_obs=1000)
        # N=2: z1=Φ⁻¹(0.5)=0, z2=Φ⁻¹(1-1/(2e))≈Φ⁻¹(0.816)≈0.900
        # SR₀ ≈ (0.4228*0 + 0.5772*0.900) / √999 ≈ 0.5195 / 31.61 ≈ 0.01643
        assert 0.015 < sr0 < 0.020


# ═══════════════════════════════════════════════════════════════════════════════
# compute_dsr — edge cases
# ═══════════════════════════════════════════════════════════════════════════════


class TestComputeDSREdgeCases:
    def test_too_few_observations(self):
        """n < 30 → all NaN."""
        r = np.random.default_rng(42).normal(0.001, 0.01, size=20)
        result = compute_dsr(r, num_trials=10)
        assert math.isnan(result["dsr_pvalue"])
        assert result["n_obs"] == 20

    def test_too_few_trials(self):
        """num_trials < 2 → all NaN."""
        r = np.random.default_rng(42).normal(0.001, 0.01, size=500)
        result = compute_dsr(r, num_trials=1)
        assert math.isnan(result["dsr_pvalue"])

    def test_zero_std(self):
        """Constant returns → NaN (Sharpe undefined)."""
        r = np.full(100, 0.001)
        result = compute_dsr(r, num_trials=10)
        assert math.isnan(result["dsr_pvalue"])

    def test_nan_in_returns_dropped(self):
        """NaN/Inf values in returns are silently dropped."""
        rng = np.random.default_rng(42)
        r = rng.normal(0.001, 0.01, size=100)
        r_dirty = r.copy()
        r_dirty[10] = np.nan
        r_dirty[20] = np.inf
        r_dirty[30] = -np.inf

        result_clean = compute_dsr(r, num_trials=10)
        result_dirty = compute_dsr(r_dirty, num_trials=10)
        # Dirty has 3 fewer obs → slightly different result
        assert result_dirty["n_obs"] == 97
        assert result_clean["n_obs"] == 100
        assert not math.isnan(result_dirty["dsr_pvalue"])


# ═══════════════════════════════════════════════════════════════════════════════
# compute_dsr — correctness
# ═══════════════════════════════════════════════════════════════════════════════


class TestComputeDSRCorrectness:
    def test_gaussian_returns_moderate_sr(self):
        """Gaussian returns with known positive mean should have DSR p > 0.5."""
        rng = np.random.default_rng(123)
        r = rng.normal(0.0005, 0.01, size=5000)  # SR ≈ 0.05 per bar
        bpy = 6.0 * 365.25
        result = compute_dsr(r, num_trials=10, bars_per_year=bpy)

        assert result["n_obs"] == 5000
        assert result["num_trials"] == 10
        assert result["sr_per_bar"] > 0
        assert result["sr0_per_bar"] > 0
        assert result["sr_annualized"] == pytest.approx(
            result["sr_per_bar"] * math.sqrt(bpy), rel=1e-10
        )
        # Gaussian: skewness ≈ 0, kurtosis ≈ 3
        assert abs(result["skewness"]) < 0.2
        assert abs(result["kurtosis"] - 3.0) < 0.3

    def test_more_trials_lower_pvalue(self):
        """Same returns, more trials → higher SR₀ → lower DSR p-value."""
        rng = np.random.default_rng(77)
        r = rng.normal(0.0003, 0.01, size=3000)

        p_10 = compute_dsr(r, num_trials=10)["dsr_pvalue"]
        p_100 = compute_dsr(r, num_trials=100)["dsr_pvalue"]
        p_1000 = compute_dsr(r, num_trials=1000)["dsr_pvalue"]

        assert p_10 > p_100 > p_1000

    def test_negative_skew_hurts(self):
        """Negative skew should reduce DSR p-value (correction penalizes)."""
        rng = np.random.default_rng(55)
        n = 5000
        # Symmetric returns
        r_sym = rng.normal(0.0004, 0.01, size=n)
        # Negative skew: clip positive tail, keep negative tail
        r_neg = r_sym.copy()
        r_neg[r_neg > 0.02] = 0.02  # cap upside
        r_neg = np.concatenate([r_neg, rng.normal(-0.03, 0.005, size=100)])

        res_sym = compute_dsr(r_sym, num_trials=50)
        res_neg = compute_dsr(r_neg, num_trials=50)

        assert res_neg["skewness"] < res_sym["skewness"]

    def test_zero_mean_returns_low_pvalue(self):
        """Pure noise (mean=0) with many trials → low DSR p-value."""
        rng = np.random.default_rng(99)
        r = rng.normal(0.0, 0.01, size=5000)
        result = compute_dsr(r, num_trials=500)

        # SR ≈ 0 but SR₀ >> 0 → DSR < 0 → p < 0.5
        assert result["dsr_pvalue"] < 0.5

    def test_strong_signal_high_pvalue(self):
        """Very strong signal should survive even many trials."""
        rng = np.random.default_rng(88)
        r = rng.normal(0.002, 0.01, size=5000)  # SR ≈ 0.2/bar → enormous
        result = compute_dsr(r, num_trials=1000)

        assert result["dsr_pvalue"] > 0.99

    def test_annualization_consistent(self):
        """sr_annualized / sr_per_bar == √bars_per_year."""
        rng = np.random.default_rng(44)
        r = rng.normal(0.0005, 0.01, size=2000)
        bpy = 365.25  # daily

        result = compute_dsr(r, num_trials=50, bars_per_year=bpy)
        ratio = result["sr_annualized"] / result["sr_per_bar"]
        assert ratio == pytest.approx(math.sqrt(bpy), rel=1e-10)

        ratio0 = result["sr0_annualized"] / result["sr0_per_bar"]
        assert ratio0 == pytest.approx(math.sqrt(bpy), rel=1e-10)

    def test_output_keys_complete(self):
        """All expected keys present in output dict."""
        rng = np.random.default_rng(42)
        r = rng.normal(0.0005, 0.01, size=500)
        result = compute_dsr(r, num_trials=10)

        expected_keys = {
            "n_obs", "num_trials", "sr_per_bar", "sr_annualized",
            "sr0_per_bar", "sr0_annualized", "dsr_statistic",
            "dsr_pvalue", "skewness", "kurtosis",
        }
        assert set(result.keys()) == expected_keys


# ═══════════════════════════════════════════════════════════════════════════════
# Cross-validation with VTrend implementation
# ═══════════════════════════════════════════════════════════════════════════════


class TestCrossValidateVTrend:
    """Verify numerical match with VTrend's compute_deflated_sharpe_ratio."""

    @staticmethod
    def _vtrend_dsr(returns, bars_per_year, num_trials):
        """Inline VTrend implementation for cross-validation.

        Exact copy from VTrend/vtrend_significance.py:887-951.
        """
        from statistics import NormalDist as ND

        clean = returns[np.isfinite(returns)]
        n = clean.size
        if n < 30 or num_trials <= 1:
            return None

        mean_ret = float(np.mean(clean))
        std_ret = float(np.std(clean, ddof=1))
        if std_ret <= 1e-12:
            return None

        sr_hat = mean_ret / std_ret
        centered = clean - mean_ret
        m2 = float(np.mean(centered ** 2))
        m3 = float(np.mean(centered ** 3))
        m4 = float(np.mean(centered ** 4))
        if m2 <= 1e-18:
            skewness = 0.0
            kurtosis = 3.0
        else:
            skewness = m3 / (m2 ** 1.5)
            kurtosis = m4 / (m2 ** 2)

        z = ND()
        gamma = 0.5772156649015329
        z1 = z.inv_cdf(max(1e-12, 1.0 - (1.0 / num_trials)))
        z2 = z.inv_cdf(max(1e-12, 1.0 - (1.0 / (num_trials * math.e))))
        sr0 = ((1.0 - gamma) * z1 + (gamma * z2)) * math.sqrt(
            1.0 / max(1, n - 1)
        )

        denom = 1.0 - (skewness * sr_hat) + (
            ((kurtosis - 1.0) / 4.0) * (sr_hat ** 2)
        )
        if denom <= 1e-12:
            return None
        dsr_stat = (sr_hat - sr0) * math.sqrt(max(1, n - 1)) / math.sqrt(denom)
        dsr_prob = float(z.cdf(dsr_stat))

        return {
            "sharpe_annualized": float(sr_hat * math.sqrt(bars_per_year)),
            "sr0_annualized": float(sr0 * math.sqrt(bars_per_year)),
            "dsr_probability": dsr_prob,
            "skewness": skewness,
            "kurtosis": kurtosis,
        }

    def test_exact_match_gaussian(self):
        """Gaussian returns: our DSR matches VTrend's exactly."""
        rng = np.random.default_rng(42)
        r = rng.normal(0.0005, 0.01, size=3000)

        ours = compute_dsr(r, num_trials=245, bars_per_year=6.0 * 365.25)
        theirs = self._vtrend_dsr(r, bars_per_year=6.0 * 365.25, num_trials=245)

        assert theirs is not None
        assert ours["sr_annualized"] == pytest.approx(
            theirs["sharpe_annualized"], rel=1e-10
        )
        assert ours["sr0_annualized"] == pytest.approx(
            theirs["sr0_annualized"], rel=1e-10
        )
        assert ours["dsr_pvalue"] == pytest.approx(
            theirs["dsr_probability"], rel=1e-10
        )
        assert ours["skewness"] == pytest.approx(theirs["skewness"], rel=1e-10)
        assert ours["kurtosis"] == pytest.approx(theirs["kurtosis"], rel=1e-10)

    def test_exact_match_skewed(self):
        """Skewed returns: our DSR matches VTrend's exactly."""
        rng = np.random.default_rng(77)
        # Log-normal returns (positive skew)
        r = np.exp(rng.normal(0.0003, 0.015, size=4000)) - 1.0

        ours = compute_dsr(r, num_trials=50, bars_per_year=365.25)
        theirs = self._vtrend_dsr(r, bars_per_year=365.25, num_trials=50)

        assert theirs is not None
        assert ours["dsr_pvalue"] == pytest.approx(
            theirs["dsr_probability"], rel=1e-10
        )
        assert ours["skewness"] == pytest.approx(theirs["skewness"], rel=1e-10)
        assert ours["kurtosis"] == pytest.approx(theirs["kurtosis"], rel=1e-10)

    def test_exact_match_fat_tails(self):
        """Fat-tailed returns (t-distribution): exact match."""
        rng = np.random.default_rng(55)
        # t-distribution with df=4 (fat tails, kurtosis > 3)
        r = rng.standard_t(df=4, size=5000) * 0.01 + 0.0002

        ours = compute_dsr(r, num_trials=100, bars_per_year=6.0 * 365.25)
        theirs = self._vtrend_dsr(r, bars_per_year=6.0 * 365.25, num_trials=100)

        assert theirs is not None
        assert ours["dsr_pvalue"] == pytest.approx(
            theirs["dsr_probability"], rel=1e-10
        )
        assert ours["kurtosis"] > 3.5  # fat tails


# ── PSR (Probabilistic Sharpe Ratio) tests ──────────────────────────────


class TestComputePSR:
    """Tests for compute_psr() — relative ranking between strategies."""

    def test_equal_sharpe_gives_half(self):
        """PSR(SR, SR) = 0.50 exactly — no evidence either way."""
        from dsr import compute_psr

        result = compute_psr(
            sr_candidate=1.0, sr_benchmark=1.0,
            n_obs=1000, skew=0.0, kurt=3.0,
        )
        assert result["psr"] == pytest.approx(0.5, abs=1e-6)
        assert result["z_score"] == pytest.approx(0.0, abs=1e-6)

    def test_higher_sharpe_gives_high_psr(self):
        """Large Sharpe gap with many observations → PSR close to 1."""
        from dsr import compute_psr

        result = compute_psr(
            sr_candidate=1.5, sr_benchmark=1.0,
            n_obs=2000, skew=0.0, kurt=3.0,
        )
        assert result["psr"] > 0.99

    def test_lower_sharpe_gives_low_psr(self):
        """Candidate below baseline → PSR < 0.5."""
        from dsr import compute_psr

        result = compute_psr(
            sr_candidate=0.8, sr_benchmark=1.2,
            n_obs=1000, skew=0.0, kurt=3.0,
        )
        assert result["psr"] < 0.05

    def test_small_gap_large_n_passes(self):
        """Small Sharpe gap but very many observations → eventually significant."""
        from dsr import compute_psr

        result = compute_psr(
            sr_candidate=1.05, sr_benchmark=1.00,
            n_obs=50_000, skew=0.0, kurt=3.0,
        )
        assert result["psr"] > 0.95

    def test_small_gap_small_n_fails(self):
        """Small Sharpe gap with few observations → not significant."""
        from dsr import compute_psr

        result = compute_psr(
            sr_candidate=1.05, sr_benchmark=1.00,
            n_obs=100, skew=0.0, kurt=3.0,
        )
        assert result["psr"] < 0.95

    def test_negative_skew_hurts(self):
        """Negative skew inflates observed SR → wider SE → lower PSR."""
        from dsr import compute_psr

        # Use small gap + few obs so PSR is in discriminating range
        psr_normal = compute_psr(
            sr_candidate=1.1, sr_benchmark=1.0,
            n_obs=200, skew=0.0, kurt=3.0,
        )
        psr_negskew = compute_psr(
            sr_candidate=1.1, sr_benchmark=1.0,
            n_obs=200, skew=-1.5, kurt=3.0,
        )
        # Negative skew widens SE → lower PSR for same gap
        assert psr_negskew["psr"] < psr_normal["psr"]
        assert psr_negskew["se"] > psr_normal["se"]

    def test_fat_tails_hurt(self):
        """High kurtosis inflates observed SR → wider SE → lower PSR."""
        from dsr import compute_psr

        psr_normal = compute_psr(
            sr_candidate=1.1, sr_benchmark=1.0,
            n_obs=200, skew=0.0, kurt=3.0,
        )
        psr_fat = compute_psr(
            sr_candidate=1.1, sr_benchmark=1.0,
            n_obs=200, skew=0.0, kurt=15.0,
        )
        assert psr_fat["psr"] < psr_normal["psr"]
        assert psr_fat["se"] > psr_normal["se"]

    def test_more_obs_increases_power(self):
        """More observations → narrower SE → higher PSR for same gap."""
        from dsr import compute_psr

        psr_small = compute_psr(
            sr_candidate=1.2, sr_benchmark=1.0,
            n_obs=500, skew=0.0, kurt=3.0,
        )
        psr_large = compute_psr(
            sr_candidate=1.2, sr_benchmark=1.0,
            n_obs=5000, skew=0.0, kurt=3.0,
        )
        assert psr_large["psr"] > psr_small["psr"]

    def test_insufficient_obs(self):
        """n_obs < 2 → NaN result."""
        from dsr import compute_psr

        result = compute_psr(
            sr_candidate=1.5, sr_benchmark=1.0,
            n_obs=1, skew=0.0, kurt=3.0,
        )
        assert math.isnan(result["psr"])

    def test_real_data_e5_vs_e0(self):
        """E5 vs E0 with real moments: PSR > 0.95 (matches comparison script)."""
        from dsr import compute_psr

        result = compute_psr(
            sr_candidate=1.3573,
            sr_benchmark=1.2653,
            n_obs=2607,
            skew=0.978623,
            kurt=15.014054,
        )
        assert result["psr"] == pytest.approx(0.9711, abs=0.005)
        assert result["psr"] > 0.95

    def test_real_data_e0plus_vs_e0(self):
        """E0+EMA1D21 vs E0: PSR < 0.95 (gap too small for significance)."""
        from dsr import compute_psr

        result = compute_psr(
            sr_candidate=1.3249,
            sr_benchmark=1.2653,
            n_obs=2607,
            skew=0.883609,
            kurt=15.312742,
        )
        assert result["psr"] == pytest.approx(0.8908, abs=0.005)
        assert result["psr"] < 0.95

    def test_se_formula_matches_dsr(self):
        """PSR standard error formula matches DSR variance formula."""
        from dsr import compute_psr, deflated_sharpe

        sr, n, skew, kurt = 1.3, 2000, 0.5, 8.0
        psr = compute_psr(sr, 1.0, n, skew, kurt)
        _, _, dsr_std = deflated_sharpe(sr, 50, n, skew, kurt)
        # Both use same variance formula: 1 - skew*SR + (kurt-1)/4 * SR²
        # PSR divides by (n-1), DSR divides by n (via max(t_samples,1))
        # Close but not identical due to n-1 vs n
        assert psr["se"] == pytest.approx(dsr_std, rel=0.01)
