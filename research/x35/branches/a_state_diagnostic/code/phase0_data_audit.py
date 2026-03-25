"""Phase 0 data audit for x35 a_state_diagnostic."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(PROJECT))

from research.x35.shared.common import DEFAULT_END  # noqa: E402
from research.x35.shared.common import DEFAULT_START  # noqa: E402
from research.x35.shared.common import DEFAULT_WARMUP_DAYS  # noqa: E402
from research.x35.shared.common import aggregate_outer_bars  # noqa: E402
from research.x35.shared.common import bars_to_frame  # noqa: E402
from research.x35.shared.common import ensure_dir  # noqa: E402
from research.x35.shared.common import load_feed  # noqa: E402
from research.x35.shared.common import write_json  # noqa: E402
from research.x35.shared.state_definitions import FROZEN_SPECS  # noqa: E402

RESULTS_DIR = ensure_dir(Path(__file__).resolve().parents[1] / "results")


def build_markdown(payload: dict) -> str:
    lines = [
        "# X35 Phase 0 Data Audit",
        "",
        f"- Study id: `{payload['study_id']}`",
        f"- Window: `{payload['window']['start']}` -> `{payload['window']['end']}`",
        f"- Warmup days: `{payload['window']['warmup_days']}`",
        "",
        "## Feed Coverage",
        "",
        "| Series | Total bars | Report bars | First close | Last close |",
        "|--------|------------|-------------|-------------|------------|",
    ]

    for row in payload["coverage"]:
        lines.append(
            f"| {row['series']} | {row['total_bars']} | {row['report_bars']} | "
            f"{row['first_close']} | {row['last_close']} |"
        )

    lines.extend(
        [
            "",
            "## Candidate Warmup Audit",
            "",
            "| Spec | Clock | Pre-report bars | Required bars | Warmup |",
            "|------|-------|-----------------|---------------|--------|",
        ]
    )
    for row in payload["candidate_audit"]:
        lines.append(
            f"| `{row['spec_id']}` | {row['timeframe']} | {row['pre_report_bars']} | "
            f"{row['required_warmup_bars']} | {row['warmup_ok']} |"
        )

    return "\n".join(lines) + "\n"


def main() -> None:
    feed = load_feed()
    report_start_ms = int(feed.report_start_ms or 0)
    h4_df = bars_to_frame(feed.h4_bars, report_start_ms)
    d1_df = bars_to_frame(feed.d1_bars, report_start_ms)
    w1_df = aggregate_outer_bars(d1_df, "W1")
    m1_df = aggregate_outer_bars(d1_df, "M1")

    coverage = []
    for label, frame in (("H4", h4_df), ("D1", d1_df), ("W1", w1_df), ("M1", m1_df)):
        report_bars = int((frame["close_time"] >= report_start_ms).sum())
        coverage.append(
            {
                "series": label,
                "total_bars": int(len(frame)),
                "report_bars": report_bars,
                "first_close": str(frame["dt_close"].iloc[0].date()),
                "last_close": str(frame["dt_close"].iloc[-1].date()),
            }
        )

    candidate_audit = []
    for spec in FROZEN_SPECS:
        outer = w1_df if spec.timeframe == "W1" else m1_df
        pre_report_bars = int((outer["close_time"] < report_start_ms).sum())
        candidate_audit.append(
            {
                "spec_id": spec.spec_id,
                "timeframe": spec.timeframe,
                "pre_report_bars": pre_report_bars,
                "required_warmup_bars": spec.required_warmup_bars,
                "warmup_ok": "PASS" if pre_report_bars >= spec.required_warmup_bars else "FAIL",
            }
        )

    payload = {
        "study_id": "x35_long_horizon_regime",
        "window": {
            "start": DEFAULT_START,
            "end": DEFAULT_END,
            "warmup_days": DEFAULT_WARMUP_DAYS,
            "report_start_ms": report_start_ms,
        },
        "coverage": coverage,
        "candidate_audit": candidate_audit,
    }

    json_path = RESULTS_DIR / "phase0_data_audit.json"
    md_path = RESULTS_DIR / "phase0_data_audit.md"
    write_json(json_path, payload)
    md_path.write_text(build_markdown(payload), encoding="utf-8")

    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")


if __name__ == "__main__":
    main()
