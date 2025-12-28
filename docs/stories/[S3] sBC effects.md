
WINDSURF STORY — Add BC Regime-Effect Benchmark (No New Detector)

NON-NEGOTIABLE RULES
	1.	Do NOT modify detectors
	•	No changes to detectors.py
	•	No new detector modules
	2.	Do NOT change event definitions
	•	BC remains exactly as currently detected
	3.	Do NOT change existing outputs
	•	Existing CSVs must remain byte-for-byte compatible
	4.	Add analysis only
	•	This is post-processing, not detection

⸻

Objective

Add a BC-conditioned evaluation that measures whether Buying Climax (BC) degrades bullish edge and increases downside risk, without treating BC as a trade signal.

Produce a new output artifact:

bc_effect_summary.csv


⸻

Files You May Change (ONLY THESE)

harness/
├── eval.py
├── run.py

No other files may be edited.

⸻

Step 1 — Add BC Evaluator to eval.py

Add a new function

def evaluate_bc_effect(
    forward_df: pd.DataFrame,
    forward_windows: list[int],
) -> pd.DataFrame:
    """
    Evaluate regime impact of BC by comparing forward returns
    after BC vs non-BC baseline.
    Returns probability-shift metrics, not trade PnL.
    """

Required behavior

For each window in forward_windows:
	1.	BC cohort

bc = forward_df[forward_df["event"] == "BC"]

	2.	Baseline cohort

baseline = forward_df[forward_df["event"] != "BC"]

	3.	Compute the following metrics:

Column	Definition
window	forward window (e.g. 20, 40)
count_bc	number of BC events
count_baseline	number of non-BC rows
median_bc	median forward return after BC
median_baseline	median forward return baseline
median_delta	median_bc − median_baseline
win_rate_bc	mean(fwd > 0) after BC
win_rate_baseline	mean(fwd > 0) baseline
win_rate_delta	win_rate_bc − win_rate_baseline
p5_bc	5th percentile forward return after BC
p5_baseline	baseline p5
p5_delta	p5_bc − p5_baseline

	4.	Return one row per window as a DataFrame.

Notes
	•	Do not introduce statistical tests yet
	•	Do not normalize or rescale
	•	Missing data should produce NaN, not errors

⸻

Step 2 — Wire BC Evaluation in run.py

Import the new evaluator

from eval import evaluate_bc_effect

After existing summaries are built

Locate where forward_df already exists (after reading forward_returns.csv).

Add:

bc_effect_df = evaluate_bc_effect(
    forward_df,
    forward_windows
)

bc_effect_df.to_csv(
    output_path / "bc_effect_summary.csv",
    index=False
)

That is the only wiring change.

⸻

Step 3 — Outputs (Expected)

After a run, the directory will now include:

outputs/
├── events.csv
├── forward_returns.csv
├── summary_by_detector.csv
├── comparison.csv
└── bc_effect_summary.csv   ← NEW

Example rows:

window,count_bc,median_delta,win_rate_delta,p5_delta
20,742,-0.018,-0.22,-0.09
40,742,-0.031,-0.27,-0.14

These numbers validate BC as a regime-risk signal, not a trade.

⸻

Acceptance Criteria (Stop Rule)

BC is validated if any two of the following hold:
	•	median_delta < 0
	•	win_rate_delta < 0
	•	p5_delta < 0

If not → BC is discarded from the regime layer.

No tuning. No retries.

⸻

Explicitly Out of Scope
	•	New detectors
	•	BC parameter tuning
	•	Short-selling logic
	•	Sequencing (BC→SOW)
	•	LLM integration
	•	Regime classifier (comes later)

⸻

Why This Is Correct
	•	Keeps detection pure
	•	Measures BC on the dimension it actually operates on
	•	Produces LLM-ready regime evidence
	•	Prevents SPRING-style over-optimization

⸻
