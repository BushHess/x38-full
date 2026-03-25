"""Shared helpers for the V4 vs E5 fair comparison branch.

Data loading, backtest wrappers, WFO, bootstrap, metrics, I/O.
"""

from __future__ import annotations

import csv
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats as sp_stats

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------

_THIS_DIR = Path(__file__).resolve().parent
BRANCH_DIR = _THIS_DIR.parent
RESULTS_DIR = BRANCH_DIR / "results"
X37_DIR = _THIS_DIR.parents[2]        # research/x37/
ROOT = _THIS_DIR.parents[4]           # btc-spot-dev/
DATA_DIR = X37_DIR / "data"           # research/x37/data/

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from v10.core.data import DataFeed  # noqa: E402
from v10.core.engine import BacktestEngine  # noqa: E402
from v10.core.types import CostConfig, SCENARIOS  # noqa: E402

# ---------------------------------------------------------------------------
# Cost configs
# ---------------------------------------------------------------------------

COST_FAIR = CostConfig(spread_bps=4.0, slippage_bps=2.0, taker_fee_pct=0.06)
# per_side = 4/2 + 2 + 0.06*100 = 2+2+6 = 10 bps -> RT = 20 bps

COST_HARSH = SCENARIOS["harsh"]  # RT = 50 bps


def make_cost_rt(rt_bps: float) -> CostConfig:
    """Create a CostConfig with given round-trip bps (simplified)."""
    per_side_pct = rt_bps / 200.0
    return CostConfig(spread_bps=0.0, slippage_bps=0.0, taker_fee_pct=per_side_pct)


COST_SWEEP_BPS = [10, 15, 20, 25, 30, 50, 100]

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

_COMBINED_PATH: str | None = None


def _get_combined_path() -> str:
    """Combine x37/data H4+D1 CSVs into a single file for DataFeed."""
    global _COMBINED_PATH
    combined = RESULTS_DIR / "_combined_data.csv"
    if _COMBINED_PATH is not None and Path(_COMBINED_PATH).exists():
        return _COMBINED_PATH
    if combined.exists():
        _COMBINED_PATH = str(combined)
        return _COMBINED_PATH

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    h4_df = pd.read_csv(DATA_DIR / "data_btcusdt_4h.csv")
    d1_df = pd.read_csv(DATA_DIR / "data_btcusdt_1d.csv")
    merged = pd.concat([h4_df, d1_df], ignore_index=True)
    merged.to_csv(combined, index=False)
    _COMBINED_PATH = str(combined)
    return _COMBINED_PATH


def load_data_feed(
    start: str | None = None,
    end: str | None = None,
    warmup_days: int = 0,
) -> DataFeed:
    """Load data from x37/data into a DataFeed."""
    return DataFeed(_get_combined_path(), start=start, end=end,
                    warmup_days=warmup_days)

# ---------------------------------------------------------------------------
# Backtest wrapper
# ---------------------------------------------------------------------------


def run_backtest(
    strategy: Any,
    feed: DataFeed,
    cost: CostConfig,
    initial_cash: float = 10_000.0,
) -> Any:
    """Run a single backtest, return BacktestResult."""
    engine = BacktestEngine(
        feed=feed, strategy=strategy, cost=cost,
        initial_cash=initial_cash, warmup_mode="no_trade",
    )
    return engine.run()


# ---------------------------------------------------------------------------
# Objective score
# ---------------------------------------------------------------------------


def objective_score(summary: dict) -> float:
    """Compute objective score matching validation pipeline formula."""
    cagr = summary.get("cagr_pct", 0.0)
    max_dd = summary.get("max_drawdown_mid_pct", 0.0)
    sharpe = summary.get("sharpe", 0.0) or 0.0
    pf_raw = summary.get("profit_factor", 0.0)
    pf_val = 3.0 if isinstance(pf_raw, str) else (pf_raw or 0.0)
    pf = min(pf_val, 3.0)
    n_trades = summary.get("trades", 0)
    return (
        2.5 * cagr
        - 0.60 * max_dd
        + 8.0 * max(0, sharpe)
        + 5.0 * max(0, pf - 1)
        + min(n_trades / 50, 1) * 5.0
    )

