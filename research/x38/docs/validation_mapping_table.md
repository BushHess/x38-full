# Validation Mapping Table — btc-spot-dev → Alpha-Lab

**Mục đích**: Pre-debate reference. Map từng component trong `btc-spot-dev/validation/`
và `research/lib/` sang Alpha-Lab: **REUSE** (giữ nguyên hoặc port), **REPLACE** (thay bằng
design mới), **DISCARD** (không cần), hoặc **INTRODUCE** (chưa có trong pipeline, cần thêm).

**Nguyên tắc**: validation/ có **ZERO direct cites** trong x38 evidence list (x38_RULES.md
§7). Nó là **audit target** — cần kiểm tra để biết cái gì reuse được, không phải authority.

**Ngày**: 2026-03-22

> **⚠ SUPERSEDED NOTE (2026-03-24)**: Cluster proposals in §3 (X38-T-13, X38-T-14a/b,
> X38-T-15 with F-30→F-39 numbering) predate the live topic registry in `debate/debate-index.md`.
> The live registry defines: 013 = convergence-analysis, 014 = execution-resilience,
> 015 = artifact-versioning, 016 = bounded-recalibration-path. Use `debate-index.md`
> as the authoritative topic map, not the cluster plan below.

---

## A. VALIDATION/ SUITES — 17 suites, 7 decision gates

### A1. Hard Gates (3 gates trong decision.py, blocking verdict) + Pre-gate Safety (2 ERROR exits)

| # | Suite | File | Chức năng | Verdict | Lý do |
|---|-------|------|-----------|---------|-------|
| 1 | **lookahead** | `suites/lookahead.py` | Auto-discovery pytest: no future data access | **REUSE** | Tier 1 axiom trong cả gen1/gen4/x38. Zero-lookahead là invariant vĩnh viễn. Code pytest-based portable. |
| 2 | **backtest** (full_harsh_delta) | `suites/backtest.py` | Full-period candidate vs baseline, ΔScore ≥ -0.2 | **REPLACE** | Alpha-Lab là multi-candidate discovery, không phải candidate-vs-baseline. Objective function cần debate (Cluster 1a). Threshold 0.2 là UNCALIBRATED. |
| 3 | **holdout** (holdout_harsh_delta) | `suites/holdout.py` | Holdout period candidate vs baseline, ΔScore ≥ -0.2, lock file | **REPLACE** | Gen4/x38 tách rõ internal reserve vs clean OOS. validation/ dùng trailing fraction (20%) của cùng dataset — conflict với temporal seal requirement. Lock file mechanism có thể reuse. |
| 4 | **invariants** | `suites/invariants.py` | 13 logical invariants: exposure bounds, NAV consistency, fill timing, position overlap | **REUSE** | Safety layer orthogonal với performance validation. Event-loop replay catches logic bugs. Gen4 yêu cầu deterministic replay — invariants suite đã implement. |
| 5 | **data_integrity** | `suites/data_integrity.py` | OHLCV sanity: missing bars, price ranges, time gaps | **REUSE** | x38 Stage 2 = data audit. Gen1 V6/V7/V8 patterns match. Code portable, chỉ cần mở rộng anomaly register format. |

### A2. Soft Gates (ảnh hưởng verdict — 3 trong 7 gates của decision.py)

| # | Suite | File | Chức năng | Verdict | Lý do |
|---|-------|------|-----------|---------|-------|
| 6 | **wfo** | `suites/wfo.py` | Sliding WFO + Wilcoxon α=0.10 + iid bootstrap CI | **REPLACE** | 3 conflicts lớn: (a) sliding vs expanding (gen1/gen4 = quarterly expanding), (b) iid bootstrap vs block bootstrap, (c) Wilcoxon không có trong gen1/gen4. Statistical test selection cần debate (Cluster 2a). WFO window generation code có thể reuse nếu refactor sang expanding mode. |
| 7 | **trade_level** | `suites/trade_level.py` | Matched-trade block bootstrap [42,84,168] bars, regime decomposition | **REUSE** (partial) | Trade-level analysis valuable. Block bootstrap implementation reusable. Nhưng authority level (conditional on WFO low-power) cần re-evaluate — Alpha-Lab có thể dùng trade-level như primary evidence, không phải fallback. |
| 8 | **selection_bias** | `suites/selection_bias.py` | PSR diagnostic + DSR advisory + PBO proxy | **REPLACE** | PSR demoted to info (2026-03-16) vì anti-conservative cho paired comparison. PBO proxy (negative_delta_ratio) quá đơn giản — không phải true Bailey et al. 2013. DSR advisory giữ nhưng cần integrate với research/lib/dsr.py (avoid duplicate). Cần debate multi-test correction (Cluster 2c). |

