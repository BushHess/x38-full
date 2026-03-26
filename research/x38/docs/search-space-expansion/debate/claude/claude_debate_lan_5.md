---
doc_type: debate_round_review
topic: search-space-expansion
round: 5
author: claude_code
date: 2026-03-26
status: OPEN
sources:
  - ../../request.md
  - ../gemini/gemini_debate_lan_4.md
  - ../codex/codex_debate_lan_4.md
  - ./claude_debate_lan_4.md
  - ../chatgptpro/chatgptpro_debate_lan_4.md
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

# Debate Round 5 — §7(c) Resolution, OI-08 Interface Lock, Termination Assessment

## 1. Ket luan nhanh

Round 4 xac nhan substance alignment 4/4 tren moi OI. Round 5 xu ly 3 viec: (1) §7(c) cho CL-11/12/13/14 sau 2 rounds khong co rejection; (2) cross-agent validation cua CL-15/16/17/18 (R4); (3) CL-19 (proposed) khoa OI-08 interface layer. Sau xu ly, moi unified OI dat CONVERGED hoac DEFER. Residual parameterization (exact correction law, cell thresholds, equivalence distances, field enumeration) thuoc downstream topics (013/017/008/015). Topic search-space-expansion san sang cho synthesis.

---

## 2. Scoreboard

Delta tu Round 4:

- **ChatGPT Pro**: Do ro artifact Tot -> Rat tot. Self-correction tren Holm va holding_bucket (`../chatgptpro/chatgptpro_debate_lan_4.md:57,139`) cho thay intellectual honesty.
- **Codex**: Ky luat contamination Tot -> Rat tot. R4 contract enforcement principled va consistent.
- **Gemini**: Kha thi v1 Rat tot -> Tot. CL-06 (AST-only equivalence) xung dot 3:1 voi consensus hybrid; R4 declares done khong address mau thuan.

| Agent | Bam yeu cau | Bam X38 | Kha thi v1 | Suc mo search | Ky luat contamination | Do ro artifact | Verdict ngan |
|-------|-------------|---------|------------|---------------|----------------------|----------------|--------------|
| Gemini | Rat tot | Rat tot | Tot | Tot | Rat tot | Tot | Anti-online deterministic dung; AST-only equivalence isolated 3:1 |
| Codex | Rat tot | Rat tot | Tot | Tot | Rat tot | Rat tot | Substance aligned 100%; procedural §7 governance chinh xac |
| Claude | Rat tot | Tot | Tot | Rat tot | Tot | Tot | Closure push dung timing; §7(c) processing round nay |
| ChatGPT Pro | Rat tot | Rat tot | Rat tot | Tot | Rat tot | Rat tot | Self-correction + contract synthesis manh nhat debate |

---

## 3. Convergence Ledger

### 3.1 CL-01 den CL-10: giu nguyen.

### 3.2 CL-11/12/13/14: §7(c) Resolution

Sau 2 rounds (R3 proposed + R4 re-requested) khong co agent nao reject steel-man hoac de xuat alternative argument manh hon. Xu ly theo §7(c):

**CL-11 — Bounded ideation thay SSS; 4 hard rules:**
- Steel-man (R3): "SSS truc tiep tai tao VDO origin story."
- R4: Codex OI-02 substance aligned — backbone accepted, bounded ideation included (`../codex/codex_debate_lan_4.md:116`). ChatGPT Pro: "SSS/online runtime da chet ve mat kien truc" (`../chatgptpro/chatgptpro_debate_lan_4.md:55`). Gemini: no opposition, declares done.
- §7(c): No rejection, no alternative after 2 rounds. Independent confirmation from ChatGPT Pro. **CONVERGED.**

**CL-12 — Domain-seed = optional provenance hook:**
- Steel-man (R3): "Cross-domain cross-pollination la co che thuc su."
- R4: ChatGPT Pro CL-11 (their numbering) explicitly CONVERGED (`../chatgptpro/chatgptpro_debate_lan_4.md:86`). ChatGPT Pro OI-07 CONVERGED (`../chatgptpro/chatgptpro_debate_lan_4.md:129-134`). Codex OI-04 substance aligned.
- §7(c): ChatGPT Pro independently confirmed. **CONVERGED.**

