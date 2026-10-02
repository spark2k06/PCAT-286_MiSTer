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
