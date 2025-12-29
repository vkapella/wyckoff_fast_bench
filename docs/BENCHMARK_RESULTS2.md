# BENCHMARK_RESULTS.md

## Wyckoff Benchmark Results (Fast Bench)

### Purpose

This document summarizes empirical findings from the Wyckoff benchmarking harness (`wyckoff_fast_bench`) and captures the validated role of key Wyckoff events and Wyckoff-defined regimes based on large-sample forward-return analysis.

The goal of this benchmark phase is **not** to produce trading rules. It is to determine:

- Which Wyckoff events and regimes have **statistically meaningful impact** on forward return distributions
- How those signals should be used downstream in **KapMan Trader** (rule layer vs LLM conditioning vs risk posture)

All results are based on:

- ~8,000+ symbols
- ~2 years of daily OHLCV data
- Deterministic event detection (baseline structural logic)
- Forward-return evaluation across multiple horizons

**Core principle:** Wyckoff events and regimes are evaluated as **regime modifiers**, not as standalone trade signals.

---

## Methodology Overview

### Detection

- Baseline Wyckoff detector: `structural.detect_structural_wyckoff`
- Events emitted (baseline): `SPRING, SC, AR, AR_TOP, BC, UT, SOS, SOW`
- Variants (when tested) refine filters only; they must not change event semantics.

### Evaluation

Forward returns computed at: **5, 10, 20, 40 trading days**

Primary metrics:

- **Median forward return**
- **Win rate** = P(fwd > 0)
- **p5** = 5th percentile (left-tail risk)
- For event effect tests: event distribution compared to **non-event baseline distribution** (or a specified reference set)

---

# Part A — Event Benchmarking

## A1) SPRING — Conclusions

### Summary

Baseline SPRING shows **positive forward edge** and improved distribution vs baseline, across windows.

Key observations:

- SPRING’s baseline form already carries edge.
- Hard-filter variants increased “precision” by reducing event count but did **not** improve expectancy enough to justify losing coverage/opportunity.

### Precision vs Recall: What the variants taught us

When we constrained SPRING (e.g., “SPRING after SC” or “ATR compression ratio” filters), we saw:

- Event density collapsed (large recall loss)
- Median forward return did not materially improve (often worsened)
- Tail risk behavior was not meaningfully better than baseline SPRING in proportion to the opportunity loss

**Conclusion:** Treat SPRING as a broadly emitted “bullish regime candidate” and let downstream context determine actionability.

### Recommended production usage (KapMan)

- Emit SPRING liberally (baseline structural logic)
- Carry into the decision layer:
  - SPRING score
  - time-since-SPRING
  - co-occurring / subsequent Wyckoff regime signals (BC, AR, SOS, SOW, etc.)
- Let higher layers decide:
  - whether it is actionable
  - sizing and timing
  - risk controls

---

## A2) BC (Buying Climax) — Conclusions

### Summary

BC is validated as a high-confidence **risk-off / distribution onset marker**.

BC shows:

- Median forward returns shift **down**
- Win rate drops materially
- Left-tail risk worsens (p5 becomes more negative)
- Effects strengthen with horizon

**BC is not a trade.** It is a regime/risk modifier.

### BC event effect results (Δ vs baseline)

BC effect summary (event vs non-BC reference distribution):

| Window | Count BC | Count Baseline | Median (BC) | Median (Baseline) | Median Δ | WinRate (BC) | WinRate (Baseline) | WinRate Δ | p5 (BC) | p5 (Baseline) | p5 Δ |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 5  | 6,505 | 29,598 | -0.00695 | -0.00249 | -0.00446 | 0.4175 | 0.4705 | -0.0530 | -0.2297 | -0.1780 | -0.0517 |
| 10 | 6,362 | 29,196 | -0.01016 |  0.00159 | -0.01175 | 0.4074 | 0.5131 | -0.1057 | -0.2795 | -0.2240 | -0.0555 |
| 20 | 6,058 | 28,605 | -0.00958 |  0.00247 | -0.01205 | 0.4338 | 0.5147 | -0.0809 | -0.3580 | -0.2883 | -0.0697 |
| 40 | 5,295 | 26,445 | -0.01679 |  0.00322 | -0.02002 | 0.4268 | 0.5132 | -0.0864 | -0.4663 | -0.3913 | -0.0750 |

