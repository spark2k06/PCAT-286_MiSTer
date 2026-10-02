# P09: SDRAM owner response evaluation

Date: 2026-10-02. Status: **evaluated in simulation; not selected for production**.
This PERF01 experiment removes one internal read-response register stage while
preserving the SDRAM controller and its physical capture. The synthetic
CheckIT-shaped kernels use only 0.03–0.11% fewer cycles with production buffers; the
working-set kernel gains 2.01%. The production owner is unchanged.

The retained [evidence inventory](../evidence/perf01-sdram-response-20261002/README.md)
contains the exact comparison, logs, source manifests and a reproducible patch.
This is a documentation milestone recording an evaluated alternative, not an
assertion of FPGA timing closure for that alternative.

## Candidate and source isolation

KFSDRAM already registers `data_out` and `read_flag` together. The current owner
copies that pair into another data/valid register before returning it upstream.
The [candidate patch](../evidence/perf01-sdram-response-20261002/reproduction/owner-direct-response.patch)
forwards the controller's registered pair directly. It preserves registered
request admission/launch, KFSDRAM's DQ sampling, commands, clock, CAS latency,
refresh cadence, byte mapping and physical write completion.

An active, issued read qualifies each valid beat. A single read presents READY
with that beat; a four-word code fill presents READY only with beat four. The
owner releases the request on the edge consuming the final response.
`physical_idle` and acceptance still require `kf_idle`. The candidate saves one
read-response clock, but cannot accept a new transaction before the physical
controller is idle.

The reference was frozen under `build/perf01-response-baseline-20261002/work`
from `b5a7c927de7db56145b7b721138e67968c0f8c8f` and its recorded working tree.
An independent file copy under `build/perf01-owner-experiment/work` changed only
the owner. [The paired source manifest](../evidence/perf01-sdram-response-20261002/private-sources.json)
records **1,195 files per variant**; final source guards found both roots
unchanged during testing. CPU, bridge, buffers, controller, firmware and test
sources are identical within the A/B pair.

| Owner source bytes | SHA-256 |
| --- | --- |
| Frozen baseline | `06567e808d7d8a9c444efeb60c9ac163eb573a9e1e33946ef63ac8a5738f2992` |
| Candidate | `63ab5b6259a661565d7da042118d558211dcc33bf0c908cb7523ae0c217b6f5a` |

The [frozen project manifest](../evidence/perf01-sdram-response-20261002/baseline/frozen-manifest.json),
[configuration](../evidence/perf01-sdram-response-20261002/baseline/config.tcl),
and compiled-source manifests for
[baseline](../evidence/perf01-sdram-response-20261002/baseline/compiled-sources.sha256)
and [candidate](../evidence/perf01-sdram-response-20261002/candidate/compiled-sources.sha256)
record actual inputs. Tests use production CPU options, `PCAT_PROFILE=1`, the
physical SDRAM owner with periodic refresh, and the 1 KiB RAM read buffer.
P03 off is an explicit comparison; P03 on is the production code-buffer setting.

## Measured fixed-work comparison

Counts are elapsed 50 MHz clocks from directed firmware, not DOS CheckIT scores.
No hardware performance measurement of this prototype was made.
The firmware named `whetstone` is a fixed-point synthetic workload, not the
floating-point software benchmark executed by CheckIT/CHECKNUM.

| Kernel | P03 | Baseline clocks | Candidate clocks | Saved | Fewer clocks |
| --- | ---: | ---: | ---: | ---: | ---: |
| Dhrystone | 0 | 1,078,263 | 1,032,337 | 45,926 | 4.2593% |
| Dhrystone | 1 | 845,438 | 844,528 | 910 | 0.1076% |
| Whetstone | 0 | 1,032,396 | 970,535 | 61,861 | 5.9920% |
| Whetstone | 1 | 701,469 | 701,279 | 190 | 0.0271% |
| Working set | 0 | 1,207,584 | 1,134,290 | 73,294 | 6.0695% |
| Working set | 1 | 956,222 | 936,999 | 19,223 | 2.0103% |
| Dhrystone 2.1 | 0 | 1,443,493 | 1,342,756 | 100,737 | 6.9787% |
| Dhrystone 2.1 | 1 | 917,710 | 916,684 | 1,026 | 0.1118% |

