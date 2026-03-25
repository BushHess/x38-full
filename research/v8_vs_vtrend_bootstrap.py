#!/usr/bin/env python3
"""V8 Apex vs VTREND: Paired Bootstrap Comparison (2000 paths).

Runs V8 Apex (original parameters, original cost ~31 bps RT) and
VTREND (harsh cost 50 bps RT) on the same 2000 block-bootstrap paths.

Paired comparison of CAGR, MDD, Sharpe, Calmar.

V8 Apex profile parameters:
  D1 regime: EMA50/200 with hysteresis (confirm=2, off=4)
  Entry gates: VDO > 0.004, close > HMA(55) OR RSI < 30
  Sizing: vol-target 0.85/vol_ann, aggression=0.85, VDO confidence scaling
  Exits: trailing 3.5x ATR (activate at 5%, tighten to 2.5x at 20%),
         fixed stop 15%, emergency DD 28%
  Overlays: vol brake (ATR/close > 3.5% → 0.40x), caution mult 0.50
"""

from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from v10.core.data import DataFeed
from v10.core.types import SCENARIOS
from strategies.vtrend.strategy import (
    _ema as vt_ema,
    _atr as vt_atr,
    _vdo as vt_vdo,
)

# ── Shared constants ────────────────────────────────────────────────

