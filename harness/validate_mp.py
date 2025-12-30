from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from itertools import repeat
from pathlib import Path

import pandas as pd

from harness import io as _io
from harness.run import _process_symbol


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    config_path = repo_root / "config" / "run_config.yaml"
    if not config_path.exists():
        config_path = Path(__file__).parent / "config.yaml"
    cfg = _io.load_config(config_path)

    ohlcv_path = cfg.get("ohlcv_path", "data/ohlcv_parquet")
    if not Path(ohlcv_path).is_absolute():
        ohlcv_path = str(repo_root / ohlcv_path)

    lookback_days = int(cfg.get("lookback_days", 0))
    detector_names = list(cfg.get("detectors", ["baseline", "variant"]))

    symbols = _io.list_symbols(ohlcv_path)[:20]

    serial = [_process_symbol(s, ohlcv_path, lookback_days, cfg, detector_names) for s in symbols]

    with ProcessPoolExecutor(max_workers=2) as executor:
        parallel = list(
            executor.map(
                _process_symbol,
                symbols,
                repeat(ohlcv_path),
                repeat(lookback_days),
                repeat(cfg),
                repeat(detector_names),
                chunksize=5,
            )
        )

    assert [x[0] for x in serial] == [x[0] for x in parallel]
    assert [x[1] for x in serial] == [x[1] for x in parallel]

    for (sym_s, _, ev_s, fwd_s), (sym_p, _, ev_p, fwd_p) in zip(serial, parallel):
        assert sym_s == sym_p

        ev_s_df = (
            pd.concat(ev_s, ignore_index=True)
            if ev_s
            else pd.DataFrame(columns=["symbol", "date", "event", "score", "detector"])
        )
        ev_p_df = (
            pd.concat(ev_p, ignore_index=True)
            if ev_p
            else pd.DataFrame(columns=["symbol", "date", "event", "score", "detector"])
        )

        fwd_s_df = (
            pd.concat(fwd_s, ignore_index=True)
            if fwd_s
            else pd.DataFrame(columns=["symbol", "date", "event", "score", "detector"])
        )
        fwd_p_df = (
            pd.concat(fwd_p, ignore_index=True)
            if fwd_p
            else pd.DataFrame(columns=["symbol", "date", "event", "score", "detector"])
        )

        if not ev_s_df.empty or not ev_p_df.empty:
            ev_s_df = ev_s_df.sort_values(["detector", "date", "event", "score"]).reset_index(drop=True)
            ev_p_df = ev_p_df.sort_values(["detector", "date", "event", "score"]).reset_index(drop=True)
            pd.testing.assert_frame_equal(ev_s_df, ev_p_df, check_like=False)

        if not fwd_s_df.empty or not fwd_p_df.empty:
            fwd_s_df = fwd_s_df.sort_values(["detector", "date", "event"]).reset_index(drop=True)
            fwd_p_df = fwd_p_df.sort_values(["detector", "date", "event"]).reset_index(drop=True)
            pd.testing.assert_frame_equal(fwd_s_df, fwd_p_df, check_like=False)

    print("OK: multiprocessing symbol worker matches serial for first 20 symbols")


if __name__ == "__main__":
    main()
