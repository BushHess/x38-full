# Session Boundaries

This document exists to prevent five failure modes:

1. context overload,
2. contamination across research modes,
3. same-snapshot re-mining disguised as progress,
4. silent drift from execution into redesign,
5. operational inconsistency between sessions.

## Short answer

Yes, complex work should be split into narrower prompts and narrower chats.

The reason is not one simple visible timer.
The real limits are:
- context load,
- task interference,
- tool runtime,
- mode contamination,
- and state drift in long chats.

## Core rule

Use **one execution chat for one mode only**.

Allowed pattern inside one execution chat:
- precheck prompt,
- execution prompts (one or more turns, depending on mode),
- packaging prompt,
- then stop.

## Modes

### 1. Seed discovery
Use one chat with:
- D0 (precheck)
- D1a through D1f3 (execution, split into 15 turns for online chat limits)
- D2 (packaging)

This mode is for:
- one historical snapshot,
- one seed freeze,
- one state pack bootstrap.

### 2. Forward evaluation
Use one chat with:
- F0
- F1
- F2

This mode is for:
- one appended evaluation window,
- one review decision,
- one updated state pack.

### 3. Governance review
Use one chat with:
- G0
- G1
- G2

This mode is for:
- charter review only,
- no candidate discovery,
- no hidden restart of search.

### 4. Discussion-only chat
This is allowed, but it is **not** part of the lineage.

Use it for:
- philosophy discussion,
- future constitution ideas,
- postmortems,
- educational explanation.

Discussion-only chats:
- do not output state packs,
- do not freeze candidates,
- do not become blind seed inputs.

## Matrix

| Mode | Prompt sequence in one chat | Must start a new chat before this mode? | Packaging allowed? |
|---|---|---:|---:|
| Seed discovery | `D0 -> D1a -> D1b1..D1b4 -> D1c -> D1d1..D1d3 -> D1e1..D1e3 -> D1f1..D1f3 -> D2` | Yes | Yes |
| Forward evaluation | `F0 -> F1 -> F2` | Yes | Yes |
| Governance review | `G0 -> G1 -> G2` | Yes | Yes |
| Discussion-only | freeform | Yes | No |

## Never mix these in one chat

- seed discovery + forward evaluation
- forward evaluation + governance review
- blind discovery + prior winners
- same-snapshot redesign after packaging
- governance charter rewrite + strategy search

## When a new chat is mandatory

Start a new chat if any of the following is true:
- the mode changes,
- the appended delta window changes,
- the state pack version changes,
- the constitution major version changes,
- the previous execution chat already packaged outputs,
- the previous chat drifted into exploratory discussion,
- you need to preserve blindness for seed discovery.

## When staying in the same chat is preferred

Stay in the same chat only when:
- you are still in the same mode,
- you are still using the same admitted input set,
- you are only moving from precheck -> execution -> packaging,
- no packaging step has yet been completed.

## Same-snapshot rule

For a given `snapshot_id`, seed discovery is allowed once only.

After `state_pack_v1` is created from that snapshot:
- do not open another seed discovery chat on the same snapshot,
- do not claim a new candidate is a new evidence gain,
- use only appended data for new evidence.

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
