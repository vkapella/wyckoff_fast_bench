# Wyckoff Benchmark System - Critical Evaluation

**Date:** December 28, 2025  
**Analyst:** Claude  
**Dataset:** ~8,000+ symbols, ~2 years daily OHLCV, ~36,400 baseline events

---

## 1. EXECUTIVE SUMMARY

### Overall Assessment: **Solid Foundation with Notable Gaps**

The benchmark results are methodologically sound and produce statistically meaningful signal separations. The core conclusions are generally defensible, but several critical weaknesses require attention before production deployment.

| Aspect | Rating | Notes |
|--------|--------|-------|
| **Sample Size** | ✅ Strong | 36K+ events, 8K+ symbols - statistically robust |
| **Event Detection Logic** | ⚠️ Moderate | Reasonable baseline, but significant false positive concerns |
| **Regime Classification** | ⚠️ Weak | Over-simplified state machine, 41% UNKNOWN is problematic |
| **Evaluation Methodology** | ✅ Strong | Clean forward returns, proper out-of-sample metrics |
| **Statistical Rigor** | ⚠️ Moderate | Missing statistical significance tests, no CI bounds |
| **Actionability** | ⚠️ Moderate | Directional insights clear, but calibration for trading unclear |

---

## 2. AGREEMENT WITH KEY FINDINGS

### Findings I Strongly Agree With

| Finding | Evidence Quality | My Assessment |
|---------|------------------|---------------|
| **BC is a risk-off signal** | Very Strong | BC shows -1.0% to -2.0% median delta, 5-10% lower win rates, worsening p5 at all horizons |
| **SPRING has baseline edge** | Strong | 70% win rate at 20d, +4.5% median - materially better than baseline |
| **Regimes differ materially** | Strong | ACCUMULATION vs DISTRIBUTION show 2-4% median separation at 40d |
| **Hard-filtering SPRING reduces value** | Moderate | spring_after_sc reduces to 233 events with similar edge - recall loss > precision gain |
| **MARKUP behaves "late"** | Strong | Negative medians suggest phase detection triggers after the move |

### Findings That Need More Scrutiny

| Finding | Concern | What's Missing |
|---------|---------|----------------|
| **SOW is bullish?** | Counter-intuitive | +2.1% median, 64% win rate - either definition is wrong OR this is oversold bounce |
| **SOS is bearish?** | Very concerning | -2.1% median, 38% win rate - the exact opposite of expected |
| **AR shows edge** | Needs context | +2.1% median is good, but is this AR-the-event or AR-the-concept? |

---

## 3. CRITICAL WEAKNESSES IDENTIFIED

### 3.1 The SOS Problem (Most Serious)

**Issue:** SOS (Sign of Strength) shows *negative* forward returns across all windows.

| Window | SOS Median | SOS Win Rate | Expected Behavior |
|--------|------------|--------------|-------------------|
| 5d | -0.6% | 41.6% | Should be positive (breakout confirmation) |
| 10d | -1.1% | 40.4% | Should be positive |
| 20d | -2.1% | 38.1% | Should be positive |
| 40d | -4.2% | 34.1% | Should be positive |

**Root Cause Analysis:**

Looking at `structural.py` lines 121-127:
```python
if resistance_level is not None:
    candidates = df[
        (df["close"] > resistance_level) & (df["tr_z"] >= cfg.sos_tr_z)
    ].index.tolist()
    if candidates:
        sos_idx = int(candidates[0])
        add_event(sos_idx, "SOS", score=float(df.loc[sos_idx, "tr_z"]))
```

**Problem:** This triggers SOS on ANY break above resistance with high range - including exhaustion gaps, failed breakouts, and distribution masquerading as strength. True Wyckoff SOS requires:
- Prior consolidation (accumulation range)
- Increasing volume on the break
- Pullback that holds above prior resistance
- Confirmation of demand

**Recommended Fix:**
1. Require SOS only AFTER accumulation/markup context
2. Add volume confirmation (volume > 1.5x average on break)
3. Consider "close above resistance for N consecutive bars"

### 3.2 The SOW Reversal Problem

**Issue:** SOW (Sign of Weakness) shows *positive* forward returns.

| Window | SOW Median | Baseline Median | Delta |
|--------|------------|-----------------|-------|
| 5d | +0.9% | -0.5% | +1.4% |
| 10d | +1.4% | -0.2% | +1.6% |
| 20d | +2.1% | -0.1% | +2.2% |
| 40d | +3.5% | -0.4% | +3.9% |

**Interpretation Options:**
1. **Mean Reversion:** SOW marks oversold conditions that bounce
2. **Detection Bug:** SOW is triggering at capitulation lows (which then rally)
3. **Semantic Confusion:** What we're detecting isn't Wyckoff SOW

