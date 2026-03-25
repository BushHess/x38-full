"""Effective degrees of freedom for correlated multiple tests.

When K tests are correlated (e.g., 16 timescales with adjacent r > 0.8),
treating them as K independent Bernoulli trials inflates the binomial
p-value. This module estimates the effective number of independent tests
(M_eff) from the correlation matrix and computes corrected p-values.

Three established methods are provided:

1. **Nyholt (2004)**: M_eff = 1 + (K-1)(1 - Var(λ)/K)
   Conservative for strong correlation. Simple eigenvalue variance formula.
   Ref: Nyholt DR (2004) Am J Hum Genet 74:765-769.

2. **Li-Ji (2005)**: M_eff = Σ f(λ_i) where f(x) = I(x≥1) + (x - floor(x))
   Less conservative. Counts eigenvalues: each ≥1 counts as 1,
   fractional parts of others accumulate.
   Ref: Li J, Ji L (2005) Heredity 95:221-227.

3. **Galwey (2009)**: M_eff = (Σλ)² / Σλ²
   Most intuitive: ratio of squared sum to sum of squares of eigenvalues.
   Equivalent to effective number of independent components.
   Ref: Galwey NW (2009) Genet Epidemiol 33:419-431.

Usage
-----
    from research.lib.effective_dof import compute_meff, corrected_binomial

    # corr_matrix: K×K correlation matrix of test outcomes across timescales
    meff = compute_meff(corr_matrix)
    result = corrected_binomial(wins=16, K=16, corr_matrix=corr_matrix)
"""

from __future__ import annotations

import numpy as np
from scipy import stats as sp_stats


def _eigenvalues(corr_matrix: np.ndarray) -> np.ndarray:
    """Eigenvalues of correlation matrix, sorted descending."""
    evals = np.linalg.eigvalsh(corr_matrix)
    # Clamp tiny negative eigenvalues from numerical noise
    evals = np.maximum(evals, 0.0)
    return np.sort(evals)[::-1]


def meff_nyholt(corr_matrix: np.ndarray) -> float:
    """Nyholt (2004): M_eff = 1 + (K-1)(1 - Var(λ)/K)."""
    evals = _eigenvalues(corr_matrix)
    K = len(evals)
    if K <= 1:
        return float(K)
    var_lambda = float(np.var(evals, ddof=0))
    meff = 1.0 + (K - 1) * (1.0 - var_lambda / K)
    return max(1.0, min(float(K), meff))


def meff_li_ji(corr_matrix: np.ndarray) -> float:
    """Li & Ji (2005): M_eff = Σ f(λ_i), f(x) = I(x≥1) + frac(x)."""
    evals = _eigenvalues(corr_matrix)
    meff = 0.0
    for lam in evals:
        if lam >= 1.0:
            meff += 1.0
        else:
            meff += lam - np.floor(lam)  # fractional part
    return max(1.0, meff)


def meff_galwey(corr_matrix: np.ndarray) -> float:
    """Galwey (2009): M_eff = (Σλ)² / Σλ²."""
    evals = _eigenvalues(corr_matrix)
    sum_lambda = float(np.sum(evals))
    sum_lambda_sq = float(np.sum(evals ** 2))
    if sum_lambda_sq < 1e-15:
        return 1.0
    meff = sum_lambda ** 2 / sum_lambda_sq
    return max(1.0, meff)


def compute_meff(corr_matrix: np.ndarray) -> dict[str, float]:
    """Compute effective DOF using all three methods.

    Parameters
    ----------
    corr_matrix : np.ndarray, shape (K, K)
        Correlation matrix of test outcomes across K tests.

    Returns
    -------
    dict with keys: 'nyholt', 'li_ji', 'galwey', 'conservative' (min of three)
    """
    m1 = meff_nyholt(corr_matrix)
    m2 = meff_li_ji(corr_matrix)
    m3 = meff_galwey(corr_matrix)
    return {
        "nyholt": round(m1, 2),
        "li_ji": round(m2, 2),
        "galwey": round(m3, 2),
        "conservative": round(min(m1, m2, m3), 2),
    }


def corrected_binomial(wins: int, K: int, corr_matrix: np.ndarray,
                       alternative: str = "greater") -> dict:
    """Compute both nominal and corrected binomial p-values.

    Parameters
    ----------
    wins : int
        Number of timescales where the metric improves (P > 0.5).
    K : int
        Total number of timescales tested.
    corr_matrix : np.ndarray, shape (K, K)
        Correlation matrix of binary outcomes across timescales.
    alternative : str
        'greater' for one-sided test (default).

    Returns
    -------
    dict with nominal p-value, corrected p-values per method, and M_eff values.
    """
    meff = compute_meff(corr_matrix)

    # Nominal p-value (assumes independence)
    p_nominal = sp_stats.binomtest(wins, K, 0.5, alternative=alternative).pvalue

    # Corrected: use M_eff as effective number of trials
    # If wins == K, corrected wins = M_eff (all effective trials won)
    # If wins < K, scale: corrected_wins = round(wins * M_eff / K)
    corrected = {}
    for method, m in meff.items():
        m_int = max(1, int(round(m)))
        # Scale wins proportionally
        if K > 0:
            w_scaled = int(round(wins * m / K))
            w_scaled = min(w_scaled, m_int)
            w_scaled = max(0, w_scaled)
        else:
            w_scaled = 0
        p_corr = sp_stats.binomtest(w_scaled, m_int, 0.5,
                                     alternative=alternative).pvalue
        corrected[method] = {
            "m_eff": round(m, 2),
            "m_eff_int": m_int,
            "wins_scaled": w_scaled,
            "p_value": float(p_corr),
        }

    return {
        "wins": wins,
        "K": K,
        "p_nominal": float(p_nominal),
        "meff": meff,
        "corrected": corrected,
    }
