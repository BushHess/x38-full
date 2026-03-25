# 08 — Divergence Event Attribution

**Date**: 2026-03-03
**Script**: `research_reports/artifacts/08_divergence_event_attribution.py`
**Artifacts**:
  `research_reports/artifacts/08_top_divergence_events.csv` (100 events)
  `research_reports/artifacts/08_divergence_event_summary.json`

---

## 1. Canonical Pair Identity

| Field              | Candidate                    | Baseline                    |
|:-------------------|:-----------------------------|:----------------------------|
| Validation label   | v12_emdd_ref_fix             | v10_baseline_frozen         |
| Underlying strategy| V8Apex                       | V8Apex                      |
| Config file        | `configs/v12/v12_emdd_ref_fix_step5_best.yaml` | `configs/frozen/v10_baseline.yaml` |
| Emergency DD mode  | `emdd_ref_mode=fixed`        | `emergency_ref=pre_cost_legacy` |
| Emergency DD %     | **4%** (from true post-fill NAV) | **28%** (from pre-cost entry NAV) |
| RSI method         | wilder                       | wilder                      |
| Entry cooldown     | 3 bars                       | 3 bars                      |

**Source**: `out/validate/v12_vs_v10/2026-02-24/run_meta.json`, confirmed
against `configs/` snapshots in the validation output directory.

**Key mechanism difference**: Both strategies are V8Apex. The ONLY functional
difference is the emergency drawdown (EMDD) exit: v12 triggers at 4% drawdown
from the true post-fill NAV; baseline triggers at 28% from the pre-cost legacy
entry NAV. The v12 candidate is 7× more aggressive on emergency exits.

**Validation config**: 2019-01-01 to 2026-02-20, 365d warmup, harsh cost
(50 bps RT), $10,000 initial, 15,647 reporting bars.

---

## 2. Event Concentration Summary

### 2.1 Total excess return vs top-N events

| Tier         | Excess return | % of total | Remaining bars | % of total |
|:-------------|:-------------|:-----------|:---------------|:-----------|
| Full series  | **+0.1078**  | 100%       | —              | —          |
| Top 1        | −0.0926      | −85.8%     | +0.2004        | +185.8%    |
| Top 5        | −0.0869      | −80.6%     | +0.1947        | +180.6%    |
| Top 10       | −0.0712      | −66.0%     | +0.1790        | +166.0%    |
| Top 20       | −0.1124      | −104.2%    | +0.2202        | +204.2%    |
| Top 50       | +0.0010      | +0.9%      | +0.1068        | +99.1%     |
| Top 100      | +0.0925      | +85.8%     | +0.0154        | +14.2%     |

The top 20 events are **net harmful** to the candidate. Their combined excess
return is −0.1124, which is −104.2% of the total — meaning they cost MORE than
the total net edge. The candidate's positive net excess (+0.1078) comes entirely
from the remaining 15,627 smaller bars, which contribute +0.2202.

### 2.2 Absolute differential concentration

| Top N | Abs differential | % of total abs (4.319) |
|:------|:-----------------|:----------------------|
| 1     | 0.0926           | 2.1%                  |
| 5     | 0.2618           | 6.1%                  |
| 10    | 0.4016           | 9.3%                  |
| 20    | 0.6143           | 14.2%                 |
| 50    | 1.0935           | 25.3%                 |
| 100   | 1.6522           | 38.3%                 |

The top 100 events (0.64% of bars) account for 38.3% of all absolute
differential. The remaining 99.36% of bars produce 61.7%.

### 2.3 Drawdown

| Metric      | Candidate | Baseline | Difference |
|:------------|:----------|:---------|:-----------|
| Max DD      | 44.14%    | 35.90%   | +8.24%     |

The candidate has **worse** max drawdown despite its 7× tighter emergency DD
trigger. The 4% emergency DD was designed to reduce drawdowns but achieves
the opposite.

---

## 3. Top-Event Table (Top 20)

