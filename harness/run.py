from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd
from tqdm import tqdm

from harness import io as _io
from harness.detectors import DETECTORS, DetectorFn
from harness.eval import (
    add_forward_returns,
    build_comparison_table,
    evaluate_bc_effect,
    evaluate_event_effect,
    evaluate_sos_after_bc_effect,
    summarize_forward_returns,
)

from concurrent.futures import ProcessPoolExecutor, as_completed
from itertools import repeat


def _resolve_detectors(requested: List[str]) -> List[Tuple[str, DetectorFn]]:
    resolved: List[Tuple[str, DetectorFn]] = []
    for name in requested:
        fn = DETECTORS.get(name)
        if fn is None:
            raise ValueError(f"Detector '{name}' not found. Available: {list(DETECTORS)}")
        resolved.append((name, fn))
    return resolved


def _flush_buffers(
    events_buffer: List[pd.DataFrame],
    forward_buffer: List[pd.DataFrame],
    events_path: Path,
    forward_path: Path,
) -> None:
    if events_buffer:
        _io.append_to_csv(pd.concat(events_buffer, ignore_index=True), events_path)
    if forward_buffer:
        _io.append_to_csv(pd.concat(forward_buffer, ignore_index=True), forward_path)


def _process_symbol(
    symbol: str,
    ohlcv_path: str,
    lookback_days: int,
    cfg: dict,
    detector_names: List[str],
):
    from harness import io as _io
    from harness.detectors import DETECTORS
    from harness.eval import add_forward_returns

    df = _io.read_symbol_data(symbol, ohlcv_path, lookback_days)
    if df is None or df.empty:
        return symbol, 0.0, [], []

    detectors = [(name, DETECTORS[name]) for name in detector_names]

    events_out = []
    forward_out = []
    forward_windows = cfg.get("forward_windows", [5, 10, 20, 40])
    years_covered = _io.compute_years_covered(df)

    for detector_name, detector_fn in detectors:
        events = detector_fn(df, cfg)
        if events.empty:
            continue

        events["detector"] = detector_name
        forward = add_forward_returns(events, df, forward_windows)
        forward["detector"] = detector_name

        events_out.append(events)
        forward_out.append(forward)

    return symbol, years_covered, events_out, forward_out


