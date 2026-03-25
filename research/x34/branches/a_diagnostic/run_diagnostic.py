#!/usr/bin/env python3
"""Phase 2 — Diagnostic: Q-VDO-RH Mode A vs VDO gốc.

Runs both indicators on full H4 data (2017-08 → 2026-02),
computes comparative statistics, divergence analysis, and plots.

Output: branches/a_diagnostic/results/ + branches/a_diagnostic/figures/

STOP criteria:
  - Spearman ρ > 0.95 → STOP ("no improvement expected")
FLAG (not STOP):
  - ρ < 0.3 → Q-VDO-RH is a DIFFERENT indicator, not a "fix"
GO criteria:
  - ρ ≤ 0.95
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
from scipy import stats
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Setup paths
# ---------------------------------------------------------------------------
PROJECT = Path(__file__).resolve().parents[4]  # btc-spot-dev/
sys.path.insert(0, str(PROJECT))

from v10.core.data import DataFeed
from research.x34.shared.indicators.q_vdo_rh import q_vdo_rh, _ema

RESULTS_DIR = Path(__file__).resolve().parent / "results"
FIGURES_DIR = Path(__file__).resolve().parent / "figures"
RESULTS_DIR.mkdir(exist_ok=True)
FIGURES_DIR.mkdir(exist_ok=True)

CSV_PATH = PROJECT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv"

# ---------------------------------------------------------------------------
# VDO gốc (copied from strategies/vtrend/strategy.py, verbatim)
# ---------------------------------------------------------------------------

def _vdo_original(close, high, low, volume, taker_buy, fast, slow):
    """Volume Delta Oscillator: EMA(vdr, fast) - EMA(vdr, slow)."""
    n = len(close)
    has_taker = taker_buy is not None and np.any(taker_buy > 0)
    if has_taker:
        taker_sell = volume - taker_buy
        vdr = np.zeros(n)
        mask = volume > 0
        vdr[mask] = (taker_buy[mask] - taker_sell[mask]) / volume[mask]
    else:
        spread = high - low
        vdr = np.zeros(n)
        mask = spread > 0
        vdr[mask] = (close[mask] - low[mask]) / spread[mask] * 2.0 - 1.0
    return _ema(vdr, fast) - _ema(vdr, slow)


# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------

def load_h4_arrays(feed: DataFeed):
    """Extract parallel numpy arrays from H4 bars."""
    bars = feed.h4_bars
    n = len(bars)
    ts = np.array([b.open_time for b in bars], dtype=np.int64)
    close = np.array([b.close for b in bars])
    high = np.array([b.high for b in bars])
    low = np.array([b.low for b in bars])
    volume = np.array([b.volume for b in bars])
    taker_buy_base = np.array([b.taker_buy_base_vol for b in bars])
    quote_vol = np.array([b.quote_volume for b in bars])
    taker_buy_quote = np.array([b.taker_buy_quote_vol for b in bars])
    return dict(
        ts=ts, close=close, high=high, low=low, volume=volume,
        taker_buy_base=taker_buy_base, quote_vol=quote_vol,
        taker_buy_quote=taker_buy_quote, n=n,
    )


def ts_to_dates(ts_ms):
    """Convert epoch-ms array to datetime array for plotting."""
    return [datetime.fromtimestamp(t / 1000, tz=timezone.utc) for t in ts_ms]


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------

def compute_stats(vdo_orig, qvdo_result, warmup=60):
    """Compute comparison statistics, skipping warmup bars."""
    m = qvdo_result.momentum[warmup:]
    v = vdo_orig[warmup:]
    theta = qvdo_result.theta[warmup:]

    # 1. Spearman rank correlation
    spearman_r, spearman_p = stats.spearmanr(v, m)

    # 2. Direction agreement
    both_valid = (v != 0) | (m != 0)
    if np.any(both_valid):
        agree = np.sign(v[both_valid]) == np.sign(m[both_valid])
        direction_agreement = float(np.mean(agree))
    else:
        direction_agreement = 1.0

    # 3. Signal frequency
    vdo_trigger = v > 0  # VDO original: entry when > 0
    qvdo_trigger = m > theta  # Q-VDO-RH: entry when m > theta
    n_vdo_on = int(np.sum(vdo_trigger))
    n_qvdo_on = int(np.sum(qvdo_trigger))
    freq_ratio = n_qvdo_on / max(n_vdo_on, 1)

    # 4. Distribution stats
    vdo_stats = dict(
        mean=float(np.mean(v)), std=float(np.std(v)),
        min=float(np.min(v)), max=float(np.max(v)),
        pct_positive=float(np.mean(v > 0)),
    )
    qvdo_stats = dict(
        mean=float(np.mean(m)), std=float(np.std(m)),
        min=float(np.min(m)), max=float(np.max(m)),
        pct_positive=float(np.mean(m > 0)),
    )

    return dict(
        spearman_r=round(spearman_r, 6),
        spearman_p=float(f"{spearman_p:.2e}"),
        direction_agreement=round(direction_agreement, 4),
        n_bars=len(v),
        vdo_trigger_count=n_vdo_on,
        qvdo_trigger_count=n_qvdo_on,
        trigger_freq_ratio=round(freq_ratio, 4),
        vdo_distribution=vdo_stats,
        qvdo_distribution=qvdo_stats,
    )


# ---------------------------------------------------------------------------
# Divergence analysis
# ---------------------------------------------------------------------------

def divergence_analysis(vdo_orig, qvdo_result, close, atr_period=60, warmup=60):
    """Classify divergence bars by regime."""
    m = qvdo_result.momentum[warmup:]
    theta = qvdo_result.theta[warmup:]
    v = vdo_orig[warmup:]
    c = close[warmup:]

    # Simple regime classification using rolling volatility
    # ATR proxy: rolling std of returns
    rets = np.diff(np.log(c))
    roll_vol = np.full(len(c), np.nan)
    for i in range(atr_period, len(rets)):
        roll_vol[i + 1] = np.std(rets[i - atr_period + 1:i + 1])

    vol_median = np.nanmedian(roll_vol)
    high_vol = roll_vol > vol_median

    # Trend: 60-bar EMA direction
    ema60 = _ema(c, 60)
    trending_up = c > ema60

    # Divergence types
    # Type 1: VDO > 0 but Q-VDO-RH < theta (VDO says go, Q-VDO says no)
    type1 = (v > 0) & (m <= theta)
    # Type 2: VDO <= 0 but Q-VDO-RH > theta (Q-VDO says go, VDO says no)
    type2 = (v <= 0) & (m > theta)

    valid = ~np.isnan(roll_vol)

    def classify(mask):
        mask_valid = mask & valid
        total = int(np.sum(mask_valid))
        if total == 0:
            return dict(total=0, high_vol=0, low_vol=0, trend_up=0, trend_down=0)
        return dict(
            total=total,
            high_vol=int(np.sum(mask_valid & high_vol)),
            low_vol=int(np.sum(mask_valid & ~high_vol)),
            trend_up=int(np.sum(mask_valid & trending_up)),
            trend_down=int(np.sum(mask_valid & ~trending_up)),
        )

    return dict(
        vdo_yes_qvdo_no=classify(type1),
        vdo_no_qvdo_yes=classify(type2),
        agreement_both_on=int(np.sum((v > 0) & (m > theta))),
        agreement_both_off=int(np.sum((v <= 0) & (m <= theta))),
    )


# ---------------------------------------------------------------------------
# Plots
# ---------------------------------------------------------------------------

def plot_overlay_period(dates, vdo, momentum, theta, close,
                        start_idx, end_idx, title, fname):
    """Overlay VDO vs Q-VDO-RH momentum for a specific period."""
    fig, axes = plt.subplots(3, 1, figsize=(14, 8), sharex=True,
                             gridspec_kw={"height_ratios": [2, 1, 1]})
    sl = slice(start_idx, end_idx)
    d = dates[sl]

    # Price
    axes[0].plot(d, close[sl], color="black", linewidth=0.8)
    axes[0].set_ylabel("Price (USDT)")
    axes[0].set_title(title)

    # VDO original
    axes[1].plot(d, vdo[sl], color="blue", linewidth=0.7, label="VDO orig")
    axes[1].axhline(0, color="gray", linestyle="--", linewidth=0.5)
    axes[1].set_ylabel("VDO")
    axes[1].legend(loc="upper right", fontsize=8)

    # Q-VDO-RH momentum + theta
    axes[2].plot(d, momentum[sl], color="red", linewidth=0.7, label="Q-VDO-RH m")
    axes[2].plot(d, theta[sl], color="orange", linewidth=0.5, linestyle="--",
                 label="θ")
    axes[2].plot(d, -theta[sl], color="orange", linewidth=0.5, linestyle="--")
    axes[2].axhline(0, color="gray", linestyle="--", linewidth=0.5)
    axes[2].set_ylabel("Q-VDO-RH")
    axes[2].legend(loc="upper right", fontsize=8)

    axes[2].xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    plt.tight_layout()
    fig.savefig(FIGURES_DIR / fname, dpi=150)
    plt.close(fig)


def plot_theta_evolution(dates, theta, fname="theta_evolution.png"):
    """Adaptive threshold θ over full period."""
    fig, ax = plt.subplots(figsize=(14, 4))
    ax.plot(dates, theta, color="orange", linewidth=0.5)
    ax.set_ylabel("θ (adaptive threshold)")
    ax.set_title("Q-VDO-RH Adaptive Threshold Evolution")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    plt.tight_layout()
    fig.savefig(FIGURES_DIR / fname, dpi=150)
    plt.close(fig)


def plot_scatter(vdo, momentum, fname="scatter_vdo_vs_qvdo.png"):
    """Scatter plot: VDO vs Q-VDO-RH momentum at each bar."""
    fig, ax = plt.subplots(figsize=(8, 8))
    ax.scatter(vdo, momentum, s=1, alpha=0.3, color="steelblue")
    ax.set_xlabel("VDO original")
    ax.set_ylabel("Q-VDO-RH momentum")
    ax.set_title("VDO vs Q-VDO-RH momentum (per bar)")
    ax.axhline(0, color="gray", linestyle="--", linewidth=0.5)
    ax.axvline(0, color="gray", linestyle="--", linewidth=0.5)
    plt.tight_layout()
    fig.savefig(FIGURES_DIR / fname, dpi=150)
    plt.close(fig)


def plot_histograms(vdo, momentum, fname="histograms.png"):
    """Side-by-side histograms of VDO vs Q-VDO-RH momentum."""
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))

    axes[0].hist(vdo, bins=100, color="blue", alpha=0.7, edgecolor="none")
    axes[0].set_title("VDO original (bounded [-1,1])")
    axes[0].set_xlabel("VDO value")

    axes[1].hist(momentum, bins=100, color="red", alpha=0.7, edgecolor="none")
    axes[1].set_title("Q-VDO-RH momentum (unbounded)")
    axes[1].set_xlabel("momentum value")

    plt.tight_layout()
    fig.savefig(FIGURES_DIR / fname, dpi=150)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("Loading data...")
    feed = DataFeed(CSV_PATH)
    d = load_h4_arrays(feed)
    print(f"  H4 bars: {d['n']}")

    # --- Compute indicators ---
    print("Computing VDO original (fast=12, slow=28)...")
    vdo_orig = _vdo_original(
        d["close"], d["high"], d["low"], d["volume"],
        d["taker_buy_base"], fast=12, slow=28,
    )

    print("Computing Q-VDO-RH Mode A (fast=12, slow=28, k=1.0)...")
    qvdo = q_vdo_rh(
        d["taker_buy_quote"], d["quote_vol"],
        fast=12, slow=28, k=1.0,
    )

    # --- Statistics ---
    print("\nComputing statistics...")
    warmup = 60
    st = compute_stats(vdo_orig, qvdo, warmup=warmup)

    print(f"\n{'='*60}")
    print("DIAGNOSTIC RESULTS")
    print(f"{'='*60}")
    print(f"  Bars (post-warmup):    {st['n_bars']}")
    print(f"  Spearman ρ:            {st['spearman_r']}")
    print(f"  Spearman p-value:      {st['spearman_p']}")
    print(f"  Direction agreement:   {st['direction_agreement']:.1%}")
    print(f"  VDO trigger bars:      {st['vdo_trigger_count']}")
    print(f"  Q-VDO-RH trigger bars: {st['qvdo_trigger_count']}")
    print(f"  Trigger freq ratio:    {st['trigger_freq_ratio']:.2f} "
          f"({'OK' if 0.5 <= st['trigger_freq_ratio'] <= 2.0 else 'FLAG'})")

    # --- STOP/FLAG check ---
    verdict = "GO"
    flags = []
    if st["spearman_r"] > 0.95:
        verdict = "STOP"
        flags.append("ρ > 0.95 → indicators near-identical → no improvement expected")
    if st["spearman_r"] < 0.3:
        flags.append("FLAG: ρ < 0.3 → Q-VDO-RH is a DIFFERENT indicator, not a 'fix'")
    if st["trigger_freq_ratio"] < 0.5:
        flags.append(f"FLAG: Q-VDO-RH triggers {st['trigger_freq_ratio']:.0%} of VDO "
                     f"(< 50%) — much more selective")
    if st["trigger_freq_ratio"] > 2.0:
        flags.append(f"FLAG: Q-VDO-RH triggers {st['trigger_freq_ratio']:.0%} of VDO "
                     f"(> 200%) — much less selective")

    print(f"\n  VERDICT: {verdict}")
    for f in flags:
        print(f"  {f}")

    # --- Divergence ---
    print("\nDivergence analysis...")
    div = divergence_analysis(vdo_orig, qvdo, d["close"], warmup=warmup)

    print(f"  VDO=on, Q-VDO=off: {div['vdo_yes_qvdo_no']['total']} bars")
    print(f"    high-vol: {div['vdo_yes_qvdo_no']['high_vol']}, "
          f"low-vol: {div['vdo_yes_qvdo_no']['low_vol']}")
    print(f"    trend-up: {div['vdo_yes_qvdo_no']['trend_up']}, "
          f"trend-down: {div['vdo_yes_qvdo_no']['trend_down']}")
    print(f"  VDO=off, Q-VDO=on: {div['vdo_no_qvdo_yes']['total']} bars")
    print(f"    high-vol: {div['vdo_no_qvdo_yes']['high_vol']}, "
          f"low-vol: {div['vdo_no_qvdo_yes']['low_vol']}")
    print(f"    trend-up: {div['vdo_no_qvdo_yes']['trend_up']}, "
          f"trend-down: {div['vdo_no_qvdo_yes']['trend_down']}")
    print(f"  Both on:  {div['agreement_both_on']} bars")
    print(f"  Both off: {div['agreement_both_off']} bars")

    # --- Save results ---
    results = dict(
        params=dict(fast=12, slow=28, k=1.0, warmup=warmup),
        statistics=st,
        divergence=div,
        verdict=verdict,
        flags=flags,
    )
    results_path = RESULTS_DIR / "diagnostic_results.json"
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved: {results_path}")

    # --- Plots ---
    print("\nGenerating plots...")
    dates = ts_to_dates(d["ts"])

    # Find period indices for bull, bear, chop
    # Bull: 2020-10 to 2021-04 (pre-ATH run)
    # Bear: 2022-01 to 2022-07 (post-ATH crash)
    # Chop: 2023-06 to 2023-12 (range-bound)
    def find_idx(year, month):
        target = datetime(year, month, 1, tzinfo=timezone.utc)
        target_ms = int(target.timestamp() * 1000)
        return int(np.searchsorted(d["ts"], target_ms))

    periods = [
        (find_idx(2020, 10), find_idx(2021, 5), "Bull: 2020-10 to 2021-04", "overlay_bull.png"),
        (find_idx(2022, 1), find_idx(2022, 8), "Bear: 2022-01 to 2022-07", "overlay_bear.png"),
        (find_idx(2023, 6), find_idx(2024, 1), "Chop: 2023-06 to 2023-12", "overlay_chop.png"),
    ]

    for si, ei, title, fname in periods:
        plot_overlay_period(dates, vdo_orig, qvdo.momentum, qvdo.theta,
                           d["close"], si, ei, title, fname)
        print(f"  {fname}")

    plot_theta_evolution(dates[warmup:], qvdo.theta[warmup:])
    print("  theta_evolution.png")

    plot_scatter(vdo_orig[warmup:], qvdo.momentum[warmup:])
    print("  scatter_vdo_vs_qvdo.png")

    plot_histograms(vdo_orig[warmup:], qvdo.momentum[warmup:])
    print("  histograms.png")

    print(f"\n{'='*60}")
    print(f"Phase 2 diagnostic complete. Verdict: {verdict}")
    if verdict == "STOP":
        print("STOP: Indicators too similar. No improvement expected.")
        return 1
    print("GO → Phase 3")
    print(f"{'='*60}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