### A3. Info/Diagnostic & Pre-gate Safety (gate #7 bootstrap ở đây; còn lại không ảnh hưởng verdict)

| # | Suite | File | Chức năng | Verdict | Lý do |
|---|-------|------|-----------|---------|-------|
| 9 | **subsampling** | `suites/subsampling.py` | Politis-Romano-Wolf 1999, deterministic, paired block subsampling | **REUSE** | Non-resampling inference complement bootstrap. Deterministic = reproducible. Calibration caveat noted (miscalibrated when near-equal returns). Không nằm trong 7 gates của decision.py — chạy như diagnostic. Cần debate role trong triple inference pattern (Cluster 2a). |
| 10 | **regression_guard** | `suites/regression_guard.py` | Golden baseline comparison, per-metric tolerance | **REUSE** (conditional) | Pre-gate safety: triggers ERROR (exit 3) trong decision.py (line 287-319) nếu golden metrics vi phạm — cứng hơn hard gate (exit 2). Useful cho production monitoring / forward evaluation. Alpha-Lab discovery phase không cần (no golden baseline yet). |
| 11 | **bootstrap** | `suites/bootstrap.py` | Wrapper quanh v10 paired_block_bootstrap, circular block, diagnostic only | **REPLACE** | Wrapper quanh v10/research/bootstrap.py. VCBB (research/lib/vcbb.py) là candidate thay thế mạnh hơn. Authority level cần debate (Cluster 2b). |
| 12 | **regime** | `suites/regime.py` | D1 regime decomposition: BULL/BEAR/CHOPPY per-regime metrics | **REUSE** | Gen4 hard constraint yêu cầu ≥2 distinct regimes trong clean OOS. Regime decomposition code portable. |
| 13 | **cost_sweep** | `suites/cost_sweep.py` | 11 cost scenarios (2-100 bps), breakeven analysis | **REUSE** | X22 study proved cost-dependent decisions critical. Code reusable. Alpha-Lab nên chạy cost sweep như standard diagnostic. |
| 14 | **sensitivity** | `suites/sensitivity.py` | Grid sweep on key params (aggression, trail, exposure cap) | **REUSE** (conditional) | Plateau verification. Gen1 V7 requires plateau check. Alpha-Lab Stage 6 = parameter refinement + plateau. Code reusable nếu param grid configurable. |
| 15 | **dd_episodes** | `suites/dd_episodes.py` | Drawdown episode detection (≥5%), recovery table | **REUSE** | Diagnostic. Gen4 emergency review trigger = MDD > 45%. DD episode detection code reusable. |
| 16 | **overlay** | `suites/overlay.py` | Overlay/cooldown mechanism value comparison | **DISCARD** | Specific to V8/V11/V12 overlay mechanism. Alpha-Lab discovery is mechanism-agnostic — overlay is a candidate feature, not a validation layer. |
| 17 | **churn_metrics** | `suites/churn_metrics.py` | Trade churn diagnostics | **DISCARD** | Specific to X12-X19 churn research series. Alpha-Lab discovery generates candidates without assuming churn is relevant. |

### A4. Core Infrastructure

| # | Component | File | Chức năng | Verdict | Lý do |
|---|-----------|------|-----------|---------|-------|
| 18 | **decision.py** | `decision.py` | 7-gate verdict logic: hard/soft/info → PROMOTE/HOLD/REJECT/ERROR | **REPLACE** | Core verdict engine. Architecture reusable (gate severity model) nhưng: (a) gate inventory thay đổi (Cluster 1b), (b) holdout/WFO overlap downgrade logic specific to current pipeline, (c) verdict vocabulary cần reform. |
| 19 | **thresholds.py** | `thresholds.py` | Authority-bearing constants with provenance tags | **REUSE** (pattern) | Provenance tagging pattern (STAT/LIT/CONV/UNPROVEN) excellent — port sang Alpha-Lab. Actual values cần re-calibrate. 3/8 constants marked UNCALIBRATED hoặc UNPROVEN. |
| 20 | **runner.py** | `runner.py` | Suite orchestrator, suite groups (basic/full/all), execution order | **REPLACE** | Alpha-Lab có 8-stage protocol engine (x38 F-05). runner.py = flat suite list. Protocol engine = staged pipeline với phase gating. Different architecture. |
| 21 | **strategy_factory.py** | `strategy_factory.py` | Static STRATEGY_REGISTRY dict, no plugin mechanism | **REPLACE** | Alpha-Lab dùng candidate registry (dynamic, per-campaign). Static dict không scale cho multi-candidate discovery. |
| 22 | **config.py** | `config.py` | ValidationConfig dataclass, suite groups, suite order | **REPLACE** | Coupled với runner.py. Alpha-Lab cần protocol-level config (per-stage), không phải flat suite config. |

