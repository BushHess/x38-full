"""Alert dispatcher for live trading — Telegram, webhook, console.

Supports:
  - Console logging (always on)
  - Telegram Bot API (if TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID set)
  - Generic webhook POST (if ALERT_WEBHOOK_URL set)

Usage:
    from monitoring.alerts import AlertDispatcher, AlertEvent, AlertLevel

    dispatcher = AlertDispatcher()  # reads env vars
    dispatcher.send(AlertEvent(
        level=AlertLevel.WARN,
        title="Regime Change",
        message="NORMAL -> AMBER (6m MDD 47.2%)",
    ))

    # Convenience methods:
    dispatcher.regime_change("NORMAL", "AMBER", 0.472, 0.31)
    dispatcher.order_filled("BUY", 0.001, 68275.0, "ema_cross")
    dispatcher.risk_halt("kill_switch_dd", nav=9500.0, dd=0.46)
"""

from __future__ import annotations

import json
import logging
import os
import urllib.request
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AlertLevel(Enum):
    INFO = "INFO"
    WARN = "WARN"
    CRITICAL = "CRITICAL"


@dataclass
class AlertEvent:
    level: AlertLevel
    title: str
    message: str
    data: dict[str, Any] = field(default_factory=dict)


class AlertDispatcher:
    """Send alerts via Telegram, webhook, and/or console log.

    Configure via constructor args or environment variables:
        TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, ALERT_WEBHOOK_URL
    """

    def __init__(
        self,
        *,
        telegram_token: str = "",
        telegram_chat_id: str = "",
        webhook_url: str = "",
        bot_name: str = "E5_ema21D1",
    ):
        self._log = logging.getLogger("alerts")
        self._tg_token = telegram_token or os.environ.get("TELEGRAM_BOT_TOKEN", "")
        self._tg_chat = telegram_chat_id or os.environ.get("TELEGRAM_CHAT_ID", "")
        self._webhook = webhook_url or os.environ.get("ALERT_WEBHOOK_URL", "")
        self._bot_name = bot_name

    @property
    def has_telegram(self) -> bool:
        return bool(self._tg_token and self._tg_chat)

    @property
    def has_webhook(self) -> bool:
        return bool(self._webhook)

    def send(self, event: AlertEvent) -> None:
        """Dispatch alert to all configured channels."""
        self._log_alert(event)
        if self.has_telegram:
            self._send_telegram(event)
        if self.has_webhook:
            self._send_webhook(event)

    # ── Convenience methods ──────────────────────────────────

    def regime_change(
        self, old: str, new: str, mdd_6m: float, mdd_12m: float,
    ) -> None:
        """Alert on regime transition (NORMAL/AMBER/RED)."""
        if old == new:
            return
        level = AlertLevel.CRITICAL if new == "RED" else (
            AlertLevel.WARN if new == "AMBER" else AlertLevel.INFO
        )
        self.send(AlertEvent(
            level=level,
            title=f"Regime: {old} -> {new}",
            message=f"MDD 6m={mdd_6m:.1%} | MDD 12m={mdd_12m:.1%}",
            data={
                "old": old, "new": new,
                "mdd_6m": f"{mdd_6m:.2%}", "mdd_12m": f"{mdd_12m:.2%}",
            },
        ))

    def risk_halt(self, reason: str, nav: float, dd: float) -> None:
        """Alert when a risk guard halts trading."""
        self.send(AlertEvent(
            level=AlertLevel.CRITICAL,
            title="RISK GUARD HALT",
            message=f"{reason} | NAV=${nav:,.2f} DD={dd:.1%}",
            data={"reason": reason, "nav": f"${nav:,.2f}", "dd": f"{dd:.2%}"},
        ))

    def order_filled(
        self, side: str, qty: float, price: float, reason: str,
    ) -> None:
        """Alert on order fill (INFO level)."""
        self.send(AlertEvent(
            level=AlertLevel.INFO,
            title=f"Order {side}",
            message=f"{qty:.5f} BTC @ ${price:,.2f} ({reason})",
        ))

    def parity_mismatch(
        self, expected: str, actual: str, diff_pct: float,
    ) -> None:
        """Alert on parity checker mismatch (shadow vs live)."""
        self.send(AlertEvent(
            level=AlertLevel.CRITICAL,
            title="PARITY MISMATCH",
            message=f"Expected {expected}, got {actual} (diff {diff_pct:.1%})",
        ))

    def bot_started(self, mode: str, strategy: str) -> None:
        self.send(AlertEvent(
            level=AlertLevel.INFO,
            title="Bot Started",
            message=f"Mode: {mode} | Strategy: {strategy}",
        ))

    def bot_stopped(self, reason: str, cycles: int) -> None:
        level = AlertLevel.CRITICAL if "error" in reason.lower() else AlertLevel.INFO
        self.send(AlertEvent(
            level=level,
            title="Bot Stopped",
            message=f"Reason: {reason} | Cycles: {cycles}",
        ))

    # ── Internal ─────────────────────────────────────────────

    def _log_alert(self, event: AlertEvent) -> None:
        level_map = {
            AlertLevel.INFO: logging.INFO,
            AlertLevel.WARN: logging.WARNING,
            AlertLevel.CRITICAL: logging.ERROR,
        }
        self._log.log(
            level_map.get(event.level, logging.INFO),
            "[%s] %s: %s", event.level.value, event.title, event.message,
        )

    def _send_telegram(self, event: AlertEvent) -> None:
        icons = {"INFO": "ℹ️", "WARN": "⚠️", "CRITICAL": "🚨"}
        icon = icons.get(event.level.value, "")
        text = f"{icon} *{self._bot_name}*\n*{event.title}*\n{event.message}"
        if event.data:
            details = "\n".join(f"  {k}: {v}" for k, v in event.data.items())
            text += f"\n```\n{details}\n```"

        payload = json.dumps({
            "chat_id": self._tg_chat,
            "text": text,
            "parse_mode": "Markdown",
        }).encode()
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{self._tg_token}/sendMessage",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        try:
            urllib.request.urlopen(req, timeout=10)
        except Exception as e:
            self._log.warning("Telegram send failed: %s", e)

    def _send_webhook(self, event: AlertEvent) -> None:
        payload = json.dumps({
            "bot": self._bot_name,
            "level": event.level.value,
            "title": event.title,
            "message": event.message,
            "data": event.data,
        }).encode()
        req = urllib.request.Request(
            self._webhook,
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        try:
            urllib.request.urlopen(req, timeout=10)
        except Exception as e:
            self._log.warning("Webhook send failed: %s", e)
