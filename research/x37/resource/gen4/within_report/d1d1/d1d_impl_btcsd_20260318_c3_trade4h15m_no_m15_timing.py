
from pathlib import Path
import importlib.util
from typing import Any, Dict, Optional

_BASE_PATH = Path(__file__).with_name("d1d_impl_btcsd_20260318_c3_trade4h15m.py")
_SPEC = importlib.util.spec_from_file_location("base_module_btcsd_20260318_c3_trade4h15m_m15_timing", _BASE_PATH)
_MOD = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(_MOD)

ABLATION_CONFIG = {'config_id': 'cfg_019', 'q_h4_rangepos_entry': 0.55, 'q_h4_rangepos_hold': 0.35, 'rho_m15_relvol_min': 1.1}

def run_candidate(
    data_by_timeframe: Dict[str, Any],
    config: Dict[str, Any],
    cost_rt_bps: float,
    start_utc: Optional[Any] = None,
    end_utc: Optional[Any] = None,
    initial_state: Optional[Dict[str, Any]] = None,
):
    _ = config  # ablation variants are pinned to the candidate's first config by design
    return _MOD._run_candidate_internal(
        data_by_timeframe=data_by_timeframe,
        config=dict(ABLATION_CONFIG),
        cost_rt_bps=cost_rt_bps,
        start_utc=start_utc,
        end_utc=end_utc,
        initial_state=initial_state,
        disabled_layers={"m15_timing"},
    )
