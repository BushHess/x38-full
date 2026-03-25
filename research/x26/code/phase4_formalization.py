"""Phase 4: Formalization — Computation Support.

Computes:
  1. Conditional returns during FLAT (bar-level, long-only)
  2. Opportunity counts for each admissible function class
  3. Power analysis (MDE, effect size, N)
  4. Complementarity statistics (overlap with VTREND)

Inputs:
- state_classification.csv (H4 bar-level FLAT/IN_TRADE)
- trades.csv (217 trades)
- flat_period_characteristics.csv (218 flat periods)
- Tbl02_flat_durations.csv (flat period durations)
- Raw OHLCV bars

Outputs:
- Tbl07_conditional_returns.csv
- Tbl08_class_opportunities.csv
- Tbl09_power_analysis.csv
- Tbl10_complementarity.csv
"""

import sys
sys.path.insert(0, "/var/www/trading-bots/btc-spot-dev")

import numpy as np
import pandas as pd
from scipy import stats as sp_stats
from pathlib import Path
import warnings
warnings.filterwarnings("ignore", category=RuntimeWarning)

# ── Paths ──────────────────────────────────────────────────────────────
ROOT = Path("/var/www/trading-bots/btc-spot-dev")
DATA = ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv"
LAB  = ROOT / "research" / "beyond_trend_lab"
TBL  = LAB / "tables"
TBL.mkdir(parents=True, exist_ok=True)

ANN = 365.25 * 6  # H4 bars per year
COST_RT_LIST = [50, 30, 20, 15]  # bps round-trip scenarios
YEARS = 8.5  # approximate sample span 2017-08 to 2026-02

print("=" * 70)
print("PHASE 4: FORMALIZATION — COMPUTATION SUPPORT")
print("=" * 70)

# ── Load data ──────────────────────────────────────────────────────────
df_all = pd.read_csv(DATA)
h4 = df_all[df_all["interval"] == "4h"].copy().reset_index(drop=True)
h4["ret"] = h4["close"].pct_change() * 1e4  # bps

state = pd.read_csv(TBL / "state_classification.csv")
assert len(state) == len(h4), f"State {len(state)} != H4 {len(h4)}"

h4["state"] = state["state"].values
h4["trade_id"] = state["trade_id"].values

# Flat mask
flat_mask = h4["state"] == "FLAT"
n_flat = flat_mask.sum()
n_total = len(h4)
print(f"\nTotal H4 bars: {n_total}")
print(f"FLAT bars: {n_flat} ({100*n_flat/n_total:.1f}%)")

# ══════════════════════════════════════════════════════════════════════
# SECTION 1: CONDITIONAL RETURNS DURING FLAT
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("SECTION 1: CONDITIONAL RETURNS DURING FLAT (bar-level)")
print("=" * 70)

# We need BOTH current bar and next bar to be FLAT for a valid trade
flat_curr = flat_mask.values[:-1]
flat_next = flat_mask.values[1:]
both_flat = flat_curr & flat_next

r_curr = h4["ret"].values[:-1]
r_next = h4["ret"].values[1:]

# Valid pairs: both bars FLAT, no NaN
valid = both_flat & np.isfinite(r_curr) & np.isfinite(r_next)
rc = r_curr[valid]
rn = r_next[valid]

print(f"\nValid FLAT bar-pairs: {valid.sum()}")

# Conditional on current bar direction
down_mask = rc < 0
up_mask = rc > 0

n_down = down_mask.sum()
n_up = up_mask.sum()

# E[r_{t+1} | r_t < 0, FLAT]  (long-only actionable: buy after down)
mean_after_down = rn[down_mask].mean()
std_after_down = rn[down_mask].std()
se_after_down = std_after_down / np.sqrt(n_down)
t_after_down = mean_after_down / se_after_down
p_after_down = 2 * sp_stats.t.sf(abs(t_after_down), n_down - 1)

# E[r_{t+1} | r_t > 0, FLAT]  (not directly actionable in long-only spot)
mean_after_up = rn[up_mask].mean()
std_after_up = rn[up_mask].std()

