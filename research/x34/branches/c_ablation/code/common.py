"""Shared helpers for X34 c_ablation strategies."""

from __future__ import annotations

import numpy as np


def ema(series: np.ndarray, period: int) -> np.ndarray:
    """EMA seeded with the first value."""
    alpha = 2.0 / (period + 1)
    out = np.empty_like(series)
    out[0] = series[0]
    for i in range(1, len(series)):
        out[i] = alpha * series[i] + (1.0 - alpha) * out[i - 1]
    return out


def atr(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    period: int,
) -> np.ndarray:
    """Wilder ATR matching the baseline VTREND implementation."""
    tr = np.maximum(
        high - low,
        np.maximum(
            np.abs(high - np.concatenate([[high[0]], close[:-1]])),
            np.abs(low - np.concatenate([[low[0]], close[:-1]])),
        ),
    )
    out = np.full_like(tr, np.nan)
    if period <= len(tr):
        out[period - 1] = np.mean(tr[:period])
        for i in range(period, len(tr)):
            out[i] = (out[i - 1] * (period - 1) + tr[i]) / period
    return out


def adaptive_gate(
    source: np.ndarray,
    *,
    fast: int,
    slow: int,
    k: float,
    eps: float = 1e-12,
) -> tuple[np.ndarray, np.ndarray]:
    """Return momentum and adaptive threshold for an oscillator source."""
    ema_fast = ema(source, fast)
    ema_slow = ema(source, slow)
    momentum = ema_fast - ema_slow
    baseline = ema(momentum, slow)
    scale = ema(np.abs(momentum - baseline), slow) + eps
    theta = k * scale
    return momentum, theta


def vdo_ratio_source(
    close: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    volume: np.ndarray,
    taker_buy: np.ndarray,
) -> np.ndarray:
    """Return the per-bar VDO ratio source before EMA oscillation."""
    n = len(close)
    has_taker = taker_buy is not None and np.any(taker_buy > 0)

    if has_taker:
        taker_sell = volume - taker_buy
        source = np.zeros(n, dtype=np.float64)
        mask = volume > 0
        source[mask] = (taker_buy[mask] - taker_sell[mask]) / volume[mask]
        return source

    spread = high - low
    source = np.zeros(n, dtype=np.float64)
    mask = spread > 0
    source[mask] = (close[mask] - low[mask]) / spread[mask] * 2.0 - 1.0
    return source
