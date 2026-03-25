#!/usr/bin/env python3
"""03_real_vs_generator_diagnostics.py — Compare real BTC 4H vs Monte Carlo generator.

Computes identical diagnostic suites on:
  A) Real BTCUSDT spot 4H data from the project CSV
  B) The Student-t AR(1) generator used in Prompt 01 simulations

Diagnostics:
  1. Skewness
  2. Excess kurtosis (Fisher)
  3. Hill tail index (upper + lower tail)
  4. ACF of returns (lags 1-50)
  5. ACF of squared returns (lags 1-50)
  6. ACF of absolute returns (lags 1-50)
  7. Rolling-vol persistence (std of rolling vol / mean of rolling vol)
  8. Regime duration distribution (bull/bear regime lengths)
  9. Drawdown duration distribution

Output: JSON artifact + console summary.
"""

import json
import math
import sys
import time
from pathlib import Path

import numpy as np
from scipy import stats as sp_stats

sys.stdout.reconfigure(line_buffering=True)

ARTIFACTS_DIR = Path(__file__).parent
BARS_PER_YEAR_4H = 2190.0


# ════════════════════════════════════════════════════════════════════════════
# Diagnostic functions
# ════════════════════════════════════════════════════════════════════════════


def compute_acf(x: np.ndarray, max_lag: int = 50) -> list[float]:
    """Compute autocorrelation function for lags 1..max_lag."""
    n = len(x)
    xm = x - x.mean()
    var = float(np.sum(xm ** 2))
    if var < 1e-20:
        return [0.0] * max_lag
    acf = []
    for lag in range(1, max_lag + 1):
        if lag >= n:
            acf.append(0.0)
            continue
        acf.append(float(np.sum(xm[:n - lag] * xm[lag:]) / var))
    return acf


def hill_estimator(data: np.ndarray, k_frac: float = 0.05) -> float:
    """Hill tail index estimator on absolute values."""
    absvals = np.abs(data)
    absvals = absvals[absvals > 0]
    sorted_abs = np.sort(absvals)[::-1]
    k = max(10, int(k_frac * len(sorted_abs)))
    if k >= len(sorted_abs) or sorted_abs[k] <= 0:
        return float("nan")
    log_ratios = np.log(sorted_abs[:k] / sorted_abs[k])
    s = np.sum(log_ratios)
    if s <= 0:
        return float("nan")
    return float(k / s)


def hill_upper_lower(data: np.ndarray, k_frac: float = 0.05) -> tuple[float, float]:
    """Hill estimator separately for upper and lower tails."""
    pos = data[data > 0]
    neg = -data[data < 0]  # flip sign for lower tail
    alpha_upper = hill_estimator(pos, k_frac) if len(pos) > 50 else float("nan")
    alpha_lower = hill_estimator(neg, k_frac) if len(neg) > 50 else float("nan")
    return alpha_upper, alpha_lower


def rolling_vol_stats(returns: np.ndarray, window: int = 120) -> dict:
    """Rolling volatility statistics."""
    n = len(returns)
    if n < window + 10:
        return {"mean_vol": float("nan"), "std_vol": float("nan"), "cv_vol": float("nan"),
                "min_vol": float("nan"), "max_vol": float("nan"), "ratio_max_min": float("nan")}
    vols = np.array([returns[i:i + window].std() for i in range(n - window + 1)])
    mean_v = float(vols.mean())
    std_v = float(vols.std())
    return {
        "mean_vol": round(mean_v, 8),
        "std_vol": round(std_v, 8),
        "cv_vol": round(std_v / mean_v, 4) if mean_v > 1e-12 else float("nan"),
        "min_vol": round(float(vols.min()), 8),
        "max_vol": round(float(vols.max()), 8),
        "ratio_max_min": round(float(vols.max() / vols.min()), 2) if vols.min() > 1e-12 else float("nan"),
    }