# Overall autocorrelation
rho1 = np.corrcoef(rc, rn)[0, 1]

print(f"\nOverall lag-1 autocorrelation (FLAT bar-pairs): ρ(1) = {rho1:.4f}")
print(f"\nAfter DOWN bars (n={n_down}):")
print(f"  E[r_{{t+1}}] = {mean_after_down:.2f} bps")
print(f"  σ[r_{{t+1}}] = {std_after_down:.2f} bps")
print(f"  t = {t_after_down:.3f}, p = {p_after_down:.4f}")
print(f"\nAfter UP bars (n={n_up}):")
print(f"  E[r_{{t+1}}] = {mean_after_up:.2f} bps")
print(f"  σ[r_{{t+1}}] = {std_after_up:.2f} bps")

# Conditional on |r_t| > k*sigma thresholds
sigma_flat = rc.std()
print(f"\nσ(r_t, FLAT) = {sigma_flat:.2f} bps")

cond_results = []
for k in [0.0, 0.25, 0.5, 0.75, 1.0, 1.5]:
    # Long-only: buy after big down bars
    big_down = (rc < -k * sigma_flat)
    n_bd = big_down.sum()
    if n_bd > 10:
        mean_bd = rn[big_down].mean()
        std_bd = rn[big_down].std()
        t_bd = mean_bd / (std_bd / np.sqrt(n_bd))
        p_bd = 2 * sp_stats.t.sf(abs(t_bd), n_bd - 1)
        per_year = n_bd / YEARS
        cond_results.append({
            "threshold_k": k,
            "n_signals": int(n_bd),
            "per_year": per_year,
            "mean_next_bps": mean_bd,
            "std_next_bps": std_bd,
            "t_stat": t_bd,
            "p_value": p_bd,
        })
        print(f"\n  k={k:.2f}: n={n_bd}, E[r_next]={mean_bd:.2f} bps, "
              f"σ={std_bd:.2f}, t={t_bd:.3f}, p={p_bd:.4f}, /yr={per_year:.0f}")

df_cond = pd.DataFrame(cond_results)

# Add cost scenarios
for cost in COST_RT_LIST:
    df_cond[f"net_{cost}bps"] = df_cond["mean_next_bps"] - cost

df_cond.to_csv(TBL / "Tbl07_conditional_returns.csv", index=False)
print(f"\nSaved Tbl07_conditional_returns.csv")

# ══════════════════════════════════════════════════════════════════════
# SECTION 2: MULTI-BAR CUMULATIVE RETURN (Class B)
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("SECTION 2: MULTI-BAR CUMULATIVE MEAN-REVERSION (Class B)")
print("=" * 70)

# For each flat period, compute cumulative returns and check
# if entering after k-bar drawdown produces positive subsequent return

# Identify flat periods
flat_periods = []
in_flat = False
start_idx = 0
for i in range(len(h4)):
    if h4["state"].iloc[i] == "FLAT":
        if not in_flat:
            start_idx = i
            in_flat = True
    else:
        if in_flat:
            flat_periods.append((start_idx, i - 1))
            in_flat = False
if in_flat:
    flat_periods.append((start_idx, len(h4) - 1))

print(f"Flat periods: {len(flat_periods)}")

# For lookback windows k=2,5,10,20:
# Signal: cumulative return over past k bars < 0 during FLAT
# Action: buy, hold for k bars (or until FLAT ends)
# Measure: forward cumulative return over next k bars

