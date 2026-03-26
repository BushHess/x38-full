---
doc_type: debate_round_review
topic: search-space-expansion
round: 3
author: claude_code
date: 2026-03-26
status: OPEN
sources:
  - ../../request.md
  - ../gemini/gemini_propone.md
  - ../codex/codex_propone.md
  - ./claude_propone.md
  - ../chatgptpro/chatgptpro_propone.md
  - ../gemini/gemini_debate_lan_1.md
  - ../codex/codex_debate_lan_1.md
  - ./claude_debate_lan_1.md
  - ../chatgptpro/chatgptpro_debate_lan_1.md
  - ../gemini/gemini_debate_lan_2.md
  - ../codex/codex_debate_lan_2.md
  - ./claude_debate_lan_2.md
  - ../chatgptpro/chatgptpro_debate_lan_2.md
  - ../../../online_vs_offline.md
  - ../../../design_brief.md
  - ../../../../debate/rules.md
  - ../../../../debate/017-epistemic-search-policy/findings-under-review.md
  - ../../../../debate/006-feature-engine/findings-under-review.md
  - ../../../../debate/015-artifact-versioning/findings-under-review.md
  - ../../../../debate/013-convergence-analysis/findings-under-review.md
  - ../../../../debate/008-architecture-identity/findings-under-review.md
tracking_rules:
  - Convergence Ledger la nguon chan ly cho cac diem da chot.
  - Vong sau chi ban cac muc trong Open Issues Register.
  - Muon lat lai diem da khoa phai tao REOPEN-* kem bang chung moi.
  - Y tuong moi phai tao NEW-* va giai thich vi sao issue hien tai khong bao phu.
  - Khong doi ID cu, khong danh so lai.
status_legend:
  CONVERGED: da du chac de khong ban lai.
  PARTIAL: cung huong lon nhung chi tiet chua khoa.
  OPEN: con tranh chap thuc chat.
  DEFER: co gia tri nhung khong nen la trong tam v1.
---

# Debate Round 3 — Pushing Near-Converged Items to Closure, Resolving GFS Depth-1

## 1. Ket luan nhanh

Vong 2 thu hep khoang cach dang ke. 4 agents dong huong tren 4 OIs (OI-02, OI-04, OI-06, OI-07) — toi de xuat day chung sang CONVERGED voi steel-man day du. Tranh chap thuc chat con lai tap trung vao 2 cau hoi: (1) **GFS depth-1 bat buoc hay optional** (OI-03) — toi cho rang gap nay hep hon no co ve, vi ChatGPT Pro da chap nhan "deterministic depth-1 grammar enumeration" trong backbone; (2) **Cell dimensions + equivalence + correction law** (OI-08 + NEW-01 ChatGPT Pro) — can chot interface-level contract truoc khi breadth mechanism merge.

Ghi chu governance: Gemini Round 2 su dung OI numbering rieng (OI-01 to OI-08 voi noi dung khac hoan toan) khong map duoc 1:1 sang unified numbering cua ChatGPT Pro/Codex/Claude. Toi mapping positions Gemini vao unified OIs noi phu hop, nhung can chinh Gemini dung chung numbering tu round 4 de tranh divergence.

---

## 2. Scoreboard

Khong thay doi diem so tong the so voi Round 2. Thu tu giu nguyen: **Codex** manh nhat backbone; **ChatGPT Pro** manh nhat guardrail + critical-path; **Claude** pressure-test + generation mechanism; **Gemini** giu offline-first nhung thieu engine.

---

## 3. Convergence Ledger (cap nhat)

> Giu CL-01 den CL-10 tu Round 2. De xuat them CL-11, CL-12, CL-13, CL-14.

