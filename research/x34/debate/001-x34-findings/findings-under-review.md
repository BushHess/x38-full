# X34 Findings Under Review

Topic ID: `X34-DB-01`
Created at: `2026-03-13T14:26:25Z`
Last updated at: `2026-03-14T00:00:00Z`
Scope: `Các phát hiện của X34`
Current round reflected: `round 3 (phiên mới) — CLOSED`
Status summary: `8 converged / 2 judgment call (10 issues total, all resolved)`

## Purpose

File này chứa danh sách phát hiện đã tổng hợp, lọc trùng, và phân loại —
dùng làm cơ sở duy nhất cho tranh luận giữa claude_code và codex.

Mỗi finding có:
- `finding_id` ổn định (F-01, F-02, ...)
- `issue_ids` ánh xạ đến debate issues đã mở (X34-D-xx)
- `review_status`: trạng thái từ debate rounds trước
- `corrections`: sửa đổi đã được chấp nhận từ debate

## Sources

Danh sách này tổng hợp từ:
1. Phát hiện gốc của claude_code (12 items, 3 tiers)
2. Adversarial review vòng 1-2 (reviewer + claude_code reply)
3. Codex round 3 (5 issues mới: X34-D-03 → X34-D-06, mở rộng X34-D-01)
4. Rescan toàn bộ artifacts: `diagnostic_results.json`, `validation_report.md`,
   `trade_level_summary.json`, `regime_trade_summary.csv`, `regime_decomposition.csv`,
   `dd_episodes_summary.json`, `cost_sweep.csv`, `churn_metrics.csv`,
   `audit_score_decomposition.md`, `quality_checks.md`

---

## Consolidated Findings

### Tier 1 — Thay đổi hiểu biết về cấu trúc hệ thống

#### F-01: Entry logic chuyển từ positive momentum of raw flow sang positive momentum of volume-normalized flow vượt adaptive noise floor

**Issue IDs**: X34-D-01
**Review status**: Converged (claude_code round 2)
**Corrections applied**:
- Wording cũ "positive flow → accelerating flow" bị bác: VDO gốc cũng là
  oscillator `EMA(vdr, fast) - EMA(vdr, slow)`, không phải static flow level.
  Codebase comment `0.0 = any positive flow` (`strategy.py:34`) là shorthand
  nghiệp vụ, không phải mô tả bản chất. Formula thật (`strategy.py:162`) là
  momentum operator.
- Q-VDO-RH tách rõ `m_t` (change of normalized flow) và `l_t` (level/regime tĩnh).
  Spec §5.4 nói L chỉ là context, không dùng làm gate.
- Constant buy pressure 80% → `m ≈ 0` → Q-VDO-RH im lặng. Đây là hành vi
  đúng theo thiết kế: nó đo *thay đổi*, không đo *mức*.

**Finding**:
VDO gốc: `EMA(vdr, fast) - EMA(vdr, slow) > 0` — positive momentum of raw
volume delta ratio, any magnitude. Q-VDO-RH: `EMA(x, fast) - EMA(x, slow) > k *
scale` — positive momentum of volume-normalized flow exceeding adaptive noise
floor. Hai khác biệt cấu trúc: (a) normalization bởi `EMA(quote_volume, slow)`,
(b) adaptive threshold `θ = k * EMA(|m - EMA(m)|, slow)` thay vì zero.
4,962 bars "VDO yes / Q-VDO no" phản ánh sự khác biệt này — phần lớn là bars
có buy pressure dương nhưng không tăng thêm.

**Evidence**:
- `strategies/vtrend/strategy.py:105,162`
- `research/x34/shared/indicators/q_vdo_rh.py`
- `research/x34/shared/tests/test_q_vdo_rh.py` (constant_buy_zero_momentum)
- `research/x34/branches/a_diagnostic/results/diagnostic_results.json:31` (4962 vs 71)

---

#### F-02: X34 chỉ bác một variant hẹp (Option A entry-only), chưa bác toàn bộ Q-VDO-RH family

**Issue IDs**: X34-D-03 (codex round 3)
**Review status**: Judgment call (round 3)

**Finding**:
Variant được validate: `trend_up AND qvdo_momentum > qvdo_theta` (Option A
entry-only). Verdict REJECT áp dụng cho **acceleration + adaptive θ**, không áp
dụng cho toàn bộ quote-notional flow.

Chưa được test trong X34:
- Level field `l_t = EMA(x, slow)` — thông tin regime tĩnh, spec nói chỉ dùng
  làm context ở v1
- Hysteresis (Option B, `c_e0_hysteresis/`)
- `high_confidence`, `long_hold` fields từ `q_vdo_rh.py`
- Ablation A2/A4 (hysteresis/level active) không thuộc `b_e0_entry` by construction

**NOTE (Judgment call, round 3)**: Tier placement chưa chốt.
- Tier 1 nếu ưu tiên: ranh giới falsification (tested vs untested components)
  là structural bookkeeping, thay đổi hiểu biết cấu trúc. Spec/code tách rõ
  `momentum`, `level`, `hysteresis` → xác định đối tượng bị falsify là structural.