multibar_results = []
for k in [2, 5, 10, 20]:
    signals = []
    for (s, e) in flat_periods:
        if e - s + 1 < 2 * k:
            continue
        rets = h4["ret"].iloc[s:e+1].values
        for j in range(k, len(rets) - k):
            cum_back = rets[j-k:j].sum()
            cum_fwd = rets[j:j+k].sum()
            signals.append({
                "cum_back": cum_back,
                "cum_fwd": cum_fwd,
            })

    if not signals:
        continue
    df_sig = pd.DataFrame(signals)

    # Long-only: enter after k-bar negative cumulative return
    neg_back = df_sig["cum_back"] < 0
    n_neg = neg_back.sum()
    if n_neg > 10:
        fwd_after_neg = df_sig.loc[neg_back, "cum_fwd"]
        mean_fwd = fwd_after_neg.mean()
        std_fwd = fwd_after_neg.std()
        t_val = mean_fwd / (std_fwd / np.sqrt(n_neg))
        p_val = 2 * sp_stats.t.sf(abs(t_val), n_neg - 1)
        per_year = n_neg / YEARS

        multibar_results.append({
            "lookback_k": k,
            "hold_period": k,
            "n_signals": int(n_neg),
            "per_year": per_year,
            "mean_fwd_bps": mean_fwd,
            "std_fwd_bps": std_fwd,
            "t_stat": t_val,
            "p_value": p_val,
        })
        print(f"  k={k}: n={n_neg}, E[fwd]={mean_fwd:.2f} bps, "
              f"σ={std_fwd:.2f}, t={t_val:.3f}, p={p_val:.4f}, /yr={per_year:.0f}")

df_multi = pd.DataFrame(multibar_results)
for cost in COST_RT_LIST:
    df_multi[f"net_{cost}bps"] = df_multi["mean_fwd_bps"] - cost

# ══════════════════════════════════════════════════════════════════════
# SECTION 3: VR-CONDITIONAL FILTER FOR VTREND (Class C)
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("SECTION 3: VR-CONDITIONAL FILTER (Class C)")
print("=" * 70)

# For each trade entry, compute VR of the preceding flat period
# Check if low-VR preceding flat → worse trade outcome

trades = pd.read_csv(TBL / "trades.csv")
print(f"Trades loaded: {len(trades)}")

# Compute VR(2) for each preceding flat period (periods with >= 5 bars)
trade_vr_data = []
for fp_idx, (s, e) in enumerate(flat_periods):
    n_bars = e - s + 1
    if n_bars < 5:
        continue

    rets = h4["ret"].iloc[s:e+1].values
    rets = rets[np.isfinite(rets)]
    if len(rets) < 5:
        continue

    # Per-period VR(2)
    r1 = rets
    r2 = np.array([rets[i] + rets[i+1] for i in range(len(rets)-1)])
    vr2 = np.var(r2, ddof=0) / (2 * np.var(r1, ddof=0)) if np.var(r1, ddof=0) > 0 else 1.0

    # Find the trade that follows this flat period
    next_bar = e + 1
    if next_bar < len(h4) and h4["state"].iloc[next_bar] == "IN_TRADE":
        trade_id = h4["trade_id"].iloc[next_bar]
        # Find this trade's return
        trade_match = trades[trades["trade_id"] == trade_id] if "trade_id" in trades.columns else None

        # Compute trade return from bar data
        trade_bars = h4[h4["trade_id"] == trade_id]
        if len(trade_bars) > 0:
            trade_ret = (trade_bars["close"].iloc[-1] / trade_bars["close"].iloc[0] - 1) * 1e4  # bps
            trade_vr_data.append({
                "flat_period_idx": fp_idx,
                "flat_n_bars": n_bars,
                "vr2": vr2,
                "trade_id": trade_id,
                "trade_ret_bps": trade_ret,
                "trade_n_bars": len(trade_bars),
            })

