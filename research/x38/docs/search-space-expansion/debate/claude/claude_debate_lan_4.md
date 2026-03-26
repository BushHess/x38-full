---
doc_type: debate_round_review
topic: search-space-expansion
round: 4
author: claude_code
date: 2026-03-26
status: OPEN
sources:
  - ../../request.md
  - ../gemini/gemini_propone.md
  - ../codex/codex_propone.md
  - ./claude_propone.md
  - ../chatgptpro/chatgptpro_propone.md
  - ../gemini/gemini_debate_lan_3.md
  - ../codex/codex_debate_lan_3.md
  - ./claude_debate_lan_3.md
  - ../chatgptpro/chatgptpro_debate_lan_3.md
  - ../../../online_vs_offline.md
  - ../../../design_brief.md
  - ../../../../debate/rules.md
  - ../../../../debate/017-epistemic-search-policy/findings-under-review.md
  - ../../../../debate/006-feature-engine/findings-under-review.md
  - ../../../../debate/015-artifact-versioning/findings-under-review.md
  - ../../../../debate/013-convergence-analysis/findings-under-review.md
  - ../../../../debate/008-architecture-identity/findings-under-review.md
  - ../../../../debate/003-protocol-engine/findings-under-review.md
  - ../../../../debate/004-meta-knowledge/final-resolution.md
  - ../../../../debate/002-contamination-firewall/final-resolution.md
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

# Debate Round 4 — Steel-man Confirmation, Depth-1 Resolution, Interface Lock for Multiplicity

## 1. Ket luan nhanh

Round 3 da thu hep gap xuong 2 cau hoi thuc chat: (1) depth-1 grammar enumeration la "mandatory" hay "default cold-start" — gap nay la naming, khong phai structural, vi 4/4 agents da include depth-1 enumeration trong backbone; (2) multiplicity/equivalence interface contract (OI-08 + NEW-01 ChatGPT Pro) — duy nhat cau hoi nay con tranh chap chi tiet thuc su.

Round 4: (a) yeu cau §7(c) steel-man confirmation cho CL-11/12/13/14; (b) de xuat convergence moi cho OI-01, OI-03, OI-05, NEW-01 (Claude); (c) khoa interface obligations cho OI-08 va day exact laws/thresholds xuong downstream topics.

Governance note: OI numbering van diverge giua agents. Claude/ChatGPT Pro dung chung unified scheme (8 OIs + 2 NEW-01). Codex dung 6 OIs. Gemini dung 2 OIs. Substance map duoc — xem mapping table tai §7. De xuat: tu R5, moi agent ghi mapping khi reference OI ngoai scheme cua minh.

---

## 2. Scoreboard

Mot dieu chinh so voi Round 3:
- **Gemini**: Tang "Do ro artifact" (Trung binh -> Tot) vi R3 stance cu the tren OI-03/OI-08. Van yeu o breadth (chi address 2/9+ unified OIs).
- Cac agents khac giu nguyen.

| Agent | Bam yeu cau | Bam X38 | Kha thi v1 | Suc mo search | Ky luat contamination | Do ro artifact | Verdict ngan |
|-------|-------------|---------|------------|---------------|----------------------|----------------|--------------|
| Gemini | Rat tot | Rat tot | Rat tot | Tot | Rat tot | Tot | GFS mandatory + static metrics; can address nhieu OIs hon |
| Codex | Rat tot | Rat tot | Tot | Tot | Tot | Rat tot | Backbone manh nhat; §7 governance dung; can explicit stance tren steel-mans |
| Claude | Rat tot | Tot | Tot | Rat tot | Tot | Tot | Push closure dung timing; risk over-numbering CLs |
| ChatGPT Pro | Rat tot | Rat tot | Rat tot | Tot | Rat tot | Rat tot | Contract discipline tot nhat; Holm default overreach scope |

---

## 3. Convergence Ledger (cap nhat)

### 3.1 CL-01 den CL-10: giu nguyen tu Round 2/3.

### 3.2 CL-11 den CL-14: yeu cau xac nhan steel-man §7(c)

Round 3 da cung cap steel-man tests §7(a)(b). Theo `debate/rules.md` §7(c), ben kia can xac nhan: "Dung, do la argument manh nhat" hoac "Khong, argument manh nhat la [X]".

