"""
Phase 3 — Signal Landscape EDA
X28 Research: Full entry x exit x filter sweep.
Measure IMPACT on Sharpe. Do NOT pick winners. Report everything.
"""

import os, json, time, warnings
import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.api as sm
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from collections import OrderedDict
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=RuntimeWarning)

t0 = time.time()

# ── Paths ─────────────────────────────────────────────────────────────
BASE = "/var/www/trading-bots/btc-spot-dev/research/x28"
DATA = "/var/www/trading-bots/btc-spot-dev/data"
FIG_DIR = os.path.join(BASE, "figures")
TBL_DIR = os.path.join(BASE, "tables")
CODE_DIR = os.path.join(BASE, "code")
os.makedirs(FIG_DIR, exist_ok=True)
os.makedirs(TBL_DIR, exist_ok=True)

ANN = 365.25 * 6   # H4 bars per year
COST_BPS = 50
COST_FRAC = COST_BPS / 10_000
HALF_COST = COST_FRAC / 2
DETECTION_WINDOW = 20   # bars after trend start to count as "detected"

# ── Data loading ──────────────────────────────────────────────────────
def load_tf(tf):
    fp = os.path.join(DATA, f"btcusdt_{tf}.csv")
    df = pd.read_csv(fp)
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
    df = df.sort_values("open_time").reset_index(drop=True)
    return df

print("Loading data...")
h4 = load_tf("4h")
d1 = load_tf("1d")
print(f"  H4: {len(h4)} bars, D1: {len(d1)} bars")

h4["log_ret"] = np.log(h4["close"] / h4["close"].shift(1))
closes = h4["close"].values.astype(float)
highs  = h4["high"].values.astype(float)
lows   = h4["low"].values.astype(float)
log_rets = h4["log_ret"].values.astype(float)
n_bars = len(closes)
n_years = n_bars / ANN

# ── Indicator helpers ─────────────────────────────────────────────────
def _ema(arr, span):
    s = pd.Series(arr)
    return s.ewm(span=span, adjust=False).mean().values

def _sma(arr, period):
    s = pd.Series(arr)
    return s.rolling(period, min_periods=period).mean().values

def _atr(hi, lo, cl, period):
    tr = np.empty(len(cl))
    tr[0] = hi[0] - lo[0]
    tr[1:] = np.maximum(hi[1:] - lo[1:],
              np.maximum(np.abs(hi[1:] - cl[:-1]),
                         np.abs(lo[1:] - cl[:-1])))
    return pd.Series(tr).ewm(span=period, adjust=False).mean().values

def _rolling_max(arr, period):
    return pd.Series(arr).rolling(period, min_periods=period).max().values

def _rolling_min(arr, period):
    return pd.Series(arr).rolling(period, min_periods=period).min().values

def _rolling_std(arr, period):
    return pd.Series(arr).rolling(period, min_periods=period).std().values

# ── Precompute indicators ────────────────────────────────────────────
print("Computing indicators...")
ema_cache = {}
for p in [1, 5, 10, 15, 20, 30, 40, 50, 60, 80, 90, 100, 120, 144]:
    ema_cache[p] = _ema(closes, p) if p > 1 else closes.copy()

atr_14 = _atr(highs, lows, closes, 14)
atr_20 = _atr(highs, lows, closes, 20)

sma_20 = _sma(closes, 20)
sma_40 = _sma(closes, 40)

roc_cache = {}
for p in [10, 20, 40]:
    shifted = pd.Series(closes).shift(p).values
    roc_cache[p] = np.where(shifted > 0, (closes / shifted - 1) * 100, 0.0)

vol_short = _rolling_std(log_rets, 10)
vol_long  = _rolling_std(log_rets, 60)

# VDO (Volume Deviation Oscillator)
vol_ma20 = _sma(h4["volume"].values.astype(float), 20)
vdo = np.where(vol_ma20 > 0, h4["volume"].values / vol_ma20 - 1, 0.0)

# D1 regime → H4 (1-day lag)
d1["ema21"]  = _ema(d1["close"].values, 21)
d1["ema50"]  = _ema(d1["close"].values, 50)
d1["sma200"] = _sma(d1["close"].values, 200)
for col, ref in [("regime_ema21","ema21"), ("regime_ema50","ema50"), ("regime_sma200","sma200")]:
    d1[col] = (d1["close"] > d1[ref]).astype(int)

d1_for_merge = d1[["open_time","regime_ema21","regime_ema50","regime_sma200"]].copy()
d1_for_merge["merge_time"] = d1_for_merge["open_time"] + pd.Timedelta(days=1)
h4_sorted = h4[["open_time"]].copy()
# Align datetime precision
h4_sorted["open_time"] = h4_sorted["open_time"].astype("datetime64[us]")
d1_for_merge["merge_time"] = d1_for_merge["merge_time"].astype("datetime64[us]")
merged = pd.merge_asof(h4_sorted, d1_for_merge[["merge_time","regime_ema21","regime_ema50","regime_sma200"]],
                        left_on="open_time", right_on="merge_time", direction="backward")
d1_regime_ema21 = merged["regime_ema21"].fillna(0).astype(int).values
d1_regime_ema50 = merged["regime_ema50"].fillna(0).astype(int).values
d1_regime_sma200 = merged["regime_sma200"].fillna(0).astype(int).values

print(f"  Indicators computed. D1 regime mapped ({d1_regime_ema21.sum()} bars above EMA21)")

# ══════════════════════════════════════════════════════════════════════
# SECTION 1: TREND DETECTION (target events)
# ══════════════════════════════════════════════════════════════════════

def find_uptrends(prices, threshold):
    """Identical to Phase 2 algorithm for consistency."""
    trends = []
    n = len(prices)
    i = 0
    while i < n:
        trough_idx = i
        trough_val = prices[i]
        peak_idx = i
        peak_val = prices[i]
        j = i + 1
        while j < n:
            if prices[j] > peak_val:
                peak_val = prices[j]
                peak_idx = j
            elif prices[j] < trough_val:
                if peak_val / trough_val - 1 >= threshold:
                    trends.append({"start": trough_idx, "peak": peak_idx,
                                   "ret": peak_val / trough_val - 1,
                                   "duration": peak_idx - trough_idx})
                trough_idx = j
                trough_val = prices[j]
                peak_idx = j
                peak_val = prices[j]
            elif (peak_val / trough_val - 1 >= threshold and
                  (peak_val - prices[j]) / peak_val > threshold * 0.5):
                trends.append({"start": trough_idx, "peak": peak_idx,
                               "ret": peak_val / trough_val - 1,
                               "duration": peak_idx - trough_idx})
                i = peak_idx + 1
                break
            j += 1
        else:
            if peak_val / trough_val - 1 >= threshold:
                trends.append({"start": trough_idx, "peak": peak_idx,
                               "ret": peak_val / trough_val - 1,
                               "duration": peak_idx - trough_idx})
            break
        continue
    return trends

