# Step 2: Cascade Episode Labeling

**Date:** 2026-02-24
**Script:** `scripts/label_cascade_episodes.py`

---

## 1. Definition

```
cascade_episode ≡ a drawdown episode containing ≥ 2 consecutive emergency_dd exits
                  (ordered by exit_ts) within the episode window [peak_ts, end_ts].

max_run_emergency_dd = length of longest consecutive emergency_dd streak in exit-time order
is_cascade           = (max_run_emergency_dd ≥ 2)
```

---

## 2. Inputs

| Source | File | Records |
|--------|------|---------|
| Baseline trades | `out_v10_apex/trades.csv` | 101 closed trades, 33 with `exit_reason=emergency_dd` |
| Full episodes | `out_overlayA_conditional/episodes_baseline_full.csv` | 16 episodes (≥ 8% depth) |
| Holdout episodes | `out_overlayA_conditional/episodes_baseline_holdout.csv` | 2 episodes |

---

## 3. Results — Full Period

| ID | Peak | Trough | Depth% | #Trades | #EmDD | MaxRun | Cascade |
|----|------|--------|--------|---------|-------|--------|---------|
| 1 | 2019-05-12 | 2019-05-12 | 8.22 | 0 | 0 | 0 | |
| 2 | 2019-05-14 | 2019-05-23 | 11.93 | 1 | 0 | 0 | |
| 3 | 2019-05-30 | 2019-06-09 | 11.32 | 1 | 0 | 0 | |
| **4** | **2019-06-26** | **2020-07-05** | **32.74** | **25** | **12** | **2** | **YES** |
| 5 | 2020-11-24 | 2020-11-26 | 8.95 | 2 | 0 | 0 | |
| 6 | 2021-01-03 | 2021-01-04 | 10.48 | 0 | 0 | 0 | |
| 7 | 2021-01-08 | 2021-01-27 | 20.68 | 4 | 0 | 0 | |
| 8 | 2021-03-14 | 2021-03-25 | 11.60 | 1 | 0 | 0 | |
| 9 | 2021-05-03 | 2021-09-28 | 24.62 | 7 | 0 | 0 | |
| 10 | 2021-10-20 | 2021-10-27 | 10.48 | 1 | 0 | 0 | |
| **11** | **2021-11-10** | **2023-06-15** | **31.17** | **14** | **5** | **2** | **YES** |
| 12 | 2023-12-09 | 2023-12-18 | 9.58 | 1 | 0 | 0 | |
| 13 | 2024-01-11 | 2024-01-23 | 11.94 | 2 | 1 | 1 | |
| **14** | **2024-03-04** | **2024-08-07** | **36.30** | **18** | **7** | **6** | **YES** |
| 15 | 2024-12-17 | 2024-12-30 | 9.61 | 2 | 0 | 0 | |
| **16** | **2025-01-20** | **2025-03-31** | **30.86** | **18** | **8** | **3** | **YES** |

### Summary counts — Full

| Metric | Value |
|--------|-------|
| Total episodes | 16 |
| Cascade episodes | **4** (25%) |
| Cascade IDs | [4, 11, 14, 16] |
| Non-cascade episodes | 12 (75%) |

---

## 4. Results — Holdout Period

| ID | Peak | Trough | Depth% | #Trades | #EmDD | MaxRun | Cascade |
|----|------|--------|--------|---------|-------|--------|---------|
| 1 | 2024-12-17 | 2024-12-30 | 9.61 | 2 | 0 | 0 | |
| **2** | **2025-01-20** | **2025-03-31** | **30.86** | **18** | **8** | **3** | **YES** |

### Summary counts — Holdout

| Metric | Value |
|--------|-------|
| Total episodes | 2 |
| Cascade episodes | **1** (50%) |
| Cascade IDs | [2] |

---

## 5. Cross-check

All 33 emergency_dd trades are accounted for — every one falls inside an episode window:

| emergency_dd count | Location |
|--------------------|----------|
| 12 | Episode 4 (2019–2020 bear) |
| 5 | Episode 11 (2021–2023 bear) |
| 1 | Episode 13 (Jan 2024 dip — maxrun=1, NOT cascade) |
| 7 | Episode 14 (2024 mid-year, maxrun=**6**) |
| 8 | Episode 16 (2025 drawdown, maxrun=**3**) |
| **33** | **Total** |

Zero emergency_dd trades fell outside episode windows, confirming the 8% minimum depth threshold captures all cascade-relevant drawdowns.

---

## 6. Cascade anatomy — worst case (Episode 14, maxrun=6)

Trades 69–74, all consecutive emergency_dd exits during the May–Aug 2024 correction:

| Trade | Entry | Exit | Entry Price | Exit Price | Return% | Exit Reason |
|-------|-------|------|-------------|------------|---------|-------------|
| 69 | 2024-05-27 | 2024-06-11 | 69,585 | 66,853 | -3.93 | emergency_dd |
| 70 | 2024-06-12 | 2024-06-17 | 68,558 | 65,332 | -4.71 | emergency_dd |
| 71 | 2024-06-20 | 2024-06-24 | 64,934 | 61,258 | -5.66 | emergency_dd |
| 72 | 2024-06-26 | 2024-07-05 | 61,398 | 55,198 | -10.10 | emergency_dd |
| 73 | 2024-07-07 | 2024-07-08 | 57,457 | 55,130 | -4.05 | emergency_dd |
| 74 | 2024-07-17 | 2024-08-03 | 66,411 | 60,846 | -8.38 | emergency_dd |

This is the classic re-entry cascade: exit on emergency_dd → VDO signal re-entry → another emergency_dd → repeat. Each cycle bleeds ~4–10% + fees. The 6-trade streak erased $25,434 from NAV.

---

## 7. Pattern: cascade ⟷ depth relationship

| Category | Avg depth | Max depth | Avg #trades |
|----------|----------|-----------|-------------|
| Cascade (4 eps) | **32.8%** | 36.3% | 18.8 |
| Non-cascade (12 eps) | **12.2%** | 24.6% | 1.7 |

All 4 cascade episodes have depth > 30%. The deepest non-cascade episode is #9 at 24.6% (7 trades, 0 emergency_dd — all trailing_stop exits). This suggests cascading and depth are strongly linked: emergency_dd re-entry cycles are a primary mechanism that converts moderate corrections into severe drawdowns.

Episode 13 (depth=11.9%) had 1 emergency_dd exit but maxrun=1, correctly classified as non-cascade.

---

## 8. Deliverables

| Artifact | Path | Records |
|----------|------|---------|
| Labeling script | `scripts/label_cascade_episodes.py` | — |
| Full labeled CSV | `out_overlayA_conditional/episodes_labeled_full.csv` | 16 rows |
| Holdout labeled CSV | `out_overlayA_conditional/episodes_labeled_holdout.csv` | 2 rows |
| This report | `reports/overlayA_conditional_step2_cascade_labeling.md` | — |

### Added columns (vs step 1 episodes)

| Column | Type | Description |
|--------|------|-------------|
| `n_trades_in_window` | int | Total trades with exit_ts in [peak_ts, end_ts] |
| `n_emergency_dd` | int | Count of emergency_dd exits in window |
| `max_run_emergency_dd` | int | Longest consecutive emergency_dd streak |
| `is_cascade` | bool | `max_run_emergency_dd ≥ 2` |
| `trade_ids_in_window` | str | Semicolon-separated trade IDs |
