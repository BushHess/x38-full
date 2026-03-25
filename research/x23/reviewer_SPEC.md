# X23 Spec Review

Ground truth used:

- Proposal: [DeCuong.md](/var/www/trading-bots/btc-spot-dev/research/x23/DeCuong.md)
- Spec under review: [SPEC.md](/var/www/trading-bots/btc-spot-dev/research/x23/SPEC.md)
- Repo files consulted for verification:
  [strategy.py](/var/www/trading-bots/btc-spot-dev/strategies/vtrend_e5_ema21_d1/strategy.py),
  [engine.py](/var/www/trading-bots/btc-spot-dev/v10/core/engine.py),
  [config.py](/var/www/trading-bots/btc-spot-dev/validation/config.py),
  [wfo.py](/var/www/trading-bots/btc-spot-dev/validation/suites/wfo.py),
  [bootstrap.py](/var/www/trading-bots/btc-spot-dev/validation/suites/bootstrap.py),
  [selection_bias.py](/var/www/trading-bots/btc-spot-dev/validation/suites/selection_bias.py),
  [decision.py](/var/www/trading-bots/btc-spot-dev/validation/decision.py),
  [decision.json](/var/www/trading-bots/btc-spot-dev/results/full_eval_e5_ema21d1/reports/decision.json),
  [validation_report.md](/var/www/trading-bots/btc-spot-dev/results/full_eval_e5_ema21d1/reports/validation_report.md),
  [benchmark.py](/var/www/trading-bots/btc-spot-dev/research/x18/benchmark.py).

## Trục 1 — Faithfulness

### F1 — Trục 1 — DEVIATION
Mô tả: Đề cương yêu cầu core implementation phải được tổ chức như một strategy mới trong repo; spec lại mô tả một nhánh nghiên cứu tự-contained xoay quanh `research/x23/benchmark.py` và các artifact đi kèm, không mô tả strategy package, đăng ký factory, hay tích hợp vào validation stack hiện tại.

Reference:
- Đề cương `§1` và câu “Core implementation phải được tổ chức như một strategy mới” trong [DeCuong.md](/var/www/trading-bots/btc-spot-dev/research/x23/DeCuong.md)
- Spec `§3 File Layout` và `§16.1 Phase 1` trong [SPEC.md](/var/www/trading-bots/btc-spot-dev/research/x23/SPEC.md)
- Cấu trúc strategy thực tế trong repo: [strategy.py](/var/www/trading-bots/btc-spot-dev/strategies/vtrend_e5_ema21_d1/strategy.py)

Impact: Nếu implement đúng spec hiện tại, kết quả nhiều khả năng dừng ở mức benchmark script trong `research/`, không phải strategy first-class để chạy qua pipeline hiện hành. Đây là sai lệch trực tiếp với mục tiêu branch mà đề cương đặt ra.

### F2 — Trục 1 — BUG
Mô tả: Spec đổi định nghĩa churn. Đề cương định nghĩa churn exit là “stop bị hit” và “trong 20 bars sau exit, giá phục hồi vượt peak cũ”. Spec lại dùng “re-entry within 20 bars” làm churn criterion, cả ở Motivation lẫn T1.

Reference:
- Đề cương `§3`, định nghĩa churn trong [DeCuong.md](/var/www/trading-bots/btc-spot-dev/research/x23/DeCuong.md)
- Spec `§2 Motivation`, `§11 T1`, và `_label_churn_x23()` trong [SPEC.md](/var/www/trading-bots/btc-spot-dev/research/x23/SPEC.md)
- Nguồn gốc của định nghĩa spec đang reuse từ X18: `_label_churn()` trong [benchmark.py](/var/www/trading-bots/btc-spot-dev/research/x18/benchmark.py)

Impact: Churn rate, “63% churn”, exit anatomy, và mọi diagnostic downstream không còn đo cùng một object với đề cương. Người implement theo spec có thể kết luận sai về việc exit geometry có thực sự giảm churn theo ý định nghiên cứu hay không.