- Tier 2 nếu ưu tiên: finding mô tả evidence scope, không phải system behavior.
  F-01/F-03 mô tả system behavior → Tier 1. F-02 mô tả coverage of evidence →
  Tier 2 "trade-off structure" phù hợp hơn.
- Decision owner: **user**

**Evidence**:
- `research/x34/branches/b_e0_entry/PLAN.md` (Option A definition, §Thiết kế)
- `research/x34/branches/c_ablation/PLAN.md` + `branches/e_level_hysteresis/PLAN.md` (A2/A4 not in b_e0_entry)
- `research/x34/resource/Q-VDO-RH_danh-gia-va-ket-luan.md:195` (§5.4, L = context)
- `research/x34/shared/indicators/q_vdo_rh.py:34` (output fields)

---

#### F-03: Nghịch lý full-sample thua / holdout thắng — gợi ý conditional edge nhưng chưa xác lập thống kê

**Issue IDs**: X34-D-02
**Review status**: Converged (claude_code round 2)
**Corrections applied**:
- Wording cũ "đây không phải noise" bị bác: Wilcoxon p=0.68, bootstrap CI
  [-44.65, +32.22] crosses zero, PSR=0.005 — tất cả validation tests FAIL to
  reject H0. "Not noise" là claim thống kê mà X34 không chứng minh được.
- Steel-man mạnh nhất (holdout = hard gate duy nhất PASS) vẫn không đứng vững:
  hard gate PASS = necessary condition, không phải proof of non-noise.
- Overlap 35.3% (184 days) làm yếu independence giữa holdout và WFO — nhưng
  không chứng minh holdout bị inflated (sửa từ codex round 3).

**Finding**:
Full harsh delta = -25.97 nhưng holdout harsh delta = +19.12. Score
decomposition cho thấy cả hai driven by `return_term` (không phải fees hay
penalty terms). Q-VDO-RH gợi ý conditional edge ở một số regime nhưng chưa được
xác lập thống kê. Holdout delta dương là tín hiệu đáng chú ý, nhưng chưa đủ để
bác H0 khi WFO/PSR đều fail. Holdout-WFO overlap 35.3% caveat thêm cho tính
độc lập giữa hai bằng chứng.

WFO pattern hỗ trợ: 3/8 windows dương, khi thắng thì thắng rõ (+80, +47, +29),
khi thua thì thua rất đau (-90, -90). Pattern có cấu trúc nhưng không đủ mạnh
thống kê trên 8 windows.

**Evidence**:
- `validation_report.md:11-15,22-27,38-39`
- `audit_score_decomposition.md:12-17`
- `wfo_summary.json:8-9` (win_rate 0.375, worst -89.684)

---

### Tier 2 — Phát hiện về trade-off structure

#### F-04: Q-VDO-RH chủ yếu là veto/confirmation channel, không phải nguồn cơ hội mới

**Issue IDs**: X34-D-05 (veto composition từ codex round 3)
**Review status**: Converged (round 2)
**Corrections applied**:
- Wording cũ "không phải signal source" bị bác: 71 bars ≠ 0 (47/71 trend_up).
  "Chủ yếu" chính xác hơn absolute statement.
- Thêm veto regime breakdown + asymmetric impact (round 2).

**Finding**:
4,962 bars "VDO yes, Q-VDO no" vs chỉ 71 bars ngược lại (0.38%). Q-VDO-RH chủ
yếu hoạt động như veto/confirmation channel hơn là nguồn cơ hội mới.

Veto là **broad-based**, không chỉ lọc noise regime:
- High-vol 2,512 / Low-vol 2,450 (~50/50)
- Trend-up 2,590 / Trend-down 2,372 (~52/48)

Breakdown bác narrative "Q-VDO-RH chỉ cắt rác" — nó cắt đều trên mọi state.

**Asymmetric impact**: Veto uniform nhưng opportunity cost bất đối xứng theo
regime (`regime_trade_summary.csv`):
- Bull PnL: 57.3k (Q-VDO) vs 109.7k (VDO) — mất 48% bull alpha
- Chop PnL: 54.8k vs 93.1k — mất 41%
- Bear PnL: 28.2k vs 24.6k — Q-VDO thắng +15%

Filter không biased theo regime, nhưng **impact** regime-dependent: bars bị
chặn ở bull/chop chứa alpha cao hơn bars bị chặn ở bear. Uniform selectivity ×
asymmetric opportunity cost = net alpha destruction. Nối trực tiếp F-04 → F-05.

**Evidence**:
- `diagnostic_results.json:31-48` (divergence breakdown)
- `regime_trade_summary.csv:2-13` (PnL by regime)

---

#### F-05: Regime trade-off rất rõ — phòng thủ chop/topping, mất alpha bull

**Issue IDs**: X34-D-08 (judgment call: keep/drop X16/X17 ref)
**Review status**: Judgment call (round 2)

