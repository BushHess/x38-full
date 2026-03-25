# Phase 3: Validation Gauntlet — WFO + Bootstrap + Diagnostics

Copy nội dung trong block ` ``` ` vào phiên mới.

---

```
NGHIÊN CỨU X30 / PHIÊN 3: VALIDATION GAUNTLET

======================================================================
BỐI CẢNH
======================================================================

Đây là phiên 3/4 của nghiên cứu X30 (Fractional Actuator).

TRƯỚC KHI LÀM GÌ:
1. Đọc context: /var/www/trading-bots/btc-spot-dev/research/x30/prompte/context.md
2. Đọc kết quả phiên 1:
   /var/www/trading-bots/btc-spot-dev/research/x30/tables/signal_summary.json
3. Đọc kết quả phiên 2:
   /var/www/trading-bots/btc-spot-dev/research/x30/tables/actuator_summary.json
   → Đặc biệt: "candidates_for_wfo" — danh sách 2-3 configs cần validate
   → "mdd_from_timing_pct" — MDD reduction từ timing hay exposure?

Tóm tắt path đến đây:
- Phiên 1: Signal IS / IS NOT reliable (signal_summary.verdict)
- Phiên 2: Best actuator(s) found + MDD mechanism understood
- Phiên 3 (ĐÂY): Chứng minh bằng toán — WFO + Bootstrap

======================================================================
TẠI SAO PHIÊN NÀY QUYẾT ĐỊNH TẤT CẢ
======================================================================

Full-sample luôn đẹp — mọi research study trước đều full-sample positive.
Nhưng 20+ studies đã FAIL ở validation (bootstrap, WFO, hoặc cả hai).

X29 pilot: X18(partial) full-sample Sh=1.650 (Δ=+0.048) tại 25 bps.
  Nhưng bootstrap P(ΔSh>0)=37.2% — tệ hơn coin flip.

Phiên này có 2 gates:
  G2: WFO 4-fold expanding, win rate ≥ 75% (3/4 folds)
  G3: VCBB bootstrap, P(ΔSh>0) ≥ 55% (500 paths, block=60)

Nếu CẢ HAI pass → PROMOTE
Nếu WFO ≥75% + bootstrap 45-55% → WATCH
Nếu WFO ≥75% + bootstrap <45% → REJECT (pilot đã ở 37.2%, đây là base case)
Nếu WFO <50% → REJECT (overfitting)
Xem VERDICT MATRIX đầy đủ ở phần QUY TẮC.

======================================================================
THIẾT KẾ THÍ NGHIỆM
======================================================================

Viết file: /var/www/trading-bots/btc-spot-dev/research/x30/code/x30_validate.py

Gồm 3 phần (A-C):

--- A: WALK-FORWARD OPTIMIZATION (4-fold expanding) ---

Protocol (cùng X18/benchmark.py):

Fold definitions (expanding window — training grows, OOS fixed ~1.5y):
  Fold 1: Train 2019-01→2021-06, OOS 2021-07→2022-12
  Fold 2: Train 2019-01→2022-12, OOS 2023-01→2024-06
  Fold 3: Train 2019-01→2024-06, OOS 2024-07→2025-06
  Fold 4: Train 2019-01→2025-06, OOS 2025-07→2026-02

Với MỖI fold:
1. Train churn model trên TRAINING DATA (50 bps, cùng protocol)
2. Compute X18 threshold trên training trades (α=40 percentile)
3. Với MỖI candidate config (từ actuator_summary.candidates_for_wfo):
   a. Chạy Base sim trên OOS period
   b. Chạy candidate sim trên OOS period (dùng model trained in-sample)
   c. ΔSharpe_OOS = candidate_Sharpe - Base_Sharpe
4. "Win" nếu ΔSharpe_OOS > 0

QUAN TRỌNG: Mỗi fold phải retrain churn model từ đầu. KHÔNG dùng
full-sample model. Đây là test xem model+actuator có generalize không.

Report per fold: Base_Sh, Candidate_Sh, ΔSh, Base_MDD, Candidate_MDD, ΔMDD

Gate G2: ≥ 3/4 folds win cho ÍT NHẤT 1 candidate

--- B: BOOTSTRAP VCBB (500 paths, primary cost 25 bps) ---

Protocol (cùng x29_benchmark.py và x29_signal_diagnostic.py):

1. Prepare ratios từ post-warmup H4 prices
2. precompute_vcbb(ratios, block_size=60)
3. 500 bootstrap paths, seed=42
4. Với mỗi path:
   a. Compute indicators (EMA, RATR, VDO) trên bootstrap prices
   b. D1 regime: reuse real regime (nhồi lên bootstrap H4 bars)
   c. Monitor V2: compute trực tiếp trên H4 bootstrap prices
      (scale windows: 1080 H4 bars = 6 months, 2160 = 12 months)
   d. Churn model: dùng full-sample trained model
      (model là frozen — trained once, applied everywhere)
   e. Chạy Base sim → Sh_base
   f. Chạy candidate sim → Sh_cand
   g. ΔSh = Sh_cand - Sh_base

