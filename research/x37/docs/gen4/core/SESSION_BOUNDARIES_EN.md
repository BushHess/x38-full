# Session Boundaries

This document exists to prevent six failure modes:

1. context overload,
2. contamination across research modes,
3. same-snapshot re-mining disguised as progress,
4. silent drift from evaluation into redesign,
5. operational inconsistency between sessions,
6. overfix through frequent redesign without sufficient evidence.

## Short answer

Yes, complex work should be split into narrower prompts and narrower chats.

The real limits are:
- context load,
- task interference,
- tool runtime,
- mode contamination,
- state drift in long chats,
- and the sandbox/mainline boundary.

## Core rules

1. Use **one execution chat for one mode only**.
2. **Sandbox is for learning. Mainline is for proving.**
3. Each seed discovery or redesign_freeze chat **freezes** the algorithm before closing.
4. The next chat opens a new session with the state pack from the previous.

## Modes

### Sandbox modes (non-lineage)

#### S1. Exploration
Use a chat (or local environment) for:
- testing hypotheses on any data,
- comparing designs,
- debugging algorithm logic,
- free-form iteration.

**Properties:**
- No OOS claim is allowed.
- No state pack is produced.
- Not part of the formal version lineage.
- Results are in-sample / contaminated / hypothesis.
- Insights may inform a future redesign_freeze, but do not substitute for forward evidence.

#### S2. Discussion
Use a chat for:
- philosophy discussion,
- future constitution ideas,
- postmortems,
- educational explanation.

**Properties:**
- Do not output state packs.
- Do not freeze candidates.
- Do not become blind seed inputs.

### Mainline modes (version lineage)

#### M1. Seed discovery
Use one chat with:
- D0 (precheck)
- D1a through D1f3 (execution, split into turns)
- D2 (packaging)

This mode is for:
- one historical snapshot,
- one seed freeze → creates `system_version_id`,
- one state pack bootstrap.

**Each seed discovery chat must freeze the algorithm at the end** (assign system_version_id, produce frozen specs, package state pack).

#### M2. Forward evaluation
Use one chat with:
- F0
- F1
- F2

This mode is for:
- one appended evaluation window,
- evaluating a specific frozen `system_version_id`,
- one review decision,
- one updated state pack.

**This mode must NEVER trigger or perform a redesign.** If forward results motivate a redesign, the researcher must close this chat, optionally explore in sandbox, then open a redesign_freeze chat.

#### M3. Redesign freeze
Use one chat with:
- R0 (precheck + redesign dossier review)
- R1 (redesign execution)
- R2 (packaging)

This mode is for:
- creating a new `system_version_id` based on learnings from forward evidence,
- recording the parent version, new freeze_cutoff_utc, and resetting the evidence clock.

**Prerequisites (all required):**
- A valid redesign trigger has fired (see `redesign_guardrails.allowed_triggers`).
- The cooldown period (180 days since last freeze) has elapsed, unless emergency/bug exception.
- A redesign dossier has been prepared.
- The dossier documents exactly one principal change.

**Each redesign_freeze chat must freeze the new algorithm at the end** (assign new system_version_id, produce frozen specs, package state pack with reset evidence clock).

#### M4. Governance review
Use one chat with:
- G0
- G1
- G2

This mode is for:
- charter review only,
- no candidate discovery,
- no hidden restart of search.

## Matrix

| Mode | Type | Prompt sequence | State pack? | Freeze? |
|---|---|---|---|---|
| Exploration | sandbox | freeform | No | No |
| Discussion | sandbox | freeform | No | No |
| Seed discovery | mainline | `D0 → D1a..D1f3 → D2` | Yes | Yes (new version) |
| Forward evaluation | mainline | `F0 → F1 → F2` | Yes | No (evaluate existing) |
| Redesign freeze | mainline | `R0 → R1 → R2` | Yes | Yes (new version) |
| Governance review | mainline | `G0 → G1 → G2` | No (governance package only) | No |

## Never mix these in one chat

- seed discovery + forward evaluation
- forward evaluation + redesign_freeze
- forward evaluation + governance review
- blind discovery + prior winners
- same-snapshot redesign after packaging
- governance charter rewrite + strategy search
- sandbox exploration + mainline freeze (exploration results ≠ mainline evidence)

## When a new chat is mandatory

Start a new chat if any of the following is true:
- the mode changes,
- the appended delta window changes,
- the state pack version changes,
- the constitution major version changes,
- the previous execution chat already packaged outputs,
- the previous chat drifted into exploratory discussion,
- you need to preserve blindness for seed discovery,
- forward evaluation results motivate a redesign (close F chat, open R chat).

## When staying in the same chat is preferred

Stay in the same chat only when:
- you are still in the same mode,
- you are still using the same admitted input set,
- you are only moving from precheck → execution → packaging,
- no packaging step has yet been completed.

## Same-snapshot rule

For a given `snapshot_id`, seed discovery is allowed **once** — regardless of `system_version_id`.

After the state pack is created from that snapshot:
- do not open another seed discovery chat on the same snapshot under any version,
- do not claim a new candidate is a new evidence gain,
- use only appended data for new evidence.

## One chat = one freeze

Each seed discovery or redesign_freeze chat **must produce exactly one freeze** before closing.
The freeze creates a `system_version_id` that is immutable from that point forward.
The next chat (typically forward_evaluation) evaluates the frozen version.

## Recovery rule

If an execution chat becomes messy, too long, or mixed-mode:
- stop,
- package whatever clean outputs already exist if possible,
- otherwise discard the session,
- then restart from the last clean state pack in a new chat.

## Blindness rule

A blind seed discovery chat should only know:
- the active constitution,
- the canonical schema document,
- the raw historical snapshot,
- the session manifest,
- optional hash and snapshot notes.

It should not know:
- previous winners,
- previous reports,
- previous ledgers,
- previous frozen system specs,
- prior contamination logs unless their content has already been reduced to axiomatic guardrails embedded in the constitution.

## Redesign guardrail summary

Redesign is the highest-cost operation in the system because it resets the evidence clock.
Before opening a redesign_freeze chat, verify:

1. **Trigger**: one of the allowed triggers has fired.
2. **Cooldown**: >= 180 days since last freeze (unless emergency/bug).
3. **Evidence**: >= 180 forward days and >= 6 entries accumulated.
4. **Dossier**: redesign_dossier.md is prepared with single-hypothesis change.
5. **Budget**: no more than 1 major redesign per 180 calendar days.

If any of these conditions is not met, the redesign is not allowed.
Continue forward evaluation instead.
