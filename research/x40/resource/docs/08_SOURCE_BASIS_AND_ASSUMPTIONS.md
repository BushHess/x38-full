# 08 — Source Basis and Assumptions

## 1. Mục đích

Tài liệu này tách rõ:
- cái nào là fact đã có trong repo / spec nguồn,
- cái nào là policy choice của x40 để vận hành được ngay.

Làm vậy để sau này nếu có debate hoặc reconciliation, đội nghiên cứu biết chính xác đang sửa **fact mismatch** hay đang sửa **policy choice**.

---

## 2. Source basis chính

## 2.1 x37
Dùng để kế thừa:
- session isolation,
- phase gating,
- freeze-before-benchmark discipline,
- abandon criteria,
- session registry semantics.

## 2.2 x38
Dùng để kế thừa:
- phân biệt `internal reserve` với `clean appended reserve`,
- clean OOS chỉ đến từ data sau `freeze_cutoff_utc`,
- x38 là blueprint/offline architecture, không phải invention engine.

## 2.3 x39
Dùng để kế thừa:
- residual explorer role,
- experiment-per-spec pattern,
- evidence rằng simplified replay là diagnostic,
- evidence rằng entry-side winner/loser separation hiện yếu,
- gợi ý rằng exit overlays đáng để ưu tiên.

## 2.4 VTREND / decision policy
Dùng để kế thừa:
- `PF0_E5_EMA21D1` là public-flow incumbent chứ không phải OHLCV-only,
- machine validation namespace production vẫn tách riêng,
- E5 hiện không được phép mặc định coi như baseline fully confirmed.

## 2.5 V8 `S_D1_TREND`
Dùng để kế thừa:
- control baseline `OH0_D1_TREND40`,
- native D1, single signal, long-only, replayability cao.

---

## 3. Facts trực tiếp từ repo mà x40 dựa vào

1. x37 là arena cho discovery sessions độc lập, root wrapper chỉ chạy một phase mỗi lần.
2. x37 có freeze discipline mạnh, Appendix A embargo, abandon criteria rõ, và cấm import giữa sessions active.
3. x38 phân biệt rõ `internal reserve` trong cùng file với `clean reserve` từ dữ liệu append sau freeze.
4. x38 là blueprint kiến trúc, không phải code project chính thức đang deploy.
5. x39 là feature invention explorer; baseline của x39 hiện xoay quanh E5 simplified replay.
6. x39 ghi rõ 0/31 features không tách winners khỏi losers tại entry trong explore findings hiện tại.
7. `exp12_rangepos_exit` cho thấy exit-side modification là một hướng hợp lý để kiểm tra.
8. `exp30_and_gate_walk_forward` tự nhận replay ở x39 là diagnostic, not authoritative.
9. VTREND blueprint hiện dùng `taker_buy_base_vol` cho VDO và đã xóa fallback OHLC vì semantic mismatch.
10. `S_D1_TREND` của V8 là native D1, one-signal, no regime gate, no cross-timeframe, no data calibration.

---

## 4. Policy choices của x40 (không phải fact đã chốt bởi repo)

Các mục dưới đây là quyết định vận hành để x40 chạy được ngay; không nên giả vờ chúng đã là “chân lý repo”:

1. Namespace baseline:
   - `B0_INCUMBENT`
   - `B1_QUALIFIED`
   - `B2_CLEAN_CONFIRMED`
   - `B_FAIL`

2. Namespace durability:
   - `DURABLE`
   - `WATCH`
   - `DECAYING`
   - `BROKEN`

3. Yêu cầu `next_action` chỉ có 3 primary actions.

4. Tách `open_x37_challenge` thành escalation flag riêng.

5. Ưu tiên cadence:
   - PF0 monthly
   - OH0 quarterly

6. Minimum floor cho `B2_CLEAN_CONFIRMED` là 180 ngày appended data.

7. Việc ép x39 residual sprint phải đi qua:
   - episode explorer
   - concept card
   - family-level robustness
   - kill battery
   trước khi đòi canonical replay.

8. Việc ưu tiên exit-focused sprint trước entry-focused sprint nếu A04 xác nhận.

Những policy choices này có thể đổi trong tương lai, nhưng phải đổi bằng artifact và revision control.

---

## 5. Assumptions vận hành

x40 đang giả định:
- có thể pin snapshot IDs,
- có canonical replay engine deterministic,
- có khả năng xuất return series native và daily UTC,
- có thể dựng public-flow baseline riêng biệt với OHLCV-only,
- có thể lưu và cập nhật `forward_evaluation_ledger.csv` lâu dài,
- đội nghiên cứu chấp nhận không self-retune live.

Nếu một assumption sai, phải ghi blocker rõ thay vì “lách” bằng ad hoc workflow.

---

## 6. Điều không nên quên

Một source basis đúng không có nghĩa là mọi policy choice đều đúng vĩnh viễn.

Nhưng nếu không tách fact khỏi policy choice, thì mỗi lần sửa gì cũng sẽ rất dễ:
- nhầm design choice thành repo truth,
- hoặc ngược lại,
- và cuối cùng làm drift cả spec lẫn implementation.

Tài liệu này tồn tại để chặn điều đó.
