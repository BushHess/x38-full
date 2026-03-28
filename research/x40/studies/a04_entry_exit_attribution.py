"""A04 — Entry vs Exit Attribution Study.

Determines whether remaining alpha value lies in entry innovation
or exit innovation for PF0_E5_EMA21D1.

Three-part analysis:
  1. Entry-side IC — feature predictive content at entry vs forward returns
  2. Exit-side characterization — oracle exit analysis, path quality
  3. Counterfactual decomposition — vary entry/exit independently

Outputs (all in results/PF0_E5_EMA21D1/):
  a04_entry_feature_summary.csv
  a04_exit_feature_summary.csv
  a04_counterfactual_decomposition.csv
  a04_directional_research_advice.json

Reference: X40 spec v3 §13 (Study A04).
Prior work: X21 (entry IC=-0.039), X12-X19 (exit series), PF1_VC07 (conditional entry).
"""

from __future__ import annotations

import csv
import json
import math
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
from scipy import stats as sp_stats

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from research.x40.pf0_strategy import (  # noqa: E402
    _ema,
    _map_d1_regime,
    _robust_atr,
    _vdo,
    run_pf0_sim,
)
from v10.core.data import DataFeed  # noqa: E402

# ── Paths ────────────────────────────────────────────────────────────────

DATA_PATH = str(ROOT / "data" / "bars_btcusdt_2016_now_h1_4h_1d.csv")
RESULTS_DIR = ROOT / "research" / "x40" / "results" / "PF0_E5_EMA21D1"

# ── PF0 frozen constants ─────────────────────────────────────────────────

_SLOW = 120
_FAST = 30
_TRAIL_MULT = 3.0
_VDO_THR = 0.0
_D1_EMA = 21
_VDO_F, _VDO_S = 12, 28
_RATR_Q, _RATR_LB, _RATR_P = 0.90, 100, 20
_ANN = math.sqrt(2190.0)  # H4 annualization

# ── Study parameters ─────────────────────────────────────────────────────

HORIZONS = [1, 2, 4, 8, 16, 32]
N_SHUFFLE = 500
SEED = 42
COST = 0.001  # 10 bps/side = 20 bps RT
_LIVE_MS = int(datetime(2019, 1, 1, tzinfo=UTC).timestamp() * 1000)


# ── Data structures ──────────────────────────────────────────────────────


@dataclass
class Trade:
    idx: int
    signal_bar: int
    entry_bar: int
    exit_bar: int
    entry_price: float
    exit_price: float
    bars_held: int
    ret: float
    peak_close: float
    peak_bar: int


# ── Indicator helpers ────────────────────────────────────────────────────


def _rolling_std(series: np.ndarray, window: int) -> np.ndarray:
    """Rolling standard deviation (ddof=1)."""
    n = len(series)
    out = np.full(n, np.nan)
    cs = np.cumsum(series)
    cs2 = np.cumsum(series**2)
    for i in range(window - 1, n):
        s = cs[i] - (cs[i - window] if i >= window else 0.0)
        s2 = cs2[i] - (cs2[i - window] if i >= window else 0.0)
        mu = s / window
        var = max(0.0, s2 / window - mu * mu)
        if window > 1:
            var = var * window / (window - 1)
        out[i] = math.sqrt(var)
    return out


def _vol_ratio(close: np.ndarray, fast: int, slow: int) -> np.ndarray:
    sf = _rolling_std(close, fast)
    ss = _rolling_std(close, slow)
    return np.where(ss > 1e-12, sf / ss, np.nan)


def _range_pos(close: np.ndarray, high: np.ndarray, low: np.ndarray) -> np.ndarray:
    rng = high - low
    return np.where(rng > 1e-12, (close - low) / rng, 0.5)


def _d1_strength(h4ct: np.ndarray, d1c: np.ndarray,
                 d1_ema: np.ndarray, d1ct: np.ndarray) -> np.ndarray:
    """D1 regime strength (continuous) mapped to H4 grid."""
    out = np.zeros(len(h4ct))
    j = 0
    for i in range(len(h4ct)):
        while j + 1 < len(d1c) and d1ct[j + 1] < h4ct[i]:
            j += 1
        if d1ct[j] < h4ct[i] and d1_ema[j] > 0:
            out[i] = d1c[j] / d1_ema[j] - 1.0
    return out


