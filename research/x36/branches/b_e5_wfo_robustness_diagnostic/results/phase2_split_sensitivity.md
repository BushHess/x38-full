# Phase 2 — Frozen Split Sensitivity

| Spec | Valid/Total | Power | Low-trade | Positive | Win rate | Mean delta | Median delta | Worst delta | Wilcoxon p | Bootstrap lo | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| canonical_24_6_last8 | 8/8 | 8 | 0 | 5 | 0.6250 | 12.4563 | 12.9825 | -20.7880 | 0.125000 | -3.4378 | FAIL |
| short_horizon_24_3_last12 | 12/12 | 10 | 2 | 6 | 0.5000 | 12.0575 | 2.3956 | -78.1378 | 0.577148 | -31.8353 | FAIL |
| long_horizon_24_9_last6 | 6/6 | 6 | 0 | 4 | 0.6667 | 32.9595 | 38.3156 | -31.4770 | 0.078125 | -3.6701 | PASS |
| canonical_24_6_all | 10/10 | 10 | 0 | 7 | 0.7000 | 28.0868 | 21.1455 | -20.7880 | 0.032227 | 4.0386 | PASS |