| ID | Ket luan hoi tu | Basis | Status | Ghi chu |
|----|----------------|-------|--------|---------|
| CL-01 | X38 manh validation, yeu discovery | 4/4 proposals + 4/4 debate round 1 | CONVERGED | |
| CL-02 | Tach Tang 1 (exploration) va Tang 2 (recognition/systematization) | Yeu cau goc + 4/4 | CONVERGED | |
| CL-03 | Post-lock execution phai deterministic offline; AI khong evaluate/rank/select trong runtime | 4/4 + `online_vs_offline.md` | CONVERGED | |
| CL-04 | Discovery artifact phai machine-readable; prompt/transcript la provenance phu | 4/4 round 1-2 | CONVERGED | |
| CL-05 | Cell-elite archive thay global top-K | 4/4 + ESP-01 | CONVERGED | Cell dimensions con OPEN (OI-08) |
| CL-06 | Discovery gates != certification gates | 4/4 round 1-2 | CONVERGED | |
| CL-07 | Same-dataset learned priors shadow-only | MK-17 + 4/4 | CONVERGED | |
| CL-08 | Freeze giu comparison set + coverage/phenotype evidence | 4/4 + ESP-01/02 | CONVERGED | |
| CL-09 | Recognition phai cham consistency motif, khong chi peak score | ChatGPT Pro + VDO evidence | CONVERGED | |
| CL-10 | Backbone v1 = Codex + ChatGPT Pro (lineage + cell-elite + gate split) | 3/4 round 1; Claude concession round 2 | CONVERGED | |
| CL-11 | **Bounded ideation lane thay SSS; 4 hard rules (manifest output, no evaluate/rank, no answer-prior view, compile-before-lock)** | OI-02: Claude concession R2 + ChatGPT Pro 4 rules + Codex protocol-lock boundary + Gemini offline-first | CONVERGED (proposed) | Schema output can chot (-> OI-02 residual) |
| CL-12 | **Domain-seed/cross-domain = optional provenance hook, khong phai core v1** | OI-07: 4/4 round 2 dong huong | CONVERGED (proposed) | Hook: `domain_hint_ref` in `proposal_provenance.json` |
| CL-13 | **Canonical lineage tach 3 lop: feature_lineage + candidate_genealogy + proposal_provenance (supplementary)** | OI-04: Claude R2 AGREE + ChatGPT Pro R2 3-layer split + Codex R2 structural lineage canonical | CONVERGED (proposed) | 015 owns enumeration; 006 owns feature-level fields |
| CL-14 | **Negative evidence = descriptor-level contradiction_registry.json, shadow-only, populated tu proof_bundle** | OI-06: 4/4 R2 dong huong; MK-17 ceiling | CONVERGED (proposed) | EPC lifecycle DEFER v2 |

### Steel-man tests cho CL-11 den CL-14

**CL-11 (Bounded ideation thay SSS):**
- Steel-man cho SSS: "SSS truc tiep tai tao VDO origin story — AI session + loose prompt + OHLCV data. Day la co che duy nhat da duoc chung minh tao ra discovery thuc su trong project nay."
- Tai sao steel-man khong du: VDO huu ich vi `volume x direction` la mot meaningful composition, khong phai vi no ra tu AI session format. GFS depth-1 cover composition nay mot cach he thong. Bounded ideation lane giu lai kha nang human/AI de xuat conceptual insight (cai ma GFS khong lam duoc) ma khong can SSS infrastructure (prompt templates, session protocols, transcript management). 4 hard rules cua ChatGPT Pro ngan moi contamination vector ma SSS tao ra.
- Evidence: `./claude_debate_lan_2.md:125-128` (self-critique); `../chatgptpro/chatgptpro_debate_lan_1.md:147-158`; `../codex/codex_debate_lan_1.md:276-282`

**CL-12 (Domain-seed = optional hook):**
- Steel-man cho domain-seed as core: "VDO den tu signal processing insight — cross-domain cross-pollination la co che thuc su. Framework can curate domain catalog de tai tao co he thong."
- Tai sao steel-man khong du: VDO den tu composition (volume x direction), khong tu domain knowledge. Domain knowledge chi inspired prompt. Curated domain catalog la pre-mature abstraction cho v1 khi lineage/coverage/archive/proof/gate inventory deu chua chot. `domain_hint_ref` provenance hook giu lai connection trail ma khong tao architectural dependency.
- Evidence: `../chatgptpro/chatgptpro_debate_lan_2.md:117-119`; `./claude_debate_lan_2.md:266-279`

**CL-13 (3-layer lineage split):**
- Steel-man cho single-schema lineage: "Tach 3 schemas tao ra 3 artifact files, 3 owner obligations, 3 invalidation paths. Single schema don gian hon va van cover du fields."
- Tai sao steel-man khong du: Feature formula change va candidate role/mutation change co invalidation semantics KHAC NHAU (`../chatgptpro/chatgptpro_debate_lan_2.md:96`). Feature thay doi operator chain -> invalidate moi candidate dung no. Candidate thay doi role assignment -> chi invalidate candidate do. Gop chung lam mo ranh gioi invalidation cua 015. Chi phi tach = 3 files thay vi 1, co the chap nhan duoc.
- Evidence: `../chatgptpro/chatgptpro_debate_lan_2.md:93-98`; `../codex/codex_debate_lan_2.md:123-129`; `./claude_debate_lan_2.md:186-202`

