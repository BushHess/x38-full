# D1d2 Report — WFO Batch Execution

## Execution Progress

- **Main configs:** 30 configs × 14 folds × 2 cost levels = **840 / 840 completed**
- **Ablation variants:** 8 variants × 14 folds × 50 bps = **112 / 112 completed**
- **Total per-fold result rows:** **952 / 952 completed**

**Scope respected:**

- Discovery folds only: 2020-01-01 → 2023-06-30
- No holdout used
- No reserve_internal used

I also had to rehydrate the missing runtime `raw/` mirror from the admitted ZIP before the batch could run. The loader fallback is now in place, so the stale-path failure that blocked the batch is no longer the active issue.

## Files Saved

**`d1d_wfo_results.csv`** — 952 rows

- 840 base config rows
- 112 ablation rows
- unique `(config_id, fold, cost_bps_rt)` keys confirmed

**`d1d_wfo_daily_returns.csv`** — 86,836 rows

- concatenated daily test-period returns across all folds
- 0 duplicate `(config_id, candidate_id, cost_bps_rt, date)` rows

---

**Ready for D1d3.**