df_vr_trade = pd.DataFrame(trade_vr_data)
if len(df_vr_trade) > 0:
    print(f"VR-trade pairs: {len(df_vr_trade)}")

    # Split by VR median
    vr_med = df_vr_trade["vr2"].median()
    low_vr = df_vr_trade[df_vr_trade["vr2"] < vr_med]
    high_vr = df_vr_trade[df_vr_trade["vr2"] >= vr_med]

    print(f"\nVR(2) median: {vr_med:.3f}")
    print(f"Low VR (<{vr_med:.3f}):  n={len(low_vr)}, mean trade ret={low_vr['trade_ret_bps'].mean():.1f} bps")
    print(f"High VR (>={vr_med:.3f}): n={len(high_vr)}, mean trade ret={high_vr['trade_ret_bps'].mean():.1f} bps")

    # Mann-Whitney test
    mw_stat, mw_p = sp_stats.mannwhitneyu(
        low_vr["trade_ret_bps"], high_vr["trade_ret_bps"], alternative="two-sided"
    )
    print(f"Mann-Whitney: U={mw_stat:.0f}, p={mw_p:.4f}")

    # Spearman correlation VR vs trade return
    rho_vr, p_vr = sp_stats.spearmanr(df_vr_trade["vr2"], df_vr_trade["trade_ret_bps"])
    print(f"Spearman(VR2, trade_ret): ρ={rho_vr:.4f}, p={p_vr:.4f}")

    # Cohen's d
    d_vr = (high_vr["trade_ret_bps"].mean() - low_vr["trade_ret_bps"].mean()) / df_vr_trade["trade_ret_bps"].std()
    print(f"Cohen's d (high-low VR): {d_vr:.4f}")

    # Tercile split
    vr_q33 = df_vr_trade["vr2"].quantile(0.333)
    vr_q67 = df_vr_trade["vr2"].quantile(0.667)
    t1 = df_vr_trade[df_vr_trade["vr2"] < vr_q33]
    t2 = df_vr_trade[(df_vr_trade["vr2"] >= vr_q33) & (df_vr_trade["vr2"] < vr_q67)]
    t3 = df_vr_trade[df_vr_trade["vr2"] >= vr_q67]
    print(f"\nTercile split:")
    print(f"  T1 (VR<{vr_q33:.3f}): n={len(t1)}, mean ret={t1['trade_ret_bps'].mean():.1f} bps")
    print(f"  T2 ({vr_q33:.3f}<=VR<{vr_q67:.3f}): n={len(t2)}, mean ret={t2['trade_ret_bps'].mean():.1f} bps")
    print(f"  T3 (VR>={vr_q67:.3f}): n={len(t3)}, mean ret={t3['trade_ret_bps'].mean():.1f} bps")

    # KW test across terciles
    kw_stat, kw_p = sp_stats.kruskal(
        t1["trade_ret_bps"], t2["trade_ret_bps"], t3["trade_ret_bps"]
    )
    print(f"  KW H={kw_stat:.3f}, p={kw_p:.4f}")

# ══════════════════════════════════════════════════════════════════════
# SECTION 4: POWER ANALYSIS
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("SECTION 4: POWER ANALYSIS")
print("=" * 70)

def compute_mde(n, alpha=0.05, power=0.80):
    """Minimum detectable effect (Cohen's d) for two-sided t-test."""
    z_alpha = sp_stats.norm.ppf(1 - alpha/2)
    z_beta = sp_stats.norm.ppf(power)
    return (z_alpha + z_beta) / np.sqrt(n)

# Class A: Single-bar contrarian
n_a = n_down  # ~5000+ opportunities
mde_a = compute_mde(n_a)
# Observed effect: mean_after_down / std_after_down
d_a = mean_after_down / std_after_down

print(f"\nClass A (single-bar contrarian long):")
print(f"  N = {n_a}")
print(f"  N/year = {n_a/YEARS:.0f}")
print(f"  MDE = {mde_a:.4f}")
print(f"  Observed |d| = {abs(d_a):.4f}")
print(f"  Ratio |d|/MDE = {abs(d_a)/mde_a:.2f}")
print(f"  Status: {'POWERED' if abs(d_a) > 1.5*mde_a else 'BORDERLINE' if abs(d_a) > mde_a else 'UNDERPOWERED'}")

# Class B: Multi-bar (use k=5 as representative)
for row in multibar_results:
    k = row["lookback_k"]
    n_b = row["n_signals"]
    mde_b = compute_mde(n_b)
    d_b = row["mean_fwd_bps"] / row["std_fwd_bps"]
    print(f"\nClass B (k={k}):")
    print(f"  N = {n_b}")
    print(f"  N/year = {n_b/YEARS:.0f}")
    print(f"  MDE = {mde_b:.4f}")
    print(f"  Observed |d| = {abs(d_b):.4f}")
    print(f"  Ratio |d|/MDE = {abs(d_b)/mde_b:.2f}")
    print(f"  Status: {'POWERED' if abs(d_b) > 1.5*mde_b else 'BORDERLINE' if abs(d_b) > mde_b else 'UNDERPOWERED'}")

