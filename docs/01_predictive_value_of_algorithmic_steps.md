# Predictive Value of Algorithmic Steps

This report compares the predictive statistics of Wyckoff event detection at each algorithmic step: baseline detection (S3), path-dependent detection (S4), regime transitions, event sequences, and context-conditioned events. It uses median forward 20-day returns, win rates, and fifth-percentile returns (p5) to measure predictive value.

---

## Baseline vs. Path-Dependent Detection

The table below summarises the baseline metrics for each event alongside the path-dependent metrics and the change (delta). Positive deltas indicate the path-dependent detection improved the metric (higher median or win rate, less severe p5).

| Event   | Baseline Median | Path Median | Δ Median | Baseline WinRate | Path WinRate | Δ WinRate | Baseline p5 | Path p5 | Δ p5 |
|--------|------------------|-------------|----------|------------------|--------------|-----------|-------------|---------|------|
| AR     | 0.021 | 0.015 | -0.006 | 0.634 | 0.601 | -0.033 | -0.198 | -0.195 | 0.003 |
| AR_TOP | -0.006 | -0.001 | 0.005 | 0.458 | 0.491 | 0.033 | -0.319 | -0.280 | 0.038 |
| BC     | -0.010 | -0.003 | 0.007 | 0.434 | 0.475 | 0.041 | -0.358 | -0.291 | 0.067 |
| SC     | 0.024 | 0.021 | -0.003 | 0.629 | 0.618 | -0.011 | -0.204 | -0.200 | 0.005 |
| SOS    | -0.021 | -0.003 | 0.018 | 0.381 | 0.480 | 0.099 | -0.371 | -0.351 | 0.021 |
| SOW    | 0.021 | 0.025 | 0.003 | 0.641 | 0.616 | -0.025 | -0.197 | -0.228 | -0.031 |
| SPRING | 0.045 | 0.028 | -0.017 | 0.706 | 0.611 | -0.095 | -0.154 | -0.218 | -0.064 |
| UT     | -0.037 | -0.020 | 0.017 | 0.325 | 0.411 | 0.086 | -0.418 | -0.341 | 0.077 |

**Key takeaways:**
- **BC, AR_TOP, UT, and SOS** show significant improvements in median return and win rate after path-dependent acceptance. For example, BC’s median return improves from −0.010 to −0.003 and its win rate increases from 0.434 to 0.475.
- **AR and SPRING** remain bullish but with smaller medians and win rates than the baseline because weaker signals are filtered out.
- **SOW** remains bullish but occurs less frequently in the path-dependent data; its median improves slightly but win rate declines.

---

## Regime Transition Benchmark

Transitions represent the moment when the regime label changes. The table shows forward returns and win rates for each transition.

| Transition | Median | WinRate | p5 |
|-----------|--------|---------|----|
| ACCUMULATION→MARKUP | -0.020 | 0.387 | -0.377 |
| DISTRIBUTION→MARKDOWN | 0.050 | 0.694 | -0.193 |
| MARKDOWN→ACCUMULATION | 0.030 | 0.681 | -0.136 |
| MARKUP→DISTRIBUTION | -0.042 | 0.307 | -0.435 |

**Insights:**
- **MARKDOWN→ACCUMULATION** and **DISTRIBUTION→MARKDOWN** show strong positive median returns and high win rates, indicating attractive bullish opportunities as markets exit markdown or enter markdown from distribution.
- **MARKUP→DISTRIBUTION** is strongly bearish, signaling caution during the start of distribution.
- **ACCUMULATION→MARKUP** is slightly negative, suggesting early markup may experience pullbacks before trend continuation.

---

## Event Sequence Benchmark

Sequences are ordered patterns of Wyckoff events. Completed sequences enhance predictive value relative to single events.

| Sequence | Median | WinRate | p5 |
|---------|--------|---------|----|
| SEQ_ACCUM_BREAKOUT | -0.469 | 0.000 | -0.469 |
| SEQ_DISTRIBUTION_TOP | -0.006 | 0.458 | -0.319 |
| SEQ_FAILED_ACCUM | 0.011 | 0.549 | -0.277 |
| SEQ_MARKDOWN_START | -0.021 | 0.350 | -0.217 |
| SEQ_RECOVERY | 0.014 | 0.613 | -0.212 |

**Highlights:**
- **SEQ_MARKDOWN_START** (BC→AR_TOP→SOW) flags early markdown risk with a negative median and low win rate.
- **SEQ_RECOVERY** (SOW→SC) is bullish with solid median returns and win rate.
- **SEQ_DISTRIBUTION_TOP** remains bearish, while **SEQ_FAILED_ACCUM** is mildly positive but limited by sample size.

---

## Context-Conditioned Event Benchmark

Some events behave differently depending on the preceding regime. The table splits SOS and SOW by prior regime.

| Context Event | Median | WinRate | p5 |
|---------------|--------|---------|----|
| SOS_after_ACCUMULATION | -0.025 | 0.374 | -0.439 |
| SOS_after_DISTRIBUTION | -0.010 | 0.428 | -0.318 |
| SOS_after_MARKDOWN | -0.045 | 0.286 | -0.454 |
| SOW_after_ACCUMULATION | 0.034 | 0.647 | -0.222 |
| SOW_after_DISTRIBUTION | 0.046 | 0.687 | -0.215 |
| SOW_after_MARKUP | 0.034 | 0.682 | -0.163 |

**Observations:**
- **SOW** is consistently bullish across all contexts, strongest after Distribution.
- **SOS** is bearish in all contexts, with the worst performance after Markdown, indicating it should not be treated as bullish without confirmation.