**CL-14 (Contradiction registry, shadow-only):**
- Steel-man cho artifact rieng (negative_evidence_registry): "Contradiction la empirical finding — no xung dang artifact rieng biet voi schema, lifecycle, va promotion path rieng, khong chi la shadow field."
- Tai sao steel-man khong du: MK-17 lam same-dataset activation inert. Negative evidence la empirical prior (`debate/004-meta-knowledge/final-resolution.md`). Tao artifact rieng voi promotion path rieng = tao contamination lane nguy trang. `contradiction_registry.json` shadow-only voi descriptor-level content (khong feature names/params/winner IDs) la du de ghi nhan patterns ma khong vi pham firewall. Full EPC lifecycle chi co y nghia khi co >=2 campaigns tren different data.
- Evidence: `../chatgptpro/chatgptpro_debate_lan_2.md:109-112`; `../codex/codex_debate_lan_2.md:131-137`; `./claude_debate_lan_2.md:236-256`

---

## 4. Open Issues Register — Phan hoi vong 3

> Tiep tuc dung unified OI numbering (ChatGPT Pro). Chi ban OPEN/PARTIAL items.

---

### OI-01 — Pre-lock generation lane ownership: fold conditions

- **Stance**: AGREE — push to PARTIAL (gan CONVERGED)

- **Diem dong y**:
  - 4/4 agents round 2 dong huong fold vao topics hien co. Khong ai con de xuat mo Topic 018 umbrella.
  - Codex R2 chot: `006` own compiled grammar/manifest ingestion; `015` own lineage/invalidation; `017` chi consume compiled outputs sau lock (`../codex/codex_debate_lan_2.md:101-103`).
  - ChatGPT Pro R2 chot: fold voi phan vai cung: `006` = operator grammar + compile-to-manifest; `015` = lineage/state-pack/invalidation; `017` = coverage/cell-elite/surprise/budget (`../chatgptpro/chatgptpro_debate_lan_2.md:76`).
  - Claude R2 da neu dieu kien testable de mo topic moi: "CHI KHI sau khi 006 va 017 close, ownership that su bi tran va gay mau thuan interface" (`./claude_debate_lan_2.md:100-101`).

- **Diem phan doi**: Khong con tranh chap thuc chat ve direction. Cau hoi con lai la procedural: lam sao detect "ownership bi tran"? De xuat: neu 006 hoac 017 closure report co section "Unresolved cross-topic contract gap" va gap do khong the quy ve 015/013/008 -> trigger mo topic hep.

- **De xuat sua**:
  - Chot fold assignment: `006` = generation mechanism + operator grammar; `017` = search policy + coverage obligations; `015` = lineage/invalidation.
  - Dieu kien mo topic moi: explicit "unresolved gap" section trong closure report cua 006/017, khong the fold vao bat ky topic nao khac.
  - Cau hoi "ai sinh manifest moi" (Codex R2) duoc tra loi boi: `006` owns manifest compilation, bounded ideation lane (CL-11) + GFS depth-1 (OI-03) la hai nguon input.

- **Evidence**: `../codex/codex_debate_lan_2.md:99-105`; `../chatgptpro/chatgptpro_debate_lan_2.md:73-77`; `./claude_debate_lan_2.md:84-107`; `debate/rules.md` §12

- **Trang thai**: PARTIAL — direction locked, dieu kien testable da neu, cho xac nhan.

---

### OI-02 — Bounded ideation lane contract

- **Stance**: AGREE — push to CONVERGED (CL-11)

- **Diem dong y**:
  - Toi da rut SSS chinh thuc o Round 2 (`./claude_debate_lan_2.md:114`).
  - 4 hard rules cua ChatGPT Pro duoc 4/4 chap nhan.
  - ChatGPT Pro R2 bo sung: bounded ideation lane phai la "schema-aware, results-blind" (`../chatgptpro/chatgptpro_debate_lan_2.md:83`). Toi dong y.
  - Claude R2 bo sung rule thu 5: "AI input = OHLCV schema + operator library only, KHONG nhin current registry hay prior results" (`./claude_debate_lan_2.md:130`). ChatGPT Pro R2 da dong y voi direction nay.
  - Output schema: `proposal_spec.yaml` hoac `candidate_grammar.json` hoac `idea_manifest.jsonl` — naming chua chot nhung structure da ro: typed proposal compile-able thanh registry entry.

- **Diem phan doi**: Khong con tranh chap thuc chat. Naming/exact schema fields la implementation detail cho 006.

- **De xuat sua**:
  - Chuyen OI-02 sang CL-11 (da ghi o tren).
  - Residual: 006 chot output schema cua bounded ideation lane khi 006 debate. Khong can ban them o search-space-expansion topic.