### F3 — Trục 1 — NOTE
Mô tả: Đề cương có tension nội tại giữa hai ý. `§6.4` và `§9.3` nói calibration phải đi từ healthy pullback distribution trên training fold; `§11` lại cho sẵn prototype preset `2.25 / 3.0 / 4.25` để implement trước. Spec chọn cách giải quyết riêng: `X23-fixed` là variant binding cho gate, còn `X23-cal` chỉ là supplementary diagnostic.

Reference:
- Đề cương `§6.4`, `§9.3`, `§11.4` trong [DeCuong.md](/var/www/trading-bots/btc-spot-dev/research/x23/DeCuong.md)
- Spec `§10.6`, `§11 T0/T3`, `§12` trong [SPEC.md](/var/www/trading-bots/btc-spot-dev/research/x23/SPEC.md)

Impact: Đây là quyết định riêng của spec, không phải điều được đề cương chốt dứt khoát. Nếu người implement đọc spec mà không đọc đề cương, họ sẽ ngầm hiểu calibration là tùy chọn phụ, dù phần trước của đề cương viết mạnh hơn thế.

## Trục 2 — Internal Consistency

### F4 — Trục 2 — BUG
Mô tả: Contract của `stats` không khớp pseudocode. Spec công bố `stats` có `n_trades` và `n_end_of_data`, nhưng pseudocode không bao giờ increment hai field này. `n_trades` cũng không được sync với `len(trades)`.

Reference:
- Spec `§9.9 Complete per-bar logic`
- Spec `§9.10 Stats dict returned by _run_sim_x23()`
- Cùng file: [SPEC.md](/var/www/trading-bots/btc-spot-dev/research/x23/SPEC.md)

Impact: Người implement theo pseudocode sẽ trả ra stats sai nhưng vẫn “đúng spec” theo mô tả code block. Diagnostic/report downstream có thể dùng nhầm các số này.

### F5 — Trục 2 — AMBIGUITY
Mô tả: Metadata “DOF budget = 0 tuned params (all values preset by spec)” mâu thuẫn với phần thân spec. `§6.1` grid-search `C` bằng 5-fold CV; `§10.6` lại có variant `X23-cal` fit multiplier theo training fold; `§17.5` thừa nhận logistic model và calibrated multipliers là fitted component.

Reference:
- Spec `§1 Study ID & Metadata`
- Spec `§6.1 Training procedure`
- Spec `§10.6 Usage in WFO`
- Spec `§17.5 No optimization over X23 parameters`
- Cùng file: [SPEC.md](/var/www/trading-bots/btc-spot-dev/research/x23/SPEC.md)

Impact: Không rõ “0 tuned params” ở đây là governance statement hay ràng buộc thực thi. Người implement sẽ không biết C-search và fold-calibrated multipliers có được tính là allowed DOF hay không.

### F6 — Trục 2 — BUG
Mô tả: Phần mô tả verbal của pullback calibration và pseudocode bên trong `_calibrate_pullback()` không khớp nhau. `§10.1` định nghĩa `tau_next_peak` là first `u > t` nơi `cl[u] > peak_t` không giới hạn bởi baseline exit. Nhưng algorithm sketch ở `§10.5` lại chỉ search `tau_peak` đến `xb + 1` với `xb = exit_bar` của baseline trade, trong khi `tau_fail` search đến hết dữ liệu.

Reference:
- Spec `§10.1 Continuation instance detection`
- Spec `§10.5 Algorithm sketch`
- Proposal `§9.1 Dataset calibration` trong [DeCuong.md](/var/www/trading-bots/btc-spot-dev/research/x23/DeCuong.md)

Impact: Healthy continuation nào chỉ tạo new peak sau khi baseline E5 đã thoát bằng trail sẽ bị loại sai khỏi calibration set. Kết quả là calibrated multipliers bị bias xuống, đúng vào phần dữ liệu mà X23 đang cố cứu.

## Trục 3 — Implementability

### F7 — Trục 3 — AMBIGUITY
Mô tả: WFO procedure không chốt semantics biên train/test. Spec nói freeze params trên training fold rồi run `_run_sim_x23()` trên full data và “measure test window only”. Spec không nói có cho phép position mở từ trước `test_start` mang PnL sang OOS hay phải flat-start ở đầu test window.

Reference:
- Spec `§10.6 Usage in WFO`
- Spec `§11 T3 Walk-Forward Optimization`
- Repo authority hiện tại chạy từng test window độc lập tại [wfo.py](/var/www/trading-bots/btc-spot-dev/validation/suites/wfo.py)