---

## B. RESEARCH/LIB/ — 4 libraries hiện tại

### B1. Candidate Techniques (introduce vào debate)

| # | Library | File | Chức năng | Verdict | Lý do |
|---|---------|------|-----------|---------|-------|
| 1 | **VCBB** | `research/lib/vcbb.py` | Vol-conditioned block bootstrap. KNN matching preserves vol clustering across blocks. 5-channel OHLCV path reconstruction. | **INTRODUCE** (Cluster 2b) | Methodologically strongest bootstrap. Addresses 84% vol clustering destruction by uniform block. Allows re-backtest on synthetic OHLCV paths (honest for strategy signals depending on H/L/V). Currently orphaned — zero references in validation/, gen4, x38. Used in 30+ research scripts. |
| 2 | **DSR** | `research/lib/dsr.py` | Deflated Sharpe Ratio (Bailey & López de Prado 2014) + PSR. Selection bias correction for multiple testing. | **INTRODUCE** (Cluster 2c) | Multi-test correction mandatory for multi-candidate Alpha-Lab. Duplicate exists in validation/lib/dsr.py (daily convention) — need reconcile. research/lib version uses per-bar, validation/ uses daily → different moment denominators. |
| 3 | **Effective DOF** | `research/lib/effective_dof.py` | Nyholt/Li-Ji/Galwey M_eff. Corrects binomial p-values for correlated tests (e.g., 16 timescales with ρ>0.8). | **INTRODUCE** (Cluster 2c) | Essential for cross-timescale claims. M_eff ≈ 4.35 (not 16) for BTC H4 timescales. Currently research-only. Alpha-Lab will generate multi-timescale results → DOF correction required. |
| 4 | **Pair Diagnostic** | `research/lib/pair_diagnostic.py` | Automated pair comparison: tolerance profile → 3-tier classification → bootstrap + subsampling + consensus → caveat generation → markdown review template. 613 lines. | **INTRODUCE** (Cluster 2e) | Complete comparison framework with NO decision authority (by design). Implements triple inference + consensus check. Could serve as Alpha-Lab's standard pair comparison tool. Currently research-only with test coverage (18+ tests). |

---

## C. V10/RESEARCH/ — Bootstrap implementation

| # | Component | File | Chức năng | Verdict | Lý do |
|---|-----------|------|-----------|---------|-------|
| 1 | **block_bootstrap** | `v10/research/bootstrap.py` | Circular block bootstrap (Politis & Romano 1994). Unpaired + paired. ddof=0, annualize sqrt(2190). | **KEEP** (as dependency) | v10 is FROZEN. validation/suites/bootstrap.py wraps this. VCBB may supersede for BTC, but v10 code stays as-is. |

---

## D. CONFLICT MATRIX — Per Decision Function

### D1. Ranking & Objective (Cluster 1a)

| Dimension | validation/ | Gen1 (V7/V8) | Gen4 | Conflict? |
|-----------|------------|---------------|------|-----------|
| **Ranking metric** | Composite score: 2.5×CAGR - 0.6×MDD + 8×Sh + 5×PF + 5×trades | Pass/fail gates, no ranking | Calmar_50bps - complexity_penalty | **YES** — 3 khác nhau |
| **Complexity penalty** | Không có | Không có | 0.02/layer + 0.03/tunable | **YES** — chỉ gen4 |
| **Max layers** | Không giới hạn | Không giới hạn | Hard cap 3 | **YES** — chỉ gen4 |
| **Max tunables** | Không giới hạn | Không giới hạn | Hard cap 4 | **YES** — chỉ gen4 |
| **Min trades** | Reject < 10 (objective sentinel) | ≥ 20 trade_count_entries | Entries/year ∈ [6, 80] | **YES** — 3 thresholds khác nhau |

### D2. Hard Gates (Cluster 1b)

| Gate | validation/ | Gen1 | Gen4 | Conflict? |
|------|------------|------|------|-----------|
| **MDD** | Không có absolute gate | Không có | ≤ 0.45 (hard) | **YES** — chỉ gen4 |
| **CAGR** | Không có (chỉ delta) | Positive edge after 20bps | > 0 (hard) | **YES** — gen1/gen4 yêu cầu, validation/ không |
| **Exposure** | Không có | Không có | ∈ [0.15, 0.90] (hard) | **YES** — chỉ gen4 |
| **Entries/year** | Reject < 10 | ≥ 20 entries total | ∈ [6, 80] (hard) | **YES** — 3 thresholds |
| **Bootstrap LB5** | Info only | Không có | > 0 (hard) | **YES** — gen4 = hard, validation/ = info |
| **Lookahead** | Hard gate (pytest) | Required (no test suite) | Tier 1 axiom | Agreement — all require |
| **Fold positive fraction** | Advisory 60% (UNPROVEN) | ≥ 50% of 14 folds | Không explicit | Partial conflict |
| **Isolation concentration** | Không có | ≤ 0.65 | Không có | **YES** — chỉ gen1 |
| **Ablation** | Không có | Không có | Formal per-layer ablation | **YES** — chỉ gen4 |

