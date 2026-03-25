"""Performance metrics — per SPEC_METRICS.md.

All metrics computed from equity curve (list of EquitySnap),
trade records, and fill records.

Sharpe/Sortino annualized on 4H returns with population std (ddof=0).
No risk-free rate subtracted.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from v10.core.types import EquitySnap, Fill, Trade

PERIODS_PER_YEAR_4H = (24.0 / 4.0) * 365.0  # 2190


def compute_metrics(
    equity: list[EquitySnap],
    trades: list[Trade],
    fills: list[Fill],
    initial_cash: float,
    report_start_nav: float | None = None,
) -> dict[str, Any]:
    """Compute full performance summary.

    Parameters
    ----------
    initial_cash : float
        Actual starting capital (always written to summary as-is).
    report_start_nav : float | None
        NAV at first reporting bar close.  Used as denominator for
        CAGR / total_return.  Defaults to *initial_cash* when None.

    Returns a flat dict suitable for JSON serialization.
    """
    if not equity:
        return {"error": "no equity data"}

    if report_start_nav is None:
        report_start_nav = initial_cash

    # -- numpy arrays --------------------------------------------------------
    navs = np.array([e.nav_mid for e in equity], dtype=np.float64)
    navs_liq = np.array([e.nav_liq for e in equity], dtype=np.float64)
    exposures = np.array([e.exposure for e in equity], dtype=np.float64)

    initial_nav = report_start_nav
    final_nav = float(navs[-1])

    # -- time span -----------------------------------------------------------
    first_t = equity[0].close_time
    last_t = equity[-1].close_time
    years = (last_t - first_t) / (365.25 * 24 * 3600 * 1000)

    # -- returns -------------------------------------------------------------
    total_return = (final_nav / initial_nav - 1.0) * 100.0
    cagr = 0.0
    if years > 1e-6 and final_nav > 0:
        try:
            cagr = (pow(final_nav / initial_nav, 1.0 / years) - 1.0) * 100.0
        except OverflowError:
            # Very short period with large return → fallback to log method
            cagr = (math.exp(math.log(final_nav / initial_nav) / years) - 1.0) * 100.0

    # -- drawdown ------------------------------------------------------------
    max_dd_mid = _max_drawdown_pct(navs)
    max_dd_liq = _max_drawdown_pct(navs_liq)

    # -- risk-adjusted (4H returns) ------------------------------------------
    sharpe, sortino = _sharpe_sortino(navs)

    # -- calmar --------------------------------------------------------------
    calmar: float | None = None
    if max_dd_mid > 1e-6:
        calmar = cagr / max_dd_mid

    # -- trade stats ---------------------------------------------------------
    n_trades = len(trades)
    wins = sum(1 for t in trades if t.pnl > 0)
    losses = n_trades - wins
    win_rate = (wins / n_trades * 100.0) if n_trades > 0 else 0.0

    gross_profit = sum(t.pnl for t in trades if t.pnl > 0)
    gross_loss = abs(sum(t.pnl for t in trades if t.pnl < 0))
    if gross_loss > 0:
        profit_factor = gross_profit / gross_loss
    elif gross_profit > 0:
        profit_factor = float("inf")
    else:
        profit_factor = 0.0

    avg_pnl = sum(t.pnl for t in trades) / n_trades if n_trades > 0 else 0.0
    avg_days = sum(t.days_held for t in trades) / n_trades if n_trades > 0 else 0.0

    avg_win = (
        sum(t.pnl for t in trades if t.pnl > 0) / wins
        if wins > 0 else 0.0
    )
    avg_loss = (
        sum(t.pnl for t in trades if t.pnl < 0) / losses
        if losses > 0 else 0.0
    )

    # -- exposure ------------------------------------------------------------
    avg_exposure = float(exposures.mean()) if len(exposures) > 0 else 0.0
    time_in_market = float((exposures > 0.01).mean()) * 100.0 if len(exposures) > 0 else 0.0

    # -- fees & turnover -----------------------------------------------------
    total_fees = sum(f.fee for f in fills)
    turnover = sum(f.notional for f in fills)
    avg_nav = float(navs.mean()) if len(navs) > 0 else 1.0

    fee_drag_per_year = 0.0
    turnover_per_year = 0.0
    if years > 0 and avg_nav > 0:
        fee_drag_per_year = (total_fees / years) / avg_nav * 100.0
        turnover_per_year = turnover / (avg_nav * years)

    return {
        "initial_cash": round(initial_cash, 2),
        "report_start_nav": round(report_start_nav, 2),
        "final_nav_mid": round(final_nav, 2),
        "total_return_pct": round(total_return, 2),
        "cagr_pct": round(cagr, 2),
        "max_drawdown_mid_pct": round(max_dd_mid, 2),
        "max_drawdown_liq_pct": round(max_dd_liq, 2),
        "sharpe": round(sharpe, 4) if sharpe is not None else None,
        "sortino": round(sortino, 4) if sortino is not None else None,
        "calmar": round(calmar, 4) if calmar is not None else None,
        "trades": n_trades,
        "wins": wins,
        "losses": losses,
        "win_rate_pct": round(win_rate, 2),
        "profit_factor": round(profit_factor, 4) if not math.isinf(profit_factor) else "inf",
        "avg_trade_pnl": round(avg_pnl, 2),
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "avg_days_held": round(avg_days, 2),
        "avg_exposure": round(avg_exposure, 4),
        "time_in_market_pct": round(time_in_market, 2),
        "fees_total": round(total_fees, 2),
        "turnover_notional": round(turnover, 2),
        "fee_drag_pct_per_year": round(fee_drag_per_year, 2),
        "turnover_per_year": round(turnover_per_year, 2),
        "fills": len(fills),
        "years": round(years, 2),
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _max_drawdown_pct(navs: np.ndarray) -> float:
    """Peak-to-trough drawdown in percent."""
    if len(navs) < 2:
        return 0.0
    peak = np.maximum.accumulate(navs)
    dd = 1.0 - navs / peak
    return float(dd.max()) * 100.0


def _sharpe_sortino(
    navs: np.ndarray,
) -> tuple[float | None, float | None]:
    """Annualized Sharpe & Sortino on 4H pct_change, ddof=0."""
    if len(navs) < 3:
        return None, None

    returns = np.diff(navs) / navs[:-1]
    mu = float(returns.mean())
    sigma = float(returns.std(ddof=0))

    sharpe: float | None = None
    if sigma > 1e-12:
        sharpe = (mu / sigma) * math.sqrt(PERIODS_PER_YEAR_4H)

    sortino: float | None = None
    down = returns[returns < 0]
    if len(down) > 0:
        down_sigma = float(down.std(ddof=0))
        if down_sigma > 1e-12:
            sortino = (mu / down_sigma) * math.sqrt(PERIODS_PER_YEAR_4H)

    return sharpe, sortino
