# Source Alignment Notes

## 1. Purpose

This file records which statements in the clean-restart pack are **inherited from the repo** and which are **explicit design choices made here**.

This is the main safeguard against accidental drift.

---

## 2. Repo-grounded facts carried into this pack

### 2.1 x37 role
Inherited fact:
- x37 is an arena for **independent discovery sessions**; each session is a full run from Phase 0 to Phase 6.
- Root wrappers should run one explicit phase at a time; no auto-advance.
- Frozen inputs and session isolation matter.

x40 uses this by treating x37 as the **blank-slate escalation engine**, not as a patching engine.

### 2.2 x37 phase and freeze discipline
Inherited fact:
- x37 has sequential phase gating.
- Phase 5 is a special irreversible checkpoint.
- Active sessions should not read results of other active sessions.

x40 uses this by requiring x37 escalation only for structural challenges, not casual iteration.

### 2.3 gen4 historical-seed window policy
Inherited fact:
- warmup through 2019-12-31,
- discovery 2020-01-01 to 2023-06-30,
- holdout 2023-07-01 to 2024-09-30,
- internal reserve 2024-10-01 to snapshot end.

x40 adopts these as the current BTC default historical-seed qualification windows.

### 2.4 clean OOS distinction
Inherited fact:
- historical archive is candidate-mining-only,
- internal holdout/reserve remain contaminated for discovery purposes,
- clean OOS requires appended data strictly after freeze.

x40 therefore forbids same-file clean-OOS claims.

### 2.5 `OH0_D1_TREND40` lineage
Inherited fact:
- x37/v8 `S_D1_TREND` is native D1, long-only, one signal, no regime gate, no cross-timeframe dependence, no parameter calibration from data.
- signal is `close_t / close_(t-40) - 1 > 0`.

x40 uses this as the `OHLCV_ONLY` control baseline.

### 2.6 x38 role
Inherited fact:
- x38 is an **architecture blueprint** for an offline framework.
- It is not the runtime code itself.
- Key open topics still include execution/resilience, bounded recalibration path, and epistemic search policy.

x40 therefore does not pretend these questions are fully solved downstream.

### 2.7 production validation tiers
Inherited fact:
- production pipeline uses its own namespace,
- machine validation emits `PROMOTE/HOLD/REJECT`,
- Tier-3 human route emits deployment decisions,
- hard fails are absolute blockers,
- soft HOLD means insufficient automated evidence, not automatic deployment ban.

x40 therefore keeps its own namespaces separate and gives low-power challengers a formal lane.

### 2.8 `PF0_E5_EMA21D1` lineage
Inherited fact:
- E5 remains the primary candidate in the current VTREND lineage,
- but it is still a `HOLD` with WFO underresolved,
- and VDO uses taker-buy information rather than OHLCV-only semantics.

x40 therefore places E5 in `PUBLIC_FLOW`, not `OHLCV_ONLY`.

### 2.9 x39 role
Inherited fact:
- x39 is a feature-invention explorer and experiment plan.
- It recorded many experiments and also formal validation for the vol-compression gate.
- x39 itself distinguishes simplified replay diagnostics from formal canonical validation.
- x39 records 0/31 features separating winners from losers at entry in the earlier residual scan summary.

x40 therefore treats x39 as:
- a discovery lab by default,
- but also a valid source of tracked challengers once formal validation exists.

### 2.10 formal challenger example
Inherited fact:
- x39 formal validation currently reports the vol-compression line as improved but overall inconclusive due to DSR pass + WFO fail, with recommended threshold `0.7`.

x40 therefore seeds `PF1_E5_VC07` as a tracked challenger rather than auto-promoting it.

---

## 3. Design choices made in this clean-restart pack

These are **not direct inherited truths**. They are explicit operational choices introduced here.

### 3.1 x40 namespace
States such as:
- `B0_INCUMBENT`
- `B1_QUALIFIED`
- `B2_CLEAN_CONFIRMED`
- `DURABLE/WATCH/DECAYING/BROKEN`

are x40 design choices.

### 3.2 Clean-confirmation default floor
The rule:
- `>= 180` days clean block and
- at least `6` clean trades or `20%` exposure

is an x40 implementation default.

### 3.3 Promotion ladder
`DIAGNOSTIC -> FILTER -> EXIT_OVERLAY -> STANDALONE`
is an x40 operational discipline choice.

### 3.4 Challenger routing split
The distinction between:
- `x40_route`, and
- `tier3_route`

is an x40 control-layer design choice.

### 3.5 Standardized comparison profile
The rule that headline x40 claims must use:
- `CP_PRIMARY_50_DAILYUTC`
- plus a common daily UTC metric domain

is an x40 design choice introduced to stop apples-to-oranges comparisons across leagues and source lineages.

### 3.6 Richer-data priority order
The recommended order:
`DERIVATIVES_FLOW -> ORDERBOOK -> ONCHAIN -> TEXT_EVENT`
is an x40 strategy choice.

### 3.7 Durability aggregation
The `PASS/WATCH/FAIL -> DURABLE/WATCH/DECAYING/BROKEN` aggregation logic is an x40 policy choice.

---

## 4. Why this split matters

Without this file, future edits can accidentally smuggle design choices into "repo truth."

This file is the guardrail:
- repo facts stay facts,
- x40 policy stays policy.

---

## 5. Revision rule

Any future x40 revision that changes:
- baseline states,
- challenger workflow,
- comparison profiles,
- clean-confirmation floors,
- or richer-data priority

must update this file explicitly.
