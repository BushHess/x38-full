#!/usr/bin/env python3
"""Exp 45: Triple Stack — Accel + Compression + Maturity Decay.

Combines exp33 (accel gate), exp34 (compression gate), exp38 (maturity decay).
Two ENTRY filters + one EXIT modifier.

Risk: stacking two entry filters may OVER-FILTER entries (X7 trap).
Key question: are accel and compression complementary or redundant?

11 configs: 4 refs + 3 duos + 4 triples.

Usage:
    python -m research.x39.experiments.exp45_triple_stack
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]  # btc-spot-dev/
sys.path.insert(0, str(ROOT))

from research.x39.explore import compute_features, load_data  # noqa: E402

RESULTS_DIR = Path(__file__).resolve().parents[1] / "results"

# ── Strategy constants (match E5-ema21D1) ─────────────────────────────────
SLOW_PERIOD = 120
TRAIL_BASE = 3.0
COST_BPS = 50
INITIAL_CASH = 10_000.0
WARMUP_DAYS = 365


# ── Reused from exp38 ────────────────────────────────────────────────────
def compute_trend_age(ema_fast: np.ndarray, ema_slow: np.ndarray) -> np.ndarray:
    """Bars since most recent EMA crossover (fast > slow)."""
    n = len(ema_fast)
    age = np.zeros(n, dtype=np.int32)
    for i in range(1, n):
        if ema_fast[i] > ema_slow[i]:
            age[i] = age[i - 1] + 1
    return age


def calc_effective_trail(
    trend_age: int,
    trail_min: float,
    decay_start: int,
    decay_end: int,
) -> float:
    """Linear decay from TRAIL_BASE to trail_min between decay_start and decay_end."""
    if trend_age < decay_start:
        return TRAIL_BASE
    if trend_age >= decay_end:
        return trail_min
    progress = (trend_age - decay_start) / (decay_end - decay_start)
    return TRAIL_BASE - (TRAIL_BASE - trail_min) * progress


# ── Config dataclass ─────────────────────────────────────────────────────
class Config:
    __slots__ = (
        "name", "lookback", "min_accel",
        "compression_thr", "trail_min", "decay_start", "decay_end",
    )

    def __init__(
        self,
        name: str,
        lookback: int | None = None,
        min_accel: float | None = None,
        compression_thr: float | None = None,
        trail_min: float | None = None,
        decay_start: int | None = None,
        decay_end: int | None = None,
    ) -> None:
        self.name = name
        self.lookback = lookback
        self.min_accel = min_accel
        self.compression_thr = compression_thr
        self.trail_min = trail_min
        self.decay_start = decay_start
        self.decay_end = decay_end

    @property
    def has_accel(self) -> bool:
        return self.lookback is not None

    @property
    def has_compression(self) -> bool:
        return self.compression_thr is not None

    @property
    def has_decay(self) -> bool:
        return self.trail_min is not None


# ── 11 Configs from spec ────────────────────────────────────────────────
CONFIGS = [
    # 4 references
    Config("ref_baseline"),
    Config("ref_accel_only", lookback=12, min_accel=0.0),
    Config("ref_comp_only", compression_thr=0.7),
    Config("ref_decay_only", trail_min=1.5, decay_start=60, decay_end=180),
    # 3 double stacks
    Config("duo_accel_decay", lookback=12, min_accel=0.0, trail_min=1.5, decay_start=60, decay_end=180),
    Config("duo_comp_decay", compression_thr=0.7, trail_min=1.5, decay_start=60, decay_end=180),
    Config("duo_accel_comp", lookback=12, min_accel=0.0, compression_thr=0.7),
    # 4 triple stacks
    Config("triple_A", lookback=12, min_accel=0.0, compression_thr=0.6, trail_min=1.5, decay_start=60, decay_end=180),
    Config("triple_B", lookback=12, min_accel=0.0, compression_thr=0.7, trail_min=1.5, decay_start=60, decay_end=180),
    Config("triple_C", lookback=12, min_accel=0.0, compression_thr=0.7, trail_min=2.0, decay_start=60, decay_end=180),
    Config("triple_D", lookback=12, min_accel=0.0, compression_thr=0.8, trail_min=1.5, decay_start=60, decay_end=180),
]


def run_backtest(
    feat: pd.DataFrame,
    trend_age: np.ndarray,
    ema_spread_roc: np.ndarray,
    warmup_bar: int,
    cfg: Config,
) -> dict:
    """Replay E5-ema21D1 with optional accel gate + compression gate + maturity decay."""
    c = feat["close"].values
    ema_f = feat["ema_fast"].values
    ema_s = feat["ema_slow"].values
    ratr = feat["ratr"].values
    vdo_arr = feat["vdo"].values
    d1_ok = feat["d1_regime_ok"].values
    vol_ratio = feat["vol_ratio_5_20"].values
    n = len(c)

    trades: list[dict] = []
    blocked_by_accel: list[int] = []
    blocked_by_compression: list[int] = []
    blocked_by_both: list[int] = []
    in_pos = False
    peak = 0.0
    entry_bar = 0
    entry_price = 0.0

    equity = np.full(n, np.nan)
    cash = INITIAL_CASH
    position_size = 0.0

    trail_at_exit: list[float] = []
    age_at_exit: list[int] = []

    for i in range(warmup_bar, n):
        if np.isnan(ratr[i]):
            equity[i] = cash if not in_pos else position_size * c[i]
            continue

        if not in_pos:
            equity[i] = cash

            base_ok = ema_f[i] > ema_s[i] and vdo_arr[i] > 0 and d1_ok[i]

            if base_ok:
                # Gate 1: Accel (exp33)
                accel_ok = True
                if cfg.has_accel:
                    if np.isfinite(ema_spread_roc[i]):
                        accel_ok = ema_spread_roc[i] > cfg.min_accel
                    else:
                        accel_ok = False

                # Gate 2: Compression (exp34)
                compression_ok = True
                if cfg.has_compression:
                    if np.isfinite(vol_ratio[i]):
                        compression_ok = vol_ratio[i] < cfg.compression_thr
                    else:
                        compression_ok = False

                if accel_ok and compression_ok:
                    in_pos = True
                    entry_bar = i
                    entry_price = c[i]
                    peak = c[i]
                    half_cost = (COST_BPS / 2) / 10_000
                    position_size = cash * (1 - half_cost) / c[i]
                    cash = 0.0
                else:
                    # Track which gate(s) blocked
                    if not accel_ok and not compression_ok:
                        blocked_by_both.append(i)
                    elif not accel_ok:
                        blocked_by_accel.append(i)
                    else:
                        blocked_by_compression.append(i)
        else:
            equity[i] = position_size * c[i]
            peak = max(peak, c[i])

            # Gate 3: Maturity decay (exp38)
            if cfg.has_decay:
                current_trail = calc_effective_trail(
                    trend_age[i], cfg.trail_min, cfg.decay_start, cfg.decay_end,
                )
            else:
                current_trail = TRAIL_BASE

            trail_stop = peak - current_trail * ratr[i]

            exit_reason = None
            if c[i] < trail_stop:
                exit_reason = "trail"
            elif ema_f[i] < ema_s[i]:
                exit_reason = "trend"

            if exit_reason:
                half_cost = (COST_BPS / 2) / 10_000
                cash = position_size * c[i] * (1 - half_cost)
                cost_rt = COST_BPS / 10_000
                gross_ret = (c[i] - entry_price) / entry_price
                net_ret = gross_ret - cost_rt

                trail_at_exit.append(current_trail)
                age_at_exit.append(int(trend_age[i]))

                trades.append({
                    "entry_bar": entry_bar,
                    "exit_bar": i,
                    "bars_held": i - entry_bar,
                    "net_ret": net_ret,
                    "win": int(net_ret > 0),
                    "exit_reason": exit_reason,
                })

                equity[i] = cash
                position_size = 0.0
                in_pos = False
                peak = 0.0

    # ── Metrics ───────────────────────────────────────────────────────
    eq = pd.Series(equity[warmup_bar:]).dropna()
    if len(eq) < 2 or len(trades) == 0:
        return _empty_result(cfg)

    rets = eq.pct_change().dropna()
    bars_per_year = 365.25 * 24 / 4

    sharpe = (rets.mean() / rets.std() * np.sqrt(bars_per_year)) if rets.std() > 0 else 0.0

    total_bars = len(eq)
    years = total_bars / bars_per_year
    final_ret = eq.iloc[-1] / eq.iloc[0]
    cagr = final_ret ** (1 / years) - 1 if years > 0 and final_ret > 0 else 0.0

    cummax = eq.cummax()
    dd = (eq - cummax) / cummax
    mdd = dd.min()

    total_bars_held = sum(t["bars_held"] for t in trades)
    exposure = total_bars_held / total_bars

    tdf = pd.DataFrame(trades)
    n_wins = int(tdf["win"].sum())
    win_rate = n_wins / len(trades) * 100
    avg_bars_held = tdf["bars_held"].mean()

    return {
        "config": cfg.name,
        "lookback": cfg.lookback if cfg.has_accel else "",
        "min_accel": cfg.min_accel if cfg.has_accel else "",
        "compression_thr": cfg.compression_thr if cfg.has_compression else "",
        "trail_min": cfg.trail_min if cfg.has_decay else "",
        "decay_start": cfg.decay_start if cfg.has_decay else "",
        "decay_end": cfg.decay_end if cfg.has_decay else "",
        "sharpe": round(sharpe, 4),
        "cagr_pct": round(cagr * 100, 2),
        "mdd_pct": round(abs(mdd) * 100, 2),
        "trades": len(trades),
        "win_rate": round(win_rate, 1),
        "avg_bars_held": round(avg_bars_held, 1),
        "exposure_pct": round(exposure * 100, 1),
        "blocked_accel_only": len(blocked_by_accel),
        "blocked_comp_only": len(blocked_by_compression),
        "blocked_both": len(blocked_by_both),
        "avg_trend_age_exit": round(np.mean(age_at_exit), 1) if age_at_exit else np.nan,
        "avg_eff_trail_exit": round(np.mean(trail_at_exit), 3) if trail_at_exit else np.nan,
    }


def _empty_result(cfg: Config) -> dict:
    return {
        "config": cfg.name,
        "lookback": cfg.lookback if cfg.has_accel else "",
        "min_accel": cfg.min_accel if cfg.has_accel else "",
        "compression_thr": cfg.compression_thr if cfg.has_compression else "",
        "trail_min": cfg.trail_min if cfg.has_decay else "",
        "decay_start": cfg.decay_start if cfg.has_decay else "",
        "decay_end": cfg.decay_end if cfg.has_decay else "",
        "sharpe": np.nan, "cagr_pct": np.nan, "mdd_pct": np.nan,
        "trades": 0, "win_rate": np.nan, "avg_bars_held": np.nan,
        "exposure_pct": np.nan, "blocked_accel_only": 0,
        "blocked_comp_only": 0, "blocked_both": 0,
        "avg_trend_age_exit": np.nan, "avg_eff_trail_exit": np.nan,
    }


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("EXP 45: Triple Stack — Accel + Compression + Maturity Decay")
    print("=" * 80)

    h4, d1 = load_data()
    feat = compute_features(h4, d1)

    ema_f = feat["ema_fast"].values
    ema_s = feat["ema_slow"].values
    n = len(feat)

    # Pre-compute shared indicators
    print("Computing trend_age...")
    trend_age = compute_trend_age(ema_f, ema_s)

    print("Computing ema_spread_roc (lookback=12)...")
    with np.errstate(divide="ignore", invalid="ignore"):
        ema_spread = np.where(ema_s != 0, (ema_f - ema_s) / ema_s, np.nan)

    lb = 12  # all configs use lookback=12
    ema_spread_roc = np.full(n, np.nan)
    ema_spread_roc[lb:] = ema_spread[lb:] - ema_spread[:n - lb]

    # Warmup: 365 days
    bars_per_day = 24 / 4
    warmup_bar = int(WARMUP_DAYS * bars_per_day)
    print(f"Warmup bar: {warmup_bar} ({WARMUP_DAYS} days)")
    print(f"Configs: {len(CONFIGS)}")

    # ── Run all configs ──────────────────────────────────────────────
    results = []
    for cfg in CONFIGS:
        roc_arr = ema_spread_roc if cfg.has_accel else np.full(n, np.nan)
        print(f"\nRunning {cfg.name}...")
        r = run_backtest(feat, trend_age, roc_arr, warmup_bar, cfg)
        results.append(r)
        total_blocked = r["blocked_accel_only"] + r["blocked_comp_only"] + r["blocked_both"]
        print(
            f"  Sharpe={r['sharpe']}, CAGR={r['cagr_pct']}%, MDD={r['mdd_pct']}%, "
            f"trades={r['trades']}, blocked={total_blocked}"
        )

    # ── Results table ────────────────────────────────────────────────
    df = pd.DataFrame(results)

    base_sharpe = df.loc[df["config"] == "ref_baseline", "sharpe"].values[0]
    base_cagr = df.loc[df["config"] == "ref_baseline", "cagr_pct"].values[0]
    base_mdd = df.loc[df["config"] == "ref_baseline", "mdd_pct"].values[0]
    base_trades = df.loc[df["config"] == "ref_baseline", "trades"].values[0]
    base_winrate = df.loc[df["config"] == "ref_baseline", "win_rate"].values[0]

    df["d_sharpe"] = df["sharpe"] - base_sharpe
    df["d_cagr"] = df["cagr_pct"] - base_cagr
    df["d_mdd"] = df["mdd_pct"] - base_mdd  # negative = improvement

    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)
    print(df.to_string(index=False))

    out_path = RESULTS_DIR / "exp45_results.csv"
    df.to_csv(out_path, index=False)
    print(f"\n-> Saved to {out_path}")

    # ── 1. Additivity table ──────────────────────────────────────────
    print("\n" + "=" * 80)
    print("1. ADDITIVITY TABLE: Single → Duo → Triple")
    print("=" * 80)

    d_accel = df.loc[df["config"] == "ref_accel_only", "d_sharpe"].values[0]
    d_comp = df.loc[df["config"] == "ref_comp_only", "d_sharpe"].values[0]
    d_decay = df.loc[df["config"] == "ref_decay_only", "d_sharpe"].values[0]

    print(f"\n  Singles (d_Sharpe vs baseline):")
    print(f"    accel:       {d_accel:+.4f}")
    print(f"    compression: {d_comp:+.4f}")
    print(f"    decay:       {d_decay:+.4f}")
    print(f"    sum all 3:   {d_accel + d_comp + d_decay:+.4f}")

    d_ac_decay = df.loc[df["config"] == "duo_accel_decay", "d_sharpe"].values[0]
    d_co_decay = df.loc[df["config"] == "duo_comp_decay", "d_sharpe"].values[0]
    d_ac_comp = df.loc[df["config"] == "duo_accel_comp", "d_sharpe"].values[0]

    print(f"\n  Duos (d_Sharpe vs baseline):")
    print(f"    accel+decay:       {d_ac_decay:+.4f}  (sum singles: {d_accel + d_decay:+.4f})")
    print(f"    comp+decay:        {d_co_decay:+.4f}  (sum singles: {d_comp + d_decay:+.4f})")
    print(f"    accel+comp:        {d_ac_comp:+.4f}  (sum singles: {d_accel + d_comp:+.4f})")

    sum_all_singles = d_accel + d_comp + d_decay
    print(f"\n  Triples (d_Sharpe vs baseline):")
    triples = df[df["config"].str.startswith("triple_")]
    for _, row in triples.iterrows():
        td = row["d_sharpe"]
        ratio = td / sum_all_singles if abs(sum_all_singles) > 1e-6 else np.nan
        # Marginal value of third mechanism
        best_duo = max(d_ac_decay, d_co_decay, d_ac_comp)
        marginal = td - best_duo
        label = (
            "SYNERGISTIC" if ratio > 1.05
            else "ADDITIVE" if ratio > 0.75
            else "PARTIALLY_ADDITIVE" if ratio > 0.50
            else "REDUNDANT"
        )
        print(
            f"    {row['config']:10s}: {td:+.4f}  "
            f"ratio={ratio:.3f} [{label}]  "
            f"marginal_over_best_duo={marginal:+.4f}"
        )

    # ── CAGR additivity ──────────────────────────────────────────────
    d_accel_cagr = df.loc[df["config"] == "ref_accel_only", "d_cagr"].values[0]
    d_comp_cagr = df.loc[df["config"] == "ref_comp_only", "d_cagr"].values[0]
    d_decay_cagr = df.loc[df["config"] == "ref_decay_only", "d_cagr"].values[0]

    print(f"\n  CAGR additivity:")
    print(f"    Singles: accel={d_accel_cagr:+.2f}pp, comp={d_comp_cagr:+.2f}pp, decay={d_decay_cagr:+.2f}pp")
    for _, row in triples.iterrows():
        sum_cagr = d_accel_cagr + d_comp_cagr + d_decay_cagr
        r_cagr = row["d_cagr"] / sum_cagr if abs(sum_cagr) > 1e-6 else np.nan
        print(f"    {row['config']:10s}: d_CAGR={row['d_cagr']:+.2f}pp, ratio={r_cagr:.3f}")

    # ── MDD additivity ───────────────────────────────────────────────
    d_accel_mdd = df.loc[df["config"] == "ref_accel_only", "d_mdd"].values[0]
    d_comp_mdd = df.loc[df["config"] == "ref_comp_only", "d_mdd"].values[0]
    d_decay_mdd = df.loc[df["config"] == "ref_decay_only", "d_mdd"].values[0]

    print(f"\n  MDD additivity (negative = improvement):")
    print(f"    Singles: accel={d_accel_mdd:+.2f}pp, comp={d_comp_mdd:+.2f}pp, decay={d_decay_mdd:+.2f}pp")
    for _, row in triples.iterrows():
        sum_mdd = d_accel_mdd + d_comp_mdd + d_decay_mdd
        r_mdd = row["d_mdd"] / sum_mdd if abs(sum_mdd) > 1e-6 else np.nan
        print(f"    {row['config']:10s}: d_MDD={row['d_mdd']:+.2f}pp, ratio={r_mdd:.3f}")

    # ── 2. Trade count check ─────────────────────────────────────────
    print("\n" + "=" * 80)
    print("2. TRADE COUNT — Over-filtering check (X7 trap: <100 trades)")
    print("=" * 80)

    print(f"\n  {'Config':20s} {'Trades':>6s} {'vs Base':>8s} {'Status':>12s}")
    print(f"  {'-' * 20} {'-' * 6} {'-' * 8} {'-' * 12}")
    for _, row in df.iterrows():
        n_trades = row["trades"]
        delta_t = n_trades - base_trades
        status = "OK" if n_trades >= 100 else "DANGER" if n_trades >= 50 else "X7_TRAP"
        print(f"  {row['config']:20s} {n_trades:6d} {delta_t:+8d} {status:>12s}")

    # ── 3. Overlap analysis ──────────────────────────────────────────
    print("\n" + "=" * 80)
    print("3. OVERLAP ANALYSIS — Are accel and compression gates redundant?")
    print("=" * 80)

    vdo_arr = feat["vdo"].values
    d1_ok_arr = feat["d1_regime_ok"].values
    vol_ratio_arr = feat["vol_ratio_5_20"].values
    ratr_arr = feat["ratr"].values

    base_entries = 0
    pass_both = 0
    fail_accel_only = 0
    fail_comp_only = 0
    fail_both = 0

    # Use triple_B params: lb=12, ma=0.0, thr=0.7
    for i in range(warmup_bar, n):
        if np.isnan(ratr_arr[i]):
            continue
        base_ok = ema_f[i] > ema_s[i] and vdo_arr[i] > 0 and d1_ok_arr[i]
        if base_ok:
            base_entries += 1
            a_ok = np.isfinite(ema_spread_roc[i]) and ema_spread_roc[i] > 0.0
            c_ok = np.isfinite(vol_ratio_arr[i]) and vol_ratio_arr[i] < 0.7
            if a_ok and c_ok:
                pass_both += 1
            elif not a_ok and not c_ok:
                fail_both += 1
            elif not a_ok:
                fail_accel_only += 1
            else:
                fail_comp_only += 1

    total_blocked = fail_accel_only + fail_comp_only + fail_both
    overlap_pct = fail_both / total_blocked * 100 if total_blocked > 0 else 0.0
    unique_accel = fail_accel_only / total_blocked * 100 if total_blocked > 0 else 0.0
    unique_comp = fail_comp_only / total_blocked * 100 if total_blocked > 0 else 0.0

    print(f"\n  Gate parameters: accel lb=12 ma=0.0, compression thr=0.7")
    print(f"  Base entry signals:       {base_entries}")
    print(f"  Pass BOTH gates:          {pass_both} ({pass_both / base_entries * 100:.1f}%)")
    print(f"  Blocked by accel ONLY:    {fail_accel_only} ({unique_accel:.1f}% of blocked)")
    print(f"  Blocked by comp ONLY:     {fail_comp_only} ({unique_comp:.1f}% of blocked)")
    print(f"  Blocked by BOTH:          {fail_both} ({overlap_pct:.1f}% of blocked)")
    print(f"  Total blocked:            {total_blocked} ({total_blocked / base_entries * 100:.1f}% of base)")

    if overlap_pct > 50:
        print("\n  -> HIGH OVERLAP: gates are mostly redundant (block same entries).")
    elif overlap_pct > 25:
        print("\n  -> MODERATE OVERLAP: gates partially redundant.")
    else:
        print("\n  -> LOW OVERLAP: gates are complementary (block DIFFERENT entries).")

    # ── 4. Win rate progression ──────────────────────────────────────
    print("\n" + "=" * 80)
    print("4. WIN RATE PROGRESSION — Does filtering improve selectivity?")
    print("=" * 80)

    print(f"\n  {'Config':20s} {'WinRate':>8s} {'d_WR':>8s} {'Trades':>7s}")
    print(f"  {'-' * 20} {'-' * 8} {'-' * 8} {'-' * 7}")
    for _, row in df.iterrows():
        wr = row["win_rate"]
        d_wr = wr - base_winrate if np.isfinite(wr) else np.nan
        wr_s = f"{wr:.1f}%" if np.isfinite(wr) else "N/A"
        d_wr_s = f"{d_wr:+.1f}pp" if np.isfinite(d_wr) else "N/A"
        print(f"  {row['config']:20s} {wr_s:>8s} {d_wr_s:>8s} {row['trades']:>7d}")

    # ── Verdict ──────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("VERDICT")
    print("=" * 80)

    best_triple = triples.loc[triples["d_sharpe"].idxmax()] if not triples.empty else None
    best_duo_row = df[df["config"].str.startswith("duo_")].loc[
        df[df["config"].str.startswith("duo_")]["d_sharpe"].idxmax()
    ]
    best_single_row = df[df["config"].str.startswith("ref_") & (df["config"] != "ref_baseline")].loc[
        df[df["config"].str.startswith("ref_") & (df["config"] != "ref_baseline")]["d_sharpe"].idxmax()
    ]

    if best_triple is not None:
        td = best_triple["d_sharpe"]
        duo_d = best_duo_row["d_sharpe"]
        single_d = best_single_row["d_sharpe"]

        print(f"\n  Best single: {best_single_row['config']} (d_Sharpe={single_d:+.4f})")
        print(f"  Best duo:    {best_duo_row['config']} (d_Sharpe={duo_d:+.4f})")
        print(f"  Best triple: {best_triple['config']} (d_Sharpe={td:+.4f})")
        print()

        print(f"  Best triple stats:")
        print(f"    Sharpe {best_triple['sharpe']}, CAGR {best_triple['cagr_pct']}%, "
              f"MDD {best_triple['mdd_pct']}%, trades {int(best_triple['trades'])}, "
              f"win rate {best_triple['win_rate']}%")
        print()

        beats_duo = td > duo_d
        beats_single = td > single_d
        trade_ok = best_triple["trades"] >= 100

        print(f"  Triple beats best duo:    {'YES' if beats_duo else 'NO'} ({td:+.4f} vs {duo_d:+.4f})")
        print(f"  Triple beats best single: {'YES' if beats_single else 'NO'} ({td:+.4f} vs {single_d:+.4f})")
        print(f"  Trade count >= 100:       {'YES' if trade_ok else 'NO'} ({int(best_triple['trades'])} trades)")
        print()

        if not trade_ok:
            print("CONCLUSION: OVER-FILTERED (X7 trap). Triple stack drops trade count")
            print("  below viable level. Use best duo or single instead.")
        elif beats_duo and beats_single:
            marginal = td - duo_d
            if marginal > 0.05:
                print("CONCLUSION: TRIPLE JUSTIFIED. Meaningful improvement over best duo.")
                print(f"  Marginal d_Sharpe from third mechanism: {marginal:+.4f}")
            else:
                print("CONCLUSION: MARGINAL GAIN. Triple barely beats best duo.")
                print(f"  Marginal d_Sharpe: {marginal:+.4f} — simpler duo may be preferable.")
        elif beats_single:
            print("CONCLUSION: TRIPLE < BEST DUO. Third mechanism adds no value over best duo.")
            print("  Use best duo configuration instead.")
        else:
            print("CONCLUSION: TRIPLE FAILS. Does not beat best single mechanism.")
            print("  Components interfere rather than complement.")

        # MDD comparison
        triple_mdd = best_triple["d_mdd"]
        duo_mdd = best_duo_row["d_mdd"]
        if triple_mdd < duo_mdd:
            print(f"\n  MDD bonus: triple ({triple_mdd:+.2f}pp) beats best duo ({duo_mdd:+.2f}pp).")
        elif triple_mdd < 0:
            print(f"\n  MDD: triple improves MDD ({triple_mdd:+.2f}pp) but not better than best duo ({duo_mdd:+.2f}pp).")


if __name__ == "__main__":
    main()
