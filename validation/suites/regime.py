"""Regime decomposition suite."""

from __future__ import annotations

import time
from pathlib import Path

from v10.research.regime import classify_d1_regimes, compute_regime_returns
from validation.output import write_csv, write_json
from validation.suites.base import BaseSuite, SuiteContext, SuiteResult
from validation.suites.common import ensure_backtest


def _has_topping_or_late_bull_trigger(config_obj: object | None) -> bool:
    if config_obj is None:
        return False
    fields = [name for name in dir(config_obj) if not name.startswith("_")]
    for field in fields:
        lname = field.lower()
        if "topping" in lname or "late_bull" in lname or "cycle_late" in lname:
            return True
    return False


def _trade_entry_time_ms(trade: object) -> int:
    if hasattr(trade, "entry_ts_ms"):
        return int(getattr(trade, "entry_ts_ms"))
    if hasattr(trade, "entry_time"):
        return int(getattr(trade, "entry_time"))
    return 0


class RegimeSuite(BaseSuite):
    def name(self) -> str:
        return "regime"

    def run(self, ctx: SuiteContext) -> SuiteResult:
        t0 = time.time()
        artifacts: list[Path] = []

        regimes = classify_d1_regimes(ctx.feed.d1_bars)
        rows: list[dict] = []
        detail: dict[str, dict] = {}

        chosen_scenario = "harsh" if "harsh" in ctx.validation_config.scenarios else "base"
        for label in ["candidate", "baseline"]:
            result = ensure_backtest(ctx, label, chosen_scenario)
            if not result.equity:
                continue

            regime_returns = compute_regime_returns(
                result.equity,
                ctx.feed.d1_bars,
                regimes,
                report_start_ms=ctx.feed.report_start_ms,
            )
            detail[label] = regime_returns

            for regime_name, stats in regime_returns.items():
                row = {"label": label, "regime": regime_name, "notes": ""}
                row.update(stats)
                rows.append(row)

        # Optional overlap diagnostics for topping/late-bull trigger candidates.
        overlap = {
            "enabled": False,
            "scenario": chosen_scenario,
            "trades_in_topping": 0,
            "trades_in_late_bull": 0,
        }
        if _has_topping_or_late_bull_trigger(ctx.candidate_config_obj):
            overlap["enabled"] = True
            candidate = ensure_backtest(ctx, "candidate", chosen_scenario)
            day_to_regime: dict[int, str] = {}
            for idx, d1 in enumerate(ctx.feed.d1_bars):
                if idx < len(regimes):
                    day_to_regime[d1.close_time // 86_400_000] = str(regimes[idx])

            for trade in candidate.trades or []:
                day = _trade_entry_time_ms(trade) // 86_400_000
                regime_name = day_to_regime.get(day, "UNKNOWN")
                if regime_name == "TOPPING":
                    overlap["trades_in_topping"] += 1
                if regime_name == "BULL":
                    overlap["trades_in_late_bull"] += 1

            rows.append(
                {
                    "label": "candidate",
                    "regime": "TOPPING_LATE_BULL_OVERLAP",
                    "total_return_pct": None,
                    "max_dd_pct": None,
                    "n_bars": None,
                    "n_days": None,
                    "sharpe": None,
                    "notes": (
                        f"topping_trades={overlap['trades_in_topping']}; "
                        f"late_bull_trades={overlap['trades_in_late_bull']}"
                    ),
                }
            )

        csv_path = write_csv(
            rows,
            ctx.results_dir / "regime_decomposition.csv",
            fieldnames=[
                "label",
                "regime",
                "total_return_pct",
                "max_dd_pct",
                "n_bars",
                "n_days",
                "sharpe",
                "notes",
            ],
        )
        artifacts.append(csv_path)

        json_path = write_json(
            {"detail": detail, "overlap": overlap},
            ctx.results_dir / "regime_decomposition.json",
        )
        artifacts.append(json_path)

        return SuiteResult(
            name=self.name(),
            status="info",
            data={"rows": rows, "detail": detail, "overlap": overlap},
            artifacts=artifacts,
            duration_seconds=time.time() - t0,
        )
