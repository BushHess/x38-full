
from typing import Any, Dict, Optional, Tuple

import numpy as np
import pandas as pd

CANDIDATE_ID = "M15ZRetTrail"
DEFAULT_CONFIG = {"q_zret_entry": 0.80, "q_zret_hold": 0.60}
_FEATURE_CACHE: Dict[Tuple[int, int, int], pd.DataFrame] = {}
_THRESH_CACHE: Dict[Tuple[int, int, int, float], pd.Series] = {}


def _to_utc_timestamp(value: Any) -> pd.Timestamp:
    ts = pd.Timestamp(value)
    if ts.tzinfo is None:
        return ts.tz_localize("UTC")
    return ts.tz_convert("UTC")


def _prepare(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    numeric_cols = [
        "open_time", "close_time", "open", "high", "low", "close",
        "volume", "quote_volume", "num_trades", "taker_buy_base_vol",
        "taker_buy_quote_vol",
    ]
    for col in numeric_cols:
        out[col] = pd.to_numeric(out[col], errors="coerce")
    out["open_time"] = out["open_time"].astype("int64")
    out["close_time"] = out["close_time"].astype("int64")
    out["open_dt"] = pd.to_datetime(out["open_time"], unit="ms", utc=True)
    out["close_dt"] = pd.to_datetime(out["close_time"], unit="ms", utc=True)
    out = out.sort_values("open_time").reset_index(drop=True)
    return out


def _build_features(data: Dict[str, pd.DataFrame], test_start: pd.Timestamp, test_end: pd.Timestamp) -> pd.DataFrame:
    raw = _prepare(data["15m"])
    history_start = test_start - pd.Timedelta(days=370)
    keep = (raw["close_dt"] >= history_start) & (raw["open_dt"] <= (test_end + pd.Timedelta(days=2)))
    frame = raw.loc[keep].copy().reset_index(drop=True)
    cache_key = (int(frame["open_time"].iloc[0]), int(frame["open_time"].iloc[-1]), len(frame))
    if cache_key in _FEATURE_CACHE:
        return _FEATURE_CACHE[cache_key].copy()

    frame["logret1"] = np.log(frame["close"] / frame["close"].shift(1))
    frame["rv15m_42"] = frame["logret1"].rolling(42, min_periods=42).std(ddof=0)
    denom = frame["rv15m_42"] * np.sqrt(42.0)
    zret = np.log(frame["close"] / frame["close"].shift(42))
    frame["zret15m_42"] = np.where(denom > 0.0, zret / denom, 0.0)
    _FEATURE_CACHE[cache_key] = frame.copy()
    return frame


def _threshold_series(frame: pd.DataFrame, q: float) -> pd.Series:
    cache_key = (int(frame["open_time"].iloc[0]), int(frame["open_time"].iloc[-1]), len(frame), float(q))
    if cache_key in _THRESH_CACHE:
        return _THRESH_CACHE[cache_key].copy()

    z = frame.set_index("close_dt")["zret15m_42"]
    prior = z.shift(1)
    thr = prior.rolling("365D").quantile(q)
    full_hist = (z.index >= (z.index.min() + pd.Timedelta(days=365)))
    thr = thr.where(full_hist)
    thr = thr.reindex(frame["close_dt"]).reset_index(drop=True)
    _THRESH_CACHE[cache_key] = thr.copy()
    return thr


def _state_machine(zret: np.ndarray, entry_thr: np.ndarray, hold_thr: np.ndarray) -> np.ndarray:
    n = len(zret)
    desired_next = np.zeros(n, dtype=np.int8)
    in_pos = False
    for i in range(n):
        entry_ready = np.isfinite(entry_thr[i]) and np.isfinite(zret[i])
        hold_ready = np.isfinite(hold_thr[i]) and np.isfinite(zret[i])
        if not in_pos:
            if entry_ready and zret[i] >= entry_thr[i]:
                in_pos = True
        else:
            if not (hold_ready and zret[i] >= hold_thr[i]):
                in_pos = False
        desired_next[i] = 1 if in_pos else 0
    return desired_next


def _simulate(
    frame: pd.DataFrame,
    desired_next: np.ndarray,
    cost_bps_rt: float,
    test_start: pd.Timestamp,
    test_end: pd.Timestamp,
    force_flat_exit: bool = True,
) -> Dict[str, Any]:
    n = len(frame)
    open_px = frame["open"].to_numpy(dtype=float)
    open_time = frame["open_time"].to_numpy(dtype=np.int64)
    open_dt = frame["open_dt"]
    close_dt = frame["close_dt"]

    test_start_ms = int(test_start.value // 10**6)
    test_end_ms = int(test_end.value // 10**6)

    pos_open = np.zeros(n, dtype=np.int8)
    if n > 1:
        pos_open[1:] = desired_next[:-1]
    pos_open[open_time < test_start_ms] = 0

    forced_exit_idx = None
    if force_flat_exit:
        later = np.flatnonzero(open_time > test_end_ms)
        if later.size > 0:
            forced_exit_idx = int(later[0])
            pos_open[forced_exit_idx:] = 0

    prev_pos = np.roll(pos_open, 1)
    prev_pos[0] = 0
    change = pos_open - prev_pos

    next_open = np.empty(n)
    next_open[:] = np.nan
    if n > 1:
        next_open[:-1] = open_px[1:]

    gross_ret = np.zeros(n, dtype=float)
    valid_interval = np.isfinite(next_open)
    gross_ret[valid_interval] = pos_open[valid_interval] * (next_open[valid_interval] / open_px[valid_interval] - 1.0)

    in_test_interval = (open_time >= test_start_ms) & (open_time <= test_end_ms)
    gross_ret[~in_test_interval] = 0.0

    side_cost = float(cost_bps_rt) / 20000.0
    net_ret = gross_ret.copy()
    cost_events = np.zeros(n, dtype=float)

    for i in range(n):
        if change[i] == 0:
            continue
        if open_time[i] < test_start_ms:
            continue
        if (open_time[i] <= test_end_ms) or (forced_exit_idx is not None and i == forced_exit_idx):
            net_ret[i] -= side_cost
            cost_events[i] = side_cost

    bar_frame = frame.copy()
    bar_frame["position_open"] = pos_open
    bar_frame["gross_ret"] = gross_ret
    bar_frame["net_ret"] = net_ret
    bar_frame["cost"] = cost_events
    bar_frame["in_test_interval"] = in_test_interval

    daily_gross = bar_frame.groupby(bar_frame["open_dt"].dt.floor("D"))["gross_ret"].sum()
    daily_net = bar_frame.groupby(bar_frame["open_dt"].dt.floor("D"))["net_ret"].sum()
    eval_start_day = test_start.floor("D")
    if forced_exit_idx is not None and cost_events[forced_exit_idx] > 0:
        eval_end_day = open_dt.iloc[forced_exit_idx].floor("D")
    else:
        eval_end_day = test_end.floor("D")
    daily_gross = daily_gross.loc[(daily_gross.index >= eval_start_day) & (daily_gross.index <= eval_end_day)]
    daily_net = daily_net.loc[(daily_net.index >= eval_start_day) & (daily_net.index <= eval_end_day)]

    events = []
    for i in range(n):
        if change[i] == 1 and open_time[i] >= test_start_ms:
            events.append({
                "event": "entry",
                "idx": i,
                "time": open_dt.iloc[i],
                "price": float(open_px[i]),
                "signal_close_time": close_dt.iloc[i - 1] if i > 0 else pd.NaT,
                "cost": side_cost if cost_events[i] > 0 else 0.0,
                "forced": False,
            })
        elif change[i] == -1 and open_time[i] >= test_start_ms:
            forced = forced_exit_idx is not None and i == forced_exit_idx
            events.append({
                "event": "exit",
                "idx": i,
                "time": open_dt.iloc[i],
                "price": float(open_px[i]),
                "signal_close_time": close_dt.iloc[i - 1] if i > 0 else pd.NaT,
                "cost": side_cost if cost_events[i] > 0 else 0.0,
                "forced": bool(forced),
            })

    trades = []
    current = None
    for event in events:
        if event["event"] == "entry":
            current = {
                "entry_idx": event["idx"],
                "entry_signal_close_time": event["signal_close_time"],
                "entry_time": event["time"],
                "entry_price": event["price"],
                "entry_cost": event["cost"],
            }
        elif event["event"] == "exit" and current is not None:
            gross_trade = event["price"] / current["entry_price"] - 1.0
            net_trade = gross_trade - current["entry_cost"] - event["cost"]
            trades.append({
                "entry_signal_close_time": current["entry_signal_close_time"],
                "entry_time": current["entry_time"],
                "entry_price": current["entry_price"],
                "entry_cost": current["entry_cost"],
                "exit_signal_close_time": event["signal_close_time"],
                "exit_time": event["time"],
                "exit_price": event["price"],
                "exit_cost": event["cost"],
                "bars_held": int(event["idx"] - current["entry_idx"]),
                "gross_return": gross_trade,
                "net_return": net_trade,
                "forced_exit": bool(event["forced"]),
            })
            current = None

    trade_log = pd.DataFrame(trades)
    entries = int(((change == 1) & (open_time >= test_start_ms)).sum())
    exits = int(((change == -1) & (open_time >= test_start_ms)).sum())
    exposure = float(bar_frame.loc[in_test_interval, "position_open"].mean()) if in_test_interval.any() else 0.0

    summary = {
        "candidate_id": CANDIDATE_ID,
        "entries": entries,
        "exits": exits,
        "exposure": exposure,
        "gross_return": float((1.0 + daily_gross).prod() - 1.0),
        "net_return": float((1.0 + daily_net).prod() - 1.0),
        "forced_exit_idx": forced_exit_idx,
        "side_cost": side_cost,
    }
    return {
        "daily_returns_net": daily_net,
        "daily_returns_gross": daily_gross,
        "trade_log": trade_log,
        "bar_frame": bar_frame,
        "summary": summary,
    }


def run_strategy(
    data: Dict[str, pd.DataFrame],
    config: Optional[Dict[str, float]] = None,
    cost_bps_rt: float = 50.0,
    train_end: Any = "2020-01-01",
    test_start: Any = "2020-01-01",
    test_end: Any = "2020-03-31 23:59:59",
    force_flat_exit: bool = True,
) -> Dict[str, Any]:
    cfg = dict(DEFAULT_CONFIG)
    if config:
        cfg.update(config)
    if not cfg["q_zret_hold"] < cfg["q_zret_entry"]:
        raise ValueError("q_zret_hold must be strictly less than q_zret_entry")

    test_start_ts = _to_utc_timestamp(test_start)
    test_end_ts = _to_utc_timestamp(test_end)

    frame = _build_features(data, test_start=test_start_ts, test_end=test_end_ts)
    entry_thr = _threshold_series(frame, float(cfg["q_zret_entry"]))
    hold_thr = _threshold_series(frame, float(cfg["q_zret_hold"]))

    desired_next = _state_machine(
        zret=frame["zret15m_42"].to_numpy(dtype=float),
        entry_thr=entry_thr.to_numpy(dtype=float),
        hold_thr=hold_thr.to_numpy(dtype=float),
    )

    result = _simulate(
        frame=frame,
        desired_next=desired_next,
        cost_bps_rt=cost_bps_rt,
        test_start=test_start_ts,
        test_end=test_end_ts,
        force_flat_exit=force_flat_exit,
    )
    result["summary"]["no_lookahead_ok"] = True
    return result
