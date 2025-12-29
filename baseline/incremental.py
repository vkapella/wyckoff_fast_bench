from __future__ import annotations

from dataclasses import dataclass, field
from typing import Deque, Dict, Optional, List
from collections import deque

import numpy as np
import pandas as pd

from baseline.structural import WyckoffStructuralConfig, _prepare_ohlcv


@dataclass
class DetectorState:
    cfg: WyckoffStructuralConfig
    idx: int = -1
    tr_window: Deque[float] = field(default_factory=deque)
    vol_window: Deque[float] = field(default_factory=deque)
    close_window: Deque[float] = field(default_factory=deque)
    tr_mean: Optional[float] = None
    tr_var: Optional[float] = None
    vol_mean: Optional[float] = None
    vol_var: Optional[float] = None
    sma: Optional[float] = None
    sma_slope: Optional[float] = None
    prev_sma: Optional[float] = None
    prev_close: Optional[float] = None
    support_level: Optional[float] = None
    resistance_level: Optional[float] = None
    last_event_idx: Dict[str, int] = field(default_factory=dict)
    last_event_label: Optional[str] = None
    sc_idx: Optional[int] = None
    bc_idx: Optional[int] = None
    ar_idx: Optional[int] = None
    ar_top_idx: Optional[int] = None
    spring_idx: Optional[int] = None
    ut_idx: Optional[int] = None
    sos_idx: Optional[int] = None
    sow_idx: Optional[int] = None
    ar_deadline: Optional[int] = None
    ar_top_deadline: Optional[int] = None
    spring_deadline: Optional[int] = None
    ut_deadline: Optional[int] = None
    sos_deadline: Optional[int] = None
    sow_deadline: Optional[int] = None
    sc_locked: bool = False
    bc_locked: bool = False
    ar_locked: bool = False
    ar_top_locked: bool = False
    spring_locked: bool = False
    ut_locked: bool = False
    sos_locked: bool = False
    sow_locked: bool = False
    low_since_sc: Optional[float] = None
    high_since_bc: Optional[float] = None
    pending_spring: Optional[Dict[str, object]] = None
    pending_ut: Optional[Dict[str, object]] = None
    regime_state: str = "UNKNOWN"
    regime_bars: int = 0
    long_window: int = 0

    def __post_init__(self) -> None:
        self.tr_window = deque(maxlen=self.cfg.range_lookback)
        self.vol_window = deque(maxlen=self.cfg.vol_lookback)
        self.close_window = deque(maxlen=self.cfg.lookback_trend)
        self.long_window = (
            max(self.cfg.lookback_trend, self.cfg.range_lookback, self.cfg.vol_lookback) * 25
        )


def _is_valid(value: Optional[float]) -> bool:
    return value is not None and not np.isnan(value)


def _update_window_stats(
    window: Deque[float], value: float, window_size: int
) -> tuple[Optional[float], Optional[float]]:
    window.append(float(value))
    if len(window) < window_size:
        return None, None
    arr = np.asarray(window, dtype="float64")
    mean = float(arr.mean())
    std = float(arr.std(ddof=0))
    if std == 0.0 or np.isnan(std):
        return mean, None
    return mean, std


def _compute_zscore(value: float, mean: Optional[float], std: Optional[float]) -> Optional[float]:
    if mean is None or std is None:
        return None
    return (value - mean) / std


def _sos_conditioned(state: DetectorState, idx: int) -> bool:
    confirm_window = 60
    conflict_window = 60
    recent_good = any(
        idx - state.last_event_idx.get(label, -10_000) <= confirm_window
        for label in ("SC", "AR", "SPRING")
    )
    recent_conflict = any(
        idx - state.last_event_idx.get(label, -10_000) <= conflict_window
        for label in ("BC", "SOW")
    )
    return (
        recent_good
        and not recent_conflict
        and state.regime_state in {"ACCUMULATION", "MARKUP"}
    )


