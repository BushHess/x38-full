# f_exit_hysteresis — PLAN.md

## Experiment ID: X34-f

**Parent:** X34 (Q-VDO-RH)  
**Status:** PROPOSED  
**Date:** 2026-03-14  
**Spec aligned with:** `E5 + EMA21D1 v1.0`

---

## §1. Bối cảnh và động lực

X34 đã bác bỏ Q-VDO-RH như một **entry filter always-on** cho E5. Tuy nhiên, phát hiện cốt lõi của X34 không phải là “Q-VDO-RH vô dụng”, mà là:

1. Q-VDO-RH có tính chất **veto / state filter** mạnh hơn là tín hiệu mở vị thế.
2. Positive thresholding ở entry có rủi ro **over-filtering** trên BTC spot trend-following.
3. Các thành phần như **hysteresis / level / confidence** hợp lý hơn nếu dùng như **context cho exit** thay vì thay entry logic.

### Sửa lại giả định nền cho đúng với E5 spec

Bản draft cũ sai ở điểm trọng yếu: nó mô tả baseline E5 như thể exit đối xứng với entry bằng `vdo < 0`.
Điều này **không đúng**.

**E5 thật sự hiện tại:**

- **Entry** chỉ xảy ra khi đồng thời thỏa 4 điều kiện:
  - đang FLAT
  - `ema_fast > ema_slow`
  - `vdo > vdo_threshold` (mặc định `> 0`)
  - `d1_regime_ok == True`
- **Exit** xảy ra khi một trong hai điều kiện sau kích hoạt theo thứ tự:
  1. `close < peak_price - trail_mult × rATR`  → **Robust ATR trailing stop**
  2. `ema_fast < ema_slow` → **H4 trend reversal**
- **VDO không dùng cho exit**.
- **D1 regime không dùng cho exit**.

Vì vậy, X34-f **không phải** là nhánh “chữa nhấp nháy của VDO exit”.  
X34-f đúng bản chất phải là nhánh kiểm tra xem Q-VDO-RH có thể đóng vai trò **exit context / confirmation / hysteresis layer** cho **exit stack hiện tại của E5** hay không.

### Vấn đề thực tế cần giải

Ngay cả với exit stack đúng của E5, vẫn có 2 nguồn whipsaw khả dĩ:

1. **EMA fast/slow recross** ở H4 trong vùng chop → thoát vì trend reversal rồi vào lại nhanh.
2. **Shallow pullback gần trailing stop** → thoát ở pullback nông rồi hệ thống quay lại theo trend ngay sau đó.

Nhánh này sẽ ưu tiên xử lý **soft exit** trước, tức **EMA trend-reversal exit**, vì đây là nơi hợp lý nhất để thêm hysteresis / confirmation mà vẫn giữ nguyên lớp bảo vệ rủi ro cứng.

### Giả thuyết trung tâm

Q-VDO-RH có thể hữu ích nếu được dùng như **lớp xác nhận hoặc veto cho soft exit**, đặc biệt là `ema_fast < ema_slow`, nhưng **không được thay thế hard risk control** của E5.

Nói thẳng: nếu muốn giảm nhấp nháy mà lại trì hoãn luôn trailing stop, đó là cách nhanh nhất để phá hồ sơ drawdown. Vì thế, trong pha chính của X34-f, **rATR trailing stop sẽ được giữ nguyên ở tất cả variant**.

---

## §2. Mục tiêu

1. Giảm số exit bị xem là **premature** rồi dẫn tới re-entry nhanh.
2. Giảm tần suất whipsaw của **EMA trend-reversal exit**.
3. Tăng hold duration trung bình mà không làm xấu Sharpe / CAGR / MDD.
4. Kiểm tra xem Q-VDO-RH có giá trị như **exit context** thay vì entry filter hay không.

### Không phải mục tiêu

- Không thay đổi baseline entry stack của E5.
- Không loại bỏ Robust ATR trailing stop khỏi variant chính.
- Không retune sau khi thấy kết quả.

---

## §3. Thiết kế thí nghiệm

### §3.1. Baseline đúng (E5 thực tế)

```
ENTRY:
  FLAT
  AND ema_fast > ema_slow
  AND vdo > vdo_threshold
  AND d1_regime_ok

EXIT 1 (hard):
  close < peak_price - trail_mult × rATR

EXIT 2 (soft):
  ema_fast < ema_slow
```

Tất cả backtest phải giữ nguyên:

