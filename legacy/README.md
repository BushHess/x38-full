# Legacy Files

Orphaned files moved from repo root during cleanup (2026-03-14).
These are NOT used by the current E5_ema21D1 pipeline.

## candidates/ (25 YAML files)

V10/V11/V12 research candidate configs. Superseded by current strategy framework.
Only reference: `v10/cli/research.py` (legacy CLI, not used in current pipeline).

## analysis_scripts/ (6 Python files)

V11-era analysis scripts (double compression, trail tighten, proposal B).
Self-contained, zero imports from current codebase. All have been superseded
by X-series research (X0-X33).

## artifacts/ (5 files)

- `btc-pa4v6.service` — systemd unit for separate V6 bot repo (`/var/www/bitcoin/`)
- `audit.html`, `rebuild_catalog.html`, `.bak` — generated HTML reports
- `requirements.txt` — superseded by monorepo `uv.lock` + `pyproject.toml`

---

**Safe to delete** after review. None of these files are referenced by active code.
