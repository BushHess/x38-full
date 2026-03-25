"""Deflated Sharpe Ratio and Probabilistic Sharpe Ratio for validation.

Self-contained copies of the DSR/PSR formulas from Bailey & López de Prado
(2012, 2014).  Kept in validation/lib/ to avoid importing from the research
package at validation runtime (research.__init__ emits a UserWarning when
imported outside research context).

Mathematical specification is identical to research/lib/dsr.py; see that
module for full academic references and the broader compute_dsr() function.
"""

from __future__ import annotations

import math
from statistics import NormalDist

# Euler-Mascheroni constant
_GAMMA = 0.5772156649015329


def deflated_sharpe(
    sr_observed: float,
    n_trials: int,
    t_samples: int,
    skew: float,
    kurt: float,
) -> tuple[float, float, float]:
    """Compute Deflated Sharpe from pre-computed moments.

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
        dsr_pvalue : Phi(z) — probability observed SR exceeds benchmark SR0.
        expected_max_sr : Gumbel-approximated expected max SR under null.
        sr_std : standard error of the SR estimator.
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
    """Probabilistic Sharpe Ratio — Bailey & Lopez de Prado (2012).

    Computes the probability that the candidate's *true* Sharpe exceeds
    ``sr_benchmark``, accounting for estimation uncertainty and non-normality.

    **Limitation**: This formulation treats ``sr_benchmark`` as a known
    constant, so it underestimates total uncertainty when comparing two
    estimated Sharpe ratios (anti-conservative for 2-strategy comparison).
    For paired inference, a differential-return bootstrap or Wilcoxon test
    on daily return differences is more appropriate.  The WFO suite
    provides this paired evidence separately.

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
