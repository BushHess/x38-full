"""VTREND monthly/yearly P&L breakdown on real BTC data (2017-now)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd
from datetime import datetime, timezone

from v10.core.data import DataFeed
from v10.core.engine import BacktestEngine
from v10.core.types import SCENARIOS
from strategies.vtrend.strategy import VTrendConfig, VTrendStrategy


def main():
    DATA_PATH = str(ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv")

    # Default VTREND params
    config = VTrendConfig(slow_period=120.0, trail_mult=3.0, vdo_threshold=0.0)
    strategy = VTrendStrategy(config)
    cost = SCENARIOS["harsh"]  # 50 bps round-trip (conservative)

    feed = DataFeed(DATA_PATH, start="2017-08-01", end="2026-02-28", warmup_days=365)
    engine = BacktestEngine(
        feed=feed, strategy=strategy, cost=cost,
        initial_cash=10_000.0, warmup_mode="no_trade"
    )
    result = engine.run()

    # Build equity DataFrame
    records = []
    for snap in result.equity:
        dt = datetime.fromtimestamp(snap.close_time / 1000, tz=timezone.utc)
        records.append({"datetime": dt, "nav": snap.nav_mid})

    df = pd.DataFrame(records)
    df["date"] = df["datetime"].dt.date
    df["year"] = df["datetime"].dt.year
    df["month"] = df["datetime"].dt.month

    # --- Monthly returns ---
    # Last NAV of each month
    df["ym"] = df["datetime"].dt.to_period("M")
    monthly_last = df.groupby("ym")["nav"].last()
    monthly_ret = monthly_last.pct_change() * 100

    # Also compute absolute P&L per month
    monthly_first = df.groupby("ym")["nav"].first()

    print("=" * 80)
    print("VTREND MONTHLY P&L  (harsh cost, slow=120, trail=3.0, vdo=0.0)")
    print("=" * 80)
    print(f"{'Month':<12} {'Start NAV':>12} {'End NAV':>12} {'P&L $':>10} {'Return %':>10}")
    print("-" * 60)

    for period in monthly_ret.index:
        if pd.isna(monthly_ret[period]):
            continue
        start_nav = monthly_first[period]
        end_nav = monthly_last[period]
        pnl = end_nav - start_nav
        ret = monthly_ret[period]
        print(f"{str(period):<12} {start_nav:>12,.2f} {end_nav:>12,.2f} {pnl:>10,.2f} {ret:>9.2f}%")

    # --- Yearly returns ---
    yearly_last = df.groupby("year")["nav"].last()
    yearly_first = df.groupby("year")["nav"].first()
    yearly_ret = yearly_last.pct_change() * 100

    print()
    print("=" * 80)
    print("VTREND YEARLY P&L")
    print("=" * 80)
    print(f"{'Year':<8} {'Start NAV':>12} {'End NAV':>12} {'P&L $':>12} {'Return %':>10}")
    print("-" * 58)

    for year in yearly_ret.index:
        start_nav = yearly_first[year]
        end_nav = yearly_last[year]
        pnl = end_nav - start_nav
        ret = (end_nav / start_nav - 1) * 100
        print(f"{year:<8} {start_nav:>12,.2f} {end_nav:>12,.2f} {pnl:>12,.2f} {ret:>9.2f}%")

    # --- Best/Worst ---
    print()
    print("=" * 80)
    print("EXTREMES")
    print("=" * 80)

    # Monthly
    valid_monthly = monthly_ret.dropna()
    best_month = valid_monthly.idxmax()
    worst_month = valid_monthly.idxmin()
    print(f"Best month:   {best_month}  → {valid_monthly[best_month]:+.2f}%")
    print(f"Worst month:  {worst_month}  → {valid_monthly[worst_month]:+.2f}%")

    # Positive/negative months
    pos_months = (valid_monthly > 0).sum()
    neg_months = (valid_monthly < 0).sum()
    flat_months = (valid_monthly == 0).sum()
    total_months = len(valid_monthly)
    print(f"Positive months: {pos_months}/{total_months} ({pos_months/total_months*100:.1f}%)")
    print(f"Negative months: {neg_months}/{total_months} ({neg_months/total_months*100:.1f}%)")

    # Yearly
    yearly_pnl = {}
    for year in yearly_ret.index:
        yearly_pnl[year] = (yearly_last[year] / yearly_first[year] - 1) * 100

    best_year = max(yearly_pnl, key=yearly_pnl.get)
    worst_year = min(yearly_pnl, key=yearly_pnl.get)
    print(f"\nBest year:    {best_year}  → {yearly_pnl[best_year]:+.2f}%")
    print(f"Worst year:   {worst_year}  → {yearly_pnl[worst_year]:+.2f}%")

    # Total
    initial = df["nav"].iloc[0]
    final = df["nav"].iloc[-1]
    total_pnl = final - initial
    total_ret = (final / initial - 1) * 100

    print(f"\n{'='*80}")
    print("TOTAL")
    print(f"{'='*80}")
    print(f"Initial NAV:  ${initial:,.2f}")
    print(f"Final NAV:    ${final:,.2f}")
    print(f"Total P&L:    ${total_pnl:,.2f}")
    print(f"Total Return: {total_ret:,.2f}%")
    print(f"Trades:       {result.summary.get('trades', 'N/A')}")
    print(f"CAGR:         {result.summary.get('cagr_pct', 0):.2f}%")
    print(f"Sharpe:       {result.summary.get('sharpe', 0):.3f}")
    print(f"Max DD:       {result.summary.get('max_drawdown_mid_pct', 0):.2f}%")

    # --- Monthly heatmap-style table ---
    print(f"\n{'='*80}")
    print("MONTHLY RETURNS HEATMAP (%)")
    print(f"{'='*80}")

    # Build pivot
    monthly_data = []
    for period in valid_monthly.index:
        monthly_data.append({
            "year": period.year,
            "month": period.month,
            "return": valid_monthly[period]
        })

    mdf = pd.DataFrame(monthly_data)
    if len(mdf) > 0:
        pivot = mdf.pivot(index="year", columns="month", values="return")
        pivot.columns = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                         "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][:len(pivot.columns)]

        # Add yearly total
        for year in pivot.index:
            if year in yearly_pnl:
                pivot.loc[year, "YEAR"] = yearly_pnl[year]

        pd.set_option("display.float_format", lambda x: f"{x:+.1f}" if not pd.isna(x) else "")
        pd.set_option("display.max_columns", 15)
        pd.set_option("display.width", 120)
        print(pivot.to_string())


if __name__ == "__main__":
    main()
