"""
VDO Standalone Research
========================
Question: Does Volume Delta Oscillator contain genuine alpha
beyond price-based trend indicators?

Tests:
1. VDO as standalone entry signal (1-2 params)
2. VDO as confirmation filter on EMA trend
3. Statistical comparison: EMA alone vs EMA+VDO
4. Walk-forward OOS validation
"""

import math
import numpy as np
import pandas as pd
from pathlib import Path


# ── Indicators ────────────────────────────────────────────────────────

def ema(series, period):
    alpha = 2.0 / (period + 1)
    out = np.empty_like(series, dtype=np.float64)
    out[0] = series[0]
    for i in range(1, len(series)):
        out[i] = alpha * series[i] + (1 - alpha) * out[i - 1]
    return out

def atr_fn(high, low, close, period=14):
    tr = np.maximum(high - low,
                    np.maximum(np.abs(high - np.roll(close, 1)),
                               np.abs(low - np.roll(close, 1))))
    tr[0] = high[0] - low[0]
    out = np.empty_like(tr, dtype=np.float64)
    out[:period] = np.nan
    out[period - 1] = np.mean(tr[:period])
    for i in range(period, len(tr)):
        out[i] = (out[i - 1] * (period - 1) + tr[i]) / period
    return out

def compute_vdo(close, high, low, volume, taker_buy_vol, fast=12, slow=28):
    """
    Volume Delta Oscillator.
    VDR = (taker_buy - taker_sell) / total_volume
    VDO = EMA(VDR, fast) - EMA(VDR, slow)

    Requires real taker_buy data.  Raises RuntimeError if taker data is
    missing or all-zero — VDO must always represent taker-imbalance,
    never an OHLC price-location proxy.
    """
    n = len(close)

    # Volume delta ratio — requires real taker data
    has_taker = taker_buy_vol is not None and np.any(taker_buy_vol > 0)
    if not has_taker:
        raise RuntimeError(
            "VDO requires taker_buy_base_vol data. Cannot compute VDO "
            "without real taker flow data — OHLC fallback has been removed "
            "to prevent semantic confusion (price-location != order-flow)."
        )

    taker_sell = volume - taker_buy_vol
    vdr = np.zeros(n)
    mask = volume > 0
    vdr[mask] = (taker_buy_vol[mask] - taker_sell[mask]) / volume[mask]

    # VDO = fast EMA - slow EMA of VDR
    ema_fast = ema(vdr, fast)
    ema_slow = ema(vdr, slow)
    vdo = ema_fast - ema_slow

    return vdo, vdr


# ── Backtest ──────────────────────────────────────────────────────────

def backtest_signal(close, signal, cost_rt_pct=0.31, initial_cash=10000.0):
    n = len(close)
    sig = np.zeros(n)
    sig[1:] = signal[:-1]

    changes = np.diff(sig, prepend=0)
    entries = np.where(changes > 0)[0]
    exits = np.where(changes < 0)[0]

    returns = np.zeros(n)
    returns[1:] = close[1:] / close[:-1] - 1.0

    cost_per_side = cost_rt_pct / 100.0 / 2.0
    position_returns = returns * sig
    for idx in entries:
        if idx < n:
            position_returns[idx] -= cost_per_side
    for idx in exits:
        if idx < n:
            position_returns[idx] -= cost_per_side

    equity = initial_cash * np.cumprod(1.0 + position_returns)

    years = (n - 1) / (6 * 365.25)
    final_nav = equity[-1]
    if years > 0.01 and final_nav > 0:
        cagr = (final_nav / initial_cash) ** (1.0 / years) - 1.0
    else:
        cagr = 0.0

    peak = np.maximum.accumulate(equity)
    dd = 1.0 - equity / peak
    mdd = float(dd.max())
    calmar = (cagr / mdd) if mdd > 1e-6 else 0.0

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

    rets = position_returns
    if np.std(rets) > 1e-12:
        sharpe = (np.mean(rets) / np.std(rets)) * math.sqrt(6.0 * 365.25)
    else:
        sharpe = 0

    return {
        "cagr": cagr * 100,
        "mdd": mdd * 100,
        "calmar": calmar,
        "sharpe": sharpe,
        "trades": n_trades,
        "win_rate": win_rate,
        "equity": equity,
    }