- **Evidence**: Steel-man o CL-11 section. `./claude_debate_lan_2.md:110-137`; `../chatgptpro/chatgptpro_debate_lan_2.md:79-84`; `../codex/codex_debate_lan_2.md:99-105`

- **Trang thai**: CONVERGED (de xuat) — chuyen sang CL-11.

---

### OI-03 — GFS depth-1: bat buoc hay optional cho v1?

- **Stance**: AMEND — push to PARTIAL (gap hep hon no tuong)

- **Diem dong y**:
  - ChatGPT Pro R2 **da chap nhan** "Deterministic depth-1 grammar enumeration + local_neighborhood_probes" trong Adopt ngay #4 (`../chatgptpro/chatgptpro_debate_lan_2.md:174`). Day chinh la GFS depth-1 duoi ten goi khac.
  - ChatGPT Pro R2 backbone: "deterministic operator grammar + compile-to-manifest, cho phep depth-1 grammar enumeration sau freeze" (`../chatgptpro/chatgptpro_debate_lan_2.md:90`).
  - Codex R2 backbone: "compiled manifest/operator grammar -> descriptor tagging -> coverage map -> cell-elite archive -> local probes" (`../codex/codex_debate_lan_2.md:165-168`). Compiled manifest implies enumeration.
  - Gemini R2 chap nhan "Grid Expansion and Randomized Scalar Mutation" cho v1 (`../gemini/gemini_debate_lan_2.md:91`). Grid expansion tren operator grammar = GFS depth-1.

- **Diem phan doi**:
  - Codex R2 giu GFS depth-1 nhu open question (`../codex/codex_debate_lan_2.md:109-113`), nhung backbone description cua Codex da implicitly include operator grammar enumeration.
  - ChatGPT Pro R2 gang dieu kien: "Depth-1 chi duoc bat cung luc voi contract multiplicity control o NEW-01" (`../chatgptpro/chatgptpro_debate_lan_2.md:90`). **Toi dong y voi dieu kien nay.** Day la coupling chinh dang, khong phai blocker.

- **Argument chinh**:

  Tat ca 4 agents da dong y voi backbone co: operator grammar + compiled manifest + exhaustive scan. GFS depth-1 la **ten cu the** cho "enumerate operator grammar at depth 1":

  ```
  operator_grammar = {ema, sma, zscore, rolling_std, percentile_rank, diff, sign, abs, ...}
  primitives = {open, high, low, close, volume}
  lookback_ranges = {10, 20, 40, 60, 80, 100, 120, 144, 200}

  depth_1_enumeration = [op(prim, lb) for op in grammar for prim in primitives for lb in lookbacks]
  ```

  Neu backbone co "operator grammar + compiled manifest + Stage 3 exhaustive scan" nhung KHONG enumerate grammar, thi "exhaustive scan" scan cai gi? Manifest do ai populate? Cau hoi nay chi co 3 tra loi:
  1. **Human hand-declares features** -> chinh xac failure mode ma request.md muon giai quyet.
  2. **Bounded ideation lane (AI propose)** -> tot nhu input bo sung, nhung non-deterministic va khong exhaustive.
  3. **Grammar enumeration (GFS depth-1)** -> deterministic, exhaustive trong declared grammar, offline.

  Tra loi #3 la duy nhat thoa man ca "offline deterministic" (CL-03) va "exhaustive scan over declared search space" (`docs/online_vs_offline.md:35`).

  **Pressure test van chua duoc tra loi boi bat ky agent nao**: cho Alpha-Lab mot asset moi, data OHLCV san, operator grammar san, nhung KHONG co GFS depth-1. Feature Engine registry chua gi? Tra loi: **TRONG**. Bounded ideation lane la optional input source (CL-11) — khong co obligation tao features. Grammar co nhung chua ai enumerate no.

- **De xuat sua**:
  - Chot: GFS depth-1 = mandatory v1 mechanism, **coupled voi multiplicity control** (dong y ChatGPT Pro dieu kien).
  - Ten: khong nhat thiet goi la "GFS" — "depth-1 grammar enumeration" (ChatGPT Pro R2 naming) cung duoc. Quan trong la co che, khong phai ten.
  - Owner: 006 (generation mechanism + operator grammar).
  - Timing: chay ngay dau Stage 3 (sau protocol lock). Manifest output la input cho exhaustive scan.
  - Scale: ~500-2,000 features (5 primitives x 12 operators x 9 lookbacks x dedup). Compute: vai gio tren single machine. v1-feasible.
  - GFS depth-2+ -> DEFER, chi khi depth-1 yield NO_ROBUST_IMPROVEMENT.

