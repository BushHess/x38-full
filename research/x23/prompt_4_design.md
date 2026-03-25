Bạn đã hoàn thành 3 vòng phân tích:
- Vòng 1: exploratory trên dữ liệu thô
- Vòng 2: conditional analysis quanh 226 trades
- Vòng 3: tổng hợp — kết luận là {{ A, B, hoặc C từ prompt 3 }}

{{ PASTE kết luận sơ bộ của AI từ prompt 3 ở đây }}

---

NẾU kết luận là (B) hoặc (C): bạn được phép dừng ở đây.
Viết final report tổng hợp 3 vòng. Kết luận:
"VDO đã gần optimal / volume info ceiling thấp. Không thiết
kế filter mới. Alpha nên tìm ở [exit / regime / sizing]."
Đó là output hoàn chỉnh và có giá trị.

---

NẾU kết luận là (A): bây giờ mới thiết kế.

Bạn đã thấy rằng {{ AI tự điền từ kết luận vòng 3 }}.
Thiết kế entry filter khai thác ĐÚNG thông tin đó.

Ràng buộc:
- Tối đa 2 tham số tự do
- Pipeline đã có 4 DOF (EMA slow, trail mult,
  VDO threshold, D1 EMA period). Tổng ≤ 6.
- Sample: ~226 trades. Phải survive WFO (4 folds),
  bootstrap (VCBB 500 paths), jackknife (6 folds).
- Chỉ dùng thông tin tại bar t. Không lookahead.
- Chỉ thay entry filter. Không đổi exit.

Yêu cầu:

1. Định nghĩa toán học đầy đủ
   - Công thức
   - Input → Output
   - Tham số và ý nghĩa mỗi tham số

2. Justification — phải trỏ ngược về observations
   - "Filter này khai thác pattern X mà tôi đã thấy
     ở Vòng 1 mục Y / Vòng 2 mục Z"
   - Nếu không trỏ được về observation cụ thể → bỏ

3. So sánh lý thuyết với VDO
   - Capture cùng thông tin hay thông tin khác?
   - Nếu cùng: tại sao dạng mới compact hơn?
   - Nếu khác: thông tin mới đó có SNR bao nhiêu?

4. Implementation + visual check
   - Viết code tính signal
   - Plot overlay với price + VDO + entry markers
   - NHÌN trước khi kết luận: signal mới nhìn
     "reasonable" hơn VDO ở đâu? Xấu hơn ở đâu?

5. Backtest so sánh
   - Chạy trong cùng pipeline, cùng parameters
   - Report: Sharpe, CAGR, MDD, trade count, exposure
   - Δ vs VDO baseline cho mỗi metric

6. Reality check
   - Nếu candidate KHÔNG beat VDO: nói thẳng, giải thích
     tại sao dựa trên cái đã thấy, kết luận.
   - Nếu beat nhẹ (ΔSharpe < 0.1): nói thẳng rằng
     improvement có thể là noise với n=226.
   - Chỉ recommend thay VDO nếu improvement rõ ràng
     VÀ giải thích được bằng pattern đã thấy trong data.

Không làm:
- Không liệt kê indicator có sẵn (RSI, OBV, MACD...)
- Không ensemble/ML
- Không đề xuất gì >2 DOF
- Không propose rồi justify — derive từ observations