| CL | Ket luan | Steel-man R3 | Ben can xac nhan |
|----|---------|-------------|-----------------|
| CL-11 | Bounded ideation thay SSS; 4 hard rules | "SSS truc tiep tai tao VDO origin story" | Codex, ChatGPT Pro, Gemini |
| CL-12 | Domain-seed = optional provenance hook | "Cross-domain cross-pollination la co che thuc su" | Codex, ChatGPT Pro |
| CL-13 | 3-layer lineage split | "Single schema don gian hon" | Codex, ChatGPT Pro |
| CL-14 | Contradiction registry = descriptor-level shadow-only | "Contradiction xung dang artifact rieng" | Codex, ChatGPT Pro |

**Cross-agent confirmation status**:
- ChatGPT Pro R3 doc lap chot CL-09 (≈CL-11) va CL-10 (≈CL-14). Day la implicit §7(c) confirmation voi substance tuong duong.
- Codex R3 substantively dong y 4/4 nhung giu §7 procedural objection ("No new CONVERGED vi steel-man chua qua §7(c)"). Toi ton trong governance nay — nhung Codex R4 CAN xac nhan hoac reject steel-mans.
- Gemini R3 khong address CL-11/12/13/14 truc tiep (chi co OI-03 va OI-08).

**De xuat**: Neu khong co agent nao trong R4 (a) reject steel-man hoac (b) de xuat alternative manh hon, thi CL-11/12/13/14 chuyen sang CONVERGED chinh thuc tai R5. Im lang = khong co argument manh hon de trinh bay, per §7(c) spirit.

### 3.3 De xuat convergence moi

| ID | Ket luan hoi tu | Basis | Status |
|----|----------------|-------|--------|
| CL-15 | **Depth-1 grammar enumeration la mandatory mechanism trong framework va default cold-start generation mode. `registry_only` hop le khi registry non-empty tai protocol lock (requires `grammar_hash` match). Coupled voi multiplicity interface (OI-08).** | OI-03: 4/4 R3 | CONVERGED (proposed) |
| CL-16 | **Pre-lock ownership fold: 006 = generation + operator grammar + compile; 015 = lineage/invalidation; 017 = coverage/archive/surprise/budget. Topic moi chi khi closure report co explicit "unresolved gap" khong quy duoc ve topic nao.** | OI-01: 4/4 R2-R3 | CONVERGED (proposed) |
| CL-17 | **Surprise criteria v1: 4 mandatory dimensions (decorrelation, risk-profile, plateau, consistency). Queue input phai co >= 1 non-peak-score dimension. Surprise = triage priority. Exact thresholds do 017 chot.** | OI-05: Claude/ChatGPT Pro/Codex R3 | CONVERGED (proposed) |
| CL-18 | **APE v1 = config-level parameterization only (lookback, threshold, cost). Khong code generation. Naming: "parameter sweep". Owner: 006.** | NEW-01 (Claude): 4/4 implicit R2-R3 | CONVERGED (proposed) |

### Steel-man tests cho CL-15 den CL-18

**CL-15 (Depth-1 = default cold-start, not mandatory every campaign):**

- Steel-man cho "mandatory EVERY campaign": Moi campaign phai re-enumerate tu dau vi grammar co the mo rong va dataset moi co the thay doi feature relevance. Cho phep `registry_only` tao precedent cho operators bo qua enumeration, khien "exhaustive scan over declared space" (`docs/online_vs_offline.md:35`) bi pham.

- Tai sao steel-man khong du: `registry_only` chi hop le khi (a) registry da non-empty va (b) `grammar_hash` match current grammar. Neu grammar da thay doi, registry khong khop va protocol lock se reject. Neu grammar khong doi, re-enumerate cho cung ket qua (deterministic) — chi phi compute ~ vai gio tren single machine la nho nhung khong zero. Dataset thay doi khong invalidate features vi features la deterministic transforms cua grammar, khong cua data. V1 protocol PHAI validate `registry.count > 0` AND `registry.grammar_hash == current_grammar_hash` tai lock — dam bao registry khong trong va khong stale.

- Evidence: `./claude_debate_lan_3.md:172-199`; `../chatgptpro/chatgptpro_debate_lan_3.md:88-94`; `../codex/codex_debate_lan_3.md:112-118`; `docs/online_vs_offline.md:35`

**CL-16 (Ownership fold, khong Topic 018):**

- Steel-man cho "Topic 018 umbrella": 006/017 scope khong cover generation mechanism. 006 = registry, 017 = intra-campaign search. Generation (depth-1, bounded ideation, future APE) co lifecycle, interface, va testing obligations rieng — xung dang topic rieng.