### D3. Statistical Inference (Cluster 2a)

| Test | validation/ | Gen1 | Gen4 | Conflict? |
|------|------------|------|------|-----------|
| **Wilcoxon signed-rank** | Primary (α=0.10, one-sided) | Không có | Không có | **YES** — chỉ validation/ |
| **Paired bootstrap** | iid percentile CI (10k resamples) | Moving block, paired (1-2k) | Moving block, common indices (3k) | **YES** — 3 methods |
| **Block sizes** | N/A (iid) | [5,10,20,40] days | [5,10,20] days | **YES** — gen1 ≠ gen4 |
| **Bootstrap authority** | Soft gate (WFO CI) / info (suite) | Diagnostic | Hard gate (LB5 > 0) | **YES** — 3 levels |
| **Subsampling** | Implemented, diagnostic | Không có | Không có | Unique to validation/ |
| **PSR** | Info (demoted 2026-03-16) | Used in early versions | Không có | Partially resolved |
| **DSR** | Advisory at trial levels | Không có | Không có | Unique to validation/ |
| **DOF correction** | Không có | Không có | Không có | **GAP** — research/lib only |
| **VCBB** | Không có | Không có | Không có | **GAP** — research/lib only |

### D4. WFO & Data Splits (Cluster 3a)

| Dimension | validation/ | Gen1 (V7/V8) | Gen4 | Conflict? |
|-----------|------------|---------------|------|-----------|
| **WFO mode** | Sliding (configurable) | 14 quarterly, expanding | 14 quarterly, expanding | **YES** — sliding vs expanding |
| **Fold count** | Configurable (typically 8) | 14 fixed | 14 fixed | **YES** |
| **Test period** | Configurable (1-3 months) | 3 months (quarterly) | 3 months (quarterly) | Mild conflict |
| **Training** | Fixed window (slide) | Anchored start (expand) | Anchored start (expand) | **YES** — fundamental |
| **Holdout** | Trailing fraction (20%) of same data | Separate period (2024-01→2026-02) | 2023-07→2024-09 (15 months) | **YES** — fraction vs fixed |
| **Clean OOS** | Không có concept | Không explicit | Evidence after freeze_cutoff_utc | **YES** — chỉ gen4 |
| **Holdout/WFO overlap** | Detected, downgrade if >50% | Prevented by temporal seal | Prevented by design | **YES** — workaround vs prevention |

### D5. Threshold Governance (Cluster 2d)

| Constant | validation/ provenance | Gen1 | Gen4 | Status |
|----------|----------------------|------|------|--------|
| HARSH_SCORE_TOLERANCE = 0.2 | **UNCALIBRATED** | Không có | Không có | Needs calibration or replacement |
| WFO_WIN_RATE = 0.60 | **UNPROVEN** | ≥ 50% of 14 folds | Không explicit | Needs decision |
| WFO_SMALL_SAMPLE_CUTOFF = 5 | **UNPROVEN** | 14 folds (no small sample) | 14 folds | Artifact of sliding WFO |
| WFO_WILCOXON_ALPHA = 0.10 | STAT (exact Wilcoxon) | Không có (no Wilcoxon) | Không có | Needs debate if Wilcoxon kept |
| WFO_BOOTSTRAP_RESAMPLES = 10000 | STAT (Efron 1993) | 1000-2000 | 3000 | **YES** — 3 values |
| PSR_THRESHOLD = 0.95 | LIT (Bailey 2012), demoted | Used in early versions | Không có | Resolved (info only) |

---

## E. ĐỀ XUẤT DEBATE CLUSTERS

Dựa trên conflict matrix, đề xuất 3 clusters mới bổ sung vào x38 debate:

### Cluster 1 → Topic X38-T-13: Candidate Ranking & Gate Inventory

**Findings mới** (derived từ mapping table):
- **F-30**: Ranking metric conflict — 3 incompatible objectives (composite score vs Calmar+penalty vs gates-only)
- **F-31**: Hard gate inventory conflict — gen4 có 5 absolute gates mà validation/ thiếu hoàn toàn
- **F-32**: Complexity penalty — gen4 only, chưa validated empirically

