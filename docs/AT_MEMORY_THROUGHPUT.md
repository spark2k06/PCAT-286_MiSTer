# AT memory throughput investigation (2026-09-13)

## Observed CheckIt results

| Platform | Displayed CPU estimate | Dhrystones | Whetstones, no NPU |
| --- | ---: | ---: | ---: |
| MiSTer AT, before this change | 34.60 MHz | 1,586 | 28.9K |
| MiSTer AT, native x16 memory, board test | 34.80 MHz | 2,368 | 45.7K |
| 86Box, user screenshot | 25.00 MHz | 4,143 | 70.9K |

These are the user's CheckIt screenshots, including the board test reported
after rebuilding this change on 2026-09-13. The native x16 path improves
Dhrystones by **49.3%** and Whetstones by **58.1%**. CheckIt's ratings increase
from 4.61x/4.38x to 6.88x/6.92x IBM PC-XT. This agrees with the approximately
50% throughput improvement measured in the A/B RTL workload below.

The remaining 86Box/core throughput ratios are **1.750x** for Dhrystones and
**1.551x** for Whetstones, down from 2.61x and 2.45x. The displayed MHz are
software estimates, not comparable measurements of RTL clock rate.

The AT top (`spk286_at_emu.sv`) clocks the machine and memory interface with
`CLK_50M` and sets `execute_enable=1`. A 50 MHz RTL clock does not imply the
instruction throughput of a historical 50 MHz 286. Fetch, bus and execution
state machines can consume many clocks per operation.

The initial `output_files_pcat286_at_fast/PCAT-286_AT_FAST.sta.rpt` reviewed
during the investigation reported 34.35 MHz Fmax and -9.109 ns setup slack.
The latest available report (file modification time **2026-09-13 15:38**, local
time) reports a **50 MHz clock constraint**, **33.88 MHz Fmax** and
**-9.515 ns setup slack** for
`FPGA_CLK2_50` at the slow 1100 mV / 100 C corner. Fmax is not an automatic
divider: this build is not timing-closed at its actual clock. The user rebuilt
and tested on the board; no additional Quartus fit was run during commit
validation. The successful CheckIt run establishes observed functionality and
performance, but neither it nor RTL simulation establishes timing compliance.

CheckIt's displayed MHz should be treated as a software estimate, not a clock
readback or the Quartus Fmax. The exact calibration routine has not been
identified in the binary; no claim is made about which instruction it times.

## Confirmed bottleneck and implemented change

The old `spk286_at_bus_bridge.sv` split every aligned CPU word into two separate
byte transactions, including instruction fetches, RAM and ROM. The existing
memory port, SDRAM owner and KFSDRAM already carry 16 bits. Each byte paid the
bridge handshakes and SDRAM access overhead again.

The memory decoder now reports target width, sampled with the CPU request:

- Conventional RAM, extended RAM, option ROM and system ROM (including the high
  reset alias) accept aligned words as one transaction with both byte lanes.
- EGA memory, I/O (including XT-IDE), INTA and unmapped targets retain their
  existing byte sequencing.
- Single-byte and odd-address accesses retain the original lane behavior.
- ROM write protection, READY/accept, LOCK, arbitration and refresh remain in
  place. No CPU instruction semantics, BIOS bytes or clock settings changed.

The production AT QIP already includes these modules, so
`PCAT-286_AT_FAST.qsf` picks up the change without new assignments. The XT
machine path is not changed.

## Reproducible A/B simulation

Run `bash scripts/test_at_memory_perf.sh` (NASM and Verilator required).
The test uses the production SPK286 source list from its QIP, CPU wrapper,
bridge, memory port, SDRAM owner and KFSDRAM with the SDRAM pin model.
`+NATIVE=0` reproduces the old byte-split behavior; `+NATIVE=1` enables the change.
Both runs use the same 64 KiB test ROM, clock and physical refresh settings.
Peripheral/IRQ/DMA contention is deliberately excluded to isolate CPU/memory;
the ROM is preloaded, and SDRAM initialization is not included in the counters.

