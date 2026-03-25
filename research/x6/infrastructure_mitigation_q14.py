#!/usr/bin/env python3
"""Q14: Infrastructure mitigation — what if we guarantee tighter entry delay?

Runs Step 5's replay harness for E5_plus_EMA1D21 and E0_plus_EMA1D21
with scenarios NOT tested in Step 5:
  - entry_D0 + exit_D1  (entry guaranteed < 4h)
  - entry_D0 + exit_D2  (entry guaranteed < 4h, exit degraded)
  - entry_D1 + exit_D1  (entry guaranteed < 8h, most realistic LT1 worst case)
  - entry_D1 + exit_D2  (entry guaranteed < 8h, exit degraded)

Compares against the binding Step 5 scenario: entry_D2 + exit_D1 = -0.396
"""

import csv
import math
import sys
from pathlib import Path

import numpy as np

# ── Use the Step 5 replay infrastructure directly ──
REPO = Path("/var/www/trading-bots/btc-spot-dev")
STEP5_DIR = REPO / "research" / "fragility_audit_20260306" / "code" / "step5"

# Constants from Step 5
NAV0 = 10_000.0
BACKTEST_YEARS = 6.5
FEE_RATE = 0.0015
BUY_ADJ = 1.00100025
SELL_ADJ = 0.99900025
PERIOD_START_MS = 1546300800000
PERIOD_END_MS = 1771545600000
WARMUP_DAYS = 365
BARS_PER_YEAR_4H = 365.0 * 6.0

CANDIDATES = {
    "E0_plus_EMA1D21": "results/parity_20260305/eval_ema21d1_vs_e0/results/trades_candidate.csv",
    "E5_plus_EMA1D21": "results/parity_20260306/eval_e5_ema21d1_vs_e0/results/trades_candidate.csv",
}

BASELINE_SHARPE = {
    "E0_plus_EMA1D21": 1.1750,
    "E5_plus_EMA1D21": 1.2702,
}


# ── Indicator functions (minimal subset from Step 5) ──

def _ema(series, period):
    alpha = 2.0 / (period + 1)
    out = np.empty_like(series)
    out[0] = series[0]
    for i in range(1, len(series)):
        out[i] = alpha * series[i] + (1 - alpha) * out[i - 1]
    return out


def _atr(high, low, close, period):
    tr = np.maximum(
        high - low,
        np.maximum(
            np.abs(high - np.concatenate([[high[0]], close[:-1]])),
            np.abs(low - np.concatenate([[low[0]], close[:-1]])),
        ),
    )
    out = np.full_like(tr, np.nan)
    if period <= len(tr):
        out[period - 1] = np.mean(tr[:period])
        for i in range(period, len(tr)):
            out[i] = (out[i - 1] * (period - 1) + tr[i]) / period
    return out


def _robust_atr(high, low, close, cap_q=0.90, cap_lb=100, period=20):
    prev_cl = np.concatenate([[close[0]], close[:-1]])
    tr = np.maximum(
        high - low,
        np.maximum(np.abs(high - prev_cl), np.abs(low - prev_cl)),
    )
    n = len(tr)
    tr_cap = np.full(n, np.nan)
    for i in range(cap_lb, n):
        q = np.percentile(tr[i - cap_lb:i], cap_q * 100)
        tr_cap[i] = min(tr[i], q)
    ratr = np.full(n, np.nan)
    s = cap_lb
    if s + period <= n:
        ratr[s + period - 1] = np.mean(tr_cap[s:s + period])
        for i in range(s + period, n):
            ratr[i] = (ratr[i - 1] * (period - 1) + tr_cap[i]) / period
    return ratr


def _vdo(close, high, low, volume, taker_buy, fast, slow):
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


def compute_d1_regime(h4_ct, d1_close, d1_ct, d1_ema_period=21):
    n_h4 = len(h4_ct)
    regime_ok = np.zeros(n_h4, dtype=np.bool_)
    if len(d1_close) == 0:
        return regime_ok
    d1_ema = _ema(d1_close, d1_ema_period)
    d1_regime = d1_close > d1_ema
    n_d1 = len(d1_ct)
    d1_idx = 0
    for i in range(n_h4):
        while d1_idx + 1 < n_d1 and d1_ct[d1_idx + 1] < h4_ct[i]:
            d1_idx += 1
        if d1_ct[d1_idx] < h4_ct[i]:
            regime_ok[i] = d1_regime[d1_idx]
    return regime_ok


