# 011 — Wyckoff Enhanced Sequence Algorithm: Results Review (Standalone Report)

**Report date:** 2025-12-30  
**Inputs:** raw benchmark outputs in `Archive.zip` (CSV summaries).  

This report analyzes the benchmark outputs produced by the **Wyckoff Enhanced Sequence Algorithm** and contrasts them with earlier stages (baseline single-event detection and incremental/path-dependent acceptance). It is intended to be a self-contained artifact.

---

## 1. Executive summary

### What improved (material, actionable)
- **Context conditioning is informative:** conditioning **BC, SPRING, SOS, and SOW** on prior regime produces materially different medians/win-rates/tails. This is strong evidence that **prior regime should be persisted and used downstream** rather than treated as incidental metadata.
- **Incremental/path-dependent acceptance continues to improve bearish signals:** relative to baseline, **BC** and **AR_TOP** become less negative (median) and show better p5 tails; **SOS** improves sharply toward neutral with a ~10-point win-rate lift.
- **Regime transitions remain high-signal:** **MARKDOWN→ACCUMULATION** and **DISTRIBUTION→MARKDOWN** continue to show strong medians and win rates, while **MARKUP→DISTRIBUTION** remains strongly bearish.

### What remains weak or inconclusive
- **SOS is still bearish across contexts:** even though path-dependent SOS improves on aggregate, SOS remains negative in every prior-regime slice. Treat as a confirmation-only component.
- **Sequences are underpowered beyond the dominant sequence:** aside from `SEQ_DISTRIBUTION_TOP`, sequence counts are low and uncertainty is high.

---

## 2. Metrics and outputs (what the archive shows)

All summary tables center on **forward 20-trading-day returns**, with:
- **Median (20d)**, **WinRate (20d)**, **p5 (20d)**
- **N** (event_count), plus density/frequency
- optional uncertainty (median CI low/high) and stability proxy (stability_delta)

---

## 3. Baseline vs incremental/path-dependent event detection

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

### Interpretation
- **BC** improves materially (median ~−1.0% → ~−0.3%) and tail-risk improves meaningfully (p5 improves by ~+6.7 pts).
- **AR_TOP** improves (less bearish) and its p5 tail improves materially.
- **SOS** shows the largest win-rate improvement (~+9.9 pts) and becomes close to neutral on median, but (critically) is still negative in context splits.
- **UT** becomes less bearish (median and win rate improve; tail improves).

---

## 4. Regime transitions

| Transition             |   Median |   WinRate |     p5 |
|:-----------------------|---------:|----------:|-------:|
| ACCUMULATION->MARKUP   |   -0.02  |     0.387 | -0.377 |
| DISTRIBUTION->MARKDOWN |    0.05  |     0.694 | -0.193 |
| MARKDOWN->ACCUMULATION |    0.03  |     0.681 | -0.136 |
| MARKUP->DISTRIBUTION   |   -0.042 |     0.307 | -0.435 |

### Interpretation
- **MARKDOWN→ACCUMULATION** is the strongest bullish transition (median ~+3.0%, win rate ~68%).
- **MARKUP→DISTRIBUTION** is strongly bearish (median ~−4.2%, p5 ~−43.5%), supporting “risk-off / reduce exposure” behavior.

---

## 5. Sequences (completed patterns)

| Sequence             |    N |   Density |   Median(20d) |   WinRate(20d) |   p5(20d) |   CI Low |   CI High |   StabilityΔ |
|:---------------------|-----:|----------:|--------------:|---------------:|----------:|---------:|----------:|-------------:|
| SEQ_DISTRIBUTION_TOP | 6074 |     0.356 |        -0.006 |          0.458 |    -0.319 |   -0.008 |    -0.004 |       -0.005 |
| SEQ_FAILED_ACCUM     |   90 |     0.005 |         0.011 |          0.549 |    -0.277 |   -0.039 |     0.046 |       -0.021 |
| SEQ_MARKDOWN_START   |   30 |     0.002 |         0.009 |          0.517 |    -0.187 |   -0.07  |     0.062 |       -0.063 |
| SEQ_RECOVERY         |  163 |     0.01  |         0.014 |          0.613 |    -0.212 |    0.005 |     0.032 |        0.029 |

