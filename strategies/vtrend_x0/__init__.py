"""X0 (vtrend_x0) — Alias for E0_ema21D1 (vtrend_ema21_d1).

Behaviorally identical to E0_ema21D1 but under its own identity.
Serves as the baseline anchor for X0 research phases.

Status: HOLD (2026-03-09) — PSR 0.8908 < 0.95 after framework reform.
Primary strategy is now E5_ema21D1 (vtrend_e5_ema21_d1).
Canonical name: vtrend_ema21_d1. Retained as fallback for LT2+ degradation.
"""

from strategies.vtrend_x0.strategy import VTrendX0Config, VTrendX0Strategy

__all__ = ["VTrendX0Config", "VTrendX0Strategy"]