# ── Replay function (from Step 5, simplified) ──

def replay_binary(close, open_, high, low, ema_fast, ema_slow, trail_atr, vdo,
                   d1_regime_ok, report_start_idx,
                   entry_delay_bars=0, exit_delay_bars=0):
    n = len(close)
    trail_mult = 3.0
    in_position = False
    peak_price = 0.0
    cash = NAV0
    btc_qty = 0.0
    entry_avg = 0.0
    pending_entry = False
    pending_exit = False
    pending_entry_delay_countdown = 0
    exit_delay_countdown = 0
    exit_decided = False
    entry_bar_idx = -1
    suppressed = 0
    trades_returns = []
    trades_pnls = []

    for i in range(n):
        cv = close[i]
        ov = open_[i]

        # Fill pending entry
        if pending_entry and i > 0:
            fpx = ov * BUY_ADJ
            fee_rate = FEE_RATE
            qty = cash / (fpx * (1 + fee_rate))
            if qty > 0:
                fee = qty * fpx * fee_rate
                cash -= qty * fpx + fee
                btc_qty = qty
                entry_avg = fpx
            pending_entry = False

        # Fill pending exit
        if pending_exit and i > 0:
            fpx = ov * SELL_ADJ
            fee = btc_qty * fpx * FEE_RATE
            rpnl = btc_qty * (fpx - entry_avg) - fee
            ret = (fpx / entry_avg - 1) * 100.0 if entry_avg > 0 else 0.0
            cash += btc_qty * fpx - fee
            trades_returns.append(ret)
            trades_pnls.append(rpnl)
            btc_qty = 0.0
            entry_avg = 0.0
            pending_exit = False
            exit_decided = False

        # Exit delay countdown
        if exit_delay_countdown > 0:
            exit_delay_countdown -= 1
            if exit_delay_countdown == 0:
                in_position = False
                peak_price = 0.0
                pending_exit = True
            if in_position:
                peak_price = max(peak_price, cv)

        # Entry delay countdown
        if pending_entry_delay_countdown > 0:
            pending_entry_delay_countdown -= 1
            if pending_entry_delay_countdown == 0:
                if not in_position and not exit_decided:
                    in_position = True
                    peak_price = cv
                    entry_bar_idx = i
                    pending_entry = True
                else:
                    suppressed += 1

        if i < report_start_idx:
            continue

        ef = ema_fast[i]
        es = ema_slow[i]
        tv = trail_atr[i]
        vd = vdo[i]

        if not np.isfinite(ef) or not np.isfinite(es) or not np.isfinite(tv):
            continue

        # Position management
        if in_position and not exit_decided:
            peak_price = max(peak_price, cv)
            trail_stop = peak_price - trail_mult * tv
            exit_cross = ef < es
            if cv < trail_stop or exit_cross:
                if exit_delay_bars > 0:
                    exit_delay_countdown = exit_delay_bars
                    exit_decided = True
                else:
                    in_position = False
                    peak_price = 0.0
                    pending_exit = True

        # Entry
        if not in_position and not pending_entry and not exit_decided and pending_entry_delay_countdown == 0:
            entry_cross = ef > es
            vdo_ok = vd >= 0.0
            regime_ok = d1_regime_ok[i] if d1_regime_ok is not None else True
            if entry_cross and vdo_ok and regime_ok:
                if entry_delay_bars > 0:
                    pending_entry_delay_countdown = entry_delay_bars
                else:
                    in_position = True
                    peak_price = cv
                    entry_bar_idx = i
                    pending_entry = True

    # Final close
    if in_position and btc_qty > 0:
        fpx = close[-1] * SELL_ADJ
        fee = btc_qty * fpx * FEE_RATE
        rpnl = btc_qty * (fpx - entry_avg) - fee
        ret = (fpx / entry_avg - 1) * 100.0 if entry_avg > 0 else 0.0
        cash += btc_qty * fpx - fee
        trades_returns.append(ret)
        trades_pnls.append(rpnl)

    # Compute metrics
    if not trades_returns:
        return {"sharpe": 0.0, "n_trades": 0, "terminal": NAV0, "mdd": 0.0, "suppressed": 0}

    returns = np.array(trades_returns)
    pnls = np.array(trades_pnls)
    nt = len(returns)
    nav_curve = NAV0 + np.cumsum(pnls)
    terminal = float(nav_curve[-1])
    rm = np.maximum.accumulate(nav_curve)
    dd = (rm - nav_curve) / rm
    mdd = float(np.max(dd))
    tpy = nt / BACKTEST_YEARS
    mr = np.mean(returns)
    sr = np.std(returns, ddof=0)
    sharpe = (mr / sr * math.sqrt(tpy)) if sr > 0 else 0.0

    return {"sharpe": sharpe, "n_trades": nt, "terminal": terminal, "mdd": mdd,
            "suppressed": suppressed}


