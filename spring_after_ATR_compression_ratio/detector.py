from __future__ import annotations

from typing import Dict

import pandas as pd

from baseline.adapter import run_baseline_structural


def _compute_atr(df: pd.DataFrame, window: int) -> pd.Series:
    col_name = f"atr.average_true_range_{window}"
    if col_name in df.columns:
        return pd.to_numeric(df[col_name], errors="coerce")
    if window == 14 and "atr.average_true_range" in df.columns:
        return pd.to_numeric(df["atr.average_true_range"], errors="coerce")

    prev_close = df["close"].shift(1)
    tr = pd.concat(
        [
            (df["high"] - df["low"]).abs(),
            (df["high"] - prev_close).abs(),
            (df["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(window=window, min_periods=window).mean()


def spring_after_ATR_compression_ratio_detector(df: pd.DataFrame, cfg: Dict) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=["symbol", "date", "event", "score"])

    if "symbol" in df.columns and not df["symbol"].isna().all():
        symbol = str(df["symbol"].iloc[0])
    else:
        symbol = str(cfg.get("symbol", "UNKNOWN"))

    baseline_events = run_baseline_structural(df, symbol, None)
    if baseline_events.empty:
        return baseline_events

    events = baseline_events.copy()
    events["date"] = pd.to_datetime(events["date"], errors="coerce")
    spring = events[events["event"].str.upper() == "SPRING"].copy()
    if spring.empty:
        return spring.reset_index(drop=True)

    data = df.copy()
    data["date"] = pd.to_datetime(data["date"], errors="coerce")
    data = data.sort_values("date").reset_index(drop=True)

    atr_fast = _compute_atr(data, 14)
    atr_slow = _compute_atr(data, 60)
    atr_ratio = atr_fast / atr_slow

    atr_df = pd.DataFrame({"date": data["date"], "atr_ratio": atr_ratio})
    merged = spring.merge(atr_df, on="date", how="left")
    # Retest v2: relaxed ATR compression threshold (0.85)
    filtered = merged[(merged["atr_ratio"] <= 0.85) & merged["atr_ratio"].notna()]

    return filtered[["symbol", "date", "event", "score"]].reset_index(drop=True)