# ── Data loading ──────────────────────────────────────────────────────

def load_data():
    csv = Path("/var/www/trading-bots/btc-spot-dev/data/bars_btcusdt_2016_now_h1_4h_1d.csv")
    df = pd.read_csv(csv)
    h4 = df[df["interval"] == "4h"].sort_values("open_time").reset_index(drop=True)
    h4["date"] = pd.to_datetime(h4["open_time"], unit="ms", utc=True)

    # Check if taker_buy_base_vol exists
    has_taker = "taker_buy_base_vol" in h4.columns and h4["taker_buy_base_vol"].sum() > 0
    print(f"Taker buy volume available: {has_taker}")
    if has_taker:
        print(f"  Non-zero taker rows: {(h4['taker_buy_base_vol'] > 0).sum()} / {len(h4)}")

    return h4, has_taker


def main():
    print("=" * 80)
    print("VDO STANDALONE RESEARCH")
    print("=" * 80)

    h4, has_taker = load_data()
    mask = h4["date"] >= "2019-01-01"
    data = h4[mask].reset_index(drop=True)

    close = data["close"].values.astype(np.float64)
    high = data["high"].values.astype(np.float64)
    low = data["low"].values.astype(np.float64)
    volume = data["volume"].values.astype(np.float64)
    taker_buy = data["taker_buy_base_vol"].values.astype(np.float64) if has_taker else None
    n = len(close)
    warmup = 200
    atr14 = atr_fn(high, low, close, 14)

    print(f"Period: {data['date'].iloc[0]} → {data['date'].iloc[-1]}")
    print(f"H4 bars: {n}")

    # ══════════════════════════════════════════════════════════════════
    # TEST 1: VDO Statistical Properties
    # ══════════════════════════════════════════════════════════════════
    print("\n" + "=" * 80)
    print("TEST 1: VDO STATISTICAL PROPERTIES")
    print("=" * 80)

    vdo, vdr = compute_vdo(close, high, low, volume, taker_buy, fast=12, slow=28)

    print(f"\n  VDR (raw volume delta ratio):")
    print(f"    Mean: {np.mean(vdr[warmup:]):+.6f}")
    print(f"    Std:  {np.std(vdr[warmup:]):.6f}")
    print(f"    Min:  {np.min(vdr[warmup:]):.4f}")
    print(f"    Max:  {np.max(vdr[warmup:]):.4f}")

    print(f"\n  VDO (oscillator):")
    print(f"    Mean: {np.mean(vdo[warmup:]):+.6f}")
    print(f"    Std:  {np.std(vdo[warmup:]):.6f}")
    print(f"    Min:  {np.min(vdo[warmup:]):.6f}")
    print(f"    Max:  {np.max(vdo[warmup:]):.6f}")

    # Predictive power: does VDO predict future returns?
    print(f"\n  VDO Predictive Power (correlation with future returns):")
    fut_rets = {}
    for horizon in [1, 3, 6, 12, 24, 48, 96]:
        if horizon < n - warmup:
            fr = np.zeros(n)
            fr[:-horizon] = close[horizon:] / close[:-horizon] - 1.0
            corr = np.corrcoef(vdo[warmup:-horizon], fr[warmup:-horizon])[0, 1]
            bars_desc = f"{horizon*4}h" if horizon <= 6 else f"{horizon*4/24:.0f}d"
            sig_thresh = 2.0 / math.sqrt(n - warmup - horizon)
            sig = "***" if abs(corr) > sig_thresh else ""
            fut_rets[horizon] = corr
            print(f"    VDO vs return(+{horizon:3d} bars / {bars_desc:>4s}): {corr:+.4f} {sig}")

    # VDO autocorrelation (persistence)
    print(f"\n  VDO Autocorrelation (persistence):")
    for lag in [1, 3, 6, 12, 24]:
        ac = np.corrcoef(vdo[warmup:-lag], vdo[warmup+lag:])[0, 1]
        print(f"    Lag {lag:3d}: {ac:+.4f}")

    # ══════════════════════════════════════════════════════════════════
    # TEST 2: VDO as Standalone Entry Signal
    # ══════════════════════════════════════════════════════════════════
    print("\n" + "=" * 80)
    print("TEST 2: VDO AS STANDALONE SIGNAL")
    print("=" * 80)

    # Test different VDO thresholds as entry signal
    for fast_p, slow_p in [(12, 28), (8, 20), (16, 40), (20, 50), (6, 16)]:
        vdo_test, _ = compute_vdo(close, high, low, volume, taker_buy, fast_p, slow_p)

        print(f"\n  VDO({fast_p}/{slow_p}):")
        for threshold in [0.0, 0.002, 0.004, 0.006, 0.008]:
            sig = np.zeros(n)
            sig[warmup:] = (vdo_test[warmup:] > threshold).astype(float)
            r = backtest_signal(close, sig)
            print(f"    thresh={threshold:.3f}: CAGR={r['cagr']:6.1f}%  MDD={r['mdd']:5.1f}%  "
                  f"Calmar={r['calmar']:5.2f}  Sharpe={r['sharpe']:5.2f}  "
                  f"Trades={r['trades']:4d}  WR={r['win_rate']:4.1f}%")

    # ══════════════════════════════════════════════════════════════════
    # TEST 3: VDO as Confirmation Filter on EMA Trend
    # ══════════════════════════════════════════════════════════════════
    print("\n" + "=" * 80)
    print("TEST 3: EMA TREND + VDO CONFIRMATION")
    print("=" * 80)
    print("Hypothesis: VDO confirms genuine trend starts, filters false breakouts")

    ema30 = ema(close, 30)
    ema120 = ema(close, 120)
    vdo_default, _ = compute_vdo(close, high, low, volume, taker_buy, 12, 28)

    # Baseline: EMA(30/120) alone
    sig_ema = np.zeros(n)
    in_pos = False
    peak_price = 0.0
    for i in range(warmup, n):
        if np.isnan(atr14[i]):
            continue
        if not in_pos:
            if ema30[i] > ema120[i]:
                in_pos = True
                peak_price = close[i]
                sig_ema[i] = 1.0
        else:
            peak_price = max(peak_price, close[i])
            trail_stop = peak_price - 3.0 * atr14[i]
            if close[i] < trail_stop or ema30[i] < ema120[i]:
                in_pos = False
            else:
                sig_ema[i] = 1.0

    r_base = backtest_signal(close, sig_ema)
    print(f"\n  Baseline EMA(30/120)+Trail(3.0):")
    print(f"    CAGR={r_base['cagr']:6.1f}%  MDD={r_base['mdd']:5.1f}%  "
          f"Calmar={r_base['calmar']:5.2f}  Sharpe={r_base['sharpe']:5.2f}  "
          f"Trades={r_base['trades']}  WR={r_base['win_rate']:.1f}%")

    # Test: EMA + VDO confirmation (entry only when VDO > threshold)
    print(f"\n  EMA(30/120)+Trail(3.0) + VDO confirmation for entry:")
    for vdo_thresh in [0.0, 0.001, 0.002, 0.003, 0.004, 0.005, 0.006, 0.008]:
        sig_combo = np.zeros(n)
        in_pos = False
        peak_price = 0.0
        for i in range(warmup, n):
            if np.isnan(atr14[i]):
                continue
            if not in_pos:
                if ema30[i] > ema120[i] and vdo_default[i] > vdo_thresh:
                    in_pos = True
                    peak_price = close[i]
                    sig_combo[i] = 1.0
            else:
                peak_price = max(peak_price, close[i])
                trail_stop = peak_price - 3.0 * atr14[i]
                if close[i] < trail_stop or ema30[i] < ema120[i]:
                    in_pos = False
                else:
                    sig_combo[i] = 1.0

        r = backtest_signal(close, sig_combo)
        delta_calmar = r["calmar"] - r_base["calmar"]
        marker = " <<<" if delta_calmar > 0.05 else ""
        print(f"    VDO>{vdo_thresh:.3f}: CAGR={r['cagr']:6.1f}%  MDD={r['mdd']:5.1f}%  "
              f"Calmar={r['calmar']:5.2f} (Δ={delta_calmar:+.2f})  "
              f"Trades={r['trades']:4d}  WR={r['win_rate']:4.1f}%{marker}")

    # Test: EMA entry + VDO for exit enhancement (exit when VDO goes negative)
    print(f"\n  EMA(30/120) + VDO exit enhancement (exit also if VDO < -thresh):")
    for vdo_exit_thresh in [0.0, -0.001, -0.002, -0.003, -0.004, -0.005]:
        sig_combo2 = np.zeros(n)
        in_pos = False
        peak_price = 0.0
        for i in range(warmup, n):
            if np.isnan(atr14[i]):
                continue
            if not in_pos:
                if ema30[i] > ema120[i]:
                    in_pos = True
                    peak_price = close[i]
                    sig_combo2[i] = 1.0
            else:
                peak_price = max(peak_price, close[i])
                trail_stop = peak_price - 3.0 * atr14[i]
                exit_cond = (close[i] < trail_stop or
                            ema30[i] < ema120[i] or
                            vdo_default[i] < vdo_exit_thresh)
                if exit_cond:
                    in_pos = False
                else:
                    sig_combo2[i] = 1.0

        r = backtest_signal(close, sig_combo2)
        delta_calmar = r["calmar"] - r_base["calmar"]
        marker = " <<<" if delta_calmar > 0.05 else ""
        print(f"    VDO<{vdo_exit_thresh:+.3f}: CAGR={r['cagr']:6.1f}%  MDD={r['mdd']:5.1f}%  "
              f"Calmar={r['calmar']:5.2f} (Δ={delta_calmar:+.2f})  "
              f"Trades={r['trades']:4d}  WR={r['win_rate']:4.1f}%{marker}")

    # ══════════════════════════════════════════════════════════════════
    # TEST 4: VDO for Position SIZING (not binary entry)
    # ══════════════════════════════════════════════════════════════════
    print("\n" + "=" * 80)
    print("TEST 4: VDO FOR POSITION SIZING")
    print("=" * 80)
    print("Hypothesis: scale position size by VDO strength (stronger VDO = larger position)")

    # Use VDO to modulate conviction
    vdo_std = np.std(vdo_default[warmup:])
    print(f"  VDO std: {vdo_std:.6f}")

    for scale_method in ["linear", "capped"]:
        sig_sized = np.zeros(n)
        in_pos = False
        peak_price = 0.0

        for i in range(warmup, n):
            if np.isnan(atr14[i]):
                continue
            if not in_pos:
                if ema30[i] > ema120[i]:
                    in_pos = True
                    peak_price = close[i]
                    sig_sized[i] = 1.0
            else:
                peak_price = max(peak_price, close[i])
                trail_stop = peak_price - 3.0 * atr14[i]
                if close[i] < trail_stop or ema30[i] < ema120[i]:
                    in_pos = False
                else:
                    sig_sized[i] = 1.0

        # Now modulate: this is a crude approximation of sizing
        # Higher VDO → stay in, Lower VDO → reduce exposure
        # We simulate by exiting early when VDO is negative enough
        for vdo_exit in [-0.002, -0.003, -0.004]:
            sig_vdo_sized = sig_sized.copy()
            in_pos2 = False
            for i in range(warmup, n):
                if sig_sized[i] > 0 and not in_pos2:
                    in_pos2 = True
                elif sig_sized[i] == 0:
                    in_pos2 = False
                elif in_pos2 and vdo_default[i] < vdo_exit:
                    # Early exit on weak VDO
                    sig_vdo_sized[i] = 0.0

            r = backtest_signal(close, sig_vdo_sized)
            delta = r["calmar"] - r_base["calmar"]
            print(f"  {scale_method} VDO exit < {vdo_exit}: CAGR={r['cagr']:6.1f}%  "
                  f"MDD={r['mdd']:5.1f}%  Calmar={r['calmar']:5.2f} (Δ={delta:+.2f})  "
                  f"Trades={r['trades']}")

    # ══════════════════════════════════════════════════════════════════
    # TEST 5: WALK-FORWARD OOS - Does VDO help out-of-sample?
    # ══════════════════════════════════════════════════════════════════
    print("\n" + "=" * 80)
    print("TEST 5: WALK-FORWARD OOS COMPARISON")
    print("=" * 80)
    print("EMA alone vs EMA+VDO (best threshold from Test 3)")

    dates = data["date"].values
    bars_per_month = int(6 * 30.44)
    train_bars = 24 * bars_per_month
    test_bars = 6 * bars_per_month
    slide_bars = 6 * bars_per_month

    windows = []
    start = 0
    while start + train_bars + test_bars <= n:
        windows.append((start + train_bars, min(start + train_bars + test_bars, n)))
        start += slide_bars

    # Find the best VDO threshold from in-sample (Test 3)
    # We'll test a few thresholds in OOS to avoid selection bias
    configs = {
        "EMA only": {"vdo_entry": None, "vdo_exit": None},
        "EMA+VDO>0.002": {"vdo_entry": 0.002, "vdo_exit": None},
        "EMA+VDO>0.004": {"vdo_entry": 0.004, "vdo_exit": None},
        "EMA+VDO_exit<-0.002": {"vdo_entry": None, "vdo_exit": -0.002},
        "EMA+VDO>0.002+exit<-0.002": {"vdo_entry": 0.002, "vdo_exit": -0.002},
    }

    for cfg_name, cfg in configs.items():
        print(f"\n  --- {cfg_name} ---")
        oos_calmars = []

        for wi, (ts, te) in enumerate(windows):
            warmup_start = max(0, ts - 300)
            fc = close[warmup_start:te].copy()
            fh = high[warmup_start:te].copy()
            fl = low[warmup_start:te].copy()
            fv = volume[warmup_start:te].copy()
            ft = taker_buy[warmup_start:te].copy() if taker_buy is not None else None
            fa = atr_fn(fh, fl, fc, 14)
            fvdo, _ = compute_vdo(fc, fh, fl, fv, ft, 12, 28)
            fema30 = ema(fc, 30)
            fema120 = ema(fc, 120)
            offset = ts - warmup_start

            nt = te - ts
            sig_test = np.zeros(nt)
            in_pos = False
            peak_price = 0.0

            for i in range(nt):
                fi = offset + i
                if fi >= len(fa) or np.isnan(fa[fi]):
                    continue
                if not in_pos:
                    entry_ok = fema30[fi] > fema120[fi]
                    if cfg["vdo_entry"] is not None:
                        entry_ok = entry_ok and fvdo[fi] > cfg["vdo_entry"]
                    if entry_ok:
                        in_pos = True
                        peak_price = fc[fi]
                        sig_test[i] = 1.0
                else:
                    peak_price = max(peak_price, fc[fi])
                    trail_stop = peak_price - 3.0 * fa[fi]
                    exit_cond = fc[fi] < trail_stop or fema30[fi] < fema120[fi]
                    if cfg["vdo_exit"] is not None:
                        exit_cond = exit_cond or fvdo[fi] < cfg["vdo_exit"]
                    if exit_cond:
                        in_pos = False
                    else:
                        sig_test[i] = 1.0

            test_close = close[ts:te]
            r = backtest_signal(test_close, sig_test)
            oos_calmars.append(r["calmar"])

            date_s = pd.Timestamp(dates[ts]).strftime("%Y-%m-%d")
            date_e = pd.Timestamp(dates[min(te-1, n-1)]).strftime("%Y-%m-%d")
            print(f"    W{wi+1:2d} [{date_s}→{date_e}]: "
                  f"CAGR={r['cagr']:+6.1f}%  MDD={r['mdd']:5.1f}%  "
                  f"Calmar={r['calmar']:+5.2f}  Trades={r['trades']}")

        pos = sum(1 for c in oos_calmars if c > 0)
        print(f"    SUMMARY: {pos}/{len(windows)} positive, "
              f"Mean Calmar={np.mean(oos_calmars):+.2f}")

    # ══════════════════════════════════════════════════════════════════
    # TEST 6: Holdout comparison
    # ══════════════════════════════════════════════════════════════════
    print("\n" + "=" * 80)
    print("TEST 6: HOLDOUT (2024-09-17 to end)")
    print("=" * 80)

    holdout_mask = data["date"] >= "2024-09-17"
    ho_start = holdout_mask.idxmax()
    ho_warmup = max(0, ho_start - 300)

    fc = close[ho_warmup:].copy()
    fh = high[ho_warmup:].copy()
    fl = low[ho_warmup:].copy()
    fv = volume[ho_warmup:].copy()
    ft = taker_buy[ho_warmup:].copy() if taker_buy is not None else None
    fa = atr_fn(fh, fl, fc, 14)
    fvdo, _ = compute_vdo(fc, fh, fl, fv, ft, 12, 28)
    fema30 = ema(fc, 30)
    fema120 = ema(fc, 120)
    offset = ho_start - ho_warmup
    ho_close = close[ho_start:]
    nt = len(ho_close)

    for cfg_name, cfg in configs.items():
        sig_ho = np.zeros(nt)
        in_pos = False
        peak_price = 0.0
        for i in range(nt):
            fi = offset + i
            if fi >= len(fa) or np.isnan(fa[fi]):
                continue
            if not in_pos:
                entry_ok = fema30[fi] > fema120[fi]
                if cfg["vdo_entry"] is not None:
                    entry_ok = entry_ok and fvdo[fi] > cfg["vdo_entry"]
                if entry_ok:
                    in_pos = True
                    peak_price = fc[fi]
                    sig_ho[i] = 1.0
            else:
                peak_price = max(peak_price, fc[fi])
                trail_stop = peak_price - 3.0 * fa[fi]
                exit_cond = fc[fi] < trail_stop or fema30[fi] < fema120[fi]
                if cfg["vdo_exit"] is not None:
                    exit_cond = exit_cond or fvdo[fi] < cfg["vdo_exit"]
                if exit_cond:
                    in_pos = False
                else:
                    sig_ho[i] = 1.0

        for cost_name, cost_pct in [("base", 0.31), ("harsh", 0.50)]:
            r = backtest_signal(ho_close, sig_ho, cost_rt_pct=cost_pct)
            print(f"  {cfg_name:35s} [{cost_name}]: CAGR={r['cagr']:+6.1f}%  "
                  f"MDD={r['mdd']:5.1f}%  Calmar={r['calmar']:+5.2f}  Trades={r['trades']}")

    # ══════════════════════════════════════════════════════════════════
    # VERDICT
    # ══════════════════════════════════════════════════════════════════
    print("\n" + "=" * 80)
    print("VERDICT: DOES VDO ADD GENUINE ALPHA?")
    print("=" * 80)


if __name__ == "__main__":
    main()
