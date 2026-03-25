# Step 1: Non-Overlapping Drawdown Episode Extractor

**Date:** 2026-02-24
**Script:** `scripts/extract_dd_episodes.py`

---

## 1. Algorithm: Sequential Watermark Scan

The extractor walks the NAV series left-to-right in a single pass, using a high-watermark
to partition the timeline into non-overlapping drawdown episodes.

### Pseudocode

```
i ← 0
while i < N:
    # Phase 1 — Find peak (advance while making new highs)
    peak ← i
    while nav[j] keeps making new highs or DD < dd_min_pct:
        update peak if nav[j] > nav[peak]
        j ← j + 1
    # Now: nav has dropped ≥ dd_min_pct from peak

    # Phase 2 — Walk through the episode (find trough + recovery)
    trough ← j (lowest NAV seen so far)
    while k < N and nav[k] < nav[peak]:
        if nav[k] < nav[trough]: trough ← k
        if nav[k] ≥ nav[peak] × (1 − 0.001): recovery ← k; break
        k ← k + 1

    # Phase 3 — Record and advance past the episode
    end ← recovery or last_bar (if no recovery)
    emit episode(peak, trough, end)
    i ← end + 1  # resume scan — guarantees non-overlap
```

### Key properties

| Property | Guarantee |
|----------|-----------|
| **Non-overlapping** | Each bar belongs to at most 1 episode. Enforced by `i ← end + 1`. |
| **Chronological** | Episodes are emitted in time order (single left-to-right pass). |
| **Complete** | Every drawdown ≥ `dd_min_pct` from a running peak is captured. |
| **Deterministic** | No greedy ranking/re-scanning. Same input always produces same output. |

### Recovery tolerance

Recovery is detected when `nav ≥ peak_nav × (1 − 0.001)`, i.e., within 0.1% of the
peak. This prevents demanding exact float equality while keeping the tolerance tight enough
to be meaningful.

### Contrast with the existing `v10_dd_episodes.py`