**CL-13 — 3-layer lineage split:**
- Steel-man (R3): "Single schema don gian hon."
- R4: ChatGPT Pro CL-12 (their numbering) explicitly CONVERGED (`../chatgptpro/chatgptpro_debate_lan_4.md:87`). OI-04 DEFER — semantic split hoi tu, residual la field enumeration cho 015 (`../chatgptpro/chatgptpro_debate_lan_4.md:112-118`). Codex OI-04 substance aligned.
- §7(c): ChatGPT Pro independently confirmed. Field detail = downstream 015. **CONVERGED.**

**CL-14 — Contradiction registry = descriptor-level shadow-only:**
- Steel-man (R3): "Contradiction xung dang artifact rieng va activation lane."
- R4: ChatGPT Pro R3 CL-10 da confirmed. Codex OI-05 substance aligned (shadow-only, no activation in v1 — `../codex/codex_debate_lan_4.md:137-140`). Row shape la downstream 015/017.
- §7(c): ChatGPT Pro confirmed via CL-10. MK-17 ceiling applies. **CONVERGED.**

### 3.3 CL-15/16/17/18: Cross-agent validation (R4 proposals, first response round)

**CL-15 — Depth-1 = mandatory mechanism + default cold-start generation mode:**
- Cross-agent R4:
  - ChatGPT Pro OI-03: "conditional cold-start law" — mandatory khi registry empty, optional voi declaration khi non-empty + frozen seed (`../chatgptpro/chatgptpro_debate_lan_4.md:106-110`). **Substance dong nhat voi CL-15.**
  - Codex OI-02: `grammar_depth1_seed` default cold-start, `registry_only` khi non-empty (`../codex/codex_debate_lan_4.md:117-119`). **Substance dong nhat.**
  - Gemini CL-05: "GFS depth-1 MUST-HAVE" (`../gemini/gemini_debate_lan_4.md:54`). Stronger framing, directionally same.
- 4/4 substance aligned. Framing gap resolved by ChatGPT Pro "conditional cold-start law": mandatory mechanism + conditional activation + grammar_hash validation.
- **Status: CONVERGED.** `generation_mode` state machine details delegated to 006.

**CL-16 — Ownership fold: 006 generate, 015 lineage, 017 coverage:**
- Cross-agent R4:
  - ChatGPT Pro OI-01: PARTIAL — wants closure trigger wording (`../chatgptpro/chatgptpro_debate_lan_4.md:98-102`). Architecture split accepted.
  - Codex OI-01: PARTIAL — wants object boundary (`../codex/codex_debate_lan_4.md:109-112`). Split accepted.
- Both PARTIALs concern implementation detail (wording, object boundary), khong phai architectural disagreement. No agent defends Topic 018.
- **Status: CONVERGED.** Closure trigger: "Topic moi chi khi 006/015 closure report co explicit unresolved gap khong quy duoc ve 006/015/017/003/013/008."

**CL-17 — 5 anomaly axes + 5-component proof bundle (obligation-level):**
- Cross-agent R4:
  - ChatGPT Pro OI-05: Identical obligation-level inventory — 5 anomaly axes (decorrelation, plateau_width, cost_stability, cross_resolution_consistency, contradiction_resurrection) + 5 proof components (`../chatgptpro/chatgptpro_debate_lan_4.md:124`). **Substance dong nhat.**
  - Codex OI-03: Interface-level minimum aligned — "queue input phai mang it nhat mot anomaly axis khong phai peak-score" (`../codex/codex_debate_lan_4.md:125-126`).
- PARTIALs la ve numeric thresholds — CL-17 da defer cho 017/013.
- **Status: CONVERGED.** Thresholds delegated to 017/013.

**CL-18 — APE v1 = parameterization only:**
- No opposition from any agent in R4.
- **Status: CONVERGED.**

### 3.4 CL-19 (proposed) — OI-08 Interface obligations for breadth-expansion

De xuat convergence cho OI-08. 6 diem:

1. **Breadth activation gate**: Protocol MUST declare `comparison_domain`, `equivalence_method`, `scan_phase_correction_method`, `minimum_robustness_bundle` BEFORE breadth activation. (4/4 aligned: ChatGPT Pro CL-13 `../chatgptpro/chatgptpro_debate_lan_4.md:88`, Codex OI-06 `../codex/codex_debate_lan_4.md:146`, Claude OI-08 `./claude_debate_lan_4.md:228`, Gemini implicit.)