Impact: Có ít nhất hai implementation hợp lý nhưng cho OOS metrics khác nhau đáng kể. Đây là chỗ implementer buộc phải đoán.

### F8 — Trục 3 — BUG
Mô tả: Fill convention trong spec không tương thích với engine hiện tại của repo. Spec/X18 benchmark dùng “signal at bar t, fill at t+1 using `cl[t]` proxy / `cl[i-1]`”, còn engine repo fill thật ở next bar open.

Reference:
- Spec `§7 _run_sim_e0()`, `§9.3 Entry logic`, `§17.2 Fill convention`
- X18 baseline implementation trong [benchmark.py](/var/www/trading-bots/btc-spot-dev/research/x18/benchmark.py)
- Repo execution semantics trong [engine.py](/var/www/trading-bots/btc-spot-dev/v10/core/engine.py)

Impact: Nếu X23 được implement thành strategy thật trong repo, số liệu benchmark theo spec sẽ không còn comparable với baseline hiện hành. Sai lệch này ảnh hưởng trực tiếp đến entry price, MFE arming, hard stop anchor và toàn bộ delta metrics.

### F9 — Trục 3 — AMBIGUITY
Mô tả: Spec mô tả training logistic bằng 5-fold CV AUC nhưng không định nghĩa fallback cho fold/sample không đủ dữ liệu hoặc chỉ có một class. X18 có fallback rõ ràng: nếu `len(y) < 10` hoặc chỉ có một class thì trả `None`.

Reference:
- Spec `§6.1 Training procedure`, `§6.4 _precompute_scores()`
- Fallback thực tế trong X18 `_train_model()` tại [benchmark.py](/var/www/trading-bots/btc-spot-dev/research/x18/benchmark.py)

Impact: Ở bootstrap paths, short windows, hay state đặc biệt, implementer có thể gặp crash hoặc phải tự chế fallback. Kết quả giữa các implementation sẽ diverge.

## Trục 4 — Validation Soundness

### F10 — Trục 4 — BUG
Mô tả: Spec tự dựng một benchmark/decision stack riêng và bỏ qua nhiều gate authority trong repo hiện tại: `lookahead`, `holdout`, `trade_level_bootstrap`, `holdout_wfo_overlap`, cùng các suite quality gates khác. Đề cương yêu cầu branch mới phải “sống được qua validation”, còn repo hiện tại đã có validation stack thống nhất.

Reference:
- Đề cương `§2.3 Validation stack hiện tại` trong [DeCuong.md](/var/www/trading-bots/btc-spot-dev/research/x23/DeCuong.md)
- Spec `§11 Benchmark Tests`, `§12 Validation Gates Summary`
- Suite registry trong [config.py](/var/www/trading-bots/btc-spot-dev/validation/config.py)
- Decision gates thực tế trong [decision.py](/var/www/trading-bots/btc-spot-dev/validation/decision.py)
- Ví dụ authority run: [decision.json](/var/www/trading-bots/btc-spot-dev/results/full_eval_e5_ema21d1/reports/decision.json) và [validation_report.md](/var/www/trading-bots/btc-spot-dev/results/full_eval_e5_ema21d1/reports/validation_report.md)

Impact: Một X23 implementation có thể “pass spec” nhưng vẫn chưa đạt chuẩn promote của repo. Đây là lỗ hổng quy trình, không chỉ khác wording.

### F11 — Trục 4 — DEVIATION
Mô tả: WFO trong spec không khớp WFO authority của repo. Spec dùng 4 expanding folds cố định và gate trên `win_rate >= 3/4` cộng `mean_d_sharpe > 0`. Repo hiện tại dùng rolling windows từ config, measure `delta_harsh_score`, rồi bind bằng Wilcoxon/Bootstrap CI; binary win-rate chỉ advisory.

Reference:
- Spec `§4 WFO_FOLDS`, `§11 T3`
- Repo WFO windowing và metric trong [wfo.py](/var/www/trading-bots/btc-spot-dev/validation/suites/wfo.py)
- Repo gate consumption trong [decision.py](/var/www/trading-bots/btc-spot-dev/validation/decision.py)

