# Proposal: Alpha-Lab Directory Structure — Full genesis/ Design

> **Status**: DRAFT — pending debate convergence
> **Date**: 2026-04-02
> **Origin**: Human researcher + Claude Code conversation
> **Purpose**: Debate document for genesis/ detailed structure
> **Target**: When CONVERGED → formalize as `tmp/rebuild/08-directory-structure.md`

---

## 1. Context & Motivation

### 1.1 Problem

x38 hiện sống tại `btc-spot-dev/research/x38/` — cùng cấp với x0-x37 (các study
cụ thể). Nhưng Alpha-Lab **không phải một study**. Nó là **meta-framework** quản lý
cách các study được thực hiện.

Nghịch lý: *nghiên cứu nằm bên trong nghiên cứu mà nó quản lý*.

### 1.2 Decisions Required

1. Alpha-Lab framework nên nằm ở đâu trong monorepo?
2. genesis/ internal structure — decisions, debates, governance, archive, tracking
3. Ranh giới giữa genesis/ và các thư mục đồng cấp (specs/, engine/, campaigns/)
4. Mối quan hệ giữa các thư mục `alpha_lab*` hiện có

### 1.3 Current State

```
/var/www/trading-bots/
├── alpha_lab_dev/              ← Campaign data (gen1: 44MB, gen4: 6.8MB, scan, x40v2)
│   └── resource/               ← 461 files
│       ├── gen1/ (8 variants)
│       ├── gen4/
│       ├── scan/ (design.md)
│       └── x40v2/
├── btc-spot-dev/
│   └── research/
│       └── x38/                ← Framework design (233 files, 19 topic dirs, ~160 findings)
│           ├── debate/         ← 19 topic-based dirs (process history)
│           ├── docs/           ← Reference materials
│           ├── drafts/         ← 4 spec drafts (SEEDED/DRAFTING)
│           ├── published/      ← Empty (no specs published yet)
│           ├── audits/         ← 12 audit files
│           ├── template/       ← Debate prompt templates
│           └── tmp/rebuild/    ← 7 blueprint files (this proposal's basis)
└── (other repos: btc-spot, vtrend, latch, data-pipeline, ...)
```

---

## 2. Proposed Top-Level Structure

### 2.1 Location

Alpha-Lab lives at `/var/www/trading-bots/alpha_lab/` (monorepo root).

**Rationale**:
- Framework ≠ study. Không thuộc `btc-spot-dev/research/`.
- Dependency arrow đúng chiều: `alpha_lab/ → btc-spot-dev/v10/` (không ngược).
- Multi-asset tương lai: framework không gắn vào btc-spot-dev.
- Cùng venv (`/var/www/trading-bots/.venv/`), cùng `pyproject.toml` — import hoạt động.
- Tiền lệ: `alpha_lab_dev/` đã nằm tại monorepo root.

### 2.2 Top-Level Layout

```
alpha_lab/
├── genesis/        ← Quá trình nghiên cứu tạo ra framework (x38 rebuild output)
├── specs/          ← Published specs (genesis/ output, consumed by engine/)
├── engine/         ← Framework code (future, implements specs/)
├── campaigns/      ← Campaign data (from alpha_lab_dev/resource/)
└── docs/           ← PLAN, README, onboarding, CLAUDE.md
```

### 2.3 Dependency Arrows (uni-directional)

```
genesis/  ──produces──→  specs/drafts/  ──publishes──→  specs/*.md
specs/*.md  ──consumed by──→  engine/
engine/  ──runs──→  campaigns/
campaigns/  ──(no dependency on)──→  genesis/
```

---

## 3. genesis/ Detailed Structure

### 3.1 Overview

genesis/ chứa **quá trình nghiên cứu đã tạo ra alpha_lab**, tổ chức theo
concept domain (per x38 rebuild blueprint), không theo process history (x38 cũ).

### 3.2 Full genesis/ Tree

