from __future__ import annotations

from typing import Callable, Dict

import pandas as pd

from baseline.adapter import run_baseline_structural
from spring_after_sc.detector import spring_after_sc_detector
from spring_after_ATR_compression_ratio.detector import (
    spring_after_ATR_compression_ratio_detector,
)

DetectorFn = Callable[[pd.DataFrame, Dict], pd.DataFrame]


def baseline_detector(df: pd.DataFrame, cfg: Dict) -> pd.DataFrame:
    if "symbol" in df.columns and not df["symbol"].isna().all():
        symbol = str(df["symbol"].iloc[0])
    else:
        symbol = str(cfg.get("symbol", "UNKNOWN"))
    return run_baseline_structural(df, symbol, None)


DETECTORS: Dict[str, DetectorFn] = {
    "baseline": baseline_detector,
    "spring_after_sc": spring_after_sc_detector,
    "spring_after_ATR_compression_ratio": spring_after_ATR_compression_ratio_detector,
}
