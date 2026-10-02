# P17: memory-path throughput review and entry-overlap prototype

Date: 2026-10-02. Source baseline: PCAT `ea283d8`, including P16.
Status: **isolated prototype validated and measured with fixed-work kernels;
real CHECKNUM integer result provisional; math, adoption and FPGA fit pending**.

Prioritize the common cache-hit latency, followed by studying write service
overlap. A private bridge/port prototype improves four directed workloads by
**9.46–11.40%** without enlarging either cache or changing CPU RTL. A separate
ideal-write experiment indicates more scope after that improvement; it does
not demonstrate correct write posting or a hardware speedup.

## Where the remaining cost lies

Completed P16 CHECKNUM gives **5666 / 102.9K** with PCAT memory timing versus
**7709 / 133.3K** with immediate READY on the same SPK286 at 50 MHz. Matching
that ideal-memory reference requires another **36.06% / 29.54%** throughput
increase. User-observed MiSTer P16 is 5139 / 97.1K; the model/hardware difference
is separate. Host PC speed does not define these guest benchmark rates.
Native 86Box 286 at 8287 / 144.9K uses another CPU timing model.

P16's complete function-phase counters show:

| Observation | Dhrystone | Software floating-point Whetstone |
| --- | ---: | ---: |
| Code-buffer hit rate | 99.98916% | 98.84766% |
| Data-buffer hit rate | 99.99189% | 98.56389% |
| Completed code transfers | 12,453,963 | 73,707,310 |
| Completed data reads | 5,152,551 | 13,228,920 |
| Completed writes | 2,732,949 | 8,888,367 |
| Mean code wait clocks | 2.00112 | 2.11882 |
| Mean data-read wait clocks | 2.00061 | 2.10527 |
| Mean write wait clocks | 6.16845 | 6.22776 |

More cache capacity removes few integer misses because almost every read
already hits. The two-clock hit interval affects millions of requests.
Capacity may still help math: P16's 8 KiB code shadow predicts 195,459 misses
against 849,359 actual; a 4 KiB direct data shadow predicts 31,364 against
189,982. These are shadow observations, not measured gains, and incur memory
and validity-bit cost.

One clock per completed read gives a raw budget of 17,606,514 / 86,936,230
clocks. This is **not saved elapsed time**: prefetch overlaps execution,
branches discard fetched bytes, and faster service changes scheduling.

## Prototype: start the cache lookup on request capture

Current entry captures address/ownership, accepts the retained command and
reads synchronous RAM on the following edge, then returns the registered hit.
The private candidate arbitrates, captures the complete request and accepts
the backend command on the initial address edge. Synchronous tag/data RAM
starts reading there; its hit response returns using the retained accepted
record on the next edge. Hits therefore fall from two wait clocks to one.

Only the bridge and common memory port change. Early commands qualify for
native memory classes 5/6/D in the common CPU clock. The bridge enters WAIT
only after acceptance; backpressure retains the record for later acceptance.
The port retains loader priority, collision diagnostics and CPU cancellation.
Idle READY cannot complete an unaccepted record. Peripheral, INTA, split and
divided-clock response paths retain their previous handling. Machine A20,
BIOS/EMS mapping and ROM-write sinks require whole-machine checks before
adoption.

Tags/data remain synchronous M10K outputs; no combinational RAM response or
zero-wait promise. Code/data capacities stay 4 KiB / 1 KiB two-way. Physical
owner, KFSDRAM commands, CAS/recovery and refresh parameters are unchanged;
writes still acknowledge physical completion. Production RTL/configuration
is unchanged by this experiment.

## Fixed-work result

Both arms use identical frozen CPU RTL/options and firmware at 50 MHz,
production capacities, physical SDRAM pin data and periodic refresh. These
are **elapsed-clock comparisons, not DOS CHECKNUM scores**. The `whetstone`
fixture is fixed point, unlike CheckIT's software floating point.

| Kernel | P16 control clocks | Entry-overlap clocks | Throughput gain |
| --- | ---: | ---: | ---: |
| Dhrystone-shaped | 745,522 | 669,226 | +11.40% |
| Fixed-point mix | 621,946 | 560,212 | +11.02% |
| Working set | 720,308 | 658,044 | +9.46% |
| Dhrystone 2.1 | 799,048 | 720,387 | +10.92% |

All pairs preserve GPRs, FLAGS, backing-memory hash, retired instructions,
CPU/SDRAM writes, consumed bytes and redirects. Speculative code traffic and
refresh phase can differ. Both arms also run P03-off controls.

Dhrystone's 76,296 saved clocks comprise 63,719 fewer operand-service clocks,
9,950 fewer opcode-starved and 2,627 fewer instruction-byte-starved clocks.
Internal, dispatch and retirement buckets are unchanged. Bus wait falls by
110,856 clocks, a different quantity. Legacy kernel hit/miss latency labels
assume asynchronous tags: use aggregate code transfers and native cache
counters with synchronous tags.

