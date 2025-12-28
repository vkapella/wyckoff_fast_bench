
WINDSURF TASK — Externalize First Sequencing Variant (spring_after_sc) and Clean Detector Registry

CRITICAL SAFETY RULES (NON-NEGOTIABLE)
	1.	Do NOT modify baseline logic
	•	No edits to any files under baseline/
	2.	Do NOT change baseline detector behavior
	•	Baseline output must be identical before and after this task
	3.	Do NOT change output formats
	•	Events must still be symbol, date, event, score, detector
	4.	No algorithmic changes beyond what is explicitly specified
	•	This task is code relocation + one new variant only

If any of these are violated, the task has failed.

⸻

Objective
	1.	Remove the inline “variant” logic from the existing detector module
	2.	Create a clean, external detector module implementing the first real variation:

spring_after_sc


	3.	Store the new variant in:

wyckoff_fast_bench/spring_after_sc/


	4.	Register the new detector cleanly without cluttering the registry.

This establishes the permanent pattern for future variants.

⸻

Step 1 — Clean the Existing Detector Module

File: harness/detectors.py (or equivalent registry file)
	1.	Remove:
	•	Any inline heuristic / toy variant code
	•	Any _prepare_features, _detect, _score, or similar helpers used only for the old variant
	•	The old "variant" entry in DETECTORS
	2.	Keep:
	•	baseline_detector
	•	The detector interface (DetectorFn)
	•	The detector registry pattern

After cleanup, this file should:
	•	Contain no experimental logic
	•	Act strictly as a registry + thin adapters

⸻

Step 2 — Create the spring_after_sc Module Directory

Create the directory:

wyckoff_fast_bench/spring_after_sc/

Add the following files:

spring_after_sc/
├── __init__.py
└── detector.py


⸻

Step 3 — Implement spring_after_sc Detector

File: spring_after_sc/detector.py

Implement a detector that:
	1.	Calls the baseline detector
	•	Reuse baseline output; do NOT re-detect events
	2.	Filters SPRING events only
	3.	Emits a SPRING event only if:
	•	There exists at least one SC event
	•	Within a lookback window N prior bars
	4.	Preserves original SPRING score
	5.	Does not modify event dates, labels, or scoring logic

Initial parameters (hard-coded for v1)
	•	Lookback window: 60 trading days

Required function signature

def spring_after_sc_detector(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:

Expected behavior
	•	Input: one symbol’s OHLCV DataFrame
	•	Output: filtered events DataFrame
	•	Event name remains "SPRING"
	•	Detector name will be injected by the harness

⸻

Reference implementation logic (guidance, not prose)

Inside spring_after_sc_detector:
	1.	Call baseline detector:

baseline_events = run_baseline_structural(...)


	2.	Split events by type:
	•	Extract all SC events
	•	Extract all SPRING events
	3.	For each SPRING at date t:
	•	Keep it only if:

exists SC where:
  sc_date < t
  AND (t - sc_date) <= lookback_days


	4.	Return the filtered SPRING events as a DataFrame

No new events are created.

⸻

Step 4 — Register the New Detector

File: harness/detectors.py
	1.	Import the new detector:

from spring_after_sc.detector import spring_after_sc_detector


	2.	Register it:

DETECTORS = {
    "baseline": baseline_detector,
    "spring_after_sc": spring_after_sc_detector,
}



Do not register any other variants.

⸻

Step 5 — Sanity & Safety Checks (MANDATORY)

After implementation:
	1.	Run with detectors:

detectors:
  - baseline
  - spring_after_sc


	2.	Confirm:
	•	Baseline results are unchanged
	•	spring_after_sc emits fewer SPRING events
	•	No new event types appear
	•	No SC events are emitted by the variant
	•	Scores match baseline SPRING scores
	3.	Run with workers: 1 and workers: 8
	•	Results must match (ordering differences allowed)

⸻

Explicitly Out of Scope
	•	YAML parameterization of lookback window (future task)
	•	Phase filtering
	•	SOW inclusion
	•	Score reweighting
	•	Exit logic

⸻

Acceptance Criteria

This task is complete when:
	•	All experimental logic is removed from the detector registry file
	•	spring_after_sc exists as a clean, external module
	•	The variant produces sensible, reduced-density SPRING output
	•	Baseline remains frozen and untouched
	•	The codebase now has a clear, scalable pattern for future variants

⸻

End of Task

