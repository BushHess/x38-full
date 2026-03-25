# Round 1 — Opening Critique (claude_code)

**Topic ID**: `X34-DB-01`
**Date**: `2026-03-13`
**Author**: `claude_code`
**Message type**: `opening-critique`
**Scope**: Fresh adversarial review of `findings-under-review.md` (consolidated state)

---

## Tổng quan

Phiên tranh luận mới. Lịch sử tranh luận cũ đã bị xóa. Tôi review toàn bộ
15 findings (F-01 → F-15) + meta-insight trong `findings-under-review.md`.

**Phương pháp review**: Đọc tất cả artifacts gốc, đối chiếu claims với data,
kiểm tra evidence pointers. Artifacts đã đọc:
`diagnostic_results.json`, `validation_report.md`, `full_backtest_detail.json`,
`wfo_summary.json`, `trade_level_summary.json`, `dd_episodes_summary.json`,
`regime_decomposition.csv`, `regime_trade_summary.csv`, `cost_sweep.csv`,
`churn_metrics.csv`, `audit_score_decomposition.md`, `quality_checks.md`,
`PLAN.md`, `resource/phan-bien-avfc-wvdo-qvdo-rh.md`,
`resource/Q-VDO-RH_danh-gia-va-ket-luan.md`.

**Kết quả tổng quan**: 10/15 findings chính xác, không cần thay đổi hoặc chỉ
cần enhancement nhỏ. 4 issues cũ cần chốt. 2 issues mới tôi mở.

---

## I. Findings chấp nhận — không có issue

### F-01 (D-01): Entry logic wording

Corrections applied chính xác. Cả VDO gốc (`EMA(vdr, fast) - EMA(vdr, slow)`,
`strategy.py:162`) lẫn Q-VDO-RH (`EMA(x, fast) - EMA(x, slow)`,
`q_vdo_rh.py`) đều là momentum operators. Wording mới "positive momentum of
raw flow → positive momentum of volume-normalized flow vượt adaptive noise
floor" phản ánh đúng hai khác biệt cấu trúc (normalization bởi
`EMA(quote_volume, slow)` + adaptive threshold `θ = k * scale`).

Evidence verified: `strategy.py:105,162`, `q_vdo_rh.py`, unit test
`constant_buy_zero_momentum`, `diagnostic_results.json:31` (4962 vs 71).

**Trạng thái: Converged — chấp nhận.**

### F-06: Trade structure rewrite

Match rate 44.16% (`trade_level_summary.json:5-16`): 68 matched / 192 baseline
/ 154 candidate. Matched trades kém: mean delta PnL = -942.6, median -77.3
(`trade_level_summary.json:9-10`). Cả trades giữ lại lẫn trades bỏ lỡ đều
tiêu cực — đúng kết luận "rewrite sâu".

**Trạng thái: Uncontested — chấp nhận.**

### F-09 (D-07): Cost/alpha tradeoff

Evidence chain đầy đủ:
- Cost sweep (`cost_sweep.csv`): crossover ~75 bps
- Audit score decomposition (`audit_score_decomposition.md:12`): thua chủ yếu
  do `return_term`, không phải cost terms
- X33 anchor (`cost_summary.md:27`): measured RT cost 16.8 bps << 75 bps

Kết luận "trade-off không có lợi ở cost thực tế" chính xác.

**Trạng thái: Converged — chấp nhận.**

### F-12: A3/A5 chưa chạy

`PLAN.md:311,320` confirms A3 (ratio mode) và A5 (VDO + adaptive θ)
preregistered nhưng chưa chạy do Phase 3 REJECT → Phase 4 skip. Wording "θ là
nghi phạm mạnh nhất nhưng chưa chứng minh" đúng mức qualifier.

**Trạng thái: Converged — chấp nhận.**

### F-13: Infrastructure gap

`v10/core/types.py` (added `quote_volume`, `taker_buy_quote_vol` with defaults)
và `v10/core/data.py` (`_row_to_bar` patched with `.get()` fallback). Giá trị
vượt X34 — bất kỳ research tương lai nào dùng quote-notional data đều cần.

**Trạng thái: Uncontested — chấp nhận.**

### F-14: Mode B deferred

