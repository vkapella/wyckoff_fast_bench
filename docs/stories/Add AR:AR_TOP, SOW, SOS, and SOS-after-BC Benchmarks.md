B
Windsurf Story: Add AR/AR_TOP, SOW, SOS, and SOS-after-BC Benchmarks (One Pass)

Repo: wyckoff_fast_bench
Target modules: harness/eval.py, harness/run.py, harness/config.yaml
Do not modify detector logic.
Do not change event detection semantics.
Benchmarks must evaluate baseline forward returns only, regardless of which detectors are listed in config.

Background / Goal

We already validated BC using evaluate_bc_effect() and now want the same distribution-shift evaluation for:
	1.	AR and AR_TOP
	2.	SOW
	3.	SOS, and a conditional test SOS-after-BC (restore upside after BC)

All evaluations should answer:

“Does this event change the forward return distribution?”

and output CSVs similar to bc_effect_summary.csv.

⸻

Requirements

A) Add a generic event-effect evaluator

In harness/eval.py, implement a reusable function:

evaluate_event_effect(forward_df: pd.DataFrame, forward_windows: list[int], event_name: str) -> pd.DataFrame

It should replicate the BC table logic exactly, but for any event_name:

Output columns:
	•	window
	•	event (string, equals event_name)
	•	count_event
	•	count_baseline
	•	median_event
	•	median_baseline
	•	median_delta
	•	win_rate_event
	•	win_rate_baseline
	•	win_rate_delta
	•	p5_event
	•	p5_baseline
	•	p5_delta

Where:
	•	event_vals = forward_df.loc[forward_df["event"] == event_name, fwd_col].dropna()
	•	base_vals = forward_df.loc[forward_df["event"] != event_name, fwd_col].dropna()

Use the same definitions as BC:
	•	win rate is (vals > 0).mean()
	•	p5 is quantile(0.05)

Do not filter by detector inside this function.

Keep evaluate_bc_effect() unchanged (for backwards compatibility), but it can internally call evaluate_event_effect(..., "BC") if you want.

⸻

B) Add SOS-after-BC conditional benchmark

In harness/eval.py, add:

evaluate_sos_after_bc_effect(forward_df: pd.DataFrame, forward_windows: list[int], lookback_days: int) -> pd.DataFrame

Definition:
	•	This benchmark compares SOS that occur after a prior BC within the last lookback_days trading days for the same symbol, against a baseline cohort.

Implementation details:
	1.	Ensure date is datetime.
	2.	Work per symbol.
	3.	For each symbol, create a boolean mask sos_after_bc for rows where:
	•	row.event == “SOS”
	•	there exists at least one prior row where event == “BC”
	•	and (sos_date - bc_date).days <= lookback_days
	•	and bc_date < sos_date
	4.	Collect those SOS rows into sos_after_bc_df.

For the comparison cohort:
	•	Use BC-only cohort (recommended for “restore after BC” semantics), i.e.:
	•	base_df = forward_df[forward_df["event"] == "BC"]
	•	If BC-only is empty, fall back to event != "SOS" baseline, but only if necessary.

Then compute the same metrics per window as the generic evaluator, but with:
	•	event_vals derived from SOS-after-BC cohort
	•	base_vals derived from BC-only cohort

Output columns:
	•	window
	•	event = "SOS_AFTER_BC"
	•	lookback_days
	•	count_event
	•	count_baseline
	•	median_event
	•	median_baseline
	•	median_delta
	•	win_rate_event
	•	win_rate_baseline
	•	win_rate_delta
	•	p5_event
	•	p5_baseline
	•	p5_delta

Performance requirement:
	•	Must be efficient enough to run on ~8,000 symbols.
Avoid nested Python loops over rows. Prefer a per-symbol scan using sorted dates and a rolling “most recent BC date” state.

A simple efficient approach:
	•	For each symbol group sorted by date:
	•	maintain last_bc_date (updated when event == “BC”)
	•	for SOS rows: if last_bc_date is not None and (sos_date - last_bc_date).days <= lookback_days -> mark true

This approximates “most recent BC” and is adequate for the benchmark.

⸻

C) Wire all benchmarks into run.py (one pass, baseline only)

In harness/run.py:
	1.	Ensure you already capture baseline_forward_df as discussed previously and only evaluate event effects using that dataframe.
	2.	After processing detectors and writing all usual outputs, add a single benchmark section:

	•	Use baseline_forward_df (not per-detector).
	•	Compute:
	•	ar_effect = evaluate_event_effect(baseline_forward_df, forward_windows, "AR")
	•	ar_top_effect = evaluate_event_effect(..., "AR_TOP")
	•	sow_effect = evaluate_event_effect(..., "SOW")
	•	sos_effect = evaluate_event_effect(..., "SOS")
	•	sos_after_bc_effect = evaluate_sos_after_bc_effect(baseline_forward_df, forward_windows, lookback_days=sos_after_bc_lookback_days)

	3.	Write outputs to the run’s output_path:

	•	ar_effect_summary.csv
	•	ar_top_effect_summary.csv
	•	sow_effect_summary.csv
	•	sos_effect_summary.csv
	•	sos_after_bc_effect_summary.csv

	4.	Also write a combined file:

	•	event_effects_summary.csv

This should be a concatenation of:
	•	AR, AR_TOP, SOW, SOS outputs (from generic evaluator)
	•	SOS_AFTER_BC output (from conditional evaluator)

Add a column event in each so the combined file is easy to pivot.

Do not overwrite BC summary; leave BC benchmark intact.

⸻

D) Add config dial

In harness/config.yaml, add:
	•	sos_after_bc_lookback_days: 60

And in run.py, read it with a default of 60.

⸻

Acceptance Criteria / Validation

After running:

python3 -m harness.run

Verify:
	1.	Output directory contains:

	•	ar_effect_summary.csv
	•	ar_top_effect_summary.csv
	•	sow_effect_summary.csv
	•	sos_effect_summary.csv
	•	sos_after_bc_effect_summary.csv
	•	event_effects_summary.csv

	2.	Each file has rows for windows (5,10,20,40) and non-zero counts (unless truly absent).
	3.	SOS-after-BC should have:

	•	event = SOS_AFTER_BC
	•	lookback_days = 60 (or configured)
	•	count_event > 0 on the full universe run

	4.	No changes to detectors or event emission.

⸻

Implementation Notes / Guardrails
	•	Do not change CSV schemas for events.csv or forward_returns.csv.
	•	Do not change multiprocessing or parquet IO behavior.
	•	Keep changes minimal and localized.
	•	If baseline_forward_df is None (baseline not run), either:
	•	raise a clear error: “baseline detector required for event effect benchmarks”
	•	or skip benchmarks with a printed warning (prefer raising to avoid silent nonsense).

⸻

If you want, I can also provide a follow-on story to extend this into right-tail (p95/p99) suppression tests for AR/AR_TOP (range behavior), but the above is the correct first institutional pass.