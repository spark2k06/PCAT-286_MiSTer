# P18: one retained CPU write below the coherent caches

Date: 2026-10-02. Production baseline: PCAT `89b9b4f`, including P17.
Status: **private prototype passes directed checks; matched real CHECKNUM
measurements running; production adoption and hardware validation pending**.

The user retained P17 and explicitly deferred timing closure. This experiment
addresses write service without changing CPU RTL, cache capacity, SDRAM timing
or refresh. The P17 ideal-write counterfactual is replaced by a real retained
record and physical drain; it no longer bypasses SDRAM writes in the kernels.

## Contract and integration

The new block sits after the code and two-way data buffers, before the physical
owner. Only unlocked CPU RAM writes of class 6, with nonzero lanes, can post.
Canonical RAM includes conventional, shifted extended and EMS backing store;
ROM/video/device areas, bursts, refresh, DMA and loader transactions bypass.

The complete address, byte lanes, data and metadata are captured before READY.
A posted write gives exactly one logical completion on the next clock. It can
launch the physical owner on its capture edge, or retain the record while
physical refresh/recovery prevents acceptance. After physical acceptance it
cannot issue again, and the owner's later READY is consumed privately. There
is one slot, with no combining, forwarding, allocation on a write or dirty
write-back state. Every later request reaching this boundary waits for drain.

On logical completion the data buffer updates a matching cached word. The
code buffer already invalidates the written line at acceptance. Subsequent
cache hits can therefore run while the physical store is pending. A conflicting
code fetch misses and waits for drain before filling from SDRAM; no stale line
can be reused. All physical cache misses and noncacheable memory accesses stall.

The bridge blocks I/O/INTA and locked requests until drain. Its idle indication
also remains false while a write is pending, so the existing HLDA/arbiter
protocol cannot grant DMA or AT refresh before that store physically completes.
The private 86Box wrapper applies the same drain barrier to host-served accesses
outside the reduced memory chain. Backend DMA/loader requests also wait for the
old record, and their own writes retain physical acknowledgement.

CPU-local reset suppresses the old CPU response and flushes both caches, but
never discards a locally accepted write, even before physical acceptance or
before its early response is sampled. The retained store drains exactly once.
Global reset clears the buffer with its physical owner and does not replay
discarded records; it does not promise to preserve an acknowledged write across
global/controller reset. This is the existing machine-reset boundary, not a
power-failure persistence contract. Reads/bursts accepted physically still drain
normally, including intermediate valid beats and final completion qualification.

## Fixed-work measurements with physical SDRAM data

Both arms reuse identical frozen CPU/options, 4 KiB code and 1 KiB two-way data
buffers, 50 MHz clock and KFSDRAM timing/refresh. Both include the same wrapper
and fences; only the explicit test enable changes. The control confirms writes
only after physical completion. These are elapsed-clock measurements, not DOS
CHECKNUM scores. The Whetstone-shaped kernel is fixed point.

| Kernel, code buffer enabled | P17 control clocks | Posting clocks | Throughput gain |
| --- | ---: | ---: | ---: |
| Dhrystone-shaped | 669,236 | 579,701 | **+15.45%** |
| Fixed-point mix | 560,222 | 490,802 | **+14.14%** |
| Working set | 658,054 | 576,767 | **+14.09%** |
| Dhrystone 2.1 | 720,397 | 636,510 | **+13.18%** |

All eight pairs (four kernels, code buffer off/on) match GPRs, FLAGS, backing
memory hash, retired instructions, architectural and physical write counts,
consumed instruction bytes and redirects. Every accepted posted store drains
exactly once. Prefetch traffic and refresh phase can differ. The new stop rule
waits for physical idle after HLT; controls include ten drain clocks beyond the
old P17 stop boundary. Compare the matched arms here. Without the instruction
buffer, gains are 1.12–5.41%; scarce read service limits overlap in that control.

## Directed protocol and data checks

- Strict `verilator --lint-only --Wall` on the new module passes without waivers.
- **495 checks** against the physical owner/pin model: initial backpressure,
  changing live fields after capture, stale idle READY, masked/odd-address
  stores, physical drain, burst beats, CPU reset, global reset/no replay,
  locked/non-CPU/ROM/refresh bypass and periodic refresh. The actual private
  bridge and production arbiter also check I/O/LOCK barriers and HLDA/DMA grant.
- **145 composed-cache checks** with production 512-line synchronous code tags,
  two-way RAM data buffer, common memory port and physical SDRAM data: updated
  data and unrelated code hits during an unissued store; DMA read ordering;
  code invalidation and refill; CPU reset after local capture before READY;
  masked DMA/loader writes; two canonical odd-word lanes; identical consecutive
  stores; and replacement among three tags mapping to one set. All 26 stores
  physically complete once; all 24 posted CPU stores drain.

The composed fixtures do not execute the whole PCAT machine, interrupt handlers
or the divided CPU clock. Those remain promotion checks. No full regression is
requested or claimed.

## Initial resource measurement

Isolated Quartus 17.0.2 mapping for Cyclone V, with unused debug counters removed,
estimates the **entire new enabled block at 51 ALMs, 59 registers, 76 ALUTs and
zero block memory bits**. The disabled wrapper maps to 44 estimated ALMs,
57 registers and 66 ALUTs. The difference of seven estimated ALMs is only the
enable comparison inside this new block; production P17 has no such block, so
it must not be presented as the whole implementation cost. Payload outputs
are retained conservatively in the isolated wrapper. Whole-project trimming,
fence logic, packing, placement and replicated logic can change the real delta.
No fitter, timing analysis or RBF was run for this measurement.

## Real CHECKNUM and next gates

Two fresh private 86Box arms use the unchanged CHECKNUM image and calibrated
CMOS, actual 50 MHz CPU and 8 MHz ISA, with exactly the same reused CPU objects
and updated profiler in both arms. Guest values and peripherals remain in
86Box; physical pin tests above validate data separately. The wrapper commits
host writes at logical CPU READY and cannot by itself validate backing-memory
effects of a reset before that READY. Use the physical cancellation tests for
that case. No live partial formatted number is treated as complete acceptance.

After completed guest output, compare both rates and phase counters, retaining
guest RC0/ALL_DONE separately from possible host teardown timeouts. If the gain
persists, adopt the measured block/fences, run bounded machine integration and
prepare the source candidate for the user's synthesis. Keep 50 MHz CPU options
unchanged; timing closure is explicitly deferred. MiSTer throughput and broader
compatibility remain hardware follow-ups.

See the [evidence inventory](../evidence/perf01-posted-write-20261002/README.md).
