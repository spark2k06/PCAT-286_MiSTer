# PERF01 real CHECKNUM memory-control attribution

See [P12](../../optimization/P12_REAL_CHECKNUM_MEMORY_ATTRIBUTION_20261002.md).

- `ideal/` and `pcat/` retain both complete guest outputs, final profiles,
  phase snapshots, coherent CPU samples, input configuration and build/run
  identities. `measurement.json` explicitly classifies the old runner's
  cleanup timeout and reconstructed receipt; its host exit code is unavailable.
- `memory-attribution.json` checks complete guest RC0/ALL_DONE, actual 50 MHz /
  8 MHz clocks, final publication and identical initial images, then computes
  rates and separate function-phase counts. Its host issue opt-in is documented.
- `trace-footprint.json` describes bounded samples and physical-address
  conflicts. Raw CSVs remain under the ignored measurement workspace; their
  exact paths, counts and SHA256 values are retained in `manifest.json`.
- `adapter-build.json` and `adapter-smoke.log` identify and check the corrected
  memory-control adapter. The reused CPU objects remain unchanged. The old
  immediate control uses the earlier profiler build without shadow tags/CSVs;
  it repeats the independently completed clean P11 control's two exact scores.
- `recover_completed_receipt.py` preserves how guest outcomes were recovered
  after the old runner failed to save its receipt during host teardown. Both
  processes were absent, guest output was complete and final profiles existed.

Original disk bytes are not versioned. `manifest.json` links all copied receipts
to their local source bytes and verifies that the user's source VHD is intact.
The two deliberately incomplete early adapter attempts remain private and
cannot supply scores; their classifications are retained in that manifest.

Reproduction uses `tools/perf01/README.md`. Private local binaries/images are
in `D:/GitHub/PCAT-286_MiSTer/build/perf01-real-memory-20261002/`.
This is a timing/control comparison, not a complete PCAT peripheral port or
electrical SDRAM validation. The 4 KiB candidate has a separate evidence bundle.
