# Findings Under Review — Feature Engine Design

**Topic ID**: X38-T-06
**Opened**: 2026-03-22 (activated from PLANNED)
**Author**: claude_code (architect)

2 findings về feature engine design.
F-38 added 2026-03-31 (gap audit).

---

## F-08: Feature engine — registry pattern

- **issue_id**: X38-D-08
- **classification**: Thiếu sót
- **opened_at**: 2026-03-18
- **opened_in_round**: 0
- **current_status**: Open

**Nội dung**:

Feature engine dùng registry pattern với @decorator:

```python
@feature("feature_name", family="family_name", timeframe="D1",
         lookbacks=[lookback_a, lookback_b, ...], tails=["high"])
def compute_feature(close: Series, lookback: int) -> Series:
    # feature-specific computation
    ...
```

Thêm feature mới = thêm 1 function với @decorator. Pipeline tự enumerate
tất cả registered features × lookbacks × threshold modes × quantile grid.

Feature families (1 file = 1 family):
- `families/trend.py` — directional persistence, trend quality, ...
- `families/volatility.py` — volatility level, clustering, compression, ...
- `families/location.py` — range position, drawdown, distance to extremes, ...
- `families/flow.py` — participation, order flow proxies, ...
- `families/structure.py` — candle structure summaries, ...
- `families/cross_tf.py` — D1→H4 aligned transports

Threshold calibration modes (4):
- fixed_zero: long if feature > 0
- expanding_quantile: quantile trên toàn bộ history tới thời điểm
- rolling_quantile: quantile trên trailing N days
- static_calendar_year: quantile trên prior-year, constant within year

Scanner enumerate: feature × lookback × tail × mode × quantile → có thể 50K+ configs.
Serialization: stage1_registry.parquet (typed, compact cho 50K+ rows).

**Evidence**:
- research/x37/resource/gen1/v5_sfq70/ [extra-archive]: 261 features, 8 role categories, scan manifest.
- research/x37/resource/gen1/v6_ret168/ [extra-archive]: 2,219 configs, threshold modes (fixed zero, expanding, calibration).
- research/x37/docs/gen1/RESEARCH_PROMPT_V6/CONTAMINATION_LOG_V2.md [extra-archive]: feature inventories từ 6 rounds — total ~100+ unique features.
- research/x37/docs/gen1/RESEARCH_PROMPT_V6/RESEARCH_PROMPT_V6.md §Stage 1 [extra-archive]: "Export the full machine-readable Stage 1 registry."

**Câu hỏi mở**:
- Decorator pattern vs config-driven (YAML/JSON define features)?
  Decorator: code-first, type-safe, IDE-friendly.
  Config: data-first, non-programmer can extend, separation of concerns.
- 1 file = 1 family vs 1 file = 1 feature? Family grouping gọn hơn nhưng files
  lớn hơn.
- 4 threshold modes đủ? V5 dùng static calendar-year; V6 dùng fixed zero.
  Có mode nào khác cần?
- Cross-timeframe: alignment ở engine level (data loader merge D1→H4) hay
  feature level (mỗi cross-TF feature tự merge)?
- Exhaustive scan (enumerate tất cả) vs intelligent pruning (skip highly
  correlated combos)?

---

## F-38: Feature family ontology — definition and extension mechanism

- **issue_id**: X38-D-38
- **classification**: Thiếu sót
- **opened_at**: 2026-03-31
- **opened_in_round**: 0 (gap audit)
- **current_status**: Open

**Chẩn đoán**:

F-08 lists 6 feature families (trend, volatility, location, flow, structure,
cross_tf) nhưng không define:

1. **Thế nào là "family"?** — taxonomy criteria. Hai features thuộc cùng family
   khi nào? Chia theo mechanism (momentum vs mean-reversion), data source
   (price vs volume), timeframe, hay computation type?

2. **Ai define family mới?** — Extension mechanism. Khi human researcher propose
   feature mới không fit existing 6 families (e.g., on-chain metrics nếu mở rộng
   sang crypto), protocol nào để thêm family?

3. **Family ↔ Convergence**: Topic 013 (convergence analysis) dùng "family-level
   convergence" (V4→V8 "hội tụ ở cấp family: D1 slow signals"). Nhưng nếu family
   definition không formal, convergence measurement bị ambiguous — hai agents có
   thể classify cùng feature vào families khác nhau.

