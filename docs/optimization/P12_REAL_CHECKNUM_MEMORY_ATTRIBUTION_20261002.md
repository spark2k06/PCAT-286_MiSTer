# P12: real CHECKNUM with PCAT memory-control timing in 86Box

Date: 2026-10-02. PERF01 attribution milestone.

Running the unchanged CHECKNUM with production PCAT memory READY timing gives
**4804 Dhrystones / 88.6K Whetstones**, versus **7709 / 133.3K** with immediate
READY on the same SPK286 at actual 50 MHz. The reduced memory path reproduces
most of the observed MiSTer gap. The real application has much more instruction
buffer pressure than the earlier synthetic kernel. This supplies the measured
basis for the [4 KiB instruction-buffer candidate](P13_CODE_BUFFER_4K_20261002.md).

## Complete guest results

| Execution | Dhrystones/s | K Whetstones/s | Whole-application BIOS ticks |
| --- | ---: | ---: | ---: |
| SPK286, immediate READY, repeated private adapter control | 7709 | 133.3 | 209 |
| Same SPK286, old PCAT 512 B code / 1 KiB data memory chain | 4804 | 88.6 | 287 |
| User-observed P10 MiSTer candidate, maximum speed | 4361 | 83.7 | Not captured |

Both private guests returned `RC TICKRUN 0` and `ALL_DONE` and published final
memory profiles. The immediate result exactly repeats the earlier complete
[P11 measurement](P11_86BOX_50MHZ_COMPARISON_20261002.md), whose host exited with
RC0. See the [receipt bundle](../evidence/perf01-real-memory-20261002/README.md).

The PCAT chain gives 62.32% / 66.47% of the immediate rates. It is 10.16% / 5.85%
above the supplied hardware observation. The absolute score reduction from
immediate READY accounts for 86.77% / 90.12% of the corresponding observed
immediate-to-hardware score gap. These are comparisons of this reduced model
and a single hardware observation; they are not independent lost-cycle
classifications or an exact model of the residual difference.

Whole-application durations are 11.479409 and 15.763590 guest seconds. CHECKNUM
adapts iteration counts and includes calibration, loading and formatting;
its whole-application duration is not a fixed-work benchmark. Host elapsed times
through the final coherent sample were 2990.887 and 4015.545 seconds. Host
execution speed affects waiting time for the result, while scores use guest
BIOS ticks.

### Host teardown qualification

The old measurement runner observed complete guest output, then timed out in
both its monitor-exit and SIGTERM waits. The processes were absent when the
receipts were recovered. Their final profiles, all original coherent samples,
guest output and disk/source hashes remain available; host exit codes were not
captured and are explicitly `null`. No clean host exit is claimed for these two
private runs. The recovery script and classification are retained in the bundle.

The launcher now freezes a private runner, drains its PTY during cleanup and
retains an explicit timeout/termination status. The summary requires an explicit
`--allow-host-teardown-issue` to use such classified complete-guest outcomes.
The earlier clean P11 control supplies an independent identical score check.
The sampler also reads CPU and RTL ports during one stop and records transient
thread-stop timeouts as skipped samples. It resumes the owned process without
accepting incoherent state. Original failed candidate attempts remain separate
from complete accepted benchmark arms.

## What was brought from PCAT

The private Verilator top uses the production AT bus bridge, common memory
port, instruction read buffer, RAM data buffer, SDRAM owner and KFSDRAM
controller. Each CPU request traverses their real command, acceptance, fill,
refresh and return states to generate READY. The SPK286 CPU model objects are
reused unchanged; the normal 86Box build products and sources are preserved.

86Box still owns guest data values and peripherals. Physical SDRAM DQ in this
timing model is zero and its returned data is discarded. The original host
memory operation occurs exactly once when the CPU accepts READY. Data values
do not choose tags, arbitration or controller timing states. This models
memory control/service timing; it does not validate cached data or electrical
SDRAM behavior. Separate byte-scoreboard and physical-chain directed checks
cover the relevant data/coherence contracts.

Routed accesses cover conventional RAM, system BIOS and extended RAM through
25FFFFh. A20 and the reset BIOS alias are resolved before tags. I/O, INTA, video,
option ROM and chipset devices remain in 86Box. DMA/loader and abstract AT
refresh arbitration are absent; KFSDRAM's periodic refresh is active. The
reduced adapter does not implement PCAT's EMS reservation/remap above CPU
address 2 MiB. The benchmark's captured traffic uses conventional RAM and HMA.
The shortened SDRAM initialization wait is outside the benchmark.