- Tai sao steel-man khong du: 006 scope DA bao gom "operator grammar + feature DSL + generation modes + compile-to-manifest" (Codex R3 OI-01 `../codex/codex_debate_lan_3.md:104-109`; ChatGPT Pro R3 OI-01 `../chatgptpro/chatgptpro_debate_lan_3.md:80-86`). Depth-1 enumeration la mot generation mode trong 006. Bounded ideation output compile-to-manifest la 006 responsibility. Lifecycle/testing la concerns chung cho moi topic. Chi khi 006/017 close ma van con explicit "unresolved gap" section khong quy duoc ve topic nao — khi do moi mo topic hep (khong umbrella). `debate/rules.md` §12 cam mo topic moi sau vong 1; gap phai duoc xu ly trong existing topics truoc.

- Evidence: `../codex/codex_debate_lan_3.md:104-109`; `../chatgptpro/chatgptpro_debate_lan_3.md:80-86`; `./claude_debate_lan_3.md:110-129`; `debate/rules.md` §12

**CL-17 (4 surprise dimensions, khong chi IC + orthogonality):**

- Steel-man cho "IC + orthogonality la du" (Gemini position): Information Coefficient va orthogonality co decades quantitative research backing. 4 named dimensions (decorrelation, risk-profile, plateau, consistency) chi la IC/orthogonality voi ten goi khac — tai sao them complexity?

- Tai sao steel-man khong du: IC do predictive power cua MOT feature over returns — dung cho feature screening (Stage 3), khong phai candidate recognition (Stage 7). Candidate recognition can multi-dimensional surprise: low IC but exceptional plateau width (plateau champion), extreme cost stability (consistency champion), low Sharpe but best MDD (risk-profile outlier). "Decorrelation" ≈ orthogonality, dong y — nhung 3 dimensions con lai (risk-profile, plateau, consistency) KHONG la special cases cua IC. IC subsumes vao decorrelation dimension, khong thay the 4 dimensions.

- Evidence: `../gemini/gemini_propone.md`; `../gemini/gemini_debate_lan_3.md:70-75`; `./claude_debate_lan_3.md:223-248`; `../chatgptpro/chatgptpro_debate_lan_3.md:104-126`; `debate/017-epistemic-search-policy/findings-under-review.md` X38-ESP-01

**CL-18 (APE v1 = parameterization only, khong code generation):**

- Steel-man cho "full APE code generation in v1": Code generation tao ra strategy STRUCTURES moi ma parameter variation khong the. VDO la structural innovation (volume * direction = new feature). Khong co code generation, v1 gioi han o variations cua seeded architectures.

- Tai sao steel-man khong du: Code generation chua co correctness guarantee — moi generated strategy can automated testing (unit test, data validation, behavior test) ma v1 pipeline chua co. Structural innovation den tu bounded ideation lane: human/AI propose structure, compile-to-manifest, validate. Code generation la shortcut bypass human review — chinh xac failure mode ma `docs/online_vs_offline.md` canh bao (AI tao code chay truc tiep trong pipeline). Parameterization + bounded ideation da cover: params vary within proven structure (exhaustive), ideas create new structures through human-verified channel (bounded).

- Evidence: `./claude_debate_lan_2.md:313-329`; `../chatgptpro/chatgptpro_debate_lan_2.md:186`; `docs/online_vs_offline.md`

---

## 4. Open Issues Register — Phan hoi vong 4

### OI-01 — Pre-lock generation lane ownership

- **Stance**: AGREE — push to CONVERGED (CL-16)
- **Diem dong y**: 4/4 agents R2-R3 dong huong fold. Codex R3: 006=producer/compilation, 015=lineage/invalidation, 017=coverage/surprise/budget (`../codex/codex_debate_lan_3.md:104-109`). ChatGPT Pro R3: same split + trigger condition (`../chatgptpro/chatgptpro_debate_lan_3.md:80-86`). Gemini R3 khong address truc tiep nhung khong contradict.
- **Diem phan doi**: Khong con tranh chap thuc chat.
- **De xuat sua**: Chuyen sang CL-16. Steel-man provided above.
- **Evidence**: Xem CL-16 steel-man.
- **Trang thai**: CONVERGED (proposed CL-16)

---

### OI-02 — Bounded ideation lane contract

- **Trang thai**: CONVERGED (CL-11, proposed R3). Cho §7(c) confirmation — xem §3.2.

---

### OI-03 — GFS depth-1 / grammar enumeration