**Sub-sessions**: 1a (ranking metric), 1b (gate inventory)
**Wave**: 2 (sau topic 007)
**Dependencies**: 007 (philosophy — defines what "good" means)

### Cluster 2 → Topics X38-T-14a + X38-T-14b: Statistical Validation Framework

**Findings mới**:
- **F-33**: Triple inference pattern exists (Wilcoxon + Bootstrap + Subsampling) nhưng không được recognized — cần decide keep all 3 or simplify
- **F-34**: Bootstrap methodology conflict — 4 distinct methods (iid, circular block, moving block, VCBB), mỗi cái có properties khác nhau
- **F-35**: VCBB orphaned — methodologically strongest nhưng zero pipeline integration
- **F-36**: Multi-test correction gap — DOF correction (M_eff) và DSR chỉ trong research/lib, không trong validation gates
- **F-37**: Threshold governance — 3/8 validation/ constants marked UNCALIBRATED/UNPROVEN. x38 yêu cầu pre-registered thresholds

**Sub-sessions**: 2a (test selection), 2b (bootstrap method + VCBB), 2c (DOF + DSR), 2d (threshold governance), 2e (pair diagnostic integration)
**Split**: 14a = {2a, 2c, 2d} (inference framework), 14b = {2b, 2e} (resampling + comparison)
**Wave**: 2 (sau topic 007, song song với 013)
**Dependencies**: 007 (philosophy)

### Cluster 3 → Topic X38-T-15: WFO & Holdout Architecture

**Findings mới**:
- **F-38**: WFO mode conflict — sliding (validation/) vs quarterly expanding (gen1/gen4). Fundamental architectural choice.
- **F-39**: Holdout semantics conflict — trailing fraction (validation/) vs fixed temporal seal (gen1/gen4) vs clean-OOS-after-freeze (gen4/x38)

**Sub-sessions**: 3a (WFO architecture), 3b (fold into topic 010 for Clean OOS power rules)
**Wave**: 2 (song song, soft-dep on 010)
**Dependencies**: 007, 013 (gate inventory), 014a (test selection → power requirements)

---

## F. REUSE SUMMARY

| Category | REUSE | REPLACE | DISCARD | INTRODUCE |
|----------|-------|---------|---------|-----------|
| Hard gates (5) | 3 (lookahead, invariants, data_integrity) | 2 (backtest, holdout) | 0 | 0 |
| Soft gates (3) | 1 (trade_level partial) | 2 (wfo, selection_bias) | 0 | 0 |
| Info/pre-gate (9) | 6 (subsampling, regression_guard cond., regime, cost_sweep, sensitivity, dd_episodes) | 1 (bootstrap) | 2 (overlay, churn_metrics) | 0 |
| Infrastructure (5) | 1 (thresholds pattern) | 4 (decision, runner, factory, config) | 0 | 0 |
| research/lib (4) | 0 | 0 | 0 | 4 (VCBB, DSR, DOF, pair_diagnostic) |
| **Total (26)** | **11** | **9** | **2** | **4** |

**Tỷ lệ**: 42% reuse, 35% replace, 8% discard, 15% introduce.

**Lưu ý phân loại**: validation/ có 7 gates chính trong `decision.py` (3 hard + 3 soft + 1 info).
Ngoài ra, `data_integrity`, `invariants`, `regression_guard` là pre-gate ERROR exits (exit 3) —
cứng hơn hard gates nhưng không nằm trong 7-gate verdict logic. `subsampling` và các info
suites chạy nhưng không feed vào verdict.

---

## G. ddof & ANNUALIZATION AUDIT

| Source | ddof | Annualization factor | Resolution (bars) |
|--------|------|---------------------|-------------------|
| v10/research/bootstrap.py | **ddof=0** (population) | √2190 (365×6) | H4 bars |
| v10/core/metrics.py | **ddof=0** (population) | √2190 (365×6) | H4 bars |
| validation/suites/selection_bias.py | **ddof=0** (population) | √365 | Daily log returns |
| research/lib/dsr.py | N/A (receives SR) | √2191.5 (default) | Per-bar |
| validation/lib/dsr.py | N/A (receives SR) | Caller-dependent | Caller-dependent |
| Gen1 spec | **ddof=1** (sample) | √365.25 | Daily |
| Gen4 spec | **ddof=1** (implied) | √365.25 | Daily |

**Conflict**: Toàn bộ code dùng ddof=0 (v10/metrics, bootstrap, selection_bias).
Gen1/gen4 specs yêu cầu ddof=1. Negligible cho N>2000, nhưng nên thống nhất cho Alpha-Lab.