- signal tại close bar `i`, fill ở open bar `i+1`
- warmup 365 ngày
- harsh cost model
- cùng dataset / cùng engine so với baseline research hiện có

### §3.2. Taxonomy exit cho nghiên cứu

Để tránh nhầm lẫn, X34-f định nghĩa rõ:

- **Hard exit** = trailing stop theo `peak_price - trail_mult × rATR`
- **Soft exit** = H4 trend reversal `ema_fast < ema_slow`

Trong pha chính của thí nghiệm:

- Hard exit được xem là **risk control gốc** và giữ nguyên.
- Hysteresis / confirmation chỉ áp lên **soft exit**, trừ khi Phase 1 chứng minh phần lớn whipsaw đến từ trailing stop.

### §3.3. Các variant

#### Variant F1 — EMA persistence hysteresis

```
Entry:  baseline E5 (giữ nguyên)
Exit 1: close < trail_stop                      (giữ nguyên)
Exit 2: ema_fast < ema_slow trong 2 bar liên tiếp
```

**Ý tưởng:** một lần cross âm đơn lẻ trên H4 chưa đủ để kết luận trend hỏng.  
Thêm persistence là biến thể ít rủi ro nhất của hysteresis.

**Tham số preregistered:** `k_confirm = 2`

---

#### Variant F2 — EMA band hysteresis

```
spread = (ema_fast - ema_slow) / close

Entry:  baseline E5 (giữ nguyên)
Exit 1: close < trail_stop                      (giữ nguyên)
Exit 2: spread < -b
```

**Ý tưởng:** không thoát chỉ vì EMA vừa cross âm rất nhỏ; chỉ thoát khi spread âm “đủ đáng kể”.

**Tham số preregistered:** `b = 0.10 × σ(spread, lookback=50)`

---

#### Variant F3 — EMA reversal + Q-level confirmation

```
Entry:  baseline E5 (giữ nguyên)
Exit 1: close < trail_stop                      (giữ nguyên)
Exit 2: ema_fast < ema_slow AND q_level < 0
```

Trong đó `q_level` là output mức trạng thái / flow level của Q-VDO-RH.

**Ý tưởng:** EMA H4 cross âm chỉ là tín hiệu trend yếu đi. Chỉ thoát khi context flow/state từ Q-VDO-RH cũng xác nhận bearish.

**Tham số preregistered:** giữ nguyên cấu hình mặc định của `q_level` từ Q-VDO-RH implementation; **không retune trong X34-f**.

---

#### Variant F4 — EMA reversal + bearish-confidence confirmation

```
Entry:  baseline E5 (giữ nguyên)
Exit 1: close < trail_stop                               (giữ nguyên)
Exit 2: (ema_fast < ema_slow AND bearish_conf >= c_min)
         OR (ema_fast < ema_slow trong 3 bar liên tiếp)
```

Trong đó `bearish_conf` là confidence của trạng thái bearish từ Q-VDO-RH.

**Ý tưởng:** nếu Q-VDO-RH chưa đủ chắc rằng bối cảnh đã chuyển bearish, không thoát ngay ở cross đầu tiên.  
Tuy nhiên phải có **time-based fallback** để tránh giữ lệnh vô thời hạn nếu soft-exit cứ kéo dài.

**Tham số preregistered:**

- `c_min = 0.60`
- `k_fallback = 3`

---

### §3.4. Điều gì KHÔNG được làm trong pha chính

- Không thay trailing stop bằng VDO / level / confidence.
- Không đổi exit thành “chỉ thoát khi Q-VDO bearish” mà bỏ qua stop.
- Không sửa entry thành chỉ còn `vdo > 0`.
- Không coi whipsaw là vấn đề của VDO cross 0, vì baseline E5 không exit theo VDO.

---

## §4. Metric đánh giá

### §4.1. Metric chính (primary — dùng cho PASS / REJECT)

| Metric | Cách đo | Mục tiêu |
|--------|---------|----------|
| Sharpe (harsh) | Giữ nguyên phương pháp research hiện tại | ≥ E5 (delta ≥ 0) |
| CAGR (harsh) | Giữ nguyên phương pháp research hiện tại | ≥ E5 − 2pp |
| MDD (harsh) | Giữ nguyên phương pháp research hiện tại | ≤ E5 + 5pp |

### §4.2. Metric whipsaw / premature-exit