2. **Comparison domain v1**: `paired_daily_returns_after_costs` on shared evaluation segment. (ChatGPT Pro R3/R4, Claude R4, Codex R4 direction `../codex/codex_debate_lan_4.md:146`.)

3. **Equivalence v1**: 2-layer hybrid — (a) deterministic structural pre-bucket (descriptor hash, parameter family — includes AST-hash as subset); (b) behavioral nearest-rival audit on comparison domain. No LLM judge. (Claude/ChatGPT Pro/Codex 3/4. Gemini: AST-hash only — isolated, see steel-man below.)

4. **Cell axes v1**: 4 mandatory (`mechanism_family`, `architecture_depth`, `turnover_bucket`, `timeframe_binding`). Additional = annotations. (ChatGPT Pro R4 self-corrected `../chatgptpro/chatgptpro_debate_lan_4.md:140`. Claude/Codex aligned.)

5. **Invalidation cascade**: Taxonomy/domain/cost-model change invalidates `coverage_map`, `cell_id`, `equivalence_clusters`, `contradiction_registry`. Raw lineage preserved. (ChatGPT Pro/Claude R4.)

6. **Exact parameterization** (correction law default, cell values, equivalence thresholds) **DEFERRED** to 013/017/008.

**Steel-man for Gemini AST-hash only position:**

"Behavioral equivalence introduces evaluation-dependency — thay doi cost model hoac evaluation window thay doi equivalence classification. AST-hash + parameter distance la context-free va stable. V1 nen bat dau voi stable metrics."

**Tai sao steel-man khong dung:**

Stability khong phai objective dung — correctness la objective. Hai features cung AST nhung khac cost treatment khong phai economically equivalent; hai features khac implementation nhung paired returns ρ>0.99 LA economically redundant. Muc dich cua equivalence la ngan framework coi redundant candidates nhu independent discoveries — behavioral redundancy la thuc do dung, khong phai code redundancy. AST-hash bat syntactic duplicates (co gia tri nhu pre-filter) nhung miss economic duplicates (khac syntax, cung behavior) va tao false positives (cung syntax, khac behavior khi cost model khac).

Quan trong: hybrid PRESERVES determinism. Ca hai layers deu deterministic (same data + code + seed = same result). Khong LLM. Khong human judgment. Gemini's determinism concern la fully addressed — hybrid chi them coverage. Evidence: `docs/online_vs_offline.md:30-36`.

§14b asymmetry: Gemini R4 declared debate finished before steel-man exchange nay. Asymmetry la acceptable vi interface obligations are substance-independent cua AST-hash position — Gemini's contribution (anti-LLM, deterministic) la fully incorporated.

**Status: CONVERGED (proposed).**

### 3.5 NEW-01 (ChatGPT Pro) resolution

- Coupling with breadth: CONVERGED (CL-19 point 1).
- Default correction formula: DEFER to 013. ChatGPT Pro R4 self-corrected tu Holm push (`../chatgptpro/chatgptpro_debate_lan_4.md:57`). Claude R4 ownership-based contract: `scan_phase_correction_method = required field, 013 recommends default`.
- `paired_daily_returns_after_costs`: Accepted as v1 direction in CL-19 point 2.
- Invalidation cascade: DEFER to 015. Interface-level coverage in CL-19 point 5.
- **Status: CONVERGED** at search-space-expansion level. Residuals DEFER downstream.

---

## 4. Open Issues Register — Phan hoi vong 5

### OI-01 — Pre-lock generation lane ownership

- **Stance**: AGREE — CONVERGED (CL-16)
- **Diem dong y**: 4/4 R4 confirm fold: 006 generate + grammar + compile; 015 lineage + provenance + invalidation; 017 coverage + archive + surprise + budget; 003 stage wiring.
- **Diem phan doi**: ChatGPT Pro R4 va Codex R4 giu PARTIAL cho closure trigger wording. Wording la implementation detail cua topic closure reports (006/015), khong phai architectural decision cua search-space-expansion.
- **De xuat sua**: CL-16 CONVERGED. Closure trigger: "Topic moi chi khi 006/015 closure report co explicit unresolved gap khong quy duoc ve existing topics."
- **Evidence**: `../chatgptpro/chatgptpro_debate_lan_4.md:96-102`; `../codex/codex_debate_lan_4.md:107-112`; `debate/rules.md` §12
- **Trang thai**: CONVERGED (CL-16)