- **Stance**: AMEND — push to CONVERGED (CL-15)

- **Diem dong y**:
  4/4 agents R3 include depth-1 enumeration trong backbone. Gap con lai la framing:
  - Claude R3: "mandatory mechanism" (`./claude_debate_lan_3.md:192`)
  - ChatGPT Pro R3: "default cold-start path, `registry_only` when non-empty" (`../chatgptpro/chatgptpro_debate_lan_3.md:92`)
  - Gemini R3: "MUST-HAVE prerequisite" (`../gemini/gemini_debate_lan_3.md:66-67`)
  - Codex R3: "accepts substance as producer candidate" (`../codex/codex_debate_lan_3.md:112-118`)

  ChatGPT Pro framing la cleanest resolution: depth-1 la mandatory mechanism (phai ton tai nhu code/capability) va default generation mode (active by default). `registry_only` valid khi registry non-empty + grammar_hash match — dam bao khong co "skip enumeration" loophole ma van cho phep re-runs tren established registry.

- **Diem phan doi**:
  - Codex R3 giu "mandatory hay optional van la phan con mo" — nhung Codex backbone da INCLUDE "compiled manifest -> descriptor tagging -> coverage map". `compiled manifest` tu dau? Tu grammar enumeration hoac bounded ideation. `registry_only` requires prior manifest. Nen Codex substance = depth-1 la one of two producers, khong phai optional afterthought.
  - Gemini R3 muon "hardcoded bounds" — cuc doan hon can thiet. Bounds duoc declare trong protocol config, khong hardcode trong engine code. Config-level declaration van la offline deterministic.
  - Coupling voi multiplicity: ChatGPT Pro R3 (`../chatgptpro/chatgptpro_debate_lan_3.md:92-93`) + Claude R3 (`./claude_debate_lan_3.md:192`) dong y. Depth-1 chi activate sau khi multiplicity interface declared (-> OI-08 interface).

- **De xuat sua**: Accept ChatGPT Pro framing:
  - Protocol config field: `generation_mode` voi values: `grammar_depth1_seed` (default), `registry_only` (requires non-empty registry + grammar_hash match), `grammar_depth1_seed + bounded_ideation` (both active).
  - Protocol lock validation: `registry.count > 0` AND `registry.grammar_hash == current_grammar_hash`.
  - Depth-2+, APE codegen, GA/continuous mutation: DEFER.
  - Coupling: `generation_mode` chi activate sau khi multiplicity interface (comparison_domain, correction_method, equivalence_method) declared.
  - Chuyen sang CL-15.

- **Evidence**: `../chatgptpro/chatgptpro_debate_lan_3.md:88-94`; `../codex/codex_debate_lan_3.md:112-118`; `../gemini/gemini_debate_lan_3.md:64-68`; `./claude_debate_lan_3.md:156-201`; `docs/online_vs_offline.md:35`
- **Trang thai**: CONVERGED (proposed CL-15)

---

### OI-04 — Canonical lineage 3-layer split

- **Trang thai**: CONVERGED (CL-13, proposed R3). Cho §7(c) confirmation — xem §3.2.

---

### OI-05 — Recognition stack + surprise criteria

- **Stance**: AGREE — push to CONVERGED (CL-17)

- **Diem dong y**:
  - Stack v1 dong huong 4/4: `surprise_queue -> equivalence_audit -> proof_bundle -> comparison_set -> phenotype -> contradiction (shadow)`.
  - 4 dimensions: Claude R3 (`./claude_debate_lan_3.md:223-248`), ChatGPT Pro R3 dong y non-peak-score + consistency motif (`../chatgptpro/chatgptpro_debate_lan_3.md:104-126`), Codex R3 dong y structure (`../codex/codex_debate_lan_3.md:120-126`).
  - Thresholds deferred to 017: 4/4 dong y.
  - Surprise = triage, khong phai winner privilege: 4/4 dong y.

- **Diem phan doi**:
  Gemini R3 de xuat "corr + IC" (`../gemini/gemini_debate_lan_3.md:72-74`). Nhung IC la sub-dimension cua decorrelation — khong conflict voi 4 mandatory dimensions. 4 dimensions la SUPERSET cua IC + orthogonality. Steel-man addressed at CL-17 above.

- **De xuat sua**: Chuyen sang CL-17. 017 chot exact trigger thresholds. 013 chot comparison domain cho equivalence_audit. Proof bundle minimum inventory do 003/015 chot khi stage gating finalized.
- **Evidence**: Xem CL-17 steel-man.
- **Trang thai**: CONVERGED (proposed CL-17)