5. P(ΔSh>0) = fraction of paths where ΔSh > 0
6. Also compute: P(ΔMDD<0) = fraction where MDD improved

Gate G3: P(ΔSh>0) ≥ 55% cho ÍT NHẤT 1 candidate

QUAN TRỌNG — Monitor V2 on bootstrap paths:
Dùng hàm _compute_h4_monitor() từ x29_monitor_diagnostic.py:
  /var/www/trading-bots/btc-spot-dev/research/x29/code/x29_monitor_diagnostic.py
Hàm này compute MDD rolling trực tiếp trên H4 prices (scaled windows).

--- C: BOOTSTRAP DIAGNOSTICS (CHỈ NẾU G3 FAIL) ---

Nếu G3 fail, chạy diagnostics để HIỂU tại sao. KHÔNG phải để bypass gate.

INTERPRETATION DISCIPLINE — diagnostics KHÔNG thay đổi verdict TRỪ KHI
tìm thấy METHODOLOGICAL BUG (code error, VCBB implementation wrong).
Nếu diagnostics cho thấy:
  - Signal yếu trên bootstrap paths → evidence FOR rejection
  - Effect nhỏ so với noise → evidence FOR rejection
  - Chỉ works trên subset of paths → evidence FOR rejection (fragile)
ĐỪNG dùng diagnostics như danh sách lý do để biện minh cho failure.

C1: Signal preservation test
  - Trên mỗi bootstrap path, score TẤT CẢ trail-stop bars bằng churn model
  - Compare score distribution (bootstrap) vs score distribution (real)
  - KS test: D-statistic và p-value
  - NẾU distributions khác biệt lớn → VCBB phá vỡ feature structure
    → GHI NHẬN, nhưng đây KHÔNG phải lý do để override verdict.
    Nếu method không phù hợp, cần method tốt hơn, không phải verdict mềm hơn.

C2: Conditional analysis
  - Chia 500 paths thành:
    (a) paths có ≥ 10 trail-stop events (sufficient signal)
    (b) paths có < 10 trail-stop events (insufficient signal)
  - P(ΔSh>0) cho mỗi group
  - NẾU group (a) has P > 55% nhưng group (b) kéo xuống → GHI NHẬN,
    nhưng production sẽ gặp CẢ HAI loại paths. Lọc bỏ low-activity paths
    là cherry-picking favorable conditions.

C3: Path-by-path decomposition
  - Sort 500 paths by ΔSh
  - Bottom 50 paths (worst performers): analyze pattern
    - Avg n_trades, avg n_partial_exits, avg exposure
    - Does partial actuator hurt in specific market conditions?
  - Top 50 paths: same analysis
  - Hypothesis: partial actuator helps in trending markets, hurts in ranging

C4: Alternative test — Paired permutation
  - 10,000 permutations: randomly swap Base/Candidate labels within each path
  - Count how often permuted ΔSh ≥ observed ΔSh
  - p-value from permutation test
  - This is a DIFFERENT test than VCBB — may give different answer

C5: Power analysis — bao nhiêu data cần để detect effect?
  - Effect size: observed ΔSh (from full-sample, e.g. +0.048)
  - Noise: std(ΔSh) across 500 bootstrap paths
  - Signal-to-noise: d = ΔSh / std(ΔSh)
  - Cần bao nhiêu paths để P(ΔSh>0) > 55% with 80% power?
  - Quy đổi sang năm data: nếu d nhỏ, cần N năm data thêm?
  - CHỈ REPORT SỐ LIỆU. Verdict vẫn do VERDICT MATRIX quyết định.
    Power analysis GIẢI THÍCH tại sao bootstrap fail, không THAY ĐỔI verdict.

======================================================================
TÀI NGUYÊN CODE
======================================================================

Đọc TRƯỚC KHI viết code:

1. /var/www/trading-bots/btc-spot-dev/research/x29/code/x29_signal_diagnostic.py
   → Sim engines, indicators, churn model training
   → Part D (_part_d) cho bootstrap pattern

2. /var/www/trading-bots/btc-spot-dev/research/x29/code/x29_monitor_diagnostic.py
   → _compute_h4_monitor() cho Monitor V2 trên bootstrap paths

3. /var/www/trading-bots/btc-spot-dev/research/x18/benchmark.py
   → WFO fold definitions pattern

4. /var/www/trading-bots/btc-spot-dev/research/lib/vcbb.py
   → make_ratios(), precompute_vcbb(), gen_path_vcbb()