### OI-02 — Bounded ideation lane

- **Trang thai**: CONVERGED (CL-11). §7(c) resolved — xem §3.2.

### OI-03 — Depth-1 grammar / cold-start

- **Stance**: AGREE — CONVERGED (CL-15)
- **Diem dong y**: 4/4 substance dong nhat: depth-1 la mandatory mechanism + conditional cold-start activation. ChatGPT Pro "conditional cold-start law" la cleanest framing.
- **Diem phan doi**: Khong con tranh chap thuc chat. `generation_mode` state machine details la 006 scope.
- **Evidence**: `../chatgptpro/chatgptpro_debate_lan_4.md:104-110`; `../codex/codex_debate_lan_4.md:115-119`; `../gemini/gemini_debate_lan_4.md:54`
- **Trang thai**: CONVERGED (CL-15)

### OI-04 — 3-layer lineage split

- **Trang thai**: CONVERGED (CL-13). §7(c) resolved — xem §3.2. Field enumeration DEFER to 015.

### OI-05 — Recognition stack + surprise criteria

- **Stance**: AGREE — CONVERGED (CL-17)
- **Diem dong y**: Obligation-level structure dong nhat Claude/ChatGPT Pro/Codex. 5 anomaly axes, 5-component proof bundle minimum. Surprise = triage priority. Thresholds deferred to 017/013.
- **Evidence**: `../chatgptpro/chatgptpro_debate_lan_4.md:120-126`; `../codex/codex_debate_lan_4.md:121-126`
- **Trang thai**: CONVERGED (CL-17)

### OI-06 — Contradiction registry

- **Trang thai**: CONVERGED (CL-14). §7(c) resolved — xem §3.2. Row shape DEFER to 015/017.

### OI-07 — Domain-seed hook

- **Trang thai**: CONVERGED (CL-12). §7(c) resolved — xem §3.2.

### OI-08 — Cell dimensions + equivalence + correction + multiplicity

- **Stance**: AGREE — push to CONVERGED (CL-19)
- **Diem dong y**: Interface obligations converged 4/4. Hybrid equivalence 3/4 (Gemini isolated — steel-man at §3.4). 4 mandatory cell axes 3/4 (ChatGPT Pro self-corrected). `paired_daily_returns_after_costs` 3/4. Exact laws DEFER downstream.
- **Diem phan doi**: Gemini CL-06 (AST-hash only) — steel-man addressed §3.4. Determinism preserved in hybrid. §14b asymmetry acknowledged.
- **De xuat sua**: CL-19 CONVERGED. Exact parameterization DEFER to 013/017/008.
- **Evidence**: `../chatgptpro/chatgptpro_debate_lan_4.md:136-142`; `../codex/codex_debate_lan_4.md:143-148`; `../gemini/gemini_debate_lan_4.md:55-56`; `docs/online_vs_offline.md:30-36`
- **Trang thai**: CONVERGED (proposed CL-19)

### NEW-01 (ChatGPT Pro) — Multiplicity control

- **Stance**: AGREE — coupling CONVERGED (CL-19), residuals DEFER
- **Diem dong y**: Coupling locked. Default correction formula = 013 scope. ChatGPT Pro R4 self-corrected on Holm.
- **Evidence**: `../chatgptpro/chatgptpro_debate_lan_4.md:144-150`
- **Trang thai**: CONVERGED at search-space-expansion level. Residuals DEFER to 013/015.

### NEW-01 (Claude) — APE v1 scope

- **Trang thai**: CONVERGED (CL-18). No opposition.

---

## 5. Per-Agent Critique (delta vong 5)

### 5.1 Gemini

**Delta**: R4 declared debate finished. CL-05 (depth-1 MUST-HAVE) aligns voi CL-15. CL-06 (AST-hash only equivalence) la genuine substantive position nhung isolated 3:1. Gemini's core contribution (anti-LLM, anti-online, deterministic enforcement) la fully incorporated trong hybrid. §14b: Gemini exited truoc hybrid steel-man exchange — asymmetry accepted vi Gemini's determinism principle khong bi compromise.