# ── Trade reconstruction ─────────────────────────────────────────────────


def _reconstruct_trades(
    result, h4o: np.ndarray, h4c: np.ndarray, cost: float,
) -> list[Trade]:
    pos = result.all_positions
    trades: list[Trade] = []
    entry_bar = -1
    idx = 0
    for i in range(1, len(pos)):
        if int(pos[i - 1]) == 0 and int(pos[i]) == 1:
            entry_bar = i
        elif int(pos[i - 1]) == 1 and int(pos[i]) == 0 and entry_bar >= 0:
            seg = h4c[entry_bar:i]
            pk_off = int(np.argmax(seg))
            trades.append(Trade(
                idx=idx, signal_bar=entry_bar - 1, entry_bar=entry_bar,
                exit_bar=i, entry_price=float(h4o[entry_bar]),
                exit_price=float(h4o[i]), bars_held=i - entry_bar,
                ret=float((h4o[i] / h4o[entry_bar]) * (1 - cost) ** 2 - 1),
                peak_close=float(seg[pk_off]), peak_bar=entry_bar + pk_off,
            ))
            idx += 1
            entry_bar = -1
    return trades


# ── Qualifying bars & potential trades ───────────────────────────────────


def _find_qualifying(ema_f, ema_s, vdo, d1_reg, ratr, h4ct) -> list[int]:
    """All bars where PF0 entry conditions are met (during live period)."""
    bars: list[int] = []
    for i in range(1, len(ema_f)):
        if h4ct[i] < _LIVE_MS:
            continue
        if math.isnan(ema_f[i]) or math.isnan(ema_s[i]) or math.isnan(ratr[i]):
            continue
        if ema_f[i] > ema_s[i] and vdo[i] > _VDO_THR and d1_reg[i]:
            bars.append(i)
    return bars


def _sim_exit(sb: int, h4c, h4o, ema_f, ema_s, ratr, cost) -> dict | None:
    """Simulate PF0 exit logic from signal bar sb. Returns trade dict or None."""
    n = len(h4c)
    eb = sb + 1
    if eb >= n:
        return None
    ep = h4o[eb]
    peak = h4c[sb]
    pk_bar = sb
    for i in range(eb, n):
        if h4c[i] > peak:
            peak = h4c[i]
            pk_bar = i
        rv = ratr[i]
        if math.isnan(rv):
            continue
        if h4c[i] < peak - _TRAIL_MULT * rv or ema_f[i] < ema_s[i]:
            xb = i + 1
            if xb >= n:
                return None
            return {
                "signal_bar": sb, "entry_bar": eb, "exit_bar": xb,
                "ret": float((h4o[xb] / ep) * (1 - cost) ** 2 - 1),
                "bars_held": xb - eb, "peak_bar": pk_bar,
            }
    return None


def _precompute_potential(qual, h4c, h4o, ema_f, ema_s, ratr, cost) -> dict:
    pot: dict[int, dict] = {}
    for sb in qual:
        t = _sim_exit(sb, h4c, h4o, ema_f, ema_s, ratr, cost)
        if t is not None:
            pot[sb] = t
    return pot


# ── Equity-curve Sharpe ──────────────────────────────────────────────────


def _eq_sharpe(trade_dicts: list[dict], h4c, h4o, h4ct, cost) -> float:
    """NAV-based Sharpe from a list of non-overlapping trade dicts."""
    n = len(h4c)
    pos = np.zeros(n, dtype=np.int8)
    for t in trade_dicts:
        pos[t["entry_bar"]:t["exit_bar"]] = 1

    cash, btc = 1.0, 0.0
    navs = np.ones(n)
    for i in range(n):
        p = pos[i - 1] if i > 0 else 0
        c = pos[i]
        if p == 0 and c == 1:
            btc = cash * (1 - cost) / h4o[i]
            cash = 0.0
        elif p == 1 and c == 0:
            cash = btc * h4o[i] * (1 - cost)
            btc = 0.0
        navs[i] = cash + btc * h4c[i]

    live = navs[h4ct >= _LIVE_MS]
    if len(live) < 2:
        return 0.0
    rets = np.diff(live) / live[:-1]
    s = float(np.std(rets, ddof=0))
    return float(np.mean(rets) / s * _ANN) if s > 1e-12 else 0.0