trends_10 = find_uptrends(closes, 0.10)
target_starts = [t["start"] for t in trends_10]
print(f"  Found {len(trends_10)} uptrends >= 10% (target events)")

# ══════════════════════════════════════════════════════════════════════
# SECTION 2: BACKTEST ENGINE
# ══════════════════════════════════════════════════════════════════════

def backtest(entry_signals, exit_func, filter_mask=None):
    """
    Event-driven backtest on H4 data.
    entry_signals: bool array — True on bars with entry trigger.
    exit_func: callable(bar, hwm, entry_bar) -> bool
    filter_mask: optional bool array — entry only allowed when True.
    Returns: equity_curve (array), trades (list of dicts)
    """
    if filter_mask is not None:
        eff_entry = entry_signals & filter_mask
    else:
        eff_entry = entry_signals

    equity = np.ones(n_bars)
    trades = []
    in_pos = False
    entry_price = hwm = 0.0
    entry_bar = 0

    for i in range(1, n_bars):
        if in_pos:
            equity[i] = equity[i-1] * (closes[i] / closes[i-1])
            if closes[i] > hwm:
                hwm = closes[i]
            if exit_func(i, hwm, entry_bar):
                equity[i] *= (1 - HALF_COST)
                trades.append({
                    "entry_bar": entry_bar, "exit_bar": i,
                    "hold": i - entry_bar,
                    "gross_ret": closes[i] / entry_price - 1,
                    "net_ret": closes[i] / entry_price - 1 - COST_FRAC,
                })
                in_pos = False
        else:
            equity[i] = equity[i-1]
            if eff_entry[i]:
                in_pos = True
                entry_price = closes[i]
                entry_bar = i
                hwm = closes[i]
                equity[i] *= (1 - HALF_COST)

    # Close open position at end
    if in_pos:
        trades.append({
            "entry_bar": entry_bar, "exit_bar": n_bars - 1,
            "hold": n_bars - 1 - entry_bar,
            "gross_ret": closes[-1] / entry_price - 1,
            "net_ret": closes[-1] / entry_price - 1 - COST_FRAC,
        })
    return equity, trades


def metrics_from_backtest(equity, trades):
    """Compute standard metrics from equity curve and trade list."""
    # Bar-by-bar log returns
    eq_log = np.diff(np.log(np.maximum(equity, 1e-12)))
    mu = np.mean(eq_log)
    sigma = np.std(eq_log, ddof=0)
    sharpe = (mu / sigma * np.sqrt(ANN)) if sigma > 0 else 0.0

    # CAGR
    if equity[-1] > 0 and n_years > 0:
        cagr = (equity[-1] / equity[0]) ** (1 / n_years) - 1
    else:
        cagr = 0.0

    # MDD
    running_max = np.maximum.accumulate(equity)
    dd = (equity - running_max) / running_max
    mdd = float(np.min(dd))

    n_trades = len(trades)
    if n_trades == 0:
        return {"sharpe": 0, "cagr": 0, "mdd": 0, "n_trades": 0,
                "exposure": 0, "churn_rate": 0, "avg_winner": 0,
                "avg_loser": 0, "win_rate": 0, "profit_factor": 0,
                "avg_hold": 0}

    net_rets = [t["net_ret"] for t in trades]
    winners = [r for r in net_rets if r > 0]
    losers  = [r for r in net_rets if r <= 0]
    avg_winner = float(np.mean(winners)) if winners else 0.0
    avg_loser  = float(np.mean(losers)) if losers else 0.0
    win_rate = len(winners) / n_trades
    pf_num = sum(winners) if winners else 0.0
    pf_den = abs(sum(losers)) if losers else 1e-12
    profit_factor = pf_num / pf_den

    exposure_bars = sum(t["hold"] for t in trades)
    exposure = exposure_bars / n_bars

    avg_hold = float(np.mean([t["hold"] for t in trades]))

    # Churn: exit -> re-entry within 10 bars
    churn_count = 0
    for k in range(len(trades) - 1):
        gap = trades[k+1]["entry_bar"] - trades[k]["exit_bar"]
        if gap <= 10:
            churn_count += 1
    churn_rate = churn_count / n_trades

    return {"sharpe": sharpe, "cagr": cagr, "mdd": mdd,
            "n_trades": n_trades, "exposure": exposure,
            "churn_rate": churn_rate, "avg_winner": avg_winner,
            "avg_loser": avg_loser, "win_rate": win_rate,
            "profit_factor": profit_factor, "avg_hold": avg_hold}


def capture_ratio(trades, trends):
    """Approximate: fraction of trend returns captured by trades."""
    in_pos = np.zeros(n_bars, dtype=bool)
    for t in trades:
        lo = max(t["entry_bar"], 0)
        hi = min(t["exit_bar"] + 1, n_bars)
        in_pos[lo:hi] = True
    captured = 0.0
    total = 0.0
    for tr in trends:
        s, p = tr["start"], tr["peak"]
        if p <= s:
            continue
        n_trend = p - s
        covered = in_pos[s:p+1].sum()
        frac = covered / (n_trend + 1)
        captured += frac * tr["ret"]
        total += tr["ret"]
    return captured / total if total > 0 else 0.0


# ══════════════════════════════════════════════════════════════════════
# SECTION 3: ENTRY SIGNAL GENERATORS
# ══════════════════════════════════════════════════════════════════════

def gen_entry_ema_cross(fast_p, slow_p):
    """EMA(fast) crosses above EMA(slow). fast=1 means close."""
    fast = ema_cache[fast_p]
    slow = ema_cache[slow_p]
    above = fast > slow
    cross_up = np.zeros(n_bars, dtype=bool)
    cross_up[1:] = above[1:] & ~above[:-1]
    return cross_up

def gen_reversal_ema_cross(fast_p, slow_p):
    """Level condition: fast < slow (used as exit condition)."""
    fast = ema_cache[fast_p]
    slow = ema_cache[slow_p]
    return fast < slow

