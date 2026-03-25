# Spec: Effective Config with Units & Provenance

**Status:** Draft — for Codex implementation
**Scope:** Structured JSON output of every effective parameter, its unit, value, and provenance.

---

## 1. Unit Taxonomy

Every numeric parameter carries a `unit` tag from this closed set:

| unit tag | Meaning | JSON value type | Example params |
|----------|---------|-----------------|----------------|
| `ratio` | Dimensionless fraction in [0, 1] (or occasionally >1 for multipliers) | `number` | `max_total_exposure` (1.0), `trail_activate_pct` (0.05), `emergency_dd_pct` (0.28), `compression_ratio` (0.75) |
| `multiplier` | Dimensionless scaling factor, no fixed range | `number` | `trail_atr_mult` (3.5), `entry_aggression` (0.85), `caution_mult` (0.50), `compression_boost` (1.0) |
| `bps` | Basis points (1 bps = 0.01%) | `number` | `spread_bps` (5.0), `slippage_bps` (3.0) |
| `pct` | Percent expressed as a decimal fraction, e.g. 0.10 means 0.10% | `number` | `taker_fee_pct` (0.10) |
| `bars` | Discrete bar count at the param's native timeframe | `integer` | `entry_cooldown_bars` (3), `cooldown_after_emergency_dd_bars` (12), `atr_fast_period` (14) |
| `days` | Calendar days | `integer` | `warmup_days` (365) |
| `usd` | US Dollar amount | `number` | `initial_cash` (10000.0), `min_notional_usdt` (10.0) |
| `level` | Indicator level on a fixed scale (e.g. RSI 0–100, ADX 0–100) | `number` | `rsi_overbought` (75.0), `rsi_oversold` (30.0), `adx_min_trend` (20.0) |
| `count` | Integer count (not bars, not days) | `integer` | `max_daily_orders` (5), `cascade_trigger_count` (2) |
| `annual_vol` | Annualized volatility (dimensionless but annual convention) | `number` | `target_vol_annual` (0.85) |
| `enum` | String chosen from a closed set | `string` | `warmup_mode` ("no_trade"), `rsi_method` ("ewm_span"), `scenario_eval` ("base") |
| `flag` | Boolean on/off | `boolean` | `enable_trail` (true), `enable_fixed_stop` (true) |
| `symbol` | Ticker / instrument identifier | `string` | `symbol` ("BTCUSDT") |
| `timeframe` | Candle interval string | `string` | `timeframe_h4` ("4h"), `timeframe_d1` ("1d") |

### 1.1 Disambiguating `ratio` vs `pct` vs `bps`

This repo uses **three different scales** for "percentage-like" values:

| Scale | Convention in this repo | Example |
|-------|-------------------------|---------|
| **ratio** | 0.28 means 28% | `emergency_dd_pct` = 0.28, `trail_activate_pct` = 0.05 |
| **pct** | 0.10 means 0.10% (i.e. the number IS the percent) | `taker_fee_pct` = 0.10 |
| **bps** | 5.0 means 5 basis points = 0.05% | `spread_bps` = 5.0 |

> **Note:** Several params with `_pct` suffix (e.g. `emergency_dd_pct`, `trail_activate_pct`, `fixed_stop_pct`) actually store **ratios** (0.28 = 28%). The `_pct` suffix is a legacy naming convention in the codebase. The `unit` tag in the JSON must reflect the *actual representation* (`ratio`), not the suffix.

### 1.2 Timeframe Annotation for `bars`

All `bars`-unit params must include a `timeframe` sub-field:

```json
{
  "name": "entry_cooldown_bars",
  "value": 3,
  "unit": "bars",
  "timeframe": "4h",
  "source": "default"
}
```

Timeframe is determined by the parameter's usage context:
- Most params: `"4h"` (H4 bars)
- `d1_regime_confirm_bars`, `d1_regime_off_bars`, `cycle_hysteresis_bars`: `"1d"` (D1 bars)

---

## 2. Provenance Rules

### 2.1 Precedence Order (lowest → highest)

```
default < yaml < cli < wfo < derived
```