```
genesis/
├── STATUS.md                         ← Single ledger (06-tracking.md design)
│                                       Domain status, deferred, circular deps,
│                                       integration log, spec readiness, export readiness
│
├── decisions/                        ← AUTHORITATIVE: 18+1 domain files
│   ├── 01-philosophy.md              ┐
│   ├── 02-campaign-model.md          │ 8 consolidated (closed topics merged)
│   ├── 03-identity-versioning.md     │ Each file: Decided / Constraints /
│   ├── 04-firewall.md               │ Open / Deferred sections
│   ├── 05-meta-knowledge.md          │ Finding ID: X38-{DOM}-{NN}
│   ├── 06-clean-oos.md              │ 5-type: CONVERGED/ARBITRATED/
│   ├── 07-convergence.md            │         AUTHORED/DEFAULT/DEFERRED
│   └── 08-search-expansion.md        ┘
│   ├── 10-protocol-engine.md         ┐
│   ├── 11-engine-design.md           │
│   ├── 12-feature-engine.md          │ 10 open-topic domains
│   ├── 13-data-integrity.md          │ (debate ongoing)
│   ├── 14-deployment.md              │
│   ├── 15-quality-assurance.md       │
│   ├── 16-bounded-recalibration.md   │
│   ├── 17-epistemic-search.md        │
│   ├── 18-discovery-feedback-loop.md │
│   └── 19-entity-lifecycle.md        ┘ ← X40 state machines (NEW)
│
├── debate/                           ← LIVE workspace for OPEN domains only
│   ├── rules.md                      ← Debate rules (from x38, refined)
│   ├── 03-identity-versioning/       ┐
│   │   ├── README.md                 │ Per domain: rounds/ + external/
│   │   ├── rounds/                   │
│   │   │   ├── claude_code/          │
│   │   │   └── codex/               │
│   │   └── external/                 │
│   │       └── chatgpt_web/          │
│   ├── 11-engine-design/             │ Only domains with OPEN findings
│   ├── 16-bounded-recalibration/     │ have debate dirs
│   ├── 17-epistemic-search/          │
│   ├── 18-discovery-feedback-loop/   │
│   └── .../                          ┘
│
├── evidence/                         ← FROZEN inputs & reference material
│   ├── online_vs_offline.md          ← Foundational distinction
│   ├── design_brief.md              ← Historical input
│   ├── x37_evidence/                ← Evidence from prior research
│   └── x40_reference/               ← X40 state machines (reference, not import)
│
├── governance/                       ← Rules of the genesis process
│   ├── taxonomy.md                   ← 5-type decision system (from 01-taxonomy.md)
│   ├── dependency-dag.md             ← Ordering, circular, reopening (from 03-dependency-rules.md)
│   ├── spec-gates.md                ← 7-tier lifecycle + provenance (from 05-spec-gates.md)
│   └── closure-workflow.md           ← 3-step: complete → notify → update
│
└── archive/                          ← x38 nguyên trạng (READ-ONLY)
    ├── README.md                     ← "historical record, do not modify"
    ├── debate/                       ← 19 topic dirs as-is
    ├── PLAN.md
    ├── EXECUTION_PLAN.md
    └── x38_RULES.md
```

### 3.3 decisions/ — Authoritative Domain Files

**Source**: x38 rebuild Step 0 extraction (per 02-concept-structure.md).

18+1 domain files organized by concept, not debate timeline:
- **8 consolidated** (01-08): Closed topics merged by concept
- **10 open-topic** (10-19): Open topics, ~1:1 mapping, debate ongoing
- Each file format: `## Decided` / `## Constraints` / `## Open` / `## Deferred`
- Finding ID: `X38-{DOM}-{NN}`, 5-type classification (per 01-taxonomy.md)

**Authority**: decisions/ is Tier 1. Everything else in genesis/ is Tier 2.

### 3.4 debate/ — Live Workspace

Only domains with OPEN findings have debate dirs. Closed domains: no debate dir
(their debates are in archive/). Structure per domain:
- `rounds/claude_code/`, `rounds/codex/` — canonical agents
- `external/chatgpt_web/` — imported critiques (external advisor lane, per 04-governance.md)
- `rules.md` — debate rules (refined from x38 debate/rules.md)

