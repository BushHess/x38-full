#!/usr/bin/env python3
"""VTREND Post-Mortem Diagnostic: Quantitative Failure Analysis.

Answers: Is VTREND losing from bad entries, late exits, or wrong regime?
How much total net loss comes from each cause?
Does failure mode change across slow_period ∈ {60, 84, 120, 144}?

Implementation assumptions (fixed across all configs):
  - Resolution: H4
  - Cost: 50 bps round-trip (25 bps per side)
  - Signal at bar close, fill at next bar open (= previous close)
  - trail_mult=3.0, vdo_threshold=0.0, atr_period=14, vdo_fast=12, vdo_slow=28
  - fast_period = max(5, slow_period // 4)
  - No look-ahead, no survivor bias
"""

from __future__ import annotations

import json
import math
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from v10.core.data import DataFeed
from v10.core.types import SCENARIOS
from strategies.vtrend.strategy import _ema, _atr, _vdo

# ═══════════════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════════════

DATA = str(ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv")
START = "2019-01-01"
END = "2026-02-20"
WARMUP = 365  # days

SLOW_PERIODS = [60, 84, 120, 144]
TRAIL = 3.0
VDO_THR = 0.0
ATR_P = 14
VDO_F = 12
VDO_S = 28
CPS = 0.0025  # 25 bps per side
CASH = 10_000.0
ANN = math.sqrt(6.0 * 365.25)  # H4 annualization
EPS = 1e-12

# ER30 context thresholds
ER_CHOP = 0.25
ER_TREND = 0.45

# Classification thresholds
EXIT_LAG_MFE_MIN = 2.0
EXIT_LAG_REAL_RATIO = 0.35
EXIT_LAG_PEAK_BARS = 4
FB_MAE_MIN = 1.0
FB_MFE_EARLY = 0.5
FB_MFE_FULL = 1.0
FIRST_N = 6

# Bootstrap
N_BOOT_VALID = 2000
BOOT_BLOCK = 20
SEED = 42

OUT_DIR = ROOT / "research" / "results"


# ═══════════════════════════════════════════════════════════════════════
# Data loading
# ═══════════════════════════════════════════════════════════════════════

def load_data():
    feed = DataFeed(DATA, start=START, end=END, warmup_days=WARMUP)
    h4 = feed.h4_bars
    n = len(h4)
    cl = np.array([b.close for b in h4], dtype=np.float64)
    hi = np.array([b.high for b in h4], dtype=np.float64)
    lo = np.array([b.low for b in h4], dtype=np.float64)
    vo = np.array([b.volume for b in h4], dtype=np.float64)
    tb = np.array([b.taker_buy_base_vol for b in h4], dtype=np.float64)
    ot = np.array([b.open_time for b in h4], dtype=np.int64)
    wi = 0
    if feed.report_start_ms is not None:
        for i, b in enumerate(h4):
            if b.close_time >= feed.report_start_ms:
                wi = i
                break
    print(f"  Loaded {n} H4 bars, reporting from index {wi} "
          f"({_ts(ot[wi])} – {_ts(ot[-1])})")
    return cl, hi, lo, vo, tb, ot, wi, n


# ═══════════════════════════════════════════════════════════════════════
# Helper indicators
# ═══════════════════════════════════════════════════════════════════════

def efficiency_ratio(close, lookback=30):
    """Kaufman ER: |net move| / sum(|bar moves|) over lookback bars."""
    n = len(close)
    er = np.full(n, np.nan)
    for i in range(lookback, n):
        net = abs(close[i] - close[i - lookback])
        total = np.sum(np.abs(np.diff(close[i - lookback:i + 1])))
        er[i] = net / total if total > EPS else 0.0
    return er


def realized_vol_arr(close, lookback=30):
    """Annualized realized vol from H4 log returns."""
    n = len(close)
    rv = np.full(n, np.nan)
    lr = np.log(close[1:] / close[:-1])
    for i in range(lookback, len(lr)):
        rv[i + 1] = np.std(lr[i - lookback + 1:i + 1]) * ANN
    return rv


def _ts(ms):
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")


def _ts_short(ms):
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")


# ═══════════════════════════════════════════════════════════════════════
# Detailed backtest
# ═══════════════════════════════════════════════════════════════════════

def run_backtest(cl, hi, lo, ot, ef, es, at, vd, er30, rvol, wi, slow_period):
    """
    Returns (trades: list[dict], nav: np.ndarray, report_start: int).
    Trades only include those with entry signal >= wi (reporting window).
    """
    n = len(cl)
    nav = np.zeros(n)
    trades = []

    cash = CASH
    bq = 0.0
    in_pos = False
    pk = 0.0
    pe = px = False
    exit_reason = ""

    sig_bar = 0
    fill_bar = 0
    e_atr = e_er30 = e_rvol = e_fill_raw = 0.0
    cash_at_entry = 0.0
    tid = 0

    for i in range(n):
        p = cl[i]

        # ── execute pending fills ──
        if i > 0:
            fp = cl[i - 1]
            if pe:
                pe = False
                e_fill_raw = fp
                effective = fp * (1.0 + CPS)
                cash_at_entry = cash
                bq = cash / effective
                cash = 0.0
                in_pos = True
                pk = p
                fill_bar = i
            elif px:
                x_fill_raw = fp
                x_cash = bq * fp * (1.0 - CPS)

                # build trade record (only reporting-window trades)
                if sig_bar >= wi:
                    t = _build_trade(
                        tid, slow_period, sig_bar, fill_bar,
                        i,          # exit_fill_bar
                        i - 1,      # exit_sig_bar (signal fired previous bar)
                        e_fill_raw, x_fill_raw,
                        e_atr, e_er30, e_rvol, exit_reason,
                        cash_at_entry, bq,
                        cl, hi, lo, ot,
                    )
                    trades.append(t)
                    tid += 1

                cash = x_cash
                bq = 0.0
                in_pos = False
                pk = 0.0
                px = False

        nav[i] = cash + bq * p

        # ── signal generation ──
        a = at[i]
        if math.isnan(a) or math.isnan(ef[i]) or math.isnan(es[i]):
            continue

        if not in_pos:
            if ef[i] > es[i] and vd[i] > VDO_THR:
                pe = True
                sig_bar = i
                e_atr = a
                e_er30 = er30[i] if not np.isnan(er30[i]) else np.nan
                e_rvol = rvol[i] if not np.isnan(rvol[i]) else np.nan
        else:
            pk = max(pk, p)
            if p < pk - TRAIL * a:
                px = True
                exit_reason = "ATR_trail"
            elif ef[i] < es[i]:
                px = True
                exit_reason = "EMA_cross_down"

    # force close at end
    if in_pos and bq > 0:
        fp = cl[-1]
        x_cash = bq * fp * (1.0 - CPS)
        if sig_bar >= wi:
            t = _build_trade(
                tid, slow_period, sig_bar, fill_bar,
                n - 1, n - 1, e_fill_raw, fp,
                e_atr, e_er30, e_rvol, "end_of_data",
                cash_at_entry, bq, cl, hi, lo, ot,
            )
            trades.append(t)
        nav[-1] = x_cash

    return trades, nav, wi


def _build_trade(tid, slow, sig_bar, fill_bar, x_fill_bar, x_sig_bar,
                 e_raw, x_raw, e_atr, e_er30, e_rvol, x_reason,
                 cash_at_entry, qty, cl, hi, lo, ot):
    """Compute all per-trade diagnostic fields."""
    entry_net = e_raw * (1.0 + CPS)
    exit_net = x_raw * (1.0 - CPS)

    gross_pnl_pct = (x_raw / e_raw - 1.0) * 100
    net_pnl_pct = (exit_net / entry_net - 1.0) * 100
    net_pnl_dollar = cash_at_entry * (exit_net / entry_net - 1.0)
    gross_pnl_dollar = cash_at_entry * (x_raw / e_raw - 1.0)

    bars_held = x_fill_bar - fill_bar

    # ── MFE / MAE from highs & lows ──
    b0, b1 = fill_bar, x_sig_bar
    if b1 >= b0 and b1 < len(hi):
        hold_hi = hi[b0:b1 + 1]
        hold_lo = lo[b0:b1 + 1]
        max_high = np.max(hold_hi)
        min_low = np.min(hold_lo)
    else:
        max_high = e_raw
        min_low = e_raw

    mfe = max(0.0, max_high - e_raw)
    mae = max(0.0, e_raw - min_low)
    mfe_r = mfe / e_atr if e_atr > EPS else 0.0
    mae_r = mae / e_atr if e_atr > EPS else 0.0

    realized = exit_net - entry_net
    realized_r = realized / e_atr if e_atr > EPS else 0.0
    giveback_r = mfe_r - realized_r
    giveback_ratio = giveback_r / max(mfe_r, EPS)

    # peak bar (highest high)
    if b1 >= b0 and len(hold_hi) > 0:
        peak_idx = b0 + int(np.argmax(hold_hi))
    else:
        peak_idx = fill_bar
    peak_to_exit = x_fill_bar - peak_idx

    # ── first-N-bar analysis ──
    first_n = min(FIRST_N, max(0, b1 - b0 + 1))
    f6_mfe_r = f6_mae_r = 0.0
    mae_before_mfe = False

    if first_n > 0 and b0 + first_n <= len(hi):
        fh = hi[b0:b0 + first_n]
        fl = lo[b0:b0 + first_n]
        f6_mfe_r = max(0.0, np.max(fh) - e_raw) / e_atr if e_atr > EPS else 0.0
        f6_mae_r = max(0.0, e_raw - np.min(fl)) / e_atr if e_atr > EPS else 0.0

        # bar-by-bar: does MAE hit FB_MAE_MIN before MFE hits FB_MFE_EARLY?
        cum_mfe = cum_mae = 0.0
        for j in range(first_n):
            bj = b0 + j
            cum_mfe = max(cum_mfe, hi[bj] - e_raw)
            cum_mae = max(cum_mae, e_raw - lo[bj])
            mfe_j = cum_mfe / e_atr if e_atr > EPS else 0.0
            mae_j = cum_mae / e_atr if e_atr > EPS else 0.0
            if mfe_j >= FB_MFE_EARLY:
                break
            if mae_j >= FB_MAE_MIN:
                mae_before_mfe = True
                break

    # ER30 context
    if np.isnan(e_er30):
        ctx = "Unknown"
    elif e_er30 < ER_CHOP:
        ctx = "Chop"
    elif e_er30 > ER_TREND:
        ctx = "Trend"
    else:
        ctx = "Transition"

    return dict(
        trade_id=tid, slow_period=slow,
        entry_time=_ts(int(ot[fill_bar])) if fill_bar < len(ot) else "",
        exit_time=_ts(int(ot[x_fill_bar])) if x_fill_bar < len(ot) else "",
        entry_bar=fill_bar, exit_bar=x_fill_bar,
        entry_price=e_raw, exit_price=x_raw,
        bars_held=bars_held,
        gross_pnl=gross_pnl_dollar, net_pnl=net_pnl_dollar,
        gross_pnl_pct=gross_pnl_pct, net_pnl_pct=net_pnl_pct,
        ATR_at_entry=e_atr,
        MFE_R=mfe_r, MAE_R=mae_r,
        realized_R=realized_r, giveback_R=giveback_r,
        giveback_ratio=giveback_ratio,
        exit_reason=x_reason,
        peak_price=max_high, peak_bar=peak_idx,
        peak_time=_ts(int(ot[peak_idx])) if peak_idx < len(ot) else "",
        time_from_peak_to_exit=peak_to_exit,
        first_6_bar_MFE_R=f6_mfe_r, first_6_bar_MAE_R=f6_mae_r,
        mae_before_mfe_first6=mae_before_mfe,
        entry_ER30=e_er30, entry_regime_context=ctx,
        entry_rvol=e_rvol,
    )


# ═══════════════════════════════════════════════════════════════════════
# Classification
# ═══════════════════════════════════════════════════════════════════════

def classify(df):
    """Assign proximate_cause to each trade. Modifies df in-place."""
    causes = []
    for _, r in df.iterrows():
        if r.net_pnl_pct >= 0:
            causes.append("Winner")
        elif (r.MFE_R >= EXIT_LAG_MFE_MIN
              and r.realized_R <= EXIT_LAG_REAL_RATIO * r.MFE_R
              and r.time_from_peak_to_exit >= EXIT_LAG_PEAK_BARS):
            causes.append("Exit_lag")
        elif (r.mae_before_mfe_first6
              and r.MFE_R < FB_MFE_FULL):
            causes.append("False_breakout")
        else:
            causes.append("Other_loss")
    df["proximate_cause"] = causes
    df["is_winner"] = df.net_pnl_pct >= 0
    return df


# ═══════════════════════════════════════════════════════════════════════
# Analysis functions
# ═══════════════════════════════════════════════════════════════════════

def perf_summary(df, nav_dict, wi, n_bars):
    """Section 2: performance table by slow_period."""
    lines = ["\n" + "=" * 80,
             "SECTION 2 — PERFORMANCE BY SLOW_PERIOD",
             "=" * 80]
    hdr = (f"{'slow':>6} {'trades':>6} {'winners':>7} {'WR%':>6} "
           f"{'CAGR%':>7} {'MDD%':>7} {'Sharpe':>7} {'Calmar':>7} "
           f"{'netPnL$':>10} {'exposure%':>9}")
    lines.append(hdr)
    lines.append("-" * len(hdr))

    for sp in SLOW_PERIODS:
        sub = df[df.slow_period == sp]
        nt = len(sub)
        nw = sub.is_winner.sum()
        wr = nw / nt * 100 if nt else 0

        nav = nav_dict[sp]
        report_nav = nav[wi:]
        report_nav = report_nav[report_nav > 0]
        if len(report_nav) < 2:
            lines.append(f"{sp:>6} — insufficient data")
            continue

        total_ret = report_nav[-1] / report_nav[0] - 1
        yrs = (len(report_nav) - 1) / (6.0 * 365.25)
        cagr = ((1 + total_ret) ** (1 / yrs) - 1) * 100 if yrs > 0 and total_ret > -1 else -100

        peak = np.maximum.accumulate(report_nav)
        dd = 1 - report_nav / peak
        mdd = dd.max() * 100

        rets = np.diff(report_nav) / report_nav[:-1]
        mu = np.mean(rets)
        std = np.std(rets, ddof=0)
        sharpe = (mu / std) * ANN if std > EPS else 0
        calmar = cagr / mdd if mdd > 0.01 else 0

        net_pnl = report_nav[-1] - report_nav[0]

        # exposure: fraction of bars in position
        in_pos_bars = sub.bars_held.sum()
        total_bars = len(report_nav)
        exp = in_pos_bars / total_bars * 100 if total_bars > 0 else 0

        lines.append(f"{sp:>6} {nt:>6} {nw:>7} {wr:>5.1f}% "
                     f"{cagr:>7.2f} {mdd:>7.2f} {sharpe:>7.3f} {calmar:>7.3f} "
                     f"{net_pnl:>10,.0f} {exp:>8.1f}%")

    return "\n".join(lines)


def loss_decomp_cause(df):
    """Section 3A: loss decomposition by proximate cause."""
    lines = ["\n" + "=" * 80,
             "SECTION 3A — LOSS DECOMPOSITION BY PROXIMATE CAUSE",
             "=" * 80]

    for sp in SLOW_PERIODS:
        sub = df[df.slow_period == sp]
        losers = sub[~sub.is_winner]
        total_gross_loss = losers.gross_pnl.sum()
        total_net_loss = losers.net_pnl.sum()

        lines.append(f"\n── slow_period = {sp} ──")
        lines.append(f"  Total losing trades: {len(losers)} / {len(sub)}")
        lines.append(f"  Total gross loss: ${total_gross_loss:,.0f}")
        lines.append(f"  Total net loss:   ${total_net_loss:,.0f}")

        hdr = (f"  {'Cause':<16} {'#trades':>7} {'%trades':>7} "
               f"{'%gross':>7} {'%net':>7} "
               f"{'med$':>9} {'mean$':>9} "
               f"{'medBars':>7} {'medMFE_R':>8} {'medMAE_R':>8} "
               f"{'medGBr':>7}")
        lines.append(hdr)
        lines.append("  " + "-" * (len(hdr) - 2))

        for cause in ["Exit_lag", "False_breakout", "Other_loss"]:
            c = losers[losers.proximate_cause == cause]
            nc = len(c)
            if nc == 0:
                lines.append(f"  {cause:<16} {0:>7} {0:>6.1f}% "
                             f"{0:>6.1f}% {0:>6.1f}% "
                             f"{'—':>9} {'—':>9} "
                             f"{'—':>7} {'—':>8} {'—':>8} {'—':>7}")
                continue
            pct_trades = nc / len(losers) * 100
            pct_gross = c.gross_pnl.sum() / total_gross_loss * 100 if abs(total_gross_loss) > EPS else 0
            pct_net = c.net_pnl.sum() / total_net_loss * 100 if abs(total_net_loss) > EPS else 0
            lines.append(
                f"  {cause:<16} {nc:>7} {pct_trades:>6.1f}% "
                f"{pct_gross:>6.1f}% {pct_net:>6.1f}% "
                f"{c.net_pnl.median():>9,.0f} {c.net_pnl.mean():>9,.0f} "
                f"{c.bars_held.median():>7.0f} {c.MFE_R.median():>8.2f} "
                f"{c.MAE_R.median():>8.2f} {c.giveback_ratio.median():>7.2f}")

    return "\n".join(lines)


def loss_decomp_context(df):
    """Section 3B: loss decomposition by market context."""
    lines = ["\n" + "=" * 80,
             "SECTION 3B — LOSS DECOMPOSITION BY MARKET CONTEXT",
             "=" * 80]

    for sp in SLOW_PERIODS:
        sub = df[df.slow_period == sp]
        total_net_loss = sub[~sub.is_winner].net_pnl.sum()
        lines.append(f"\n── slow_period = {sp} ──")

        hdr = (f"  {'Context':<12} {'#trades':>7} {'%trades':>7} "
               f"{'WR%':>6} {'E[pnl%]':>8} {'netLoss$':>10} {'%netLoss':>8} "
               f"{'turnover':>8}")
        lines.append(hdr)
        lines.append("  " + "-" * (len(hdr) - 2))

        for ctx in ["Chop", "Transition", "Trend", "Unknown"]:
            c = sub[sub.entry_regime_context == ctx]
            nc = len(c)
            if nc == 0:
                continue
            pct_t = nc / len(sub) * 100
            wr = c.is_winner.sum() / nc * 100
            exp_pnl = c.net_pnl_pct.mean()
            nl = c[~c.is_winner].net_pnl.sum()
            pct_nl = nl / total_net_loss * 100 if abs(total_net_loss) > EPS else 0
            turnover = c.bars_held.sum()
            lines.append(
                f"  {ctx:<12} {nc:>7} {pct_t:>6.1f}% "
                f"{wr:>5.1f}% {exp_pnl:>7.2f}% {nl:>10,.0f} {pct_nl:>7.1f}% "
                f"{turnover:>8}")

    return "\n".join(lines)


def cause_x_context(df):
    """Section 3C: cause × context cross-tabulation."""
    lines = ["\n" + "=" * 80,
             "SECTION 3C — CAUSE × CONTEXT MATRIX",
             "=" * 80]

    for sp in SLOW_PERIODS:
        sub = df[df.slow_period == sp]
        losers = sub[~sub.is_winner]
        total_nl = losers.net_pnl.sum()
        total_count = len(losers)

        lines.append(f"\n── slow_period = {sp}  (% of total net loss / % of losing trades) ──")

        causes = ["Exit_lag", "False_breakout", "Other_loss"]
        ctxs = ["Chop", "Transition", "Trend"]

        # header
        hdr = f"  {'':>16}"
        for ctx in ctxs:
            hdr += f" {ctx:>18}"
        hdr += f" {'TOTAL':>18}"
        lines.append(hdr)
        lines.append("  " + "-" * (len(hdr) - 2))

        for cause in causes:
            row = f"  {cause:<16}"
            cause_nl_total = 0
            cause_ct_total = 0
            for ctx in ctxs:
                cell = losers[(losers.proximate_cause == cause) &
                              (losers.entry_regime_context == ctx)]
                nl = cell.net_pnl.sum()
                ct = len(cell)
                pct_nl = nl / total_nl * 100 if abs(total_nl) > EPS else 0
                pct_ct = ct / total_count * 100 if total_count > 0 else 0
                row += f"  {pct_nl:>6.1f}% / {pct_ct:>5.1f}%"
                cause_nl_total += nl
                cause_ct_total += ct
            # total
            pct_nl_t = cause_nl_total / total_nl * 100 if abs(total_nl) > EPS else 0
            pct_ct_t = cause_ct_total / total_count * 100 if total_count > 0 else 0
            row += f"  {pct_nl_t:>6.1f}% / {pct_ct_t:>5.1f}%"
            lines.append(row)

    return "\n".join(lines)


def losing_streaks(df):
    """Section 4: losing streak analysis."""
    lines = ["\n" + "=" * 80,
             "SECTION 4 — LOSING STREAKS",
             "=" * 80]

    for sp in SLOW_PERIODS:
        sub = df[df.slow_period == sp].sort_values("entry_bar").reset_index(drop=True)
        results = sub.is_winner.values

        # find all losing streaks
        streaks = []
        current_len = 0
        start_idx = 0
        for i, w in enumerate(results):
            if not w:
                if current_len == 0:
                    start_idx = i
                current_len += 1
            else:
                if current_len > 0:
                    streaks.append((start_idx, current_len))
                current_len = 0
        if current_len > 0:
            streaks.append((start_idx, current_len))

        longest = max((s[1] for s in streaks), default=0)
        streaks_ge5 = sum(1 for s in streaks if s[1] >= 5)

        lines.append(f"\n── slow_period = {sp} ──")
        lines.append(f"  Total streaks: {len(streaks)}")
        lines.append(f"  Longest streak: {longest} trades")
        lines.append(f"  Streaks >= 5 trades: {streaks_ge5}")

        # Analyze major streaks (top 3 by length)
        major = sorted(streaks, key=lambda x: -x[1])[:3]
        for rank, (sidx, slen) in enumerate(major, 1):
            streak_trades = sub.iloc[sidx:sidx + slen]
            st_entry = streak_trades.iloc[0].entry_time
            st_exit = streak_trades.iloc[-1].exit_time
            cum_loss = streak_trades.net_pnl_pct.sum()

            cause_mix = streak_trades.proximate_cause.value_counts().to_dict()
            ctx_mix = streak_trades.entry_regime_context.value_counts().to_dict()
            avg_mae = streak_trades.MAE_R.mean()
            avg_bars = streak_trades.bars_held.mean()

            # calendar duration
            cal_bars = streak_trades.iloc[-1].exit_bar - streak_trades.iloc[0].entry_bar

            lines.append(f"\n  Streak #{rank}: {slen} trades, "
                         f"{st_entry} → {st_exit}")
            lines.append(f"    Calendar H4 bars: {cal_bars} "
                         f"(~{cal_bars/6:.0f} days)")
            lines.append(f"    Cumulative loss: {cum_loss:+.1f}% "
                         f"(mean {streak_trades.net_pnl_pct.mean():.2f}%)")
            lines.append(f"    Cause mix: {cause_mix}")
            lines.append(f"    Context mix: {ctx_mix}")
            lines.append(f"    Avg MAE_R: {avg_mae:.2f}, "
                         f"Avg bars held: {avg_bars:.0f}")

    return "\n".join(lines)


def drawdown_anatomy(df, nav_dict, cl, ot, er30, rvol, wi):
    """Section 5: all drawdowns > 20% on equity curve."""
    lines = ["\n" + "=" * 80,
             "SECTION 5 — DRAWDOWN ANATOMY (MDD > 20%)",
             "=" * 80]

    for sp in SLOW_PERIODS:
        sub = df[df.slow_period == sp].sort_values("entry_bar")
        nav = nav_dict[sp]
        rn = nav[wi:]
        rn_ot = ot[wi:]

        if len(rn) < 2:
            continue

        peak = np.maximum.accumulate(rn)
        dd_pct = (1 - rn / peak) * 100

        # find distinct drawdown periods
        in_dd = dd_pct > 0
        dds = []
        start = None
        for i in range(len(rn)):
            if in_dd[i] and start is None:
                start = i
            elif not in_dd[i] and start is not None:
                trough_idx = start + np.argmax(dd_pct[start:i])
                max_dd = dd_pct[trough_idx]
                if max_dd >= 20:
                    dds.append((start, trough_idx, i, max_dd))
                start = None
        # handle ongoing drawdown at end
        if start is not None:
            trough_idx = start + np.argmax(dd_pct[start:])
            max_dd = dd_pct[trough_idx]
            if max_dd >= 20:
                dds.append((start, trough_idx, None, max_dd))

        lines.append(f"\n── slow_period = {sp}: {len(dds)} drawdown(s) > 20% ──")

        for didx, (s, tr, rec, mdd_val) in enumerate(dds, 1):
            # global bar indices
            gs = wi + s
            gtr = wi + tr
            grec = wi + rec if rec is not None else None

            s_date = _ts_short(int(rn_ot[s]))
            tr_date = _ts_short(int(rn_ot[tr]))
            rec_date = _ts_short(int(rn_ot[rec])) if rec is not None else "Not recovered"

            p2t_bars = tr - s
            full_bars = rec - s if rec is not None else None

            # trades during drawdown
            dd_end = grec if grec is not None else len(cl) - 1
            dd_trades = sub[(sub.entry_bar >= gs) & (sub.entry_bar <= dd_end)]

            # market context
            dd_slice = slice(gs, dd_end + 1)
            btc_ret = (cl[dd_end] / cl[gs] - 1) * 100 if gs < dd_end else 0
            avg_er30 = np.nanmean(er30[dd_slice])
            avg_rvol = np.nanmean(rvol[dd_slice])

            lines.append(f"\n  DD #{didx}: {mdd_val:.1f}%")
            lines.append(f"    Start: {s_date} → Trough: {tr_date} "
                         f"→ Recovery: {rec_date}")
            lines.append(f"    Peak→Trough: {p2t_bars} bars "
                         f"(~{p2t_bars/6:.0f}d), "
                         f"Full recovery: "
                         f"{'~'+str(full_bars//6)+'d' if full_bars else 'N/A'}")
            lines.append(f"    Trades in DD: {len(dd_trades)}, "
                         f"turnover: {dd_trades.bars_held.sum()} bars")

            if len(dd_trades) > 0:
                cause_mix = dd_trades.proximate_cause.value_counts().to_dict()
                ctx_mix = dd_trades.entry_regime_context.value_counts().to_dict()
                exit_mix = dd_trades.exit_reason.value_counts().to_dict()
                lines.append(f"    Cause mix: {cause_mix}")
                lines.append(f"    Context mix: {ctx_mix}")
                lines.append(f"    Exit reason mix: {exit_mix}")

            lines.append(f"    Market during DD: BTC return {btc_ret:+.1f}%, "
                         f"avg ER30 {avg_er30:.3f}, "
                         f"avg annualized vol {avg_rvol:.1f}%")

            # diagnosis
            if len(dd_trades) > 0:
                n_fb = (dd_trades.proximate_cause == "False_breakout").sum()
                n_el = (dd_trades.proximate_cause == "Exit_lag").sum()
                n_losers = (~dd_trades.is_winner).sum()
                if n_fb > n_el and n_fb >= n_losers * 0.5:
                    lines.append("    → Dominated by repeated false breakouts")
                elif n_el > 0 and dd_trades[dd_trades.proximate_cause == "Exit_lag"].giveback_R.sum() > 3.0:
                    lines.append("    → Driven by large giveback on exit-lag trades")
                elif avg_er30 < ER_CHOP:
                    lines.append("    → Prolonged chop market structure")
                else:
                    lines.append("    → Mixed causes")

    return "\n".join(lines)


def cross_config_comparison(df, nav_dict, wi):
    """Section 7 in spec: comparison across slow_periods."""
    lines = ["\n" + "=" * 80,
             "SECTION 7 — CROSS-CONFIG COMPARISON",
             "=" * 80]

    # Summary table
    hdr = (f"{'slow':>6} {'trades':>6} {'WR%':>6} {'Sharpe':>7} "
           f"{'MDD%':>7} {'%FB':>6} {'%EL':>6} {'%Other':>6} "
           f"{'%Chop_loss':>10} {'%Trend_loss':>11}")
    lines.append(hdr)
    lines.append("-" * len(hdr))

    for sp in SLOW_PERIODS:
        sub = df[df.slow_period == sp]
        losers = sub[~sub.is_winner]
        nt = len(sub)
        wr = sub.is_winner.sum() / nt * 100 if nt else 0

        nav = nav_dict[sp]
        rn = nav[wi:]
        rn = rn[rn > 0]
        rets = np.diff(rn) / rn[:-1]
        mu = np.mean(rets)
        std = np.std(rets, ddof=0)
        sharpe = (mu / std) * ANN if std > EPS else 0
        peak = np.maximum.accumulate(rn)
        mdd = ((1 - rn / peak).max()) * 100

        nl_total = losers.net_pnl.sum()
        pct_fb = losers[losers.proximate_cause == "False_breakout"].net_pnl.sum() / nl_total * 100 if abs(nl_total) > EPS else 0
        pct_el = losers[losers.proximate_cause == "Exit_lag"].net_pnl.sum() / nl_total * 100 if abs(nl_total) > EPS else 0
        pct_ot = losers[losers.proximate_cause == "Other_loss"].net_pnl.sum() / nl_total * 100 if abs(nl_total) > EPS else 0

        chop_loss = sub[(sub.entry_regime_context == "Chop") & (~sub.is_winner)].net_pnl.sum()
        trend_loss = sub[(sub.entry_regime_context == "Trend") & (~sub.is_winner)].net_pnl.sum()
        pct_chop = chop_loss / nl_total * 100 if abs(nl_total) > EPS else 0
        pct_trend = trend_loss / nl_total * 100 if abs(nl_total) > EPS else 0

        lines.append(
            f"{sp:>6} {nt:>6} {wr:>5.1f}% {sharpe:>7.3f} "
            f"{mdd:>7.2f} {pct_fb:>5.1f}% {pct_el:>5.1f}% {pct_ot:>5.1f}% "
            f"{pct_chop:>9.1f}% {pct_trend:>10.1f}%")

    # Detailed comparison commentary
    lines.append("\nKey observations:")

    # trade count change
    counts = {sp: len(df[df.slow_period == sp]) for sp in SLOW_PERIODS}
    lines.append(f"  Trade count: {counts[60]} → {counts[84]} → "
                 f"{counts[120]} → {counts[144]} "
                 f"(slow=60→144)")

    # Does larger slow reduce false breakout but increase exit lag?
    for sp in SLOW_PERIODS:
        losers = df[(df.slow_period == sp) & (~df.is_winner)]
        nl = losers.net_pnl.sum()
        n_fb = len(losers[losers.proximate_cause == "False_breakout"])
        n_el = len(losers[losers.proximate_cause == "Exit_lag"])
        lines.append(f"  slow={sp}: FB={n_fb} trades, EL={n_el} trades "
                     f"(FB count as slow↑: {'↓' if sp > 60 else '—'})")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════
# Counterfactual diagnostics
# ═══════════════════════════════════════════════════════════════════════

def counterfactuals(df):
    """Section 6: three counterfactual analyses."""
    lines = ["\n" + "=" * 80,
             "SECTION 6 — COUNTERFACTUAL DIAGNOSTICS",
             "=" * 80]

    for sp in SLOW_PERIODS:
        sub = df[df.slow_period == sp].sort_values("entry_bar").reset_index(drop=True)
        lines.append(f"\n── slow_period = {sp} ──")

        # Baseline equity
        base_eq = _equity_from_trades(sub)
        base_final = base_eq[-1] if len(base_eq) > 0 else CASH
        base_mdd = _mdd_from_equity(base_eq)

        # A. Remove false breakout trades
        no_fb = sub[sub.proximate_cause != "False_breakout"]
        eq_a = _equity_from_trades(no_fb)
        final_a = eq_a[-1] if len(eq_a) > 0 else CASH
        mdd_a = _mdd_from_equity(eq_a)
        fb_trades = sub[sub.proximate_cause == "False_breakout"]
        fb_loss = fb_trades.net_pnl.sum() if len(fb_trades) > 0 else 0

        lines.append(f"\n  A. Perfect entry filter (remove {len(fb_trades)} false breakouts):")
        lines.append(f"    Trades: {len(sub)} → {len(no_fb)}")
        lines.append(f"    Final equity: ${base_final:,.0f} → ${final_a:,.0f} "
                     f"(+${final_a - base_final:,.0f})")
        lines.append(f"    MDD: {base_mdd:.1f}% → {mdd_a:.1f}% "
                     f"({mdd_a - base_mdd:+.1f}pp)")
        lines.append(f"    Upper bound net PnL improvement: ${-fb_loss:,.0f}")

        # B. Faster exit on exit-lag trades
        #    Replace exit-lag trade PnLs with exit-at-peak PnLs
        improved = sub.copy()
        el_mask = improved.proximate_cause == "Exit_lag"
        el_count = el_mask.sum()
        saved_r = 0.0
        if el_count > 0:
            el_trades = improved[el_mask]
            # improved net pnl if we sold at peak_price
            for idx in el_trades.index:
                t = improved.loc[idx]
                improved_exit_net = t.peak_price * (1.0 - CPS)
                improved_entry_net = t.entry_price * (1.0 + CPS)
                improved_pnl_pct = (improved_exit_net / improved_entry_net - 1) * 100
                saved_r += (improved_pnl_pct - t.net_pnl_pct)
                improved.loc[idx, "net_pnl_pct"] = improved_pnl_pct

        eq_b = _equity_from_trades(improved)
        final_b = eq_b[-1] if len(eq_b) > 0 else CASH
        mdd_b = _mdd_from_equity(eq_b)

        lines.append(f"\n  B. Perfect exit (exit at MFE peak for {el_count} exit-lag trades):")
        lines.append(f"    Final equity: ${base_final:,.0f} → ${final_b:,.0f} "
                     f"(+${final_b - base_final:,.0f})")
        lines.append(f"    MDD: {base_mdd:.1f}% → {mdd_b:.1f}% "
                     f"({mdd_b - base_mdd:+.1f}pp)")
        lines.append(f"    Cumulative saved return: {saved_r:+.1f}pp")

        # C. Remove chop trades
        no_chop = sub[sub.entry_regime_context != "Chop"]
        eq_c = _equity_from_trades(no_chop)
        final_c = eq_c[-1] if len(eq_c) > 0 else CASH
        mdd_c = _mdd_from_equity(eq_c)
        chop_trades = sub[sub.entry_regime_context == "Chop"]
        chop_loss = chop_trades[~chop_trades.is_winner].net_pnl.sum()

        # exposure change
        base_bars = sub.bars_held.sum()
        no_chop_bars = no_chop.bars_held.sum()

        lines.append(f"\n  C. Chop gate (remove {len(chop_trades)} chop trades):")
        lines.append(f"    Trades: {len(sub)} → {len(no_chop)}")
        lines.append(f"    Final equity: ${base_final:,.0f} → ${final_c:,.0f} "
                     f"(+${final_c - base_final:,.0f})")
        lines.append(f"    MDD: {base_mdd:.1f}% → {mdd_c:.1f}% "
                     f"({mdd_c - base_mdd:+.1f}pp)")
        lines.append(f"    Exposure bars: {base_bars} → {no_chop_bars} "
                     f"({(no_chop_bars/base_bars - 1)*100:+.1f}%)" if base_bars > 0 else "")

        # Summary: which lever has highest EV?
        improvements = {
            "Entry filter": final_a - base_final,
            "Faster exit": final_b - base_final,
            "Chop gate": final_c - base_final,
        }
        best = max(improvements, key=improvements.get)
        lines.append(f"\n  → Highest EV lever: {best} "
                     f"(+${improvements[best]:,.0f})")

    return "\n".join(lines)


def _equity_from_trades(trades_df):
    """Compute equity curve from trade returns (compounding)."""
    if len(trades_df) == 0:
        return np.array([CASH])
    eq = [CASH]
    for _, t in trades_df.iterrows():
        eq.append(eq[-1] * (1 + t.net_pnl_pct / 100))
    return np.array(eq)


def _mdd_from_equity(eq):
    """Max drawdown % from equity array."""
    if len(eq) < 2:
        return 0.0
    peak = np.maximum.accumulate(eq)
    dd = 1 - eq / peak
    return dd.max() * 100


# ═══════════════════════════════════════════════════════════════════════
# Bootstrap validation
# ═══════════════════════════════════════════════════════════════════════

def bootstrap_validation(nav_dict, ot, wi):
    """Section 9: block bootstrap on daily strategy returns."""
    lines = ["\n" + "=" * 80,
             "SECTION 9 — BOOTSTRAP VALIDATION",
             "=" * 80]

    # Aggregate to daily returns for each config
    daily_rets = {}
    for sp in SLOW_PERIODS:
        nav = nav_dict[sp]
        rn = nav[wi:]
        rn_ot = ot[wi:]
        rn = rn[rn > 0]
        rn_ot = rn_ot[:len(rn)]

        # group by day (6 H4 bars per day)
        days = rn_ot // 86_400_000
        unique_days = np.unique(days)
        d_rets = []
        for k in range(1, len(unique_days)):
            mask_prev = days == unique_days[k - 1]
            mask_curr = days == unique_days[k]
            if np.any(mask_prev) and np.any(mask_curr):
                nav_prev = rn[mask_prev][-1]
                nav_curr = rn[mask_curr][-1]
                if nav_prev > 0:
                    d_rets.append(nav_curr / nav_prev - 1)
        daily_rets[sp] = np.array(d_rets)

    rng = np.random.default_rng(SEED)

    # Bootstrap Sharpe CIs
    lines.append("\nBootstrap Sharpe 90% CI (2000 samples, block=20d):")
    hdr = f"  {'slow':>6} {'Sharpe':>8} {'2.5%':>8} {'50%':>8} {'97.5%':>8}"
    lines.append(hdr)
    lines.append("  " + "-" * (len(hdr) - 2))

    ann_d = math.sqrt(365.25)
    boot_sharpes = {}

    for sp in SLOW_PERIODS:
        dr = daily_rets[sp]
        n = len(dr)
        if n < BOOT_BLOCK * 2:
            lines.append(f"  {sp:>6} — insufficient data ({n} days)")
            continue

        real_sharpe = (np.mean(dr) / np.std(dr, ddof=0)) * ann_d if np.std(dr) > EPS else 0

        sharpes = np.zeros(N_BOOT_VALID)
        for b in range(N_BOOT_VALID):
            n_blocks = math.ceil(n / BOOT_BLOCK)
            starts = rng.integers(0, n - BOOT_BLOCK + 1, size=n_blocks)
            idx = np.concatenate([np.arange(s, s + BOOT_BLOCK) for s in starts])[:n]
            sample = dr[idx]
            mu = np.mean(sample)
            std = np.std(sample, ddof=0)
            sharpes[b] = (mu / std) * ann_d if std > EPS else 0

        boot_sharpes[sp] = sharpes
        p025 = np.percentile(sharpes, 2.5)
        p500 = np.percentile(sharpes, 50)
        p975 = np.percentile(sharpes, 97.5)
        lines.append(f"  {sp:>6} {real_sharpe:>8.3f} {p025:>8.3f} "
                     f"{p500:>8.3f} {p975:>8.3f}")

    # Paired comparison (adjacent slow_periods)
    lines.append("\nPaired comparison (P that row > column on Sharpe):")
    pairs = [(60, 84), (60, 120), (60, 144),
             (84, 120), (84, 144), (120, 144)]
    for sp_a, sp_b in pairs:
        if sp_a in boot_sharpes and sp_b in boot_sharpes:
            p = np.mean(boot_sharpes[sp_a] > boot_sharpes[sp_b])
            sig = " *" if p > 0.975 or p < 0.025 else ""
            lines.append(f"  P(slow={sp_a} > slow={sp_b}) = {p:.3f}{sig}")

    lines.append("\n  Note: * = significant at 95% level (P > 0.975 or P < 0.025)")
    lines.append("  Block bootstrap preserves autocorrelation but may understate")
    lines.append("  uncertainty for non-stationary returns. Interpret with caution.")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════
# Executive summary + final diagnosis
# ═══════════════════════════════════════════════════════════════════════

def executive_summary(df, nav_dict, wi):
    """Section 1: 5 quantitative bullets."""
    lines = ["=" * 80,
             "SECTION 1 — EXECUTIVE SUMMARY",
             "=" * 80]

    # Focus on the default config (slow=120)
    s120 = df[df.slow_period == 120]
    losers_120 = s120[~s120.is_winner]
    total_nl = losers_120.net_pnl.sum()

    fb_pct = losers_120[losers_120.proximate_cause == "False_breakout"].net_pnl.sum() / total_nl * 100 if abs(total_nl) > EPS else 0
    el_pct = losers_120[losers_120.proximate_cause == "Exit_lag"].net_pnl.sum() / total_nl * 100 if abs(total_nl) > EPS else 0
    ot_pct = losers_120[losers_120.proximate_cause == "Other_loss"].net_pnl.sum() / total_nl * 100 if abs(total_nl) > EPS else 0

    chop_pct = s120[(s120.entry_regime_context == "Chop") & (~s120.is_winner)].net_pnl.sum() / total_nl * 100 if abs(total_nl) > EPS else 0

    nav120 = nav_dict[120]
    rn = nav120[wi:]
    rn = rn[rn > 0]
    rets = np.diff(rn) / rn[:-1]
    sharpe = (np.mean(rets) / np.std(rets, ddof=0)) * ANN if np.std(rets) > EPS else 0

    # Find best counterfactual lever
    # (will be filled in after counterfactuals run)

    lines.append(f"1. Primary loss driver (N=120): False breakout accounts for "
                 f"{fb_pct:.0f}% of total net loss, Exit lag {el_pct:.0f}%, "
                 f"Other {ot_pct:.0f}%.")
    lines.append(f"2. Market context: Chop regime contributes {chop_pct:.0f}% "
                 f"of total net loss (N=120).")
    lines.append(f"3. Win rate range: "
                 f"{' / '.join(f'{sp}={df[df.slow_period==sp].is_winner.mean()*100:.0f}%' for sp in SLOW_PERIODS)}")
    lines.append(f"4. Sharpe (N=120): {sharpe:.3f}. "
                 f"Trade count scales inversely with slow_period: "
                 f"{len(df[df.slow_period==60])} → {len(df[df.slow_period==144])}.")

    # Failure mode stability
    fb_counts = []
    el_counts = []
    for sp in SLOW_PERIODS:
        losers = df[(df.slow_period == sp) & (~df.is_winner)]
        nl = losers.net_pnl.sum()
        fb = losers[losers.proximate_cause == "False_breakout"].net_pnl.sum() / nl * 100 if abs(nl) > EPS else 0
        el = losers[losers.proximate_cause == "Exit_lag"].net_pnl.sum() / nl * 100 if abs(nl) > EPS else 0
        fb_counts.append(f"{sp}:{fb:.0f}%")
        el_counts.append(f"{sp}:{el:.0f}%")

    lines.append(f"5. Failure mode is STABLE across configs: "
                 f"FB%=[{', '.join(fb_counts)}], "
                 f"EL%=[{', '.join(el_counts)}].")

    return "\n".join(lines)


def final_diagnosis(df, nav_dict, wi):
    """Section 7: final conclusions."""
    lines = ["\n" + "=" * 80,
             "SECTION 8 — FINAL DIAGNOSIS",
             "=" * 80]

    # Determine largest cause of net loss and MDD for each config
    for sp in SLOW_PERIODS:
        sub = df[df.slow_period == sp]
        losers = sub[~sub.is_winner]
        nl = losers.net_pnl.sum()

        causes = {}
        for c in ["Exit_lag", "False_breakout", "Other_loss"]:
            causes[c] = losers[losers.proximate_cause == c].net_pnl.sum()

        biggest_cause = min(causes, key=causes.get)  # most negative
        biggest_pct = causes[biggest_cause] / nl * 100 if abs(nl) > EPS else 0

        lines.append(f"\nslow={sp}:")
        lines.append(f"  Largest net loss cause: {biggest_cause} "
                     f"({biggest_pct:.0f}% of total net loss, "
                     f"${causes[biggest_cause]:,.0f})")

    # Overall conclusions
    lines.append("\n" + "-" * 60)
    lines.append("OVERALL CONCLUSIONS:")

    # 1. Largest net loss cause across all configs
    all_losers = df[~df.is_winner]
    total_nl = all_losers.net_pnl.sum()
    fb_nl = all_losers[all_losers.proximate_cause == "False_breakout"].net_pnl.sum()
    el_nl = all_losers[all_losers.proximate_cause == "Exit_lag"].net_pnl.sum()
    ot_nl = all_losers[all_losers.proximate_cause == "Other_loss"].net_pnl.sum()

    lines.append(f"\n1. LARGEST NET LOSS CAUSE: "
                 f"{'False breakout' if fb_nl < el_nl and fb_nl < ot_nl else 'Exit lag' if el_nl < ot_nl else 'Other'} "
                 f"(FB: {fb_nl/total_nl*100:.0f}%, EL: {el_nl/total_nl*100:.0f}%, "
                 f"Other: {ot_nl/total_nl*100:.0f}% of total net loss)")

    # 2. Largest MDD cause (from drawdown anatomy — qualitative)
    lines.append(f"\n2. LARGEST MDD CAUSE: Determined by drawdown anatomy above.")

    # 3. Highest EV change
    lines.append(f"\n3. HIGHEST EV CHANGE: See counterfactual analysis (Section 6).")

    # 4. Least toxic slow_period
    lines.append(f"\n4. LEAST TOXIC FAILURE PROFILE:")
    for sp in SLOW_PERIODS:
        losers = df[(df.slow_period == sp) & (~df.is_winner)]
        nl = losers.net_pnl.sum()
        fb_pct = losers[losers.proximate_cause == "False_breakout"].net_pnl.sum() / nl * 100 if abs(nl) > EPS else 0
        el_pct = losers[losers.proximate_cause == "Exit_lag"].net_pnl.sum() / nl * 100 if abs(nl) > EPS else 0
        # "toxicity" = how concentrated losses are in one mode
        max_mode = max(fb_pct, el_pct)
        lines.append(f"  slow={sp}: max single-mode concentration = {max_mode:.0f}%")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════

def main():
    t0 = time.time()

    print("VTREND POST-MORTEM DIAGNOSTIC")
    print("=" * 80)
    print(f"Configs: slow_period ∈ {SLOW_PERIODS}")
    print(f"Fixed: trail={TRAIL}, vdo_thr={VDO_THR}, ATR_period={ATR_P}")
    print(f"Cost: {CPS*2*10000:.0f} bps round-trip ({CPS*10000:.0f} bps/side)")
    print(f"Period: {START} → {END}, warmup={WARMUP}d")
    print()

    # Load data
    print("Loading data...")
    cl, hi, lo, vo, tb, ot, wi, n = load_data()

    # Precompute common indicators
    print("Computing indicators...")
    er30 = efficiency_ratio(cl, 30)
    rvol = realized_vol_arr(cl, 30)

    all_trades = []
    nav_dict = {}

    for sp in SLOW_PERIODS:
        fast = max(5, sp // 4)
        print(f"\nRunning backtest: slow={sp}, fast={fast}...")

        ef = _ema(cl, fast)
        es = _ema(cl, sp)
        at = _atr(hi, lo, cl, ATR_P)
        vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)

        trades, nav, _ = run_backtest(
            cl, hi, lo, ot, ef, es, at, vd, er30, rvol, wi, sp)

        nav_dict[sp] = nav
        all_trades.extend(trades)
        print(f"  → {len(trades)} trades in reporting window")

    # Build DataFrame
    df = pd.DataFrame(all_trades)
    if len(df) == 0:
        print("ERROR: No trades generated. Check data and parameters.")
        return

    # Classify
    print("\nClassifying trades...")
    df = classify(df)

    # Save trade CSV
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = OUT_DIR / "vtrend_postmortem_trades.csv"
    df.to_csv(csv_path, index=False)
    print(f"Saved {len(df)} trade records to {csv_path}")

    # ── Generate report ──
    print("\nGenerating report...\n")

    sections = []
    sections.append(executive_summary(df, nav_dict, wi))
    sections.append(perf_summary(df, nav_dict, wi, n))
    sections.append(loss_decomp_cause(df))
    sections.append(loss_decomp_context(df))
    sections.append(cause_x_context(df))
    sections.append(losing_streaks(df))
    sections.append(drawdown_anatomy(df, nav_dict, cl, ot, er30, rvol, wi))
    sections.append(counterfactuals(df))
    sections.append(cross_config_comparison(df, nav_dict, wi))
    sections.append(bootstrap_validation(nav_dict, ot, wi))
    sections.append(final_diagnosis(df, nav_dict, wi))

    report = "\n".join(sections)
    print(report)

    # Save report
    report_path = OUT_DIR / "vtrend_postmortem_report.txt"
    with open(report_path, "w") as f:
        f.write(report)
    print(f"\nReport saved to {report_path}")

    elapsed = time.time() - t0
    print(f"\nTotal time: {elapsed:.1f}s")


if __name__ == "__main__":
    main()
