# Origin: research/prod_readiness_e5_ema1d21/regime_monitor_v2.py, promoted 2026-03-09
#
# MDD-only Regime Monitor (production version).
#
# Monitors rolling 6-month and 12-month max drawdown on D1 bars.
# Classifies market regime into NORMAL / AMBER / RED.
# RED = bear market detected → block new entries, force flat.
#
# Alert thresholds (MDD-only, no ATR):
#   RED:   6m MDD > 55% OR 12m MDD > 70%
#   AMBER: 6m MDD > 45% OR 12m MDD > 60%
#
# Validated: 2022 bear triggers RED, ≤2 false RED episodes in 7-year history.
# Backtest impact: Sharpe +0.118, CAGR +5.3%, MDD -0.9%.
# Mechanism: entry prevention (blocks false bullish signals during bear bounces).

from __future__ import annotations

import numpy as np


# =========================================================================
# CONSTANTS
# =========================================================================

ALERT_NAMES = {0: "NORMAL", 1: "AMBER", 2: "RED"}

# Rolling window lengths (D1 bars)
ROLL_6M = 180
ROLL_12M = 360

# Alert thresholds
AMBER_MDD_6M = 0.45
AMBER_MDD_12M = 0.60
RED_MDD_6M = 0.55
RED_MDD_12M = 0.70


# =========================================================================
# CORE FUNCTIONS
# =========================================================================


def rolling_mdd(close: np.ndarray, window: int = ROLL_6M) -> np.ndarray:
    """Rolling max drawdown over trailing ``window`` bars.

    Returns array of same length as ``close``, NaN where insufficient history.
    MDD expressed as fraction (0.55 = 55%).
    """
    n = len(close)
    mdd = np.full(n, np.nan)
    for t in range(window - 1, n):
        seg = close[t - window + 1 : t + 1]
        peak = np.maximum.accumulate(seg)
        dd = 1.0 - seg / peak
        mdd[t] = np.max(dd)
    return mdd


def classify_alerts(mdd_6m: np.ndarray, mdd_12m: np.ndarray) -> np.ndarray:
    """Classify each bar as 0=NORMAL, 1=AMBER, 2=RED using MDD-only.

    RED:   6m MDD > 55% OR 12m MDD > 70%
    AMBER: 6m MDD > 45% OR 12m MDD > 60%
    """
    n = len(mdd_6m)
    alerts = np.zeros(n, dtype=np.int8)

    for t in range(n):
        m6 = mdd_6m[t] if not np.isnan(mdd_6m[t]) else 0.0
        m12 = mdd_12m[t] if not np.isnan(mdd_12m[t]) else 0.0

        if m6 > RED_MDD_6M or m12 > RED_MDD_12M:
            alerts[t] = 2
        elif m6 > AMBER_MDD_6M or m12 > AMBER_MDD_12M:
            alerts[t] = 1

    return alerts


def extract_episodes(alerts: np.ndarray, level: int) -> list[tuple[int, int]]:
    """Extract contiguous episodes where alert >= ``level``.

    Returns list of (start_idx, end_idx) inclusive tuples.
    """
    episodes: list[tuple[int, int]] = []
    in_ep = False
    start = 0
    for t in range(len(alerts)):
        if alerts[t] >= level and not in_ep:
            in_ep = True
            start = t
        elif alerts[t] < level and in_ep:
            episodes.append((start, t - 1))
            in_ep = False
    if in_ep:
        episodes.append((start, len(alerts) - 1))
    return episodes


def map_d1_alert_to_h4(
    d1_alerts: np.ndarray, d1_ct: np.ndarray, h4_ct: np.ndarray
) -> np.ndarray:
    """Map D1 alert level to H4 bar grid (causal — uses latest D1 close <= H4 close)."""
    n_h4 = len(h4_ct)
    n_d1 = len(d1_ct)
    h4_alerts = np.zeros(n_h4, dtype=np.int8)
    d1_idx = 0
    for i in range(n_h4):
        while d1_idx + 1 < n_d1 and d1_ct[d1_idx + 1] < h4_ct[i]:
            d1_idx += 1
        if d1_ct[d1_idx] < h4_ct[i]:
            h4_alerts[i] = d1_alerts[d1_idx]
    return h4_alerts


def compute_regime(d1_close: np.ndarray) -> dict:
    """Compute full regime monitor signals from D1 close prices.

    Returns dict with keys: mdd_6m, mdd_12m, alerts, alert_counts.
    """
    mdd_6m = rolling_mdd(d1_close, ROLL_6M)
    mdd_12m = rolling_mdd(d1_close, ROLL_12M)
    alerts = classify_alerts(mdd_6m, mdd_12m)

    n = len(d1_close)
    return {
        "mdd_6m": mdd_6m,
        "mdd_12m": mdd_12m,
        "alerts": alerts,
        "alert_counts": {
            "total": n,
            "normal": int(np.sum(alerts == 0)),
            "amber": int(np.sum(alerts == 1)),
            "red": int(np.sum(alerts == 2)),
        },
    }


def is_red(alerts: np.ndarray, idx: int) -> bool:
    """Check if bar at ``idx`` is in RED regime."""
    return bool(alerts[idx] == 2)