- **Evidence**: `../chatgptpro/chatgptpro_debate_lan_2.md:90,174`; `../codex/codex_debate_lan_2.md:109-113,165-168`; `./claude_debate_lan_2.md:151-179`; `../../request.md:13`; `docs/online_vs_offline.md:35`

- **Trang thai**: PARTIAL — direction da ro (depth-1 enumeration la phan cua backbone), tranh chap con lai la coupling voi multiplicity control (-> NEW-01 ChatGPT Pro) va exact operator set (-> 006).

---

### OI-04 — Canonical lineage 3-layer split

- **Stance**: AGREE — push to CONVERGED (CL-13)

- **Diem dong y**:
  - ChatGPT Pro R2 neu ro 3 artifacts: `feature_lineage.jsonl`, `candidate_genealogy.jsonl`, `proposal_provenance.json` (`../chatgptpro/chatgptpro_debate_lan_2.md:97`).
  - Codex R2 dong y canonical = structural/deterministic lineage, prompt/session = supplementary provenance (`../codex/codex_debate_lan_2.md:123-129`).
  - Claude R2 da AGREE, de xuat tach feature vs candidate sub-schemas sharing common fields (`./claude_debate_lan_2.md:186-202`).
  - Gemini R2 chap nhan artifact JSON standard (`../gemini/gemini_debate_lan_2.md:77-78`).

- **Diem phan doi**: Khong con. Chuyen sang CL-13.

- **Evidence**: Steel-man o CL-13 section.

- **Trang thai**: CONVERGED (de xuat) — chuyen sang CL-13.

---

### OI-05 — Recognition stack + surprise criteria

- **Stance**: AMEND — push to PARTIAL (gan CONVERGED)

- **Diem dong y**:
  - Stack v1 da dong huong: `surprise_queue -> equivalence_audit -> proof_bundle -> freeze_comparison_set -> candidate_phenotype -> contradiction_registry (shadow)`.
  - ChatGPT Pro R2 chot: surprise criteria toi thieu phai co it nhat mot chieu **khong phai peak-score** (`../chatgptpro/chatgptpro_debate_lan_2.md:104`). Toi dong y.
  - Codex R2: surprise = triage priority, khong phai winner privilege (`../codex/codex_debate_lan_2.md:117-121`). Dong y.
  - Human chen vao o 2 diem: ambiguity/reconstruction-risk va deployment authority. Dong y.

- **Diem phan doi**:
  - Surprise criteria cu the chua chot. Claude R2 de xuat 4 simplified criteria (decorrelation, risk-profile, plateau, consistency). ChatGPT Pro R2 chap nhan consistency motif va non-peak-score dimensions. Chua co agent nao phan doi 4 criteria nay.
  - De xuat chot 4 criteria nhu **mandatory minimum**, khong phai **exhaustive list**:
    1. **Decorrelation outlier**: max |corr| voi cell-elite survivors < threshold (0.3 la starter, 006/013 chot threshold cu the).
    2. **Risk-profile outlier**: Sharpe < cell median BUT MDD hoac cost-stability tot hon cell-best.
    3. **Plateau champion**: plateau width > 2x cell median.
    4. **Consistency champion**: cross-timescale/cross-resolution win rate > threshold.
  - Threshold cu the la implementation detail cho 017; search-space-expansion debate chi can chot **dimensions**.

- **De xuat sua**:
  - Chot: 4 surprise dimensions mandatory (decorrelation, risk-profile, plateau, consistency). Thresholds do 017 chot.
  - Equivalence metric: daily paired returns tren common evaluation domain. Descriptor-bundle distance bo sung sau.

- **Evidence**: `./claude_debate_lan_2.md:206-232`; `../chatgptpro/chatgptpro_debate_lan_2.md:100-105`; `../codex/codex_debate_lan_2.md:115-121`

- **Trang thai**: PARTIAL — dimensions dong huong, thresholds con open cho 017.

---

### OI-06 — Contradiction registry schema

- **Stance**: AGREE — push to CONVERGED (CL-14)

- **Diem dong y**:
  - 4/4 agents R2 dong huong: descriptor-level, shadow-only, contradiction_registry.json.
  - ChatGPT Pro R2: artifact chi chua descriptor bundle, evidence IDs, contradiction type, locality scope, reconstruction-risk, retention scope, invalidation rule; khong chua feature names/params/winner IDs (`../chatgptpro/chatgptpro_debate_lan_2.md:111`).
  - Codex R2: descriptor-level shadow-only + defer storage form cho 015+017 (`../codex/codex_debate_lan_2.md:131-137`).
  - Claude R2 da AGREE (`./claude_debate_lan_2.md:236-256`).
  - EPC lifecycle DEFER v2.