**Resolution đề xuất**: ddof=1 (sample std, consistent with gen1/gen4/validation/).
Annualization: √(365.25) cho daily, √(365.25 × bars_per_day) cho sub-daily.

---

## H. DECISION AUTHORITY MODEL COMPARISON

| Layer | validation/ | Gen1 | Gen4 | x38 (proposed) |
|-------|------------|------|------|----------------|
| **Tier 1: Machine** | 7 gates → PROMOTE/HOLD/REJECT/ERROR | Promotion gates (pass/fail) | Hard constraints + Calmar ranking | Protocol engine (8 stages) |
| **Tier 2: Gate results** | Hard/soft/info severity | Stage 1/2 promotion criteria | Discovery → holdout → reserve → forward | Stage gating + freeze checkpoint |
| **Tier 3: Human** | "HOLD ≠ not deployable" (STRATEGY_STATUS_MATRIX) | Researcher decision | Forward evaluation policy | Clean OOS 3-verdict model |
| **Evidence clock** | Không có | Không có | freeze_cutoff_utc | Boundary timestamps per session |
| **Contamination** | Holdout lock file only | Protocol docs (manual) | Explicit data boundaries | Machine-enforced firewall (F-04) |

---

## I. DISCOVERY TECHNIQUES — Algorithm Finding Pipeline

Sections A-H cover **validation** (post-freeze). Section I covers **discovery** (pre-freeze):
kỹ thuật để TÌM thuật toán, không phải kiểm chứng chúng.

### I1. Discovery Pipeline: 8 Stages × 3 Sources

| Stage | Tên | Gen1 (V8) | Gen4 | Code hiện có | x38 planned |
|-------|-----|-----------|------|-------------|-------------|
| 1 | Protocol lock + data audit | Protocol docs (manual) | D0 precheck + hash | `data_integrity.py` (partial) | Machine-enforced freeze (F-05) |
| 2 | **Feature scan** | 1,234 configs, 29 families, 4 buckets | 4 channels measured (D1b) | Không có registry | **50K+ configs**, registry + decorator (F-08) |
| 3 | **Orthogonal pruning** | Manual curation (ρ + family clustering) | Constitution caps (3 candidates) | Không có | Automated ledger (keep/drop) |
| 4 | **Architecture search** | Manual (single → 2-layer → 3-layer) | From measured channels | Không có | Budget-constrained (≤3 layers, ≤6 tunables) |
| 5 | **Plateau detection** | 80% Sharpe retention, center > peak | Calmar ranking | `sensitivity.py` (grid only) | Coarse → local + ±20% perturbation |
| 6 | Freeze comparison set | Keep/drop ledger | `frozen_spec.json` | Không có | IMMUTABLE after freeze |
| 7 | Holdout + internal reserve | Separate periods | D1e2 holdout | `holdout.py` (fraction-based) | Temporal seal (from gen4) |
| 8 | Evaluation battery | Informal | 13-point | `runner.py` (17 suites) | 13-point mandatory |

### I2. Feature Engineering & Registry

**Code hiện có**: Không có feature registry. Features hardcoded trong mỗi `strategy.py`.

| Aspect | Gen1 (V8) | Gen4 | x38 (F-08) | Conflict? |
|--------|-----------|------|------------|-----------|
| **Definition** | Per-spec manual list | Per-spec manual list | Registry + @decorator | Gen1/gen4 = manual, x38 = automated |
| **Enumeration** | Manual count (1,234) | Manual count (30) | Auto Cartesian product (50K+) | Scale difference 40x-1600x |
| **Families** | 29 (9 types × 2 timeframes + XR + transport) | 4 channels (price, vol, flow, XR) | 9+ planned | Gen1 more exhaustive than gen4 |
| **Feature buckets** | D1 native, H4 native, cross-TF, transported D1→H4 | D1, H4, 1h, 15m (multi-resolution) | TBD | Gen4 adds 1h/15m |
| **Threshold modes** | 4: sign, train_quantile, structural_level, categorical | Heuristic (per-design) | 4 (from gen1) | Agreement gen1→x38 |
| **Lookback grids** | D1: {3,5,10,20,40,80}, H4: {6,12,24,48,96,168} | Per-candidate specific | Configurable per family | Gen1 more systematic |
| **Reusable code** | Không (specs only) | Không (specs only) | `v10/research/candidates.py` (YAML loader, partial) | candidates.py reusable for matrix, not registry |

**Verdict**: **BUILD** — Không có code để reuse. x38 phải build feature registry từ scratch.
Gen1's 29-family library là **design reference** tốt nhất.

