# Richer-Data League Bootstrap

## 1. Purpose

This document defines how x40 pivots beyond current public-data leagues.

The goal is not to chase novelty.  
The goal is to move only when current leagues show enough decay/crowding/exhaustion that richer information is justified.

---

## 2. Trigger conditions

A richer-data pivot should be opened only when one of these high-level conditions is true:

### Trigger A
Both `OHLCV_ONLY` and `PUBLIC_FLOW` baselines are `DECAYING` or `BROKEN`.

### Trigger B
`A04` shows severe crowding / implementation fragility in public-data leagues.

### Trigger C
Two residual cycles fail to produce any tracked challenger with incremental value.

### Trigger D
Human review concludes that the current information surface has hit a practical ceiling.

---

## 3. Priority order for richer-data leagues

Initial recommended order:

1. `DERIVATIVES_FLOW`
2. `ORDERBOOK`
3. `ONCHAIN`
4. `TEXT_EVENT`

### Why this order?
Because the first three are closer to market mechanics and execution reality.  
Generic text/sentiment is more commoditized and should not be the first pivot by default.

---

## 4. League bootstrap contract

Every new richer-data league must define:

- `league_id`
- admitted raw fields
- physical file schema
- logic-usable fields
- latency assumptions
- update frequency
- missingness policy
- timezone policy
- benchmark/control baseline
- minimal objective floors
- primary comparison profile used for x40 control views

No richer-data league may begin with "we'll figure out the schema later."

---

## 5. Bootstrap steps

### Step 1 — choose league
Example:
- `DERIVATIVES_FLOW`

### Step 2 — write league constitution addendum
Declare the precise admitted data surface.

### Step 3 — choose a control baseline
Control should remain one of:
- `OH0_D1_TREND40`
- `PF0_E5_EMA21D1`

depending on comparability.

### Step 4 — define the first richer-data baseline challenge
Usually through x37 blank-slate discovery.

### Step 5 — return first champion to x40
The champion returns as tracked challenger or baseline candidate.

### Step 6 — update central registries
Update:
- `registry/leagues.yaml`
- `registry/baselines.yaml`
- `registry/challengers.yaml`
- `registry/comparison_profiles.yaml` if a new profile is needed

Optional league-specific addenda may live under:
- `registry/league_addenda/<league>.yaml`

### Step 7 — build standardized control view
Restate the new league champion and chosen control baseline on the same explicit comparison profile before making a superiority claim.

Default headline profile for the initial control view:
- `CP_PRIMARY_50_DAILYUTC`

---

## 6. Default richer-data league definitions

### 6.1 `DERIVATIVES_FLOW`
Candidate raw fields may include:
- open interest,
- funding rate,
- liquidations,
- perp/spot basis,
- futures premium.

### 6.2 `ORDERBOOK`
Candidate raw fields may include:
- best bid/ask,
- top-N depth,
- order-book imbalance,
- sweep intensity,
- quote refill rate.

### 6.3 `ONCHAIN`
Candidate raw fields may include:
- exchange inflow/outflow,
- active addresses,
- stablecoin issuance or transfer proxies,
- miner/supply movement proxies.

### 6.4 `TEXT_EVENT`
Candidate raw fields may include:
- structured event calendars,
- exchange incident feeds,
- curated domain-specific text streams.

Generic "internet sentiment" should not be the first text-based lane.

---

## 7. Minimal viability rule for a richer-data league

A richer-data league is not considered active until it has:

1. a written league constitution,
2. at least one admitted raw data bundle,
3. one control baseline reference,
4. one x37 discovery charter,
5. one first-cycle x40 plan,
6. one explicit comparison profile for control views.

---

## 8. How x40 treats richer-data champions

A richer-data champion does **not** automatically invalidate OHLCV/public-flow work.

Instead:
- it becomes a challenger within the new league,
- then a candidate baseline within that league,
- while old leagues remain as controls.

This preserves comparability across information surfaces.

---

## 9. Anti-patterns

Invalid richer-data pivots include:

1. pivoting because richer data feels more sophisticated,
2. mixing league admission rules ad hoc,
3. skipping control baselines,
4. claiming richer-data superiority before baseline qualification,
5. starting with high-noise generic sentiment instead of more mechanistic data,
6. comparing the new league champion and its control baseline under different comparison profiles.
