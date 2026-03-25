#!/usr/bin/env python3
"""Unified validation CLI entrypoint.

Example (E5_ema21D1 vs E0 baseline):
    python validate_strategy.py \
      --strategy vtrend_e5_ema21_d1 --baseline vtrend \
      --config configs/vtrend_e5_ema21_d1/vtrend_e5_ema21_d1_default.yaml \
      --baseline-config configs/vtrend/vtrend_default.yaml \
      --out out_validation --suite all
"""

from __future__ import annotations

import sys

from validation.cli import main


if __name__ == "__main__":
    sys.exit(main())
