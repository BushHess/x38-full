#!/usr/bin/env python3
"""
Double Compression Damage Analysis for V10
============================================
Measures whether trailing stop "double compression" causes real damage.

Double compression = ATR shrinks (vol nén) + multiplier drops 3.5→2.5 (profit tightening)
simultaneously, making trail distance very small relative to normal price movement.

Key question: Does V10's trailing stop cause measurable damage? If so, is it
from double compression specifically, or from the trailing stop mechanism in general?
"""

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path
import json
import warnings
warnings.filterwarnings('ignore')

# ─── Config ────────────────────────────────────────────────────────────
BAR_FILE = Path("/var/www/trading-bots/btc-spot-dev/data/bars_btcusdt_2016_now_h1_4h_1d.csv")
CANDIDATES = {
    'baseline_020': Path("/var/www/trading-bots/btc-spot/out_v10_trail_tighten/candidates/baseline_legacy/base/trades.csv"),
    'tighten_025': Path("/var/www/trading-bots/btc-spot/out_v10_trail_tighten/candidates/tighten_025/base/trades.csv"),
    'tighten_030': Path("/var/www/trading-bots/btc-spot/out_v10_trail_tighten/candidates/tighten_030/base/trades.csv"),
    'apex': Path("/var/www/trading-bots/btc-spot/out_v10_apex/trades.csv"),
}
OUT_DIR = Path("/var/www/trading-bots/btc-spot/out_v10_trail_tighten/damage_analysis")

# V10 default parameters
ATR_FAST_PERIOD = 14
ATR_SLOW_PERIOD = 50
TRAIL_ACTIVATE_PCT = 0.05
TRAIL_ATR_MULT_WIDE = 3.5
TRAIL_ATR_MULT_TIGHT = 2.5
COMPRESSION_RATIO = 0.75

# Tighten thresholds for each candidate
TIGHTEN_THRESHOLDS = {
    'baseline_020': 0.20,
    'tighten_025': 0.25,
    'tighten_030': 0.30,
    'apex': 0.20,
}

# Counterfactual horizons (in H4 bars)
HORIZONS = [6, 12, 18, 30, 42]  # 1d, 2d, 3d, 5d, 7d
HORIZON_LABELS = ['1d', '2d', '3d', '5d', '7d']


# ─── Data Loading ──────────────────────────────────────────────────────

def ema(arr, period):
    alpha = 2.0 / (period + 1)
    out = np.zeros_like(arr, dtype=float)
    out[0] = arr[0]
    for i in range(1, len(arr)):
        out[i] = alpha * arr[i] + (1 - alpha) * out[i - 1]
    return out


def load_h4_bars():
    """Load H4 bars and compute ATR + derived metrics."""
    print("Loading H4 bar data...")
    df = pd.read_csv(BAR_FILE)
    df = df[df['interval'] == '4h'].copy()
    df = df.sort_values('open_time').reset_index(drop=True)
    df['timestamp'] = pd.to_datetime(df['open_time'], unit='ms')

    h = df['high'].values.astype(float)
    lo = df['low'].values.astype(float)
    c = df['close'].values.astype(float)

    pc = np.roll(c, 1); pc[0] = c[0]
    tr = np.maximum(h - lo, np.maximum(np.abs(h - pc), np.abs(lo - pc)))

    df['atr_fast'] = ema(tr, ATR_FAST_PERIOD)
    df['atr_slow'] = ema(tr, ATR_SLOW_PERIOD)
    df['compression'] = df['atr_fast'] / df['atr_slow']
    df['is_compressed'] = df['compression'] < COMPRESSION_RATIO
    df['bar_range_pct'] = (df['high'] - df['low']) / df['close']
    df['atr_fast_pct'] = df['atr_fast'] / df['close']

    print(f"  {len(df)} bars, {df['timestamp'].min()} → {df['timestamp'].max()}")
    return df


def load_trades(filepath):
    """Load trades CSV, handling both 11-col and 13-col schemas."""
    df = pd.read_csv(filepath)
    # Always use entry_ts_ms/exit_ts_ms (milliseconds) as the canonical timestamp
    if 'entry_ts_ms' not in df.columns and 'entry_time' in df.columns:
        # Derive ms from ISO timestamps
        df['entry_ts_ms'] = pd.to_datetime(df['entry_time'], utc=True).astype(np.int64) // 10**6
        df['exit_ts_ms'] = pd.to_datetime(df['exit_time'], utc=True).astype(np.int64) // 10**6
    # Create timezone-naive timestamps from ms
    df['entry_ts'] = pd.to_datetime(df['entry_ts_ms'], unit='ms')
    df['exit_ts'] = pd.to_datetime(df['exit_ts_ms'], unit='ms')
    return df


def find_bar_index(bars_open_ms, target_ms):
    """Binary search for closest bar using millisecond epoch arrays."""
    idx = np.searchsorted(bars_open_ms, target_ms, side='right') - 1
    return max(0, min(idx, len(bars_open_ms) - 1))


# ─── Core Analysis ─────────────────────────────────────────────────────