Impact: Kết luận OOS từ spec không map sang verdict authority của repo. Một strategy có thể pass `3/4` nhưng fail Wilcoxon, hoặc ngược lại.

### F12 — Trục 4 — DEVIATION
Mô tả: Bootstrap trong spec được dùng như hard gate (`G2`, `G3`) trên VCBB synthetic paths với retraining. Repo hiện tại dùng paired block bootstrap trên actual equity curves và đánh dấu rõ đó chỉ là diagnostic, “no veto power”.

Reference:
- Đề cương `§2.3` nêu VCBB bootstrap là thành phần stack lịch sử
- Spec `§11 T4`, `§12`
- Repo bootstrap suite trong [bootstrap.py](/var/www/trading-bots/btc-spot-dev/validation/suites/bootstrap.py)
- Repo decision handling trong [decision.py](/var/www/trading-bots/btc-spot-dev/validation/decision.py)

Impact: Spec đang gán quyền quyết định cho một test mà pipeline authority hiện tại cố ý không dùng làm veto. Điều này làm verdict theo spec không tương thích với verdict thật của repo.

### F13 — Trục 4 — DEVIATION
Mô tả: PSR/selection-bias gate trong spec cũng không khớp repo. Spec dùng PSR tuyệt đối với `sr0 = benchmark_sr0(E0_EFFECTIVE_DOF)`. Repo dùng PSR tương đối `P(SR_candidate > SR_baseline)` trên daily log returns; DSR chỉ advisory.

Reference:
- Spec `§11 T6 PSR with DOF Correction`
- Repo selection-bias suite trong [selection_bias.py](/var/www/trading-bots/btc-spot-dev/validation/suites/selection_bias.py)
- Threshold authority trong [thresholds.py](/var/www/trading-bots/btc-spot-dev/validation/thresholds.py)

Impact: Hai phép kiểm định đang trả lời hai câu hỏi khác nhau. Pass T6 theo spec không có nghĩa là pass selection-bias gate của repo.

## Trục 5 — Soundness

### F14 — Trục 5 — NOTE
Mô tả: Cả đề cương và spec đều tái sử dụng logistic churn model như một “market-state score” để bucket continuation strength, nhưng không có bước nào chứng minh score này thực sự monotonic với healthy-pullback depth dưới kiến trúc stop mới. Đề cương đã chỉ ra binary churn target là mismatch với trading objective; spec vẫn dùng chính model đó làm biến trung tâm cho stop width.

Reference:
- Đề cương `§5` và `§6.2`
- Spec `§6 Market-State Score Model`, `§10 Pullback Calibration Algorithm`

Impact: Nếu score chỉ dự báo “khả năng recover sau stop cũ” chứ không dự báo “độ sâu healthy pullback”, toàn bộ state bucketing của X23 có thể condition stop width theo một surrogate lệch mục tiêu.

### F15 — Trục 5 — NOTE
Mô tả: Cả đề cương lẫn spec đều xem “mọi in-position bar” là sample riêng cho pullback calibration và dùng raw count để quyết định shrinkage (`len >= 20`, `len >= 5`). Các sample này overlap cực mạnh trong cùng một trade, nên effective sample size nhỏ hơn nhiều raw count.

Reference:
- Đề cương `§9.1`, `§9.3`
- Spec `§10.1`, `§10.3`

Impact: Stability của per-state quantile và shrinkage rule có thể bị overstate. Nhìn bề ngoài bucket “đủ mẫu”, nhưng thực chất chỉ là nhiều bar rất tương quan từ vài trade dài.

## Tổng kết

- BUG: 5
- AMBIGUITY: 3
- DEVIATION: 4
- NOTE: 3

Đánh giá ngắn: spec này chưa đủ tin cậy để bắt đầu implementation. Có ít nhất ba vấn đề phải sửa trước khi code: định nghĩa churn đang lệch đề cương, pullback calibration pseudocode đang cắt sai `tau_next_peak`, và benchmark/validation stack trong spec không khớp validation authority hiện có của repo. Nếu implement ngay theo spec hiện tại, rủi ro cao là vừa tốn thời gian vừa tạo ra kết quả không so sánh được với baseline/promote flow đang dùng.