======================================================================
OUTPUT
======================================================================

Thư mục: /var/www/trading-bots/btc-spot-dev/research/x30/

Code:
  code/x30_validate.py

Tables:
  tables/Tbl_wfo_results.csv
    Columns: candidate, fold, train_start, train_end, oos_start, oos_end,
             base_sharpe, cand_sharpe, delta_sh, base_mdd, cand_mdd, delta_mdd, win

  tables/Tbl_bootstrap.csv
    Columns: candidate, p_delta_sh_pos, median_delta_sh, mean_delta_sh,
             p_delta_mdd_neg, median_delta_mdd

  tables/Tbl_bootstrap_diagnostics.csv  (nếu G3 fail)
    Columns: test, metric, value, interpretation

  tables/validation_summary.json
    {
      "candidates_tested": ["config1", "config2"],
      "wfo_results": {
        "config1": {"wins": int, "total": 4, "mean_delta_sh": float},
        "config2": {...}
      },
      "bootstrap_results": {
        "config1": {"p_delta_sh_pos": float, "median_delta_sh": float},
        "config2": {...}
      },
      "gate_G2": true/false,
      "gate_G3": true/false,
      "best_candidate": "config_name" or null,
      "diagnostics": {                    // only if G3 fail
        "signal_preserved": true/false,   // C1
        "ks_pvalue": float,
        "conditional_p_high_activity": float,  // C2
        "conditional_p_low_activity": float,
        "permutation_pvalue": float,      // C4
        "effect_d": float,                // C5: ΔSh / std(ΔSh)
        "years_needed_for_55pct": float   // C5: estimated years to detect
      },
      "verdict": "PROMOTE" / "WATCH" / "REJECT"
    }

Figures:
  figures/Fig_wfo_bars.png           (grouped bar: ΔSh per fold per candidate)
  figures/Fig_bootstrap_violin.png   (violin: ΔSh distribution per candidate)
  figures/Fig_bootstrap_hist.png     (histogram: ΔSh with 0 line marked)
  figures/Fig_signal_preservation.png (nếu diagnostics: KDE real vs bootstrap scores)
  figures/Fig_conditional_bootstrap.png (nếu diagnostics: P(Δ>0) by activity level)

======================================================================
QUY TẮC
======================================================================

1. RETRAIN PER FOLD — WFO phải retrain churn model mỗi fold.
   Dùng full-sample model là GIAN LẬN.

2. FROZEN ACTUATOR CONFIG — Dùng configs từ actuator_summary.json.
   KHÔNG tune thêm bất cứ gì trong phiên này.

3. HONEST GATES — Report PASS/FAIL thẳng thắn. Không lower threshold.
   55% cho bootstrap, 75% (3/4) cho WFO. Đây là standards từ X14, X18.

4. DIAGNOSTICS LÀ HIỂU, KHÔNG PHẢI BYPASS — Nếu G3 fail, diagnostics
   giải thích TẠI SAO, không phải để find-a-way-to-pass.

5. VERDICT MATRIX (balanced — both gates can cause rejection):
   - WFO ≥ 75% AND bootstrap ≥ 55% → PROMOTE
   - WFO ≥ 75% AND bootstrap 45-55% → WATCH (close to threshold, more data needed)
   - WFO ≥ 75% AND bootstrap < 45% → REJECT (effect too small for practical use,
     pilot's 37.2% already in this range — do NOT lower this bar)
   - WFO 50% AND bootstrap ≥ 55% → WATCH (signal noisy across time)
   - WFO < 50% → REJECT (overfitting, regardless of bootstrap)

   NOTE: "WATCH" is NOT a soft promote. It means "insufficient evidence today,
   check again when 2+ years of new OOS data is available."

6. REPORT MDD alongside Sharpe — MDD improvement là feature quan trọng
   nhất của partial actuator, có thể valuable ngay cả khi Sharpe neutral.

======================================================================
BẮT ĐẦU
======================================================================

Bước 1: Đọc context.md
Bước 2: Đọc signal_summary.json → verify "PROCEED"
Bước 3: Đọc actuator_summary.json → lấy candidates_for_wfo
Bước 4: Đọc x29_signal_diagnostic.py + x18/benchmark.py (code patterns)
Bước 5: Viết code/x30_validate.py
Bước 6: Chạy Part A (WFO) → report G2
Bước 7: Nếu G2 PASS → chạy Part B (Bootstrap) → report G3
Bước 8: Nếu G3 FAIL → chạy Part C (Diagnostics)
Bước 9: Ghi validation_summary.json
Bước 10: Kết luận: PROMOTE / WATCH / REJECT

Hãy bắt đầu từ Bước 1.
```