**Most Likely:** Detection is correct but interpretation is wrong. SOW marks *breakdown weakness* which often precedes selling climax territory = bounce setup, not continuation short.

**Recommended Action:** Rename to "Breakdown Alert" or split into:
- SOW_EARLY (distribution breakdown) - hold as bearish
- SOW_LATE (markdown capitulation) - treat as potential SC territory

### 3.3 Regime Classification Oversimplification

**Current State Machine (from `regime.py`):**
```python
_EVENT_TO_REGIME: Dict[str, str] = {
    "SC": "ACCUMULATION",
    "SPRING": "ACCUMULATION",
    "SOS": "MARKUP",
    "BC": "DISTRIBUTION",
    "UT": "DISTRIBUTION",
    "SOW": "MARKDOWN",
}
```

**Problems:**
1. **No Transition Logic:** Each event immediately changes regime (no validation)
2. **No Duration Minimum:** Regime can flip on a single bar
3. **No Confirmation Required:** SOS alone puts you in MARKUP (even if it fails)
4. **41% UNKNOWN:** Massive coverage gap

**Regime Distribution:**

| Regime | Count (40d window) | Pct |
|--------|-------------------|-----|
| UNKNOWN | 1,678,097 | 41% |
| DISTRIBUTION | 803,731 | 20% |
| ACCUMULATION | 660,281 | 16% |
| MARKUP | 404,479 | 10% |
| MARKDOWN | 318,580 | 8% |

**Recommended Fixes:**
1. Require event sequences for regime transitions (not single events)
2. Add minimum phase duration (e.g., 5 bars minimum)
3. Add "confirmation bar" logic before committing to new regime
4. Allow regime to "revert" if follow-through fails

### 3.4 Missing Statistical Rigor

