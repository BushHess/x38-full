# Exit Delay Sensitivity: Sharpe Degradation

**File**: `exit_delay_delta_sharpe.png`

Shows delta Sharpe (vs baseline) as a function of exit delay (1-4 H4 bars) for all 5 candidates.

Key observations:
- SM is nearly flat (max -0.074 at D4), confirming exit delay robustness
- Binary candidates show monotonic degradation with exit delay (D4: -0.24 to -0.25)
- E5 and E5_plus are slightly less exit-delay-fragile than E0/E0_plus at D1-D3 but converge at D4
- Non-monotonic behavior: E0 shows D2 less bad than D1, D3 worse again. This is due to delay-dependent trade alignment effects
- Exit delay sensitivity (~0.25 max) is ~60% of entry delay sensitivity (~0.37-0.52 from Step 3)
