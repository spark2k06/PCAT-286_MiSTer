# P17: memory-path throughput review and entry-overlap prototype

Date: 2026-10-02. Source baseline: PCAT `ea283d8`, including P16.
Status: **entry overlap integrated; directed checks and complete CHECKNUM pass;
user fit and MiSTer throughput observed; 50 MHz timing closure pending**.

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
BIOS mapping, A20 transactions and ROM-write sinks have passed whole-machine
checks during adoption. EMS translation remains unchanged; canonical 25-bit
records and cache aliases are checked at the port/cache boundary.

Tags/data remain synchronous M10K outputs; no combinational RAM response or
zero-wait promise. Code/data capacities stay 4 KiB / 1 KiB two-way. Physical
owner, KFSDRAM commands, CAS/recovery and refresh parameters are unchanged;
writes still acknowledge physical completion. Production RTL/configuration
was unchanged during the isolated experiment. The measured bridge/port change
is now integrated in production; CPU RTL and configuration remain unchanged.

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
  compiled SPK286 objects and the unchanged profiler. Unmodified CHECKNUM ran
  with the same disk, CMOS, BIOS, EGA, RAM, actual 50 MHz CPU and 8 MHz
  ISA configuration as P16. Binary SHA-256:
  `b51ff6e1a9bcd057149b5f988684998aaffa62743881c3d20f45a7977f4f446b`.
  A read-only diagnostic recovered **6138 Dhrystones** from the guest's stable
  formatted output buffer at 4CB38h while execution had entered Whetstone.
  This is **+8.33%** against P16's completed 5666. Two successive reads agree,
  process/executable ownership and binary hash are checked, and no guest write
  or stop was issued. This initial observation was provisional; the complete
  output, guest RC0/ALL_DONE and final profile below subsequently confirmed it.

## Production adoption and completed CHECKNUM

The unchanged DOS executable completed normally in the guest, with `RC TICKRUN
0`, `ALL_DONE`, full formatted output and a final memory profile. The earlier
provisional integer observation is confirmed. Strict comparison verifies the
same original disk, calibrated CMOS, configuration, profiler/backend and
compiled CPU objects as P16, at actual 50 MHz and ISA 8 MHz.

| CHECKNUM | P16 | P17 | Gain |
| --- | ---: | ---: | ---: |
| Dhrystones/s | 5666 | 6138 | +8.33% |
| Software Whetstones/s, thousands | 102.9 | 113.6 | +10.40% |

Mean integer code/data waits are now 1.00085 / 1.00041 clocks instead of
2.00112 / 2.00061. Writes average 5.16253 instead of 6.16845. Floating-point
code/data waits fall to 1.11613 / 1.10429. Adaptive work differs between arms;
compare rates rather than absolute instruction or elapsed-clock counts.
Host time was 3563.322 s, application time 250 BIOS ticks. After complete guest
success, the host again needed SIGTERM following its exit timeout; the retained
receipt classifies `exit_timeout_then_sigterm` separately from guest completion.

Production bridge/port/smoke sources match the measured private variant except
comments. The CPU, cache geometry, physical owner/controller and configuration
match the frozen control. Seven bounded integration scripts pass; bridge
response covers common/divided clocks, port tests both simulators and all
request fields, cancellation covers both 64 and production 512 code lines,
and the cache scoreboard covers DMA/loader coherence and refresh/reset.
Whole-machine boot passes with 108 memory beats. A second ROM completes actual
A20 alias reads/writes and blocked word/upper-byte ROM writes, then the same
IRQ/IRET path with 162 memory beats. No full regression was run.

Initial fixture failures are retained, with their cause and adaptation:
the bridge fixture changed live width before the new initial sampling edge;
the port fixture checked combinational outputs without settling after changing
READY. The new ROM initially contained NASM's 386 near conditional branch
`0F 85`, rejected by vector 6 in both P16 and P17. Short conditional branches
plus near JMP and a `cpu 286` assembly directive correct that fixture. No CPU
change or instruction waiver is involved.

## User fit and MiSTer observation

The user subsequently synthesized production P17 and supplied CheckIT and
CHECKNUM screenshots. Both report **5666 Dhrystones/s and 106.7K Whetstones/s**.
Against the previous hardware observation, P16's 5139 / 97.1K, this is
**+10.25% / +9.89%**. The first hardware baseline was 3584 / 72.2K, making the
observed cumulative gain **+58.09% / +47.78%**. These are individual observations,
without a repeat-run distribution. The private model's P17 6138 / 113.6K and
P16 5666 / 102.9K are separate measurements; the repeated integer value 5666
does not make the model and hardware arms interchangeable.

The existing user build completed in **27 min 17 s**. Its RBF is
`output_files/PCAT-286.rbf`, 4,102,776 bytes, modified at 17:19:55 Europe/Madrid
on 2026-10-02. Quartus report timestamps use UTC. SHA-256:
`94f210cbaa590e3e80e210e661bea5eb9ba34772a6c8d04f797620359ba27ad0`.
The pre-user-build freeze matches all 1206 current source files. Relative to
the preserved P16 inputs, the only production compilation-input differences
are the bridge and memory port. The new fit hierarchy also contains the P17
logic. No compiler-side input receipt or independent attestation of the RBF
hash loaded on MiSTer is available; the screenshots are associated with this
latest build by session context. The OSD speed was not separately reconfirmed.

### Fitted resource cost