| Source | `source` value | `source_detail` contents |
|--------|---------------|--------------------------|
| Dataclass field default | `"default"` | `"V8ApexConfig.field_name"` or equivalent config class |
| YAML config file | `"yaml"` | Relative path, e.g. `"configs/baseline_legacy.live.yaml"` |
| CLI argument | `"cli"` | `"--trail-atr-mult 4.0"` (the literal CLI flag + value) |
| WFO grid search | `"wfo"` | `"candidate=apex_wide_trail grid_point=7"` |
| Derived at runtime | `"derived"` | Formula or description, e.g. `"per_side_bps = spread_bps/2 + slippage_bps + taker_fee_pct*100"` |

### 2.2 Override Semantics

- Each level **completely replaces** the previous value (no merging within a single param).
- A `wfo` override replaces a `cli` value which replaces a `yaml` value which replaces a `default`.
- The effective config records **only the winning source** — not a stack of all sources.

### 2.3 Derived Parameters

Some parameters are computed from others at runtime. These must have `source: "derived"` and the `source_detail` must record the formula:

| Derived param | Formula | Inputs |
|---------------|---------|--------|
| `per_side_bps` | `spread_bps / 2 + slippage_bps + taker_fee_pct * 100` | CostConfig fields |
| `round_trip_bps` | `per_side_bps * 2` | per_side_bps |
| `round_trip_pct` | `round_trip_bps / 100` | round_trip_bps |

---

## 3. Unknown Key Policy

**Recommendation: Fail fast.**

### 3.1 Current Behavior (already implemented)

