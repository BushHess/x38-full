#!/usr/bin/env python3
"""Multi-Coin Diversification Study (v2 — complete rewrite).

Tests whether VTREND E0 (unchanged, zero parameter modification) generates
alpha on non-BTC coins, and whether a multi-coin portfolio improves
risk-adjusted returns via cross-asset diversification.

Design decisions:
  1. Single prepare_data() aligns all coins to common time range
  2. Indicators computed on FULL per-coin history for maximum warmup,
     then extracted for common range
  3. Warmup index (wi) used consistently in ALL sims (real data AND bootstrap)
  4. Bootstrap ratios from common aligned data (synchronized = same time)
  5. BTC-only benchmark on exact same analysis period as portfolio
  6. sim_fast and sim_nav_series have consistent warmup behavior

Fixes vs v1:
  F1. Bootstrap now uses wi (was 0)
  F2. sim_nav_series consistent with sim_fast (no warmup gate)
  F3. Indicators pre-warmed from full per-coin history
  F4. Single prepare_data() function, all phases share its output
  F5. Sanity check: BTC common range != BTC full history
"""

from __future__ import annotations

import glob
import json
import math
import sys
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.stats import binomtest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from strategies.vtrend.strategy import _ema, _atr, _vdo
from research.lib.vcbb import make_ratios, precompute_vcbb, gen_path_vcbb

# ══════════════════════════════════════════════════════════════════
# Constants (identical to all studies)
# ══════════════════════════════════════════════════════════════════

CACHE_DIR = "/var/www/trading-bots/data-pipeline/.cache_binance_vision"

COINS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
    "LTCUSDT", "ADAUSDT", "DOGEUSDT", "TRXUSDT", "AVAXUSDT",
    "LINKUSDT", "BCHUSDT", "HBARUSDT", "XLMUSDT",
]

LARGE_CAP = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT"]

CASH     = 10_000.0
CPS      = 0.0025       # 25 bps per side (50 bps round-trip)
TRAIL    = 3.0
ATR_P    = 14
VDO_F    = 12
VDO_S    = 28
VDO_THR  = 0.0
ANN      = math.sqrt(6.0 * 365.25)   # sqrt(6 bars/day * 365.25 days)

N_BOOT   = 500
BLKSZ    = 60
SEED     = 42

WARMUP_DAYS = 365

SLOW_PERIODS = [30, 48, 60, 72, 84, 96, 108, 120, 144, 168, 200, 240, 300, 360, 500, 720]


# ══════════════════════════════════════════════════════════════════
# Data Loading
# ══════════════════════════════════════════════════════════════════

def load_coin_raw(symbol: str) -> dict:
    """Load raw H4 data from Binance Vision ZIP cache."""
    monthly = sorted(glob.glob(
        f"{CACHE_DIR}/spot/monthly/klines/{symbol}/4h/*.zip"))
    daily = sorted(glob.glob(
        f"{CACHE_DIR}/spot/daily/klines/{symbol}/4h/*.zip"))

    rows = []
    for zp in monthly + daily:
        try:
            with zipfile.ZipFile(zp) as zf:
                fname = zf.namelist()[0]
                data = zf.read(fname).decode()
                for line in data.strip().split('\n'):
                    cols = line.split(',')
                    if len(cols) < 12:
                        continue
                    # Normalize timestamp: older files use ms (13 digits),
                    # newer files use us (16 digits). Convert all to ms.
                    ts = int(cols[0])
                    if ts > 1e15:
                        ts = ts // 1000  # us -> ms
                    rows.append((
                        ts,                 # open_time (ms)
                        float(cols[2]),     # high
                        float(cols[3]),     # low
                        float(cols[4]),     # close
                        float(cols[5]),     # volume
                        float(cols[9]),     # taker_buy_base_vol
                    ))
        except Exception as e:
            print(f"  Warning: failed to read {zp}: {e}")

    # Sort by open_time, deduplicate
    rows.sort(key=lambda x: x[0])
    seen = set()
    unique = []
    for r in rows:
        if r[0] not in seen:
            seen.add(r[0])
            unique.append(r)

    n = len(unique)
    timestamps = np.array([r[0] for r in unique], dtype=np.int64)
    hi = np.array([r[1] for r in unique], dtype=np.float64)
    lo = np.array([r[2] for r in unique], dtype=np.float64)
    cl = np.array([r[3] for r in unique], dtype=np.float64)
    vo = np.array([r[4] for r in unique], dtype=np.float64)
    tb = np.array([r[5] for r in unique], dtype=np.float64)

    return {"cl": cl, "hi": hi, "lo": lo, "vo": vo, "tb": tb,
            "n": n, "timestamps": timestamps}


# ══════════════════════════════════════════════════════════════════
# Data Preparation (single source of truth for all phases)
# ══════════════════════════════════════════════════════════════════

