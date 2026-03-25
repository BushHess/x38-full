"""Parity tool: paper vs backtest signal comparison.

Inputs:
    --paper-signals   path to paper_signals.csv
    --backtest-equity path to backtest equity.csv (derive signals from equity)
    OR
    --backtest-signals path to backtest signals dump (direct comparison)
    --paper-equity    path to paper_equity.csv (optional equity comparison)
    --tolerance       numeric tolerance (default 1e-6)

Checks:
    1. Same H4 close timestamps sequence
    2. Same target_exposure per bar (within tolerance)
    3. Same entry/exit event timestamps (bar-level)

Exit codes:
    0 — pass (all checks match)
    2 — mismatch (prints first mismatch + diagnostic JSON)
"""

from __future__ import annotations

import csv
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class SignalRow:
    """Normalised signal record for comparison."""
    h4_close_ms: int
    target_exposure: float | None
    entry_reason: str
    exit_reason: str


@dataclass
class EquityRow:
    """Normalised equity record for comparison."""
    close_time_ms: int
    nav_mid: float
    cash: float
    btc_qty: float
    exposure: float


# ---------------------------------------------------------------------------
# CSV loaders
# ---------------------------------------------------------------------------

def _load_paper_signals(path: Path) -> list[SignalRow]:
    """Load paper_signals.csv → list[SignalRow]."""
    rows: list[SignalRow] = []
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            te_str = r["target_exposure"].strip()
            te = float(te_str) if te_str else None
            rows.append(SignalRow(
                h4_close_ms=int(r["h4_close_ms"]),
                target_exposure=te,
                entry_reason=r.get("entry_reason", ""),
                exit_reason=r.get("exit_reason", ""),
            ))
    return rows


def _load_paper_equity(path: Path) -> list[EquityRow]:
    """Load paper_equity.csv → list[EquityRow]."""
    rows: list[EquityRow] = []
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            rows.append(EquityRow(
                close_time_ms=int(r["close_time_ms"]),
                nav_mid=float(r["nav_mid"]),
                cash=float(r["cash"]),
                btc_qty=float(r["btc_qty"]),
                exposure=float(r["exposure"]),
            ))
    return rows


def _load_backtest_equity(path: Path) -> list[EquityRow]:
    """Load backtest equity.csv → list[EquityRow]."""
    rows: list[EquityRow] = []
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            rows.append(EquityRow(
                close_time_ms=int(r["close_time_ms"]),
                nav_mid=float(r["nav_mid"]),
                cash=float(r["cash"]),
                btc_qty=float(r["btc_qty"]),
                exposure=float(r["exposure"]),
            ))
    return rows


def _derive_signals_from_equity(
    equity: list[EquityRow],
    tol: float = 1e-6,
) -> list[SignalRow]:
    """Derive entry/exit signals from equity exposure transitions.

    A signal is emitted at bar i whenever the exposure changes between
    bar i-1 and bar i by more than tol.
    """
    signals: list[SignalRow] = []
    if not equity:
        return signals

    prev_exp = 0.0
    for eq in equity:
        delta = eq.exposure - prev_exp
        entry_reason = ""
        exit_reason = ""
        if delta > tol:
            entry_reason = "entry"
        elif delta < -tol:
            if eq.exposure < tol:
                exit_reason = "full_exit"
            else:
                exit_reason = "partial_exit"

        if entry_reason or exit_reason:
            signals.append(SignalRow(
                h4_close_ms=eq.close_time_ms,
                target_exposure=eq.exposure,
                entry_reason=entry_reason,
                exit_reason=exit_reason,
            ))
        prev_exp = eq.exposure

    return signals


# ---------------------------------------------------------------------------
# Comparison checks
# ---------------------------------------------------------------------------

@dataclass
class Mismatch:
    check: str
    index: int
    detail: dict[str, Any]


