#!/usr/bin/env python3
"""True Walk-Forward Optimization: VTREND vs V8 Apex — Fair Comparison.

Part 1: Anchored WFO with In-Window Grid Search
  - Both strategies optimize exactly 3 parameters on TRAIN data only
  - Test best params on OOS window (never seen during selection)
  - Buy & Hold as zero-parameter reference

Part 2: Permutation Test for VDO Signal Authenticity
  - Block-shuffle VDO signal, keep everything else intact
  - Prove VDO has genuine alpha (or not)

Cost: harsh (50 bps round-trip) throughout.
"""

from __future__ import annotations

import csv
import itertools
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
from dateutil.relativedelta import relativedelta

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from v10.core.data import DataFeed
from v10.core.engine import BacktestEngine
from v10.core.types import SCENARIOS
from v10.research.objective import compute_objective
from v10.strategies.buy_and_hold import BuyAndHold
from v10.strategies.v8_apex import V8ApexConfig, V8ApexStrategy
from strategies.vtrend.strategy import VTrendConfig, VTrendStrategy

# ── Constants ────────────────────────────────────────────────────────────

DATA_PATH = str(ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv")
COST = SCENARIOS["harsh"]
WARMUP = 365
CASH = 10_000.0
START = "2019-01-01"
END = "2026-02-20"

# V8 structural params from frozen baseline (not optimized)
V8_FIXED = dict(
    emergency_ref="pre_cost_legacy",
    rsi_method="wilder",
    entry_cooldown_bars=3,
)

# 3 knobs each — matched grid density for fairness
VTREND_GRID = dict(
    slow_period=[60.0, 80.0, 100.0, 120.0, 140.0, 160.0, 200.0],
    trail_mult=[1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0],
    vdo_threshold=[-0.002, 0.0, 0.002, 0.004, 0.008],
)  # 7 × 7 × 5 = 245

V8_GRID = dict(
    trail_atr_mult=[2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0],
    vdo_entry_threshold=[0.0, 0.002, 0.004, 0.006, 0.008, 0.012],
    entry_aggression=[0.50, 0.65, 0.85, 1.00, 1.15, 1.30],
)  # 7 × 6 × 6 = 252


# ── Helpers ──────────────────────────────────────────────────────────────

def _cartesian(grid: dict) -> list[dict]:
    keys = sorted(grid)
    return [dict(zip(keys, vals))
            for vals in itertools.product(*(grid[k] for k in keys))]


def _build_vtrend(params: dict) -> VTrendStrategy:
    cfg = VTrendConfig()
    for k, v in params.items():
        setattr(cfg, k, v)
    return VTrendStrategy(cfg)


def _build_v8(params: dict) -> V8ApexStrategy:
    cfg = V8ApexConfig()
    for k, v in {**V8_FIXED, **params}.items():
        setattr(cfg, k, v)
    return V8ApexStrategy(cfg)


def _score(feed: DataFeed, strategy) -> tuple[float, dict]:
    engine = BacktestEngine(
        feed=feed, strategy=strategy, cost=COST,
        initial_cash=CASH, warmup_mode="no_trade",
    )
    res = engine.run()
    return compute_objective(res.summary), res.summary


def _fmt_p(params: dict, keys: list[str]) -> str:
    return " ".join(f"{k}={params[k]}" for k in keys)


# ── Window generation ────────────────────────────────────────────────────

def anchored_windows(start: str, end: str,
                     min_train_months: int = 24,
                     test_months: int = 6) -> list[dict]:
    s = datetime.strptime(start, "%Y-%m-%d")
    e = datetime.strptime(end, "%Y-%m-%d")
    wins, wid = [], 0
    test_s = s + relativedelta(months=min_train_months)
    while test_s < e:
        test_e = min(test_s + relativedelta(months=test_months), e)
        # require at least 3 months in the test window
        if (test_e.year - test_s.year) * 12 + test_e.month - test_s.month < 3:
            break
        wins.append(dict(
            id=wid,
            tr_s=start, tr_e=test_s.strftime("%Y-%m-%d"),
            te_s=test_s.strftime("%Y-%m-%d"),
            te_e=test_e.strftime("%Y-%m-%d"),
        ))
        wid += 1
        test_s = test_e
    return wins


# ═════════════════════════════════════════════════════════════════════════
# PART 1 — True Walk-Forward Optimization
# ═════════════════════════════════════════════════════════════════════════

def run_true_wfo() -> list[dict]:
    vt_combos = _cartesian(VTREND_GRID)
    v8_combos = _cartesian(V8_GRID)
    windows = anchored_windows(START, END)

    print("=" * 72)
    print("PART 1: TRUE WALK-FORWARD OPTIMIZATION")
    print(f"  VTREND {len(vt_combos)} combos  |  V8 {len(v8_combos)} combos  |  "
          f"{len(windows)} windows  |  harsh cost")
    print("=" * 72)

    for w in windows:
        print(f"  W{w['id']}: train [{w['tr_s']}→{w['tr_e']}]  "
              f"test [{w['te_s']}→{w['te_e']}]")

    rows: list[dict] = []

    for w in windows:
        t0 = time.time()
        print(f"\n── Window {w['id']} ──")

        # one feed per phase — reused across all combos
        tr_feed = DataFeed(DATA_PATH, start=w["tr_s"], end=w["tr_e"],
                           warmup_days=WARMUP)
        te_feed = DataFeed(DATA_PATH, start=w["te_s"], end=w["te_e"],
                           warmup_days=WARMUP)

        # ── VTREND grid on train ──
        best_vt = (-1e9, None)
        for i, p in enumerate(vt_combos):
            sc, _ = _score(tr_feed, _build_vtrend(p))
            if sc > best_vt[0]:
                best_vt = (sc, p)
            if (i + 1) % 50 == 0:
                print(f"  VT train {i+1}/{len(vt_combos)}")
        print(f"  VT best train: {best_vt[0]:.1f}  "
              f"{_fmt_p(best_vt[1], sorted(VTREND_GRID))}")

        # ── V8 grid on train ──
        best_v8 = (-1e9, None)
        for i, p in enumerate(v8_combos):
            sc, _ = _score(tr_feed, _build_v8(p))
            if sc > best_v8[0]:
                best_v8 = (sc, p)
            if (i + 1) % 50 == 0:
                print(f"  V8 train {i+1}/{len(v8_combos)}")
        print(f"  V8 best train: {best_v8[0]:.1f}  "
              f"{_fmt_p(best_v8[1], sorted(V8_GRID))}")

        # ── OOS test ──
        vt_sc, vt_s = _score(te_feed, _build_vtrend(best_vt[1]))
        v8_sc, v8_s = _score(te_feed, _build_v8(best_v8[1]))
        bh_sc, bh_s = _score(te_feed, BuyAndHold())

        winner = "VTREND" if vt_sc > v8_sc else ("V8" if v8_sc > vt_sc else "TIE")
        dt = time.time() - t0

        row = dict(
            wid=w["id"],
            test=f"{w['te_s']}→{w['te_e']}",
            # vtrend
            vt_tr=round(best_vt[0], 1), vt_te=round(vt_sc, 1),
            vt_cagr=round(vt_s.get("cagr_pct", 0), 1),
            vt_mdd=round(vt_s.get("max_drawdown_mid_pct", 0), 1),
            vt_calmar=round(vt_s.get("calmar") or 0, 2),
            vt_sharpe=round(vt_s.get("sharpe") or 0, 2),
            vt_trades=vt_s.get("trades", 0),
            vt_params=best_vt[1],
            vt_deg=round(best_vt[0] - vt_sc, 1),
            # v8
            v8_tr=round(best_v8[0], 1), v8_te=round(v8_sc, 1),
            v8_cagr=round(v8_s.get("cagr_pct", 0), 1),
            v8_mdd=round(v8_s.get("max_drawdown_mid_pct", 0), 1),
            v8_calmar=round(v8_s.get("calmar") or 0, 2),
            v8_sharpe=round(v8_s.get("sharpe") or 0, 2),
            v8_trades=v8_s.get("trades", 0),
            v8_params=best_v8[1],
            v8_deg=round(best_v8[0] - v8_sc, 1),
            # b&h
            bh_te=round(bh_sc, 1),
            bh_cagr=round(bh_s.get("cagr_pct", 0), 1),
            bh_mdd=round(bh_s.get("max_drawdown_mid_pct", 0), 1),
            # meta
            winner=winner, secs=round(dt),
        )
        rows.append(row)
        print(f"  OOS: VT={vt_sc:.1f} V8={v8_sc:.1f} B&H={bh_sc:.1f} → "
              f"{winner}  ({dt:.0f}s)")

    # ── Summary ──
    n = len(rows)
    vt_w = sum(1 for r in rows if r["winner"] == "VTREND")
    v8_w = sum(1 for r in rows if r["winner"] == "V8")

    print("\n" + "=" * 72)
    print("TRUE WFO SUMMARY (all metrics are OOS — never seen during selection)")
    print("=" * 72)

    hdr = (f"{'W':>2} {'Test Period':>24} {'VT sc':>7} {'V8 sc':>7} "
           f"{'B&H':>7} {'VT CAGR':>8} {'V8 CAGR':>8} "
           f"{'VT MDD':>7} {'V8 MDD':>7} {'Win':>7}")
    print(hdr)
    print("-" * len(hdr))
    for r in rows:
        print(f"{r['wid']:>2} {r['test']:>24} {r['vt_te']:>7.1f} "
              f"{r['v8_te']:>7.1f} {r['bh_te']:>7.1f} "
              f"{r['vt_cagr']:>7.1f}% {r['v8_cagr']:>7.1f}% "
              f"{r['vt_mdd']:>6.1f}% {r['v8_mdd']:>6.1f}% "
              f"{r['winner']:>7}")

    def _mean(k): return np.mean([r[k] for r in rows])
    def _median(k): return np.median([r[k] for r in rows])

    print(f"\nWin rate:  VTREND {vt_w}/{n} ({100*vt_w/n:.0f}%)   "
          f"V8 {v8_w}/{n} ({100*v8_w/n:.0f}%)")
    print(f"\nMean OOS score:    VT={_mean('vt_te'):.1f}  "
          f"V8={_mean('v8_te'):.1f}  B&H={_mean('bh_te'):.1f}")
    print(f"Median OOS score:  VT={_median('vt_te'):.1f}  "
          f"V8={_median('v8_te'):.1f}  B&H={_median('bh_te'):.1f}")
    print(f"\nMean OOS CAGR:     VT={_mean('vt_cagr'):.1f}%  "
          f"V8={_mean('v8_cagr'):.1f}%  B&H={_mean('bh_cagr'):.1f}%")
    print(f"Mean OOS Calmar:   VT={_mean('vt_calmar'):.2f}  "
          f"V8={_mean('v8_calmar'):.2f}")
    print(f"Mean OOS Sharpe:   VT={_mean('vt_sharpe'):.2f}  "
          f"V8={_mean('v8_sharpe'):.2f}")
    print(f"\nMean degradation (train→OOS):  VT={_mean('vt_deg'):.1f}  "
          f"V8={_mean('v8_deg'):.1f}  (lower = less overfit)")

    print("\n── Parameter Stability ──")
    vt_keys = sorted(VTREND_GRID)
    v8_keys = sorted(V8_GRID)
    print("VTREND selected params per window:")
    for r in rows:
        print(f"  W{r['wid']}: {_fmt_p(r['vt_params'], vt_keys)}")
    print("V8 selected params per window:")
    for r in rows:
        print(f"  W{r['wid']}: {_fmt_p(r['v8_params'], v8_keys)}")

    # check param spread
    for label, grid_keys, key in [("VTREND", vt_keys, "vt_params"),
                                   ("V8", v8_keys, "v8_params")]:
        print(f"\n{label} param spread:")
        for pk in grid_keys:
            vals = [r[key][pk] for r in rows]
            print(f"  {pk}: min={min(vals)} max={max(vals)} "
                  f"unique={len(set(vals))}/{n}")

    return rows


# ═════════════════════════════════════════════════════════════════════════
# PART 2 — Permutation Test for VDO
# ═════════════════════════════════════════════════════════════════════════

def _block_shuffle(arr: np.ndarray, block_size: int,
                   rng: np.random.RandomState) -> np.ndarray:
    n = len(arr)
    n_blocks = n // block_size
    if n_blocks <= 1:
        return arr.copy()
    idx = np.arange(n_blocks)
    rng.shuffle(idx)
    blocks = [arr[i * block_size:(i + 1) * block_size] for i in idx]
    tail = arr[n_blocks * block_size:]
    if len(tail):
        blocks.append(tail)
    return np.concatenate(blocks)


class _ShuffledVDO(VTrendStrategy):
    """VTrend that block-shuffles VDO after on_init (for permutation test)."""

    def __init__(self, config: VTrendConfig, block: int, seed: int):
        super().__init__(config)
        self._blk = block
        self._seed = seed

    def on_init(self, h4_bars, d1_bars):
        super().on_init(h4_bars, d1_bars)
        if self._vdo is not None:
            self._vdo = _block_shuffle(
                self._vdo, self._blk, np.random.RandomState(self._seed))


class _ShuffledEMA(VTrendStrategy):
    """VTrend that block-shuffles BOTH EMAs (test if EMA structure matters)."""

    def __init__(self, config: VTrendConfig, block: int, seed: int):
        super().__init__(config)
        self._blk = block
        self._seed = seed

    def on_init(self, h4_bars, d1_bars):
        super().on_init(h4_bars, d1_bars)
        rng = np.random.RandomState(self._seed)
        if self._ema_fast is not None:
            self._ema_fast = _block_shuffle(self._ema_fast, self._blk, rng)
        if self._ema_slow is not None:
            self._ema_slow = _block_shuffle(self._ema_slow, self._blk, rng)


def run_permutation_test(n_perms: int = 200, block: int = 20) -> dict:
    print("\n\n" + "=" * 72)
    print("PART 2: PERMUTATION TEST — VDO Signal Authenticity")
    print(f"  {n_perms} permutations  |  block={block} H4 bars  |  harsh cost")
    print("=" * 72)

    feed = DataFeed(DATA_PATH, start=START, end=END, warmup_days=WARMUP)

    # A. Real VTREND (baseline)
    print("\nA. VTREND with real VDO...")
    real_sc, real_s = _score(feed, VTrendStrategy(VTrendConfig()))
    print(f"   score={real_sc:.1f}  CAGR={real_s['cagr_pct']:.1f}%  "
          f"MDD={real_s['max_drawdown_mid_pct']:.1f}%  "
          f"Calmar={real_s.get('calmar') or 0:.2f}  "
          f"trades={real_s['trades']}")

    # B. VDO disabled (EMA-only)
    print("\nB. VTREND with VDO DISABLED (threshold=-999)...")
    ema_sc, ema_s = _score(
        feed, VTrendStrategy(VTrendConfig(vdo_threshold=-999.0)))
    print(f"   score={ema_sc:.1f}  CAGR={ema_s['cagr_pct']:.1f}%  "
          f"MDD={ema_s['max_drawdown_mid_pct']:.1f}%  "
          f"Calmar={ema_s.get('calmar') or 0:.2f}  "
          f"trades={ema_s['trades']}")

    # C. Shuffled VDO (null distribution)
    print(f"\nC. {n_perms} VDO permutations...")
    vdo_null: list[float] = []
    t0 = time.time()
    for i in range(n_perms):
        sc, _ = _score(feed, _ShuffledVDO(VTrendConfig(), block, seed=i))
        vdo_null.append(sc)
        if (i + 1) % 25 == 0:
            el = time.time() - t0
            print(f"   {i+1}/{n_perms}  ({el:.0f}s)")
    vdo_arr = np.array(vdo_null)
    p_vdo = float(np.mean(vdo_arr >= real_sc))

    # D. Shuffled EMA (test EMA structure importance)
    print(f"\nD. {n_perms} EMA permutations...")
    ema_null: list[float] = []
    t0 = time.time()
    for i in range(n_perms):
        sc, _ = _score(feed, _ShuffledEMA(VTrendConfig(), block, seed=i))
        ema_null.append(sc)
        if (i + 1) % 25 == 0:
            el = time.time() - t0
            print(f"   {i+1}/{n_perms}  ({el:.0f}s)")
    ema_arr = np.array(ema_null)
    p_ema = float(np.mean(ema_arr >= real_sc))

    # ── Results ──
    print("\n" + "=" * 60)
    print("PERMUTATION TEST RESULTS")
    print("=" * 60)
    print(f"\nBaseline (real VDO + real EMA):  score = {real_sc:.1f}")
    print(f"EMA-only (VDO disabled):         score = {ema_sc:.1f}  "
          f"(delta = {real_sc - ema_sc:+.1f})")

    print(f"\nVDO Shuffle Test  (EMA intact, VDO shuffled):")
    print(f"  null mean={np.mean(vdo_arr):.1f}  std={np.std(vdo_arr):.1f}  "
          f"[{np.percentile(vdo_arr,5):.1f}, {np.percentile(vdo_arr,95):.1f}]")
    print(f"  p-value = {p_vdo:.4f}  "
          f"{'*** SIGNIFICANT' if p_vdo < 0.05 else '* marginal' if p_vdo < 0.10 else 'NOT significant'}")

    print(f"\nEMA Shuffle Test  (VDO intact, EMA shuffled):")
    print(f"  null mean={np.mean(ema_arr):.1f}  std={np.std(ema_arr):.1f}  "
          f"[{np.percentile(ema_arr,5):.1f}, {np.percentile(ema_arr,95):.1f}]")
    print(f"  p-value = {p_ema:.4f}  "
          f"{'*** SIGNIFICANT' if p_ema < 0.05 else '* marginal' if p_ema < 0.10 else 'NOT significant'}")

    print("\nInterpretation:")
    if p_vdo < 0.05 and p_ema < 0.05:
        print("  BOTH signals are genuine — EMA trend + VDO confirmation both add alpha.")
    elif p_vdo >= 0.05 and p_ema < 0.05:
        print("  EMA structure is genuine, but VDO adds no significant alpha.")
        print("  VDO can be simplified or removed without loss.")
    elif p_vdo < 0.05 and p_ema >= 0.05:
        print("  VDO is genuine, but EMA structure is not significant (surprising).")
    else:
        print("  NEITHER signal is significant — strategy may rely on luck.")

    return dict(
        real=real_sc, ema_only=ema_sc,
        vdo_null_mean=float(np.mean(vdo_arr)),
        vdo_null_std=float(np.std(vdo_arr)),
        p_vdo=p_vdo,
        ema_null_mean=float(np.mean(ema_arr)),
        ema_null_std=float(np.std(ema_arr)),
        p_ema=p_ema,
    )


# ═════════════════════════════════════════════════════════════════════════
# MAIN
# ═════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    t_all = time.time()

    wfo_rows = run_true_wfo()
    perm = run_permutation_test()

    total = time.time() - t_all
    print(f"\n\nTotal runtime: {total:.0f}s ({total / 60:.1f} min)")

    # ── Persist ──
    out = ROOT / "research" / "results"
    out.mkdir(parents=True, exist_ok=True)

    # WFO CSV
    csv_path = out / "true_wfo_results.csv"
    flat_keys = [k for k in wfo_rows[0] if k not in ("vt_params", "v8_params")]
    with open(csv_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=flat_keys + ["vt_params", "v8_params"])
        w.writeheader()
        for r in wfo_rows:
            d = {**r, "vt_params": json.dumps(r["vt_params"]),
                 "v8_params": json.dumps(r["v8_params"])}
            w.writerow(d)
    print(f"Saved: {csv_path}")

    # Permutation JSON
    perm_path = out / "permutation_test.json"
    with open(perm_path, "w") as f:
        json.dump(perm, f, indent=2)
    print(f"Saved: {perm_path}")
