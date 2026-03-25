# D1f1 Report — Champion & Challenger Selection

## Champion Selection

### Champion: `btcsd_20260318_c3_trade4h15m`

**Why:**

- Rank 1 by adjusted preference was `btcsd_20260318_c1_av4h`, but it failed holdout hard constraints at 50 bps RT on:
  - entries/year
  - exposure
- The next highest-ranked candidate that passes both discovery hard constraints and holdout hard constraints is `btcsd_20260318_c3_trade4h15m`.
- Its representative config is **cfg_025**.

**Discovery 50 bps aggregate:**

| Metric | Value |
|---|---|
| Calmar | 1.039666 |
| CAGR | 39.7348% |
| Sharpe | 1.010698 |
| MDD | 38.2188% |
| Entries | 65 |
| Exposure | 37.0755% |

**Holdout 50 bps:**

| Metric | Value |
|---|---|
| CAGR | 33.6548% |
| Sharpe | 1.075025 |
| MDD | 29.6983% |
| Entries | 34 |
| Exposure | 44.4164% |
| Hard constraints | **PASS** |

Bluntly: reserve was weak for this candidate, but D1f1 does not use reserve as the champion gate. By the stated rule, this is the champion.

## Challenger Selection

### Challenger 1: `btcsd_20260318_c1_av4h`

**holdout_flag: FAIL**

**Why:**

- Champion exists, so challengers are allowed.
- `btcsd_20260318_c1_av4h` is the next highest-ranked candidate that passes discovery hard constraints.
- Representative config: **cfg_001**

**Discovery 50 bps aggregate:**

| Metric | Value |
|---|---|
| Calmar | 1.065877 |
| CAGR | 22.9900% |
| Sharpe | 0.976175 |
| MDD | 21.5691% |
| Entries | 22 |
| Exposure | 18.2780% |

**Holdout 50 bps:**

| Metric | Value |
|---|---|
| CAGR | 17.3999% |
| Sharpe | 1.169409 |
| MDD | 6.7520% |
| Entries | 3 |
| Exposure | 10.7715% |
| Hard constraints | **FAIL** |
| Fail reasons | entries_per_year_out_of_range \| exposure_out_of_range |

### Challenger 2: none

**Reason:** No other candidate remained discovery-valid after D1e1.

## Rejected Candidate Summary

### `btcsd_20260318_c1_av4h`

- Rejected from the **champion role only**.
- Reason: rank-1 by adjusted preference, but failed holdout hard constraints at 50 bps.

### `btcsd_20260318_c2_flow1hpb`

- Rejected from the **live set entirely**.
- Reason: zero representative configs survived discovery hard constraints in D1e1.
- No post-ablation simplification was promotable, because the best eligible ablation variant still failed hard constraints.

### No second challenger

- Reason: only two candidates reached D1e3 final ranking, and one of them became champion.

## Frozen System Specs

**Shared version identity for all live candidates:**

| Field | Value |
|---|---|
| `system_version_id` | V1 |
| `parent_system_version_id` | null |
| `freeze_cutoff_utc` | 2026-03-18T23:59:59.999000+00:00 |
| `design_inputs_end_utc` | 2026-03-18T23:59:59.999000+00:00 |

### Frozen live set

**`btcsd_20260318_c3_trade4h15m`**

- **role:** champion
- **mechanism:** daily trade-surprise permission + 4h range-position context + 15m relative-volume timing
- **frozen tunables:**
  - `q_h4_rangepos_entry = 0.65`
  - `q_h4_rangepos_hold = 0.35`
  - `rho_m15_relvol_min = 1.10`
- **layers:** 3
- **spec file:** `frozen_system_specs/btcsd_20260318_c3_trade4h15m.md`

**`btcsd_20260318_c1_av4h`**

- **role:** challenger
- **mechanism:** daily anti-vol permission + 4h range-position continuation
- **frozen tunables:**
  - `q_d1_antivol_rank = 0.35`
  - `q_h4_rangepos_entry = 0.55`
  - `q_h4_rangepos_hold = 0.45`
- **layers:** 2
- **holdout flag:** FAIL
- **spec file:** `frozen_system_specs/btcsd_20260318_c1_av4h.md`

## Files Created

- `frozen_system_specs/btcsd_20260318_c3_trade4h15m.md`
- `frozen_system_specs/btcsd_20260318_c1_av4h.md`

---

D1f1 is complete. **Ready for D1f2.**
