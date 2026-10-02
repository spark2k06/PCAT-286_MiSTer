# P11: same-clock CHECKNUM comparison at 50 MHz

Date: 2026-10-02. PERF01 measurement milestone.

The primary performance comparison is **SPK286 in 86Box versus the same SPK286
in PCAT/MiSTer**, both at 50 MHz with matching CPU sources/options. The native
86Box 286 supplies an additional control. PCAT reaches
**56.57% of standalone SPK286's integer rate and
62.79% of its software math rate**.
The next attribution target is this integration gap.

## Results

All numerical scores use the accepted CHECKNUM executable, SHA-256
`38324ad68abe13f143ff76dfcdee45f424ff25ce78f67883214ce6b82fa637e6`. Both 86Box 50 MHz arms finished the whole application
with DOS RC0 and an `ALL_DONE` marker. The native repeat reproduced both scores
and exited normally on the host. Original outputs and receipts are in the
[evidence bundle](../evidence/perf01-86box-50mhz-20261002/README.md).

| Implementation | Configured CPU clock | Dhrystones/s | K Whetstones/s |
| --- | ---: | ---: | ---: |
| SPK286 in 86Box, P02/P05/P07 | 50 MHz | 7709 | 133.3 |
| PCAT on MiSTer, user-observed candidate | 50 MHz, maximum speed | 4361 | 83.7 |
| Native 86Box 286, additional control | 50 MHz | 8287 | 144.9 |
| Native 86Box 286, prior-frequency control | 25 MHz | 4143 | 70.9 |

The hardware observation is the earlier user-supplied CHECKNUM result from the
[bridge candidate](P10_BRIDGE_RESPONSE_20261002.md). Its separate CheckIT result
was 4361 / 84.1K; the matched numerical-program comparison uses 83.7K.

| Comparison | Integer rate | Software math rate |
| --- | ---: | ---: |
| MiSTer as a fraction of standalone SPK286 | 56.57% | 62.79% |
| Standalone SPK286 as a fraction of native 86Box | 93.03% | 91.99% |
| MiSTer as a fraction of native 86Box | 52.62% | 57.76% |

Reaching standalone SPK286's result would require hardware gains of
**76.77% / 59.26%** (integer / math). This is the primary PERF01 target.
For the additional native-reference comparison, standalone SPK286 requires
a further **7.50% / 8.70%** rate increase; hardware requires
**90.03% / 73.12%** to reach the native result.
These are increases relative to each slower result, which differ from its
percentage shortfall against the faster reference.

## Profiles and CPU identity

86Box commit `fa3343da5` adds `50 (test)` to the Intel 80286 family. Runtime
sampling verifies `cpu_s->rspeed = 50000000`, the selected native/SPK dispatcher,
ISA 8 MHz and ISA cycle divisor 6. The profile retains the 25 MHz CPU entry's
four memory/cache cycles. The 25 MHz control uses divisor 3.

The paired 50 MHz profiles select MR BIOS 1.65 / `mr286`, 2048 KiB RAM, original
86Box EGA, AT keyboard, no mouse, no dynarec, and the same IDE geometry
(1020 cylinders, 15 heads, 17 sectors). CHECKNUM selects software floating
point. Both start from byte-identical private DOS images, matching configuration
bytes and matching initial CMOS. Their source disk is
`D:/ISOs/MiSTer/286_win3.1.vhd`, preserved with SHA-256
`cc544775154d8f6093bb6075a21a00e3d391b979bd954ad811709d291555145f`.

The Verilated model is built from PCAT's current vendor CPU with P02 fetch
chaining, P05 parallel limit checks and P07 synchronous microcode. Each of its
41 RTL inputs matches the corresponding source hash from the fitted hardware
candidate. P01/P06 belong to the external PCAT bus integration. The
[build manifest](../evidence/perf01-86box-50mhz-20261002/build-manifest.json)
records source identities, defines and both executable hashes.

The native reference replaces only the CPU-dispatcher object in the same build;
the peripherals and CPU table remain shared. SPK286 consumes one configured
CPU clock per model tick, and the standalone adapter supplies READY immediately.
MiSTer includes PCAT's buffers, bridge, SDRAM, refresh and peripheral service.
Consequently the hardware/standalone gap includes the whole integration; these
scores support further memory-path attribution under PERF01. The native timing
model and the standalone adapter's memory service remain distinct models.

The frozen PCAT top selects the 50 MHz CPU clock with the divided debug mode
disabled and `execute_enable = 1`; its wrapper requests timing policy zero,
matching the standalone adapter. The remaining integration cost consequently
needs bus/memory/peripheral attribution rather than a nominal-frequency change.
The [clock/enable/policy receipt](../evidence/perf01-86box-50mhz-20261002/pcat-clock-policy.json)
matches these source/configuration hashes against the fitted candidate.

MR BIOS detected the changed oscillator on each first 50 MHz boot. Identical
Enter/F10 keyboard events acknowledged and saved its calibration before the
application began. The native repeat used already calibrated native CMOS.
BIOS/CheckIT frequency estimates describe calibration loops; the actual clock
for this comparison is verified from the configured runtime CPU state.

