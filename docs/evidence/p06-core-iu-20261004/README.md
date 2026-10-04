# Frozen P06 M5 register handoff evidence

Private full CPU directed acceptance. Production, MAX RBF and frozen M3/M4 are
unchanged. Work is paused at the user's request after this validated checkpoint.

- `receipt.json`: qualified scope, source/artifact hashes and measured results.
- `streams/`: warm/cold/late and 15 lifecycle/event/scope modes.
- `baseline/`: the same stream oracle with overlap disabled.
- `original-max/`, `private-max/`: identical 208-case edge traces.
- `single/`: warm exact register/immediate minima and cold functional results.
- `private-rtl/`: deterministic real CPU source selection.
- `generic-*.json`, `equivalence-*.log`: isolated cost and MAX component proofs.
- `negative-run.log`: an incorrect architectural oracle is rejected.
- `freeze.json`, `audit.py`, `acceptance.json`: checkpoint integrity checks.

Edge traces are losslessly compressed as `.csv.gz`; their original uncompressed
hashes are in the receipt. Other CSVs remain plain text. The receipt preserves
the original build paths for provenance; the runner reconstructs a fresh build.

See [the report](../../optimization/P06_CORE_IU_HANDOFF_20261004.md).
This is not the complete decoded queue, event timing, FPGA fit/STA or a new RBF.