def main() -> None:
    config_path = Path(__file__).parent / "config.yaml"
    cfg = _io.load_config(config_path)

    repo_root = Path(__file__).resolve().parents[1]
    ohlcv_path = cfg.get("ohlcv_path", "data/ohlcv_parquet")
    if not Path(ohlcv_path).is_absolute():
        ohlcv_path = str(repo_root / ohlcv_path)

    output_path_value = cfg.get("output_path", "outputs")
    if not Path(output_path_value).is_absolute():
        output_path_value = str(repo_root / output_path_value)
    output_path = _io.ensure_output_path(output_path_value)
    lookback_days = int(cfg.get("lookback_days", 0))
    forward_windows = cfg.get("forward_windows", [5, 10, 20, 40])
    sos_after_bc_lookback_days = int(cfg.get("sos_after_bc_lookback_days", 60))
    max_workers = int(cfg.get("workers", 8))

    detectors = _resolve_detectors(cfg.get("detectors", ["baseline", "variant"]))
    symbols = _io.list_symbols(ohlcv_path)

    if not symbols:
        print(f"No symbols found under {ohlcv_path}")
        sys.exit(0)

    # ------------------------------------------------------------------
    # Build per-detector output paths
    # ------------------------------------------------------------------
    paths: Dict[str, Dict[str, Path]] = {}
    for detector_name, _ in detectors:
        paths[detector_name] = {
            "events": output_path / f"{detector_name}_events.csv",
            "forward": output_path / f"{detector_name}_forward_returns.csv",
            "summary": output_path / f"{detector_name}_summary_by_detector.csv",
            "comparison": output_path / f"{detector_name}_comparison.csv",
        }
        for p in paths[detector_name].values():
            if p.exists():
                p.unlink()

    # ------------------------------------------------------------------
    # Baseline sanity check (unchanged behavior)
    # ------------------------------------------------------------------
    baseline_entry = next((fn for name, fn in detectors if name == "baseline"), None)
    sample_symbol = symbols[0]
    sample_df = _io.read_symbol_data(sample_symbol, ohlcv_path, lookback_days)
    if baseline_entry and sample_df is not None and not sample_df.empty:
        sample_events = baseline_entry(sample_df, cfg)
        unique_events = sorted(sample_events["event"].dropna().unique().tolist()) if not sample_events.empty else []
        if not sample_events.empty:
            event_dates = pd.to_datetime(sample_events["date"], errors="coerce")
            date_min = event_dates.min().date() if event_dates.notna().any() else ""
            date_max = event_dates.max().date() if event_dates.notna().any() else ""
        else:
            date_min = ""
            date_max = ""
        print(
            f"[baseline sanity] symbol={sample_symbol} events={len(sample_events)} "
            f"types={unique_events} range={date_min}->{date_max}"
        )

    # ------------------------------------------------------------------
    # Per-detector buffers
    # ------------------------------------------------------------------
    events_buffers: Dict[str, List[pd.DataFrame]] = {name: [] for name, _ in detectors}
    forward_buffers: Dict[str, List[pd.DataFrame]] = {name: [] for name, _ in detectors}

    coverage_years = 0.0
    flush_every = 25

    detector_names = [name for name, _ in detectors]

    if max_workers <= 1:
        for idx, symbol in enumerate(symbols, start=1):
            df = _io.read_symbol_data(symbol, ohlcv_path, lookback_days)
            if df is None or df.empty:
                continue

            coverage_years += _io.compute_years_covered(df)

            for detector_name, detector_fn in detectors:
                events = detector_fn(df, cfg)
                if events.empty:
                    continue

                events["detector"] = detector_name
                forward = add_forward_returns(events, df, forward_windows)
                forward["detector"] = detector_name

                events_buffers[detector_name].append(events)
                forward_buffers[detector_name].append(forward)

            if idx % flush_every == 0:
                for detector_name, _ in detectors:
                    _flush_buffers(
                        events_buffers[detector_name],
                        forward_buffers[detector_name],
                        paths[detector_name]["events"],
                        paths[detector_name]["forward"],
                    )
                    events_buffers[detector_name].clear()
                    forward_buffers[detector_name].clear()
                print(f"Processed {idx}/{len(symbols)} symbols")
    else:
        processed = 0
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(
                    _process_symbol,
                    symbol,
                    ohlcv_path,
                    lookback_days,
                    cfg,
                    detector_names,
                )
                for symbol in symbols
            ]

            with tqdm(total=len(futures), desc="Processing symbols", unit="symbol") as pbar:
                for fut in as_completed(futures):
                    symbol, years_covered, events_list, forward_list = fut.result()
                    pbar.update(1)

                    processed += 1
                    coverage_years += years_covered

                    if not events_list and not forward_list:
                        continue

                    for events in events_list:
                        events_buffers[events["detector"].iloc[0]].append(events)

                    for forward in forward_list:
                        forward_buffers[forward["detector"].iloc[0]].append(forward)

                    if processed % flush_every == 0:
                        for detector_name, _ in detectors:
                            _flush_buffers(
                                events_buffers[detector_name],
                                forward_buffers[detector_name],
                                paths[detector_name]["events"],
                                paths[detector_name]["forward"],
                            )
                            events_buffers[detector_name].clear()
                            forward_buffers[detector_name].clear()
                        print(f"Processed {processed}/{len(symbols)} symbols")

    # Final flush
    for detector_name, _ in detectors:
        _flush_buffers(
            events_buffers[detector_name],
            forward_buffers[detector_name],
            paths[detector_name]["events"],
            paths[detector_name]["forward"],
        )

    # ------------------------------------------------------------------
    # Summaries per detector
    # ------------------------------------------------------------------
    baseline_forward_df = None
    for detector_name, _ in detectors:
        events_path = paths[detector_name]["events"]
        forward_path = paths[detector_name]["forward"]
        summary_path = paths[detector_name]["summary"]
        comparison_path = paths[detector_name]["comparison"]

        if not forward_path.exists():
            continue

        forward_df = pd.read_csv(forward_path, parse_dates=["date"])
        if detector_name == "baseline":
            baseline_forward_df = forward_df
        summary_df = summarize_forward_returns(forward_df, coverage_years)
        summary_df.to_csv(summary_path, index=False)

        comparison_df = build_comparison_table(summary_df)
        comparison_df.to_csv(comparison_path, index=False)

    if baseline_forward_df is not None:
        bc_effect_df = evaluate_bc_effect(baseline_forward_df, forward_windows)
        bc_effect_df.to_csv(output_path / "bc_effect_summary.csv", index=False)

        ar_effect_df = evaluate_event_effect(baseline_forward_df, forward_windows, "AR")
        ar_top_effect_df = evaluate_event_effect(baseline_forward_df, forward_windows, "AR_TOP")
        sow_effect_df = evaluate_event_effect(baseline_forward_df, forward_windows, "SOW")
        sos_effect_df = evaluate_event_effect(baseline_forward_df, forward_windows, "SOS")
        sos_after_bc_effect_df = evaluate_sos_after_bc_effect(
            baseline_forward_df, forward_windows, sos_after_bc_lookback_days
        )

        ar_effect_df.to_csv(output_path / "ar_effect_summary.csv", index=False)
        ar_top_effect_df.to_csv(output_path / "ar_top_effect_summary.csv", index=False)
        sow_effect_df.to_csv(output_path / "sow_effect_summary.csv", index=False)
        sos_effect_df.to_csv(output_path / "sos_effect_summary.csv", index=False)
        sos_after_bc_effect_df.to_csv(output_path / "sos_after_bc_effect_summary.csv", index=False)

        combined = pd.concat(
            [ar_effect_df, ar_top_effect_df, sow_effect_df, sos_effect_df, sos_after_bc_effect_df],
            ignore_index=True,
            sort=False,
        )
        combined.to_csv(output_path / "event_effects_summary.csv", index=False)

    print(f"Processed {len(symbols)} symbols. Outputs written to {output_path}")


if __name__ == "__main__":
    main()
