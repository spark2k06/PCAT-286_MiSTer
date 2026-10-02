# PERF01 4 KiB instruction-buffer directed evidence

The RTL and production capacity change are documented in
[P13](../../optimization/P13_CODE_BUFFER_4K_20261002.md).

`sources.sha256` identifies the final scoreboard and RTL used by the directed
512-line run. `unit-icarus.log`, `unit-verilator.log` and `pipeline.log` retain
its results. The initial compatibility matrix's logs cover 1, 64 and 512 lines,
enabled and disabled; that matrix ran before the additional pre-acceptance
cancellation test was added. Its separate source receipt preserves that fact.

`adapter-build.json` records the private executable, source/macros, generated
top, capacity and hashes of unchanged reused SPK286 CPU objects. `adapter-smoke.log`
checks that actual physical-controller timing reaches the adapter correctly.
Guest memory values remain in 86Box; the scoreboard tests retain actual data
coherence separately.

Full local builds, binaries and diagnostic scripts remain in the ignored
`D:/GitHub/PCAT-286_MiSTer/build/perf01-real-memory-20261002/` directory.
Complete CHECKNUM measurement and hardware/timing acceptance are pending at
this implementation milestone.

`resources-before/` captures the completed frozen P10 fitted reference before
the user's candidate synthesis finishes. It retains map/fit summaries, the
Fitter resource section and identities of the original full report, frozen
source manifest and delivered RBF. `resources-after/` retains the completed
user fit and its cost comparison; `hardware/` retains the original MiSTer
screenshots and their numerical improvement. Root `output_files` is not used
as a historical baseline.
