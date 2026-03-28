#!/usr/bin/env python3
"""Exp 47: Acceleration-Weighted Initial Trail.

Instead of binary accel gate (exp33), use acceleration MAGNITUDE to set
the initial trail multiplier continuously:
  - High acceleration (strong trend) -> wider trail (more room)
  - Low acceleration (weak trend)    -> tighter trail (more protection)

Option A: accel-weighted trail only (initial_trail fixed at entry).
Option B: accel-weighted + maturity decay (initial_trail decays toward trail_min).

10 configs: 4A + 4B + baseline + exp38-only reference.

Usage:
    python -m research.x39.experiments.exp47_accel_weighted_trail
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats as sp_stats

ROOT = Path(__file__).resolve().parents[3]  # btc-spot-dev/
sys.path.insert(0, str(ROOT))

from research.x39.explore import compute_features, load_data  # noqa: E402

RESULTS_DIR = Path(__file__).resolve().parents[1] / "results"

# ── Strategy constants (match E5-ema21D1) ─────────────────────────────────
SLOW_PERIOD = 120
BASELINE_TRAIL = 3.0
COST_BPS = 50
INITIAL_CASH = 10_000.0
WARMUP_DAYS = 365

# ── Accel feature params ─────────────────────────────────────────────────
ACCEL_LOOKBACK = 12       # ema_spread_roc lag (H4 bars)
ACCEL_WINDOW = 365        # percentile ranking window (H4 bars, ~61 days)


# ── Helpers ──────────────────────────────────────────────────────────────

def compute_trend_age(ema_fast: np.ndarray, ema_slow: np.ndarray) -> np.ndarray:
    """Bars since most recent EMA crossover (fast > slow)."""
    n = len(ema_fast)
    age = np.zeros(n, dtype=np.int32)
    for i in range(1, n):
        if ema_fast[i] > ema_slow[i]:
            age[i] = age[i - 1] + 1
    return age


def compute_accel_pctl(ema_spread_roc: np.ndarray, window: int) -> np.ndarray:
    """Percentile rank of ema_spread_roc in trailing `window` bars.

    Returns values in [0, 1]. NaN where insufficient history.
    """
    n = len(ema_spread_roc)
    pctl = np.full(n, np.nan)
    for i in range(window, n):
        if np.isnan(ema_spread_roc[i]):
            continue
        hist = ema_spread_roc[i - window : i]
        valid = hist[np.isfinite(hist)]
        if len(valid) < 30:  # need reasonable sample
            continue
        pctl[i] = np.mean(valid < ema_spread_roc[i])
    return pctl


def decay_trail(
    trend_age: int,
    initial_trail: float,
    trail_min: float,
    decay_start: int,
    decay_end: int,
) -> float:
    """Linear decay from initial_trail to trail_min between decay_start and decay_end."""
    if trend_age < decay_start:
        return initial_trail
    if trend_age >= decay_end:
        return trail_min
    progress = (trend_age - decay_start) / (decay_end - decay_start)
    return initial_trail - (initial_trail - trail_min) * progress


# ── Config ───────────────────────────────────────────────────────────────

class Config:
    __slots__ = (
        "name", "trail_low", "trail_high",
        "decay_min", "decay_start", "decay_end",
    )

    def __init__(
        self,
        name: str,
        trail_low: float | None = None,
        trail_high: float | None = None,
        decay_min: float | None = None,
        decay_start: int | None = None,
        decay_end: int | None = None,
    ) -> None:
        self.name = name
        self.trail_low = trail_low
        self.trail_high = trail_high
        self.decay_min = decay_min
        self.decay_start = decay_start
        self.decay_end = decay_end

    @property
    def has_accel(self) -> bool:
        return self.trail_low is not None

    @property
    def has_decay(self) -> bool:
        return self.decay_min is not None


CONFIGS = [
    # References
    Config("baseline"),
    Config("exp38_only", decay_min=1.5, decay_start=60, decay_end=180),
    # Option A — accel-weighted trail only
    Config("A1", trail_low=2.0, trail_high=3.0),
    Config("A2", trail_low=2.0, trail_high=4.0),
    Config("A3", trail_low=2.5, trail_high=3.5),
    Config("A4", trail_low=1.5, trail_high=3.0),
    # Option B — accel-weighted + maturity decay
    Config("B1", trail_low=2.0, trail_high=3.0, decay_min=1.5, decay_start=60, decay_end=180),
    Config("B2", trail_low=2.0, trail_high=4.0, decay_min=1.5, decay_start=60, decay_end=180),
    Config("B3", trail_low=2.5, trail_high=3.5, decay_min=1.5, decay_start=60, decay_end=180),
    Config("B4", trail_low=1.5, trail_high=3.0, decay_min=1.5, decay_start=60, decay_end=180),
]


# ── Backtest ─────────────────────────────────────────────────────────────

def run_backtest(
    feat: pd.DataFrame,
    trend_age: np.ndarray,
    accel_pctl: np.ndarray,
    warmup_bar: int,
    cfg: Config,
) -> dict:
    """Replay E5-ema21D1 with accel-weighted initial trail."""
    c = feat["close"].values
    ema_f = feat["ema_fast"].values
    ema_s = feat["ema_slow"].values
    ratr = feat["ratr"].values
    vdo_arr = feat["vdo"].values
    d1_ok = feat["d1_regime_ok"].values
    n = len(c)

    trades: list[dict] = []
    in_pos = False
    peak = 0.0
    entry_bar = 0
    entry_price = 0.0
    entry_trail = BASELINE_TRAIL  # initial trail for current trade

    equity = np.full(n, np.nan)
    cash = INITIAL_CASH
    position_size = 0.0

    initial_trails: list[float] = []  # for distribution analysis
    trail_at_exit: list[float] = []
    age_at_exit: list[int] = []

    for i in range(warmup_bar, n):
        if np.isnan(ratr[i]):
            equity[i] = cash if not in_pos else position_size * c[i]
            continue

        if not in_pos:
            equity[i] = cash

            entry_ok = ema_f[i] > ema_s[i] and vdo_arr[i] > 0 and d1_ok[i]

            if entry_ok:
                in_pos = True
                entry_bar = i
                entry_price = c[i]
                peak = c[i]

                # Determine initial trail
                if cfg.has_accel and np.isfinite(accel_pctl[i]):
                    entry_trail = cfg.trail_low + accel_pctl[i] * (cfg.trail_high - cfg.trail_low)
                elif cfg.name == "exp38_only":
                    entry_trail = BASELINE_TRAIL  # exp38 always starts at 3.0
                else:
                    entry_trail = BASELINE_TRAIL  # NaN fallback

                initial_trails.append(entry_trail)

                half_cost = (COST_BPS / 2) / 10_000
                position_size = cash * (1 - half_cost) / c[i]
                cash = 0.0
        else:
            equity[i] = position_size * c[i]
            peak = max(peak, c[i])

            # Determine current trail multiplier
            if cfg.has_decay:
                current_trail = decay_trail(
                    trend_age[i], entry_trail, cfg.decay_min,
                    cfg.decay_start, cfg.decay_end,
                )
            elif cfg.name == "exp38_only":
                # Pure exp38 reference: decay from 3.0 to 1.5
                current_trail = decay_trail(
                    trend_age[i], BASELINE_TRAIL, 1.5, 60, 180,
                )
            else:
                current_trail = entry_trail  # Option A: fixed at entry

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
                    "initial_trail": entry_trail,
                    "trail_at_exit": current_trail,
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

    # Correlation: initial_trail vs net_ret
    if cfg.has_accel and len(tdf) > 5:
        corr, corr_p = sp_stats.spearmanr(tdf["initial_trail"], tdf["net_ret"])
    else:
        corr, corr_p = np.nan, np.nan

    # Initial trail distribution
    it_arr = np.array(initial_trails)
    it_median = np.median(it_arr) if len(it_arr) > 0 else np.nan
    it_p10 = np.percentile(it_arr, 10) if len(it_arr) > 0 else np.nan
    it_p90 = np.percentile(it_arr, 90) if len(it_arr) > 0 else np.nan

    return {
        "config": cfg.name,
        "trail_low": cfg.trail_low if cfg.has_accel else "",
        "trail_high": cfg.trail_high if cfg.has_accel else "",
        "decay_min": cfg.decay_min if cfg.has_decay else "",
        "sharpe": round(sharpe, 4),
        "cagr_pct": round(cagr * 100, 2),
        "mdd_pct": round(abs(mdd) * 100, 2),
        "trades": len(trades),
        "win_rate": round(win_rate, 1),
        "avg_bars_held": round(tdf["bars_held"].mean(), 1),
        "exposure_pct": round(exposure * 100, 1),
        "it_median": round(it_median, 3) if np.isfinite(it_median) else np.nan,
        "it_p10": round(it_p10, 3) if np.isfinite(it_p10) else np.nan,
        "it_p90": round(it_p90, 3) if np.isfinite(it_p90) else np.nan,
        "corr_trail_ret": round(corr, 4) if np.isfinite(corr) else np.nan,
        "corr_p": round(corr_p, 4) if np.isfinite(corr_p) else np.nan,
        "avg_trail_exit": round(np.mean(trail_at_exit), 3) if trail_at_exit else np.nan,
        "avg_age_exit": round(np.mean(age_at_exit), 1) if age_at_exit else np.nan,
    }


def _empty_result(cfg: Config) -> dict:
    return {
        "config": cfg.name,
        "trail_low": cfg.trail_low if cfg.has_accel else "",
        "trail_high": cfg.trail_high if cfg.has_accel else "",
        "decay_min": cfg.decay_min if cfg.has_decay else "",
        "sharpe": np.nan, "cagr_pct": np.nan, "mdd_pct": np.nan,
        "trades": 0, "win_rate": np.nan, "avg_bars_held": np.nan,
        "exposure_pct": np.nan, "it_median": np.nan, "it_p10": np.nan,
        "it_p90": np.nan, "corr_trail_ret": np.nan, "corr_p": np.nan,
        "avg_trail_exit": np.nan, "avg_age_exit": np.nan,
    }


# ── Main ─────────────────────────────────────────────────────────────────

def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("EXP 47: Acceleration-Weighted Initial Trail")
    print("=" * 80)

    h4, d1 = load_data()
    feat = compute_features(h4, d1)

    ema_f = feat["ema_fast"].values
    ema_s = feat["ema_slow"].values
    n = len(feat)

    # ── Pre-compute indicators ───────────────────────────────────────
    print("Computing trend_age...")
    trend_age = compute_trend_age(ema_f, ema_s)

    print(f"Computing ema_spread_roc (lookback={ACCEL_LOOKBACK})...")
    with np.errstate(divide="ignore", invalid="ignore"):
        ema_spread = np.where(ema_s != 0, (ema_f - ema_s) / ema_s, np.nan)
    ema_spread_roc = np.full(n, np.nan)
    ema_spread_roc[ACCEL_LOOKBACK:] = (
        ema_spread[ACCEL_LOOKBACK:] - ema_spread[: n - ACCEL_LOOKBACK]
    )

    print(f"Computing accel_pctl (window={ACCEL_WINDOW})...")
    accel_pctl = compute_accel_pctl(ema_spread_roc, ACCEL_WINDOW)

    # Warmup
    bars_per_day = 24 / 4
    warmup_bar = int(WARMUP_DAYS * bars_per_day)
    print(f"Warmup bar: {warmup_bar} ({WARMUP_DAYS} days)")

    # Accel_pctl stats in eval window
    eval_pctl = accel_pctl[warmup_bar:]
    valid_pctl = eval_pctl[np.isfinite(eval_pctl)]
    print(f"accel_pctl stats (eval window): n={len(valid_pctl)}, "
          f"mean={valid_pctl.mean():.3f}, "
          f"median={np.median(valid_pctl):.3f}, "
          f"P10={np.percentile(valid_pctl, 10):.3f}, "
          f"P90={np.percentile(valid_pctl, 90):.3f}")

    # ── Run all configs ──────────────────────────────────────────────
    results = []
    for cfg in CONFIGS:
        print(f"\nRunning {cfg.name}...")
        r = run_backtest(feat, trend_age, accel_pctl, warmup_bar, cfg)
        results.append(r)
        corr_str = f", corr={r['corr_trail_ret']}" if np.isfinite(r.get("corr_trail_ret", np.nan)) else ""
        print(
            f"  Sharpe={r['sharpe']}, CAGR={r['cagr_pct']}%, MDD={r['mdd_pct']}%, "
            f"trades={r['trades']}, it_med={r['it_median']}{corr_str}"
        )

    # ── Results table ────────────────────────────────────────────────
    df = pd.DataFrame(results)

    base_sharpe = df.loc[df["config"] == "baseline", "sharpe"].values[0]
    base_cagr = df.loc[df["config"] == "baseline", "cagr_pct"].values[0]
    base_mdd = df.loc[df["config"] == "baseline", "mdd_pct"].values[0]

    df["d_sharpe"] = df["sharpe"] - base_sharpe
    df["d_cagr"] = df["cagr_pct"] - base_cagr
    df["d_mdd"] = df["mdd_pct"] - base_mdd  # negative = improvement

    # Delta vs exp38-only
    exp38_sharpe = df.loc[df["config"] == "exp38_only", "sharpe"].values[0]
    exp38_cagr = df.loc[df["config"] == "exp38_only", "cagr_pct"].values[0]
    exp38_mdd = df.loc[df["config"] == "exp38_only", "mdd_pct"].values[0]

    df["d_sharpe_vs_exp38"] = df["sharpe"] - exp38_sharpe
    df["d_cagr_vs_exp38"] = df["cagr_pct"] - exp38_cagr
    df["d_mdd_vs_exp38"] = df["mdd_pct"] - exp38_mdd

    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)
    print(df.to_string(index=False))

    out_path = RESULTS_DIR / "exp47_results.csv"
    df.to_csv(out_path, index=False)
    print(f"\n-> Saved to {out_path}")

    # ── Analysis 1: Option A vs baseline ─────────────────────────────
    print("\n" + "=" * 80)
    print("ANALYSIS 1: Option A (accel-weighted only) vs Baseline")
    print("=" * 80)

    option_a = df[df["config"].str.startswith("A")]
    for _, row in option_a.iterrows():
        tag = "BETTER" if row["d_sharpe"] > 0 and row["d_mdd"] < 0 else (
            "MIXED" if row["d_sharpe"] > 0 else "WORSE"
        )
        print(
            f"  {row['config']}: trail=[{row['trail_low']}-{row['trail_high']}]  "
            f"d_Sh={row['d_sharpe']:+.4f}, d_MDD={row['d_mdd']:+.2f}pp  "
            f"it_med={row['it_median']}, P10={row['it_p10']}, P90={row['it_p90']}  [{tag}]"
        )

    # ── Analysis 2: Option B vs exp38-only ───────────────────────────
    print("\n" + "=" * 80)
    print("ANALYSIS 2: Option B (accel + decay) vs exp38-only")
    print("=" * 80)

    option_b = df[df["config"].str.startswith("B")]
    for _, row in option_b.iterrows():
        tag = "BETTER" if row["d_sharpe_vs_exp38"] > 0 and row["d_mdd_vs_exp38"] < 0 else (
            "MIXED" if row["d_sharpe_vs_exp38"] > 0 else "WORSE"
        )
        print(
            f"  {row['config']}: trail=[{row['trail_low']}-{row['trail_high']}]  "
            f"d_Sh_vs38={row['d_sharpe_vs_exp38']:+.4f}, "
            f"d_MDD_vs38={row['d_mdd_vs_exp38']:+.2f}pp  "
            f"it_med={row['it_median']}  [{tag}]"
        )

    # ── Analysis 3: Initial trail distribution ───────────────────────
    print("\n" + "=" * 80)
    print("ANALYSIS 3: Initial Trail Distribution")
    print("=" * 80)

    accel_configs = df[df["config"].str.match(r"^[AB]\d")]
    for _, row in accel_configs.iterrows():
        spread = row["it_p90"] - row["it_p10"] if np.isfinite(row["it_p10"]) else np.nan
        range_width = float(row["trail_high"]) - float(row["trail_low"]) if row["trail_high"] != "" else np.nan
        utilization = spread / range_width * 100 if np.isfinite(range_width) and range_width > 0 else np.nan
        util_str = f"{utilization:.0f}%" if np.isfinite(utilization) else "N/A"
        print(
            f"  {row['config']}: median={row['it_median']:.3f}, "
            f"P10={row['it_p10']:.3f}, P90={row['it_p90']:.3f}, "
            f"P90-P10={spread:.3f}, range_util={util_str}"
        )

    # ── Analysis 4: Correlation (initial_trail vs net_ret) ───────────
    print("\n" + "=" * 80)
    print("ANALYSIS 4: Correlation (initial_trail vs trade net_ret)")
    print("=" * 80)
    print("  Positive = high trail entries do better (validates hypothesis)")

    for _, row in accel_configs.iterrows():
        sig = "*" if np.isfinite(row["corr_p"]) and row["corr_p"] < 0.05 else ""
        val_str = f"{row['corr_trail_ret']:+.4f} (p={row['corr_p']:.4f}){sig}" if np.isfinite(row["corr_trail_ret"]) else "N/A"
        print(f"  {row['config']}: rho={val_str}")

    # ── Analysis 5: B vs A (does decay add value to accel-weighted?) ─
    print("\n" + "=" * 80)
    print("ANALYSIS 5: B vs A (does maturity decay help accel-weighted trails?)")
    print("=" * 80)

    pairs = [("A1", "B1"), ("A2", "B2"), ("A3", "B3"), ("A4", "B4")]
    for a_name, b_name in pairs:
        a_row = df.loc[df["config"] == a_name]
        b_row = df.loc[df["config"] == b_name]
        if a_row.empty or b_row.empty:
            continue
        a_sh = a_row["sharpe"].values[0]
        b_sh = b_row["sharpe"].values[0]
        a_mdd = a_row["mdd_pct"].values[0]
        b_mdd = b_row["mdd_pct"].values[0]
        d_sh = b_sh - a_sh
        d_mdd = b_mdd - a_mdd
        tag = "DECAY_HELPS" if d_sh > 0 and d_mdd < 0 else (
            "MIXED" if d_sh > 0 or d_mdd < 0 else "DECAY_HURTS"
        )
        print(
            f"  {b_name} vs {a_name}: d_Sh={d_sh:+.4f}, d_MDD={d_mdd:+.2f}pp  [{tag}]"
        )

    # ── Verdict ──────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("VERDICT")
    print("=" * 80)

    all_variants = df[~df["config"].isin(["baseline", "exp38_only"])]
    improvements = all_variants[(all_variants["d_sharpe"] > 0) & (all_variants["d_mdd"] < 0)]

    if not improvements.empty:
        best = improvements.loc[improvements["d_sharpe"].idxmax()]
        print(
            f"PASS: {best['config']} improves both Sharpe ({best['d_sharpe']:+.4f}) "
            f"and MDD ({best['d_mdd']:+.2f} pp)"
        )
        print(
            f"  Sharpe {best['sharpe']}, CAGR {best['cagr_pct']}%, "
            f"MDD {best['mdd_pct']}%, trades {int(best['trades'])}"
        )
        if np.isfinite(best.get("corr_trail_ret", np.nan)):
            print(f"  Correlation (trail vs ret): rho={best['corr_trail_ret']:+.4f}, p={best['corr_p']:.4f}")
    else:
        sharpe_up = all_variants[all_variants["d_sharpe"] > 0]
        if not sharpe_up.empty:
            best = sharpe_up.loc[sharpe_up["d_sharpe"].idxmax()]
            print(
                f"MIXED: {best['config']} improves Sharpe ({best['d_sharpe']:+.4f}) "
                f"but MDD changes {best['d_mdd']:+.2f} pp"
            )
        else:
            print("FAIL: No accel-weighted trail config improves Sharpe over baseline.")
            print("Acceleration magnitude does NOT add value as continuous trail sizing.")

    # Best option A vs baseline
    best_a = option_a.loc[option_a["d_sharpe"].idxmax()] if not option_a.empty else None
    if best_a is not None:
        print(f"\n  Best Option A: {best_a['config']} "
              f"(d_Sh={best_a['d_sharpe']:+.4f}, d_MDD={best_a['d_mdd']:+.2f}pp)")

    # Best option B vs exp38
    best_b_vs38 = option_b.loc[option_b["d_sharpe_vs_exp38"].idxmax()] if not option_b.empty else None
    if best_b_vs38 is not None:
        print(f"  Best Option B vs exp38: {best_b_vs38['config']} "
              f"(d_Sh={best_b_vs38['d_sharpe_vs_exp38']:+.4f}, "
              f"d_MDD={best_b_vs38['d_mdd_vs_exp38']:+.2f}pp)")


if __name__ == "__main__":
    main()
