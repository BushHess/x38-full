from __future__ import annotations

import json

import numpy as np
from validation.output import write_json
from validation.suites.trade_level import _bootstrap_mean_diff_summary
from validation.suites.trade_level import _match_trades


def _strict_json_loads(text: str) -> dict:
    def _raise_constant(value: str) -> None:
        raise ValueError(f"non-strict JSON constant: {value}")

    return json.loads(text, parse_constant=_raise_constant)


def _trade_row(trade_id: int, entry_ts_ms: int, pnl_usd: float, side: str = "long") -> dict:
    return {
        "trade_id": trade_id,
        "side": side,
        "entry_ts": f"t{entry_ts_ms}",
        "exit_ts": f"t{entry_ts_ms + 10}",
        "entry_ts_ms": entry_ts_ms,
        "exit_ts_ms": entry_ts_ms + 10,
        "return_pct": pnl_usd / 100.0,
        "pnl_usd": pnl_usd,
        "fees_usd": 1.0,
        "entry_reason": "entry",
        "exit_reason": "exit",
        "max_exposure_during_trade": 1.0,
        "exposure_at_entry": 0.5,
        "exposure_at_exit": 0.0,
    }


def test_bootstrap_return_diff_json_is_strict(tmp_path) -> None:
    series = np.linspace(-0.002, 0.003, 256, dtype=np.float64)
    payload = _bootstrap_mean_diff_summary(
        series,
        block_len=42,
        n_resamples=500,
        seed=7,
    )

    path = write_json(payload, tmp_path / "bootstrap_return_diff.json")
    loaded = _strict_json_loads(path.read_text())

    assert loaded["n_obs"] == 256
    assert loaded["block_len"] == 42
    assert loaded["n_resamples"] == 500
    for key in ["mean_diff", "ci95_low", "ci95_high", "p_gt_0"]:
        assert isinstance(loaded[key], float)


def test_bootstrap_seed_reproducible_and_changes_with_seed() -> None:
    series = np.sin(np.linspace(0.0, 8.0, 300, dtype=np.float64)) * 0.001
    a = _bootstrap_mean_diff_summary(
        series,
        block_len=84,
        n_resamples=800,
        seed=1337,
    )
    b = _bootstrap_mean_diff_summary(
        series,
        block_len=84,
        n_resamples=800,
        seed=1337,
    )
    c = _bootstrap_mean_diff_summary(
        series,
        block_len=84,
        n_resamples=800,
        seed=1338,
    )

    assert a == b
    assert (
        a["ci95_low"] != c["ci95_low"]
        or a["ci95_high"] != c["ci95_high"]
        or a["p_gt_0"] != c["p_gt_0"]
    )


def test_match_trades_deterministic_with_tie_breaking() -> None:
    candidate = [
        _trade_row(1, 100, 10.0),
        _trade_row(2, 200, -5.0),
    ]
    baseline = [
        _trade_row(11, 104, 2.0),   # tie on |delta|=4 (later)
        _trade_row(10, 96, 1.0),    # tie on |delta|=4 (earlier) -> should win
        _trade_row(12, 204, -1.0),  # closest for candidate 2
    ]

    matched_a, cand_only_a, base_only_a = _match_trades(candidate, baseline, tolerance_ms=10)
    matched_b, cand_only_b, base_only_b = _match_trades(candidate, baseline, tolerance_ms=10)

    assert matched_a == matched_b
    assert cand_only_a == cand_only_b == []
    assert base_only_a == base_only_b
    assert [row["trade_id"] for row in base_only_a] == [11]
    assert [row["baseline_trade_id"] for row in matched_a] == [10, 12]


def test_match_trades_optimal_over_greedy() -> None:
    """Regression: greedy nearest-neighbor can produce suboptimal pairings.

    Counterexample: candidate entries [0, 1, 2], baseline [0, 2, 4], tol=1.
    Greedy (process cand in order): cand[0]→base[0] (d=0), cand[1]→base[1] (d=1),
      cand[2] unmatched (base[1] taken, base[2] too far).  Total distance = 1.
    Optimal: cand[0]→base[0] (d=0), cand[2]→base[1] (d=0),
      cand[1] unmatched.  Total distance = 0.
    """
    candidate = [
        _trade_row(1, 0, 10.0),
        _trade_row(2, 1, -50.0),
        _trade_row(3, 2, 20.0),
    ]
    baseline = [
        _trade_row(10, 0, 5.0),
        _trade_row(11, 2, 100.0),
        _trade_row(12, 4, -10.0),
    ]

    matched, cand_only, base_only = _match_trades(candidate, baseline, tolerance_ms=1)

    # Optimal: 2 matches with total distance 0
    assert len(matched) == 2
    matched_pairs = {
        (row["candidate_trade_id"], row["baseline_trade_id"]) for row in matched
    }
    assert matched_pairs == {(1, 10), (3, 11)}, (
        f"Expected optimal assignment (1→10, 3→11) but got {matched_pairs}"
    )
    # cand[2] (trade_id=2) is unmatched, base[12] is unmatched
    assert [row["trade_id"] for row in cand_only] == [2]
    assert [row["trade_id"] for row in base_only] == [12]
    # Both matched pairs have delta=0
    for row in matched:
        assert row["entry_ts_delta_ms"] == 0
