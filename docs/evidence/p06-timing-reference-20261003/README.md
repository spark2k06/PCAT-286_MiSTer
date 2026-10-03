# Native 286 timing-reference evidence

The final 6 MHz and 12.5 MHz controls have guest and host exit 0 and strict
42-sample/six-summary validation. See
[interpretation and limitations](../../optimization/P06_NATIVE_REFERENCE_RESULTS_20261003.md)
and [tools](../../../SW/CPUTIME/README.md).

The bundle contains the frozen 2,840-byte `T286REF.COM`, exact NASM listing,
build and arithmetic receipts, raw final CSVs, runtime samples, config and
initial CMOS in each final control's `nvr/`, logs and recomputed validation.
The source DOS disk, copyrighted ROM images and Linux native executable are
identified by hashes; they are not copied into this bundle. Final profile
directories can supply `--profile` to the native runner with the identified
external inputs and a new output directory.

`manifest.json` pins the bundle files and current source/tool identity. The
pre-runtime manifest is a historical snapshot: README instructions were later
expanded; the executable, assembly and runtime tool bytes remain unchanged.
ROM hashes were collected after the runs from the read-only source-selected
files, not from a before/after runtime hash guard.

`host-failed-controls/` retains the two preceding revision-2 runs: valid guest
raw output, but host teardown −6, so neither is a complete-run PASS. Their
cause is unproven. Earlier dispatch-initialization/BIOS acknowledgment probes
remain in the private build directory and are not accepted measurements.
The accepted final runs used separately calibrated CMOS without screenshots.

`parser-tests/` retains the original synthetic controls and original receipt.
Its archived `test_parser.py` preserves historical bytes/paths; use the
repository's `SW/CPUTIME/test_t286ref_parser.py` for a new run.
`parser-repro-final/` is that runnable check's repeat: two positive mode fixtures
and thirteen rejected negative controls, API and CLI. Mode 3 is not a DOS
runtime control here. The timer remains NOT_CALIBRATED and physical 6/12 MHz
results remain NOT_MEASURED.
