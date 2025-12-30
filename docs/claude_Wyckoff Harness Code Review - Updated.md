# Wyckoff Harness Code Review - Updated Version

**Date:** December 29, 2025  
**Purpose:** Review additions and changes to the benchmark harness

---

## 1. SUMMARY OF CHANGES

The updated harness has evolved significantly from the original version. Here's a complete inventory:

### New Modules Added

| Module | Purpose | Lines | Quality |
|--------|---------|-------|---------|
| `sequence_labels.py` | Detect ordered event sequences (SC→AR→SPRING→SOS, etc.) | ~110 | ✅ Good |
| `transition_labels.py` | Detect regime transitions with min_prior_bars validation | ~65 | ✅ Good |
| `contextual_event_eval.py` | Attach prior_regime to events for context-aware analysis | ~50 | ✅ Good |

### Modified Modules

| Module | Key Changes |
|--------|-------------|
| `detectors.py` | Added `incremental_baseline_detector` registration |
| `eval.py` | Added `evaluate_path_dependency()` function |
| `run.py` | Major expansion: +200 lines for transition/sequence/contextual benchmarks |

---

## 2. DETAILED CODE REVIEW

### 2.1 `sequence_labels.py` - Event Sequence Detection

**Architecture:** Clean and well-structured

```python
_SEQUENCES = {
    "SEQ_ACCUM_BREAKOUT": ["SC", "AR", "SPRING", "SOS"],
    "SEQ_DISTRIBUTION_TOP": ["BC", "AR_TOP"],
    "SEQ_MARKDOWN_START": ["BC", "AR_TOP", "SOW"],
    "SEQ_FAILED_ACCUM": ["SC", "AR", "SPRING"],  # Special: no SOS within gap
    "SEQ_RECOVERY": ["SOW", "SC"],
}
```

**Strengths:**
- Clean separation of sequence patterns from detection logic
- `max_gap` parameter controls temporal window (configurable)
- Special handling for `SEQ_FAILED_ACCUM` (absence-based detection)
- Returns sparse events at sequence completion

**Concerns:**

| Issue | Severity | Recommendation |
|-------|----------|----------------|
| `SEQ_FAILED_ACCUM` sample size likely tiny | Medium | Log count warnings |
| No overlap prevention between sequences | Low | Consider mutual exclusion logic |
| All sequences use same `max_gap` | Low | Per-sequence gap configuration |

**Code Quality:** 8/10

### 2.2 `transition_labels.py` - Regime Transition Detection

**Architecture:** Well-designed with validation

```python
_ALLOWED_TRANSITIONS: List[Tuple[str, str]] = [
    ("ACCUMULATION", "MARKUP"),
    ("MARKUP", "DISTRIBUTION"),
    ("DISTRIBUTION", "MARKDOWN"),
    ("MARKDOWN", "ACCUMULATION"),
]
```

**Strengths:**
- Enforces valid Wyckoff cycle (no skipping phases)
- `min_prior_bars` prevents noise transitions (addresses my earlier concern!)
- Excludes UNKNOWN regime transitions
- Clean state machine implementation

**This directly addresses my recommendation:** "Add minimum phase duration"

**Code Quality:** 9/10

### 2.3 `contextual_event_eval.py` - Context-Aware Event Analysis

**Architecture:** Simple and effective

```python
def attach_prior_regime(
    events_df: pd.DataFrame, regime_df: pd.DataFrame, lookback: int = 1
) -> pd.DataFrame:
```

**Strengths:**
- Attaches prior regime to each event for context-aware analysis
- Configurable lookback (default=1, meaning "regime at event time")
- Enables SOS_after_ACCUMULATION vs SOS_after_DISTRIBUTION analysis

**This directly addresses my recommendation:** "Context-aware SOW split"

**Code Quality:** 8/10

### 2.4 `eval.py` - Path Dependency Evaluation

**New Function:**

```python
def evaluate_path_dependency(
    baseline_df: pd.DataFrame, incremental_df: pd.DataFrame
) -> pd.DataFrame:
```