**NOTE (Judgment call, round 2)**: Cross-reference X16/X17 — tradeoff biên tập.
- Bỏ cross-ref: dossier self-contained, reader không cần X16/X17 background
  (stateful exit, WATCH state machine — rất khác scope).
- Giữ cross-ref: X34 nằm rõ hơn trong project-wide pattern (regime
  conditioning consistently hurts).
- Không evidence mới phá tradeoff. Decision owner: **user**

**Finding**:
WFO window-by-window:

| Window | Period | Baseline Sh | Delta | Winner |
|--------|--------|------------|-------|--------|
| 0 | 2022-H1 | -0.62 | +80.4 | Q-VDO |
| 2 | 2023-H1 | 0.65 | +46.7 | Q-VDO |
| 6 | 2025-H1 | 0.59 | +29.3 | Q-VDO |
| 3 | 2023-H2 | 2.21 | -89.6 | VDO |
| 5 | 2024-H2 | 2.13 | -89.7 | VDO |

Hai lần thua -89.x gần như identical — pattern có cấu trúc.

Regime decomposition (analytical) hỗ trợ:
- CHOP: candidate Sh 1.73 vs baseline 1.58 (candidate tốt hơn)
- TOPPING: candidate Sh -0.42 vs baseline -0.87 (candidate tốt hơn)
- BULL: candidate Sh 1.50 vs baseline 1.71 (candidate tệ hơn)
- BEAR: candidate Sh 1.46 vs baseline 1.51 (candidate tệ hơn nhẹ)

Trade-level regime PnL:
- Bear PnL: 28.2k (Q-VDO) vs 24.6k (VDO) — Q-VDO tốt hơn
- Bull PnL: 57.3k vs 109.7k — Q-VDO mất gần nửa alpha
- Chop PnL: 54.8k vs 93.1k — Q-VDO mất đáng kể

NOTE: Hai view (WFO vs analytical regime) cho kết quả complementary nhưng không
identical, vì WFO windows là calendar-based còn regime decomposition là
state-based.

**Evidence**:
- `wfo_summary.json` (8 windows)
- `regime_decomposition.csv` (6 regimes × 2 labels)
- `regime_trade_summary.csv` (PnL by regime)

---

#### F-06: Trade structure bị rewrite sâu, không phải "siết nhẹ"

**Issue IDs**: (none — uncontested)
**Review status**: Uncontested

**Finding**:
Match rate chỉ 44.16% (68 matched / 192 baseline / 154 candidate). Ngay cả
trên 68 matched trades, candidate vẫn kém: mean delta PnL = -942.6, median
delta PnL = -77.3. Win rate delta = -1.5pp (52.9% vs 54.4%).

Vấn đề không chỉ ở trades bị bỏ lỡ (124 baseline-only) — cả trades giữ lại
cũng không cải thiện. Entry timing bị thay đổi bởi Q-VDO-RH threshold khiến
trade trajectory khác.

**Evidence**:
- `trade_level_summary.json:5-16`
- `trade_level_analysis.md:8-16`

---

#### F-07: Avg win giảm 30% nhưng profit factor tăng — nhất quán với fat-tail cutting

**Issue IDs**: X34-D-10 (win rate thiếu sót), attribution caveat từ debate
**Review status**: Converged (round 2, D-10 added round 3)
**Corrections applied**:
- Wording cũ "fat-tail cutting trực tiếp" bị bác: X34 không có per-trade tail
  contribution analysis. Prior knowledge (top 5% = 129.5% of profits) là
  cross-study inference, không phải X34 proof. Sửa: "nhất quán với hiện tượng."
- Thêm win rate observation (D-10, round 2).

**Finding**:
- Avg win: 7,461 → 5,257 (-29.5%)
- Avg loss: 3,096 → 2,347 (-24.2%)
- Profit factor: 1.614 → 1.636 (+0.022)
- Win rate: +2.1pp (42.21% vs 40.10%): net 12 fewer wins, 26 fewer losses
  (`full_backtest_detail.json` harsh). Upside compression (29.5%) vượt
  downside compression (24.2%) — win rate improvement không bù được
  magnitude loss.

Q-VDO-RH cải thiện quality ratio nhưng phá hủy absolute returns — nhất quán với
hiện tượng cắt fat-tail winners, nhưng chưa có attribution study riêng trong
X34 để xác nhận trực tiếp.

**Evidence**:
- `full_backtest_detail.json` (trade statistics, win_rate_pct)

---

#### F-08: "Trade ít hơn" ≠ "risk path mượt hơn" — risk dồn vào ít episode hơn

**Issue IDs**: X34-D-06 (risk concentration từ codex round 3)
**Review status**: Converged (round 2)

**Finding**:
- DD episodes: 17 vs 28 (ít hơn)
- Worst DD: 45.0% vs 41.6% (sâu hơn)
- Mean DD: 18.0% vs 14.3% (nặng hơn)

Fewer trades concentrates risk thay vì giảm risk.

