# Memory bus latency reduction at 50 MHz — 2026-09-22

The previous RBF omitted P01/P02 although the directed benchmark runner enabled
both. This concealed two extra bridge start states and a fetch-response bubble
in the physical configuration. This increment enables those existing functional
optimizations, adds P06 parallel address capture, and makes the affected simulation
runners read the project's performance switches from `config.tcl`.

CPU clock remains 50 MHz, `SPK286_AT_NO_DEBUG` remains enabled and the CPU divider
remains disabled. The register-execution import and 16 MiB RAM fixes are retained.
No cache or SDRAM timing-parameter change accompanies this increment.

## Implementation

P06 exposes a valid decoded memory address during the edge when the bridge
captures the CPU request. The downstream memory port captures its record on the
same edge. The bridge then enters COMMAND instead of spending an additional edge
in ADDRESS. Command acceptance and completion still require the retained records;
CPU READY and read data still come from the bridge's registered completion.

Eligibility requires a valid memory request to a word-capable target. I/O, INTA,
video and other byte-wide targets retain their previous sequence. Lane validity,
LOCK, split accesses and reset handling remain checked. The bridge reports busy
during its early address interval so arbitration cannot treat that interval as
an idle boundary. No CPU, physical SDRAM owner or KFSDRAM RTL is changed here.

The benchmark, bridge tests, full-machine tests and BIOS/LOADALL fixture now use
`scripts/at_performance_flags.sh`. Each records its active performance macros.
`PCAT_PERF_CONFIG` can select a frozen configuration for an explicit comparison;
the default is the actual project's config. The Quartus timing inventory also
records the performance macros for the fitted bitstream.

## Measured comparison

All three variants use the same optimized CPU, firmware, physical SDRAM model
and architectural scoreboards. The ideal-owner model is disabled. P03=1 is the
production code-buffer setting. These are synthetic directed workloads, not
execution of DOS CheckIt itself.

| Workload | Old RBF flags: P05 | P01/P02/P05 | P01/P02/P05/P06 | Throughput gain vs old flags |
| --- | ---: | ---: | ---: | ---: |
| Integer mix | 1,432,129 | 1,215,988 | 1,151,471 | +24.4% |
| Fixed-point mix | 1,198,833 | 1,018,477 | 961,554 | +24.7% |
| Working set | 1,380,742 | 1,140,571 | 1,087,135 | +27.0% |
| Dhrystone 2.1 fixture | 1,618,272 | 1,347,223 | 1,270,699 | +27.4% |

Counts are elapsed 50 MHz clocks. P06 by itself adds approximately 4.9–6.0%
throughput over the P01/P02 configuration; most of the total gain comes from
enabling P01/P02 in the real project. The measured physical-owner service time
per accepted read, write and code-line fill is identical across configurations.

Minimum CPU-bus wait latency for a data read drops from 11 to 8 clocks (220 to
160 ns); owner availability and refresh increase some accesses above that minimum.
Code-buffer hits drop from exactly 6 to 3 clocks (120 to 60 ns). These latency
counts exclude the terminal READY edge and are not sustained transfer intervals.

The [comparison receipt](bus_latency_50mhz_comparison.json) includes all 24 runs,
both P03 settings, active macros, full-state signatures, log hashes and per-access
latency decompositions. Earlier profiling reports now explicitly identify their
P01/P02 mismatch with the old RBF. Hardware CheckIt observations are recorded
separately below.

## User-reported hardware CheckIt result

On 2026-09-22 the user tested the bus-latency RBF and supplied a side-by-side
CheckIt screenshot with 86Box 5.3 build 8200 configured as an 80286 at 25 MHz.
The board retains the configured 50 MHz CPU clock and NO_DEBUG build above.
The previous board values come from the user's preceding CheckIt screenshot.

| System | Dhrystones | Whetstones |
| --- | ---: | ---: |
| Previous PCAT RBF, 50 MHz | 2,695 | 53.3K |
| Bus-latency PCAT RBF, 50 MHz | 3,400 | 67.1K |
| 86Box, 80286 at 25 MHz | 4,143 | 70.9K |

The observed board gains are **26.16%** in Dhrystones and **25.89%** in
Whetstones, consistent with the directed simulations' approximate 24–27% gain.
86Box still scores **21.85%** higher in Dhrystones and **5.66%** higher in
Whetstones than the updated board. These are single-run, user-reported results;
they do not isolate the remaining CPU, memory or emulator-model differences.
CheckIt's detected 34.87 MHz on the board is its estimate, not a change to the
configured 50 MHz clock or the fitted Fmax. The source image is
`codex-clipboard-cf292c12-9bb3-4a46-943d-2be6fed542d8.png`.

## Verification