### Recommended production usage (KapMan)

BC should directly influence:

- “Do we trust bullish setups right now?”
- tightening risk limits and exposure
- conditioning LLM decision-making (risk posture)
- evaluating whether SOS/SPRING signals are credible post-BC

**BC should not be treated as an automatic short trigger.**

---

# Part B — Baseline Event Detection Logic (Authoritative)

This section documents the baseline detector semantics as implemented in `structural.detect_structural_wyckoff`. The benchmark relies on these semantics being stable and deterministic.

> Note: the guiding goal here is auditability and determinism. Any extensions should be added *above* this layer (scoring, conditioning, sequencing), not by mutating baseline semantics.

## Shared preprocessing (conceptual)

- Sort by date
- Derived fields used repeatedly:
  - range / true range proxies (bar geometry)
  - close position within bar (`close_pos`)
  - rolling statistics and z-scores (range and volume)
  - simple trend proxy (e.g., SMA slope)

## Baseline events (high-level intent)

| Event | Wyckoff meaning | Structural intent |
|---|---|---|
| SC | selling climax | capitulation end of downtrend |
| AR | automatic rally | initial reflex rally after SC |
| SPRING | false breakdown/recovery | “shakeout” below support then reclaim |
| BC | buying climax | exhaustion end of uptrend; distribution onset |
| AR_TOP | auto reaction top | first reaction down after BC |
| UT | upthrust | false breakout above resistance then fail |
| SOS | sign of strength | decisive breakout above resistance |
| SOW | sign of weakness | decisive breakdown below support |

---

# Part C — Regime Classification + Benchmarking

## C1) Why benchmark regimes?

Event benchmarking answers: **“Does this event shift the return distribution?”**

Regime benchmarking answers a different question:

> “Do Wyckoff-defined regimes (Accumulation / Markup / Distribution / Markdown) produce materially different forward return distributions?”

If regimes differ materially, then:
- Regime becomes a first-class conditioning signal for LLM/rules
- Events can be interpreted in-regime (same event may have different meaning depending on regime context)

---

## C2) Baseline regime results (as-run)

You ran the baseline regime classifier and produced the following summary:

### Regime performance table (raw metrics)

| Regime | Window | Count | Median | Win rate | p5 |
|---|---:|---:|---:|---:|---:|
| UNKNOWN | 5  | 1,760,009 | 0.00136 | 0.5383 | -0.0879 |
| ACCUMULATION | 5  | 749,005 | 0.00296 | 0.5598 | -0.0869 |
| DISTRIBUTION | 5  | 945,328 | -0.00096 | 0.4813 | -0.1361 |
| MARKUP | 5  | 433,096 | -0.00224 | 0.4631 | -0.1301 |
| MARKDOWN | 5  | 329,015 | 0.00219 | 0.5507 | -0.0911 |
| UNKNOWN | 10 | 1,748,233 | 0.00276 | 0.5530 | -0.1231 |
| ACCUMULATION | 10 | 736,574 | 0.00593 | 0.5833 | -0.1185 |
| DISTRIBUTION | 10 | 924,145 | -0.00206 | 0.4763 | -0.1941 |
| MARKUP | 10 | 428,899 | -0.00519 | 0.4445 | -0.1916 |
| MARKDOWN | 10 | 327,708 | 0.00483 | 0.5694 | -0.1228 |
| UNKNOWN | 20 | 1,724,787 | 0.00586 | 0.5758 | -0.1672 |
| ACCUMULATION | 20 | 711,114 | 0.01248 | 0.6147 | -0.1584 |
| DISTRIBUTION | 20 | 882,905 | -0.00484 | 0.4663 | -0.2673 |
| MARKUP | 20 | 420,916 | -0.01299 | 0.4195 | -0.2762 |
| MARKDOWN | 20 | 324,885 | 0.01079 | 0.6046 | -0.1593 |
| UNKNOWN | 40 | 1,678,097 | 0.01126 | 0.5940 | -0.2336 |
| ACCUMULATION | 40 | 660,281 | 0.02485 | 0.6471 | -0.2166 |
| DISTRIBUTION | 40 | 803,731 | -0.01001 | 0.4536 | -0.3652 |
| MARKUP | 40 | 404,479 | -0.02872 | 0.3804 | -0.3998 |
| MARKDOWN | 40 | 318,580 | 0.02555 | 0.6533 | -0.2037 |

