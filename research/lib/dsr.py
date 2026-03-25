"""Deflated Sharpe Ratio (Bailey & López de Prado, 2014).

Adjusts observed Sharpe ratio for:
  1. Number of trials (strategies tested) — via Gumbel-approximated benchmark SR₀
  2. Skewness — negative skew inflates SR
  3. Excess kurtosis — fat tails inflate SR

Formula
-------
  SR₀ = [(1-γ)·Φ⁻¹(1-1/N) + γ·Φ⁻¹(1-1/(N·e))] · √(1/(n-1))
  DSR = (SR - SR₀)·√(n-1) / √[1 - skew·SR + ((kurt-1)/4)·SR²]
  p   = Φ(DSR)

Where:
  γ = 0.5772156649015329 (Euler-Mascheroni constant)
  N = num_trials (total strategies explored)
  n = number of return observations
  SR = μ/σ (sample Sharpe, per-bar, NOT annualized)

Usage
-----
    from research.lib.dsr import compute_dsr, benchmark_sr0

    result = compute_dsr(returns, num_trials=245)
    # result['dsr_pvalue']     → probability SR is genuine (> SR₀)
    # result['sr_annualized']  → annualized observed Sharpe
    # result['sr0_annualized'] → annualized benchmark (null) Sharpe

    sr0 = benchmark_sr0(num_trials=245, n_obs=5000)
    # Expected max Sharpe from 245 iid strategies on n=5000 observations

Ref: Bailey DH, López de Prado M (2014) "The Deflated Sharpe Ratio:
     Correcting for Selection Bias, Backtest Overfitting, and
     Non-Normality." J Portfolio Management 40(5):94-107.
"""

from __future__ import annotations

import math
from statistics import NormalDist

import numpy as np

# Euler-Mascheroni constant
_GAMMA = 0.5772156649015329


def _nan_result(n_obs: int, num_trials: int) -> dict:
    return {
        "n_obs": n_obs,
        "num_trials": num_trials,
        "sr_per_bar": float("nan"),
        "sr_annualized": float("nan"),
        "sr0_per_bar": float("nan"),
        "sr0_annualized": float("nan"),
        "dsr_statistic": float("nan"),
        "dsr_pvalue": float("nan"),
        "skewness": float("nan"),
        "kurtosis": float("nan"),
    }


def benchmark_sr0(num_trials: int, n_obs: int) -> float:
    """Expected maximum Sharpe ratio under null (all strategies have SR=0).

    Uses the Gumbel approximation from Bailey & López de Prado (2014):

        SR₀ = [(1-γ)·Φ⁻¹(1-1/N) + γ·Φ⁻¹(1-1/(N·e))] · √(1/(n-1))

    Parameters
    ----------
    num_trials : int
        Number of strategy variants tested (N). Must be >= 2.
    n_obs : int
        Number of return observations (n). Must be >= 2.

    Returns
    -------
    float
        Per-bar benchmark Sharpe ratio (SR₀). Returns NaN if inputs invalid.
    """
    if num_trials < 2 or n_obs < 2:
        return float("nan")

    z = NormalDist()
    z1 = z.inv_cdf(max(1e-12, 1.0 - 1.0 / num_trials))
    z2 = z.inv_cdf(max(1e-12, 1.0 - 1.0 / (num_trials * math.e)))
    return ((1.0 - _GAMMA) * z1 + _GAMMA * z2) * math.sqrt(1.0 / (n_obs - 1))


def deflated_sharpe(
    sr_observed: float,
    n_trials: int,
    t_samples: int,
    skew: float,
    kurt: float,
) -> tuple[float, float, float]:
    """Compute Deflated Sharpe from pre-computed moments.

    Convenience wrapper matching the calling convention used by the
    validation pipeline, where Sharpe / skew / kurt are computed
    externally before entering the DSR formula.

    Parameters
    ----------
    sr_observed : float
        Observed Sharpe ratio (per-bar or annualized — must be consistent
        with the skew/kurt that were computed from the same return series).
    n_trials : int
        Number of strategy variants tested.
    t_samples : int
        Number of return observations.
    skew : float
        Sample skewness of returns.
    kurt : float
        Sample kurtosis of returns (raw, NOT excess).

    Returns
    -------
    (dsr_pvalue, expected_max_sr, sr_std)
        dsr_pvalue : Φ(z) — probability observed SR exceeds benchmark SR₀.
        expected_max_sr : Gumbel-approximated expected max SR under null.
        sr_std : standard error of the SR estimator.

    Note: The validation suite (selection_bias.py) derives all inputs (SR,
    T, skew, kurt) from the same daily log-return series, matching the
    theoretical contract of Bailey & López de Prado (2014).
    See Report 21, §3 — DSR is a single-strategy advisory, not a paired gate.
    """
    z = NormalDist()
    variance = (
        1.0 - skew * sr_observed + ((kurt - 1.0) / 4.0) * sr_observed ** 2
    ) / max(t_samples, 1)
    variance = max(variance, 1e-12)
    std = math.sqrt(variance)

    if n_trials <= 1:
        expected_max_sr = 0.0
    else:
        z1 = z.inv_cdf(max(1e-12, 1.0 - 1.0 / n_trials))
        z2 = z.inv_cdf(max(1e-12, 1.0 - 1.0 / (n_trials * math.e)))
        expected_max_sr = std * ((1.0 - _GAMMA) * z1 + _GAMMA * z2)

    zscore = (sr_observed - expected_max_sr) / std
    dsr_pvalue = float(z.cdf(zscore))
    return dsr_pvalue, expected_max_sr, std