def gen_entry_breakout(period):
    """Close exceeds previous N-bar high."""
    prev_max = np.full(n_bars, np.nan)
    rm = _rolling_max(closes, period)
    prev_max[period:] = rm[period-1:-1]  # shift by 1 to avoid look-ahead
    entry = np.zeros(n_bars, dtype=bool)
    valid = ~np.isnan(prev_max)
    entry[valid] = closes[valid] > prev_max[valid]
    # Only fire on first bar of breakout (new high)
    entry[1:] = entry[1:] & ~entry[:-1]
    return entry

def gen_reversal_breakdown(period):
    """Close below previous N-bar low (level condition)."""
    prev_min = np.full(n_bars, np.nan)
    rm = _rolling_min(closes, period)
    prev_min[period:] = rm[period-1:-1]
    cond = np.zeros(n_bars, dtype=bool)
    valid = ~np.isnan(prev_min)
    cond[valid] = closes[valid] < prev_min[valid]
    return cond

def gen_entry_roc(period, threshold):
    """ROC(period) crosses above threshold%."""
    roc = roc_cache[period]
    above = roc > threshold
    cross_up = np.zeros(n_bars, dtype=bool)
    cross_up[1:] = above[1:] & ~above[:-1]
    return cross_up

def gen_reversal_roc(period):
    """ROC drops below 0 (level condition)."""
    return roc_cache[period] < 0

def gen_entry_volbreak(sma_period, k, atr_arr=None):
    """Close > SMA + k * ATR."""
    sma_arr = _sma(closes, sma_period)
    if atr_arr is None:
        atr_arr = atr_14
    threshold = sma_arr + k * atr_arr
    above = closes > threshold
    cross_up = np.zeros(n_bars, dtype=bool)
    cross_up[1:] = above[1:] & ~above[:-1]
    # Suppress where SMA is NaN
    nan_mask = np.isnan(sma_arr)
    cross_up[nan_mask] = False
    return cross_up

def gen_reversal_volbreak(sma_period, k, atr_arr=None):
    """Close < SMA - k*ATR (level condition)."""
    sma_arr = _sma(closes, sma_period)
    if atr_arr is None:
        atr_arr = atr_14
    threshold = sma_arr - k * atr_arr
    cond = closes < threshold
    cond[np.isnan(sma_arr)] = False
    return cond

# ══════════════════════════════════════════════════════════════════════
# SECTION 4: EXIT FUNCTION FACTORIES
# ══════════════════════════════════════════════════════════════════════

def make_exit_trail_pct(pct):
    """Fixed % trailing stop."""
    def f(i, hwm, entry_bar):
        return closes[i] < hwm * (1 - pct)
    return f

def make_exit_atr_trail(atr_arr, mult):
    """ATR trailing stop."""
    def f(i, hwm, entry_bar):
        return closes[i] < hwm - mult * atr_arr[i]
    return f

def make_exit_reversal(rev_cond):
    """Exit on level condition (precomputed bool array)."""
    def f(i, hwm, entry_bar):
        return rev_cond[i]
    return f

def make_exit_time(period):
    """Exit after N bars."""
    def f(i, hwm, entry_bar):
        return (i - entry_bar) >= period
    return f

def make_exit_vol(mult):
    """Exit when short-term vol > mult * long-term vol."""
    def f(i, hwm, entry_bar):
        if np.isnan(vol_short[i]) or np.isnan(vol_long[i]) or vol_long[i] <= 0:
            return False
        return vol_short[i] > mult * vol_long[i]
    return f

def make_exit_or(fa, fb):
    """Composite: exit when EITHER condition fires."""
    def f(i, hwm, entry_bar):
        return fa(i, hwm, entry_bar) or fb(i, hwm, entry_bar)
    return f


# ══════════════════════════════════════════════════════════════════════
# SECTION 5: PART A — ENTRY SIGNAL SWEEP
# ══════════════════════════════════════════════════════════════════════
print("\n" + "="*70)
print("PART A: ENTRY SIGNAL SWEEP")
print("="*70)

def evaluate_entry(entry_signals, label):
    """Evaluate entry signals against target events."""
    sig_bars = np.where(entry_signals)[0]
    n_signals = len(sig_bars)
    freq = n_signals / n_years if n_years > 0 else 0

    detected = 0
    lags = []
    for ts in target_starts:
        window = sig_bars[(sig_bars >= ts) & (sig_bars <= ts + DETECTION_WINDOW)]
        if len(window) > 0:
            detected += 1
            lags.append(int(window[0] - ts))

    det_rate = detected / len(target_starts) if target_starts else 0
    median_lag = float(np.median(lags)) if lags else np.nan

    # False positives: signals NOT within any [trend_start, trend_peak]
    trend_mask = np.zeros(n_bars, dtype=bool)
    for tr in trends_10:
        trend_mask[tr["start"]:tr["peak"]+1] = True
    fp_count = np.sum(entry_signals & ~trend_mask)
    fp_rate = fp_count / n_signals if n_signals > 0 else 0

    return {"label": label, "n_signals": n_signals, "freq_per_yr": freq,
            "det_rate": det_rate, "fp_rate": fp_rate, "median_lag": median_lag}

entry_sweep = []

# Type A: EMA crossover
for fast in [1, 10, 20, 30]:
    for slow in [60, 90, 120]:
        if fast >= slow:
            continue
        sig = gen_entry_ema_cross(fast, slow)
        label = f"A_ema{fast}_{slow}"
        entry_sweep.append(evaluate_entry(sig, label))
        print(f"  {label}: det={entry_sweep[-1]['det_rate']:.2f}, fp={entry_sweep[-1]['fp_rate']:.2f}, "
              f"lag={entry_sweep[-1]['median_lag']:.1f}, freq={entry_sweep[-1]['freq_per_yr']:.1f}/yr")

# Type B: Breakout
for period in [20, 40, 60, 80, 120]:
    sig = gen_entry_breakout(period)
    label = f"B_break{period}"
    entry_sweep.append(evaluate_entry(sig, label))
    print(f"  {label}: det={entry_sweep[-1]['det_rate']:.2f}, fp={entry_sweep[-1]['fp_rate']:.2f}, "
          f"lag={entry_sweep[-1]['median_lag']:.1f}, freq={entry_sweep[-1]['freq_per_yr']:.1f}/yr")

