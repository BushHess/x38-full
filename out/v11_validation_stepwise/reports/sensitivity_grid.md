# Nhiệm vụ B2: Sensitivity Grid Test — Cycle Late Only

**Script:** `out_v11_validation_stepwise/scripts/sensitivity_grid.py`
**Baseline:** V10 = V8ApexConfig() defaults
**Period:** 2019-01-01 → 2026-02-20 (warmup 365 days)
**Scenarios:** harsh (50 bps), base (31 bps), smart (13 bps)

---

## 1. Tham số & Grid Definition

### Code defaults (`v10/strategies/v11_hybrid.py:81-83`):

| Param | Code default | WFO-optimal | Grid range |
|-------|-------------|-------------|------------|
| `cycle_late_aggression` | 0.60 | 0.95 | [0.85, 0.90, 0.95] |
| `cycle_late_trail_mult` | 2.5 | 2.8 | [2.7, 3.0, 3.3] |
| `cycle_late_max_exposure` | 0.70 | 0.90 | [0.75, 0.90, 0.95] |

**Fixed params** (không thay đổi trong grid):
- `enable_cycle_phase = True`
- `cycle_early_aggression = 1.0`
- `cycle_early_trail_mult = 3.5`

**Total:** 3 × 3 × 3 = **27 grid points** × 3 scenarios = **81 backtests**

### V10 Baseline Scores:

| Scenario | Score | CAGR% | MDD% |
|----------|-------|-------|------|
| harsh | 88.94 | 37.26 | 36.28 |
| base | 112.74 | 45.55 | 34.78 |
| smart | 121.37 | 48.56 | 34.07 |

---

## 2. Full Grid Results (Δ harsh_score)

### Heatmap by aggression level

**aggression = 0.85:**

| trail \ cap | 0.75 | 0.90 | 0.95 |
|-------------|------|------|------|
| **2.7** | -7.59 | -1.74 | -1.63 |
| **3.0** | -5.12 | **+1.32** | **+1.58** |
| **3.3** | -7.52 | -1.13 | -0.86 |

**aggression = 0.90:**

| trail \ cap | 0.75 | 0.90 | 0.95 |
|-------------|------|------|------|
| **2.7** | -7.27 | -1.47 | -1.33 |
| **3.0** | -4.80 | **+1.59** | **+1.88** |
| **3.3** | -7.20 | -0.86 | -0.56 |

**aggression = 0.95:**

| trail \ cap | 0.75 | 0.90 | 0.95 |
|-------------|------|------|------|
| **2.7** | -7.05 | -1.22 | -1.14 |
| **3.0** | -4.55 | **+1.86** | **+2.10** |
| **3.3** | -6.95 | -0.58 | -0.32 |

### Readable pattern (+ = beats baseline, - = loses):

```
              cap=0.75  cap=0.90  cap=0.95
trail=2.7:      ---       ---       ---
trail=3.0:      ---       +++       +++      ← ONLY winning row
trail=3.3:      ---       ---       ---
```

---

## 3. Cross-Scenario Consistency

| Grid Point | Δ harsh | Δ base | Δ smart | All 3 win? |
|------------|---------|--------|---------|------------|
| (0.85, 3.0, 0.90) | **+1.32** | **+1.34** | **+1.37** | YES |
| (0.85, 3.0, 0.95) | **+1.58** | **+1.63** | **+1.66** | YES |
| (0.90, 3.0, 0.90) | **+1.59** | **+1.64** | **+1.66** | YES |
| (0.90, 3.0, 0.95) | **+1.88** | **+1.96** | **+1.98** | YES |
| (0.95, 3.0, 0.90) | **+1.86** | **+1.91** | **+1.93** | YES |
| (0.95, 3.0, 0.95) | **+2.10** | **+2.20** | **+2.22** | YES |

**Tất cả 6 winning points thắng consistently trên cả 3 scenarios.** Không có point nào thắng trên 1 scenario nhưng thua trên scenario khác.

---

## 4. Aggregate Statistics

| Metric | harsh | base | smart |
|--------|-------|------|-------|
| **Beat baseline** | **6/27 (22%)** | **6/27 (22%)** | **6/27 (22%)** |
| Tie | 0/27 | 0/27 | 0/27 |
| Lose | 21/27 (78%) | 21/27 (78%) | 21/27 (78%) |
| Best Δ | +2.10 | +2.20 | +2.22 |
| Worst Δ | -7.59 | -8.65 | -8.58 |
| Mean Δ | -2.24 | -2.60 | -2.55 |
| Median Δ | -1.22 | -1.25 | -1.25 |

---

## 5. Cliff Risk Analysis

### Winning region geometry:

6 winning points form a **single connected block**:
- Fixed dimension: `trail_mult = 3.0` (ALL 6 winners have trail=3.0)
- Free dimensions: aggression ∈ {0.85, 0.90, 0.95} × cap ∈ {0.90, 0.95}

```
Winning region (trail=3.0 plane):

     cap=0.75   cap=0.90   cap=0.95
aggr=0.85:  ✗         ✓          ✓
aggr=0.90:  ✗         ✓          ✓
aggr=0.95:  ✗         ✓          ✓
```

### Cliff characteristics:

| Direction | Δ score change | Cliff? |
|-----------|----------------|--------|
| trail 3.0 → 2.7 (at aggr=0.95, cap=0.95) | +2.10 → -1.14 | **YES, -3.24 cliff** |
| trail 3.0 → 3.3 (at aggr=0.95, cap=0.95) | +2.10 → -0.32 | **YES, -2.42 cliff** |
| cap 0.90 → 0.75 (at aggr=0.95, trail=3.0) | +1.86 → -4.55 | **YES, -6.41 cliff** |
| aggr 0.95 → 0.85 (at trail=3.0, cap=0.95) | +2.10 → +1.58 | No, smooth |

**Trail_mult** là chiều nhạy nhất: chỉ trail=3.0 thắng, cả 2.7 và 3.3 đều thua. Đây là **ridge pattern** — winning chỉ trên 1 hyperplane.

**Max_exposure cap = 0.75** luôn thua nặng (Δ = -4.6 to -7.6). Cap thấp quá giới hạn khả năng accumulate position.

**Aggression** ít nhạy nhất: thay đổi 0.85 → 0.95 chỉ thay Δ khoảng 0.5 points.

### Neighbor analysis:
- Avg neighbors cũng thắng: **2.3/4.8 = 48%**
- Cliff risk threshold: < 50% → **cliff risk = YES** (marginal)

---

## 6. Decomposition: Tại sao trail=3.0 thắng?

| Trail mult | Behavior | Result |
|------------|----------|--------|
| **2.7** | Trail quá tight → exit sớm trong pullbacks → miss continuation | **Thua -1 to -7 points** |
| **3.0** | Trail vừa đủ → giữ position qua pullbacks, exit trước crash lớn | **Thắng +1.3 to +2.1 points** |
| **3.3** | Trail quá wide → giữ position quá lâu → ride down trong corrections | **Thua -0.3 to -7.5 points** |

V10 baseline trail_mult (default V8Apex) nằm ở khoảng 3.2–3.5 ATR. V11 cycle late with trail=3.0 **tightens slightly** so với V10 default trong late bull — vừa đủ để protect gains mà không quá aggressive.

Trail = 2.7: over-tighten → exit quá nhiều.
Trail = 3.3: gần V10 default → V11 cycle late **gần như không có effect** → thua do aggression scaling vẫn giảm sizing.

---

## 7. Sensitivity to max_exposure

| Cap | Avg Δ harsh (across all aggr & trail) | Why |
|-----|---------------------------------------|-----|
| **0.75** | **-6.28** | Cap 75% chặn V11 accumulate → significant underperformance |
| **0.90** | **-0.81** | Moderate cap, close to V10's typical exposure |
| **0.95** | **-0.52** | Near uncapped, V11 cycle logic more visible |

Cap = 0.75 là **poison**: mọi grid point với cap=0.75 thua nặng (-4.6 to -7.6 points). V10 thường runs exposure ~85-95% trong bull. Cap 75% giới hạn quá mức → bỏ lỡ upside lớn.

---

## 8. Kết luận

### VERDICT: **FAIL**

### Lý do:

1. **Chỉ 6/27 = 22% grid points thắng baseline** — rất xa ngưỡng 60% cần cho PASS.

2. **Winning region là 1 ridge hẹp**: chỉ tại `trail_mult = 3.0`, cap ∈ {0.90, 0.95}. Trail = 2.7 hay 3.3 đều thua. Đây là **cliff risk rõ ràng** — parameter space không robust.

3. **Mean Δ harsh = -2.24**: trung bình, V11 **thua** V10 trên toàn grid. Median cũng âm (-1.22).

4. **Worst case nghiêm trọng**: Δ = -7.59 (tại trail=2.7, cap=0.75). V11 có thể gây thiệt hại lớn nếu chọn sai params.

5. **Magnitude asymmetry bất lợi**: Best win = +2.10, worst loss = -7.59. Downside risk **3.6× upside**.

### Pattern rõ ràng:

```
V11 cycle late chỉ có giá trị tại điểm "sweet spot" hẹp:
  trail_mult ≈ 3.0 (±0 steps trên grid)
  max_exposure ≥ 0.90
  aggression: không quan trọng lắm (0.85–0.95 đều OK)

Bên ngoài sweet spot này: V11 thua V10 ở 78% parameter space.
```

### Positive notes (dù FAIL):

- 6 winning points **consistent across all 3 cost scenarios** — không phải noise
- Winning region **connected** (block 3×2), không phải isolated spike
- Aggression dimension **smooth** — không cliff theo chiều này
- WFO-optimal (0.95, 2.8, 0.90) nằm gần winning zone nhưng trail=2.8 **ngoài** sweet spot trail=3.0 → giải thích tại sao WFO-optimal chỉ thắng marginally (+1.86)

---

## 9. Data Files

| File | Mô tả |
|------|--------|
| `out_v11_validation_stepwise/sensitivity_grid.csv` | 27 rows, deltas cho 3 scenarios |
| `out_v11_validation_stepwise/sensitivity_grid_full.csv` | 81 rows (27×3), full V10/V11 metrics |
| `out_v11_validation_stepwise/sensitivity_grid.json` | Aggregate stats + verdict |
| `out_v11_validation_stepwise/scripts/sensitivity_grid.py` | Reproducible script |
| `out_v11_validation_stepwise/reports/sensitivity_grid.md` | This report |