### I3. Exhaustive Scan vs Measurement-First Design

Hai approach fundamentally khác nhau:

| Approach | Source | Scale | Method | Strength | Weakness |
|----------|--------|-------|--------|----------|----------|
| **Exhaustive scan** | Gen1 V8 | 1,234 configs | Scan toàn bộ library → filter qua 5 hard gates → 631 promoted | Không miss viable candidates | Expensive, needs automation |
| **Measurement-first** | Gen4 | 30 configs | Measure channels → design 3 candidates từ data insights | Informed design, less configs | Can miss unexpected signals |

**x38 stance (PLAN.md)**: Exhaustive (50K+), nhưng chưa explicitly reject measurement-first.

**Conflict?** YES — fundamental methodology choice. x38 cần decide:
- Pure exhaustive (gen1 style, 50K+ brute-force)?
- Measurement → design (gen4 style, informed but smaller)?
- Hybrid (measure channels → exhaustive within promising families)?

**Finding**: **F-40** — Exhaustive vs measurement-first: architectural choice chưa resolved.
**Maps to**: Topic 003 (protocol engine) hoặc 006 (feature engine).

### I4. Promotion Gates (Stage 2 → Stage 3)

| Gate | Gen1 (V8) | Gen4 | Code (`wfo.py`) | x38 |
|------|-----------|------|-----------------|-----|
| Positive edge after cost | Yes (20 bps) | Yes (50 bps CAGR > 0) | Objective sentinel (< 10 trades → reject) | TBD |
| Min trades | ≥ 20 trade_count_entries | Entries/year ∈ [6, 80] | < 10 → reject | TBD |
| Fold consistency | ≥ 50% of 14 folds positive | Không explicit | Win rate 60% (UNPROVEN) | TBD |
| No isolation | Largest fold / sum ≤ 0.65 | Không có | Không có | TBD |
| No leakage | Required | Không explicit | Lookahead suite | Required |

**Conflict?** YES — 3 different gate sets. Maps to Cluster 1b (gate inventory), nhưng
discovery-phase gates khác validation-phase gates. Cùng concept, khác context.

**Finding**: **F-41** — Discovery promotion gates vs validation gates: separate inventories needed.

### I5. Orthogonal Pruning

**Code hiện có**: Không có.

| Aspect | Gen1 | Gen4 | x38 |
|--------|------|------|-----|
| **Method** | Pairwise ρ → family clustering → manual keep/drop | Constitution caps (3 candidates max) | Automated ledger |
| **De-dup threshold** | ρ ≈ 1.0 removed, ρ < 0.90 kept | Not explicit | TBD |
| **Redundancy audit** | V7 pattern P-07: clone D1→H4, measure ρ with natives | Not explicit | From gen1 |
| **Shortlist size** | ~29 (11 single + 12 two-layer + 6 three-layer) | 3 candidates | TBD |
| **Minimum survivors** | ≥1 slow-TF, ≥1 fast-native, ≥1 layered alternative | 1 champion + 2 challengers | TBD |

**Verdict**: **BUILD** — Automation needed. Gen1 manual curation = design reference.
Gen4 constitutional caps (3 max) = simplicity constraint.

**Finding**: **F-42** — Orthogonal pruning: no code exists. Need algorithm + thresholds.

### I6. Layered Architecture Search

| Aspect | Gen1 | Gen4 | Code | x38 |
|--------|------|------|------|-----|
| **Max layers** | 3 | 3 | Không giới hạn | **≤3** (consensus) |
| **Max tunables** | Not explicit | **4** (hard cap) | ≤8 (wfo.py grid limit) | **≤6** (relaxed) |
| **Complexity penalty** | Không | 0.02/layer + 0.03/tunable | Không | TBD (Cluster 1a) |
| **Layer roles** | gate (slow) + controller (fast) + optional entry filter | permission + continuation + timing | Per-strategy | TBD |
| **Ablation** | No formal protocol | **Mandatory** per-layer | Không có | **Mandatory** (from gen4) |
| **Post-ablation simplification** | Không | Yes (simpler variant can promote) | Không | From gen4 |

**Key gen4 innovation**: Ablation-mandatory + post-ablation simplification.
Nếu bỏ 1 layer mà Calmar tăng → layer đó FAIL. Simpler variant có thể thay thế.

**Finding**: **F-43** — Ablation protocol: gen4 mandatory, gen1/code không có. x38 cần spec.

### I7. Plateau Detection & Parameter Refinement

**Code hiện có**: `validation/suites/sensitivity.py` chỉ sweep grid, không score plateau.

