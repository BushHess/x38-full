# How to Add a New Strategy Version Cleanly

> **LEGACY (2026-03-14):** This document predates the current E5_ema21D1 framework.
> The `candidates.yaml` system has been superseded — files moved to `legacy/candidates/`.
> Current strategy registration: `validation/strategy_factory.py` (STRATEGY_REGISTRY).
> Current research patterns: `docs/research/RESEARCH_RULES.md`.

This document defines the folder contract to avoid version sprawl.

## Folder Contract

- `strategies/`: production-candidate strategy code only.
- `configs/v*/`: versioned production configs only.
- `experiments/`: research scripts, conditional analysis, leave-one-out, notebooks.
- `candidates.yaml`: production registry; must not reference `experiments/`.
- `candidates_v*.yaml`: legacy/research candidate matrices (non-production registry).

## Canonical Layout

```text
btc-spot/
├── strategies/
│   └── v12_emdd_ref_fix/
├── configs/
│   └── v12/
├── experiments/
│   ├── overlayA/
│   ├── conditional_analysis/
│   ├── leave_one_out/
│   └── notebooks/
├── candidates.yaml
└── docs/
    └── strategy_versioning.md
```

## Workflow

1. Create strategy package in `strategies/<version_name>/`.
2. Add version configs in `configs/v<NN>/`.
3. Register production-ready entries in `candidates.yaml` using only:
   - `strategy_dir: strategies/...`
   - `config_path: configs/v...`
4. Keep all exploratory code in `experiments/`:
   - overlay and robustness scripts
   - conditional/decomposition scripts
   - leave-one-out scripts
   - notebooks
5. Add/extend tests under `tests/` for the new strategy version.

## Guardrails

- Do not place analysis scripts in `strategies/`.
- Do not point `candidates.yaml` to `experiments/`.
- Promote to `strategies/` only after validation gates pass.