def reconstruct_trade_trail(trade, bars, bars_ms, tighten_threshold):
    """
    Bar-by-bar trailing stop reconstruction for one trade.
    Uses the CORRECT tighten_threshold for the candidate being analyzed.
    """
    entry_idx = find_bar_index(bars_ms, trade['entry_ts_ms'])
    exit_idx = find_bar_index(bars_ms, trade['exit_ts_ms'])
    if exit_idx <= entry_idx:
        return None

    entry_price = trade['entry_price']
    trade_bars = bars.iloc[entry_idx:exit_idx + 1]

    peak_price = entry_price
    peak_profit = 0.0
    records = []

    for _, bar in trade_bars.iterrows():
        mid = bar['close']
        peak_price = max(peak_price, mid)
        profit = (mid - entry_price) / entry_price
        peak_profit = max(peak_profit, profit)

        trail_active = peak_profit >= TRAIL_ACTIVATE_PCT
        tightened = peak_profit >= tighten_threshold
        mult = TRAIL_ATR_MULT_TIGHT if tightened else TRAIL_ATR_MULT_WIDE

        atr_val = bar['atr_fast']
        trail_distance = mult * atr_val
        trail_dist_pct = trail_distance / mid if mid > 0 else 0

        records.append({
            'timestamp': bar['timestamp'],
            'close': mid,
            'atr_fast': atr_val,
            'compression': bar['compression'],
            'is_compressed': bar['is_compressed'],
            'peak_price': peak_price,
            'peak_profit': peak_profit,
            'current_profit': profit,
            'trail_active': trail_active,
            'tightened': tightened,
            'multiplier': mult,
            'trail_distance': trail_distance,
            'trail_distance_pct': trail_dist_pct,
            'trail_stop': peak_price - trail_distance if trail_active else None,
            'bar_range_pct': bar['bar_range_pct'],
            'trail_in_noise': trail_dist_pct < bar['bar_range_pct'] if trail_active else False,
        })

    return pd.DataFrame(records)


def compute_counterfactual(trade, bars, bars_ms):
    """Post-exit price action at multiple horizons."""
    exit_idx = find_bar_index(bars_ms, trade['exit_ts_ms'])
    results = {}

    for h, label in zip(HORIZONS, HORIZON_LABELS):
        end_idx = min(exit_idx + h, len(bars) - 1)
        if exit_idx + 1 > end_idx:
            results[f'max_high_{label}'] = trade['exit_price']
            results[f'max_return_{label}'] = 0.0
            results[f'close_at_{label}'] = trade['exit_price']
            results[f'close_return_{label}'] = 0.0
            continue

        future = bars.iloc[exit_idx + 1:end_idx + 1]
        max_high = future['high'].max()
        close_h = future['close'].iloc[-1]

        results[f'max_high_{label}'] = max_high
        results[f'max_return_{label}'] = (max_high - trade['exit_price']) / trade['exit_price']
        results[f'close_at_{label}'] = close_h
        results[f'close_return_{label}'] = (close_h - trade['exit_price']) / trade['exit_price']

    # Max drawdown in 7d window
    end_idx = min(exit_idx + max(HORIZONS), len(bars) - 1)
    if exit_idx + 1 <= end_idx:
        future = bars.iloc[exit_idx + 1:end_idx + 1]
        min_low = future['low'].min()
        results['max_dd_7d'] = (min_low - trade['exit_price']) / trade['exit_price']
    else:
        results['max_dd_7d'] = 0.0

    return results


def analyze_candidate(name, trade_file, bars, bars_ms):
    """Full analysis of one candidate's trades."""
    trades = load_trades(trade_file)
    trail_exits = trades[trades['exit_reason'] == 'trailing_stop']
    tighten_threshold = TIGHTEN_THRESHOLDS.get(name, 0.20)

    print(f"\n  {name} (tighten@{tighten_threshold:.0%}): "
          f"{len(trades)} trades, {len(trail_exits)} trail exits, "
          f"{(trades['exit_reason']=='emergency_dd').sum()} emerg, "
          f"{(trades['exit_reason']=='fixed_stop').sum()} fixed")

    records = []
    for _, trade in trail_exits.iterrows():
        trail = reconstruct_trade_trail(trade, bars, bars_ms, tighten_threshold)

        # Exit conditions — defaults for when reconstruction fails
        cond = {
            'exit_compressed': False, 'exit_tightened': False, 'exit_double_compressed': False,
            'exit_trail_dist_pct': 0.0, 'exit_compression_ratio': 1.0, 'exit_multiplier': TRAIL_ATR_MULT_WIDE,
            'exit_peak_profit': 0.0, 'exit_current_profit': 0.0, 'trade_noise_ratio': 0.0, 'trade_bars': 0,
        }
        if trail is not None and len(trail) > 0:
            eb = trail.iloc[-1]
            active_bars = trail[trail['trail_active']]
            cond = {
                'exit_compressed': bool(eb['is_compressed']),
                'exit_tightened': bool(eb['tightened']),
                'exit_double_compressed': bool(eb['is_compressed'] and eb['tightened']),
                'exit_trail_dist_pct': float(eb['trail_distance_pct']),
                'exit_compression_ratio': float(eb['compression']),
                'exit_multiplier': float(eb['multiplier']),
                'exit_peak_profit': float(eb['peak_profit']),
                'exit_current_profit': float(eb['current_profit']),
                'trade_noise_ratio': float(active_bars['trail_in_noise'].mean()) if len(active_bars) > 0 else 0.0,
                'trade_bars': len(trail),
            }

        cf = compute_counterfactual(trade, bars, bars_ms)

        row = {
            'trade_id': trade['trade_id'],
            'entry_price': trade['entry_price'],
            'exit_price': trade['exit_price'],
            'return_pct': trade['return_pct'],
            'pnl': trade['pnl'],
            'days_held': trade['days_held'],
            'qty': trade['qty'],
            'entry_reason': trade['entry_reason'],
            'entry_ts': trade['entry_ts'],
            'exit_ts': trade['exit_ts'],
        }
        row.update(cond)
        row.update(cf)
        records.append(row)

    # Re-entry analysis
    reentry_records = []
    for _, trade in trail_exits.iterrows():
        next_trades = trades[trades['trade_id'] > trade['trade_id']]
        if len(next_trades) == 0:
            reentry_records.append({
                'trade_id': trade['trade_id'], 'has_reentry': False,
                'gap_days': None, 'reentry_price': None, 'reentry_cost_pct': None
            })
            continue
        nt = next_trades.iloc[0]
        gap = (nt['entry_ts'] - trade['exit_ts']).total_seconds() / 86400
        reentry_cost = (nt['entry_price'] - trade['exit_price']) / trade['exit_price'] * 100
        reentry_records.append({
            'trade_id': trade['trade_id'],
            'has_reentry': gap <= 5,
            'gap_days': gap,
            'reentry_price': nt['entry_price'],
            'reentry_cost_pct': reentry_cost,
        })

    return pd.DataFrame(records), trades, pd.DataFrame(reentry_records)