| Aspect | Gen1 | Gen4 | Code | x38 |
|--------|------|------|------|-----|
| **Method** | 80% Sharpe retention target, center > peak | Calmar ranking (implicit) | Grid sweep only | Coarse → local + ±20% perturbation |
| **Perturbation test** | ±20% on each tunable | Not explicit | Not implemented | ±20% (from gen1) |
| **Plateau scoring** | Heuristic (count cells above 80% threshold) | Not explicit | Not implemented | TBD |
| **Grid size** | 12-180 cells per family | 6-12 configs per candidate | Configurable | TBD |
| **Selection rule** | Center of broad plateau | Highest adjusted preference | Highest objective | TBD |

**Verdict**: **BUILD** — Plateau detection algorithm cần implement mới.
`sensitivity.py` grid sweep reusable cho data generation, nhưng scoring logic cần build.

**Finding**: **F-44** — Plateau detection: no algorithm exists in code. Need scoring + selection rule.

### I8. Comparison & Tie-Breaking (Stage 6-7)

| Aspect | Gen1 | Gen4 | Code |
|--------|------|------|------|
| **Paired comparison** | Moving-block bootstrap (2-3K, 3 block sizes) | Paired block bootstrap (3K, [5,10,20] days, 95% prob) | `paired_block_bootstrap()` in v10 |
| **Meaningful advantage** | P(diff > 0) ≥ 0.95 on ≥2 block sizes | P ≥ 0.95 on ≥2 sizes + point estimate ≥ 5e-5 | `p_a_better` in BootstrapResult |
| **Tie-breaking** | Simpler wins if bootstrap indeterminate | Complexity penalty in ranking | No tie-breaking logic |
| **Ablation tie-break** | Không | Layer removal → Calmar change | Không |

**Code reusable**: `paired_block_bootstrap()` từ v10/research. Nhưng tie-breaking logic và
meaningful-advantage threshold cần debate (Cluster 2a/2b).

---

## J. DISCOVERY REUSE SUMMARY

| Category | BUILD | REUSE | REPLACE | N/A |
|----------|-------|-------|---------|-----|
| Feature registry (Stage 2) | **1** (no code exists) | 0 | 0 | 0 |
| Exhaustive scan engine (Stage 2) | **1** (wfo.py partial) | 0 | 0 | 0 |
| Promotion gates (Stage 2→3) | **1** (need new gate set) | 0 | 0 | 0 |
| Orthogonal pruning (Stage 3) | **1** (no code exists) | 0 | 0 | 0 |
| Architecture search (Stage 4) | **1** (no code exists) | 0 | 0 | 0 |
| Plateau detection (Stage 5) | **1** (sensitivity.py partial) | 0 | 0 | 0 |
| Comparison tools (Stage 6-7) | 0 | **3** (bootstrap, subsampling, pair_diagnostic) | 0 | 0 |
| Matrix runner (cross-cutting) | 0 | **1** (candidates.py) | 0 | 0 |
| Regime classifier (cross-cutting) | 0 | **1** (regime.py) | 0 | 0 |
| Objective function (cross-cutting) | 0 | 0 | **1** (weights TBD, Cluster 1a) | 0 |
| **Total (12)** | **6** | **5** | **1** | **0** |

**Discovery vs Validation**: Validation = 42% reuse. Discovery = **50% BUILD from scratch**.
Alpha-Lab's discovery infrastructure requires significant new code.

---

## K. DISCOVERY FINDINGS (supplement to Section E)

Findings derived từ discovery analysis, bổ sung vào existing topics:

| Finding | Mô tả | Maps to Topic |
|---------|--------|---------------|
| **F-40** | Exhaustive scan (gen1, 50K+) vs measurement-first design (gen4, 30): fundamental methodology choice chưa resolved | 003 (protocol) hoặc 006 (feature) |
| **F-41** | Discovery promotion gates ≠ validation gates: cần separate inventories cho Stage 2→3 vs Stage 8 | 003 (protocol) + 013 (gate inventory) |
| **F-42** | Orthogonal pruning: no code exists. Cần algorithm (ρ threshold, family clustering, min survivors) + automation scope | 006 (feature engine) |
| **F-43** | Ablation protocol: gen4 = mandatory per-layer + post-ablation simplification. Gen1/code = không có. x38 cần spec | 003 (protocol) |
| **F-44** | Plateau detection: no scoring algorithm in code. sensitivity.py = grid sweep only. Cần plateau metric + selection rule | 003 (protocol) hoặc 005 (core engine) |

---

*Document updated. Covers both validation (Sections A-H) and discovery (Sections I-K).
Serve as input to debate clusters X38-T-13, X38-T-14a/b, X38-T-15,
and existing topics 003 (protocol), 005 (engine), 006 (feature).*