| Workload | Old cycles | New cycles | Throughput gain |
| --- | ---: | ---: | ---: |
| Register arithmetic and branches, including instruction fetch | 38,068 | 24,974 | 52.4% |
| RAM read/modify/write and stack, plus byte/unaligned checks | 103,893 | 65,159 | 59.4% |
| REP STOSW / MOVSW / SCASW | 103,500 | 70,226 | 47.4% |
| Integer MUL / DIV and checks | 37,054 | 27,463 | 34.9% |
| Whole program, including setup and completion | 282,858 | 188,037 | 50.4% |

Both runs retire **4,399 instructions** and produce the same checked register
and RAM results. CPU bus request counts are identical (9,434 reads and 2,821
writes), while physical SDRAM transfers are nearly halved in the word-heavy
stages. The whole program uses **33.52% fewer cycles**, or 1.504x throughput.
REP iterations are not counted as separately retired instructions.

Average CPU bus request duration, including bridge/SDRAM wait time, drops from
20.29 to 12.12 clocks for reads and 18.53 to 11.15 for writes. These are mixed
workload averages, not the latency specification of every word access.

There is still significant fetch/memory overhead: in the native-x16 register
arithmetic/branch stage, the CPU bus is active for 21,631 of 24,974 clocks
(86.6%), and the prefetch queue is empty for 20,332 clocks (81.4%). These
counters overlap; an empty queue is not itself proof of an execution stall.
They identify the fetch/memory path as a useful next profiling target, without
claiming to explain the entire remaining CheckIt gap.

This is **not CheckIt**, Dhrystone or Whetstone. It demonstrates a causal speedup
in the real RTL, not a promised CheckIt score or equivalence to a real 286.

## What 86Box models

Inspected local source: `D:/GitHub/86box_dev`, HEAD
`de4a54c96fbdb9b3a233703646f354e7b2f2b8ff`; no emulator was launched.

- `src/cpu/cpu_table.c`, i286 "25" entry: 25,000,000 Hz, four nominal memory
  read/write cycles, and `atclk_div=3` for the AT/ISA clock.
- `src/cpu/cpu.c`, `cpu_update_waitstates()`: the 16-bit CPU bus prefetches two
  bytes; memory timings can be overridden by configured wait states/cache.
- The 286 execution path uses software cycle accounting (`CLOCK_CYCLES`), not
  the state-machine latencies of this FPGA implementation.
- `src/cpu/386_common.c`, `prefetch_run()`, explicitly describes an approximate
  model: fetch missing instruction bytes, subtract data-memory cycles, and use
  remaining instruction cycles to refill. The shared model caps its queue at
  16 bytes. It is useful as a performance reference, not a cycle-exact oracle.

The screenshot alone does not establish the emulator's exact board/cache/wait
state configuration. The ISA divider is not a universal RAM-speed divider.
Neither the clock label nor using an AT bus guarantees equal benchmark scores.

## Validation and next steps

Passed after the change:

- A1 bridge and A2 memory decoder/arbiter tests, Icarus and Verilator.
- A4 DMA/refresh/PIT regression, Icarus and Verilator.
- XT-IDE machine tests with back-to-back and spaced CPU transactions: identify,
  sector read and sector write, Icarus.
- AT production-profile elaboration.
- HPS ROM loading, reset-vector word fetch and first 32 memory fetches with the
  diagnostic ROM, original Sergey ROM and `xtsergey_mod_at.rom`, Verilator.
  These are startup-path tests, not complete BIOS POST or DOS boot tests.
- CPU/memory A/B workload above; matching work and reduced cycles are asserted.
- User board validation after rebuilding AT_FAST: CheckIt completes with
  2,368 Dhrystones and 45.7K Whetstones, no NPU.

The first-fetch harness was updated to the current production PM5 source list,
XT-IDE dependencies and public MSW debug signal; old internal names were stale.

The board comparison now confirms the improvement. Physical timing closure
remains outstanding, as shown by the rebuilt AT_FAST report above.

Further measured optimization candidates are the bridge's unconditional
SNAPSHOT/DECODE phases, single-access closed-page SDRAM overhead, and instruction
prefetch latency. Caching/burst buffering would also need DMA and self-modifying
code coherence. Execution/microcode and physical timing closure are separate
workstreams; none has been silently changed to inflate this test's result.