Spec Mode B chưa đóng băng F, gamma, de-rate rule
(`resource/Q-VDO-RH_danh-gia-va-ket-luan.md` §7). Quyết định không encode vào
`shared/` là hygiene đúng.

**Trạng thái: Uncontested — chấp nhận.**

---

## II. Findings chấp nhận — có enhancement đề xuất

### F-03 (D-02): Holdout paradox — thêm WFO structural pattern

Kết luận "gợi ý conditional edge nhưng chưa xác lập thống kê" chính xác.
Corrections (Wilcoxon p=0.68, bootstrap CI crosses zero, PSR=0.005, overlap
35.3%) đều verified.

**Enhancement đề xuất** (không thay đổi kết luận, không cần issue mới):

`wfo_summary.json` cho thấy structural pattern rõ hơn mô tả hiện tại:

| Windows candidate thắng | Baseline Sharpe | Delta |
|---|---|---|
| W0 (2022-H1) | -0.62 | +80.4 |
| W2 (2023-H1) | +0.65 | +46.7 |
| W6 (2025-H1) | +0.59 | +29.3 |

| Windows candidate thua nặng | Baseline Sharpe | Delta |
|---|---|---|
| W3 (2023-H2) | +2.21 | -89.6 |
| W5 (2024-H2) | +2.13 | -89.7 |

Pattern: candidate thắng KHI VÀ CHỈ KHI baseline Sharpe ≤ 0.65 (bear/chop).
Thua nặng KHI VÀ CHỈ KHI baseline Sharpe ≥ 2.13 (strong bull). Delta thua
-89.x gần identical → structural, không phải noise.

Hiện F-03 nói "khi thắng thì thắng rõ (+80, +47, +29), khi thua thì thua rất
đau (-90, -90)". Đề xuất thêm: "candidate thắng ở low-Sharpe windows (≤ 0.65)
và thua ở high-Sharpe windows (≥ 2.13) — conditional edge cụ thể là defensive
filter hoạt động tốt ở bear/chop, mất alpha ở bull."

**Evidence**: `wfo_summary.json` windows 0,2,6 (win, low baseline Sharpe) vs
windows 3,5 (lose, high baseline Sharpe).

### F-05 (D-08): Regime trade-off — bỏ cross-reference X16/X17

Finding body chính xác. WFO window-by-window và regime decomposition nhất quán.

**Judgment call resolved**: **Bỏ X16/X17 ref.** Lý do:
1. Finding doc = "phát hiện của X34". Self-contained tốt hơn.
2. X16/X17 context rất khác (stateful exit, WATCH state machine) — reader cần
   hiểu background riêng để parse cross-reference → barrier to entry.
3. Evidence nội bộ X34 đã đủ: WFO windows (`wfo_summary.json`), regime
   decomposition (`regime_decomposition.csv`), trade PnL
   (`regime_trade_summary.csv`).

### F-11: Adaptive θ — thêm observation cho record

Corrections "có vẻ hấp thụ" (thay vì "triệt tiêu") chính xác. A5 chưa chạy
→ không disentangle được.

**Minor observation** (ghi nhận, không yêu cầu thay đổi finding, không đủ
evidence cho issue):

θ dùng `EMA(|m - EMA(m, slow)|, slow)` — cùng slow window (28 bars ≈ 4.7
ngày ở H4). EMA characteristic lag ≈ `slow/(slow+1)` bars. Khi regime volume
thay đổi nhanh hơn slow_period (halving cycles, liquidity regime shifts), θ
structurally lags momentum. Đây là mathematical property, không phải empirical
finding. Nếu A5 được chạy tương lai, đây là direction cần xem xét.

### F-15: Exposure giảm — thêm efficiency ratio

Finding đúng. Đề xuất thêm 1 data point quantitative:

Return per unit exposure (harsh, `full_backtest_detail.json`):
- Candidate: CAGR 42.79% / exposure 40.13% = **1.066 %/%**
- Baseline: CAGR 52.04% / exposure 46.82% = **1.111 %/%**

Baseline hiệu quả hơn 4.2% per unit capital deployed. Exposure giảm KHÔNG
convert thành efficiency tăng — **double negative**: vừa ít vốn hoạt động,
vừa kém hiệu quả per unit.

---

## III. Positions on Open Issues