# Type C: ROC threshold
for period in [10, 20, 40]:
    for thresh in [5, 10, 15]:
        sig = gen_entry_roc(period, thresh)
        label = f"C_roc{period}_{thresh}"
        entry_sweep.append(evaluate_entry(sig, label))
        print(f"  {label}: det={entry_sweep[-1]['det_rate']:.2f}, fp={entry_sweep[-1]['fp_rate']:.2f}, "
              f"lag={entry_sweep[-1]['median_lag']:.1f}, freq={entry_sweep[-1]['freq_per_yr']:.1f}/yr")

# Type D: Volatility breakout
for sma_p in [20, 40]:
    for k in [1.0, 1.5, 2.0]:
        sig = gen_entry_volbreak(sma_p, k)
        label = f"D_vb{sma_p}_{k}"
        entry_sweep.append(evaluate_entry(sig, label))
        print(f"  {label}: det={entry_sweep[-1]['det_rate']:.2f}, fp={entry_sweep[-1]['fp_rate']:.2f}, "
              f"lag={entry_sweep[-1]['median_lag']:.1f}, freq={entry_sweep[-1]['freq_per_yr']:.1f}/yr")

entry_df = pd.DataFrame(entry_sweep)
entry_df.to_csv(os.path.join(TBL_DIR, "Tbl07_entry_signals_summary.csv"), index=False)
print(f"\n  Saved Tbl07 ({len(entry_sweep)} entry configs)")

# Fig10: Entry efficiency frontier (lag vs FP rate)
fig, ax = plt.subplots(figsize=(10, 7))
colors = {"A": "tab:blue", "B": "tab:orange", "C": "tab:green", "D": "tab:red"}
for _, row in entry_df.iterrows():
    etype = row["label"][0]
    ax.scatter(row["median_lag"], row["fp_rate"], c=colors.get(etype, "gray"),
               s=80, alpha=0.7, edgecolors="k", linewidth=0.5)
    ax.annotate(row["label"], (row["median_lag"], row["fp_rate"]),
                fontsize=6, alpha=0.7, xytext=(3, 3), textcoords="offset points")
ax.set_xlabel("Median Lag (bars)")
ax.set_ylabel("False Positive Rate")
ax.set_title("Fig10: Entry Signal Efficiency Frontier")
from matplotlib.patches import Patch
legend_elements = [Patch(facecolor=c, label=f"Type {t}") for t, c in colors.items()]
ax.legend(handles=legend_elements)
ax.grid(True, alpha=0.3)
fig.tight_layout()
fig.savefig(os.path.join(FIG_DIR, "Fig10_entry_frontier.png"), dpi=150)
plt.close(fig)
print("  Saved Fig10")


# ══════════════════════════════════════════════════════════════════════
# SECTION 6: PART B — EXIT SIGNAL SWEEP
# ══════════════════════════════════════════════════════════════════════
print("\n" + "="*70)
print("PART B: EXIT SIGNAL SWEEP")
print("="*70)

# Use standard entry (close > EMA(120) cross) for exit evaluation
std_entry = gen_entry_ema_cross(1, 120)
std_rev   = gen_reversal_ema_cross(1, 120)

exit_sweep = []

def eval_exit(exit_func, label):
    eq, trades = backtest(std_entry, exit_func)
    m = metrics_from_backtest(eq, trades)
    cr = capture_ratio(trades, trends_10)
    m["capture_ratio"] = cr
    m["label"] = label
    return m

# Type X: Fixed % trail
for pct in [0.03, 0.05, 0.08, 0.12, 0.15]:
    r = eval_exit(make_exit_trail_pct(pct), f"X_trail{int(pct*100)}pct")
    exit_sweep.append(r)
    print(f"  {r['label']}: Sh={r['sharpe']:.3f}, cap={r['capture_ratio']:.3f}, "
          f"churn={r['churn_rate']:.3f}, hold={r['avg_hold']:.0f}")

# Type Y: ATR trail
for mult in [2.0, 3.0, 4.0, 5.0]:
    r = eval_exit(make_exit_atr_trail(atr_14, mult), f"Y_atr14_{mult}")
    exit_sweep.append(r)
    print(f"  {r['label']}: Sh={r['sharpe']:.3f}, cap={r['capture_ratio']:.3f}, "
          f"churn={r['churn_rate']:.3f}, hold={r['avg_hold']:.0f}")

# Type Z: Signal reversal (EMA cross-down)
for fast, slow in [(1, 120), (20, 90), (10, 60)]:
    rev = gen_reversal_ema_cross(fast, slow)
    r = eval_exit(make_exit_reversal(rev), f"Z_rev{fast}_{slow}")
    exit_sweep.append(r)
    print(f"  {r['label']}: Sh={r['sharpe']:.3f}, cap={r['capture_ratio']:.3f}, "
          f"churn={r['churn_rate']:.3f}, hold={r['avg_hold']:.0f}")

# Type W: Time-based
for period in [20, 40, 80, 120]:
    r = eval_exit(make_exit_time(period), f"W_time{period}")
    exit_sweep.append(r)
    print(f"  {r['label']}: Sh={r['sharpe']:.3f}, cap={r['capture_ratio']:.3f}, "
          f"churn={r['churn_rate']:.3f}, hold={r['avg_hold']:.0f}")

# Type V: Volatility-based
for vmult in [1.5, 2.0, 2.5]:
    r = eval_exit(make_exit_vol(vmult), f"V_vol{vmult}")
    exit_sweep.append(r)
    print(f"  {r['label']}: Sh={r['sharpe']:.3f}, cap={r['capture_ratio']:.3f}, "
          f"churn={r['churn_rate']:.3f}, hold={r['avg_hold']:.0f}")

# COMPOSITE exits
print("  --- Composites ---")

# Y∪Z: ATR trail OR reversal
for mult in [2.0, 3.0, 4.0]:
    ef = make_exit_or(make_exit_atr_trail(atr_14, mult), make_exit_reversal(std_rev))
    r = eval_exit(ef, f"YZ_atr{mult}_rev1_120")
    exit_sweep.append(r)
    print(f"  {r['label']}: Sh={r['sharpe']:.3f}, cap={r['capture_ratio']:.3f}, "
          f"churn={r['churn_rate']:.3f}, hold={r['avg_hold']:.0f}")

# Y∪W: ATR trail OR time
for tp in [80, 120]:
    ef = make_exit_or(make_exit_atr_trail(atr_14, 3.0), make_exit_time(tp))
    r = eval_exit(ef, f"YW_atr3_{tp}")
    exit_sweep.append(r)
    print(f"  {r['label']}: Sh={r['sharpe']:.3f}, cap={r['capture_ratio']:.3f}, "
          f"churn={r['churn_rate']:.3f}, hold={r['avg_hold']:.0f}")

