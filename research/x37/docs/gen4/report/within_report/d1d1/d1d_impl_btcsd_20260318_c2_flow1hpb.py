
CANDIDATE_ID = "btcsd_20260318_c2_flow1hpb"
DECISION_TF = "1h"


import math
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Sequence, Set

import numpy as np
import pandas as pd

_FEATURE_CACHE: Dict[Any, pd.DataFrame] = {}

def _ensure_frame(df: pd.DataFrame, interval_label: str) -> pd.DataFrame:
    out = df.copy()
    required = [
        "symbol", "interval", "open_time", "close_time", "open", "high", "low",
        "close", "volume", "quote_volume", "num_trades",
        "taker_buy_base_vol", "taker_buy_quote_vol",
    ]
    missing = [c for c in required if c not in out.columns]
    if missing:
        raise ValueError(f"Missing required columns for {interval_label}: {missing}")
    out = out[required]
    out = out.sort_values("open_time").reset_index(drop=True)
    numeric_cols = [
        "open_time", "close_time", "open", "high", "low", "close", "volume",
        "quote_volume", "num_trades", "taker_buy_base_vol", "taker_buy_quote_vol",
    ]
    for c in numeric_cols:
        out[c] = pd.to_numeric(out[c], errors="coerce")
    out["open_time"] = out["open_time"].astype("int64")
    out["close_time"] = out["close_time"].astype("int64")
    out["dt_open"] = pd.to_datetime(out["open_time"], unit="ms", utc=True)
    out["dt_close"] = pd.to_datetime(out["close_time"], unit="ms", utc=True)
    return out

def _interval_ms_from_label(label: str) -> int:
    mapping = {"15m": 15 * 60 * 1000, "1h": 60 * 60 * 1000, "4h": 4 * 60 * 60 * 1000, "1d": 24 * 60 * 60 * 1000}
    if label not in mapping:
        raise ValueError(f"Unsupported interval label: {label}")
    return mapping[label]

def _segment_ids(open_time: pd.Series, interval_ms: int) -> pd.Series:
    diff = open_time.diff()
    gap = diff.ne(interval_ms)
    if not gap.empty:
        gap.iloc[0] = True
    return gap.cumsum().astype("int64")

def _groupby_rolling(series: pd.Series, seg: pd.Series, window: int, how: str) -> pd.Series:
    g = series.groupby(seg)
    roll = getattr(g.rolling(window=window, min_periods=window), how)()
    return roll.reset_index(level=0, drop=True)

def _gap_rolling_mean(series: pd.Series, seg: pd.Series, window: int) -> pd.Series:
    return _groupby_rolling(series, seg, window, "mean")

def _gap_rolling_sum(series: pd.Series, seg: pd.Series, window: int) -> pd.Series:
    return _groupby_rolling(series, seg, window, "sum")

def _gap_rolling_min(series: pd.Series, seg: pd.Series, window: int) -> pd.Series:
    return _groupby_rolling(series, seg, window, "min")

def _gap_rolling_max(series: pd.Series, seg: pd.Series, window: int) -> pd.Series:
    return _groupby_rolling(series, seg, window, "max")

def _gap_shift(series: pd.Series, seg: pd.Series, periods: int) -> pd.Series:
    return series.groupby(seg).shift(periods)

def _gap_return(close: pd.Series, seg: pd.Series, periods: int) -> pd.Series:
    prev = _gap_shift(close, seg, periods)
    return close / prev - 1.0

def _gap_rangepos(high: pd.Series, low: pd.Series, close: pd.Series, seg: pd.Series, window: int) -> pd.Series:
    lo = _gap_rolling_min(low, seg, window)
    hi = _gap_rolling_max(high, seg, window)
    width = hi - lo
    out = (close - lo) / width
    out = out.where(width > 0)
    return out

def _last_pct_rank_inclusive(x: np.ndarray) -> float:
    if x.size == 0 or np.isnan(x[-1]):
        return np.nan
    valid = x[~np.isnan(x)]
    if valid.size == 0:
        return np.nan
    last = x[-1]
    return float(np.mean(valid <= last))

