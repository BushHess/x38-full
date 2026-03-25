"""
Phase 1: Raw Exploratory Reconnaissance — Entry Filter Lab
============================================================
Empirical-first. Observation before interpretation.
No formalization, no suggestion, no design.

Deliverables:
  - 00_data_audit.md
  - 01_raw_eda.md
  - figures/Fig01..Fig08
  - tables/data_audit_summary.csv, Tbl01..Tbl03
"""

import pathlib
import warnings

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore", category=FutureWarning)

# ── paths ──────────────────────────────────────────────────────────────
ROOT = pathlib.Path(__file__).resolve().parent.parent          # entry_filter_lab/
DATA = pathlib.Path("/var/www/trading-bots/btc-spot/data/bars_btcusdt_h1_4h_1d.csv")
FIG  = ROOT / "figures"
TBL  = ROOT / "tables"
FIG.mkdir(exist_ok=True)
TBL.mkdir(exist_ok=True)

# ── load ───────────────────────────────────────────────────────────────
raw = pd.read_csv(DATA)
print(f"Loaded {len(raw):,} rows, columns: {list(raw.columns)}")

# ======================================================================
# 1  DATA AUDIT
# ======================================================================
def data_audit(df: pd.DataFrame):
    """Full data audit → 00_data_audit.md + tables/data_audit_summary.csv"""
    lines = ["# Data Audit — Phase 1\n"]

    # --- schema & dtypes ---
    lines.append("## Schema\n")
    lines.append(f"Rows: {len(df):,}")
    lines.append(f"Columns: {len(df.columns)}")
    lines.append("")
    lines.append("| Column | dtype | nulls | unique |")
    lines.append("|--------|-------|-------|--------|")
    summary_rows = []
    for c in df.columns:
        n_null = int(df[c].isna().sum())
        n_uniq = int(df[c].nunique())
        lines.append(f"| {c} | {df[c].dtype} | {n_null} | {n_uniq} |")
        summary_rows.append(dict(column=c, dtype=str(df[c].dtype), nulls=n_null, unique=n_uniq))
    lines.append("")

    # --- intervals ---
    intervals = df["interval"].value_counts().to_dict()
    lines.append("## Interval counts\n")
    for k, v in sorted(intervals.items()):
        lines.append(f"- {k}: {v:,}")
    lines.append("")

    # --- per-interval audit ---
    for iv in ["4h", "1d"]:
        sub = df[df["interval"] == iv].copy()
        sub["open_time_dt"] = pd.to_datetime(sub["open_time"], unit="ms")
        sub["close_time_dt"] = pd.to_datetime(sub["close_time"], unit="ms")
        sub = sub.sort_values("open_time").reset_index(drop=True)

        lines.append(f"## Interval: {iv}\n")
        lines.append(f"Rows: {len(sub):,}")
        lines.append(f"Time range: {sub['open_time_dt'].iloc[0]} → {sub['open_time_dt'].iloc[-1]}")
        lines.append("")

        # monotonicity
        ot_mono = sub["open_time"].is_monotonic_increasing
        ct_mono = sub["close_time"].is_monotonic_increasing
        lines.append(f"open_time monotonic increasing: {ot_mono}")
        lines.append(f"close_time monotonic increasing: {ct_mono}")

        # duplicates
        dup_ot = sub.duplicated(subset=["open_time"]).sum()
        dup_full = sub.duplicated().sum()
        lines.append(f"Duplicate open_time: {dup_ot}")
        lines.append(f"Fully duplicate rows: {dup_full}")

        # gaps
        if iv == "4h":
            expected_gap_ms = 4 * 3600 * 1000
        else:
            expected_gap_ms = 24 * 3600 * 1000
        gaps = sub["open_time"].diff().dropna()
        gap_ok = (gaps == expected_gap_ms).sum()
        gap_bad = (gaps != expected_gap_ms).sum()
        lines.append(f"Expected gap: {expected_gap_ms / 3600_000:.0f}h")
        lines.append(f"Correct gaps: {gap_ok:,}  |  Anomalous gaps: {gap_bad:,}")
        if gap_bad > 0:
            bad_idx = gaps[gaps != expected_gap_ms].index
            lines.append(f"First 5 anomalous gap timestamps:")
            for idx in list(bad_idx[:5]):
                ts_prev = sub.loc[idx - 1, "open_time_dt"]
                ts_curr = sub.loc[idx, "open_time_dt"]
                gap_h = (sub.loc[idx, "open_time"] - sub.loc[idx - 1, "open_time"]) / 3600_000
                lines.append(f"  {ts_prev} → {ts_curr}  ({gap_h:.1f}h)")
        lines.append("")

        # close_time validity: should be open_time + interval - 1ms
        expected_close = sub["open_time"] + expected_gap_ms - 1
        close_ok = (sub["close_time"] == expected_close).sum()
        close_bad = (sub["close_time"] != expected_close).sum()
        lines.append(f"close_time = open_time + interval - 1ms: OK={close_ok:,}, BAD={close_bad}")
        lines.append("")

        # volume / taker_buy checks
        for vc in ["volume", "taker_buy_base_vol"]:
            n_neg = (sub[vc] < 0).sum()
            n_zero = (sub[vc] == 0).sum()
            lines.append(f"{vc}: negative={n_neg}, zero={n_zero}, "
                         f"min={sub[vc].min():.6f}, max={sub[vc].max():.2f}, "
                         f"median={sub[vc].median():.2f}")
        lines.append("")

        # taker_buy_ratio sanity
        ratio = sub["taker_buy_base_vol"] / sub["volume"]
        ratio_valid = ratio.replace([np.inf, -np.inf], np.nan).dropna()
        lines.append(f"taker_buy_ratio: min={ratio_valid.min():.4f}, max={ratio_valid.max():.4f}, "
                     f"mean={ratio_valid.mean():.4f}, median={ratio_valid.median():.4f}")
        n_gt1 = (ratio_valid > 1.0).sum()
        n_lt0 = (ratio_valid < 0.0).sum()
        lines.append(f"  >1.0: {n_gt1},  <0.0: {n_lt0}")
        lines.append("")

        # H4/D1 alignment check
        if iv == "4h":
            # check that every D1 bar date is covered by exactly 6 H4 bars
            sub["date"] = sub["open_time_dt"].dt.date
            bars_per_day = sub.groupby("date").size()
            n6 = (bars_per_day == 6).sum()
            nnot6 = (bars_per_day != 6).sum()
            lines.append(f"H4 bars per calendar day: 6 bars={n6:,}, !=6 bars={nnot6:,}")
            if nnot6 > 0:
                bad_days = bars_per_day[bars_per_day != 6]
                lines.append(f"  First 5 non-6 days: {list(bad_days.head(5).items())}")
            lines.append("")

    # save
    audit_path = ROOT / "00_data_audit.md"
    audit_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Written: {audit_path}")

    pd.DataFrame(summary_rows).to_csv(TBL / "data_audit_summary.csv", index=False)
    print(f"Written: {TBL / 'data_audit_summary.csv'}")


