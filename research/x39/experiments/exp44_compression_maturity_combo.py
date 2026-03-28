#!/usr/bin/env python3
"""Exp 44: Vol Compression Gate + Maturity Decay Combination.

Combines exp34 (vol compression entry gate) with exp38 (maturity trail decay).
They modify INDEPENDENT parts of the strategy:
  - exp34: blocks entries when vol_ratio_5_20 >= threshold (no compression)
  - exp38: tightens trail as trend ages (linear decay)

9 configs: baseline + exp34-only + exp38-only + 6 combos.
Key question: does combo achieve BOTH Sharpe >= exp34 AND MDD <= exp38?

Usage:
    python -m research.x39.experiments.exp44_compression_maturity_combo
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
    __slots__ = ("name", "compression_thr", "trail_min", "decay_start", "decay_end")

    def __init__(
        self,
        name: str,
        compression_thr: float | None = None,
        trail_min: float | None = None,
        decay_start: int | None = None,
        decay_end: int | None = None,
    ) -> None:
        self.name = name
        self.compression_thr = compression_thr
        self.trail_min = trail_min
        self.decay_start = decay_start
        self.decay_end = decay_end

    @property
    def has_compression(self) -> bool:
        return self.compression_thr is not None

    @property
    def has_decay(self) -> bool:
        return self.trail_min is not None


# ── 9 Configs from spec ──────────────────────────────────────────────────
CONFIGS = [
    Config("baseline"),
    Config("exp34_only", compression_thr=0.6),
    Config("exp38_only", trail_min=1.5, decay_start=60, decay_end=180),
    Config("combo_A", compression_thr=0.6, trail_min=1.5, decay_start=60, decay_end=180),
    Config("combo_B", compression_thr=0.7, trail_min=1.5, decay_start=60, decay_end=180),
    Config("combo_C", compression_thr=0.6, trail_min=1.5, decay_start=60, decay_end=240),
    Config("combo_D", compression_thr=0.6, trail_min=2.0, decay_start=60, decay_end=180),
    Config("combo_E", compression_thr=0.8, trail_min=1.5, decay_start=60, decay_end=180),
    Config("combo_F", compression_thr=0.5, trail_min=1.5, decay_start=60, decay_end=180),
]


def run_backtest(
    feat: pd.DataFrame,
    trend_age: np.ndarray,
    warmup_bar: int,
    cfg: Config,
) -> dict:
    """Replay E5-ema21D1 with optional compression gate + maturity decay."""
    c = feat["close"].values
    ema_f = feat["ema_fast"].values
    ema_s = feat["ema_slow"].values
    ratr = feat["ratr"].values
    vdo_arr = feat["vdo"].values
    d1_ok = feat["d1_regime_ok"].values
    vol_ratio = feat["vol_ratio_5_20"].values
    n = len(c)

    trades: list[dict] = []
    blocked_by_compression: list[int] = []
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
                # Compression gate (exp34)
                compression_ok = True
                if cfg.has_compression:
                    if np.isfinite(vol_ratio[i]):
                        compression_ok = vol_ratio[i] < cfg.compression_thr
                    else:
                        compression_ok = False

                if compression_ok:
                    in_pos = True
                    entry_bar = i
                    entry_price = c[i]
                    peak = c[i]
                    half_cost = (COST_BPS / 2) / 10_000
                    position_size = cash * (1 - half_cost) / c[i]
                    cash = 0.0
                else:
                    blocked_by_compression.append(i)
        else:
            equity[i] = position_size * c[i]
            peak = max(peak, c[i])

            # Maturity decay (exp38)
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
        "blocked_by_compression": len(blocked_by_compression),
        "avg_trend_age_exit": round(np.mean(age_at_exit), 1) if age_at_exit else np.nan,
        "avg_eff_trail_exit": round(np.mean(trail_at_exit), 3) if trail_at_exit else np.nan,
    }


def _empty_result(cfg: Config) -> dict:
    return {
        "config": cfg.name,
        "compression_thr": cfg.compression_thr if cfg.has_compression else "",
        "trail_min": cfg.trail_min if cfg.has_decay else "",
        "decay_start": cfg.decay_start if cfg.has_decay else "",
        "decay_end": cfg.decay_end if cfg.has_decay else "",
        "sharpe": np.nan, "cagr_pct": np.nan, "mdd_pct": np.nan,
        "trades": 0, "win_rate": np.nan, "avg_bars_held": np.nan,
        "exposure_pct": np.nan, "blocked_by_compression": 0,
        "avg_trend_age_exit": np.nan, "avg_eff_trail_exit": np.nan,
    }


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("EXP 44: Vol Compression Gate + Maturity Decay Combination")
    print("=" * 80)

    h4, d1 = load_data()
    feat = compute_features(h4, d1)

    ema_f = feat["ema_fast"].values
    ema_s = feat["ema_slow"].values

    # Pre-compute shared indicator
    print("Computing trend_age...")
    trend_age = compute_trend_age(ema_f, ema_s)

    # Warmup: 365 days
    bars_per_day = 24 / 4
    warmup_bar = int(WARMUP_DAYS * bars_per_day)
    print(f"Warmup bar: {warmup_bar} ({WARMUP_DAYS} days)")
    print(f"Configs: {len(CONFIGS)}")

    # ── Run all configs ──────────────────────────────────────────────
    results = []
    for cfg in CONFIGS:
        print(f"\nRunning {cfg.name}...")
        r = run_backtest(feat, trend_age, warmup_bar, cfg)
        results.append(r)
        print(
            f"  Sharpe={r['sharpe']}, CAGR={r['cagr_pct']}%, MDD={r['mdd_pct']}%, "
            f"trades={r['trades']}, blocked={r['blocked_by_compression']}"
        )

    # ── Results table ────────────────────────────────────────────────
    df = pd.DataFrame(results)

    base_sharpe = df.loc[df["config"] == "baseline", "sharpe"].values[0]
    base_cagr = df.loc[df["config"] == "baseline", "cagr_pct"].values[0]
    base_mdd = df.loc[df["config"] == "baseline", "mdd_pct"].values[0]

    df["d_sharpe"] = df["sharpe"] - base_sharpe
    df["d_cagr"] = df["cagr_pct"] - base_cagr
    df["d_mdd"] = df["mdd_pct"] - base_mdd  # negative = improvement

    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)
    print(df.to_string(index=False))

    out_path = RESULTS_DIR / "exp44_results.csv"
    df.to_csv(out_path, index=False)
    print(f"\n-> Saved to {out_path}")

    # ── Additivity analysis ──────────────────────────────────────────
    print("\n" + "=" * 80)
    print("ADDITIVITY ANALYSIS")
    print("=" * 80)

    exp34_delta = df.loc[df["config"] == "exp34_only", "d_sharpe"].values[0]
    exp38_delta = df.loc[df["config"] == "exp38_only", "d_sharpe"].values[0]
    sum_individual = exp34_delta + exp38_delta

    print(f"  exp34-only  d_Sharpe: {exp34_delta:+.4f}")
    print(f"  exp38-only  d_Sharpe: {exp38_delta:+.4f}")
    print(f"  Sum (if additive):    {sum_individual:+.4f}")
    print()

    combos = df[df["config"].str.startswith("combo_")]
    for _, row in combos.iterrows():
        combo_delta = row["d_sharpe"]
        if abs(sum_individual) > 1e-6:
            ratio = combo_delta / sum_individual
        else:
            ratio = np.nan
        label = (
            "SYNERGISTIC" if ratio > 1.05
            else "ADDITIVE" if ratio > 0.75
            else "PARTIALLY_ADDITIVE" if ratio > 0.50
            else "REDUNDANT"
        )
        print(
            f"  {row['config']:8s}: d_Sharpe={combo_delta:+.4f}, "
            f"ratio={ratio:.3f} [{label}]"
        )

    # ── Additivity for CAGR and MDD ─────────────────────────────────
    exp34_d_cagr = df.loc[df["config"] == "exp34_only", "d_cagr"].values[0]
    exp38_d_cagr = df.loc[df["config"] == "exp38_only", "d_cagr"].values[0]
    exp34_d_mdd = df.loc[df["config"] == "exp34_only", "d_mdd"].values[0]
    exp38_d_mdd = df.loc[df["config"] == "exp38_only", "d_mdd"].values[0]

    print(f"\n  CAGR additivity:")
    print(f"    exp34 d_CAGR: {exp34_d_cagr:+.2f}pp, exp38 d_CAGR: {exp38_d_cagr:+.2f}pp, sum: {exp34_d_cagr + exp38_d_cagr:+.2f}pp")
    for _, row in combos.iterrows():
        sum_cagr = exp34_d_cagr + exp38_d_cagr
        r_cagr = row["d_cagr"] / sum_cagr if abs(sum_cagr) > 1e-6 else np.nan
        print(f"    {row['config']:8s}: d_CAGR={row['d_cagr']:+.2f}pp, ratio={r_cagr:.3f}")

    print(f"\n  MDD additivity (negative = improvement):")
    print(f"    exp34 d_MDD: {exp34_d_mdd:+.2f}pp, exp38 d_MDD: {exp38_d_mdd:+.2f}pp, sum: {exp34_d_mdd + exp38_d_mdd:+.2f}pp")
    for _, row in combos.iterrows():
        sum_mdd = exp34_d_mdd + exp38_d_mdd
        r_mdd = row["d_mdd"] / sum_mdd if abs(sum_mdd) > 1e-6 else np.nan
        print(f"    {row['config']:8s}: d_MDD={row['d_mdd']:+.2f}pp, ratio={r_mdd:.3f}")

    # ── Gate overlap analysis ────────────────────────────────────────
    print("\n" + "=" * 80)
    print("GATE OVERLAP ANALYSIS")
    print("=" * 80)
    print("How many base entries pass vs fail the compression gate?")

    n = len(feat)
    vdo_arr = feat["vdo"].values
    d1_ok_arr = feat["d1_regime_ok"].values
    vol_ratio_arr = feat["vol_ratio_5_20"].values

    base_entries = 0
    compression_pass = 0
    compression_blocked = 0

    for i in range(warmup_bar, n):
        if np.isnan(feat["ratr"].values[i]):
            continue
        base_ok = ema_f[i] > ema_s[i] and vdo_arr[i] > 0 and d1_ok_arr[i]
        if base_ok:
            base_entries += 1
            if np.isfinite(vol_ratio_arr[i]) and vol_ratio_arr[i] < 0.6:
                compression_pass += 1
            else:
                compression_blocked += 1

    print(f"  Base entry signals:          {base_entries}")
    print(f"  Pass compression (thr=0.6):  {compression_pass}")
    print(f"  Blocked by compression:      {compression_blocked}")
    print(f"  Block rate:                  {compression_blocked / base_entries * 100:.1f}%")
    print()
    print("  (Maturity decay modifies EXIT, not entry -- no entry-level overlap to measure.)")
    print("  The two mechanisms are structurally independent: compression filters entries,")
    print("  decay tightens exits. Overlap = same TRADES affected by both.")

    # ── Key question: does combo achieve Sharpe>=exp34 AND MDD<=exp38? ──
    print("\n" + "=" * 80)
    print("KEY QUESTION: Sharpe >= exp34 AND MDD <= exp38?")
    print("=" * 80)

    exp34_r = df.loc[df["config"] == "exp34_only"].iloc[0]
    exp38_r = df.loc[df["config"] == "exp38_only"].iloc[0]

    print(f"  exp34-only: Sharpe={exp34_r['sharpe']}, MDD={exp34_r['mdd_pct']}%")
    print(f"  exp38-only: Sharpe={exp38_r['sharpe']}, MDD={exp38_r['mdd_pct']}%")
    print()

    for _, row in combos.iterrows():
        sharpe_ok = row["sharpe"] >= exp34_r["sharpe"]
        mdd_ok = row["mdd_pct"] <= exp38_r["mdd_pct"]
        status = "BOTH" if (sharpe_ok and mdd_ok) else ("SHARPE_ONLY" if sharpe_ok else ("MDD_ONLY" if mdd_ok else "NEITHER"))
        print(
            f"  {row['config']:8s}: Sharpe={row['sharpe']} ({'>=exp34' if sharpe_ok else '<exp34'}), "
            f"MDD={row['mdd_pct']}% ({'<=exp38' if mdd_ok else '>exp38'}) -> {status}"
        )

    # ── Verdict ──────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("VERDICT")
    print("=" * 80)

    best_combo = combos.loc[combos["d_sharpe"].idxmax()] if not combos.empty else None

    if best_combo is not None:
        combo_delta = best_combo["d_sharpe"]
        beats_34 = combo_delta > exp34_delta
        beats_38 = combo_delta > exp38_delta
        ratio = combo_delta / sum_individual if abs(sum_individual) > 1e-6 else np.nan

        print(f"Best combo: {best_combo['config']}")
        print(f"  Sharpe {best_combo['sharpe']}, CAGR {best_combo['cagr_pct']}%, MDD {best_combo['mdd_pct']}%")
        print(f"  d_Sharpe vs baseline: {combo_delta:+.4f}")
        print(f"  Beats exp34-only: {'YES' if beats_34 else 'NO'} ({combo_delta:+.4f} vs {exp34_delta:+.4f})")
        print(f"  Beats exp38-only: {'YES' if beats_38 else 'NO'} ({combo_delta:+.4f} vs {exp38_delta:+.4f})")
        print(f"  Additivity ratio: {ratio:.3f}")
        print()

        sharpe_ok = best_combo["sharpe"] >= exp34_r["sharpe"]
        mdd_ok = best_combo["mdd_pct"] <= exp38_r["mdd_pct"]

        if sharpe_ok and mdd_ok:
            print("CONCLUSION: STRICTLY BETTER. Combo achieves Sharpe >= exp34 AND MDD <= exp38.")
            print("  Compression's MDD penalty IS neutralized by maturity decay.")
        elif beats_34 and beats_38:
            if ratio > 0.75:
                print("CONCLUSION: ADDITIVE or better. Combination is justified --")
                print("  entry + exit independently contribute to improvement.")
            else:
                print("CONCLUSION: PARTIALLY ADDITIVE. Combination beats either alone")
                print("  but mechanisms share some of the same improvement pathway.")
        elif beats_34 or beats_38:
            print("CONCLUSION: MARGINAL. Combo beats one component but not both.")
            print("  Simpler single-mechanism may be preferable.")
        else:
            print("CONCLUSION: REDUNDANT. Combo does NOT beat either component alone.")
            print("  exp34 and exp38 capture the same improvement via different routes.")

        # MDD check
        combo_mdd = best_combo["d_mdd"]
        if combo_mdd < min(exp34_d_mdd, exp38_d_mdd):
            print(f"\n  MDD bonus: combo MDD improvement ({combo_mdd:+.2f}pp) beats both singles.")
        elif combo_mdd < 0:
            print(f"\n  MDD: combo improves MDD ({combo_mdd:+.2f}pp) but not better than best single.")


if __name__ == "__main__":
    main()
