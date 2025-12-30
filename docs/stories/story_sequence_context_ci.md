# Sequence + Context Benchmarks (S4.1)

This note describes the updated sequence and contextual benchmarks, including low-sample warnings and optional bootstrap confidence intervals for median forward returns.

## Low-sample warnings

The sequence benchmark now emits warnings when a sequence has too few occurrences. The harness prints a warning when any sequence has fewer than `min_sequence_samples` events. This helps avoid over-interpreting sparse results.

## Sequence tuning

Sequence detection supports per-sequence gap tuning and disabling sequences entirely.

- `sequence_max_gap_default`: fallback max gap (days) between the first and last event in a sequence.
- `sequence_max_gap_map`: overrides per sequence ID (e.g., `SEQ_MARKDOWN_START`).
- `disabled_sequences`: list of sequence IDs to skip.

## Contextual benchmark updates

Contextual evaluation now includes `BC` and `SPRING` by default alongside `SOS` and `SOW`. This lets you see effects like `BC_after_MARKUP` or `SPRING_after_DISTRIBUTION` in the same report. Use `context_events` to restrict the event list.

## Bootstrap confidence intervals

When enabled, the summary output includes `median_ci_low` and `median_ci_high`, computed by bootstrap resampling of the median forward return. The harness draws `bootstrap_resamples` samples with replacement and uses the 2.5th and 97.5th percentiles (for a 95% interval) of those medians.

Because bootstrapping is compute-heavy, it is disabled by default.

## Config snippet

Update `config/run_config.yaml` with these parameters:

```yaml
sequence_max_gap_default: 30
sequence_max_gap_map:
  SEQ_ACCUM_BREAKOUT: 20
  SEQ_MARKDOWN_START: 40
disabled_sequences: []
min_sequence_samples: 50

context_events: ["SOS", "SOW", "BC", "SPRING"]

bootstrap_ci_enabled: false
bootstrap_resamples: 1000
```

## Running the benchmarks

Run the harness as usual. When bootstrap is enabled, the summary CSVs include the additional confidence interval columns.