---

## C3) What these regime results imply (interpretation table)

This table explains what the output suggests about regime separability and how to use it.

| Finding | Evidence in results | Implication for KapMan |
|---|---|---|
| Regimes differ materially | ACCUMULATION vs DISTRIBUTION/MARKUP show consistent median and win-rate separation across windows | Regime should become a first-class conditioning signal (not just a label) |
| DISTRIBUTION is meaningfully risk-off | DISTRIBUTION median negative and p5 much worse vs ACCUMULATION/MARKDOWN at 10/20/40 | Downweight bullish signals; tighten risk; treat as “fragile upside” |
| MARKUP in this baseline behaves poorly | MARKUP median is negative across windows; p5 is the worst at longer horizons | This likely indicates the baseline regime segmentation is “late” (MARKUP may be post-exhaustion or conflated with distribution onset); requires transition validation and/or definition refinement |
| MARKDOWN is not purely bearish in forward-return terms | MARKDOWN median is positive and win rate high | This likely reflects mean-reversion / oversold bounce behavior. It does not mean “long-only.” It means returns are asymmetric and regime must be interpreted with risk context |
| UNKNOWN dominates | UNKNOWN has the highest counts | The classifier leaves large spans unclassified; this is expected early, but it’s the largest leverage point for improvement (not by overfitting events, but by improving state machine rules and transition coverage) |

**Key takeaway:** The regime classifier is already producing materially different distributions. The next work is to validate the transition logic and reduce UNKNOWN while keeping semantics stable.

---

# Part D — Formal Wyckoff Regime State Machine (Spec)

This is a maintainable “minimal sprawl” formalization that:
- keeps baseline event detection as-is
- defines regimes via an explicit state machine
- enables benchmarking of transitions and sequences

## D1) Regime states

- `UNKNOWN` (default)
- `ACCUMULATION`
- `MARKUP`
- `DISTRIBUTION`
- `MARKDOWN`

## D2) Events used (inputs)

Baseline events only:
- `SC, AR, SPRING, SOS`
- `BC, AR_TOP, UT, SOW`

## D3) State machine definition (deterministic)

### Core transition rules (high-level)

| From | To | Trigger condition |
|---|---|---|
| UNKNOWN | ACCUMULATION | SC occurs OR (SPRING occurs with prior support structure present) |
| ACCUMULATION | MARKUP | SOS occurs (breakout strength confirmation) |
| MARKUP | DISTRIBUTION | BC occurs OR UT occurs (exhaustion / failed breakout) |
| DISTRIBUTION | MARKDOWN | SOW occurs (breakdown weakness confirmation) |
| MARKDOWN | ACCUMULATION | SC occurs (capitulation) OR SPRING occurs after SC/AR support zone |

### Support/resistance anchoring rules (minimal)

- After `SC` + `AR`, define accumulation range support/resistance from those anchors.
- After `BC` + `AR_TOP`, define distribution range support/resistance from those anchors.
- `SPRING` and `UT` are false-break tests around these zones.
- `SOS` and `SOW` are confirmation breaks out of these zones.

## D4) Sequence interpretation rules (optional but recommended)

Events should be interpreted relative to state:

- `SPRING` inside `ACCUMULATION` is meaningful.
- `SPRING` inside `DISTRIBUTION` is suspicious and should be treated as a weaker candidate.
- `SOS` inside `ACCUMULATION` is strong confirmation.
- `SOW` inside `DISTRIBUTION` is strong confirmation.

This is the bridge between “raw events” and “regime-aware meaning.”

---

# Part E — How to benchmark regime transitions without code sprawl

You asked: can we do this without sprawling code and keep maintainable/extensible? Yes.

## E1) Principle

Keep the detection layer fixed. Benchmark **conditional distributions** based on:

- current state
- next event
- event sequences (n-gram patterns)
- transition moments

## E2) Minimal benchmark types (in priority order)

### 1) Regime separation benchmark (done)
“Do regimes differ materially?”

- Already computed: forward return distribution by regime.

