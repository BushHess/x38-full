# First-Cycle Implementation Runbook

## 1. Purpose

This runbook defines exactly what to do **after the x40 codebase exists and is runnable**.

The output of the first cycle is not "new alpha."  
The output is a **decision-ready evidence state**.

By the end of the first cycle, x40 must produce:

- qualified baseline status for `OH0` and `PF0`,
- durability states,
- adjudication status for `PF1`,
- one standardized control panel on `CP_PRIMARY_50_DAILYUTC`,
- and one `next_action.md`.

---

## 2. Precondition

Do not start this runbook until all of the following are true:

1. x40 code compiles and basic smoke tests pass;
2. template files exist;
3. baseline/challenger/profile registries are initialized;
4. raw data bundle paths are resolved;
5. metric-domain conversion to daily UTC is implemented.

---

## 3. First-cycle canonical order

### Phase 0 — bootstrap and registry
Create:

- `registry/baselines.yaml`
- `registry/challengers.yaml`
- `registry/leagues.yaml`
- `registry/comparison_profiles.yaml`
- `runs/`
- `reports/`

Seed the registry with:
- `OH0_D1_TREND40`
- `PF0_E5_EMA21D1`
- `PF1_E5_VC07`
- `CP_PRIMARY_50_DAILYUTC`
- `CP_SENS_20_DAILYUTC`

#### Required output
`reports/bootstrap_report.md`

---

### Phase 1 — `A00` for `OH0_D1_TREND40`
Run source parity against x37/v8 frozen source.

#### Suggested CLI
```bash
python -m research.x40.run_a00 --baseline OH0_D1_TREND40
```

#### Required outputs
- `runs/OH0_D1_TREND40/a00/parity_report.md`
- `runs/OH0_D1_TREND40/a00/parity_metrics.json`
- `runs/OH0_D1_TREND40/a00/equity_source.csv`
- `runs/OH0_D1_TREND40/a00/equity_x40.csv`

#### Stop rule
If parity is `PARITY_FAIL`, stop the whole first cycle and fix implementation before proceeding.

---

### Phase 2 — `A01` for `OH0_D1_TREND40`
Run baseline qualification.

#### Suggested CLI
```bash
python -m research.x40.run_a01 --baseline OH0_D1_TREND40
```

#### Required outputs
- `baseline_manifest.yaml`
- `qualification_report.md`
- `qualification_state.json`
- `metrics_CP_PRIMARY_50_DAILYUTC.json`
- `metrics_CP_SENS_20_DAILYUTC.json` (optional but recommended)
- `comparison_header.json`
- `forward_evaluation_ledger.csv`
- `qualification_decision.md`

#### Decision
`OH0` must exit as exactly one of:
- `B1_QUALIFIED`
- `B0_INCUMBENT`
- `B_FAIL`

---

### Phase 3 — `A00` for `PF0_E5_EMA21D1`
Run source parity against the current canonical E5 lineage.

#### Suggested CLI
```bash
python -m research.x40.run_a00 --baseline PF0_E5_EMA21D1
```

#### Required outputs
Same artifact set as `OH0` parity.

#### Stop rule
If parity is `PARITY_FAIL`, stop `PUBLIC_FLOW` work and fix lineage normalization.

---

### Phase 4 — `A01` for `PF0_E5_EMA21D1`
Run baseline qualification.

#### Suggested CLI
```bash
python -m research.x40.run_a01 --baseline PF0_E5_EMA21D1
```

#### Decision
`PF0` must exit as exactly one of:
- `B1_QUALIFIED`
- `B0_INCUMBENT`
- `B_FAIL`

---

### Phase 5 — build standardized control panel
After both baselines have completed `A01`, generate one control panel using **only** `CP_PRIMARY_50_DAILYUTC` as the headline profile.

#### Suggested CLI
```bash
python -m research.x40.make_control_panel --profile CP_PRIMARY_50_DAILYUTC
```

#### Required outputs
- `reports/control_panel_CP_PRIMARY_50_DAILYUTC.md`
- `reports/control_panel_CP_PRIMARY_50_DAILYUTC.csv`

