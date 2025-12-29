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
from harness.contextual_event_eval import attach_prior_regime
from harness.regime import classify_regime_daily
from harness.regime_eval import add_forward_returns_daily, pairwise_vs_baseline, summarize_regimes
from harness.sequence_labels import label_event_sequences
from harness.transition_labels import label_regime_transitions

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


def _read_csv_or_empty(path: Path, columns: List[str]) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=columns)
    df = pd.read_csv(path, parse_dates=["date"] if "date" in columns else None)
    if df.empty:
        return pd.DataFrame(columns=columns)
    return df[columns].copy()


def _build_forward_returns_for_events(
    events_df: pd.DataFrame,
    symbols: List[str],
    ohlcv_path: str,
    lookback_days: int,
    forward_windows: List[int],
) -> pd.DataFrame:
    if events_df is None or events_df.empty:
        base_columns = list(events_df.columns) if events_df is not None else []
        return pd.DataFrame(columns=base_columns + [f"fwd_{w}" for w in forward_windows])

    events_by_symbol = {
        symbol: group.copy() for symbol, group in events_df.groupby("symbol", sort=False)
    }
    forward_parts: List[pd.DataFrame] = []

    for symbol in symbols:
        symbol_events = events_by_symbol.get(symbol)
        if symbol_events is None or symbol_events.empty:
            continue

        price_df = _io.read_symbol_data(symbol, ohlcv_path, lookback_days)
        if price_df is None or price_df.empty:
            continue

        forward_parts.append(add_forward_returns(symbol_events, price_df, forward_windows))

    if not forward_parts:
        return pd.DataFrame(columns=list(events_df.columns) + [f"fwd_{w}" for w in forward_windows])

    return pd.concat(forward_parts, ignore_index=True)


