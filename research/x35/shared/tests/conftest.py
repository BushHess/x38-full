"""Local pytest path setup for x35 tests only.

This avoids requiring external PYTHONPATH manipulation and does not affect
other studies or framework-level test behavior.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