# ── Part 1: Entry IC ────────────────────────────────────────────────────


def _entry_ic(trades, h4c, h4o, ema_f, ema_s, ratr, vdo,
              d1s, volr, rpos, tkr) -> list[list]:
    n = len(h4c)
    feat: dict[str, list[float]] = {
        "ema_spread": [], "vdo_value": [], "ratr_norm": [],
        "d1_regime_str": [], "vol_ratio_5_20": [],
        "range_pos": [], "taker_ratio": [],
    }
    fwd: dict[int, list[float]] = {h: [] for h in HORIZONS}
    trets: list[float] = []

    for t in trades:
        sb = t.signal_bar
        es = ema_s[sb]
        feat["ema_spread"].append((ema_f[sb] - es) / es if es > 0 else 0.0)
        feat["vdo_value"].append(float(vdo[sb]))
        feat["ratr_norm"].append(
            float(ratr[sb] / h4c[sb])
            if not math.isnan(ratr[sb]) and h4c[sb] > 0 else 0.0,
        )
        feat["d1_regime_str"].append(float(d1s[sb]))
        feat["vol_ratio_5_20"].append(
            float(volr[sb]) if not math.isnan(volr[sb]) else 1.0,
        )
        feat["range_pos"].append(float(rpos[sb]))
        feat["taker_ratio"].append(float(tkr[sb]))

        ep = h4o[t.entry_bar]
        for h in HORIZONS:
            j = t.entry_bar + h
            fwd[h].append(h4c[j] / ep - 1 if j < n else np.nan)
        trets.append(t.ret)

    rows: list[list] = []
    tr = np.array(trets)
    for fname, fvals in feat.items():
        fv = np.array(fvals)
        mask = ~np.isnan(fv)
        if mask.sum() > 10:
            ic, pv = sp_stats.spearmanr(fv[mask], tr[mask])
            rows.append([fname, "trade_return", round(ic, 4), round(pv, 4),
                         int(mask.sum())])
        for h in HORIZONS:
            fr = np.array(fwd[h])
            m2 = mask & ~np.isnan(fr)
            if m2.sum() > 10:
                ic, pv = sp_stats.spearmanr(fv[m2], fr[m2])
                rows.append([fname, f"fwd_{h}bar", round(ic, 4), round(pv, 4),
                             int(m2.sum())])

    print("  Entry IC vs trade_return:")
    for r in rows:
        if r[1] == "trade_return":
            sig = " *" if abs(float(r[3])) < 0.10 else ""
            print(f"    {r[0]:20s}: IC={r[2]:+.4f}  p={r[3]:.4f}{sig}")
    return rows


# ── Part 2: Exit characterization ───────────────────────────────────────