---

### OI-06 — Contradiction registry schema

- **Trang thai**: CONVERGED (CL-14, proposed R3). Cho §7(c) confirmation — xem §3.2.

---

### OI-07 — Domain-seed optional provenance hook

- **Trang thai**: CONVERGED (CL-12, proposed R3). Cho §7(c) confirmation — xem §3.2.

---

### OI-08 — Cell dimensions + equivalence + correction + multiplicity

- **Stance**: AMEND — push to PARTIAL (interface CONVERGED, exact laws DEFERRED)

- **Diem dong y (interface layer — de xuat converge)**:

  1. **Interface obligations**: Protocol PHAI declare `comparison_domain`, `scan_phase_correction_method`, `equivalence_method`, `invalidation_scope` TRUOC khi breadth activation. 4/4 dong y (`../chatgptpro/chatgptpro_debate_lan_3.md:130-133`; `../codex/codex_debate_lan_3.md:144-150`; `./claude_debate_lan_3.md:293-310`; `../gemini/gemini_debate_lan_3.md:72-74`).

  2. **Comparison domain default**: `paired_daily_returns` (after costs) tren shared evaluation segment. ChatGPT Pro R3 de xuat cu the (`../chatgptpro/chatgptpro_debate_lan_3.md:132`), Claude R3 dong y, Codex R3 accepts implicitly.

  3. **Cell axes structure**: 4+ mandatory axes (mechanism_family, architecture_depth, turnover_bucket, timeframe_binding). Exact axis list va values do 017 chot. ChatGPT Pro R3 de xuat 5 axes + annotations (`../chatgptpro/chatgptpro_debate_lan_3.md:124`); gap nho (holding_bucket vs turnover_bucket) la implementation detail cho 017.

  4. **Equivalence v1**: Hybrid = descriptor pre-bucket + paired-return distance. 4/4 dong huong. AST-hash (Gemini) la subset cua descriptor pre-bucket, khong conflict.

  5. **Invalidation cascade**: Taxonomy/domain/cost-model change invalidate `coverage_map`, `cell_id`, `equivalence_clusters`, `contradiction_registry`. Raw lineage (`feature_lineage`, `candidate_genealogy`) giu nguyen vi mo ta generation khong evaluation. ChatGPT Pro R3 (`../chatgptpro/chatgptpro_debate_lan_3.md:132`), Claude R3 dong y.

  6. **NEW-01 (ChatGPT Pro) merged**: Multiplicity control = coupled constraint cho breadth. Da absorb vao OI-08 tu Round 3.

- **Diem phan doi (exact laws — DEFER cho downstream)**:

  1. **Correction law**: ChatGPT Pro R3 de xuat Holm lam default cho Stage 3 (`../chatgptpro/chatgptpro_debate_lan_3.md:132`). Toi AMEND: Holm la reasonable candidate default nhung search-space-expansion debate KHONG PHAI noi chot statistical methodology. Ly do:
     - 013 own correction law per `debate/013-convergence-analysis/findings-under-review.md` X38-CA-01.
     - Search-space-expansion chot INTERFACE obligation ("protocol phai declare method"), khong chot IMPLEMENTATION ("method phai la Holm").
     - Chon Holm vs FDR phu thuoc vao breadth cua search space — thong tin ma v1 chua co cho den khi depth-1 thuc su chay va report so luong features.
     - ChatGPT Pro R3 yeu cau "ben phan doi phai dua ra contract thay the hoan chinh" (`../chatgptpro/chatgptpro_debate_lan_3.md:232`). Contract: `scan_phase_correction_method` la required field trong protocol config, protocol lock reject neu khong co. 013 recommend default; operator chon. Day khong phai "de topic sau" — day la dung ownership boundary.

  2. **Exact cell axes count/values**: 4 vs 5 mandatory — gap nho. 017 owns.

  3. **Equivalence thresholds**: Chua co evidence de chot. 013/017 owns.

  4. **Gemini's AST-hash + Euclidean**: Qua hep. AST-hash chi detect syntactic duplicates — hai strategies dung cung logic nhung cau truc code khac se miss. Euclidean tren parameter vector khong capture structural similarity (ema(20) vs zscore(20) co cung lookback nhung khac operator family). Hybrid bao phu rong hon va INCLUDE static metrics nhu subset. De xuat: Gemini accept hybrid nhu superset.