def wilcoxon_test(deltas: list[float]) -> dict:
    """One-sided Wilcoxon signed-rank test (H_a: median > 0)."""
    arr = np.array(deltas, dtype=np.float64)
    arr = arr[arr != 0]  # remove zeros
    if len(arr) < 6:
        return {
            "W_plus": float("nan"),
            "p_value": 1.0,
            "n": len(arr),
            "pass": False,
            "sufficient": False,
        }

    stat, p_two = sp_stats.wilcoxon(arr, alternative="greater")
    return {
        "W_plus": float(stat),
        "p_value": float(p_two),
        "n": int(len(arr)),
        "pass": float(p_two) <= 0.10,
        "sufficient": True,
    }


def bootstrap_ci(
    deltas: list[float],
    n_boot: int = 10_000,
    alpha: float = 0.05,
) -> dict:
    """Percentile bootstrap CI on mean delta."""
    arr = np.array(deltas, dtype=np.float64)
    if len(arr) < 2:
        return {
            "mean": float("nan"),
            "ci_lo": float("nan"),
            "ci_hi": float("nan"),
            "ci_above_zero": False,
            "n": int(len(arr)),
        }
    rng = np.random.default_rng(42)
    means = np.empty(n_boot)
    for b in range(n_boot):
        idx = rng.integers(0, len(arr), size=len(arr))
        means[b] = arr[idx].mean()
    lo = float(np.percentile(means, 100 * alpha / 2))
    hi = float(np.percentile(means, 100 * (1 - alpha / 2)))
    return {
        "mean": float(arr.mean()),
        "ci_lo": round(lo, 4),
        "ci_hi": round(hi, 4),
        "ci_above_zero": lo > 0,
        "n": int(len(arr)),
    }

# ---------------------------------------------------------------------------
# Daily returns extraction
# ---------------------------------------------------------------------------


def extract_daily_nav(result: Any) -> pd.Series:
    """Extract daily NAV series from BacktestResult equity curve."""
    if not result.equity:
        return pd.Series(dtype=float)

    times = [
        dt.datetime.fromtimestamp(e.close_time / 1000, tz=dt.timezone.utc)
        for e in result.equity
    ]
    navs = [e.nav_mid for e in result.equity]
    s = pd.Series(navs, index=pd.DatetimeIndex(times))
    # Resample to daily (last observation of each day)
    return s.resample("1D").last().dropna()


def daily_returns(result: Any) -> np.ndarray:
    """Extract daily log returns from BacktestResult."""
    nav = extract_daily_nav(result)
    if len(nav) < 2:
        return np.array([])
    return np.diff(np.log(nav.values))

# ---------------------------------------------------------------------------
# Paired block bootstrap (V4 vs E5)
# ---------------------------------------------------------------------------


def paired_block_bootstrap(
    ret_a: np.ndarray,
    ret_b: np.ndarray,
    block_size: int = 20,
    n_boot: int = 2_000,
) -> dict:
    """Block bootstrap on (ret_a - ret_b) daily returns.

    Returns P(Sharpe_A > Sharpe_B), median delta, 95% CI.
    """
    n = min(len(ret_a), len(ret_b))
    if n < 30 or n < block_size + 1:
        return {"p_a_gt_b": 0.5, "median_delta": 0.0,
                "ci_lo": 0.0, "ci_hi": 0.0, "n_days": n}

    ret_a = ret_a[:n]
    ret_b = ret_b[:n]
    rng = np.random.default_rng(42)
    n_blocks = (n + block_size - 1) // block_size

    delta_sharpes = np.empty(n_boot)
    for b in range(n_boot):
        # Sample block start indices
        starts = rng.integers(0, n - block_size + 1, size=n_blocks)
        idx = np.concatenate([np.arange(s, s + block_size) for s in starts])[:n]
        ra = ret_a[idx]
        rb = ret_b[idx]
        sha = _sharpe_from_daily(ra)
        shb = _sharpe_from_daily(rb)
        delta_sharpes[b] = sha - shb

    p_gt = float(np.mean(delta_sharpes > 0))
    return {
        "p_a_gt_b": round(p_gt, 4),
        "median_delta": round(float(np.median(delta_sharpes)), 4),
        "ci_lo": round(float(np.percentile(delta_sharpes, 2.5)), 4),
        "ci_hi": round(float(np.percentile(delta_sharpes, 97.5)), 4),
        "n_days": n,
    }


