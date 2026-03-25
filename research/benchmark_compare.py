"""VTREND vs Benchmarks: USDT savings, VND savings, BTC buy-and-hold."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd
import numpy as np
from datetime import datetime, timezone

from v10.core.data import DataFeed
from v10.core.engine import BacktestEngine
from v10.core.types import SCENARIOS
from strategies.vtrend.strategy import VTrendConfig, VTrendStrategy

# ---------- Benchmark rates ----------
# USDT flexible savings APY by year (approximate averages, major CEXs)
# 2017-2019: DeFi/lending not mainstream yet, ~2-4%
# 2020: DeFi summer, ~8-12%
# 2021: bull market, high demand, ~8-12%
# 2022: post-Luna/FTX crash, rates dropped, ~4-6%
# 2023-2024: normalized, ~4-6%
# 2025-2026: ~3-5%
USDT_APY = {
    2017: 0.03, 2018: 0.04, 2019: 0.04, 2020: 0.10,
    2021: 0.10, 2022: 0.05, 2023: 0.05, 2024: 0.05,
    2025: 0.04, 2026: 0.04,
}

# VND bank deposit rate by year (12-month term, approximate)
# Source: SBV data, big-4 banks
VND_APY = {
    2017: 0.068, 2018: 0.069, 2019: 0.070, 2020: 0.060,
    2021: 0.055, 2022: 0.065, 2023: 0.075, 2024: 0.055,
    2025: 0.050, 2026: 0.050,
}


def compound_savings(initial: float, apy_by_year: dict,
                     start_year: int, start_month: int,
                     end_year: int, end_month: int) -> list[dict]:
    """Compute monthly compounding savings. Returns list of {year, month, nav}."""
    nav = initial
    results = []
    y, m = start_year, start_month
    while (y, m) <= (end_year, end_month):
        results.append({"year": y, "month": m, "nav": nav})
        apy = apy_by_year.get(y, 0.04)
        monthly_rate = (1 + apy) ** (1/12) - 1
        nav *= (1 + monthly_rate)
        m += 1
        if m > 12:
            m = 1
            y += 1
    return results


def main():
    DATA_PATH = str(ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv")
    INITIAL = 10_000.0

    # --- Run VTREND ---
    config = VTrendConfig(slow_period=120.0, trail_mult=3.0, vdo_threshold=0.0)
    strategy = VTrendStrategy(config)
    cost = SCENARIOS["harsh"]
    feed = DataFeed(DATA_PATH, start="2017-08-01", end="2026-02-28", warmup_days=365)
    engine = BacktestEngine(
        feed=feed, strategy=strategy, cost=cost,
        initial_cash=INITIAL, warmup_mode="no_trade"
    )
    result = engine.run()

    # VTREND equity → monthly
    records = []
    for snap in result.equity:
        dt = datetime.fromtimestamp(snap.close_time / 1000, tz=timezone.utc)
        records.append({"datetime": dt, "nav": snap.nav_mid})
    edf = pd.DataFrame(records)
    edf["year"] = edf["datetime"].dt.year
    edf["month"] = edf["datetime"].dt.month
    edf["ym"] = edf["datetime"].dt.to_period("M")
    vtrend_monthly = edf.groupby("ym").agg(
        nav_end=("nav", "last"),
        year=("year", "last"),
        month=("month", "last"),
    ).reset_index(drop=True)

    # --- BTC Buy & Hold ---
    # Get BTC price from the H4 data
    raw = pd.read_csv(DATA_PATH)
    h4 = raw[raw["interval"] == "4h"].copy()
    h4["datetime"] = pd.to_datetime(h4["close_time"], unit="ms", utc=True)
    h4 = h4.sort_values("datetime")
    # Start from first VTREND equity point
    first_dt = edf["datetime"].iloc[0]
    h4_filtered = h4[h4["datetime"] >= first_dt].copy()
    h4_filtered["year"] = h4_filtered["datetime"].dt.year
    h4_filtered["month"] = h4_filtered["datetime"].dt.month
    h4_filtered["ym"] = h4_filtered["datetime"].dt.to_period("M")

    # BTC price at start and each month-end
    btc_start_price = h4_filtered["close"].iloc[0]
    btc_qty = INITIAL / btc_start_price  # How much BTC we buy

    btc_monthly = h4_filtered.groupby("ym").agg(
        price_end=("close", "last"),
        year=("year", "last"),
        month=("month", "last"),
    ).reset_index(drop=True)
    btc_monthly["nav"] = btc_qty * btc_monthly["price_end"]

    # --- Savings benchmarks ---
    start_y = int(vtrend_monthly["year"].iloc[0])
    start_m = int(vtrend_monthly["month"].iloc[0])
    end_y = int(vtrend_monthly["year"].iloc[-1])
    end_m = int(vtrend_monthly["month"].iloc[-1])

    usdt_data = compound_savings(INITIAL, USDT_APY, start_y, start_m, end_y, end_m)
    vnd_data = compound_savings(INITIAL, VND_APY, start_y, start_m, end_y, end_m)

    usdt_df = pd.DataFrame(usdt_data)
    vnd_df = pd.DataFrame(vnd_data)

    # --- Merge all into yearly comparison ---
    print("=" * 100)
    print("YEARLY COMPARISON: VTREND vs BTC Buy&Hold vs USDT Savings vs VND Savings")
    print("Starting capital: $10,000 (Aug 2017)")
    print("=" * 100)
    print(f"{'Year':<6} {'VTREND NAV':>14} {'VTREND %':>10} │ {'BTC B&H NAV':>14} {'BTC %':>10} │ {'USDT NAV':>12} {'USDT %':>8} │ {'VND NAV':>12} {'VND %':>8}")
    print("─" * 100)

    years = sorted(vtrend_monthly["year"].unique())

    vtrend_yearly = {}
    btc_yearly = {}
    usdt_yearly = {}
    vnd_yearly = {}

    for y in years:
        # VTREND
        vt = vtrend_monthly[vtrend_monthly["year"] == y]
        if len(vt) > 0:
            vtrend_yearly[y] = vt["nav_end"].iloc[-1]

        # BTC
        bt = btc_monthly[btc_monthly["year"] == y]
        if len(bt) > 0:
            btc_yearly[y] = bt["nav"].iloc[-1]

        # USDT
        ut = usdt_df[usdt_df["year"] == y]
        if len(ut) > 0:
            usdt_yearly[y] = ut["nav"].iloc[-1]

        # VND
        vt2 = vnd_df[vnd_df["year"] == y]
        if len(vt2) > 0:
            vnd_yearly[y] = vt2["nav"].iloc[-1]

    prev_vtrend = INITIAL
    prev_btc = INITIAL
    prev_usdt = INITIAL
    prev_vnd = INITIAL

    for y in years:
        vt_nav = vtrend_yearly.get(y, prev_vtrend)
        bt_nav = btc_yearly.get(y, prev_btc)
        ut_nav = usdt_yearly.get(y, prev_usdt)
        vn_nav = vnd_yearly.get(y, prev_vnd)

        vt_ret = (vt_nav / prev_vtrend - 1) * 100
        bt_ret = (bt_nav / prev_btc - 1) * 100
        ut_ret = (ut_nav / prev_usdt - 1) * 100
        vn_ret = (vn_nav / prev_vnd - 1) * 100

        print(f"{y:<6} ${vt_nav:>12,.0f} {vt_ret:>+9.1f}% │ ${bt_nav:>12,.0f} {bt_ret:>+9.1f}% │ ${ut_nav:>10,.0f} {ut_ret:>+7.1f}% │ ${vn_nav:>10,.0f} {vn_ret:>+7.1f}%")

        prev_vtrend = vt_nav
        prev_btc = bt_nav
        prev_usdt = ut_nav
        prev_vnd = vn_nav

    # --- Final summary ---
    final_vtrend = vtrend_yearly[years[-1]]
    final_btc = btc_yearly[years[-1]]
    final_usdt = usdt_yearly[years[-1]]
    final_vnd = vnd_yearly[years[-1]]

    n_years = (end_y - start_y) + (end_m - start_m) / 12
    vtrend_cagr = (final_vtrend / INITIAL) ** (1 / n_years) - 1
    btc_cagr = (final_btc / INITIAL) ** (1 / n_years) - 1
    usdt_cagr = (final_usdt / INITIAL) ** (1 / n_years) - 1
    vnd_cagr = (final_vnd / INITIAL) ** (1 / n_years) - 1

    # Max drawdown for BTC B&H
    btc_prices = h4_filtered.sort_values("datetime")["close"].values
    btc_navs = btc_qty * btc_prices
    btc_peak = np.maximum.accumulate(btc_navs)
    btc_dd = (btc_navs - btc_peak) / btc_peak
    btc_max_dd = btc_dd.min() * 100

    # VTREND max dd from result
    vtrend_max_dd = result.summary.get("max_drawdown_mid_pct", 0)

    print("─" * 100)
    print()
    print("=" * 80)
    print("FINAL COMPARISON SUMMARY")
    print("=" * 80)
    print(f"Period: Aug 2017 → Feb 2026 ({n_years:.1f} years)")
    print(f"Starting capital: $10,000")
    print()
    print(f"{'Strategy':<20} {'Final NAV':>14} {'Total Return':>14} {'CAGR':>8} {'Max DD':>10}")
    print("─" * 70)
    print(f"{'VTREND':<20} ${final_vtrend:>12,.0f} {(final_vtrend/INITIAL-1)*100:>+13.1f}% {vtrend_cagr*100:>+7.1f}% {-abs(vtrend_max_dd):>9.1f}%")
    print(f"{'BTC Buy & Hold':<20} ${final_btc:>12,.0f} {(final_btc/INITIAL-1)*100:>+13.1f}% {btc_cagr*100:>+7.1f}% {btc_max_dd:>9.1f}%")
    print(f"{'USDT Savings':<20} ${final_usdt:>12,.0f} {(final_usdt/INITIAL-1)*100:>+13.1f}% {usdt_cagr*100:>+7.1f}% {'0.0':>9}%")
    print(f"{'VND Savings':<20} ${final_vnd:>12,.0f} {(final_vnd/INITIAL-1)*100:>+13.1f}% {vnd_cagr*100:>+7.1f}% {'0.0':>9}%")

    print()
    print("─" * 70)
    print("VTREND vs BTC B&H:")
    vtrend_vs_btc = final_vtrend / final_btc
    print(f"  VTREND / BTC = {vtrend_vs_btc:.2f}x")
    if final_vtrend > final_btc:
        print(f"  VTREND beats BTC B&H by ${final_vtrend - final_btc:,.0f} ({(final_vtrend/final_btc - 1)*100:+.1f}%)")
    else:
        print(f"  BTC B&H beats VTREND by ${final_btc - final_vtrend:,.0f} ({(final_btc/final_vtrend - 1)*100:+.1f}%)")

    print(f"\nVTREND vs USDT savings:")
    print(f"  VTREND / USDT = {final_vtrend/final_usdt:.1f}x")

    print(f"\nVTREND vs VND savings:")
    print(f"  VTREND / VND = {final_vtrend/final_vnd:.1f}x")

    # --- Year-by-year winner ---
    print()
    print("=" * 80)
    print("YEAR-BY-YEAR WINNER")
    print("=" * 80)

    prev = {"VTREND": INITIAL, "BTC": INITIAL, "USDT": INITIAL, "VND": INITIAL}
    for y in years:
        rets = {
            "VTREND": (vtrend_yearly.get(y, prev["VTREND"]) / prev["VTREND"] - 1) * 100,
            "BTC B&H": (btc_yearly.get(y, prev["BTC"]) / prev["BTC"] - 1) * 100,
            "USDT": (usdt_yearly.get(y, prev["USDT"]) / prev["USDT"] - 1) * 100,
            "VND": (vnd_yearly.get(y, prev["VND"]) / prev["VND"] - 1) * 100,
        }
        winner = max(rets, key=rets.get)
        print(f"  {y}: {winner:<10} ({rets[winner]:+.1f}%)  |  VTREND {rets['VTREND']:+.1f}%  BTC {rets['BTC B&H']:+.1f}%  USDT {rets['USDT']:+.1f}%  VND {rets['VND']:+.1f}%")

        prev["VTREND"] = vtrend_yearly.get(y, prev["VTREND"])
        prev["BTC"] = btc_yearly.get(y, prev["BTC"])
        prev["USDT"] = usdt_yearly.get(y, prev["USDT"])
        prev["VND"] = vnd_yearly.get(y, prev["VND"])

    # Risk-adjusted
    print()
    print("=" * 80)
    print("RISK-ADJUSTED (return per unit of max drawdown)")
    print("=" * 80)
    print(f"  VTREND Calmar:  {abs((final_vtrend/INITIAL-1)*100 / vtrend_max_dd):.2f}")
    print(f"  BTC B&H Calmar: {abs((final_btc/INITIAL-1)*100 / btc_max_dd):.2f}")
    print(f"  USDT: no drawdown risk (counterparty risk only)")
    print(f"  VND:  no drawdown risk (inflation risk ~3-4%/yr)")


if __name__ == "__main__":
    main()
