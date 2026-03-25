# Ambiguity patch set (delta from prior spec pack)

## P-01 — Canonical identity
Replace all mixed spellings with:
- canonical strategy name = **VP1** (VTREND-P1); legacy ID = `Phase1ParentCore_ATRstandard_REVon_D1ON`
- historical alias = `Phase1ParentCore_ATRstandard_REVon_D1on` (logs only)

## P-02 — Promote inherited core mechanics to explicit VP1 rules
Where the prior pack said a rule was “inferred from Baseline lineage”, rewrite it as a direct VP1 rule:
- `fast_period = 35`
- `ATR period = 20`
- `ATR smoothing = Wilder`
- `VDO EMA periods = 12 / 28`
- `warmup_days = 365`
- `D1 is entry-only`
- `VDO is entry-only`
- `trailing stop before trend reversal`

## P-03 — Lock VDO missing-data semantics
Add exact wording:
- per-bar auto path is canonical
- if primary path unavailable and fallback denominator invalid (`high <= low`), current `vdr = NaN`
- `EMA_nan_carry` means current VDO remains equal to prior EMA spread if already seeded; otherwise it remains NaN

## P-04 — Separate strategy logic from benchmark-wrapper logic
Rewrite terminal handling as:
- intrinsic strategy: no EOF exit
- benchmark wrapper: optional synthetic `window_flatten` sell at finite window end open

## P-05 — Separate strategy from benchmark cost model
Rewrite cost section as:
- VP1 logic itself is cost-agnostic
- canonical benchmark reproduction uses flat 50 bps round-trip = 25 bps per side, charged at BUY/SELL events under next-open event accounting

## P-06 — Demote non-auditable tests
Delete as hard acceptance gates:
- full-history first legal trade timestamp
- full-history first three entries/exits
unless those values are packaged as preserved artifacts

Replace with artifact-backed gates:
- Tier-2 trade count
- first three Tier-2 entry fill timestamps
- first three Tier-2 exit fill timestamps
- first Tier-2 trade decision/fill/exit cycle
- spec hash / manifest hash match

## P-07 — Demote the mixed reference trace
Keep the old trace as informative only.
Promote the real Tier-2 trade-log cycle to the canonical frozen verification trace.
Indicator-number checking remains local recomputation, not frozen artifact truth.

## P-08 — Re-label forced resolutions
Any rule not directly specified by artifact but chosen to make rebuild deterministic must be labeled:
- `FORCED-RESOLUTION`
This applies to:
- duplicate timestamp handling
- structural gap handling
- negative/zero price hard fail
- absent full taker column -> fallback-only globally
- missing prevday D1 row -> regime = False