**What's Missing:**
- No confidence intervals on metrics
- No bootstrap significance tests
- No Bonferroni/FDR correction for multiple comparisons
- No effect size calculations (Cohen's d)

**Why This Matters:**

With 8 events × 4 windows × 3 metrics = 96 comparisons, some will be "significant" by chance. The AR edge of +2.1% median sounds impressive, but is it statistically distinguishable from zero after accounting for variance?

**Quick Calculation Needed:**
```python
# For AR at 20d window:
# n = 4,009 samples
# median = 2.1%
# Need: SE of median, CI, p-value vs 0
```

---

## 4. DETECTION LOGIC DEEP DIVE

### 4.1 Selling Climax (SC) - Generally Sound

```python
sc_candidates = df[
    (df["tr_z"] >= cfg.sc_tr_z)        # High range (z ≥ 2.0)
    & (df["vol_z"] >= cfg.sc_vol_z)    # High volume (z ≥ 2.0)
    & (df["close_pos"] >= 0.5)         # Close above midpoint
].index.tolist()
```

**Assessment:** ✅ Reasonable
- Close position filter catches "hammer"-like candles (buying into the close)
- Z-score thresholds are standard
- Downtrend validation via SMA slope is crude but functional

**Potential Enhancement:**
- Add prior decline measurement (% drop over lookback)
- Consider using % of range rather than z-score for extremity

### 4.2 Buying Climax (BC) - Generally Sound

**Assessment:** ✅ Reasonable
- Mirror logic of SC (which is appropriate)
- The results validate this works well (clear negative forward returns)

### 4.3 SPRING - Good But Could Be Better

```python
if support_level is not None:
    for i in range(cfg.min_bars_in_range, n):
        low = float(df.loc[i, "low"])
        if low < support_level * (1 - cfg.spring_break_pct):  # Break below support
            # Check for reentry
            reentry = False
            for j in range(i, min(i + cfg.spring_reentry_bars + 1, n)):
                if float(df.loc[j, "close"]) >= support_level:
                    reentry = True
                    break
            if not reentry:
                continue
            if float(df.loc[i, "close_pos"]) < cfg.spring_close_pos:  # Close high in bar
                continue
            if float(df.loc[i, "vol_z"]) < cfg.spring_vol_z:  # Low volume
                continue
            add_event(i, "SPRING", score=float(df.loc[i, "vol_z"]))
            break  # Only first spring
```

**Assessment:** ⚠️ Moderate
- Core logic is correct (break below + reclaim + close high + low volume)
- Problem: `break` after first spring means we miss subsequent springs
- Problem: No validation of prior range/accumulation context

### 4.4 SOS - Needs Rework

**Current Implementation:** Triggers on ANY close above resistance with high range.

**Recommended Fixes:**
1. Require prior ACCUMULATION regime (or at minimum, prior SC/AR)
2. Add volume confirmation: `vol_z >= 1.0` (above average)
3. Consider requiring 2+ consecutive closes above resistance
4. Add pullback validation (price retraces but holds above prior resistance)

### 4.5 SOW - Potentially Misaligned

**Current Implementation:** Triggers on ANY close below support with high range.

**Issue:** This catches capitulation lows (which bounce) as much as distribution breakdowns.

**Recommended Split:**
- SOW in DISTRIBUTION context → bearish (markdown beginning)
- SOW in MARKDOWN context → potential SC territory (bounce setup)

---

## 5. WHAT DESERVES MORE TESTING

### Priority 1: Event Sequence Validation

Test these sequences and compare to single-event results:

| Sequence | Expected Behavior | Test Priority |
|----------|-------------------|---------------|
| SC → AR → SPRING → SOS | Strong entry sequence | HIGH |
| BC → AR_TOP → UT | Distribution confirmation | HIGH |
| BC → AR_TOP → SOW | Markdown initiation | HIGH |
| SC → AR → SPRING → (no SOS) | Failed accumulation | MEDIUM |
| SOW → SC → AR | Markdown-to-accumulation transition | MEDIUM |

**What to Measure:**
- Forward returns from final event in sequence
- Compare to isolated final event (e.g., SOS-in-sequence vs SOS-alone)
- Win rate improvement from sequence confirmation

### Priority 2: Regime Transition Effects

Current regime benchmark evaluates "in-regime" returns. Missing:

| Transition | Test Design |
|------------|-------------|
| ACCUMULATION → MARKUP | Returns from SOS date when prior regime was ACCUMULATION |
| MARKUP → DISTRIBUTION | Returns from BC date when prior regime was MARKUP |
| DISTRIBUTION → MARKDOWN | Returns from SOW date when prior regime was DISTRIBUTION |
| MARKDOWN → ACCUMULATION | Returns from SC date when prior regime was MARKDOWN |

**Hypothesis:** Transition moments have higher signal quality than in-regime periods.

### Priority 3: False Positive Reduction

Focus on SOS and SOW:

| Test | Design |
|------|--------|
| SOS with volume confirmation | Require vol_z >= 1.0 |
| SOS with prior accumulation | Only emit if regime == ACCUMULATION |
| SOS with follow-through | Require close above resistance for 3+ bars |
| SOW with context split | Separate DISTRIBUTION SOW from MARKDOWN SOW |

### Priority 4: Threshold Sensitivity

Current defaults may not be optimal:

| Parameter | Current | Test Range |
|-----------|---------|------------|
| sc_tr_z | 2.0 | 1.5, 2.0, 2.5, 3.0 |
| sc_vol_z | 2.0 | 1.5, 2.0, 2.5, 3.0 |
| spring_close_pos | 0.6 | 0.5, 0.6, 0.7, 0.8 |
| sos_tr_z | 1.5 | 1.0, 1.5, 2.0 |

**Method:** Grid search with cross-validation to avoid overfitting.

---

## 6. IMPROVEMENTS THAT SHOULD MAKE A MATERIAL DIFFERENCE

### 6.1 High-Impact: Fix SOS Detection

**Expected Improvement:** +5-10% win rate, +1-2% median return

**Implementation:**
```python
# Replace current SOS logic with:
if resistance_level is not None and regime_context == "ACCUMULATION":
    candidates = df[
        (df["close"] > resistance_level) 
        & (df["tr_z"] >= cfg.sos_tr_z)
        & (df["vol_z"] >= 1.0)  # Volume confirmation
    ].index.tolist()
    
    for idx in candidates:
        # Require 2+ days above resistance
        if idx + 2 < n:
            if df.loc[idx+1, "close"] > resistance_level and df.loc[idx+2, "close"] > resistance_level:
                add_event(idx, "SOS", score=...)
                break
```

### 6.2 High-Impact: Sequence-Based Regime Transitions

**Expected Improvement:** Reduce false regime assignments by 30-50%

**Implementation:**
```python
# Example: ACCUMULATION → MARKUP transition requires:
# 1. Prior regime is ACCUMULATION
# 2. SOS event detected
# 3. Price holds above resistance for 5 bars
# 4. Volume on SOS bar above average

def transition_to_markup(prior_regime, events_window, price_df):
    if prior_regime != "ACCUMULATION":
        return False
    if "SOS" not in events_window:
        return False
    # Additional confirmation logic
    ...
```

### 6.3 Medium-Impact: Split SOW by Context

**Expected Improvement:** Clarify signal interpretation, prevent wrong-direction trades

**Implementation:**
- Track prior regime when emitting SOW
- SOW_DISTRIBUTION (if prior regime = DISTRIBUTION): bearish signal
- SOW_MARKDOWN (if prior regime = MARKDOWN): potential reversal territory

### 6.4 Medium-Impact: Add Minimum Phase Duration

**Expected Improvement:** Reduce phase flip-flopping, improve regime stability

**Implementation:**
```python
MIN_PHASE_BARS = 5

# Only commit to new regime if maintained for MIN_PHASE_BARS
def commit_regime(candidate_regime, candidate_start, current_bar):
    if current_bar - candidate_start >= MIN_PHASE_BARS:
        return candidate_regime
    return current_regime  # Don't commit yet
```

### 6.5 Lower-Impact but Useful: Add Statistical Bounds

**Value:** Confidence in results, avoid false discovery

**Implementation:** Bootstrap confidence intervals for key metrics
```python
def bootstrap_ci(data, metric_fn, n_bootstrap=1000, ci=0.95):
    samples = [metric_fn(np.random.choice(data, len(data), replace=True)) 
               for _ in range(n_bootstrap)]
    lower = np.percentile(samples, (1-ci)/2 * 100)
    upper = np.percentile(samples, (1+ci)/2 * 100)
    return lower, upper
```

---

## 7. ASSESSMENT OF THE OVERALL APPROACH

### What's Working Well

1. **Separation of Concerns:** Detection layer separate from evaluation layer - clean architecture
2. **Large Sample Sizes:** 8K+ symbols provides robust statistical power
3. **Forward Return Methodology:** Using actual future returns (not paper gains) is correct
4. **Multiple Windows:** Testing 5/10/20/40 day horizons reveals time-dependent effects
5. **Event Effect Comparison:** Comparing to non-event baseline is proper methodology
6. **Regime as Conditioning Signal:** Treating regime as "weather" rather than trade trigger is wise

### What Needs Work

1. **Detection Logic Quality:** Some events (SOS, SOW) have semantic drift from Wyckoff intent
2. **Regime State Machine:** Too simple, high UNKNOWN rate, no transition validation
3. **Statistical Rigor:** Missing significance tests, confidence intervals
4. **No Cross-Validation:** Risk of overfitting to historical period
5. **No Market Regime Control:** Results may be period-specific (2-year window includes bull market)

### Recommended Architecture Changes

**Current Flow:**
```
OHLCV → Event Detection → Forward Returns → Metrics
```

**Recommended Flow:**
```
OHLCV → TA Enrichment → Event Detection (context-aware)
                           ↓
                    Sequence Validation
                           ↓
                    Regime Classification (state machine)
                           ↓
                    Signal Scoring (composite)
                           ↓
                    Forward Returns + Statistical Tests
```

---

## 8. SPECIFIC RECOMMENDATIONS FOR KAPMAN PRODUCTION

### Immediate Actions (Before MVP)

| Action | Impact | Effort |
|--------|--------|--------|
| Fix SOS detection (add volume + context) | High | Medium |
| Add sequence validation for regime transitions | High | High |
| Rename/split SOW by context | Medium | Low |
| Add bootstrap CI to key metrics | Medium | Low |

### Post-MVP Improvements

| Action | Impact | Effort |
|--------|--------|--------|
| Grid search for optimal thresholds | Medium | Medium |
| Add market regime control (VIX, breadth) | Medium | Medium |
| Implement Brier scoring for calibration | Medium | Low |
| Add cross-validation for robustness | Low | Medium |

### What to Trust in Production

| Signal | Trust Level | Usage |
|--------|-------------|-------|
| BC (Buying Climax) | HIGH | Risk-off trigger, reduce exposure |
| SPRING | HIGH | Bullish bias, but use with context |
| SC (Selling Climax) | MEDIUM | Potential reversal zone |
| AR (Automatic Rally) | MEDIUM | Confirm with subsequent price action |
| Regime: ACCUMULATION | MEDIUM | Bullish posture |
| Regime: DISTRIBUTION | MEDIUM | Bearish posture |
| SOS | LOW (until fixed) | Do not trust current detection |
| SOW | LOW (until split) | Interpret with caution |

---

## 9. SOURCES AND DATA REFERENCES

| Source | Description |
|--------|-------------|
| `baseline_forward_returns.csv` | 36,437 event-level forward returns |
| `event_effects_summary.csv` | Event vs baseline comparison metrics |
| `baseline_regime_summary.csv` | Regime-level forward return summary |
| `baseline_regime_pairwise.csv` | Regime vs UNKNOWN baseline deltas |
| `structural.py` | Baseline detection implementation |
| `regime.py` | Regime state machine implementation |
| `eval.py` | Forward return calculation methodology |
| `BENCHMARK_RESULTS.md` | Original analysis document |
| `WYCKOFF_BENCH_V2_PROPOSAL.md` | Proposed refactoring architecture |

---

**END OF ANALYSIS**