### Interpretation and reliability
- **SEQ_DISTRIBUTION_TOP** dominates N and is consistently bearish.
- **SEQ_RECOVERY** is bullish with decent N (163) but still far smaller than single events.
- **SEQ_MARKDOWN_START** has **N=30** and a very wide confidence interval; treat as non-actionable until it scales.

---

## 6. Context-conditioned events (prior regime)

### 6.1 SOS by prior regime
| Prior        |    N |   Median(20d) |   WinRate(20d) |   p5(20d) |   CI Low |   CI High |
|:-------------|-----:|--------------:|---------------:|----------:|---------:|----------:|
| ACCUMULATION |  379 |        -0.025 |          0.374 |    -0.439 |   -0.038 |    -0.013 |
| DISTRIBUTION | 2357 |        -0.01  |          0.428 |    -0.318 |   -0.014 |    -0.007 |
| MARKDOWN     |  191 |        -0.045 |          0.286 |    -0.454 |   -0.068 |    -0.023 |

**Read:** SOS is bearish across all contexts; worst after Markdown.

### 6.2 SOW by prior regime
| Prior        |   N |   Median(20d) |   WinRate(20d) |   p5(20d) |   CI Low |   CI High |
|:-------------|----:|--------------:|---------------:|----------:|---------:|----------:|
| ACCUMULATION | 989 |         0.034 |          0.647 |    -0.222 |    0.028 |     0.041 |
| DISTRIBUTION | 348 |         0.046 |          0.687 |    -0.215 |    0.032 |     0.06  |
| MARKUP       | 110 |         0.034 |          0.682 |    -0.163 |    0.007 |     0.067 |

**Read:** SOW is bullish across all contexts; strongest after Distribution.

### 6.3 SPRING by prior regime
| Prior        |   N |   Median(20d) |   WinRate(20d) |   p5(20d) |   CI Low |   CI High |
|:-------------|----:|--------------:|---------------:|----------:|---------:|----------:|
| ACCUMULATION | 266 |         0.028 |          0.587 |    -0.246 |    0.012 |     0.038 |
| DISTRIBUTION | 288 |         0.045 |          0.711 |    -0.193 |    0.038 |     0.058 |
| MARKDOWN     | 841 |         0.043 |          0.702 |    -0.15  |    0.033 |     0.05  |
| MARKUP       |  96 |         0.06  |          0.708 |    -0.123 |    0.029 |     0.074 |

**Read:** SPRING is bullish across all contexts; strongest median occurs after Markup (low N).

### 6.4 BC by prior regime
| Prior        |    N |   Median(20d) |   WinRate(20d) |   p5(20d) |   CI Low |   CI High |
|:-------------|-----:|--------------:|---------------:|----------:|---------:|----------:|
| ACCUMULATION | 2099 |        -0.004 |          0.466 |    -0.32  |   -0.009 |    -0.001 |
| DISTRIBUTION | 1521 |        -0.037 |          0.342 |    -0.402 |   -0.048 |    -0.032 |
| MARKDOWN     |  554 |        -0     |          0.491 |    -0.33  |   -0.009 |     0.005 |
| MARKUP       |  600 |        -0.017 |          0.374 |    -0.339 |   -0.028 |    -0.007 |

**Read:** BC is bearish in all contexts and is materially worse after Distribution.

---

## 7. Operational implications for KapMan MVP

1. **Persist prior regime and context-conditioned event codes** in the daily snapshot schema (or in the wyckoff JSON blob) so LLM/ranking layers can score them deterministically without recomputation.
2. **Gate sequence usage by minimum N** (configurable). Until sequences have adequate sample sizes, sequences should not drive trade decisions alone.
3. **Downgrade SOS from “bullish event” to “conditional confirmation”** in scoring logic. If SOS is used, require conjunctions (e.g., SPRING+SOS) and/or a bullish regime transition.
4. **Continue using p5 as a primary KPI** since incremental acceptance is improving tails even when medians remain negative.

---

## Appendix — Archive contents (high-level)

The archive includes summary and comparison files for:
- baseline and incremental baseline single-event detection
- regime transitions (events, forward returns, summary)
- event sequences (events, forward returns, summary)
- contextual (prior-regime) event variants (events, forward returns, summary)
- per-event effect sizing across 5/10/20/40 day horizons