### 5.2 Codex

**Delta**: R4 la principled governance intervention manh nhat debate. Codex dung khi yeu cau §7(c) explicit — ngan premature closure. Tai R5, substance tren moi OI aligned voi convergence direction. Codex's remaining PARTIALs (OI-01 through OI-06 trong Codex scheme) concern downstream detail: field enumeration (015), exact contracts (013), boundary wording (006). Day la legitimate work nhung thuoc downstream topics, khong phai search-space-expansion scope. Neu Codex R5 confirm substance alignment, topic co the close.

### 5.3 ChatGPT Pro

**Delta**: R4 la strongest single round trong debate. Self-correction tren Holm va holding_bucket + CL-11/12/13 + closing OI-04/OI-07 + "conditional cold-start law" — tat ca deu precise va evidence-based. ChatGPT Pro's discipline (yeu cau "contract thay the hoan chinh" tu opponents, dong thoi self-correct khi evidence yeu cau) la gold standard.

### 5.4 Claude (self-critique)

**Delta**: R5 push CL-19 cho OI-08 va termination assessment. Total CLs: 19 trong Claude scheme. Risk: over-proliferating CLs — nhung moi CL map chinh xac 1 substantive decision voi steel-man. Codex's concern ve convergence velocity la legitimate; toi da address bang cach xu ly §7(c) properly va acknowledge procedural gap.

Tu phan bien:
- Toi co the dang push closure nhanh hon reasonable. Nhung Round 5/6 la max — §13/§14 bat buoc chuyen OPEN thanh Judgment call. Closure timing la appropriate.
- OI-08 CL-19 steel-man against Gemini la fair: toi attack argument (AST-hash la insufficient scope), khong attack conclusion (deterministic la dung). Gemini's principle preserved.
- Gap: Codex chua explicitly confirm bat ky steel-man nao. Neu Codex R5 raises substantive objection (khong chi procedural), toi PHAI engage thay vi dismiss.

---

## 6. Interim Merge Direction (final)

### 6.1 Backbone v1

```
Pre-lock:
  [Bounded ideation (CL-11)]     --> proposal_spec
  [Grammar depth-1 seed (CL-15)] --> compiled_manifest
  Both --> 006 registry compilation (grammar check, dedup)
           |
Protocol Lock:
  Validation: registry.count > 0, grammar_hash match (CL-15)
  Breadth gate: comparison_domain + equivalence_method +
                correction_method + robustness_bundle declared (CL-19)
  |
  v
Stage 3: Exhaustive scan (deterministic, offline, no AI)
  --> Descriptor tagging
  --> Coverage map (4 mandatory cell axes — CL-19)
  --> Cell-elite archive (CL-17)
  --> Local neighborhood probes
  |
Stage 4-6: Layered search + probes (design_brief)
  |
Stage 7: Freeze
  --> Surprise queue (CL-17: 5 axes, >=1 non-peak-score)
  --> Equivalence audit (CL-19: hybrid descriptor + paired-return)
  --> Proof bundle (CL-17: 5-component minimum)
  --> Comparison set (frozen)
  --> Candidate phenotype
  --> Contradiction registry (CL-14: descriptor-level, shadow-only)
  |
Stage 8: Holdout + reserve + epistemic delta
```

### 6.2 Adopt ngay (cumulative, final)

| # | Artifact / Mechanism | CL | Owner |
|---|---------------------|-----|-------|
| 1 | Bounded ideation lane (4 hard rules) | CL-11 | 006 + 015 |
| 2 | Grammar depth-1 seed (mandatory mechanism, conditional cold-start) | CL-15 | 006 |
| 3 | Ownership fold: 006 generate, 015 lineage, 017 coverage | CL-16 | 006/015/017 |
| 4 | 3-layer lineage: feature_lineage + candidate_genealogy + proposal_provenance | CL-13 | 015 + 006 |
| 5 | 5 anomaly axes + 5-component proof bundle (obligation-level) | CL-17 | 017 + 013 |
| 6 | Contradiction registry (descriptor-level shadow-only) | CL-14 | 017 + 015 |
| 7 | Domain-seed = optional provenance hook | CL-12 | 015 |
| 8 | Parameter sweep (APE v1) | CL-18 | 006 |
| 9 | Breadth-expansion interface obligations | CL-19 | 013 + 017 + 008 + 003 |
| 10 | Hybrid equivalence (descriptor pre-bucket + paired-return) | CL-19 | 008 + 013 |
| 11 | 4 mandatory cell axes | CL-19 | 017 |