- **De xuat sua**:
  - Chot OI-08 interface layer (5 obligations above) va chuyen phan nay sang status "interface CONVERGED".
  - Remaining: exact correction law default -> 013. Cell axes exact list -> 017. Equivalence thresholds -> 013/017.
  - Search-space-expansion topic co the close OI-08 khi all agents dong y interface la du. Downstream topics take over exact parameterization.

- **Evidence**: `../chatgptpro/chatgptpro_debate_lan_3.md:120-134`; `../codex/codex_debate_lan_3.md:144-150`; `../gemini/gemini_debate_lan_3.md:70-75`; `./claude_debate_lan_3.md:288-310`; `debate/013-convergence-analysis/findings-under-review.md` X38-CA-01; `debate/017-epistemic-search-policy/findings-under-review.md` X38-ESP-01

- **Trang thai**: PARTIAL — interface converged, exact laws deferred cho downstream (013, 017, 008).

---

### NEW-01 (Claude) — APE v1 scope

- **Stance**: AGREE — push to CONVERGED (CL-18)
- **Diem dong y**: 4/4 implicit/explicit agree: v1 = parameterization only. ChatGPT Pro R3 defer APE codegen (`../chatgptpro/chatgptpro_debate_lan_3.md:192-193`). Gemini R3 gioi han v1 tai "Grid + Random Mutation" (`../gemini/gemini_debate_lan_3.md:113`). Codex R3 khong de cap APE = khong con tranh chap.
- **De xuat sua**: Chuyen sang CL-18. Steel-man provided above.
- **Evidence**: Xem CL-18 steel-man.
- **Trang thai**: CONVERGED (proposed CL-18)

---

## 5. Per-Agent Critique (delta vong 4)

### 5.1 Gemini

**Delta**: R3 focused hon R2 — stance cu the tren GFS mandatory va static metrics. Nhung van chi address 2 trong 9+ unified OIs. Nhieu proposed CLs (11-14, OI-01, OI-04, OI-05, OI-06, OI-07) khong co Gemini explicit position. Day tao bat doi xung per `debate/rules.md` §14b.

**De xuat**: Gemini R4 nen address tat ca unified OIs hoac explicitly declare "no position" cho OIs ngoai core thesis. Dac biet: CL-11 (bounded ideation) va CL-13 (lineage split) anh huong truc tiep den Gemini's prompt ancestry proposal — im lang tren chung la governance gap.

**Diem manh**: GFS mandatory = aligned voi consensus direction. Anti-sandbox consistent.
**Diem yeu**: AST-hash + Euclidean equivalence qua hep — hybrid (descriptor + paired-return) la superset da duoc 3/4 chap nhan. Can accept hybrid.

### 5.2 Codex

**Delta**: R3 principled nhat ve governance — no premature convergence per §7. `pre_lock_authoring_contract` la dong gop structural tot. Tuy nhien, procedural caution co risk lam cham convergence khi substance da aligned 4/4.

**De xuat**: Codex R4 nen explicitly address steel-mans cho CL-11/12/13/14. Co 3 options: (a) "Dung, do la argument manh nhat" — confirm va move to CONVERGED; (b) "Khong, argument manh nhat la [X]" — cung cap alternative; (c) reject convergence voi substantive reason. Im lang sau 2 rounds la governance gap tuong tu voi Gemini.

**Diem manh**: Substance aligned tren moi OI. Backbone clean.
**Diem yeu**: Codex OI numbering (6 OIs) van diverge — mapping table tai §7 de giai quyet.

### 5.3 ChatGPT Pro

**Delta**: R3 la strongest round cua debate. CL-09/CL-10 independent confirmation. `grammar_depth1_seed` framing resolve OI-03 gap. NEW-01 candidate contract specific.

**Diem manh**: Contract discipline, ownership split, cold-start resolution, multiplicity coupling.
**Diem yeu**: Holm default tai search-space-expansion debate overreach scope — 013 own statistical methodology. Yeu cau "ben phan doi phai dua ra contract thay the" la fair, nhung contract toi de xuat la ownership-based: `scan_phase_correction_method = required field, 013 recommend default`. Day la contract, khong phai "de topic sau".

### 5.4 Claude (self-critique)

**Delta**: R3 push closure voi 4 steel-man tests la dung approach. R4 push them 4 CLs nua (15-18). Risk: 8 proposed CLs trong 2 rounds co ve rush convergence. Mitigation: moi CL co steel-man day du, moi convergence co basis tu 4/4 agents.

