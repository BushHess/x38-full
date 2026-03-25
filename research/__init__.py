"""Research module — frozen research artifacts, NOT for production use.

If you need monitoring functionality, import from `monitoring.regime_monitor` instead.
Research scripts import from each other for internal validation only.
"""

import os as _os
import sys as _sys
import warnings as _warnings

# Anti-import guard: warn when research code is imported from production context.
# Research scripts set _RESEARCH_CONTEXT=1 or run as __main__; production code does not.
_caller = _os.environ.get("_RESEARCH_CONTEXT", "")
_is_research = (
    _caller == "1"
    or "pytest" in _sys.modules
    or any(
        token in (_os.environ.get("PYTEST_CURRENT_TEST", "") + _os.environ.get("_", ""))
        for token in ("pytest", "research", "test_")
    )
)

if not _is_research:
    _warnings.warn(
        "Importing from 'research' package — this is research code. "
        "For production use, import from the appropriate production module instead "
        "(e.g., 'monitoring.regime_monitor').",
        UserWarning,
        stacklevel=2,
    )