def _exit_analysis(trades: list[Trade], h4c, h4o, cost) -> list[list]:
    n = len(h4o)
    oracle_rets: list[float] = []
    actual_rets: list[float] = []
    leftovers: list[float] = []
    pct_caps: list[float] = []

    for t in trades:
        actual_rets.append(t.ret)
        oxb = min(t.peak_bar + 1, n - 1)
        oxb = max(oxb, t.entry_bar + 1)
        oret = float((h4o[oxb] / t.entry_price) * (1 - cost) ** 2 - 1)
        oracle_rets.append(oret)
        leftovers.append(oret - t.ret)
        pct_caps.append(max(0.0, t.ret / oret) if oret > 0 else 1.0)

    def _f(v: float) -> str:
        return f"{v:.4f}"

    rows: list[list] = []
    rows.append(["oracle_mean_return", _f(np.mean(oracle_rets)),
                 "Mean return if exiting at peak"])
    rows.append(["actual_mean_return", _f(np.mean(actual_rets)),
                 "Mean actual trade return"])
    rows.append(["mean_leftover", _f(np.mean(leftovers)),
                 "Mean (oracle - actual) per trade"])
    rows.append(["median_leftover", _f(np.median(leftovers)),
                 "Median leftover"])
    rows.append(["pct_oracle_captured", _f(np.mean(pct_caps)),
                 "Fraction of oracle captured (where oracle > 0)"])

    # Winners vs losers
    w_lo = [leftovers[t.idx] for t in trades if t.ret > 0]
    l_lo = [leftovers[t.idx] for t in trades if t.ret <= 0]
    rows.append(["winner_mean_leftover", _f(np.mean(w_lo) if w_lo else 0),
                 f"Leftover for {len(w_lo)} winners"])
    rows.append(["loser_mean_leftover", _f(np.mean(l_lo) if l_lo else 0),
                 f"Leftover for {len(l_lo)} losers"])

    # Holding period
    bh = np.array([t.bars_held for t in trades])
    rows.append(["median_bars_held", f"{np.median(bh):.0f}", "Median H4 bars"])
    rows.append(["mean_bars_held", f"{np.mean(bh):.1f}", "Mean H4 bars"])
    ic_bh, pv_bh = sp_stats.spearmanr(bh, np.array(actual_rets))
    rows.append(["ic_bars_held_vs_return", _f(ic_bh),
                 f"Spearman IC, p={pv_bh:.4f}"])

    # Peak timing
    pf = [(t.peak_bar - t.entry_bar) / t.bars_held
          for t in trades if t.bars_held > 0]
    rows.append(["mean_peak_fraction", _f(np.mean(pf)),
                 "Fraction through trade where peak occurs"])

    # Mid-trade path IC
    mid_ur, mid_dd, mid_rem = [], [], []
    for t in trades:
        mb = t.entry_bar + t.bars_held // 2
        if mb >= len(h4c) or mb >= t.exit_bar:
            continue
        ur = h4c[mb] / t.entry_price - 1
        pk = float(np.max(h4c[t.entry_bar : mb + 1]))
        dd = (pk - h4c[mb]) / pk if pk > 0 else 0.0
        mid_ur.append(ur)
        mid_dd.append(dd)
        mid_rem.append(t.ret - ur)

    if len(mid_ur) > 10:
        ic_ur, pv_ur = sp_stats.spearmanr(mid_ur, mid_rem)
        ic_dd, pv_dd = sp_stats.spearmanr(mid_dd, mid_rem)
        rows.append(["ic_midtrade_unreal_vs_remain", _f(ic_ur),
                     f"Mid-trade unrealized vs remaining, p={pv_ur:.4f}"])
        rows.append(["ic_midtrade_dd_vs_remain", _f(ic_dd),
                     f"Mid-trade drawdown vs remaining, p={pv_dd:.4f}"])

    print("  Exit analysis:")
    for r in rows:
        print(f"    {r[0]:35s} = {r[1]:>10s}  ({r[2]})")
    return rows


# ── Part 3: Counterfactual decomposition ─────────────────────────────────