**Tu phan bien**:
- Over-numbering: CL-11 den CL-18 la nhieu. Nhung moi CL dai dien 1 converged conclusion cu the, khong phai padding. Tat ca deu traceable den §7 process.
- Toi co the da under-weight Codex's §7 concern — Codex dung khi noi rang §7(c) can explicit confirmation. Toi da address bang way: request confirmation, note that silence after 2 rounds la implicit, va ghi ro mapping.
- Gap lon nhat con lai: OI-08 interface vs exact laws. Toi da chon dung ranh gioi — search-space-expansion owns interface, downstream owns parameterization. Nhung ChatGPT Pro co the thay rang "interface without default" la rong. Toi accept nay nhu genuine remaining dispute.

---

## 6. Interim Merge Direction (cap nhat)

### 6.1 Backbone v1

```
Pre-lock:
  [Bounded ideation lane (CL-11)]  --> proposal_spec
  [Grammar depth-1 seed (CL-15)]   --> compiled_manifest
  Both --> 006 registry compilation (grammar check, dedup)
           |
Protocol Lock (CL-15 validation: registry.count > 0, grammar_hash match,
               OI-08 interface: comparison_domain + correction_method + equivalence_method declared)
  |
  v
Stage 3: Exhaustive scan (deterministic, offline, no AI)
  --> Descriptor tagging
  --> Coverage map (4+ cell axes per CL-17/017)
  --> Cell-elite archive (CL-05)
  --> Local neighborhood probes
  |
Stage 4-6: Layered search + probes (design_brief)
  |
Stage 7: Freeze
  --> Surprise queue (CL-17: 4 dimensions, non-peak-score required)
  --> Equivalence audit (OI-08: hybrid descriptor + paired-return)
  --> Proof bundle (minimum: rival audit, plateau, cost, ablation, contradiction)
  --> Comparison set (frozen)
  --> Candidate phenotype (CL-09)
  --> Contradiction registry (CL-14: descriptor-level, shadow-only)
  |
Stage 8: Holdout + reserve + epistemic delta
```

### 6.2 Adopt ngay (cumulative)

| # | Artifact / Mechanism | Nguon CL/OI | Owner |
|---|---------------------|-------------|-------|
| 1 | Bounded ideation lane (4 hard rules + schema-aware, results-blind) | CL-11 | 006 + 015 |
| 2 | Grammar depth-1 seed (default cold-start) | CL-15 (proposed) | 006 |
| 3 | Ownership split: 006 generate, 015 lineage, 017 coverage | CL-16 (proposed) | 006/015/017 |
| 4 | 3-layer lineage: feature_lineage + candidate_genealogy + proposal_provenance | CL-13 | 015 + 006 |
| 5 | Cell-elite archive + 4 surprise dimensions | CL-05 + CL-17 (proposed) | 017 |
| 6 | Contradiction registry (descriptor-level shadow-only) | CL-14 | 017 + 015 |
| 7 | Domain-seed = optional provenance hook | CL-12 | 015 |
| 8 | Parameter sweep (APE v1) | CL-18 (proposed) | 006 |
| 9 | Multiplicity interface bundle | OI-08 interface | 013 + 015 + 017 |

### 6.3 Defer (khong doi tu R3)

| # | Artifact / Mechanism | Ly do defer |
|---|---------------------|-------------|
| 1 | Topic 018 umbrella | CL-16: fold sufficient |
| 2 | SSS first-class | CL-11: replaced |
| 3 | GFS depth 2/3, APE codegen, GA/mutation | Compute/correctness risk |
| 4 | CDAP / domain catalog as core | CL-12: hook only |
| 5 | Full EPC lifecycle / activation ladder | MK-17 ceiling |
| 6 | Exact correction law / thresholds | 013 owns |

### 6.4 Ownership tam (khong doi tu R3)

| Topic | Ganh gi |
|-------|---------|
| 006 | Operator grammar, feature DSL, generation modes, depth-1 seed, compile-to-manifest, parameter sweep, feature descriptor core |
| 015 | feature_lineage, candidate_genealogy, proposal_provenance, invalidation rules |
| 017 | Coverage, cell archive, probes, surprise, phenotype/contradiction shadow, budget |
| 013 | Common comparison domain, correction law, convergence/diminishing-returns |
| 008 | Identity vocabulary, equivalence categories |
| 003 | Stage insertion, required artifacts, freeze/gating wiring |

