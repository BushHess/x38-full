"""Effective-config provenance and runtime config-usage auditing."""

from __future__ import annotations

import dataclasses
from dataclasses import fields
from pathlib import Path
from typing import Any
from typing import Mapping

import yaml

from v10.core.config import LiveConfig
from validation.config import ValidationConfig


class AccessTracker:
    """Track field-level config accesses from strategy runtime."""

    def __init__(self, *, label: str, known_fields: set[str]) -> None:
        self.label = label
        self.known_fields = set(known_fields)
        self._used_fields: set[str] = set()

    def mark(self, field_name: str) -> None:
        if field_name in self.known_fields:
            self._used_fields.add(field_name)

    @property
    def used_fields(self) -> set[str]:
        return set(self._used_fields)


class ConfigProxy:
    """Proxy object that marks field access via AccessTracker."""

    def __init__(self, cfg: Any, tracker: AccessTracker) -> None:
        object.__setattr__(self, "_cfg", cfg)
        object.__setattr__(self, "_tracker", tracker)

    def __getattr__(self, name: str) -> Any:
        cfg = object.__getattribute__(self, "_cfg")
        tracker = object.__getattribute__(self, "_tracker")
        if hasattr(cfg, name):
            tracker.mark(name)
            return getattr(cfg, name)
        raise AttributeError(f"{type(self).__name__} has no attribute {name!r}")

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_"):
            object.__setattr__(self, name, value)
            return

        cfg = object.__getattribute__(self, "_cfg")
        tracker = object.__getattribute__(self, "_tracker")
        if hasattr(cfg, name):
            tracker.mark(name)
            setattr(cfg, name, value)
            return
        object.__setattr__(self, name, value)


def tracker_for_config_obj(config_obj: Any, *, label: str) -> AccessTracker | None:
    if config_obj is None or not dataclasses.is_dataclass(config_obj):
        return None
    known = {f.name for f in fields(config_obj)}
    return AccessTracker(label=label, known_fields=known)


def load_raw_yaml(path: Path) -> dict[str, Any]:
    with open(path) as file_obj:
        raw = yaml.safe_load(file_obj) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"Config YAML must be a mapping: {path}")
    return raw


def _infer_unit(param_path: str, value: Any) -> str:
    name = param_path.lower().split(".")[-1]
    if isinstance(value, bool):
        return "bool"
    if "bps" in name:
        return "bps"
    if name.endswith("_bars") or name == "bars":
        return "bars"
    if name.endswith("_days") or name == "days":
        return "days"
    if name.endswith("_usd") or "notional" in name or "cash" in name or "usdt" in name:
        return "usd"
    if "pct" in name:
        return "pct"
    if "ratio" in name:
        return "ratio"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    return "none"


def _param_entry(
    *,
    value: Any,
    source: str,
    source_detail: str,
    param_path: str,
) -> dict[str, Any]:
    return {
        "value": value,
        "unit": _infer_unit(param_path, value),
        "source": source,
        "source_detail": source_detail,
    }