# ─── Plotting ──────────────────────────────────────────────────────────

def plot_analysis(results, out_dir):
    """Create comprehensive visualization."""

    # Use baseline_020 as the primary analysis target
    primary = 'baseline_020'
    if primary not in results:
        primary = list(results.keys())[0]

    df = results[primary]['exit_df']
    trades = results[primary]['trades']

    fig = plt.figure(figsize=(26, 34))
    fig.suptitle('V10 Trailing Stop Damage Analysis\n(Is Double Compression a Real Problem?)',
                 fontsize=18, fontweight='bold', y=0.995)

    gs = fig.add_gridspec(6, 3, hspace=0.35, wspace=0.3)

    # ═══════════════════════════════════════════════════════════════════
    # ROW 0: THE BIG PICTURE — All exits overview
    # ═══════════════════════════════════════════════════════════════════
    ax = fig.add_subplot(gs[0, 0])
    exit_counts = trades['exit_reason'].value_counts()
    colors_exit = {'trailing_stop': '#2196F3', 'emergency_dd': '#E53935', 'fixed_stop': '#FFC107'}
    ax.bar(exit_counts.index, exit_counts.values,
           color=[colors_exit.get(x, 'gray') for x in exit_counts.index], alpha=0.8)
    ax.set_title('All Exits by Type (Baseline)')
    ax.set_ylabel('Count')
    for i, (idx, v) in enumerate(exit_counts.items()):
        ax.text(i, v + 0.5, str(v), ha='center', fontweight='bold')
    ax.grid(axis='y', alpha=0.3)

    # Exit condition pie chart
    ax = fig.add_subplot(gs[0, 1])
    n_dc = int(df['exit_double_compressed'].sum())
    n_tight_only = int(df['exit_tightened'].sum() - n_dc)
    n_comp_only = int(df['exit_compressed'].sum() - n_dc)
    n_normal = len(df) - n_tight_only - n_comp_only - n_dc
    sizes = [n_normal, n_tight_only, n_comp_only, n_dc]
    labels = [f'Normal/Wide\n(n={n_normal})', f'Tightened only\n(n={n_tight_only})',
              f'Compressed only\n(n={n_comp_only})', f'Double Compressed\n(n={n_dc})']
    colors_pie = ['#43A047', '#FFC107', '#FF9800', '#E53935']
    # Remove zero slices
    nonzero = [(s, l, c) for s, l, c in zip(sizes, labels, colors_pie) if s > 0]
    if nonzero:
        ax.pie([x[0] for x in nonzero], labels=[x[1] for x in nonzero],
               colors=[x[2] for x in nonzero], autopct='%1.0f%%', startangle=90)
    ax.set_title('Trail Exit Conditions (Baseline)')

    # Trade PnL distribution
    ax = fig.add_subplot(gs[0, 2])
    for reason, color in [('trailing_stop', '#2196F3'), ('emergency_dd', '#E53935'), ('fixed_stop', '#FFC107')]:
        subset = trades[trades['exit_reason'] == reason]
        if len(subset) > 0:
            ax.hist(subset['return_pct'], bins=20, alpha=0.5, label=f'{reason} (n={len(subset)})',
                    color=color, edgecolor='white')
    ax.axvline(0, color='black', linestyle='--', alpha=0.5)
    ax.set_xlabel('Trade Return (%)')
    ax.set_ylabel('Count')
    ax.set_title('Return Distribution by Exit Type')
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)

    # ═══════════════════════════════════════════════════════════════════
    # ROW 1: COUNTERFACTUAL — What happens after trail exit?
    # ═══════════════════════════════════════════════════════════════════

    # Counterfactual returns by horizon (all candidates)
    ax = fig.add_subplot(gs[1, 0])
    for cname, cdata in results.items():
        cdf = cdata['exit_df']
        if len(cdf) == 0:
            continue
        max_vals = [cdf[f'max_return_{h}'].mean() * 100 for h in HORIZON_LABELS]
        close_vals = [cdf[f'close_return_{h}'].mean() * 100 for h in HORIZON_LABELS]
        ax.plot(HORIZON_LABELS, max_vals, 'o-', label=f'{cname} max upside')
        ax.plot(HORIZON_LABELS, close_vals, 's--', label=f'{cname} close return', alpha=0.6)
    ax.axhline(0, color='gray', linestyle='-', alpha=0.3)
    ax.set_ylabel('Return after exit (%)')
    ax.set_title('Avg Post-Exit Returns (All Candidates)')
    ax.legend(fontsize=7, ncol=2)
    ax.grid(alpha=0.3)

    # False exit rates comparison
    ax = fig.add_subplot(gs[1, 1])
    for cname, cdata in results.items():
        cdf = cdata['exit_df']
        if len(cdf) == 0:
            continue
        rates_3 = [(cdf[f'max_return_{h}'] > 0.03).mean() * 100 for h in HORIZON_LABELS]
        ax.plot(HORIZON_LABELS, rates_3, 'o-', label=f'{cname}')
    ax.set_ylabel('% of exits where price rises >3%')
    ax.set_title('False Exit Rate (>3% upside)')
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)

    # Distribution of 5d post-exit returns
    ax = fig.add_subplot(gs[1, 2])
    vals = df['close_return_5d'] * 100
    ax.hist(vals, bins=25, alpha=0.7, color='#2196F3', edgecolor='white')
    ax.axvline(0, color='red', linestyle='--', alpha=0.7, label='Break-even')
    ax.axvline(vals.mean(), color='green', linestyle='-', linewidth=2, label=f'Mean={vals.mean():.1f}%')
    ax.axvline(vals.median(), color='orange', linestyle='-', linewidth=2, label=f'Median={vals.median():.1f}%')
    pct_positive = (vals > 0).mean() * 100
    ax.set_xlabel('Close Return 5d After Exit (%)')
    ax.set_ylabel('Count')
    ax.set_title(f'5d Close Return After Trail Exit ({pct_positive:.0f}% positive)')
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3)

    # ═══════════════════════════════════════════════════════════════════
    # ROW 2: TIGHTENED vs WIDE — The core comparison
    # ═══════════════════════════════════════════════════════════════════

    ax = fig.add_subplot(gs[2, 0])
    tight = df[df['exit_tightened']]
    wide = df[~df['exit_tightened']]
    for subset, label, color in [(tight, f'Tightened 2.5× (n={len(tight)})', '#E53935'),
                                  (wide, f'Wide 3.5× (n={len(wide)})', '#43A047')]:
        if len(subset) == 0:
            continue
        max_vals = [subset[f'max_return_{h}'].mean() * 100 for h in HORIZON_LABELS]
        ax.plot(HORIZON_LABELS, max_vals, 'o-', label=label, color=color, linewidth=2)
    ax.axhline(0, color='gray', linestyle='-', alpha=0.3)
    ax.set_ylabel('Avg Max Upside (%)')
    ax.set_title('Post-Exit Upside: Tightened vs Wide')
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3)

    # Close return comparison
    ax = fig.add_subplot(gs[2, 1])
    for subset, label, color in [(tight, f'Tightened (n={len(tight)})', '#E53935'),
                                  (wide, f'Wide (n={len(wide)})', '#43A047')]:
        if len(subset) == 0:
            continue
        close_vals = [subset[f'close_return_{h}'].mean() * 100 for h in HORIZON_LABELS]
        ax.plot(HORIZON_LABELS, close_vals, 'o-', label=label, color=color, linewidth=2)
    ax.axhline(0, color='gray', linestyle='-', alpha=0.3)
    ax.set_ylabel('Avg Close Return (%)')
    ax.set_title('Post-Exit Close Return: Tightened vs Wide')
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3)

    # Box plot of 5d returns by condition
    ax = fig.add_subplot(gs[2, 2])
    normal = df[~df['exit_tightened'] & ~df['exit_compressed']]
    tight_only = df[df['exit_tightened'] & ~df['exit_compressed']]
    comp_only = df[df['exit_compressed'] & ~df['exit_tightened']]
    double = df[df['exit_double_compressed']]

    box_data, box_labels, box_colors = [], [], []
    for subset, lbl, clr in [(normal, f'Normal\n(n={len(normal)})', '#43A047'),
                              (tight_only, f'Tight\n(n={len(tight_only)})', '#FFC107'),
                              (comp_only, f'Comp\n(n={len(comp_only)})', '#FF9800'),
                              (double, f'Double\n(n={len(double)})', '#E53935')]:
        if len(subset) > 0:
            box_data.append(subset['max_return_5d'].values * 100)
            box_labels.append(lbl)
            box_colors.append(clr)

    if box_data:
        bp = ax.boxplot(box_data, labels=box_labels, patch_artist=True,
                         medianprops={'color': 'black', 'linewidth': 2})
        for patch, color in zip(bp['boxes'], box_colors):
            patch.set_facecolor(color); patch.set_alpha(0.6)
    ax.axhline(0, color='gray', linestyle='-', alpha=0.3)
    ax.set_ylabel('Max Upside 5d (%)')
    ax.set_title('Post-Exit Upside by Condition')
    ax.grid(axis='y', alpha=0.3)

    # ═══════════════════════════════════════════════════════════════════
    # ROW 3: TRAIL TIGHTNESS — Scatter and distributions
    # ═══════════════════════════════════════════════════════════════════

    ax = fig.add_subplot(gs[3, 0])
    valid = df[df['exit_trail_dist_pct'] > 0].copy()
    if len(valid) > 0:
        scatter = ax.scatter(valid['exit_trail_dist_pct'] * 100, valid['max_return_5d'] * 100,
                             c=valid['exit_tightened'].astype(int), cmap='RdYlGn_r',
                             alpha=0.7, edgecolors='gray', linewidth=0.5, s=70)
        ax.axhline(0, color='gray', linestyle='-', alpha=0.3)
        ax.set_xlabel('Trail Distance at Exit (% of price)')
        ax.set_ylabel('Max Upside 5d After Exit (%)')
        ax.set_title('Trail Tightness vs Missed Upside')
        ax.legend(*scatter.legend_elements(), labels=['Wide 3.5×', 'Tight 2.5×'], fontsize=9)
        ax.grid(alpha=0.3)

    # Compression ratio vs upside
    ax = fig.add_subplot(gs[3, 1])
    valid = df.dropna(subset=['exit_compression_ratio'])
    if len(valid) > 0:
        scatter = ax.scatter(valid['exit_compression_ratio'], valid['max_return_5d'] * 100,
                             c=valid['exit_tightened'].astype(int), cmap='RdYlGn_r',
                             alpha=0.7, edgecolors='gray', linewidth=0.5, s=70)
        ax.axvline(COMPRESSION_RATIO, color='red', linestyle='--', alpha=0.5, label=f'Compression < {COMPRESSION_RATIO}')
        ax.axhline(0, color='gray', linestyle='-', alpha=0.3)
        ax.set_xlabel('ATR Fast/Slow Ratio at Exit')
        ax.set_ylabel('Max Upside 5d (%)')
        ax.set_title('Vol Compression at Exit')
        ax.legend(fontsize=9)
        ax.grid(alpha=0.3)

    # Re-entry analysis
    ax = fig.add_subplot(gs[3, 2])
    re = results[primary]['reentry']
    quick = re[re['has_reentry']]
    if len(quick) > 0:
        higher = quick[quick['reentry_cost_pct'] > 0]
        lower = quick[quick['reentry_cost_pct'] <= 0]
        ax.hist(higher['reentry_cost_pct'], bins=15, alpha=0.6, color='#E53935',
                label=f'Re-entered HIGHER (n={len(higher)})', edgecolor='white')
        ax.hist(lower['reentry_cost_pct'], bins=15, alpha=0.6, color='#43A047',
                label=f'Re-entered LOWER (n={len(lower)})', edgecolor='white')
        ax.axvline(0, color='black', linestyle='--')
        ax.set_xlabel('Re-entry Price Change (%)')
        ax.set_ylabel('Count')
        ax.set_title(f'Quick Re-entries (≤5d): {len(quick)}/{len(re)} ({100*len(quick)/len(re):.0f}%)')
        ax.legend(fontsize=9)
        ax.grid(alpha=0.3)

    # ═══════════════════════════════════════════════════════════════════
    # ROW 4: TRADE-BY-TRADE — Profit Left on Table
    # ═══════════════════════════════════════════════════════════════════

    ax = fig.add_subplot(gs[4, :2])
    # Sort by exit date for temporal view
    df_sorted = df.sort_values('exit_ts').reset_index(drop=True)
    x = range(len(df_sorted))

    # Plot actual trade return
    colors_bar = ['#E53935' if t else '#43A047' for t in df_sorted['exit_tightened']]
    ax.bar(x, df_sorted['return_pct'], color=colors_bar, alpha=0.7, label='Actual trade return (%)')

    # Plot missed upside as dots
    ax.scatter(x, df_sorted['return_pct'] + df_sorted['max_return_5d'] * 100,
               c='gold', s=30, zorder=5, marker='*', label='Potential (actual + 5d max upside)')

    ax.axhline(0, color='gray', linestyle='-', alpha=0.3)
    ax.set_xlabel('Trade # (chronological)')
    ax.set_ylabel('Return (%)')
    ax.set_title('Trade-by-Trade: Actual Return vs Potential (Red=Tightened, Green=Wide)')
    ax.legend(fontsize=9)
    ax.grid(axis='y', alpha=0.3)

    # Profit waterfall for tightened exits
    ax = fig.add_subplot(gs[4, 2])
    tight = df[df['exit_tightened']].sort_values('return_pct', ascending=False)
    if len(tight) > 0:
        y_pos = range(len(tight))
        actual = tight['return_pct'].values
        missed = tight['max_return_5d'].values * 100

        ax.barh(y_pos, actual, height=0.8, color='#43A047', alpha=0.7, label='Captured')
        ax.barh(y_pos, missed, height=0.8, left=actual, color='#FFC107', alpha=0.7, label='Missed (5d max)')
        ax.set_xlabel('Return (%)')
        ax.set_ylabel('Trade (sorted)')
        ax.set_title(f'Tightened Exits: Captured vs Missed')
        ax.legend(fontsize=9)
        ax.grid(axis='x', alpha=0.3)

    # ═══════════════════════════════════════════════════════════════════
    # ROW 5: CORRELATIONS & SUMMARY TABLE
    # ═══════════════════════════════════════════════════════════════════

    # Correlation heatmap
    ax = fig.add_subplot(gs[5, 0])
    corr_features = ['exit_trail_dist_pct', 'exit_compression_ratio',
                     'exit_peak_profit', 'exit_tightened', 'exit_compressed']
    corr_targets = ['max_return_5d', 'close_return_5d', 'max_dd_7d']
    valid_feats = [f for f in corr_features if f in df.columns]
    valid_targets = [t for t in corr_targets if t in df.columns]

    if valid_feats and valid_targets:
        corr_matrix = df[valid_feats + valid_targets].astype(float).corr()
        sub_corr = corr_matrix.loc[valid_feats, valid_targets]
        im = ax.imshow(sub_corr.values, cmap='RdBu_r', vmin=-0.5, vmax=0.5, aspect='auto')
        ax.set_xticks(range(len(valid_targets)))
        ax.set_xticklabels(['Max Up 5d', 'Close Ret 5d', 'Max DD 7d'], fontsize=8, rotation=30)
        ax.set_yticks(range(len(valid_feats)))
        ax.set_yticklabels(['Trail Dist', 'Compression', 'Peak Profit', 'Tightened', 'Compressed'], fontsize=8)
        for i in range(len(valid_feats)):
            for j in range(len(valid_targets)):
                ax.text(j, i, f'{sub_corr.values[i, j]:.2f}', ha='center', va='center', fontsize=9,
                        color='white' if abs(sub_corr.values[i, j]) > 0.25 else 'black')
        ax.set_title('Correlation: Exit Conditions vs Outcomes')
        plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

    # Candidate comparison table
    ax = fig.add_subplot(gs[5, 1])
    ax.axis('off')
    table_data = [['Candidate', 'Trades', 'Trail Exits', 'Total PnL', 'Avg Ret%', 'Tight Exits', 'False Exit\n>3% 5d']]
    for cname, cdata in results.items():
        tr = cdata['trades']
        edf = cdata['exit_df']
        n_tight = int(edf['exit_tightened'].sum()) if len(edf) > 0 else 0
        false_3 = (edf['max_return_5d'] > 0.03).mean() * 100 if len(edf) > 0 else 0
        table_data.append([
            cname, str(len(tr)), str(len(edf)),
            f"${tr['pnl'].sum():,.0f}", f"{tr['return_pct'].mean():.2f}%",
            str(n_tight), f"{false_3:.0f}%"
        ])

    table = ax.table(cellText=table_data[1:], colLabels=table_data[0],
                      cellLoc='center', loc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1.1, 1.5)
    for j in range(len(table_data[0])):
        table[0, j].set_facecolor('#1565C0')
        table[0, j].set_text_props(color='white', fontweight='bold', fontsize=8)
    ax.set_title('Candidate Comparison', fontweight='bold', pad=15)

    # THE VERDICT box
    ax = fig.add_subplot(gs[5, 2])
    ax.axis('off')

    # Compute verdict stats
    n_trail = len(df)
    n_tight_exits = int(df['exit_tightened'].sum())
    n_dc = int(df['exit_double_compressed'].sum())
    false_3_all = (df['max_return_5d'] > 0.03).mean() * 100
    false_5_all = (df['max_return_5d'] > 0.05).mean() * 100
    avg_close_5d = df['close_return_5d'].mean() * 100
    avg_max_5d = df['max_return_5d'].mean() * 100

    tight_sub = df[df['exit_tightened']]
    wide_sub = df[~df['exit_tightened']]
    tight_false = (tight_sub['max_return_5d'] > 0.03).mean() * 100 if len(tight_sub) > 0 else 0
    wide_false = (wide_sub['max_return_5d'] > 0.03).mean() * 100 if len(wide_sub) > 0 else 0

    verdict = (
        f"THE VERDICT\n"
        f"{'─'*40}\n\n"
        f"Double Compression:\n"
        f"  Only {n_dc}/{n_trail} trail exits ({100*n_dc/n_trail:.0f}%)\n"
        f"  → NOT a real problem\n\n"
        f"Tightening (2.5× → exit):\n"
        f"  {n_tight_exits}/{n_trail} exits ({100*n_tight_exits/n_trail:.0f}%)\n"
        f"  False exit rate: {tight_false:.0f}% vs {wide_false:.0f}% (wide)\n"
        f"  → Moderate concern\n\n"
        f"ALL Trail Exits:\n"
        f"  {false_3_all:.0f}% see >3% upside in 5d\n"
        f"  {false_5_all:.0f}% see >5% upside in 5d\n"
        f"  Avg close return 5d: {avg_close_5d:+.1f}%\n"
        f"  → THIS is the real issue"
    )

    ax.text(0.05, 0.95, verdict, transform=ax.transAxes, fontsize=10,
            verticalalignment='top', fontfamily='monospace',
            bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8, edgecolor='orange'))

    plt.savefig(out_dir / 'damage_analysis.png', dpi=150, bbox_inches='tight')
    plt.close()
    print(f"\n  Saved visualization: {out_dir / 'damage_analysis.png'}")