- **Diem phan doi**: Khong con. Chuyen sang CL-14.

- **Evidence**: Steel-man o CL-14 section.

- **Trang thai**: CONVERGED (de xuat) — chuyen sang CL-14.

---

### OI-07 — Domain-seed optional provenance hook

- **Stance**: AGREE — push to CONVERGED (CL-12)

- **Diem dong y**:
  - 4/4 agents R2: domain-seed = optional, khong core v1.
  - ChatGPT Pro R2: hook cuc hep `domain_hint_ref` trong `proposal_provenance.json`, khong anh huong replay/invalidation/budget (`../chatgptpro/chatgptpro_debate_lan_2.md:118`).
  - Claude R2 da AGREE (`./claude_debate_lan_2.md:260-279`).

- **Diem phan doi**: Khong con. Chuyen sang CL-12.

- **Evidence**: Steel-man o CL-12 section.

- **Trang thai**: CONVERGED (de xuat) — chuyen sang CL-12.

---

### OI-08 — Cell dimensions + equivalence + correction law

- **Stance**: AMEND — giu OPEN, thu hep tranh chap

- **Diem dong y**:
  - Ownership split da ro: 006 = feature descriptor primitives; 017 = strategy cell axes; 013 = comparison domain + distance metrics; 008 = identity vocabulary (`../chatgptpro/chatgptpro_debate_lan_2.md:125`). Toi dong y.
  - Equivalence v1 = hybrid: descriptor pre-bucket + paired-return distance (`../chatgptpro/chatgptpro_debate_lan_2.md:125`). Dong y — nay la chinh xac de xuat Claude R2 (Pearson tren daily paired returns + descriptor-bundle distance optional).
  - Codex R2 dong y: protocol phai khai bao explicit `scan_phase_correction_method`, `equivalence_method`, `minimum_robustness_bundle` (`../codex/codex_debate_lan_2.md:143`). Dong y.

- **Diem phan doi**:
  - **Cell dimensions** chua duoc chot. Claude R2 de xuat starter set: mechanism(5) x complexity(3) x turnover(3) x timeframe_primary(3) = 135 cells (`./claude_debate_lan_2.md:298-303`). ChatGPT Pro R2 de xuat tuong tu nhung voi nhieu dimensions hon, chia "cell axes" va "annotations" (`../chatgptpro/chatgptpro_debate_lan_2.md:125`). Chua co agent nao phan doi 4 dimensions co ban nay.
  - **Correction law** van open. Claude R2 de xuat Holm step-down. Codex R2 de xuat giu open ("FDR, Holm, hay cascade"). ChatGPT Pro R2 de xuat cho 013 chot.
  - **Equivalence threshold** (0.85?) chua co agent nao phan doi nhung cung chua co ai xac nhan.

- **De xuat sua**:
  - Chot **structure**: 4 mandatory cell axes (mechanism, complexity, turnover, timeframe). Exact values cua moi axis la implementation detail cho 006/017.
  - Chot **interface obligation**: protocol phai khai bao `scan_phase_correction_method` va `equivalence_method` truoc khi breadth mechanism duoc bat.
  - Defer **exact law** (Holm vs FDR vs cascade) cho 013 khi co evidence tu first campaign.
  - Defer **exact threshold** (0.85 correlation, 0.3 decorrelation) cho 013/017.

- **Evidence**: `./claude_debate_lan_2.md:283-309`; `../chatgptpro/chatgptpro_debate_lan_2.md:122-126`; `../codex/codex_debate_lan_2.md:139-145`

- **Trang thai**: PARTIAL — structure dong huong, exact laws/thresholds DEFER cho topic owners.

---

### NEW-01 (ChatGPT Pro) — Multiplicity control coupling

- **Stance**: AGREE

- **Diem dong y**:
  - ChatGPT Pro dung: breadth expansion + multiplicity/equivalence control la coupled design (`../chatgptpro/chatgptpro_debate_lan_2.md:129-131`). Codex R2 da noi ro dieu nay tu Round 1 (`../codex/codex_debate_lan_1.md:212-216`).
  - Toi da dong y o Round 2: "v1 khong nen freeze breadth ma bo trong correction/equivalence contract" (`./claude_debate_lan_2.md:291`).

- **Diem phan doi**: Khong.

- **De xuat sua**:
  - Merge NEW-01 (ChatGPT Pro) vao OI-08 nhu coupling constraint. Khong can issue rieng — OI-08 da cover "breadth vs multiplicity".
  - Contract toi thieu truoc khi depth-1 enumeration duoc bat: (1) common comparison domain defined; (2) scan-phase correction method declared; (3) equivalence method declared. Day chinh la interface obligations ma Codex R2 da neu.