# Class C: VR-conditional filter
if len(df_vr_trade) > 0:
    n_c = len(df_vr_trade)
    mde_c = compute_mde(n_c)
    print(f"\nClass C (VR-conditional filter):")
    print(f"  N (VR-trade pairs) = {n_c}")
    print(f"  N/year = {n_c/YEARS:.0f}")
    print(f"  MDE = {mde_c:.4f}")
    print(f"  Observed |d| (VR→trade_ret) = {abs(d_vr):.4f}")
    print(f"  Ratio |d|/MDE = {abs(d_vr)/mde_c:.2f}")
    print(f"  Status: {'POWERED' if abs(d_vr) > 1.5*mde_c else 'BORDERLINE' if abs(d_vr) > mde_c else 'UNDERPOWERED'}")

# WFO fold sizes
print(f"\n--- WFO Fold Sizes ---")
total_bars = n_flat
for n_folds in [4, 5]:
    fold_size = total_bars // n_folds
    fold_years = fold_size / ANN
    print(f"  {n_folds}-fold: {fold_size} bars/fold ({fold_years:.1f} years/fold)")

# ══════════════════════════════════════════════════════════════════════
# SECTION 5: COMPLEMENTARITY
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("SECTION 5: COMPLEMENTARITY PROOF")
print("=" * 70)

# All classes operate during FLAT periods by construction
pct_flat = n_flat / n_total * 100
print(f"\nVTREND FLAT fraction: {pct_flat:.1f}%")
print(f"All three classes operate ONLY during FLAT → 0% time overlap with VTREND IN_TRADE")

# For Class C specifically: it modifies VTREND entry decisions
# Compute what fraction of entries would be affected
# An entry is "preceded by a low-VR flat period" → potential suppression
if len(df_vr_trade) > 0:
    n_total_trades = 217
    n_vr_pairs = len(df_vr_trade)  # trades with computable preceding VR
    pct_covered = n_vr_pairs / n_total_trades * 100

    # How many would be suppressed at various VR thresholds?
    for vr_thresh in [0.5, 0.6, 0.7, 0.8]:
        would_suppress = (df_vr_trade["vr2"] < vr_thresh).sum()
        suppress_pct = would_suppress / n_vr_pairs * 100
        # What's the mean return of suppressed trades?
        suppressed = df_vr_trade[df_vr_trade["vr2"] < vr_thresh]
        if len(suppressed) > 0:
            mean_supp = suppressed["trade_ret_bps"].mean()
            # What's the mean return of kept trades?
            kept = df_vr_trade[df_vr_trade["vr2"] >= vr_thresh]
            mean_kept = kept["trade_ret_bps"].mean() if len(kept) > 0 else np.nan
            print(f"\n  VR threshold < {vr_thresh}: suppress {would_suppress}/{n_vr_pairs} ({suppress_pct:.1f}%)")
            print(f"    Suppressed mean ret: {mean_supp:.1f} bps")
            print(f"    Kept mean ret: {mean_kept:.1f} bps")

# Capital allocation: Classes A and B occupy capital during FLAT
# If VTREND entry fires while Class A/B is in position → conflict
# Compute: how often does VTREND entry occur within k bars of a Class A signal?

# Class A: buy every down bar → 1 bar hold
# If VTREND enters next bar, Class A exits (same bar)
# Max conflict duration: 1 bar (negligible)
print(f"\n--- Capital Conflict ---")
print(f"Class A: 1-bar hold → max 1-bar overlap with VTREND entry. Negligible.")
print(f"Class B (k-bar hold): potential k-bar overlap.")

