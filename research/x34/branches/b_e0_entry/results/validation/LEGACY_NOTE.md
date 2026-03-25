# Legacy Validation Artifact

This directory is kept as historical evidence from the pre-rule X34 workflow.

Status:
- Produced on 2026-03-13 via the old `validate_strategy.py` pipeline.
- Preserved because it contains the original `b_e0_entry` REJECT evidence.
- Not the active X34 execution pattern anymore.

Current X34 rule:
- Active research execution for X34 uses branch-local standalone runners under
  `research/x34/branches/*/code/`.
- New work must not wire research strategies into `validation/`, `v10/`, or
  top-level `tests/`.

Interpretation:
- Treat files here as frozen legacy artifacts.
- Do not extend or refresh this folder for new X34 branches.