def _gap_pct_rank_inclusive(series: pd.Series, seg: pd.Series, window: int) -> pd.Series:
    pieces = []
    for _, s in series.groupby(seg):
        rolled = s.rolling(window=window, min_periods=window).apply(_last_pct_rank_inclusive, raw=True)
        pieces.append(rolled)
    if not pieces:
        return pd.Series(index=series.index, dtype=float)
    out = pd.concat(pieces).sort_index()
    return out.reindex(series.index)

def _merge_asof_features(fast: pd.DataFrame, slow: pd.DataFrame, cols: Sequence[str]) -> pd.DataFrame:
    right = slow[["close_time", *cols]].sort_values("close_time").copy()
    left = fast[["close_time"]].sort_values("close_time").copy()
    merged = pd.merge_asof(left, right, on="close_time", direction="backward")
    merged.index = fast.sort_values("close_time").index
    merged = merged.reindex(fast.index)
    return merged[cols]

def _parse_utc_boundary(value: Optional[Any], is_end: bool = False) -> Optional[pd.Timestamp]:
    if value is None:
        return None
    ts = pd.Timestamp(value)
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    else:
        ts = ts.tz_convert("UTC")
    if isinstance(value, str) and len(value.strip()) <= 10:
        if is_end:
            ts = ts + pd.Timedelta(days=1) - pd.Timedelta(milliseconds=1)
    return ts