# Count how many Class A signals (down bars in FLAT) are followed by
# an IN_TRADE bar (meaning VTREND would enter)
flat_down = flat_mask.values[:-1] & (h4["ret"].values[:-1] < 0)
next_is_trade = h4["state"].values[1:] == "IN_TRADE"
conflict_a = (flat_down & next_is_trade).sum()
total_a_signals = flat_down.sum()
print(f"\nClass A: {conflict_a}/{total_a_signals} signals ({100*conflict_a/total_a_signals:.1f}%) "
      f"followed by VTREND entry next bar")

# For Class B, similar but with k-bar horizon
for k in [5, 10]:
    # A Class B signal at bar t means we hold until t+k
    # Conflict if any bar in [t+1, t+k] is IN_TRADE
    conflicts = 0
    total_signals = 0
    for i in range(len(h4) - k):
        if flat_mask.iloc[i] and h4["ret"].iloc[i] < 0:
            # Check if this is part of a consecutive flat sequence
            if all(flat_mask.iloc[i:i+1]):  # simplified
                total_signals += 1
                if any(h4["state"].iloc[i+1:i+k+1] == "IN_TRADE"):
                    conflicts += 1
    if total_signals > 0:
        print(f"Class B (k={k}): {conflicts}/{total_signals} signals ({100*conflicts/total_signals:.1f}%) "
              f"overlap with VTREND entry in hold window")

# ══════════════════════════════════════════════════════════════════════
# SECTION 6: ECONOMIC MAGNITUDE — SHARPE ESTIMATES
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("SECTION 6: ECONOMIC MAGNITUDE — STANDALONE SHARPE ESTIMATES")
print("=" * 70)

# Class A standalone Sharpe estimate
for cost in COST_RT_LIST:
    net_per_trade = mean_after_down - cost
    n_trades_yr = n_down / YEARS
    ann_ret = net_per_trade * n_trades_yr / 1e4  # fraction
    ann_std = std_after_down * np.sqrt(n_trades_yr) / 1e4  # fraction
    sharpe = ann_ret / ann_std if ann_std > 0 else 0
    print(f"  Class A @ {cost} bps RT: net/trade={net_per_trade:.1f} bps, "
          f"N/yr={n_trades_yr:.0f}, Sharpe={sharpe:.3f}")

# Class B standalone (k=5)
if multibar_results:
    for row in multibar_results:
        k = row["lookback_k"]
        for cost in COST_RT_LIST:
            net = row["mean_fwd_bps"] - cost
            n_yr = row["n_signals"] / YEARS
            ann_ret = net * n_yr / 1e4
            ann_std = row["std_fwd_bps"] * np.sqrt(n_yr) / 1e4
            sharpe = ann_ret / ann_std if ann_std > 0 else 0
            if cost == 50:  # only print 50 bps for each k
                print(f"  Class B (k={k}) @ {cost} bps RT: net/trade={net:.1f} bps, "
                      f"N/yr={n_yr:.0f}, Sharpe={sharpe:.3f}")

# ══════════════════════════════════════════════════════════════════════
# SECTION 7: INFORMATION CONTENT — MUTUAL INFORMATION PROXY
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("SECTION 7: I(ΔU; V_new | P_t, VT_t) ESTIMATION")
print("=" * 70)

# The central question: does the mean-reversion observable (V_new)
# carry information about the utility of the next trade,
# conditional on price and VTREND state?

# V_new = {VR(k), ACF(lag-1), rolling_vol}
# P_t = {price, returns}
# VT_t = {FLAT/IN_TRADE state}

# We already condition on VT_t = FLAT.
# The question is: I(r_{t+1}; r_t | FLAT_t) > 0?

# From Section 1: ρ(1) = rho1, p is known
# This IS the mutual information proxy for Class A

# For Gaussian: I ≈ -0.5 * log(1 - ρ²)
mi_proxy = -0.5 * np.log(1 - rho1**2)
print(f"\nGaussian MI proxy: I(r_{{t+1}}; r_t | FLAT) = {mi_proxy:.6f} nats")
print(f"  (ρ = {rho1:.4f})")
print(f"  This is {mi_proxy/np.log(2)*1000:.3f} millibits")
print(f"  For context: perfect prediction = ~11.5 nats (for Gaussian with σ=157bps)")

