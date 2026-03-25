"""
AMT Research: First-Principles BTC Analysis
============================================
Goal: Find the minimal, statistically valid algorithm for BTC-USDT
that optimizes Calmar ratio (CAGR / MaxDD).

Part 1: BTC Statistical Properties
Part 2: Trend Indicator Comparison (single-param each)
Part 3: Asymmetric Entry/Exit Analysis
Part 4: Parameter Sensitivity (robustness check)
"""

import sys
import math
from pathlib import Path

import numpy as np
import pandas as pd

# ── Data loading ──────────────────────────────────────────────────────────

DATA_PATH = Path("/var/www/trading-bots/btc-spot-dev/data/bars_btcusdt_2017_now_15m.csv")

def load_h4_bars() -> pd.DataFrame:
    """Load H4 bars from multi-TF CSV."""
    csv = Path("/var/www/trading-bots/btc-spot-dev/data/bars_btcusdt_2016_now_h1_4h_1d.csv")
    df = pd.read_csv(csv)
    h4 = df[df["interval"] == "4h"].sort_values("open_time").reset_index(drop=True)
    h4["date"] = pd.to_datetime(h4["open_time"], unit="ms", utc=True)
    return h4

def load_d1_bars() -> pd.DataFrame:
    csv = Path("/var/www/trading-bots/btc-spot-dev/data/bars_btcusdt_2016_now_h1_4h_1d.csv")
    df = pd.read_csv(csv)
    d1 = df[df["interval"] == "1d"].sort_values("open_time").reset_index(drop=True)
    d1["date"] = pd.to_datetime(d1["open_time"], unit="ms", utc=True)
    return d1


# ── Indicators (vectorized) ──────────────────────────────────────────────

def ema(series: np.ndarray, period: int) -> np.ndarray:
    """Exponential moving average."""
    alpha = 2.0 / (period + 1)
    out = np.empty_like(series)
    out[0] = series[0]
    for i in range(1, len(series)):
        out[i] = alpha * series[i] + (1 - alpha) * out[i - 1]
    return out

def sma(series: np.ndarray, period: int) -> np.ndarray:
    """Simple moving average with NaN padding."""
    out = np.full_like(series, np.nan)
    cumsum = np.cumsum(series)
    out[period - 1:] = (cumsum[period - 1:] - np.concatenate([[0], cumsum[:-period]])) / period
    return out

def atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> np.ndarray:
    """Average True Range (Wilder smoothing)."""
    tr = np.maximum(high - low,
                    np.maximum(np.abs(high - np.roll(close, 1)),
                               np.abs(low - np.roll(close, 1))))
    tr[0] = high[0] - low[0]
    out = np.empty_like(tr)
    out[:period] = np.nan
    out[period - 1] = np.mean(tr[:period])
    for i in range(period, len(tr)):
        out[i] = (out[i - 1] * (period - 1) + tr[i]) / period
    return out