### X34-D-03 (→ F-02): Scope of verdict — ĐỒNG Ý caveat, hạ Tier

**Vị trí**: Caveat cần có. **Nhưng F-02 nên ở Tier 2, không phải Tier 1.**

**Lý do đồng ý caveat cần có**:
- Factually accurate: X34 chỉ test Option A entry-only (`PLAN.md:221`)
- `PLAN.md:304,314` ghi rõ A2/A4 không thuộc `b_e0_entry` by construction
- Prevents overgeneralization

**Lý do hạ Tier 1 → Tier 2**:

Tier 1 = "Thay đổi hiểu biết về cấu trúc hệ thống". Scope caveat qualifying
giới hạn diễn giải, không thay đổi hiểu biết cấu trúc.

Core mechanism đã bị reject: quote-notional normalization + adaptive threshold
= REJECT exit 2 (`validation_report.md:11`). Đây LÀ giả thuyết chính
(`PLAN.md:10-11`: "Q-VDO-RH sửa đúng lỗi cấu trúc..."). Reject core = strong
evidence against family.

Untested variants đối mặt prior constraints riêng:
- Level `l_t`: spec nói chỉ context, không hard gate
  (`resource/Q-VDO-RH_danh-gia-va-ket-luan.md` §5.4)
- Hysteresis (Option B): X31-A selectivity 0.21 — mid-trade exit rủi ro
- A2/A4: Δ=0 by construction cho Option A (`PLAN.md:314-317`)

Scope caveat → Tier 2 phù hợp: nó nói về giới hạn diễn giải, không phải
insight cấu trúc mới.

**Steel-man cho Tier 1**: Nếu reader chỉ thấy "REJECT" và không biết scope
hẹp, họ có thể bỏ qua toàn bộ hướng quote-notional flow cho future research.
Đó là thay đổi hiểu biết cấu trúc (loại bỏ sai cả family).

**Phản bác steel-man**: Communication concern ≠ structural finding. Bất kỳ
REJECT nào cũng chỉ áp dụng cho config tested — đây là nguyên tắc chung của
research methodology, không phải X34-specific structural insight. Nếu mọi
scope caveat = Tier 1, tier system bị inflation. Tier 2 "trade-off structure"
phù hợp hơn: finding qualifying scope VÀ noting remaining space is narrow.

**Classification**: Judgment call (tier placement).

### X34-D-04 (→ F-10): Diagnostic GO vs REJECT — reframe

**Vị trí**: Finding cần tồn tại ở Tier 3. Reframe từ "surprise" sang
"methodological reminder".

Hiện finding nói: "Đây không phải chi tiết nhỏ — nó là bài học phương pháp".
Vấn đề: trong framework X34, diagnostic GO → validation REJECT là **expected
behavior**, không phải bất thường. Diagnostic Phase 2 chỉ kiểm tra: ρ ≤ 0.95
(indicator đủ khác baseline), không predict PROMOTE (`PLAN.md:184-196`). GO =
"tiếp tục Phase 3", không phải "indicator tốt hơn".

**Đề xuất**: Thay "Đây không phải chi tiết nhỏ" bằng:
"Đây là methodological reminder: signal-space quality (Spearman ρ=0.887,
selectivity 4,477 vs 9,378, wider dynamic range) KHÔNG sufficient nếu
trade-level alpha và OOS robustness không đi cùng."

Cùng insight, wording không overclaim importance.

**Steel-man cho "không phải chi tiết nhỏ"**: Researcher tương lai có thể chỉ
nhìn diagnostic và skip validation → deploy indicator tệ. Finding cảnh báo
explicitly.

**Phản bác**: "Methodological reminder" đã convey cùng cảnh báo. Framing
"không phải chi tiết nhỏ" là defensive rhetoric, không thêm substance. Phase 2
`PLAN.md:184-196` design diagnostic CỤ THỂ là prefilter nhanh, không phải
validation. Ai đọc PLAN đều biết GO ≠ PROMOTE.

**Classification**: Judgment call (framing).

### X34-D-05 (→ F-04): Veto broad-based — ĐỒNG Ý, thêm asymmetric impact

**Vị trí**: Đồng ý regime breakdown cần có.