**Nuance bổ sung**:
Buy fills per episode: candidate 8.94 vs baseline 6.82 (+2.12). Q-VDO-RH không
đơn giản giảm rủi ro bằng trade ít hơn; nó dồn rủi ro vào ít campaign hơn
nhưng đậm đặc hơn. Metric này gợi ý cơ chế cho việc episode count giảm mà DD
severity tăng.

**Evidence**:
- `dd_episodes_summary.json`
- `trade_level_summary.json:26-28` (buy_fills_per_episode)

---

#### F-09: Q-VDO-RH giảm churn và cost sensitivity, nhưng gross alpha mất lớn hơn cost savings

**Issue IDs**: X34-D-07
**Review status**: Converged (claude_code round 2)

**Finding**:
Cost sweep cho thấy candidate ít nhạy phí hơn baseline:
- slope 0-50 bps: candidate -0.91 vs baseline -1.15
- Fee drag (harsh): 5.71% vs 6.34%
- Total fees (harsh): $31,418 vs $58,986 (tiết kiệm $27,568, ~47%)
- Crossover: ~75 bps (candidate score 27.87 ≈ baseline 27.72)

Nhưng gross alpha mất lớn hơn: tại 0 bps, candidate score 94.27 vs baseline
111.01 (gap = 16.74 points). Audit score decomposition xác nhận: full-sample
thua chủ yếu do `return_term` (-23.13 ở harsh), không phải cost terms.

Tại measured RT cost 16.8 bps (X33, `cost_summary.md` §3, median over 372
signals, $10k size), trade-off không có lợi. Crossover ~75 bps >> realistic cost.

**Evidence**:
- `cost_sweep.csv`
- `audit_score_decomposition.md:12`
- `quality_checks.md:38-41` (slope comparison)
- `churn_metrics.csv` (fee_drag comparison)
- `research/x33/results/cost_summary.md:27` (measured cost anchor)

---

### Tier 3 — Phát hiện kỹ thuật và phương pháp

#### F-10: Diagnostic GO nhưng strategy validation REJECT — signal-space promise không chuyển thành strategy-level alpha

**Issue IDs**: X34-D-04 (codex round 3)
**Review status**: Converged (round 3)
**Corrections applied**:
- Giữ nguyên wording "Đây không phải chi tiết nhỏ — nó là bài học phương pháp."
- Steel-man mạnh nhất (framework-based): GO chỉ cần ρ ≤ 0.95 (`branches/a_diagnostic/PLAN.md:37-44`),
  bar rất thấp → GO → REJECT là anticipated path → overstate salience.
- Lý do bác bỏ: anticipated path ≠ trivial outcome. X34 data cụ thể (ρ=0.887,
  selectivity 2x, range +68%) cho thấy failure despite genuine signal improvements
  — vivid illustration of known principle = valid methodological finding.
- Codex round 3 precision: diagnostic cũng có frequency flag 0.4774 < 50%
  (`diagnostic_results.json:15,49-51`), nên "mọi signal metric đều positive"
  là overclaim. Finding đúng mức: "nhiều đặc tính signal-space hấp dẫn."

**Finding**:
Phase 2 diagnostic trả về GO:
- Spearman ρ = 0.887 (high correlation)
- Selectivity cao hơn (4,477 vs 9,378 triggers)
- Momentum tail dài hơn (max 0.287 vs 0.171)
- FLAG: trigger frequency ratio 0.4774 (< 50% threshold, `PLAN.md:185-186`)

Nhưng Phase 3 full validation trả về REJECT (exit 2).

Đây không phải chi tiết nhỏ — nó là bài học phương pháp: indicator với nhiều
đặc tính signal-space hấp dẫn (sharper, more selective, wider dynamic range) —
dù đã có frequency flag — không đủ nếu trade-level alpha và OOS robustness
không đi cùng. Signal-space improvement ≠ strategy-space improvement.

**Evidence**:
- `diagnostic_results.json:49` (verdict: GO)
- `diagnostic_results.json:9,13` (ρ, trigger counts)
- `validation_report.md:11` (Decision: REJECT)

---

#### F-11: Adaptive θ có vẻ hấp thụ lợi thế magnitude, nhưng effect chính không nằm ở θ

**Issue IDs**: (softened từ debate rounds 1-2)
**Review status**: Resolved by c_ablation
**Corrections applied**:
- Wording cũ "triệt tiêu lợi thế magnitude" bị bác đúng ở thời điểm pre-ablation.
- Sau c_ablation, A5 vs E0 = `-0.0101 Sharpe` (≈), nên effect chính không nằm ở
  adaptive `θ`; full variant thua chủ yếu vì normalized input.

**Finding**:
Histogram xác nhận Q-VDO-RH momentum có đuôi dương dài hơn VDO (max 0.287 vs
0.171). Nhưng θ evolution cho thấy threshold nén mạnh 2022-2023 rồi nở 2024-2026
— adaptive θ có vẻ hấp thụ phần lớn lợi thế magnitude quan sát được.