**Metrics Computed:**
- `total_events`: Total baseline events
- `matched_events`: Events in both detectors
- `moved_events`: Matched events with different dates
- `mean_date_delta` / `median_date_delta`: Timing differences
- `unmatched_baseline` / `unmatched_incremental`: Missing events

**Strengths:**
- Clean merge on (symbol, event) for comparison
- Handles missing events gracefully
- Returns single-row summary for easy consumption

**Code Quality:** 8/10

### 2.5 `run.py` - Main Orchestration

**Major Additions:**

| Section | Lines | Purpose |
|---------|-------|---------|
| Config expansion | 179-201 | New output paths for transition/sequence/contextual |
| Path dependency check | 388-396 | Compare baseline vs incremental |
| Transition benchmark | 478-500 | Run transition labeling and evaluation |
| Sequence benchmark | 502-522 | Run sequence labeling and evaluation |
| Contextual benchmark | 524-569 | Run context-aware SOS/SOW analysis |

**New Helper Functions:**

```python
def _read_csv_or_empty(path: Path, columns: List[str]) -> pd.DataFrame:
    """Safely read CSV or return empty DataFrame"""

def _build_forward_returns_for_events(
    events_df, symbols, ohlcv_path, lookback_days, forward_windows
) -> pd.DataFrame:
    """Build forward returns for arbitrary event DataFrames"""

def _write_benchmark_outputs(
    events_df, eval_df, output_dir, prefix, ...
) -> None:
    """Standardized output writing for any benchmark type"""
```

**Architecture Assessment:**
- Good factoring of common operations into helper functions
- Clean separation of benchmark types
- Maintains backward compatibility with existing outputs

**Code Quality:** 7/10 (some repetition could be further reduced)

---

## 3. ALIGNMENT WITH MY RECOMMENDATIONS

| My Recommendation | Implementation Status | Evidence |
|-------------------|----------------------|----------|
| Require event sequences for regime transitions | ✅ Implemented | `transition_labels.py` with `_ALLOWED_TRANSITIONS` |
| Add minimum phase duration | ✅ Implemented | `min_prior_bars` parameter (default=5) |
| Context-aware SOW/SOS analysis | ✅ Implemented | `contextual_event_eval.py` + run.py lines 524-569 |
| Lock events (no reclassification) | ✅ Implemented | `incremental_baseline_detector` in story |
| Fix SOS detection logic | ⚠️ Partial | Filtered by context, but not volume-confirmed |
| Fix SPRING over-filtering | ❌ Not addressed | Incremental detector still constrains SPRING |
| Add statistical significance tests | ❌ Not addressed | No CI bounds, no p-values |

---

## 4. PRODUCTION READINESS ASSESSMENT

### What's Ready

| Component | Status | Notes |
|-----------|--------|-------|
| Regime transition detection | ✅ Ready | Clean implementation with validation |
| Context-aware event analysis | ✅ Ready | SOS/SOW by prior regime working |
| Path dependency comparison | ✅ Ready | Good for A/B testing detectors |
| Sequence detection framework | ⚠️ Caution | Low sample sizes for some sequences |
| Event effect evaluation | ✅ Ready | Solid forward return methodology |

### What Needs Work

| Component | Issue | Impact |
|-----------|-------|--------|
| `SEQ_ACCUM_BREAKOUT` | 0% win rate in results | Fundamental detection issue |
| SPRING degradation | Lost 10% win rate vs baseline | Incremental detector too restrictive |
| SOS still negative | Context helps but doesn't fix | Detection logic flawed |
| Statistical rigor | No confidence intervals | Can't distinguish signal from noise |

---

## 5. SPECIFIC CODE IMPROVEMENTS

### 5.1 Add Sample Size Warnings

```python
# In run.py, after sequence benchmark:
sequence_counts = sequence_eval_df.groupby("event").size()
low_sample_sequences = sequence_counts[sequence_counts < 50]
if not low_sample_sequences.empty:
    print(f"[warning] Low sample sequences: {low_sample_sequences.to_dict()}")
```

### 5.2 Add Bootstrap CI to Summaries