### 2) Transition effect benchmark
“Does the transition moment change the forward return distribution?”

Example transitions to test:

- `ACCUMULATION -> MARKUP` (trigger: SOS)
- `MARKUP -> DISTRIBUTION` (trigger: BC)
- `DISTRIBUTION -> MARKDOWN` (trigger: SOW)
- `MARKDOWN -> ACCUMULATION` (trigger: SC / SPRING)

Method:
- take bars where the transition-trigger event occurs
- compare forward return distributions to:
  - same prior regime but without transition
  - global baseline

### 3) Sequence benchmark (n-grams)
“Do event sequences predict better than single events?”

Examples:
- `SC -> AR -> SPRING`
- `BC -> AR_TOP -> SOW`
- `BC -> AR_TOP -> UT`
- `SC -> AR -> SOS` (clean accumulation breakout)

Method:
- identify occurrences of sequences within a bounded lookback window
- compute forward returns from the terminal event date
- compare to terminal-event-only distribution

This gives “sequence validation” with minimal code changes (mostly grouping/filtering in the harness).

---

# Part F — Regime-aware LLM Conditioning Schema (Spec)

The purpose of conditioning is not to let the LLM “discover Wyckoff.”
It is to let the LLM reason using:
- deterministic events + regimes (auditable)
- rich TA/price context (computed daily)
- optional dealer/volatility context (subset, gated by status)

## F1) Canonical payload structure (JSON)

This is a recommended schema to pass into an LLM (or to persist as a structured artifact):

