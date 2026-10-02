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
completed scores and fitted resources are pending at this implementation hito.
No full regression or hardware acceptance is claimed.

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

After this candidate, the next throughput targets are the fixed cost of
common hit responses and physical RAM writes. Current candidate averages are
approximately 2.00 / 2.12 wait clocks for code transfers, 2.55 / 3.07 for data
reads and 7.32 / 7.28 for data writes. These counts overlap internal execution;
they cannot be added to instruction clocks or directly converted to a speedup.
Any latency reduction must retain physical ownership, coherence and event
ordering. No latency-reduction change is implemented by this recommendation.
