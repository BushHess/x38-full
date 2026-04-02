# Findings Under Review — Grammar Expansion

**Topic ID**: X38-T-19D3
**Opened**: 2026-04-02
**Author**: human researcher

1 finding about grammar depth-2 composition — whether the grammar should support
composition operators that create ~140K features from depth-1 OHLCV primitives,
and the spirit-of-the-law question for SSE-D-02. Split from Topic 019D (DFL-12).

**Issue ID prefix**: `X38-DFL-` (Discovery Feedback Loop).

**Convergence notes applicable** (full text at `../000-framework-proposal/findings-under-review.md`):
- C-01: MK-17 != primary evidence; firewall = main pillar
- C-02: Shadow-only principle settled
- C-12: Answer priors banned ALWAYS

**Closed topic invariants** (non-negotiable):
- Topic 018 SSE-D-02: Bounded ideation = results-blind, compile-only, OHLCV-only, provenance-tracked
- Topic 018 SSE-D-11: APE v1 = template parameterization only, no code generation
- Topic 018 SSE-D-05: Recognition stack = pre-freeze topology + named working minimum inventory (Judgment call)
- Topic 002 F-04: Contamination firewall typed schema + whitelist
- Topic 004 MK-17: Same-dataset empirical priors = shadow-only
- Topic 007 F-01: "Inherit methodology, not answers"

**Upstream dependencies within 019 split**:
- 019A (DFL-04/05/09): Foundational boundary decisions — DFL-09 SSE-D-02
  analysis/ideation distinction. DFL-12 SSE-D-02 spirit question depends on
  019A outcome for D-01 (scope clarification).
- 019D2 (DFL-11): Statistical budget — DFL-11 budget capacity determines
  whether ~140K expansion is viable. If budget K_max is small, depth-2
  grammar is academic regardless of SSE-D-02 spirit question.

---

## DFL-12: Grammar Depth-2 Composition

- **issue_id**: X38-DFL-12
- **classification**: Thiếu sót
- **opened_at**: 2026-03-31
- **opened_in_round**: 0
- **current_status**: Open

**Motivation**:

v1 grammar (SSE-D-02, Topic 018 CLOSED) is depth-1: `feature = f(field, lookback)`.
This captures single indicators (ema, sma, std, atr) but NOT compositions — features
that combine two depth-1 features through an operator.

VDO is a composition: `ratio(ema(taker_buy_vol, 14), ema(total_vol, 14))`. Under
v1, VDO cannot be expressed in grammar — it entered via human insight. But the
formula itself is a depth-2 composition of two depth-1 features through a `ratio`
operator. If grammar supported depth-2, VDO's formula (though not the CONCEPT)
would be in the search space.

**The gap**: No finding in Topic 019 proposes depth-2 composition. DFL-03 discusses
grammar extension as "new building blocks for grammar_depth1_seed" (adding
primitives like `volume_ratio`). DFL-09 clarifies scope (analysis vs ideation).
Neither proposes NEW COMPOSITION OPERATORS that create features from EXISTING
features. This is a qualitatively different kind of grammar expansion.

**Proposal**: Add composition operators to the grammar, creating depth-2 features.

### Composition operators

| Operator | Signature | Example |
|----------|-----------|---------|
| `ratio` | (Series, Series) → Series | `ratio(ema(close,21), ema(close,50))` |
| `diff` | (Series, Series) → Series | `diff(ema(close,21), sma(close,50))` |
| `zscore` | (Series, int) → Series | `zscore(ema(close,21), 20)` |
| `rank` | (Series, int) → Series | `rank(std(close,14), 50)` |

**Excluded operators**:
- `crossover`: produces BoolSeries (signal), not composable Series
- `lag`: redundant with lookback parameter extension

### Search space impact

Depth-2 DRAMATICALLY expands the grammar search space:

| Grammar level | Fields | Estimated configs |
|---------------|--------|-------------------|
| Depth-1 (v1) | 5 OHLCV | ~300 |
| Depth-2, binary (ratio, diff) | 5 OHLCV | ~135,000 |
| Depth-2, unary (zscore, rank) | 5 OHLCV | ~6,000 |
| **Total depth-2 (OHLCV)** | 5 | **~140,000** |