The config loader (`config.py:_unknown_yaml_keys`) already **rejects** unknown keys at load time with a `ValueError`. This applies to:
- Unknown top-level keys (not in `{engine, strategy, risk}`)
- Unknown `engine.*` keys (not in `EngineConfig` fields)
- Unknown `risk.*` keys (not in `RiskConfig` fields)
- Unknown `strategy.*` keys (not in the active strategy's config class fields)

### 3.2 Spec Requirements

| Rule | Action |
|------|--------|
| Unknown key in YAML | **Raise `ValueError`** at load time — no silent drop |
| Unknown key in CLI | **Raise `argparse` error** — standard behavior |
| Unknown key in WFO candidate `params` | **Raise `ValueError`** during candidate validation |
| Unknown key in WFO candidate `param_ranges` | **Raise `ValueError`** during candidate validation |
| Typo-distance suggestion | Optional: if Levenshtein distance ≤ 2 from a known field, include `"did you mean '{suggestion}'?"` in the error message |

### 3.3 Rationale

- **Reproducibility:** A silently-dropped param means the run doesn't match the researcher's intent. This is catastrophic for research credibility.
- **Debugging:** Fail-fast surfaces config errors immediately rather than hiding them in unexpected backtest results.

---

## 4. Unused Param Policy

### 4.1 Definition of "Used"

A parameter is **used** if the strategy's `__init__`, `on_bar`, `on_fill`, or any method called during `engine.run()` reads `self.cfg.<param_name>` at least once during the backtest.

### 4.2 Detection Method

Instrument config access via a `__getattr__` wrapper or post-run audit:

```python
@dataclass
class TrackedConfig:
    _delegate: V8ApexConfig
    _accessed: set[str] = field(default_factory=set)

    def __getattr__(self, name: str) -> Any:
        self._accessed.add(name)
        return getattr(self._delegate, name)

    def unused_params(self) -> set[str]:
        all_fields = {f.name for f in dataclasses.fields(self._delegate)}
        return all_fields - self._accessed
```

### 4.3 Reporting

After each backtest, emit an `unused_params` list in the effective config JSON:

```json
{
  "unused_params": ["enable_structural_exit", "exit_on_hma_cross"],
  "unused_policy": "warn"
}
```

### 4.4 Allowlist (suppress warnings)

These params are legitimately unused in certain configurations:

| Category | Params | Reason |
|----------|--------|--------|
| Feature flags (off) | `enable_structural_exit`, `exit_on_hma_cross`, `enable_dd_adaptive`, `enable_mr_defensive`, `enable_cycle_phase`, `enable_adx_gating` | Guarded sub-params are unused when flag is `false` |
| Overlay flags (off) | `enable_overlay_pyramid_ban`, `enable_overlay_peak_dd_stop`, `enable_overlay_decel` | Same pattern |
| Escalating cooldown (off) | `escalating_cooldown`, `short_cooldown_bars`, `long_cooldown_bars`, `escalating_lookback_bars`, `cascade_trigger_count` | Used only when `escalating_cooldown=true` |
| Debug / logging | (none currently) | Reserve for future use |

**Rule:** If a feature flag is `false`, all params guarded by that flag are exempt from "unused" warnings. Implementation: build a `flag → guarded_params` map and suppress accordingly.

---

## 5. JSON Compliance

### 5.1 Forbidden Values

| Value | JSON legality | Policy |
|-------|---------------|--------|
| `NaN` | **Illegal** in JSON | Use `null` + `"missing_reason": "<reason>"` |
| `Infinity` / `-Infinity` | **Illegal** in JSON | Use `null` + `"missing_reason": "<reason>"` |
| Python `None` | Maps to JSON `null` | Allowed for optional fields |

### 5.2 Missing Reason Codes

When a numeric field is `null`, include a `missing_reason`:

| Code | Meaning |
|------|---------|
| `"zero_denominator"` | Division by zero (e.g. Sharpe with zero volatility) |
| `"insufficient_data"` | Not enough data points to compute |
| `"not_applicable"` | Metric doesn't apply to this config (e.g. Sortino when no negative returns) |
| `"overflow"` | Computation overflowed (e.g. CAGR with extreme returns) |
| `"capped_at_maximum"` | Value was infinite but capped (e.g. profit_factor "inf" → 3.0 in objective) |

### 5.3 Existing Codebase Patterns to Normalize

| Current behavior | Location | Required change |
|-----------------|----------|-----------------|
| `profit_factor` serialized as string `"inf"` | `metrics.py` line 139 | Emit `null` + `"missing_reason": "zero_denominator"` OR the capped value (3.0) with `"capped": true` |
| `sharpe` = `None` when sigma < 1e-12 | `metrics.py` line 180-181 | Already `null` — add `"missing_reason": "zero_denominator"` |
| `sortino` = `None` when down_sigma < 1e-12 | `metrics.py` line 187-188 | Already `null` — add `"missing_reason": "zero_denominator"` |
| `calmar` = `None` when max_dd < 1e-6 | `metrics.py` line 79 | Already `null` — add `"missing_reason": "zero_denominator"` |

---

## 6. Effective Config JSON Schema

### 6.1 Top-Level Structure

```json
{
  "schema_version": "1.0",
  "effective_config": {
    "engine": [ ...param entries... ],
    "risk": [ ...param entries... ],
    "strategy": [ ...param entries... ],
    "cost": [ ...param entries... ]
  },
  "unused_params": ["param_a", "param_b"],
  "unused_policy": "warn",
  "metadata": {
    "strategy_name": "v8_apex",
    "config_class": "V8ApexConfig",
    "timestamp_utc": "2026-02-24T12:00:00Z",
    "git_sha": "abc1234"
  }
}
```

### 6.2 Single Parameter Entry

```json
{
  "name": "trail_atr_mult",
  "value": 3.5,
  "unit": "multiplier",
  "source": "yaml",
  "source_detail": "configs/baseline_legacy.live.yaml"
}
```

For `bars`-unit params, add `timeframe`:

```json
{
  "name": "entry_cooldown_bars",
  "value": 3,
  "unit": "bars",
  "timeframe": "4h",
  "source": "default",
  "source_detail": "V8ApexConfig.entry_cooldown_bars"
}
```

For `enum` params, add `allowed_values`:

```json
{
  "name": "rsi_method",
  "value": "ewm_span",
  "unit": "enum",
  "allowed_values": ["ewm_span", "wilder"],
  "source": "yaml",
  "source_detail": "configs/baseline_legacy.live.yaml"
}
```

### 6.3 Unit Assignment Table (Canonical)

This table is the **single source of truth** for assigning units to every parameter. Implementation must use this mapping.

#### Engine Params

| Param | Unit |
|-------|------|
| `symbol` | symbol |
| `timeframe_h4` | timeframe |
| `timeframe_d1` | timeframe |
| `warmup_days` | days |
| `warmup_mode` | enum |
| `scenario_eval` | enum |
| `initial_cash` | usd |

#### Risk Params

| Param | Unit |
|-------|------|
| `max_total_exposure` | ratio |
| `min_notional_usdt` | usd |
| `kill_switch_dd_total` | ratio |
| `max_daily_orders` | count |

#### Cost Params (derived from scenario)

| Param | Unit |
|-------|------|
| `spread_bps` | bps |
| `slippage_bps` | bps |
| `taker_fee_pct` | pct |
| `per_side_bps` | bps |
| `round_trip_bps` | bps |
| `round_trip_pct` | pct |

#### V8 Apex Strategy Params

| Param | Unit | Timeframe (if bars) |
|-------|------|---------------------|
| `atr_fast_period` | bars | 4h |
| `atr_slow_period` | bars | 4h |
| `trail_atr_mult` | multiplier | — |
| `trail_activate_pct` | ratio | — |
| `trail_tighten_mult` | multiplier | — |
| `trail_tighten_profit_pct` | ratio | — |
| `vol_brake_atr_ratio` | ratio | — |
| `vol_brake_mult` | multiplier | — |
| `compression_ratio` | ratio | — |
| `compression_boost` | multiplier | — |
| `fixed_stop_pct` | ratio | — |
| `emergency_dd_pct` | ratio | — |
| `cooldown_after_emergency_dd_bars` | bars | 4h |
| `max_total_exposure` | ratio | — |
| `target_vol_annual` | annual_vol | — |
| `max_add_per_bar` | ratio | — |
| `entry_aggression` | multiplier | — |
| `caution_mult` | multiplier | — |
| `min_target_to_add` | ratio | — |
| `d1_ema_fast` | bars | 1d |
| `d1_ema_slow` | bars | 1d |
| `d1_regime_confirm_bars` | bars | 1d |
| `d1_regime_off_bars` | bars | 1d |
| `regime_exit_immediate` | flag | — |
| `rsi_period` | bars | 4h |
| `rsi_overbought` | level | — |
| `rsi_oversold` | level | — |
| `rsi_method` | enum | — |
| `vdr_fast_period` | bars | 4h |
| `vdr_slow_period` | bars | 4h |
| `vdo_entry_threshold` | ratio | — |
| `vdo_scale` | ratio | — |
| `hma_period` | bars | 4h |
| `roc_period` | bars | 4h |
| `accel_smooth_period` | bars | 4h |
| `entry_cooldown_bars` | bars | 4h |
| `exit_cooldown_bars` | bars | 4h |
| `structural_exit_bars` | bars | 4h |
| `hma_exit_bars` | bars | 4h |
| `enable_trail` | flag | — |
| `enable_fixed_stop` | flag | — |
| `enable_vol_brake` | flag | — |
| `enable_structural_exit` | flag | — |
| `exit_on_hma_cross` | flag | — |
| `escalating_cooldown` | flag | — |
| `short_cooldown_bars` | bars | 4h |
| `long_cooldown_bars` | bars | 4h |
| `escalating_lookback_bars` | bars | 4h |
| `cascade_trigger_count` | count | — |
| `enable_dd_adaptive` | flag | — |
| `dd_adaptive_start` | ratio | — |
| `dd_adaptive_floor` | ratio | — |

---

## 7. Implementation Checklist

- [ ] Create `unit_registry.py` mapping every param name → `(unit, timeframe|None)`
- [ ] Create `provenance_tracker.py` that records source at each override step
- [ ] Wrap config loading pipeline: `default` → mark source → `yaml` → mark source → `cli` → mark source → `wfo` → mark source
- [ ] Add `TrackedConfig` wrapper for unused-param detection (§4.2)
- [ ] Add `flag_guard_map` for unused-param allowlist (§4.4)
- [ ] Sanitize JSON output: replace `NaN`/`Inf` with `null` + `missing_reason` (§5)
- [ ] Emit `effective_config.json` alongside existing `summary.json` after each backtest
- [ ] Add unit test: round-trip `effective_config.json` through `json.loads` without error
- [ ] Add unit test: every param in effective config has a known `unit` tag
- [ ] Add unit test: `sum(source == "derived")` matches expected derived param count