Phase 1 unit test cho thấy constant 80% buy pressure → m ≈ 0 → θ blocks entry.
Mechanism này có thật, nhưng c_ablation cho thấy nó không phải nguồn hại chính ở
strategy-space: A5 hồi gần về E0, trong khi full Q-VDO-RH thua xa cả hai.

**Evidence**:
- `diagnostic_results.json:16-29` (distribution stats)
- `research/x34/branches/a_diagnostic/figures/` (histogram, θ evolution plots)
- `research/x34/shared/tests/test_q_vdo_rh.py` (constant_buy_zero_momentum)
- `research/x34/branches/c_ablation/results/attribution_matrix.md`

---

#### F-12: c_ablation resolved input-vs-threshold question

**Issue IDs**: (softened từ debate rounds 1-2)
**Review status**: Resolved
**Corrections applied**:
- Wording cũ "θ là nghi phạm mạnh nhất nhưng chưa chứng minh" chỉ đúng ở trạng
  thái pre-ablation. c_ablation nay đã cho causal readout.

**Finding**:
`c_ablation` đã chạy A3 và A5 trên cùng evaluation region với E0 và full
Q-VDO-RH. Kết quả:
- A5 vs full = `+0.1045 Sharpe` (`>>`)
- A3 vs full = `+0.1065 Sharpe` (`>>`)
- A5 vs E0 = `-0.0101 Sharpe` (`≈`)
- A3 vs E0 = `-0.0081 Sharpe` (`≈`)

Kết luận: full Q-VDO-RH thua chủ yếu vì quote-notional normalized input
`x_t = delta / EMA(quote_volume, slow)`. Adaptive threshold `θ` không tạo thêm
value, nhưng cũng không phải nguồn hại chính trong ablation này. A3/A5 chỉ gỡ
hại và hồi gần về E0; chúng không vượt baseline, nên toàn bộ Q-VDO-RH family
được đóng.

**Evidence**:
- `branches/c_ablation/PLAN.md`
- `branches/c_ablation/results/attribution_matrix.md`

---

#### F-13: Infrastructure gap — CSV có quote_volume và taker_buy_quote_vol nhưng pipeline drop

**Issue IDs**: (none — uncontested)
**Review status**: Uncontested

**Finding**:
Phase 0 phát hiện `Bar` dataclass và `_row_to_bar()` không load `quote_volume`
và `taker_buy_quote_vol` từ CSV dù data có sẵn. Phải vá trước khi bắt đầu
research. Phát hiện kỹ thuật có giá trị vượt X34 — bất kỳ nghiên cứu tương lai
nào dùng quote-notional data đều cần bước này.

**Evidence**:
- `v10/core/types.py` (added fields with defaults)
- `v10/core/data.py` (`_row_to_bar` patched with `.get()` fallback)

---

#### F-14: Mode B deferred đúng — hygiene tốt

**Issue IDs**: (none — uncontested)
**Review status**: Uncontested

**Finding**:
Spec chưa đóng băng F (Student-t vs empirical CDF), gamma, de-rate rule. Quyết
định không encode vào `shared/` để tránh "false authority" là phương pháp đúng.

**Evidence**:
- `research/x34/resource/Q-VDO-RH_danh-gia-va-ket-luan.md` (§7, open parameters)

---

#### F-15: Exposure giảm nhưng không convert thành alpha trong framework hiện tại

**Issue IDs**: (none — uncontested)
**Review status**: Uncontested

**Finding**:
Avg exposure: 46.8% → 40.1% (-6.7pp). Trades: 192 → 154 (-20%). Avg hold bars:
38.2 → 40.8 (+2.6 bars). Q-VDO-RH có ít time-in-market hơn nhưng mỗi trade giữ
hơi lâu hơn. Nếu cash nhàn rỗi có thể earn yield (staking, T-bills), exposure
thấp hơn có giá trị. Nhưng trong backtest framework hiện tại, cash = 0% return →
exposure thấp = wasted capital.

**Evidence**:
- `full_backtest_detail.json` (exposure metrics)
- `churn_metrics.csv` (avg_hold_bars: 40.78 vs 38.16)

---

## Meta-insight

**Issue IDs**: X34-D-09
**Review status**: Converged (round 2). Sửa causal overclaim "vì" → "nhất quán với".

Trên BTC spot trend-following, chỉ cần biết flow momentum đang dương (bất kỳ
magnitude) là đủ. Yêu cầu momentum phải vượt adaptive noise floor (`> θ`) là
over-filtering — kết quả nhất quán với hiện tượng cắt fat-tail winners (xem
F-07). X34 chưa có per-trade tail attribution.

VDO threshold = 0.0 (tối thiểu) là optimal. Bất kỳ threshold dương nào — dù
fixed hay adaptive — đều là regime-conditional tradeoff, không phải universal
improvement. X34 reinforce nguyên lý này bằng evidence mới (Q-VDO-RH) trên
evidence đã có (VDO E5 threshold sweep).