def _counterfactual(
    trades: list[Trade], pot: dict, qual: list[int],
    h4c, h4o, h4ct, cost: float, n_bars: int,
) -> list[list]:
    rng = np.random.default_rng(SEED)
    nt = len(trades)
    n = n_bars

    # C0: Actual
    c0d = [{"entry_bar": t.entry_bar, "exit_bar": t.exit_bar} for t in trades]
    c0_sh = _eq_sharpe(c0d, h4c, h4o, h4ct, cost)
    c0_mr = float(np.mean([t.ret for t in trades]))
    c0_wr = sum(1 for t in trades if t.ret > 0) / nt
    print(f"  C0 actual:        Sh={c0_sh:.4f}  mean={c0_mr:.4f}  WR={c0_wr:.3f}  N={nt}")

    # C1: Shuffle entry — random qualifying bars + actual exit logic
    qp = [sb for sb in qual if sb in pot]
    c1_sh_list: list[float] = []
    c1_nt_list: list[int] = []
    sample_sz = min(nt * 2, len(qp))
    for _ in range(N_SHUFFLE):
        chosen = sorted(rng.choice(qp, size=sample_sz, replace=False))
        sel: list[dict] = []
        last_x = -1
        for sb in chosen:
            if sb > last_x:
                sel.append(pot[sb])
                last_x = pot[sb]["exit_bar"]
                if len(sel) >= nt:
                    break
        if sel:
            c1_sh_list.append(_eq_sharpe(sel, h4c, h4o, h4ct, cost))
            c1_nt_list.append(len(sel))

    c1_sh = float(np.mean(c1_sh_list)) if c1_sh_list else 0.0
    c1_sd = float(np.std(c1_sh_list)) if c1_sh_list else 0.0
    c1_p = (sum(1 for s in c1_sh_list if s >= c0_sh)
            / len(c1_sh_list)) if c1_sh_list else 1.0
    c1_nt = float(np.mean(c1_nt_list)) if c1_nt_list else 0
    print(f"  C1 shuffle entry: Sh={c1_sh:.4f}±{c1_sd:.4f}  "
          f"p(≥actual)={c1_p:.3f}  avg_N={c1_nt:.0f}")

    # C2: Actual entry + median time-stop
    med_hold = int(np.median([t.bars_held for t in trades]))
    c2d: list[dict] = []
    for i, t in enumerate(trades):
        xb = t.entry_bar + med_hold
        if i + 1 < nt:
            xb = min(xb, trades[i + 1].entry_bar)
        xb = max(min(xb, n - 1), t.entry_bar + 1)
        c2d.append({"entry_bar": t.entry_bar, "exit_bar": xb,
                     "ret": float((h4o[xb] / t.entry_price) * (1 - cost) ** 2 - 1)})
    c2_sh = _eq_sharpe(c2d, h4c, h4o, h4ct, cost)
    c2_mr = float(np.mean([d["ret"] for d in c2d]))
    c2_wr = sum(1 for d in c2d if d["ret"] > 0) / nt
    print(f"  C2 time-stop:     Sh={c2_sh:.4f}  mean={c2_mr:.4f}  hold={med_hold}")

    # C3: Actual entry + shuffled holding period
    actual_holds = np.array([t.bars_held for t in trades])
    c3_sh_list: list[float] = []
    for _ in range(N_SHUFFLE):
        sh_h = rng.permutation(actual_holds)
        dicts: list[dict] = []
        for i, (t, h) in enumerate(zip(trades, sh_h)):
            xb = t.entry_bar + int(h)
            if i + 1 < nt:
                xb = min(xb, trades[i + 1].entry_bar)
            xb = max(min(xb, n - 1), t.entry_bar + 1)
            dicts.append({"entry_bar": t.entry_bar, "exit_bar": xb})
        c3_sh_list.append(_eq_sharpe(dicts, h4c, h4o, h4ct, cost))

    c3_sh = float(np.mean(c3_sh_list))
    c3_sd = float(np.std(c3_sh_list))
    c3_p = sum(1 for s in c3_sh_list if s >= c0_sh) / len(c3_sh_list)
    print(f"  C3 shuffle exit:  Sh={c3_sh:.4f}±{c3_sd:.4f}  p(≥actual)={c3_p:.3f}")

    # C4: Actual entry + oracle exit (at peak)
    c4d: list[dict] = []
    for i, t in enumerate(trades):
        xb = t.peak_bar + 1
        if i + 1 < nt:
            xb = min(xb, trades[i + 1].entry_bar)
        xb = max(min(xb, n - 1), t.entry_bar + 1)
        c4d.append({"entry_bar": t.entry_bar, "exit_bar": xb,
                     "ret": float((h4o[xb] / t.entry_price) * (1 - cost) ** 2 - 1)})
    c4_sh = _eq_sharpe(c4d, h4c, h4o, h4ct, cost)
    c4_mr = float(np.mean([d["ret"] for d in c4d]))
    c4_wr = sum(1 for d in c4d if d["ret"] > 0) / nt
    print(f"  C4 oracle exit:   Sh={c4_sh:.4f}  mean={c4_mr:.4f}  WR={c4_wr:.3f}")

    return [
        ["C0_actual", f"{c0_sh:.4f}", f"{c0_mr:.4f}", f"{c0_wr:.4f}",
         str(nt), "Actual PF0 strategy"],
        ["C1_shuffle_entry", f"{c1_sh:.4f}", "--", "--",
         f"{c1_nt:.0f}",
         f"Random qualifying entry + actual exit (N={N_SHUFFLE}, p={c1_p:.3f})"],
        ["C2_timestop", f"{c2_sh:.4f}", f"{c2_mr:.4f}", f"{c2_wr:.4f}",
         str(nt), f"Actual entry + median time-stop (h={med_hold})"],
        ["C3_shuffle_exit", f"{c3_sh:.4f}", "--", "--",
         str(nt),
         f"Actual entry + shuffled holding (N={N_SHUFFLE}, p={c3_p:.3f})"],
        ["C4_oracle_exit", f"{c4_sh:.4f}", f"{c4_mr:.4f}", f"{c4_wr:.4f}",
         str(nt), "Actual entry + exit at peak"],
    ]