All eight pairs agree on complete GPR/FLAGS, backing-memory hash, retired
instructions, CPU writes and SDRAM writes. The
[full comparison](../evidence/perf01-sdram-response-20261002/profile-comparison.json)
retains all counters, signatures, per-class latency, owner statistics, buffer
statistics and hashes of the original logs. Speculative code-read counts may
change with scheduling and are recorded without imposing false equality.

The traffic explains the modest production CheckIT benefit. Dhrystone has
52,067 code hits and 36,960 RAM hits, but only 49 physical code fills and 656
RAM misses, against 21,124 physical writes. This response change accelerates
physical reads, leaving hits and writes directly unaffected. The working-set
kernel has 19,996 code fills and benefits more. Changed refresh phase can also
affect total time, so saved workload clocks need not equal read counts exactly.

## Directed validation and its limits

All seven stages in the
[validation receipt](../evidence/perf01-sdram-response-20261002/validation-summary.json)
exit zero. The receipt records full commands, environments, timestamps, log
locations and hashes; archived copies are mapped in the evidence inventory.

| Stage | Result |
| --- | --- |
| Physical capture | Both DQM wirings pass 28 transactions each: 16 writes and 12 reads. Both deliberate +4 ns skew controls produce the required invalid-read failure. |
| Registered entry | Icarus and Verilator each pass 79 checks and 6 read beats: payload retention, burst order, byte masks, frequent refresh, reset before launch and zero-lane rejection. Strict owner lint passes. |
| Physical owner unit | Both simulators pass 20 writes and 14 reads. |
| RAM read buffer | Both unit simulators pass; the Verilator memory-port/code-buffer/data-buffer chain passes CPU/DMA/loader coherence, refresh, burst and reset. |
| Code buffer | Both simulators pass hits, fills, byte lanes, invalidation and reset checks. |
| Memory port | Both simulators pass ownership, preaccept CPU cancellation, accepted-transfer draining and loader preservation. |
| CPU workload | Four kernels, each with P03 off/on, pass the original architectural checks and the A/B comparison above. |

The buffer pipeline and memory-port unit tests use an abstract backend. They
verify preserved contracts and coherence; capture, entry, physical-owner tests
and CPU workloads exercise the physical SDRAM path. This does not establish
physical CPU cancellation at every individual burst beat.

Releasing the owner a response clock earlier also changes when dedicated DQM
pins return to their masked idle state. The finite DQ-window tests pass with
both the MiSTer A12/A11 wiring and dedicated DQM pins, and final READY preserves
the four-beat contract. Further adoption should cover physical cancellation
at every beat and a successor request queued immediately after final response.

## Decision and following SDRAM opportunities

Retain the alternative as an experiment. There is no Quartus synthesis, fit,
all-corner setup/hold analysis or hardware run for it. The changed registered
response path into cache/bridge consumers needs its own timing evidence; the
existing 50 MHz closure cannot certify this netlist. A change covering hits and
writes at the bridge has a broader measured opportunity in these workloads.
The two candidates were evaluated independently; gains cannot simply be added.

Physical writes remain frequent. A later evaluation can measure post-write
recovery, precharge and owner turnaround separately before changing them.
It must preserve one accepted transaction, byte enables, completion ordering,
CPU cancellation/draining, loader/DMA coherence and physical write recovery.
Early write acknowledgement or posting would introduce a new completion
contract and is not justified by this read-response experiment.

Keeping a row open could reduce repeated ACTIVATE/PRECHARGE cost for nearby
accesses. It requires explicit bank/row state, conflict handling, bounded
refresh service, legal read/write turnaround and enforcement of tRAS, tRP,
tRCD and write-recovery constraints. The current functional pin model checks
row ownership, command order, DQM and a finite CL2 read window; it is not an
exhaustive SDRAM timing/retention model. Expand that physical contract before
using it to accept an open-row controller, and preserve the shared XT behavior.

This milestone neither reopens nor completes the deferred full CPU regression.