def hma(series: np.ndarray, period: int) -> np.ndarray:
    """Hull Moving Average."""
    half = max(1, period // 2)
    sqrt_p = max(1, int(math.sqrt(period)))
    wma_half = _wma(series, half)
    wma_full = _wma(series, period)
    diff = 2 * wma_half - wma_full
    return _wma(diff, sqrt_p)

def _wma(series: np.ndarray, period: int) -> np.ndarray:
    """Weighted moving average."""
    weights = np.arange(1, period + 1, dtype=np.float64)
    wsum = weights.sum()
    out = np.full_like(series, np.nan)
    for i in range(period - 1, len(series)):
        out[i] = np.dot(series[i - period + 1:i + 1], weights) / wsum
    return out

def donchian_high(high: np.ndarray, period: int) -> np.ndarray:
    """Rolling max of highs."""
    out = np.full_like(high, np.nan)
    for i in range(period - 1, len(high)):
        out[i] = np.max(high[i - period + 1:i + 1])
    return out

def donchian_low(low: np.ndarray, period: int) -> np.ndarray:
    """Rolling min of lows."""
    out = np.full_like(low, np.nan)
    for i in range(period - 1, len(low)):
        out[i] = np.min(low[i - period + 1:i + 1])
    return out

def roc(series: np.ndarray, period: int) -> np.ndarray:
    """Rate of Change (percent)."""
    out = np.full_like(series, np.nan)
    out[period:] = (series[period:] / series[:-period] - 1.0) * 100.0
    return out


# ── Backtest primitives ──────────────────────────────────────────────────

COST_BASE_RT_PCT = 0.31   # base round-trip cost
COST_HARSH_RT_PCT = 0.50  # harsh round-trip cost

def backtest_signal(
    close: np.ndarray,
    signal: np.ndarray,  # 1=long, 0=flat (binary)
    cost_rt_pct: float = COST_BASE_RT_PCT,
    initial_cash: float = 10000.0,
) -> dict:
    """
    Simple vectorized backtest of binary signal.
    Entry/exit at next bar's open (approximated by close for simplicity).
    Returns performance metrics.
    """
    n = len(close)
    assert len(signal) == n

    # Shift signal by 1 (execution delay: signal at close, fill at next open)
    sig = np.zeros(n)
    sig[1:] = signal[:-1]

    # Track position changes
    changes = np.diff(sig, prepend=0)
    entries = np.where(changes > 0)[0]
    exits = np.where(changes < 0)[0]

    # Equity curve
    returns = np.zeros(n)
    returns[1:] = close[1:] / close[:-1] - 1.0

    # Apply cost on position changes
    cost_per_side = cost_rt_pct / 100.0 / 2.0
    position_returns = returns * sig
    for idx in entries:
        if idx < n:
            position_returns[idx] -= cost_per_side
    for idx in exits:
        if idx < n:
            position_returns[idx] -= cost_per_side

    # Compound equity
    equity = initial_cash * np.cumprod(1.0 + position_returns)

    # Metrics
    years = (n - 1) / (6 * 365.25)  # H4 bars per year = 2191.5
    final_nav = equity[-1]
    total_return = final_nav / initial_cash - 1.0

    if years > 0.01 and final_nav > 0:
        cagr = (final_nav / initial_cash) ** (1.0 / years) - 1.0
    else:
        cagr = 0.0

    # MDD
    peak = np.maximum.accumulate(equity)
    dd = 1.0 - equity / peak
    mdd = float(dd.max())

    # Calmar
    calmar = (cagr / mdd) if mdd > 1e-6 else 0.0

    # Sharpe (annualized from H4)
    ret_4h = position_returns[sig > 0] if sig.sum() > 0 else position_returns
    if len(ret_4h) > 1 and np.std(ret_4h) > 1e-12:
        sharpe = (np.mean(ret_4h) / np.std(ret_4h)) * math.sqrt(6.0 * 365.25)
    else:
        sharpe = 0.0

    # Trade count
    n_trades = len(entries)

    # Win rate
    trade_pnls = []
    for i, entry_idx in enumerate(entries):
        if i < len(exits):
            exit_idx = exits[i]
            pnl = close[exit_idx] / close[entry_idx] - 1.0 - cost_rt_pct / 100.0
            trade_pnls.append(pnl)

    wins = sum(1 for p in trade_pnls if p > 0)
    win_rate = wins / len(trade_pnls) * 100 if trade_pnls else 0

    # Time in market
    time_in_market = np.mean(sig) * 100

    return {
        "cagr": cagr * 100,
        "mdd": mdd * 100,
        "calmar": calmar,
        "sharpe": sharpe,
        "trades": n_trades,
        "win_rate": win_rate,
        "time_in_mkt": time_in_market,
        "total_return": total_return * 100,
        "final_nav": final_nav,
        "equity": equity,
        "dd": dd,
    }


# ══════════════════════════════════════════════════════════════════════════
# PART 1: BTC Statistical Properties
# ══════════════════════════════════════════════════════════════════════════

def part1_btc_properties(h4: pd.DataFrame, d1: pd.DataFrame):
    print("=" * 80)
    print("PART 1: BTC STATISTICAL PROPERTIES")
    print("=" * 80)

    close_h4 = h4["close"].values
    close_d1 = d1["close"].values

    # Filter to 2019+ for trading period
    mask = h4["date"] >= "2019-01-01"
    close_trading = h4.loc[mask, "close"].values
    n_bars = len(close_trading)
    n_years = (n_bars - 1) / (6 * 365.25)

    print(f"\nTrading period: 2019-01-01 to {h4['date'].iloc[-1].strftime('%Y-%m-%d')}")
    print(f"H4 bars: {n_bars:,} ({n_years:.1f} years)")
    print(f"Price range: ${close_trading[0]:,.0f} → ${close_trading[-1]:,.0f}")

    # Return distribution
    ret_h4 = np.diff(close_trading) / close_trading[:-1]
    ret_d1_trading = np.diff(close_d1[close_d1.shape[0] - int(n_years * 365):]) / close_d1[close_d1.shape[0] - int(n_years * 365):-1] if len(close_d1) > int(n_years * 365) else np.diff(close_d1) / close_d1[:-1]

    print(f"\n--- H4 Return Distribution ---")
    print(f"  Mean:     {np.mean(ret_h4)*100:.4f}%")
    print(f"  Std:      {np.std(ret_h4)*100:.4f}%")
    print(f"  Skewness: {_skewness(ret_h4):.3f}")
    print(f"  Kurtosis: {_kurtosis(ret_h4):.3f} (normal=3)")
    print(f"  Min:      {np.min(ret_h4)*100:.2f}%")
    print(f"  Max:      {np.max(ret_h4)*100:.2f}%")
    print(f"  Ann. Vol: {np.std(ret_h4)*math.sqrt(6.0 * 365.25)*100:.1f}%")

    # Autocorrelation (key for trend-following)
    print(f"\n--- Autocorrelation of H4 Returns ---")
    print(f"  (Positive autocorrelation = trend persistence)")
    for lag in [1, 2, 3, 6, 12, 24, 48]:
        ac = np.corrcoef(ret_h4[:-lag], ret_h4[lag:])[0, 1]
        bars_desc = f"{lag*4}h" if lag <= 6 else f"{lag*4/24:.0f}d"
        sig = "***" if abs(ac) > 2/math.sqrt(len(ret_h4)) else ""
        print(f"  Lag {lag:3d} ({bars_desc:>4s}): {ac:+.4f} {sig}")

    # Autocorrelation of ABSOLUTE returns (volatility clustering)
    abs_ret = np.abs(ret_h4)
    print(f"\n--- Autocorrelation of |Returns| (Volatility Clustering) ---")
    for lag in [1, 6, 24, 48, 96]:
        ac = np.corrcoef(abs_ret[:-lag], abs_ret[lag:])[0, 1]
        bars_desc = f"{lag*4}h" if lag <= 6 else f"{lag*4/24:.0f}d"
        print(f"  Lag {lag:3d} ({bars_desc:>4s}): {ac:+.4f}")

    # Major drawdown episodes
    print(f"\n--- Major Drawdown Episodes (>20%) ---")
    equity = np.cumprod(1.0 + ret_h4) * 10000
    peak = np.maximum.accumulate(equity)
    dd = 1.0 - equity / peak

    in_dd = False
    dd_start = 0
    episodes = []
    for i in range(len(dd)):
        if dd[i] > 0.20 and not in_dd:
            in_dd = True
            dd_start = i
        elif dd[i] < 0.05 and in_dd:
            max_dd_in_episode = np.max(dd[dd_start:i])
            duration_days = (i - dd_start) * 4 / 24
            episodes.append((dd_start, i, max_dd_in_episode, duration_days))
            in_dd = False

    if in_dd:  # still in DD
        max_dd_in_episode = np.max(dd[dd_start:])
        duration_days = (len(dd) - dd_start) * 4 / 24
        episodes.append((dd_start, len(dd)-1, max_dd_in_episode, duration_days))

    print(f"  Total episodes: {len(episodes)}")
    for idx, (s, e, mdd_ep, dur) in enumerate(episodes):
        date_s = h4.loc[mask].iloc[s]["date"].strftime("%Y-%m-%d") if s < len(h4.loc[mask]) else "?"
        print(f"  #{idx+1}: {date_s}, MDD={mdd_ep*100:.1f}%, Duration={dur:.0f} days")

    # Regime analysis (simple: above/below 200-bar EMA)
    ema200 = ema(close_trading, 200)
    above = close_trading > ema200
    print(f"\n--- Simple Regime Analysis (Price vs EMA200) ---")
    print(f"  Above EMA200: {np.mean(above)*100:.1f}% of time")
    print(f"  Below EMA200: {(1-np.mean(above))*100:.1f}% of time")

    # Returns in each regime
    ret_above = ret_h4[1:][above[:-2]] if len(above) > 2 else ret_h4
    ret_below = ret_h4[1:][~above[:-2]] if len(above) > 2 else ret_h4
    print(f"  Return when ABOVE: {np.mean(ret_above)*(6*365.25)*100:.1f}% annualized")
    print(f"  Return when BELOW: {np.mean(ret_below)*(6*365.25)*100:.1f}% annualized")
    print(f"  Vol when ABOVE:    {np.std(ret_above)*math.sqrt(6.0 * 365.25)*100:.1f}% annualized")
    print(f"  Vol when BELOW:    {np.std(ret_below)*math.sqrt(6.0 * 365.25)*100:.1f}% annualized")

    # Crash speed analysis
    print(f"\n--- Crash Speed Analysis ---")
    print(f"  (How fast do major drawdowns develop?)")
    for ep_idx, (s, e, mdd_ep, dur) in enumerate(episodes):
        # Time from start to 50% of max DD
        dd_slice = dd[s:e+1]
        half_dd = mdd_ep * 0.5
        half_idx = np.argmax(dd_slice > half_dd)
        half_days = half_idx * 4 / 24
        print(f"  Episode #{ep_idx+1}: 50% of max DD reached in {half_days:.1f} days (total: {dur:.0f} days)")

    return episodes


def _skewness(x):
    n = len(x)
    mu = np.mean(x)
    sigma = np.std(x)
    if sigma < 1e-12:
        return 0.0
    return np.mean(((x - mu) / sigma) ** 3)

def _kurtosis(x):
    n = len(x)
    mu = np.mean(x)
    sigma = np.std(x)
    if sigma < 1e-12:
        return 0.0
    return np.mean(((x - mu) / sigma) ** 4)


# ══════════════════════════════════════════════════════════════════════════
# PART 2: Trend Indicator Comparison
# ══════════════════════════════════════════════════════════════════════════

def part2_indicator_comparison(h4: pd.DataFrame):
    print("\n" + "=" * 80)
    print("PART 2: TREND INDICATOR COMPARISON (1-param each)")
    print("=" * 80)

    mask = h4["date"] >= "2019-01-01"
    data = h4[mask].reset_index(drop=True)
    close = data["close"].values
    high = data["high"].values
    low = data["low"].values
    n = len(close)

    # Skip first 200 bars for warmup
    warmup = 200

    results = []

    # --- A. EMA Crossover (parameter: slow period, fast = slow//4) ---
    print(f"\n--- A. EMA Crossover (fast=slow//4) ---")
    for slow_p in [40, 60, 80, 100, 120, 150, 200]:
        fast_p = max(5, slow_p // 4)
        ema_f = ema(close, fast_p)
        ema_s = ema(close, slow_p)
        sig = np.zeros(n)
        sig[warmup:] = (ema_f[warmup:] > ema_s[warmup:]).astype(float)
        r = backtest_signal(close, sig)
        results.append({
            "method": f"EMA({fast_p}/{slow_p})",
            "params": 1,  # slow_p determines fast_p
            **{k: v for k, v in r.items() if k not in ("equity", "dd")}
        })
        print(f"  EMA({fast_p:3d}/{slow_p:3d}): CAGR={r['cagr']:6.1f}%  MDD={r['mdd']:5.1f}%  "
              f"Calmar={r['calmar']:5.2f}  Sharpe={r['sharpe']:5.2f}  Trades={r['trades']:3d}  "
              f"WR={r['win_rate']:4.1f}%  InMkt={r['time_in_mkt']:4.1f}%")

    # --- B. SMA Crossover ---
    print(f"\n--- B. SMA Crossover (fast=slow//4) ---")
    for slow_p in [40, 60, 80, 100, 120, 150, 200]:
        fast_p = max(5, slow_p // 4)
        sma_f = sma(close, fast_p)
        sma_s = sma(close, slow_p)
        sig = np.zeros(n)
        valid = ~(np.isnan(sma_f) | np.isnan(sma_s))
        sig[valid & (np.arange(n) >= warmup)] = (sma_f[valid & (np.arange(n) >= warmup)] > sma_s[valid & (np.arange(n) >= warmup)]).astype(float)
        r = backtest_signal(close, sig)
        results.append({
            "method": f"SMA({fast_p}/{slow_p})",
            "params": 1,
            **{k: v for k, v in r.items() if k not in ("equity", "dd")}
        })
        print(f"  SMA({fast_p:3d}/{slow_p:3d}): CAGR={r['cagr']:6.1f}%  MDD={r['mdd']:5.1f}%  "
              f"Calmar={r['calmar']:5.2f}  Sharpe={r['sharpe']:5.2f}  Trades={r['trades']:3d}  "
              f"WR={r['win_rate']:4.1f}%  InMkt={r['time_in_mkt']:4.1f}%")

    # --- C. HMA Direction ---
    print(f"\n--- C. HMA Direction (period) ---")
    for p in [30, 45, 55, 70, 90, 120]:
        h = hma(close, p)
        sig = np.zeros(n)
        for i in range(warmup + 1, n):
            if not np.isnan(h[i]) and not np.isnan(h[i-1]):
                sig[i] = 1.0 if h[i] > h[i-1] else 0.0
        r = backtest_signal(close, sig)
        results.append({
            "method": f"HMA({p})",
            "params": 1,
            **{k: v for k, v in r.items() if k not in ("equity", "dd")}
        })
        print(f"  HMA({p:3d}):       CAGR={r['cagr']:6.1f}%  MDD={r['mdd']:5.1f}%  "
              f"Calmar={r['calmar']:5.2f}  Sharpe={r['sharpe']:5.2f}  Trades={r['trades']:3d}  "
              f"WR={r['win_rate']:4.1f}%  InMkt={r['time_in_mkt']:4.1f}%")

    # --- D. Donchian Breakout ---
    print(f"\n--- D. Donchian Breakout (period) ---")
    for p in [20, 40, 60, 80, 100, 120]:
        dh = donchian_high(high, p)
        dl = donchian_low(low, p)
        sig = np.zeros(n)
        in_pos = False
        for i in range(warmup, n):
            if np.isnan(dh[i-1]) or np.isnan(dl[i-1]):
                continue
            if not in_pos and close[i] > dh[i-1]:
                in_pos = True
            elif in_pos and close[i] < dl[i-1]:
                in_pos = False
            sig[i] = 1.0 if in_pos else 0.0
        r = backtest_signal(close, sig)
        results.append({
            "method": f"Donchian({p})",
            "params": 1,
            **{k: v for k, v in r.items() if k not in ("equity", "dd")}
        })
        print(f"  Donch({p:3d}):     CAGR={r['cagr']:6.1f}%  MDD={r['mdd']:5.1f}%  "
              f"Calmar={r['calmar']:5.2f}  Sharpe={r['sharpe']:5.2f}  Trades={r['trades']:3d}  "
              f"WR={r['win_rate']:4.1f}%  InMkt={r['time_in_mkt']:4.1f}%")

    # --- E. Simple Momentum (ROC) ---
    print(f"\n--- E. ROC Momentum (period) ---")
    for p in [20, 40, 60, 80, 100, 120]:
        r_val = roc(close, p)
        sig = np.zeros(n)
        for i in range(warmup, n):
            if not np.isnan(r_val[i]):
                sig[i] = 1.0 if r_val[i] > 0 else 0.0
        r = backtest_signal(close, sig)
        results.append({
            "method": f"ROC({p})",
            "params": 1,
            **{k: v for k, v in r.items() if k not in ("equity", "dd")}
        })
        print(f"  ROC({p:3d}):       CAGR={r['cagr']:6.1f}%  MDD={r['mdd']:5.1f}%  "
              f"Calmar={r['calmar']:5.2f}  Sharpe={r['sharpe']:5.2f}  Trades={r['trades']:3d}  "
              f"WR={r['win_rate']:4.1f}%  InMkt={r['time_in_mkt']:4.1f}%")

    # --- F. Price vs Single EMA ---
    print(f"\n--- F. Price > EMA (period) ---")
    for p in [50, 80, 100, 150, 200]:
        ema_val = ema(close, p)
        sig = np.zeros(n)
        sig[warmup:] = (close[warmup:] > ema_val[warmup:]).astype(float)
        r = backtest_signal(close, sig)
        results.append({
            "method": f"Price>EMA({p})",
            "params": 1,
            **{k: v for k, v in r.items() if k not in ("equity", "dd")}
        })
        print(f"  Price>EMA({p:3d}): CAGR={r['cagr']:6.1f}%  MDD={r['mdd']:5.1f}%  "
              f"Calmar={r['calmar']:5.2f}  Sharpe={r['sharpe']:5.2f}  Trades={r['trades']:3d}  "
              f"WR={r['win_rate']:4.1f}%  InMkt={r['time_in_mkt']:4.1f}%")

    # Buy & Hold baseline
    sig_bh = np.ones(n)
    sig_bh[:warmup] = 0
    r_bh = backtest_signal(close, sig_bh, cost_rt_pct=0)
    print(f"\n  Buy&Hold:        CAGR={r_bh['cagr']:6.1f}%  MDD={r_bh['mdd']:5.1f}%  "
          f"Calmar={r_bh['calmar']:5.2f}  Sharpe={r_bh['sharpe']:5.2f}  InMkt=100.0%")

    # Summary: top 10 by Calmar
    print(f"\n--- TOP 10 by Calmar Ratio (base cost) ---")
    results_sorted = sorted(results, key=lambda x: x["calmar"], reverse=True)
    for i, r in enumerate(results_sorted[:10]):
        print(f"  #{i+1:2d} {r['method']:20s}: Calmar={r['calmar']:5.2f}  "
              f"CAGR={r['cagr']:6.1f}%  MDD={r['mdd']:5.1f}%  Trades={r['trades']:3d}")

    return results


# ══════════════════════════════════════════════════════════════════════════
# PART 3: Asymmetric Entry/Exit Analysis
# ══════════════════════════════════════════════════════════════════════════

def part3_asymmetric_analysis(h4: pd.DataFrame):
    print("\n" + "=" * 80)
    print("PART 3: ASYMMETRIC ENTRY/EXIT ANALYSIS")
    print("=" * 80)
    print("(Slow entry = reduce whipsaw, Fast exit = cut losses)")

    mask = h4["date"] >= "2019-01-01"
    data = h4[mask].reset_index(drop=True)
    close = data["close"].values
    high = data["high"].values
    low = data["low"].values
    n = len(close)
    warmup = 200

    results = []

    # Test: EMA crossover entry, trailing stop exit
    print(f"\n--- A. EMA Entry + Trailing Stop Exit ---")
    print(f"  (Entry: fast EMA > slow EMA; Exit: close < peak - mult*ATR)")

    atr14 = atr(high, low, close, 14)

    for slow_p in [60, 80, 100, 120]:
        fast_p = max(5, slow_p // 4)
        ema_f = ema(close, fast_p)
        ema_s = ema(close, slow_p)

        for trail_mult in [2.0, 2.5, 3.0, 3.5, 4.0]:
            sig = np.zeros(n)
            in_pos = False
            peak_price = 0.0

            for i in range(warmup, n):
                if np.isnan(atr14[i]):
                    continue
                if not in_pos:
                    if ema_f[i] > ema_s[i]:
                        in_pos = True
                        peak_price = close[i]
                        sig[i] = 1.0
                else:
                    peak_price = max(peak_price, close[i])
                    trail_stop = peak_price - trail_mult * atr14[i]

                    # Exit: trailing stop OR trend reversal
                    if close[i] < trail_stop or ema_f[i] < ema_s[i]:
                        in_pos = False
                        sig[i] = 0.0
                    else:
                        sig[i] = 1.0

            r = backtest_signal(close, sig)
            label = f"EMA({fast_p}/{slow_p})+Trail({trail_mult})"
            results.append({
                "method": label,
                "entry_slow": slow_p,
                "trail_mult": trail_mult,
                "params": 2,  # slow_p + trail_mult
                **{k: v for k, v in r.items() if k not in ("equity", "dd")}
            })

    # Print top results
    results_sorted = sorted(results, key=lambda x: x["calmar"], reverse=True)
    print(f"\n  TOP 15 Asymmetric combinations by Calmar:")
    for i, r in enumerate(results_sorted[:15]):
        print(f"  #{i+1:2d} {r['method']:30s}: Calmar={r['calmar']:5.2f}  "
              f"CAGR={r['cagr']:6.1f}%  MDD={r['mdd']:5.1f}%  "
              f"Trades={r['trades']:3d}  WR={r['win_rate']:4.1f}%")

    # --- B. EMA Entry + ATR Trailing (exit only, no trend reversal exit) ---
    print(f"\n--- B. EMA Entry + ONLY Trailing Stop Exit (no trend exit) ---")
    results_b = []

    for slow_p in [60, 80, 100, 120]:
        fast_p = max(5, slow_p // 4)
        ema_f = ema(close, fast_p)
        ema_s = ema(close, slow_p)

        for trail_mult in [2.0, 2.5, 3.0, 3.5, 4.0, 5.0]:
            sig = np.zeros(n)
            in_pos = False
            peak_price = 0.0

            for i in range(warmup, n):
                if np.isnan(atr14[i]):
                    continue
                if not in_pos:
                    if ema_f[i] > ema_s[i]:
                        in_pos = True
                        peak_price = close[i]
                        sig[i] = 1.0
                else:
                    peak_price = max(peak_price, close[i])
                    trail_stop = peak_price - trail_mult * atr14[i]

                    if close[i] < trail_stop:
                        in_pos = False
                        sig[i] = 0.0
                    else:
                        sig[i] = 1.0

            r = backtest_signal(close, sig)
            label = f"EMA({fast_p}/{slow_p})+OnlyTrail({trail_mult})"
            results_b.append({
                "method": label,
                **{k: v for k, v in r.items() if k not in ("equity", "dd")}
            })

    results_b_sorted = sorted(results_b, key=lambda x: x["calmar"], reverse=True)
    print(f"\n  TOP 10 by Calmar (trail-only exit):")
    for i, r in enumerate(results_b_sorted[:10]):
        print(f"  #{i+1:2d} {r['method']:35s}: Calmar={r['calmar']:5.2f}  "
              f"CAGR={r['cagr']:6.1f}%  MDD={r['mdd']:5.1f}%  "
              f"Trades={r['trades']:3d}  WR={r['win_rate']:4.1f}%")

    # --- C. Hybrid: Fast exit = min(trail, trend_reversal) ---
    print(f"\n--- C. Asymmetric: Slow Entry EMA + Fast Exit (separate periods) ---")
    results_c = []

    for entry_slow in [80, 100, 120]:
        entry_fast = entry_slow // 4
        ema_entry_f = ema(close, entry_fast)
        ema_entry_s = ema(close, entry_slow)

        for exit_fast in [10, 15, 20, 30]:
            exit_slow = exit_fast * 3
            ema_exit_f = ema(close, exit_fast)
            ema_exit_s = ema(close, exit_slow)

            sig = np.zeros(n)
            in_pos = False

            for i in range(warmup, n):
                if not in_pos:
                    if ema_entry_f[i] > ema_entry_s[i]:
                        in_pos = True
                        sig[i] = 1.0
                else:
                    if ema_exit_f[i] < ema_exit_s[i]:
                        in_pos = False
                        sig[i] = 0.0
                    else:
                        sig[i] = 1.0

            r = backtest_signal(close, sig)
            label = f"Entry({entry_fast}/{entry_slow})+Exit({exit_fast}/{exit_slow})"
            results_c.append({
                "method": label,
                **{k: v for k, v in r.items() if k not in ("equity", "dd")}
            })

    results_c_sorted = sorted(results_c, key=lambda x: x["calmar"], reverse=True)
    print(f"\n  TOP 10 by Calmar (asymmetric EMA entry/exit):")
    for i, r in enumerate(results_c_sorted[:10]):
        print(f"  #{i+1:2d} {r['method']:40s}: Calmar={r['calmar']:5.2f}  "
              f"CAGR={r['cagr']:6.1f}%  MDD={r['mdd']:5.1f}%  "
              f"Trades={r['trades']:3d}  WR={r['win_rate']:4.1f}%")

    return results_sorted[:5]


# ══════════════════════════════════════════════════════════════════════════
# PART 4: Robustness Check (Parameter Sensitivity)
# ══════════════════════════════════════════════════════════════════════════

def part4_robustness(h4: pd.DataFrame, top_methods: list):
    print("\n" + "=" * 80)
    print("PART 4: ROBUSTNESS CHECK")
    print("=" * 80)
    print("Testing: if we perturb parameters ±20%, does Calmar stay positive?")

    mask = h4["date"] >= "2019-01-01"
    data = h4[mask].reset_index(drop=True)
    close = data["close"].values
    high = data["high"].values
    low = data["low"].values
    n = len(close)
    warmup = 200
    atr14 = atr(high, low, close, 14)

    # Test the best EMA+Trail combination with perturbations
    best = top_methods[0] if top_methods else {"entry_slow": 80, "trail_mult": 3.0}
    base_slow = best.get("entry_slow", 80)
    base_trail = best.get("trail_mult", 3.0)

    print(f"\n  Base config: EMA(slow={base_slow}) + Trail(mult={base_trail})")
    print(f"\n  Perturbation grid (±30%):")

    grid_results = []
    for slow_pct in [-30, -20, -10, 0, 10, 20, 30]:
        for trail_pct in [-30, -20, -10, 0, 10, 20, 30]:
            slow_p = max(20, int(base_slow * (1 + slow_pct/100)))
            fast_p = max(5, slow_p // 4)
            trail_m = base_trail * (1 + trail_pct/100)

            ema_f = ema(close, fast_p)
            ema_s = ema(close, slow_p)

            sig = np.zeros(n)
            in_pos = False
            peak_price = 0.0
            for i in range(warmup, n):
                if np.isnan(atr14[i]):
                    continue
                if not in_pos:
                    if ema_f[i] > ema_s[i]:
                        in_pos = True
                        peak_price = close[i]
                        sig[i] = 1.0
                else:
                    peak_price = max(peak_price, close[i])
                    trail_stop = peak_price - trail_m * atr14[i]
                    if close[i] < trail_stop or ema_f[i] < ema_s[i]:
                        in_pos = False
                        sig[i] = 0.0
                    else:
                        sig[i] = 1.0

            r = backtest_signal(close, sig)
            grid_results.append({
                "slow_pct": slow_pct,
                "trail_pct": trail_pct,
                "slow_p": slow_p,
                "trail_m": trail_m,
                "calmar": r["calmar"],
                "cagr": r["cagr"],
                "mdd": r["mdd"],
                "sharpe": r["sharpe"],
            })

    # Print heatmap-style
    print(f"\n  Calmar Ratio Heatmap (row=slow_pct, col=trail_pct):")
    print(f"  {'':>8s}", end="")
    for tp in [-30, -20, -10, 0, 10, 20, 30]:
        print(f"  t{tp:+d}%", end="")
    print()

    for sp in [-30, -20, -10, 0, 10, 20, 30]:
        print(f"  s{sp:+d}%  ", end="")
        for tp in [-30, -20, -10, 0, 10, 20, 30]:
            match = [r for r in grid_results if r["slow_pct"] == sp and r["trail_pct"] == tp]
            if match:
                cal = match[0]["calmar"]
                print(f"  {cal:5.2f}", end="")
        print()

    # Robustness score
    all_calmars = [r["calmar"] for r in grid_results]
    positive = sum(1 for c in all_calmars if c > 0.5)
    total = len(all_calmars)
    print(f"\n  Robustness: {positive}/{total} ({positive/total*100:.0f}%) configs have Calmar > 0.5")
    print(f"  Mean Calmar: {np.mean(all_calmars):.2f}")
    print(f"  Min Calmar:  {np.min(all_calmars):.2f}")
    print(f"  Std Calmar:  {np.std(all_calmars):.2f}")

    # Also test with harsh costs
    print(f"\n--- Harsh Cost Scenario ---")
    for sp in [0]:
        for tp in [0]:
            slow_p = max(20, int(base_slow * (1 + sp/100)))
            fast_p = max(5, slow_p // 4)
            trail_m = base_trail * (1 + tp/100)
            ema_f = ema(close, fast_p)
            ema_s = ema(close, slow_p)
            sig = np.zeros(n)
            in_pos = False
            peak_price = 0.0
            for i in range(warmup, n):
                if np.isnan(atr14[i]):
                    continue
                if not in_pos:
                    if ema_f[i] > ema_s[i]:
                        in_pos = True
                        peak_price = close[i]
                        sig[i] = 1.0
                else:
                    peak_price = max(peak_price, close[i])
                    trail_stop = peak_price - trail_m * atr14[i]
                    if close[i] < trail_stop or ema_f[i] < ema_s[i]:
                        in_pos = False
                        sig[i] = 0.0
                    else:
                        sig[i] = 1.0
            for cost_name, cost_pct in [("smart", 0.13), ("base", 0.31), ("harsh", 0.50)]:
                r = backtest_signal(close, sig, cost_rt_pct=cost_pct)
                print(f"  {cost_name:>6s}: CAGR={r['cagr']:6.1f}%  MDD={r['mdd']:5.1f}%  "
                      f"Calmar={r['calmar']:5.2f}  Sharpe={r['sharpe']:5.2f}  Trades={r['trades']}")

    return grid_results


# ══════════════════════════════════════════════════════════════════════════
# PART 5: Walk-Forward Validation (Out-of-Sample)
# ══════════════════════════════════════════════════════════════════════════

def part5_walk_forward(h4: pd.DataFrame, slow_period=80, trail_mult=3.0):
    print("\n" + "=" * 80)
    print("PART 5: WALK-FORWARD OUT-OF-SAMPLE TEST")
    print("=" * 80)
    print(f"  Config: EMA(slow={slow_period}) + Trail({trail_mult})")
    print(f"  Windows: 2-year train, 6-month test, sliding")

    mask = h4["date"] >= "2019-01-01"
    data = h4[mask].reset_index(drop=True)
    close = data["close"].values
    high = data["high"].values
    low = data["low"].values
    dates = data["date"].values
    n = len(close)

    # Generate windows
    bars_per_month = int(6 * 30.44)  # ~183 H4 bars per month
    train_bars = 24 * bars_per_month
    test_bars = 6 * bars_per_month
    slide_bars = 6 * bars_per_month

    windows = []
    start = 0
    while start + train_bars + test_bars <= n:
        windows.append({
            "train_start": start,
            "train_end": start + train_bars,
            "test_start": start + train_bars,
            "test_end": min(start + train_bars + test_bars, n),
        })
        start += slide_bars

    print(f"  Generated {len(windows)} walk-forward windows")

    atr14 = atr(high, low, close, 14)

    oos_results = []
    for wi, w in enumerate(windows):
        ts, te = w["test_start"], w["test_end"]
        test_close = close[ts:te]
        test_high = high[ts:te]
        test_low = low[ts:te]
        test_atr = atr14[ts:te]
        nt = len(test_close)

        fast_p = max(5, slow_period // 4)

        # Need warmup for EMAs - use last 200 bars of train
        warmup_start = max(0, ts - 200)
        full_close = close[warmup_start:te]
        full_atr = atr14[warmup_start:te]

        ema_f = ema(full_close, fast_p)
        ema_s = ema(full_close, slow_period)
        offset = ts - warmup_start

        sig = np.zeros(nt)
        in_pos = False
        peak_price = 0.0
        for i in range(nt):
            fi = offset + i
            if fi >= len(ema_f) or np.isnan(full_atr[fi]):
                continue
            if not in_pos:
                if ema_f[fi] > ema_s[fi]:
                    in_pos = True
                    peak_price = test_close[i]
                    sig[i] = 1.0
            else:
                peak_price = max(peak_price, test_close[i])
                trail_stop = peak_price - trail_mult * full_atr[fi]
                if test_close[i] < trail_stop or ema_f[fi] < ema_s[fi]:
                    in_pos = False
                    sig[i] = 0.0
                else:
                    sig[i] = 1.0

        r = backtest_signal(test_close, sig)

        # BH baseline
        sig_bh = np.ones(nt)
        r_bh = backtest_signal(test_close, sig_bh, cost_rt_pct=0)

        date_start = pd.Timestamp(dates[ts]).strftime("%Y-%m-%d")
        date_end = pd.Timestamp(dates[min(te-1, n-1)]).strftime("%Y-%m-%d")

        oos_results.append({
            "window": wi + 1,
            "period": f"{date_start} → {date_end}",
            "cagr": r["cagr"],
            "mdd": r["mdd"],
            "calmar": r["calmar"],
            "sharpe": r["sharpe"],
            "trades": r["trades"],
            "bh_cagr": r_bh["cagr"],
            "bh_mdd": r_bh["mdd"],
            "delta_calmar": r["calmar"] - (r_bh["cagr"] / r_bh["mdd"] if r_bh["mdd"] > 0 else 0),
        })

        print(f"  W{wi+1:2d} [{date_start}→{date_end}]: "
              f"CAGR={r['cagr']:+6.1f}%  MDD={r['mdd']:5.1f}%  Calmar={r['calmar']:+5.2f}  "
              f"vs BH: CAGR={r_bh['cagr']:+6.1f}%  MDD={r_bh['mdd']:5.1f}%")

    # Summary
    print(f"\n  --- WFO Summary ---")
    calmars = [r["calmar"] for r in oos_results]
    pos_windows = sum(1 for c in calmars if c > 0)
    print(f"  Positive Calmar windows: {pos_windows}/{len(windows)} ({pos_windows/len(windows)*100:.0f}%)")
    print(f"  Mean OOS Calmar: {np.mean(calmars):.2f}")
    print(f"  Min OOS Calmar:  {np.min(calmars):.2f}")
    print(f"  Max OOS Calmar:  {np.max(calmars):.2f}")

    return oos_results


# ══════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════

def main():
    print("Loading data...")
    h4 = load_h4_bars()
    d1 = load_d1_bars()
    print(f"H4 bars: {len(h4):,}, D1 bars: {len(d1):,}")
    print(f"Date range: {h4['date'].iloc[0]} → {h4['date'].iloc[-1]}")

    # Part 1: BTC properties
    episodes = part1_btc_properties(h4, d1)

    # Part 2: Indicator comparison
    indicator_results = part2_indicator_comparison(h4)

    # Part 3: Asymmetric analysis
    top_asymmetric = part3_asymmetric_analysis(h4)

    # Part 4: Robustness
    grid = part4_robustness(h4, top_asymmetric)

    # Part 5: Walk-forward
    # Use the best base config from Part 3
    best = top_asymmetric[0] if top_asymmetric else {}
    slow_p = best.get("entry_slow", 80)
    trail_m = best.get("trail_mult", 3.0)
    wfo = part5_walk_forward(h4, slow_period=slow_p, trail_mult=trail_m)

    print("\n" + "=" * 80)
    print("RESEARCH COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