# ── Part 4: Directional advice ──────────────────────────────────────────


def _build_advice(entry_rows, exit_rows, cf_rows, actual_sharpe) -> dict:
    cf = {r[0]: float(r[1]) for r in cf_rows}
    c0 = cf["C0_actual"]

    entry_value = c0 - cf["C1_shuffle_entry"]
    exit_value = c0 - cf["C3_shuffle_exit"]
    exit_ceiling = cf["C4_oracle_exit"] - c0

    # Significant entry features (p < 0.10 vs trade_return)
    sig_entry = [
        {"feature": r[0], "ic": float(r[2]), "p": float(r[3])}
        for r in entry_rows
        if r[1] == "trade_return" and float(r[3]) < 0.10
    ]

    # Oracle capture
    oracle_cap = None
    for r in exit_rows:
        if r[0] == "pct_oracle_captured":
            oracle_cap = float(r[1])

    # Direction decision
    has_entry = len(sig_entry) > 0 or entry_value > 0.05
    has_exit = exit_ceiling > 0.15

    if has_exit and not has_entry:
        direction = "EXIT"
        reason = "Exit ceiling substantial, no significant entry features"
    elif has_entry and not has_exit:
        direction = "ENTRY"
        reason = "Significant entry features present, small exit ceiling"
    elif has_entry and has_exit:
        direction = "BOTH"
        reason = "Both entry signal and exit ceiling present"
    else:
        direction = "NEITHER"
        reason = "Neither entry features nor exit ceiling sufficient"

    if direction != "NEITHER":
        rec = f"Next x39 sprint: focus on {direction} side."
    else:
        rec = ("No x39 sprint warranted. Wait for new data or "
               "x37 gen4 discovery.")

    return {
        "baseline_id": "PF0_E5_EMA21D1",
        "study": "A04",
        "cost_rt_bps": 20,
        "direction": direction,
        "reason": reason,
        "entry_value_sharpe": round(entry_value, 4),
        "exit_value_sharpe": round(exit_value, 4),
        "exit_ceiling_sharpe": round(exit_ceiling, 4),
        "oracle_capture_pct": oracle_cap,
        "significant_entry_features": sig_entry,
        "counterfactual": {k: round(v, 4) for k, v in cf.items()},
        "recommendation": rec,
        "prior_work_reference": {
            "X21_entry_IC_cv": -0.039,
            "X13_exit_oracle_ceiling_sharpe": 0.845,
            "X14_X18_exit_capture_pct": "10-14%",
            "PF1_VC07_conditional_entry_d_sharpe": "+0.116 to +0.140",
        },
    }


# ── Output helpers ───────────────────────────────────────────────────────


def _write_csv(path: Path, header: list[str], rows: list[list]) -> None:
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    print(f"  -> {path.name}")