- **Evidence**: `../chatgptpro/chatgptpro_debate_lan_2.md:129-131`; `../codex/codex_debate_lan_2.md:139-145`

- **Trang thai**: Merge vao OI-08. OI-08 la PARTIAL.

---

### NEW-01 (Claude) — APE scope cho v1

- **Stance**: AMEND — push to PARTIAL

- **Diem dong y**: Chua co agent nao phan hoi truc tiep NEW-01 cua Claude o Round 2. Tuy nhien:
  - ChatGPT Pro R2 defer "APE code generation + GFS depth 2/3" (`../chatgptpro/chatgptpro_debate_lan_2.md:186`). Dong huong voi APE v1 = parameterization only.
  - Codex R2 khong de cap APE.
  - Gemini R2 gioi han v1 tai "Grid Expansion and Randomized Scalar Mutation" (`../gemini/gemini_debate_lan_2.md:91`) — dong huong.

- **Diem phan doi**: Khong ai phan doi APE v1 = template parameterization only.

- **De xuat sua**:
  - Chot: v1 APE = config-level parameterization (lookback, threshold, cost). Khong code generation.
  - v2+ APE = code generation khi co proven template engine + automated test harness.
  - Owner: 006 (APE parameterization la phan cua operator grammar).
  - Rename: "APE" ten qua lon cho "config variation". Goi don gian la "parameter sweep" hoac "config perturbation". De 006 chot naming.

- **Evidence**: `./claude_debate_lan_2.md:313-329`; `../chatgptpro/chatgptpro_debate_lan_2.md:186`

- **Trang thai**: PARTIAL — direction da ro (parameterization only), cho xac nhan.

---

## 5. Per-Agent Critique (delta vong 3)

### 5.1 Gemini
**Delta**: Gemini R2 co governance issue: OI numbering rieng (OI-01 to OI-08) khong map sang unified numbering. Dieu nay gay kho khan cho convergence tracking. Noi dung thuc chat cua Gemini van dong huong voi consensus (offline-first, batch processing, no runtime LLM). Nhung viec khong dung chung OI framework khien cac agents khac khong the respond truc tiep den positions cua Gemini.

De xuat: Gemini round 4 phai dung unified OI numbering (ChatGPT Pro scheme) hoac map ro positions cua minh vao unified OIs.

**Evidence**: `../gemini/gemini_debate_lan_2.md` (OI-01 to OI-08 la noi dung khac voi cac agents khac)

### 5.2 Codex
**Delta**: Codex R2 la round chac chan nhat. Khong them convergence moi de tranh hoi tu gia (dung rules.md §7-§9). Backbone description da implicitly include operator grammar enumeration. Diem con thieu thuc su chi la explicit stance tren GFS depth-1: da chap nhan hay con coi la open question?

### 5.3 ChatGPT Pro
**Delta**: ChatGPT Pro R2 tot nhat ve structural clarity. NEW-01 (multiplicity control) la dong gop quan trong. 3-layer lineage split la clean. Tu phan bien ve under-specification tren pre-lock authoring contract va multiplicity control cho thay intellectual honesty cao. Backbone description da include "deterministic depth-1 grammar enumeration" — de facto dong y voi GFS depth-1 du chua goi no bang ten do.

### 5.4 Claude (self)
**Delta**: Round 2 cua toi da rut dung nhung gi can rut (SSS, Topic 018, APE code-gen, EPC). Round 3 toi push for closure tren 4 items near-converged va thu hep gap tren OI-03 (GFS depth-1). Tu phan bien: toi co the da over-push tren GFS depth-1 naming — dieu quan trong la mechanism (deterministic enumeration cua declared grammar), khong phai ten. ChatGPT Pro da chap nhan mechanism du khong goi la "GFS". Toi nen chap nhan naming flexibility.

---

## 6. Interim Merge Direction (cap nhat)

### 6.1 Backbone v1 (khong doi tu Round 2)

Codex + ChatGPT Pro backbone + deterministic depth-1 grammar enumeration + bounded ideation lane.

```
[Bounded ideation lane] --- proposal_spec.yaml ------+
                                                      +---> 006 registry compilation
[Depth-1 grammar enumeration] - manifest.json -------+
                                                      |
                            +-------------------------+
                            v
Protocol Lock --> Stage 3 scan (deterministic, offline)
    --> Stage 4 cell-elite archive + surprise slots
    --> Stage 5-6 layered search + probes
    --> Stage 7 freeze comparison set + proof bundles
    --> Stage 8 holdout/reserve + epistemic_delta + contradiction_registry
```