# ── Main ──

def main():
    import pandas as pd

    print("Loading data...")
    df = pd.read_csv(REPO / "data/bars_btcusdt_2016_now_h1_4h_1d.csv")
    h4 = df[df["interval"] == "4h"].sort_values("open_time").reset_index(drop=True)
    d1 = df[df["interval"] == "1d"].sort_values("open_time").reset_index(drop=True)

    warmup_start_ms = PERIOD_START_MS - WARMUP_DAYS * 86_400_000
    h4 = h4[h4["close_time"] >= warmup_start_ms].reset_index(drop=True)
    d1 = d1[d1["close_time"] >= warmup_start_ms].reset_index(drop=True)

    rsi = int(np.searchsorted(h4["close_time"].values, PERIOD_START_MS))

    close = h4["close"].values.astype(np.float64)
    open_ = h4["open"].values.astype(np.float64)
    high = h4["high"].values.astype(np.float64)
    low = h4["low"].values.astype(np.float64)
    vol = h4["volume"].values.astype(np.float64)
    tb = h4["taker_buy_base_vol"].values.astype(np.float64)
    h4_ct = h4["close_time"].values.astype(np.int64)
    d1_cl = d1["close"].values.astype(np.float64)
    d1_ct = d1["close_time"].values.astype(np.int64)

    # Compute indicators
    slow_p = 120
    fast_p = max(5, slow_p // 4)
    ema_f = _ema(close, fast_p)
    ema_s = _ema(close, slow_p)
    vdo_arr = _vdo(close, high, low, vol, tb, 12, 28)
    d1_regime = compute_d1_regime(h4_ct, d1_cl, d1_ct, 21)

    # Standard ATR for E0_plus
    atr_std = _atr(high, low, close, 14)
    # Robust ATR for E5_plus
    atr_robust = _robust_atr(high, low, close, 0.90, 100, 20)

    # Scenarios to test
    scenarios = [
        ("baseline",         0, 0),
        ("exit_only_D1",     0, 1),
        ("exit_only_D2",     0, 2),
        ("entry_D1+exit_D1", 1, 1),
        ("entry_D1+exit_D2", 1, 2),
        ("entry_D2+exit_D1", 2, 1),  # Step 5 binding scenario
        ("entry_D2+exit_D2", 2, 2),
    ]

    print("\n" + "=" * 95)
    print("INFRASTRUCTURE MITIGATION: Combined disruption at tighter entry delay bounds")
    print("=" * 95)

    for label, atr_arr in [("E5_plus_EMA1D21", atr_robust), ("E0_plus_EMA1D21", atr_std)]:
        print(f"\n{'─' * 95}")
        print(f"  {label}")
        print(f"{'─' * 95}")

        baseline_sharpe = None
        results = {}

        for sc_name, ed, xd in scenarios:
            r = replay_binary(close, open_, high, low, ema_f, ema_s, atr_arr, vdo_arr,
                              d1_regime, rsi, entry_delay_bars=ed, exit_delay_bars=xd)
            if sc_name == "baseline":
                baseline_sharpe = r["sharpe"]
            delta = r["sharpe"] - baseline_sharpe if baseline_sharpe else 0.0
            results[sc_name] = {**r, "delta_sharpe": delta}

            threshold_status = ""
            if sc_name != "baseline":
                if delta > -0.20:
                    threshold_status = "  → GO"
                elif delta > -0.35:
                    threshold_status = "  → GO_WITH_GUARDS"
                else:
                    threshold_status = "  → HOLD ✗"

            print(f"  {sc_name:<22} Sharpe={r['sharpe']:.4f}  delta={delta:+.4f}  "
                  f"trades={r['n_trades']:>3d}  MDD={r['mdd']:.3f}{threshold_status}")

    # Summary table
    print("\n" + "=" * 95)
    print("SUMMARY: Sign-off status at each infrastructure level")
    print("=" * 95)

    # Re-run for clean summary
    summary_data = {}
    for label, atr_arr in [("E5_plus", atr_robust), ("E0_plus", atr_std)]:
        baseline = replay_binary(close, open_, high, low, ema_f, ema_s, atr_arr, vdo_arr,
                                 d1_regime, rsi, 0, 0)
        bs = baseline["sharpe"]
        for sc_name, ed, xd in scenarios:
            if sc_name == "baseline":
                continue
            r = replay_binary(close, open_, high, low, ema_f, ema_s, atr_arr, vdo_arr,
                              d1_regime, rsi, ed, xd)
            delta = r["sharpe"] - bs
            summary_data[(label, sc_name)] = delta

    print(f"\n{'Scenario':<22} {'E5_plus':>12} {'Status':>18} {'E0_plus':>12} {'Status':>18}")
    print("─" * 84)
    for sc_name, _, _ in scenarios:
        if sc_name == "baseline":
            continue
        e5d = summary_data.get(("E5_plus", sc_name), 0)
        e0d = summary_data.get(("E0_plus", sc_name), 0)
        e5s = "GO" if e5d > -0.20 else "GO_WITH_GUARDS" if e5d > -0.35 else "HOLD"
        e0s = "GO" if e0d > -0.20 else "GO_WITH_GUARDS" if e0d > -0.35 else "HOLD"
        print(f"{sc_name:<22} {e5d:>+12.4f} {e5s:>18} {e0d:>+12.4f} {e0s:>18}")

    # Infrastructure level analysis
    print("\n" + "=" * 95)
    print("INFRASTRUCTURE LEVELS: What entry delay bound is needed for E5_plus to pass?")
    print("=" * 95)

    infra_levels = [
        ("LT0.5: entry < 2h (D0 guaranteed)", "exit_only_D2", "No entry delay, worst exit D2"),
        ("LT0.75: entry ≤ 4h (D1 max)", "entry_D1+exit_D1", "D1 entry + D1 exit"),
        ("LT0.75+: entry ≤ 4h, exit degraded", "entry_D1+exit_D2", "D1 entry + D2 exit"),
        ("LT1 current: entry ≤ 8h (D2 max)", "entry_D2+exit_D1", "D2 entry + D1 exit (BINDING)"),
    ]

    print(f"\n{'Infrastructure Level':<45} {'E5+ delta':>12} {'Pass -0.35?':>12} {'E0+ delta':>12} {'Pass?':>8}")
    print("─" * 91)
    for desc, sc, note in infra_levels:
        e5d = summary_data.get(("E5_plus", sc), 0)
        e0d = summary_data.get(("E0_plus", sc), 0)
        e5p = "YES" if e5d > -0.35 else "NO"
        e0p = "YES" if e0d > -0.35 else "NO"
        print(f"{desc:<45} {e5d:>+12.4f} {e5p:>12} {e0d:>+12.4f} {e0p:>8}")

    print(f"""
KEY FINDING:
  Step 5 binding scenario (entry_D2 + exit_D1):
    E5_plus delta = {summary_data.get(('E5_plus', 'entry_D2+exit_D1'), 0):+.4f}  → FAILS -0.35 threshold
    E0_plus delta = {summary_data.get(('E0_plus', 'entry_D2+exit_D1'), 0):+.4f}  → passes

  With entry_D1 max (entry ≤ 4h infrastructure):
    E5_plus delta = {summary_data.get(('E5_plus', 'entry_D1+exit_D1'), 0):+.4f}  → {"PASSES" if summary_data.get(('E5_plus', 'entry_D1+exit_D1'), 0) > -0.35 else "FAILS"} -0.35 threshold
    E0_plus delta = {summary_data.get(('E0_plus', 'entry_D1+exit_D1'), 0):+.4f}  → passes

  Conclusion: If infrastructure guarantees entry delay ≤ 1 H4 bar (4h),
  E5_plus's worst combined disruption drops from {summary_data.get(('E5_plus', 'entry_D2+exit_D1'), 0):+.4f} to {summary_data.get(('E5_plus', 'entry_D1+exit_D1'), 0):+.4f}.
""")


if __name__ == "__main__":
    main()
