# Wyckoff Fast Bench

Minimal research harness to benchmark Wyckoff-style event detectors over a large symbol universe without loading everything into memory.

The baseline detector is the handwritten structural Wyckoff logic in `baseline/` and is treated as authoritative; Fast Bench only adapts it for streaming, not reinterpretation.

## What it answers
- Which detector surfaces more stable / higher-quality events (SPRING, BC).
- Event density per symbol-year and forward performance (+5/+10/+20/+40 bars).
- Tail risk (5th percentile of fwd_20) and stability (first half vs second half median fwd_20).
- One comparison table (`outputs/comparison.csv`) to decide whether a variant survives.

## What it is not
- No dashboards, APIs, notebooks, or database integrations.
- Not a phase classifier or production trading system; purely research and repeatable stats.

## Data contract
- Input: Parquet partitions at `data/ohlcv_parquet/symbol=XXXX/*.parquet` with columns `symbol, date, open, high, low, close, volume`.
- Output CSVs written to `output_path` (from config), with one set per detector (e.g. `baseline_events.csv`, `baseline_forward_returns.csv`, etc.).
- Deterministic: same Parquet + same config => identical outputs; sorting by symbol/date throughout.

## Quickstart
1) Install deps (example): `python -m pip install pandas numpy pyarrow pyyaml`.
2) Adjust `harness/config.yaml` if needed (paths, lookback_days, detector list).
3) Run: `python -m harness.run`.
4) Inspect `output_path` for the head-to-head readout.

## Baseline detector contract
- Baseline logic is `baseline/structural.py` and is called directly by the adapter via `baseline/adapter.py:run_baseline_structural`.
- Baseline files are treated as immutable research artifacts; re-benchmark after any baseline change via `python -m harness.run`.

## Config knobs (`harness/config.yaml`)
- `ohlcv_path`: Parquet root (default `data/ohlcv_parquet`).
- `output_path`: Where CSVs land (default `outputs`).
- `lookback_days`: Limit history per symbol (default 730).
- `forward_windows`: Forward horizons (default `[5, 10, 20, 40]`).
- `detectors`: Ordered list of detectors to run (default `["baseline", "variant"]`).

## Adding a detector safely
1) Implement `detect(df, cfg) -> DataFrame` in `harness/detectors.py` returning sparse events (`symbol, date, event, score`).
2) Add it to the `DETECTORS` dict.
3) List it in `harness/config.yaml` under `detectors`.
Keep the change minimal and deterministic; reuse the existing feature prep helper where possible.

## How to run the tool
source .venv/bin/activate
python3 -m harness.run

## How to combine files
output_path: outputs/006_Add_AR_AR_TOP_SOW_SOS_and_SOS-after-BC Benchmarks_evaluation
DIR="outputs/006_Add_AR_AR_TOP_SOW_SOS_and_SOS-after-BC Benchmarks_evaluation"

(head -n 1 "$DIR"/*effect_summary.csv | head -n 1 && \
 tail -n +2 -q "$DIR"/*effect_summary.csv) \
> "$DIR/combined_effect_summary.csv"