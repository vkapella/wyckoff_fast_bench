# [S4] Path-dependent incremental detection

## Objective
Add a path-dependent, incremental Wyckoff detector that processes bars in order,
emits each event once, and benchmarks it against the baseline detector without
altering existing outputs.

## Scope
- New incremental detector state machine and adapter in `baseline/incremental.py`.
- Register the detector in `harness/detectors.py` as `incremental_baseline`.
- Add `evaluate_path_dependency` in `harness/eval.py` and emit
  `path_dependency_summary.csv` in `harness/run.py`.
- Update `harness/config.yaml` to use a new output path and enable the detector.

## Constraints
- Do not modify `baseline/structural.py` or existing detector outputs.
- Incremental logic is deterministic and does not re-emit or move events.