| Aspect | Existing (`v10_dd_episodes.py`) | New (`extract_dd_episodes.py`) |
|--------|--------------------------------|-------------------------------|
| Approach | Greedy: find deepest DD, mask, repeat | Sequential: single-pass watermark |
| Overlap | Episodes CAN share peaks (e.g., eps 4–9 all peak at 2025-01-20) | Strictly non-overlapping by construction |
| Input | Runs its own backtest | Reads equity.csv (decoupled) |
| Episode boundary | peak → trough (recovery marks as "used" but doesn't bound) | peak → recovery (or sample end) |
| Ranking | By depth (top-N) | Chronological (all ≥ threshold) |

---

## 2. Input / Output Specification

### Input

| Field | Type | Description |
|-------|------|-------------|
| `close_time` | int (ms) | H4 bar close timestamp |
| `nav_mid` | float | Portfolio NAV at mid price |

Source: `out_v10_apex/equity.csv` (15,648 bars, 2019-01-01 → 2026-02-20)

### Output columns

| Column | Type | Description |
|--------|------|-------------|
| `episode_id` | int | Sequential ID (1-based, chronological) |
| `peak_ts` | int (ms) | Timestamp of peak NAV |
| `trough_ts` | int (ms) | Timestamp of trough NAV |
| `end_ts` | int (ms) | Recovery timestamp, or sample end if no recovery |
| `peak_nav` | float | NAV at peak |
| `trough_nav` | float | NAV at trough |
| `end_nav` | float | NAV at end (≈ peak_nav if recovered) |
| `depth_pct` | float | `(peak − trough) / peak × 100` |
| `duration_days` | float | Peak → trough in calendar days |
| `recovery_days` | float | Trough → end in calendar days (empty if no recovery) |
| `peak_date` | str | Human-readable peak date |
| `trough_date` | str | Human-readable trough date |
| `end_date` | str | Human-readable end date |
| `recovered` | bool | Whether NAV recovered to peak level |

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--dd_min_pct` | 0.08 (8%) | Minimum drawdown depth to qualify |
| `--equity` | `out_v10_apex/equity.csv` | Input equity file |
| `--outdir` | `out_overlayA_conditional/` | Output directory |

---

## 3. Results

### Full period (2019-01 → 2026-02): 16 episodes ≥ 8%

| ID | Peak | Trough | End | Depth% | Dur(d) | Recov(d) | Rcvd |
|----|------|--------|-----|--------|--------|----------|------|
| 1 | 2019-05-12 | 2019-05-12 | 2019-05-13 | 8.22 | 0.3 | 1.0 | Y |
| 2 | 2019-05-14 | 2019-05-23 | 2019-05-27 | 11.93 | 9.0 | 3.8 | Y |
| 3 | 2019-05-30 | 2019-06-09 | 2019-06-15 | 11.32 | 10.3 | 5.7 | Y |
| 4 | 2019-06-26 | 2020-07-05 | 2020-11-06 | 32.74 | 374.8 | 123.7 | Y |
| 5 | 2020-11-24 | 2020-11-26 | 2020-12-16 | 8.95 | 1.8 | 20.2 | Y |
| 6 | 2021-01-03 | 2021-01-04 | 2021-01-06 | 10.48 | 1.2 | 1.8 | Y |
| 7 | 2021-01-08 | 2021-01-27 | 2021-03-11 | 20.68 | 19.2 | 43.2 | Y |
| 8 | 2021-03-14 | 2021-03-25 | 2021-04-13 | 11.60 | 11.5 | 19.3 | Y |
| 9 | 2021-05-03 | 2021-09-28 | 2021-10-06 | 24.62 | 148.7 | 7.7 | Y |
| 10 | 2021-10-20 | 2021-10-27 | 2021-11-09 | 10.48 | 7.3 | 12.2 | Y |
| 11 | 2021-11-10 | 2023-06-15 | 2023-12-04 | 31.17 | 582.0 | 172.2 | Y |
| 12 | 2023-12-09 | 2023-12-18 | 2024-01-08 | 9.58 | 8.8 | 21.7 | Y |
| 13 | 2024-01-11 | 2024-01-23 | 2024-02-08 | 11.94 | 12.3 | 15.8 | Y |
| 14 | 2024-03-04 | 2024-08-07 | 2024-12-05 | 36.30 | 155.8 | 119.3 | Y |
| 15 | 2024-12-17 | 2024-12-30 | 2025-01-17 | 9.61 | 13.5 | 18.0 | Y |
| 16 | 2025-01-20 | 2025-03-31 | 2026-02-20 | 30.86 | 69.7 | — | N |

### Holdout period (2024-10-01 → 2026-02-20): 2 episodes ≥ 8%

| ID | Peak | Trough | End | Depth% | Dur(d) | Recov(d) | Rcvd |
|----|------|--------|-----|--------|--------|----------|------|
| 1 | 2024-12-17 | 2024-12-30 | 2025-01-17 | 9.61 | 13.5 | 18.0 | Y |
| 2 | 2025-01-20 | 2025-03-31 | 2026-02-20 | 30.86 | 69.7 | — | N |

### Notable patterns

- **3 major episodes** ≥ 30%: #4 (2019–2020, 32.7%), #11 (2021–2023, 31.2%), #14 (2024, 36.3%), #16 (2025, 30.9%)
- **Episode #11** is the longest: 582 days peak-to-trough + 172 days recovery = 754 total days
- **Episode #16** is open (unrecovered) — the most recent drawdown, still in progress at sample end
- The holdout period captures the tail of episode #14's recovery (Oct–Dec 2024) as non-episode time, plus two distinct episodes
- Holdout has limited sample size (2 episodes) — conditional analysis must account for this

### Non-overlap verification

```
PASS — all 16 episodes strictly non-overlapping
```

Each episode's `end_ts` is strictly before the next episode's `peak_ts`, confirmed programmatically.

---

## 4. Deliverables

| Artifact | Path | Status |
|----------|------|--------|
| Extractor script | `scripts/extract_dd_episodes.py` | Done |
| Full episodes CSV | `out_overlayA_conditional/episodes_baseline_full.csv` | 16 rows |
| Holdout episodes CSV | `out_overlayA_conditional/episodes_baseline_holdout.csv` | 2 rows |
| This report | `reports/overlayA_conditional_step1_episode_extractor.md` | Done |