| Resource | P16 | User P17 fit | Difference |
| --- | ---: | ---: | ---: |
| Equivalent ALMs | 31,052 | 30,832 / 41,910 (74%) | -220 |
| Physically placed ALMs | 36,442 | 36,191 / 41,910 (86.35%) | -251 |
| Registers | 38,171 | 38,198 | +27 |
| M10K blocks | 416 | 416 / 553 (75%) | 0 |
| Block memory bits | 3,301,019 | 3,301,019 / 5,662,720 (58%) | 0 |
| DSP blocks | 39 | 39 / 112 (35%) | 0 |
| PLLs | 3 | 3 / 6 (50%) | 0 |

The two changed entities add only **13.8 equivalent ALMs** in this fit:
bridge 98.8 -> 105.6 (+6.8), memory port 82.9 -> 89.9 (+7.0).
Their combined register count falls by three, with no added M10K.
Whole-design area falls, but unchanged cache/CPU logic also changes packing
and replication. The global reduction is an observed fitted total, not proof
that entry overlap intrinsically removes 220 ALMs. Hierarchical owner and
KFSDRAM resource rows must not be added as independent costs.

### Timing at the configured 50 MHz

The original user-build STA summary is authoritative for the whole clock:

| Quartus model | P16 setup, ns | P17 setup, ns | P17 hold, ns |
| --- | ---: | ---: | ---: |
| Slow 1100 mV, 100 C | -0.450 | **-0.979** | +0.251 |
| Slow 1100 mV, -40 C | -0.029 | **-0.958** | +0.240 |
| Fast 1100 mV, 100 C | +2.569 | +2.570 | +0.134 |
| Fast 1100 mV, -40 C | +2.734 | +2.735 | +0.119 |

CPU/system hold remains positive in all four corners. Setup worsens by
0.529 / 0.929 ns in the slow corners; setup TNS rises in magnitude from
-6.195 / -0.080 ns to **-63.600 / -72.436 ns**. Reported CPU Fmax is
**47.67 / 47.71 MHz** in those corners, versus 48.90 / 49.93 MHz for P16.
The hardware remains clocked at 50 MHz; this report does not automatically
reduce its frequency. CheckIT's estimated 35.06 MHz is calibration software,
not measurement of the actual FPGA clock. This candidate is **not timing
closed at 50 MHz**, despite the successful benchmark execution.

Other negative summary entries are video-domain hold **-0.042 / -0.074 ns**
in the two slow corners, and HDMI PLL source-domain setup **-0.034 ns** at
Slow -40 C. These are recorded separately from CPU hold and from the scaled
HDMI output clocks. They also prevent whole-design closure.

### Bounded critical-path review

TimeQuest was run against a private copy of the user's fitted netlist, without
synthesis, fitting, RTL/SDC changes or regression. Ten paths per group and
check were requested. The slow same-clock setup paths reproduce the original
summary's worst CPU margins:

- Slow 100 C: `prefetch_queue.storage_q[1][4]` ->
  `events.event_error_code[5]` / `[8]`, **-0.979 ns**, 20 logic levels.
  Data delay is 20.282 ns: 8.265 ns cells and 12.017 ns interconnect, with
  -0.517 ns clock skew.
- Slow -40 C: `prefetch_queue.storage_q[1][7]` ->
  `events.event_error_code[5]`, **-0.958 ns**, also 20 logic levels.
- Code-buffer setup reaches **-0.269 / -0.486 ns**; data-buffer setup reaches
  **-0.486 / -0.500 ns**. The top paths start at machine reset/admission
  synchronizers (`at_reset_sync2_q` or `missing_main_sync[1]`) and end in
  code validity or data lookup-valid registers, with 17 / 18 logic levels.
- Groups ending at bridge registers have **+0.828 / +0.629 ns** setup;
  groups ending at memory-port registers have **+1.129 / +0.890 ns**.
  This does not establish the slack of every path passing through their
  combinational logic and ending elsewhere.
- The worst video hold path goes from DAC `write_index[3]` to the blue palette
  memory address register, reaching **-0.074 ns** at Slow -40 C.

The worst setup path is inside unchanged CPU RTL. Placement/replication can
expose an existing long decode path after a local integration change; one fit
does not establish the sole cause of its regression. The CPU prefetch-to-event
decode and cache reset/admission controls are concrete timing follow-ups.
Preserve the measured one-clock cache-hit behavior when addressing them.

The available custom fast operating conditions are `MIN_fast`; their bounded
internal-clock setup values are not replacements for the original report's
all-clock fast summary. This extraction is not a full constraint/CDC audit.
TimeQuest regenerated **only the private `db/PCAT-286.cmp.rdb`**, causing the
initial immutable-artifact guard to reject the run. The final verifier records
that exception and confirms every source, the other 22 private fit artifacts,
and **all 23 original project fit artifacts** remain unchanged. No original
user build artifact was overwritten.

The observed performance gain justifies retaining entry overlap at this small
local area cost. Timing closure, repeated hardware measurements and broader
compatibility remain open. The posted-write and open-row ideas above remain
future experiments; neither is implemented by this observation. The user then
retained P17, deferred timing closure and authorized the
[one-entry posted-write experiment P18](P18_ONE_ENTRY_POSTED_WRITES_20261002.md).

Reproduction and observations are in the
[evidence inventory](../evidence/perf01-entry-overlap-20261002/README.md).