```python
# In eval.py, add to summarize_forward_returns:
def _bootstrap_ci(data, n_bootstrap=1000, ci=0.95):
    if len(data) < 10:
        return np.nan, np.nan
    medians = [np.median(np.random.choice(data, len(data), replace=True)) 
               for _ in range(n_bootstrap)]
    alpha = (1 - ci) / 2
    return np.percentile(medians, [alpha * 100, (1 - alpha) * 100])

# Then in the results dict:
ci_low, ci_high = _bootstrap_ci(fwd20.values)
results.append({
    ...
    "median_ci_low": ci_low,
    "median_ci_high": ci_high,
})
```

### 5.3 Fix Contextual Event Filter

Currently only SOS/SOW are analyzed contextually:

```python
contextual_events_df = contextual_events_df[
    contextual_events_df["event"].isin(["SOS", "SOW"])
].copy()
```

Consider expanding to BC (BC_after_MARKUP is the key risk signal):

```python
contextual_events_df = contextual_events_df[
    contextual_events_df["event"].isin(["SOS", "SOW", "BC", "SPRING"])
].copy()
```

### 5.4 Add Sequence Overlap Prevention

```python
# In sequence_labels.py, track used events:
def label_event_sequences(events_df: pd.DataFrame, max_gap: int = 30) -> pd.DataFrame:
    # ... existing code ...
    
    used_positions: set = set()  # Track events already in sequences
    
    for symbol, group in data.groupby("symbol", sort=False):
        events = list(zip(group["date"].tolist(), group["event"].tolist(), group.index.tolist()))
        
        for sequence_id, pattern in _SEQUENCES.items():
            positions = _find_sequence_positions(events, pattern, max_gap, used_positions)
            for idx in positions:
                used_positions.add(idx)  # Prevent reuse
                rows.append(...)
```

---

## 6. RECOMMENDED NEXT STEPS

### Before Productionizing (Priority Order)

| Step | Action | Effort | Impact |
|------|--------|--------|--------|
| 1 | Investigate SEQ_ACCUM_BREAKOUT 0% WR | Low | Critical diagnostic |
| 2 | Add sample size warnings to outputs | Low | Prevents false conclusions |
| 3 | Expand contextual analysis to BC/SPRING | Low | Better risk signals |
| 4 | Add bootstrap CI to summary reports | Medium | Statistical rigor |
| 5 | Review incremental detector SPRING logic | Medium | Restore best signal |

### Production Pipeline Architecture

```
Daily Batch:
┌─────────────────────────────────────────────────────────────┐
│  1. Load yesterday's OHLCV (Polygon S3)                     │
│  2. Run incremental_baseline detector                       │
│  3. Classify regimes                                        │
│  4. Detect transitions (min_prior_bars=5)                   │
│  5. Detect sequences (max_gap=30)                           │
│  6. Attach context to SOS/SOW/BC                            │
│  7. Generate signals:                                       │
│     - ENTRY: SPRING in ACCUMULATION, SEQ_RECOVERY           │
│     - EXIT: BC in MARKUP, MARKUP→DISTRIBUTION transition    │
│     - RISK_OFF: BC_score >= 24                              │
│  8. Store to daily_snapshots table                          │
└─────────────────────────────────────────────────────────────┘
```

---

## 7. SUMMARY VERDICT

**The harness evolution is solid and addresses most of my architectural recommendations.** The addition of:
- Transition labeling with `min_prior_bars`
- Sequence detection framework
- Context-aware event analysis

...represents meaningful progress toward production-quality Wyckoff detection.

**Key Remaining Gaps:**
1. SPRING signal degradation in incremental detector
2. SOS detection remains fundamentally flawed
3. SEQ_ACCUM_BREAKOUT at 0% WR indicates core issue
4. No statistical confidence bounds

**Recommendation:** Spend 1-2 iterations fixing the SPRING/SOS detection issues before building the production pipeline. The infrastructure is ready; the detection logic needs refinement.

---

## SOURCES

| File | Key Contribution |
|------|------------------|
| `run.py` | Main orchestration, benchmark integration |
| `sequence_labels.py` | Sequence pattern detection |
| `transition_labels.py` | Regime transition detection |
| `contextual_event_eval.py` | Prior regime attachment |
| `eval.py` | Path dependency evaluation |
| `detectors.py` | Incremental detector registration |