# Y∪V: ATR trail OR vol
ef = make_exit_or(make_exit_atr_trail(atr_14, 3.0), make_exit_vol(2.0))
r = eval_exit(ef, "YV_atr3_vol2")
exit_sweep.append(r)
print(f"  {r['label']}: Sh={r['sharpe']:.3f}, cap={r['capture_ratio']:.3f}, "
      f"churn={r['churn_rate']:.3f}, hold={r['avg_hold']:.0f}")

# X∪Z: Fixed trail OR reversal
ef = make_exit_or(make_exit_trail_pct(0.08), make_exit_reversal(std_rev))
r = eval_exit(ef, "XZ_trail8_rev1_120")
exit_sweep.append(r)
print(f"  {r['label']}: Sh={r['sharpe']:.3f}, cap={r['capture_ratio']:.3f}, "
      f"churn={r['churn_rate']:.3f}, hold={r['avg_hold']:.0f}")

exit_df = pd.DataFrame(exit_sweep)
exit_df.to_csv(os.path.join(TBL_DIR, "Tbl08_exit_signals_summary.csv"), index=False)
print(f"\n  Saved Tbl08 ({len(exit_sweep)} exit configs)")

# Fig11: Capture vs Churn
fig, ax = plt.subplots(figsize=(10, 7))
simple_mask = ~exit_df["label"].str.contains(r"[A-Z]{2}_")
ax.scatter(exit_df.loc[simple_mask, "churn_rate"], exit_df.loc[simple_mask, "capture_ratio"],
           c="tab:blue", s=80, alpha=0.7, label="Simple", edgecolors="k", linewidth=0.5)
ax.scatter(exit_df.loc[~simple_mask, "churn_rate"], exit_df.loc[~simple_mask, "capture_ratio"],
           c="tab:red", s=100, alpha=0.8, label="Composite", edgecolors="k", linewidth=0.5, marker="D")
for _, row in exit_df.iterrows():
    ax.annotate(row["label"], (row["churn_rate"], row["capture_ratio"]),
                fontsize=5.5, alpha=0.7, xytext=(3, 3), textcoords="offset points")
ax.set_xlabel("Churn Rate")
ax.set_ylabel("Capture Ratio")
ax.set_title("Fig11: Exit Capture vs Churn")
ax.legend()
ax.grid(True, alpha=0.3)
fig.tight_layout()
fig.savefig(os.path.join(FIG_DIR, "Fig11_exit_capture_vs_churn.png"), dpi=150)
plt.close(fig)
print("  Saved Fig11")

# Fig12: Capture vs MDD
fig, ax = plt.subplots(figsize=(10, 7))
ax.scatter(exit_df.loc[simple_mask, "mdd"].abs(), exit_df.loc[simple_mask, "capture_ratio"],
           c="tab:blue", s=80, alpha=0.7, label="Simple", edgecolors="k", linewidth=0.5)
ax.scatter(exit_df.loc[~simple_mask, "mdd"].abs(), exit_df.loc[~simple_mask, "capture_ratio"],
           c="tab:red", s=100, alpha=0.8, label="Composite", edgecolors="k", linewidth=0.5, marker="D")
for _, row in exit_df.iterrows():
    ax.annotate(row["label"], (abs(row["mdd"]), row["capture_ratio"]),
                fontsize=5.5, alpha=0.7, xytext=(3, 3), textcoords="offset points")
ax.set_xlabel("|MDD|")
ax.set_ylabel("Capture Ratio")
ax.set_title("Fig12: Exit Capture vs MDD")
ax.legend()
ax.grid(True, alpha=0.3)
fig.tight_layout()
fig.savefig(os.path.join(FIG_DIR, "Fig12_exit_capture_vs_mdd.png"), dpi=150)
plt.close(fig)
print("  Saved Fig12")


# ══════════════════════════════════════════════════════════════════════
# SECTION 7: PART C — ENTRY x EXIT GRID + FILTERS + DECOMPOSITION
# ══════════════════════════════════════════════════════════════════════
print("\n" + "="*70)
print("PART C: ENTRY x EXIT GRID")
print("="*70)

# Define grid entries (representative per type)
grid_entries = OrderedDict([
    ("A_1_120",  {"entry": gen_entry_ema_cross(1, 120),  "rev": gen_reversal_ema_cross(1, 120)}),
    ("A_20_90",  {"entry": gen_entry_ema_cross(20, 90),  "rev": gen_reversal_ema_cross(20, 90)}),
    ("B_60",     {"entry": gen_entry_breakout(60),       "rev": gen_reversal_breakdown(60)}),
    ("C_20_10",  {"entry": gen_entry_roc(20, 10),        "rev": gen_reversal_roc(20)}),
    ("D_20_1.5", {"entry": gen_entry_volbreak(20, 1.5),  "rev": gen_reversal_volbreak(20, 1.5)}),
])

# Define grid exits (functions need entry-specific reversal for Z-based exits)
def get_grid_exits(rev_cond):
    """Return dict of exit_name -> exit_func, using given reversal condition."""
    return OrderedDict([
        ("X_trail8",  make_exit_trail_pct(0.08)),
        ("Y_atr3",    make_exit_atr_trail(atr_14, 3.0)),
        ("Z_rev",     make_exit_reversal(rev_cond)),
        ("W_time80",  make_exit_time(80)),
        ("V_vol2",    make_exit_vol(2.0)),
        ("YZ_atr3_rev", make_exit_or(make_exit_atr_trail(atr_14, 3.0),
                                      make_exit_reversal(rev_cond))),
        ("YW_atr3_80",  make_exit_or(make_exit_atr_trail(atr_14, 3.0),
                                      make_exit_time(80))),
        ("YV_atr3_vol2", make_exit_or(make_exit_atr_trail(atr_14, 3.0),
                                       make_exit_vol(2.0))),
        ("XZ_trail8_rev", make_exit_or(make_exit_trail_pct(0.08),
                                        make_exit_reversal(rev_cond))),
    ])

grid_results = []
for ename, edata in grid_entries.items():
    exits = get_grid_exits(edata["rev"])
    for xname, xfunc in exits.items():
        eq, trades = backtest(edata["entry"], xfunc)
        m = metrics_from_backtest(eq, trades)
        m["entry"] = ename
        m["exit"] = xname
        m["config"] = f"{ename}+{xname}"
        grid_results.append(m)
        print(f"  {m['config']}: Sh={m['sharpe']:.3f}, CAGR={m['cagr']:.1%}, "
              f"MDD={m['mdd']:.1%}, trades={m['n_trades']}")