### 3.5 evidence/ — Frozen Inputs

Read-only reference material consumed during debates:
- `online_vs_offline.md` — foundational distinction (mandatory read)
- `design_brief.md` — historical input (Tier 2, informational)
- `x37_evidence/` — evidence from prior research (v6/v7/v8 patterns, etc.)
- `x40_reference/` — X40 state machines (reference, not formal import)

### 3.6 governance/ — Rules of the Game

Governance rules govern the **genesis process itself**, not the framework.
When genesis completes, governance becomes historical.

Source: formalized from tmp/rebuild/ blueprint files:
- `taxonomy.md` ← 01-taxonomy.md (5-type decision system)
- `dependency-dag.md` ← 03-dependency-rules.md (DAG, circular, reopening)
- `spec-gates.md` ← 05-spec-gates.md (7-tier lifecycle, provenance tags)
- `closure-workflow.md` ← 04-governance.md (3-step closure, 2-tier authority)

### 3.7 archive/ — x38 Nguyên Trạng

Full x38 as-is, read-only. Purpose: provenance tracing.

Evidence chain example:
`decisions/04-firewall.md` → provenance tag →
`archive/debate/002-contamination-firewall/round-3_rebuttal.md`

### 3.8 STATUS.md — Single Ledger

At genesis/ root (not inside decisions/) — tracks the process, not domain decisions.

Sections (per 06-tracking.md):
1. Domain Status table (decided/open/deferred counts)
2. Deferred Items Registry
3. Circular Dependencies
4. Integration Log
5. Spec Readiness
6. Export Readiness

### 3.9 genesis/ Lifecycle

1. **Active** — Step 0 extraction, debate open domains, draft specs
2. **Winding down** — all domains INTEGRATED, specs moving to PUBLISHED
3. **Frozen** — all specs published, genesis = historical record

---

## 4. specs/ and Other Top-Level Directories

### 4.1 specs/ — Why Outside genesis/

Genesis = process (nhà máy). Specs = product (sản phẩm).
Sản phẩm không nằm trong nhà máy.

```
genesis/decisions/  →produces→  specs/drafts/  →publishes→  specs/*.md
specs/*.md          →consumed by→  engine/
```

Structure:
```
specs/
├── drafts/                     ← Consuming genesis/decisions/, not yet published
│   ├── architecture_spec.md
│   ├── discovery_spec.md
│   ├── meta_spec.md
│   ├── methodology_spec.md
│   └── ...
└── (published specs at root)
```

### 4.2 engine/ — Framework Code (Future)

Implements specs/. Protocol Engine, Meta-Updater, Contamination Firewall.
Imports from btc-spot-dev/v10/ as needed. Empty until specs reach PUBLISHED.

### 4.3 campaigns/ — Campaign Data

Migrated from alpha_lab_dev/resource/:
```
campaigns/
├── gen1/           ← 8 variants, 44MB
├── gen4/           ← 6.8MB
├── scan/           ← design.md
└── x40v2/
```

### 4.4 docs/

```
docs/
├── CLAUDE.md       ← AI context for alpha_lab/ (separate from btc-spot-dev/)
├── README.md       ← Project overview, onboarding
└── PLAN.md         ← Narrative (informational, not authoritative)
```

---

## 5. Migration Plan

### 5.1 Mapping

| Current | After | Action |
|---------|-------|--------|
| `btc-spot-dev/research/x38/` | `alpha_lab/genesis/archive/` (as-is) + `alpha_lab/genesis/` (rebuilt) | Rebuild per blueprint, archive original |
| `alpha_lab_dev/resource/` | `alpha_lab/campaigns/` | Migrate content |
| `alpha_lab_dev/` | Delete after migration | Empty shell |
| `btc-spot-dev/research/x38/drafts/` | `alpha_lab/specs/drafts/` | Migrate 4 spec drafts |
| `btc-spot-dev/research/x38/tmp/rebuild/` | `alpha_lab/genesis/governance/` | Formalize into governance docs |

### 5.2 Migration Order

