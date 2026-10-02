# PERF01 entry-overlap review evidence

The [P17 review](../../optimization/P17_MEMORY_PATH_THROUGHPUT_REVIEW_20261002.md)
records a private bridge/port entry-overlap prototype and larger write-path
opportunities. Production RTL, CPU options, cache capacities and SDRAM timing
remain unchanged. No FPGA fit or hardware result is claimed.

## Evidence

- `source-manifest.json`, `candidate.patch`: frozen control/candidate inputs
  from PCAT `ea283d8`. Only bridge/port RTL differs; the private smoke's explicit
  hit timing expectation changes from two to one. CPU inputs are identical.
- `directed-comparison.json`, `directed/`: all four fixed-work kernels, both
  P03 settings, full GPR/FLAGS/memory signatures, architectural/write-count
  equality and elapsed-clock results. Actual gains are 9.46–11.40%.
- `directed/*/ideal-writes/`: simulation-only physical-write bypass controls,
  preserving architectural results. They establish potential, not a working
  posting design or achievable hardware gain.
- `completed-baseline-review.json`: derivation from completed P16 CHECKNUM,
  including full-phase hit/wait statistics and bounded write-address locality.
  Adjacent writes omit intervening reads/refresh and cannot establish row hits.
- `validation/`, `small-cancel/`: strict lint, two-simulator memory-port
  checks, cache/coherence/cancel adapter smoke and 171-check composed cancellation
  at small and production synchronous-tag capacities.
- `validation/original-counter-control-run.log` intentionally rejects the
  old diagnostic counter check on P16 control. Both adapted 512-line variants
  pass. The first candidate failure is retained as `cancel-512-run.log`.
  This changes observation of hit-count timing, not architectural expectations.
- `ongoing-dos/`: retained **incomplete** private CHECKNUM snapshot, frozen
  disk/configuration/CMOS/build identities and exact unchanged CPU object hashes.
  It is not a completed guest receipt. Use final results before adoption.
- `provisional-integer/`: two read-only guest-RAM observations agree on
  `6138\r\n` at the output buffer 4CB38h after entry into Whetstone. The binary
  matches the ongoing arm. Other matched numeric strings are static runtime
  messages and are not treated as results. Integer +8.33% over completed P16
  is provisional until normal CHECKNUM output/guest completion is captured.
- `inventory.json`: retained hashes and production/private source guards.
- `measurement/`: complete P16/P17 CHECKNUM output, guest RC0/ALL_DONE, final
  counters, source/CPU/configuration identities and classified host teardown.
  Confirms 6138 / 113.6K (+8.33% / +10.40%). Its separate byte inventory is
  `measurement/retained-files.json`; earlier incomplete snapshots are preserved.
- `promotion/`: seven production integration scripts and additional machine
  A20/ROM-sink transactions pass. Production matches the measured prototype
  except comments, with unchanged CPU/cache/controller/configuration inputs.
  Initial fixture failures and the invalid near-Jcc ROM control are retained
  alongside their explanation in `promotion/retained-files.json`. No full
  regression or hardware acceptance is inferred from these checks.

The kernel named `whetstone` is fixed point, unlike real CHECKNUM software
floating point. Its code-hit/miss latency labels assume asynchronous tags;
use aggregate code counts/latency and native buffer counters for this geometry.
Raw bus wait overlaps CPU execution and cannot be added to speedup estimates.
The ongoing 86Box model supplies guest values/peripherals; separate physical
pin tests validate data. DMA/HPS/abstract AT refresh are absent from its reduced
memory timing chain, although KFSDRAM periodic refresh remains enabled.

## Reproduce

From the repository, prepare a fresh private root:

```text
python3 tools/perf01/prepare_early_command.py --baseline-source build/perf01-entry-overlap-20261002/baseline --output build/fresh-entry-overlap
```

The baseline must be P16, before adoption of P17. A separate P16 checkout
also works; current production is no longer the historical control.
In WSL, run each frozen root's `scripts/test_checkit_directed.sh` with
`PCAT_BUILD_DIR` pointing to a separate `directed-baseline` or
`directed-candidate`, `PCAT_CODE_BUFFER_LINES=512`, and `PCAT_PROFILE=1`.
Then run `tools/perf01/review_entry_overlap.py` against that private root.
It preserves signatures and executes the ideal-write controls without Quartus.
The retained validation/analysis scripts describe bounded follow-up checks;
their paths must point to the fresh root when repeating.

Build the private 86Box probe with the frozen candidate's
`tools/perf01/build_86box_memory_probe.py`, reusing the recorded unchanged CPU
build objects. The ongoing arm records the precise launcher arguments. Use a
fresh arm/disk copy rather than reusing mutable guest output as a control.
