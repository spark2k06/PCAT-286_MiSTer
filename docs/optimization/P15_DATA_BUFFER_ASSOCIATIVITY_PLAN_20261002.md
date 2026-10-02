# P15: reduce data-buffer conflicts at the same 1 KiB capacity

Date: 2026-10-02. PERF01 two-way data-buffer candidate.
The user retains P14 and defers HDMI closure while prioritizing throughput.
The user has authorized implementation, measurement and resource comparison.

## Implemented candidate and directed acceptance

The production data buffer now has 256 sets and two ways, retaining 512 words
and 1 KiB of payload. Parallel synchronous tag/data reads preserve the existing
hit response. Invalid ways precede LRU replacement. Read hits/fills make their
way most recently used; writes update a matching cached word only after physical
completion and do not change read recency or allocate on a write miss.
CPU options, clocks and the 4 KiB instruction buffer are unchanged.

The [implementation evidence](../evidence/perf01-data2way-20261002/README.md)
retains these completed directed checks:

| Check | Result |
| --- | --- |
| Icarus/Verilator unit and strict Verilator lint | PASS |
| Same-index coexistence, LRU reread, both ways' byte merges, CPU/DMA/loader writes | PASS |
| Local hit response clock and CPU flush of both ways | PASS |
| Common memory-port/code/data pipeline, 64 and 512 code lines | PASS |
| Two words / one set minimum elaboration | PASS, Icarus |
| Private 86Box memory-control adapter smoke | PASS, sampled data-hit wait remains two CPU clocks |
| Isolated Quartus RAM inference | PASS, two 256 x 32-bit M10K memories |

The isolated map reports 957 registers and 16,384 memory bits, including
diagnostic outputs. The previous full fit had two M10Ks for data/tag storage;
the new geometry also fits two. Whole-design placed cost is being measured
separately in a pre-build frozen Quartus run. A fresh unchanged CHECKNUM run
uses the same initial disk/configuration/CMOS and actual 50 MHz CPU. Its
completed private-model comparison, final fit and user-confirmed MiSTer benchmark
are recorded below. No full regression is part of this milestone.

## Completed FPGA fit and first MiSTer observation

The frozen compilation finished in **30:57**, with 0 errors and 854 warnings.
All 1,203 pre-build source hashes remained unchanged. The candidate RBF is
`D:/GitHub/PCAT-286_MiSTer/build/perf01-data2way-fit-20261002/work/output_files/PCAT-286.rbf`,
4,131,340 bytes, SHA-256
`aafb3dcf9b223cdce9dc62f5e4fb828810fb0c0b160d845ec4d9f33c9f4a8b67`.
The production configuration uses 50 MHz CPU, no debug observer and the existing
CPU access optimizations. The user confirmed this exact RBF and maximum CPU speed.
[Fit and image evidence](../evidence/perf01-data2way-20261002/README.md) retains
report/source hashes, resources, STA summaries and both hardware screenshots.

| Whole design, fitted | P14 | P15 | Delta |
| --- | ---: | ---: | ---: |
| Equivalent ALMs / 41,910 | 30,552 | 30,587 (73%) | +35 |
| Physical placement ALMs / 41,910 | 36,043 | 36,128 (86%) | +85 |
| Registers | 37,733 | 38,022 | +289 |
| M10Ks / 553 | 416 | 416 (75%) | 0 |
| Payload/tag block-memory bits | 3,300,507 | 3,301,019 | +512 |
| Allocated block-memory bits | 4,259,840 | 4,259,840 | 0 |
| DSPs / PLLs | 39 / 3 | 39 / 3 | 0 |

These are net whole-fit differences, not an isolated marginal logic cost.
The fitted data-buffer entity rises from 606.0 to 948.8 equivalent ALMs
(**+342.8**) and from 582 to 937 registers (**+355**); its M10Ks remain two.
Physical synthesis/packing also changes other entities: the unchanged-source
code-buffer entity falls from 2001.3 to 1701.5 equivalent ALMs. This compensates
much of the data-buffer logic increase in the measured complete design.
The P14 baseline was a completed user build with matched production hashes;
the P15 build additionally has an independently retained pre-build manifest.

| CPU/system 50 MHz corner | Setup ns | Hold ns |
| --- | ---: | ---: |
| Slow 100 C | **-0.194** | +0.251 |
| Slow -40 C | +0.082 | +0.239 |
| Fast 100 C | +2.579 | +0.134 |
| Fast -40 C | +2.740 | +0.117 |

CPU setup is therefore **not closed at 50 MHz** in the slow 100 C corner
(TNS -0.660 ns). The deferred HDMI clock also has -0.188 ns setup in slow
-40 C (TNS -0.452 ns). These are the only negative STA summary rows; hold
summaries are positive. No new complete timing-constraint audit is claimed.
This is a performance candidate with a remaining CPU timing follow-up.

