from __future__ import annotations

from typing import Dict, List

import pandas as pd


REGIMES: List[str] = ["UNKNOWN", "ACCUMULATION", "MARKUP", "DISTRIBUTION", "MARKDOWN"]

_EVENT_ORDER: List[str] = ["SC", "SPRING", "SOS", "BC", "UT", "SOW"]
_EVENT_TO_REGIME: Dict[str, str] = {
    "SC": "ACCUMULATION",
    "SPRING": "ACCUMULATION",
    "SOS": "MARKUP",
    "BC": "DISTRIBUTION",
    "UT": "DISTRIBUTION",
    "SOW": "MARKDOWN",
}


def classify_regime_daily(price_df: pd.DataFrame, events_df: pd.DataFrame) -> pd.DataFrame:
    if price_df is None or price_df.empty:
        return pd.DataFrame(columns=["symbol", "date", "regime"])

    data = price_df.copy()
    data["date"] = pd.to_datetime(data["date"], errors="coerce")
    data = data.sort_values("date").reset_index(drop=True)

    symbol = str(data["symbol"].iloc[0]) if "symbol" in data.columns else ""

    if events_df is None or events_df.empty:
        return pd.DataFrame(
            {"symbol": symbol, "date": data["date"], "regime": ["UNKNOWN"] * len(data)}
        )

    events = events_df.copy()
    events["date"] = pd.to_datetime(events["date"], errors="coerce")
    events["event"] = events["event"].astype(str).str.upper()
    events = events[events["event"].isin(_EVENT_TO_REGIME.keys())]

    if events.empty:
        return pd.DataFrame(
            {"symbol": symbol, "date": data["date"], "regime": ["UNKNOWN"] * len(data)}
        )

    events_by_date = (
        events.groupby("date", sort=False)["event"]
        .apply(lambda s: set(s))
        .to_dict()
    )

    regime = "UNKNOWN"
    regimes_out: List[str] = []
    for dt in data["date"]:
        day_events = events_by_date.get(dt)
        if day_events:
            for event in _EVENT_ORDER:
                if event in day_events:
                    regime = _EVENT_TO_REGIME[event]
        regimes_out.append(regime)

    return pd.DataFrame({"symbol": symbol, "date": data["date"], "regime": regimes_out})