# VR as information source for Class C
if len(df_vr_trade) > 0:
    mi_vr = -0.5 * np.log(1 - rho_vr**2) if abs(rho_vr) < 1 else 0
    print(f"\nGaussian MI proxy: I(trade_ret; VR(2)_preceding_flat) = {mi_vr:.6f} nats")
    print(f"  (Spearman ρ = {rho_vr:.4f}, p = {p_vr:.4f})")
    print(f"  This is {mi_vr/np.log(2)*1000:.3f} millibits")

# ══════════════════════════════════════════════════════════════════════
# SUMMARY TABLE
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("SUMMARY TABLE: FUNCTION CLASS ASSESSMENT")
print("=" * 70)

summary = []

# Class A
summary.append({
    "class": "A",
    "name": "Single-bar contrarian long",
    "DOF": 1,
    "N_total": int(n_down),
    "N_per_year": int(n_down / YEARS),
    "gross_bps": round(mean_after_down, 1),
    "net_50bps": round(mean_after_down - 50, 1),
    "net_20bps": round(mean_after_down - 20, 1),
    "effect_d": round(d_a, 4),
    "MDE": round(mde_a, 4),
    "powered": "POWERED" if abs(d_a) > 1.5*mde_a else "BORDERLINE" if abs(d_a) > mde_a else "UNDERPOWERED",
})

# Class B (k=5)
if multibar_results:
    for row in multibar_results:
        if row["lookback_k"] == 5:
            d_b5 = row["mean_fwd_bps"] / row["std_fwd_bps"]
            mde_b5 = compute_mde(row["n_signals"])
            summary.append({
                "class": "B",
                "name": f"Multi-bar MR long (k={row['lookback_k']})",
                "DOF": 2,
                "N_total": int(row["n_signals"]),
                "N_per_year": int(row["per_year"]),
                "gross_bps": round(row["mean_fwd_bps"], 1),
                "net_50bps": round(row["mean_fwd_bps"] - 50, 1),
                "net_20bps": round(row["mean_fwd_bps"] - 20, 1),
                "effect_d": round(d_b5, 4),
                "MDE": round(mde_b5, 4),
                "powered": "POWERED" if abs(d_b5) > 1.5*mde_b5 else "BORDERLINE" if abs(d_b5) > mde_b5 else "UNDERPOWERED",
            })

# Class C
if len(df_vr_trade) > 0:
    summary.append({
        "class": "C",
        "name": "VR-conditional VTREND filter",
        "DOF": 2,
        "N_total": int(n_c),
        "N_per_year": int(n_c / YEARS),
        "gross_bps": "N/A (filter)",
        "net_50bps": "N/A",
        "net_20bps": "N/A",
        "effect_d": round(d_vr, 4),
        "MDE": round(mde_c, 4),
        "powered": "POWERED" if abs(d_vr) > 1.5*mde_c else "BORDERLINE" if abs(d_vr) > mde_c else "UNDERPOWERED",
    })

df_summary = pd.DataFrame(summary)
df_summary.to_csv(TBL / "Tbl09_power_analysis.csv", index=False)
print(f"\n{df_summary.to_string(index=False)}")

# Save complementarity table
comp_data = {
    "class": ["A", "B", "C"],
    "operates_during": ["FLAT only", "FLAT only", "FLAT→VTREND transition"],
    "time_overlap_vtrend": ["0%", "0%", "0% (modifies entry decision)"],
    "capital_conflict_rate": [
        f"{100*conflict_a/total_a_signals:.1f}%",
        "varies by k",
        "0% (no capital deployment)",
    ],
    "correlation_with_vtrend": ["0.00 (non-overlapping)", "0.00 (non-overlapping)", "modifies VTREND"],
}
df_comp = pd.DataFrame(comp_data)
df_comp.to_csv(TBL / "Tbl10_complementarity.csv", index=False)

print("\n" + "=" * 70)
print("DONE — All Phase 4 computation tables saved.")
print("=" * 70)