grid_df = pd.DataFrame(grid_results)
grid_df.to_csv(os.path.join(TBL_DIR, "Tbl09_entry_exit_grid.csv"), index=False)
print(f"\n  Saved Tbl09 ({len(grid_results)} pairs)")

# ── Fig13: Heatmap ───────────────────────────────────────────────────
entry_names = list(grid_entries.keys())
exit_names = list(get_grid_exits(np.zeros(n_bars, dtype=bool)).keys())
heat = np.zeros((len(entry_names), len(exit_names)))
for r in grid_results:
    ei = entry_names.index(r["entry"])
    xi = exit_names.index(r["exit"])
    heat[ei, xi] = r["sharpe"]

fig, ax = plt.subplots(figsize=(14, 6))
im = ax.imshow(heat, cmap="RdYlGn", aspect="auto")
ax.set_xticks(range(len(exit_names)))
ax.set_xticklabels(exit_names, rotation=45, ha="right", fontsize=8)
ax.set_yticks(range(len(entry_names)))
ax.set_yticklabels(entry_names, fontsize=9)
for i in range(heat.shape[0]):
    for j in range(heat.shape[1]):
        ax.text(j, i, f"{heat[i,j]:.2f}", ha="center", va="center", fontsize=7,
                color="white" if abs(heat[i,j]) > 0.7 * np.max(np.abs(heat)) else "black")
ax.set_title("Fig13: Entry x Exit Sharpe Heatmap (incl. composite exits)")
fig.colorbar(im, ax=ax, label="Sharpe")
fig.tight_layout()
fig.savefig(os.path.join(FIG_DIR, "Fig13_entry_exit_heatmap.png"), dpi=150)
plt.close(fig)
print("  Saved Fig13")

# ── Filter layer on TOP-10 pairs ─────────────────────────────────────
print("\n  --- Filter layer on TOP-10 ---")
top10 = grid_df.nlargest(10, "sharpe")

filter_masks = OrderedDict([
    ("F1_d1ema21", d1_regime_ema21.astype(bool)),
    ("F2_d1ema50", d1_regime_ema50.astype(bool)),
    ("F3_vdo_pos", vdo > 0.0),
    ("F4_vol_low", vol_long < np.nanmedian(vol_long)),  # low-vol regime
])

filter_results = []
for _, row in top10.iterrows():
    ename = row["entry"]
    xname = row["exit"]
    edata = grid_entries[ename]
    exits = get_grid_exits(edata["rev"])
    xfunc = exits[xname]
    base_sharpe = row["sharpe"]

    for fname, fmask in filter_masks.items():
        eq, trades = backtest(edata["entry"], xfunc, filter_mask=fmask)
        m = metrics_from_backtest(eq, trades)
        m["entry"] = ename
        m["exit"] = xname
        m["filter"] = fname
        m["config"] = f"{ename}+{xname}+{fname}"
        m["base_sharpe"] = base_sharpe
        m["delta_sharpe"] = m["sharpe"] - base_sharpe
        filter_results.append(m)
        print(f"    {m['config']}: Sh={m['sharpe']:.3f} (Δ={m['delta_sharpe']:+.3f}), "
              f"trades={m['n_trades']}")

filter_df = pd.DataFrame(filter_results)
filter_df.to_csv(os.path.join(TBL_DIR, "Tbl10_filter_effects.csv"), index=False)
print(f"  Saved Tbl10 ({len(filter_results)} filtered configs)")

# ── Best-known strategy decomposition ─────────────────────────────────
print("\n  --- Best-known strategy decomposition ---")

# Full config: EMA(1,120) entry + dual exit (ATR3 OR reversal) + VDO>0 + D1 EMA(21)
bk_entry = gen_entry_ema_cross(1, 120)
bk_rev   = gen_reversal_ema_cross(1, 120)
bk_exit_dual = make_exit_or(make_exit_atr_trail(atr_14, 3.0), make_exit_reversal(bk_rev))
bk_exit_trail = make_exit_atr_trail(atr_14, 3.0)
bk_exit_rev   = make_exit_reversal(bk_rev)
bk_filter_vdo = vdo > 0.0
bk_filter_d1  = d1_regime_ema21.astype(bool)
bk_filter_both = bk_filter_vdo & bk_filter_d1

decomp = OrderedDict()

configs = [
    ("a_full",            bk_exit_dual,  bk_filter_both),
    ("b_no_vdo",          bk_exit_dual,  bk_filter_d1),
    ("c_no_d1regime",     bk_exit_dual,  bk_filter_vdo),
    ("d_trail_only",      bk_exit_trail, bk_filter_both),
    ("e_reversal_only",   bk_exit_rev,   bk_filter_both),
    ("f_no_filters",      bk_exit_dual,  None),
]

for label, xfunc, fmask in configs:
    eq, trades = backtest(bk_entry, xfunc, filter_mask=fmask)
    m = metrics_from_backtest(eq, trades)
    m["config"] = label
    decomp[label] = m
    print(f"    {label}: Sh={m['sharpe']:.3f}, CAGR={m['cagr']:.1%}, "
          f"MDD={m['mdd']:.1%}, trades={m['n_trades']}")

full_sh = decomp["a_full"]["sharpe"]
decomp_rows = []
for label, m in decomp.items():
    r = {"config": label, "sharpe": m["sharpe"], "cagr": m["cagr"],
         "mdd": m["mdd"], "n_trades": m["n_trades"], "exposure": m["exposure"],
         "delta_sharpe": m["sharpe"] - full_sh}
    decomp_rows.append(r)

decomp_df = pd.DataFrame(decomp_rows)
decomp_df.to_csv(os.path.join(TBL_DIR, "Tbl_decomposition.csv"), index=False)
print("  Saved Tbl_decomposition")

# Fig_decomposition: Component contribution bar chart
contributions = {
    "VDO filter":       full_sh - decomp["b_no_vdo"]["sharpe"],
    "D1 regime":        full_sh - decomp["c_no_d1regime"]["sharpe"],
    "Dual exit\n(vs trail)": full_sh - decomp["d_trail_only"]["sharpe"],
    "Trail\n(vs reversal)":  full_sh - decomp["e_reversal_only"]["sharpe"],
    "Both filters":     full_sh - decomp["f_no_filters"]["sharpe"],
}

