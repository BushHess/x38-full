# Strategy Naming Convention

**Last updated**: 2026-03-17
**Authority**: This is the single source of truth for all strategy identifiers.

---

## Canonical Strategy IDs

Every strategy has exactly **three** name forms:

| Short ID | Code name | Directory | Description |
|----------|-----------|-----------|-------------|
| **E0** | `vtrend` | `strategies/vtrend/` | Standard ATR(14) trail + EMA cross-down exit. 3 params. Baseline. |
| **E5** | `vtrend_e5` | `strategies/vtrend_e5/` | Robust ATR(20, Q90 cap) trail + EMA cross-down exit. 3 params. |
| **E0_ema21D1** | `vtrend_ema21_d1` | `strategies/vtrend_ema21_d1/` | E0 + D1 EMA(21) regime filter on entry. 4 params. |
| **E5_ema21D1** | `vtrend_e5_ema21_d1` | `strategies/vtrend_e5_ema21_d1/` | E5 + D1 EMA(21) regime filter on entry. 4 params. **PRIMARY**. |

### When to use which form

| Context | Form | Example |
|---------|------|---------|
| Discussion, docs, reports, memory | **Short ID** | E5_ema21D1 |
| File paths, imports, registry keys | **Code name** | `vtrend_e5_ema21_d1` |
| Linking to directory | **Directory** | `strategies/vtrend_e5_ema21_d1/` |
| Python class names | **CamelCase** | `VTrendE5Ema21D1Strategy` |

---

## Two Orthogonal Axes

```
              No D1 regime            D1 EMA(21) regime
            ┌───────────────────┬──────────────────────────────┐
Std ATR(14) │  E0  (vtrend)     │  E0_ema21D1 (vtrend_ema21_d1)      │
            ├───────────────────┼──────────────────────────────┤
Robust ATR  │  E5  (vtrend_e5)  │  E5_ema21D1 (vtrend_e5_ema21_d1)   │
            └───────────────────┴──────────────────────────────┘
```

- **E0 → E5**: only ATR method changes (standard → robust)
- **E0 → E0_ema21D1**: only adds D1 EMA(21) regime filter on entry
- **E0_ema21D1 → E5_ema21D1**: only ATR method changes
- **E5 → E5_ema21D1**: only adds D1 EMA(21) regime filter on entry

---

## External Algorithm IDs (X37 Arena)

Algorithms discovered outside the VTREND family, evaluated via the X37 arena.

| Short ID | Algorithm | Source | Directory | Verdict | Notes |
|----------|-----------|--------|-----------|---------|-------|
| **x37v4** | macroHystB | `research/x37/resource/gen1/v4_macroHystB/` | `research/x37/branches/a_v4_vs_e5_fair_comparison/` | **V4_COMPETITIVE** | 3-feature hysteresis (d1_ret_60 + h4_trendq_84 + h4_buyimb_12). ~10 params. NOT a VTREND variant. |

---

## Research-Origin Aliases (X0 series)

These strategy directories were created during X-series research.
They are **duplicates** of canonical strategies and exist only for research provenance.

| Research ID | Directory | Canonical equivalent | Relationship |
|-------------|-----------|---------------------|--------------|
| **X0** | `strategies/vtrend_x0/` | **E0_ema21D1** (`vtrend_ema21_d1`) | **IDENTICAL** — same algorithm, same defaults. Only class names and signal reason strings differ. |
| **X0_E5exit** | `strategies/vtrend_x0_e5exit/` | **E5_ema21D1** (`vtrend_e5_ema21_d1`) | **NEAR-IDENTICAL** — same core algorithm. E5_ema21D1 additionally has optional regime monitor (disabled by default). When `enable_regime_monitor=False`, functionally equivalent. |
| **X0-Volsize** | `strategies/vtrend_x0_volsize/` | — | Research variant (vol-targeted sizing). No canonical equivalent. |

### Why duplicates exist

The X-series research (`research/x0/` through `research/x33/`) used `vtrend_x0` as its
baseline anchor before the naming convention was established. The canonical strategies
(`vtrend_ema21_d1`, `vtrend_e5_ema21_d1`) were created independently with clean naming.

**Rule**: Always use the canonical name. Use X0/X0_E5exit only when referencing
the original research context (e.g., "X0 was the baseline in X-series studies").

---

## Research Directory Naming Variants

Historical research directories used alternative naming for the D1 EMA(21) concept:

| Directory pattern | Canonical equivalent | Context |
|-------------------|---------------------|---------|
| `eval_e5_ema1d21/` | E5_ema21D1 | Research eval directories |
| `prod_readiness_e5_ema1d21/` | E5_ema21D1 | Production readiness research |
| `full_eval_e5_ema21d1/` | E5_ema21D1 | Validation results |
| `full_eval_x0_ema21d1/` | E0_ema21D1 | Validation results (uses X0 alias) |
| `E5_PLUS_EMA1D21_*` | E5_ema21D1 | Parity report filenames |

These directory names are **not renamed** (would break references) but are all
equivalent to the canonical forms listed above.

---

## Deprecated Names — DO NOT USE

| Old / ambiguous name | Correct canonical name |
|---------------------|----------------------|
| "E5+EMA1D21", "E5+EMA21D1", "E5D1" | **E5_ema21D1** |
| "E0+EMA1D21", "E0+EMA21D1", "E0D1" | **E0_ema21D1** |
| "X0" (when meaning E0_ema21D1) | **E0_ema21D1** |
| "X0_E5exit" (when meaning E5_ema21D1) | **E5_ema21D1** |
| "VTREND E5 + EMA(21d)" | **E5_ema21D1** |
| "E0_plus", "E0_plus_EMA1D21" | **E0_ema21D1** |
| "E5_plus", "E5_plus_EMA1D21" | **E5_ema21D1** |
| "VTREND baseline" (ambiguous) | **E0** (be specific) |
| "ema1d21" (directory variant) | **ema21_d1** (code name) or **ema21D1** (short ID) |

---

## Quick Lookup

Need to find a strategy? Use this table:

| You see... | It means... | Canonical short ID |
|------------|------------|-------------------|
| `vtrend` | E0 baseline | **E0** |
| `vtrend_e5` | Robust ATR variant | **E5** |
| `vtrend_ema21_d1` | E0 + D1 regime | **E0_ema21D1** |
| `vtrend_e5_ema21_d1` | E5 + D1 regime (PRIMARY) | **E5_ema21D1** |
| `vtrend_x0` | Research duplicate of E0_ema21D1 | **E0_ema21D1** |
| `vtrend_x0_e5exit` | Research near-duplicate of E5_ema21D1 | **E5_ema21D1** |
| `eval_e5_ema1d21` | Research directory for E5_ema21D1 | **E5_ema21D1** |
| `full_eval_x0_ema21d1` | Validation results for E0_ema21D1 | **E0_ema21D1** |