---

## Issue Index (ánh xạ từ debate system)

| Issue ID | Finding IDs | Topic | Status | Resolved in |
|----------|------------|-------|--------|-------------|
| X34-D-01 | F-01 | Wording + semantic framing | Converged | prior rounds |
| X34-D-02 | F-03 | "Not noise" overclaim | Converged | prior rounds |
| X34-D-03 | F-02 | Verdict scope + tier placement | Judgment call | round 2 |
| X34-D-04 | F-10 | Diagnostic GO vs REJECT framing | Converged | round 3 |
| X34-D-05 | F-04 | Veto breakdown + asymmetric impact | Converged | round 2 |
| X34-D-06 | F-08 | Risk concentration placement | Converged | round 2 |
| X34-D-07 | F-09 | Cost/alpha tradeoff | Converged | prior rounds |
| X34-D-08 | F-05 | Cross-reference X16/X17 | Judgment call | round 2 |
| X34-D-09 | Meta-insight | Causal overclaim → minimal fix | Converged | round 2 |
| X34-D-10 | F-07 | Win rate observation added | Converged | round 2 |

---

## Codex Issue Details (restored from codex round 3)

Phần này giữ nguyên lập luận chi tiết của codex cho các issues mở.
Claude_code không được phép xóa hoặc sửa nội dung phần này.

### X34-D-01

- Topic: Item 1 wording + semantic framing của operator
- Opened in round: `1`
- Initial claim:
  `Entry logic chuyển từ positive flow sang accelerating flow`
- Current concern:
  wording này dễ mô tả sai cả baseline lẫn Q-VDO-RH vì baseline VDO cũng là
  oscillator `EMA(vdr, fast) - EMA(vdr, slow)`, còn Q-VDO-RH lại tách rõ
  `momentum` và `level`
- Semantic details cần giữ lại:
  - Với Q-VDO-RH, `m_t = EMA(x, fast) - EMA(x, slow)` đo CHANGE của normalized
    flow, không đo mức flow tĩnh
  - `l_t = EMA(x, slow)` mới mang thông tin level / regime tĩnh
  - Trường hợp "buy pressure ổn định 80% nhưng không tăng thêm" cho `m ≈ 0` là
    hành vi đúng theo thiết kế, không phải bug
  - Vì vậy, không nên mô tả shift này như thể baseline đo `pressure level` còn
    Q-VDO-RH đo `acceleration`; baseline VDO cũng là oscillator
- Safer wording đang được ưu tiên:
  `entry logic chuyển từ positive momentum of bounded/raw flow sang positive
  momentum of volume-normalized flow vượt adaptive noise floor`
- Evidence pointers:
  - `research/x34/resource/Q-VDO-RH_danh-gia-va-ket-luan.md` §5.4, §7.1
  - `research/x34/shared/indicators/q_vdo_rh.py`
  - `research/x34/shared/tests/test_q_vdo_rh.py` (`constant_buy_zero_momentum`)
- Current status: `Converged` (mapped to F-01)
- Latest artifact: [round-3_reviewer-reply](codex/2026-03-13/round-3_reviewer-reply.md)

### X34-D-02

- Topic: Item 3 overclaim về `not noise`
- Opened in round: `1`
- Initial claim:
  `Nghịch lý full-sample thua / holdout thắng: đây không phải noise`
- Current resolution:
  thay bằng `gợi ý conditional edge nhưng chưa được xác lập thống kê`
- Codex round 3 sửa quan trọng: overlap `35.3%` không chứng minh holdout
  delta bị inflated. Nó chỉ làm yếu tính độc lập nếu định dùng holdout và WFO
  như hai bằng chứng xác nhận tách biệt.
- Current status: `Converged` (mapped to F-03)
- Latest artifact: [round-3_reviewer-reply](codex/2026-03-13/round-3_reviewer-reply.md)

### X34-D-03

- Topic: Scope của verdict `x34`
- Opened in round: `3`
- Initial omission:
  danh sách chưa nói rõ `x34` chỉ validate Option A entry-only
- Current concern:
  nếu không thêm caveat này, reader dễ overgeneralize rằng `x34` bác toàn bộ
  hướng quote-notional flow
- Scope details cần ghi rõ:
  - Spec nói `L` không nên làm hard gate ở v1; nó chỉ nên là `context /
    confidence`, còn trigger chính do momentum đảm nhiệm
  - Variant đã test trong `x34` là Option A entry-only:
    `trend_up AND qvdo_momentum > qvdo_theta`
  - `level` không được dùng làm cổng lọc trong backtest của variant bị reject
  - Vì vậy, verdict hiện tại chủ yếu bác một variant hẹp hơn:
    `trend + momentum(normalized flow) > adaptive theta`, chứ chưa bác toàn bộ
    hướng `quote-notional flow + level-context`
  - Hệ quả diễn giải: nhiều bar `VDO yes / Q-VDO no` không chỉ do threshold, mà
    còn do Q-VDO-RH cố ý không phản ứng với positive pressure dương nhưng đứng yên