fig, ax = plt.subplots(figsize=(9, 5))
bars = ax.bar(contributions.keys(), contributions.values(),
              color=["#4CAF50" if v > 0 else "#F44336" for v in contributions.values()],
              edgecolor="k", linewidth=0.5)
ax.axhline(0, color="k", linewidth=0.5)
ax.set_ylabel("ΔSharpe (contribution)")
ax.set_title(f"Fig_decomposition: Component Contributions (full Sharpe={full_sh:.3f})")
for bar, val in zip(bars, contributions.values()):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height(),
            f"{val:+.3f}", ha="center", va="bottom" if val >= 0 else "top", fontsize=9)
ax.grid(True, alpha=0.3, axis="y")
fig.tight_layout()
fig.savefig(os.path.join(FIG_DIR, "Fig_decomposition.png"), dpi=150)
plt.close(fig)
print("  Saved Fig_decomposition")


# ══════════════════════════════════════════════════════════════════════
# SECTION 8: PART D — IMPACT ANALYSIS (OLS Regression)
# ══════════════════════════════════════════════════════════════════════
print("\n" + "="*70)
print("PART D: IMPACT ANALYSIS")
print("="*70)

# Combine grid + filter results for regression
all_configs = pd.concat([grid_df, filter_df], ignore_index=True)
print(f"  Total data points for regression: {len(all_configs)}")

predictors = ["exposure", "churn_rate", "n_trades", "avg_loser", "win_rate", "avg_hold"]
y = all_configs["sharpe"].values.astype(float)
X = all_configs[predictors].values.astype(float)

# Handle NaN/Inf
valid = np.all(np.isfinite(X), axis=1) & np.isfinite(y)
y_v = y[valid]
X_v = X[valid]
print(f"  Valid data points: {valid.sum()}")

# Standardize for comparable coefficients
X_std = (X_v - X_v.mean(axis=0)) / (X_v.std(axis=0) + 1e-12)
y_std = (y_v - y_v.mean()) / (y_v.std() + 1e-12)

X_ols = sm.add_constant(X_v)
model = sm.OLS(y_v, X_ols).fit()
print(model.summary())

# Standardized impact: |beta * std(x)|
raw_betas = model.params[1:]
x_stds = X_v.std(axis=0)
std_impact = np.abs(raw_betas * x_stds)
impact_rank = sorted(zip(predictors, raw_betas, model.pvalues[1:], std_impact),
                     key=lambda t: -t[3])

# Partial R^2
ssr_full = model.ssr
partial_r2 = {}
for k, pred in enumerate(predictors):
    cols = [j for j in range(X_v.shape[1]) if j != k]
    X_red = sm.add_constant(X_v[:, cols])
    m_red = sm.OLS(y_v, X_red).fit()
    partial_r2[pred] = 1 - ssr_full / m_red.ssr

drivers_rows = []
for pred, beta, pval, si in impact_rank:
    drivers_rows.append({
        "predictor": pred, "beta": beta, "p_value": pval,
        "std_impact": si, "partial_R2": partial_r2.get(pred, 0),
    })
    print(f"  {pred:12s}: β={beta:+.4f}, p={pval:.4f}, "
          f"|β·σ|={si:.4f}, partial_R²={partial_r2.get(pred, 0):.4f}")

print(f"  Overall R² = {model.rsquared:.4f}, Adj R² = {model.rsquared_adj:.4f}")

drivers_df = pd.DataFrame(drivers_rows)
drivers_df.to_csv(os.path.join(TBL_DIR, "Tbl_sharpe_drivers.csv"), index=False)
print("  Saved Tbl_sharpe_drivers")

# Fig_impact: Top-3 predictors vs Sharpe
top3_preds = [r["predictor"] for r in drivers_rows[:3]]
fig, axes = plt.subplots(1, 3, figsize=(15, 5))
for ax_i, pred in enumerate(top3_preds):
    ax = axes[ax_i]
    xvals = all_configs.loc[valid, pred].values if pred in all_configs.columns else X_v[:, predictors.index(pred)]
    ax.scatter(xvals, y_v, alpha=0.5, s=30, edgecolors="k", linewidth=0.3)
    # Regression line
    slope, intercept = np.polyfit(xvals, y_v, 1)
    xs = np.linspace(xvals.min(), xvals.max(), 50)
    ax.plot(xs, slope * xs + intercept, "r-", linewidth=2, alpha=0.7)
    ax.set_xlabel(pred)
    ax.set_ylabel("Sharpe")
    ax.set_title(f"{pred} (|β·σ|={drivers_rows[ax_i]['std_impact']:.3f})")
    ax.grid(True, alpha=0.3)
fig.suptitle("Fig_impact: Top-3 Sharpe Predictors", y=1.02)
fig.tight_layout()
fig.savefig(os.path.join(FIG_DIR, "Fig_impact_sharpe_drivers.png"), dpi=150, bbox_inches="tight")
plt.close(fig)
print("  Saved Fig_impact")


# ══════════════════════════════════════════════════════════════════════
# SECTION 9: PART E — TOP-N ANALYSIS
# ══════════════════════════════════════════════════════════════════════
print("\n" + "="*70)
print("PART E: TOP-N ANALYSIS")
print("="*70)

# Combine all results
all_df = pd.concat([grid_df, filter_df], ignore_index=True)

# TOP-20 by Sharpe
top20_sharpe = all_df.nlargest(20, "sharpe")[
    ["config", "sharpe", "cagr", "mdd", "n_trades", "exposure",
     "churn_rate", "avg_winner", "avg_loser", "win_rate", "profit_factor", "avg_hold"]
]
top20_sharpe.to_csv(os.path.join(TBL_DIR, "Tbl_top20_sharpe.csv"), index=False)
print("\n  TOP-20 by Sharpe:")
for _, row in top20_sharpe.head(20).iterrows():
    print(f"    {row['config']:45s}  Sh={row['sharpe']:.3f}  CAGR={row['cagr']:.1%}  "
          f"MDD={row['mdd']:.1%}  N={row['n_trades']:3.0f}")

# TOP-20 by Calmar (CAGR / |MDD|)
all_df["calmar"] = all_df["cagr"] / all_df["mdd"].abs().clip(lower=0.01)
top20_calmar = all_df.nlargest(20, "calmar")[
    ["config", "calmar", "sharpe", "cagr", "mdd", "n_trades", "exposure"]
]
top20_calmar.to_csv(os.path.join(TBL_DIR, "Tbl_top20_calmar.csv"), index=False)
print("\n  TOP-20 by Calmar:")
for _, row in top20_calmar.head(10).iterrows():
    print(f"    {row['config']:45s}  Cal={row['calmar']:.3f}  Sh={row['sharpe']:.3f}  "
          f"CAGR={row['cagr']:.1%}  MDD={row['mdd']:.1%}")

