# Findings Under Review — Feature Engine Design

**Topic ID**: X38-T-06
**Opened**: 2026-03-22 (activated from PLANNED)
**Author**: claude_code (architect)

1 finding về feature engine design.

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

## Cross-topic tensions

| Topic | Finding | Tension | Resolution path |
|-------|---------|---------|-----------------|
| 017 | ESP-01, ESP-02 | Phenotype descriptor taxonomy (017) overlaps feature family taxonomy (006). Both define how to categorize/tag strategies and features. | 006 owns feature-level taxonomy; 017 owns strategy-level descriptors. Must not conflict. |

## Bảng tổng hợp

| Issue ID | Finding | Phân loại | Status |
|----------|---------|-----------|--------|
| X38-D-08 | Feature engine — registry pattern | Thiếu sót | Open |
