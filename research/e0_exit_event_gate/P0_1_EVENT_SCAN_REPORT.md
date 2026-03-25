# P0.1 Exit-Event Scan Report

## Scope

- Reference: `X0_E5EXIT`
- Candidate event source: `X0E5_FLOOR_LATCH`
- Scenario: `harsh`
- Period: `2019-01-01` to `2026-02-20`

## Event Summary

- total floor events: `56`
- actionable floor events: `23`
- actionable matched events: `22`
- good / bad / neutral actionable matched events: `14` / `8` / `0`
- actionable matched net delta: `-91444.81 USD`

## Top Rules

- `er20`: accepted=6, good=5, bad=1, net=+13808.70 USD, precision=83.33%, good_capture=35.71%, bad_capture=12.50%
- `peak_age_ge_3`: accepted=13, good=10, bad=3, net=+12418.05 USD, precision=76.92%, good_capture=71.43%, bad_capture=37.50%
- `combo_weak3`: accepted=4, good=3, bad=1, net=+9217.40 USD, precision=75.00%, good_capture=21.43%, bad_capture=12.50%
- `combo_weak1`: accepted=5, good=4, bad=1, net=+5133.38 USD, precision=80.00%, good_capture=28.57%, bad_capture=12.50%
- `peak_age_ge_6`: accepted=7, good=5, bad=2, net=+1273.15 USD, precision=71.43%, good_capture=35.71%, bad_capture=25.00%

## Interpretation

- There is at least one simple event rule worth benchmarking.
- Recommended first benchmark candidate: `er20`