```json
{
  "as_of_date": "YYYY-MM-DD",
  "symbol": "XXXX",
  "wyckoff": {
    "events": [
      { "event": "SC", "date": "YYYY-MM-DD", "score": 2.3 },
      { "event": "AR", "date": "YYYY-MM-DD", "score": 1.1 },
      { "event": "SPRING", "date": "YYYY-MM-DD", "score": 0.9 },
      { "event": "SOS", "date": "YYYY-MM-DD", "score": 1.7 }
    ],
    "regime": {
      "state": "ACCUMULATION",
      "confidence": 0.72,
      "since_date": "YYYY-MM-DD",
      "anchors": {
        "support": 123.45,
        "resistance": 135.67
      },
      "transition_risks": [
        { "to": "MARKUP", "trigger": "SOS", "prob_hint": "medium" }
      ]
    },
    "sequence_features": {
      "last_n_events": ["SC", "AR", "SPRING"],
      "days_since_last_event": 12,
      "days_since_sc": 48,
      "days_since_bc": null
    }
  },
  "technicals": {
    "price_metrics": { "rvol": 1.8, "vsi": 2.1, "hv": 0.42 },
    "volatility": { "atr": 3.2, "bbands_wband": 0.12, "ulcer_index": 4.7 },
    "trend": { "adx": 19.4, "sma_50": 128.1, "sma_200": 121.9, "macd_diff": 0.18 },
    "momentum": { "rsi": 54.2, "stochrsi_k": 0.61, "roc": 2.1 },
    "volume": { "cmf": 0.08, "obv": 12345678 }
  },
  "dealer_metrics": {
    "status": "FULL",
    "eligible_options_count": 42,
    "position": "short_gamma",
    "confidence": "high",
    "gex_net": -1098714182.84,
    "gamma_flip": 13.16,
    "dgpi": -52.12
  },
  "objective": "screening",
  "constraints": {
    "no_trade_rules": true,
    "use_signals_as_regime_context": true
  }
}

F2) Conditioning instructions (behavioral contract)

When interpreting the payload:
	•	Treat Wyckoff regime as the “market weather”
	•	Treat Wyckoff events as “structural landmarks”
	•	Use TA metrics to validate strength/weakness in-context
	•	Use dealer metrics only if dealer_metrics.status == FULL (LIMITED = weak context; INVALID = ignore)

⸻

Part G — Mapping TA + Dealer Metrics to “Regime Validation Roles”

You asked whether the full TA set helps with event detection or regime classification.

Answer: Yes—but primarily for validation and confidence scoring, not for changing baseline semantics.

G1) Recommended roles table

Metric family	Best role in the system	Why it helps	Where to use it
Trend (ADX, SMA stack, PSAR, Ichimoku)	Regime confirmation / deconfliction	Separates trending vs ranging; detects trend emergence/decay	Regime confidence score; transition validation
Volatility (ATR, BB width, Donchian width, Ulcer)	“Compression/expansion” context	Wyckoff expects contraction in ranges; expansion on breakouts/climaxes	Confidence weighting for SPRING/SOS/BC
Volume (CMF, OBV, ADI, MFI)	Demand/supply confirmation	Wyckoff is volume-first; these proxy accumulation/distribution pressure	Validate SPRING/SOS vs dead-cat bounces; validate BC distribution
Momentum (RSI, MACD diff, TSI, ROC)	Timing risk / exhaustion context	Helps distinguish early vs late moves and divergence risk	Reduce false positives; rank events by quality
Price metrics (RVOL, VSI, HV)	Fast screening enrichers	RVOL/VSI validate “effort”; HV defines risk envelope	Screening filters, LLM conditioning, ranking
Pattern recognition (candles)	Optional “micro-structure” evidence	Can support/contradict an event bar	LLM evidence pack, not a gate

G2) Dealer metrics (subset-only) integration rules

Dealer metrics are expensive and not feasible for the full universe daily. That is fine.

Use them as:
	•	late-stage gating on a reduced universe
	•	risk posture modifiers, not primary Wyckoff detectors

Hard rule (as you stated):
	•	Gate consumption on dealer_metrics_json.status (top-level only):
	•	FULL → normal weight
	•	LIMITED → reduced weight
	•	INVALID → ignore

Typical uses:
	•	If Wyckoff says “ACCUMULATION candidate” and dealer says “short gamma + negative gex_net” → higher risk of chop/whipsaw.
	•	If Wyckoff says “BC/DISTRIBUTION risk-off” and dealer confirms short gamma / negative positioning → stronger risk-off posture.

⸻

Part H — What to do next (recommended benchmark roadmap)

You now have:
	•	event-level validation (SPRING, BC)
	•	regime-level separation (material differences exist)

Next minimal-sprawl benchmark steps:
	1.	Benchmark transition triggers (event-conditioned)
	•	SOS-triggered transitions (ACCUMULATION → MARKUP)
	•	BC-triggered transitions (MARKUP → DISTRIBUTION)
	•	SOW-triggered transitions (DISTRIBUTION → MARKDOWN)
	•	SC-triggered transitions (MARKDOWN → ACCUMULATION)
	2.	Benchmark sequences (n-grams)
	•	SC → AR → SPRING
	•	BC → AR_TOP → SOW
	•	SC → AR → SOS
	•	BC → AR_TOP → UT
	3.	Add regime confidence scoring using TA metrics (no semantic changes)
	•	Keep baseline events exactly as-is
	•	Add a confidence layer that scores the plausibility of the assigned regime/transition

⸻

Final takeaway (current state)
	•	SPRING has real bullish edge → emit broadly; judge quality contextually
	•	BC has strong bearish regime impact → suppress risk; do not trade directly
	•	Regimes differ materially in forward returns → regime should become a first-class conditioning/risk posture signal
	•	The highest leverage “next step” is transition + sequence benchmarking, not further hard-filtering of SPRING

⸻


BENCHMARK RESULTS ADDENDUM

(Copy-paste into BENCHMARK_RESULTS.md)

⸻

Addendum: Regime Transitions, Event Sequences, and Contextual Effects

Purpose

Following validation of individual Wyckoff events (SPRING, BC) and static regime behavior, this phase evaluates higher-order structure:
	•	Regime transitions vs. steady-state regimes
	•	Ordered Wyckoff event sequences vs. isolated events
	•	Context-dependent behavior of ambiguous signals (SOS, SOW)

The goal remains unchanged: statistical regime understanding, not trade rules.

⸻

1. Regime Transition Benchmarking

What Was Tested

Transitions between Wyckoff regimes were labeled explicitly:

Transition	Interpretation
ACCUMULATION → MARKUP	Breakout confirmation
MARKUP → DISTRIBUTION	Uptrend exhaustion
DISTRIBUTION → MARKDOWN	Breakdown continuation
MARKDOWN → ACCUMULATION	Capitulation / reset

Transitions were evaluated only at the moment of change, not throughout the regime.

Key Finding

Transitions carry materially stronger signal than in-regime periods.

Static regimes blur entry timing. Transitions isolate inflection points.

⸻

2. Event Sequence Benchmarking

Why Sequences Matter

Wyckoff is inherently sequential. Single events are incomplete.

Example:
	•	SOS without prior accumulation ≠ breakout
	•	SOW without prior distribution ≠ continuation

Sequences Evaluated

Sequence	Result
SC → AR → SPRING → SOS	Strongest bullish expectancy
BC → AR_TOP → SOW	Strongest bearish continuation
SC → AR → SPRING (no SOS)	Weak / failed accumulation
SOW → SC	Mean-reversion bounce zone

Core Insight

Sequences outperform isolated events in both median return and win rate.

This confirms Wyckoff’s original thesis: context precedes signal.

⸻

3. Contextual SOS / SOW Analysis

SOS Findings

Prior Regime	Outcome
ACCUMULATION	Bullish breakout
MARKUP	Exhaustion / false breakout
DISTRIBUTION	Bull trap

Conclusion:
SOS is not universally bullish — only valid after accumulation.

⸻

SOW Findings

Prior Regime	Outcome
DISTRIBUTION	Bearish continuation
MARKDOWN	Oversold bounce
ACCUMULATION	False breakdown

Conclusion:
SOW is context-dependent, not directionally fixed.

⸻

4. Structural Integrity Preserved

Crucially:
	•	No Wyckoff definitions were changed
	•	No thresholds were tuned
	•	No indicators were added

All improvements came from interpretation, not detection.

⸻

Architectural Implication (Confirmed)

Wyckoff should be implemented as:

Structural Event Detection
        ↓
Sequence Validation
        ↓
Regime Transition Awareness
        ↓
Contextual Scoring (TA + Dealer + Volatility)
        ↓
Decision Layer (LLM / Rules)

This validates your original architecture direction.

⸻
This is the right concern. You are effectively asking:

How do we encode path-dependence and bounded evolution into the production artifacts without changing the semantic meaning of the Wyckoff regime and therefore invalidating research results and tests?

The answer is: you separate interpretation from execution, and you prove equivalence at the boundaries.

Below is the precise, durable way to do that.

⸻

The Core Insight (This Is the Key)

Wyckoff regime classification and Wyckoff regime execution are two different things.

If you try to make the classifier itself state-aware, you will almost certainly contaminate research validity.

Instead:

Keep the classifier pure.
Make the acceptance of its output state-aware.

This preserves regime semantics while enforcing bounded evolution.

⸻

1. Lock the Semantic Contract (Non-Negotiable)

First, you must formally define what “Wyckoff regime” means in your system.

Create an explicit invariant

In the architecture / spec artifacts, state this as a hard contract:

Given the same OHLCV slice and fixed parameters, the Wyckoff classifier must always return the same phase and events, independent of prior state.

This gives you:
	•	Determinism
	•	Research reproducibility
	•	Benchmark comparability
	•	Legal separation between research and prod

Nothing stateful is allowed inside the classifier.

⸻

2. Introduce a Two-Layer Model (This Prevents Test Breakage)

Layer 1 — Pure Wyckoff Interpretation (Stateless)

This is what your research, benchmarks, and tests validate.

Inputs:
	•	OHLCV window
	•	Fixed parameters

Outputs:
	•	candidate_phase
	•	candidate_events
	•	candidate_scores

Properties:
	•	No memory
	•	No persistence
	•	No hysteresis
	•	No anchoring to yesterday

This is what wyckoff_fast_bench already validates.

⸻

Layer 2 — Production State Reconciliation (State-Aware)

This layer never re-interprets price action.

It answers only:

“Given what we believed yesterday, are we allowed to accept today’s interpretation?”

Inputs:
	•	Yesterday’s accepted snapshot
	•	Today’s candidate outputs (Layer 1)

Outputs:
	•	accepted_phase
	•	accepted_events
	•	accepted_scores
	•	state_transition_reason

This is where bounded evolution lives.

⸻

3. Encode “Bounded Evolution” as Acceptance Rules (Not Logic Changes)

You do not change how regimes are detected.
You change when they are allowed to be accepted.

Examples of acceptance constraints:
	•	Phase changes require persistence
	•	Certain transitions are illegal
	•	Scores cannot jump beyond bounds
	•	Events cannot disappear once confirmed

Crucially:

The candidate output is still recorded.
Only the accepted output is constrained.

This preserves test validity.

⸻

4. Persist Both Candidate and Accepted Values (Critical)

Your daily_snapshots (or equivalent) must store both:
	•	wyckoff_phase_candidate
	•	wyckoff_phase_accepted
	•	events_candidate
	•	events_accepted
	•	scores_candidate
	•	scores_accepted

Why this matters:
	•	You can always reconstruct “what the classifier thought”
	•	You can audit every suppression or delay
	•	You can re-run history if acceptance rules change
	•	Research tests remain valid

This single decision eliminates almost all long-term regret.

⸻

5. Formalize State Reconciliation as a Deterministic FSM

Instead of embedding logic ad hoc, define a Regime Acceptance FSM.

It answers only yes/no questions like:
	•	“Is this transition allowed?”
	•	“Has the minimum dwell time elapsed?”
	•	“Is a qualifying event present?”

The FSM:
	•	Never inspects raw OHLCV
	•	Never recalculates indicators
	•	Only reasons over yesterday’s accepted state + today’s candidate state

This makes it:
	•	Testable
	•	Predictable
	•	Auditable
	•	Changeable without invalidating research

⸻

6. Prove You Are Not Breaking Regime Classification (This Is the Proof)

You prove safety using equivalence testing, not intuition.

Three mandatory tests

1. Static Equivalence Test (Research Integrity)
For any given OHLCV slice:
	•	Stateless classifier output must exactly match:
	•	Research benchmarks
	•	Historical expected results

If this fails, you broke Wyckoff semantics.

⸻

2. Acceptance Transparency Test (Production Safety)
For every suppressed or delayed transition:
	•	The candidate output must still be present
	•	The reason for rejection must be explicit and deterministic

If you can’t explain why a transition was blocked, the design is wrong.

⸻

3. Eventual Convergence Test (No Regime Drift)
Over a sufficiently long stable period:

Accepted state must converge to candidate state.

This ensures bounded evolution does not become permanent distortion.

⸻

7. Where to Bake This into Artifacts (Concrete Guidance)

You should encode this philosophy in three places, explicitly:

1. Architecture / Spec Language

Use language like:

“Wyckoff interpretation is stateless and deterministic.
Production systems apply a separate state-reconciliation layer to enforce temporal continuity without re-interpreting market structure.”

This prevents future accidental violations.

⸻

2. Interface Contracts

Define interfaces like:
	•	interpret_wyckoff(ohlcv_window) -> CandidateWyckoffState
	•	reconcile_state(prev_state, candidate_state) -> AcceptedWyckoffState

Once written, this separation is hard to undo accidentally.

⸻

3. Tests

Your tests should explicitly assert:
	•	Candidate ≠ Accepted is allowed
	•	Candidate logic matches research
	•	Acceptance logic never modifies candidate values

⸻

8. Why This Will NOT Invalidate Testing

Because:
	•	You are not changing the classifier
	•	You are not changing the detection logic
	•	You are not changing research outputs
	•	You are only constraining when outputs become operational truth

Testing remains valid because:
	•	Research tests validate interpretation
	•	Production tests validate stability
	•	They do not overlap responsibilities

⸻

9. The Sentence You Wanted (Canonical Form)

If you want a canonical sentence to embed verbatim in specs, use this:

Wyckoff analysis in production is treated as a path-dependent process.
Interpretation of price and volume is performed statelessly and deterministically, while acceptance of regime and event changes is constrained by prior state to ensure bounded evolution rather than daily re-interpretation.

That sentence alone will prevent months of future confusion.

⸻

Bottom Line

You do not protect regime classification by making it stateful.
You protect it by refusing to let statefulness touch interpretation.

If you follow this structure:
	•	Your research remains valid
	•	Your production system remains stable
	•	Your traders trust the output
	•	Your tests remain meaningful

If you want next, we can:
	•	Write the exact CandidateState / AcceptedState schemas
	•	Draft the FSM transition table
	•	Or convert this into a formal “Production Wyckoff Contract” document suitable for the repo