---

## 7. Agenda vong sau (Round 5)

### Issues status summary

| OI (unified) | Codex mapping | Gemini mapping | Trang thai | Can chot R5 |
|-------------|---------------|----------------|-----------|-------------|
| OI-01 | OI-01 | — | CL-16 proposed | §7(c) confirm |
| OI-02 | OI-02 part | — | CL-11 proposed R3 | §7(c) confirm |
| OI-03 | OI-02 part | OI-03 | CL-15 proposed | §7(c) confirm |
| OI-04 | OI-04 | — | CL-13 proposed R3 | §7(c) confirm |
| OI-05 | OI-03 | — | CL-17 proposed | §7(c) confirm |
| OI-06 | OI-05 | — | CL-14 proposed R3 | §7(c) confirm |
| OI-07 | — | — | CL-12 proposed R3 | §7(c) confirm |
| OI-08 | OI-06 | OI-08 | PARTIAL | Interface converged, exact laws → downstream |
| NEW-01 ChatGPT Pro | OI-06 part | — | Merged into OI-08 | — |
| NEW-01 Claude | — | — | CL-18 proposed | §7(c) confirm |

**Trong tam R5**:
1. **Steel-man §7(c) confirmation** cho CL-11/12/13/14 (R3) va CL-15/16/17/18 (R4).
2. **OI-08 final status**: co dong y rang interface layer la du de close OI-08 tai search-space-expansion topic? Exact parameterization chuyen xuong 013/017/008.
3. **Neu tat ca §7(c) xac nhan va OI-08 interface accepted**: topic ready for `final-resolution.md` preparation.

---

## 8. Change Log

| Vong | Ngay | Agent | Tom tat thay doi |
|------|------|-------|-------------------|
| 1 | 2026-03-25 | claude_code | Round mo dau: phan bien 4 proposals, tu phan bien |
| 2 | 2026-03-26 | claude_code | Concessions: rut SSS/Topic 018/EPC/APE codegen |
| 3 | 2026-03-26 | claude_code | Push closure: CL-11/12/13/14 voi steel-man |
| 4 | 2026-03-26 | claude_code | Request §7(c) confirmation. De xuat CL-15 (depth-1 default cold-start), CL-16 (ownership fold), CL-17 (surprise structure), CL-18 (APE param). OI-08 interface converged, exact laws deferred downstream. OI numbering mapping table. |

---

**Status Table (required by `debate/rules.md` §11)**

| Issue ID | Diem | Phan loai | Trang thai | Steel-man vi tri cu | Ly do bac bo steel-man |
|---|---|---|---|---|---|
| OI-01 | Pre-lock generation lane ownership | Judgment call | CONVERGED (proposed CL-16) | "006/017 khong cover generation — can Topic 018" | 006 scope da bao gom generation modes + compile; §12 cam topic moi |
| OI-02 | Bounded ideation lane vs SSS | Judgment call | CONVERGED (CL-11, awaiting §7c) | "SSS tai tao VDO origin" | VDO value tu composition, khong session format |
| OI-03 | Depth-1 grammar enumeration | Thieu sot | CONVERGED (proposed CL-15) | "Mandatory EVERY campaign" | registry_only valid khi non-empty + grammar_hash match; re-enumerate deterministic |
| OI-04 | 3-layer lineage split | Thieu sot | CONVERGED (CL-13, awaiting §7c) | "Single schema don gian hon" | Feature vs candidate co invalidation semantics khac nhau |
| OI-05 | Surprise criteria structure | Thieu sot | CONVERGED (proposed CL-17) | "IC + orthogonality du" | IC = feature screening metric; candidate recognition can 4 dimensions |
| OI-06 | Contradiction registry schema | Judgment call | CONVERGED (CL-14, awaiting §7c) | "Contradiction xung dang artifact rieng" | MK-17 ceiling; shadow-only du |
| OI-07 | Domain-seed provenance hook | Judgment call | CONVERGED (CL-12, awaiting §7c) | "Cross-pollination la core mechanism" | VDO value tu composition; hook giu trail |
| OI-08 | Cell dimensions + equivalence + correction + multiplicity | Thieu sot | PARTIAL | — | Interface converged; exact laws open cho downstream |
| NEW-01 (Claude) | APE v1 = parameterization only | Thieu sot | CONVERGED (proposed CL-18) | "Code generation tao structural innovation" | Correctness guarantee chua co; bounded ideation + parameterization du |
