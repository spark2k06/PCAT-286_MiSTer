# Native 286 1/2-wait controls

Four selected controls at actual 6/12.5 MHz, each with visible wait states 1/2:
guest exit 0, host exit 0, unchanged DOS program, 42 valid raw samples and six
summaries. [Results and interpretation](../../optimization/P06_NATIVE_WAITSTATES_RESULTS_20261003.md).

`manifest.json` freezes raw files, runner/validator identity, requested visible
settings, stored config values and observed effective native service costs.
Each selected folder contains the original receipt/CSV/config/logs, runtime
samples and initial CMOS in `nvr/`; use it as a runner profile with a fresh
output directory. The original disk, emulator and ROMs are identified through
the [automatic reference](../p06-timing-reference-20261003/manifest.json).
They are not duplicated here. The ready-to-copy DOS binary remains
`build/p06-timing-reference-20261003/T286REF.COM`; its committed frozen copy is
in the original evidence bundle.

86Box reordered the wait-state config key when saving at exit. Each
`initial-86box.cfg` is reconstructed from the frozen input profile and runner
transformation and matches the recorded pre-run hash byte for byte; its
provenance is explicit. `86box.cfg` retains the final emulator-saved config.

`runner-used.py`, `validator-used.py` and `archive-script.py` preserve the exact
source bytes for this series; these are evidence snapshots. Reproduce with the
repository runner and the recorded matching inputs, adding
`--memory-wait-states 1` or `--memory-wait-states 2` as documented in
[the tool README](../../../SW/CPUTIME/README.md).

`earlier-controls/` preserves two probes rejected before CPU-dispatch
initialization, the earlier successful 6 MHz 1-wait run and two valid-guest
runs with host teardown −6. The selected controls use a single later runner
that pauses the emulator only after DOS measurement completion and before exit.
All four selected hosts returned 0; the underlying host-corruption cause is
not established. BIOS/library diagnostics remain in the logs.

PIT mode 2 was observed. Timer qualification stays NOT_CALIBRATED and physical
6/12 MHz measurements remain NOT_MEASURED. These controls do not certify
historical CPU cycles or physical READY waits.