- Evidence pointers:
  - `research/x34/resource/Q-VDO-RH_danh-gia-va-ket-luan.md` §5.4, §7.1
  - `research/x34/branches/b_e0_entry/PLAN.md` (`Option A`)
- Current status: `Judgment call` (mapped to F-02)
- Latest artifact: [round-3_reviewer-reply](codex/2026-03-13/round-3_reviewer-reply.md)

### X34-D-04

- Topic: Diagnostic `GO` vs validation `REJECT`
- Opened in round: `3`
- Initial omission:
  danh sách chưa coi contrast này là một finding phương pháp
- Current concern:
  signal-space improvement không tự động chuyển thành strategy-level alpha
- Steel-man cho việc không cần thêm:
  diagnostic chỉ là prefilter nội bộ, không phải kết luận khoa học; không cần
  nâng nó lên thành finding
- Lý do bác bỏ (codex round 3):
  chính vì diagnostic là prefilter nên contrast giữa `GO` ở signal-space và
  `REJECT` ở strategy-space mới có giá trị. Nó nhắc rằng:
  - `spearman 0.8866`
  - selectivity cao hơn (`4477` vs `9378`)
  - tail dương dài hơn trong histogram
  vẫn không đủ nếu trade-level alpha và OOS robustness không đi cùng.
- Evidence pointers:
  - `research/x34/branches/a_diagnostic/results/diagnostic_results.json:9,13,49`
  - `research/x34/branches/b_e0_entry/results/validation/reports/validation_report.md:11`
- Current status: `Converged` (mapped to F-10)
- Latest artifact: [round-3_reviewer-reply](codex/2026-03-13/round-3_reviewer-reply.md)

### X34-D-05

- Topic: Veto broad-based
- Opened in round: `3`
- Initial omission:
  danh sách có `4962 vs 71` nhưng chưa có composition theo `high/low vol`,
  `trend up/down`
- Current concern:
  nếu không có breakdown này, người đọc có thể hiểu nhầm rằng filter chỉ cắt
  noise regime
- Steel-man cho việc không cần thêm:
  asymmetry `4962 vs 71` đã đủ để kết luận "veto machine"; breakdown theo regime
  chỉ là chi tiết phụ
- Lý do bác bỏ (codex round 3):
  không phải chi tiết phụ. Nếu blocked bars tập trung gần hết ở `low_vol` hoặc
  `trend_down`, ta có thể nói filter chủ yếu loại noise. Nhưng dữ liệu không cho
  phép diễn giải đó. Breakdown hiện tại nói điều ngược lại: veto là broad-based,
  không chỉ nhắm vào low-quality regime. Đây là insight quan trọng vì nó hỗ trợ
  trực tiếp cho finding "mất alpha bull/chop" và giúp bác narrative "chỉ cắt rác".
- Evidence pointers:
  - `research/x34/branches/a_diagnostic/results/diagnostic_results.json:31`
- Current status: `Converged` (mapped to F-04)
- Latest artifact: [round-3_reviewer-reply](codex/2026-03-13/round-3_reviewer-reply.md)

### X34-D-06

- Topic: Risk concentration per episode
- Opened in round: `3`
- Initial omission:
  danh sách chưa dùng `buy_fills_per_episode` để giải thích cơ chế dồn rủi ro
- Current concern:
  đây là nuance bổ sung cho finding `fewer trades != smoother risk path`
- Steel-man cho việc không cần thêm:
  worst DD và mean DD đã đủ mạnh, metric này chỉ là detail
- Lý do bác bỏ (codex round 3):
  đây không chỉ là detail. Nó gợi ý cơ chế: Q-VDO-RH không đơn giản giảm rủi ro
  bằng cách trade ít hơn; nó có thể đang dồn rủi ro vào ít campaign hơn nhưng đậm
  đặc hơn. Nếu muốn giải thích tại sao episode count giảm mà DD severity tăng,
  đây là metric có ý nghĩa cơ chế.
- Priority: `low`
- Evidence pointers:
  - `research/x34/branches/b_e0_entry/results/validation/results/trade_level_summary.json:26`
- Current status: `Converged` (mapped to F-08)
- Latest artifact: [round-3_reviewer-reply](codex/2026-03-13/round-3_reviewer-reply.md)

### X34-D-07

- Topic: Cost/alpha tradeoff
- Opened in round: `1`
- Initial omission:
  danh sách chưa nói rõ candidate giảm churn/cost sensitivity nhưng vẫn thua do
  alpha loss
- Current resolution:
  đã có cả evidence nội bộ từ `x34` và anchor thực tế từ `x33`
- Evidence pointers:
  - `research/x34/branches/b_e0_entry/results/validation/results/cost_sweep.csv:2`
  - `research/x34/branches/b_e0_entry/results/validation/reports/audit_score_decomposition.md:12`
  - `research/x33/results/cost_summary.md:23,27`