**Derivation** (binary operators):
- Depth-1 base features: 6 ops × 5 fields × 10 lookbacks = 300
- `ratio` (non-commutative): 300 × 299 = 89,700 ordered pairs
- `diff` (anti-symmetric): C(300,2) = 44,850 unordered pairs
- Total binary: ~135,000 (before structural pruning)

This is a ~460× expansion from depth-1. The entire pre-filter design (DFL-11
Tier 0) and budget model (DFL-11) exist to make this tractable.

### SSE-D-02 interaction

Depth-2 composition operates WITHIN the OHLCV-only constraint (SSE-D-02 rule 3).
Composition operators combine OHLCV-derived features — they do not introduce new
input fields. `ratio(ema(close,21), ema(volume,14))` uses close and volume, both
OHLCV fields.

**However**, the combinatorial explosion from ~300 to ~140,000 features raises a
SPIRIT-of-the-law question: SSE-D-02's OHLCV-only rule was designed to prevent
search space explosion. Depth-2 achieves explosion WITHIN OHLCV. Does this violate
the intent of SSE-D-02 even though it satisfies the letter?

### Pruning strategy

~140K features contain structural redundancies:
- Self-compositions: `ratio(f, f)` = constant → remove
- Degenerate lookbacks: `zscore(ema(close,3), 3)` → near-constant → remove
- Expected reduction via structural pruning: ~140K → ~80-100K
- Further reduction via DFL-11 Tier 0 MI ranking: → top-200

### Key design decision for debate

**The central question**: Should v2 grammar support depth-2 composition?

| Option | Search space | VDO expressible? | Budget impact | Risk |
|--------|-------------|-------------------|---------------|------|
| **A: YES, depth-2 in grammar** | ~140K (OHLCV-only) | Formula yes, but OHLCV-only fields | Pre-filter required (DFL-11) | Combinatorial explosion vs budget |
| **B: NO, depth-2 via human template only** | ~300 (grammar) + unlimited (human) | Only via human insight | No grammar budget impact | Human bottleneck |
| **C: YES, but depth ≤ 2 and operator whitelist** | ~140K with pruning | Formula yes, OHLCV-only | Bounded expansion | Requires operator review |

Option B is the status quo (v1). Option A/C extend grammar. The debate must
decide whether the ~460× expansion is justified given the statistical budget
constraints identified in DFL-11.

### Interaction with other findings

| Finding | Interaction |
|---------|------------|
| DFL-03 | Grammar extension channel 2. DFL-12 is a SPECIFIC extension (operators, not primitives) |
| DFL-08 | Stage 1 input: grammar depth-2 output feeds into graduation pipeline |
| DFL-09 | Scope: depth-2 composition within OHLCV satisfies SSE-D-02 letter, but spirit? |
| DFL-11 | Budget: ~140K features → pre-filter essential. Budget K_max constrains formal testing |
| SSE-D-02 (018) | OHLCV-only: composition uses only OHLCV fields, but search space explodes |
| F-08 (006) | Feature registry: depth-2 features need `generation_mode: grammar_depth2` |

### Open questions

- Does depth-2 within OHLCV violate the SPIRIT of SSE-D-02, even though it
  satisfies the letter? If so, should 018 be reopened?
- Should the operator whitelist be fixed in the spec or extensible by debate?
- Is depth-2 sufficient, or will depth-3 eventually be needed? If depth-3 is
  foreseeable, should the design account for it now (general recursion) or later?
- Should depth-2 generation be deterministic (enumerate all) or sampled
  (random subset) to manage compute cost?

---

## Cross-topic tensions

| Topic | Finding | Tension | Resolution path |
|-------|---------|---------|-----------------|
| 018 | SSE-D-02 (rule 3, spirit) | Depth-2 composition within OHLCV — ~460x expansion violates spirit? | DFL-12 poses the question; debate decides |

---

## Decision summary — what debate must resolve

Debate for Topic 019D3 must produce a decision on this question. Tier 2
(depends on 019A Tier 1 foundational decisions and 019D2 budget outcome).

**Tier 2 — Mechanisms**:

| ID | Decision | Finding | Alternatives |
|----|----------|---------|-------------|
| D-04 | Should grammar support depth-2 composition operators in v2? | DFL-12 | YES (expand grammar) / NO (human templates only for composition) / YES with operator whitelist |

---

## Summary table

| Issue ID | Finding | Classification | Status |
|----------|---------|---------------|--------|
| X38-DFL-12 | Grammar depth-2 composition (search space expansion) | Thiếu sót | Open |
