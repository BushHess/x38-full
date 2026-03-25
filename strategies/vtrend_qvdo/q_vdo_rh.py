"""Q-VDO-RH indicator — Mode A (taker quote data).

Production copy, self-contained within the vtrend_qvdo strategy.
Origin: research/x34/shared/indicators/q_vdo_rh.py

Spec: research/x34/resource/Q-VDO-RH_danh-gia-va-ket-luan.md §7, §9.1

Mode A uses signed notional flow normalized by activity regime:
    delta_t = 2 * taker_buy_quote_t - quote_volume_t
    x_t     = delta_t / (EMA(quote_volume, slow) + eps)
    m_t     = EMA(x, fast) - EMA(x, slow)          # momentum
    l_t     = EMA(x, slow)                          # level (context)
    scale_t = EMA(|m - EMA(m, slow)|, slow) + eps   # robust MAD scale
    theta_t = k * scale_t                           # adaptive threshold

Tunable params: fast, slow, k.  Locked: N_vol=slow, N_scale=slow, hyst=0.5.

Mode B (BVC fallback) is deferred — spec not frozen (§8).
The API is designed so Mode B can later replace x_t without refactoring
the m → l → scale → theta pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


# ---------------------------------------------------------------------------
# Output container
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class QVDOResult:
    """Per-bar output arrays from Q-VDO-RH."""
    x: np.ndarray            # normalized signed flow
    momentum: np.ndarray     # m_t  (fast EMA - slow EMA of x)
    level: np.ndarray        # l_t  (slow EMA of x — context only)
    scale: np.ndarray        # robust MAD scale of momentum
    theta: np.ndarray        # adaptive threshold (k * scale)
    long_trigger: np.ndarray   # bool: m > theta
    long_hold: np.ndarray      # bool: m > 0.5 * theta
    high_confidence: np.ndarray  # bool: sign(l) == sign(m)


# ---------------------------------------------------------------------------
# EMA helper (matches v10 strategies/_ema exactly)
# ---------------------------------------------------------------------------

def _ema(series: np.ndarray, period: int) -> np.ndarray:
    """Exponential moving average, seeded with first value."""
    alpha = 2.0 / (period + 1)
    out = np.empty_like(series, dtype=np.float64)
    out[0] = series[0]
    for i in range(1, len(series)):
        out[i] = alpha * series[i] + (1.0 - alpha) * out[i - 1]
    return out


# ---------------------------------------------------------------------------
# Main indicator
# ---------------------------------------------------------------------------

def q_vdo_rh(
    taker_buy_quote: np.ndarray,
    quote_volume: np.ndarray,
    fast: int = 12,
    slow: int = 28,
    k: float = 1.0,
    eps: float = 1e-12,
) -> QVDOResult:
    """Compute Q-VDO-RH Mode A.

    Parameters
    ----------
    taker_buy_quote : array, shape (N,)
        Taker buy quote asset volume per bar.
    quote_volume : array, shape (N,)
        Total quote asset volume per bar.
    fast : int
        Fast EMA period for oscillator.
    slow : int
        Slow EMA period — also used for activity normalization and scale.
    k : float
        Threshold multiplier (1.0 = 1× MAD scale).
    eps : float
        Numerical safety for denominators.

    Returns
    -------
    QVDOResult
        Per-bar arrays. First ``slow`` bars are warmup — values are
        mathematically valid but statistically unreliable.
    """
    taker_buy_quote = np.asarray(taker_buy_quote, dtype=np.float64)
    quote_volume = np.asarray(quote_volume, dtype=np.float64)

    n = len(taker_buy_quote)
    if n == 0:
        empty = np.empty(0, dtype=np.float64)
        empty_bool = np.empty(0, dtype=bool)
        return QVDOResult(
            x=empty, momentum=empty, level=empty,
            scale=empty, theta=empty,
            long_trigger=empty_bool, long_hold=empty_bool,
            high_confidence=empty_bool,
        )

    # --- Step 1: signed notional flow, normalized by activity regime ---
    delta = 2.0 * taker_buy_quote - quote_volume
    ema_qv = _ema(quote_volume, slow)
    x = delta / (ema_qv + eps)

    # --- Step 2: momentum and level ---
    ema_x_fast = _ema(x, fast)
    ema_x_slow = _ema(x, slow)
    m = ema_x_fast - ema_x_slow   # momentum
    l = ema_x_slow                 # level (context)

    # --- Step 3: robust adaptive threshold ---
    ema_m_slow = _ema(m, slow)
    abs_dev = np.abs(m - ema_m_slow)
    scale = _ema(abs_dev, slow) + eps
    theta = k * scale

    # --- Step 4: triggers and holds ---
    long_trigger = m > theta
    long_hold = m > 0.5 * theta
    high_confidence = np.sign(l) == np.sign(m)

    return QVDOResult(
        x=x,
        momentum=m,
        level=l,
        scale=scale,
        theta=theta,
        long_trigger=long_trigger,
        long_hold=long_hold,
        high_confidence=high_confidence,
    )