def _sharpe_from_daily(rets: np.ndarray) -> float:
    """Annualized Sharpe from daily returns."""
    if len(rets) < 2 or np.std(rets) == 0:
        return 0.0
    return float(np.mean(rets) / np.std(rets, ddof=0) * np.sqrt(365.25))

# ---------------------------------------------------------------------------
# Trade-level analysis
# ---------------------------------------------------------------------------


def trade_distribution(trades: list) -> dict:
    """Compute trade distribution statistics."""
    n = len(trades)
    if n == 0:
        return {"trades": 0}

    rets = [t.return_pct / 100.0 for t in trades]
    pnls = [t.pnl for t in trades]
    days = [t.days_held for t in trades]
    wins = [r for r in rets if r > 0]
    losses = [r for r in rets if r <= 0]

    sorted_pnl = sorted(pnls, reverse=True)
    top5 = sum(sorted_pnl[:5])
    bot5 = sum(sorted_pnl[-5:])

    return {
        "trades": n,
        "win_rate": round(len(wins) / n, 4) if n else 0,
        "avg_return": round(float(np.mean(rets)), 6),
        "median_return": round(float(np.median(rets)), 6),
        "avg_hold_days": round(float(np.mean(days)), 2),
        "median_hold_days": round(float(np.median(days)), 2),
        "top5_pnl_sum": round(top5, 2),
        "bottom5_pnl_sum": round(bot5, 2),
    }


def trades_to_rows(trades: list) -> list[dict]:
    """Convert Trade objects to dicts for CSV export."""
    rows = []
    for t in trades:
        rows.append({
            "trade_id": t.trade_id,
            "entry_ts": t.entry_ts_ms,
            "exit_ts": t.exit_ts_ms,
            "entry_price": round(t.entry_price, 2),
            "exit_price": round(t.exit_price, 2),
            "qty": round(t.qty, 8),
            "pnl": round(t.pnl, 2),
            "return_pct": round(t.return_pct, 4),
            "days_held": round(t.days_held, 2),
            "entry_reason": t.entry_reason,
            "exit_reason": t.exit_reason,
        })
    return rows

# ---------------------------------------------------------------------------
# Regime decomposition
# ---------------------------------------------------------------------------


def classify_regime(d1_bars: list) -> np.ndarray:
    """Classify D1 bars into regimes using EMA(200) trend + volatility.

    Returns array of labels: 'TREND_UP', 'TREND_DOWN', 'CHOP', 'HIGH_VOL'.
    """
    n = len(d1_bars)
    labels = np.array(["CHOP"] * n, dtype="U12")
    if n < 200:
        return labels

    close = np.array([b.close for b in d1_bars], dtype=np.float64)

    # EMA(200)
    alpha = 2.0 / 201
    ema = np.empty(n)
    ema[0] = close[0]
    for i in range(1, n):
        ema[i] = alpha * close[i] + (1 - alpha) * ema[i - 1]

    # 20-day realized vol
    logret = np.full(n, np.nan)
    logret[1:] = np.log(close[1:] / close[:-1])
    vol20 = np.full(n, np.nan)
    for i in range(20, n):
        vol20[i] = np.std(logret[i - 19: i + 1], ddof=1) * np.sqrt(365.25)

    # Volatility percentile (rolling 252-day)
    vol_pctl = np.full(n, np.nan)
    for i in range(252, n):
        window = vol20[i - 251: i + 1]
        window = window[~np.isnan(window)]
        if len(window) > 10:
            vol_pctl[i] = sp_stats.percentileofscore(window, vol20[i]) / 100.0

    # Classify
    for i in range(252, n):
        if np.isnan(vol_pctl[i]):
            continue
        if vol_pctl[i] > 0.80:
            labels[i] = "HIGH_VOL"
        elif close[i] > ema[i] * 1.02:
            labels[i] = "TREND_UP"
        elif close[i] < ema[i] * 0.98:
            labels[i] = "TREND_DOWN"
        else:
            labels[i] = "CHOP"

    return labels


