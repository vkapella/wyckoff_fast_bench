from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd


def add_forward_returns(
    events_df: pd.DataFrame, price_df: pd.DataFrame, forward_windows: Iterable[int]
) -> pd.DataFrame:
    forward_windows = sorted(set(int(w) for w in forward_windows))
    base_columns = list(events_df.columns) + [f"fwd_{w}" for w in forward_windows]
    if events_df.empty:
        return pd.DataFrame(columns=base_columns)

    price = price_df[["date", "close"]].copy()
    price["date"] = pd.to_datetime(price["date"])
    price = price.sort_values("date").reset_index(drop=True)
    price.set_index("date", inplace=True)

    for window in forward_windows:
        price[f"fwd_{window}"] = price["close"].shift(-window) / price["close"] - 1.0

    events = events_df.copy()
    events["date"] = pd.to_datetime(events["date"])
    events = events.sort_values("date").set_index("date")

    for window in forward_windows:
        events[f"fwd_{window}"] = price[f"fwd_{window}"].reindex(events.index)

    return events.reset_index()


def summarize_forward_returns(forward_df: pd.DataFrame, coverage_years: float) -> pd.DataFrame:
    columns = [
        "detector",
        "event",
        "density",
        "median_fwd_20",
        "win_rate_20",
        "p5_fwd_20",
        "stability_delta",
        "event_count",
    ]
    if forward_df.empty:
        return pd.DataFrame(columns=columns)

    fwd = forward_df.copy()
    fwd["date"] = pd.to_datetime(fwd["date"])

    results = []
    grouped = fwd.groupby(["detector", "event"])
    for (detector, event), grp in grouped:
        fwd20 = grp["fwd_20"].dropna()
        median_20 = fwd20.median() if not fwd20.empty else np.nan
        win_rate_20 = (fwd20 > 0).mean() if not fwd20.empty else np.nan
        p5 = fwd20.quantile(0.05) if not fwd20.empty else np.nan

        if grp["date"].empty:
            stability_delta = np.nan
        else:
            t_min, t_max = grp["date"].min(), grp["date"].max()
            midpoint = t_min + (t_max - t_min) / 2
            first = grp[grp["date"] <= midpoint]["fwd_20"].dropna()
            second = grp[grp["date"] > midpoint]["fwd_20"].dropna()
            stability_delta = (
                second.median() - first.median() if not first.empty and not second.empty else np.nan
            )

        density = len(grp) / coverage_years if coverage_years else np.nan

        results.append(
            {
                "detector": detector,
                "event": event,
                "density": density,
                "median_fwd_20": median_20,
                "win_rate_20": win_rate_20,
                "p5_fwd_20": p5,
                "stability_delta": stability_delta,
                "event_count": len(grp),
            }
        )

    return pd.DataFrame(results, columns=columns).sort_values(["detector", "event"]).reset_index(drop=True)


def build_comparison_table(summary_df: pd.DataFrame) -> pd.DataFrame:
    columns = ["detector", "event", "density", "median_fwd_20", "win_rate_20", "p5_fwd_20", "stability_delta"]
    if summary_df.empty:
        return pd.DataFrame(columns=columns)
    return summary_df[columns].copy()


def evaluate_bc_effect(forward_df: pd.DataFrame, forward_windows: list[int]) -> pd.DataFrame:
    rows = []
    if forward_df.empty:
        return pd.DataFrame(
            columns=[
                "window",
                "count_bc",
                "count_baseline",
                "median_bc",
                "median_baseline",
                "median_delta",
                "win_rate_bc",
                "win_rate_baseline",
                "win_rate_delta",
                "p5_bc",
                "p5_baseline",
                "p5_delta",
            ]
        )

    bc_df = evaluate_event_effect(forward_df, forward_windows, "BC").rename(
        columns={
            "count_event": "count_bc",
            "median_event": "median_bc",
            "win_rate_event": "win_rate_bc",
            "p5_event": "p5_bc",
        }
    )
    if "event" in bc_df.columns:
        bc_df = bc_df.drop(columns=["event"])
    return bc_df[
        [
            "window",
            "count_bc",
            "count_baseline",
            "median_bc",
            "median_baseline",
            "median_delta",
            "win_rate_bc",
            "win_rate_baseline",
            "win_rate_delta",
            "p5_bc",
            "p5_baseline",
            "p5_delta",
        ]
    ]