def _ms(ts: Optional[pd.Timestamp]) -> Optional[int]:
    if ts is None:
        return None
    return int(ts.value // 1_000_000)

def _to_iso(ts: Optional[pd.Timestamp]) -> Optional[str]:
    if ts is None or pd.isna(ts):
        return None
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    else:
        ts = ts.tz_convert("UTC")
    return ts.isoformat()

def _normalize_config(config: Dict[str, Any]) -> Dict[str, Any]:
    out = {}
    for k, v in config.items():
        if pd.isna(v):
            continue
        try:
            out[k] = float(v)
        except Exception:
            out[k] = v
    return out

def _config_id(config: Dict[str, Any]) -> Optional[str]:
    cid = config.get("config_id")
    return None if cid is None or (isinstance(cid, float) and math.isnan(cid)) else str(cid)

def _data_signature(data_by_timeframe: Dict[str, pd.DataFrame], keys: Sequence[str], extra: Any = None):
    sig = [extra]
    for key in keys:
        df = data_by_timeframe[key]
        sig.append((key, len(df), int(df["open_time"].iloc[0]), int(df["open_time"].iloc[-1])))
    return tuple(sig)

def _prepare_initial_state(initial_state: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not initial_state:
        return {
            "position": 0,
            "position_fraction": 0.0,
            "entry_time_utc": None,
            "entry_price": None,
        }
    position_state = str(initial_state.get("position_state", "flat")).lower()
    position_fraction = float(initial_state.get("position_fraction", 0.0) or 0.0)
    position = 1 if position_state == "long" and position_fraction > 0 else 0
    entry_time = initial_state.get("entry_time_utc")
    entry_price = initial_state.get("entry_price")
    return {
        "position": position,
        "position_fraction": 1.0 if position else 0.0,
        "entry_time_utc": entry_time,
        "entry_price": float(entry_price) if entry_price is not None else None,
    }

def _finalize_daily_returns(interval_df: pd.DataFrame) -> pd.DataFrame:
    if interval_df.empty:
        return pd.DataFrame(columns=["date_utc", "gross_return", "net_return"])
    day = interval_df["exec_time"].dt.floor("D")
    grouped = interval_df.groupby(day)
    gross = grouped["gross_return"].apply(lambda x: float(np.prod(1.0 + x.to_numpy()) - 1.0))
    net = grouped["net_return"].apply(lambda x: float(np.prod(1.0 + x.to_numpy()) - 1.0))
    out = pd.DataFrame({"date_utc": gross.index, "gross_return": gross.values, "net_return": net.values})
    return out.reset_index(drop=True)

def _build_trade_log(events: Sequence[Dict[str, Any]], candidate_id: str, config_id: Optional[str]) -> pd.DataFrame:
    if not events:
        return pd.DataFrame(columns=[
            "candidate_id", "config_id", "trade_id", "entry_time_utc", "entry_price",
            "exit_time_utc", "exit_price", "gross_return", "net_return", "bars_held",
            "duration_seconds",
        ])
    rows = []
    open_trade = None
    trade_id = 0
    for ev in events:
        side = ev["side"]
        if side == "entry":
            trade_id += 1
            open_trade = {
                "trade_id": trade_id,
                "entry_time_utc": ev["time"],
                "entry_price": ev["price"],
                "entry_cost": ev["cost"],
                "entry_bar_ix": ev["bar_ix"],
            }
        elif side == "exit" and open_trade is not None:
            gross_ret = ev["price"] / open_trade["entry_price"] - 1.0
            total_cost = open_trade["entry_cost"] + ev["cost"]
            net_ret = gross_ret - total_cost
            duration_seconds = (ev["time"] - open_trade["entry_time_utc"]).total_seconds()
            rows.append({
                "candidate_id": candidate_id,
                "config_id": config_id,
                "trade_id": open_trade["trade_id"],
                "entry_time_utc": _to_iso(open_trade["entry_time_utc"]),
                "entry_price": float(open_trade["entry_price"]),
                "exit_time_utc": _to_iso(ev["time"]),
                "exit_price": float(ev["price"]),
                "gross_return": float(gross_ret),
                "net_return": float(net_ret),
                "bars_held": int(ev["bar_ix"] - open_trade["entry_bar_ix"]),
                "duration_seconds": float(duration_seconds),
            })
            open_trade = None
    if open_trade is not None:
        rows.append({
            "candidate_id": candidate_id,
            "config_id": config_id,
            "trade_id": open_trade["trade_id"],
            "entry_time_utc": _to_iso(open_trade["entry_time_utc"]),
            "entry_price": float(open_trade["entry_price"]),
            "exit_time_utc": None,
            "exit_price": None,
            "gross_return": None,
            "net_return": None,
            "bars_held": None,
            "duration_seconds": None,
        })
    return pd.DataFrame(rows)

def _simulate_from_decision_frame(
    decision_df: pd.DataFrame,
    config: Dict[str, Any],
    cost_rt_bps: float,
    candidate_id: str,
    decision_timeframe: str,
    disabled_layers: Optional[Set[str]] = None,
    start_utc: Optional[Any] = None,
    end_utc: Optional[Any] = None,
    initial_state: Optional[Dict[str, Any]] = None,
):
    disabled_layers = set(disabled_layers or [])
    config = _normalize_config(dict(config))
    config_id = _config_id(config)

    start_ts = _parse_utc_boundary(start_utc, is_end=False)
    end_ts = _parse_utc_boundary(end_utc, is_end=True)
    start_ms = _ms(start_ts)
    end_ms = _ms(end_ts)

    state = _prepare_initial_state(initial_state)
    current_pos = int(state["position"])
    current_entry_time = pd.Timestamp(state["entry_time_utc"]) if state["entry_time_utc"] is not None else None
    if current_entry_time is not None:
        if current_entry_time.tzinfo is None:
            current_entry_time = current_entry_time.tz_localize("UTC")
        else:
            current_entry_time = current_entry_time.tz_convert("UTC")
    current_entry_price = state["entry_price"]

    interval_df = decision_df.copy()
    interval_df = interval_df.iloc[:-1].copy()
    interval_df["exec_time"] = interval_df["next_open_dt"]
    interval_df["exec_open"] = interval_df["next_open"]
    interval_df["next_exec_open"] = interval_df["next_next_open"]
    interval_df["interval_return"] = interval_df["next_exec_open"] / interval_df["exec_open"] - 1.0
    interval_df = interval_df.loc[interval_df["next_exec_open"].notna()].reset_index(drop=True)

    side_cost = float(cost_rt_bps) / 20000.0
    last_signal_time = None
    events = []
    interval_rows = []

    for i, row in interval_df.iterrows():
        exec_ms = int(row["next_open_time"])
        if end_ms is not None and exec_ms > end_ms:
            break

        last_signal_time = row["dt_close"]

        tradable_now = start_ms is None or exec_ms >= start_ms
        entry_flag = bool(row["entry_cond"])
        hold_flag = bool(row["hold_cond"])

        next_pos = current_pos
        trade_delta = 0

        if tradable_now:
            if current_pos == 0:
                if entry_flag:
                    next_pos = 1
                    trade_delta = 1
                    current_entry_time = row["exec_time"]
                    current_entry_price = float(row["exec_open"])
                    events.append({
                        "side": "entry",
                        "time": row["exec_time"],
                        "price": float(row["exec_open"]),
                        "cost": side_cost,
                        "bar_ix": i,
                    })
            else:
                if not hold_flag:
                    next_pos = 0
                    trade_delta = -1
                    events.append({
                        "side": "exit",
                        "time": row["exec_time"],
                        "price": float(row["exec_open"]),
                        "cost": side_cost,
                        "bar_ix": i,
                    })
                    current_entry_time = None
                    current_entry_price = None
        else:
            next_pos = current_pos

        gross_return = float(next_pos * row["interval_return"])
        net_return = gross_return - abs(trade_delta) * side_cost

        interval_rows.append({
            "exec_time": row["exec_time"],
            "gross_return": gross_return,
            "net_return": net_return,
            "position": next_pos,
            "entry_flag": entry_flag,
            "hold_flag": hold_flag,
            "trade_delta": trade_delta,
        })

        current_pos = next_pos

    interval_res = pd.DataFrame(interval_rows)
    if start_ts is not None and not interval_res.empty:
        interval_res = interval_res.loc[interval_res["exec_time"] >= start_ts].reset_index(drop=True)
    if end_ts is not None and not interval_res.empty:
        interval_res = interval_res.loc[interval_res["exec_time"] <= end_ts].reset_index(drop=True)

    daily_returns = _finalize_daily_returns(interval_res)

    trade_log = _build_trade_log(events, candidate_id=candidate_id, config_id=config_id)
    if start_ts is not None and not trade_log.empty:
        trade_log = trade_log.loc[
            trade_log["entry_time_utc"].isna() | (pd.to_datetime(trade_log["entry_time_utc"], utc=True) >= start_ts)
        ].reset_index(drop=True)
    if end_ts is not None and not trade_log.empty:
        keep = pd.to_datetime(trade_log["entry_time_utc"], utc=True) <= end_ts
        trade_log = trade_log.loc[keep.fillna(True)].reset_index(drop=True)

    terminal_state = {
        "position_state": "long" if current_pos == 1 else "flat",
        "position_fraction": 1.0 if current_pos == 1 else 0.0,
        "entry_time_utc": _to_iso(current_entry_time),
        "entry_price": None if current_entry_price is None else float(current_entry_price),
        "trail_state": {},
        "custom_state": {
            "candidate_id": candidate_id,
            "decision_timeframe": decision_timeframe,
            "config_id": config_id,
            "disabled_layers": sorted(list(disabled_layers)),
        },
        "last_signal_time_utc": _to_iso(last_signal_time),
        "reconstructable_from_warmup_only": True,
    }

    return {
        "daily_returns": daily_returns[["date_utc", "net_return"]].copy(),
        "daily_returns_gross": daily_returns[["date_utc", "gross_return"]].copy(),
        "trade_log": trade_log,
        "terminal_state": terminal_state,
        "interval_returns": interval_res,
    }


def _build_feature_frame(data_by_timeframe: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    sig = _data_signature(data_by_timeframe, keys=["1d", "4h", "1h"], extra="c2")
    if sig in _FEATURE_CACHE:
        return _FEATURE_CACHE[sig].copy()

    d1 = _ensure_frame(data_by_timeframe["1d"], "1d")
    h4 = _ensure_frame(data_by_timeframe["4h"], "4h")
    h1 = _ensure_frame(data_by_timeframe["1h"], "1h")

    d1_seg = _segment_ids(d1["open_time"], _interval_ms_from_label("1d"))
    h4_seg = _segment_ids(h4["open_time"], _interval_ms_from_label("4h"))
    h1_seg = _segment_ids(h1["open_time"], _interval_ms_from_label("1h"))

    flow_num = _gap_rolling_sum(d1["taker_buy_base_vol"], d1_seg, 12)
    flow_den = _gap_rolling_sum(d1["volume"], d1_seg, 12)
    d1["d1_flow12"] = 2.0 * (flow_num / flow_den) - 1.0
    d1["d1_flow12"] = d1["d1_flow12"].where(flow_den > 0)

    h4["h4_rangepos168"] = _gap_rangepos(h4["high"], h4["low"], h4["close"], h4_seg, 168)
    h1["h1_ret168"] = _gap_return(h1["close"], h1_seg, 168)

    merged = h1.copy()
    d1_feats = _merge_asof_features(merged, d1, ["d1_flow12"])
    h4_feats = _merge_asof_features(merged, h4, ["h4_rangepos168"])
    merged = pd.concat([merged, d1_feats, h4_feats], axis=1)

    merged["next_open_time"] = merged["open_time"].shift(-1)
    merged["next_open_dt"] = merged["dt_open"].shift(-1)
    merged["next_open"] = merged["open"].shift(-1)
    merged["next_next_open"] = merged["open"].shift(-2)

    _FEATURE_CACHE[sig] = merged.copy()
    return merged

def _run_candidate_internal(
    data_by_timeframe: Dict[str, pd.DataFrame],
    config: Dict[str, Any],
    cost_rt_bps: float,
    start_utc: Optional[Any] = None,
    end_utc: Optional[Any] = None,
    initial_state: Optional[Dict[str, Any]] = None,
    disabled_layers: Optional[Set[str]] = None,
):
    disabled_layers = set(disabled_layers or [])
    config = _normalize_config(dict(config))
    df = _build_feature_frame(data_by_timeframe)

    d1_entry = pd.Series(True, index=df.index)
    d1_hold = pd.Series(True, index=df.index)
    if "d1_flow_permission" not in disabled_layers:
        d1_entry = df["d1_flow12"] <= 0.0
        d1_hold = d1_entry.copy()

    h4_entry = pd.Series(True, index=df.index)
    h4_hold = pd.Series(True, index=df.index)
    if "h4_context" not in disabled_layers:
        h4_entry = df["h4_rangepos168"] >= config["q_h4_rangepos_min"]
        h4_hold = h4_entry.copy()

    h1_entry = pd.Series(True, index=df.index)
    h1_hold = pd.Series(True, index=df.index)
    if "h1_execution" not in disabled_layers:
        h1_entry = df["h1_ret168"] <= config["theta_h1_ret168_entry"]
        h1_hold = df["h1_ret168"] <= config["theta_h1_ret168_hold"]

    df = df.copy()
    df["entry_cond"] = d1_entry & h4_entry & h1_entry
    df["hold_cond"] = d1_hold & h4_hold & h1_hold
    return _simulate_from_decision_frame(
        decision_df=df,
        config=config,
        cost_rt_bps=cost_rt_bps,
        candidate_id=CANDIDATE_ID,
        decision_timeframe=DECISION_TF,
        disabled_layers=disabled_layers,
        start_utc=start_utc,
        end_utc=end_utc,
        initial_state=initial_state,
    )

def run_candidate(
    data_by_timeframe: Dict[str, pd.DataFrame],
    config: Dict[str, Any],
    cost_rt_bps: float,
    start_utc: Optional[Any] = None,
    end_utc: Optional[Any] = None,
    initial_state: Optional[Dict[str, Any]] = None,
):
    return _run_candidate_internal(
        data_by_timeframe=data_by_timeframe,
        config=config,
        cost_rt_bps=cost_rt_bps,
        start_utc=start_utc,
        end_utc=end_utc,
        initial_state=initial_state,
        disabled_layers=None,
    )