def check_timestamps(
    paper: list[SignalRow],
    bt: list[SignalRow],
) -> Mismatch | None:
    """Check 1: Same H4 close timestamps sequence."""
    p_ts = [s.h4_close_ms for s in paper]
    b_ts = [s.h4_close_ms for s in bt]

    if len(p_ts) != len(b_ts):
        return Mismatch(
            check="timestamps_count",
            index=min(len(p_ts), len(b_ts)),
            detail={
                "paper_signal_count": len(p_ts),
                "backtest_signal_count": len(b_ts),
                "paper_ts": p_ts[:10],
                "backtest_ts": b_ts[:10],
            },
        )

    for i, (pt, bt_) in enumerate(zip(p_ts, b_ts)):
        if pt != bt_:
            return Mismatch(
                check="timestamp_value",
                index=i,
                detail={
                    "paper_h4_close_ms": pt,
                    "backtest_h4_close_ms": bt_,
                },
            )
    return None


def check_target_exposure(
    paper: list[SignalRow],
    bt: list[SignalRow],
    tol: float,
) -> Mismatch | None:
    """Check 2: Same target_exposure per signal bar (within tolerance)."""
    n = min(len(paper), len(bt))
    for i in range(n):
        p_te = paper[i].target_exposure
        b_te = bt[i].target_exposure

        # Both None → match
        if p_te is None and b_te is None:
            continue

        # One None → mismatch
        if p_te is None or b_te is None:
            return Mismatch(
                check="target_exposure_none",
                index=i,
                detail={
                    "h4_close_ms": paper[i].h4_close_ms,
                    "paper_target_exposure": p_te,
                    "backtest_target_exposure": b_te,
                },
            )

        if abs(p_te - b_te) > tol:
            return Mismatch(
                check="target_exposure_value",
                index=i,
                detail={
                    "h4_close_ms": paper[i].h4_close_ms,
                    "paper_target_exposure": p_te,
                    "backtest_target_exposure": b_te,
                    "delta": abs(p_te - b_te),
                    "tolerance": tol,
                },
            )
    return None


def check_entry_exit_events(
    paper: list[SignalRow],
    bt: list[SignalRow],
) -> Mismatch | None:
    """Check 3: Same entry/exit event timestamps (bar-level)."""
    p_events = [
        (s.h4_close_ms, bool(s.entry_reason), bool(s.exit_reason))
        for s in paper
    ]
    b_events = [
        (s.h4_close_ms, bool(s.entry_reason), bool(s.exit_reason))
        for s in bt
    ]

    n = min(len(p_events), len(b_events))
    for i in range(n):
        if p_events[i] != b_events[i]:
            return Mismatch(
                check="entry_exit_event",
                index=i,
                detail={
                    "h4_close_ms": p_events[i][0],
                    "paper_has_entry": p_events[i][1],
                    "paper_has_exit": p_events[i][2],
                    "backtest_has_entry": b_events[i][1],
                    "backtest_has_exit": b_events[i][2],
                },
            )
    return None


