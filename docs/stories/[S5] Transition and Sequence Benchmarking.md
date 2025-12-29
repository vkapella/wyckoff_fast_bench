WINDSURF STORY

Title: Wyckoff Regime & Sequence Transition Benchmarking (Non-Intrusive Extension)

Objective

Extend wyckoff_fast_bench to evaluate whether Wyckoff-defined event sequences and regime transitions materially change forward return distributions, without modifying:
	•	Structural Wyckoff detection logic
	•	Existing event definitions
	•	Existing event-level benchmarks

This story explicitly answers:
	1.	Do regime transitions carry more edge than static regimes?
	2.	Do event sequences outperform isolated events?
	3.	Does prior regime context materially alter event impact (SOS / SOW)?
	4.	Can all of the above be measured without altering detection code?

⸻

Non-Goals (Hard Constraints)
	•	❌ No changes to baseline/structural.py
	•	❌ No new Wyckoff semantics
	•	❌ No new TA indicators
	•	❌ No production trading rules

This is pure benchmarking.

⸻

High-Level Design

We introduce three additive benchmark layers that consume existing outputs:

existing events + regimes
        ↓
transition labeling
        ↓
sequence labeling
        ↓
context-conditioned event analysis

Each layer:
	•	Reads existing CSVs
	•	Emits new CSVs
	•	Uses the same eval.py forward-return machinery

⸻

Files to Add (Minimal Surface Area)

1. harness/transition_labels.py (NEW)

Purpose: Label regime transitions without redefining regimes.

# transition_labels.py
def label_regime_transitions(regime_df):
    """
    Input: per-symbol daily regime labels
    Output: sparse transition events:
      - ACCUMULATION→MARKUP
      - MARKUP→DISTRIBUTION
      - DISTRIBUTION→MARKDOWN
      - MARKDOWN→ACCUMULATION
    """

Rules:
	•	Transition emitted only on first bar of new regime
	•	Ignore UNKNOWN→X transitions
	•	Enforce minimum prior regime duration (default: 5 bars)

Output:

symbol, date, transition, prior_regime, new_regime


⸻

2. harness/sequence_labels.py (NEW)

Purpose: Detect event sequences from existing event streams.

# sequence_labels.py
def label_event_sequences(events_df, max_gap=30):
    """
    Emits sequence completion events when ordered patterns occur
    within a rolling window.
    """

Sequences to detect:

Sequence ID	Ordered Events
SEQ_ACCUM_BREAKOUT	SC → AR → SPRING → SOS
SEQ_DISTRIBUTION_TOP	BC → AR_TOP
SEQ_MARKDOWN_START	BC → AR_TOP → SOW
SEQ_FAILED_ACCUM	SC → AR → SPRING (no SOS within window)
SEQ_RECOVERY	SOW → SC

Rules:
	•	Order must be preserved
	•	All events within max_gap bars
	•	Emit only at final event
	•	One sequence per cycle

Output:

symbol, date, sequence_id


⸻

3. harness/contextual_event_eval.py (NEW)

Purpose: Evaluate events conditioned on prior regime.

# contextual_event_eval.py
def attach_prior_regime(events_df, regime_df, lookback=1):
    """
    Adds prior_regime column to each event.
    """

Example splits:
	•	SOS_after_ACCUMULATION
	•	SOS_after_MARKUP
	•	SOW_after_DISTRIBUTION
	•	SOW_after_MARKDOWN

Output:

symbol, date, event, prior_regime


⸻

Harness Integration (Minimal Change)

Modify run.py ONLY to:
	1.	Load baseline outputs
	2.	Call new labelers
	3.	Reuse existing eval.py

No detector registry changes.
No config breakage.

# run.py (additive)
from harness.transition_labels import label_regime_transitions
from harness.sequence_labels import label_event_sequences
from harness.contextual_event_eval import attach_prior_regime

Each new benchmark writes to:

outputs/007_transition_bench/
outputs/008_sequence_bench/
outputs/009_contextual_event_bench/


⸻

Evaluation Metrics (Unchanged)

Reuse existing metrics:
	•	median forward return (5/10/20/40)
	•	win rate
	•	p5 (tail risk)
	•	event density
	•	stability delta

This ensures direct comparability with prior benchmarks.

⸻

Acceptance Criteria

✔ Structural detection unchanged
✔ Regime transition CSV produced
✔ Sequence CSV produced
✔ Context-split SOS / SOW CSVs produced
✔ Summary tables comparable to prior benchmarks
✔ Deterministic, reproducible

⸻

