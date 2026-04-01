# Findings Under Review — Data Integrity & Session Immutability

**Topic ID**: X38-T-09
**Opened**: 2026-03-22
**Split from**: Topic 000 (X38-T-00)
**Author**: claude_code (architect)

2 findings về data integrity (đầu vào) và session immutability (đầu ra).

---

## F-10: Data management — data-pipeline output + SHA-256 checksum

- **issue_id**: X38-D-10
- **classification**: Judgment call
- **opened_at**: 2026-03-18
- **opened_in_round**: 0
- **current_status**: Open

**Nội dung**:

Data đọc từ **data-pipeline output** tại
`/var/www/trading-bots/data-pipeline/output/` (parquet format).
Mỗi campaign.json ghi SHA-256 của data files nó dùng.

### Research data scope

Tất cả 5 loại data trong data-pipeline output nằm trong **scope nghiên cứu**.
Chỉ sau khi nghiên cứu xác định giá trị từng loại mới quyết định dùng/loại.
Nguyên tắc: không loại trước khi điều tra — tránh bỏ sót giá trị tiềm ẩn.

**Loại duy nhất bị loại**: `bars_multi_4h.parquet` — multi-asset H4. X20 đã
chứng minh altcoins dilute BTC alpha (best portfolio Sh 0.259 << BTC-only 0.735).

```
/var/www/trading-bots/data-pipeline/output/
│
├── spot_klines/BTCUSDT/              # OHLCV + taker volume
│   ├── 4h.parquet    18,750 rows     ← primary research timeframe
│   ├── 1d.parquet     3,128 rows     ← regime filter timeframe
│   ├── 1h.parquet    74,941 rows
│   └── 15m.parquet  299,710 rows
│   Columns (11): open_time, close_time, open, high, low, close,
│                 volume, quote_volume, num_trades,
│                 taker_buy_base_vol, taker_buy_quote_vol
│
├── futures_metrics/BTCUSDT/          # OI, positioning, leverage
│   ├── 4h.parquet    12,101 rows
│   ├── 1d.parquet     2,018 rows
│   ├── 1h.parquet    48,387 rows
│   ├── 15m.parquet  193,490 rows
│   └── 5m.parquet   580,256 rows
│   Columns (8): open_time, close_time, open_interest,
│                open_interest_value, toptrader_ls_ratio_accounts,
│                toptrader_ls_ratio_positions, ls_ratio_accounts,
│                taker_ls_vol_ratio
│
├── futures_fundingRate/              # Funding rate (~8h interval)
│   └── BTCUSDT.parquet  7,091 rows
│   Columns (3): timestamp, funding_rate, funding_interval_hours
│
├── futures_premiumIndexKlines/BTCUSDT/  # Spot-futures premium
│   ├── 4h.parquet    13,560 rows
│   ├── 1d.parquet     2,260 rows
│   ├── 1h.parquet    54,239 rows
│   └── 15m.parquet  216,952 rows
│   Columns (7): open_time, close_time, premium_open, premium_high,
│                premium_low, premium_close, num_trades
│
└── aggtrades_bulk/BTCUSDT/           # Tick-level trades
    └── BTCUSDT-aggTrades-YYYY-MM-DD.parquet  (~3,100 daily files)
    Size: ~80GB total
```

### Giá trị nghiên cứu tiềm năng (cần điều tra, chưa kết luận)

| Data type | Giả thuyết nghiên cứu | Liên hệ hiện tại |
|-----------|----------------------|-------------------|
| spot_klines | **Đang dùng** — OHLCV + taker vol là nền tảng E5-ema21D1 | 5/11 fields đã dùng, 4 chưa khai thác (DFL-06) |
| futures_metrics | OI + LS ratios → regime detection, positioning fragility | Chưa điều tra |
| funding_rate | Leverage sentiment → crowded trade reversal signal | Chưa điều tra |
| premium_index | Contango/backwardation → basis signal, market stress | Chưa điều tra |
| aggtrades | Tick-level microstructure → order flow, liquidity depth | Chưa điều tra, size lớn (~80GB) |

Quyết định dùng/loại thuộc về kết quả nghiên cứu, không phải thiết kế trước.
Topic 019 DFL-15 (data acquisition scope) quản lý quyết định này.

### Lý do dùng data-pipeline output thay vì copies

- Data-pipeline là single source of truth, đã có `_catalog.json` + QA.
- Tránh duplicate data mỗi campaign.
- SHA-256 checksum trong campaign.json đảm bảo reproducibility:
  nếu file thay đổi, checksum mismatch → campaign từ chối chạy.

### campaign.json schema

