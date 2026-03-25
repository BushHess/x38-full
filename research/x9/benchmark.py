#!/usr/bin/env python3
"""X9 Research — Break-Even Stop for E5+EMA21D1.

Hypothesis: When unrealized profit reaches X*R (R = trail_mult * ratr_at_entry),
moving the stop to entry price (breakeven) eliminates winning-to-losing trades.

Counter-hypothesis: ATR trail mult=3.0 already provides this organically.
Hard BE stop may whipsaw out of profitable trends prematurely.

Variants:
  E5     — E5+EMA21D1 baseline (no BE stop)
  BE_0.8 — BE stop activates at 0.8R profit
  BE_1.0 — BE stop activates at 1.0R profit

Tests:
  T1: Full backtest via BacktestEngine (3 variants × 3 cost scenarios)
  T2: Timescale robustness (16 slow_periods, vectorized)
  T3: Bootstrap VCBB (500 paths, head-to-head)
  T4: BE threshold sweep (0.4R to 2.5R, step 0.2)
  T5: Trade anatomy — per-trade MFE in R units, BE impact
  T6: Organic BE analysis — does ATR trail already protect at 1R?
"""

from __future__ import annotations

import csv
import json
import math
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from scipy.signal import lfilter
from scipy.stats import skew, kurtosis

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from v10.core.data import DataFeed
from v10.core.engine import BacktestEngine
from v10.core.types import SCENARIOS, Fill, MarketState, Signal
from v10.strategies.base import Strategy
from research.lib.vcbb import make_ratios, precompute_vcbb, gen_path_vcbb

from strategies.vtrend_e5_ema21_d1.strategy import (
    VTrendE5Ema21D1Config,
    VTrendE5Ema21D1Strategy,
)

# =========================================================================
# CONSTANTS
# =========================================================================

