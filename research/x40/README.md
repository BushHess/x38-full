# X40 — Baseline Forge (slim)

**Status**: Implementation phase
**Purpose**: Baseline qualification, source parity verification, temporal decay audit.

## What x40 does

x40 answers two questions:

1. **Are our baselines faithful?** (A00 — source parity replay)
2. **Are our baselines decaying?** (A01 — temporal decay audit)

It does NOT do discovery (x37), feature invention (x39), or governance (x38).

## League model

| League | Baseline ID | Strategy | Data surface |
|--------|-------------|----------|-------------|
| `OHLCV_ONLY` | `OH0_D1_TREND40` | D1 momentum(40) > 0 → long | `close` only |
| `PUBLIC_FLOW` | `PF0_E5_EMA21D1` | EMA crossover + VDO + D1 EMA(21) regime | OHLCV + `taker_buy_base_vol` |

Cross-league comparison is diagnostic only, never authoritative.

## Challenger tracking

| ID | Source | Verdict | Note |
|----|--------|---------|------|
| `PF1_E5_VC07` | x39 exp42 formal validation | HOLD (WFO p=0.191) | See `challengers/PF1_E5_VC07_status.md` |

## Phase plan

| Phase | Scope | Status |
|-------|-------|--------|
| **Phase 1** | Scaffold + frozen specs + source references | Done |
| **Phase 2** | A00 source parity replay (both baselines) | Done |
| **Phase 3** | A01 temporal decay (era splits + rolling Sharpe) | Done (both WATCH) |
| **Phase 4** | A04 entry vs exit attribution (PF0) | Done |
| **Deferred** | A02, A03, A05-A07 (activate post-deployment or at scale) | Preserved in `DEFERRED.md` |

## Usage

```bash
cd /var/www/trading-bots/btc-spot-dev
source /var/www/trading-bots/.venv/bin/activate

# A00: Source parity replay
python research/x40/replay.py

# A01: Temporal decay
python research/x40/studies/a01_temporal_decay.py

# A04: Entry vs exit attribution
python research/x40/studies/a04_entry_exit_attribution.py
```

## Directory layout

```
research/x40/
├── README.md                              # This file
├── x40_RULES.md                           # Operational rules
├── DEFERRED.md                            # A02-A07 specs for future
├── replay.py                              # A00 source parity runner
├── oh0_strategy.py                        # OH0 D1_TREND40 sim (Pattern B)
├── pf0_strategy.py                        # PF0 E5_EMA21D1 sim (Pattern B)
├── baselines/
│   ├── OH0_D1_TREND40/
│   │   ├── source_reference.md            # Authoritative source artifacts
│   │   └── frozen_spec.md                 # Exact algorithm spec
│   └── PF0_E5_EMA21D1/
│       ├── source_reference.md
│       └── frozen_spec.md
├── studies/
│   ├── a01_temporal_decay.py              # Era split + rolling Sharpe
│   └── a04_entry_exit_attribution.py      # Entry vs exit attribution
├── challengers/
│   └── PF1_E5_VC07_status.md              # Vol compression gate status
├── results/                               # Machine-generated outputs
│   ├── OH0_D1_TREND40/
│   └── PF0_E5_EMA21D1/
├── output/                                # Plots, CSVs
└── resource/                              # Original v3 spec docs (reference)
```

## Key design decisions

1. **Slim over full**: Only A00 + A01 implemented. A02-A07 deferred until deployment or multi-asset scale.
2. **Self-contained**: Both baselines use Pattern B (vectorized sim) within x40. No import from `strategies/` or `v10/core/engine.py`. DataFeed used only for CSV loading.
3. **Synchronized cost**: Both baselines use simple per-side cost model, default 20 bps RT. Cost sweep [10-100] for sensitivity.
4. **League separation conceptual, not infra**: Two baselines, two leagues. No namespace machinery.
5. **Lineage guard**: PF0's `pf0_strategy.py` is verified against original `strategies/vtrend_e5_ema21_d1/strategy.py` (SHA256 lineage pin, trade count 188 exact).