def regime_durations(returns: np.ndarray, ema_period: int = 120) -> dict:
    """Compute bull/bear regime durations using EMA sign."""
    n = len(returns)
    if n < ema_period + 10:
        return {"bull_mean": float("nan"), "bear_mean": float("nan"),
                "bull_median": float("nan"), "bear_median": float("nan"),
                "n_regimes": 0}

    # Simple EMA of cumulative returns as regime indicator
    prices = np.cumprod(1.0 + returns)
    alpha = 2.0 / (ema_period + 1)
    ema = np.empty(n)
    ema[0] = prices[0]
    for i in range(1, n):
        ema[i] = alpha * prices[i] + (1 - alpha) * ema[i - 1]

    bull = prices > ema  # price above EMA = bull
    durations_bull = []
    durations_bear = []
    current_len = 1
    for i in range(1, n):
        if bull[i] == bull[i - 1]:
            current_len += 1
        else:
            if bull[i - 1]:
                durations_bull.append(current_len)
            else:
                durations_bear.append(current_len)
            current_len = 1
    # Final segment
    if bull[-1]:
        durations_bull.append(current_len)
    else:
        durations_bear.append(current_len)

    return {
        "bull_mean": round(float(np.mean(durations_bull)), 1) if durations_bull else float("nan"),
        "bear_mean": round(float(np.mean(durations_bear)), 1) if durations_bear else float("nan"),
        "bull_median": round(float(np.median(durations_bull)), 1) if durations_bull else float("nan"),
        "bear_median": round(float(np.median(durations_bear)), 1) if durations_bear else float("nan"),
        "bull_max": int(max(durations_bull)) if durations_bull else 0,
        "bear_max": int(max(durations_bear)) if durations_bear else 0,
        "n_bull_regimes": len(durations_bull),
        "n_bear_regimes": len(durations_bear),
        "n_regimes": len(durations_bull) + len(durations_bear),
    }


def drawdown_durations(returns: np.ndarray) -> dict:
    """Compute drawdown duration distribution."""
    equity = np.cumprod(1.0 + returns)
    peak = np.maximum.accumulate(equity)
    dd = 1.0 - equity / peak

    # Find drawdown episodes
    in_dd = dd > 0.001  # threshold for being "in drawdown"
    durations = []
    current_len = 0
    max_dd_in_episode = 0.0
    for i in range(len(dd)):
        if in_dd[i]:
            current_len += 1
            max_dd_in_episode = max(max_dd_in_episode, dd[i])
        else:
            if current_len > 0:
                durations.append((current_len, max_dd_in_episode))
            current_len = 0
            max_dd_in_episode = 0.0
    if current_len > 0:
        durations.append((current_len, max_dd_in_episode))

    if not durations:
        return {"n_episodes": 0, "mean_duration": float("nan"), "median_duration": float("nan"),
                "max_duration": 0, "p90_duration": float("nan"), "mean_depth_pct": float("nan")}

    lens = [d[0] for d in durations]
    depths = [d[1] * 100 for d in durations]
    return {
        "n_episodes": len(durations),
        "mean_duration": round(float(np.mean(lens)), 1),
        "median_duration": round(float(np.median(lens)), 1),
        "max_duration": int(max(lens)),
        "p90_duration": round(float(np.percentile(lens, 90)), 1),
        "mean_depth_pct": round(float(np.mean(depths)), 2),
        "max_depth_pct": round(float(max(depths)), 2),
    }