| Metric | Định nghĩa | Mục tiêu |
|--------|------------|----------|
| Exit→Re-entry rate | % exit được theo sau bởi long entry mới trong ≤ 5 bar H4 | Giảm ≥ 30% so với E5 |
| Trend-exit whipsaw rate | % exit do `ema_fast < ema_slow` mà hệ thống re-enter trong ≤ 5 bar | Giảm ≥ 40% so với E5 |
| Mean hold duration | Trung bình số bar giữ lệnh | Tăng ≥ 20% |
| Median hold duration | Trung vị số bar giữ lệnh | Tăng ≥ 15% |
| Short round-trip rate | % trade có hold ≤ 3 bar | Giảm ≥ 25% |
| Trade count | Tổng số trade | Giảm hoặc giữ nguyên |

### §4.3. Metric phụ (secondary — quan sát)

| Metric | Mục đích |
|--------|----------|
| Exit reason breakdown | Tỷ trọng exit do trailing stop vs EMA reversal |
| MAE sau soft-exit bị trì hoãn | Đo cái giá phải trả khi hold lâu hơn |
| MFE bỏ lỡ do thoát sớm | Đo lợi ích tiềm năng của hysteresis |
| Win rate | Quan sát phân phối trade |
| Avg win / Avg loss | Kiểm tra payoff ratio |
| Max consecutive losses | Kiểm tra tail risk |
| Regime breakdown | Bull / bear / chop |

---

## §5. Tiêu chí quyết định (preregistered)

### §5.1. PASS

Một variant chỉ PASS nếu đồng thời thỏa mãn:

- Sharpe delta ≥ 0
- CAGR delta ≥ -2pp
- MDD không tăng quá 5pp
- Exit→Re-entry rate giảm ≥ 30%
- Mean hold duration tăng ≥ 20%

### §5.2. CONDITIONAL

Một variant được xếp CONDITIONAL nếu:

- Sharpe delta ≥ -0.05
- MDD tăng không quá 5pp
- Trend-exit whipsaw rate giảm ≥ 50%
- Và không có dấu hiệu tail-risk bất thường trong MAE / drawdown profile

### §5.3. REJECT

REJECT nếu xảy ra ít nhất một trong các điều kiện sau:

- Sharpe delta < -0.10
- MDD tăng > 10pp
- Exit→Re-entry rate không giảm
- Mean hold duration không tăng
- Tỷ trọng exit bị chuyển từ soft exit sang hard stop tăng mạnh và làm xấu MAE rõ rệt

**Nếu REJECT: STOP. Không tiếp tục tune để “cứu” kết quả.**

---

## §6. Quy trình thực hiện

### Phase 1 — Baseline exit audit

Chạy E5 đúng theo spec và đo đầy đủ metric ở §4.
Bắt buộc phải tách whipsaw theo **exit reason**:

- do trailing stop
- do EMA reversal

#### Gate 1

- Nếu `Trend-exit whipsaw rate < 5%` → nhánh X34-f yếu lý do tồn tại → **STOP**.
- Nếu > 60% premature exits đến từ **trailing stop** chứ không phải EMA reversal → **de-scope X34-f**, mở nhánh mới cho trailing-stop state model; **không ép Q-VDO-RH vào bài toán sai**.

### Phase 2 — Implement và unit test F1–F4

Unit test tối thiểu phải có:

- EMA cross âm 1 bar rồi hồi ngay: baseline exit, F1/F2/F3/F4 giữ lệnh đúng logic
- EMA cross âm kéo dài: tất cả variant phải exit trong giới hạn thiết kế
- Trailing stop breach thật: **mọi variant phải exit ngay**, bất kể Q state
- Edge case: `ema_fast == ema_slow`, `q_level == 0`, `bearish_conf == c_min`
- No-lookahead: tất cả tín hiệu chỉ dùng dữ liệu quá khứ
- Fill timing không thay đổi: signal close `i` → fill open `i+1`

**Gate 2:** 100% unit test PASS.

### Phase 3 — Backtest full-sample

- Chạy F1–F4 trên đúng dataset / cost model / engine như baseline.
- So sánh theo toàn bộ metric §4.
- Áp dụng tiêu chí §5.

**Gate 3:** ít nhất 1 variant đạt PASS hoặc CONDITIONAL.
Nếu tất cả REJECT → STOP.

### Phase 4 — Holdout validation

Chỉ áp dụng cho variant PASS / CONDITIONAL.

**Gate 4:** holdout không được đảo dấu ở các metric chính:

- Sharpe delta không chuyển từ dương sang âm rõ rệt
- MDD không xấu vượt ngưỡng
- Whipsaw improvement không biến mất hoàn toàn

### Phase 5 — Sensitivity analysis

Chỉ để kiểm tra robustness, **không dùng để tìm tham số tối ưu**.

Dải kiểm tra preregistered:

- `k_confirm ∈ {1, 2, 3}`
- `b ∈ {0.5×, 1.0×, 1.5×}` của giá trị mặc định
- `c_min ∈ {0.50, 0.60, 0.70}`
- `k_fallback ∈ {2, 3, 4}`

Nếu kết quả chỉ PASS ở đúng một điểm tham số hẹp → đánh dấu **fragile**.

---

## §7. Kết nối với các nhánh khác

### §7.1. Quan hệ với c_ablation và d_regime_switch

X34-f độc lập về logic với nhánh entry optimization.  
Nhánh này chỉ hợp lệ nếu giữ đúng luận điểm: **Q-VDO-RH được thử ở vai trò exit context, không phải hard entry gate**.

### §7.2. Tương thích ngược với E5

Nếu X34-f PASS:

- có thể ghép với c_ablation, d_regime_switch hoặc sizing/regime-monitor branch sau này
- nhưng từng nhánh phải PASS độc lập trước khi ghép

### §7.3. Kết nối với luận đề thống nhất

- **Nếu PASS:** củng cố luận điểm rằng Q-VDO-RH có giá trị ở vai trò **state / confirmation layer** cho exit, không phải entry filter always-on.
- **Nếu REJECT:** tăng bằng chứng rằng Q-VDO-RH không tạo headroom đủ mạnh ngay cả khi bị giới hạn vào vai trò exit-context.

---

## §8. Rủi ro và giới hạn đã biết

1. **Delay soft exit có thể làm tăng give-back.**  
   Một cross EMA ngắn đôi khi là nhiễu, nhưng đôi khi là điểm bắt đầu của leg giảm thật.

2. **Q-VDO-RH có thể redundant với EMA trend.**  
   Nếu q_level / bearish_conf chỉ phản ánh cùng một cấu trúc đã có trong EMA, lợi ích có thể bằng 0.

3. **Nếu phần lớn whipsaw đến từ trailing stop thì X34-f có thể không còn đúng bài toán.**  
   Khi đó phải mở nhánh mới cho stop-state / volatility-state thay vì cố vá EMA exit.

4. **Parameter fragility.**  
   Hysteresis rất dễ “đẹp” ở đúng một điểm tham số rồi sụp khi lệch nhẹ.

5. **False comfort risk.**  
   Hysteresis làm trade count đẹp hơn chưa chắc làm PnL tốt hơn.  
   Trade ít hơn mà drawdown sâu hơn thì vẫn là kết quả tệ.

---

## §9. Deliverables

| Sản phẩm | Mô tả |
|-----------|--------|
| `f_exit_hysteresis.py` | Module triển khai F1–F4 |
| `test_f_exit_hysteresis.py` | Unit test cho EMA-soft-exit hysteresis |
| `baseline_exit_audit.md` | Phase 1: audit baseline, exit-reason breakdown |
| `backtest_results.md` | Phase 3: so sánh F1–F4 vs E5 |
| `holdout_results.md` | Phase 4: validation |
| `sensitivity_report.md` | Phase 5: độ nhạy |
| `validation_report.md` | PASS / CONDITIONAL / REJECT với lý do |

---

## §10. Tiêu chí thành công tổng thể

**X34-f thành công nếu:** ít nhất một variant giảm được premature exits / re-entry nhanh do soft-exit logic mà **không phá risk profile** của E5.

**X34-f thất bại nhưng vẫn có giá trị nếu:** Phase 1 chứng minh vấn đề nằm chủ yếu ở trailing stop hoặc tất cả variant REJECT một cách nhất quán. Khi đó ta biết rõ rằng **bài toán không nằm ở EMA-soft-exit hysteresis**, và phải chuyển sang nhánh khác thay vì tiếp tục mò sai hướng.

---

*Tài liệu này tuân thủ nguyên tắc preregistered research: giả định nền, baseline, variant, metric và tiêu chí quyết định phải được khóa trước khi chạy backtest. Điểm sửa lớn nhất của bản này là: baseline E5 đã được chỉnh đúng theo spec và nhánh X34-f chỉ còn kiểm tra hysteresis cho soft exit thay vì dựng một “VDO exit baseline” không tồn tại.*