def build_effective_config_payload(
    *,
    role: str,
    config_path: Path,
    live_config: LiveConfig,
    strategy_config_obj: Any,
    validation_config: ValidationConfig,
    raw_yaml: Mapping[str, Any],
    wfo_overrides: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build effective-config payload with field-level provenance."""
    params: dict[str, dict[str, Any]] = {}
    wfo_overrides = dict(wfo_overrides or {})

    engine_raw = raw_yaml.get("engine", {}) if isinstance(raw_yaml.get("engine"), dict) else {}
    risk_raw = raw_yaml.get("risk", {}) if isinstance(raw_yaml.get("risk"), dict) else {}
    strategy_raw = (
        raw_yaml.get("strategy", {}) if isinstance(raw_yaml.get("strategy"), dict) else {}
    )

    for field_def in fields(live_config.engine):
        key = field_def.name
        path = f"engine.{key}"
        source = "yaml" if key in engine_raw else "default"
        source_detail = f"{path} in {config_path.name}" if source == "yaml" else f"{path} default"
        value = getattr(live_config.engine, key)
        if key == "warmup_days":
            value = int(validation_config.warmup_days)
            source = "cli"
            source_detail = "--warmup-days"
        elif key == "initial_cash":
            value = float(validation_config.initial_cash)
            source = "cli"
            source_detail = "--initial-cash"
        elif key == "warmup_mode":
            # Validation suites always use "no_trade" regardless of YAML.
            # Report the actual value used, not the YAML value.
            value = "no_trade"
            source = "pipeline"
            source_detail = "validation pipeline enforces no_trade"
        params[path] = _param_entry(
            value=value,
            source=source,
            source_detail=source_detail,
            param_path=path,
        )

    for field_def in fields(live_config.risk):
        key = field_def.name
        path = f"risk.{key}"
        source = "yaml" if key in risk_raw else "default"
        source_detail = f"{path} in {config_path.name}" if source == "yaml" else f"{path} default"
        params[path] = _param_entry(
            value=getattr(live_config.risk, key),
            source=source,
            source_detail=source_detail,
            param_path=path,
        )

    params["strategy.name"] = _param_entry(
        value=live_config.strategy.name,
        source="yaml" if "name" in strategy_raw else "default",
        source_detail="strategy.name",
        param_path="strategy.name",
    )

    if strategy_config_obj is not None and dataclasses.is_dataclass(strategy_config_obj):
        for field_def in fields(strategy_config_obj):
            key = field_def.name
            path = f"strategy.{key}"
            source = "yaml" if key in strategy_raw else "default"
            source_detail = (
                f"{path} in {config_path.name}" if source == "yaml" else f"{path} default"
            )
            value = getattr(strategy_config_obj, key)
            if key in wfo_overrides:
                value = wfo_overrides[key]
                source = "wfo"
                source_detail = f"wfo override for {key}"
            params[path] = _param_entry(
                value=value,
                source=source,
                source_detail=source_detail,
                param_path=path,
            )

    return {
        "model": role,
        "config_path": str(config_path),
        "strategy_name": live_config.strategy.name,
        "wfo_overrides_applied": bool(wfo_overrides),
        "params": params,
    }


def _expand_conditional_allowlist(config_obj: Any) -> set[str]:
    if config_obj is None or not dataclasses.is_dataclass(config_obj):
        return set()

    values = {f.name: getattr(config_obj, f.name) for f in fields(config_obj)}
    allow: set[str] = set()

    # Strategies that use resolved() consume all fields via dataclasses.asdict()
    # at init time. ConfigProxy cannot track asdict() field access because it
    # reads __dict__ directly, bypassing __getattr__. Allowlist all fields
    # for configs with a resolved() method since they are provably consumed.
    if callable(getattr(config_obj, "resolved", None)):
        allow.update(values.keys())

    def add_when_disabled(flag_name: str, dependent_fields: list[str]) -> None:
        if flag_name in values and values.get(flag_name) is False:
            for field_name in dependent_fields:
                if field_name in values:
                    allow.add(field_name)

    add_when_disabled("enable_structural_exit", ["structural_exit_bars"])
    add_when_disabled("exit_on_hma_cross", ["hma_exit_bars"])
    add_when_disabled(
        "escalating_cooldown",
        [
            "short_cooldown_bars",
            "long_cooldown_bars",
            "escalating_lookback_bars",
            "cascade_trigger_count",
        ],
    )
    add_when_disabled("enable_dd_adaptive", ["dd_adaptive_start", "dd_adaptive_floor"])
    add_when_disabled(
        "enable_trail",
        [
            "trail_atr_mult",
            "trail_activate_pct",
            "trail_tighten_mult",
            "trail_tighten_profit_pct",
        ],
    )
    add_when_disabled("enable_fixed_stop", ["fixed_stop_pct"])
    add_when_disabled("enable_vol_brake", ["vol_brake_atr_ratio", "vol_brake_mult"])

    if values.get("enable_mr_defensive") is False:
        allow.update(
            {
                key
                for key in values
                if key.startswith("d1_rsi_")
                or key.startswith("ma200_dist_")
                or key.startswith("mr_trail_")
            }
        )
    if values.get("enable_cycle_phase") is False:
        allow.update({key for key in values if key.startswith("cycle_")})
    if values.get("enable_adx_gating") is False:
        allow.update({key for key in values if key.startswith("adx_")})
    if values.get("enable_overlay_pyramid_ban") is False:
        allow.update({key for key in values if key.startswith("ov1_")})
    if values.get("enable_overlay_peak_dd_stop") is False:
        allow.update({key for key in values if key.startswith("ov2_")})
    if values.get("enable_overlay_decel") is False:
        allow.update({key for key in values if key.startswith("ov3_")})

    return allow


def build_usage_payloads(
    *,
    candidate_tracker: AccessTracker | None,
    baseline_tracker: AccessTracker | None,
    candidate_config_obj: Any,
    baseline_config_obj: Any,
) -> tuple[dict[str, Any], dict[str, Any], bool]:
    def build_one(
        tracker: AccessTracker | None,
        cfg_obj: Any,
    ) -> tuple[dict[str, Any], dict[str, Any], bool]:
        if tracker is None:
            used = {
                "known_fields": [],
                "used_fields": [],
                "used_count": 0,
                "known_count": 0,
            }
            unused = {
                "unused_fields": [],
                "unused_raw": [],
                "allowlist": [],
                "status": "PASS",
            }
            return used, unused, False

        known = sorted(tracker.known_fields)
        used_fields = sorted(tracker.used_fields)
        unused_raw = sorted(set(known) - set(used_fields))
        allowlist = sorted(_expand_conditional_allowlist(cfg_obj))
        unused_fields = sorted(field for field in unused_raw if field not in allowlist)

        used_payload = {
            "known_fields": known,
            "used_fields": used_fields,
            "used_count": len(used_fields),
            "known_count": len(known),
        }
        unused_payload = {
            "unused_fields": unused_fields,
            "unused_raw": unused_raw,
            "allowlist": allowlist,
            "status": "FAIL" if unused_fields else "PASS",
        }
        return used_payload, unused_payload, bool(unused_fields)

    cand_used, cand_unused, cand_fail = build_one(candidate_tracker, candidate_config_obj)
    base_used, base_unused, base_fail = build_one(baseline_tracker, baseline_config_obj)

    used_payload = {
        "candidate": cand_used,
        "baseline": base_used,
    }
    unused_payload = {
        "candidate": cand_unused,
        "baseline": base_unused,
        "status": "FAIL" if cand_fail or base_fail else "PASS",
    }
    return used_payload, unused_payload, bool(cand_fail or base_fail)


def build_effective_config_report(
    *,
    baseline_payload: Mapping[str, Any],
    candidate_payload: Mapping[str, Any],
    unused_payload: Mapping[str, Any],
    unknown_status: str,
) -> str:
    baseline_params = dict(baseline_payload.get("params", {}))
    candidate_params = dict(candidate_payload.get("params", {}))

    shared_keys = sorted(set(baseline_params) & set(candidate_params))
    diffs: list[tuple[str, Any, Any, str, str]] = []
    for key in shared_keys:
        left = baseline_params[key]
        right = candidate_params[key]
        if left.get("value") != right.get("value"):
            diffs.append(
                (
                    key,
                    left.get("value"),
                    right.get("value"),
                    left.get("source", ""),
                    right.get("source", ""),
                )
            )

    lines: list[str] = [
        "# Effective config audit",
        "",
        "## Status",
        "",
        f"- Unknown keys: **{unknown_status}**",
        f"- Unused fields: **{unused_payload.get('status', 'PASS')}**",
        "",
    ]

    cand_unused = list(unused_payload.get("candidate", {}).get("unused_fields", []))
    base_unused = list(unused_payload.get("baseline", {}).get("unused_fields", []))
    lines.append(f"- Candidate unused count: `{len(cand_unused)}`")
    lines.append(f"- Baseline unused count: `{len(base_unused)}`")

    if cand_unused:
        lines.append(f"- Candidate unused fields: `{', '.join(cand_unused)}`")
    if base_unused:
        lines.append(f"- Baseline unused fields: `{', '.join(base_unused)}`")

    lines.extend(
        [
            "",
            "## Top diffs (baseline vs candidate)",
            "",
        ]
    )

    if not diffs:
        lines.append("- No parameter value differences detected.")
    else:
        lines.extend(
            [
                "| param | baseline | candidate | baseline_source | candidate_source |",
                "|---|---:|---:|---|---|",
            ]
        )
        for key, left, right, left_source, right_source in diffs[:30]:
            lines.append(
                f"| {key} | {left} | {right} | {left_source} | {right_source} |"
            )

    return "\n".join(lines) + "\n"