Evidence (`diagnostic_results.json:31-48`):
- High-vol 2,512 / Low-vol 2,450 (~50/50)
- Trend-up 2,590 / Trend-down 2,372 (~52/48)

Đây bác narrative "chỉ cắt rác" — filter cắt **đều** trên mọi regime.

**Thêm nuance (cùng evidence base)**: Veto 50/50 nhưng impact bất đối xứng.
Regime trade PnL (`regime_trade_summary.csv`):
- Bull: 57.3k (Q-VDO) vs 109.7k (VDO) — mất 48% bull alpha
- Chop: 54.8k vs 93.1k — mất 41%
- Bear: 28.2k vs 24.6k — Q-VDO thắng +15%

**Uniform veto × asymmetric opportunity cost = net alpha destruction.** Bars bị
chặn ở bull regime chứa alpha cao hơn bars bị chặn ở bear. Đây nối trực tiếp
F-04 (veto composition) → F-05 (regime trade-off): filter không biased NHƯNG
impact biased.

**Classification**: Thiếu sót (đồng ý thêm breakdown + impact asymmetry).

### X34-D-06 (→ F-08): Risk concentration — giữ trong nuance section

**Vị trí**: Buy fills per episode (8.94 vs 6.82,
`trade_level_summary.json:26-28`) hữu ích nhưng là **mechanistic detail**.

Point chính đã established:
- DD episodes: 17 vs 28 (`dd_episodes_summary.json`)
- Worst DD: 45.0% vs 41.6%
- Mean DD: 18.0% vs 14.3%

Buy fills/episode giải thích *cơ chế* (fewer campaigns, denser per campaign)
nhưng không thay đổi *kết luận*. Giữ trong "Nuance bổ sung" section đã có —
phù hợp mức quan trọng.

**Classification**: Judgment call (placement priority).

---

## IV. New Issues

### X34-D-09: Meta-insight overclaims causation

**Classification**: Sai khoa học
**Priority**: high

Meta-insight hiện tại chứa causal claim:

> "nó cắt fat-tail winners **vì** những trade lớn nhất bắt đầu từ flow tăng
> nhẹ, không phải flow tăng mạnh"

**Vấn đề**: "vì" là causal claim. X34 KHÔNG có per-trade tail contribution
analysis. Không có evidence nào trong X34 cho thấy:
(a) trade nào là fat-tail winner,
(b) fat-tail winners có flow tăng nhẹ tại entry,
(c) Q-VDO-RH cắt cụ thể những trade đó.

F-07 corrections đã ghi nhận chính xác: "nhất quán với hiện tượng... nhưng
chưa có attribution study riêng trong X34 để xác nhận trực tiếp"
(`findings-under-review.md:227-238`). Meta-insight phải nhất quán với cùng mức
qualifying mà F-07 đã áp dụng.

Prior knowledge (top 5% = 129.5% profits) đến từ fragility audit
(`memory/fragility_audit.md`), không phải X34. Hierarchy bằng chứng (Rule 6):
kết quả từ project > domain chung, nhưng phải trích đúng nguồn.

**Đề xuất sửa**: Thay đoạn causal claim trong meta-insight bằng:

> "Kết quả nhất quán với hiện tượng cắt fat-tail winners — prior research
> (fragility audit, Step 2) cho thấy top 5% trades = 129.5% profits. Trên
> distribution này, giảm 20% trade count (~38/192 trades) có xác suất ~87%
> loại ít nhất 1 fat-tail trade (binomial calculation). Nhưng X34 chưa có
> per-trade tail attribution study."

Thêm scope qualifier cuối meta-insight:

> "Evidence từ BTCUSDT 2017-08 → 2026-02, H4. Kết luận có thể không áp dụng
> cho instruments có return distribution ít fat-tailed hơn."

**Evidence**:
- `full_backtest_detail.json`: có avg_win, avg_loss, profit_factor — KHÔNG có
  per-trade breakdown
- `findings-under-review.md:227-238`: F-07 corrections dùng "nhất quán với" —
  meta-insight dùng "vì" → inconsistent
- `memory/fragility_audit.md`: nguồn gốc claim "top 5% = 129.5%"
- Binomial: P(hit ≥ 1 fat-tail | remove 38 from 192, 10 fat-tail) =
  1 - C(182,38)/C(192,38) ≈ 1 - (182!/38!144!)/(192!/38!154!) ≈ 87%

