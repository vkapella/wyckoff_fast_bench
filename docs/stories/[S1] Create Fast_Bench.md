Below is a Windsurf / Codex SINGLE-FILE PROMPT you can paste verbatim into Windsurf, targeted at the new repo qyckoff_fast_bench (as you spelled it), assuming:
	•	Parquet OHLCV already exists at data/ohlcv_parquet/
	•	Data is partitioned by symbol=
	•	This repo is research-only
	•	Goal is 80% insight, 20% effort, not architectural perfection

This prompt is intentionally strict and minimal. It will produce a working Fast Bench you can iterate on immediately.

⸻

WINDSURF TASK — BUILD WYCKOFF FAST BENCH (80/20 VERSION)

Objective

Create a minimal, fast-to-iterate Wyckoff benchmarking harness that can be run against the entire symbol universe using an existing Parquet OHLCV dataset.

The system must:
	•	Compare two Wyckoff event detectors (baseline vs variant)
	•	Measure event density, forward returns, tail risk, and stability
	•	Run in streaming / batch mode (full universe safe)
	•	Produce one comparison table that tells us which idea survives

This is a research harness, not production code.

⸻

Non-Goals (Explicitly Do NOT Build)

Do NOT build:
	•	Plugin registries
	•	CLI frameworks (argparse is optional, not required)
	•	YAML schema validation
	•	Postgres access
	•	Docker integration
	•	Phase classification (A–E)
	•	Dashboards, APIs, or notebooks
	•	Options, dealer, or volatility metrics

If it is not required to statistically kill or validate a detector, it does not belong here.

⸻

Required Repository Structure

Create exactly this structure:

wyckoff_fast_bench/
├── run.py
├── config.yaml
├── detectors.py
├── eval.py
├── io.py
├── README.md
└── data/
└── ohlcv_parquet/
└── symbol=XXXX/
└── part.parquet

No additional top-level directories.

⸻

Data Contract (Non-Negotiable)

Input (Parquet)

Each symbol partition contains rows with:
	•	symbol (string)
	•	date (date)
	•	open (float)
	•	high (float)
	•	low (float)
	•	close (float)
	•	volume (float or int)

Output (All CSV, written to outputs/)
	1.	events.csv
	2.	forward_returns.csv
	3.	summary_by_detector.csv
	4.	comparison.csv

⸻

Detector Contract (Core Abstraction)

All detectors must be plain Python functions with this signature:

detect(df: pandas.DataFrame, cfg: dict) -> pandas.DataFrame

Where:
	•	df contains one symbol’s full OHLCV history
	•	Returned DataFrame is sparse events only

Required output columns:
	•	symbol
	•	date
	•	event (string, e.g. “SPRING”, “BC”)
	•	score (float, bounded 0–1 or 0–N)

No per-bar outputs. No signals. Events only.

⸻

Required Detectors (Minimum)

Implement exactly two detectors in detectors.py:

1. baseline_detector
	•	A simple Wyckoff-style heuristic
	•	Must detect at least:
	•	SPRING
	•	BC (Buying Climax)
	•	Use basic logic:
	•	range expansion
	•	volume vs rolling average
	•	close location in range

This detector is the control.

2. variant_detector
	•	Identical to baseline except for one intentional change
	•	Example changes:
	•	Different volume normalization
	•	Different support/resistance window
	•	Different close-location threshold

No multiple changes. One difference only.

⸻

Evaluation Logic (Where the Value Is)

In eval.py, compute:

Forward Returns

For every event:
	•	+5 bars
	•	+10 bars
	•	+20 bars
	•	+40 bars

Store:
	•	fwd_5
	•	fwd_10
	•	fwd_20
	•	fwd_40

⸻

Metrics to Compute (Only These)

For each detector × event type:
	1.	Event Density
	•	events per symbol per year
	2.	Median Forward Return
	•	median(fwd_20)
	3.	Win Rate
	•	% of fwd_20 > 0
	4.	Tail Risk
	•	5th percentile of fwd_20
	5.	Stability
	•	Difference in median(fwd_20) between:
	•	first half of time range
	•	second half of time range

⸻

Comparison Table (Primary Output)

Create comparison.csv with columns:
	•	detector
	•	event
	•	density
	•	median_fwd_20
	•	win_rate_20
	•	p5_fwd_20
	•	stability_delta

This table is the entire point of Fast Bench.

⸻

Execution Model (Critical)

In run.py:
	•	Discover symbols from data/ohlcv_parquet/
	•	Process one symbol at a time (or small batches)
	•	Never load the full universe into memory
	•	Append results incrementally to disk
	•	Print progress every N symbols

This must safely handle 8,000–15,000 symbols.

⸻

config.yaml (Simple Knobs Only)

Include only:
	•	ohlcv_path
	•	output_path
	•	lookback_days (default: 730)
	•	forward_windows: [5, 10, 20, 40]
	•	detectors: [“baseline”, “variant”]

No nested configs. No schemas.

⸻

README.md (Required)

Document:
	•	What Fast Bench is
	•	What questions it answers
	•	How to run it
	•	What NOT to use it for
	•	How to add a new detector safely

⸻

Determinism Requirements
	•	Same Parquet + same config = identical outputs
	•	No randomness unless explicitly seeded
	•	Stable sorting by symbol/date everywhere

⸻

Acceptance Criteria

The implementation is complete when:
	•	python run.py runs end-to-end
	•	It processes the full symbol universe without crashing
	•	comparison.csv is produced
	•	You can clearly say:
“Detector A is better / worse than Detector B, and why”

⸻

Execution Authorization

You are authorized to:
	•	Create all required files
	•	Read all Parquet data
	•	Implement detectors and evaluation logic
	•	Make reasonable assumptions where necessary
	•	Favor clarity and speed over abstraction

No further confirmation is required.

Proceed autonomously until complete.

⸻

End of Task