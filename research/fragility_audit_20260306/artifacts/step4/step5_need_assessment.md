# Step 5 Necessity Assessment

## Verdict: NOT NEEDED for research conclusion. RECOMMENDED for live sign-off.

## Why Step 5 is not needed for the research conclusion

1. **Candidate ranking is stable.** The relative ordering of candidates across all 4 evidence layers (portfolio, trade structure, behavioral fragility, replay fragility) is consistent and convergent. No single candidate occupies a borderline position where additional evidence could flip its disposition.

2. **The key fragility axis (entry delay) is fully characterized.** Step 3 tested delays of 1-4 H4 bars across all 6 candidates with 24 replay runs. The convex degradation pattern is clear. Further delay testing (e.g., stochastic delay) would refine the curve shape but cannot change the fundamental finding: binary strategies are delay-fragile, vol-target strategies are not.

3. **Redundancy decisions are definitive.** SM vs LATCH: identical on every metric tested (Steps 2 and 3). No amount of additional testing will differentiate them. EMA overlay value: characterized at 4 delay levels with clear crossover behavior. No ambiguity remains.

4. **The "no universal winner" conclusion is overdetermined.** Three independent evidence layers confirm the mandate x latency structure: (a) portfolio metrics show SM/LATCH dominate on risk, binary dominates on CAGR; (b) trade structure shows SM/LATCH have smooth native dependence while binary strategies have cliff-like; (c) replay fragility shows SM/LATCH are delay-robust while binary strategies are delay-fragile. These are structural properties, not sampling artifacts.

## What Step 5 could still contribute

1. **Live engine validation**: Confirm that the standalone replay harness (REPLAY_REGRESS PASS) matches the BacktestEngine under disruption scenarios (not just baseline). This is a fidelity check, not a new finding.

2. **Combined disruption testing**: Simultaneous random miss + delayed entry. This could reveal interaction effects, but given that random miss has CV < 1.5% and delay is the dominant axis, interactions are likely small.

3. **Exit delay testing**: Step 3 only tested entry delays. Exit delays (late stop-loss execution) could be more damaging and might differentially affect candidates. This is the most decision-relevant gap.

4. **Stochastic delay model**: Variable delay drawn from empirical distribution (e.g., 1 bar 90% of the time, 4 bars 10%). More realistic than fixed delay but unlikely to change rankings.

## Which recommendations could Step 5 destabilize?

- **E0 vs E0_plus under LT2**: If exit delay testing shows E0_plus is MORE robust to exit delay than E0 (despite being more fragile to entry delay), this could flip the LT2 recommendation. Probability: LOW but non-zero.
- **E5_plus LT1 primacy**: If combined disruption testing shows E5_plus collapses disproportionately under compound stress (miss + delay simultaneously), its M1/LT1 recommendation could weaken. Probability: LOW.
- **SM vs LATCH**: CANNOT be destabilized. They are structurally identical.
- **Binary vs vol-target class boundary**: CANNOT be destabilized. The 7x delay sensitivity gap is too large.

## Recommendation

Proceed to deployment planning using Step 4 conclusions. Execute Step 5 as a parallel hardening workstream if live capital deployment is imminent. Do not gate the research conclusion on Step 5.