| Rank | Date             | Simp Diff  | Cand Ret  | Base Ret  | Cand Exp | Base Exp | Pattern              |
|-----:|:-----------------|:-----------|:----------|:----------|:---------|:---------|:---------------------|
|    1 | 2020-03-12 11:59 | **−9.26%** | −9.39%    | −0.13%    | 0.47     | 0.00     | Cand holds, base flat |
|    2 | 2021-11-26 11:59 | +4.80%     | 0.00%     | −4.80%    | 0.00     | 0.84     | Cand flat, base holds |
|    3 | 2021-09-26 11:59 | −4.10%     | 0.00%     | +4.10%    | 0.00     | 0.93     | Cand flat, base holds |
|    4 | 2021-11-28 23:59 | −4.08%     | 0.00%     | +4.08%    | 0.00     | 0.85     | Cand flat, base holds |
|    5 | 2019-05-26 19:59 | +3.94%     | +5.92%    | +1.98%    | 0.95     | 0.33     | Both in, diff exposure |
|    6 | 2023-06-06 19:59 | −3.77%     | 0.00%     | +3.77%    | 0.00     | 0.97     | Cand flat, base holds |
|    7 | 2025-02-25 07:59 | +2.91%     | 0.00%     | −2.91%    | 0.00     | 0.95     | Cand flat, base holds |
|    8 | 2023-06-10 07:59 | +2.47%     | 0.00%     | −2.47%    | 0.00     | 0.97     | Cand flat, base holds |
|    9 | 2019-11-10 19:59 | −2.44%     | 0.00%     | +2.44%    | 0.00     | 0.87     | Cand flat, base holds |
|   10 | 2024-07-15 03:59 | +2.39%     | +2.39%    | 0.00%     | 0.79     | 0.00     | Cand holds, base flat |
|   11 | 2024-07-16 07:59 | −2.28%     | −2.28%    | 0.00%     | 0.79     | 0.00     | Cand holds, base flat |
|   12 | 2021-10-01 11:59 | +2.28%     | +4.30%    | +2.02%    | 0.73     | 0.36     | Both in, diff exposure |
|   13 | 2020-05-21 15:59 | −2.25%     | −2.25%    | 0.00%     | 0.68     | 0.00     | Cand holds, base flat |
|   14 | 2025-02-24 23:59 | +2.18%     | −0.24%    | −2.41%    | 0.00     | 0.95     | Cand exited, base held |
|   15 | 2021-09-26 07:59 | +2.15%     | 0.00%     | −2.15%    | 0.00     | 0.92     | Cand flat, base holds |
|   16 | 2025-06-23 23:59 | −2.11%     | 0.00%     | +2.11%    | 0.00     | 1.00     | Cand flat, base holds |
|   17 | 2025-06-22 23:59 | −2.10%     | 0.00%     | +2.10%    | 0.00     | 1.00     | Cand flat, base holds |
|   18 | 2025-01-27 23:59 | −1.98%     | 0.00%     | +1.98%    | 0.00     | 0.83     | Cand flat, base holds |
|   19 | 2019-11-11 07:59 | +1.98%     | 0.00%     | −1.98%    | 0.00     | 0.87     | Cand flat, base holds |
|   20 | 2025-01-27 15:59 | −1.97%     | 0.00%     | +1.97%    | 0.00     | 0.83     | Cand flat, base holds |

### 3.1 Dominant pattern

In **16 of the top 20** events, one strategy is flat (exposure ≈ 0) while the
other holds BTC at high exposure (0.79–1.00). Of these 16:
- 13 events: **candidate flat, baseline holds**
- 3 events: candidate holds, baseline flat

The candidate is out of the market during most large-differential bars. This
is the direct consequence of the 4% emergency DD: it exits positions on small
drawdowns and is then in cooldown while the baseline continues to ride the trend.

### 3.2 The single largest event

**Rank 1: 2020-03-12 11:59 UTC (COVID crash)**. Differential = −9.27%.
The candidate holds BTC (exp 0.47) during the crash while the baseline is flat.
This is paradoxical: v12's tighter DD should have exited sooner. What happened:
the baseline had already exited the trade (via trail stop or trend reversal) on
a previous bar. The candidate's 4% DD had previously kicked it out of an
earlier position and re-entered on a new signal — placing it back in the market
just before the crash. The aggressive churn created re-entry risk.