Both guests start from identical private image bytes, SHA256
`7a50d61047b47a4913474a29e90bc35ebd3a666824509c9deffd8904ef740b74`, and the same
calibrated CMOS and configuration: MR BIOS 1.65, 2 MiB RAM, EGA, IDE, software
floating point, actual 50 MHz CPU and 8 MHz ISA. The accepted CHECKNUM SHA256
remains `38324ad68abe13f143ff76dfcdee45f424ff25ce78f67883214ce6b82fa637e6`.
The original VHD's SHA256 remains unchanged. Hardware image/load placement,
memory-manager settings, peripheral contention and repeat variation still need
matching before attributing the remaining difference.

### ISA frequency and the RAM path

The two arms retain the same measured 8 MHz ISA setting. The local 86Box
`src/cpu/cpu.c:cpu_set_isa_speed()` selects 8 MHz by default once the CPU bus
reaches that frequency. ISA's 16-bit width is separate from its clock;
[Intel's SIO datasheet](https://mark-ogden.uk/files/intel/publications/290571-001%2082378ZB%20System%20IO%28SIO%29%20and%2082379AB%20System%20IO%20APIC%28SIO.A%29-Mar96.pdf)
specifies ISA SYSCLK from 6 to 8.33 MHz.

Production CPU, instruction/data buffers and SDRAM owner/controller use
`CLK_50M`; the reduced adapter also advances those blocks once per CPU clock.
RAM transactions do not pass through an 8 MHz ISA divider. The measured RAM
READY difference therefore does not originate in this ISA frequency setting.
I/O/device timing and hardware contention remain separate scope limits.
PCAT has no global 8 MHz ISA clock in this path: its functional AT transaction
bridge and chipset run on `CLK_50M` and await device READY. That does not imply
one transaction per FPGA clock, nor reproduce all electrical timing of an ISA
slot. The 8 MHz setting above belongs to 86Box; it must not be presented as
matched PCAT peripheral timing. A later I/O comparison would need the actual
device transaction counts and waits in both implementations.

### Fast mode and optional historical timing

2026-10-03 user clarification: retain a fast mode without imposed historical
T-states, then offer optional T-states and speed profiles. This is the intended
product direction, not an implemented timing selector. Current CPU optimization
macros are implementation choices, not the future historical timing mode.
This direction follows the separation already specified in the
[SPK286 timing draft](../../vendor/spk286/SPK286_TIMING_MODEL.md); its conceptual
mode names should not be mistaken for an exposed historical profile today.

Fast mode may reduce actual memory/bridge stalls through coherent buffers,
posting and overlap. It must preserve architectural work, device register
semantics, ordering and independently clocked peripherals. Never rescale
PIT/RTC time, change benchmark work/results or relabel clock units to match an
emulator score. The immediate-memory 86Box arm is a service-model comparison,
not a required FPGA score. Native 86Box timing also needs its own reference
qualification.

The retained PERF01 evidence identifies real service improvements and the P19
refresh correction; no result manipulation is identified in that review.
Extra buffering/overlap does not establish stock IBM 5170 cycle behavior.
Historical timings must specify the chosen CPU and board profile, including
how caches/posted service obey that observable schedule. Merely delaying
instruction retirement or altering nominal MHz is insufficient.

86Box is the principal implementation reference for this project, not the sole
timing authority. Use Intel/IBM diagrams and tables to define the contract,
86Box to inspect practical instruction/prefetch/wait handling, and real-286
measurements where available to resolve discrepancies. As another code
reference, [MAME's 286 implementation](https://github.com/mamedev/mame/blob/master/src/devices/cpu/i86/i286.cpp)
contains instruction timing tables but explicitly questions some entries;
it is supplemental evidence, not an exact-bus oracle. Total instruction cycle
counts and Ts/Tc/READY sequencing need separate specifications.

Real-hardware access is through the user's collaborators, who can execute DOS
programs on 286 systems at 6 and 12 MHz, including both speeds on the same PC
as reported by the user. A local 286 or direct signal capture is not available.
Plan self-contained DOS measurement programs with fixed machine-code blocks,
known work/signatures, PIT ticks, calibrated measurement overhead and textual
results. Record the board/BIOS, speed selection, memory and interrupt policy
alongside the result. Paired runs on one machine are especially useful for
distinguishing CPU scaling from fixed peripheral or memory-service cost.

Those programs can measure instruction/loop and memory/I/O behavior and expose
prefetch effects. They cannot by themselves observe individual Ts/Tc pins or
prove every internal timing transition. Keep that measurement boundary explicit
and use the manufacturer bus diagrams for the corresponding specification.
No such new DOS program is implemented or executed in this documentation work.

The next search prioritizes manufacturer-documented AT behavior compared with
86Box. See the [functional audit](../AT_FUNCTIONAL_REFERENCE_AUDIT_20261003.md)
for source findings, reference limitations and proposed future cases.

### Requirements for future cycle accuracy

This is a future specification task. PERF01 currently measures throughput of
the implemented SPK286/PCAT path. Matching nominal MHz, CHECKNUM scores or
architectural results does not establish historical cycle accuracy. Positive
FPGA setup/hold establishes compliance with the selected physical timing
constraints; it does not establish the guest-visible timing of an original AT.

First define the reference: CPU model/stepping, board/chipset, CPU and bus
clocks, RAM wait states, device configuration and any buffering/cache policy.
Specify whether each frequency denotes a physical clock input, a modeled CPU
cycle or a nominal software setting, including the relationship between them.
The present 50 MHz comparison counts SPK286 model clocks; BIOS/CheckIT
calibration loops do not define this future reference contract. The native
86Box 286 remains a useful comparison, with its own timing model requiring
validation against the chosen hardware reference.

| Area | Required future specification and evidence |
| --- | --- |
| CPU execution | Instruction timing under specified operand/addressing conditions, prefetch refill/consumption and overlap with execution; include taken branches, strings and event entry/return. |
| AT bus | Reference Ts/Tc/Ti sequencing, READY sampling and wait insertion, byte/word/unaligned transfers, I/O recovery and interrupt acknowledge. |
| Ownership and events | HOLD/HLDA, LOCK, DMA and refresh arbitration, interrupt recognition and reset/shutdown timing relative to the selected clocks. |
| Devices | Per-device acceptance/completion latency, relevant peripheral clocks and interrupt/DMA cadence; distinguish ISA width from frequency. |
| Memory buffers | Define which fetch/data transactions and latencies the reference exposes, including writes and self-modifying code; internal hits must obey that observable contract. |

The current bridge explicitly documents a functional transaction boundary and
defers historical Ts/Tc and an 82288/82289 pin-level implementation:
[bridge source](../../rtl/spk286_integration/spk286_at_bus_bridge.sv).
The present co-simulation retains actual PCAT RAM-controller state timing,
while I/O, INTA and devices remain in 86Box and DMA/AT-refresh arbitration is
absent. It cannot supply acceptance for those omitted timing requirements.

Keeping a 50 MHz FPGA clock may be possible through clock enables and wait
states once the reference cadence and phase resolution are specified. CPU
execution, prefetch, bus ownership and peripheral time must advance consistently.
Adding a fixed delay at instruction retirement alone would not reconstruct
their overlap or the ordering of observable events. Optimizations may remain
internally where they preserve the specified observations; each such claim
needs directed evidence rather than assuming functional equivalence preserves
historical timing.

Future acceptance should compare timestamped CPU/bus/event traces against the
defined reference, identify the first divergent transaction and verify both
architectural results and elapsed reference cycles. Start with directed
instruction, READY, I/O, interrupt, DMA and refresh cases, then real workloads.
Use the Intel manuals already catalogued in
[SPK286 source notes](../../vendor/spk286/docs/SOURCE_NOTES.md) together with
the chosen board/device documentation and hardware measurements. Aggregate
benchmarks remain a performance check and cannot replace those trace comparisons.
No timing-policy, clock, RTL or configuration change is introduced by this note.

## Real application phase counters

Frontend signature and relative far-call addresses identify both function
phases without modifying guest bytes or assuming its DOS load segment. The
phases include their calibration, timed loops and interrupts.

| Old PCAT-chain counter | Dhrystone phase | Whetstone phase |
| --- | ---: | ---: |
| CPU clocks | 140,157,019 | 634,462,602 |
| Retired instructions | 7,522,203 | 50,390,718 |
| Instruction-buffer hits | 9,537,146 | 60,720,866 |
| Instruction-buffer misses/fills | 2,473,075 | 11,414,980 |
| RAM-data-buffer hits | 4,710,852 | 11,218,015 |
| RAM-data-buffer misses | 378,351 | 1,931,505 |
| Mean READY waits per code transfer | 3.899 | 3.472 |
| Mean READY waits per data read | 2.549 | 3.075 |
| Mean READY waits per data write | 7.366 | 7.354 |

Code hits are approximately 79.41% / 84.18%, rather than the synthetic kernel's
99.91%. Data hits are approximately 92.57% / 85.31%. Exact transfer counts,
owner requests, per-status waits and phase snapshots are retained in JSON.
READY waits and queue-empty counts overlap internal CPU execution. They cannot
be added to CPU clocks or each other as separate lost time. Adaptive work counts
differ between timing arms; absolute phase clocks alone do not compare rates.

## Counterfactual tags on exactly the accepted real traffic

These warmed tag models retain write invalidation/update and no write
allocation. Two-way variants use read LRU. They predict miss counts for the
same accepted stream, not a future implementation's benchmark score or timing.
Their old-capacity hit/miss phase totals exactly match the actual RTL counters.
They omit cancelled fills/reset flushing during boot; the benchmark phases
contain neither that boot mismatch nor a CPU reset.

| Code-buffer model | Dhrystone misses | Whetstone misses |
| --- | ---: | ---: |
| 512 B direct, actual capacity | 2,473,075 | 11,414,980 |
| 512 B, two ways | 2,420,556 | 11,740,102 |
| 1 KiB direct | 1,199,801 | 7,368,187 |
| 2 KiB direct | 187,515 | 3,469,354 |
| 4 KiB direct | 1,399 | 846,308 |
| 8 KiB direct | 1,231 | 193,512 |

| Data-buffer model | Dhrystone misses | Whetstone misses |
| --- | ---: | ---: |
| 1 KiB direct, actual capacity | 378,351 | 1,931,505 |
| 1 KiB, two ways | 421 | 190,439 |
| 2 KiB direct | 403 | 1,634,679 |
| 4 KiB direct | 363 | 31,422 |

Increasing associativity alone does not cure the small instruction buffer.
Doubling direct-mapped data capacity helps Dhrystone far more than the complete
Whetstone phase. These differences justify real whole-application measurements
when selecting any later candidate.

The first 250,000 accepted operations of each phase visit 420 / 434 distinct
eight-byte code blocks, or 3360 / 3472 bytes. Every old code index has multiple
distinct blocks. The bounded data samples have 245 / 180 distinct read words,
with 61 / 30 conflicting old data indices. Dhrystone data addresses 4CAA4h and
4D6A4h differ by 3072 bytes and map to the same old data index. Whetstone also
alternates words from distinct stack/data regions at identical indices. These
samples demonstrate traffic and conflicts; their unique footprint does not
establish simultaneous occupancy or the entire phase's working set.

## Implementation and next decision

Tool milestone: `53a9cad`. The subsequent candidate `0399806` implements 4 KiB
of code with synchronous tags, keeps hit latency and leaves the 1 KiB data
buffer intact. Its directed checks and separate candidate measurement are in
[P13](P13_CODE_BUFFER_4K_20261002.md). No CPU functional H-story is reopened by
this platform-memory finding.

At the user's request, the next production change will be selected after their
MiSTer test of that fixed candidate and its completed 86Box measurement. Data
conflicts, hit turnaround and physical writes remain measured opportunities;
their potential gains require separate A/B evidence. No full regression or
FPGA fitter/timing closure was run for this attribution milestone.

## Later AT ownership confirmation (P19)

The memory-only model's omitted AT refresh/HOLD service is now observable in
real CHECKNUM. [P19](P19_AT_REFRESH_PLATFORM_ATTRIBUTION_20261002.md) adds the
unchanged production 32-clock requester and arbiter to identical P17 controls:
the first integer outputs are 6138 without that service and **5666 with it**,
exactly the P17 MiSTer observation. The math/guest-exit controls are still in
progress; the initial integer capture is retained separately as partial evidence.
This does not retroactively change this document's original P10 rates or traces.

The corrected AT requester follows real PIT channel 1 OUT rising edges. A
BIOS-programmed divisor 18 at 1.193182 MHz gives about 15.1 us, whereas the old
32-clock functional requester waits only 0.64 us plus service at 50 MHz.
Physical SDRAM AUTO REFRESH remains independent and active. CPU HOLD/HLDA,
arbiter priority and posted-write drain ordering remain explicit in the model.
The new private adapter samples the real 86Box PIT OUT1; its integer result is
pending. ISA speed remains 8 MHz in these matched runs, and this refresh cost
must not be mistaken for an ISA frequency difference or host CPU capacity.

Exact AT cycle accounting remains open: service occupancy, CPU boundary/HLDA
latency, wait-state policy and PIT/PIC/DMA behavior need measured traces for a
cycle-accurate platform. Corrected functionality and a matched throughput
observation do not establish complete cycle accuracy.
