"""Base suite interfaces and shared context."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from v10.core.config import LiveConfig
from v10.core.data import DataFeed
from v10.core.types import BacktestResult
from validation.config import ValidationConfig


@dataclass
class SuiteContext:
    feed: DataFeed
    data_path: Path
    project_root: Path

    candidate_factory: Any
    baseline_factory: Any

    candidate_live_config: LiveConfig
    baseline_live_config: LiveConfig

    candidate_config_obj: Any
    baseline_config_obj: Any

    validation_config: ValidationConfig
    resolved_suites: list[str]

    outdir: Path
    results_dir: Path
    reports_dir: Path

    backtest_cache: dict[tuple[str, str], BacktestResult] = field(default_factory=dict)
    run_warnings: list[str] = field(default_factory=list)

    logger: logging.Logger = field(default_factory=lambda: logging.getLogger("validation"))


@dataclass
class SuiteResult:
    name: str
    status: str  # pass | fail | skip | error | info
    data: dict[str, Any] = field(default_factory=dict)
    artifacts: list[Path] = field(default_factory=list)
    duration_seconds: float = 0.0
    error_message: str | None = None


class BaseSuite(ABC):
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    def run(self, ctx: SuiteContext) -> SuiteResult:
        ...

    def skip_reason(self, ctx: SuiteContext) -> str | None:
        return None