# ── Main ─────────────────────────────────────────────────────────────────


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    # Load data
    print("Loading data...")
    feed = DataFeed(DATA_PATH, start="2019-01-01", end="2026-02-20",
                    warmup_days=365)
    h4, d1 = feed.h4_bars, feed.d1_bars
    n = len(h4)

    h4c = np.array([b.close for b in h4], dtype=np.float64)
    h4h = np.array([b.high for b in h4], dtype=np.float64)
    h4l = np.array([b.low for b in h4], dtype=np.float64)
    h4o = np.array([b.open for b in h4], dtype=np.float64)
    h4v = np.array([b.volume for b in h4], dtype=np.float64)
    h4tb = np.array([b.taker_buy_base_vol for b in h4], dtype=np.float64)
    h4ct = np.array([b.close_time for b in h4], dtype=np.int64)
    h4ot = np.array([b.open_time for b in h4], dtype=np.int64)
    d1c = np.array([b.close for b in d1], dtype=np.float64)
    d1ct = np.array([b.close_time for b in d1], dtype=np.int64)

    # Run baseline
    print("Running PF0 baseline...")
    result = run_pf0_sim(
        h4c, h4h, h4l, h4o, h4v, h4tb, h4ct, h4ot, d1c, d1ct,
        cost_per_side=COST,
    )
    print(f"  Sharpe={result.sharpe:.4f}  trades={result.n_trades}")

    # Compute indicators
    ema_f = _ema(h4c, _FAST)
    ema_s = _ema(h4c, _SLOW)
    ratr = _robust_atr(h4h, h4l, h4c, _RATR_Q, _RATR_LB, _RATR_P)
    vdo = _vdo(h4v, h4tb, _VDO_F, _VDO_S)
    d1_reg = _map_d1_regime(h4ct, d1c, d1ct, _D1_EMA)
    d1_ema_arr = _ema(d1c, _D1_EMA)
    d1s = _d1_strength(h4ct, d1c, d1_ema_arr, d1ct)
    volr = _vol_ratio(h4c, 5, 20)
    rpos = _range_pos(h4c, h4h, h4l)
    tkr = np.where(h4v > 0, h4tb / h4v, 0.5)

    # Reconstruct trades
    trades = _reconstruct_trades(result, h4o, h4c, COST)
    print(f"  Reconstructed {len(trades)} trades")

    # Qualifying bars + potential trades
    qual = _find_qualifying(ema_f, ema_s, vdo, d1_reg, ratr, h4ct)
    print(f"  Qualifying bars: {len(qual)}")
    print("Pre-computing potential trades...")
    pot = _precompute_potential(qual, h4c, h4o, ema_f, ema_s, ratr, COST)
    print(f"  Potential trades: {len(pot)} / {len(qual)} qualifying")

    # ── Part 1 ──
    print("\n=== Part 1: Entry-side IC ===")
    entry_rows = _entry_ic(trades, h4c, h4o, ema_f, ema_s, ratr, vdo,
                           d1s, volr, rpos, tkr)
    _write_csv(RESULTS_DIR / "a04_entry_feature_summary.csv",
               ["feature", "horizon", "ic", "p_value", "n_trades"],
               entry_rows)

    # ── Part 2 ──
    print("\n=== Part 2: Exit-side characterization ===")
    exit_rows = _exit_analysis(trades, h4c, h4o, COST)
    _write_csv(RESULTS_DIR / "a04_exit_feature_summary.csv",
               ["metric", "value", "description"],
               exit_rows)

    # ── Part 3 ──
    print("\n=== Part 3: Counterfactual decomposition ===")
    cf_rows = _counterfactual(trades, pot, qual, h4c, h4o, h4ct, COST, n)
    _write_csv(RESULTS_DIR / "a04_counterfactual_decomposition.csv",
               ["scenario", "sharpe", "mean_return", "win_rate",
                "n_trades", "description"],
               cf_rows)

    # ── Part 4 ──
    print("\n=== Directional advice ===")
    advice = _build_advice(entry_rows, exit_rows, cf_rows, result.sharpe)
    with open(RESULTS_DIR / "a04_directional_research_advice.json", "w") as f:
        json.dump(advice, f, indent=2)
    print(f"  direction: {advice['direction']}")
    print(f"  reason: {advice['reason']}")
    print(f"  entry_value: {advice['entry_value_sharpe']:+.4f} Sharpe")
    print(f"  exit_value:  {advice['exit_value_sharpe']:+.4f} Sharpe")
    print(f"  exit_ceiling: {advice['exit_ceiling_sharpe']:+.4f} Sharpe")
    print(f"  recommendation: {advice['recommendation']}")

    print(f"\nA04 complete. Results in: {RESULTS_DIR}")


if __name__ == "__main__":
    main()
