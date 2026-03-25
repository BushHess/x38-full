#!/usr/bin/env python3
"""Multi-Coin Exit Variants Study.

Runs E0, E5, E6, E7 on all 14 coins at N=120 (default VTREND params).
Each coin uses its FULL available data history for maximum warmup.

Exit variants:
  E0: Standard ATR trail (3.0× ATR-14) + EMA cross-down
  E5: Robust ATR trail (cap TR at Q90/100 bars, Wilder period=20) + EMA cross-down
  E6: E0 + staleness exit (sb=24, mt=3.0)
  E7: E5 + staleness exit (sb=24, mt=3.0)

Prior BTC-only results:
  E0: baseline (PROVEN)
  E5: PROVEN MDD reduction (16/16), LOSES CAGR (0/16) → REJECTED
  E6: REJECTED (P(NAV+)=32.4%, staleness hurts in bootstrap)
  E7: REJECTED (P(NAV+)=40.6%, no positive interaction)
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

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from strategies.vtrend.strategy import _ema, _atr, _vdo

# ── Constants ─────────────────────────────────────────────────────────

CACHE_DIR = "/var/www/trading-bots/data-pipeline/.cache_binance_vision"

COINS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
    "LTCUSDT", "ADAUSDT", "DOGEUSDT", "TRXUSDT", "AVAXUSDT",
    "LINKUSDT", "BCHUSDT", "HBARUSDT", "XLMUSDT",
]

CASH     = 10_000.0
CPS      = 0.0025       # 25 bps per side (50 bps round-trip)
TRAIL    = 3.0
ATR_P    = 14
VDO_F    = 12
VDO_S    = 28
VDO_THR  = 0.0
ANN      = math.sqrt(6.0 * 365.25)

WARMUP_DAYS = 365

# Default timescale
SP = 120
FP = max(5, SP // 4)  # = 30

# Staleness params for E6 and E7 (representative middle-grid values)
STALE_BARS = 24
MFE_THR = 3.0

OUTDIR = Path(__file__).resolve().parent / "results" / "multicoin_exit_variants"


# ═══════════════════════════════════════════════════════════════════════
# Data Loading (from multicoin_diversification.py)
# ═══════════════════════════════════════════════════════════════════════

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
                    ts = int(cols[0])
                    if ts > 1e15:
                        ts = ts // 1000
                    rows.append((
                        ts,
                        float(cols[2]),     # high
                        float(cols[3]),     # low
                        float(cols[4]),     # close
                        float(cols[5]),     # volume
                        float(cols[9]),     # taker_buy_base_vol
                    ))
        except Exception as e:
            print(f"  Warning: failed to read {zp}: {e}")

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


# ═══════════════════════════════════════════════════════════════════════
# Robust ATR (from e5_validation.py)
# ═══════════════════════════════════════════════════════════════════════

def _robust_atr(hi, lo, cl, cap_q=0.90, cap_lb=100, period=20):
    """Robust ATR: cap TR at rolling Q90, then Wilder EMA."""
    prev_cl = np.concatenate([[cl[0]], cl[:-1]])
    tr = np.maximum(
        hi - lo,
        np.maximum(np.abs(hi - prev_cl), np.abs(lo - prev_cl)),
    )
    n = len(tr)
    tr_cap = np.full(n, np.nan)
    for i in range(cap_lb, n):
        q = np.percentile(tr[i - cap_lb : i], cap_q * 100)
        tr_cap[i] = min(tr[i], q)
    ratr = np.full(n, np.nan)
    s = cap_lb
    if s + period <= n:
        ratr[s + period - 1] = np.mean(tr_cap[s : s + period])
        for i in range(s + period, n):
            ratr[i] = (ratr[i - 1] * (period - 1) + tr_cap[i]) / period
    return ratr


# ═══════════════════════════════════════════════════════════════════════
# Metrics helper
# ═══════════════════════════════════════════════════════════════════════

def _metrics(navs_start, navs_end, nav_min_ratio, rets_sum, rets_sq_sum, n_rets, nt):
    if n_rets < 2 or navs_start <= 0:
        return {"sharpe": 0.0, "cagr": -100.0, "mdd": 100.0, "calmar": 0.0,
                "trades": nt, "final_nav": navs_end}
    tr = navs_end / navs_start - 1.0
    yrs = n_rets / (6.0 * 365.25)
    cagr = ((1 + tr) ** (1.0 / yrs) - 1.0) * 100 if yrs > 0 and tr > -1 else -100.0
    mdd = (1.0 - nav_min_ratio) * 100.0
    mu = rets_sum / n_rets
    var = rets_sq_sum / n_rets - mu * mu
    std = math.sqrt(max(var, 0.0))
    sharpe = (mu / std * ANN) if std > 1e-12 else 0.0
    calmar = cagr / mdd if mdd > 0.01 else 0.0
    return {
        "sharpe": sharpe,
        "cagr": cagr,
        "mdd": mdd,
        "calmar": calmar,
        "trades": nt,
        "final_nav": navs_end,
    }


# ═══════════════════════════════════════════════════════════════════════
# Simulation: E0 (standard)
# ═══════════════════════════════════════════════════════════════════════

def sim_e0(cl, ef, es, at, vd, wi):
    n = len(cl)
    cash = CASH; bq = 0.0; inp = False; pk = 0.0; pe = px = False; nt = 0
    navs_start = 0.0; navs_end = 0.0; nav_peak = 0.0; nav_min_ratio = 1.0
    rets_sum = 0.0; rets_sq_sum = 0.0; n_rets = 0; prev_nav = 0.0; started = False

    for i in range(n):
        p = cl[i]
        if i > 0:
            fp = cl[i - 1]
            if pe:
                pe = False; bq = cash / (fp * (1.0 + CPS)); cash = 0.0; inp = True; pk = p
            elif px:
                cash = bq * fp * (1.0 - CPS); bq = 0.0; inp = False; pk = 0.0; nt += 1; px = False
        nav = cash + bq * p
        if i >= wi:
            if not started:
                navs_start = nav; nav_peak = nav; prev_nav = nav; started = True
            else:
                if prev_nav > 0:
                    r = nav / prev_nav - 1.0
                    rets_sum += r; rets_sq_sum += r * r; n_rets += 1
                prev_nav = nav
            navs_end = nav
            if nav > nav_peak: nav_peak = nav
            ratio = nav / nav_peak if nav_peak > 0 else 1.0
            if ratio < nav_min_ratio: nav_min_ratio = ratio
        a_val = at[i]
        if math.isnan(a_val) or math.isnan(ef[i]) or math.isnan(es[i]): continue
        if not inp:
            if ef[i] > es[i] and vd[i] > VDO_THR: pe = True
        else:
            pk = max(pk, p)
            if p < pk - TRAIL * a_val: px = True
            elif ef[i] < es[i]: px = True
    if inp and bq > 0:
        cash = bq * cl[-1] * (1.0 - CPS); bq = 0.0; nt += 1; navs_end = cash
    return _metrics(navs_start, navs_end, nav_min_ratio, rets_sum, rets_sq_sum, n_rets, nt)


# ═══════════════════════════════════════════════════════════════════════
# Simulation: E5 (robust ATR trail)
# ═══════════════════════════════════════════════════════════════════════

def sim_e5(cl, ef, es, at, vd, wi, ratr):
    n = len(cl)
    cash = CASH; bq = 0.0; inp = False; pk = 0.0; pe = px = False; nt = 0
    navs_start = 0.0; navs_end = 0.0; nav_peak = 0.0; nav_min_ratio = 1.0
    rets_sum = 0.0; rets_sq_sum = 0.0; n_rets = 0; prev_nav = 0.0; started = False

    for i in range(n):
        p = cl[i]
        if i > 0:
            fp = cl[i - 1]
            if pe:
                pe = False; bq = cash / (fp * (1.0 + CPS)); cash = 0.0; inp = True; pk = p
            elif px:
                cash = bq * fp * (1.0 - CPS); bq = 0.0; inp = False; pk = 0.0; nt += 1; px = False
        nav = cash + bq * p
        if i >= wi:
            if not started:
                navs_start = nav; nav_peak = nav; prev_nav = nav; started = True
            else:
                if prev_nav > 0:
                    r = nav / prev_nav - 1.0
                    rets_sum += r; rets_sq_sum += r * r; n_rets += 1
                prev_nav = nav
            navs_end = nav
            if nav > nav_peak: nav_peak = nav
            ratio = nav / nav_peak if nav_peak > 0 else 1.0
            if ratio < nav_min_ratio: nav_min_ratio = ratio
        a_val = at[i]; ra_val = ratr[i]
        if math.isnan(a_val) or math.isnan(ef[i]) or math.isnan(es[i]): continue
        if math.isnan(ra_val): continue
        if not inp:
            if ef[i] > es[i] and vd[i] > VDO_THR: pe = True
        else:
            pk = max(pk, p)
            if p < pk - TRAIL * ra_val: px = True
            elif ef[i] < es[i]: px = True
    if inp and bq > 0:
        cash = bq * cl[-1] * (1.0 - CPS); bq = 0.0; nt += 1; navs_end = cash
    return _metrics(navs_start, navs_end, nav_min_ratio, rets_sum, rets_sq_sum, n_rets, nt)


# ═══════════════════════════════════════════════════════════════════════
# Simulation: E6 (E0 + staleness exit)
# ═══════════════════════════════════════════════════════════════════════

def sim_e6(cl, ef, es, at, vd, wi, stale_bars, mfe_thr):
    n = len(cl)
    cash = CASH; bq = 0.0; inp = False; pk = 0.0; pe = px = False; nt = 0
    entry_price = 0.0; entry_atr = 0.0; pk_bar = 0
    navs_start = 0.0; navs_end = 0.0; nav_peak = 0.0; nav_min_ratio = 1.0
    rets_sum = 0.0; rets_sq_sum = 0.0; n_rets = 0; prev_nav = 0.0; started = False

    for i in range(n):
        p = cl[i]
        if i > 0:
            fp = cl[i - 1]
            if pe:
                pe = False; bq = cash / (fp * (1.0 + CPS)); cash = 0.0; inp = True
                pk = p; pk_bar = i; entry_price = fp
                entry_atr = at[i] if not math.isnan(at[i]) else 0.0
            elif px:
                cash = bq * fp * (1.0 - CPS); bq = 0.0; inp = False; pk = 0.0; nt += 1; px = False
                entry_price = 0.0; entry_atr = 0.0; pk_bar = 0
        nav = cash + bq * p
        if i >= wi:
            if not started:
                navs_start = nav; nav_peak = nav; prev_nav = nav; started = True
            else:
                if prev_nav > 0:
                    r = nav / prev_nav - 1.0
                    rets_sum += r; rets_sq_sum += r * r; n_rets += 1
                prev_nav = nav
            navs_end = nav
            if nav > nav_peak: nav_peak = nav
            ratio = nav / nav_peak if nav_peak > 0 else 1.0
            if ratio < nav_min_ratio: nav_min_ratio = ratio
        a_val = at[i]
        if math.isnan(a_val) or math.isnan(ef[i]) or math.isnan(es[i]): continue
        if not inp:
            if ef[i] > es[i] and vd[i] > VDO_THR: pe = True
        else:
            if p > pk: pk = p; pk_bar = i
            if p < pk - TRAIL * a_val: px = True
            elif ef[i] < es[i]: px = True
            if not px and entry_atr > 1e-12:
                mfe_r = (pk - entry_price) / entry_atr
                if mfe_r >= mfe_thr and (i - pk_bar) >= stale_bars: px = True
    if inp and bq > 0:
        cash = bq * cl[-1] * (1.0 - CPS); bq = 0.0; nt += 1; navs_end = cash
    return _metrics(navs_start, navs_end, nav_min_ratio, rets_sum, rets_sq_sum, n_rets, nt)


# ═══════════════════════════════════════════════════════════════════════
# Simulation: E7 (E5 + staleness exit)
# ═══════════════════════════════════════════════════════════════════════

def sim_e7(cl, ef, es, at, vd, wi, ratr, stale_bars, mfe_thr):
    n = len(cl)
    cash = CASH; bq = 0.0; inp = False; pk = 0.0; pe = px = False; nt = 0
    entry_price = 0.0; entry_atr = 0.0; pk_bar = 0
    navs_start = 0.0; navs_end = 0.0; nav_peak = 0.0; nav_min_ratio = 1.0
    rets_sum = 0.0; rets_sq_sum = 0.0; n_rets = 0; prev_nav = 0.0; started = False

    for i in range(n):
        p = cl[i]
        if i > 0:
            fp = cl[i - 1]
            if pe:
                pe = False; bq = cash / (fp * (1.0 + CPS)); cash = 0.0; inp = True
                pk = p; pk_bar = i; entry_price = fp
                entry_atr = at[i] if not math.isnan(at[i]) else 0.0
            elif px:
                cash = bq * fp * (1.0 - CPS); bq = 0.0; inp = False; pk = 0.0; nt += 1; px = False
                entry_price = 0.0; entry_atr = 0.0; pk_bar = 0
        nav = cash + bq * p
        if i >= wi:
            if not started:
                navs_start = nav; nav_peak = nav; prev_nav = nav; started = True
            else:
                if prev_nav > 0:
                    r = nav / prev_nav - 1.0
                    rets_sum += r; rets_sq_sum += r * r; n_rets += 1
                prev_nav = nav
            navs_end = nav
            if nav > nav_peak: nav_peak = nav
            ratio = nav / nav_peak if nav_peak > 0 else 1.0
            if ratio < nav_min_ratio: nav_min_ratio = ratio
        a_val = at[i]; ra_val = ratr[i]
        if math.isnan(a_val) or math.isnan(ef[i]) or math.isnan(es[i]): continue
        if math.isnan(ra_val): continue
        if not inp:
            if ef[i] > es[i] and vd[i] > VDO_THR: pe = True
        else:
            if p > pk: pk = p; pk_bar = i
            trail = pk - TRAIL * ra_val
            if p < trail: px = True
            elif ef[i] < es[i]: px = True
            if not px and entry_atr > 1e-12:
                mfe_r = (pk - entry_price) / entry_atr
                if mfe_r >= mfe_thr and (i - pk_bar) >= stale_bars: px = True
    if inp and bq > 0:
        cash = bq * cl[-1] * (1.0 - CPS); bq = 0.0; nt += 1; navs_end = cash
    return _metrics(navs_start, navs_end, nav_min_ratio, rets_sum, rets_sq_sum, n_rets, nt)


# ═══════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    t0 = time.time()

    print("MULTI-COIN EXIT VARIANTS: E0 / E5 / E6 / E7")
    print("=" * 90)
    print(f"  N={SP} (fast={FP}), trail={TRAIL}, cost=50bps RT, warmup={WARMUP_DAYS}d")
    print(f"  E5: robust ATR (cap_q=0.90, cap_lb=100, period=20)")
    print(f"  E6: E0 + staleness (sb={STALE_BARS}, mt={MFE_THR})")
    print(f"  E7: E5 + staleness (sb={STALE_BARS}, mt={MFE_THR})")
    print(f"  Coins: {len(COINS)}")

    # ── Load and run per coin ──
    results = {}

    print(f"\n  Loading coins and running simulations...")
    for symbol in COINS:
        d = load_coin_raw(symbol)
        n = d["n"]
        cl, hi, lo = d["cl"], d["hi"], d["lo"]
        vo, tb = d["vo"], d["tb"]

        # Warmup index
        wi = min(WARMUP_DAYS * 6, n - 100)

        # Compute indicators on full data
        at = _atr(hi, lo, cl, ATR_P)
        vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)
        ratr = _robust_atr(hi, lo, cl)
        ef = _ema(cl, FP)
        es = _ema(cl, SP)

        t0_s = datetime.fromtimestamp(d["timestamps"][0] / 1000, tz=timezone.utc)
        t1_s = datetime.fromtimestamp(d["timestamps"][-1] / 1000, tz=timezone.utc)

        r0 = sim_e0(cl, ef, es, at, vd, wi)
        r5 = sim_e5(cl, ef, es, at, vd, wi, ratr)
        r6 = sim_e6(cl, ef, es, at, vd, wi, STALE_BARS, MFE_THR)
        r7 = sim_e7(cl, ef, es, at, vd, wi, ratr, STALE_BARS, MFE_THR)

        results[symbol] = {
            "n_bars": n, "wi": wi,
            "start": f"{t0_s:%Y-%m-%d}", "end": f"{t1_s:%Y-%m-%d}",
            "E0": r0, "E5": r5, "E6": r6, "E7": r7,
        }
        print(f"    {symbol:>10s}: {n:6d} bars ({t0_s:%Y-%m-%d} → {t1_s:%Y-%m-%d})")

    # ── Results table: Sharpe ──
    print("\n" + "=" * 90)
    print("SHARPE RATIO BY COIN × EXIT VARIANT")
    print("=" * 90)
    print(f"  {'Coin':>10s}  {'Bars':>6s}  {'E0':>8s}  {'E5':>8s}  {'E6':>8s}  {'E7':>8s}  "
          f"{'Best':>4s}  {'ΔE5-E0':>8s}  {'ΔE7-E0':>8s}")
    print("  " + "-" * 80)

    for s in COINS:
        r = results[s]
        sh = {v: r[v]["sharpe"] for v in ["E0", "E5", "E6", "E7"]}
        best = max(sh, key=sh.get)
        d_e5 = sh["E5"] - sh["E0"]
        d_e7 = sh["E7"] - sh["E0"]
        print(f"  {s:>10s}  {r['n_bars']:6d}  "
              f"{sh['E0']:+8.3f}  {sh['E5']:+8.3f}  {sh['E6']:+8.3f}  {sh['E7']:+8.3f}  "
              f"{best:>4s}  {d_e5:+8.4f}  {d_e7:+8.4f}")

    # ── Results table: CAGR ──
    print("\n" + "=" * 90)
    print("CAGR (%) BY COIN × EXIT VARIANT")
    print("=" * 90)
    print(f"  {'Coin':>10s}  {'E0':>9s}  {'E5':>9s}  {'E6':>9s}  {'E7':>9s}  "
          f"{'Best':>4s}  {'ΔE5-E0':>8s}  {'ΔE7-E0':>8s}")
    print("  " + "-" * 65)

    for s in COINS:
        r = results[s]
        cg = {v: r[v]["cagr"] for v in ["E0", "E5", "E6", "E7"]}
        best = max(cg, key=cg.get)
        d_e5 = cg["E5"] - cg["E0"]
        d_e7 = cg["E7"] - cg["E0"]
        print(f"  {s:>10s}  "
              f"{cg['E0']:+8.1f}%  {cg['E5']:+8.1f}%  {cg['E6']:+8.1f}%  {cg['E7']:+8.1f}%  "
              f"{best:>4s}  {d_e5:+7.1f}pp  {d_e7:+7.1f}pp")

    # ── Results table: MDD ──
    print("\n" + "=" * 90)
    print("MAX DRAWDOWN (%) BY COIN × EXIT VARIANT")
    print("=" * 90)
    print(f"  {'Coin':>10s}  {'E0':>7s}  {'E5':>7s}  {'E6':>7s}  {'E7':>7s}  "
          f"{'Best':>4s}  {'ΔE5-E0':>8s}  {'ΔE7-E0':>8s}")
    print("  " + "-" * 60)

    for s in COINS:
        r = results[s]
        md = {v: r[v]["mdd"] for v in ["E0", "E5", "E6", "E7"]}
        best = min(md, key=md.get)  # lower is better
        d_e5 = md["E5"] - md["E0"]
        d_e7 = md["E7"] - md["E0"]
        print(f"  {s:>10s}  "
              f"{md['E0']:6.1f}%  {md['E5']:6.1f}%  {md['E6']:6.1f}%  {md['E7']:6.1f}%  "
              f"{best:>4s}  {d_e5:+7.1f}pp  {d_e7:+7.1f}pp")

    # ── Results table: Trades ──
    print("\n" + "=" * 90)
    print("TRADE COUNT BY COIN × EXIT VARIANT")
    print("=" * 90)
    print(f"  {'Coin':>10s}  {'E0':>6s}  {'E5':>6s}  {'E6':>6s}  {'E7':>6s}")
    print("  " + "-" * 38)

    for s in COINS:
        r = results[s]
        print(f"  {s:>10s}  "
              f"{r['E0']['trades']:6d}  {r['E5']['trades']:6d}  "
              f"{r['E6']['trades']:6d}  {r['E7']['trades']:6d}")

    # ── Summary statistics ──
    print("\n" + "=" * 90)
    print("SUMMARY: CROSS-COIN CONSISTENCY")
    print("=" * 90)

    variants = ["E0", "E5", "E6", "E7"]
    for v in variants:
        sharpes = [results[s][v]["sharpe"] for s in COINS]
        cagrs = [results[s][v]["cagr"] for s in COINS]
        mdds = [results[s][v]["mdd"] for s in COINS]
        n_pos_sh = sum(1 for x in sharpes if x > 0)
        n_pos_cagr = sum(1 for x in cagrs if x > 0)
        print(f"\n  {v}:")
        print(f"    Sharpe: med={np.median(sharpes):+.3f}, mean={np.mean(sharpes):+.3f}, "
              f"positive: {n_pos_sh}/{len(COINS)}")
        print(f"    CAGR:   med={np.median(cagrs):+.1f}%, mean={np.mean(cagrs):+.1f}%, "
              f"positive: {n_pos_cagr}/{len(COINS)}")
        print(f"    MDD:    med={np.median(mdds):.1f}%, mean={np.mean(mdds):.1f}%")

    # ── Pairwise: which variant wins most coins? ──
    print("\n" + "=" * 90)
    print("PAIRWISE: VARIANT WINS PER COIN (on Sharpe)")
    print("=" * 90)

    for v1, v2 in [("E5", "E0"), ("E6", "E0"), ("E7", "E0"), ("E7", "E5")]:
        wins = sum(1 for s in COINS
                   if results[s][v1]["sharpe"] > results[s][v2]["sharpe"])
        print(f"  {v1} > {v2}: {wins}/{len(COINS)} coins")

    print(f"\n  Best variant per coin (Sharpe):")
    for s in COINS:
        sh = {v: results[s][v]["sharpe"] for v in variants}
        best = max(sh, key=sh.get)
        print(f"    {s:>10s}: {best} (Sharpe={sh[best]:+.3f})")

    # ── E5 vs E0 MDD comparison (E5's proven advantage on BTC) ──
    print("\n" + "=" * 90)
    print("E5 MDD ADVANTAGE (robust ATR = PROVEN MDD reduction on BTC)")
    print("=" * 90)

    n_mdd_better = sum(1 for s in COINS
                       if results[s]["E5"]["mdd"] < results[s]["E0"]["mdd"])
    print(f"  E5 lower MDD: {n_mdd_better}/{len(COINS)} coins")
    for s in COINS:
        d = results[s]["E5"]["mdd"] - results[s]["E0"]["mdd"]
        marker = " +" if d < 0 else ""
        print(f"    {s:>10s}: E0={results[s]['E0']['mdd']:.1f}%, "
              f"E5={results[s]['E5']['mdd']:.1f}%, Δ={d:+.1f}pp{marker}")

    el = time.time() - t0
    print(f"\n  Total time: {el:.1f}s")

    # ── Save JSON ──
    OUTDIR.mkdir(parents=True, exist_ok=True)
    outfile = OUTDIR / "multicoin_exit_variants.json"
    with open(outfile, "w") as f:
        json.dump({
            "config": {
                "slow_period": SP, "fast_period": FP,
                "trail": TRAIL, "cost_bps_rt": 50,
                "warmup_days": WARMUP_DAYS,
                "stale_bars": STALE_BARS, "mfe_thr": MFE_THR,
                "e5_cap_q": 0.90, "e5_cap_lb": 100, "e5_period": 20,
                "coins": COINS,
            },
            "per_coin": results,
        }, f, indent=2)
    print(f"  Saved: {outfile}")
    print("=" * 90)
