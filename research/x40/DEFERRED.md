# X40 Deferred Studies — A02 through A07

These studies are specified in the full x40 v3 spec but **deferred** from
initial implementation. Activate when the corresponding trigger condition is met.

Full spec: `resource/spec/X40_Baseline_Forge_Durability_Residual_Spec_v3.md`

---

## A02 — Alpha Half-Life and Horizon Compression

**Purpose**: Detect if the market is pricing the edge faster (crowding signal).

**Method**: Forward return curves at horizons h={1,2,4,8,16,32} bars from each
entry. Compare peak horizon and late-realization share across eras.

**Trigger**: Activate post-deployment, when real execution data exists to compare
against historical curves.

**Why deferred**: Academic at single-asset pre-deployment scale. Knowing "edge
is crowded faster" doesn't change decision when nothing is deployed.

---

## A03 — Capacity and Crowding Audit

**Purpose**: Estimate whether the signal is becoming harder to monetize.

**Method**: Execution-bar quote volume, participation proxy at notional ladder
(10K-5M), cost-stress sweep (35-100 bps RT), signal-conditioned implementation
shortfall.

**Trigger**: Activate when deploying at >$100K notional, or when adding a
second asset.

**Why deferred**: BTC/USDT D1 bar volume >> any notional below $5M.
Participation proxy will always return "fine" at current scale. A03 becomes
meaningful only at institutional scale or for less liquid instruments.

---

## A04 — Entry vs Exit Attribution

**Purpose**: Decide whether future research should focus on entry or exit.

**Method**: Counterfactual decomposition (fix entry/vary exit, and vice versa).
Entry-side residual feature scan. Exit-side path-quality analysis.

**Trigger**: Before opening next x39 residual sprint.

**Why deferred**: Partially answered by X21 (entry IC = -0.039, no predictive
power) and X12-X19 (exit series complete, static suppress only viable policy).

**Caveat**: unconditional entry-residual nulls do NOT fully rule out conditional
entry mechanisms inside an existing strategy context. The x39 vol compression
finding (PF1_E5_VC07) demonstrates exactly this: vol_ratio_5_20 has zero
residual-scan significance unconditionally but strong conditional value as an
entry gate. Re-run A04 if new conditional mechanism candidates emerge.

---

## A05 — Canary and Drift Detection

**Purpose**: Detect live/appended-data deterioration without silent self-retuning.

**Method**: Rolling expectancy over last 12 trades, rolling 6-month Sharpe,
hit-rate delta, MAE worsening, half-life compression.

**Trigger**: Activate AFTER deployment decision is made and live/shadow
execution begins. Run monthly for H4 baselines, quarterly for D1.

**Why deferred**: Cannot monitor what isn't running. Monitoring a backtest
is just re-running the backtest — not monitoring.

---

## A06 — Bounded Requalification

**Purpose**: Define response to detected decay (no silent self-retuning).

**Method**: Escalation ladder — no action → WATCH → profile switch →
offline requalification → league pivot.

**Trigger**: When A05 detects `TRIGGERED` state.

**Why deferred**: Requires A05 operational. No decay detection = no
requalification trigger.

---

## A07 — League Pivot Gate

**Purpose**: Decide whether to abandon current data league.

**Method**: If official baseline is DECAYING/BROKEN + crowding severe +
residual discovery repeatedly fails + richer-data league available →
recommend pivot.

**Trigger**: When both OH0 and PF0 show sustained decay, or when
richer data (order book, funding, on-chain) becomes available and
integrated.

**Why deferred**: PUBLIC_FLOW league not exhausted. PF0 is HOLD (not
DECAYING). No richer-data infrastructure exists yet.

---

## Activation checklist

| Study | Activate when | Depends on |
|-------|---------------|------------|
| A02 | Post-deployment, real execution data | A01 |
| A03 | Notional > $100K or multi-asset | A00 |
| A04 | Before next x39 sprint | A00, A01 |
| A05 | Deployment decision made | A01 |
| A06 | A05 TRIGGERED | A05 |
| A07 | Both baselines DECAYING + richer data available | A01, A03, A05 |