# TOP-5 by Sharpe: WHY analysis
print("\n  TOP-5 Sharpe — pattern analysis:")
top5 = all_df.nlargest(5, "sharpe")
for col in ["entry", "exit", "exposure", "churn_rate", "avg_loser", "avg_hold", "win_rate"]:
    if col in top5.columns:
        vals = top5[col]
        if pd.api.types.is_numeric_dtype(vals):
            print(f"    {col}: mean={vals.mean():.4f}, range=[{vals.min():.4f}, {vals.max():.4f}]")
        else:
            print(f"    {col}: {vals.tolist()}")

# ══════════════════════════════════════════════════════════════════════
# SECTION 10: OBSERVATION LOG
# ══════════════════════════════════════════════════════════════════════
observations = []

def obs(obs_id, text, refs):
    observations.append({"id": obs_id, "text": text, "refs": refs})
    print(f"\n  {obs_id}: {text}")

print("\n" + "="*70)
print("OBSERVATIONS")
print("="*70)

# Entry observations
best_det = entry_df.loc[entry_df["det_rate"].idxmax()]
worst_det = entry_df.loc[entry_df["det_rate"].idxmin()]
obs("Obs18", f"Entry detection rates range from {worst_det['det_rate']:.2f} ({worst_det['label']}) "
    f"to {best_det['det_rate']:.2f} ({best_det['label']}). "
    f"Lag-FP tradeoff: lower lag → higher FP rate.", ["Fig10", "Tbl07"])

# Exit observations
best_sh_exit = exit_df.loc[exit_df["sharpe"].idxmax()]
obs("Obs19", f"Exit sweep (fixed entry A_1_120): best Sharpe {best_sh_exit['sharpe']:.3f} "
    f"({best_sh_exit['label']}). Composite exits occupy distinct region in capture-churn space.",
    ["Fig11", "Fig12", "Tbl08"])

composite_exits = exit_df[exit_df["label"].str.contains(r"^[A-Z]{2}_")]
simple_exits = exit_df[~exit_df["label"].str.contains(r"^[A-Z]{2}_")]
obs("Obs20", f"Composite exits: mean Sharpe {composite_exits['sharpe'].mean():.3f} "
    f"(n={len(composite_exits)}) vs simple exits: mean Sharpe {simple_exits['sharpe'].mean():.3f} "
    f"(n={len(simple_exits)}). {'Composites higher.' if composite_exits['sharpe'].mean() > simple_exits['sharpe'].mean() else 'Simples higher.'}",
    ["Tbl08"])

# Grid observations
best_grid = grid_df.loc[grid_df["sharpe"].idxmax()]
obs("Obs21", f"Grid best: {best_grid['config']} Sharpe={best_grid['sharpe']:.3f}. "
    f"Sharpe range across grid: [{grid_df['sharpe'].min():.3f}, {grid_df['sharpe'].max():.3f}].",
    ["Fig13", "Tbl09"])

# Entry type comparison
for etype in grid_entries:
    sub = grid_df[grid_df["entry"] == etype]
    print(f"    {etype}: mean Sh={sub['sharpe'].mean():.3f}, "
          f"range=[{sub['sharpe'].min():.3f}, {sub['sharpe'].max():.3f}]")

# Decomposition observation
obs("Obs22", f"Best-known decomposition: full Sharpe={decomp['a_full']['sharpe']:.3f}. "
    f"D1 regime contributes Δ={full_sh - decomp['c_no_d1regime']['sharpe']:+.3f}, "
    f"VDO filter Δ={full_sh - decomp['b_no_vdo']['sharpe']:+.3f}, "
    f"dual exit (vs trail) Δ={full_sh - decomp['d_trail_only']['sharpe']:+.3f}.",
    ["Tbl_decomposition", "Fig_decomposition"])

# Filter observation
mean_delta_by_filter = filter_df.groupby("filter")["delta_sharpe"].mean()
best_filter = mean_delta_by_filter.idxmax()
obs("Obs23", f"Filter impact on top-10 pairs: {best_filter} has largest mean ΔSharpe "
    f"({mean_delta_by_filter[best_filter]:+.3f}). {dict(mean_delta_by_filter)}",
    ["Tbl10"])

# Impact analysis observation
obs("Obs24", f"OLS regression R²={model.rsquared:.3f}. Top predictor: {impact_rank[0][0]} "
    f"(|β·σ|={impact_rank[0][3]:.4f}, p={impact_rank[0][2]:.4f}). "
    f"Second: {impact_rank[1][0]} (|β·σ|={impact_rank[1][3]:.4f}).",
    ["Tbl_sharpe_drivers", "Fig_impact"])

# Top-N pattern observation
if "entry" in top5.columns:
    entry_counts = top5["entry"].value_counts()
    dominant_entry = entry_counts.index[0] if len(entry_counts) > 0 else "none"
    obs("Obs25", f"Top-5 Sharpe configs: dominant entry type = {dominant_entry} "
        f"(appears {entry_counts.iloc[0]}/{len(top5)} times). "
        f"Mean exposure={top5['exposure'].mean():.3f}, "
        f"mean avg_loser={top5['avg_loser'].mean():.4f}.",
        ["Tbl_top20_sharpe"])

# Save observations
obs_json = os.path.join(TBL_DIR, "observations_phase3.json")
with open(obs_json, "w") as f:
    json.dump(observations, f, indent=2, default=str)
print(f"\n  Saved {len(observations)} observations to {obs_json}")


# ══════════════════════════════════════════════════════════════════════
# SUMMARY
# ══════════════════════════════════════════════════════════════════════
elapsed = time.time() - t0
print(f"\n{'='*70}")
print(f"Phase 3 complete in {elapsed:.1f}s")
print(f"  Entry configs swept: {len(entry_sweep)}")
print(f"  Exit configs swept:  {len(exit_sweep)}")
print(f"  Grid pairs:          {len(grid_results)}")
print(f"  Filter variants:     {len(filter_results)}")
print(f"  Total backtests:     {len(grid_results) + len(filter_results) + len(exit_sweep) + 6}")
print(f"  Observations:        Obs18-Obs{17 + len(observations)}")
print(f"{'='*70}")
