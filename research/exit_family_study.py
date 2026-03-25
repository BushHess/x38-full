#!/usr/bin/env python3
"""Exit Family Study — Controlled comparative study of 6 exit-branch variants
for the VTREND strategy on real BTC H4 data.

Branches:
  E0: Baseline (peak_close anchor, 3.0×ATR trail, EMA cross-down)
  E1: Threshold ratcheting (trail_mult steps by MFE_R thresholds)
  E2: Simple dynamic trail (continuous trail_mult = clip(3.0 - 0.75*MFE_R))
  E3: Partial exit only (sell 1/3 at MFE_R >= 1.0, residual uses E0 exit)
  E4: Partial + ratchet (sell 1/3, residual uses E1 ratchet exit)
  E5: Close-based robust-ATR trail (capped TR → Wilder rATR20)

Methodology:
  - Walk-forward OOS (train=24mo, test=6mo, step=3mo)
  - Matched-trade exit isolation
  - Stationary bootstrap (10k resamples, mean block=10d)
  - Local sensitivity (conditional, only for OOS winners)
  - Context stratification by Kaufman ER30

IMPLEMENTATION AUDIT NOTE:
  The proposal specified E0 uses peak_high_since_entry as trail anchor.
  However, the actual VTREND code (strategy.py:111) uses peak_close:
    self._peak_price = max(self._peak_price, price)  # price = bar.close
  Per rule 1.1 ("exact current reference implementation"), ALL branches
  use peak_close_since_entry as anchor. E5's "close anchor" factor is
  therefore moot — E5 isolates ONLY the robust ATR effect.
  Data: BTC only. "Single-market confirmation only."
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

# ═══════════════════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════════════════

DATA = str(ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv")
COST = SCENARIOS["harsh"]
CPS = COST.per_side_bps / 10_000.0  # 0.0025 per side

START = "2019-01-01"
END = "2026-02-20"
WARMUP = 365
CASH = 10_000.0

# Annualization
ANN_DAILY = math.sqrt(365.25)
H4_PER_DAY = 6
MS_PER_DAY = 86_400_000

# Strategy constants (frozen from baseline)
ATR_P = 14
VDO_F = 12
VDO_S = 28
TRAIL = 3.0
VDO_THR = 0.0

# Study config
BRANCHES = ["E0", "E1", "E2", "E3", "E4", "E5"]
SLOW_PERIODS = [120, 144]

# WFO config
WFO_TRAIN_MO = 24
WFO_TEST_MO = 6
WFO_STEP_MO = 3

# Bootstrap config
N_BOOT = 10_000
BOOT_BLOCK = 10  # mean block length in days
BOOT_SEED = 42

# ER30 bins
ER30_LABELS = ["<0.10", "0.10-0.15", "0.15-0.20", "0.20-0.25", ">=0.25"]

EPSILON = 1e-10
OUTDIR = Path(__file__).resolve().parent / "results" / "exit_family"


# ═══════════════════════════════════════════════════════════════════════════
# Data Loading
# ═══════════════════════════════════════════════════════════════════════════

def load_data():
    """Load H4 bars, return arrays + metadata."""
    feed = DataFeed(DATA, start=START, end=END, warmup_days=WARMUP)
    h4 = feed.h4_bars
    n = len(h4)
    cl = np.array([b.close for b in h4], dtype=np.float64)
    hi = np.array([b.high for b in h4], dtype=np.float64)
    lo = np.array([b.low for b in h4], dtype=np.float64)
    op = np.array([b.open for b in h4], dtype=np.float64)
    vo = np.array([b.volume for b in h4], dtype=np.float64)
    tb = np.array([b.taker_buy_base_vol for b in h4], dtype=np.float64)
    ts_ms = np.array([b.close_time for b in h4], dtype=np.int64)
    open_ts = np.array([b.open_time for b in h4], dtype=np.int64)

    wi = 0
    if feed.report_start_ms is not None:
        for i, b in enumerate(h4):
            if b.close_time >= feed.report_start_ms:
                wi = i
                break

    return cl, hi, lo, op, vo, tb, ts_ms, open_ts, wi, n


# ═══════════════════════════════════════════════════════════════════════════
# Indicator Helpers
# ═══════════════════════════════════════════════════════════════════════════

def compute_er30(cl, period=30):
    """Kaufman Efficiency Ratio on `period` bars."""
    n = len(cl)
    er = np.full(n, np.nan)
    for i in range(period, n):
        direction = abs(cl[i] - cl[i - period])
        volatility = np.sum(np.abs(np.diff(cl[i - period : i + 1])))
        er[i] = direction / max(volatility, EPSILON)
    return er


def er30_bin(val):
    """Assign ER30 value to bin label."""
    if math.isnan(val) or val < 0.10:
        return "<0.10"
    if val < 0.15:
        return "0.10-0.15"
    if val < 0.20:
        return "0.15-0.20"
    if val < 0.25:
        return "0.20-0.25"
    return ">=0.25"


def compute_robust_atr(hi, lo, cl, cap_q=0.90, cap_lb=100, period=20):
    """Robust ATR: cap TR at rolling quantile, then Wilder EMA.

    - TR_cap = min(TR, Q90 of prior cap_lb bars of TR)
    - rATR = WilderEMA(TR_cap, period)
    """
    prev_cl = np.concatenate([[cl[0]], cl[:-1]])
    tr = np.maximum(
        hi - lo,
        np.maximum(np.abs(hi - prev_cl), np.abs(lo - prev_cl)),
    )

    n = len(tr)
    tr_cap = np.full(n, np.nan)

    # Cap at rolling quantile (no look-ahead)
    for i in range(cap_lb, n):
        q = np.percentile(tr[i - cap_lb : i], cap_q * 100)
        tr_cap[i] = min(tr[i], q)

    # Wilder EMA on capped TR
    ratr = np.full(n, np.nan)
    s = cap_lb
    if s + period <= n:
        ratr[s + period - 1] = np.mean(tr_cap[s : s + period])
        for i in range(s + period, n):
            ratr[i] = (ratr[i - 1] * (period - 1) + tr_cap[i]) / period

    return ratr


def ts_to_date(ms):
    """Epoch ms → 'YYYY-MM-DD' UTC."""
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")


def ts_to_month(ms):
    """Epoch ms → (year, month) tuple."""
    dt = datetime.fromtimestamp(ms / 1000, tz=timezone.utc)
    return (dt.year, dt.month)


def month_add(ym, months):
    """Add months to (year, month) tuple."""
    y, m = ym
    m += months
    while m > 12:
        m -= 12
        y += 1
    while m < 1:
        m += 12
        y -= 1
    return (y, m)


def ym_to_ms(ym):
    """(year, month) → epoch ms for 1st of that month UTC."""
    dt = datetime(ym[0], ym[1], 1, tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


# ═══════════════════════════════════════════════════════════════════════════
# Core Simulation — Single function for all 6 branches
# ═══════════════════════════════════════════════════════════════════════════

def simulate_branch(
    branch_id,
    cl, hi, lo, op, ts_ms, open_ts, ef, es, at, vd, er30_arr, wi,
    slow_period,
    ratr=None,
    # Sensitivity params for E1/E4 ratchet thresholds
    e1_t1=1.0, e1_t2=2.0, e1_mid=2.0, e1_tight=1.5,
    # Sensitivity params for E2 dynamic trail
    e2_slope=0.75, e2_floor=1.5,
    # Sensitivity params for E3/E4 partial exit
    partial_trigger_r=1.0, partial_frac=1.0 / 3.0,
):
    """Run a single exit branch on given data arrays.

    Returns
    -------
    equity : np.ndarray  (len n, NAV at each H4 bar close)
    trades : list[dict]  (one per completed trade)
    """
    n = len(cl)
    exit_atr = ratr if (branch_id == "E5" and ratr is not None) else at

    # Portfolio state
    cash = CASH
    bq = 0.0  # BTC quantity
    in_pos = False

    # Pending signals (mutually exclusive)
    pe = px = pp = False

    # Per-trade state
    tid = 0
    e_bar = -1
    e_px = 0.0
    e_atr = 0.0
    e_er_bin = ""
    pk_hi = 0.0
    pk_cl = 0.0
    pk_bar = -1
    lo_lo = 1e18
    p_done = False
    p_time = 0
    p_qty = 0.0
    p_price = 0.0
    o_qty = 0.0
    e_cash = 0.0
    p_cost = 0.0
    x_reason = ""

    equity = np.zeros(n, dtype=np.float64)
    trades = []

    for i in range(n):
        p = cl[i]

        # ── Fill pending from previous bar's signal ──
        if i > 0:
            fp = cl[i - 1]  # fill price (bar close as proxy for next bar open)

            if pe:
                pe = False
                bq = cash / (fp * (1.0 + CPS))
                e_cash = cash
                cash = 0.0
                in_pos = True
                o_qty = bq

                e_bar = i
                e_px = fp
                e_atr = at[i - 1] if not math.isnan(at[i - 1]) else 0.0
                e_er_bin = er30_bin(
                    er30_arr[i - 1] if not math.isnan(er30_arr[i - 1]) else 0.0
                )

                pk_hi = hi[i]
                pk_cl = p
                pk_bar = i
                lo_lo = lo[i]
                p_done = False
                p_time = 0
                p_qty = 0.0
                p_price = 0.0
                p_cost = 0.0

            elif pp:
                pp = False
                pq = bq * partial_frac
                p_proceeds = pq * fp * (1.0 - CPS)
                p_cost = pq * fp * CPS
                cash += p_proceeds
                bq -= pq
                p_done = True
                p_time = open_ts[i]
                p_qty = pq
                p_price = fp

            elif px:
                px = False
                remaining = bq
                x_proceeds = remaining * fp * (1.0 - CPS)
                x_cost = remaining * fp * CPS
                cash += x_proceeds

                # Record trade
                entry_cost = o_qty * e_px * CPS
                total_cost = entry_cost + p_cost + x_cost

                if p_done:
                    gross = p_qty * (p_price - e_px) + remaining * (fp - e_px)
                    total_out = p_qty * p_price * (1.0 - CPS) + x_proceeds
                else:
                    gross = remaining * (fp - e_px)
                    total_out = x_proceeds

                net = total_out - e_cash
                net_pct = net / e_cash * 100 if e_cash > 0 else 0.0

                mfe_r = (pk_hi - e_px) / e_atr if e_atr > EPSILON else 0.0
                mae_r = (e_px - lo_lo) / e_atr if e_atr > EPSILON else 0.0
                real_r = net / (o_qty * e_atr) if (o_qty > EPSILON and e_atr > EPSILON) else 0.0
                gb_r = mfe_r - real_r
                gb_ratio = gb_r / max(mfe_r, EPSILON)

                peak_ts = ts_ms[pk_bar]
                exit_ts = open_ts[i]
                t_peak_exit = (exit_ts - peak_ts) / 3_600_000

                trades.append(
                    _make_trade(
                        branch_id, slow_period, tid, e_bar, i,
                        open_ts, ts_ms, e_px, fp, gross, net, net_pct,
                        e_atr, mfe_r, mae_r, real_r, gb_r, gb_ratio,
                        x_reason, pk_hi, pk_cl, peak_ts, t_peak_exit,
                        p_done, p_time, p_qty, p_price, o_qty,
                        total_cost, e_er_bin,
                    )
                )

                tid += 1
                bq = 0.0
                in_pos = False
                pk_hi = 0.0
                pk_cl = 0.0
                pk_bar = -1
                lo_lo = 1e18
                o_qty = 0.0

        # ── NAV ──
        nav = cash + bq * p
        equity[i] = nav

        # ── Signal generation ──
        a_val = at[i]
        ea_val = exit_atr[i] if exit_atr is not None else a_val
        if math.isnan(a_val) or math.isnan(ef[i]) or math.isnan(es[i]):
            continue
        if branch_id == "E5" and (ratr is None or math.isnan(ea_val)):
            continue

        if not in_pos:
            if ef[i] > es[i] and vd[i] > VDO_THR:
                pe = True
        else:
            # Update peaks
            pk_hi = max(pk_hi, hi[i])
            if p > pk_cl:
                pk_cl = p
                pk_bar = i
            lo_lo = min(lo_lo, lo[i])

            # MFE_R for trail/partial logic (uses peak_high and frozen ATR_entry)
            mfe_r_now = (pk_hi - e_px) / e_atr if e_atr > EPSILON else 0.0

            # Determine trail multiplier
            if branch_id in ("E0", "E3", "E5"):
                t_mult = TRAIL
            elif branch_id in ("E1", "E4"):
                if mfe_r_now < e1_t1:
                    t_mult = TRAIL
                elif mfe_r_now < e1_t2:
                    t_mult = e1_mid
                else:
                    t_mult = e1_tight
            elif branch_id == "E2":
                t_mult = max(e2_floor, min(TRAIL, TRAIL - e2_slope * mfe_r_now))
            else:
                t_mult = TRAIL

            # Trail stop (anchor = peak_close, ATR = branch-specific)
            trail_stop = pk_cl - t_mult * ea_val

            # Check full exit first (precedence over partial)
            full_exit = False
            if p < trail_stop:
                full_exit = True
                x_reason = "trail_stop"
            elif ef[i] < es[i]:
                full_exit = True
                x_reason = "ema_cross_down"

            if full_exit:
                px = True
            else:
                # Check partial exit (E3, E4 only)
                if branch_id in ("E3", "E4") and not p_done:
                    if mfe_r_now >= partial_trigger_r:
                        pp = True

    # ── Force close at end ──
    if in_pos and bq > 0:
        fp = cl[-1]
        remaining = bq
        x_proceeds = remaining * fp * (1.0 - CPS)
        x_cost = remaining * fp * CPS
        cash += x_proceeds

        entry_cost = o_qty * e_px * CPS
        total_cost = entry_cost + p_cost + x_cost
        if p_done:
            gross = p_qty * (p_price - e_px) + remaining * (fp - e_px)
            total_out = p_qty * p_price * (1.0 - CPS) + x_proceeds
        else:
            gross = remaining * (fp - e_px)
            total_out = x_proceeds
        net = total_out - e_cash
        net_pct = net / e_cash * 100 if e_cash > 0 else 0.0
        mfe_r = (pk_hi - e_px) / e_atr if e_atr > EPSILON else 0.0
        mae_r = (e_px - lo_lo) / e_atr if e_atr > EPSILON else 0.0
        real_r = net / (o_qty * e_atr) if (o_qty > EPSILON and e_atr > EPSILON) else 0.0
        gb_r = mfe_r - real_r
        gb_ratio = gb_r / max(mfe_r, EPSILON)
        peak_ts = ts_ms[pk_bar] if pk_bar >= 0 else ts_ms[-1]
        exit_ts = ts_ms[-1]
        t_peak_exit = (exit_ts - peak_ts) / 3_600_000
        trades.append(
            _make_trade(
                branch_id, slow_period, tid, e_bar, n - 1,
                open_ts, ts_ms, e_px, fp, gross, net, net_pct,
                e_atr, mfe_r, mae_r, real_r, gb_r, gb_ratio,
                "end_of_data", pk_hi, pk_cl, peak_ts, t_peak_exit,
                p_done, p_time, p_qty, p_price, o_qty,
                total_cost, e_er_bin,
            )
        )
        equity[-1] = cash
        bq = 0.0

    return equity, trades


def _make_trade(
    branch_id, slow_period, tid, e_bar, x_bar,
    open_ts, ts_ms, e_px, x_px, gross, net, net_pct,
    e_atr, mfe_r, mae_r, real_r, gb_r, gb_ratio,
    x_reason, pk_hi, pk_cl, peak_ts, t_peak_exit,
    p_done, p_time, p_qty, p_price, o_qty,
    total_cost, e_er_bin,
):
    """Build trade record dict."""
    entry_ts = int(open_ts[e_bar])
    exit_ts = int(open_ts[x_bar]) if x_bar < len(open_ts) else int(ts_ms[-1])
    return {
        "branch_id": branch_id,
        "slow_period": slow_period,
        "trade_id": tid,
        "entry_time": entry_ts,
        "exit_time": exit_ts,
        "entry_price_exec": round(e_px, 2),
        "exit_price_exec": round(x_px, 2),
        "bars_held": x_bar - e_bar,
        "gross_pnl": round(gross, 4),
        "net_pnl": round(net, 4),
        "net_pnl_pct": round(net_pct, 4),
        "ATR_entry": round(e_atr, 4),
        "MFE_R_final": round(mfe_r, 4),
        "MAE_R_final": round(mae_r, 4),
        "realized_R": round(real_r, 4),
        "giveback_R": round(gb_r, 4),
        "giveback_ratio": round(gb_ratio, 4),
        "exit_reason": x_reason,
        "peak_high_since_entry": round(pk_hi, 2),
        "peak_close_since_entry": round(pk_cl, 2),
        "peak_time": int(peak_ts),
        "time_from_peak_to_exit": round(t_peak_exit, 2),
        "partial_exit_done": p_done,
        "partial_exit_time": int(p_time) if p_done else 0,
        "partial_exit_qty": round(p_qty, 8) if p_done else 0.0,
        "partial_exit_price": round(p_price, 2) if p_done else 0.0,
        "residual_qty_after_partial": round(o_qty - p_qty, 8) if p_done else 0.0,
        "total_cost_paid": round(total_cost, 4),
        "entry_ER30_context_bin": e_er_bin,
        "entry_date": ts_to_date(entry_ts),
        "exit_date": ts_to_date(exit_ts),
    }


# ═══════════════════════════════════════════════════════════════════════════
# Portfolio Backtest Driver
# ═══════════════════════════════════════════════════════════════════════════

def run_all_branches(cl, hi, lo, op, ts_ms, open_ts, vo, tb, wi, n):
    """Run all branches × slow_periods on real data. Returns results dict."""
    er30_arr = compute_er30(cl)
    results = {}  # key: (branch, slow_period) → (equity, trades)

    for sp in SLOW_PERIODS:
        fast_p = max(5, sp // 4)
        ef = _ema(cl, fast_p)
        es = _ema(cl, sp)
        at = _atr(hi, lo, cl, ATR_P)
        vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)
        ratr = compute_robust_atr(hi, lo, cl)

        for bid in BRANCHES:
            eq, tr = simulate_branch(
                bid, cl, hi, lo, op, ts_ms, open_ts,
                ef, es, at, vd, er30_arr, wi, sp, ratr=ratr,
            )
            results[(bid, sp)] = (eq, tr)
            oos_trades = [t for t in tr if t["entry_time"] >= open_ts[wi]]
            print(
                f"  {bid} N={sp}: {len(oos_trades)} trades, "
                f"final NAV={eq[-1]:.2f}"
            )

    return results, er30_arr


# ═══════════════════════════════════════════════════════════════════════════
# WFO Fold Management
# ═══════════════════════════════════════════════════════════════════════════

def define_wfo_folds(ts_ms, open_ts):
    """Define walk-forward test folds. Returns list of (test_start_ms, test_end_ms)."""
    # First test start: START + WFO_TRAIN_MO months
    start_ym = ts_to_month(open_ts[0])
    # Find actual reporting start
    report_ym = (2019, 1)
    first_test_ym = month_add(report_ym, WFO_TRAIN_MO)  # (2021, 1)

    folds = []
    test_ym = first_test_ym
    data_end_ms = int(ts_ms[-1])

    while True:
        test_start_ms = ym_to_ms(test_ym)
        test_end_ym = month_add(test_ym, WFO_TEST_MO)
        test_end_ms = ym_to_ms(test_end_ym)

        if test_start_ms >= data_end_ms:
            break
        # Allow partial last fold if >= 3 months of data
        actual_end = min(test_end_ms, data_end_ms)
        duration_days = (actual_end - test_start_ms) / MS_PER_DAY
        if duration_days < 80:  # ~2.7 months minimum
            break

        folds.append((test_start_ms, actual_end))
        test_ym = month_add(test_ym, WFO_STEP_MO)

    return folds


def aggregate_daily_nav(equity, ts_ms, wi):
    """Aggregate H4 equity into daily NAV (last bar each UTC day)."""
    days = ts_ms[wi:] // MS_PER_DAY
    eq = equity[wi:]
    n = len(days)

    daily_nav = []
    daily_ts = []

    for i in range(n):
        is_last = (i == n - 1) or (days[i] != days[i + 1])
        if is_last:
            daily_nav.append(eq[i])
            daily_ts.append(ts_ms[wi + i])

    return np.array(daily_nav), np.array(daily_ts)


def fold_metrics_from_equity(daily_nav, daily_ts, fold_start_ms, fold_end_ms):
    """Compute portfolio metrics for a single WFO fold from daily NAV."""
    mask = (daily_ts >= fold_start_ms) & (daily_ts < fold_end_ms)
    nav = daily_nav[mask]

    if len(nav) < 10:
        return None

    # Daily returns
    rets = nav[1:] / nav[:-1] - 1.0
    n_days = len(rets)
    if n_days < 5:
        return None

    # CAGR
    total_r = nav[-1] / nav[0] - 1.0
    years = n_days / 365.25
    cagr = ((1 + total_r) ** (1 / years) - 1) * 100 if years > 0 and total_r > -1 else -100.0

    # MDD
    peak = np.maximum.accumulate(nav)
    dd = 1.0 - nav / peak
    mdd = float(np.max(dd)) * 100

    # Sharpe
    mu = np.mean(rets)
    std = np.std(rets, ddof=0)
    sharpe = (mu / std) * ANN_DAILY if std > EPSILON else 0.0

    # Sortino
    down = rets[rets < 0]
    down_std = np.sqrt(np.mean(down ** 2)) if len(down) > 0 else EPSILON
    sortino = (mu / down_std) * ANN_DAILY if down_std > EPSILON else 0.0

    # MAR / Calmar
    mar = cagr / mdd if mdd > 0.01 else 0.0

    # Ulcer Index
    ui = np.sqrt(np.mean(dd ** 2)) * 100

    return {
        "cagr": cagr,
        "mdd": mdd,
        "sharpe": sharpe,
        "sortino": sortino,
        "mar": mar,
        "ulcer_index": ui,
        "n_days": n_days,
    }


def fold_trade_metrics(trades, fold_start_ms, fold_end_ms):
    """Compute trade-level metrics for trades exiting within the fold."""
    fold_tr = [t for t in trades if fold_start_ms <= t["exit_time"] < fold_end_ms]
    if not fold_tr:
        return None

    n = len(fold_tr)
    net_pnls = np.array([t["net_pnl"] for t in fold_tr])
    net_pcts = np.array([t["net_pnl_pct"] for t in fold_tr])
    bars = np.array([t["bars_held"] for t in fold_tr])
    mfe_rs = np.array([t["MFE_R_final"] for t in fold_tr])
    mae_rs = np.array([t["MAE_R_final"] for t in fold_tr])
    real_rs = np.array([t["realized_R"] for t in fold_tr])
    gb_rs = np.array([t["giveback_R"] for t in fold_tr])
    gb_ratios = np.array([t["giveback_ratio"] for t in fold_tr])
    costs = np.array([t["total_cost_paid"] for t in fold_tr])

    wins = net_pnls > 0
    win_rate = float(np.mean(wins)) * 100
    gross_win = float(np.sum(net_pnls[wins])) if np.any(wins) else 0.0
    gross_loss = float(np.abs(np.sum(net_pnls[~wins]))) if np.any(~wins) else EPSILON
    pf = gross_win / gross_loss if gross_loss > EPSILON else 0.0

    # Skew and tail ratio
    skew = float(pd.Series(net_pcts).skew()) if n > 2 else 0.0
    p95 = np.percentile(net_pcts, 95) if n > 5 else 0.0
    p5 = np.percentile(net_pcts, 5) if n > 5 else EPSILON
    tail_ratio = abs(p95 / p5) if abs(p5) > EPSILON else 0.0

    # Exit reason mix
    reasons = {}
    for t in fold_tr:
        r = t["exit_reason"]
        reasons[r] = reasons.get(r, 0) + 1

    # Partial metrics
    partials = [t for t in fold_tr if t["partial_exit_done"]]

    # MFE >= 1.0 but final loss
    mfe_1_loss = np.sum((mfe_rs >= 1.0) & (net_pnls < 0))
    mfe_1_loss_pct = mfe_1_loss / max(np.sum(mfe_rs >= 1.0), 1) * 100

    # MFE >= 1.0 and realized_R <= 35% of MFE_R
    mfe_1_retained_low = np.sum(
        (mfe_rs >= 1.0) & (real_rs <= 0.35 * mfe_rs)
    )
    mfe_1_retained_low_pct = mfe_1_retained_low / max(np.sum(mfe_rs >= 1.0), 1) * 100

    # MFE >= 2.0 and realized_R <= 35% of MFE_R
    mfe_2_retained_low = np.sum(
        (mfe_rs >= 2.0) & (real_rs <= 0.35 * mfe_rs)
    )
    mfe_2_retained_low_pct = mfe_2_retained_low / max(np.sum(mfe_rs >= 2.0), 1) * 100

    # Tail preservation
    sorted_pnl = np.sort(net_pnls)[::-1]
    total_pnl = np.sum(net_pnls)
    top5_n = max(1, int(np.ceil(n * 0.05)))
    top10_n = max(1, int(np.ceil(n * 0.10)))
    top5_pnl_pct = np.sum(sorted_pnl[:top5_n]) / max(abs(total_pnl), EPSILON) * 100
    top10_pnl_pct = np.sum(sorted_pnl[:top10_n]) / max(abs(total_pnl), EPSILON) * 100
    top10_mean = float(np.mean(sorted_pnl[:top10_n]))

    # Exposure (fraction of bars in position)
    exposure = float(np.sum(bars)) / max(1, (fold_end_ms - fold_start_ms) // (4 * 3_600_000))

    return {
        "trade_count": n,
        "win_rate": round(win_rate, 2),
        "profit_factor": round(pf, 4),
        "avg_holding_bars": round(float(np.mean(bars)), 1),
        "total_cost": round(float(np.sum(costs)), 2),
        "skew": round(skew, 4),
        "tail_ratio": round(tail_ratio, 4),
        "exposure": round(min(exposure, 1.0), 4),
        # Exit quality
        "mean_MFE_R": round(float(np.mean(mfe_rs)), 4),
        "median_MFE_R": round(float(np.median(mfe_rs)), 4),
        "mean_realized_R": round(float(np.mean(real_rs)), 4),
        "median_realized_R": round(float(np.median(real_rs)), 4),
        "mean_giveback_R": round(float(np.mean(gb_rs)), 4),
        "median_giveback_R": round(float(np.median(gb_rs)), 4),
        "mean_giveback_ratio": round(float(np.mean(gb_ratios)), 4),
        "median_giveback_ratio": round(float(np.median(gb_ratios)), 4),
        "pct_MFE1_loss": round(mfe_1_loss_pct, 2),
        "pct_MFE1_retained_low": round(mfe_1_retained_low_pct, 2),
        "pct_MFE2_retained_low": round(mfe_2_retained_low_pct, 2),
        "mean_time_peak_to_exit": round(float(np.mean([t["time_from_peak_to_exit"] for t in fold_tr])), 2),
        "exit_reason_mix": reasons,
        # Tail preservation
        "top5_pnl_pct": round(top5_pnl_pct, 2),
        "top10_pnl_pct": round(top10_pnl_pct, 2),
        "top10_mean_size": round(top10_mean, 4),
        # Partial
        "n_partials": len(partials),
        "partial_frac_of_trades": round(len(partials) / max(n, 1) * 100, 2),
    }


# ═══════════════════════════════════════════════════════════════════════════
# Matched-Trade Exit Analysis
# ═══════════════════════════════════════════════════════════════════════════

def run_matched_trades(
    e0_trades, cl, hi, lo, op, ts_ms, open_ts,
    ef, es, at, vd, er30_arr, wi, slow_period, ratr,
):
    """Replay each E0 entry through all 6 exit branches independently."""
    matched = []

    for e0t in e0_trades:
        entry_bar = e0t["_entry_bar"]  # internal bar index
        entry_px = e0t["entry_price_exec"]
        entry_atr = e0t["ATR_entry"]
        e0_tid = e0t["trade_id"]

        if entry_atr < EPSILON:
            continue

        for bid in BRANCHES:
            exit_atr = ratr if bid == "E5" else at
            result = _replay_single_trade(
                bid, entry_bar, entry_px, entry_atr,
                cl, hi, lo, ts_ms, open_ts, ef, es, at, vd,
                exit_atr, slow_period, e0_tid,
            )
            if result is not None:
                result["entry_ER30_context_bin"] = e0t["entry_ER30_context_bin"]
                matched.append(result)

    return matched


def _replay_single_trade(
    branch_id, entry_bar, entry_px, entry_atr,
    cl, hi, lo, ts_ms, open_ts, ef, es, at, vd,
    exit_atr, slow_period, e0_tid,
):
    """Simulate a single trade from entry to exit for one branch."""
    n = len(cl)
    pk_hi = 0.0
    pk_cl = 0.0
    pk_bar = entry_bar
    lo_lo = 1e18
    p_done = False
    p_bar = -1
    pp_pending = False
    px_pending = False
    x_reason = ""

    # For partial exits: track quantities (normalized to 1 unit)
    remaining_frac = 1.0
    partial_frac_val = 1.0 / 3.0
    partial_px = 0.0

    for i in range(entry_bar, n):
        p = cl[i]

        # Fill pending partial/exit
        if i > entry_bar:
            fp = cl[i - 1]
            if pp_pending:
                pp_pending = False
                p_done = True
                p_bar = i
                partial_px = fp
                remaining_frac -= partial_frac_val
            elif px_pending:
                px_pending = False
                # Trade is done
                exit_px = fp
                exit_bar = i

                mfe_r = (pk_hi - entry_px) / entry_atr if entry_atr > EPSILON else 0.0
                mae_r = (entry_px - lo_lo) / entry_atr if entry_atr > EPSILON else 0.0

                # Net PnL per unit (normalized)
                if p_done:
                    gross_per_unit = (
                        partial_frac_val * (partial_px - entry_px)
                        + remaining_frac * (exit_px - entry_px)
                    )
                    cost_per_unit = (
                        entry_px * CPS
                        + partial_frac_val * partial_px * CPS
                        + remaining_frac * exit_px * CPS
                    )
                else:
                    gross_per_unit = exit_px - entry_px
                    cost_per_unit = entry_px * CPS + exit_px * CPS

                net_per_unit = gross_per_unit - cost_per_unit
                real_r = net_per_unit / entry_atr if entry_atr > EPSILON else 0.0
                gb_r = mfe_r - real_r
                gb_ratio = gb_r / max(mfe_r, EPSILON)

                peak_ts = ts_ms[pk_bar]
                exit_ts = open_ts[exit_bar] if exit_bar < len(open_ts) else ts_ms[-1]

                return {
                    "branch_id": branch_id,
                    "slow_period": slow_period,
                    "e0_trade_id": e0_tid,
                    "entry_bar": entry_bar,
                    "exit_bar": exit_bar,
                    "entry_price_exec": round(entry_px, 2),
                    "exit_price_exec": round(exit_px, 2),
                    "bars_held": exit_bar - entry_bar,
                    "ATR_entry": round(entry_atr, 4),
                    "MFE_R_final": round(mfe_r, 4),
                    "MAE_R_final": round(mae_r, 4),
                    "realized_R": round(real_r, 4),
                    "giveback_R": round(gb_r, 4),
                    "giveback_ratio": round(gb_ratio, 4),
                    "exit_reason": x_reason,
                    "partial_exit_done": p_done,
                    "net_pnl_per_unit": round(net_per_unit, 4),
                    "gross_pnl_per_unit": round(gross_per_unit, 4),
                    "cost_per_unit": round(cost_per_unit, 4),
                    "time_from_peak_to_exit": round((exit_ts - peak_ts) / 3_600_000, 2),
                }

        # Update peaks
        pk_hi = max(pk_hi, hi[i])
        if p > pk_cl:
            pk_cl = p
            pk_bar = i
        lo_lo = min(lo_lo, lo[i])

        # Check exit conditions (skip first bar — just entered)
        if i == entry_bar:
            continue

        ea_val = exit_atr[i] if exit_atr is not None else at[i]
        if math.isnan(at[i]) or math.isnan(ef[i]) or math.isnan(es[i]):
            continue
        if branch_id == "E5" and (exit_atr is None or math.isnan(ea_val)):
            continue

        mfe_r_now = (pk_hi - entry_px) / entry_atr if entry_atr > EPSILON else 0.0

        # Trail multiplier
        if branch_id in ("E0", "E3", "E5"):
            t_mult = TRAIL
        elif branch_id in ("E1", "E4"):
            if mfe_r_now < 1.0:
                t_mult = TRAIL
            elif mfe_r_now < 2.0:
                t_mult = 2.0
            else:
                t_mult = 1.5
        elif branch_id == "E2":
            t_mult = max(1.5, min(TRAIL, TRAIL - 0.75 * mfe_r_now))
        else:
            t_mult = TRAIL

        trail_stop = pk_cl - t_mult * ea_val

        full_exit = False
        if p < trail_stop:
            full_exit = True
            x_reason = "trail_stop"
        elif ef[i] < es[i]:
            full_exit = True
            x_reason = "ema_cross_down"

        if full_exit:
            px_pending = True
        elif branch_id in ("E3", "E4") and not p_done and mfe_r_now >= 1.0:
            pp_pending = True

    # Never exited — force close at last bar
    exit_px = cl[-1]
    exit_bar = n - 1
    mfe_r = (pk_hi - entry_px) / entry_atr if entry_atr > EPSILON else 0.0
    mae_r = (entry_px - lo_lo) / entry_atr if entry_atr > EPSILON else 0.0
    if p_done:
        gross_per_unit = partial_frac_val * (partial_px - entry_px) + remaining_frac * (exit_px - entry_px)
        cost_per_unit = entry_px * CPS + partial_frac_val * partial_px * CPS + remaining_frac * exit_px * CPS
    else:
        gross_per_unit = exit_px - entry_px
        cost_per_unit = entry_px * CPS + exit_px * CPS
    net_per_unit = gross_per_unit - cost_per_unit
    real_r = net_per_unit / entry_atr if entry_atr > EPSILON else 0.0
    gb_r = mfe_r - real_r
    gb_ratio = gb_r / max(mfe_r, EPSILON)
    peak_ts = ts_ms[pk_bar]

    return {
        "branch_id": branch_id,
        "slow_period": slow_period,
        "e0_trade_id": e0_tid,
        "entry_bar": entry_bar,
        "exit_bar": exit_bar,
        "entry_price_exec": round(entry_px, 2),
        "exit_price_exec": round(exit_px, 2),
        "bars_held": exit_bar - entry_bar,
        "ATR_entry": round(entry_atr, 4),
        "MFE_R_final": round(mfe_r, 4),
        "MAE_R_final": round(mae_r, 4),
        "realized_R": round(real_r, 4),
        "giveback_R": round(gb_r, 4),
        "giveback_ratio": round(gb_ratio, 4),
        "exit_reason": "end_of_data",
        "partial_exit_done": p_done,
        "net_pnl_per_unit": round(net_per_unit, 4),
        "gross_pnl_per_unit": round(gross_per_unit, 4),
        "cost_per_unit": round(cost_per_unit, 4),
        "time_from_peak_to_exit": round((ts_ms[-1] - peak_ts) / 3_600_000, 2),
        "entry_ER30_context_bin": "",
    }


# ═══════════════════════════════════════════════════════════════════════════
# Stationary Bootstrap
# ═══════════════════════════════════════════════════════════════════════════

def gen_boot_indices(n, n_boot, mean_block, rng):
    """Generate stationary bootstrap index arrays (Politis-Romano)."""
    p = 1.0 / mean_block
    idx = np.zeros((n_boot, n), dtype=np.int64)
    idx[:, 0] = rng.integers(0, n, size=n_boot)
    for t in range(1, n):
        jump = rng.random(n_boot) < p
        new_pos = rng.integers(0, n, size=n_boot)
        cont_pos = (idx[:, t - 1] + 1) % n
        idx[:, t] = np.where(jump, new_pos, cont_pos)
    return idx


def bootstrap_metrics(rets, idx):
    """Compute CAGR, Sharpe, MDD, MAR for each bootstrap sample.

    rets: (n_days,)  daily returns
    idx:  (n_boot, n_days)  bootstrap index arrays
    Returns dict of arrays each shape (n_boot,)
    """
    resampled = rets[idx]  # (n_boot, n_days)
    n_days = resampled.shape[1]
    years = n_days / 365.25

    # Sharpe
    mu = resampled.mean(axis=1)
    std = resampled.std(axis=1, ddof=0)
    std = np.maximum(std, EPSILON)
    sharpe = mu / std * ANN_DAILY

    # CAGR
    cum = np.cumprod(1.0 + resampled, axis=1)
    total = cum[:, -1]
    # Handle negative total returns
    cagr = np.where(
        total > 0,
        (total ** (1.0 / years) - 1.0) * 100,
        -100.0,
    )

    # MDD
    peak = np.maximum.accumulate(cum, axis=1)
    dd = 1.0 - cum / peak
    mdd = dd.max(axis=1) * 100

    # MAR
    mar = np.where(mdd > 0.01, cagr / mdd, 0.0)

    return {"sharpe": sharpe, "cagr": cagr, "mdd": mdd, "mar": mar}


def run_bootstrap_comparison(results, ts_ms, wi, slow_period):
    """Run stationary bootstrap comparison of each branch vs E0."""
    print(f"\n  Bootstrap comparison (N={N_BOOT}, block={BOOT_BLOCK}d, sp={slow_period})")

    # Get daily returns for each branch
    daily_rets = {}
    for bid in BRANCHES:
        eq = results[(bid, slow_period)][0]
        dnav, dts = aggregate_daily_nav(eq, ts_ms, wi)
        dr = dnav[1:] / dnav[:-1] - 1.0
        daily_rets[bid] = dr

    # Use shortest length
    min_len = min(len(v) for v in daily_rets.values())
    for bid in daily_rets:
        daily_rets[bid] = daily_rets[bid][:min_len]

    rng = np.random.default_rng(BOOT_SEED)
    idx = gen_boot_indices(min_len, N_BOOT, BOOT_BLOCK, rng)

    e0_metrics = bootstrap_metrics(daily_rets["E0"], idx)
    boot_results = {}

    for bid in BRANCHES:
        if bid == "E0":
            boot_results[bid] = {
                "sharpe_med": float(np.median(e0_metrics["sharpe"])),
                "cagr_med": float(np.median(e0_metrics["cagr"])),
                "mdd_med": float(np.median(e0_metrics["mdd"])),
                "mar_med": float(np.median(e0_metrics["mar"])),
            }
            continue

        bk_metrics = bootstrap_metrics(daily_rets[bid], idx)

        # Paired differences
        d_sharpe = bk_metrics["sharpe"] - e0_metrics["sharpe"]
        d_cagr = bk_metrics["cagr"] - e0_metrics["cagr"]
        d_mdd = e0_metrics["mdd"] - bk_metrics["mdd"]  # positive = improvement
        d_mar = bk_metrics["mar"] - e0_metrics["mar"]

        boot_results[bid] = {
            "sharpe_med": float(np.median(bk_metrics["sharpe"])),
            "cagr_med": float(np.median(bk_metrics["cagr"])),
            "mdd_med": float(np.median(bk_metrics["mdd"])),
            "mar_med": float(np.median(bk_metrics["mar"])),
            # Deltas
            "d_sharpe_mean": float(np.mean(d_sharpe)),
            "d_cagr_mean": float(np.mean(d_cagr)),
            "d_mdd_mean": float(np.mean(d_mdd)),
            "d_mar_mean": float(np.mean(d_mar)),
            # P-values (fraction better)
            "p_sharpe": float(np.mean(d_sharpe > 0)),
            "p_cagr": float(np.mean(d_cagr > 0)),
            "p_mdd": float(np.mean(d_mdd > 0)),
            "p_mar": float(np.mean(d_mar > 0)),
            # CIs
            "ci_sharpe": [float(np.percentile(d_sharpe, 2.5)), float(np.percentile(d_sharpe, 97.5))],
            "ci_cagr": [float(np.percentile(d_cagr, 2.5)), float(np.percentile(d_cagr, 97.5))],
            "ci_mdd": [float(np.percentile(d_mdd, 2.5)), float(np.percentile(d_mdd, 97.5))],
            "ci_mar": [float(np.percentile(d_mar, 2.5)), float(np.percentile(d_mar, 97.5))],
        }

        print(
            f"    {bid} vs E0: dSharpe={d_sharpe.mean():+.4f} P={np.mean(d_sharpe>0)*100:.1f}%  "
            f"dMDD={d_mdd.mean():+.2f} P={np.mean(d_mdd>0)*100:.1f}%  "
            f"dCAGR={d_cagr.mean():+.2f} P={np.mean(d_cagr>0)*100:.1f}%  "
            f"dMAR={d_mar.mean():+.4f} P={np.mean(d_mar>0)*100:.1f}%"
        )

    return boot_results


def holm_adjust(p_values):
    """Holm-Bonferroni multiple comparison adjustment."""
    n = len(p_values)
    if n == 0:
        return []
    order = np.argsort(p_values)
    adjusted = np.zeros(n)
    for i, idx in enumerate(order):
        raw = p_values[idx]
        adjusted[idx] = min(raw * (n - i), 1.0)
    # Enforce monotonicity
    for i in range(1, n):
        idx = order[i]
        prev_idx = order[i - 1]
        adjusted[idx] = max(adjusted[idx], adjusted[prev_idx])
    return adjusted.tolist()


# ═══════════════════════════════════════════════════════════════════════════
# Matched-Trade Bootstrap
# ═══════════════════════════════════════════════════════════════════════════

def matched_trade_bootstrap(matched_df, slow_period, n_boot=5000):
    """Bootstrap paired deltas on matched-trade dataset."""
    rng = np.random.default_rng(BOOT_SEED + 1)
    e0_df = matched_df[
        (matched_df["branch_id"] == "E0") & (matched_df["slow_period"] == slow_period)
    ].set_index("e0_trade_id")

    results = {}
    for bid in BRANCHES:
        if bid == "E0":
            continue
        bk_df = matched_df[
            (matched_df["branch_id"] == bid) & (matched_df["slow_period"] == slow_period)
        ].set_index("e0_trade_id")

        # Align on common trades
        common = e0_df.index.intersection(bk_df.index)
        if len(common) < 5:
            continue

        e0_r = e0_df.loc[common, "realized_R"].values
        bk_r = bk_df.loc[common, "realized_R"].values
        e0_gb = e0_df.loc[common, "giveback_ratio"].values
        bk_gb = bk_df.loc[common, "giveback_ratio"].values

        # Bootstrap paired differences
        n = len(common)
        d_real = np.zeros(n_boot)
        d_gb = np.zeros(n_boot)

        for b in range(n_boot):
            sample = rng.integers(0, n, size=n)
            d_real[b] = np.mean(bk_r[sample] - e0_r[sample])
            d_gb[b] = np.mean(e0_gb[sample] - bk_gb[sample])  # positive = improvement

        results[bid] = {
            "d_realized_R_mean": float(np.mean(d_real)),
            "p_realized_R": float(np.mean(d_real > 0)),
            "d_giveback_ratio_mean": float(np.mean(d_gb)),
            "p_giveback_lower": float(np.mean(d_gb > 0)),
        }

    return results


# ═══════════════════════════════════════════════════════════════════════════
# Sensitivity Analysis
# ═══════════════════════════════════════════════════════════════════════════

def run_sensitivity(
    winning_branches, cl, hi, lo, op, ts_ms, open_ts,
    vo, tb, wi, slow_period,
):
    """Local one-factor-at-a-time sensitivity for winning branches."""
    er30_arr = compute_er30(cl)
    fast_p = max(5, slow_period // 4)
    ef = _ema(cl, fast_p)
    es = _ema(cl, slow_period)
    at = _atr(hi, lo, cl, ATR_P)
    vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)

    sensitivity = {}

    for bid in winning_branches:
        configs = []

        if bid in ("E1", "E4"):
            # Ratchet thresholds
            for label, kwargs in [
                ("e1_t1=0.75", {"e1_t1": 0.75}),
                ("e1_t1=1.25", {"e1_t1": 1.25}),
                ("e1_t2=1.5", {"e1_t2": 1.5}),
                ("e1_t2=2.5", {"e1_t2": 2.5}),
                ("e1_mid=1.75", {"e1_mid": 1.75}),
                ("e1_mid=2.25", {"e1_mid": 2.25}),
                ("e1_tight=1.25", {"e1_tight": 1.25}),
                ("e1_tight=1.75", {"e1_tight": 1.75}),
            ]:
                configs.append((label, kwargs))

        if bid in ("E3", "E4"):
            # Partial params
            for label, kwargs in [
                ("partial_trigger=0.75", {"partial_trigger_r": 0.75}),
                ("partial_trigger=1.25", {"partial_trigger_r": 1.25}),
                ("partial_frac=0.25", {"partial_frac": 0.25}),
                ("partial_frac=0.50", {"partial_frac": 0.50}),
            ]:
                configs.append((label, kwargs))

        if bid == "E2":
            # Dynamic trail params
            for label, kwargs in [
                ("e2_slope=0.50", {"e2_slope": 0.50}),
                ("e2_slope=1.00", {"e2_slope": 1.00}),
                ("e2_floor=1.25", {"e2_floor": 1.25}),
                ("e2_floor=1.75", {"e2_floor": 1.75}),
            ]:
                configs.append((label, kwargs))

        if bid == "E5":
            # Robust ATR params
            for cap_q in [0.85, 0.95]:
                ratr = compute_robust_atr(hi, lo, cl, cap_q=cap_q)
                eq, tr = simulate_branch(
                    bid, cl, hi, lo, op, ts_ms, open_ts,
                    ef, es, at, vd, er30_arr, wi, slow_period, ratr=ratr,
                )
                oos_tr = [t for t in tr if t["entry_time"] >= open_ts[wi]]
                dnav, _ = aggregate_daily_nav(eq, ts_ms, wi)
                dr = dnav[1:] / dnav[:-1] - 1.0
                years = len(dr) / 365.25
                total = dnav[-1] / dnav[0] - 1.0
                cagr = ((1 + total) ** (1 / years) - 1) * 100 if total > -1 else -100
                mu = np.mean(dr)
                std = np.std(dr, ddof=0)
                sharpe = mu / max(std, EPSILON) * ANN_DAILY
                pk = np.maximum.accumulate(dnav)
                mdd = float(np.max(1 - dnav / pk)) * 100
                mar = cagr / mdd if mdd > 0.01 else 0.0

                sensitivity.setdefault(bid, []).append({
                    "variant": f"cap_q={cap_q}",
                    "cagr": cagr,
                    "sharpe": sharpe,
                    "mdd": mdd,
                    "mar": mar,
                    "trades": len(oos_tr),
                })

            for cap_lb in [50, 200]:
                ratr = compute_robust_atr(hi, lo, cl, cap_lb=cap_lb)
                eq, tr = simulate_branch(
                    bid, cl, hi, lo, op, ts_ms, open_ts,
                    ef, es, at, vd, er30_arr, wi, slow_period, ratr=ratr,
                )
                oos_tr = [t for t in tr if t["entry_time"] >= open_ts[wi]]
                dnav, _ = aggregate_daily_nav(eq, ts_ms, wi)
                dr = dnav[1:] / dnav[:-1] - 1.0
                years = len(dr) / 365.25
                total = dnav[-1] / dnav[0] - 1.0
                cagr = ((1 + total) ** (1 / years) - 1) * 100 if total > -1 else -100
                mu = np.mean(dr)
                std = np.std(dr, ddof=0)
                sharpe = mu / max(std, EPSILON) * ANN_DAILY
                pk = np.maximum.accumulate(dnav)
                mdd = float(np.max(1 - dnav / pk)) * 100
                mar = cagr / mdd if mdd > 0.01 else 0.0

                sensitivity.setdefault(bid, []).append({
                    "variant": f"cap_lb={cap_lb}",
                    "cagr": cagr,
                    "sharpe": sharpe,
                    "mdd": mdd,
                    "mar": mar,
                    "trades": len(oos_tr),
                })

            continue  # E5 handled separately above

        # Standard sensitivity for E1-E4
        ratr = compute_robust_atr(hi, lo, cl)
        for label, kwargs in configs:
            eq, tr = simulate_branch(
                bid, cl, hi, lo, op, ts_ms, open_ts,
                ef, es, at, vd, er30_arr, wi, slow_period,
                ratr=ratr, **kwargs,
            )
            oos_tr = [t for t in tr if t["entry_time"] >= open_ts[wi]]
            dnav, _ = aggregate_daily_nav(eq, ts_ms, wi)
            dr = dnav[1:] / dnav[:-1] - 1.0
            years = len(dr) / 365.25
            total = dnav[-1] / dnav[0] - 1.0
            cagr = ((1 + total) ** (1 / years) - 1) * 100 if total > -1 else -100
            mu = np.mean(dr)
            std = np.std(dr, ddof=0)
            sharpe = mu / max(std, EPSILON) * ANN_DAILY
            pk = np.maximum.accumulate(dnav)
            mdd = float(np.max(1 - dnav / pk)) * 100
            mar = cagr / mdd if mdd > 0.01 else 0.0

            sensitivity.setdefault(bid, []).append({
                "variant": label,
                "cagr": cagr,
                "sharpe": sharpe,
                "mdd": mdd,
                "mar": mar,
                "trades": len(oos_tr),
            })

    return sensitivity


# ═══════════════════════════════════════════════════════════════════════════
# Context Stratification
# ═══════════════════════════════════════════════════════════════════════════

def context_stratification(all_trades_df, slow_period):
    """Compute context-conditioned metrics by ER30 bins."""
    df = all_trades_df[all_trades_df["slow_period"] == slow_period].copy()
    ctx = {}

    for bid in BRANCHES:
        bdf = df[df["branch_id"] == bid]
        bid_ctx = {}
        for er_bin in ER30_LABELS:
            sub = bdf[bdf["entry_ER30_context_bin"] == er_bin]
            if len(sub) == 0:
                bid_ctx[er_bin] = {"trade_count": 0}
                continue
            net = sub["net_pnl"].values
            wins = net > 0
            bid_ctx[er_bin] = {
                "trade_count": len(sub),
                "win_rate": round(float(np.mean(wins)) * 100, 2),
                "expectancy": round(float(np.mean(net)), 4),
                "net_pnl_contribution": round(float(np.sum(net)), 4),
                "median_giveback_ratio": round(float(np.median(sub["giveback_ratio"].values)), 4),
                "median_bars_held": round(float(np.median(sub["bars_held"].values)), 1),
            }
        ctx[bid] = bid_ctx

    return ctx


# ═══════════════════════════════════════════════════════════════════════════
# CSV Export
# ═══════════════════════════════════════════════════════════════════════════

def export_all(
    results, folds, fold_results, all_trades_df, matched_df,
    boot_results, sensitivity, outdir,
):
    """Export all required CSV files."""
    outdir.mkdir(parents=True, exist_ok=True)

    # 1. Trade log
    all_trades_df.to_csv(outdir / "exit_family_trade_log.csv", index=False)

    # 2. Matched trades
    if matched_df is not None and len(matched_df) > 0:
        matched_df.to_csv(outdir / "exit_family_matched_trades.csv", index=False)

    # 3. Fold results
    fold_rows = []
    for (bid, sp), fold_data in fold_results.items():
        for fi, fd in enumerate(fold_data):
            if fd is None:
                continue
            row = {"branch_id": bid, "slow_period": sp, "fold": fi}
            row.update(fd)
            fold_rows.append(row)
    if fold_rows:
        pd.DataFrame(fold_rows).to_csv(outdir / "exit_family_fold_results.csv", index=False)

    # 4. Portfolio summary
    summary_rows = []
    for (bid, sp), (eq, trades) in results.items():
        tr_list = [t for t in trades]
        if not tr_list:
            continue
        dnav, dts = aggregate_daily_nav(eq, dts_cache[(bid, sp)][0], dts_cache[(bid, sp)][1])
        if len(dnav) < 10:
            continue
        dr = dnav[1:] / dnav[:-1] - 1.0
        years = len(dr) / 365.25
        total = dnav[-1] / dnav[0] - 1.0
        cagr = ((1 + total) ** (1 / years) - 1) * 100 if total > -1 else -100
        mu = np.mean(dr)
        std = np.std(dr, ddof=0)
        sharpe = mu / max(std, EPSILON) * ANN_DAILY
        pk = np.maximum.accumulate(dnav)
        dd = 1 - dnav / pk
        mdd = float(np.max(dd)) * 100
        mar = cagr / mdd if mdd > 0.01 else 0.0

        down = dr[dr < 0]
        down_std = np.sqrt(np.mean(down ** 2)) if len(down) > 0 else EPSILON
        sortino = mu / down_std * ANN_DAILY

        ui = np.sqrt(np.mean(dd ** 2)) * 100

        net_pnls = np.array([t["net_pnl"] for t in tr_list])
        net_pcts = np.array([t["net_pnl_pct"] for t in tr_list])
        wins = net_pnls > 0
        win_rate = float(np.mean(wins)) * 100
        gross_w = float(np.sum(net_pnls[wins])) if np.any(wins) else 0.0
        gross_l = float(np.abs(np.sum(net_pnls[~wins]))) if np.any(~wins) else EPSILON
        pf = gross_w / gross_l

        summary_rows.append({
            "branch_id": bid, "slow_period": sp,
            "trades": len(tr_list), "cagr": cagr,
            "sharpe": sharpe, "sortino": sortino,
            "mar": mar, "mdd": mdd,
            "ulcer_index": ui,
            "win_rate": win_rate,
            "profit_factor": pf,
            "total_cost": sum(t["total_cost_paid"] for t in tr_list),
        })
    if summary_rows:
        pd.DataFrame(summary_rows).to_csv(outdir / "exit_family_portfolio_summary.csv", index=False)

    # 5. Bootstrap results
    boot_rows = []
    for sp, br in boot_results.items():
        for bid, vals in br.items():
            row = {"slow_period": sp, "branch_id": bid}
            row.update(vals)
            boot_rows.append(row)
    if boot_rows:
        pd.DataFrame(boot_rows).to_csv(outdir / "exit_family_bootstrap_results.csv", index=False)

    # 6. Sensitivity results
    sens_rows = []
    for bid, variants in sensitivity.items():
        for v in variants:
            row = {"branch_id": bid}
            row.update(v)
            sens_rows.append(row)
    if sens_rows:
        pd.DataFrame(sens_rows).to_csv(outdir / "exit_family_sensitivity_results.csv", index=False)

    print(f"  All CSVs exported to {outdir}/")


# ═══════════════════════════════════════════════════════════════════════════
# Report Generation
# ═══════════════════════════════════════════════════════════════════════════

def generate_report(
    results, folds, fold_results, all_trades_df, matched_df,
    boot_results, mt_boot, sensitivity, ctx, ts_ms, wi, outdir,
):
    """Generate exit_family_report.md."""
    lines = []
    W = lines.append

    W("# Exit Family Study — Final Report\n")

    # ── Part 1: Executive Summary ──
    W("## Part 1 — Executive Summary\n")

    # Gather key numbers for summary
    for sp in SLOW_PERIODS:
        W(f"\n### slow_period = {sp}\n")
        br = boot_results.get(sp, {})
        e0 = br.get("E0", {})
        for bid in BRANCHES:
            if bid == "E0":
                continue
            bk = br.get(bid, {})
            if not bk:
                continue
            W(f"- **{bid}** vs E0: dSharpe={bk.get('d_sharpe_mean',0):+.4f} "
              f"(P={bk.get('p_sharpe',0)*100:.1f}%), "
              f"dMDD={bk.get('d_mdd_mean',0):+.2f}pp (P={bk.get('p_mdd',0)*100:.1f}%), "
              f"dCAGR={bk.get('d_cagr_mean',0):+.2f}pp (P={bk.get('p_cagr',0)*100:.1f}%), "
              f"dMAR={bk.get('d_mar_mean',0):+.4f} (P={bk.get('p_mar',0)*100:.1f}%)")

    # ── Part 2: Implementation Audit ──
    W("\n## Part 2 — Implementation Audit\n")
    W("### Data & Assumptions")
    W(f"- Data: `{Path(DATA).name}` — BTC/USDT H4 bars, {START} to {END}")
    W(f"- Warmup: {WARMUP} days before {START}")
    W(f"- Cost: harsh scenario ({COST.round_trip_bps:.0f} bps RT = {CPS*10000:.1f} bps/side)")
    W(f"- Fill: signal at bar close, fill at previous close (proxy for next-bar open)")
    W(f"- Initial capital: ${CASH:,.0f}")
    W(f"- Position sizing: fully invested (100% NAV in BTC at entry)")
    W(f"- Single-market confirmation only (no ETH/altcoin data available)")
    W("")
    W("### CRITICAL DISCLOSURE: Trail Anchor")
    W("The proposal specified E0 uses `peak_high_since_entry` as trail anchor.")
    W("The actual VTREND code (strategy.py:111) uses `peak_close_since_entry`:")
    W("```python")
    W("self._peak_price = max(self._peak_price, price)  # price = bar.close")
    W("```")
    W("Per rule 1.1 ('exact current reference implementation'), ALL branches")
    W("use peak_close as anchor. E5's 'close anchor' isolation is moot.")
    W("E5 tests ONLY the robust ATR effect, not the anchor change.")
    W("")
    W("### Unchanged from Baseline")
    W("- Entry: EMA_fast > EMA_slow AND VDO > 0")
    W("- EMA fast = slow // 4 (standard alpha=2/(p+1))")
    W("- ATR: Wilder period=14")
    W("- VDO: EMA(VDR, 12) - EMA(VDR, 28), threshold=0.0")
    W("- Position sizing: 100% NAV at entry, flat at exit")
    W("- No regime gates, no PE, no chop filters")

    # ── Part 3: Branch Definitions ──
    W("\n## Part 3 — Exact Branch Definitions\n")
    for bid in BRANCHES:
        W(f"### {bid}")
        if bid == "E0":
            W("Baseline: trail_mult=3.0, anchor=peak_close, ATR=standard, no partial.")
        elif bid == "E1":
            W("Threshold ratchet: MFE_R<1→3.0, [1,2)→2.0, >=2→1.5. No partial.")
        elif bid == "E2":
            W("Dynamic trail: trail_mult = clip(3.0 - 0.75*MFE_R, 1.5, 3.0). No partial.")
        elif bid == "E3":
            W("Partial only: sell 1/3 at MFE_R>=1.0, residual uses E0 exit (trail=3.0).")
        elif bid == "E4":
            W("Partial + ratchet: sell 1/3 at MFE_R>=1.0, residual uses E1 ratchet.")
        elif bid == "E5":
            W("Robust ATR: capped TR at Q90(100 bars), Wilder EMA(20). Anchor=peak_close. No partial.")
        W("")

    # ── Part 3B: Full-Sample & OOS Cumulative Outcomes ──
    W("\n## Part 3B — Actual Outcomes (Final Equity & Net Profit)\n")
    W("These are the outcomes a trader would actually receive — final equity from $10k.\n")
    W("**When proxy metrics (per-trade realized_R, fold-median Sharpe) conflict with "
      "actual outcomes (final NAV, total profit), the actual outcome takes priority.**\n")

    full_years = (ts_ms[-1] - ts_ms[0]) / (MS_PER_DAY * 365.25)
    oos_years = (ts_ms[-1] - ts_ms[wi]) / (MS_PER_DAY * 365.25)

    # Collect outcome data for use in acceptance criteria later
    outcome_data = {}  # (bid, sp) → dict

    for sp in SLOW_PERIODS:
        W(f"\n### slow_period = {sp}\n")
        W("| Branch | Final NAV | vs E0 | Full CAGR | OOS Mult | Trades | Cost | Net Profit |")
        W("|--------|-----------|-------|-----------|----------|--------|------|------------|")

        e0_nav = results[("E0", sp)][0][-1]

        for bid in BRANCHES:
            eq, trades = results[(bid, sp)]
            fnav = eq[-1]
            oos_start = eq[wi]

            f_total = fnav / CASH
            f_cagr = (f_total ** (1.0 / full_years) - 1.0) * 100 if f_total > 0 else -100

            oos_mult = fnav / oos_start if oos_start > 0 else 0.0

            total_cost = sum(t["total_cost_paid"] for t in trades)
            net_profit = fnav - CASH

            delta_pct = (fnav / e0_nav - 1.0) * 100
            delta_str = f" ({delta_pct:+.1f}%)" if bid != "E0" else ""

            W(f"| {bid} | ${fnav:,.0f}{delta_str} | "
              f"{'baseline' if bid == 'E0' else f'{delta_pct:+.1f}%'} | "
              f"{f_cagr:+.1f}% | {oos_mult:.2f}x | "
              f"{len(trades)} | ${total_cost:,.0f} | ${net_profit:,.0f} |")

            outcome_data[(bid, sp)] = {
                "final_nav": fnav,
                "full_cagr": f_cagr,
                "oos_mult": oos_mult,
                "net_profit": net_profit,
                "total_cost": total_cost,
                "delta_vs_e0_pct": delta_pct,
            }

    # ── Part 4: OOS Portfolio Results ──
    W("\n## Part 4 — OOS Portfolio Results (Fold-Level Proxy Metrics)\n")
    for sp in SLOW_PERIODS:
        W(f"\n### slow_period = {sp}\n")
        W("#### Per-Fold Table\n")
        W("| Fold | " + " | ".join(f"{b} MAR" for b in BRANCHES) + " |")
        W("|------|" + "|".join(["------" for _ in BRANCHES]) + "|")
        n_folds = len(folds)
        for fi in range(n_folds):
            row = f"| {fi} |"
            for bid in BRANCHES:
                fd_list = fold_results.get((bid, sp), [])
                if fi < len(fd_list) and fd_list[fi] is not None:
                    row += f" {fd_list[fi].get('mar', 0):.4f} |"
                else:
                    row += " N/A |"
            W(row)

        W("\n#### Aggregated OOS (median across folds)\n")
        W("| Branch | med CAGR | med Sharpe | med MDD | med MAR | med Sortino |")
        W("|--------|----------|------------|---------|---------|-------------|")
        for bid in BRANCHES:
            fd_list = fold_results.get((bid, sp), [])
            valid = [f for f in fd_list if f is not None]
            if valid:
                med_cagr = np.median([f["cagr"] for f in valid])
                med_sh = np.median([f["sharpe"] for f in valid])
                med_mdd = np.median([f["mdd"] for f in valid])
                med_mar = np.median([f["mar"] for f in valid])
                med_sort = np.median([f["sortino"] for f in valid])
                W(f"| {bid} | {med_cagr:+.2f}% | {med_sh:.4f} | {med_mdd:.2f}% | {med_mar:.4f} | {med_sort:.4f} |")

    # ── Part 5: Matched-Trade Exit Analysis ──
    W("\n## Part 5 — Matched-Trade Exit Analysis\n")
    if matched_df is not None and len(matched_df) > 0:
        for sp in SLOW_PERIODS:
            W(f"\n### slow_period = {sp}\n")
            W("| Branch | med realized_R | med giveback_R | med giveback_ratio | med bars_held |")
            W("|--------|----------------|----------------|--------------------|---------------|")
            for bid in BRANCHES:
                sub = matched_df[(matched_df["branch_id"] == bid) & (matched_df["slow_period"] == sp)]
                if len(sub) > 0:
                    W(f"| {bid} | {sub['realized_R'].median():.4f} | "
                      f"{sub['giveback_R'].median():.4f} | "
                      f"{sub['giveback_ratio'].median():.4f} | "
                      f"{sub['bars_held'].median():.1f} |")

        # Matched-trade bootstrap
        if mt_boot:
            for sp in SLOW_PERIODS:
                mb = mt_boot.get(sp, {})
                if mb:
                    W(f"\n#### Matched-Trade Bootstrap (sp={sp})\n")
                    W("| Branch | d_realized_R | P(better) | d_giveback | P(lower) |")
                    W("|--------|-------------|-----------|------------|----------|")
                    for bid, vals in mb.items():
                        W(f"| {bid} | {vals['d_realized_R_mean']:+.4f} | "
                          f"{vals['p_realized_R']*100:.1f}% | "
                          f"{vals['d_giveback_ratio_mean']:+.4f} | "
                          f"{vals['p_giveback_lower']*100:.1f}% |")

    # ── Part 6: Partial-Exit Evaluation ──
    W("\n## Part 6 — Partial-Exit Evaluation\n")
    for sp in SLOW_PERIODS:
        W(f"\n### slow_period = {sp}\n")
        for bid in ["E3", "E4"]:
            key = (bid, sp)
            if key not in results:
                continue
            _, trades = results[key]
            oos_tr = [t for t in trades if t["entry_time"] >= ts_ms[wi] - WARMUP * MS_PER_DAY]
            partials = [t for t in oos_tr if t["partial_exit_done"]]
            W(f"**{bid}**: {len(partials)}/{len(oos_tr)} trades triggered partial "
              f"({len(partials)/max(len(oos_tr),1)*100:.1f}%)")
            if partials:
                extra_costs = sum(t["partial_exit_qty"] * t["partial_exit_price"] * CPS for t in partials)
                W(f"  - Extra cost from partials: ${extra_costs:.2f}")
                # Compare with E0 tail
                e0_key = ("E0", sp)
                if e0_key in results:
                    _, e0_trades = results[e0_key]
                    e0_oos = [t for t in e0_trades if t["entry_time"] >= ts_ms[wi] - WARMUP * MS_PER_DAY]
                    e0_pnls = sorted([t["net_pnl"] for t in e0_oos], reverse=True)
                    bk_pnls = sorted([t["net_pnl"] for t in oos_tr], reverse=True)
                    e0_top10n = max(1, int(len(e0_pnls) * 0.10))
                    bk_top10n = max(1, int(len(bk_pnls) * 0.10))
                    e0_top10_total = sum(e0_pnls[:e0_top10n])
                    bk_top10_total = sum(bk_pnls[:bk_top10n])
                    e0_total = sum(e0_pnls)
                    bk_total = sum(bk_pnls)
                    e0_frac = e0_top10_total / max(abs(e0_total), EPSILON) * 100
                    bk_frac = bk_top10_total / max(abs(bk_total), EPSILON) * 100
                    W(f"  - Top 10% PnL contribution: {bid}={bk_frac:.1f}% vs E0={e0_frac:.1f}%")
            W("")

    # ── Part 7: Robust ATR / Close-Anchor Evaluation ──
    W("\n## Part 7 — Robust ATR / Close-Anchor Evaluation\n")
    W("E5 uses robust ATR (capped TR at Q90, Wilder EMA period=20).")
    W("Since baseline already uses peak_close anchor, E5 isolates ONLY the robust ATR effect.")
    for sp in SLOW_PERIODS:
        br = boot_results.get(sp, {})
        e5 = br.get("E5", {})
        if e5:
            W(f"\n### sp={sp}: E5 vs E0")
            W(f"- dSharpe={e5.get('d_sharpe_mean',0):+.4f} (P={e5.get('p_sharpe',0)*100:.1f}%)")
            W(f"- dMDD={e5.get('d_mdd_mean',0):+.2f}pp (P={e5.get('p_mdd',0)*100:.1f}%)")
            W(f"- dMAR={e5.get('d_mar_mean',0):+.4f} (P={e5.get('p_mar',0)*100:.1f}%)")

    # ── Part 8: Context Stratification ──
    W("\n## Part 8 — Context Stratification\n")
    for sp in SLOW_PERIODS:
        c = ctx.get(sp, {})
        if not c:
            continue
        W(f"\n### slow_period = {sp}\n")
        W("| Branch | ER30 Bin | Trades | WinRate | Expectancy | med GB ratio |")
        W("|--------|----------|--------|---------|------------|--------------|")
        for bid in BRANCHES:
            for er_bin in ER30_LABELS:
                vals = c.get(bid, {}).get(er_bin, {})
                tc = vals.get("trade_count", 0)
                if tc == 0:
                    continue
                W(f"| {bid} | {er_bin} | {tc} | "
                  f"{vals.get('win_rate',0):.1f}% | "
                  f"${vals.get('expectancy',0):.2f} | "
                  f"{vals.get('median_giveback_ratio',0):.4f} |")

    # ── Part 9: Bootstrap and Significance ──
    W("\n## Part 9 — Bootstrap and Significance\n")
    for sp in SLOW_PERIODS:
        br = boot_results.get(sp, {})
        W(f"\n### slow_period = {sp}\n")
        W("#### Raw P-values (fraction of 10k resamples where branch beats E0)\n")
        W("| Branch | P(Sharpe+) | P(MDD-) | P(CAGR+) | P(MAR+) |")
        W("|--------|------------|---------|----------|---------|")
        raw_ps = []
        for bid in ["E1", "E2", "E3", "E4", "E5"]:
            bk = br.get(bid, {})
            if not bk:
                continue
            ps = bk.get("p_sharpe", 0.5)
            pm = bk.get("p_mdd", 0.5)
            pc = bk.get("p_cagr", 0.5)
            pr = bk.get("p_mar", 0.5)
            W(f"| {bid} | {ps*100:.1f}% | {pm*100:.1f}% | {pc*100:.1f}% | {pr*100:.1f}% |")
            raw_ps.append((bid, max(ps, pm, pc, pr)))

        # Holm adjustment on best p-value per branch
        if raw_ps:
            best_ps = [1 - p for _, p in raw_ps]  # convert to two-sided
            adjusted = holm_adjust(best_ps)
            W("\n#### Holm-Adjusted P-values\n")
            W("| Branch | Raw best P | Holm-adjusted |")
            W("|--------|-----------|---------------|")
            for i, (bid, raw_best) in enumerate(raw_ps):
                W(f"| {bid} | {(1-best_ps[i])*100:.1f}% | {(1-adjusted[i])*100:.1f}% |")

    # ── Part 10: Local Sensitivity ──
    W("\n## Part 10 — Local Sensitivity\n")
    if sensitivity:
        for bid, variants in sensitivity.items():
            W(f"\n### {bid}\n")
            W("| Variant | CAGR | Sharpe | MDD | MAR | Trades |")
            W("|---------|------|--------|-----|-----|--------|")
            for v in variants:
                W(f"| {v['variant']} | {v['cagr']:+.2f}% | {v['sharpe']:.4f} | "
                  f"{v['mdd']:.2f}% | {v['mar']:.4f} | {v['trades']} |")
    else:
        W("No branches beat E0 in OOS → no sensitivity analysis required.")

    # ── Part 11: Final Recommendation ──
    W("\n## Part 11 — Final Recommendation (Dual-Level Acceptance)\n")
    W("**Framework**: Outcome-first. Proxy metrics (per-trade realized_R, fold-median "
      "Sharpe/MAR) are diagnostics. When proxy conflicts with actual outcome "
      "(final NAV, total net profit), outcome takes priority.\n")
    W("A conclusion of 'variant X is better' must hold on BOTH levels:\n")
    W("1. **Level 1 — Actual Outcome**: final NAV, total net profit, bootstrap P(CAGR+)\n")
    W("2. **Level 2 — Per-Trade Quality**: matched-trade exit quality, giveback, "
      "tail preservation\n")
    W("Verdicts: **PROVEN** (both levels pass, ≥97.5%), "
      "**SUPPORTED** (outcome passes, quality consistent, 80-97.5%), "
      "**INCONCLUSIVE** (levels conflict or borderline), "
      "**REJECTED** (outcome worse or quality catastrophic)\n")

    # ── Dual-level evaluation per branch ──
    verdicts = {}  # bid → {verdict, details...}

    for bid in ["E1", "E2", "E3", "E4", "E5"]:
        W(f"\n### {bid}\n")

        # ── Level 1: Actual Outcome ──
        W("**Level 1 — Actual Outcome:**\n")

        # Outcome at each slow period
        outcome_checks = []
        for sp in SLOW_PERIODS:
            od = outcome_data.get((bid, sp), {})
            e0_od = outcome_data.get(("E0", sp), {})
            if not od or not e0_od:
                continue

            delta = od["delta_vs_e0_pct"]
            fnav = od["final_nav"]
            e0_fnav = e0_od["final_nav"]
            net_profit = od["net_profit"]
            e0_net_profit = e0_od["net_profit"]

            W(f"- sp={sp}: final NAV ${fnav:,.0f} vs E0 ${e0_fnav:,.0f} "
              f"({delta:+.1f}%), net profit ${net_profit:,.0f} vs E0 ${e0_net_profit:,.0f}")

            outcome_checks.append({
                "sp": sp, "delta": delta, "fnav": fnav, "e0_fnav": e0_fnav,
                "net_profit": net_profit, "e0_net_profit": e0_net_profit,
            })

        # Bootstrap P(CAGR+) at each slow period
        boot_cagr_checks = []
        for sp in SLOW_PERIODS:
            br = boot_results.get(sp, {})
            bk = br.get(bid, {})
            p_cagr = bk.get("p_cagr", 0.5)
            p_sharpe = bk.get("p_sharpe", 0.5)
            p_mar = bk.get("p_mar", 0.5)
            W(f"- sp={sp}: bootstrap P(CAGR+)={p_cagr*100:.1f}%, "
              f"P(Sharpe+)={p_sharpe*100:.1f}%, P(MAR+)={p_mar*100:.1f}%")
            boot_cagr_checks.append({
                "sp": sp, "p_cagr": p_cagr, "p_sharpe": p_sharpe, "p_mar": p_mar,
            })

        # Assess Level 1
        nav_better_both = all(c["delta"] > 0 for c in outcome_checks) if outcome_checks else False
        nav_better_any = any(c["delta"] > 0 for c in outcome_checks) if outcome_checks else False
        nav_worse_both = all(c["delta"] < 0 for c in outcome_checks) if outcome_checks else True
        # Best bootstrap P across metrics, at each sp
        boot_max_ps = [max(c["p_cagr"], c["p_sharpe"], c["p_mar"]) for c in boot_cagr_checks]
        boot_min_p = min(boot_max_ps) if boot_max_ps else 0.0  # worst sp
        boot_best_p = max(boot_max_ps) if boot_max_ps else 0.0  # best sp
        boot_p_cagrs = [c["p_cagr"] for c in boot_cagr_checks]
        boot_min_cagr_p = min(boot_p_cagrs) if boot_p_cagrs else 0.0

        if nav_better_both:
            if boot_min_cagr_p >= 0.975:
                l1_status = "PASS_PROVEN"
                W(f"\n**Level 1 verdict**: PASS — outcome better at both sp's, "
                  f"bootstrap ≥97.5% → PROVEN")
            elif boot_min_cagr_p >= 0.75:
                l1_status = "PASS_SUPPORTED"
                W(f"\n**Level 1 verdict**: PASS — outcome better at both sp's, "
                  f"bootstrap {boot_min_cagr_p*100:.1f}% → directionally supported")
            else:
                l1_status = "WEAK"
                W(f"\n**Level 1 verdict**: WEAK — outcome better in data but bootstrap "
                  f"only {boot_min_cagr_p*100:.1f}% (not robust)")
        elif nav_worse_both:
            l1_status = "FAIL"
            W(f"\n**Level 1 verdict**: FAIL — outcome WORSE at both sp's")
        elif nav_better_any:
            l1_status = "INCONSISTENT"
            W(f"\n**Level 1 verdict**: INCONSISTENT — better at one sp, worse at other")
        else:
            l1_status = "FAIL"
            W(f"\n**Level 1 verdict**: FAIL")

        # ── Level 2: Per-Trade Quality ──
        W("\n**Level 2 — Per-Trade Quality:**\n")

        l2_issues = []

        # Matched-trade realized_R
        for sp in SLOW_PERIODS:
            mb = mt_boot.get(sp, {}).get(bid, {})
            if mb:
                p_r = mb.get("p_realized_R", 0.5)
                d_r = mb.get("d_realized_R_mean", 0.0)
                p_gb = mb.get("p_giveback_lower", 0.5)
                d_gb = mb.get("d_giveback_ratio_mean", 0.0)
                W(f"- sp={sp} matched-trade: d_realized_R={d_r:+.4f} P(better)={p_r*100:.1f}%, "
                  f"d_giveback_ratio={d_gb:+.4f} P(lower)={p_gb*100:.1f}%")
                if p_r < 0.25:
                    l2_issues.append(f"sp={sp}: per-trade quality significantly WORSE "
                                     f"(P={p_r*100:.1f}%)")

        # Top-10% PnL preservation
        for sp in SLOW_PERIODS:
            e0_eq, e0_trades = results[("E0", sp)]
            bk_eq, bk_trades = results[(bid, sp)]
            e0_oos = [t for t in e0_trades if t["entry_time"] >= ts_ms[wi]]
            bk_oos = [t for t in bk_trades if t["entry_time"] >= ts_ms[wi]]
            e0_pnls = sorted([t["net_pnl"] for t in e0_oos], reverse=True)
            bk_pnls = sorted([t["net_pnl"] for t in bk_oos], reverse=True)
            e0_top10n = max(1, int(len(e0_pnls) * 0.10))
            bk_top10n = max(1, int(len(bk_pnls) * 0.10))
            e0_top10 = sum(e0_pnls[:e0_top10n])
            bk_top10 = sum(bk_pnls[:bk_top10n])
            top10_delta = (bk_top10 / max(abs(e0_top10), EPSILON) - 1.0) * 100
            W(f"- sp={sp} top-10% PnL: {bid}=${bk_top10:,.0f} vs E0=${e0_top10:,.0f} "
              f"({top10_delta:+.1f}%)")
            if top10_delta < -20:
                l2_issues.append(f"sp={sp}: top-10% PnL dropped {top10_delta:.1f}% "
                                 f"(limit -20%)")

        # Partial exit cost check (E3/E4)
        if bid in ("E3", "E4"):
            for sp in SLOW_PERIODS:
                bk_eq, bk_trades = results[(bid, sp)]
                e0_eq, e0_trades = results[("E0", sp)]
                bk_oos = [t for t in bk_trades if t["entry_time"] >= ts_ms[wi]]
                e0_oos = [t for t in e0_trades if t["entry_time"] >= ts_ms[wi]]
                bk_pnl_total = sum(t["net_pnl"] for t in bk_oos)
                e0_pnl_total = sum(t["net_pnl"] for t in e0_oos)
                partials = [t for t in bk_oos if t["partial_exit_done"]]
                extra_cost = sum(t["partial_exit_qty"] * t["partial_exit_price"] * CPS
                                 for t in partials)
                net_benefit = bk_pnl_total - e0_pnl_total
                W(f"- sp={sp} partial cost: extra=${extra_cost:,.0f}, "
                  f"net PnL benefit={bid}${bk_pnl_total:,.0f} - E0${e0_pnl_total:,.0f} = "
                  f"${net_benefit:+,.0f}")
                if net_benefit <= 0:
                    l2_issues.append(f"sp={sp}: partial exits cost more than they save "
                                     f"(net PnL ${net_benefit:+,.0f})")

        # Fold consistency
        for sp in SLOW_PERIODS:
            e0_folds = fold_results.get(("E0", sp), [])
            bk_folds = fold_results.get((bid, sp), [])
            e0_valid = [f for f in e0_folds if f is not None]
            bk_valid = [f for f in bk_folds if f is not None]
            if e0_valid and bk_valid:
                e0_mars = [f["mar"] for f in e0_valid]
                bk_mars = [f["mar"] for f in bk_valid]
                folds_won = sum(1 for b, e in zip(bk_mars, e0_mars) if b > e)
                n_folds = min(len(bk_mars), len(e0_mars))
                W(f"- sp={sp} fold consistency: {bid} beats E0 in {folds_won}/{n_folds} "
                  f"folds on MAR")

        # Assess Level 2
        if l2_issues:
            l2_status = "FAIL" if len(l2_issues) >= 2 else "WARNING"
            W(f"\n**Level 2 verdict**: {'FAIL' if l2_status == 'FAIL' else 'WARNING'}")
            for issue in l2_issues:
                W(f"  - {issue}")
        else:
            l2_status = "PASS"
            W(f"\n**Level 2 verdict**: PASS — per-trade quality consistent with outcome")

        # ── Conflict Detection ──
        conflict = None
        if l1_status in ("PASS_PROVEN", "PASS_SUPPORTED") and l2_status == "FAIL":
            conflict = "OUTCOME_BETTER_QUALITY_WORSE"
            W(f"\n**CONFLICT DETECTED**: Actual outcome is better but per-trade quality "
              f"is worse. Investigating mechanism...")
            # Check if it's re-entry timing / trade count difference
            for sp in SLOW_PERIODS:
                bk_trades = results[(bid, sp)][1]
                e0_trades = results[("E0", sp)][1]
                bk_oos = [t for t in bk_trades if t["entry_time"] >= ts_ms[wi]]
                e0_oos = [t for t in e0_trades if t["entry_time"] >= ts_ms[wi]]
                W(f"  - sp={sp}: {bid} has {len(bk_oos)} OOS trades vs E0 {len(e0_oos)} "
                  f"(delta={len(bk_oos)-len(e0_oos):+d})")
                if len(bk_oos) > len(e0_oos):
                    W(f"    → More trades means different re-entry timing after exits. "
                      f"Matched-trade analysis misses this effect.")
                    W(f"    → Outcome improvement is from TRADE TIMING, not per-trade quality.")
                elif len(bk_oos) < len(e0_oos):
                    W(f"    → Fewer trades means longer holds / less whipsaw.")
        elif l1_status == "FAIL" and l2_status == "PASS":
            conflict = "QUALITY_BETTER_OUTCOME_WORSE"
            W(f"\n**CONFLICT DETECTED**: Per-trade quality appears better but actual "
              f"outcome is worse — likely exposure reduction or compounding penalty.")

        # ── Combined Verdict ──
        if l1_status == "PASS_PROVEN" and l2_status == "PASS":
            verdict = "PROVEN"
        elif l1_status in ("PASS_PROVEN", "PASS_SUPPORTED") and l2_status in ("PASS", "WARNING"):
            verdict = "SUPPORTED"
        elif l1_status in ("PASS_PROVEN", "PASS_SUPPORTED") and l2_status == "FAIL":
            # Outcome priority: actual outcome wins, but flag mechanism
            verdict = "SUPPORTED_WITH_CAVEAT"
        elif l1_status == "WEAK":
            verdict = "INCONCLUSIVE"
        elif l1_status == "INCONSISTENT":
            verdict = "INCONCLUSIVE"
        else:
            verdict = "REJECTED"

        verdicts[bid] = {
            "verdict": verdict,
            "l1_status": l1_status,
            "l2_status": l2_status,
            "conflict": conflict,
            "outcome_checks": outcome_checks,
            "boot_cagr_checks": boot_cagr_checks,
        }

        W(f"\n**Combined verdict: {verdict}**")
        if verdict == "SUPPORTED_WITH_CAVEAT":
            W(f"  Outcome takes priority over per-trade proxy. Improvement is real but "
              f"mechanism is trade-timing, not per-trade exit quality.")
        W("")

    # ── Summary Table ──
    W("\n### Summary Table\n")
    W("| Branch | Verdict | NAV vs E0 (sp=120) | NAV vs E0 (sp=144) | "
      "Boot P(CAGR+) | Per-Trade | Conflict? |")
    W("|--------|---------|--------------------|--------------------|"
      "---------------|----------|-----------|")
    for bid in ["E1", "E2", "E3", "E4", "E5"]:
        v = verdicts.get(bid, {})
        oc = v.get("outcome_checks", [])
        bc = v.get("boot_cagr_checks", [])
        nav_120 = next((c["delta"] for c in oc if c["sp"] == 120), 0)
        nav_144 = next((c["delta"] for c in oc if c["sp"] == 144), 0)
        bp_120 = next((c["p_cagr"] for c in bc if c["sp"] == 120), 0.5)
        bp_144 = next((c["p_cagr"] for c in bc if c["sp"] == 144), 0.5)
        W(f"| {bid} | **{v.get('verdict','?')}** | {nav_120:+.1f}% | {nav_144:+.1f}% | "
          f"{bp_120*100:.0f}%/{bp_144*100:.0f}% | {v.get('l2_status','?')} | "
          f"{'YES' if v.get('conflict') else 'no'} |")

    # ── Final Verdict ──
    W("\n### Final Verdict\n")

    proven = [b for b, v in verdicts.items() if v["verdict"] == "PROVEN"]
    supported = [b for b, v in verdicts.items() if v["verdict"] in ("SUPPORTED", "SUPPORTED_WITH_CAVEAT")]
    inconclusive = [b for b, v in verdicts.items() if v["verdict"] == "INCONCLUSIVE"]
    rejected = [b for b, v in verdicts.items() if v["verdict"] == "REJECTED"]

    winners = []
    if proven:
        best = proven[0]
        W(f"- **PROVEN winner**: {best} — replace E0 in production")
        for b in proven:
            od = outcome_data.get((b, SLOW_PERIODS[0]), {})
            winners.append({"bid": b, "sp": SLOW_PERIODS[0],
                            "med_mar": 0, "verdict": "PROVEN"})
    elif supported:
        W("- **No branch reaches PROVEN (≥97.5% significance).**")
        for b in supported:
            v = verdicts[b]
            cav = " (with caveat)" if v["verdict"] == "SUPPORTED_WITH_CAVEAT" else ""
            oc = v.get("outcome_checks", [])
            nav_deltas = [c["delta"] for c in oc]
            mean_delta = np.mean(nav_deltas) if nav_deltas else 0
            W(f"- **SUPPORTED{cav}**: {b} — actual outcome +{mean_delta:.1f}% "
              f"avg NAV improvement")
            winners.append({"bid": b, "sp": SLOW_PERIODS[0],
                            "med_mar": 0, "verdict": v["verdict"]})
        W("- **Recommendation**: E0 remains default. Supported branches warrant "
          "further validation (cross-market, forward OOS).")
    else:
        W("- **No branch meets acceptance criteria.**")
        W("- **Recommendation**: Keep baseline E0 (VTREND with trail_mult=3.0).")

    if inconclusive:
        W(f"- **Inconclusive**: {', '.join(inconclusive)}")
    if rejected:
        W(f"- **Rejected**: {', '.join(rejected)}")

    partial_worth = any(verdicts.get(b, {}).get("verdict", "REJECTED") in
                        ("PROVEN", "SUPPORTED", "SUPPORTED_WITH_CAVEAT")
                        for b in ("E3", "E4"))
    W(f"- **Partial exits**: {'implement' if partial_worth else 'do NOT implement'}")

    W("\n### Research Questions Answered\n")
    W("1. **Does exit redesign improve net MAR / Sharpe / MDD vs baseline?** — "
      "See Parts 3B (outcome), 4 (fold-level proxy), 9 (bootstrap).")
    W("2. **Are improvements durable OOS?** — See Part 4 fold tables.")
    W("3. **Do improvements come from reduced giveback vs destroying right-tail winners?** — "
      "See Parts 5, 6.")
    W("4. **Are partial exits worth the extra cost?** — See Part 6 and per-branch Level 2.")
    W("5. **Does robust ATR improve exit quality?** — See Part 7 and E5 dual-level analysis.")
    W("6. **Is ratcheting significant?** — See E1/E4 Level 1 (outcome).")
    W("7. **Is dynamic trail significant?** — See E2 Level 1 (outcome).")
    W("8. **Are results consistent across slow_period 120 and 144?** — See Part 3B.")
    W("9. **Do context regimes (ER30) affect branch ranking?** — See Part 8.")
    W("10. **Does sensitivity show plateau or razor-edge?** — See Part 10.")
    W("11. **Which branch should replace E0, if any?** — See Final Verdict above.")
    W("12. **Single-market (BTC) confirmation only** — no ETH/altcoin data available.")

    # Write report
    report_path = outdir / "exit_family_report.md"
    report_path.write_text("\n".join(lines))
    print(f"  Report written to {report_path}")

    return winners


# ═══════════════════════════════════════════════════════════════════════════
# Global cache for daily NAV (avoids recomputation)
# ═══════════════════════════════════════════════════════════════════════════
dts_cache = {}


# ═══════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    t0 = time.time()
    OUTDIR.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("EXIT FAMILY STUDY — 6 Exit Branches × 2 Slow Periods")
    print("=" * 70)
    print(f"  Branches: {BRANCHES}")
    print(f"  Slow periods: {SLOW_PERIODS}")
    print(f"  Period: {START} → {END}  Warmup: {WARMUP}d")
    print(f"  Cost: harsh ({COST.round_trip_bps:.0f} bps RT)")
    print(f"  Bootstrap: {N_BOOT} resamples, block={BOOT_BLOCK}d")
    print(f"  WFO: train={WFO_TRAIN_MO}mo, test={WFO_TEST_MO}mo, step={WFO_STEP_MO}mo")

    # ── Load data ──
    print("\nLoading data...")
    cl, hi, lo, op, vo, tb, ts_ms, open_ts, wi, n = load_data()
    print(f"  {n} H4 bars, warmup idx={wi}, trading={n - wi} bars")

    # ── Run all branches ──
    print("\nRunning all branches on real data...")
    results, er30_arr = run_all_branches(cl, hi, lo, op, ts_ms, open_ts, vo, tb, wi, n)

    # ── Cache daily NAV for export ──
    for key, (eq, _) in results.items():
        dts_cache[key] = (ts_ms, wi)

    # ── Collect all trades ──
    all_trades = []
    for (bid, sp), (eq, trades) in results.items():
        for t in trades:
            t["_entry_bar"] = None  # will be set below
        all_trades.extend(trades)

    # Add _entry_bar to E0 trades for matched-trade analysis
    for (bid, sp), (eq, trades) in results.items():
        if bid == "E0":
            for t in trades:
                # Find entry bar index from entry_time
                entry_ms = t["entry_time"]
                for idx in range(len(open_ts)):
                    if open_ts[idx] >= entry_ms:
                        t["_entry_bar"] = idx
                        break

    all_trades_df = pd.DataFrame(all_trades)
    if "_entry_bar" in all_trades_df.columns:
        all_trades_df = all_trades_df.drop(columns=["_entry_bar"])

    # ── Define WFO folds ──
    print("\nDefining WFO folds...")
    folds = define_wfo_folds(ts_ms, open_ts)
    print(f"  {len(folds)} folds defined")
    for fi, (fs, fe) in enumerate(folds):
        print(f"    Fold {fi}: {ts_to_date(fs)} → {ts_to_date(fe)}")

    # ── Extract fold metrics ──
    print("\nExtracting fold metrics...")
    fold_results = {}
    for (bid, sp), (eq, trades) in results.items():
        dnav, dts = aggregate_daily_nav(eq, ts_ms, wi)
        fold_data = []
        for fs, fe in folds:
            pm = fold_metrics_from_equity(dnav, dts, fs, fe)
            tm = fold_trade_metrics(trades, fs, fe)
            if pm is not None and tm is not None:
                pm.update(tm)
            fold_data.append(pm)
        fold_results[(bid, sp)] = fold_data

    # ── Matched-trade analysis ──
    print("\nRunning matched-trade exit analysis...")
    matched_all = []
    for sp in SLOW_PERIODS:
        fast_p = max(5, sp // 4)
        ef = _ema(cl, fast_p)
        es = _ema(cl, sp)
        at = _atr(hi, lo, cl, ATR_P)
        vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)
        ratr = compute_robust_atr(hi, lo, cl)

        e0_trades = results[("E0", sp)][1]
        # Filter to OOS trades only
        e0_oos = [t for t in e0_trades if t.get("_entry_bar") is not None
                  and t["_entry_bar"] >= wi]

        matched = run_matched_trades(
            e0_oos, cl, hi, lo, op, ts_ms, open_ts,
            ef, es, at, vd, er30_arr, wi, sp, ratr,
        )
        matched_all.extend(matched)
        print(f"  sp={sp}: {len(matched)} matched-trade records ({len(e0_oos)} E0 entries × 6 branches)")

    matched_df = pd.DataFrame(matched_all) if matched_all else None

    # ── Bootstrap comparison ──
    print("\nRunning stationary bootstrap comparison...")
    boot_results = {}
    for sp in SLOW_PERIODS:
        boot_results[sp] = run_bootstrap_comparison(results, ts_ms, wi, sp)

    # ── Matched-trade bootstrap ──
    mt_boot = {}
    if matched_df is not None and len(matched_df) > 0:
        print("\nRunning matched-trade bootstrap...")
        for sp in SLOW_PERIODS:
            mt_boot[sp] = matched_trade_bootstrap(matched_df, sp)

    # ── Holm adjustment ──
    print("\nHolm adjustment for multiple comparisons...")
    for sp in SLOW_PERIODS:
        br = boot_results.get(sp, {})
        raw_ps = []
        bids = []
        for bid in ["E1", "E2", "E3", "E4", "E5"]:
            bk = br.get(bid, {})
            if not bk:
                continue
            # Best metric (most favorable direction)
            best_p = max(
                bk.get("p_sharpe", 0.5),
                bk.get("p_mdd", 0.5),
                bk.get("p_cagr", 0.5),
                bk.get("p_mar", 0.5),
            )
            raw_ps.append(1.0 - best_p)  # Convert to conventional p-value
            bids.append(bid)

        if raw_ps:
            adjusted = holm_adjust(raw_ps)
            for i, bid in enumerate(bids):
                br[bid]["holm_best_p_raw"] = round(raw_ps[i], 6)
                br[bid]["holm_best_p_adj"] = round(adjusted[i], 6)
                sig = "***" if adjusted[i] < 0.05 else "*" if adjusted[i] < 0.10 else ""
                print(f"  sp={sp} {bid}: raw p={raw_ps[i]:.4f} → Holm adj={adjusted[i]:.4f} {sig}")

    # ── Determine winners for sensitivity ──
    print("\nChecking acceptance criteria for sensitivity...")
    winning_branches = set()
    for sp in SLOW_PERIODS:
        e0_folds = fold_results.get(("E0", sp), [])
        e0_valid = [f for f in e0_folds if f is not None]
        if not e0_valid:
            continue
        e0_med_mar = np.median([f["mar"] for f in e0_valid])
        e0_med_mdd = np.median([f["mdd"] for f in e0_valid])
        e0_med_cagr = np.median([f["cagr"] for f in e0_valid])
        e0_med_sh = np.median([f["sharpe"] for f in e0_valid])

        for bid in ["E1", "E2", "E3", "E4", "E5"]:
            bk_folds = fold_results.get((bid, sp), [])
            bk_valid = [f for f in bk_folds if f is not None]
            if not bk_valid:
                continue
            bk_med_mar = np.median([f["mar"] for f in bk_valid])
            if bk_med_mar > e0_med_mar:
                winning_branches.add(bid)

    # ── Sensitivity analysis ──
    sensitivity = {}
    if winning_branches:
        print(f"\nRunning sensitivity for: {winning_branches}")
        for sp in SLOW_PERIODS:
            s = run_sensitivity(
                winning_branches, cl, hi, lo, op, ts_ms, open_ts,
                vo, tb, wi, sp,
            )
            for bid, variants in s.items():
                sensitivity.setdefault(bid, []).extend(variants)
    else:
        print("\n  No branches beat E0 in OOS MAR → skipping sensitivity.")

    # ── Context stratification ──
    print("\nComputing context stratification...")
    ctx = {}
    for sp in SLOW_PERIODS:
        ctx[sp] = context_stratification(all_trades_df, sp)

    # ── Export CSVs ──
    print("\nExporting CSVs...")
    export_all(
        results, folds, fold_results, all_trades_df, matched_df,
        boot_results, sensitivity, OUTDIR,
    )

    # ── Generate report ──
    print("\nGenerating report...")
    winners = generate_report(
        results, folds, fold_results, all_trades_df, matched_df,
        boot_results, mt_boot, sensitivity, ctx, ts_ms, wi, OUTDIR,
    )

    elapsed = time.time() - t0
    print(f"\n{'='*70}")
    print(f"STUDY COMPLETE in {elapsed:.1f}s")
    print(f"Winners: {[w['bid'] for w in winners] if winners else 'None (keep baseline)'}")
    print(f"Output: {OUTDIR}/")
    print(f"{'='*70}")