def check_equity_curve(
    paper_eq: list[EquityRow],
    bt_eq: list[EquityRow],
    tol: float,
) -> Mismatch | None:
    """Optional check: equity curves match (timestamps + values)."""
    if len(paper_eq) != len(bt_eq):
        return Mismatch(
            check="equity_count",
            index=min(len(paper_eq), len(bt_eq)),
            detail={
                "paper_equity_count": len(paper_eq),
                "backtest_equity_count": len(bt_eq),
            },
        )

    for i, (pe, be) in enumerate(zip(paper_eq, bt_eq)):
        if pe.close_time_ms != be.close_time_ms:
            return Mismatch(
                check="equity_timestamp",
                index=i,
                detail={
                    "paper_close_time_ms": pe.close_time_ms,
                    "backtest_close_time_ms": be.close_time_ms,
                },
            )
        if abs(pe.nav_mid - be.nav_mid) > tol:
            return Mismatch(
                check="equity_nav_mid",
                index=i,
                detail={
                    "close_time_ms": pe.close_time_ms,
                    "paper_nav_mid": pe.nav_mid,
                    "backtest_nav_mid": be.nav_mid,
                    "delta": abs(pe.nav_mid - be.nav_mid),
                },
            )
        if abs(pe.exposure - be.exposure) > tol:
            return Mismatch(
                check="equity_exposure",
                index=i,
                detail={
                    "close_time_ms": pe.close_time_ms,
                    "paper_exposure": pe.exposure,
                    "backtest_exposure": be.exposure,
                    "delta": abs(pe.exposure - be.exposure),
                },
            )

    return None


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def compare(
    paper_signals_path: Path | None = None,
    backtest_equity_path: Path | None = None,
    backtest_signals_path: Path | None = None,
    paper_equity_path: Path | None = None,
    tolerance: float = 1e-6,
) -> list[Mismatch]:
    """Run all parity checks. Returns list of mismatches (empty = pass).

    Two modes:
      A) Equity-only: --paper-equity + --backtest-equity
         Gold standard — compares timestamps, NAV, and exposure directly.
      B) Signal-level: --paper-signals + --backtest-signals
         Compares signal timestamps, target_exposure, and entry/exit events.

    Both modes can run together if all four paths are provided.
    """
    mismatches: list[Mismatch] = []

    # Mode A: direct equity curve comparison (gold standard)
    if paper_equity_path and backtest_equity_path:
        paper_eq = _load_paper_equity(paper_equity_path)
        bt_eq = _load_backtest_equity(backtest_equity_path)
        m = check_equity_curve(paper_eq, bt_eq, tolerance)
        if m:
            mismatches.append(m)
            return mismatches  # equity mismatch is definitive

    # Mode B: signal-level comparison
    if paper_signals_path and backtest_signals_path:
        paper_sigs = _load_paper_signals(paper_signals_path)
        bt_sigs = _load_paper_signals(backtest_signals_path)

        # Check 1: timestamps
        m = check_timestamps(paper_sigs, bt_sigs)
        if m:
            mismatches.append(m)
            return mismatches

        # Check 2: target exposure
        m = check_target_exposure(paper_sigs, bt_sigs, tolerance)
        if m:
            mismatches.append(m)

        # Check 3: entry/exit events
        m = check_entry_exit_events(paper_sigs, bt_sigs)
        if m:
            mismatches.append(m)

    if not paper_equity_path and not backtest_equity_path \
       and not paper_signals_path and not backtest_signals_path:
        raise ValueError(
            "Must provide either equity paths or signal paths for comparison"
        )

    return mismatches


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="V10 Parity Tool: paper vs backtest comparison",
    )
    parser.add_argument(
        "--paper-signals", default=None,
        help="Path to paper_signals.csv (for signal-level comparison)",
    )
    parser.add_argument(
        "--backtest-equity", default=None,
        help="Path to backtest equity.csv (for equity curve comparison)",
    )
    parser.add_argument(
        "--backtest-signals", default=None,
        help="Path to backtest signals dump CSV (for signal-level comparison)",
    )
    parser.add_argument(
        "--paper-equity", default=None,
        help="Path to paper_equity.csv (for equity curve comparison)",
    )
    parser.add_argument(
        "--tolerance", type=float, default=1e-6,
        help="Numeric tolerance for float comparisons (default: 1e-6)",
    )
    args = parser.parse_args(argv)

    has_equity = args.paper_equity and args.backtest_equity
    has_signals = args.paper_signals and args.backtest_signals
    if not has_equity and not has_signals:
        parser.error(
            "Must provide either (--paper-equity + --backtest-equity) "
            "or (--paper-signals + --backtest-signals)"
        )

    mismatches = compare(
        paper_signals_path=(
            Path(args.paper_signals) if args.paper_signals else None
        ),
        backtest_equity_path=(
            Path(args.backtest_equity) if args.backtest_equity else None
        ),
        backtest_signals_path=(
            Path(args.backtest_signals) if args.backtest_signals else None
        ),
        paper_equity_path=(
            Path(args.paper_equity) if args.paper_equity else None
        ),
        tolerance=args.tolerance,
    )

    if not mismatches:
        print("PASS: all parity checks passed")
        return 0

    # Print first mismatch + dump diagnostic JSON
    m = mismatches[0]
    print(f"MISMATCH: {m.check} at index {m.index}", file=sys.stderr)
    diagnostic = {
        "status": "mismatch",
        "total_mismatches": len(mismatches),
        "first_mismatch": {
            "check": m.check,
            "index": m.index,
            "detail": m.detail,
        },
    }
    print(json.dumps(diagnostic, indent=2), file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