| User-confirmed maximum-speed MiSTer observation | P14 | P15 | Change |
| --- | ---: | ---: | ---: |
| CheckIT Dhrystones/s | 4,911 | 5,023 | +2.28% |
| CheckIT K Whetstones/s | 95.1 | 95.6 | +0.53% |
| CHECKNUM Dhrystones/s | 4,911 | 5,023 | +2.28% |
| CHECKNUM K Whetstones/s | 99.1 | 96.4 | -2.72% |

Both programs agree on the integer increase. The math observations differ;
there is no repeat distribution or established math speedup from these images.
Earlier CHECKNUM math observations at the same integer score also differed
(P13 94.4K, P14 99.1K). The source images and explicit RBF/max-speed attestation
are retained without treating that variation as a proven implementation effect.
Windows/OS/2 or a full regression were not re-exercised for P15.

## Completed unchanged CHECKNUM on the private PCAT model

The guest completed with RC0, `ALL_DONE` and a final profile. The strict
[comparison and retained receipts](../evidence/perf01-data2way-20261002/measurement/comparison.json)
verify matched initial disk, CHECKNUM/configuration/CMOS, actual 50 MHz CPU,
8 MHz 86Box ISA, original CPU backend, profiler, compiled CPU objects and CPU
macros. Capacity is 4 KiB code and 1 KiB data in both; data changes from direct
to two-way. The P13 control uses the older code-tag mapping; P14's separate
paired directed check established matching behavior/latency under its exercised
traffic. This comparison does not assert byte-identical code-buffer sources.

| Private PCAT memory-control path | Dhrystones/s | K Whetstones/s | Application BIOS ticks |
| --- | ---: | ---: | ---: |
| Completed 4 KiB code / 1 KiB direct data control | 5,390 | 101.4 | 260 |
| P15 4 KiB code / 1 KiB two-way data | 5,525 | 102.4 | 256 |
| Measured rate change | **+2.50%** | **+0.99%** | Adaptive work; not fixed-work timing |

The host elapsed time was 3895.737 seconds including teardown. The owned host
again needed SIGTERM after the monitor-exit timeout (return code -15), after
successful guest completion and final profile publication. The receipt keeps
`exit_timeout_then_sigterm`; the comparison required explicit
`--allow-host-teardown-issue`. This is not a clean host-exit claim.

| Completed phase | Direct data misses | Two-way data misses | Direct mean read wait | Two-way mean read wait |
| --- | ---: | ---: | ---: | ---: |
| Dhrystone | 378,345 | 421 | 2.54574 | 2.00059 |
| Whetstone | 1,931,287 | 190,051 | 3.06706 | 2.10415 |

Actual data hit/miss counts **exactly match** the corresponding direct/two-way
shadow model in each full function phase. P15 data hit fractions are 99.9919%
and 98.5562%. CHECKNUM adapts work and interrupt placement, so rates and mean
per-transfer waits are the comparisons; absolute phase work is not forced equal.
Each retained trace has 250,000 accepted operations including calibration and
interrupts. These bounded traces are not the full phase or simultaneous occupancy.

The increase is modest because CPU execution, code fetches and physical writes
still consume time. P15 writes average 7.24954 / 7.26504 wait clocks; code
transfers average 2.00110 / 2.11925. Bus waits overlap internal CPU execution
and cannot be added to instruction clocks or directly converted to a speedup.
86Box owns guest values/peripherals; DMA/loader/abstract AT-refresh arbitration
and electrical SDRAM behavior remain outside this adapter. The user hardware
benchmark is a separate observation. No full regression was launched.

## Completed 4 KiB code-buffer CHECKNUM measurement

The frozen P13 private adapter has now finished the unchanged CHECKNUM with
the real PCAT memory-control path. [Receipts and counters](../evidence/perf01-code4k-checknum-20261002/README.md)
retain exact binary, disk, CMOS, CPU/backend and profiler identities. The
comparison script verified matched 50 MHz CPU, 8 MHz 86Box ISA, configuration,
initial disk, CHECKNUM executable and unchanged CPU backend.

| Same SPK286 at actual 50 MHz | Dhrystones/s | K Whetstones/s | Application BIOS ticks |
| --- | ---: | ---: | ---: |
| Immediate READY reference | 7,709 | 133.3 | 209 |
| PCAT path, old 512 B code / 1 KiB data | 4,804 | 88.6 | 287 |
| PCAT path, 4 KiB code / 1 KiB data | 5,390 | 101.4 | 260 |

The code-buffer candidate improves measured rates by **12.20% / 14.45%**.
Application ticks are not fixed-work timing: CHECKNUM adapts iteration counts
and also loads/calibrates/formats. The completed P14 MiSTer observation is
4911 / 99.1K in CHECKNUM; the separate CheckIT observation is 4911 / 95.1K.
No equal guest/peripheral configuration or repeat distribution is established
between hardware and the private model.

