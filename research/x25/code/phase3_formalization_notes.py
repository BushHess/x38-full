"""
Phase 3: Formalization — Supporting Computations

Power analysis and detectability bounds for entry filter design.
Not a backtest. Not a candidate.
"""

import numpy as np
from scipy import stats


def mde_two_group(n1: int, n2: int, alpha: float = 0.05, power: float = 0.80) -> float:
    """Minimum detectable effect (Cohen's d) for two-group comparison."""
    z_a = stats.norm.ppf(1 - alpha / 2)
    z_b = stats.norm.ppf(power)
    return (z_a + z_b) * np.sqrt(1 / n1 + 1 / n2)


def sharpe_mde(n: int, sh_base: float, alpha: float = 0.05, power: float = 0.80) -> float:
    """Minimum detectable Sharpe difference (two-sample)."""
    z_a = stats.norm.ppf(1 - alpha / 2)
    z_b = stats.norm.ppf(power)
    sigma_sh = np.sqrt((1 + 0.5 * sh_base ** 2) / n)
    return (z_a + z_b) * sigma_sh * np.sqrt(2)


def win_rate_power(wr_base: float, wr_new: float, n: int, alpha: float = 0.05) -> float:
    """Power to detect win rate change from wr_base to wr_new."""
    z_a = stats.norm.ppf(1 - alpha / 2)
    h = 2 * np.arcsin(np.sqrt(wr_new)) - 2 * np.arcsin(np.sqrt(wr_base))
    noncentrality = h * np.sqrt(n)
    return 1 - stats.norm.cdf(z_a - noncentrality)


def rank_biserial_to_d(r_rb: float) -> float:
    """Approximate conversion from rank-biserial to Cohen's d."""
    return 2 * r_rb / np.sqrt(1 - r_rb ** 2)


def blocking_analysis(n_w: int, n_l: int, k: int, loser_precision: float):
    """Effect of blocking k trades where loser_precision fraction are actual losers."""
    losers_blocked = int(k * loser_precision)
    winners_blocked = k - losers_blocked
    new_w = n_w - winners_blocked
    new_l = n_l - losers_blocked
    return new_w, new_l, new_w / (new_w + new_l)


if __name__ == "__main__":
    # --- Phase 2 sample ---
    N = 201
    N_W, N_L = 78, 123
    WR = N_W / N
    SH_BASE = 1.19

    print("=" * 60)
    print("PHASE 3 — DETECTABILITY & POWER BOUNDS")
    print("=" * 60)

    # 1. Two-group MDE
    d_mde = mde_two_group(N_W, N_L)
    print(f"\n1. Two-group MDE (n_w={N_W}, n_l={N_L})")
    print(f"   Cohen d = {d_mde:.3f} at 80% power, alpha=0.05")

    # 2. Obs18 VDO effect vs MDE
    r_rb_vdo = 0.144
    d_vdo = rank_biserial_to_d(r_rb_vdo)
    print(f"\n2. VDO effect (Obs18)")
    print(f"   Rank-biserial = {r_rb_vdo}")
    print(f"   Approx Cohen d = {d_vdo:.3f}")
    print(f"   Status: {'DETECTABLE' if d_vdo >= d_mde else 'BELOW MDE'}")

    # 3. Win rate power table
    print(f"\n3. Win rate detection (base={WR:.1%})")
    print(f"   {'Target WR':>12} {'Cohen h':>10} {'Power':>10} {'n_eff':>8}")
    for new_wr in [0.42, 0.45, 0.48, 0.50, 0.55]:
        for block_frac in [0.0, 0.15]:
            k = int(N * block_frac)
            n_eff = N - k
            pw = win_rate_power(WR, new_wr, n_eff)
            tag = f" (block {block_frac:.0%})" if block_frac > 0 else ""
            print(f"   {new_wr:>10.0%}{tag:>6} {2*np.arcsin(np.sqrt(new_wr))-2*np.arcsin(np.sqrt(WR)):>10.3f} {pw:>10.3f} {n_eff:>8}")

    # 4. Sharpe MDE
    print(f"\n4. Sharpe ratio MDE (base Sh={SH_BASE})")
    for block_pct in [0, 10, 20, 30]:
        n_eff = int(N * (1 - block_pct / 100))
        mde = sharpe_mde(n_eff, SH_BASE)
        print(f"   Block {block_pct:>2}%: n_eff={n_eff:>3}, delta_Sh MDE = {mde:.3f}")

    # 5. Blocking precision analysis
    print(f"\n5. Blocking analysis (k=30 blocked)")
    print(f"   {'Loser prec':>12} {'New W':>7} {'New L':>7} {'New WR':>10}")
    for lp in [0.5, 0.6, 0.7, 0.8, 0.9, 1.0]:
        nw, nl, nwr = blocking_analysis(N_W, N_L, 30, lp)
        print(f"   {lp:>10.0%} {nw:>7} {nl:>7} {nwr:>10.1%}")

    # 6. Information-theoretic bound
    # Mutual information upper bound from rank-biserial
    # I(Y; X) <= H(Y) for binary Y
    h_y = -WR * np.log2(WR) - (1 - WR) * np.log2(1 - WR)
    print(f"\n6. Information bounds")
    print(f"   H(win/lose) = {h_y:.3f} bits")
    print(f"   With r_rb=0.144 (VDO), approx MI << {h_y:.3f} bits")
    print(f"   Point-biserial r² ≈ {r_rb_vdo**2:.4f} → {r_rb_vdo**2 * 100:.2f}% variance explained")

    print(f"\n{'=' * 60}")
    print(f"CONCLUSION: MDE d=0.406. Strongest signal (VDO) d=0.291.")
    print(f"VDO explains ~2.1% of win/lose variance.")
    print(f"Any volume-based filter faces severe power constraints at n=201.")
    print(f"{'=' * 60}")