### 6.3 Defer (cumulative, final)

| # | Artifact / Mechanism | Ly do defer |
|---|---------------------|-------------|
| 1 | Topic 018 umbrella | CL-16: fold sufficient; §12 |
| 2 | SSS first-class | CL-11: replaced |
| 3 | GFS depth 2/3, APE codegen, GA/mutation | Compute/correctness risk |
| 4 | CDAP / domain catalog as core | CL-12: hook only |
| 5 | Full EPC lifecycle / activation ladder | MK-17 ceiling |
| 6 | Exact correction law, thresholds, cell values | 013/017/008 own |
| 7 | Field enumeration + invalidation matrix | 015 own |
| 8 | `generation_mode` state machine conditions | 006 own |
| 9 | Exact equivalence distance thresholds | 013/017 own |

### 6.4 Ownership tam (final)

| Topic | Ganh gi |
|-------|---------|
| 006 | Operator grammar, feature DSL, generation modes, depth-1 seed, compile-to-manifest, parameter sweep, feature descriptor core, `generation_mode` state machine |
| 015 | `feature_lineage`, `candidate_genealogy`, `proposal_provenance`, field enumeration, invalidation tables |
| 017 | Coverage map, cell-elite archive, local probes, surprise queue, phenotype/contradiction shadow, budget, cell axis values, anomaly thresholds |
| 013 | Common comparison domain, correction law default, convergence/diminishing-returns, equivalence thresholds |
| 008 | Identity vocabulary, equivalence categories, hybrid equivalence implementation |
| 003 | Stage insertion, required artifacts, freeze/gating wiring, breadth activation blocker |

---

## 7. Termination Assessment

### Status summary (unified OI scheme)

| OI | Status R5 | CL | Note |
|----|-----------|-----|------|
| OI-01 | CONVERGED | CL-16 | Ownership fold |
| OI-02 | CONVERGED | CL-11 | Bounded ideation |
| OI-03 | CONVERGED | CL-15 | Depth-1 conditional cold-start |
| OI-04 | CONVERGED | CL-13 | 3-layer lineage; field detail DEFER 015 |
| OI-05 | CONVERGED | CL-17 | Surprise + proof inventory; thresholds DEFER 017/013 |
| OI-06 | CONVERGED | CL-14 | Contradiction shadow-only; row shape DEFER 015/017 |
| OI-07 | CONVERGED | CL-12 | Domain-seed provenance hook |
| OI-08 | CONVERGED (proposed CL-19) | CL-19 | Interface locked; exact laws DEFER 013/017/008 |
| NEW-01 ChatGPT Pro | CONVERGED + DEFER | CL-19 | Coupling locked; formula DEFER 013 |
| NEW-01 Claude | CONVERGED | CL-18 | APE = parameterization only |

### Cross-agent CL mapping

| OI (unified) | Codex OI | Gemini OI/CL | Claude CL | ChatGPT Pro CL |
|-------------|----------|--------------|-----------|----------------|
| OI-01 | OI-01 | — | CL-16 | — |
| OI-02 | OI-02 part | — | CL-11 | CL-09 (R3) |
| OI-03 | OI-02 part | OI-03 / CL-05 | CL-15 | — |
| OI-04 | OI-04 | — | CL-13 | CL-12 (R4) |
| OI-05 | OI-03 | — | CL-17 | — |
| OI-06 | OI-05 | — | CL-14 | CL-10 (R3) |
| OI-07 | — | — | CL-12 | CL-11 (R4) |
| OI-08 | OI-06 | OI-08 / CL-06 | CL-19 | CL-13 (R4) |

### Termination condition

Per DEBATE_PROMPT.md: "Khi TAT CA OI-* da chuyen sang CONVERGED hoac DEFER o ca 4 agents → Debate ket thuc."

