from __future__ import annotations

from bisect import bisect_right
from typing import Dict

import pandas as pd

from baseline.adapter import run_baseline_structural


def spring_after_sc_detector(df: pd.DataFrame, cfg: Dict) -> pd.DataFrame:
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
    sc = events[events["event"].str.upper() == "SC"]

    if spring.empty or sc.empty:
        return spring.reset_index(drop=True)

    data = df.copy()
    data["date"] = pd.to_datetime(data["date"], errors="coerce")
    data = data.sort_values("date").reset_index(drop=True)
    date_index = data.reset_index().groupby("date", sort=False)["index"].min()

    sc_indices = []
    for sc_date in pd.to_datetime(sc["date"], errors="coerce").dropna():
        idx = date_index.get(sc_date)
        if idx is not None:
            sc_indices.append(int(idx))
    sc_indices.sort()

    if not sc_indices:
        return spring.reset_index(drop=True)

    lookback_bars = 60
    keep_rows = []
    for i, row in spring.iterrows():
        spring_date = row["date"]
        if pd.isna(spring_date):
            continue
        spring_idx = date_index.get(spring_date)
        if spring_idx is None:
            continue
        pos = bisect_right(sc_indices, int(spring_idx) - 1) - 1
        if pos >= 0 and int(spring_idx) - sc_indices[pos] <= lookback_bars:
            keep_rows.append(i)

    filtered = spring.loc[keep_rows, ["symbol", "date", "event", "score"]]
    return filtered.reset_index(drop=True)