The guest returned RC0 and `ALL_DONE`, published a final profile and retained
both 250,000-operation phase traces. The host monitor-exit timed out after
guest completion and the owned process exited after SIGTERM (return code -15).
That teardown is explicitly classified; no clean host exit is claimed.
The strict summary required `--allow-host-teardown-issue` for this completed
guest result and the previously classified baseline teardown.

This run uses the original P13 frozen executable. P14's directed paired
check establishes matching responses under its exercised traffic; the private
measurement is not a benchmark of P14's physical implementation. The model
still has the P12 limits: 86Box owns values/peripherals, memory READY follows
the real PCAT RTL, and DMA/loader/AT-refresh arbitration and electrical SDRAM
effects are outside this adapter.

## Why data associativity is the next candidate

The 4 KiB instruction buffer now hits **99.989%** in Dhrystone and **98.840%**
in Whetstone. Its data buffer hits **92.722% / 85.306%**. Enlarging code again
would have little Dhrystone opportunity from misses; data conflicts remain.

On the candidate's exact accepted data stream, the shadow models report:

| Phase | Current 1 KiB direct misses | 1 KiB two-way shadow | 2 KiB direct shadow | 4 KiB direct shadow |
| --- | ---: | ---: | ---: | ---: |
| Dhrystone | 378,345 | 420 | 402 | 361 |
| Whetstone | 1,931,287 | 190,075 | 1,634,533 | 31,366 |

The current-capacity direct shadow exactly matches the observed hit/miss
counts in both phases. The two-way shadow removes approximately **99.89% /
90.16%** of those misses. Doubling direct-mapped capacity helps Dhrystone but
leaves much of Whetstone's conflict pressure. These are tag-model results on
existing traffic, not an implemented speedup or a promised CHECKNUM score.

The selected production organization is **256 sets x 2 ways x 16-bit word**,
retaining 1 KiB of payload. Two distinct physical words sharing an index can
coexist. Use one replacement bit per set and prefer an invalid way. Parallel
synchronous way lookups must preserve the current hit-response latency.

Current storage combines tag and data in M10K. The new organization has two
256 x 32-bit tag/data arrays rather than one 512 x 31-bit array. Both RAM
inference and final block use must be checked; the same payload capacity is
not proof of unchanged FPGA cost. Replacement bits and way selection add
logic. P14's cost reduction makes disciplined cost measurement a requirement.

## Bounded implementation and acceptance plan

1. Implement two-way lookup/replacement only in
   `spk286_at_sdram_data_buffer.sv`, retaining the canonical address contract
   and current hit latency. Keep code capacity, CPU options and clocks fixed.
2. Preserve physical write completion/no write posting/no write allocation.
   Matching CPU/DMA/loader byte writes must update the correct cached way;
   reset/cancellation, ROM/device exclusions, code bursts and refresh must
   retain their current contracts.
3. Run directed byte-scoreboard/conflict/replacement/cancellation checks and
   the common memory-port/code/data chain. Include two aliases mapping to one
   set, both lanes, invalid-way preference and evicted-word rereads. No full
   regression is part of this milestone.
4. Verify both tag/data arrays infer M10K; record map/fit ALMs, registers,
   M10Ks and CPU/system timing against the accepted P14 fit. Reject accidental
   register arrays or an added hit clock.
5. Measure the unchanged CHECKNUM on a frozen private PCAT adapter candidate
   against the completed 5390 / 101.4K control before asking for hardware
   comparison. Do not change unrelated parameters in that comparison.
6. Commit the directed, measured implementation milestone and leave a
   reviewable candidate for the user's final synthesis/hardware measurement.

After this candidate, the next throughput targets are the fixed cost of common
hit responses and physical RAM writes. P15's completed averages are 2.00110 /
2.11925 wait clocks for code, 2.00059 / 2.10415 for data reads and 7.24954 /
7.26504 for writes. The user has authorized a private write-admission prototype
and a real 86Box measurement **before** another resource synthesis. Production
RTL remained P15 during the initial experiment. [P16](P16_WRITE_ADMISSION_PROTOTYPE_20261002.md)
subsequently completed 5666 / 102.9K versus 5525 / 102.4K (+2.55% / +0.49%). The user
requested an RBF after the early integer output. Commit `95f5b21` adds the directed-tested
write-admission owner. Its frozen full fit adds 465 net equivalent ALMs, 149
registers and no M10Ks; worst CPU setup is -0.450 ns with positive hold. A candidate
RBF is available for hardware comparison. Later options include eliminating
avoidable common-hit pipeline cycles, reusing open SDRAM rows (KFSDRAM currently
precharges after each transfer) and evaluating larger code capacity from
measured traffic. Every reduction must retain physical ownership, coherence,
refresh behavior and event ordering; no such change is part of P15.