#### Rule
Do not use source-native 20 bps tables from one baseline and 50 bps tables from another baseline in this panel.

---

### Phase 6 — durability suite for `OH0`
Run:

- `A02`
- `A03`
- `A04`
- `A05`
- `A07`

#### Suggested CLI
```bash
python -m research.x40.run_a02 --baseline OH0_D1_TREND40
python -m research.x40.run_a03 --baseline OH0_D1_TREND40
python -m research.x40.run_a04 --baseline OH0_D1_TREND40
python -m research.x40.run_a05 --baseline OH0_D1_TREND40
python -m research.x40.run_a07 --baseline OH0_D1_TREND40
python -m research.x40.aggregate_durability --baseline OH0_D1_TREND40
```

#### Required outputs
- `temporal_decay_report.md`
- `half_life_report.md`
- `capacity_crowding_report.md`
- `entry_exit_report.md`
- `canary_report.md`
- `durability_state.json`

---

### Phase 7 — durability suite for `PF0`
Run the same durability suite for `PF0`.

#### Stop rule
Do not skip `PF0` durability just because a challenger exists.

---

### Phase 8 — `A06` tracked challenger adjudication for `PF1`
If `PF1_E5_VC07` is present in the registry, adjudicate it now.

#### Suggested CLI
```bash
python -m research.x40.run_a06 --challenger PF1_E5_VC07
```

#### Required outputs
- `challenger_manifest.yaml`
- `challenger_review.md`
- `challenger_decision.json`
- `pair_metrics_CP_PRIMARY_50_DAILYUTC.json`
- `pair_metrics_CP_SENS_20_DAILYUTC.json` (optional sensitivity)

#### Stop rule
Do **not** open a new generic `PUBLIC_FLOW` residual sprint until `PF1` exits `A06`.

---

### Phase 9 — aggregate branch decision
Run the global next-action generator.

#### Suggested CLI
```bash
python -m research.x40.make_next_action
```

#### Required output
- `reports/next_action.md`
- `reports/next_action.json`

Exactly one `primary_next_action` must be chosen.

---

## 4. Mandatory first-cycle decision meeting

At the end of Phase 9, conduct one decision review and record:

- baseline states,
- durability states,
- challenger state,
- standardized control panel profile,
- next action.

This is not optional.  
Without this review, x40 has not finished its first cycle.

---

## 5. First-cycle review checklist

Confirm all of the following before signing the cycle complete:

- `OH0` parity exists;
- `OH0` qualification exists;
- `PF0` parity exists;
- `PF0` qualification exists;
- durability state exists for both baselines;
- `PF1` adjudication exists or is explicitly absent;
- one `control_panel_CP_PRIMARY_50_DAILYUTC.md` exists;
- one `next_action.md` exists;
- all registries are updated.

If any one of these is missing, the first cycle is incomplete.

---

## 6. What x40 must NOT do during first cycle

x40 must not:

1. open an x37 blank-slate session before both current baselines have been measured;
2. declare public-flow league dead before `PF1` is adjudicated;
3. open a richer-data pivot before durability evidence says it is warranted;
4. claim clean confirmation for any baseline on the initial historical archive;
5. allow multiple competing `next_action.md` outputs;
6. publish any headline cross-system table without one explicit comparison profile ID.

---

## 7. Failure handling

### 7.1 If `OH0` parity fails
Fix the x40 OHLCV-only implementation first.  
No residual work should proceed until the control baseline is trustworthy.

### 7.2 If `PF0` parity fails
Freeze public-flow challenger work until PF0 lineage is normalized.

### 7.3 If both parity passes but durability is `BROKEN`
Skip generic residual work.  
Go straight to the decision tree.

### 7.4 If `PF1` is low-power but directionally positive
That is exactly why `A06` exists.  
Do not ignore it and do not auto-promote it.

---

## 8. First-cycle success condition

The first cycle is successful only if x40 exits with:

- two measured baselines,
- one adjudicated challenger state,
- one standardized control panel on `CP_PRIMARY_50_DAILYUTC`,
- and one next action.

Anything less is an unfinished installation, not an operating research system.