## Guest application timing

`TICKRUN.COM` uses BIOS INT 1Ah around the unchanged CHECKNUM child and forwards
its exit status. One tick is `65536 / 1193182` seconds.

| Execution | BIOS ticks for whole application | Guest seconds |
| --- | ---: | ---: |
| Native 25 MHz control | 212 | 11.644185 |
| Native 50 MHz, both runs | 198 | 10.875229 |
| SPK286 50 MHz | 209 | 11.479409 |

Whole-application timing includes loading, calibration, the two adaptive tests,
formatting and exit. CHECKNUM adjusts its iteration counts, so this duration
has variable work. The rates above provide the benchmark comparison. The JSON
also derives effective clocks per Dhrystone as `50000000 / reported_rate`;
those estimates inherit the original timer quantization and score rounding.

The slow Verilator host execution affects how long the measurement takes to
finish. The benchmark uses the emulated DOS/BIOS timer throughout. Fast forward
removes host pacing while preserving the configured guest CPU/timer relationship.

The first native host process aborted during teardown after complete DOS RC0
output (`corrupted double-linked list`, host RC -6). Its separately recorded
repeat returned the same scores and tick interval, with host RC0. Both original
receipts are retained. The SPK host return code is 0.

## Ready-to-use profiles

Local launchers:

- `D:/GitHub/86Box_dev/build/spk286/Run-Native286-50MHz.cmd`
- `D:/GitHub/86Box_dev/build/spk286/Run-SPK286-50MHz.cmd`

They run the corresponding Linux binary through Ubuntu-24.04 WSL and open a
normal visible instance. Each has a separate disk and calibrated CMOS, at
50 MHz / MR BIOS / 2 MiB / EGA. CHECKNUM runs automatically and prints its two
scores, then returns to the DOS prompt. Their image bytes match each other;
the evidence retains the measured disks separately. Artifact identities are
in [ready-profiles.json](../evidence/perf01-86box-50mhz-20261002/ready-profiles.json).

The reproducible preparation and measurement commands are documented in
`D:/GitHub/86Box_dev/tools/spk286_cpu/README-50MHZ.md`. The measurement workspace
is `D:/GitHub/PCAT-286_MiSTer/build/perf01-86box-50-20261002`.

## Next attribution step

Update: [P12](P12_REAL_CHECKNUM_MEMORY_ATTRIBUTION_20261002.md) completes real
CHECKNUM with production PCAT memory-control timing: 4804 / 88.6K, versus the
7709 / 133.3K immediate reference. Its much lower real code-buffer hit rate
motivates [the 4 KiB candidate](P13_CODE_BUFFER_4K_20261002.md). The paragraphs
below preserve the original attribution plan and synthetic baseline.

The completed same-clock result supplies the standalone reference missing from
earlier PERF01 comparisons. The user's priority is PCAT versus standalone
SPK286; the smaller native-CPU difference is retained as a control.
Profile accepted request/response latency, code/data
buffer behavior and SDRAM service against this workload before selecting the
next optimization. Changes to the CPU, bridge or timing closure are subsequent
milestones with separate directed functional, performance and fitted evidence.

The existing candidate's **synthetic Dhrystone-shaped kernel** records 99.91%
code-buffer hits and 98.26% data-buffer hits. Code hits still wait two clocks;
data reads average 2.12 clocks and writes 7.22. The kernel performs 21,124
physical writes, despite just 656 data-read misses and 49 code-line fills.
See the [guarded latency comparison](../evidence/perf01-bridge-response-20261002/latency-comparison-guarded.json).
These are different workloads from the DOS application, but they identify hit
turnaround and writes as candidates alongside SDRAM miss service. Overlapping
CPU/bus busy counts cannot be added as separate lost cycles.

The code buffer is direct-mapped with 64 eight-byte lines (512 bytes); the data
buffer contains 512 words (1 KiB). Actual CHECKNUM code/data working sets,
cross-function conflicts, capacity misses, invalidation, speculative prefetch
and write frequency remain to be profiled. High hit rates in the synthetic
kernel cannot establish equally high hit rates in the DOS benchmark. Evaluate
that evidence before assuming either a buffer-size limit or saturated SDRAM.

KFSDRAM currently precharges after each independent read/write transaction.
Keeping a row open across nearby accesses could amortize activation/precharge;
the [Winbond W9825G6KH A05 specification](https://docs.rs-online.com/eb6b/0900766b817040a8.pdf),
pages 3 and 7-10, describes bursts, selected-row accesses and bank operation.
The exact module suffix/speed remains the conditional identification recorded
in P05. An open-row controller needs bank/row ownership, refresh deadlines and
all device timing constraints; this capability is an opportunity to evaluate.
The selected bridge change already gained 10.517% hardware integer throughput
without changing the SDRAM clock or commands. The remaining score gap alone
therefore cannot establish an exhausted physical SDRAM limit or quantify the
gain of a particular future redesign.