def full_diagnostics(returns: np.ndarray, label: str) -> dict:
    """Compute the full diagnostic suite on a return series."""
    n = len(returns)
    print(f"\n  [{label}] n={n} bars")

    # 1. Basic moments
    skew = float(sp_stats.skew(returns))
    kurt_excess = float(sp_stats.kurtosis(returns, fisher=True))  # Fisher = excess
    kurt_raw = kurt_excess + 3.0
    print(f"    skewness:       {skew:.4f}")
    print(f"    excess kurtosis:{kurt_excess:.2f}  (raw={kurt_raw:.2f})")

    # 2. Hill tail index
    alpha_both = hill_estimator(returns)
    alpha_upper, alpha_lower = hill_upper_lower(returns)
    print(f"    Hill α (both):  {alpha_both:.2f}")
    print(f"    Hill α (upper): {alpha_upper:.2f}")
    print(f"    Hill α (lower): {alpha_lower:.2f}")

    # 3. ACF of returns
    acf_ret = compute_acf(returns, 50)
    print(f"    ACF(r, lag=1):  {acf_ret[0]:.4f}")
    print(f"    ACF(r, lag=5):  {acf_ret[4]:.4f}")
    print(f"    ACF(r, lag=10): {acf_ret[9]:.4f}")

    # 4. ACF of squared returns (volatility clustering)
    acf_sq = compute_acf(returns ** 2, 50)
    print(f"    ACF(r², lag=1): {acf_sq[0]:.4f}")
    print(f"    ACF(r², lag=5): {acf_sq[4]:.4f}")
    print(f"    ACF(r², lag=10):{acf_sq[9]:.4f}")
    print(f"    ACF(r², lag=50):{acf_sq[49]:.4f}")

    # 5. ACF of absolute returns
    acf_abs = compute_acf(np.abs(returns), 50)
    print(f"    ACF(|r|, lag=1):{acf_abs[0]:.4f}")
    print(f"    ACF(|r|, lag=5):{acf_abs[4]:.4f}")
    print(f"    ACF(|r|, lag=50):{acf_abs[49]:.4f}")

    # 6. Rolling vol
    rvol = rolling_vol_stats(returns, window=120)
    print(f"    Rolling vol CV: {rvol['cv_vol']}")
    print(f"    Rolling vol max/min: {rvol['ratio_max_min']}")

    # 7. Regime durations
    regimes = regime_durations(returns, ema_period=120)
    print(f"    Regimes: {regimes['n_regimes']} total")
    print(f"    Bull mean/median: {regimes['bull_mean']}/{regimes['bull_median']} bars")
    print(f"    Bear mean/median: {regimes['bear_mean']}/{regimes['bear_median']} bars")

    # 8. Drawdown durations
    dd = drawdown_durations(returns)
    print(f"    DD episodes: {dd['n_episodes']}")
    print(f"    DD mean/median: {dd['mean_duration']}/{dd['median_duration']} bars")
    print(f"    DD max: {dd['max_duration']} bars, max depth: {dd.get('max_depth_pct', 'N/A')}%")

    # 9. Additional: Jarque-Bera test
    jb_stat, jb_p = sp_stats.jarque_bera(returns)

    # 10. Ljung-Box on |r| at lag 20 (manual)
    n_obs = len(returns)
    abs_acf = acf_abs[:20]
    lb_stat = n_obs * (n_obs + 2) * sum(a ** 2 / (n_obs - (i + 1)) for i, a in enumerate(abs_acf))

    return {
        "label": label,
        "n": n,
        "skewness": round(skew, 4),
        "excess_kurtosis": round(kurt_excess, 2),
        "kurtosis_raw": round(kurt_raw, 2),
        "hill_alpha_both": round(alpha_both, 2),
        "hill_alpha_upper": round(alpha_upper, 2),
        "hill_alpha_lower": round(alpha_lower, 2),
        "acf_returns": {f"lag_{i+1}": round(v, 4) for i, v in enumerate(acf_ret[:10])},
        "acf_returns_full": [round(v, 4) for v in acf_ret],
        "acf_squared": {f"lag_{i+1}": round(v, 4) for i, v in enumerate(acf_sq[:10])},
        "acf_squared_full": [round(v, 4) for v in acf_sq],
        "acf_absolute": {f"lag_{i+1}": round(v, 4) for i, v in enumerate(acf_abs[:10])},
        "acf_absolute_full": [round(v, 4) for v in acf_abs],
        "rolling_vol": rvol,
        "regimes": regimes,
        "drawdowns": dd,
        "jarque_bera_stat": round(float(jb_stat), 1),
        "jarque_bera_p": float(jb_p),
        "ljung_box_abs_lag20": round(float(lb_stat), 1),
        "mean_return": round(float(returns.mean()), 8),
        "std_return": round(float(returns.std()), 6),
        "min_return": round(float(returns.min()), 6),
        "max_return": round(float(returns.max()), 6),
        "p1_return": round(float(np.percentile(returns, 1)), 6),
        "p99_return": round(float(np.percentile(returns, 99)), 6),
    }


# ════════════════════════════════════════════════════════════════════════════
# Data loaders
# ════════════════════════════════════════════════════════════════════════════


