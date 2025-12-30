# Predictive Value of Algorithmic Steps

This report compares the predictive statistics of Wyckoff event detection at each algorithmic step: baseline detection, incremental/path-dependent detection, regime transitions, event sequences, and context-conditioned events.

**Metric definitions (forward 20 trading days):**
- **Median**: central tendency of returns.
- **WinRate**: fraction of positive forward returns.
- **p5**: fifth percentile return (tail-risk proxy).

**Report date:** 2025-12-30

---

## Baseline vs. Path-Dependent Detection

| Event   |   Baseline Median |   Path Median |   Δ Median |   Baseline WinRate |   Path WinRate |   Δ WinRate |   Baseline p5 |   Path p5 |   Δ p5 |
|:--------|------------------:|--------------:|-----------:|-------------------:|---------------:|------------:|--------------:|----------:|-------:|
| AR      |             0.021 |         0.015 |     -0.006 |              0.634 |          0.601 |      -0.033 |        -0.198 |    -0.195 |  0.003 |
| AR_TOP  |            -0.006 |        -0.001 |      0.005 |              0.458 |          0.491 |       0.033 |        -0.319 |    -0.28  |  0.038 |
| BC      |            -0.01  |        -0.003 |      0.007 |              0.434 |          0.475 |       0.041 |        -0.358 |    -0.291 |  0.067 |
| SC      |             0.024 |         0.021 |     -0.003 |              0.629 |          0.618 |      -0.011 |        -0.204 |    -0.2   |  0.005 |
| SOS     |            -0.021 |        -0.003 |      0.018 |              0.381 |          0.48  |       0.099 |        -0.371 |    -0.351 |  0.021 |
| SOW     |             0.021 |         0.025 |      0.003 |              0.641 |          0.616 |      -0.025 |        -0.197 |    -0.228 | -0.031 |
| SPRING  |             0.045 |         0.028 |     -0.017 |              0.706 |          0.611 |      -0.095 |        -0.154 |    -0.218 | -0.064 |
| UT      |            -0.037 |        -0.02  |      0.017 |              0.325 |          0.411 |       0.086 |        -0.418 |    -0.341 |  0.077 |

**Key takeaways:**
- **BC, AR_TOP, UT, and SOS** improve meaningfully after path-dependent acceptance (higher medians and win rates; less severe p5).
- **AR and SPRING** remain bullish but show smaller medians/win rates than baseline, consistent with stricter acceptance filtering weaker signals.
- **Tail-risk (p5) improvement** is one of the strongest benefits of path dependence (notably for BC and AR_TOP).

---

## Regime Transition Benchmark

Transitions represent the moment when the regime label changes.

| Transition             |   Median |   WinRate |     p5 |
|:-----------------------|---------:|----------:|-------:|
| ACCUMULATION->MARKUP   |   -0.02  |     0.387 | -0.377 |
| DISTRIBUTION->MARKDOWN |    0.05  |     0.694 | -0.193 |
| MARKDOWN->ACCUMULATION |    0.03  |     0.681 | -0.136 |
| MARKUP->DISTRIBUTION   |   -0.042 |     0.307 | -0.435 |

**Insights:**
- **MARKDOWN→ACCUMULATION** and **DISTRIBUTION→MARKDOWN** have strong positive medians and high win rates.
- **MARKUP→DISTRIBUTION** is strongly bearish and remains a clear risk-off signal.
- **ACCUMULATION→MARKUP** remains slightly negative, consistent with early markup pullbacks.

---

## Event Sequence Benchmark

Sequences are ordered patterns of Wyckoff events; results below reflect completed sequences.

| Sequence             |   Median |   WinRate |     p5 |
|:---------------------|---------:|----------:|-------:|
| SEQ_DISTRIBUTION_TOP |   -0.006 |     0.458 | -0.319 |
| SEQ_FAILED_ACCUM     |    0.011 |     0.549 | -0.277 |
| SEQ_MARKDOWN_START   |    0.009 |     0.517 | -0.187 |
| SEQ_RECOVERY         |    0.014 |     0.613 | -0.212 |

**Highlights and cautions:**
- **SEQ_DISTRIBUTION_TOP** is consistently bearish and is the only sequence with very large N in this dataset.
- **SEQ_RECOVERY** is bullish with a solid win rate, but still far smaller N than single events.
- Low-frequency sequences (e.g., **SEQ_MARKDOWN_START**) should be treated as hypothesis-level until N increases or definitions tighten.

---

## Context-Conditioned Event Benchmark

### SOS and SOW split by prior regime

| Context Event          |   Median |   WinRate |     p5 |
|:-----------------------|---------:|----------:|-------:|
| SOS_after_ACCUMULATION |   -0.025 |     0.374 | -0.439 |
| SOS_after_DISTRIBUTION |   -0.01  |     0.428 | -0.318 |
| SOS_after_MARKDOWN     |   -0.045 |     0.286 | -0.454 |
| SOW_after_ACCUMULATION |    0.034 |     0.647 | -0.222 |
| SOW_after_DISTRIBUTION |    0.046 |     0.687 | -0.215 |
| SOW_after_MARKUP       |    0.034 |     0.682 | -0.163 |

**Observations:**
- **SOW** is consistently bullish across contexts, strongest after **Distribution**.
- **SOS** is bearish across contexts, worst after **Markdown**; it should not be treated as bullish without additional confirmation.

### Additional context splits introduced by the enhanced algorithm (BC, SPRING)

| Context Event             |   Median |   WinRate |     p5 |    N |
|:--------------------------|---------:|----------:|-------:|-----:|
| BC_after_ACCUMULATION     |   -0.004 |     0.466 | -0.32  | 2099 |
| BC_after_DISTRIBUTION     |   -0.037 |     0.342 | -0.402 | 1521 |
| BC_after_MARKDOWN         |   -0     |     0.491 | -0.33  |  554 |
| BC_after_MARKUP           |   -0.017 |     0.374 | -0.339 |  600 |
| SPRING_after_ACCUMULATION |    0.028 |     0.587 | -0.246 |  266 |
| SPRING_after_DISTRIBUTION |    0.045 |     0.711 | -0.193 |  288 |
| SPRING_after_MARKDOWN     |    0.043 |     0.702 | -0.15  |  841 |
| SPRING_after_MARKUP       |    0.06  |     0.708 | -0.123 |   96 |

**Observations:**
- **BC_after_DISTRIBUTION** is materially more bearish than other BC contexts (lower median and weak win rate).
- **SPRING** is bullish in all contexts, with the strongest medians in **SPRING_after_MARKUP** (note: low N).