1. Tạo `alpha_lab/` skeleton (5 top-level dirs)
2. Thực thi x38 rebuild → genesis/ (Step 0 extraction + domain population)
3. Migrate `alpha_lab_dev/resource/` → `alpha_lab/campaigns/`
4. Migrate `x38/drafts/` → `alpha_lab/specs/drafts/`
5. Tạo `alpha_lab/docs/CLAUDE.md`
6. Archive `btc-spot-dev/research/x38/` → `alpha_lab/genesis/archive/`
7. Cleanup: delete `alpha_lab_dev/` (empty after step 3)

**Step 2 là blocking** — genesis/ phải hoàn thành trước khi các bước khác có ý nghĩa.

---

## 6. Open Questions

### OQ-01: alpha_lab/ location

Monorepo root (`/var/www/trading-bots/alpha_lab/`) hay nơi khác?

**Current position**: Monorepo root. Same level as btc-spot-dev, alpha_lab_dev.

### OQ-02: genesis/ naming

`genesis/` hay tên khác?

**Alternatives considered**: origin/ (git conflict), provenance/ (dài),
foundation/ (gợi ý vẫn active), research/ (generic), forge/ (metaphorical).

**Current position**: `genesis/` — rõ ràng, ngắn gọn, chính xác.

### OQ-03: archive/ scope

Full x38 (bao gồm tmp/rebuild/, audits/) hay chỉ debate-relevant subset?

**Current position**: Full x38. Provenance tracing may need any file. Disk is cheap.

### OQ-04: campaigns/ migration timing

Khi nào migrate alpha_lab_dev/resource/ → alpha_lab/campaigns/?

**Current position**: Sau khi genesis/ established. Campaigns độc lập — migrate bất kỳ lúc nào.

### OQ-05: alpha_lab/ cần CLAUDE.md riêng?

**Current position**: Có. Scope riêng, write permissions riêng, rules riêng.

### OQ-06: 19-entity-lifecycle.md — standalone domain hay merge?

X40 state machines could merge into 03-identity-versioning + 16-bounded-recalibration.

**Current position**: Standalone. 3 cross-cutting state machine concepts.
Merging recreates fragmentation (B-01 problem).

### OQ-07: Spec drafts location

**Position A** (current): `specs/drafts/` — specs là output, dù đang draft.
**Position B**: `genesis/drafts/` — drafts đang consume decisions/ = thuộc genesis process.
Chỉ move ra specs/ khi PUBLISHABLE.

### OQ-08: STATUS.md placement

**Position A** (current): genesis/ root — tracks process, not domain decisions.
**Position B**: decisions/00-status.md — visible khi listing domain files.

---

## 7. Convergence Criteria

This proposal CONVERGES when all OQ-* resolved (DECIDED or DEFERRED).

Upon convergence:
1. Formalize as `tmp/rebuild/08-directory-structure.md`
2. Update `tmp/rebuild/06-tracking.md` § Final Directory Structure
3. Update `tmp/rebuild/07-genesis-pipeline.md` to reflect actual paths
4. Proceed with Step 0 extraction into the new structure

---

## 8. References

- `tmp/rebuild/00-issues-registry.md` — 50 issues driving restructure
- `tmp/rebuild/01-taxonomy.md` — 5-type decision system (→ genesis/governance/taxonomy.md)
- `tmp/rebuild/02-concept-structure.md` — 19→18+1 domain consolidation (→ genesis/decisions/)
- `tmp/rebuild/03-dependency-rules.md` — DAG, circular, reopening (→ genesis/governance/dependency-dag.md)
- `tmp/rebuild/04-governance.md` — 2-tier authority, closure workflow (→ genesis/governance/closure-workflow.md)
- `tmp/rebuild/05-spec-gates.md` — 7-tier lifecycle, provenance (→ genesis/governance/spec-gates.md)
- `tmp/rebuild/06-tracking.md` — STATUS.md design, extraction methodology
- `tmp/rebuild/07-genesis-pipeline.md` — export contract, abstraction test
- `alpha_lab_dev/resource/scan/design.md` — existing campaign data structure