- Three bridge configurations pass in Icarus and Verilator: original, P01/P02
  and the production candidate. Address-phase metadata and absence of premature
  command acceptance are checked. Existing acceptance stalls, stale READY,
  byte lanes, I/O splitting, identical back-to-back requests, LOCK, INTA and
  reset-abort checks remain.
- Fetch chaining passes both simulators: 26 bus/response checks plus waits,
  cancellation, backpressure and segment limits.
- Memory decode/arbitration and DMA/refresh/PIT tests pass both simulators.
- All 24 workload runs match GPR/FLAGS and a hash of the complete explicit
  backing memory, plus retirement, write and fast-register-operation counts.
  Both stages reduce elapsed clocks in every workload and P03 setting.
- Full production-machine elaboration and lint pass, with no new bridge latch
  or combinational-loop warning. The diagnostic completes with 107 memory beats,
  12 I/O writes, 32 IRQ0 observations, 27 refresh observations and four port-80 writes.
- Physical BIOS first fetch and 16 MiB isolation pass: 238 blocks and all 65,536
  BIOS bytes. LOADALL/XMS passes repeated LOADALL, extended copying, A20 and byte
  lanes at 50 MHz (5,333 clocks) and in the /2 diagnostic configuration (7,009 clocks).

```sh
bash scripts/test_at_bus_latency.sh
bash scripts/test_at_machine_boundary.sh
bash scripts/test_at_loadall_xms.sh
AT_CPU_DIV2_TEST=1 PCAT_BUILD_DIR="$PWD/build/loadall-div2" bash scripts/test_at_loadall_xms.sh
PCAT_PROFILE=1 bash scripts/test_checkit_directed.sh
```

The archived comparison under `build/bus-latency/` contains `baseline-config.tcl`,
`baseline-bridge.sv`, `p01-p02-config.tcl` and three workload directories. With
those artifacts, `python3 scripts/report_at_bus_latency.py build/bus-latency`
rechecks accounting, state equivalence, profile macros and the comparison table.

## FPGA build

A fresh isolated build completed successfully with Quartus 17.0.2 for
5CSEBA6U23I7 under `build/at-no-debug/20260922-bus-latency-50mhz/`.
Full compilation took 32 minutes 58 seconds; the additional four-corner timing
report took 2 minutes 7 seconds. The fitted inventory confirms P01/P02/P05/P06,
NO_DEBUG, zero debug observers and a 20 ns FPGA_CLK2_50 period.

The resulting [PCAT-286_BUS_LATENCY_50MHz.RBF](../../output_files/PCAT-286_BUS_LATENCY_50MHz.RBF)
is 4,073,332 bytes. SHA-256:
`28c4b7b31fe44d153eb0e88b44f18ed37f564342ffb8278c78ce64d03243700d`.
Its JSON and SHA-256 sidecars record the frozen source manifest and timing
reports. Packaging verified 342 current production inputs against that snapshot
and verified the copied binary. Previous RBFs are preserved.

Resource use is 28,603 / 41,910 ALMs (68%), 34,199 registers,
3,152,832 / 5,662,720 RAM bits (56%), 395 / 553 RAM blocks (71%),
38 / 112 DSP blocks (34%) and three PLLs.

| Timing corner | CLK2 Fmax (MHz) | CPU setup slack (ns) | CPU hold slack (ns) | Global setup slack (ns) | Global hold slack (ns) |
| --- | ---: | ---: | ---: | ---: | ---: |
| Slow, 1100 mV, 100 C | 40.57 | -4.648 | 0.247 | -20.779 | -2.813 |
| Slow, 1100 mV, -40 C | 40.86 | -4.472 | 0.239 | -21.417 | -2.607 |
| Fast, 1100 mV, 100 C | 75.35 | 6.729 | 0.132 | -10.817 | -1.205 |
| Fast, 1100 mV, -40 C | 89.33 | 8.806 | 0.115 | -8.897 | -1.139 |

**The build does not close timing at 50 MHz.** CPU setup improves from -6.018 ns
in the previous fitted build to -4.648 ns, and CLK2 Fmax from 38.43 to 40.57 MHz.
This does not establish a causal improvement for every path: fitting has changed,
and other margins worsen. In particular, slow/100 C memory-port setup is
-4.246 ns, SDRAM-owner setup -8.939 ns and SDRAM-output setup -7.388 ns.
The worst paths in those groups originate at `sysmem|init_reset_n` in the HPS
clock domain. They remain unresolved timing findings; no exception was added to
hide them. CPU-to-bridge and bridge-to-CPU setup remain positive in all corners.
Global setup failures include video paths; global hold failures include the
CLK2-to-HDMI framebuffer-stride crossing. TimeQuest also reports incomplete
constraints, so CLK2 Fmax alone is not a whole-design sign-off.

The CPU remains at the requested 50 MHz. The CheckIt run above confirms a
performance improvement on the user's board. It does not establish timing
closure across operating conditions or resolve the Windows 3.1 restart.