---

## 4. Trigger / State Attribution

### 4.1 Event type distribution (top 100)

| Event type             | Count | Description                                  |
|:-----------------------|------:|:---------------------------------------------|
| other                  |    74 | Already in divergent states; market move hits |
| same_state_diff_exp    |    14 | Both in market, different exposure levels     |
| base_exit_cand_hold    |     7 | Baseline exited, candidate stayed in          |
| cand_exit_base_hold    |     5 | Candidate exited, baseline stayed in          |

**74 of 100 top events are "other"** — meaning both strategies were already in
divergent positions (one flat, one holding) from previous bars. The large
differential on these bars is simply the market moving while positions differ.

Only **12 events** involve an actual entry/exit transition at that bar. The
divergence is not concentrated at trigger moments; it is the ongoing
consequence of position trajectories that diverged bars or days earlier.

### 4.2 Economic classification (top 100)

| Class                        | Count | PnL contribution |
|:-----------------------------|------:|:-----------------|
| beneficial (generic)         |    49 | +0.7685          |
| harmful (generic)            |    39 | −0.6514          |
| beneficial_stayed_in         |     4 | +0.0486          |
| harmful_stayed_in            |     3 | −0.1178          |
| beneficial_crash_avoidance   |     3 | +0.0434          |
| beneficial_exit_at_top       |     1 | +0.0119          |
| harmful_premature_exit       |     1 | −0.0107          |

Net PnL of top 100 events: +0.0925. This decomposes as:
- Beneficial: +0.8724 (57 events)
- Harmful: −0.7799 (43 events)

The beneficial and harmful events nearly cancel. The net is a small residual.

---

## 5. Forward Outcome Analysis

For each of the top 5 events, cumulative returns over +1/+6/+24/+42 bars:

### Rank 1: 2020-03-12 (COVID crash, diff = −9.27%)

| Horizon | Cand fwd | Base fwd | Fwd diff |
|:--------|:---------|:---------|:---------|
| +1 bar  | −0.14%   | 0.00%    | −0.14%   |
| +6 bars | −0.14%   | 0.00%    | −0.14%   |
| +24     | +2.24%   | 0.00%    | +2.24%   |
| +42     | +7.68%   | +3.46%   | +4.21%   |

The candidate partially recovered over 42 bars but was still worse off net.

### Rank 2: 2021-11-26 (BTC drop, diff = +4.80%)

| Horizon | Cand fwd | Base fwd | Fwd diff |
|:--------|:---------|:---------|:---------|
| +1 bar  | 0.00%    | −5.18%   | +5.18%   |
| +6 bars | 0.00%    | +1.38%   | −1.38%   |
| +24     | 0.00%    | −5.10%   | +5.10%   |
| +42     | 0.00%    | −9.40%   | +9.40%   |

Candidate was flat and avoided a sustained BTC decline. Genuine crash avoidance.

### Rank 3: 2021-09-26 (BTC rally, diff = −4.10%)

| Horizon | Cand fwd | Base fwd | Fwd diff |
|:--------|:---------|:---------|:---------|
| +1 bar  | −0.27%   | +4.10%   | −4.37%   |
| +6 bars | −0.27%   | +1.45%   | −1.72%   |
| +24     | +3.73%   | +20.00%  | −16.27%  |
| +42     | +4.86%   | +35.95%  | −31.09%  |

Candidate was flat and missed the entire Oct-Nov 2021 rally. Severe premature
exit with compounding opportunity cost over 42 bars.

### Rank 14: 2025-02-24 (actual cand_exit event, diff = +2.18%)

| Horizon | Cand fwd | Base fwd | Fwd diff |
|:--------|:---------|:---------|:---------|
| +1 bar  | 0.00%    | −2.91%   | +2.91%   |
| +6 bars | 0.00%    | −2.54%   | +2.54%   |
| +24     | 0.00%    | −0.77%   | +0.77%   |
| +42     | 0.00%    | +2.83%   | −2.83%   |