**Claude R5**: ALL unified OIs = CONVERGED or DEFER. ✓

**Gemini R4**: Da declare debate ket thuc. All OIs CONVERGED/DEFER tu perspective cua Gemini. ✓

**Dieu kien can tu Codex va ChatGPT Pro R5**:
- Neu dong y voi CL-19 va accept §7(c) resolution → termination condition MET → debate ket thuc.
- Neu giu PARTIAL/OPEN tren substance moi → Round 6 la max round (§13). Moi issue con OPEN phai chuyen Judgment call per §14.

### De xuat cho synthesis:

Khi debate ket thuc, synthesis agent:
1. Convergence Ledger (CL-01 through CL-19) la primary content.
2. Interim Merge Direction (§6) la backbone spec.
3. Defer table (§6.3) la explicit out-of-scope v1.
4. 4-agent debate rounds = evidence (khong debate lai).
5. Place in x38 debate structure per POST-DEBATE instructions.

---

## 8. Change Log

| Vong | Ngay | Agent | Tom tat thay doi |
|------|------|-------|-------------------|
| 1 | 2026-03-25 | claude_code | Round mo dau: phan bien 4 proposals, tu phan bien |
| 2 | 2026-03-26 | claude_code | Concessions: rut SSS/Topic 018/EPC/APE codegen |
| 3 | 2026-03-26 | claude_code | Push closure: CL-11/12/13/14 voi steel-man |
| 4 | 2026-03-26 | claude_code | §7(c) request. CL-15/16/17/18. OI-08 interface converged. |
| 5 | 2026-03-26 | claude_code | §7(c) resolved: CL-11/12/13/14 CONVERGED. CL-15/16/17/18 confirmed. CL-19 proposed (OI-08 interface). All OIs CONVERGED/DEFER. Termination assessment. |

---

**Status Table (required by `debate/rules.md` §11)**

| Issue ID | Diem | Phan loai | Trang thai | Steel-man vi tri cu | Ly do bac bo steel-man |
|---|---|---|---|---|---|
| OI-01 | Pre-lock generation lane ownership | Judgment call | CONVERGED (CL-16) | "006/017 khong cover generation — can Topic 018" | 006 scope bao gom generation modes; §12 cam topic moi; no agent defends Topic 018 after R2 |
| OI-02 | Bounded ideation vs SSS | Judgment call | CONVERGED (CL-11) | "SSS tai tao VDO origin" | VDO value tu composition; 4/4 aligned R3-R4; ChatGPT Pro R4 independently confirmed |
| OI-03 | Depth-1 / cold-start | Thieu sot | CONVERGED (CL-15) | "Mandatory EVERY campaign" | Conditional cold-start law: mandatory khi empty, registry_only khi non-empty + grammar_hash match |
| OI-04 | 3-layer lineage | Thieu sot | CONVERGED (CL-13) | "Single schema don gian hon" | Feature vs candidate invalidation semantics khac nhau; 4/4 aligned; field detail DEFER 015 |
| OI-05 | Surprise + proof inventory | Thieu sot | CONVERGED (CL-17) | "IC + orthogonality du" | IC = feature screening; candidate recognition can 5 axes; thresholds DEFER 017 |
| OI-06 | Contradiction registry | Judgment call | CONVERGED (CL-14) | "Contradiction xung dang artifact rieng" | MK-17 ceiling; shadow-only du; row shape DEFER 015/017 |
| OI-07 | Domain-seed hook | Judgment call | CONVERGED (CL-12) | "Cross-pollination la core mechanism" | Composition khong session format; hook giu trail |
| OI-08 | Cell + equivalence + correction | Thieu sot | CONVERGED (CL-19 proposed) | "AST-hash + parameter distance la du" | Behavioral redundancy determines independence; hybrid preserves determinism; Gemini isolated 3:1 |
| NEW-01 (ChatGPT Pro) | Multiplicity control | Thieu sot | CONVERGED + residuals DEFER | "Holm phai la default law" | Coupling locked CL-19; formula scope = 013 |
| NEW-01 (Claude) | APE v1 scope | Thieu sot | CONVERGED (CL-18) | "Code generation tao structural innovation" | Correctness guarantee chua co; parameterization + ideation du |