def map_regime_to_h4(
    h4_bars: list,
    d1_bars: list,
    d1_regime: np.ndarray,
) -> np.ndarray:
    """Map D1 regime labels to H4 bar grid."""
    n_h4 = len(h4_bars)
    h4_regime = np.array(["CHOP"] * n_h4, dtype="U12")
    if not d1_bars:
        return h4_regime

    d1_ct = [b.close_time for b in d1_bars]
    d1_idx = 0
    n_d1 = len(d1_bars)
    for i in range(n_h4):
        h4_ct = h4_bars[i].close_time
        while d1_idx + 1 < n_d1 and d1_ct[d1_idx + 1] < h4_ct:
            d1_idx += 1
        if d1_ct[d1_idx] < h4_ct:
            h4_regime[i] = d1_regime[d1_idx]
    return h4_regime

# ---------------------------------------------------------------------------
# Drawdown episodes
# ---------------------------------------------------------------------------


def dd_episodes(result: Any) -> list[dict]:
    """Extract drawdown episodes from equity curve."""
    if not result.equity:
        return []

    navs = [e.nav_mid for e in result.equity]
    times = [e.close_time for e in result.equity]
    peak = navs[0]
    episodes: list[dict] = []
    current: dict | None = None

    for i, nav in enumerate(navs):
        if nav >= peak:
            if current is not None:
                current["end_ts"] = times[i]
                current["recovery_bars"] = i - current.get("_trough_idx", i)
                episodes.append(current)
                current = None
            peak = nav
        else:
            dd = (peak - nav) / peak * 100
            if current is None:
                current = {
                    "start_ts": times[i - 1] if i > 0 else times[i],
                    "peak_nav": round(peak, 2),
                    "trough_nav": round(nav, 2),
                    "depth_pct": round(dd, 2),
                    "_trough_idx": i,
                }
            elif dd > current["depth_pct"]:
                current["trough_nav"] = round(nav, 2)
                current["depth_pct"] = round(dd, 2)
                current["_trough_idx"] = i

    # Handle open drawdown at end of data
    if current is not None:
        current["end_ts"] = times[-1]
        current["recovery_bars"] = None
        episodes.append(current)

    # Clean up internal keys and sort by depth
    for ep in episodes:
        ep.pop("_trough_idx", None)

    return sorted(episodes, key=lambda x: x["depth_pct"], reverse=True)

# ---------------------------------------------------------------------------
# Yearly / monthly metrics
# ---------------------------------------------------------------------------


def period_metrics(
    result: Any,
    period_fmt: str = "%Y",
) -> list[dict]:
    """Compute metrics per time period from equity curve.

    period_fmt: strftime format, e.g. '%Y' for yearly, '%Y-%m' for monthly.
    """
    if not result.equity:
        return []

    nav_series = extract_daily_nav(result)
    if len(nav_series) < 2:
        return []

    nav_series.index = pd.to_datetime(nav_series.index)
    periods: dict[str, list[float]] = {}
    for ts, nav in nav_series.items():
        key = ts.strftime(period_fmt)
        if key not in periods:
            periods[key] = []
        periods[key].append(nav)

    rows = []
    for period_key, nav_list in sorted(periods.items()):
        if len(nav_list) < 2:
            continue
        start_nav = nav_list[0]
        end_nav = nav_list[-1]
        ret = (end_nav / start_nav - 1) * 100
        # Simple drawdown within period
        peak = nav_list[0]
        max_dd = 0.0
        for n in nav_list:
            if n > peak:
                peak = n
            dd = (peak - n) / peak * 100
            if dd > max_dd:
                max_dd = dd
        # Daily returns for Sharpe
        arr = np.array(nav_list)
        daily_r = np.diff(np.log(arr))
        sharpe = _sharpe_from_daily(daily_r) if len(daily_r) > 1 else 0.0

        rows.append({
            "period": period_key,
            "return_pct": round(ret, 2),
            "max_dd_pct": round(max_dd, 2),
            "sharpe": round(sharpe, 2),
            "start_nav": round(start_nav, 2),
            "end_nav": round(end_nav, 2),
        })

    return rows

# ---------------------------------------------------------------------------
# I/O
# ---------------------------------------------------------------------------


def save_json(path: str | Path, data: Any) -> None:
    """Save data as JSON."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w") as f:
        json.dump(data, f, indent=2, default=str)


def save_csv(path: str | Path, rows: list[dict]) -> None:
    """Save list of dicts as CSV."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        p.write_text("")
        return
    fieldnames = list(rows[0].keys())
    with open(p, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