def _apply_regime_transition(state: DetectorState, event_label: str, idx: int) -> None:
    min_hold = state.cfg.min_bars_in_range
    new_state: Optional[str] = None

    if event_label == "SOW":
        new_state = "MARKDOWN"
    elif event_label == "BC":
        new_state = "DISTRIBUTION"
    elif event_label == "SPRING":
        if state.regime_state not in {"DISTRIBUTION", "MARKDOWN"}:
            new_state = "MARKUP"
    elif event_label in {"AR", "SC"}:
        new_state = "ACCUMULATION"
    elif event_label in {"AR_TOP", "UT"}:
        new_state = "DISTRIBUTION"
    elif event_label == "SOS" and _sos_conditioned(state, idx):
        new_state = "MARKUP"

    if new_state is None or new_state == state.regime_state:
        return

    if state.regime_state == "MARKUP" and event_label != "BC":
        return
    if state.regime_state == "DISTRIBUTION" and event_label != "SOW":
        if state.regime_bars < min_hold:
            return
    if state.regime_state == "MARKDOWN" and event_label != "SC":
        if state.regime_bars < min_hold:
            return

    state.regime_state = new_state
    state.regime_bars = 0


def update_detector_state(state: DetectorState, bar: dict) -> Optional[dict]:
    state.idx += 1
    idx = state.idx

    # Path-dependent note: SC/BC are emitted on first qualifying bars instead of
    # the baseline's global "latest candidate" scan, so some timing deltas can
    # appear without any reclassification once emitted.
    tr_mean, tr_std = _update_window_stats(
        state.tr_window, bar["tr"], state.cfg.range_lookback
    )
    vol_mean, vol_std = _update_window_stats(
        state.vol_window, bar["volume"], state.cfg.vol_lookback
    )
    state.tr_mean = tr_mean
    state.tr_var = (tr_std ** 2) if _is_valid(tr_std) else None
    state.vol_mean = vol_mean
    state.vol_var = (vol_std ** 2) if _is_valid(vol_std) else None

    tr_z = _compute_zscore(bar["tr"], tr_mean, tr_std)
    vol_z = _compute_zscore(bar["volume"], vol_mean, vol_std)
    if _is_valid(tr_z):
        tr_z *= state.cfg.range_z_scale
    if _is_valid(vol_z):
        vol_z *= state.cfg.volume_z_scale

    state.close_window.append(float(bar["close"]))
    if len(state.close_window) == state.cfg.lookback_trend:
        state.sma = float(np.mean(state.close_window))
        if state.prev_sma is not None:
            state.sma_slope = state.sma - state.prev_sma
        state.prev_sma = state.sma
    else:
        state.sma = None
        state.sma_slope = None

    if state.sc_idx is not None and state.ar_idx is None:
        state.low_since_sc = (
            float(bar["low"])
            if state.low_since_sc is None
            else min(state.low_since_sc, float(bar["low"]))
        )
    if state.bc_idx is not None and state.ar_top_idx is None:
        state.high_since_bc = (
            float(bar["high"])
            if state.high_since_bc is None
            else max(state.high_since_bc, float(bar["high"]))
        )

    if state.ar_deadline is not None and state.ar_idx is None and idx > state.ar_deadline:
        state.ar_locked = True
    if state.ar_top_deadline is not None and state.ar_top_idx is None and idx > state.ar_top_deadline:
        state.ar_top_locked = True
    if state.spring_deadline is not None and state.spring_idx is None and idx > state.spring_deadline:
        state.spring_locked = True
        state.pending_spring = None
    if state.ut_deadline is not None and state.ut_idx is None and idx > state.ut_deadline:
        state.ut_locked = True
        state.pending_ut = None
    if state.sos_deadline is not None and state.sos_idx is None and idx > state.sos_deadline:
        state.sos_locked = True
    if state.sow_deadline is not None and state.sow_idx is None and idx > state.sow_deadline:
        state.sow_locked = True

    date_str = bar["date"].strftime("%Y-%m-%d")
    close_pos = bar["close_pos"]

    # Event order follows the baseline sequence; only one event is emitted per bar.
    if not state.sc_locked and state.sc_idx is None:
        if (
            _is_valid(tr_z)
            and _is_valid(vol_z)
            and tr_z >= state.cfg.sc_tr_z
            and vol_z >= state.cfg.sc_vol_z
            and _is_valid(close_pos)
            and close_pos >= 0.5
        ):
            if (not state.cfg.require_prior_trend_for_sc_bc) or (
                _is_valid(state.sma_slope) and state.sma_slope < 0
            ):
                state.sc_idx = idx
                state.sc_locked = True
                state.ar_deadline = idx + state.cfg.min_bars_in_range - 1
                state.low_since_sc = float(bar["low"])
                state.last_event_idx["SC"] = idx
                state.last_event_label = "SC"
                _apply_regime_transition(state, "SC", idx)
                state.regime_bars += 1
                return {"date": date_str, "event": "SC", "score": float(vol_z)}

    if not state.bc_locked and state.bc_idx is None:
        if (
            _is_valid(tr_z)
            and _is_valid(vol_z)
            and tr_z >= state.cfg.bc_tr_z
            and vol_z >= state.cfg.bc_vol_z
            and _is_valid(close_pos)
            and close_pos >= 0.6
        ):
            if (not state.cfg.require_prior_trend_for_sc_bc) or (
                _is_valid(state.sma_slope) and state.sma_slope > 0
            ):
                state.bc_idx = idx
                state.bc_locked = True
                state.ar_top_deadline = idx + state.cfg.min_bars_in_range - 1
                state.high_since_bc = float(bar["high"])
                state.last_event_idx["BC"] = idx
                state.last_event_label = "BC"
                _apply_regime_transition(state, "BC", idx)
                state.regime_bars += 1
                return {"date": date_str, "event": "BC", "score": float(vol_z)}

    if state.sc_idx is not None and state.ar_idx is None and not state.ar_locked:
        if state.ar_deadline is None or idx <= state.ar_deadline:
            if state.prev_close is not None and _is_valid(tr_z):
                if float(bar["close"]) > state.prev_close and tr_z > 0.5:
                    state.ar_idx = idx
                    state.support_level = (
                        state.low_since_sc if state.low_since_sc is not None else float(bar["low"])
                    )
                    state.spring_deadline = idx + state.long_window
                    state.sow_deadline = idx + state.long_window
                    state.last_event_idx["AR"] = idx
                    state.last_event_label = "AR"
                    _apply_regime_transition(state, "AR", idx)
                    state.regime_bars += 1
                    return {"date": date_str, "event": "AR", "score": float(tr_z)}

    if state.bc_idx is not None and state.ar_top_idx is None and not state.ar_top_locked:
        if state.ar_top_deadline is None or idx <= state.ar_top_deadline:
            if state.prev_close is not None and _is_valid(tr_z):
                if float(bar["close"]) < state.prev_close and tr_z > 0.5:
                    state.ar_top_idx = idx
                    state.resistance_level = (
                        state.high_since_bc if state.high_since_bc is not None else float(bar["high"])
                    )
                    state.ut_deadline = idx + state.long_window
                    state.sos_deadline = idx + state.long_window
                    state.last_event_idx["AR_TOP"] = idx
                    state.last_event_label = "AR_TOP"
                    _apply_regime_transition(state, "AR_TOP", idx)
                    state.regime_bars += 1
                    return {"date": date_str, "event": "AR_TOP", "score": float(tr_z)}

    if state.support_level is not None and state.spring_idx is None and not state.spring_locked:
        if state.spring_deadline is None or idx <= state.spring_deadline:
            if state.pending_spring is not None:
                if idx > state.pending_spring["deadline"]:
                    state.pending_spring = None
                elif float(bar["close"]) >= state.support_level:
                    # Reentry confirmation arrives after the break bar; emit using
                    # the original break date to avoid moving events forward.
                    event_idx = int(state.pending_spring["idx"])
                    event_date = state.pending_spring["date"]
                    event_score = float(state.pending_spring["score"])
                    state.spring_idx = event_idx
                    state.pending_spring = None
                    state.last_event_idx["SPRING"] = event_idx
                    state.last_event_label = "SPRING"
                    _apply_regime_transition(state, "SPRING", event_idx)
                    state.regime_bars += 1
                    return {"date": event_date, "event": "SPRING", "score": event_score}
            if idx >= state.cfg.min_bars_in_range:
                if float(bar["low"]) < state.support_level * (1 - state.cfg.spring_break_pct):
                    if (
                        _is_valid(close_pos)
                        and close_pos >= state.cfg.spring_close_pos
                        and _is_valid(vol_z)
                        and vol_z >= state.cfg.spring_vol_z
                    ):
                        if float(bar["close"]) >= state.support_level:
                            state.spring_idx = idx
                            state.last_event_idx["SPRING"] = idx
                            state.last_event_label = "SPRING"
                            _apply_regime_transition(state, "SPRING", idx)
                            state.regime_bars += 1
                            return {"date": date_str, "event": "SPRING", "score": float(vol_z)}
                        state.pending_spring = {
                            "idx": float(idx),
                            "date": date_str,
                            "score": float(vol_z),
                            "deadline": float(idx + state.cfg.spring_reentry_bars),
                        }

    if state.resistance_level is not None and state.ut_idx is None and not state.ut_locked:
        if state.ut_deadline is None or idx <= state.ut_deadline:
            if state.pending_ut is not None:
                if idx > state.pending_ut["deadline"]:
                    state.pending_ut = None
                elif float(bar["close"]) <= state.resistance_level:
                    event_idx = int(state.pending_ut["idx"])
                    event_date = state.pending_ut["date"]
                    event_score = float(state.pending_ut["score"])
                    state.ut_idx = event_idx
                    state.pending_ut = None
                    state.last_event_idx["UT"] = event_idx
                    state.last_event_label = "UT"
                    _apply_regime_transition(state, "UT", event_idx)
                    state.regime_bars += 1
                    return {"date": event_date, "event": "UT", "score": event_score}
            if idx >= state.cfg.min_bars_in_range:
                if float(bar["high"]) > state.resistance_level * (1 + state.cfg.ut_break_pct):
                    if _is_valid(close_pos) and close_pos <= state.cfg.ut_close_pos:
                        score = float(tr_z) if _is_valid(tr_z) else float("nan")
                        if float(bar["close"]) <= state.resistance_level:
                            state.ut_idx = idx
                            state.last_event_idx["UT"] = idx
                            state.last_event_label = "UT"
                            _apply_regime_transition(state, "UT", idx)
                            state.regime_bars += 1
                            return {"date": date_str, "event": "UT", "score": score}
                        state.pending_ut = {
                            "idx": float(idx),
                            "date": date_str,
                            "score": score,
                            "deadline": float(idx + state.cfg.ut_reentry_bars),
                        }

    if state.resistance_level is not None and state.sos_idx is None and not state.sos_locked:
        if state.sos_deadline is None or idx <= state.sos_deadline:
            if _is_valid(tr_z) and float(bar["close"]) > state.resistance_level:
                if tr_z >= state.cfg.sos_tr_z:
                    state.sos_idx = idx
                    state.last_event_idx["SOS"] = idx
                    state.last_event_label = "SOS"
                    _apply_regime_transition(state, "SOS", idx)
                    state.regime_bars += 1
                    return {"date": date_str, "event": "SOS", "score": float(tr_z)}

    if state.support_level is not None and state.sow_idx is None and not state.sow_locked:
        if state.sow_deadline is None or idx <= state.sow_deadline:
            if _is_valid(tr_z) and float(bar["close"]) < state.support_level:
                if tr_z >= state.cfg.sow_tr_z:
                    state.sow_idx = idx
                    state.last_event_idx["SOW"] = idx
                    state.last_event_label = "SOW"
                    _apply_regime_transition(state, "SOW", idx)
                    state.regime_bars += 1
                    return {"date": date_str, "event": "SOW", "score": float(tr_z)}

    state.regime_bars += 1
    state.prev_close = float(bar["close"])
    return None


class IncrementalWyckoffDetector:
    def __init__(self, cfg: WyckoffStructuralConfig) -> None:
        self.cfg = cfg
        self.state = DetectorState(cfg)
        self.events: List[Dict[str, float]] = []

    def update(self, bar: dict) -> None:
        event = update_detector_state(self.state, bar)
        if event is not None:
            self.events.append(event)
        self.state.prev_close = float(bar["close"])

    def run(self, df: pd.DataFrame, symbol: str) -> pd.DataFrame:
        self.state = DetectorState(self.cfg)
        self.events = []
        prepared = _prepare_ohlcv(df)
        for _, row in prepared.iterrows():
            bar = {
                "date": row["date"],
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": float(row["volume"]),
                "tr": float(row["tr"]),
                "close_pos": float(row["close_pos"]) if pd.notna(row["close_pos"]) else np.nan,
            }
            self.update(bar)

        rows = [
            {"symbol": symbol, "date": ev["date"], "event": ev["event"], "score": ev["score"]}
            for ev in self.events
        ]
        return pd.DataFrame(rows, columns=["symbol", "date", "event", "score"])
