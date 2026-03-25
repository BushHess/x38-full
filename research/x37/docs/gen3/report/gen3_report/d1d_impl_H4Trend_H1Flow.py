
import math
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

CANDIDATE_ID = "H4Trend_H1Flow"
DEFAULT_CONFIG = {"q_flow_entry": 0.80, "q_flow_hold": 0.60}
ABLATION = None


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


def _build_features(data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    fast = _prepare(data["1h"])
    slow = _prepare(data["4h"])

    fast["imb"] = np.where(
        fast["volume"] > 0.0,
        2.0 * (fast["taker_buy_base_vol"] / fast["volume"]) - 1.0,
        0.0,
    )
    fast["flow1h_168"] = fast["imb"].rolling(168, min_periods=168).mean()

    slow["trend4h_168"] = slow["close"] / slow["close"].shift(168) - 1.0
    slow_merge = slow[["close_time", "trend4h_168"]].copy()
    slow_merge = slow_merge.rename(columns={"close_time": "slow_close_time"})

    merged = pd.merge_asof(
        fast.sort_values("close_time"),
        slow_merge.sort_values("slow_close_time"),
        left_on="close_time",
        right_on="slow_close_time",
        direction="backward",
        allow_exact_matches=False,
    )
    return merged.reset_index(drop=True)


def _training_quantile(series: pd.Series, train_end_ms: int, q: float, close_time: pd.Series) -> float:
    mask = (close_time < train_end_ms) & series.notna()
    values = series.loc[mask].to_numpy(dtype=float)
    if values.size == 0:
        return float("nan")
    return float(np.quantile(values, q, method="linear"))


def _state_machine(trend_ok: np.ndarray, flow: np.ndarray, entry_thr: float, hold_thr: float) -> np.ndarray:
    n = len(flow)
    desired_next = np.zeros(n, dtype=np.int8)
    in_pos = False
    for i in range(n):
        has_flow = np.isfinite(flow[i])
        allow = bool(trend_ok[i]) if np.isfinite(trend_ok[i]) else False
        if ABLATION == "trend4h":
            allow = has_flow
        if ABLATION == "flow1h":
            has_flow = True
        if not in_pos:
            cond = allow and has_flow
            if ABLATION != "flow1h":
                cond = cond and (flow[i] >= entry_thr)
            if cond:
                in_pos = True
        else:
            cond = allow and has_flow
            if ABLATION != "flow1h":
                cond = cond and (flow[i] >= hold_thr)
            if not cond:
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

    entry_lookup = {}
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
        "ablation": ABLATION,
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
    if ABLATION is None and config:
        cfg.update(config)
    if not cfg["q_flow_hold"] < cfg["q_flow_entry"]:
        raise ValueError("q_flow_hold must be strictly less than q_flow_entry")

    train_end_ts = _to_utc_timestamp(train_end)
    test_start_ts = _to_utc_timestamp(test_start)
    test_end_ts = _to_utc_timestamp(test_end)

    frame = _build_features(data)
    entry_thr = _training_quantile(frame["flow1h_168"], int(train_end_ts.value // 10**6), float(cfg["q_flow_entry"]), frame["close_time"])
    hold_thr = _training_quantile(frame["flow1h_168"], int(train_end_ts.value // 10**6), float(cfg["q_flow_hold"]), frame["close_time"])

    trend_ok = frame["trend4h_168"].to_numpy(dtype=float) > 0.0
    desired_next = _state_machine(
        trend_ok=trend_ok,
        flow=frame["flow1h_168"].to_numpy(dtype=float),
        entry_thr=entry_thr,
        hold_thr=hold_thr,
    )

    result = _simulate(
        frame=frame,
        desired_next=desired_next,
        cost_bps_rt=cost_bps_rt,
        test_start=test_start_ts,
        test_end=test_end_ts,
        force_flat_exit=force_flat_exit,
    )

    if frame["slow_close_time"].notna().any():
        no_lookahead_ok = bool((frame.loc[frame["slow_close_time"].notna(), "slow_close_time"] < frame.loc[frame["slow_close_time"].notna(), "close_time"]).all())
    else:
        no_lookahead_ok = True
    result["summary"]["no_lookahead_ok"] = no_lookahead_ok
    result["summary"]["entry_threshold"] = entry_thr
    result["summary"]["hold_threshold"] = hold_thr
    return result
