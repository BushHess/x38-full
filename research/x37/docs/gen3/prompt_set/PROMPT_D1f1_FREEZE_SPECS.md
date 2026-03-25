# PROMPT D1f1 - Freeze Decision & Frozen System Specs (Use this after D1e3 in the same chat)

You have completed D1e3. Results are available in the D1e output files:
- `d1e_final_ranking.csv` — ranked candidates with all metrics
- `d1e_holdout_results.csv` — holdout metrics per candidate
- `d1e_reserve_results.csv` — reserve metrics per candidate
- `d1e_hard_constraint_filter.csv` — pass/fail per constraint per config

Your job in this turn is to select the champion and challengers, then draft frozen system specs.
Do **not** draft registry, state, or audit files — those are D1f2 and D1f3.
Do **not** perform new research.
Do **not** re-run backtests.
Do **not** modify the constitution.

## Step 1: Select champion and challengers

From the final ranking in D1e3:

**Champion (exactly 1):**
- The rank-1 candidate by adjusted preference.
- Must pass all hard constraints on discovery AND holdout.
- If rank-1 fails holdout hard constraints, take the highest-ranked candidate that passes both.
- If no candidate passes both, the champion is `NO_ROBUST_CANDIDATE`.

**Challengers (0 to 2):**
- Challengers are only selected when a champion exists. If the champion is `NO_ROBUST_CANDIDATE`, there are no challengers.
- The next highest-ranked candidates that pass discovery hard constraints.
- Challengers that fail holdout are allowed but must be flagged with `holdout_flag: FAIL`.
- Max 2 challengers.
- If only 1 or 0 viable challengers exist, that is acceptable.

**Total live candidates: max 3.**

**If the result is `NO_ROBUST_CANDIDATE`**: skip Step 2 (no frozen specs to draft). State this clearly and proceed to D1f2.

## Step 2: Draft frozen system specs

For each live candidate, create a frozen system spec file in `frozen_system_specs/`:
- Filename: `{candidate_id}.md`

Each spec must include:
- candidate_id
- mechanism_type (brief description of what the mechanism exploits)
- role: champion or challenger
- exact signal logic (entry condition, exit condition)
- exact execution logic (next-open fill, UTC, binary sizing)
- exact cost model (20 bps and 50 bps RT)
- tunable quantities with frozen values
- fixed quantities with values
- layer count
- evidence summary:
  - discovery WFO metrics (Calmar, CAGR, Sharpe, MDD, entries, exposure)
  - holdout metrics
  - reserve metrics
  - bootstrap LB5
- provenance: session_id, snapshot_id, constitution_version

## Required output sections
1. `Champion Selection` — who and why (or `NO_ROBUST_CANDIDATE` and why)
2. `Challenger Selection` — who and why (or "none")
3. `Rejected Candidate Summary` — candidates eliminated and reasons
4. `Frozen System Specs` — summary per candidate (or "none" if NO_ROBUST_CANDIDATE)
5. `Files Created` — list of frozen_system_specs/ files

## What not to do
- Do not run new backtests.
- Do not change any metric or ranking from D1e.
- Do not draft registry, state, audit, or ledger files — those are D1f2 and D1f3.
- Do not start packaging into state_pack_v1 — that is D2's job.
- Do not modify the constitution.