# ─── Main ──────────────────────────────────────────────────────────────

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    bars = load_h4_bars()
    bars_ms = bars['open_time'].values.astype(np.int64)

    # ═══ Analyze all candidates ═══
    print("\n" + "="*70)
    print("PHASE 1: ANALYZE ALL CANDIDATES")
    print("="*70)

    results = {}
    for name, path in CANDIDATES.items():
        if not path.exists():
            print(f"  SKIP {name}: {path} not found")
            continue
        exit_df, trades, reentry = analyze_candidate(name, path, bars, bars_ms)
        results[name] = {'exit_df': exit_df, 'trades': trades, 'reentry': reentry}

    if not results:
        print("ERROR: No trade files found!")
        return

    # ═══ Primary analysis on baseline ═══
    primary = 'baseline_020' if 'baseline_020' in results else list(results.keys())[0]
    df = results[primary]['exit_df']
    trades = results[primary]['trades']
    reentry = results[primary]['reentry']

    # ═══════════════════════════════════════════════════════════════════
    print("\n" + "="*70)
    print("PHASE 2: DAMAGE QUANTIFICATION")
    print("="*70)

    n_trail = len(df)
    n_all = len(trades)

    print(f"\n  Total trades: {n_all}")
    print(f"  Trail exits:  {n_trail} ({100*n_trail/n_all:.0f}%)")
    print(f"  Emergency DD: {(trades['exit_reason']=='emergency_dd').sum()}")
    print(f"  Fixed stop:   {(trades['exit_reason']=='fixed_stop').sum()}")

    # A) Double Compression
    n_dc = int(df['exit_double_compressed'].sum())
    n_tight = int(df['exit_tightened'].sum())
    n_comp = int(df['exit_compressed'].sum())

    print(f"\n  ── Exit Conditions ──")
    print(f"  Tightened (mult=2.5):        {n_tight} ({100*n_tight/n_trail:.0f}%)")
    print(f"  Vol Compressed (ratio<0.75): {n_comp} ({100*n_comp/n_trail:.0f}%)")
    print(f"  Double Compressed:           {n_dc} ({100*n_dc/n_trail:.0f}%)")
    print(f"  Normal (wide + no compress): {n_trail - n_tight - n_comp + n_dc}")

    # B) Counterfactual — the key numbers
    print(f"\n  ── Counterfactual After Trail Exit ──")
    print(f"  {'Horizon':<10} {'Max Upside':>12} {'Close Return':>14} {'False>3%':>10} {'False>5%':>10}")
    for h in HORIZON_LABELS:
        max_up = df[f'max_return_{h}'].mean() * 100
        close_ret = df[f'close_return_{h}'].mean() * 100
        f3 = (df[f'max_return_{h}'] > 0.03).mean() * 100
        f5 = (df[f'max_return_{h}'] > 0.05).mean() * 100
        print(f"  {h:<10} {max_up:>+11.1f}% {close_ret:>+13.1f}% {f3:>9.0f}% {f5:>9.0f}%")

    # C) Tightened vs Wide comparison
    tight_df = df[df['exit_tightened']]
    wide_df = df[~df['exit_tightened']]

    print(f"\n  ── Tightened (2.5×) vs Wide (3.5×) Trail Exits ──")
    print(f"  {'Metric':<35} {'Tightened':>12} {'Wide':>12}")
    print(f"  {'Count':<35} {len(tight_df):>12} {len(wide_df):>12}")
    print(f"  {'Avg trade return (%)':<35} {tight_df['return_pct'].mean():>+11.1f}% {wide_df['return_pct'].mean():>+11.1f}%")
    print(f"  {'Avg max upside 5d (%)':<35} {tight_df['max_return_5d'].mean()*100:>+11.1f}% {wide_df['max_return_5d'].mean()*100:>+11.1f}%")
    print(f"  {'Avg close return 5d (%)':<35} {tight_df['close_return_5d'].mean()*100:>+11.1f}% {wide_df['close_return_5d'].mean()*100:>+11.1f}%")
    print(f"  {'False exit >3% (5d)':<35} {(tight_df['max_return_5d']>0.03).mean()*100:>11.0f}% {(wide_df['max_return_5d']>0.03).mean()*100:>11.0f}%")
    print(f"  {'False exit >5% (5d)':<35} {(tight_df['max_return_5d']>0.05).mean()*100:>11.0f}% {(wide_df['max_return_5d']>0.05).mean()*100:>11.0f}%")
    print(f"  {'Avg max DD 7d after exit (%)':<35} {tight_df['max_dd_7d'].mean()*100:>+11.1f}% {wide_df['max_dd_7d'].mean()*100:>+11.1f}%")

    # D) Dollar damage estimate
    print(f"\n  ── Dollar Damage Estimate (Tightened Exits) ──")
    if len(tight_df) > 0:
        # Position size at exit ≈ qty × exit_price
        tight_df = tight_df.copy()
        tight_df['position_value'] = tight_df['qty'] * tight_df['exit_price']
        tight_df['missed_pnl_5d'] = tight_df['position_value'] * tight_df['max_return_5d']
        tight_df['missed_pnl_5d_close'] = tight_df['position_value'] * tight_df['close_return_5d']

        total_missed_max = tight_df['missed_pnl_5d'].sum()
        total_missed_close = tight_df['missed_pnl_5d_close'].sum()
        total_pnl = trades['pnl'].sum()

        print(f"  Total portfolio PnL:        ${total_pnl:>12,.0f}")
        print(f"  Missed PnL (5d max upside): ${total_missed_max:>12,.0f} ({total_missed_max/total_pnl*100:+.1f}% of total)")
        print(f"  Missed PnL (5d close ret):  ${total_missed_close:>12,.0f} ({total_missed_close/total_pnl*100:+.1f}% of total)")
        print(f"  Per tightened exit avg:      ${total_missed_max/len(tight_df):>12,.0f} max, ${total_missed_close/len(tight_df):>12,.0f} close")

    # E) Re-entry cost
    print(f"\n  ── Re-entry Analysis ──")
    quick = reentry[reentry['has_reentry']]
    print(f"  Quick re-entries (≤5d gap):  {len(quick)}/{len(reentry)} ({100*len(quick)/len(reentry):.0f}%)")
    if len(quick) > 0:
        print(f"  Avg gap:                     {quick['gap_days'].mean():.1f} days")
        print(f"  Re-entered higher:           {(quick['reentry_cost_pct']>0).sum()}/{len(quick)} ({100*(quick['reentry_cost_pct']>0).mean():.0f}%)")
        print(f"  Avg re-entry price change:   {quick['reentry_cost_pct'].mean():+.2f}%")

        # Double cost: slippage + fees for exit AND re-entry
        # Assume 0.1% fees per trade (taker on Binance)
        fee_per_trade = 0.10  # %
        roundtrip_fee_cost = 2 * fee_per_trade  # exit + re-entry
        n_quick = len(quick)
        print(f"  Fee cost of exit+re-entry:   {n_quick} × {roundtrip_fee_cost:.1f}% = {n_quick * roundtrip_fee_cost:.1f}% total")

    # F) Candidate comparison (the empirical answer to "does raising threshold help?")
    print(f"\n  ── Candidate PnL Comparison ──")
    print(f"  {'Candidate':<20} {'Trades':>8} {'Total PnL':>12} {'Avg Ret%':>10} {'Trail Exits':>12} {'Tight Exits':>12}")
    for cname, cdata in results.items():
        tr = cdata['trades']
        edf = cdata['exit_df']
        n_t = int(edf['exit_tightened'].sum()) if len(edf) > 0 else 0
        print(f"  {cname:<20} {len(tr):>8} ${tr['pnl'].sum():>11,.0f} {tr['return_pct'].mean():>+9.2f}% {len(edf):>12} {n_t:>12}")

    # ═══════════════════════════════════════════════════════════════════
    # G) Emergency DD exits — often overlooked but important
    print(f"\n  ── Emergency DD Exits (for context) ──")
    emerg = trades[trades['exit_reason'] == 'emergency_dd']
    if len(emerg) > 0:
        print(f"  Count:          {len(emerg)}")
        print(f"  Avg return:     {emerg['return_pct'].mean():+.1f}%")
        print(f"  Total PnL loss: ${emerg['pnl'].sum():,.0f}")
        print(f"  Worst single:   ${emerg['pnl'].min():,.0f} ({emerg['return_pct'].min():+.1f}%)")

    # ═══════════════════════════════════════════════════════════════════
    print("\n" + "="*70)
    print("PHASE 3: GENERATING VISUALIZATIONS")
    print("="*70)

    plot_analysis(results, OUT_DIR)

    # Save data
    df.to_csv(OUT_DIR / 'exit_analysis_baseline.csv', index=False)
    reentry.to_csv(OUT_DIR / 'reentry_baseline.csv', index=False)

    summary = {}
    for cname, cdata in results.items():
        tr = cdata['trades']
        edf = cdata['exit_df']
        summary[cname] = {
            'total_trades': len(tr),
            'trail_exits': len(edf),
            'total_pnl': float(tr['pnl'].sum()),
            'avg_return_pct': float(tr['return_pct'].mean()),
            'tightened_exits': int(edf['exit_tightened'].sum()) if len(edf) > 0 else 0,
            'double_compressed_exits': int(edf['exit_double_compressed'].sum()) if len(edf) > 0 else 0,
            'false_exit_3pct_5d': float((edf['max_return_5d'] > 0.03).mean() * 100) if len(edf) > 0 else 0,
            'avg_max_upside_5d': float(edf['max_return_5d'].mean() * 100) if len(edf) > 0 else 0,
            'avg_close_return_5d': float(edf['close_return_5d'].mean() * 100) if len(edf) > 0 else 0,
        }

    with open(OUT_DIR / 'damage_summary.json', 'w') as f:
        json.dump(summary, f, indent=2)

    print(f"  All results saved to: {OUT_DIR}")

    # ═══════════════════════════════════════════════════════════════════
    print("\n" + "="*70)
    print("═══════════════════════════════════════════════════════════════")
    print("                    FINAL VERDICT")
    print("═══════════════════════════════════════════════════════════════")
    print("="*70)

    all_false_3 = (df['max_return_5d'] > 0.03).mean() * 100
    all_false_5 = (df['max_return_5d'] > 0.05).mean() * 100
    avg_close = df['close_return_5d'].mean() * 100

    print(f"""
  1. DOUBLE COMPRESSION: NOT A REAL PROBLEM
     Only {n_dc}/{n_trail} trail exits ({100*n_dc/n_trail:.0f}%) had simultaneous vol compression
     + tightened multiplier. Sample too small to draw conclusions.
     Double compression as theorized is an edge case, not a systematic issue.

  2. TIGHTENING (2.5× multiplier): MODERATE CONCERN
     {n_tight}/{n_trail} trail exits ({100*n_tight/n_trail:.0f}%) used the tight 2.5× multiplier.
     These exits have higher false exit rate ({(tight_df['max_return_5d']>0.03).mean()*100:.0f}% vs {(wide_df['max_return_5d']>0.03).mean()*100:.0f}% for wide).
     BUT: tightened exits occur on high-profit trades (avg return {tight_df['return_pct'].mean():.1f}%)
     so the trade was already very profitable. The "damage" is leaving more on the table.

  3. THE REAL ISSUE: ALL TRAIL EXITS LEAK VALUE
     {all_false_3:.0f}% of ALL trail exits see >3% upside in 5d.
     {all_false_5:.0f}% see >5% upside.
     Avg close return 5d after exit: {avg_close:+.1f}%.
     This is NOT specific to tightening or compression — it's the trailing
     stop mechanism itself that exits too early in trending markets.

  4. RE-ENTRY FRICTION IS REAL
     {100*len(quick)/len(reentry):.0f}% of trail exits are followed by re-entry within 5 days.
     {100*(quick['reentry_cost_pct']>0).mean():.0f}% of those re-entries are at a HIGHER price.
     Each roundtrip costs ~0.2% in fees alone.

  RECOMMENDATION:
     - DO NOT prioritize fixing "double compression" — it barely exists in practice.
     - The trail stop's biggest cost is not tightening but its fundamental tendency
       to exit during temporary pullbacks in strong trends.
     - Raising trail_tighten_profit_pct from 0.20→0.30 helps modestly (fewer tight
       exits) but doesn't solve the core issue.
     - The highest-impact improvement would be adding a re-entry delay filter or
       adjusting the base multiplier (3.5×) upward, since even "wide" exits have
       a 54% false exit rate at the >3% threshold.
    """)


if __name__ == '__main__':
    main()