def _write_benchmark_outputs(
    events_df: pd.DataFrame,
    eval_df: pd.DataFrame,
    output_dir: Path,
    prefix: str,
    symbols: List[str],
    ohlcv_path: str,
    lookback_days: int,
    forward_windows: List[int],
    coverage_years: float,
) -> None:
    events_path = output_dir / f"{prefix}_events.csv"
    forward_path = output_dir / f"{prefix}_forward_returns.csv"
    summary_path = output_dir / f"{prefix}_summary.csv"
    comparison_path = output_dir / f"{prefix}_comparison.csv"

    for p in [events_path, forward_path, summary_path, comparison_path]:
        if p.exists():
            p.unlink()

    events_df.to_csv(events_path, index=False)

    forward_df = _build_forward_returns_for_events(
        eval_df, symbols, ohlcv_path, lookback_days, forward_windows
    )
    forward_df.to_csv(forward_path, index=False)

    summary_df = summarize_forward_returns(forward_df, coverage_years)
    summary_df.to_csv(summary_path, index=False)

    comparison_df = build_comparison_table(summary_df)
    comparison_df.to_csv(comparison_path, index=False)


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
    transition_output_value = cfg.get("transition_output_path", "outputs/007_transition_bench")
    if not Path(transition_output_value).is_absolute():
        transition_output_value = str(repo_root / transition_output_value)
    transition_output_path = _io.ensure_output_path(transition_output_value)
    sequence_output_value = cfg.get("sequence_output_path", "outputs/008_sequence_bench")
    if not Path(sequence_output_value).is_absolute():
        sequence_output_value = str(repo_root / sequence_output_value)
    sequence_output_path = _io.ensure_output_path(sequence_output_value)
    contextual_output_value = cfg.get("contextual_output_path", "outputs/009_contextual_event_bench")
    if not Path(contextual_output_value).is_absolute():
        contextual_output_value = str(repo_root / contextual_output_value)
    contextual_output_path = _io.ensure_output_path(contextual_output_value)
    lookback_days = int(cfg.get("lookback_days", 0))
    forward_windows = cfg.get("forward_windows", [5, 10, 20, 40])
    sos_after_bc_lookback_days = int(cfg.get("sos_after_bc_lookback_days", 60))
    transition_min_prior_bars = int(cfg.get("transition_min_prior_bars", 5))
    sequence_max_gap = int(cfg.get("sequence_max_gap", 30))
    contextual_lookback = int(cfg.get("contextual_lookback", 1))
    max_workers = int(cfg.get("workers", 8))
    regime_benchmark = bool(cfg.get("regime_benchmark", True))
    regime_detector = str(cfg.get("regime_detector", "baseline"))
    regime_output_prefix = str(cfg.get("regime_output_prefix", "regime"))
    regime_baseline_regime = str(cfg.get("regime_baseline_regime", "UNKNOWN"))

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

    if regime_benchmark:
        events_path = output_path / f"{regime_detector}_events.csv"
        events_df = None
        if events_path.exists():
            events_df = pd.read_csv(events_path, parse_dates=["date"])
        else:
            fallback_path = output_path / "events.csv"
            if fallback_path.exists():
                events_df = pd.read_csv(fallback_path, parse_dates=["date"])
                if "detector" in events_df.columns:
                    events_df = events_df[events_df["detector"] == regime_detector]

        if events_df is None:
            print(f"[regime] No events file found for detector '{regime_detector}'. Skipping regime benchmark.")
        else:
            events_df = events_df[["symbol", "date", "event"]].copy() if not events_df.empty else events_df
            events_by_symbol = {
                symbol: group[["date", "event"]].copy()
                for symbol, group in events_df.groupby("symbol", sort=False)
            }

            regime_daily_path = output_path / f"{regime_detector}_{regime_output_prefix}s_daily.csv"
            regime_summary_path = output_path / f"{regime_detector}_{regime_output_prefix}_summary.csv"
            regime_pairwise_path = output_path / f"{regime_detector}_{regime_output_prefix}_pairwise.csv"

            for p in [regime_daily_path, regime_summary_path, regime_pairwise_path]:
                if p.exists():
                    p.unlink()

            regime_daily_buffer: List[pd.DataFrame] = []
            merged_buffers: List[pd.DataFrame] = []

            for idx, symbol in enumerate(symbols, start=1):
                price_df = _io.read_symbol_data(symbol, ohlcv_path, lookback_days)
                if price_df is None or price_df.empty:
                    continue

                symbol_events = events_by_symbol.get(symbol, pd.DataFrame(columns=["date", "event"]))
                regime_daily = classify_regime_daily(price_df, symbol_events)
                daily_fwd = add_forward_returns_daily(price_df, forward_windows)

                regime_daily_buffer.append(regime_daily)
                merged_buffers.append(
                    regime_daily.merge(daily_fwd, on=["symbol", "date"], how="inner")
                )

                if idx % flush_every == 0:
                    _io.append_to_csv(pd.concat(regime_daily_buffer, ignore_index=True), regime_daily_path)
                    regime_daily_buffer.clear()

            if regime_daily_buffer:
                _io.append_to_csv(pd.concat(regime_daily_buffer, ignore_index=True), regime_daily_path)

            if merged_buffers:
                merged_all = pd.concat(merged_buffers, ignore_index=True)
                regime_daily_all = merged_all[["symbol", "date", "regime"]]
                daily_fwd_all = merged_all.drop(columns=["regime"])
                regime_summary_df = summarize_regimes(regime_daily_all, daily_fwd_all)
                regime_summary_df.to_csv(regime_summary_path, index=False)

                pairwise_df = pairwise_vs_baseline(regime_summary_df, regime_baseline_regime)
                pairwise_df.to_csv(regime_pairwise_path, index=False)

    # ------------------------------------------------------------------
    # Transition/sequence/context benchmarks (additive)
    # ------------------------------------------------------------------
    baseline_events_path = output_path / "baseline_events.csv"
    baseline_events_df = _read_csv_or_empty(
        baseline_events_path, ["symbol", "date", "event"]
    )
    if not baseline_events_path.exists():
        print("[extra benchmarks] baseline events file missing; outputs will be empty.")

    regime_daily_path = output_path / f"{regime_detector}_{regime_output_prefix}s_daily.csv"
    regime_daily_df = _read_csv_or_empty(
        regime_daily_path, ["symbol", "date", "regime"]
    )
    if not regime_daily_path.exists():
        print("[extra benchmarks] regime daily file missing; outputs will be empty.")

    transition_events_df = label_regime_transitions(
        regime_daily_df, transition_min_prior_bars
    )
    transition_eval_df = transition_events_df.copy()
    if transition_eval_df.empty:
        transition_eval_df = pd.DataFrame(
            columns=["symbol", "date", "event", "detector"]
        )
    else:
        transition_eval_df["event"] = transition_eval_df["transition"]
        transition_eval_df["detector"] = "transition"

    _write_benchmark_outputs(
        transition_events_df,
        transition_eval_df,
        transition_output_path,
        "transition",
        symbols,
        ohlcv_path,
        lookback_days,
        forward_windows,
        coverage_years,
    )

    sequence_events_df = label_event_sequences(baseline_events_df, sequence_max_gap)
    sequence_eval_df = sequence_events_df.copy()
    if sequence_eval_df.empty:
        sequence_eval_df = pd.DataFrame(
            columns=["symbol", "date", "event", "detector"]
        )
    else:
        sequence_eval_df["event"] = sequence_eval_df["sequence_id"]
        sequence_eval_df["detector"] = "sequence"

    _write_benchmark_outputs(
        sequence_events_df,
        sequence_eval_df,
        sequence_output_path,
        "sequence",
        symbols,
        ohlcv_path,
        lookback_days,
        forward_windows,
        coverage_years,
    )

    contextual_events_df = attach_prior_regime(
        baseline_events_df, regime_daily_df, contextual_lookback
    )
    contextual_events_df = contextual_events_df[
        contextual_events_df["event"].isin(["SOS", "SOW"])
    ].copy()
    contextual_events_df = contextual_events_df.dropna(subset=["prior_regime"])
    if not contextual_events_df.empty:
        contextual_events_df["event"] = (
            contextual_events_df["event"].astype(str).str.upper()
        )
        contextual_events_df["prior_regime"] = (
            contextual_events_df["prior_regime"].astype(str).str.upper()
        )
        allowed_regimes = {"ACCUMULATION", "MARKUP", "DISTRIBUTION", "MARKDOWN"}
        contextual_events_df = contextual_events_df[
            contextual_events_df["prior_regime"].isin(allowed_regimes)
        ]
    contextual_events_df = contextual_events_df.reindex(
        columns=["symbol", "date", "event", "prior_regime"]
    )

    contextual_eval_df = contextual_events_df.copy()
    if contextual_eval_df.empty:
        contextual_eval_df = pd.DataFrame(
            columns=["symbol", "date", "event", "detector"]
        )
    else:
        contextual_eval_df["event"] = (
            contextual_eval_df["event"].astype(str)
            + "_after_"
            + contextual_eval_df["prior_regime"].astype(str)
        )
        contextual_eval_df["detector"] = "contextual_event"

    _write_benchmark_outputs(
        contextual_events_df,
        contextual_eval_df,
        contextual_output_path,
        "contextual",
        symbols,
        ohlcv_path,
        lookback_days,
        forward_windows,
        coverage_years,
    )

    print(f"Processed {len(symbols)} symbols. Outputs written to {output_path}")


if __name__ == "__main__":
    main()