# ======================================================================
# 2  TAKER BUY RATIO
# ======================================================================
def taker_buy_ratio_plots(h4: pd.DataFrame):
    """Fig01: price + taker_buy_ratio, Fig02: yearly histograms"""
    h4 = h4.copy()
    h4["tbr"] = h4["taker_buy_base_vol"] / h4["volume"]
    h4["dt"] = pd.to_datetime(h4["open_time"], unit="ms")
    h4["year"] = h4["dt"].dt.year

    # Fig01
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 8), sharex=True,
                                     gridspec_kw={"height_ratios": [2, 1]})
    ax1.plot(h4["dt"], h4["close"], linewidth=0.4, color="black")
    ax1.set_ylabel("Close (USDT)")
    ax1.set_yscale("log")
    ax1.set_title("Fig01: H4 Close + Taker Buy Ratio (full period)")
    ax2.plot(h4["dt"], h4["tbr"], linewidth=0.3, color="steelblue", alpha=0.6)
    ax2.axhline(0.5, color="red", linewidth=0.8, linestyle="--", alpha=0.7)
    ax2.set_ylabel("Taker Buy Ratio")
    ax2.set_xlabel("Date")
    ax2.set_ylim(0.2, 0.8)
    for ax in (ax1, ax2):
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    plt.tight_layout()
    fig.savefig(FIG / "Fig01_h4_close_tbr.png", dpi=150)
    plt.close(fig)
    print("Written: Fig01")

    # Fig02: yearly histograms
    years = sorted(h4["year"].unique())
    n_years = len(years)
    ncols = 3
    nrows = int(np.ceil(n_years / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(14, 3 * nrows))
    axes = axes.flatten()
    for i, yr in enumerate(years):
        sub = h4[h4["year"] == yr]["tbr"].dropna()
        axes[i].hist(sub, bins=60, range=(0.3, 0.7), density=True, color="steelblue", alpha=0.7)
        axes[i].axvline(0.5, color="red", linewidth=0.8, linestyle="--")
        axes[i].set_title(f"{yr} (n={len(sub):,})")
        axes[i].set_xlim(0.3, 0.7)
    for j in range(i + 1, len(axes)):
        axes[j].set_visible(False)
    fig.suptitle("Fig02: Taker Buy Ratio Histogram by Year (H4)", fontsize=13, y=1.01)
    plt.tight_layout()
    fig.savefig(FIG / "Fig02_tbr_yearly_hist.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("Written: Fig02")


# ======================================================================
# 3  VOLUME BY BAR TYPE
# ======================================================================
def volume_by_bar_type(h4: pd.DataFrame):
    """Fig03, Fig04, Tbl01"""
    h4 = h4.copy()
    h4["ret"] = h4["close"].pct_change()
    h4["tbr"] = h4["taker_buy_base_vol"] / h4["volume"]
    h4 = h4.dropna(subset=["ret"]).copy()

    def classify(r):
        if r > 0.02:
            return "up_strong"
        elif r < -0.02:
            return "down_strong"
        else:
            return "sideway"
    h4["bar_type"] = h4["ret"].apply(classify)

    groups = ["up_strong", "down_strong", "sideway"]
    colors = {"up_strong": "forestgreen", "down_strong": "firebrick", "sideway": "gray"}

    # Fig03: volume distribution
    fig, ax = plt.subplots(figsize=(10, 5))
    data_vol = [h4[h4["bar_type"] == g]["volume"].values for g in groups]
    parts = ax.violinplot(data_vol, positions=[1, 2, 3], showmedians=True)
    for i, pc in enumerate(parts["bodies"]):
        pc.set_facecolor(list(colors.values())[i])
        pc.set_alpha(0.6)
    ax.set_xticks([1, 2, 3])
    ax.set_xticklabels(groups)
    ax.set_ylabel("Volume (BTC)")
    ax.set_title("Fig03: Volume Distribution by Bar Type (H4)")
    ax.set_yscale("log")
    plt.tight_layout()
    fig.savefig(FIG / "Fig03_volume_by_bartype.png", dpi=150)
    plt.close(fig)
    print("Written: Fig03")

    # Fig04: taker_buy_ratio distribution
    fig, ax = plt.subplots(figsize=(10, 5))
    data_tbr = [h4[h4["bar_type"] == g]["tbr"].dropna().values for g in groups]
    parts = ax.violinplot(data_tbr, positions=[1, 2, 3], showmedians=True)
    for i, pc in enumerate(parts["bodies"]):
        pc.set_facecolor(list(colors.values())[i])
        pc.set_alpha(0.6)
    ax.set_xticks([1, 2, 3])
    ax.set_xticklabels(groups)
    ax.set_ylabel("Taker Buy Ratio")
    ax.set_title("Fig04: Taker Buy Ratio by Bar Type (H4)")
    ax.axhline(0.5, color="red", linewidth=0.8, linestyle="--", alpha=0.5)
    plt.tight_layout()
    fig.savefig(FIG / "Fig04_tbr_by_bartype.png", dpi=150)
    plt.close(fig)
    print("Written: Fig04")

    # Mann-Whitney tests
    test_results = []
    for metric_name, metric_col in [("volume", "volume"), ("taker_buy_ratio", "tbr")]:
        for i in range(len(groups)):
            for j in range(i + 1, len(groups)):
                g1, g2 = groups[i], groups[j]
                x = h4[h4["bar_type"] == g1][metric_col].dropna().values
                y = h4[h4["bar_type"] == g2][metric_col].dropna().values
                u_stat, p_val = stats.mannwhitneyu(x, y, alternative="two-sided")
                # rank-biserial: r = 1 - 2U/(n1*n2)
                n1, n2 = len(x), len(y)
                r_rb = 1.0 - (2.0 * u_stat) / (n1 * n2)
                test_results.append(dict(
                    metric=metric_name,
                    group1=g1, group2=g2,
                    n1=n1, n2=n2,
                    U=u_stat, p_value=p_val,
                    rank_biserial=round(r_rb, 4),
                    median_g1=round(np.median(x), 6),
                    median_g2=round(np.median(y), 6),
                ))
    tbl = pd.DataFrame(test_results)
    tbl.to_csv(TBL / "Tbl01_bar_type_tests.csv", index=False)
    print(f"Written: Tbl01 ({len(tbl)} rows)")
    return tbl


# ======================================================================
# 4  AUTOCORRELATION
# ======================================================================
def autocorrelation_analysis(h4: pd.DataFrame):
    """Fig05: ACF for tbr, volume, returns"""
    h4 = h4.copy()
    h4["tbr"] = h4["taker_buy_base_vol"] / h4["volume"]
    h4["ret"] = h4["close"].pct_change()
    h4 = h4.dropna(subset=["ret", "tbr"]).reset_index(drop=True)

    max_lag = 20
    lags = np.arange(1, max_lag + 1)

    series_dict = {
        "taker_buy_ratio": h4["tbr"].values,
        "volume": h4["volume"].values,
        "H4_return": h4["ret"].values,
    }

    acf_results = {}
    for name, vals in series_dict.items():
        acfs = []
        for lag in lags:
            acfs.append(np.corrcoef(vals[:-lag], vals[lag:])[0, 1])
        acf_results[name] = acfs

    fig, ax = plt.subplots(figsize=(12, 5))
    markers = {"taker_buy_ratio": "o", "volume": "s", "H4_return": "^"}
    colors = {"taker_buy_ratio": "steelblue", "volume": "darkorange", "H4_return": "forestgreen"}
    for name, acfs in acf_results.items():
        ax.plot(lags, acfs, marker=markers[name], markersize=4, label=name,
                color=colors[name], linewidth=1.2)
    # 95% CI band
    n = len(h4)
    ci = 1.96 / np.sqrt(n)
    ax.axhline(ci, color="gray", linestyle="--", linewidth=0.7, alpha=0.6)
    ax.axhline(-ci, color="gray", linestyle="--", linewidth=0.7, alpha=0.6)
    ax.axhline(0, color="black", linewidth=0.5)
    ax.set_xlabel("Lag (H4 bars)")
    ax.set_ylabel("Autocorrelation")
    ax.set_title("Fig05: ACF Comparison (lag 1..20, H4)")
    ax.legend()
    ax.set_xticks(lags)
    plt.tight_layout()
    fig.savefig(FIG / "Fig05_acf_comparison.png", dpi=150)
    plt.close(fig)
    print("Written: Fig05")

    return acf_results


# ======================================================================
# 5  PREDICTIVE CONTENT (RAW)
# ======================================================================
def predictive_content(h4: pd.DataFrame):
    """Fig06a-c, Tbl02"""
    h4 = h4.copy()
    h4["tbr"] = h4["taker_buy_base_vol"] / h4["volume"]
    h4["ret"] = h4["close"].pct_change()

    horizons = {"t+1": 1, "t+6": 6, "t+24": 24}
    for label, shift in horizons.items():
        h4[f"fwd_{label}"] = h4["ret"].shift(-shift)

    h4 = h4.dropna(subset=["tbr"] + [f"fwd_{k}" for k in horizons]).reset_index(drop=True)

    corr_results = []
    for label, shift in horizons.items():
        x = h4["tbr"].values
        y = h4[f"fwd_{label}"].values
        rho, p = stats.spearmanr(x, y)
        corr_results.append(dict(
            horizon=label,
            shift_bars=shift,
            spearman_rho=round(rho, 6),
            p_value=p,
            n=len(x),
        ))

    tbl = pd.DataFrame(corr_results)
    tbl.to_csv(TBL / "Tbl02_forward_corr.csv", index=False)
    print(f"Written: Tbl02")

    # scatter plots
    for label, shift in horizons.items():
        fig, ax = plt.subplots(figsize=(8, 6))
        # subsample for readability
        n_plot = min(5000, len(h4))
        idx = np.random.RandomState(42).choice(len(h4), n_plot, replace=False)
        ax.scatter(h4["tbr"].iloc[idx], h4[f"fwd_{label}"].iloc[idx],
                   alpha=0.15, s=4, color="steelblue")
        rho_val = tbl[tbl["horizon"] == label]["spearman_rho"].values[0]
        p_val = tbl[tbl["horizon"] == label]["p_value"].values[0]
        ax.set_xlabel("Taker Buy Ratio (t)")
        ax.set_ylabel(f"Forward Return ({label})")
        ax.set_title(f"Fig06: TBR vs Forward Return {label}\n"
                     f"Spearman ρ = {rho_val:.4f}, p = {p_val:.2e}")
        ax.axhline(0, color="gray", linewidth=0.5)
        ax.axvline(0.5, color="red", linewidth=0.5, linestyle="--", alpha=0.5)
        plt.tight_layout()
        suffix = label.replace("+", "")
        fig.savefig(FIG / f"Fig06{chr(96 + list(horizons.keys()).index(label) + 1)}_tbr_vs_fwd_{suffix}.png",
                    dpi=150)
        plt.close(fig)
    print("Written: Fig06a, Fig06b, Fig06c")

    return tbl


# ======================================================================
# 6  REGIME DEPENDENCY
# ======================================================================
def regime_dependency(h4: pd.DataFrame):
    """Fig07, Tbl03"""
    h4 = h4.copy()
    h4["tbr"] = h4["taker_buy_base_vol"] / h4["volume"]
    h4["ret"] = h4["close"].pct_change()
    h4["ema126"] = h4["close"].ewm(span=126, adjust=False).mean()
    h4["regime"] = np.where(h4["close"] > h4["ema126"], "bull", "bear")

    horizons = {"t+1": 1, "t+6": 6, "t+24": 24}
    for label, shift in horizons.items():
        h4[f"fwd_{label}"] = h4["ret"].shift(-shift)

    h4 = h4.dropna(subset=["tbr", "ema126"] + [f"fwd_{k}" for k in horizons]).reset_index(drop=True)

    results = []
    for regime in ["bull", "bear"]:
        sub = h4[h4["regime"] == regime]
        for label, shift in horizons.items():
            x = sub["tbr"].values
            y = sub[f"fwd_{label}"].values
            rho, p = stats.spearmanr(x, y)
            results.append(dict(
                regime=regime,
                horizon=label,
                spearman_rho=round(rho, 6),
                p_value=p,
                n=len(x),
            ))

    tbl = pd.DataFrame(results)
    tbl.to_csv(TBL / "Tbl03_regime_corr.csv", index=False)
    print(f"Written: Tbl03")

    # Fig07: grouped bar chart
    fig, ax = plt.subplots(figsize=(10, 5))
    hor_labels = list(horizons.keys())
    x_pos = np.arange(len(hor_labels))
    width = 0.35
    bull_rhos = [tbl[(tbl["regime"] == "bull") & (tbl["horizon"] == h)]["spearman_rho"].values[0]
                 for h in hor_labels]
    bear_rhos = [tbl[(tbl["regime"] == "bear") & (tbl["horizon"] == h)]["spearman_rho"].values[0]
                 for h in hor_labels]

    ax.bar(x_pos - width / 2, bull_rhos, width, label="bull", color="forestgreen", alpha=0.7)
    ax.bar(x_pos + width / 2, bear_rhos, width, label="bear", color="firebrick", alpha=0.7)
    ax.set_xticks(x_pos)
    ax.set_xticklabels(hor_labels)
    ax.set_ylabel("Spearman ρ")
    ax.set_title("Fig07: TBR → Forward Return Correlation by Regime")
    ax.axhline(0, color="black", linewidth=0.5)
    ax.legend()
    # add value labels
    for i, (b, br) in enumerate(zip(bull_rhos, bear_rhos)):
        ax.text(i - width / 2, b + 0.001 * np.sign(b), f"{b:.4f}", ha="center", va="bottom" if b > 0 else "top", fontsize=8)
        ax.text(i + width / 2, br + 0.001 * np.sign(br), f"{br:.4f}", ha="center", va="bottom" if br > 0 else "top", fontsize=8)
    plt.tight_layout()
    fig.savefig(FIG / "Fig07_regime_corr.png", dpi=150)
    plt.close(fig)
    print("Written: Fig07")

    return tbl


# ======================================================================
# 7  STATIONARITY
# ======================================================================
def stationarity_rolling(h4: pd.DataFrame, window: int = 500):
    """Fig08: rolling Spearman correlation"""
    h4 = h4.copy()
    h4["tbr"] = h4["taker_buy_base_vol"] / h4["volume"]
    h4["ret"] = h4["close"].pct_change()
    h4["fwd_6"] = h4["ret"].shift(-6)
    h4 = h4.dropna(subset=["tbr", "fwd_6"]).reset_index(drop=True)
    h4["dt"] = pd.to_datetime(h4["open_time"], unit="ms")

    n = len(h4)
    roll_rho = np.full(n, np.nan)
    tbr_vals = h4["tbr"].values
    fwd_vals = h4["fwd_6"].values

    for i in range(window, n):
        x = tbr_vals[i - window:i]
        y = fwd_vals[i - window:i]
        rho, _ = stats.spearmanr(x, y)
        roll_rho[i] = rho

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 7), sharex=True,
                                     gridspec_kw={"height_ratios": [1, 2]})
    ax1.plot(h4["dt"], h4["close"], linewidth=0.4, color="black")
    ax1.set_ylabel("Close (USDT)")
    ax1.set_yscale("log")
    ax1.set_title("Fig08: Rolling Spearman ρ (TBR vs fwd 6-bar return, window=500)")

    ax2.plot(h4["dt"], roll_rho, linewidth=0.6, color="steelblue")
    ax2.axhline(0, color="red", linewidth=0.8, linestyle="--")
    ax2.fill_between(h4["dt"], roll_rho, 0, alpha=0.15, color="steelblue")
    ax2.set_ylabel("Rolling Spearman ρ")
    ax2.set_xlabel("Date")
    ax2.set_ylim(-0.15, 0.15)
    for ax in (ax1, ax2):
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    plt.tight_layout()
    fig.savefig(FIG / "Fig08_rolling_spearman.png", dpi=150)
    plt.close(fig)
    print("Written: Fig08")