Private adapter smoke measures code/data hits at one wait clock and ordinary
writes at five without intervening refresh, versus P16's two and six. Miss
latency depends on physical readiness/refresh. Aliases, code invalidation,
matching byte updates, no write allocation, uniqueness and reset pass.

## Larger opportunity: overlap execution with physical writes

The simulation-only ideal owner eliminates physical write service while
preserving CPU, entry and read/cache handling. After entry overlap it gives:

| Kernel | Additional gain over entry overlap | Combined gain over P16 |
| --- | ---: | ---: |
| Dhrystone-shaped | +15.74% | +28.93% |
| Fixed-point mix | +14.35% | +26.95% |
| Working set | +14.36% | +25.18% |
| Dhrystone 2.1 | +13.31% | +25.68% |

These results justify evaluating a small posted-write design. They are not
queue measurements: the ideal owner writes simulation memory directly,
without physical drain, DMA or posting/reset hazards. Start with one retained
write, separate logical acceptance from physical completion, and measure
backpressure before increasing queue depth. Requirements include:

- acknowledge only after retaining address, lanes and data;
- drain acknowledged writes exactly once across CPU-local reset;
- preserve order against reads, writes, DMA, HPS and noncacheable accesses;
- update matching cached data and invalidate code before later CPU hits can
  observe it, with canonical aliases and byte masks;
- forward pending matching data or stall conflicting reads until drain;
- cover LOCK, HOLD/HLDA, odd words, refresh and global reset behavior.

Posting belongs in the machine memory subsystem; the CPU still honors real
READY/operand dependencies. Dirty write-back caching and write combining
require further specifications and are not selected here. Historical cycle
accuracy remains the separate P12 reference-contract task.

## SDRAM controller opportunity

KFSDRAM activates a row and precharges all banks after every transfer.
Retaining an open row could avoid repeated activate/precharge commands.
The first 250,000 accepted P16 CPU events show adjacent-write row reuse of
89.62% / 97.86% in integer/math traces, with captured writes all in bank 0
under the current 9-column/13-row/2-bank geometry.

This is **write-address locality, not SDRAM row-hit rate**: intervening physical
reads, refresh and other owners are excluded. The bounded traces contain
calibration/interrupts and are not full working sets. Simply parallelizing
four banks would not automatically help these captured addresses.
An open-row prototype needs actual owner row/refresh traces and pin checks
for conflicts, write recovery, turnarounds, precharge-before-refresh and
retention bounds. Controller gains overlap posting gains; do not add them.
No SDRAM timing or refresh interval is relaxed in this review.

## Validation and next gates

- Strict bridge lint passes common/divided response configurations and port
  lint passes without waivers. Existing port tests pass Icarus/Verilator.
- Composed bridge/port/code/data cancellation passes 171 checks both with the
  original small buffer and production 512-line synchronous tags.
- The larger-tag test initially failed a diagnostic assertion expecting hit
  counts at acceptance. P16 control reproduces it. Synchronous tags count on
  completion, which this test cancels. Both variants pass the retained adapted
  fixture checking the actual synchronous hit before cancelled completion;
  address, data, uniqueness and reset assertions remain. Failures are retained.
- Frozen source guards pass. The private 86Box candidate reuses unchanged
  compiled SPK286 objects and the unchanged profiler. Unmodified CHECKNUM is
  running with the same disk, CMOS, BIOS, EGA, RAM, actual 50 MHz CPU and 8 MHz
  ISA configuration as P16. Binary SHA-256:
  `b51ff6e1a9bcd057149b5f988684998aaffa62743881c3d20f45a7977f4f446b`.
  A read-only diagnostic recovered **6138 Dhrystones** from the guest's stable
  formatted output buffer at 4CB38h while execution had entered Whetstone.
  This is **+8.33%** against P16's completed 5666. Two successive reads agree,
  process/executable ownership and binary hash are checked, and no guest write
  or stop is issued. Full output, guest RC0/ALL_DONE and final profile remain
  pending; this is a **provisional integer result**, not complete acceptance.

Before adoption: finish CHECKNUM and compare complete receipts to P16; check
whole-machine mapping/ROM sinks, arbitration, external writers and divided
clock; then fit a frozen FPGA candidate and report net/entity ALMs, registers,
M10Ks and all-corner setup/hold. No additional RAM capacity is requested, but
fitted logic cost is **unmeasured** and the live-input acceptance/address path
may affect timing. P16 CPU setup violations remain pending. No full regression,
new RBF or hardware acceptance is part of this review milestone.

Reproduction and observations are in the
[evidence inventory](../evidence/perf01-entry-overlap-20261002/README.md).
