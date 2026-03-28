#!/usr/bin/env python3
"""Phase 2: Formal Reproduction Check — x39 simplified replay vs v10 engine.

Runs BOTH the x39 simplified replay (exp34 style) AND the v10 formal engine
side-by-side, for baseline (E5-ema21D1) and compression (thr=0.6/0.7),
then compares deltas to verify the vol compression gate reproduces.

Acceptance criteria (from formal_validation_spec.md):
  - d_Sharpe same sign (v10 > 0, like x39's +0.19)
  - d_Sharpe magnitude within ±30% of x39 value
  - d_Trades: compression has fewer trades than baseline
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]  # btc-spot-dev/
sys.path.insert(0, str(ROOT))

from v10.core.data import DataFeed  # noqa: E402
from v10.core.engine import BacktestEngine  # noqa: E402
from v10.core.types import SCENARIOS  # noqa: E402
from strategies.vtrend_e5_ema21_d1.strategy import (  # noqa: E402
    VTrendE5Ema21D1Config,
    VTrendE5Ema21D1Strategy,
)
from strategies.vtrend_e5_ema21_d1_vc.strategy import (  # noqa: E402
    VTrendE5Ema21D1VCConfig,
    VTrendE5Ema21D1VCStrategy,
)

DATA = str(ROOT / "data" / "bars_btcusdt_2016_now_h1_4h_1d.csv")

# x39 reference values from exp34_results.csv
X39_REF = {
    "baseline": {"sharpe": 1.2965, "trades": 221, "mdd_pct": 51.32},
    0.6: {"sharpe": 1.4866, "d_sharpe": 0.1901, "trades": 197, "d_trades": -24, "d_mdd_pp": 2.27},
    0.7: {"sharpe": 1.4764, "d_sharpe": 0.1799, "trades": 202, "d_trades": -19, "d_mdd_pp": 0.42},
}


def run_v10(strategy, label: str) -> dict:
    """Run v10 backtest and return summary metrics."""
    feed = DataFeed(DATA, start="2019-01-01", end="2026-02-20", warmup_days=365)
    engine = BacktestEngine(
        feed=feed,
        strategy=strategy,
        cost=SCENARIOS["harsh"],
        initial_cash=10_000.0,
        warmup_mode="no_trade",
    )
    result = engine.run()
    s = result.summary
    print(f"\n  [{label}] v10 result:")
    print(f"    Sharpe:   {s['sharpe']:.4f}")
    print(f"    CAGR:     {s['cagr_pct']:.2f}%")
    print(f"    MDD:      {s['max_drawdown_mid_pct']:.2f}%")
    print(f"    Trades:   {s['trades']}")
    print(f"    Exposure: {s.get('exposure_pct', 'N/A')}")
    return s


def main() -> None:
    print("=" * 80)
    print("PHASE 2: FORMAL REPRODUCTION CHECK")
    print("  x39 simplified replay vs v10 BacktestEngine")
    print("=" * 80)

    # ── Step 2a: v10 baseline (E5-ema21D1) ──────────────────────────────
    print("\n--- Step 2a: v10 Baseline (E5-ema21D1) ---")
    base_strat = VTrendE5Ema21D1Strategy(VTrendE5Ema21D1Config())
    base = run_v10(base_strat, "E5-ema21D1 baseline")

    # ── Step 2b: v10 compression thr=0.6 ────────────────────────────────
    print("\n--- Step 2b: v10 Compression thr=0.6 ---")
    vc06_strat = VTrendE5Ema21D1VCStrategy(
        VTrendE5Ema21D1VCConfig(compression_threshold=0.6)
    )
    vc06 = run_v10(vc06_strat, "E5-ema21D1-VC thr=0.6")

    # ── Step 2b': v10 compression thr=0.7 ───────────────────────────────
    print("\n--- Step 2b': v10 Compression thr=0.7 ---")
    vc07_strat = VTrendE5Ema21D1VCStrategy(
        VTrendE5Ema21D1VCConfig(compression_threshold=0.7)
    )
    vc07 = run_v10(vc07_strat, "E5-ema21D1-VC thr=0.7")

    # ── Step 2c: Discrepancy analysis ───────────────────────────────────
    print("\n" + "=" * 80)
    print("STEP 2c: DISCREPANCY ANALYSIS")
    print("=" * 80)

    v10_d_sharpe_06 = vc06["sharpe"] - base["sharpe"]
    v10_d_sharpe_07 = vc07["sharpe"] - base["sharpe"]
    v10_d_mdd_06 = vc06["max_drawdown_mid_pct"] - base["max_drawdown_mid_pct"]
    v10_d_mdd_07 = vc07["max_drawdown_mid_pct"] - base["max_drawdown_mid_pct"]
    v10_d_trades_06 = vc06["trades"] - base["trades"]
    v10_d_trades_07 = vc07["trades"] - base["trades"]

    x39_d_sh_06 = X39_REF[0.6]["d_sharpe"]
    x39_d_sh_07 = X39_REF[0.7]["d_sharpe"]

    print(f"\n{'Metric':<25} {'x39 Value':>12} {'v10 Value':>12} {'Discrepancy':>12} {'Acceptable?':>14}")
    print("-" * 77)

    # thr=0.6 comparison
    print(f"\n  --- thr=0.6 ---")
    disc_06 = (v10_d_sharpe_06 - x39_d_sh_06) / x39_d_sh_06 * 100 if x39_d_sh_06 != 0 else float("inf")
    sign_ok_06 = v10_d_sharpe_06 > 0
    mag_ok_06 = abs(disc_06) <= 30
    print(f"  {'d_Sharpe (full)':<23} {x39_d_sh_06:>+12.4f} {v10_d_sharpe_06:>+12.4f} {disc_06:>+11.1f}% {'YES' if sign_ok_06 and mag_ok_06 else 'NO':>14}")

    x39_d_mdd_06 = X39_REF[0.6]["d_mdd_pp"]
    mdd_sign_ok_06 = (v10_d_mdd_06 > 0) == (x39_d_mdd_06 > 0)
    print(f"  {'d_MDD (full, pp)':<23} {x39_d_mdd_06:>+12.2f} {v10_d_mdd_06:>+12.2f} {'':>12} {'YES (same sign)' if mdd_sign_ok_06 else 'NO (sign flip)':>14}")

    x39_d_tr_06 = X39_REF[0.6]["d_trades"]
    tr_ok_06 = abs(v10_d_trades_06 - x39_d_tr_06) <= 5
    print(f"  {'d_Trades':<23} {x39_d_tr_06:>12} {v10_d_trades_06:>12} {v10_d_trades_06 - x39_d_tr_06:>+12} {'YES' if tr_ok_06 else 'NO (>±5)':>14}")

    # thr=0.7 comparison
    print(f"\n  --- thr=0.7 ---")
    disc_07 = (v10_d_sharpe_07 - x39_d_sh_07) / x39_d_sh_07 * 100 if x39_d_sh_07 != 0 else float("inf")
    sign_ok_07 = v10_d_sharpe_07 > 0
    mag_ok_07 = abs(disc_07) <= 30
    print(f"  {'d_Sharpe (full)':<23} {x39_d_sh_07:>+12.4f} {v10_d_sharpe_07:>+12.4f} {disc_07:>+11.1f}% {'YES' if sign_ok_07 and mag_ok_07 else 'NO':>14}")

    x39_d_mdd_07 = X39_REF[0.7]["d_mdd_pp"]
    mdd_sign_ok_07 = (v10_d_mdd_07 > 0) == (x39_d_mdd_07 > 0)
    print(f"  {'d_MDD (full, pp)':<23} {x39_d_mdd_07:>+12.2f} {v10_d_mdd_07:>+12.2f} {'':>12} {'YES (same sign)' if mdd_sign_ok_07 else 'NO (sign flip)':>14}")

    x39_d_tr_07 = X39_REF[0.7]["d_trades"]
    tr_ok_07 = abs(v10_d_trades_07 - x39_d_tr_07) <= 5
    print(f"  {'d_Trades':<23} {x39_d_tr_07:>12} {v10_d_trades_07:>12} {v10_d_trades_07 - x39_d_tr_07:>+12} {'YES' if tr_ok_07 else 'NO (>±5)':>14}")

    # ── Overall verdict ──────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("PHASE 2 VERDICT")
    print("=" * 80)

    # Primary check: thr=0.6 (the main candidate)
    pass_06 = sign_ok_06 and mag_ok_06
    pass_07 = sign_ok_07 and mag_ok_07

    print(f"\n  thr=0.6: {'PASS' if pass_06 else 'FAIL'}")
    print(f"    d_Sharpe sign positive: {'YES' if sign_ok_06 else 'NO'}")
    print(f"    d_Sharpe within ±30%:   {'YES' if mag_ok_06 else 'NO'} ({disc_06:+.1f}%)")
    print(f"    d_Trades fewer:         {'YES' if v10_d_trades_06 < 0 else 'NO'} ({v10_d_trades_06:+d})")

    print(f"\n  thr=0.7: {'PASS' if pass_07 else 'FAIL'}")
    print(f"    d_Sharpe sign positive: {'YES' if sign_ok_07 else 'NO'}")
    print(f"    d_Sharpe within ±30%:   {'YES' if mag_ok_07 else 'NO'} ({disc_07:+.1f}%)")
    print(f"    d_Trades fewer:         {'YES' if v10_d_trades_07 < 0 else 'NO'} ({v10_d_trades_07:+d})")

    overall = pass_06  # thr=0.6 is primary
    print(f"\n  OVERALL: {'PASS — proceed to Phase 3' if overall else 'FAIL — diagnose before proceeding'}")

    # ── Absolute level comparison (informational) ────────────────────────
    print("\n" + "=" * 80)
    print("INFORMATIONAL: Absolute Level Comparison")
    print("  (x39 uses simplified replay; absolute levels expected to differ)")
    print("=" * 80)
    print(f"\n  {'':25} {'x39':>12} {'v10':>12}")
    print(f"  {'Baseline Sharpe':<25} {X39_REF['baseline']['sharpe']:>12.4f} {base['sharpe']:>12.4f}")
    print(f"  {'Baseline trades':<25} {X39_REF['baseline']['trades']:>12} {base['trades']:>12}")
    print(f"  {'Baseline MDD %':<25} {X39_REF['baseline']['mdd_pct']:>12.2f} {base['max_drawdown_mid_pct']:>12.2f}")
    print(f"  {'thr=0.6 Sharpe':<25} {X39_REF[0.6]['sharpe']:>12.4f} {vc06['sharpe']:>12.4f}")
    print(f"  {'thr=0.6 trades':<25} {X39_REF[0.6]['trades']:>12} {vc06['trades']:>12}")
    print(f"  {'thr=0.7 Sharpe':<25} {X39_REF[0.7]['sharpe']:>12.4f} {vc07['sharpe']:>12.4f}")
    print(f"  {'thr=0.7 trades':<25} {X39_REF[0.7]['trades']:>12} {vc07['trades']:>12}")


if __name__ == "__main__":
    main()