### X34-D-10: F-07 thiếu win rate observation

**Classification**: Thiếu sót
**Priority**: normal

`full_backtest_detail.json` harsh scenario:
- Candidate `win_rate_pct`: 42.21% (65 wins / 154 trades)
- Baseline `win_rate_pct`: 40.10% (77 wins / 192 trades)
- **Delta: +2.11pp**

F-07 body hiện tại nêu:
- Avg win: 7,461 → 5,257 (-29.5%)
- Avg loss: 3,096 → 2,347 (-24.2%)
- Profit factor: 1.614 → 1.636 (+0.022)

**Thiếu**: Win rate +2.1pp. Data point này quan trọng vì:

1. Trên bề mặt, win rate tăng gợi ý "chọn trades tốt hơn"
2. Nhưng combined với avg_win giảm 29.5% vs avg_loss giảm 24.2%, ta thấy:
   Q-VDO-RH loại losers nhiều hơn winners (→ better win rate) nhưng **upside
   compression > downside compression** (gap 5.3pp)
3. Trên fat-tailed distribution, winning 2pp more trades KHÔNG compensate cho
   mất 29.5% magnitude per winner

**Đề xuất thêm vào F-07**:

> "Win rate tăng +2.1pp (42.21% vs 40.10%, `full_backtest_detail.json` harsh):
> Q-VDO-RH loại tỉ lệ losers cao hơn winners. Nhưng upside compression
> (29.5%) > downside compression (24.2%) — win rate improvement không bù được
> magnitude loss trên fat-tailed distribution."

**Evidence**: `full_backtest_detail.json` harsh: candidate `win_rate_pct` 42.21,
baseline `win_rate_pct` 40.10.

---

## V. Status Table

| Issue ID | Điểm | Phân loại | Trạng thái | Priority | Steel-man vị trí cũ | Lý do bác bỏ steel-man |
|---|---|---|---|---|---|---|
| X34-D-01 | F-01: Entry logic wording | — | Converged | — | "Positive flow → accelerating flow" captures behavioral shift (static threshold 0 → adaptive θ) | Mô tả sai cả baseline: VDO gốc cũng là oscillator, không phải static flow level (`strategy.py:162`). Shift thực sự là raw vs normalized + threshold, không phải flow vs acceleration. |
| X34-D-02 | F-03: Holdout overclaim | — | Converged | — | Holdout +19.12 PASS hard gate = sufficient evidence of non-noise | Hard gate PASS = necessary, không sufficient. Wilcoxon p=0.68, bootstrap CI [-44.65, +32.22] crosses zero, PSR=0.005 — tất cả validation tests FAIL to reject H0 (`validation_report.md:11-15,22-27`). |
| X34-D-03 | F-02: Verdict scope + tier placement | Judgment call | Open | high | — | — |
| X34-D-04 | F-10: Diagnostic GO vs REJECT framing | Judgment call | Open | normal | — | — |
| X34-D-05 | F-04: Veto broad-based + asymmetric impact | Thiếu sót | Open | normal | — | — |
| X34-D-06 | F-08: Risk concentration placement | Judgment call | Open | low | — | — |
| X34-D-07 | F-09: Cost/alpha tradeoff | — | Converged | — | Candidate ít nhạy phí hơn (slope 0.91 vs 1.15) = đáng triển khai | Gross alpha mất > cost savings: tại 0 bps, gap = 16.74 points (`audit_score_decomposition.md:12`). Crossover ~75 bps >> measured 16.8 bps (`cost_summary.md:27`). |
| X34-D-08 | F-05: Cross-reference X16/X17 | Judgment call | Converged | — | Cross-ref giúp reader thấy X34 trong bức tranh lớn project | Finding doc = X34 findings, self-contained. X16/X17 context (stateful exit, WATCH) rất khác → barrier to entry. Evidence nội bộ đã đủ: WFO + regime + trade PnL. |
| X34-D-09 | Meta-insight causal overclaim | Sai khoa học | Open | high | — | — |
| X34-D-10 | F-07: Thiếu win rate observation | Thiếu sót | Open | normal | — | — |

---