def compute_psr(
    sr_candidate: float,
    sr_benchmark: float,
    n_obs: int,
    skew: float,
    kurt: float,
) -> dict:
    """Probabilistic Sharpe Ratio — Bailey & López de Prado (2012).

    Computes the probability that the candidate's *true* Sharpe exceeds
    ``sr_benchmark``, accounting for estimation uncertainty and non-normality.

    Formula
    -------
        PSR(SR*) = Φ[(SR̂ − SR*) · √(n−1) / √(1 − γ₃·SR̂ + (γ₄−1)/4 · SR̂²)]

    Where:
        SR̂  = candidate's observed (sample) Sharpe
        SR*  = benchmark Sharpe to beat (e.g. baseline strategy)
        γ₃   = skewness of candidate returns
        γ₄   = kurtosis of candidate returns (raw, NOT excess)

    This is the *relative* test: "does candidate genuinely beat baseline?"
    Contrast with DSR which is *absolute*: "does candidate beat random noise?"

    Parameters
    ----------
    sr_candidate : float
        Candidate's observed Sharpe ratio (same scale as sr_benchmark).
    sr_benchmark : float
        Benchmark Sharpe to exceed (typically the baseline strategy's Sharpe).
    n_obs : int
        Number of return observations used to estimate sr_candidate.
    skew : float
        Sample skewness of candidate's returns.
    kurt : float
        Sample kurtosis of candidate's returns (raw, NOT excess).

    Returns
    -------
    dict with keys:
        psr          : float — P(true SR > SR*), in [0, 1]
        sr_candidate : float
        sr_benchmark : float
        n_obs        : int
        se           : float — standard error of SR estimator
        z_score      : float — test statistic

    Ref: Bailey DH, López de Prado M (2012) "The Sharpe Ratio Efficient
         Frontier." J Risk 15(2):3-44.
    """
    if n_obs < 2:
        return {
            "psr": float("nan"),
            "sr_candidate": sr_candidate,
            "sr_benchmark": sr_benchmark,
            "n_obs": n_obs,
            "se": float("nan"),
            "z_score": float("nan"),
        }

    # Variance of the SR estimator under non-normality
    variance = 1.0 - skew * sr_candidate + ((kurt - 1.0) / 4.0) * sr_candidate ** 2
    variance = max(variance, 1e-12)
    se = math.sqrt(variance / max(n_obs - 1, 1))

    if se < 1e-12:
        # Degenerate: treat any positive gap as certain
        psr_value = 1.0 if sr_candidate > sr_benchmark else 0.0
        return {
            "psr": psr_value,
            "sr_candidate": sr_candidate,
            "sr_benchmark": sr_benchmark,
            "n_obs": n_obs,
            "se": 0.0,
            "z_score": float("inf") if sr_candidate > sr_benchmark else float("-inf"),
        }

    z = (sr_candidate - sr_benchmark) / se
    psr_value = float(NormalDist().cdf(z))

    return {
        "psr": round(psr_value, 6),
        "sr_candidate": round(sr_candidate, 6),
        "sr_benchmark": round(sr_benchmark, 6),
        "n_obs": n_obs,
        "se": round(se, 6),
        "z_score": round(z, 6),
    }


def compute_dsr(
    returns: np.ndarray,
    num_trials: int,
    bars_per_year: float = 6.0 * 365.25,
) -> dict:
    """Compute the Deflated Sharpe Ratio.

    Parameters
    ----------
    returns : np.ndarray
        Per-bar (not annualized) return series. NaN/Inf values are dropped.
    num_trials : int
        Total number of strategy configurations explored (e.g., grid size).
    bars_per_year : float
        For annualization. Default 6×365.25 = 2191.5 (H4 bars).

    Returns
    -------
    dict with keys:
        n_obs, num_trials, sr_per_bar, sr_annualized, sr0_per_bar,
        sr0_annualized, dsr_statistic, dsr_pvalue, skewness, kurtosis.

        dsr_pvalue is the CDF value Φ(DSR). Higher → more confident that
        observed SR exceeds the benchmark SR₀.  Values > 0.95 are strong.
    """
    clean = returns[np.isfinite(returns)]
    n = int(clean.size)

    if n < 30 or num_trials < 2:
        return _nan_result(n, num_trials)

    mean_ret = float(np.mean(clean))
    std_ret = float(np.std(clean, ddof=1))

    if std_ret <= 1e-12:
        return _nan_result(n, num_trials)

    sr_hat = mean_ret / std_ret

    # Higher moments
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

    # Benchmark SR₀
    sr0 = benchmark_sr0(num_trials, n)

    # Deflated t-statistic with moment correction
    denom = 1.0 - skewness * sr_hat + ((kurtosis - 1.0) / 4.0) * (sr_hat ** 2)
    if denom <= 1e-12:
        return _nan_result(n, num_trials)

    dsr_stat = (sr_hat - sr0) * math.sqrt(n - 1) / math.sqrt(denom)
    dsr_pvalue = float(NormalDist().cdf(dsr_stat))

    ann = math.sqrt(bars_per_year)
    return {
        "n_obs": n,
        "num_trials": num_trials,
        "sr_per_bar": float(sr_hat),
        "sr_annualized": float(sr_hat * ann),
        "sr0_per_bar": float(sr0),
        "sr0_annualized": float(sr0 * ann),
        "dsr_statistic": float(dsr_stat),
        "dsr_pvalue": dsr_pvalue,
        "skewness": float(skewness),
        "kurtosis": float(kurtosis),
    }
