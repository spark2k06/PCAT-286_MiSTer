# PERF01 bridge response: functional evidence, 2026-10-02

This bundle records directed functional checks and physical-SDRAM simulation
workloads for the bridge response experiment. It does not establish FPGA
50 MHz timing closure or report measured DOS CheckIT results. Timing and
warm-reset machine evidence are maintained separately.

## Scope

- `response/`: the same synchronous response contract with candidate and
  frozen baseline bridges, both normal and divided CPU clocks, Icarus and
  Verilator. Each clock case reports 159 checks. Lint logs are intentionally
  empty on success. Candidate normal-clock RAM/ROM replies are consumed on
  the backend completion edge; the baseline and divided clock remain registered.
- `bus-latency/`: existing bridge contracts under reference, P01/P02, and
  production options; fetch, arbiter, memory policy and DMA/refresh checks.
  These are existing run logs. Only the source/configuration guards actually
  produced by each runner are included; missing guards are not synthesized.
- `mutation-audit/`: four deliberately broken bridge variants rejected by the
  directed response contract. `receipt.json` pins input and mutant hashes;
  `*.run.log` contains the expected failures. These failures are audit success,
  not unexplained production test failures.
- `cancel-pipeline/`: bridge, memory port, P03 code buffer, RAM data buffer and
  retained controllable backend. Both bridges pass 171 checks, 18 CPU
  acceptances, 10 CPU responses, 15 physical completions and one write.
  Cases include hits, prephysical cancellation, accepted data/code misses,
  coincident or delayed replies, a new fetch during drain and an accepted
  write completed once. A simplified synchronous CPU consumer checks data and
  stale READY. No real CPU execution, DMA or physical SDRAM occurs in this bank.
  Verilator is used because the existing cascaded buffer composition has a
  known Icarus delta scheduling loop; this omission is explicit in the runner.
- `profiles/`: four synthetic kernels with P03 disabled/enabled, eight runs
  per build (16 total), frozen configuration and source manifests. The
  physical SDRAM model includes refresh but excludes DMA/HPS/IRQ contention.
  The `whetstone` kernel is fixed-point synthetic work, not CheckIT's software
  floating-point implementation. Architectural signatures, write counts and
  source guards must be compared before interpreting cycle savings.

## Comparator and source-binding controls

`audit-controls/` preserves the exact final control runner, its receipt, the
source-binding block actually exercised, and the 11 comparator case logs.
The receipt covers two successful positive controls and 18 expected rejections:
10 negative comparator cases and eight negative source-binding cases.

These are controls of the workload parser/comparator and the source-binding
block extracted from `check_at_timing_closure.py`. They did not compile RTL,
run TimeQuest, perform a new STA, or prove that the candidate meets 50 MHz.
The source-binding control accepts an owner-only change while rejecting
missing, duplicate and unrelated CPU/configuration/firmware/harness inputs.
The comparator controls reject missing or malformed architectural signatures,
changed instruction counts, disabled RAM buffering and invalid source receipts.

`audit_profiles_and_binding_final.py` is copied byte-for-byte from
`build/perf01-audit-controls/`. Its original dependency paths remain intact:
`final-checked-scripts` pins the exercised checker/comparator/parser versions,
and the runner reads the frozen baseline workload and owner-experiment inputs.
The receipt hashes identify those tools and the extracted binding block.
Original case datasets and RTL are deliberately omitted from this compact
bundle; the comparator logs and receipt retain every observed rejection reason.
## Provenance and integrity

`provenance.json` records the exact original absolute path, packaged relative
path, byte size and SHA-256 for every copied file. Original logs and manifests
are copied byte-for-byte; paths inside them continue to identify their original
builds. `profiles/candidate/manifest.json` is the snapshot manifest from the fit
run directory, identifying frozen compilation inputs, not a timing PASS receipt.
The baseline profile comes from `build/perf01-response-baseline-20261002`;
the candidate comes from `build/perf01-bridge-response-fit-20261002`.

`files.sha256` covers every packaged file except itself, including this README
and provenance. Build transcripts, generated C++, objects, simulation binaries,
ROM binaries and mutated RTL copies are omitted to keep the bundle compact.

## Guarded comparison

`latency-comparison-guarded.json` is included. It is the authoritative guarded comparison of the two frozen sets of eight workload logs.

