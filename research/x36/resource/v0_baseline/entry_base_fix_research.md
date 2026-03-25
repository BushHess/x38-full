# Entry Filtering — ML trên bài toán nhiều dữ liệu hơn

## Ý tưởng chính

Chuyển ML sang **entry filtering** thay vì thay thế strategy logic.

## Tại sao entry filtering?

1. **Giữ nguyên base strategy làm nền** — không phá vỡ thứ đang hoạt động
2. **Sample size lớn hơn nhiều** — câu hỏi ML đặt ở mức bar-level ("bar này có nên vào lệnh không?"), nên dùng được toàn bộ dữ liệu bar để train/predict
3. **Chỉ hành động khi base strategy ra tín hiệu entry** — ML lọc bớt entry kém, không thay thế logic gốc

## Cơ chế hoạt động

- Model dự đoán trên **mọi bar** (tận dụng toàn bộ data)
- Chỉ **áp dụng quyết định** tại các bar mà base strategy phát tín hiệu entry
- Kết quả: một số entry bị suppress (ML đánh giá là kém), phần còn lại giữ nguyên
