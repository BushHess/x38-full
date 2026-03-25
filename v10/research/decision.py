"""Decision gate — promote/hold/reject candidates based on matrix results.

Reads matrix output artifacts (scenario_table.csv, regime_returns, dd_episodes)
and produces a decision report + JSON with per-candidate gate verdicts.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from v10.core.meta import get_git_hash


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class GateResult:
    """Per-candidate gate verdict."""
    name: str
    tag: str  # "PROMOTE" | "HOLD" | "REJECT"
    reasons: list[str]
    worst: dict[str, Any]  # min_score, min_cagr, max_mdd, max_fee_drag, trades
    regime: dict[str, Any] | None  # TOPPING + SHOCK subset
    top_dd: list[dict[str, Any]]  # top 5 drawdown episodes


@dataclass
class DecisionResult:
    """Aggregated decision across all candidates."""
    selected: str
    gates: list[GateResult]
    metadata: dict[str, Any]


# ---------------------------------------------------------------------------
# File loaders
# ---------------------------------------------------------------------------

_NUMERIC_COLS = {
    "score", "cagr_pct", "max_drawdown_mid_pct", "sharpe", "sortino",
    "profit_factor", "win_rate_pct", "avg_trade_pnl", "fees_total",
    "trades", "turnover_per_year", "fee_drag_pct_per_year",
}


def _parse_num(val: str, col: str) -> int | float | None:
    """Parse a CSV value to int (trades) or float, returning None for empty/N/A."""
    if val in ("", "None", "N/A", "inf"):
        return float("inf") if val == "inf" else None
    if col == "trades":
        return int(float(val))
    return float(val)


def _load_scenario_table(outdir: Path) -> list[dict[str, Any]]:
    """Read scenario_table.csv and parse numeric columns."""
    path = outdir / "scenario_table.csv"
    rows: list[dict[str, Any]] = []
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            parsed: dict[str, Any] = {}
            for k, v in row.items():
                if k in _NUMERIC_COLS:
                    parsed[k] = _parse_num(v, k)
                else:
                    parsed[k] = v
            rows.append(parsed)
    return rows


def _load_regime_returns(outdir: Path, candidate: str) -> dict[str, Any] | None:
    """Read regime_returns_{candidate}.json. Returns None if missing."""
    path = outdir / f"regime_returns_{candidate}.json"
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def _load_dd_episodes(outdir: Path, candidate: str) -> list[dict[str, Any]]:
    """Read dd_episodes_{candidate}.csv, fall back to dd_episodes.json."""
    csv_path = outdir / f"dd_episodes_{candidate}.csv"
    if csv_path.exists():
        with open(csv_path, newline="") as f:
            rows = list(csv.DictReader(f))
        for row in rows:
            for k in ("drawdown_pct", "peak_nav", "trough_nav",
                       "days_to_trough", "days_to_recovery"):
                if k in row and row[k] not in ("", "None"):
                    row[k] = float(row[k])
                elif k in row:
                    row[k] = None
            for k in ("bars_to_trough", "bars_to_recovery"):
                if k in row and row[k] not in ("", "None"):
                    row[k] = int(row[k])
                elif k in row:
                    row[k] = None
        return rows

    json_path = outdir / "candidates" / candidate / "dd_episodes.json"
    if json_path.exists():
        with open(json_path) as f:
            return json.load(f)

    return []


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _group_by_candidate(rows: list[dict]) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = {}
    for r in rows:
        groups.setdefault(r["candidate"], []).append(r)
    return groups


def _get_row(rows: list[dict], scenario: str) -> dict | None:
    for r in rows:
        if r["scenario"] == scenario:
            return r
    return None


def _worst_case(rows: list[dict]) -> dict[str, Any]:
    scores = [r["score"] for r in rows if r["score"] is not None]
    cagrs = [r["cagr_pct"] for r in rows if r["cagr_pct"] is not None]
    mdds = [r["max_drawdown_mid_pct"] for r in rows if r["max_drawdown_mid_pct"] is not None]
    fee_drags = [r.get("fee_drag_pct_per_year") for r in rows
                 if r.get("fee_drag_pct_per_year") is not None]
    base = _get_row(rows, "base") or rows[0]
    return {
        "min_score": min(scores) if scores else None,
        "min_cagr": min(cagrs) if cagrs else None,
        "max_mdd": max(mdds) if mdds else None,
        "max_fee_drag": max(fee_drags) if fee_drags else None,
        "trades": base.get("trades"),
    }


# ---------------------------------------------------------------------------
# Gate evaluation
# ---------------------------------------------------------------------------

def evaluate(
    outdir: str | Path,
    baseline_name: str = "baseline_legacy",
) -> DecisionResult:
    """Read matrix artifacts and evaluate gate rules for each candidate.

    Returns a DecisionResult with per-candidate tags and a selected candidate.
    """
    outdir = Path(outdir)

    table = _load_scenario_table(outdir)
    by_cand = _group_by_candidate(table)

    if baseline_name not in by_cand:
        raise ValueError(
            f"Baseline '{baseline_name}' not found in scenario_table.csv. "
            f"Available: {sorted(by_cand)}"
        )

    # Baseline reference values
    bl_rows = by_cand[baseline_name]
    bl_harsh = _get_row(bl_rows, "harsh")
    bl_base = _get_row(bl_rows, "base") or bl_rows[0]
    bl_regime = _load_regime_returns(outdir, baseline_name)

    bl_harsh_mdd = bl_harsh["max_drawdown_mid_pct"] if bl_harsh else 999.0
    bl_harsh_score = bl_harsh["score"] if bl_harsh else -1e6
    bl_topping_ret = (
        bl_regime.get("TOPPING", {}).get("total_return_pct", -999.0)
        if bl_regime else -999.0
    )
    bl_turnover = bl_base.get("turnover_per_year", 999.0)

    scenarios_seen = sorted({r["scenario"] for r in table})
    gates: list[GateResult] = []

    for cand_name, rows in by_cand.items():
        reasons: list[str] = []
        tag = "HOLD"  # default

        worst = _worst_case(rows)
        regime = _load_regime_returns(outdir, cand_name)
        regime_subset = None
        if regime:
            regime_subset = {
                k: regime[k] for k in ("TOPPING", "SHOCK") if k in regime
            }

        dd_episodes = _load_dd_episodes(outdir, cand_name)
        top_dd = sorted(
            dd_episodes,
            key=lambda e: e.get("drawdown_pct", 0) if e.get("drawdown_pct") is not None else 0,
            reverse=True,
        )[:5]

        # --- REJECT gate 1: trades < 10 in any scenario ---
        for row in rows:
            t = row.get("trades")
            if t is not None and t < 10:
                tag = "REJECT"
                reasons.append(f"trades={t} < 10 in scenario '{row['scenario']}'")

        # --- REJECT gate 2: harsh MDD too high vs baseline ---
        if tag != "REJECT":
            harsh_row = _get_row(rows, "harsh")
            if harsh_row:
                harsh_mdd = harsh_row["max_drawdown_mid_pct"]
                if harsh_mdd is not None and harsh_mdd > bl_harsh_mdd + 5:
                    tag = "REJECT"
                    reasons.append(
                        f"harsh MDD {harsh_mdd:.1f}% > baseline "
                        f"{bl_harsh_mdd:.1f}% + 5"
                    )

        # --- PROMOTE gate (all 3 conditions) ---
        if tag != "REJECT":
            harsh_row = _get_row(rows, "harsh")
            base_row = _get_row(rows, "base") or rows[0]
            cand_topping_ret = (
                regime.get("TOPPING", {}).get("total_return_pct", -999.0)
                if regime else -999.0
            )
            cand_turnover = base_row.get("turnover_per_year", 999.0)

            cond_score = (harsh_row and harsh_row["score"] is not None
                          and harsh_row["score"] >= bl_harsh_score)
            cond_topping = cand_topping_ret >= bl_topping_ret
            cond_turnover = (cand_turnover is not None
                             and bl_turnover is not None
                             and cand_turnover <= 1.2 * bl_turnover)

            if cond_score and cond_topping and cond_turnover:
                tag = "PROMOTE"
                reasons.append("harsh score >= baseline")
                reasons.append("TOPPING return >= baseline")
                reasons.append(f"turnover {cand_turnover:.1f}x <= "
                               f"1.2 * baseline {bl_turnover:.1f}x")
            else:
                tag = "HOLD"
                if not cond_score:
                    h_score = harsh_row["score"] if harsh_row else None
                    reasons.append(
                        f"harsh score {h_score} < baseline {bl_harsh_score:.1f}"
                    )
                if not cond_topping:
                    reasons.append(
                        f"TOPPING return {cand_topping_ret:.1f}% < "
                        f"baseline {bl_topping_ret:.1f}%"
                    )
                if not cond_turnover:
                    reasons.append(
                        f"turnover {cand_turnover}x > "
                        f"1.2 * baseline {bl_turnover}x"
                    )

        gates.append(GateResult(
            name=cand_name,
            tag=tag,
            reasons=reasons,
            worst=worst,
            regime=regime_subset,
            top_dd=top_dd,
        ))

    # --- Selection: best PROMOTE by harsh score, else baseline ---
    promoted = [g for g in gates if g.tag == "PROMOTE"]
    if promoted:
        promoted.sort(
            key=lambda g: g.worst["min_score"] if g.worst["min_score"] is not None else -1e6,
            reverse=True,
        )
        selected = promoted[0].name
    else:
        selected = baseline_name

    metadata = {
        "git_hash": get_git_hash(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "scenarios": scenarios_seen,
    }

    return DecisionResult(selected=selected, gates=gates, metadata=metadata)


# ---------------------------------------------------------------------------
# Output writers
# ---------------------------------------------------------------------------

def write_decision_report(result: DecisionResult, outdir: str | Path) -> Path:
    """Write decision_report.md — human-readable summary."""
    outdir = Path(outdir)
    path = outdir / "decision_report.md"

    lines: list[str] = []
    lines.append("# Decision Report")
    lines.append("")
    lines.append(f"**Generated:** {result.metadata.get('timestamp', 'N/A')}")
    git = result.metadata.get("git_hash")
    if git:
        lines.append(f"**Git:** {git}")
    lines.append(f"**Scenarios:** {', '.join(result.metadata.get('scenarios', []))}")
    lines.append("")

    # --- Section 1: Worst-Case Summary ---
    lines.append("## 1. Worst-Case Across Scenarios")
    lines.append("")
    lines.append("| Candidate | Tag | Min Score | Min CAGR% | Max MDD% | Fee Drag%/yr | Trades |")
    lines.append("|-----------|-----|-----------|-----------|----------|--------------|--------|")
    for g in result.gates:
        w = g.worst
        lines.append(
            f"| {g.name} | **{g.tag}** "
            f"| {_fmt(w.get('min_score'))} "
            f"| {_fmt(w.get('min_cagr'))} "
            f"| {_fmt(w.get('max_mdd'))} "
            f"| {_fmt(w.get('max_fee_drag'))} "
            f"| {_fmt_int(w.get('trades'))} |"
        )
    lines.append("")

    # --- Section 2: Regime Analysis ---
    lines.append("## 2. Regime Analysis (TOPPING + SHOCK)")
    lines.append("")
    lines.append("| Candidate | TOPPING Return% | TOPPING MDD% | SHOCK Return% | SHOCK MDD% |")
    lines.append("|-----------|-----------------|--------------|---------------|------------|")
    for g in result.gates:
        if g.regime:
            top = g.regime.get("TOPPING", {})
            shk = g.regime.get("SHOCK", {})
            lines.append(
                f"| {g.name} "
                f"| {_fmt(top.get('total_return_pct'))} "
                f"| {_fmt(top.get('max_dd_pct'))} "
                f"| {_fmt(shk.get('total_return_pct'))} "
                f"| {_fmt(shk.get('max_dd_pct'))} |"
            )
        else:
            lines.append(f"| {g.name} | N/A | N/A | N/A | N/A |")
    lines.append("")

    # --- Section 3: Top Drawdown Episodes ---
    lines.append("## 3. Top 5 Drawdown Episodes")
    lines.append("")
    for g in result.gates:
        if not g.top_dd:
            continue
        lines.append(f"### {g.name}")
        lines.append("")
        lines.append("| # | DD% | Peak Date | Trough Date | Recovery Date | Days to Recovery |")
        lines.append("|---|-----|-----------|-------------|---------------|------------------|")
        for i, ep in enumerate(g.top_dd, 1):
            lines.append(
                f"| {i} "
                f"| {_fmt(ep.get('drawdown_pct'))} "
                f"| {ep.get('peak_date', 'N/A')} "
                f"| {ep.get('trough_date', 'N/A')} "
                f"| {ep.get('recovery_date', 'N/A') or 'ongoing'} "
                f"| {_fmt(ep.get('days_to_recovery')) or 'ongoing'} |"
            )
        lines.append("")

    # --- Section 4: Decision ---
    lines.append("## 4. Decision")
    lines.append("")
    lines.append(f"**Selected:** `{result.selected}`")
    lines.append("")
    for g in result.gates:
        lines.append(f"- **{g.name}** [{g.tag}]")
        for r in g.reasons:
            lines.append(f"  - {r}")
    lines.append("")

    path.write_text("\n".join(lines))
    return path


def write_decision_json(result: DecisionResult, outdir: str | Path) -> Path:
    """Write decision.json — machine-readable gate results."""
    outdir = Path(outdir)
    path = outdir / "decision.json"

    data = {
        "selected_candidate": result.selected,
        "metadata": result.metadata,
        "candidates": [
            {
                "name": g.name,
                "tag": g.tag,
                "reasons": g.reasons,
                "worst": g.worst,
            }
            for g in result.gates
        ],
    }

    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)

    return path


def _fmt(val: Any) -> str:
    if val is None:
        return "N/A"
    if isinstance(val, float):
        return f"{val:.2f}"
    return str(val)


def _fmt_int(val: Any) -> str:
    if val is None:
        return "N/A"
    return str(int(val))