DATA = str(ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv")
CASH = 10_000.0
ANN = math.sqrt(6.0 * 365.25)

START = "2019-01-01"
END = "2026-02-20"
WARMUP = 365

VDO_F = 12
VDO_S = 28
VDO_THR = 0.0

# E5+EMA21D1 default params
SLOW = 120
TRAIL = 3.0
D1_EMA_P = 21

# Robust ATR params
RATR_CAP_Q = 0.90
RATR_CAP_LB = 100
RATR_PERIOD = 20

SLOW_PERIODS = [30, 48, 60, 72, 84, 96, 108, 120, 144, 168, 200, 240, 300, 360, 500, 720]

N_BOOT = 500
BLKSZ = 60
SEED = 42

COST_SCENARIOS = {
    "smart": SCENARIOS["smart"].per_side_bps / 10_000.0,
    "base": SCENARIOS["base"].per_side_bps / 10_000.0,
    "harsh": SCENARIOS["harsh"].per_side_bps / 10_000.0,
}
CPS_HARSH = COST_SCENARIOS["harsh"]

OUTDIR = Path(__file__).resolve().parent

STRATEGY_IDS = ["E5", "BE_0.8", "BE_1.0"]

BE_SWEEP_RANGE = [round(x, 1) for x in np.arange(0.4, 2.6, 0.2)]


# =========================================================================
# ENGINE STRATEGY: E5+EMA21D1 with Break-Even Stop
# =========================================================================

class VTrendE5BEStrategy(VTrendE5Ema21D1Strategy):
    """E5+EMA21D1 with optional break-even stop.

    When unrealized profit >= be_mult * R (R = trail_mult * ratr at signal bar),
    the stop floor is raised to the actual entry fill price.
    Effective stop = max(entry_price, trail_stop).
    """

    def __init__(
        self,
        config: VTrendE5Ema21D1Config | None = None,
        be_mult: float = 1.0,
    ) -> None:
        super().__init__(config)
        self._be_mult = be_mult
        self._signal_ratr = 0.0
        self._be_active = False

    def name(self) -> str:
        return f"vtrend_e5_be{self._be_mult}"

    def on_bar(self, state: MarketState) -> Signal | None:
        i = state.bar_index

        if (self._ema_fast is None or self._ratr is None or
                self._vdo is None or self._d1_regime_ok is None or i < 1):
            return None

        ema_f = self._ema_fast[i]
        ema_s = self._ema_slow[i]
        ratr_val = self._ratr[i]
        vdo_val = self._vdo[i]
        price = state.bar.close

        if math.isnan(ratr_val) or math.isnan(ema_f) or math.isnan(ema_s):
            return None

        trend_up = ema_f > ema_s
        trend_down = ema_f < ema_s

        if not self._in_position:
            regime_ok = bool(self._d1_regime_ok[i])
            if trend_up and vdo_val > self._c.vdo_threshold and regime_ok:
                self._in_position = True
                self._peak_price = price
                self._signal_ratr = ratr_val
                self._be_active = False
                return Signal(target_exposure=1.0, reason="e5_be_entry")
        else:
            self._peak_price = max(self._peak_price, price)

            # BE activation using actual portfolio entry price
            entry_px = state.entry_price_avg
            R = self._c.trail_mult * self._signal_ratr
            if not self._be_active and R > 0 and entry_px > 0:
                if price - entry_px >= self._be_mult * R:
                    self._be_active = True

            # Trail stop with BE floor
            trail_stop = self._peak_price - self._c.trail_mult * ratr_val
            if self._be_active and entry_px > 0:
                effective_stop = max(entry_px, trail_stop)
            else:
                effective_stop = trail_stop

            if price < effective_stop:
                reason = ("e5_be_stop" if self._be_active and entry_px > trail_stop
                          else "e5_trail_stop")
                self._in_position = False
                self._peak_price = 0.0
                return Signal(target_exposure=0.0, reason=reason)

            if trend_down:
                self._in_position = False
                self._peak_price = 0.0
                return Signal(target_exposure=0.0, reason="e5_trend_exit")

        return None

    def on_after_fill(self, state: MarketState, fill: Fill) -> None:
        pass


# =========================================================================
# FAST INDICATORS (vectorized)
# =========================================================================

def _ema(series: np.ndarray, period: int) -> np.ndarray:
    alpha = 2.0 / (period + 1)
    b = np.array([alpha])
    a = np.array([1.0, -(1.0 - alpha)])
    zi = np.array([(1.0 - alpha) * series[0]])
    out, _ = lfilter(b, a, series, zi=zi)
    return out


def _robust_atr(high, low, close,
                cap_q=RATR_CAP_Q, cap_lb=RATR_CAP_LB, period=RATR_PERIOD):
    """Robust ATR: cap TR at rolling Q90, then Wilder EMA.

    Uses sliding_window_view for vectorized percentile (~33x vs loop).
    """
    prev_cl = np.empty_like(close)
    prev_cl[0] = close[0]
    prev_cl[1:] = close[:-1]
    tr = np.maximum(high - low,
                    np.maximum(np.abs(high - prev_cl), np.abs(low - prev_cl)))

    n = len(tr)

    # Vectorized rolling quantile via sliding window
    windows = sliding_window_view(tr, cap_lb)  # (n-cap_lb+1, cap_lb)
    q_vals = np.percentile(windows, cap_q * 100, axis=1)

    tr_cap = np.full(n, np.nan)
    num = n - cap_lb
    tr_cap[cap_lb:] = np.minimum(tr[cap_lb:], q_vals[:num])

    # Wilder EMA via lfilter
    ratr = np.full(n, np.nan)
    s = cap_lb
    if s + period <= n:
        ratr[s + period - 1] = np.mean(tr_cap[s:s + period])
        alpha_w = 1.0 / period
        b_w = np.array([alpha_w])
        a_w = np.array([1.0, -(1.0 - alpha_w)])
        tail = tr_cap[s + period:]
        if len(tail) > 0:
            zi_w = np.array([(1.0 - alpha_w) * ratr[s + period - 1]])
            smoothed, _ = lfilter(b_w, a_w, tail, zi=zi_w)
            ratr[s + period:] = smoothed

    return ratr


def _vdo(close, high, low, volume, taker_buy, fast=VDO_F, slow=VDO_S):
    n = len(close)
    has_taker = taker_buy is not None and np.any(taker_buy > 0)
    if has_taker:
        taker_sell = np.maximum(volume - taker_buy, 0.0)
        vdr = np.zeros(n)
        mask = volume > 1e-12
        vdr[mask] = (taker_buy[mask] - taker_sell[mask]) / volume[mask]
    else:
        spread = high - low
        vdr = np.zeros(n)
        mask = spread > 1e-12
        vdr[mask] = (close[mask] - low[mask]) / spread[mask] * 2.0 - 1.0
    return _ema(vdr, fast) - _ema(vdr, slow)


def _metrics(nav, wi, nt=0):
    navs = nav[wi:]
    if len(navs) < 2:
        return {"sharpe": 0.0, "cagr": -100.0, "mdd": 100.0, "calmar": 0.0, "trades": nt}
    rets = navs[1:] / navs[:-1] - 1.0
    mu = np.mean(rets)
    std = np.std(rets, ddof=0)
    sharpe = (mu / std * ANN) if std > 1e-12 else 0.0
    total_ret = navs[-1] / navs[0] - 1.0
    yrs = len(rets) / (6.0 * 365.25)
    cagr = ((1 + total_ret) ** (1.0 / yrs) - 1.0) * 100 if yrs > 0 and total_ret > -1 else -100.0
    peak = np.maximum.accumulate(navs)
    dd = 1.0 - navs / peak
    mdd = np.max(dd) * 100
    calmar = cagr / mdd if mdd > 0.01 else 0.0
    return {"sharpe": sharpe, "cagr": cagr, "mdd": mdd, "calmar": calmar, "trades": nt}


# =========================================================================
# D1 REGIME FILTER
# =========================================================================

def _compute_d1_regime(h4_ct, d1_cl, d1_ct, d1_ema_period=D1_EMA_P):
    """Compute D1 EMA regime and map to H4 close_time grid."""
    d1_ema = _ema(d1_cl, d1_ema_period)
    d1_regime = d1_cl > d1_ema

    n_h4 = len(h4_ct)
    regime_h4 = np.zeros(n_h4, dtype=np.bool_)
    d1_idx = 0
    n_d1 = len(d1_cl)
    for i in range(n_h4):
        while d1_idx + 1 < n_d1 and d1_ct[d1_idx + 1] < h4_ct[i]:
            d1_idx += 1
        if d1_ct[d1_idx] < h4_ct[i]:
            regime_h4[i] = d1_regime[d1_idx]

    return regime_h4


# =========================================================================
# VECTORIZED SIM: E5+EMA21D1 with optional BE stop
# =========================================================================

def sim_e5_d1(cl, hi, lo, vo, tb, regime_h4, wi,
              slow_period=SLOW, trail_mult=TRAIL, be_mult=None,
              cps=CPS_HARSH, track_trades=False):
    """E5+EMA21D1 vectorized sim with optional break-even stop.

    be_mult: None = no BE, float = activate BE when profit >= be_mult * R
    R = trail_mult * ratr_at_entry (in price terms)

    Returns (nav, nt) or (nav, nt, trades_list) if track_trades=True.
    """
    n = len(cl)
    fast_p = max(5, slow_period // 4)
    ef = _ema(cl, fast_p)
    es = _ema(cl, slow_period)
    ratr = _robust_atr(hi, lo, cl)
    vd = _vdo(cl, hi, lo, vo, tb)

    cash = CASH
    bq = 0.0
    inp = False
    pe = px = False
    nt = 0
    pk = 0.0
    entry_px = 0.0
    ratr_at_entry = 0.0
    be_active = False
    exit_reason = ""

    nav = np.zeros(n)

    # Trade tracking
    trades_list = [] if track_trades else None
    cur_entry_bar = 0
    cur_entry_px = 0.0
    cur_peak = 0.0
    cur_be_bar = -1        # bar where BE activated (-1 = never)
    cur_trail_ge_entry = -1  # first bar where trail_stop >= entry_px

    for i in range(n):
        p = cl[i]
        if i > 0:
            fp = cl[i - 1]
            if pe:
                pe = False
                entry_px = fp
                ratr_at_entry = ratr[i - 1] if not math.isnan(ratr[i - 1]) else 0.0
                bq = cash / (fp * (1 + cps))
                cash = 0.0
                inp = True
                pk = p
                be_active = False
                cur_entry_bar = i
                cur_entry_px = fp
                cur_peak = p
                cur_be_bar = -1
                cur_trail_ge_entry = -1
            elif px:
                px = False
                if track_trades and cur_entry_px > 0:
                    R_val = trail_mult * ratr_at_entry if ratr_at_entry > 0 else 1.0
                    trades_list.append({
                        "entry_bar": cur_entry_bar,
                        "exit_bar": i,
                        "entry_px": cur_entry_px,
                        "exit_px": fp,
                        "peak_px": cur_peak,
                        "mfe_pct": (cur_peak / cur_entry_px - 1) * 100,
                        "mfe_R": (cur_peak - cur_entry_px) / R_val,
                        "mae_pct": (min(cur_entry_px, fp) / cur_entry_px - 1) * 100,
                        "pnl_pct": (fp / cur_entry_px - 1) * 100,
                        "R": R_val,
                        "be_activated": be_active,
                        "be_bar": cur_be_bar,
                        "trail_ge_entry_bar": cur_trail_ge_entry,
                        "exit_reason": exit_reason,
                        "bars_held": i - cur_entry_bar,
                    })
                cash = bq * fp * (1 - cps)
                bq = 0.0
                inp = False
                nt += 1

        nav[i] = cash + bq * p

        if math.isnan(ratr[i]) or math.isnan(ef[i]) or math.isnan(es[i]):
            continue

        if not inp:
            if ef[i] > es[i] and vd[i] > VDO_THR and regime_h4[i]:
                pe = True
        else:
            pk = max(pk, p)
            if track_trades:
                cur_peak = max(cur_peak, p)

            # Check BE activation
            if be_mult is not None and not be_active and ratr_at_entry > 0:
                R = trail_mult * ratr_at_entry
                if p - entry_px >= be_mult * R:
                    be_active = True
                    cur_be_bar = i

            # Track organic trail >= entry (for T6)
            trail_stop_val = pk - trail_mult * ratr[i]
            if track_trades and cur_trail_ge_entry < 0 and trail_stop_val >= entry_px:
                cur_trail_ge_entry = i

            # Exit: trail stop (with BE floor if active)
            if be_active:
                effective_stop = max(entry_px, trail_stop_val)
            else:
                effective_stop = trail_stop_val

            if p < effective_stop:
                if be_active and entry_px > trail_stop_val:
                    exit_reason = "be_stop"
                else:
                    exit_reason = "trail_stop"
                px = True
            elif ef[i] < es[i]:
                exit_reason = "trend_exit"
                px = True

    # Close open position at end
    if inp and bq > 0:
        if track_trades and cur_entry_px > 0:
            R_val = trail_mult * ratr_at_entry if ratr_at_entry > 0 else 1.0
            trades_list.append({
                "entry_bar": cur_entry_bar,
                "exit_bar": n - 1,
                "entry_px": cur_entry_px,
                "exit_px": cl[-1],
                "peak_px": cur_peak,
                "mfe_pct": (cur_peak / cur_entry_px - 1) * 100,
                "mfe_R": (cur_peak - cur_entry_px) / R_val,
                "mae_pct": 0.0,
                "pnl_pct": (cl[-1] / cur_entry_px - 1) * 100,
                "R": R_val,
                "be_activated": be_active,
                "be_bar": cur_be_bar,
                "trail_ge_entry_bar": cur_trail_ge_entry,
                "exit_reason": "eod",
                "bars_held": n - 1 - cur_entry_bar,
            })
        cash += bq * cl[-1] * (1 - cps)
        bq = 0
        nt += 1
        nav[-1] = cash

    if track_trades:
        return nav, nt, trades_list
    return nav, nt


def _run_vec(sid, cl, hi, lo, vo, tb, regime_h4, wi,
             slow_period=SLOW, trail_mult=TRAIL, cps=CPS_HARSH,
             track_trades=False):
    """Dispatch to sim with correct be_mult for strategy ID."""
    be_map = {"E5": None, "BE_0.8": 0.8, "BE_1.0": 1.0}
    be_mult = be_map.get(sid)
    return sim_e5_d1(cl, hi, lo, vo, tb, regime_h4, wi,
                     slow_period=slow_period, trail_mult=trail_mult,
                     be_mult=be_mult, cps=cps, track_trades=track_trades)


# =========================================================================
# T1: FULL BACKTEST via BacktestEngine
# =========================================================================

def run_t1_backtest():
    print("\n" + "=" * 80)
    print("T1: FULL BACKTEST via BacktestEngine (3 variants × 3 scenarios)")
    print("=" * 80)

    feed = DataFeed(DATA, start=START, end=END, warmup_days=WARMUP)
    results = {}

    for sid in STRATEGY_IDS:
        results[sid] = {}
        for scenario in ["smart", "base", "harsh"]:
            cost_cfg = SCENARIOS[scenario]
            cfg = VTrendE5Ema21D1Config(
                slow_period=SLOW, trail_mult=TRAIL,
                vdo_threshold=VDO_THR, d1_ema_period=D1_EMA_P,
            )
            if sid == "E5":
                strat = VTrendE5Ema21D1Strategy(cfg)
            else:
                be_mult = float(sid.split("_")[1])
                strat = VTrendE5BEStrategy(cfg, be_mult=be_mult)

            eng = BacktestEngine(feed=feed, strategy=strat, cost=cost_cfg,
                                 initial_cash=CASH, warmup_mode="no_trade")
            res = eng.run()
            s = res.summary
            results[sid][scenario] = {
                "sharpe": s.get("sharpe", 0),
                "cagr_pct": s.get("cagr_pct", 0),
                "max_drawdown_mid_pct": s.get("max_drawdown_mid_pct", 0),
                "calmar": s.get("calmar", 0),
                "trades": s.get("trades", 0),
                "wins": s.get("wins", 0),
                "losses": s.get("losses", 0),
                "win_rate_pct": s.get("win_rate_pct", 0),
                "profit_factor": s.get("profit_factor", 0),
                "avg_trade_pnl": s.get("avg_trade_pnl", 0),
                "avg_days_held": s.get("avg_days_held", 0),
                "avg_exposure": s.get("avg_exposure", 0),
                "turnover_per_year": s.get("turnover_per_year", 0),
            }
            exit_counts = {}
            for t in res.trades:
                exit_counts[t.exit_reason] = exit_counts.get(t.exit_reason, 0) + 1
            results[sid][scenario]["exit_reason_counts"] = exit_counts

    # Print results
    header = (f"{'Strategy':10s} {'Scen':6s} {'Sharpe':>8s} {'CAGR%':>8s} {'MDD%':>8s} "
              f"{'Calmar':>8s} {'Trades':>7s} {'WR%':>6s} {'PF':>7s} {'AvgExpo':>8s}")
    print(f"\n{header}")
    print("-" * len(header))
    for sid in STRATEGY_IDS:
        for sc in ["smart", "base", "harsh"]:
            m = results[sid][sc]
            pf_str = f"{m['profit_factor']:.4f}" if isinstance(m['profit_factor'], (int, float)) else str(m['profit_factor'])
            print(f"{sid:10s} {sc:6s} {m['sharpe']:8.4f} {m['cagr_pct']:8.2f} "
                  f"{m['max_drawdown_mid_pct']:8.2f} {m['calmar']:8.4f} {m['trades']:7d} "
                  f"{m['win_rate_pct']:6.1f} {pf_str:>7s} {m['avg_exposure']:8.4f}")

    # Delta table
    print(f"\n{'DELTA vs E5 baseline':>30s}")
    print("-" * 80)
    for be_sid in ["BE_0.8", "BE_1.0"]:
        for sc in ["smart", "base", "harsh"]:
            b = results["E5"][sc]
            x = results[be_sid][sc]
            print(f"  {be_sid:6s} {sc:6s}  dSharpe={x['sharpe']-b['sharpe']:+.4f}  "
                  f"dCAGR={x['cagr_pct']-b['cagr_pct']:+.2f}%  "
                  f"dMDD={x['max_drawdown_mid_pct']-b['max_drawdown_mid_pct']:+.2f}%  "
                  f"dTrades={x['trades']-b['trades']:+d}  "
                  f"dWR={x['win_rate_pct']-b['win_rate_pct']:+.1f}%")

    # Exit reason breakdown
    print(f"\n{'EXIT REASON BREAKDOWN (harsh)':>35s}")
    for sid in STRATEGY_IDS:
        m = results[sid]["harsh"]
        print(f"  {sid}: {m['exit_reason_counts']}")

    return results


# =========================================================================
# T2: TIMESCALE ROBUSTNESS (16 TS)
# =========================================================================

def run_t2_timescale(cl, hi, lo, vo, tb, regime_h4, wi):
    print("\n" + "=" * 80)
    print("T2: TIMESCALE ROBUSTNESS (16 slow_periods)")
    print("=" * 80)

    results = {sid: {} for sid in STRATEGY_IDS}
    for slow_p in SLOW_PERIODS:
        for sid in STRATEGY_IDS:
            nav, nt = _run_vec(sid, cl, hi, lo, vo, tb, regime_h4, wi,
                               slow_period=slow_p)
            m = _metrics(nav, wi, nt)
            results[sid][slow_p] = m

    # Print table
    print(f"\n{'Slow':>6s}", end="")
    for sid in STRATEGY_IDS:
        print(f"  {'Sharpe':>8s} {'CAGR%':>8s} {'MDD%':>8s}", end="")
    print()
    print("-" * (6 + len(STRATEGY_IDS) * 28))
    for slow_p in SLOW_PERIODS:
        print(f"{slow_p:6d}", end="")
        for sid in STRATEGY_IDS:
            m = results[sid][slow_p]
            print(f"  {m['sharpe']:8.4f} {m['cagr']:8.2f} {m['mdd']:8.2f}", end="")
        print()

    # Head-to-head wins
    for be_sid in ["BE_0.8", "BE_1.0"]:
        sharpe_wins = sum(1 for sp in SLOW_PERIODS
                          if results[be_sid][sp]["sharpe"] > results["E5"][sp]["sharpe"])
        mdd_wins = sum(1 for sp in SLOW_PERIODS
                       if results[be_sid][sp]["mdd"] < results["E5"][sp]["mdd"])
        cagr_wins = sum(1 for sp in SLOW_PERIODS
                        if results[be_sid][sp]["cagr"] > results["E5"][sp]["cagr"])
        print(f"\n  {be_sid} vs E5:  Sharpe {sharpe_wins}/16  CAGR {cagr_wins}/16  MDD {mdd_wins}/16")

    return results


# =========================================================================
# T3: BOOTSTRAP VCBB (500 paths × 16 timescales, head-to-head)
# =========================================================================

def run_t3_bootstrap(cl, hi, lo, vo, tb, regime_h4, wi):
    print("\n" + "=" * 80)
    print(f"T3: BOOTSTRAP VCBB ({N_BOOT} paths, block={BLKSZ})")
    print("=" * 80)

    n = len(cl)
    cr, hr, lr, vol_r, tb_r = make_ratios(cl[wi:], hi[wi:], lo[wi:], vo[wi:], tb[wi:])
    vcbb = precompute_vcbb(cr, BLKSZ)
    n_trans = n - wi - 1
    p0 = cl[wi]
    rng = np.random.default_rng(SEED)

    print("  Generating bootstrap paths...", end=" ", flush=True)
    t0 = time.time()
    boot_paths = []
    for _ in range(N_BOOT):
        bcl, bhi, blo, bvo, btb = gen_path_vcbb(
            cr, hr, lr, vol_r, tb_r, n_trans, BLKSZ, p0, rng, vcbb,
        )
        boot_paths.append((
            np.concatenate([cl[:wi], bcl]),
            np.concatenate([hi[:wi], bhi]),
            np.concatenate([lo[:wi], blo]),
            np.concatenate([vo[:wi], bvo]),
            np.concatenate([tb[:wi], btb]),
        ))
    print(f"done ({time.time() - t0:.1f}s)")

    # -- Default timescale bootstrap --
    results = {}
    h2h = {be_sid: {"sharpe": np.zeros(N_BOOT), "cagr": np.zeros(N_BOOT),
                     "mdd": np.zeros(N_BOOT)}
            for be_sid in ["BE_0.8", "BE_1.0"]}

    for sid in STRATEGY_IDS:
        sharpes, cagrs, mdds = [], [], []
        t0 = time.time()
        for b_idx, (bcl, bhi, blo, bvo, btb) in enumerate(boot_paths):
            bnav, bnt = _run_vec(sid, bcl, bhi, blo, bvo, btb, regime_h4, wi)
            bm = _metrics(bnav, wi, bnt)
            sharpes.append(bm["sharpe"])
            cagrs.append(bm["cagr"])
            mdds.append(bm["mdd"])

            if sid == "E5":
                for be_sid in h2h:
                    h2h[be_sid]["sharpe"][b_idx] -= bm["sharpe"]
                    h2h[be_sid]["cagr"][b_idx] -= bm["cagr"]
                    h2h[be_sid]["mdd"][b_idx] -= bm["mdd"]
            elif sid in h2h:
                h2h[sid]["sharpe"][b_idx] += bm["sharpe"]
                h2h[sid]["cagr"][b_idx] += bm["cagr"]
                h2h[sid]["mdd"][b_idx] += bm["mdd"]

        sharpes = np.array(sharpes)
        cagrs = np.array(cagrs)
        mdds = np.array(mdds)

        results[sid] = {
            "sharpe_median": float(np.median(sharpes)),
            "sharpe_p5": float(np.percentile(sharpes, 5)),
            "sharpe_p95": float(np.percentile(sharpes, 95)),
            "sharpe_mean": float(np.mean(sharpes)),
            "cagr_median": float(np.median(cagrs)),
            "cagr_p5": float(np.percentile(cagrs, 5)),
            "cagr_p95": float(np.percentile(cagrs, 95)),
            "mdd_median": float(np.median(mdds)),
            "mdd_p5": float(np.percentile(mdds, 5)),
            "mdd_p95": float(np.percentile(mdds, 95)),
            "p_cagr_gt0": float(np.mean(cagrs > 0)),
            "p_sharpe_gt0": float(np.mean(sharpes > 0)),
        }

        r = results[sid]
        elapsed = time.time() - t0
        print(f"  {sid:10s}  Sharpe={r['sharpe_median']:.4f} "
              f"[{r['sharpe_p5']:.4f}, {r['sharpe_p95']:.4f}]  "
              f"CAGR={r['cagr_median']:.2f}% [{r['cagr_p5']:.2f}, {r['cagr_p95']:.2f}]  "
              f"MDD={r['mdd_median']:.2f}%  P(CAGR>0)={r['p_cagr_gt0']:.3f}  ({elapsed:.1f}s)")

    # Head-to-head
    print(f"\n  HEAD-TO-HEAD vs E5 across {N_BOOT} bootstrap paths:")
    for be_sid in ["BE_0.8", "BE_1.0"]:
        d = h2h[be_sid]
        sw = np.sum(d["sharpe"] > 0)
        cw = np.sum(d["cagr"] > 0)
        mw = np.sum(d["mdd"] < 0)
        print(f"    {be_sid}: Sharpe wins {sw}/{N_BOOT} ({sw/N_BOOT*100:.1f}%)  "
              f"CAGR wins {cw}/{N_BOOT} ({cw/N_BOOT*100:.1f}%)  "
              f"MDD wins {mw}/{N_BOOT} ({mw/N_BOOT*100:.1f}%)")
        results[f"h2h_{be_sid}"] = {
            "sharpe_win_pct": float(sw / N_BOOT * 100),
            "sharpe_mean_delta": float(np.mean(d["sharpe"])),
            "cagr_win_pct": float(cw / N_BOOT * 100),
            "cagr_mean_delta": float(np.mean(d["cagr"])),
            "mdd_win_pct": float(mw / N_BOOT * 100),
            "mdd_mean_delta": float(np.mean(d["mdd"])),
        }

    return results


# =========================================================================
# T4: BE THRESHOLD SWEEP
# =========================================================================

def run_t4_be_sweep(cl, hi, lo, vo, tb, regime_h4, wi):
    print("\n" + "=" * 80)
    print(f"T4: BE THRESHOLD SWEEP ({BE_SWEEP_RANGE[0]}R to {BE_SWEEP_RANGE[-1]}R)")
    print("=" * 80)

    # Baseline (no BE)
    nav_base, nt_base = sim_e5_d1(cl, hi, lo, vo, tb, regime_h4, wi, be_mult=None)
    m_base = _metrics(nav_base, wi, nt_base)
    print(f"\n  Baseline (no BE): Sharpe={m_base['sharpe']:.4f}  "
          f"CAGR={m_base['cagr']:.2f}%  MDD={m_base['mdd']:.2f}%  "
          f"Trades={m_base['trades']}")

    results = {"baseline": m_base}
    print(f"\n{'BE_mult':>8s} {'Sharpe':>8s} {'CAGR%':>8s} {'MDD%':>8s} "
          f"{'Trades':>7s} {'dSharpe':>9s} {'dCAGR':>8s} {'dMDD':>8s}")
    print("-" * 72)
    for be_m in BE_SWEEP_RANGE:
        nav, nt = sim_e5_d1(cl, hi, lo, vo, tb, regime_h4, wi, be_mult=be_m)
        m = _metrics(nav, wi, nt)
        results[f"be_{be_m}"] = m
        print(f"{be_m:8.1f} {m['sharpe']:8.4f} {m['cagr']:8.2f} {m['mdd']:8.2f} "
              f"{m['trades']:7d} {m['sharpe']-m_base['sharpe']:+9.4f} "
              f"{m['cagr']-m_base['cagr']:+8.2f} {m['mdd']-m_base['mdd']:+8.2f}")

    return results


# =========================================================================
# T5: TRADE ANATOMY (per-trade MFE / BE impact)
# =========================================================================

def run_t5_trade_anatomy(cl, hi, lo, vo, tb, regime_h4, wi):
    print("\n" + "=" * 80)
    print("T5: TRADE ANATOMY — MFE in R units & BE impact")
    print("=" * 80)

    results = {}

    for sid in STRATEGY_IDS:
        be_mult = {"E5": None, "BE_0.8": 0.8, "BE_1.0": 1.0}[sid]
        nav, nt, trades = sim_e5_d1(cl, hi, lo, vo, tb, regime_h4, wi,
                                     be_mult=be_mult, track_trades=True)

        if not trades:
            print(f"  {sid}: no trades")
            continue

        pnls = np.array([t["pnl_pct"] for t in trades])
        mfes = np.array([t["mfe_R"] for t in trades])
        bars = np.array([t["bars_held"] for t in trades])

        n_t = len(trades)
        n_win = np.sum(pnls > 0)
        wr = n_win / n_t * 100

        # MFE distribution
        print(f"\n  {sid}: {n_t} trades, WR={wr:.1f}%")
        print(f"    MFE (R units): mean={np.mean(mfes):.2f}  "
              f"median={np.median(mfes):.2f}  "
              f"P25={np.percentile(mfes, 25):.2f}  "
              f"P75={np.percentile(mfes, 75):.2f}  "
              f"max={np.max(mfes):.2f}")

        # Trades that reached XR but ended as losers
        for threshold in [0.5, 0.8, 1.0, 1.5, 2.0]:
            reached = mfes >= threshold
            n_reached = np.sum(reached)
            if n_reached > 0:
                ended_loss = np.sum(reached & (pnls < 0))
                loss_pct = ended_loss / n_reached * 100
            else:
                ended_loss = 0
                loss_pct = 0
            print(f"    Reached {threshold:.1f}R: {n_reached}/{n_t} trades, "
                  f"{ended_loss} ended as losers ({loss_pct:.1f}%)")

        # Exit reason breakdown
        exit_groups = {}
        for t in trades:
            r = t["exit_reason"]
            if r not in exit_groups:
                exit_groups[r] = {"count": 0, "pnls": []}
            exit_groups[r]["count"] += 1
            exit_groups[r]["pnls"].append(t["pnl_pct"])

        print(f"    Exit reasons:")
        for reason, data in sorted(exit_groups.items()):
            avg_pnl = np.mean(data["pnls"])
            wr_r = sum(1 for p in data["pnls"] if p > 0) / data["count"] * 100
            print(f"      {reason:20s}  n={data['count']:4d}  "
                  f"avg_pnl={avg_pnl:+.2f}%  WR={wr_r:.1f}%")

        # Holding time
        print(f"    Bars held: mean={np.mean(bars):.1f}  "
              f"median={np.median(bars):.1f}  "
              f"P10={np.percentile(bars, 10):.0f}  "
              f"P90={np.percentile(bars, 90):.0f}")

        # Fat-tail stats
        if len(pnls) > 8:
            sk = float(skew(pnls))
            kt = float(kurtosis(pnls))
            print(f"    Return stats: skew={sk:.3f}  kurtosis={kt:.3f}")

        results[sid] = {
            "n_trades": n_t,
            "win_rate": wr,
            "mfe_mean_R": float(np.mean(mfes)),
            "mfe_median_R": float(np.median(mfes)),
            "mfe_p25_R": float(np.percentile(mfes, 25)),
            "mfe_p75_R": float(np.percentile(mfes, 75)),
            "exit_reasons": {r: d["count"] for r, d in exit_groups.items()},
            "avg_bars_held": float(np.mean(bars)),
        }

    return results


# =========================================================================
# T6: ORGANIC BE ANALYSIS — does ATR trail already protect at 1R?
# =========================================================================

def run_t6_organic_be(cl, hi, lo, vo, tb, regime_h4, wi):
    print("\n" + "=" * 80)
    print("T6: ORGANIC BE ANALYSIS — does ATR trail already protect at 1R?")
    print("=" * 80)

    # Run baseline E5 with full trade tracking
    nav, nt, trades = sim_e5_d1(cl, hi, lo, vo, tb, regime_h4, wi,
                                 be_mult=None, track_trades=True)

    if not trades:
        print("  No trades.")
        return {}

    n_t = len(trades)
    mfes = np.array([t["mfe_R"] for t in trades])
    pnls = np.array([t["pnl_pct"] for t in trades])

    # 1. How many trades have trail_stop >= entry_px at some point?
    trail_protected = sum(1 for t in trades if t["trail_ge_entry_bar"] >= 0)
    print(f"\n  Total trades: {n_t}")
    print(f"  Trades where trail_stop reaches entry_px (organic BE): "
          f"{trail_protected}/{n_t} ({trail_protected/n_t*100:.1f}%)")

    # 2. Among trades that reached 1R MFE: how many had organic BE protection?
    reached_1r = [t for t in trades if t["mfe_R"] >= 1.0]
    n_1r = len(reached_1r)
    if n_1r > 0:
        organic_at_1r = sum(1 for t in reached_1r if t["trail_ge_entry_bar"] >= 0)
        losers_at_1r = sum(1 for t in reached_1r if t["pnl_pct"] < 0)
        print(f"\n  Trades reaching ≥1.0R MFE: {n_1r}/{n_t}")
        print(f"    Had organic trail BE protection: {organic_at_1r}/{n_1r} "
              f"({organic_at_1r/n_1r*100:.1f}%)")
        print(f"    Ended as losers: {losers_at_1r}/{n_1r} "
              f"({losers_at_1r/n_1r*100:.1f}%)")

        if losers_at_1r > 0:
            # These are the trades BE could "save"
            saveable = [t for t in reached_1r if t["pnl_pct"] < 0]
            total_saved_pnl = sum(t["pnl_pct"] for t in saveable)
            print(f"    → BE could save these {losers_at_1r} trades "
                  f"(total lost: {total_saved_pnl:+.2f}%)")
            for t in saveable:
                print(f"      Trade bar {t['entry_bar']}-{t['exit_bar']}: "
                      f"MFE={t['mfe_R']:.2f}R  PnL={t['pnl_pct']:+.2f}%  "
                      f"exit={t['exit_reason']}")
        else:
            print(f"    → NO trades to save. ATR trail already provides organic BE at 1R.")

    # 3. Same analysis for 0.8R
    reached_08r = [t for t in trades if t["mfe_R"] >= 0.8]
    n_08r = len(reached_08r)
    if n_08r > 0:
        losers_08r = sum(1 for t in reached_08r if t["pnl_pct"] < 0)
        print(f"\n  Trades reaching ≥0.8R MFE: {n_08r}/{n_t}")
        print(f"    Ended as losers: {losers_08r}/{n_08r} "
              f"({losers_08r/n_08r*100:.1f}%)")

    # 4. Speed of organic BE: how many bars until trail >= entry?
    bars_to_be = [t["trail_ge_entry_bar"] - t["entry_bar"]
                  for t in trades if t["trail_ge_entry_bar"] >= 0]
    if bars_to_be:
        bars_arr = np.array(bars_to_be)
        print(f"\n  Bars until organic trail BE (among protected trades):")
        print(f"    mean={np.mean(bars_arr):.1f}  median={np.median(bars_arr):.0f}  "
              f"P10={np.percentile(bars_arr, 10):.0f}  P90={np.percentile(bars_arr, 90):.0f}")

    # 5. Key verdict
    print(f"\n  SUMMARY:")
    if n_1r > 0:
        pct_losers_at_1r = losers_at_1r / n_1r * 100
        if pct_losers_at_1r < 5:
            print(f"    ATR trail mult={TRAIL} ALREADY provides near-complete BE "
                  f"protection at 1R ({pct_losers_at_1r:.1f}% loss rate).")
            print(f"    → BE stop is REDUNDANT. Risk: whipsaw without benefit.")
        elif pct_losers_at_1r < 20:
            print(f"    ATR trail provides PARTIAL BE protection at 1R "
                  f"({pct_losers_at_1r:.1f}% loss rate).")
            print(f"    → BE stop MIGHT help. Check T2/T3 for net effect.")
        else:
            print(f"    ATR trail provides WEAK BE protection at 1R "
                  f"({pct_losers_at_1r:.1f}% loss rate).")
            print(f"    → BE stop has material to work with. Check T2/T3.")
    else:
        print(f"    No trades reach 1R MFE. BE stop has nothing to activate on.")

    return {
        "n_trades": n_t,
        "trail_protected": trail_protected,
        "reached_1r": n_1r,
        "losers_at_1r": losers_at_1r if n_1r > 0 else 0,
        "reached_08r": n_08r,
        "losers_at_08r": losers_08r if n_08r > 0 else 0,
        "bars_to_be_median": float(np.median(bars_arr)) if bars_to_be else None,
    }


# =========================================================================
# SAVE OUTPUTS
# =========================================================================

def save_results(bt_results, ts_results, boot_results,
                 sweep_results, anatomy_results, organic_results):
    out = {
        "backtest": {},
        "timescale": {},
        "bootstrap": {},
        "be_sweep": {},
        "trade_anatomy": {},
        "organic_be": organic_results,
    }

    for sid in STRATEGY_IDS:
        out["backtest"][sid] = {}
        for sc in ["smart", "base", "harsh"]:
            m = bt_results[sid][sc].copy()
            m.pop("exit_reason_counts", None)
            out["backtest"][sid][sc] = m

        out["timescale"][sid] = {}
        for sp in SLOW_PERIODS:
            out["timescale"][sid][str(sp)] = ts_results[sid][sp]

        if sid in boot_results:
            out["bootstrap"][sid] = boot_results[sid]

    for k in boot_results:
        if k.startswith("h2h_") or k.startswith("ts_boot"):
            out["bootstrap"][k] = boot_results[k]

    for k, v in sweep_results.items():
        out["be_sweep"][k] = v

    for k, v in anatomy_results.items():
        out["trade_anatomy"][k] = v

    # JSON
    json_path = OUTDIR / "x9_results.json"
    with open(json_path, "w") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"\nSaved: {json_path}")

    # CSV backtest table
    csv_path = OUTDIR / "x9_backtest_table.csv"
    fields = ["strategy", "scenario", "sharpe", "cagr_pct", "max_drawdown_mid_pct",
              "calmar", "trades", "win_rate_pct", "profit_factor",
              "avg_exposure", "avg_days_held", "turnover_per_year"]
    with open(csv_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for sid in STRATEGY_IDS:
            for sc in ["smart", "base", "harsh"]:
                row = {"strategy": sid, "scenario": sc}
                row.update({k: bt_results[sid][sc][k]
                           for k in fields if k not in ("strategy", "scenario")})
                w.writerow(row)
    print(f"Saved: {csv_path}")

    # CSV timescale table
    csv_ts = OUTDIR / "x9_timescale_table.csv"
    with open(csv_ts, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["slow_period",
                     "e5_sharpe", "e5_cagr", "e5_mdd",
                     "be08_sharpe", "be08_cagr", "be08_mdd",
                     "be10_sharpe", "be10_cagr", "be10_mdd"])
        for sp in SLOW_PERIODS:
            e5 = ts_results["E5"][sp]
            b08 = ts_results["BE_0.8"][sp]
            b10 = ts_results["BE_1.0"][sp]
            w.writerow([sp,
                        f"{e5['sharpe']:.4f}", f"{e5['cagr']:.2f}", f"{e5['mdd']:.2f}",
                        f"{b08['sharpe']:.4f}", f"{b08['cagr']:.2f}", f"{b08['mdd']:.2f}",
                        f"{b10['sharpe']:.4f}", f"{b10['cagr']:.2f}", f"{b10['mdd']:.2f}"])
    print(f"Saved: {csv_ts}")

    # CSV bootstrap table
    csv_boot = OUTDIR / "x9_bootstrap_table.csv"
    boot_fields = ["strategy", "sharpe_median", "sharpe_p5", "sharpe_p95",
                   "cagr_median", "cagr_p5", "cagr_p95",
                   "mdd_median", "mdd_p5", "mdd_p95",
                   "p_cagr_gt0", "p_sharpe_gt0"]
    with open(csv_boot, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=boot_fields)
        w.writeheader()
        for sid in STRATEGY_IDS:
            if sid in boot_results:
                row = {"strategy": sid}
                row.update({k: boot_results[sid].get(k)
                           for k in boot_fields if k != "strategy"})
                w.writerow(row)
    print(f"Saved: {csv_boot}")

    # CSV BE sweep
    csv_sweep = OUTDIR / "x9_be_sweep.csv"
    with open(csv_sweep, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["be_mult", "sharpe", "cagr", "mdd", "trades",
                     "d_sharpe", "d_cagr", "d_mdd"])
        base = sweep_results["baseline"]
        w.writerow(["none", f"{base['sharpe']:.4f}", f"{base['cagr']:.2f}",
                    f"{base['mdd']:.2f}", base["trades"], "0", "0", "0"])
        for be_m in BE_SWEEP_RANGE:
            k = f"be_{be_m}"
            if k in sweep_results:
                m = sweep_results[k]
                w.writerow([f"{be_m:.1f}",
                           f"{m['sharpe']:.4f}", f"{m['cagr']:.2f}",
                           f"{m['mdd']:.2f}", m["trades"],
                           f"{m['sharpe']-base['sharpe']:+.4f}",
                           f"{m['cagr']-base['cagr']:+.2f}",
                           f"{m['mdd']-base['mdd']:+.2f}"])
    print(f"Saved: {csv_sweep}")


# =========================================================================
# MAIN
# =========================================================================

def main():
    print("=" * 80)
    print("X9 RESEARCH — BREAK-EVEN STOP FOR E5+EMA21D1")
    print(f"  Data: {DATA}")
    print(f"  Period: {START} to {END} (warmup={WARMUP}d)")
    print(f"  E5 params: slow={SLOW}, trail={TRAIL}, vdo_thr={VDO_THR}, "
          f"d1_ema={D1_EMA_P}")
    print(f"  BE variants: 0.8R, 1.0R  |  Sweep: {BE_SWEEP_RANGE}")
    print(f"  Bootstrap: {N_BOOT} VCBB paths, block={BLKSZ}")
    print("=" * 80)

    t_start = time.time()

    # T1: Engine backtest
    bt_results = run_t1_backtest()

    # Load raw arrays for vectorized tests
    feed = DataFeed(DATA, start=START, end=END, warmup_days=WARMUP)
    cl = np.array([b.close for b in feed.h4_bars], dtype=np.float64)
    hi = np.array([b.high for b in feed.h4_bars], dtype=np.float64)
    lo = np.array([b.low for b in feed.h4_bars], dtype=np.float64)
    vo = np.array([b.volume for b in feed.h4_bars], dtype=np.float64)
    tb = np.array([b.taker_buy_base_vol for b in feed.h4_bars], dtype=np.float64)
    h4_ct = np.array([b.close_time for b in feed.h4_bars], dtype=np.int64)

    d1_cl = np.array([b.close for b in feed.d1_bars], dtype=np.float64)
    d1_ct = np.array([b.close_time for b in feed.d1_bars], dtype=np.int64)

    # Compute D1 regime mask
    regime_h4 = _compute_d1_regime(h4_ct, d1_cl, d1_ct, D1_EMA_P)

    # Warmup index
    wi = 0
    if feed.report_start_ms is not None:
        for j, b in enumerate(feed.h4_bars):
            if b.close_time >= feed.report_start_ms:
                wi = j
                break

    # T5 & T6 first (fast, answers the key question)
    anatomy_results = run_t5_trade_anatomy(cl, hi, lo, vo, tb, regime_h4, wi)
    organic_results = run_t6_organic_be(cl, hi, lo, vo, tb, regime_h4, wi)

    # T4: BE sweep
    sweep_results = run_t4_be_sweep(cl, hi, lo, vo, tb, regime_h4, wi)

    # T2: Timescale robustness
    ts_results = run_t2_timescale(cl, hi, lo, vo, tb, regime_h4, wi)

    # T3: Bootstrap (slow — run last)
    boot_results = run_t3_bootstrap(cl, hi, lo, vo, tb, regime_h4, wi)

    # Save
    save_results(bt_results, ts_results, boot_results,
                 sweep_results, anatomy_results, organic_results)

    elapsed = time.time() - t_start
    print(f"\n{'=' * 80}")
    print(f"X9 BENCHMARK COMPLETE — {elapsed:.0f}s total")
    print(f"{'=' * 80}")


if __name__ == "__main__":
    main()