Campaign khai báo tất cả data files nó dùng. Danh sách files có thể thay đổi
theo kết quả nghiên cứu — campaign nào dùng data type nào do protocol quyết định.

```json
{
    "data_root": "/var/www/trading-bots/data-pipeline/output",
    "data_files": {
        "spot_klines_h4":     "spot_klines/BTCUSDT/4h.parquet",
        "spot_klines_d1":     "spot_klines/BTCUSDT/1d.parquet",
        "futures_metrics_h4": "futures_metrics/BTCUSDT/4h.parquet",
        "futures_metrics_d1": "futures_metrics/BTCUSDT/1d.parquet",
        "funding_rate":       "futures_fundingRate/BTCUSDT.parquet",
        "premium_h4":         "futures_premiumIndexKlines/BTCUSDT/4h.parquet",
        "premium_d1":         "futures_premiumIndexKlines/BTCUSDT/1d.parquet"
    },
    "data_sha256": {
        "spot_klines_h4":     "abc123...",
        "spot_klines_d1":     "def456...",
        "futures_metrics_h4": "789abc...",
        "futures_metrics_d1": "012def...",
        "funding_rate":       "345ghi...",
        "premium_h4":         "678jkl...",
        "premium_d1":         "901mno..."
    },
    "data_start": "2017-08-17",
    "data_end": "2026-03-10"
}
```

> **Lưu ý**: `data_files` ở trên là ví dụ đầy đủ. Campaign thực tế chỉ khai báo
> files nó thực sự dùng. Aggtrades (daily files) cần schema mở rộng riêng nếu
> nghiên cứu xác định giá trị.

**Evidence**:
- PROMPT_FOR_V[n]_CLEAN_OOS_V1.md §verification [extra-archive]: "how to confirm the new data is
  correctly formatted and continuous with the old data."

**Câu hỏi mở**:
- Data-pipeline update parquet files → campaign cũ có checksum mismatch.
  Policy: campaign ghi snapshot SHA-256 lúc tạo, chạy lại phải verify checksum.
  Nếu mismatch → fail-closed (abort) hay re-snapshot (ghi SHA mới)?
- Cần lock mechanism khi data-pipeline đang write + campaign đang read?
- `_catalog.json` đủ metadata hay campaign cần scan riêng?

---

## F-11: Session immutability — filesystem-level

- **issue_id**: X38-D-11
- **classification**: Thiếu sót
- **opened_at**: 2026-03-18
- **opened_in_round**: 0
- **current_status**: Open

**Nội dung**:

Session artifacts trở thành read-only theo lifecycle:

```
SCANNING → stages 1-6 writable
FROZEN → stages 1-6 read-only (chmod), chỉ holdout/reserve/verdict writable
CLOSED → toàn bộ session dir read-only
```

Enforcement bằng chmod 444 trên files, chmod 555 trên directories.

Lý do: ngăn post-hoc redesign (V6 anti-pattern "quietly retunes after holdout").
Code-level check là backup; filesystem permission là primary enforcement cho
**session immutability** (ngăn sửa artifacts sau freeze).

> **Lưu ý**: "Primary enforcement" ở đây nói về **session immutability** —
> khác với F-04 (contamination firewall) nơi primary enforcement là typed
> schema + state machine. Hai subsystem, hai cơ chế enforcement khác nhau:
> - **Contamination firewall** (F-04): ngăn knowledge leakage → typed schema
> - **Session immutability** (F-11): ngăn post-hoc redesign → filesystem chmod

**Evidence**:
- RESEARCH_PROMPT_V6.md §Stage 6 [extra-archive]: "No redesign or retuning is allowed after this point."
- x37_RULES.md §7.2 [extra-archive]: "Phase 5 là checkpoint bất khả đảo ngược."

**Câu hỏi mở**:
- chmod trên shared filesystem (multi-user) có vấn đề permission?
- Nếu freeze bị lỗi (incomplete artifacts), cách rollback? chmod lại?
- Alternative: hash-based verification thay vì chmod (check SHA-256 artifacts
  thay vì block write)?

---

## Cross-topic tensions

| Topic | Finding | Tension | Resolution path |
|-------|---------|---------|-----------------|
| 002 | F-04 | F-11 session immutability uses chmod enforcement; F-04 contamination firewall uses typed schema + state machine — overlapping enforcement domains may conflict on which mechanism is authoritative for shared artifacts | 002 owns firewall enforcement; 009 owns immutability enforcement |

## Bảng tổng hợp

| Issue ID | Finding | Phân loại | Status |
|----------|---------|-----------|--------|
| X38-D-10 | Data management — data-pipeline output + SHA-256 checksum | Judgment call | Open |
| X38-D-11 | Session immutability — filesystem-level | Thiếu sót | Open |
