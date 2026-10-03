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

### Performance target and FPGA resource budget

2026-10-03 scope clarification: offer the ordinary 86Box 286 speed profiles
through 25 MHz, plus a maximum mode using the core's validated capability.
Further peak-throughput work must respect the user's limited FPGA headroom.
The retained 50 MHz emulator entry is a custom attribution profile, not a
required product speed or score target.

| CHECKNUM observation | Dhrystones per second | K Whetstones per second |
| --- | ---: | ---: |
| Native 86Box 286 at 25 MHz, retained P11 control | 4143 | 70.9 |
| User-confirmed MiSTer combined P18/P19 RBF, maximum mode | 6906 | 121.6 |
| Improvement over the 25 MHz control | 66.69% | 71.51% |

These use the same numeric benchmark at different configured clock rates.
Measured peak throughput is sufficient for the revised scope; it does not
calibrate a selectable 25 MHz hardware profile or establish instruction timing
equivalence. Separate CheckIT reports 6765 / 121.6K on this MiSTer RBF and
must not replace the CHECKNUM row.

The combined fit uses 30,039 / 41,910 equivalent ALMs (72%), 35,676 physically
placed ALMs (85.13%), and 416 / 553 M10Ks (75%). Placement and routing headroom
is limited; the equivalent logic count alone should not describe the reserve.
See the [combined fit](P18_P19_COMBINED_RBF_20261002.md) for provenance.

Recommendation: retain the current implementation and treat measured throughput
as sufficient for this scope. Park cache-capacity, deeper-queue and extra
lookahead experiments. Functional compatibility and physical timing compliance
remain separate unfinished work.

Future speed selection should share one CPU and reuse timing-policy/control
where feasible, keeping PIT/RTC and required SDRAM service independent of CPU
selection. Prefer execution enables and a shared timing policy over adding new
physical clock domains; CPU/BIU timing and prefetch still need a consistent
profile contract. The ordinary Intel-family reference entries are 6, 8, 10, 12.5,
16, 20 and 25 MHz. Its display label "12" actually sets 12,500,000 Hz in the
inspected 86Box table; preserve explicit units when naming/calibrating profiles.
Add Maximum, bypassing optional historical delays while retaining real
dependencies. Prefer resource-neutral changes or small shared control logic;
no zero-cost implementation or fitted profile overhead is established yet.
Measure added ALMs/registers/M10Ks and critical paths before adopting profile
logic; do not duplicate CPUs or increase buffers just to select a speed.

### Physical timing compliance and maximum speed

Closing timing at 50 MHz is not a product requirement. Positive setup and hold
at every actual operating clock, under the relevant constraints and models,
remain required for a validated implementation. Benchmark success measures
throughput and does not replace that physical timing requirement.

The current RBF runs at a configured 50 MHz, with worst setup -1.519 ns and
reported Fmax 46.47 MHz. That report is not a validated lower-frequency RBF.
The current common 50 MHz CPU/bridge/memory clock relationship is valuable.
Following the user's concern about SDRAM clock alignment, preserve it as the
first choice and seek structural timing improvements with neutral or small
measured resource cost, without additional cache capacity or clock domains.
Do not require an expensive redesign just to match an emulator score.

A lower physical frequency remains a possible architecture alternative, not a
cheap assumed fix or an action authorized by this specification. Changing CPU
frequency alone may require additional domain crossings, synchronization and
latency. Changing a larger domain also affects SDRAM, clock constraints and
device time bases. Its full cost must be evaluated before selecting it. Maximum
means the fastest validated setting within the resource budget; while the
current physical domains remain at 50 MHz, those paths must close at 50 MHz.

CPU, bridge, devices and CDC relationships must be considered together. The
current worst system paths include CPU BIU admission into Sound Blaster DSP;
other paths stay in the 50 MHz system domain. Lowering only the CPU cannot be
assumed to close them. The existing /2 debug clock is a specific related-clock
path, not acceptance for arbitrary frequencies or all system timing. An OSD
throttle or added historical waits also does not
automatically relax the physical register clock period. Preserve independent
device time bases when changing clocks and specify any legitimate timing
exceptions from actual control behavior.

No replacement frequency or proportional benchmark gain/loss is validated by
this documentation update. No new profile, RTL, benchmark, functional test or
synthesis is introduced.

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