def prepare_data():
    """Load all coins, compute indicators on full history, align to common range.

    Returns:
        aligned: dict[symbol] -> {cl, hi, lo, vo, tb, at, vd, ema: {sp: (ef, es)}}
            All arrays of length n_common. Indicators computed from full per-coin
            history then extracted for common range (maximum warmup).
        wi: int - warmup index within common range
        n_common: int - total bars in common range
        n_trans: int - n_common - 1 (transitions for bootstrap)
        boot_ratios: dict[symbol] -> {cr, hr, lr, vol, tb}
            Ratios from common range data (time-aligned for synchronized bootstrap).
        raw: dict[symbol] -> raw data (for sanity check)
        info: dict - diagnostic information
    """
    print("\n  Loading raw data...")
    raw = {}
    for s in COINS:
        d = load_coin_raw(s)
        raw[s] = d
        t0 = datetime.fromtimestamp(d["timestamps"][0] / 1000, tz=timezone.utc)
        t1 = datetime.fromtimestamp(d["timestamps"][-1] / 1000, tz=timezone.utc)
        print(f"    {s:>10s}: {d['n']:6d} bars ({t0:%Y-%m-%d} -> {t1:%Y-%m-%d})")

    # Common data range: latest start -> earliest end
    latest_start = max(d["timestamps"][0] for d in raw.values())
    earliest_end = min(d["timestamps"][-1] for d in raw.values())

    # Find common range indices per coin in their full data
    coin_ranges = {}
    for s in COINS:
        ts = raw[s]["timestamps"]
        i0 = int(np.searchsorted(ts, latest_start, side='left'))
        i1 = int(np.searchsorted(ts, earliest_end, side='right'))
        coin_ranges[s] = (i0, i1)

    n_common = min(i1 - i0 for i0, i1 in coin_ranges.values())

    print(f"\n  Computing indicators on full per-coin history...")
    aligned = {}
    for s in COINS:
        d = raw[s]
        i0 = coin_ranges[s][0]
        i1 = i0 + n_common

        # Compute indicators on FULL data (maximum warmup)
        at_full = _atr(d["hi"], d["lo"], d["cl"], ATR_P)
        vd_full = _vdo(d["cl"], d["hi"], d["lo"], d["vo"], d["tb"], VDO_F, VDO_S)

        # Precompute EMA for all timescales on full data
        ema_dict = {}
        for sp in SLOW_PERIODS:
            fp = max(5, sp // 4)
            ef_full = _ema(d["cl"], fp)
            es_full = _ema(d["cl"], sp)
            ema_dict[sp] = (ef_full[i0:i1].copy(), es_full[i0:i1].copy())

        aligned[s] = {
            "cl": d["cl"][i0:i1].copy(),
            "hi": d["hi"][i0:i1].copy(),
            "lo": d["lo"][i0:i1].copy(),
            "vo": d["vo"][i0:i1].copy(),
            "tb": d["tb"][i0:i1].copy(),
            "at": at_full[i0:i1].copy(),
            "vd": vd_full[i0:i1].copy(),
            "ema": ema_dict,
        }

        # Sanity: no NaN in ATR at analysis start
        warmup_bars = WARMUP_DAYS * 6
        if warmup_bars < n_common:
            at_val = aligned[s]["at"][warmup_bars]
            assert not np.isnan(at_val), f"{s}: ATR still NaN at analysis start (bar {warmup_bars})"

    # Warmup index
    wi = min(WARMUP_DAYS * 6, n_common - 100)
    n_analysis = n_common - wi

    # Bootstrap ratios from common aligned data
    print(f"  Computing bootstrap ratios...")
    boot_ratios = {}
    for s in COINS:
        a = aligned[s]
        cr, hr, lr, vr, tr = make_ratios(a["cl"], a["hi"], a["lo"], a["vo"], a["tb"])
        vcbb_st = precompute_vcbb(cr, blksz=BLKSZ, ctx=90)
        boot_ratios[s] = {"cr": cr, "hr": hr, "lr": lr, "vol": vr, "tb": tr, "vcbb": vcbb_st}

    n_trans = n_common - 1

    # Verify all arrays are time-aligned (same length)
    for s in COINS:
        assert len(aligned[s]["cl"]) == n_common, f"{s}: length mismatch"
        assert len(boot_ratios[s]["cr"]) == n_trans, f"{s}: ratio length mismatch"

    # Diagnostic info
    common_start = datetime.fromtimestamp(latest_start / 1000, tz=timezone.utc)
    common_end = datetime.fromtimestamp(earliest_end / 1000, tz=timezone.utc)
    analysis_start = datetime.fromtimestamp(
        latest_start / 1000 + WARMUP_DAYS * 86400, tz=timezone.utc)

    info = {
        "common_start": f"{common_start:%Y-%m-%d}",
        "common_end": f"{common_end:%Y-%m-%d}",
        "analysis_start": f"{analysis_start:%Y-%m-%d}",
        "n_common": n_common,
        "wi": wi,
        "n_analysis": n_analysis,
        "n_trans": n_trans,
    }

    print(f"\n  Common data range: {common_start:%Y-%m-%d} -> {common_end:%Y-%m-%d}")
    print(f"  Total bars: {n_common}")
    print(f"  Warmup: {wi} bars ({WARMUP_DAYS} days)")
    print(f"  Analysis start: ~{analysis_start:%Y-%m-%d}")
    print(f"  Analysis bars: {n_analysis}")

    return aligned, wi, n_common, n_trans, boot_ratios, raw, info


# ══════════════════════════════════════════════════════════════════
# Simulation (canonical E0, from timescale_robustness.py:116-228)
# ══════════════════════════════════════════════════════════════════

def sim_fast(cl, ef, es, at, vd, wi, vdo_thr):
    """VTREND binary sim (f=1.0). Returns metrics dict.

    Signals checked for all bars (including warmup).
    Metrics recorded only from bar wi onward.
    Identical to timescale_robustness.py:116-228 plus final_nav.
    """
    n = len(cl)
    cash = CASH
    bq = 0.0
    inp = False
    pk = 0.0
    pe = px = False
    nt = 0

    navs_start = 0.0
    navs_end = 0.0
    nav_peak = 0.0
    nav_min_ratio = 1.0
    rets_sum = 0.0
    rets_sq_sum = 0.0
    n_rets = 0
    prev_nav = 0.0
    started = False

    for i in range(n):
        p = cl[i]

        if i > 0:
            fp = cl[i - 1]
            if pe:
                pe = False
                bq = cash / (fp * (1.0 + CPS))
                cash = 0.0
                inp = True
                pk = p
            elif px:
                cash = bq * fp * (1.0 - CPS)
                bq = 0.0
                inp = False
                pk = 0.0
                nt += 1
                px = False

        nav = cash + bq * p

        if i >= wi:
            if not started:
                navs_start = nav
                prev_nav = nav
                nav_peak = nav
                started = True
            else:
                if prev_nav > 0:
                    r = nav / prev_nav - 1.0
                    rets_sum += r
                    rets_sq_sum += r * r
                    n_rets += 1
                prev_nav = nav
            nav_peak = max(nav_peak, nav)
            if nav_peak > 0:
                ratio = nav / nav_peak
                if ratio < nav_min_ratio:
                    nav_min_ratio = ratio
            navs_end = nav

        a_val = at[i]
        if math.isnan(a_val) or math.isnan(ef[i]) or math.isnan(es[i]):
            continue

        if not inp:
            if ef[i] > es[i] and vd[i] > vdo_thr:
                pe = True
        else:
            pk = max(pk, p)
            if p < pk - TRAIL * a_val:
                px = True
            elif ef[i] < es[i]:
                px = True

    # Force close
    if inp and bq > 0:
        cash = bq * cl[-1] * (1.0 - CPS)
        bq = 0.0
        nt += 1
        navs_end = cash

    if n_rets < 2 or navs_start <= 0:
        return {"cagr": -100.0, "mdd": 100.0, "sharpe": 0.0, "calmar": 0.0,
                "trades": 0, "final_nav": navs_end}

    tr = navs_end / navs_start - 1.0
    yrs = n_rets / (6.0 * 365.25)
    cagr = ((1 + tr) ** (1 / yrs) - 1) * 100 if yrs > 0 and tr > -1 else -100.0
    mdd = (1.0 - nav_min_ratio) * 100.0
    mu = rets_sum / n_rets
    var = rets_sq_sum / n_rets - mu * mu
    std = math.sqrt(max(var, 0.0))
    sharpe = (mu / std) * ANN if std > 1e-12 else 0.0
    calmar = cagr / mdd if mdd > 0.01 else 0.0

    return {"cagr": cagr, "mdd": mdd, "sharpe": sharpe, "calmar": calmar,
            "trades": nt, "final_nav": navs_end}


def sim_nav_series(cl, ef, es, at, vd, wi, start_cash):
    """Run E0 and return per-bar NAV array.

    Consistent with sim_fast: signals checked for all bars (including warmup).
    No warmup gate — trades CAN occur during warmup.
    """
    n = len(cl)
    cash = start_cash
    bq = 0.0
    inp = False
    pe = False
    px = False
    pk = 0.0

    navs = np.full(n, start_cash)

    for i in range(n):
        p = cl[i]

        if i > 0:
            fp = cl[i - 1]
            if pe:
                pe = False
                bq = cash / (fp * (1.0 + CPS))
                cash = 0.0
                inp = True
                pk = p
            elif px:
                px = False
                cash = bq * fp * (1.0 - CPS)
                bq = 0.0
                inp = False
                pk = 0.0

        nav = cash + bq * p
        navs[i] = nav

        a_val = at[i]
        if math.isnan(a_val) or math.isnan(ef[i]) or math.isnan(es[i]):
            continue

        # NO warmup gate here — consistent with sim_fast
        # Signals checked for all bars, but metrics only from wi onward

        if not inp:
            if ef[i] > es[i] and vd[i] > VDO_THR:
                pe = True
        else:
            pk = max(pk, p)
            if p < pk - TRAIL * a_val:
                px = True
            elif ef[i] < es[i]:
                px = True

    # Force close
    if inp and bq > 0:
        cash = bq * cl[-1] * (1.0 - CPS)
        navs[-1] = cash

    return navs


def metrics_from_navs(navs, wi):
    """Compute standard metrics from a NAV time series, starting from bar wi."""
    active = navs[wi:]
    n = len(active)
    if n < 10:
        return {"sharpe": 0.0, "cagr": -100.0, "mdd": 100.0, "calmar": 0.0,
                "final_nav": active[-1] if n > 0 else navs[0]}

    rets = active[1:] / active[:-1] - 1.0
    n_rets = len(rets)
    if n_rets < 2:
        return {"sharpe": 0.0, "cagr": -100.0, "mdd": 100.0, "calmar": 0.0,
                "final_nav": active[-1]}

    mu = np.mean(rets)
    std = np.std(rets, ddof=0)
    sharpe = (mu / std * ANN) if std > 1e-12 else 0.0

    tr = active[-1] / active[0] - 1.0
    yrs = n_rets / (6.0 * 365.25)
    cagr = ((1 + tr) ** (1.0 / yrs) - 1.0) * 100 if yrs > 0 and tr > -1 else -100.0

    peak = np.maximum.accumulate(active)
    dd = 1.0 - active / peak
    mdd = np.max(dd) * 100.0
    calmar = cagr / mdd if mdd > 0.01 else 0.0

    return {"sharpe": sharpe, "cagr": cagr, "mdd": mdd, "calmar": calmar,
            "final_nav": active[-1]}


# ══════════════════════════════════════════════════════════════════
# Sanity Check
# ══════════════════════════════════════════════════════════════════

def sanity_check_btc(aligned, wi, n_common, raw):
    """Verify BTC metrics differ between common range and full history."""
    print("\n" + "=" * 90)
    print("SANITY CHECK: BTC common range vs full history")
    print("=" * 90)

    sp = 120

    # BTC on common range (pre-warmed indicators)
    a = aligned["BTCUSDT"]
    ef, es = a["ema"][sp]
    m_common = sim_fast(a["cl"], ef, es, a["at"], a["vd"], wi, VDO_THR)

    # BTC on full history (compute from scratch)
    d = raw["BTCUSDT"]
    cl, hi, lo, vo, tb = d["cl"], d["hi"], d["lo"], d["vo"], d["tb"]
    at_f = _atr(hi, lo, cl, ATR_P)
    vd_f = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)
    fp = max(5, sp // 4)
    ef_f = _ema(cl, fp)
    es_f = _ema(cl, sp)
    wi_full = min(WARMUP_DAYS * 6, len(cl) - 100)
    m_full = sim_fast(cl, ef_f, es_f, at_f, vd_f, wi_full, VDO_THR)

    print(f"\n  Common range ({n_common - wi} analysis bars):")
    print(f"    Sharpe={m_common['sharpe']:.4f}  CAGR={m_common['cagr']:.2f}%  "
          f"MDD={m_common['mdd']:.2f}%  Trades={m_common['trades']}")
    print(f"\n  Full history ({len(cl) - wi_full} analysis bars):")
    print(f"    Sharpe={m_full['sharpe']:.4f}  CAGR={m_full['cagr']:.2f}%  "
          f"MDD={m_full['mdd']:.2f}%  Trades={m_full['trades']}")

    delta_sh = abs(m_common['sharpe'] - m_full['sharpe'])
    if delta_sh < 0.001:
        print(f"\n  WARNING: Sharpe difference only {delta_sh:.4f} -- alignment may not work!")
        return False
    else:
        print(f"\n  OK: Sharpe differs by {delta_sh:.3f} -- alignment confirmed")
        return True


# ══════════════════════════════════════════════════════════════════
# Phase 2: Per-Coin Real Data Analysis (on aligned common range)
# ══════════════════════════════════════════════════════════════════

def phase2_per_coin(aligned, wi):
    """Run E0 at 16 timescales on each coin's aligned data."""
    print("\n" + "=" * 90)
    print("PHASE 2: PER-COIN REAL DATA ANALYSIS (aligned common range)")
    print("=" * 90)

    results = {}

    for symbol in COINS:
        a = aligned[symbol]
        cl = a["cl"]
        at = a["at"]
        vd = a["vd"]

        coin_results = {}
        for sp in SLOW_PERIODS:
            ef, es = a["ema"][sp]
            m = sim_fast(cl, ef, es, at, vd, wi, VDO_THR)
            coin_results[sp] = {
                "sharpe": round(m["sharpe"], 4),
                "cagr": round(m["cagr"], 2),
                "mdd": round(m["mdd"], 2),
                "calmar": round(m["calmar"], 4),
                "trades": m["trades"],
                "final_nav": round(m["final_nav"], 2),
            }

        m120 = coin_results[120]
        best_sp = max(SLOW_PERIODS, key=lambda sp: coin_results[sp]["sharpe"])
        n_positive = sum(1 for sp in SLOW_PERIODS if coin_results[sp]["sharpe"] > 0)

        results[symbol] = {
            "by_timescale": coin_results,
            "n120": m120,
            "best_sp": best_sp,
            "best_sharpe": coin_results[best_sp]["sharpe"],
            "n_positive_timescales": n_positive,
        }

        print(f"\n  {symbol:>10s}  N=120: Sh={m120['sharpe']:+.3f}  CAGR={m120['cagr']:+.1f}%  "
              f"MDD={m120['mdd']:.1f}%  Trades={m120['trades']}  "
              f"Best@N={best_sp}(Sh={coin_results[best_sp]['sharpe']:.3f})  "
              f"Positive: {n_positive}/16")

    # Meta-test
    k_positive = sum(1 for s in COINS if results[s]["n120"]["sharpe"] > 0)
    n_coins = len(COINS)
    binom = binomtest(k_positive, n_coins, 0.5, alternative='greater')

    print(f"\n  {'_' * 80}")
    print(f"  Meta-test: {k_positive}/{n_coins} coins with positive Sharpe at N=120")
    print(f"  Binomial P(>={k_positive} | p=0.5) = {binom.pvalue:.6f}")
    if binom.pvalue < 0.05:
        print(f"  -> SIGNIFICANT: VTREND E0 generalizes beyond BTC")
    else:
        print(f"  -> NOT significant")

    results["_meta"] = {
        "k_positive": k_positive,
        "n_coins": n_coins,
        "binomial_p": binom.pvalue,
    }

    return results


# ══════════════════════════════════════════════════════════════════
# Phase 3: Cross-Asset Strategy Return Correlation
# ══════════════════════════════════════════════════════════════════

def phase3_correlation(aligned, wi):
    """Compute pairwise strategy-return correlation at N=120."""
    print("\n" + "=" * 90)
    print("PHASE 3: CROSS-ASSET STRATEGY RETURN CORRELATION (N=120)")
    print("=" * 90)

    sp = 120
    K = len(COINS)

    # Compute NAV series per coin
    nav_dict = {}
    for symbol in COINS:
        a = aligned[symbol]
        ef, es = a["ema"][sp]
        nav_dict[symbol] = sim_nav_series(
            a["cl"], ef, es, a["at"], a["vd"], wi, CASH)

    # Strategy returns (post-warmup)
    returns = {}
    for symbol in COINS:
        nav = nav_dict[symbol][wi:]
        returns[symbol] = nav[1:] / nav[:-1] - 1.0

    # Pairwise strategy correlation
    corr_matrix = np.ones((K, K), dtype=np.float64)
    for i in range(K):
        for j in range(i + 1, K):
            r = np.corrcoef(returns[COINS[i]], returns[COINS[j]])[0, 1]
            corr_matrix[i, j] = r
            corr_matrix[j, i] = r

    # Price correlation for comparison
    price_corr_matrix = np.ones((K, K), dtype=np.float64)
    for i in range(K):
        for j in range(i + 1, K):
            pi = aligned[COINS[i]]["cl"][wi:]
            pj = aligned[COINS[j]]["cl"][wi:]
            pri = pi[1:] / pi[:-1] - 1.0
            prj = pj[1:] / pj[:-1] - 1.0
            r = np.corrcoef(pri, prj)[0, 1]
            price_corr_matrix[i, j] = r
            price_corr_matrix[j, i] = r

    mask_upper = np.triu_indices(K, k=1)
    strat_rhos = corr_matrix[mask_upper]
    price_rhos = price_corr_matrix[mask_upper]

    mean_rho = float(np.mean(strat_rhos))
    median_rho = float(np.median(strat_rhos))
    min_rho = float(np.min(strat_rhos))
    max_rho = float(np.max(strat_rhos))
    mean_price_rho = float(np.mean(price_rhos))

    print(f"\n  Strategy-return correlation:")
    print(f"    Mean rho  = {mean_rho:.4f}")
    print(f"    Median    = {median_rho:.4f}")
    print(f"    Min       = {min_rho:.4f}")
    print(f"    Max       = {max_rho:.4f}")
    print(f"\n  Price-return correlation:")
    print(f"    Mean rho  = {mean_price_rho:.4f}")

    # Print matrix
    print(f"\n  Strategy rho matrix:")
    hdr = "          " + "  ".join(f"{s[:5]:>5s}" for s in COINS)
    print(f"  {hdr}")
    for i, s in enumerate(COINS):
        row = f"  {s[:5]:>5s}  " + "  ".join(
            f"{corr_matrix[i, j]:+.2f}" if i != j else " 1.00"
            for j in range(K))
        print(row)

    # PSD check
    eigvals = np.linalg.eigvalsh(corr_matrix)
    is_psd = bool(eigvals.min() >= -1e-10)
    print(f"\n  PSD check: min eigenvalue = {eigvals.min():.6f} -> {'OK' if is_psd else 'FAIL'}")

    return {
        "strategy_corr": corr_matrix.tolist(),
        "price_corr": price_corr_matrix.tolist(),
        "labels": COINS,
        "mean_strategy_rho": round(mean_rho, 6),
        "median_strategy_rho": round(median_rho, 6),
        "min_strategy_rho": round(min_rho, 6),
        "max_strategy_rho": round(max_rho, 6),
        "mean_price_rho": round(mean_price_rho, 6),
        "is_psd": is_psd,
    }


# ══════════════════════════════════════════════════════════════════
# Phase 4: Portfolio Simulation (Real Data, aligned)
# ══════════════════════════════════════════════════════════════════

def phase4_portfolio(aligned, wi, phase2):
    """Simulate equal-weight multi-coin portfolios on aligned real data."""
    print("\n" + "=" * 90)
    print("PHASE 4: PORTFOLIO SIMULATION (REAL DATA, aligned)")
    print("=" * 90)

    sp = 120
    n_common = len(aligned["BTCUSDT"]["cl"])

    pos_coins = [s for s in COINS if phase2[s]["n120"]["sharpe"] > 0]
    print(f"\n  Positive-Sharpe coins at N=120: {len(pos_coins)}")

    portfolios = {
        "all_14": COINS,
        "large_cap_5": LARGE_CAP,
        "positive_sharpe": pos_coins,
        "btc_only": ["BTCUSDT"],
    }

    results = {}

    for port_name, port_coins in portfolios.items():
        K = len(port_coins)
        per_coin_cash = CASH / K

        port_navs = np.zeros(n_common, dtype=np.float64)

        for symbol in port_coins:
            a = aligned[symbol]
            ef, es = a["ema"][sp]
            navs = sim_nav_series(
                a["cl"], ef, es, a["at"], a["vd"], wi, per_coin_cash)
            port_navs += navs

        m = metrics_from_navs(port_navs, wi)

        results[port_name] = {
            "coins": port_coins,
            "K": K,
            "sharpe": round(m["sharpe"], 4),
            "cagr": round(m["cagr"], 2),
            "mdd": round(m["mdd"], 2),
            "calmar": round(m["calmar"], 4),
            "final_nav": round(m["final_nav"], 2),
        }

        print(f"\n  {port_name} ({K} coins):")
        print(f"    Sharpe={m['sharpe']:.3f}  CAGR={m['cagr']:.1f}%  "
              f"MDD={m['mdd']:.1f}%  Calmar={m['calmar']:.3f}  "
              f"Final NAV={m['final_nav']:.0f}")

    # Comparison table
    print(f"\n  {'_' * 80}")
    print(f"  {'Portfolio':<20s} {'K':>3s} {'Sharpe':>8s} {'CAGR%':>8s} "
          f"{'MDD%':>8s} {'Calmar':>8s} {'FinalNAV':>10s}")
    print(f"  {'_' * 80}")
    for name, r in results.items():
        print(f"  {name:<20s} {r['K']:>3d} {r['sharpe']:>8.3f} {r['cagr']:>8.1f} "
              f"{r['mdd']:>8.1f} {r['calmar']:>8.3f} {r['final_nav']:>10.0f}")

    btc = results["btc_only"]
    print(f"\n  Diversification vs BTC-only:")
    for name, r in results.items():
        if name == "btc_only":
            continue
        sh_ratio = r["sharpe"] / btc["sharpe"] if btc["sharpe"] > 0.01 else 0
        mdd_ratio = r["mdd"] / btc["mdd"] if btc["mdd"] > 0.01 else 0
        print(f"    {name}: Sharpe x{sh_ratio:.3f}  MDD x{mdd_ratio:.3f}")

    return results


# ══════════════════════════════════════════════════════════════════
# Phase 5: Synchronized Bootstrap (preserves cross-asset correlation)
# ══════════════════════════════════════════════════════════════════

def phase5_bootstrap(aligned, wi, n_trans, boot_ratios):
    """Synchronized bootstrap with multiple portfolio variants.

    Uses same block indices for all coins -> preserves cross-asset correlation.
    Tests: equal-weight, quality-filtered, Sharpe-weighted.
    """
    print("\n" + "=" * 90)
    print(f"PHASE 5: SYNCHRONIZED BOOTSTRAP ({N_BOOT} paths)")
    print("  Same block indices for all coins -> preserves cross-asset rho")
    print("=" * 90)

    sp = 120
    fp = max(5, sp // 4)
    n_common = n_trans + 1

    print(f"\n  Transitions: {n_trans}")
    print(f"  Warmup index: {wi}")
    print(f"  Analysis bars per path: {n_common - wi}")

    # Seed management
    rng = np.random.default_rng(SEED)
    boot_seeds = rng.integers(0, 2**31, size=N_BOOT)

    # ── Step 1: Per-coin bootstrap for quality assessment ─────────
    print(f"\n  Step 1: Per-coin quality assessment ({N_BOOT} paths)...")
    per_coin = {}
    t0 = time.time()

    for symbol in COINS:
        r = boot_ratios[symbol]
        p0 = aligned[symbol]["cl"][0]
        sharpes = []
        cagrs = []

        for b in range(N_BOOT):
            brng = np.random.default_rng(boot_seeds[b])
            c, h, l, v, t = gen_path_vcbb(
                r["cr"], r["hr"], r["lr"], r["vol"], r["tb"],
                n_trans, BLKSZ, p0, brng, vcbb=r["vcbb"])

            at = _atr(h, l, c, ATR_P)
            vd = _vdo(c, h, l, v, t, VDO_F, VDO_S)
            ef = _ema(c, fp)
            es = _ema(c, sp)

            # FIX: use wi (not 0) — bootstrap path includes warmup
            m = sim_fast(c, ef, es, at, vd, wi, VDO_THR)
            sharpes.append(m["sharpe"])
            cagrs.append(m["cagr"])

        sharpes = np.array(sharpes)
        cagrs = np.array(cagrs)

        per_coin[symbol] = {
            "p_sharpe_pos": round(float(np.mean(sharpes > 0)), 4),
            "median_sharpe": round(float(np.median(sharpes)), 4),
            "p_cagr_pos": round(float(np.mean(cagrs > 0)), 4),
            "median_cagr": round(float(np.median(cagrs)), 4),
        }

        print(f"    {symbol:>10s}: P(Sh>0)={per_coin[symbol]['p_sharpe_pos']:.1%}  "
              f"medSh={per_coin[symbol]['median_sharpe']:.3f}  "
              f"P(CAGR>0)={per_coin[symbol]['p_cagr_pos']:.1%}")

    elapsed = time.time() - t0
    print(f"  Per-coin: {elapsed:.1f}s")

    # ── Step 2: Define portfolio variants ─────────────────────────
    QUALITY_THR = 0.85
    quality_coins = [s for s in COINS
                     if per_coin[s]["p_sharpe_pos"] >= QUALITY_THR]

    # Sharpe weights (clipped to 0)
    raw_sh = {s: max(0.0, per_coin[s]["median_sharpe"]) for s in COINS}
    total_sh = sum(raw_sh.values())
    sharpe_wts = {s: raw_sh[s] / total_sh if total_sh > 0 else 1 / len(COINS)
                  for s in COINS}

    q_raw_sh = {s: raw_sh[s] for s in quality_coins}
    total_qsh = sum(q_raw_sh.values())
    q_sharpe_wts = {s: q_raw_sh[s] / total_qsh if total_qsh > 0
                    else 1 / len(quality_coins) for s in quality_coins}

    print(f"\n  Quality coins (P(Sh>0) >= {QUALITY_THR:.0%}): {len(quality_coins)}")
    for s in quality_coins:
        print(f"    {s:>10s}: P(Sh>0)={per_coin[s]['p_sharpe_pos']:.1%}  "
              f"medSh={per_coin[s]['median_sharpe']:.3f}")

    print(f"\n  Sharpe weights (top 5):")
    for s, w in sorted(sharpe_wts.items(), key=lambda x: -x[1])[:5]:
        print(f"    {s:>10s}: {w:.1%}")

    port_defs = {
        "eq_all14": {"coins": COINS,
                     "weights": {s: 1.0 / len(COINS) for s in COINS}},
        "eq_quality": {"coins": quality_coins,
                       "weights": {s: 1.0 / len(quality_coins) for s in quality_coins}},
        "sharpe_wt_all14": {"coins": COINS,
                            "weights": sharpe_wts},
        "sharpe_wt_quality": {"coins": quality_coins,
                              "weights": q_sharpe_wts},
        "btc_only": {"coins": ["BTCUSDT"],
                     "weights": {"BTCUSDT": 1.0}},
    }

    # ── Step 3: Synchronized portfolio bootstrap ──────────────────
    print(f"\n  Step 2: Synchronized portfolio bootstrap ({N_BOOT} paths)...")
    t0 = time.time()

    port_results = {name: {"sharpes": [], "cagrs": [], "mdds": []}
                    for name in port_defs}

    for b in range(N_BOOT):
        brng = np.random.default_rng(boot_seeds[b])

        # SHARED block indices (same for all coins)
        n_blk = math.ceil(n_trans / BLKSZ)
        mx = n_trans - BLKSZ
        if mx <= 0:
            shared_idx = np.arange(n_trans)
        else:
            starts = brng.integers(0, mx + 1, size=n_blk)
            shared_idx = np.concatenate(
                [np.arange(s, s + BLKSZ) for s in starts])[:n_trans]

        # Build path for each coin using shared indices, run sim
        coin_navs = {}
        for symbol in COINS:
            r = boot_ratios[symbol]
            p0 = aligned[symbol]["cl"][0]

            # Reconstruct price path from shared indices
            c = np.empty(len(shared_idx) + 1, dtype=np.float64)
            c[0] = p0
            c[1:] = p0 * np.cumprod(r["cr"][shared_idx])

            h = np.empty_like(c)
            l_arr = np.empty_like(c)
            v = np.empty_like(c)
            t_arr = np.empty_like(c)

            h[0] = p0 * 1.002
            l_arr[0] = p0 * 0.998
            v[0] = r["vol"][shared_idx[0]]
            t_arr[0] = r["tb"][shared_idx[0]]

            h[1:] = c[:-1] * r["hr"][shared_idx]
            l_arr[1:] = c[:-1] * r["lr"][shared_idx]
            v[1:] = r["vol"][shared_idx]
            t_arr[1:] = r["tb"][shared_idx]

            np.maximum(h, c, out=h)
            np.minimum(l_arr, c, out=l_arr)

            # Compute indicators on synthetic path
            at = _atr(h, l_arr, c, ATR_P)
            vd = _vdo(c, h, l_arr, v, t_arr, VDO_F, VDO_S)
            ef = _ema(c, fp)
            es = _ema(c, sp)

            # FIX: use wi (not 0) — bootstrap path includes warmup
            coin_navs[symbol] = sim_nav_series(c, ef, es, at, vd, wi, 1.0)

        # Compute each portfolio variant
        for port_name, pdef in port_defs.items():
            port_nav = np.zeros(n_common, dtype=np.float64)
            for symbol in pdef["coins"]:
                w = pdef["weights"][symbol]
                port_nav += coin_navs[symbol] * (w * CASH)

            # FIX: use wi (not 0) — metrics from post-warmup bars
            m = metrics_from_navs(port_nav, wi)
            port_results[port_name]["sharpes"].append(m["sharpe"])
            port_results[port_name]["cagrs"].append(m["cagr"])
            port_results[port_name]["mdds"].append(m["mdd"])

        if (b + 1) % 100 == 0:
            print(f"    Path {b + 1}/{N_BOOT}...")

    elapsed = time.time() - t0
    print(f"  Portfolio bootstrap: {elapsed:.1f}s")

    # ── Analysis ──────────────────────────────────────────────────
    for name in port_results:
        for k in ["sharpes", "cagrs", "mdds"]:
            port_results[name][k] = np.array(port_results[name][k])

    btc_sh = port_results["btc_only"]["sharpes"]
    btc_md = port_results["btc_only"]["mdds"]

    print(f"\n  {'_' * 85}")
    print(f"  {'Portfolio':<22s} {'medSh':>7s} {'medCAGR':>8s} {'medMDD':>7s} "
          f"{'P(Sh>B)':>8s} {'P(MDD<B)':>9s} {'p(Sh)':>10s} {'p(MDD)':>10s}")
    print(f"  {'_' * 85}")

    output = {"per_coin": per_coin, "portfolios": {}}

    for name in port_defs:
        sh = port_results[name]["sharpes"]
        cg = port_results[name]["cagrs"]
        md = port_results[name]["mdds"]

        med_sh = float(np.median(sh))
        med_cg = float(np.median(cg))
        med_md = float(np.median(md))

        if name == "btc_only":
            print(f"  {name:<22s} {med_sh:>7.3f} {med_cg:>7.1f}% {med_md:>6.1f}% "
                  f"{'--':>8s} {'--':>9s} {'--':>10s} {'--':>10s}")
            output["portfolios"][name] = {
                "median_sharpe": round(med_sh, 4),
                "median_cagr": round(med_cg, 2),
                "median_mdd": round(med_md, 2),
            }
            continue

        p_sh = float(np.mean(sh > btc_sh))
        p_mdd = float(np.mean(md < btc_md))
        n_sh_wins = int(np.sum(sh > btc_sh))
        n_mdd_wins = int(np.sum(md < btc_md))
        bt_sh = binomtest(n_sh_wins, N_BOOT, 0.5, alternative='greater')
        bt_mdd = binomtest(n_mdd_wins, N_BOOT, 0.5, alternative='greater')

        print(f"  {name:<22s} {med_sh:>7.3f} {med_cg:>7.1f}% {med_md:>6.1f}% "
              f"{p_sh:>7.1%} {p_mdd:>8.1%} {bt_sh.pvalue:>10.2e} {bt_mdd.pvalue:>10.2e}")

        output["portfolios"][name] = {
            "coins": port_defs[name]["coins"],
            "weights": {k: round(v, 4) for k, v in port_defs[name]["weights"].items()},
            "median_sharpe": round(med_sh, 4),
            "median_cagr": round(med_cg, 2),
            "median_mdd": round(med_md, 2),
            "p_sharpe_higher": round(p_sh, 4),
            "p_mdd_lower": round(p_mdd, 4),
            "binom_sharpe_p": float(bt_sh.pvalue),
            "binom_mdd_p": float(bt_mdd.pvalue),
        }

    return output


# ══════════════════════════════════════════════════════════════════
# Phase 6: Diversification Quantification
# ══════════════════════════════════════════════════════════════════

def phase6_diversification(corr, phase4, phase5):
    """Quantify theoretical vs empirical diversification benefit."""
    print("\n" + "=" * 90)
    print("PHASE 6: DIVERSIFICATION BENEFIT QUANTIFICATION")
    print("=" * 90)

    mean_rho = corr["mean_strategy_rho"]
    K = len(COINS)

    div_ratio_theoretical = math.sqrt(K / (1.0 + (K - 1) * mean_rho))
    k_eff = K / (1.0 + (K - 1) * mean_rho)

    btc_sharpe_real = phase4["btc_only"]["sharpe"]
    port_sharpe_real = phase4["all_14"]["sharpe"]
    div_ratio_real = (port_sharpe_real / btc_sharpe_real
                      if btc_sharpe_real > 0.01 else 0.0)

    btc_sh_boot = phase5["portfolios"]["btc_only"]["median_sharpe"]
    port_sh_boot = phase5["portfolios"]["eq_all14"]["median_sharpe"]
    div_ratio_boot = (port_sh_boot / btc_sh_boot
                      if btc_sh_boot > 0.01 else 0.0)

    print(f"\n  Mean strategy rho = {mean_rho:.4f}")
    print(f"  K = {K} coins")
    print(f"\n  Theoretical Sharpe ratio: x{div_ratio_theoretical:.3f}")
    print(f"  Effective K:             {k_eff:.2f}")
    print(f"\n  Empirical (real data):    x{div_ratio_real:.3f} "
          f"(All14={port_sharpe_real:.3f} / BTC={btc_sharpe_real:.3f})")
    print(f"  Empirical (bootstrap):   x{div_ratio_boot:.3f} "
          f"(All14={port_sh_boot:.3f} / BTC={btc_sh_boot:.3f})")

    # MDD ratio
    btc_mdd_real = phase4["btc_only"]["mdd"]
    port_mdd_real = phase4["all_14"]["mdd"]
    mdd_ratio = port_mdd_real / btc_mdd_real if btc_mdd_real > 0.01 else 0.0
    print(f"\n  MDD ratio (real data):   x{mdd_ratio:.3f} "
          f"(All14={port_mdd_real:.1f}% / BTC={btc_mdd_real:.1f}%)")

    return {
        "mean_rho": round(mean_rho, 6),
        "K": K,
        "k_effective": round(k_eff, 4),
        "div_ratio_theoretical": round(div_ratio_theoretical, 4),
        "div_ratio_real": round(div_ratio_real, 4),
        "div_ratio_bootstrap": round(div_ratio_boot, 4),
        "mdd_ratio_real": round(mdd_ratio, 4),
    }


# ══════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════

def main():
    t_start = time.time()

    print("=" * 90)
    print("MULTI-COIN DIVERSIFICATION STUDY (v2)")
    print(f"VTREND E0 unchanged (N=120, trail=3.0, VDO>0.0)")
    print(f"14 coins x 16 timescales x {N_BOOT} bootstrap paths")
    print(f"Cost: {CPS * 2 * 10000:.0f} bps round-trip ({CPS * 10000:.0f} per side)")
    print("All phases use SAME aligned time range + warmup")
    print("=" * 90)

    # ── Phase 1: Load & prepare ────────────────────────────────
    print("\n" + "=" * 90)
    print("PHASE 1: DATA LOADING & ALIGNMENT")
    print("=" * 90)

    aligned, wi, n_common, n_trans, boot_ratios, raw, info = prepare_data()

    # ── Sanity check ───────────────────────────────────────────
    sanity_ok = sanity_check_btc(aligned, wi, n_common, raw)

    # ── Phase 2: Per-coin real data ────────────────────────────
    phase2 = phase2_per_coin(aligned, wi)

    # ── Phase 3: Correlation ───────────────────────────────────
    phase3 = phase3_correlation(aligned, wi)

    # ── Phase 4: Portfolio simulation ──────────────────────────
    phase4 = phase4_portfolio(aligned, wi, phase2)

    # ── Phase 5: Synchronized bootstrap ────────────────────────
    phase5 = phase5_bootstrap(aligned, wi, n_trans, boot_ratios)

    # ── Phase 6: Diversification ───────────────────────────────
    phase6 = phase6_diversification(phase3, phase4, phase5)

    # ── Final verdict ──────────────────────────────────────────
    print("\n" + "=" * 90)
    print("FINAL VERDICT")
    print("=" * 90)

    meta = phase2["_meta"]
    verdicts = []

    # 1. Cross-asset alpha
    if meta["binomial_p"] < 0.05:
        verdicts.append(f"VTREND generalizes: {meta['k_positive']}/{meta['n_coins']} "
                        f"coins positive Sharpe (p={meta['binomial_p']:.4f})")
    else:
        verdicts.append(f"Insufficient cross-asset alpha: only {meta['k_positive']}/{meta['n_coins']} "
                        f"coins (p={meta['binomial_p']:.4f})")

    # 2. Synchronized bootstrap — find best variant
    best_name = None
    best_p_sh = 0.0
    for name, r in phase5["portfolios"].items():
        if name == "btc_only":
            continue
        p = r.get("p_sharpe_higher", 0)
        if p > best_p_sh:
            best_p_sh = p
            best_name = name

    if best_name:
        best = phase5["portfolios"][best_name]
        bp_sh = best["binom_sharpe_p"]
        bp_mdd = best["binom_mdd_p"]

        if bp_sh < 0.001:
            verdicts.append(f"Bootstrap ({best_name}): PROVEN higher Sharpe *** "
                            f"(P={best['p_sharpe_higher']:.1%}, p={bp_sh:.2e})")
        elif bp_sh < 0.05:
            verdicts.append(f"Bootstrap ({best_name}): Significantly higher Sharpe "
                            f"(P={best['p_sharpe_higher']:.1%}, p={bp_sh:.4f})")
        else:
            verdicts.append(f"Bootstrap ({best_name}): Sharpe NOT significant "
                            f"(P={best['p_sharpe_higher']:.1%}, p={bp_sh:.4f})")

        if bp_mdd < 0.001:
            verdicts.append(f"Bootstrap ({best_name}): PROVEN lower MDD *** "
                            f"(P={best['p_mdd_lower']:.1%}, p={bp_mdd:.2e})")
        elif bp_mdd < 0.05:
            verdicts.append(f"Bootstrap ({best_name}): Significantly lower MDD "
                            f"(P={best['p_mdd_lower']:.1%}, p={bp_mdd:.4f})")
        else:
            verdicts.append(f"Bootstrap ({best_name}): MDD NOT significant "
                            f"(P={best['p_mdd_lower']:.1%}, p={bp_mdd:.4f})")

        sync_pass = bp_sh < 0.05 or bp_mdd < 0.05
    else:
        sync_pass = False

    # 3. Real data check
    btc_real = phase4["btc_only"]
    port_real = phase4["all_14"]
    real_sh_wins = port_real["sharpe"] > btc_real["sharpe"]
    real_mdd_wins = port_real["mdd"] < btc_real["mdd"]
    if real_sh_wins and real_mdd_wins:
        verdicts.append(f"Real data: Portfolio beats BTC on BOTH Sharpe and MDD")
    elif real_sh_wins or real_mdd_wins:
        won = "Sharpe" if real_sh_wins else "MDD"
        verdicts.append(f"Real data: Portfolio beats BTC on {won} only")
    else:
        verdicts.append(f"Real data: Portfolio LOSES to BTC "
                        f"(Sh {port_real['sharpe']:.3f} vs {btc_real['sharpe']:.3f}, "
                        f"MDD {port_real['mdd']:.1f}% vs {btc_real['mdd']:.1f}%)")

    real_pass = real_sh_wins or real_mdd_wins

    if sync_pass and real_pass:
        overall = "ACCEPT: Multi-coin diversification adds proven value"
    elif sync_pass and not real_pass:
        overall = ("SHARPE PROVEN (bootstrap), MDD WORSE: Multi-coin adds Sharpe "
                   "but does NOT reduce MDD. Use position sizing to control drawdown.")
    elif not sync_pass:
        overall = "REJECT: No significant diversification benefit"
    else:
        overall = "INCONCLUSIVE"

    for v in verdicts:
        print(f"  * {v}")
    print(f"\n  OVERALL: {overall}")

    elapsed = time.time() - t_start
    print(f"\n  Total runtime: {elapsed:.1f}s")

    # ── Save results ───────────────────────────────────────────
    out_dir = ROOT / "research" / "results" / "multicoin_diversification"
    out_dir.mkdir(parents=True, exist_ok=True)

    output = {
        "config": {
            "coins": COINS,
            "slow_periods": SLOW_PERIODS,
            "n_boot": N_BOOT,
            "blksz": BLKSZ,
            "seed": SEED,
            "cash": CASH,
            "cps": CPS,
            "trail": TRAIL,
            "atr_p": ATR_P,
            "vdo_f": VDO_F,
            "vdo_s": VDO_S,
            "vdo_thr": VDO_THR,
            "warmup_days": WARMUP_DAYS,
        },
        "alignment": info,
        "sanity_check_passed": sanity_ok,
        "phase2_per_coin": {
            s: {k: v for k, v in r.items() if k != "by_timescale"}
            for s, r in phase2.items() if s != "_meta"
        },
        "phase2_meta": phase2["_meta"],
        "phase2_full": {s: r for s, r in phase2.items() if s != "_meta"},
        "phase3_correlation": phase3,
        "phase4_portfolio": phase4,
        "phase5_bootstrap": phase5,
        "phase6_diversification": phase6,
        "overall_verdict": overall,
        "verdicts": verdicts,
        "runtime_seconds": round(elapsed, 1),
    }

    out_file = out_dir / "multicoin_diversification.json"
    with open(out_file, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\n  Results saved to: {out_file}")


if __name__ == "__main__":
    main()