def evaluate_event_effect(
    forward_df: pd.DataFrame, forward_windows: list[int], event_name: str
) -> pd.DataFrame:
    rows = []
    if forward_df.empty:
        return pd.DataFrame(
            columns=[
                "window",
                "event",
                "count_event",
                "count_baseline",
                "median_event",
                "median_baseline",
                "median_delta",
                "win_rate_event",
                "win_rate_baseline",
                "win_rate_delta",
                "p5_event",
                "p5_baseline",
                "p5_delta",
            ]
        )

    for window in forward_windows:
        col = f"fwd_{int(window)}"
        if col not in forward_df.columns:
            event_vals = pd.Series(dtype="float64")
            base_vals = pd.Series(dtype="float64")
        else:
            event_vals = forward_df.loc[forward_df["event"] == event_name, col].dropna()
            base_vals = forward_df.loc[forward_df["event"] != event_name, col].dropna()

        median_event = event_vals.median() if not event_vals.empty else np.nan
        median_base = base_vals.median() if not base_vals.empty else np.nan
        win_event = (event_vals > 0).mean() if not event_vals.empty else np.nan
        win_base = (base_vals > 0).mean() if not base_vals.empty else np.nan
        p5_event = event_vals.quantile(0.05) if not event_vals.empty else np.nan
        p5_base = base_vals.quantile(0.05) if not base_vals.empty else np.nan

        rows.append(
            {
                "window": int(window),
                "event": event_name,
                "count_event": int(event_vals.shape[0]),
                "count_baseline": int(base_vals.shape[0]),
                "median_event": median_event,
                "median_baseline": median_base,
                "median_delta": median_event - median_base
                if pd.notna(median_event) and pd.notna(median_base)
                else np.nan,
                "win_rate_event": win_event,
                "win_rate_baseline": win_base,
                "win_rate_delta": win_event - win_base if pd.notna(win_event) and pd.notna(win_base) else np.nan,
                "p5_event": p5_event,
                "p5_baseline": p5_base,
                "p5_delta": p5_event - p5_base if pd.notna(p5_event) and pd.notna(p5_base) else np.nan,
            }
        )

    return pd.DataFrame(rows)


def evaluate_sos_after_bc_effect(
    forward_df: pd.DataFrame, forward_windows: list[int], lookback_days: int
) -> pd.DataFrame:
    rows = []
    if forward_df.empty:
        return pd.DataFrame(
            columns=[
                "window",
                "event",
                "lookback_days",
                "count_event",
                "count_baseline",
                "median_event",
                "median_baseline",
                "median_delta",
                "win_rate_event",
                "win_rate_baseline",
                "win_rate_delta",
                "p5_event",
                "p5_baseline",
                "p5_delta",
            ]
        )

    df = forward_df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])

    sos_after_bc_mask = pd.Series(False, index=df.index)
    for _, group in df.groupby("symbol", sort=False):
        group = group.sort_values("date")
        last_bc_date = None
        for idx, row in group.iterrows():
            if row["event"] == "BC":
                last_bc_date = row["date"]
                continue
            if row["event"] == "SOS" and last_bc_date is not None:
                delta_days = (row["date"] - last_bc_date).days
                if 0 < delta_days <= lookback_days:
                    sos_after_bc_mask.at[idx] = True

    sos_after_bc_df = df.loc[sos_after_bc_mask]
    base_df = df.loc[df["event"] == "BC"]
    if base_df.empty:
        base_df = df.loc[df["event"] != "SOS"]

    for window in forward_windows:
        col = f"fwd_{int(window)}"
        if col not in df.columns:
            event_vals = pd.Series(dtype="float64")
            base_vals = pd.Series(dtype="float64")
        else:
            event_vals = sos_after_bc_df[col].dropna()
            base_vals = base_df[col].dropna()

        median_event = event_vals.median() if not event_vals.empty else np.nan
        median_base = base_vals.median() if not base_vals.empty else np.nan
        win_event = (event_vals > 0).mean() if not event_vals.empty else np.nan
        win_base = (base_vals > 0).mean() if not base_vals.empty else np.nan
        p5_event = event_vals.quantile(0.05) if not event_vals.empty else np.nan
        p5_base = base_vals.quantile(0.05) if not base_vals.empty else np.nan

        rows.append(
            {
                "window": int(window),
                "event": "SOS_AFTER_BC",
                "lookback_days": int(lookback_days),
                "count_event": int(event_vals.shape[0]),
                "count_baseline": int(base_vals.shape[0]),
                "median_event": median_event,
                "median_baseline": median_base,
                "median_delta": median_event - median_base
                if pd.notna(median_event) and pd.notna(median_base)
                else np.nan,
                "win_rate_event": win_event,
                "win_rate_baseline": win_base,
                "win_rate_delta": win_event - win_base if pd.notna(win_event) and pd.notna(win_base) else np.nan,
                "p5_event": p5_event,
                "p5_baseline": p5_base,
                "p5_delta": p5_event - p5_base if pd.notna(p5_event) and pd.notna(p5_base) else np.nan,
            }
        )

    return pd.DataFrame(rows)