def load_real_btc_4h(csv_path: str, start: str = "2019-01-01", end: str = "2026-02-20") -> np.ndarray:
    """Load real BTC 4H close prices and return log-returns."""
    import csv
    from datetime import datetime, timezone

    start_ms = int(datetime.strptime(start, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp() * 1000)
    end_ms = int(datetime.strptime(end, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp() * 1000)

    closes = []
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["interval"] != "4h":
                continue
            ct = int(row["close_time"])
            if ct < start_ms or ct > end_ms:
                continue
            closes.append(float(row["close"]))

    prices = np.array(closes, dtype=np.float64)
    returns = np.diff(prices) / prices[:-1]  # percentage returns
    print(f"  Loaded {len(prices)} 4H prices → {len(returns)} returns")
    print(f"  Period: {start} to {end}")
    return returns


def generate_student_t_returns(
    n_bars: int = 15000,
    vol: float = 0.0065,
    mean_excess: float = 0.0,
    phi: float = 0.15,
    df: float = 3.0,
    seed: int = 42,
) -> np.ndarray:
    """Generate returns from the Student-t AR(1) generator (Prompt 01 spec)."""
    rng = np.random.default_rng(seed)
    t_scale = vol * math.sqrt((df - 2) / df) if df > 2 else vol
    innovations = rng.standard_t(df, size=n_bars) * t_scale

    returns = np.empty(n_bars)
    returns[0] = mean_excess + innovations[0]
    for i in range(1, n_bars):
        returns[i] = mean_excess + phi * (returns[i - 1] - mean_excess) + innovations[i]

    return returns


# ════════════════════════════════════════════════════════════════════════════
# Main
# ════════════════════════════════════════════════════════════════════════════


def main():
    print("=" * 72)
    print("REAL BTC 4H vs MONTE CARLO GENERATOR — Diagnostic Comparison")
    print("=" * 72)

    csv_path = str(Path(__file__).resolve().parent.parent.parent / "data/bars_btcusdt_2016_now_h1_4h_1d.csv")
    print(f"\nData source: {csv_path}")

    # ── A. Real data ──
    print("\n" + "─" * 72)
    print("A. REAL BTC 4H DATA")
    print("─" * 72)
    real_returns = load_real_btc_4h(csv_path, start="2019-01-01", end="2026-02-20")
    real_diag = full_diagnostics(real_returns, "Real BTC 4H")

    # ── B. Generator (5 seeds, take median) ──
    print("\n" + "─" * 72)
    print("B. STUDENT-t AR(1) GENERATOR (Prompt 01 spec)")
    print("─" * 72)
    print("  Parameters: df=3.0, vol=0.0065, phi=0.15, n_bars=15000")

    # Single canonical run (seed=42)
    sim_returns = generate_student_t_returns(
        n_bars=len(real_returns),  # match real data length
        vol=float(real_returns.std()),  # match real vol
        mean_excess=float(real_returns.mean()),  # match real mean
        phi=0.15,
        df=3.0,
        seed=42,
    )
    sim_diag = full_diagnostics(sim_returns, "Generator (matched vol, seed=42)")

    # Also run with ORIGINAL parameters (not vol-matched)
    print("\n  --- Also with ORIGINAL Prompt 01 parameters (vol=0.0065) ---")
    sim_orig_returns = generate_student_t_returns(
        n_bars=15000,
        vol=0.0065,
        mean_excess=0.0,
        phi=0.15,
        df=3.0,
        seed=42,
    )
    sim_orig_diag = full_diagnostics(sim_orig_returns, "Generator (original params)")

    # ── C. Multi-seed statistics for generator variability ──
    print("\n  --- Generator variability (10 seeds) ---")
    seed_diags = []
    for seed in range(10):
        sr = generate_student_t_returns(
            n_bars=len(real_returns),
            vol=float(real_returns.std()),
            mean_excess=float(real_returns.mean()),
            phi=0.15,
            df=3.0,
            seed=seed * 1000,
        )
        sd = {
            "skewness": float(sp_stats.skew(sr)),
            "excess_kurtosis": float(sp_stats.kurtosis(sr, fisher=True)),
            "hill_alpha": hill_estimator(sr),
            "acf_sq_lag1": compute_acf(sr ** 2, 5)[0],
            "acf_sq_lag5": compute_acf(sr ** 2, 5)[4],
            "acf_abs_lag1": compute_acf(np.abs(sr), 5)[0],
            "rolling_vol_cv": rolling_vol_stats(sr, 120)["cv_vol"],
        }
        seed_diags.append(sd)

    # Compute ranges
    for key in seed_diags[0]:
        vals = [d[key] for d in seed_diags if not (isinstance(d[key], float) and math.isnan(d[key]))]
        if vals:
            print(f"    {key}: [{min(vals):.4f}, {max(vals):.4f}]  median={np.median(vals):.4f}")

    # ── D. Summary comparison table ──
    print("\n" + "=" * 72)
    print("SIDE-BY-SIDE COMPARISON")
    print("=" * 72)

    comparison = {
        "skewness": (real_diag["skewness"], sim_diag["skewness"]),
        "excess_kurtosis": (real_diag["excess_kurtosis"], sim_diag["excess_kurtosis"]),
        "hill_alpha_both": (real_diag["hill_alpha_both"], sim_diag["hill_alpha_both"]),
        "hill_alpha_upper": (real_diag["hill_alpha_upper"], sim_diag["hill_alpha_upper"]),
        "hill_alpha_lower": (real_diag["hill_alpha_lower"], sim_diag["hill_alpha_lower"]),
        "acf_r_lag1": (real_diag["acf_returns"]["lag_1"], sim_diag["acf_returns"]["lag_1"]),
        "acf_r_lag5": (real_diag["acf_returns"]["lag_5"], sim_diag["acf_returns"]["lag_5"]),
        "acf_r2_lag1": (real_diag["acf_squared"]["lag_1"], sim_diag["acf_squared"]["lag_1"]),
        "acf_r2_lag5": (real_diag["acf_squared"]["lag_5"], sim_diag["acf_squared"]["lag_5"]),
        "acf_r2_lag10": (real_diag["acf_squared"]["lag_10"], sim_diag["acf_squared"]["lag_10"]),
        "acf_abs_lag1": (real_diag["acf_absolute"]["lag_1"], sim_diag["acf_absolute"]["lag_1"]),
        "acf_abs_lag5": (real_diag["acf_absolute"]["lag_5"], sim_diag["acf_absolute"]["lag_5"]),
        "acf_abs_lag10": (real_diag["acf_absolute"]["lag_10"], sim_diag["acf_absolute"]["lag_10"]),
        "rolling_vol_cv": (real_diag["rolling_vol"]["cv_vol"], sim_diag["rolling_vol"]["cv_vol"]),
        "rolling_vol_max_min": (real_diag["rolling_vol"]["ratio_max_min"], sim_diag["rolling_vol"]["ratio_max_min"]),
        "regime_n": (real_diag["regimes"]["n_regimes"], sim_diag["regimes"]["n_regimes"]),
        "regime_bull_mean": (real_diag["regimes"]["bull_mean"], sim_diag["regimes"]["bull_mean"]),
        "regime_bear_mean": (real_diag["regimes"]["bear_mean"], sim_diag["regimes"]["bear_mean"]),
        "dd_n_episodes": (real_diag["drawdowns"]["n_episodes"], sim_diag["drawdowns"]["n_episodes"]),
        "dd_max_duration": (real_diag["drawdowns"]["max_duration"], sim_diag["drawdowns"]["max_duration"]),
        "dd_max_depth_pct": (real_diag["drawdowns"].get("max_depth_pct", "N/A"), sim_diag["drawdowns"].get("max_depth_pct", "N/A")),
        "mean_return": (real_diag["mean_return"], sim_diag["mean_return"]),
        "std_return": (real_diag["std_return"], sim_diag["std_return"]),
    }

    print(f"\n{'Metric':<24} {'Real BTC':>12} {'Generator':>12} {'Match?':>8}")
    print("-" * 58)
    for metric, (real_val, sim_val) in comparison.items():
        try:
            rv = float(real_val)
            sv = float(sim_val)
            if abs(rv) < 1e-8:
                match = "~" if abs(sv) < 0.01 else "MISS"
            else:
                ratio = abs(sv / rv) if rv != 0 else float("inf")
                if 0.5 <= ratio <= 2.0:
                    match = "OK"
                elif 0.25 <= ratio <= 4.0:
                    match = "WEAK"
                else:
                    match = "MISS"
        except (ValueError, TypeError):
            match = "?"
        print(f"{metric:<24} {str(real_val):>12} {str(sim_val):>12} {match:>8}")

    # ── Save artifacts ──
    artifact = {
        "real_data": real_diag,
        "generator_matched_vol": sim_diag,
        "generator_original_params": sim_orig_diag,
        "generator_variability_10_seeds": seed_diags,
        "comparison": {k: {"real": v[0], "generator": v[1]} for k, v in comparison.items()},
    }

    out_path = ARTIFACTS_DIR / "03_real_vs_generator.json"
    with open(out_path, "w") as f:
        json.dump(artifact, f, indent=2, default=str)
    print(f"\nSaved: {out_path}")


if __name__ == "__main__":
    main()
