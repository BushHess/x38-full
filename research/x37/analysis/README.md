# X37 Cross-Session Analysis

`analysis/` chỉ dành cho derivative work từ sessions đã hoàn thành.

Allowed:

- so sánh verdict giữa các session `DONE`
- paired comparison giữa các systems đã freeze xong
- meta-analysis về channels, mechanism families, failure modes

Not allowed:

- chỉnh sửa output của session gốc
- dùng `analysis/` để ghi đè verdict session
- dùng `analysis/` làm nơi chạy discovery song song với session ACTIVE

Quy tắc dữ liệu:

- nguồn vào phải là sessions `DONE` hoặc `ABANDONED`
- không đọc sessions đang `ACTIVE`
- mọi output mới nằm trong `analysis/code/` hoặc `analysis/results/`
