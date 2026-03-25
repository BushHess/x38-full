"""Drawdown episode detection and recovery table.

Walks the equity curve tracking running peak. When drawdown from peak
exceeds min_dd_pct, opens an episode. On recovery (NAV >= peak), closes it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from v10.core.types import EquitySnap


@dataclass(slots=True)
class DrawdownEpisode:
    """A single peak-to-trough-to-recovery drawdown episode."""
    peak_ms: int
    peak_nav: float
    trough_ms: int
    trough_nav: float
    recovery_ms: int | None  # None = still ongoing at end of data
    drawdown_pct: float      # positive number, e.g. 25.0 for -25%
    bars_to_trough: int
    bars_to_recovery: int | None
    days_to_trough: float
    days_to_recovery: float | None


def detect_drawdown_episodes(
    equity: list[EquitySnap],
    min_dd_pct: float = 5.0,
) -> list[DrawdownEpisode]:
    """Detect drawdown episodes exceeding *min_dd_pct* from equity curve.

    Returns episodes sorted by start time (peak_ms).
    """
    if len(equity) < 2:
        return []

    episodes: list[DrawdownEpisode] = []
    peak_nav = equity[0].nav_mid
    peak_ms = equity[0].close_time
    peak_idx = 0

    in_episode = False
    trough_nav = peak_nav
    trough_ms = peak_ms
    trough_idx = 0
    episode_peak_nav = peak_nav
    episode_peak_ms = peak_ms
    episode_peak_idx = 0

    for i, snap in enumerate(equity):
        nav = snap.nav_mid

        if nav >= peak_nav:
            # New high or recovery
            if in_episode:
                # Close the episode
                dd_pct = (1.0 - trough_nav / episode_peak_nav) * 100.0
                days_to_trough = (trough_ms - episode_peak_ms) / 86_400_000.0
                days_to_recovery = (snap.close_time - episode_peak_ms) / 86_400_000.0
                episodes.append(DrawdownEpisode(
                    peak_ms=episode_peak_ms,
                    peak_nav=episode_peak_nav,
                    trough_ms=trough_ms,
                    trough_nav=trough_nav,
                    recovery_ms=snap.close_time,
                    drawdown_pct=dd_pct,
                    bars_to_trough=trough_idx - episode_peak_idx,
                    bars_to_recovery=i - episode_peak_idx,
                    days_to_trough=days_to_trough,
                    days_to_recovery=days_to_recovery,
                ))
                in_episode = False

            peak_nav = nav
            peak_ms = snap.close_time
            peak_idx = i

        else:
            dd = (1.0 - nav / peak_nav) * 100.0
            if not in_episode and dd >= min_dd_pct:
                # Open new episode
                in_episode = True
                episode_peak_nav = peak_nav
                episode_peak_ms = peak_ms
                episode_peak_idx = peak_idx
                trough_nav = nav
                trough_ms = snap.close_time
                trough_idx = i
            elif in_episode and nav < trough_nav:
                # Deeper trough
                trough_nav = nav
                trough_ms = snap.close_time
                trough_idx = i

    # Close any ongoing episode
    if in_episode:
        dd_pct = (1.0 - trough_nav / episode_peak_nav) * 100.0
        days_to_trough = (trough_ms - episode_peak_ms) / 86_400_000.0
        episodes.append(DrawdownEpisode(
            peak_ms=episode_peak_ms,
            peak_nav=episode_peak_nav,
            trough_ms=trough_ms,
            trough_nav=trough_nav,
            recovery_ms=None,
            drawdown_pct=dd_pct,
            bars_to_trough=trough_idx - episode_peak_idx,
            bars_to_recovery=None,
            days_to_trough=days_to_trough,
            days_to_recovery=None,
        ))

    return episodes


def recovery_table(episodes: list[DrawdownEpisode]) -> list[dict[str, Any]]:
    """Convert episodes to a list of dicts for CSV/JSON output."""
    from v10.core.formatting import ms_to_iso

    rows: list[dict[str, Any]] = []
    for ep in episodes:
        rows.append({
            "peak_date": ms_to_iso(ep.peak_ms),
            "peak_nav": round(ep.peak_nav, 2),
            "trough_date": ms_to_iso(ep.trough_ms),
            "trough_nav": round(ep.trough_nav, 2),
            "recovery_date": ms_to_iso(ep.recovery_ms) if ep.recovery_ms else None,
            "drawdown_pct": round(ep.drawdown_pct, 2),
            "bars_to_trough": ep.bars_to_trough,
            "bars_to_recovery": ep.bars_to_recovery,
            "days_to_trough": round(ep.days_to_trough, 1),
            "days_to_recovery": round(ep.days_to_recovery, 1) if ep.days_to_recovery is not None else None,
        })
    return rows
