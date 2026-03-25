#!/usr/bin/env python3
"""Multi-coin comparison: slow=200/fast=50/trail=3.0 vs slow=120/fast=30/trail=3.0.

Real data only. All 14 coins on aligned common date range.
Per-coin + portfolio comparison.
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

LARGE_CAP = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT"]

CASH     = 10_000.0
CPS      = 0.0025
ATR_P    = 14
VDO_F    = 12
VDO_S    = 28
VDO_THR  = 0.0
ANN      = math.sqrt(6.0 * 365.25)

WARMUP_DAYS = 365

CONFIGS = {
    "C200": {"slow": 200, "fast": 50, "trail": 3.0, "label": "200/50/3.0"},
    "D120": {"slow": 120, "fast": 30, "trail": 3.0, "label": "120/30/3.0"},
}

OUTDIR = Path(__file__).resolve().parent / "results" / "multicoin_200v120"


# ═══════════════════════════════════════════════════════════════════════

def load_coin_raw(symbol):
    monthly = sorted(glob.glob(f"{CACHE_DIR}/spot/monthly/klines/{symbol}/4h/*.zip"))
    daily = sorted(glob.glob(f"{CACHE_DIR}/spot/daily/klines/{symbol}/4h/*.zip"))
    rows = []
    for zp in monthly + daily:
        try:
            with zipfile.ZipFile(zp) as zf:
                fname = zf.namelist()[0]
                data = zf.read(fname).decode()
                for line in data.strip().split('\n'):
                    cols = line.split(',')
                    if len(cols) < 12: continue
                    ts = int(cols[0])
                    if ts > 1e15: ts = ts // 1000
                    rows.append((ts, float(cols[2]), float(cols[3]), float(cols[4]),
                                 float(cols[5]), float(cols[9])))
        except Exception:
            pass
    rows.sort(key=lambda x: x[0])
    seen = set(); unique = []
    for r in rows:
        if r[0] not in seen: seen.add(r[0]); unique.append(r)
    return {
        "cl": np.array([r[3] for r in unique], dtype=np.float64),
        "hi": np.array([r[1] for r in unique], dtype=np.float64),
        "lo": np.array([r[2] for r in unique], dtype=np.float64),
        "vo": np.array([r[4] for r in unique], dtype=np.float64),
        "tb": np.array([r[5] for r in unique], dtype=np.float64),
        "n": len(unique),
        "timestamps": np.array([r[0] for r in unique], dtype=np.int64),
    }


def _metrics(navs_start, navs_end, nav_min_ratio, rets_sum, rets_sq_sum, n_rets, nt):
    if n_rets < 2 or navs_start <= 0:
        return {"sharpe": 0.0, "cagr": -100.0, "mdd": 100.0, "calmar": 0.0, "trades": nt}
    tr = navs_end / navs_start - 1.0
    yrs = n_rets / (6.0 * 365.25)
    cagr = ((1 + tr) ** (1.0 / yrs) - 1.0) * 100 if yrs > 0 and tr > -1 else -100.0
    mdd = (1.0 - nav_min_ratio) * 100.0
    mu = rets_sum / n_rets
    var = rets_sq_sum / n_rets - mu * mu
    std = math.sqrt(max(var, 0.0))
    sharpe = (mu / std * ANN) if std > 1e-12 else 0.0
    calmar = cagr / mdd if mdd > 0.01 else 0.0
    return {"sharpe": sharpe, "cagr": cagr, "mdd": mdd,
            "calmar": calmar, "trades": nt}


def sim_vtrend(cl, ef, es, at, vd, wi, trail):
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
            if p < pk - trail * a_val: px = True
            elif ef[i] < es[i]: px = True
    if inp and bq > 0:
        cash = bq * cl[-1] * (1.0 - CPS); bq = 0.0; nt += 1; navs_end = cash
    return _metrics(navs_start, navs_end, nav_min_ratio, rets_sum, rets_sq_sum, n_rets, nt)


def sim_nav_series(cl, ef, es, at, vd, wi, start_cash, trail):
    n = len(cl)
    cash = start_cash; bq = 0.0; inp = False; pk = 0.0; pe = px = False
    navs = np.full(n, start_cash)
    for i in range(n):
        p = cl[i]
        if i > 0:
            fp = cl[i - 1]
            if pe:
                pe = False; bq = cash / (fp * (1.0 + CPS)); cash = 0.0; inp = True; pk = p
            elif px:
                px = False; cash = bq * fp * (1.0 - CPS); bq = 0.0; inp = False; pk = 0.0
        nav = cash + bq * p
        navs[i] = nav
        a_val = at[i]
        if math.isnan(a_val) or math.isnan(ef[i]) or math.isnan(es[i]): continue
        if not inp:
            if ef[i] > es[i] and vd[i] > VDO_THR: pe = True
        else:
            pk = max(pk, p)
            if p < pk - trail * a_val: px = True
            elif ef[i] < es[i]: px = True
    if inp and bq > 0:
        cash = bq * cl[-1] * (1.0 - CPS); navs[-1] = cash
    return navs


def metrics_from_navs(navs, wi):
    active = navs[wi:]
    n = len(active)
    if n < 10:
        return {"sharpe": 0.0, "cagr": -100.0, "mdd": 100.0, "calmar": 0.0}
    rets = active[1:] / active[:-1] - 1.0
    n_rets = len(rets)
    if n_rets < 2:
        return {"sharpe": 0.0, "cagr": -100.0, "mdd": 100.0, "calmar": 0.0}
    mu = np.mean(rets); std = np.std(rets, ddof=0)
    sharpe = (mu / std * ANN) if std > 1e-12 else 0.0
    tr = active[-1] / active[0] - 1.0
    yrs = n_rets / (6.0 * 365.25)
    cagr = ((1 + tr) ** (1.0 / yrs) - 1.0) * 100 if yrs > 0 and tr > -1 else -100.0
    peak = np.maximum.accumulate(active)
    dd = 1.0 - active / peak
    mdd = float(np.max(dd)) * 100.0
    calmar = cagr / mdd if mdd > 0.01 else 0.0
    return {"sharpe": sharpe, "cagr": cagr, "mdd": mdd,
            "calmar": calmar}


# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    t_start = time.time()

    print("MULTI-COIN: slow=200/fast=50/trail=3.0 vs slow=120/fast=30/trail=3.0")
    print("=" * 100)

    # ── Phase 1: Per-coin full history ──
    print(f"\n{'='*100}")
    print("PHASE 1: PER-COIN FULL HISTORY")
    print(f"{'='*100}")

    print(f"\n  {'Coin':>10s}  {'Bars':>6s}  "
          f"{'C200 Sh':>7s} {'CAGR':>7s} {'MDD':>6s} {'Trd':>4s}  "
          f"{'D120 Sh':>7s} {'CAGR':>7s} {'MDD':>6s} {'Trd':>4s}  "
          f"{'ΔSh':>6s} {'ΔCAGR':>7s} {'ΔMDD':>6s}")
    print("  " + "-" * 98)

    coin_results = {}
    c200_wins_sh = 0; c200_wins_cg = 0; c200_wins_md = 0

    for symbol in COINS:
        d = load_coin_raw(symbol)
        cl, hi, lo, vo, tb = d["cl"], d["hi"], d["lo"], d["vo"], d["tb"]
        n = d["n"]
        wi = min(WARMUP_DAYS * 6, n - 100)

        at = _atr(hi, lo, cl, ATR_P)
        vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)

        results = {}
        for cname, cfg in CONFIGS.items():
            ef = _ema(cl, cfg["fast"]); es = _ema(cl, cfg["slow"])
            results[cname] = sim_vtrend(cl, ef, es, at, vd, wi, cfg["trail"])

        rc = results["C200"]; rd = results["D120"]
        d_sh = rc["sharpe"] - rd["sharpe"]
        d_cg = rc["cagr"] - rd["cagr"]
        d_md = rc["mdd"] - rd["mdd"]

        if d_sh > 0: c200_wins_sh += 1
        if d_cg > 0: c200_wins_cg += 1
        if d_md < 0: c200_wins_md += 1

        coin_results[symbol] = {"C200": rc, "D120": rd, "d_sh": d_sh, "d_cg": d_cg, "d_md": d_md}

        print(f"  {symbol:>10s}  {n:6d}  "
              f"{rc['sharpe']:+7.3f} {rc['cagr']:+6.1f}% {rc['mdd']:5.1f}% {rc['trades']:4d}  "
              f"{rd['sharpe']:+7.3f} {rd['cagr']:+6.1f}% {rd['mdd']:5.1f}% {rd['trades']:4d}  "
              f"{d_sh:+5.3f} {d_cg:+6.1f}% {d_md:+5.1f}")

    print(f"\n  C200 wins: Sharpe {c200_wins_sh}/14, CAGR {c200_wins_cg}/14, MDD {c200_wins_md}/14")

    # ── Phase 2: Aligned common range + portfolio ──
    print(f"\n{'='*100}")
    print("PHASE 2: ALIGNED COMMON RANGE + PORTFOLIO")
    print(f"{'='*100}")

    print("\n  Loading data...")
    raw = {}
    for s in COINS:
        raw[s] = load_coin_raw(s)

    # Force start from FORCE_START if set, else use latest coin start
    FORCE_START_MS = 1672531200000  # 2023-01-01 00:00 UTC (0 = auto)
    if FORCE_START_MS > 0:
        latest_start = FORCE_START_MS
    else:
        latest_start = max(d["timestamps"][0] for d in raw.values())
    earliest_end = min(d["timestamps"][-1] for d in raw.values())

    coin_ranges = {}
    for s in COINS:
        ts = raw[s]["timestamps"]
        i0 = int(np.searchsorted(ts, latest_start, side='left'))
        i1 = int(np.searchsorted(ts, earliest_end, side='right'))
        coin_ranges[s] = (i0, i1)

    n_common = min(i1 - i0 for i0, i1 in coin_ranges.values())
    wi = min(WARMUP_DAYS * 6, n_common - 100)

    common_start = datetime.fromtimestamp(latest_start / 1000, tz=timezone.utc)
    common_end = datetime.fromtimestamp(earliest_end / 1000, tz=timezone.utc)
    print(f"  Common range: {common_start:%Y-%m-%d} → {common_end:%Y-%m-%d}")
    print(f"  Bars: {n_common}, Analysis starts after bar {wi}")

    # Per-coin on common range
    K = len(COINS)
    per_coin_cash = CASH

    navs = {cname: {} for cname in CONFIGS}

    print(f"\n  {'Coin':>10s}  "
          f"{'C200 Sh':>7s} {'CAGR':>7s} {'MDD':>6s}  "
          f"{'D120 Sh':>7s} {'CAGR':>7s} {'MDD':>6s}  "
          f"{'ΔSh':>6s} {'ΔMDD':>6s}")
    print("  " + "-" * 75)

    c200_wins_common = 0

    for s in COINS:
        d = raw[s]
        i0 = coin_ranges[s][0]
        i1 = i0 + n_common

        at_full = _atr(d["hi"], d["lo"], d["cl"], ATR_P)
        vd_full = _vdo(d["cl"], d["hi"], d["lo"], d["vo"], d["tb"], VDO_F, VDO_S)

        for cname, cfg in CONFIGS.items():
            ef_full = _ema(d["cl"], cfg["fast"]); es_full = _ema(d["cl"], cfg["slow"])
            nav_arr = sim_nav_series(
                d["cl"][i0:i1], ef_full[i0:i1], es_full[i0:i1],
                at_full[i0:i1], vd_full[i0:i1], wi, per_coin_cash, cfg["trail"])
            navs[cname][s] = nav_arr

        mc = metrics_from_navs(navs["C200"][s], wi)
        md = metrics_from_navs(navs["D120"][s], wi)
        d_sh = mc["sharpe"] - md["sharpe"]
        d_md = mc["mdd"] - md["mdd"]
        if d_sh > 0: c200_wins_common += 1

        print(f"  {s:>10s}  "
              f"{mc['sharpe']:+7.3f} {mc['cagr']:+6.1f}% {mc['mdd']:5.1f}%  "
              f"{md['sharpe']:+7.3f} {md['cagr']:+6.1f}% {md['mdd']:5.1f}%  "
              f"{d_sh:+5.3f} {d_md:+5.1f}")

    print(f"\n  C200 wins (common range): {c200_wins_common}/14 Sharpe")

    # Portfolio
    print(f"\n  Portfolio (equal-weight, common range):")

    combos = []
    for cname in CONFIGS:
        # 14-coin
        port_all = sum(navs[cname][s] for s in COINS)
        # 5 large-cap
        port_lc = sum(navs[cname][s] for s in LARGE_CAP)
        # BTC only (scaled to same total capital)
        btc_scaled = navs[cname]["BTCUSDT"] * K
        combos.append((f"BTC-only {CONFIGS[cname]['label']}", btc_scaled))
        combos.append((f"5-LC {CONFIGS[cname]['label']}", port_lc))
        combos.append((f"14-coin {CONFIGS[cname]['label']}", port_all))

    print(f"  {'Portfolio':>25s}  {'Sharpe':>7s}  {'CAGR':>7s}  {'MDD':>6s}  {'Calmar':>7s}")
    print("  " + "-" * 60)

    for label, nav_arr in combos:
        m = metrics_from_navs(nav_arr, wi)
        print(f"  {label:>25s}  {m['sharpe']:+7.3f}  {m['cagr']:+6.1f}%  {m['mdd']:5.1f}%  {m['calmar']:+7.3f}")

    # ── Phase 3: Buy & Hold comparison ──
    print(f"\n{'='*100}")
    print("PHASE 3: vs BUY & HOLD (common range)")
    print(f"{'='*100}")

    print(f"\n  {'Coin':>10s}  {'B&H CAGR':>9s}  {'C200 CAGR':>10s}  {'D120 CAGR':>10s}  {'C200>BH':>8s}  {'D120>BH':>8s}")
    print("  " + "-" * 65)

    c200_beats_bh = 0; d120_beats_bh = 0

    for s in COINS:
        d = raw[s]
        i0 = coin_ranges[s][0]
        i1 = i0 + n_common
        cl_c = d["cl"][i0:i1]

        # Buy & Hold
        bh_nav = np.full(n_common, per_coin_cash)
        bh_nav = per_coin_cash * cl_c / cl_c[0]
        m_bh = metrics_from_navs(bh_nav, wi)

        mc = metrics_from_navs(navs["C200"][s], wi)
        md = metrics_from_navs(navs["D120"][s], wi)

        c200_better = mc["cagr"] > m_bh["cagr"]
        d120_better = md["cagr"] > m_bh["cagr"]
        if c200_better: c200_beats_bh += 1
        if d120_better: d120_beats_bh += 1

        print(f"  {s:>10s}  {m_bh['cagr']:+8.1f}%  {mc['cagr']:+9.1f}%  {md['cagr']:+9.1f}%  "
              f"{'YES' if c200_better else 'no':>8s}  {'YES' if d120_better else 'no':>8s}")

    print(f"\n  Beats Buy&Hold: C200 = {c200_beats_bh}/14, D120 = {d120_beats_bh}/14")

    el = time.time() - t_start
    print(f"\n  Total time: {el:.0f}s ({el/60:.1f} min)")

    # Save
    OUTDIR.mkdir(parents=True, exist_ok=True)
    output = {
        "configs": {k: v["label"] for k, v in CONFIGS.items()},
        "phase1_per_coin": {s: {
            "C200_sharpe": coin_results[s]["C200"]["sharpe"],
            "D120_sharpe": coin_results[s]["D120"]["sharpe"],
            "d_sharpe": round(coin_results[s]["d_sh"], 4),
        } for s in COINS},
        "phase1_wins": {"sharpe": c200_wins_sh, "cagr": c200_wins_cg, "mdd": c200_wins_md},
    }
    outfile = OUTDIR / "multicoin_200v120.json"
    with open(outfile, "w") as f:
        json.dump(output, f, indent=2)
    print(f"  Saved: {outfile}")
    print("=" * 100)