### 6.2 Adopt ngay (khong doi tu Round 2, xem `./claude_debate_lan_2.md:354-368`)

### 6.3 Defer (khong doi tu Round 2, xem `./claude_debate_lan_2.md:371-383`)

### 6.4 Ownership tam (khong doi tu Round 2, xem `./claude_debate_lan_2.md:386-394`)

---

## 7. Agenda vong sau

| OI | Trang thai | Can chot |
|----|-----------|---------|
| OI-01 | PARTIAL | Fold conditions: xac nhan tu cac agents? Co the CONVERGE neu khong co phan doi. |
| OI-02 | CONVERGED (proposed CL-11) | Cho xac nhan steel-man. |
| OI-03 | PARTIAL | GFS depth-1/grammar enumeration: co phai gap da dong lai? ChatGPT Pro da chap nhan mechanism. Codex can explicit stance. |
| OI-04 | CONVERGED (proposed CL-13) | Cho xac nhan steel-man. |
| OI-05 | PARTIAL | 4 surprise dimensions: phan hoi tu agents? Threshold defer cho 017. |
| OI-06 | CONVERGED (proposed CL-14) | Cho xac nhan steel-man. |
| OI-07 | CONVERGED (proposed CL-12) | Cho xac nhan steel-man. |
| OI-08 | PARTIAL | 4 cell axes structure + interface obligations. Exact laws/thresholds DEFER cho topic owners. |
| NEW-01 (Claude) | PARTIAL | APE v1 = parameterization only. Cho xac nhan. |

**Trong tam vong 4**: Xac nhan 4 CL moi (CL-11 to CL-14). Chot OI-03 (grammar enumeration). Thu hep OI-08 (cell structure). Neu duoc, phan lon issues se la CONVERGED hoac PARTIAL voi clear ownership, va topic co the chuyen sang closure preparation.

---

## 8. Change Log

| Vong | Ngay | Agent | Tom tat thay doi |
|------|------|-------|-------------------|
| 1 | 2026-03-25 | claude_code | Round mo dau: phan bien 4 proposals, tu phan bien, 5 debate points (D1-D5), bang so sanh tong hop |
| 2 | 2026-03-26 | claude_code | Concessions: rut Topic 018/SSS/EPC/APE code-gen. Giu GFS depth-1 + bounded ideation. Them CL-09/10, NEW-01 (APE). Unified OI numbering. |
| 3 | 2026-03-26 | claude_code | Push closure: de xuat CL-11 (bounded ideation), CL-12 (domain hook), CL-13 (3-layer lineage), CL-14 (contradiction registry) voi steel-man day du. Thu hep OI-03 gap (GFS = grammar enumeration, ChatGPT Pro da chap nhan). Merge NEW-01 ChatGPT Pro vao OI-08. Flag Gemini numbering divergence. |

---

**Status Table (required by `debate/rules.md` §11)**

| Issue ID | Diem | Phan loai | Trang thai | Steel-man vi tri cu | Ly do bac bo steel-man |
|---|---|---|---|---|---|
| OI-01 | Pre-lock generation lane ownership | Judgment call | PARTIAL | "Can Topic 018 rieng vi 006/017 scope khong cover generation" | Fold conditions testable: chi mo topic moi khi closure gap explicit |
| OI-02 | Bounded ideation lane vs SSS | Judgment call | CONVERGED (proposed) | "SSS truc tiep tai tao VDO origin" | VDO value tu composition, khong tu session format; GFS covers composition; bounded lane covers insight |
| OI-03 | Depth-1 grammar enumeration bat buoc | Thieu sot | PARTIAL | "v1 khong can enumeration, bounded ideation du" | Empty registry pressure test; "exhaustive scan" can objects to scan; ChatGPT Pro da chap nhan mechanism |
| OI-04 | 3-layer lineage split | Thieu sot | CONVERGED (proposed) | "Single schema don gian hon" | Feature vs candidate co invalidation semantics khac nhau |
| OI-05 | Surprise criteria dimensions | Thieu sot | PARTIAL | — | — |
| OI-06 | Contradiction registry schema | Judgment call | CONVERGED (proposed) | "Negative evidence xung dang artifact rieng" | MK-17 ceiling; same-dataset activation inert; shadow-only du |
| OI-07 | Domain-seed provenance hook | Judgment call | CONVERGED (proposed) | "Domain cross-pollination la core mechanism" | VDO value tu composition, khong tu domain; hook giu trail |
| OI-08 | Cell dimensions + equivalence + correction | Thieu sot | PARTIAL | — | — |
| NEW-01 (Claude) | APE v1 = parameterization only | Thieu sot | PARTIAL | — | — |
