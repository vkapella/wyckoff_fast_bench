from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Union

import pandas as pd
import yaml


def load_config(path: Union[str, Path] = "config.yaml") -> Dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)


def ensure_output_path(path: str) -> Path:
    output_path = Path(path)
    output_path.mkdir(parents=True, exist_ok=True)
    return output_path


def list_symbols(ohlcv_path: str) -> List[str]:
    base = Path(ohlcv_path)
    symbols: List[str] = []
    if not base.exists():
        return symbols
    for entry in base.iterdir():
        if entry.is_dir() and entry.name.startswith("symbol="):
            symbols.append(entry.name.split("symbol=", 1)[1])
    return sorted(symbols)


def read_symbol_data(symbol: str, ohlcv_path: str, lookback_days: int) -> Optional[pd.DataFrame]:
    path = Path(ohlcv_path) / f"symbol={symbol}"
    if not path.exists():
        return None

    df = pd.read_parquet(path)
    if df.empty:
        return None

    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    if "symbol" not in df.columns:
        df["symbol"] = symbol
    df = df.sort_values("date")
    if lookback_days and lookback_days > 0:
        cutoff = df["date"].max() - pd.Timedelta(days=int(lookback_days))
        df = df[df["date"] >= cutoff]

    return df.reset_index(drop=True)

def compute_years_covered(df: pd.DataFrame) -> float:
    if df.empty:
        return 0.0
    date_min, date_max = df["date"].min(), df["date"].max()
    days = max(1, (date_max - date_min).days)
    return days / 365.25


def append_to_csv(df: pd.DataFrame, path: Path) -> None:
    if df.empty:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    header = not path.exists()
    df.to_csv(path, mode="a", header=header, index=False)