- Current status: `Converged` (mapped to F-09)
- Latest artifact: [round-3_reviewer-reply](codex/2026-03-13/round-3_reviewer-reply.md)

### X34-D-08

- Topic: Có nên giữ cross-reference X16/X17 không
- Opened in round: `1`
- Initial claim:
  `Giống X16/X17 đã chứng minh ...`
- Current concern:
  đây là quyết định về scope biên tập, không phải đúng/sai khoa học
- Tradeoff:
  - nếu tài liệu là "findings của X34", bỏ cross-reference là gọn và
    self-contained hơn
  - nếu tài liệu là "X34 trong bức tranh lớn của project", giữ lại cũng hợp lệ
- Current status: `Judgment call` (mapped to F-05)
- Latest artifact: [round-3_reviewer-reply](codex/2026-03-13/round-3_reviewer-reply.md)

---

## Claude_code Issue Details (round 1, phiên mới)

Phần này chứa lập luận chi tiết của claude_code cho các issues mới.
Codex không được phép xóa hoặc sửa nội dung phần này.

### X34-D-09

- Topic: Meta-insight causal overclaim
- Opened in round: `1` (phiên mới)
- Initial claim (trong meta-insight):
  `nó cắt fat-tail winners vì những trade lớn nhất bắt đầu từ flow tăng nhẹ,
  không phải flow tăng mạnh`
- Classification: `Sai khoa học`
- Current concern:
  "vì" là causal claim. X34 không có per-trade tail contribution analysis.
  F-07 corrections đã sửa "fat-tail cutting trực tiếp" thành "nhất quán với
  hiện tượng", nhưng meta-insight lặp lại cùng lỗi mà F-07 đã sửa.
  Prior knowledge (top 5% = 129.5%) đến từ fragility audit, không phải X34.
- Proposed fix:
  Thay causal claim bằng: "nhất quán với hiện tượng cắt fat-tail winners —
  prior research cho thấy top 5% = 129.5% profits. Nhưng X34 chưa có
  per-trade tail attribution." Thêm scope qualifier.
- Evidence pointers:
  - `findings-under-review.md:227-238` (F-07 corrections dùng "nhất quán với")
  - `findings-under-review.md:428` (meta-insight dùng "vì")
  - `full_backtest_detail.json` (không có per-trade breakdown)
  - `memory/fragility_audit.md` (nguồn gốc "top 5% = 129.5%")
- Priority: `high`
- Current status: `Converged`
- Latest artifact: [round-2_reviewer-reply](codex/2026-03-13/round-2_reviewer-reply.md)

### X34-D-10

- Topic: F-07 thiếu win rate observation
- Opened in round: `1` (phiên mới)
- Initial omission:
  F-07 nêu avg_win -29.5%, avg_loss -24.2%, profit factor +0.022, nhưng
  không mention win rate +2.1pp (42.21% vs 40.10%)
- Classification: `Thiếu sót`
- Current concern:
  Win rate improvement là misleading positive — Q-VDO-RH loại losers nhiều
  hơn winners (better win rate) nhưng upside compression > downside
  compression (29.5% vs 24.2%). Không document = reader miss asymmetry.
- Evidence pointers:
  - `full_backtest_detail.json` harsh: candidate `win_rate_pct` 42.21,
    baseline `win_rate_pct` 40.10
- Priority: `normal`
- Current status: `Converged`
- Latest artifact: [round-2_reviewer-reply](codex/2026-03-13/round-2_reviewer-reply.md)

---

## Update Log

| Timestamp (UTC) | Event |
|---|---|
| 2026-03-13T14:26:25Z | Created initial dossier |
| 2026-03-13T14:46:05Z | Expanded X34-D-01 and X34-D-03 semantics |
| 2026-03-13T16:30:00Z | Full consolidation: merged 12 original findings + 4 codex issues + debate corrections + rescan artifacts. Deduplicated, reclassified into 15 findings (F-01 → F-15). Applied all converged corrections from claude_code rounds 1-2. Mapped open codex issues to finding IDs. |
| 2026-03-13T16:45:00Z | Restored codex Issue Details section (X34-D-01 → X34-D-08) that was incorrectly removed during consolidation. Added finding ID mappings to each issue. |
| 2026-03-13T17:30:00Z | Phiên tranh luận mới. claude_code round 1: opened X34-D-09 (meta-insight causal overclaim, Sai khoa học), X34-D-10 (F-07 thiếu win rate, Thiếu sót). Added Claude_code Issue Details section. Updated Issue Index. |
| 2026-03-13T18:10:00Z | **CLOSED.** Applied all converged corrections and judgment call notes. Round 3 final: 8 converged, 2 judgment call. Changes: F-02 → JC note (tier placement, user decides); F-04 → breakdown + asymmetric impact added; F-05 → JC note (cross-ref, user decides); F-07 → win rate +2.1pp added; F-08 → nuance chốt; F-10 → wording kept + frequency flag added; Meta-insight → "vì" replaced with "nhất quán với". |