4. **Family ↔ ESP cell-axis**: Topic 017 ESP-01 proposes `mechanism_family` as
   cell axis cho cell-elite archive. Cell axis cần categorical values — nhưng
   F-08 families ≠ mechanism families (e.g., "trend" family includes both
   momentum AND trend-following, which are different mechanisms).

**Câu hỏi cần debate**:

| Position | Mô tả | Tradeoff |
|----------|--------|----------|
| A: Fixed taxonomy (6 families) | Freeze current 6 families. No extension mechanism. New features must fit existing families | Simple, deterministic. But constrains search space for non-OHLCV assets |
| B: Extensible taxonomy with governance | 6 families as v1 default. Extension via protocol-level proposal (pre-Stage 1, human-approved, provenance-tracked) | Flexible, but extension = protocol change → new campaign (per D-16) |
| C: Flat registry, no families | Features individually tagged with descriptors (per ESP-01). "Family" is a derived grouping, not a structural category | Maximum flexibility, but no grouping for convergence analysis |

**Evidence**:
- F-08: 6 families listed without formal definition criteria
- Topic 013 CA-01: "family-level convergence" — requires formal family definition
- Topic 017 ESP-01: `mechanism_family` as cell axis — requires categorical values
- CONVERGENCE_STATUS_V3.md [extra-archive]: "hội tụ ở cấp family (D1 slow)" — but
  "D1 slow" is not one of F-08's families, it's an ad hoc grouping
- F-36 (Topic 003): multi-asset pipeline → different assets may need different
  family taxonomies

---

## Cross-topic tensions

| Topic | Finding | Tension | Resolution path |
|-------|---------|---------|-----------------|
| 017 | ESP-01, ESP-02 | Phenotype descriptor taxonomy (017) overlaps feature family taxonomy (006). Both define how to categorize/tag strategies and features. | 006 owns feature-level taxonomy; 017 owns strategy-level descriptors. Must not conflict. |
| 018 | SSE-D-03 | `generation_mode` feeds registry acceptance — registry must accept auto-generated features from `grammar_depth1_seed`. Routed from Topic 018 (CLOSED 2026-03-27). Routing confirmed. | 006 owns registry acceptance rules; 018 provides generation mode contract (confirmed). |
| 019 | DFL-08 (Stage 4) | Feature candidate graduation path feeds discovery loop features into F-08 registry with `source: discovery_loop` + provenance chain. Registry must accept this new source type alongside grammar-generated features. | 006 owns registry schema; 019 defines discovery-to-registry interface (DFL-08). |

## Bảng tổng hợp

| Issue ID | Finding | Phân loại | Status |
|----------|---------|-----------|--------|
| X38-D-08 | Feature engine — registry pattern | Thiếu sót | Open |
| X38-D-38 | Feature family ontology — definition and extension | Thiếu sót | Open |
| X38-SSE-D-03 | Registry acceptance for auto-generated features (từ Topic 018) | Thiếu sót | Open |

---

## Issue routed from Topic 018 — Search-Space Expansion (2026-03-27)

Architecture-level decision from Topic 018 (**CLOSED** 2026-03-27 —
standard 2-agent debate completed, 10 Converged + 1 Judgment call). This issue
represents a confirmed implementation obligation.
Source: `debate/018-search-space-expansion/final-resolution.md` (authoritative).

---

## SSE-D-03: Registry acceptance for auto-generated features

- **issue_id**: X38-SSE-D-03
- **classification**: Thiếu sót
- **opened_at**: 2026-03-27
- **opened_in_round**: 0 (routed from Topic 018, SSE-D-03)
- **current_status**: Open

**Nội dung**:

Topic 018 decided (confirmed 2026-03-27): `generation_mode` is a mandatory field in the
breadth-activation contract (SSE-D-04 field 2). Feature engine registry must accept
auto-generated features from `grammar_depth1_seed` generation mode.

Topic 006 owns:
1. Registry acceptance criteria for auto-generated features
2. Whether decorator pattern or config-driven approach handles generation mode metadata
3. How generated features integrate with family organization (e.g., separate `families/generated.py` or inline)

**Evidence**:
- `debate/018-search-space-expansion/final-resolution.md:350` [within-x38]: SSE-D-03 routing confirmed.
- `debate/018-search-space-expansion/final-resolution.md:42-49` [within-x38]: Cross-topic impact table.
