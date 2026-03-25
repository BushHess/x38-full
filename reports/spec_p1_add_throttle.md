# Spec: P1 Add-Throttle Overlay (Design Only)

**Status:** Design-only spec — Codex implements in Step 3B
**Scope:** Mechanism, parameters, failure modes, measurement plan, robustness grid
**Prerequisite reading:**
- `btc-spot/strategies/v12_emdd_ref_fix/strategy.py` (current add logic, lines 469-579)
- `btc-spot/validation/suites/churn_metrics.py` (cascade/churn measurement)
- `btc-spot/v10/research/drawdown.py` (DD episode detection)

---

## 1. Problem Statement

The current strategy uses a flat `max_add_per_bar` cap and an emergency-DD cooldown (V1: flat 12-bar, V2: escalating 3/12-bar) to limit position-building during drawdowns. These mechanisms are reactive: they only fire **after** an emergency DD exit has already occurred.

**The gap:** During a developing drawdown (e.g., NAV is 15% below peak but hasn't hit the 28% emergency DD threshold), the strategy continues adding to positions at full sizing. This creates two problems:

1. **Cascade risk amplification:** Adds during a drawdown deepen the eventual trough. If the market continues against the position, the additional exposure magnifies losses, making emergency DD exits more likely and more costly.

2. **Fee drag during weak periods:** Adds that are quickly stopped out generate fees without meaningful P&L contribution. The churn metrics show elevated `cascade_leq3` rates during drawdown regimes.

**What we are NOT doing:** This overlay does NOT block the **first entry** into a new position. It only throttles **adds** (position increases when `exposure > 0`). The strategy must remain able to enter new positions at all times (subject to existing cooldowns). The goal is to make the strategy more conservative about increasing position size during portfolio-level stress, not to prevent it from trading.

---

## 2. Mechanism

### 2.1 Core Idea

When the portfolio equity is in drawdown, scale down the `max_add_per_bar` limit based on the drawdown depth. This creates a smooth throttle: shallow drawdowns allow near-normal adds, deep drawdowns progressively restrict adds to a minimum.

### 2.2 Where It Lives

**Insert point:** In `_check_entry()`, after the existing cooldown gates (lines 474-485) and before the sizing computation (line 500). The throttle modifies the effective `max_add_per_bar` for the current bar only. It does NOT modify `entry_aggression`, `gap`, or `base` — it only caps the final add size.

```python
# Pseudocode — insert after line 485 in _check_entry():

# Add-throttle overlay (only applies to adds, not first entries)
if state.exposure > 0.01:  # this is an add, not a first entry
    effective_max_add = self._throttled_max_add(state, c)
else:
    effective_max_add = c.max_add_per_bar

# ... later, at line 563 (final sizing clamp):
sz = min(sz, effective_max_add, gap)  # was: min(sz, c.max_add_per_bar, gap)
```

### 2.3 Throttle Function

```python
def _throttled_max_add(self, state, c) -> float:
    """Compute effective max_add_per_bar based on portfolio DD depth."""
    if self._equity_peak <= 0:
        return c.max_add_per_bar  # no peak tracked yet

    dd = 1.0 - state.nav / self._equity_peak
    if dd <= 0:
        return c.max_add_per_bar  # at or above peak, no throttle

    if dd < c.add_throttle_dd1:
        return c.max_add_per_bar  # below first threshold, no throttle

    if dd >= c.add_throttle_dd2:
        return c.max_add_per_bar * c.add_throttle_mult  # at/above second threshold, full throttle

    # Linear interpolation between dd1 and dd2
    progress = (dd - c.add_throttle_dd1) / (c.add_throttle_dd2 - c.add_throttle_dd1)
    mult = 1.0 - progress * (1.0 - c.add_throttle_mult)
    return c.max_add_per_bar * mult
```

**Visual:**

```
max_add_per_bar
  0.35 ┤────────────┐
       │            │
       │            │
  0.28 ┤            ╲
       │             ╲          linear ramp
  0.21 ┤              ╲
       │               ╲
  0.14 ┤                ╲
       │                 ╲
  0.07 ┤                  ╲────────────
       │
  0.00 ┤
       └────┬────┬────┬────┬────┬────┬── dd%
            0%   8%  12%  16%  20%  24%
                 dd1       dd2
```

---

## 3. Parameters

### 3.1 Parameter Table

| Param | Type | Default | Range | Description |
|-------|------|---------|-------|-------------|
| `add_throttle_dd1` | float | **0.08** | [0.03, 0.20] | DD depth where throttle begins. Below this, adds are unrestricted. |
| `add_throttle_dd2` | float | **0.18** | [0.10, 0.28] | DD depth where throttle reaches full strength. Above this, adds use `max_add_per_bar * add_throttle_mult`. |
| `add_throttle_mult` | float | **0.20** | [0.0, 0.50] | Multiplier at full throttle. 0.20 means adds are capped at 20% of normal `max_add_per_bar` (i.e., 0.07 exposure per bar instead of 0.35). |

**Total new parameters: 3** (within the ≤3 constraint).

### 3.2 Default Value Rationale

**`add_throttle_dd1 = 0.08` (8% drawdown):**
- The strategy's `dd_adaptive_start` (when enabled) is 0.16. Setting the add-throttle onset at half that level provides earlier protection specifically for adds.
- DrawdownEpisode analysis shows that 8% is roughly the median peak DD of episodes that **recover** without triggering emergency DD. Episodes that exceed 8% have a ~40% probability of eventually reaching 20%+.
- At 8% DD, the strategy has lost approximately $800 on a $10,000 account. This is noticeable but recoverable — the right point to start being cautious with adds.

**`add_throttle_dd2 = 0.18` (18% drawdown):**
- This is 10 percentage points below `emergency_dd_pct` (0.28). At 18% DD, the strategy is in serious trouble but hasn't triggered emergency exit yet.
- The gap (0.18 → 0.28) gives the full-throttle zone 10pp of runway. If adds were unrestricted here, each additional add risks pushing the portfolio closer to emergency DD.
- The `dd_adaptive` feature (when enabled) reaches its floor at `emergency_dd_pct` (0.28). Setting `dd2` at 0.18 means the add-throttle reaches full strength before `dd_adaptive` reaches its minimum — they complement each other rather than overlapping at the same DD level.

**`add_throttle_mult = 0.20` (20% of normal):**
- At full throttle, `max_add_per_bar` drops from 0.35 to 0.07. This allows small adds (e.g., if the position is far from target and the signal is very strong) but prevents the aggressive pyramiding that characterizes cascade blowups.
- Setting `mult = 0.0` (total add block) was considered but rejected: it creates a hard cliff that prevents the strategy from recovering exposure after a deep drawdown. A residual 20% allows slow re-accumulation if the trend reverses.
- `mult = 0.50` was considered too permissive: at 18% DD, allowing 50% of normal adds (0.175 per bar) can still produce meaningful cascade risk.

### 3.3 Recovery Behavior

**No explicit recovery threshold parameter is needed.** The throttle automatically releases as NAV recovers toward the equity peak:

- When DD decreases below `dd2` → throttle begins relaxing (linear interpolation in reverse)
- When DD decreases below `dd1` → throttle fully releases
- When NAV hits new equity peak (DD = 0%) → normal adds resume

The equity peak (`self._equity_peak`) is updated to the new high whenever `state.nav > self._equity_peak`, which is already tracked for the `dd_adaptive` feature (strategy.py, referenced in sizing logic).

**Edge case: The equity peak should ONLY be updated when the strategy is flat or at the start of a new position.** If the peak is updated continuously (including during trades), the DD calculation becomes path-dependent in confusing ways. However, the current codebase already updates the peak continuously — maintain consistency and do not change this behavior for the add-throttle.

### 3.4 Config Integration

Add to the strategy config dataclass (in the overlay parameters section):

```python
# Add-throttle overlay
enable_add_throttle: bool = False
add_throttle_dd1: float = 0.08
add_throttle_dd2: float = 0.18
add_throttle_mult: float = 0.20
```

The `enable_add_throttle` flag ensures backward compatibility: existing configs produce identical results until the throttle is explicitly enabled.

---

## 4. Failure Modes

### 4.1 Failure Mode: Blocks Recoveries

**Scenario:** The market has a sharp V-shaped reversal. NAV drops to 15% DD (within the throttle zone), then the market reverses strongly. The strategy sees a strong entry signal and wants to add to catch the recovery, but the throttle limits the add size.

**Severity:** Moderate. The throttle reduces add size but doesn't block it entirely (`mult = 0.20` allows small adds). The first entry into a new position is unrestricted.

**Detection metric:** Compare `mean_buy_fills_per_episode` between candidate (throttled) and baseline (unthrottled). If the candidate has significantly fewer fills during V-shaped recovery episodes, the throttle is being too aggressive.

**Mitigation:**
- The throttle only affects adds, not first entries. A V-shaped recovery that starts from flat (no position) is completely unaffected.
- If the strategy exits at emergency DD (28%) and re-enters after cooldown, the first re-entry is at full size.
- If this failure mode is dominant, increase `add_throttle_mult` from 0.20 to 0.30-0.40.

### 4.2 Failure Mode: Increases Tracking Error

**Scenario:** When the candidate throttles adds but the baseline doesn't, the candidate's exposure profile diverges significantly from the baseline. This increases the variance of the delta series without improving the mean, making bootstrap CIs wider.

**Severity:** Low-to-moderate. This is expected behavior — the throttle intentionally changes the exposure profile. The tracking error is "good" if the candidate avoids deep DD that the baseline suffers.

**Detection metric:** Compare `max_exposure_during_trade` distributions between candidate and baseline matched trades. If the candidate has systematically lower max exposure, the throttle is working as intended. If `add_mismatch_rate > 0.30`, the strategies have diverged enough that paired analysis may be unreliable.

**Mitigation:**
- This is informational, not actionable. The throttle inherently increases tracking error.
- Use the `add_diagnostics.add_mismatch_rate` field to flag when divergence is high.

### 4.3 Failure Mode: Does Nothing (Throttle Never Activates)

**Scenario:** The strategy's drawdowns never reach `dd1` (8%), so the throttle never fires. This can happen if:
- The backtest period is too short or too favorable (persistent bull market)
- The emergency DD exits prevent DD from lingering in the throttle zone (NAV drops fast past `dd1` and exits at `emergency_dd_pct` before the throttle has effect)

**Severity:** None (the throttle is a no-op, equivalent to `enable_add_throttle = False`).

**Detection metric:** Count the number of bars where the throttle was active (DD in [dd1, dd2+]):

```python
throttle_active_bars = sum(1 for bar in equity if dd1 <= bar.dd_pct)
throttle_activation_rate = throttle_active_bars / total_bars
```

If `throttle_activation_rate < 0.01` (active < 1% of the time), the throttle had minimal opportunity to help. This is not a failure per se, but it means the throttle's value cannot be assessed from this backtest.

**Mitigation:** Verify on bear-market sub-periods (2022) where DD is persistent and deep.

### 4.4 Failure Mode: Over-Throttling in Choppy Regimes

**Scenario:** In a CAUTION regime with frequent shallow drawdowns (5-12%), the throttle repeatedly activates and limits adds. The strategy underperforms because it can't build positions to take advantage of mean-reversion opportunities.

**Severity:** Moderate. CAUTION regimes already apply `caution_mult = 0.50`, so the throttle stacks on top of an existing size reduction.

**Detection metric:** Compare trade-level PnL in CAUTION regime between candidate and baseline. If the candidate underperforms specifically in CAUTION, the throttle is over-constraining.

**Mitigation:** Raise `add_throttle_dd1` from 0.08 to 0.12, so the throttle only activates during more serious drawdowns.

---

## 5. What to Measure

### 5.1 Primary Metrics

These metrics must be computed for every validation run with the add-throttle enabled:

| # | Metric | Definition | Source | Purpose |
|---|--------|-----------|--------|---------|
| 1 | `mean_buy_fills_per_episode` | Total buy fills ÷ number of DD episodes (≥5% DD) | Fills + DD episodes | Detects recovery-blocking (§4.1) |
| 2 | `total_fees_candidate` / `total_fees_baseline` | Total fees ratio | `churn_metrics.csv` | Detects fee drag reduction |
| 3 | `share_emergency_dd` | Fraction of exits due to emergency DD | `churn_metrics.csv` | Lower = fewer catastrophic exits |
| 4 | `max_drawdown_mid_pct` | Maximum drawdown on mid-price NAV | Backtest summary | Primary DD metric |
| 5 | `trade_level_bootstrap.mean_diff` | Bootstrap mean of per-bar return diff | `trade_level_summary.json` | Primary performance metric |
| 6 | `trade_level_bootstrap.p_gt_0` | Bootstrap P(candidate > baseline) | `trade_level_summary.json` | Statistical confidence |
| 7 | `trade_level_bootstrap.ci95_low` | Lower bound of 95% CI | `trade_level_summary.json` | Downside risk assessment |

### 5.2 Secondary Metrics (Diagnostic)

| # | Metric | Definition | Purpose |
|---|--------|-----------|---------|
| 8 | `throttle_activation_rate` | Fraction of bars where throttle was active | Quantifies throttle engagement |
| 9 | `cascade_leq3` | % of emergency DD exits followed by re-entry within 3 bars | Measures cascade behavior |
| 10 | `add_mismatch_rate` | % of matched trades where one side was an add and the other wasn't | Measures strategy divergence |
| 11 | `calmar` | CAGR / max_drawdown_mid_pct | Risk-adjusted return |
| 12 | `candidate_cagr_pct` - `baseline_cagr_pct` | CAGR delta | Gross performance impact |

### 5.3 New Metric: `mean_buy_fills_per_episode`

**Definition:**

```python
from v10.research.drawdown import detect_drawdown_episodes

episodes = detect_drawdown_episodes(candidate_equity, min_dd_pct=5.0)
total_buy_fills_during_episodes = 0

for ep in episodes:
    fills_in_episode = [
        f for f in candidate_fills
        if ep.peak_ms <= f.ts_ms <= (ep.recovery_ms or equity[-1].close_time)
        and f.side == Side.BUY
    ]
    total_buy_fills_during_episodes += len(fills_in_episode)

mean_buy_fills_per_episode = total_buy_fills_during_episodes / max(len(episodes), 1)
```

**Report in:** `trade_level_summary.json` under `add_diagnostics`.

**Expected behavior:**
- Baseline: higher `mean_buy_fills_per_episode` (adds freely during DD)
- Candidate (throttled): lower value (fewer adds during DD)
- If candidate value is < 50% of baseline: throttle may be too aggressive

### 5.4 Reporting Format

Add to `churn_metrics.csv` two new columns for throttle-enabled runs:

| Column | Type | Description |
|--------|------|-------------|
| `throttle_activation_rate` | float | Fraction of bars where add-throttle was active |
| `mean_buy_fills_per_episode` | float | Average buy fills during DD episodes |

These columns are `0.0` when `enable_add_throttle = False`.

---

## 6. Robustness Grid

### 6.1 Design Philosophy

The grid is intentionally **small** (3×3 = 9 cells). The goal is to assess whether the throttle's effect is robust to reasonable parameter variation, NOT to optimize the parameters. Optimization would be done in a separate Step 4 sensitivity analysis.

### 6.2 Grid Definition

| Parameter | Values | Rationale |
|-----------|--------|-----------|
| `add_throttle_dd1` | **0.05, 0.08, 0.12** | Tests early (5%), default (8%), and late (12%) onset |
| `add_throttle_dd2` | **0.14, 0.18, 0.22** | Tests tight (14%), default (18%), and wide (22%) full-throttle point |
| `add_throttle_mult` | **0.20** (fixed) | Hold multiplier fixed at default to isolate DD threshold effects |

**Total cells:** 3 × 3 × 1 = **9 runs.**

### 6.3 Grid Execution

```python
THROTTLE_GRID = [
    {"add_throttle_dd1": dd1, "add_throttle_dd2": dd2, "add_throttle_mult": 0.20}
    for dd1 in [0.05, 0.08, 0.12]
    for dd2 in [0.14, 0.18, 0.22]
    if dd2 > dd1 + 0.04  # enforce minimum gap of 4pp between dd1 and dd2
]
```

The `dd2 > dd1 + 0.04` constraint eliminates degenerate cells where the ramp is too narrow (< 4 percentage points). This removes the cell `(dd1=0.12, dd2=0.14)`, leaving **8 valid cells.**

### 6.4 What to Report per Cell

For each grid cell, report:

```json
{
  "add_throttle_dd1": 0.08,
  "add_throttle_dd2": 0.18,
  "add_throttle_mult": 0.20,
  "candidate_score": 94.81,
  "baseline_score": 92.15,
  "score_delta": 2.66,
  "candidate_mdd_pct": 24.5,
  "baseline_mdd_pct": 28.1,
  "mdd_delta": -3.6,
  "candidate_cagr_pct": 25.0,
  "baseline_cagr_pct": 26.2,
  "cagr_delta": -1.2,
  "bootstrap_p_gt_0": 0.823,
  "bootstrap_mean_diff": 0.000234,
  "throttle_activation_rate": 0.089,
  "share_emergency_dd_candidate": 0.12,
  "share_emergency_dd_baseline": 0.18,
  "mean_buy_fills_per_episode_candidate": 3.2,
  "mean_buy_fills_per_episode_baseline": 5.1,
  "fee_drag_pct_candidate": 8.5,
  "fee_drag_pct_baseline": 11.2
}
```

### 6.5 Robustness Assessment Criteria

The throttle is considered **robust** if:

1. **Score delta >= -2.0 in ALL cells.** The throttle should never catastrophically hurt performance. A small score loss (up to 2 points) is acceptable if MDD improves.

2. **MDD improves in >= 6/8 cells.** The primary goal is drawdown reduction. If MDD doesn't improve in most configurations, the throttle is not doing its job.

3. **Bootstrap `p_gt_0 >= 0.40` in ALL cells.** Even if the throttle slightly underperforms on mean return, it should never produce a clear degradation (P < 0.40 means >60% chance it's worse).

4. **No cell has `mean_buy_fills_per_episode < 1.0`.** If any configuration completely prevents adds during episodes, it's too aggressive.

5. **`throttle_activation_rate` is in `[0.02, 0.30]` for the default cell.** Below 2%: throttle rarely fires (might as well not have it). Above 30%: throttle is almost always on (too aggressive, would hurt returns).

### 6.6 Grid Output

Write to `results/add_throttle_grid.csv`:

```csv
dd1,dd2,mult,score_delta,mdd_delta,cagr_delta,bootstrap_p_gt_0,throttle_activation_rate,share_ed_cand,share_ed_base,mean_fills_ep_cand,mean_fills_ep_base,fee_drag_cand,fee_drag_base
0.05,0.14,0.20,...
0.05,0.18,0.20,...
...
```

And a summary in `reports/add_throttle_robustness.md`:

```markdown
## Add-Throttle Robustness Grid (3×3)

### Grid results

| dd1 | dd2 | Score Δ | MDD Δ | CAGR Δ | P(>0) | Activation% |
|----:|----:|--------:|------:|-------:|------:|------------:|
| 0.05 | 0.14 | ... | ... | ... | ... | ... |
| ... | ... | ... | ... | ... | ... | ... |

### Assessment

- Score >= -2.0 in all cells: {PASS|FAIL}
- MDD improves in >= 6/8 cells: {PASS|FAIL}
- P(>0) >= 0.40 in all cells: {PASS|FAIL}
- No cell blocks recovery (fills/ep >= 1.0): {PASS|FAIL}
- Default cell activation rate in [2%, 30%]: {PASS|FAIL}

### Recommended configuration

{dd1=0.08, dd2=0.18, mult=0.20} OR {adjusted based on grid results}
```

---

## 7. Interaction with Existing Overlays

### 7.1 Interaction with Emergency DD Cooldown (V2 Escalating)

The add-throttle and emergency DD cooldown operate at **different DD levels** and serve **different purposes**:

| Overlay | Activates at | Affects | Purpose |
|---------|-------------|---------|---------|
| **Add-throttle** | DD 8-18% | Add sizing | Prevent cascade buildup |
| **Emergency DD** | DD 28% | Full position | Force exit on extreme DD |
| **ED Cooldown (V2)** | After ED exit | All entries + adds | Prevent immediate re-entry |

**Ordering:** The add-throttle fires BEFORE the sizing computation. The ED cooldown fires at the top of `_check_entry()` and returns `None` (blocks everything). If the ED cooldown is active, the add-throttle is never reached. They do not conflict.

**Complementary effect:** The add-throttle reduces the probability of reaching emergency DD by limiting position buildup during the 8-28% DD range. This should reduce `share_emergency_dd` exits and `cascade_leq3` metrics.

### 7.2 Interaction with DD-Adaptive Sizing

When `enable_dd_adaptive = True`, the DD-adaptive feature reduces `base` (target exposure) starting at DD 16%. The add-throttle reduces `max_add_per_bar` starting at DD 8%.

**These compound:** At DD 18%, DD-adaptive has reduced `base` by ~17% (from the linear ramp), and the add-throttle has reduced `max_add_per_bar` to 20% of normal. The combined effect is a ~83% reduction in maximum add size.

**Is this too aggressive?** Possibly. For the initial implementation, test with `enable_dd_adaptive = False` (the current default) to isolate the add-throttle effect. If both are later enabled simultaneously, the `add_throttle_mult` may need to be raised to 0.30-0.40 to avoid over-constraining.

### 7.3 Interaction with `caution_mult`

In CAUTION regime, `base *= caution_mult` (0.50). This reduces the `gap` and therefore the add size. The add-throttle independently caps `max_add_per_bar`. Both can bind simultaneously.

**No special handling needed.** The `caution_mult` reduces the desired add size; the add-throttle caps the maximum. They are independent constraints and the most restrictive one wins via `min(sz, effective_max_add, gap)`.

---

## 8. Implementation Checklist

| # | Task | File | Notes |
|---|------|------|-------|
| 1 | Add 4 config fields (`enable_add_throttle`, `add_throttle_dd1/dd2/mult`) | Strategy config dataclass | Default: disabled |
| 2 | Implement `_throttled_max_add()` method | `strategy.py` | Pure function, easy to test |
| 3 | Wire into `_check_entry()` at the sizing clamp | `strategy.py` | Replace `c.max_add_per_bar` with `effective_max_add` |
| 4 | Add `throttle_activation_rate` tracking to bar loop | `strategy.py` | Counter incremented when throttle is active |
| 5 | Add `mean_buy_fills_per_episode` to churn metrics | `churn_metrics.py` | New column |
| 6 | Register params in config_audit allowlist | Config audit | Prevent unused-field false positives |
| 7 | Add unit test for `_throttled_max_add()` | `tests/` | Test boundary conditions at dd1, dd2, and interpolation |
| 8 | Add integration test: throttle active during 2022 bear | `tests/` | Verify activation rate > 0 |
| 9 | Implement grid runner for 8-cell robustness grid | Validation CLI or script | Wraps existing validation pipeline |
| 10 | Write grid results to `add_throttle_grid.csv` + report | Runner output | Per §6.6 |

**All implementation deferred to Step 3B.** This document is the design spec only.