Genuine emergency DD trigger. Candidate exited and avoided −2.5% baseline loss
over 6 bars, but baseline recovered by +42 bars. Short-term beneficial.

---

## 6. Economic Interpretation

### 6.1 The difference is a rare-event treatment patch, not a broad edge

The evidence is unambiguous:

1. **Top-20 events are net harmful** (−0.1124, or −104% of total excess).
   The total positive excess (+0.1078) comes from the remaining 15,627
   non-extreme bars.

2. **A single event (COVID crash, −9.27%) dominates**: It alone costs −85.8%
   of the total excess. Without this one bar, the candidate's excess return
   would roughly double.

3. **Position divergence, not trigger events, drives the differential**: 74 of
   the top 100 events are bars where both strategies were already in different
   states. The v12's aggressive 4% DD creates a different position trajectory,
   and ordinary market moves then generate large differentials.

4. **The 4% DD increases drawdowns**: MDD is 44.14% (candidate) vs 35.90%
   (baseline). The mechanism designed to reduce drawdowns makes them worse,
   because aggressive exits create re-entry risk. The COVID crash event is
   the clearest example: the baseline had already exited via natural trail
   stop, while the candidate had re-entered after a 4% DD exit.

### 6.2 The excess return is a fragile cancellation

The candidate's net +0.1078 excess is the residual of:
- +0.8724 from 57 beneficial events in the top 100
- −0.7799 from 43 harmful events in the top 100
- +0.0154 from the remaining 15,547 bars

This is a cancellation of effects 8× larger than the result. The sign of the
net excess depends heavily on whether specific events occurred (COVID crash
timing, specific entry/exit alignment). A single additional harmful event of
the COVID type would flip the sign.

### 6.3 The candidate is not a strict improvement

| Metric     | Candidate | Baseline | Better? |
|:-----------|:----------|:---------|:--------|
| Sharpe     | 1.2297    | 1.1872   | Cand    |
| CAGR       | 39.47%    | 37.45%   | Cand    |
| Max DD     | 44.14%    | 35.90%   | **Base**|
| Trades     | 102       | 98       | —       |

The candidate wins on Sharpe/CAGR but loses on MDD. This is a tradeoff, not
an improvement. The validation pipeline correctly rejected this pair.

---

## 7. Recommendation

### For evaluating the v12-vs-v10 pair specifically

This pair should NOT be evaluated with aggregate statistical tests (bootstrap,
subsampling). The difference is driven by a small number of large events
arising from position-trajectory divergence, not by a systematic per-bar edge.
Appropriate evaluation would be:

1. **Trade-level comparison**: Match entry/exit pairs between strategies and
   compare trade outcomes directly.
2. **Event decomposition**: Attribute each divergence episode to a specific
   mechanism (emergency DD trigger, cooldown-induced re-entry timing, etc.)
   and evaluate each mechanism's expected value.
3. **Regime conditioning**: Evaluate separately in high-vol (crash) regimes vs
   normal regimes, since the large events are concentrated in crashes.

### For the project's inference infrastructure

The bootstrap/subsampling pipeline is appropriate for comparing **genuinely
different** strategies (e.g., VTREND vs V8Apex, where ρ ≈ 0.648 and the
position trajectory diverges broadly). It is not informative for near-identical
variants that differ only in a rare-event trigger threshold.

### For the 4% emergency DD mechanism

The evidence suggests the 4% emergency DD is counterproductive in its current
form. It creates churn that worsens max drawdown and generates re-entry risk
at the worst possible times. If a tighter emergency DD is desired, it should
be coupled with a re-entry cooldown long enough to prevent re-entering during
the same drawdown episode.

---

*Generated by `08_divergence_event_attribution.py` on 2026-03-03.*
*Full event table in `artifacts/08_top_divergence_events.csv`.*
*Summary data in `artifacts/08_divergence_event_summary.json`.*