# ======================================================================
# MAIN
# ======================================================================
def main():
    print("=" * 60)
    print("Phase 1: Raw Exploratory Reconnaissance")
    print("=" * 60)

    # ── 1. Data audit ──
    print("\n[1] Data Audit")
    data_audit(raw)

    # ── filter H4 & D1 ──
    h4 = raw[raw["interval"] == "4h"].copy().sort_values("open_time").reset_index(drop=True)
    d1 = raw[raw["interval"] == "1d"].copy().sort_values("open_time").reset_index(drop=True)
    print(f"\nH4: {len(h4):,} bars, D1: {len(d1):,} bars")

    # ── 2. Taker buy ratio ──
    print("\n[2] Taker Buy Ratio Plots")
    taker_buy_ratio_plots(h4)

    # ── 3. Volume by bar type ──
    print("\n[3] Volume by Bar Type")
    tbl01 = volume_by_bar_type(h4)
    print(tbl01.to_string(index=False))

    # ── 4. Autocorrelation ──
    print("\n[4] Autocorrelation")
    acf_res = autocorrelation_analysis(h4)
    for name, acfs in acf_res.items():
        print(f"  {name:20s}: lag1={acfs[0]:.4f}, lag5={acfs[4]:.4f}, lag20={acfs[19]:.4f}")

    # ── 5. Predictive content ──
    print("\n[5] Predictive Content (raw)")
    tbl02 = predictive_content(h4)
    print(tbl02.to_string(index=False))

    # ── 6. Regime dependency ──
    print("\n[6] Regime Dependency")
    tbl03 = regime_dependency(h4)
    print(tbl03.to_string(index=False))

    # ── 7. Stationarity ──
    print("\n[7] Rolling Stationarity")
    stationarity_rolling(h4)

    print("\n" + "=" * 60)
    print("Phase 1 script complete. All figures and tables written.")
    print("=" * 60)


if __name__ == "__main__":
    main()