DATA   = str(ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv")
COST   = SCENARIOS["harsh"]
CPS    = COST.per_side_bps / 10_000.0   # 0.0025

START  = "2019-01-01"
END    = "2026-02-20"
WARMUP = 365
CASH   = 10_000.0

N_BOOT = 2000
BLKSZ  = 60
SEED   = 42

ANN = math.sqrt(6.0 * 365.25)

# ── VTREND params ───────────────────────────────────────────────────

VT_SLOW  = 120
VT_FAST  = 30
VT_TRAIL = 3.0
VT_VDO_T = 0.0
VT_ATR_P = 14
VT_VDO_F = 12
VT_VDO_S = 28

# ── V8 Apex params (exact from V8ApexConfig + apex profile) ────────

# D1 regime
V8_D1_EMA_F = 50
V8_D1_EMA_S = 200
V8_CONFIRM  = 2
V8_OFF      = 4

# H4 VDO
V8_VDR_F    = 12
V8_VDR_S    = 28
V8_VDO_E    = 0.004
V8_VDO_SC   = 0.016

# H4 Momentum
V8_HMA_P    = 55
V8_ROC_P    = 8
V8_ACCEL_SM = 3

# H4 Volatility
V8_ATR_F    = 14
V8_ATR_S    = 50
V8_COMP_R   = 0.75

# H4 RSI
V8_RSI_P    = 14
V8_RSI_OB   = 75.0
V8_RSI_OS   = 30.0

# Entry
V8_MAX_EX   = 1.0
V8_VOL_TGT  = 0.85
V8_MAX_ADD  = 0.35
V8_AGG      = 0.85
V8_E_COOL   = 3
V8_X_COOL   = 3
V8_C_BOOST  = 1.0
V8_CAUT_M   = 0.50
V8_MIN_TGT  = 0.05

# Exit
V8_TR_ATR   = 3.5
V8_TR_ACT   = 0.05
V8_TR_TIGHT = 2.5
V8_TR_T_PCT = 0.20
V8_FX_STOP  = 0.15
V8_EM_DD    = 0.28
V8_EM_COOL  = 12

# Vol brake
V8_VB_R     = 0.035
V8_VB_M     = 0.40

# V8 cost model (original: spread=5bps, slip=3bps, fee=0.10%)
V8_BUY_PX   = (1 + 5.0 / 20000) * (1 + 3.0 / 10000)            # fill price mult
V8_BUY_COST = V8_BUY_PX * (1 + 0.001)                            # total cost mult
V8_SELL_PX   = (1 - 5.0 / 20000) * (1 - 3.0 / 10000)            # fill price mult
V8_SELL_PROC = V8_SELL_PX * (1 - 0.001)                           # net proceeds mult

# D1 regime enum
_RK_ON  = 0
_CAUT   = 1
_RK_OFF = 2


# ═══════════════════════════════════════════════════════════════════
# Data loading & bootstrap path generation
# ═══════════════════════════════════════════════════════════════════

def load_arrays():
    feed = DataFeed(DATA, start=START, end=END, warmup_days=WARMUP)
    h4 = feed.h4_bars
    n  = len(h4)
    cl = np.array([b.close for b in h4], dtype=np.float64)
    hi = np.array([b.high  for b in h4], dtype=np.float64)
    lo = np.array([b.low   for b in h4], dtype=np.float64)
    vo = np.array([b.volume for b in h4], dtype=np.float64)
    tb = np.array([b.taker_buy_base_vol for b in h4], dtype=np.float64)
    wi = 0
    if feed.report_start_ms is not None:
        for i, b in enumerate(h4):
            if b.close_time >= feed.report_start_ms:
                wi = i
                break
    return cl, hi, lo, vo, tb, wi, n


def make_ratios(cl, hi, lo, vo, tb):
    pc = cl[:-1]
    return cl[1:] / pc, hi[1:] / pc, lo[1:] / pc, vo[1:].copy(), tb[1:].copy()


def gen_path(cr, hr, lr, vol, tb, n_trans, blksz, p0, rng):
    n_blk = math.ceil(n_trans / blksz)
    mx = len(cr) - blksz
    if mx <= 0:
        idx = np.arange(min(n_trans, len(cr)))
    else:
        starts = rng.integers(0, mx + 1, size=n_blk)
        idx = np.concatenate([np.arange(s, s + blksz) for s in starts])[:n_trans]
    c = np.empty(len(idx) + 1, dtype=np.float64)
    c[0] = p0
    c[1:] = p0 * np.cumprod(cr[idx])
    h = np.empty_like(c); l = np.empty_like(c)
    v = np.empty_like(c); t = np.empty_like(c)
    h[0] = p0 * 1.002;  l[0] = p0 * 0.998
    v[0] = vol[idx[0]];  t[0] = tb[idx[0]]
    h[1:] = c[:-1] * hr[idx];  l[1:] = c[:-1] * lr[idx]
    v[1:] = vol[idx];          t[1:] = tb[idx]
    np.maximum(h, c, out=h);   np.minimum(l, c, out=l)
    return c, h, l, v, t


# ═══════════════════════════════════════════════════════════════════
# V8 indicator helpers (numpy, EMA-based — same as v8_apex.py)
# ═══════════════════════════════════════════════════════════════════

def _ema(a, p):
    """Standard EMA: alpha = 2/(p+1)."""
    alpha = 2.0 / (p + 1)
    out = np.empty(len(a), dtype=np.float64)
    out[0] = a[0]
    for i in range(1, len(a)):
        out[i] = alpha * a[i] + (1 - alpha) * out[i - 1]
    return out


def _wma(a, p):
    """Weighted Moving Average (vectorized)."""
    n = len(a)
    out = np.full(n, np.nan)
    if n < p:
        return out
    w = np.arange(1, p + 1, dtype=np.float64)
    ws = w.sum()
    windows = sliding_window_view(a, p)
    out[p - 1:] = windows @ w / ws
    return out


def _hma(a, p):
    """Hull Moving Average — minimal lag trend indicator."""
    half = max(p // 2, 1)
    sq = max(int(math.sqrt(p)), 1)
    return _wma(2.0 * _wma(a, half) - _wma(a, p), sq)


def _rsi(c, p):
    """RSI using standard EMA smoothing (ewm_span method, matches V8ApexStrategy)."""
    delta = np.diff(c, prepend=c[0])
    g = np.where(delta > 0, delta, 0.0)
    l_ = np.where(delta < 0, -delta, 0.0)
    ag = _ema(g, p)
    al = _ema(l_, p)
    rs = np.where(al > 1e-12, ag / al, 100.0)
    return 100.0 - 100.0 / (1.0 + rs)


def _atr_v8(h, lo, c, p):
    """ATR using standard EMA (V8 implementation — NOT Wilder)."""
    pc = np.roll(c, 1)
    pc[0] = c[0]
    tr = np.maximum(h - lo, np.maximum(np.abs(h - pc), np.abs(lo - pc)))
    return _ema(tr, p)


# ═══════════════════════════════════════════════════════════════════
# V8 D1 regime & vol computation
# ═══════════════════════════════════════════════════════════════════

def aggregate_h4_to_d1(cl, hi, lo):
    """Aggregate H4 bars to D1 (groups of 6). Returns (close, high, low)."""
    n_full = (len(cl) // 6) * 6
    if n_full == 0:
        return np.array([]), np.array([]), np.array([])
    c6 = cl[:n_full].reshape(-1, 6)
    h6 = hi[:n_full].reshape(-1, 6)
    l6 = lo[:n_full].reshape(-1, 6)
    return c6[:, -1], h6.max(axis=1), l6.min(axis=1)


def compute_d1_regime(d1_cl):
    """D1 regime with hysteresis (V8ApexStrategy._compute_regime)."""
    n = len(d1_cl)
    ef = _ema(d1_cl, V8_D1_EMA_F)
    es = _ema(d1_cl, V8_D1_EMA_S)
    regimes = np.full(n, _RK_OFF, dtype=np.int8)
    above = below = 0
    cur = _RK_OFF
    for i in range(n):
        if d1_cl[i] > es[i]:
            above = min(above + 1, V8_CONFIRM + 2)
            below = 0
        else:
            below = min(below + 1, V8_OFF + 2)
            above = 0
        if below >= V8_OFF:
            cur = _RK_OFF
        elif above >= V8_CONFIRM:
            cur = _RK_ON if ef[i] > es[i] else _CAUT
        regimes[i] = cur
    return regimes


def compute_d1_vol_ann(d1_cl):
    """Annualized vol from D1 log returns (V8ApexStrategy.on_init method)."""
    lr = np.diff(np.log(np.maximum(d1_cl, 1e-10)), prepend=0.0)
    lr[0] = 0.0
    em = _ema(lr, 30)
    em2 = _ema(lr ** 2, 30)
    sig = np.sqrt(np.maximum(em2 - em ** 2, 0.0))
    return np.clip(sig * math.sqrt(365), 0.10, 3.00)


# ═══════════════════════════════════════════════════════════════════
# V8 Apex fast simulation
# ═══════════════════════════════════════════════════════════════════

def sim_v8(cl, hi, lo, vo, tb, wi):
    """Run V8 Apex on H4 arrays with original parameters + original cost.

    Returns metrics dict: {cagr, mdd, sharpe, calmar, trades}.
    """
    n = len(cl)

    # ── Pre-compute H4 indicators ──
    safe_vo = np.where(vo > 0, vo, 1.0)
    vdr = np.clip(tb / safe_vo, 0.0, 1.0)
    h4_vdo = _ema(vdr, V8_VDR_F) - _ema(vdr, V8_VDR_S)
    h4_hma = _hma(cl, V8_HMA_P)
    h4_rsi = _rsi(cl, V8_RSI_P)
    h4_atr_f = _atr_v8(hi, lo, cl, V8_ATR_F)
    h4_atr_s = _atr_v8(hi, lo, cl, V8_ATR_S)

    prev_cl = np.roll(cl, V8_ROC_P)
    prev_cl[:V8_ROC_P] = cl[:V8_ROC_P]
    roc = np.where(prev_cl > 0, (cl - prev_cl) / prev_cl, 0.0)
    h4_accel = _ema(np.diff(roc, prepend=0.0), V8_ACCEL_SM)

    # ── Pre-compute D1 indicators ──
    d1_cl, _, _ = aggregate_h4_to_d1(cl, hi, lo)
    n_d1 = len(d1_cl)

    if n_d1 > 0:
        d1_reg = compute_d1_regime(d1_cl)
        d1_va  = compute_d1_vol_ann(d1_cl)
    else:
        d1_reg = np.array([], dtype=np.int8)
        d1_va  = np.array([])

    # ── Portfolio state ──
    cash = CASH
    bq   = 0.0        # btc qty
    epa  = 0.0        # entry price avg (weighted)
    ppk  = 0.0        # peak price since entry
    ppf  = 0.0        # peak profit since entry
    pen  = 0.0        # position entry NAV
    lai  = -999       # last add bar index
    lei  = -999       # last exit bar index
    ecl  = 0          # emergency DD cooldown remaining
    nt   = 0          # trade count

    navs = []

    for i in range(n):
        mid = cl[i]
        if mid <= 0:
            if i >= wi:
                navs.append(cash)
            continue

        # D1 index (latest completed D1 bar, no lookahead)
        d1i = (i + 1) // 6 - 1
        if 0 <= d1i < n_d1:
            regime  = int(d1_reg[d1i])
            vol_ann = float(d1_va[d1i])
        else:
            regime  = _RK_OFF
            vol_ann = 0.80

        atr_f = h4_atr_f[i]
        in_pos = bq > 1e-8

        # Decrement emergency cooldown
        if ecl > 0:
            ecl -= 1

        # ── EXIT CHECKS ──────────────────────────────────────────
        if in_pos:
            nav = cash + bq * mid
            ppk = max(ppk, mid)
            if epa > 0:
                ppf = max(ppf, (mid - epa) / epa)

            # 1. Emergency DD (ref: position_entry_nav)
            if pen > 0 and (1.0 - nav / pen) >= V8_EM_DD:
                cash += bq * mid * V8_SELL_PROC
                bq = 0.0; nt += 1; lei = i
                epa = 0.0; ppk = 0.0; ppf = 0.0; pen = 0.0
                ecl = V8_EM_COOL
                in_pos = False

            # 2a. Trailing stop (peak_profit >= activate_pct)
            if in_pos and epa > 0 and ppf >= V8_TR_ACT:
                mult = V8_TR_TIGHT if ppf >= V8_TR_T_PCT else V8_TR_ATR
                if mid <= ppk - mult * atr_f:
                    cash += bq * mid * V8_SELL_PROC
                    bq = 0.0; nt += 1; lei = i
                    epa = 0.0; ppk = 0.0; ppf = 0.0; pen = 0.0
                    in_pos = False

            # 2b. Fixed stop (before trailing activates)
            elif in_pos and epa > 0 and mid <= epa * (1 - V8_FX_STOP):
                cash += bq * mid * V8_SELL_PROC
                bq = 0.0; nt += 1; lei = i
                epa = 0.0; ppk = 0.0; ppf = 0.0; pen = 0.0
                in_pos = False

        # ── Record equity ─────────────────────────────────────────
        nav = cash + bq * mid
        if i >= wi:
            navs.append(nav)

        # ── ENTRY CHECKS ─────────────────────────────────────────
        if regime == _RK_OFF:
            continue
        if ecl > 0:
            continue
        if i - lai < V8_E_COOL:
            continue
        if i - lei < V8_X_COOL:
            continue

        # VDO gate
        vdo_v = h4_vdo[i]
        if math.isnan(vdo_v) or vdo_v <= V8_VDO_E:
            continue

        # HMA trend OR RSI oversold
        hma_v = h4_hma[i]
        rsi_v = h4_rsi[i]
        above_hma = not math.isnan(hma_v) and mid > hma_v
        oversold  = not math.isnan(rsi_v) and rsi_v < V8_RSI_OS
        if not above_hma and not oversold:
            continue

        # Target exposure (vol-target sized)
        base = min(V8_MAX_EX, V8_VOL_TGT / vol_ann) if vol_ann > 0 else V8_MAX_EX
        if regime == _CAUT:
            base *= V8_CAUT_M

        # Vol brake
        if mid > 0 and atr_f / mid > V8_VB_R:
            base *= V8_VB_M

        base = min(base, V8_MAX_EX)
        nav = cash + bq * mid
        if nav <= 0:
            continue
        cur_ex = (bq * mid) / nav
        gap = base - cur_ex
        if gap < V8_MIN_TGT:
            continue

        # Sizing: VDO confidence * aggression * gap
        vc = max(0.3, min(2.0, vdo_v / max(V8_VDO_SC, 0.001)))
        add_sz = gap * V8_AGG * vc

        # Acceleration bonus
        accel_v = h4_accel[i]
        if not math.isnan(accel_v) and accel_v >= 0:
            add_sz *= 1.15

        # Compression boost
        atr_s_v = h4_atr_s[i]
        if atr_s_v > 0 and (atr_f / atr_s_v) < V8_COMP_R:
            add_sz *= V8_C_BOOST

        # RSI modulation
        if not math.isnan(rsi_v):
            if rsi_v > V8_RSI_OB:
                add_sz *= 0.5
            elif rsi_v < V8_RSI_OS:
                add_sz *= 1.3

        # CAUTION reduction
        if regime == _CAUT:
            add_sz *= V8_CAUT_M

        add_sz = min(add_sz, V8_MAX_ADD, gap)
        if add_sz < 0.01:
            continue

        # Execute buy
        desired = min(cur_ex + add_sz, base)
        tgt_val = desired * nav
        diff = tgt_val - bq * mid

        if diff > 1.0:
            qty = diff / (mid * V8_BUY_COST)
            cost = qty * mid * V8_BUY_COST
            if cost > cash + 0.01:
                qty = cash / (mid * V8_BUY_COST)
                cost = qty * mid * V8_BUY_COST
            if qty > 1e-8 and cost <= cash + 0.01:
                fp = mid * V8_BUY_PX
                if bq < 1e-8:
                    pen = nav
                    epa = fp
                    ppk = mid
                    ppf = 0.0
                else:
                    epa = (bq * epa + qty * fp) / (bq + qty)
                    ppk = max(ppk, mid)
                cash -= cost
                bq += qty
                lai = i

    # Force close at end
    if bq > 1e-8:
        cash += bq * cl[-1] * V8_SELL_PROC
        bq = 0.0
        nt += 1
        if navs:
            navs[-1] = cash

    return _metrics(navs, nt)


# ═══════════════════════════════════════════════════════════════════
# VTREND simulation (same logic as position_sizing.py)
# ═══════════════════════════════════════════════════════════════════

def compute_vt_ind(cl, hi, lo, vo, tb):
    """Compute VTREND indicators."""
    return (
        vt_ema(cl, VT_FAST),
        vt_ema(cl, VT_SLOW),
        vt_atr(hi, lo, cl, VT_ATR_P),
        vt_vdo(cl, hi, lo, vo, tb, VT_VDO_F, VT_VDO_S),
    )


def sim_vtrend(cl, ef, es, at, vd, wi, frac=1.0):
    """VTREND with fixed fraction sizing. Harsh cost (50 bps RT)."""
    n = len(cl)
    cash = CASH
    bq = 0.0
    inp = False
    pk = 0.0
    pe = px = False
    nt = 0
    entry_f = frac

    navs = []

    for i in range(n):
        p = cl[i]

        # Fill pending
        if i > 0:
            fp = cl[i - 1]
            if pe:
                pe = False
                nav_now = cash
                invest = entry_f * nav_now
                if invest >= 1.0 and nav_now >= 1.0:
                    bq = invest / (fp * (1.0 + CPS))
                    cash -= invest
                    inp = True
                    pk = p
            elif px:
                cash += bq * fp * (1.0 - CPS)
                bq = 0.0
                inp = False
                pk = 0.0
                nt += 1
                px = False

        nav = cash + bq * p
        if i >= wi:
            navs.append(nav)

        a_val = at[i]
        if math.isnan(a_val) or math.isnan(ef[i]) or math.isnan(es[i]):
            continue

        if not inp:
            if ef[i] > es[i] and vd[i] > VT_VDO_T:
                pe = True
        else:
            pk = max(pk, p)
            if p < pk - VT_TRAIL * a_val:
                px = True
            elif ef[i] < es[i]:
                px = True

    # Force close
    if inp and bq > 0:
        cash += bq * cl[-1] * (1.0 - CPS)
        bq = 0.0
        nt += 1
        if navs:
            navs[-1] = cash

    return _metrics(navs, nt)


# ═══════════════════════════════════════════════════════════════════
# Metrics computation
# ═══════════════════════════════════════════════════════════════════

def _metrics(navs, nt):
    if len(navs) < 2 or navs[0] <= 0:
        return {"cagr": -100.0, "mdd": 100.0, "sharpe": 0.0, "calmar": 0.0, "trades": 0}
    na = np.array(navs, dtype=np.float64)
    tr = na[-1] / na[0] - 1.0
    yrs = (len(na) - 1) / (6.0 * 365.25)
    cagr = ((1 + tr) ** (1 / yrs) - 1) * 100 if yrs > 0 and tr > -1 else -100.0
    peak = np.maximum.accumulate(na)
    dd = (peak - na) / peak * 100
    mdd = float(dd.max())
    rets = np.diff(na) / na[:-1]
    std = float(np.std(rets, ddof=0))
    sharpe = float(np.mean(rets)) / std * ANN if std > 1e-12 else 0.0
    calmar = cagr / mdd if mdd > 0.01 else 0.0
    return {"cagr": cagr, "mdd": mdd, "sharpe": sharpe, "calmar": calmar, "trades": nt}


# ═══════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════

def _fmt(r):
    return (f"CAGR={r['cagr']:+.1f}%  MDD={r['mdd']:.1f}%  "
            f"Sharpe={r['sharpe']:.3f}  Calmar={r['calmar']:.3f}  "
            f"Trades={r['trades']}")


if __name__ == "__main__":
    print("=" * 70)
    print("V8 APEX vs VTREND: PAIRED BOOTSTRAP COMPARISON")
    print("=" * 70)
    print(f"  Period : {START} → {END}   Warmup: {WARMUP}d")
    print(f"  V8 cost: ~{(1 - V8_SELL_PROC / V8_BUY_COST + 1) * 10000 / 2:.0f} bps RT "
          f"(spread=5, slip=3, fee=0.10%)")
    v8_rt = (V8_BUY_COST / V8_SELL_PROC - 1) * 10000
    print(f"  V8 effective round-trip: {v8_rt:.1f} bps")
    print(f"  VT cost: {COST.round_trip_bps:.0f} bps RT (harsh)")
    print(f"  Bootstrap: {N_BOOT} paths, block={BLKSZ}, seed={SEED}")

    print("\nLoading data...")
    cl, hi, lo, vo, tb, wi, n = load_arrays()
    print(f"  {n} H4 bars, warmup idx={wi}, trading={n - wi} bars")

    # ══════════════════════════════════════════════════════════════
    # REAL DATA PERFORMANCE
    # ══════════════════════════════════════════════════════════════

    print("\n" + "=" * 70)
    print("REAL DATA PERFORMANCE")
    print("=" * 70)

    r_v8 = sim_v8(cl, hi, lo, vo, tb, wi)
    print(f"\n  V8 Apex (original cost):  {_fmt(r_v8)}")

    ef, es, at, vd = compute_vt_ind(cl, hi, lo, vo, tb)
    r_vt1 = sim_vtrend(cl, ef, es, at, vd, wi, frac=1.0)
    r_vt3 = sim_vtrend(cl, ef, es, at, vd, wi, frac=0.30)

    print(f"  VTREND f=1.0 (harsh):     {_fmt(r_vt1)}")
    print(f"  VTREND f=0.30 (harsh):    {_fmt(r_vt3)}")

    # ══════════════════════════════════════════════════════════════
    # BOOTSTRAP: 2000 PATHS
    # ══════════════════════════════════════════════════════════════

    print("\n" + "=" * 70)
    print(f"BOOTSTRAP: {N_BOOT} PATHS")
    print("=" * 70)

    cr, hr, lr, vol, tbr = make_ratios(cl, hi, lo, vo, tb)
    n_trans = len(cl) - 1
    p0 = cl[0]
    rng = np.random.default_rng(SEED)

    mkeys = ["cagr", "mdd", "sharpe", "calmar", "trades"]
    labels = ["V8_Apex", "VT_f1.0", "VT_f0.3"]
    boot = {lab: {m: [] for m in mkeys} for lab in labels}

    t0 = time.time()
    for b in range(N_BOOT):
        if (b + 1) % 100 == 0 or b == 0:
            el = time.time() - t0
            rate = (b + 1) / el if el > 0 else 1
            eta = (N_BOOT - b - 1) / rate
            print(f"    {b+1:5d}/{N_BOOT}  ({el:.0f}s, ~{eta:.0f}s left)")

        c, h, l, v, t = gen_path(cr, hr, lr, vol, tbr, n_trans, BLKSZ, p0, rng)

        # V8
        r = sim_v8(c, h, l, v, t, wi)
        for m in mkeys:
            boot["V8_Apex"][m].append(r[m])

        # VTREND
        ef_b, es_b, at_b, vd_b = compute_vt_ind(c, h, l, v, t)

        r = sim_vtrend(c, ef_b, es_b, at_b, vd_b, wi, frac=1.0)
        for m in mkeys:
            boot["VT_f1.0"][m].append(r[m])

        r = sim_vtrend(c, ef_b, es_b, at_b, vd_b, wi, frac=0.30)
        for m in mkeys:
            boot["VT_f0.3"][m].append(r[m])

    el = time.time() - t0
    print(f"\n  Done: {el:.1f}s ({N_BOOT / el:.1f} paths/sec)")

    # Convert to numpy
    for lab in labels:
        for m in mkeys:
            boot[lab][m] = np.array(boot[lab][m])

    # ══════════════════════════════════════════════════════════════
    # BOOTSTRAP DISTRIBUTIONS
    # ══════════════════════════════════════════════════════════════

    print("\n" + "-" * 70)
    print("BOOTSTRAP DISTRIBUTIONS")
    print("-" * 70)

    for lab in labels:
        print(f"\n  ── {lab} ──")
        for m in ["cagr", "mdd", "sharpe", "calmar"]:
            a = boot[lab][m]
            p5, p25, p50, p75, p95 = np.percentile(a, [5, 25, 50, 75, 95])
            pgt0 = np.mean(a > 0) * 100 if m != "mdd" else np.nan
            extra = f"  P(>0)={pgt0:.1f}%" if m != "mdd" else ""
            print(f"    {m:7s}  med={p50:+8.2f}  "
                  f"[p5={p5:+7.2f}, p95={p95:+7.2f}]{extra}")

    # ══════════════════════════════════════════════════════════════
    # V8 APEX BOOTSTRAP SUMMARY
    # ══════════════════════════════════════════════════════════════

    print("\n" + "-" * 70)
    print("V8 APEX BOOTSTRAP SUMMARY")
    print("-" * 70)

    for m, fmt in [("cagr", "+.1f"), ("mdd", ".1f"),
                    ("sharpe", ".3f"), ("calmar", ".3f")]:
        a = boot["V8_Apex"][m]
        prefix = "P(CAGR>0)" if m == "cagr" else ""
        print(f"  Median {m:7s} = {np.median(a):{fmt}}", end="")
        if m == "cagr":
            print(f"    P(CAGR > 0) = {np.mean(a > 0) * 100:.1f}%")
        elif m == "mdd":
            print(f"    P(MDD < 30%) = {np.mean(a < 30) * 100:.1f}%")
        else:
            print()

    # ══════════════════════════════════════════════════════════════
    # PAIRED COMPARISONS
    # ══════════════════════════════════════════════════════════════

    print("\n" + "-" * 70)
    print("PAIRED COMPARISONS (same 2000 paths)")
    print("-" * 70)
    print("  P(V8 better) > 97.5% ≈ significant at α=0.05 (one-sided).\n")

    for vt_lab in ["VT_f1.0", "VT_f0.3"]:
        print(f"  ── V8 Apex vs {vt_lab} ──")

        for m, direction in [("cagr", "higher"), ("mdd", "lower"),
                              ("sharpe", "higher"), ("calmar", "higher")]:
            v8_a = boot["V8_Apex"][m]
            vt_a = boot[vt_lab][m]

            if direction == "lower":
                d = vt_a - v8_a   # positive = V8 has lower MDD
            else:
                d = v8_a - vt_a   # positive = V8 is higher

            p_v8 = np.mean(d > 0)
            ci = np.percentile(d, [2.5, 97.5])
            print(f"    Δ{m:7s}  mean={d.mean():+8.3f}  "
                  f"P(V8 {direction:6s})={p_v8 * 100:5.1f}%  "
                  f"95%CI=[{ci[0]:+.3f}, {ci[1]:+.3f}]")
        print()

    # ══════════════════════════════════════════════════════════════
    # REAL PERFORMANCE PERCENTILE IN BOOTSTRAP
    # ══════════════════════════════════════════════════════════════

    print("-" * 70)
    print("REAL PERFORMANCE PERCENTILE IN BOOTSTRAP")
    print("-" * 70)
    print("  (percentile = % of bootstrap paths with worse performance)\n")

    real_map = {"V8_Apex": r_v8, "VT_f1.0": r_vt1, "VT_f0.3": r_vt3}
    for lab in labels:
        rv = real_map[lab]
        print(f"  ── {lab} ──")
        for m in ["cagr", "mdd", "sharpe", "calmar"]:
            a = boot[lab][m]
            if m == "mdd":
                pctile = np.mean(a >= rv[m]) * 100   # lower is better
            else:
                pctile = np.mean(a <= rv[m]) * 100
            print(f"    {m:7s}  real={rv[m]:+8.2f}  percentile={pctile:.1f}%")
        print()

    # ══════════════════════════════════════════════════════════════
    # SAVE RESULTS
    # ══════════════════════════════════════════════════════════════

    outdir = Path(__file__).resolve().parent / "results"
    outdir.mkdir(exist_ok=True)

    output = {
        "config": {
            "n_boot": N_BOOT,
            "block_size": BLKSZ,
            "seed": SEED,
            "start": START,
            "end": END,
            "warmup_days": WARMUP,
            "v8_cost_rt_bps": round(v8_rt, 1),
            "vtrend_cost_rt_bps": COST.round_trip_bps,
        },
        "real_data": {
            "V8_Apex": {k: round(v, 4) for k, v in r_v8.items()},
            "VT_f1.0": {k: round(v, 4) for k, v in r_vt1.items()},
            "VT_f0.3": {k: round(v, 4) for k, v in r_vt3.items()},
        },
        "bootstrap": {},
        "paired": {},
        "percentiles": {},
    }

    for lab in labels:
        output["bootstrap"][lab] = {}
        for m in ["cagr", "mdd", "sharpe", "calmar"]:
            a = boot[lab][m]
            p5, p25, p50, p75, p95 = np.percentile(a, [5, 25, 50, 75, 95])
            output["bootstrap"][lab][m] = {
                "mean": round(float(a.mean()), 4),
                "median": round(float(p50), 4),
                "std": round(float(a.std()), 4),
                "p5": round(float(p5), 4),
                "p25": round(float(p25), 4),
                "p75": round(float(p75), 4),
                "p95": round(float(p95), 4),
                "p_positive": round(float(np.mean(a > 0)), 4),
            }

    for vt_lab in ["VT_f1.0", "VT_f0.3"]:
        key = f"V8_vs_{vt_lab}"
        output["paired"][key] = {}
        for m in ["cagr", "mdd", "sharpe", "calmar"]:
            v8_a = boot["V8_Apex"][m]
            vt_a = boot[vt_lab][m]
            d = (vt_a - v8_a) if m == "mdd" else (v8_a - vt_a)
            ci = np.percentile(d, [2.5, 97.5])
            output["paired"][key][m] = {
                "mean_diff": round(float(d.mean()), 4),
                "p_v8_better": round(float(np.mean(d > 0)), 4),
                "ci_2.5": round(float(ci[0]), 4),
                "ci_97.5": round(float(ci[1]), 4),
            }

    for lab in labels:
        rv = real_map[lab]
        output["percentiles"][lab] = {}
        for m in ["cagr", "mdd", "sharpe", "calmar"]:
            a = boot[lab][m]
            if m == "mdd":
                pctile = float(np.mean(a >= rv[m]) * 100)
            else:
                pctile = float(np.mean(a <= rv[m]) * 100)
            output["percentiles"][lab][m] = round(pctile, 1)

    outpath = outdir / "v8_vs_vtrend_bootstrap.json"
    with open(outpath, "w") as f:
        json.dump(output, f, indent=2, default=str)

    print(f"Results saved → {outpath}")
    print("\n" + "=" * 70)
    print("DONE")
    print("=" * 70)
