# P06 M6f — private serialized A3 word WRITE

Date: 2026-10-04. Directed acceptance PASS; frozen independent audit PASS.
This builds on the frozen [M6e CPU](P06_CORE_ODD_READ_CPU_PILOT_20261004.md).
Production config, source selection, physical 50 MHz clock and selected RBF
are unchanged. The candidate uses a private 6 MHz virtual CPU schedule.

## Functional boundary

The qualified instruction is prefix-free Real Mode `MOV [moffs16],AX` (A3).
Its original microcode, operand service, address, write payload and physical
byte-lane sequencing are retained. An aligned word has one physical WRITE;
an odd word has two, carrying AX's low byte on the first high lane and its
high byte on the second low lane. The original address increment carries
across A16/A20. Offset FFFF, MMIO, code modification, LOCK and events are
outside this qualification.

Memory changes on actual physical WRITE acceptance, independently of logical
Tc and CPU retirement. Logical DATA ownership persists until the final Tc;
the first odd beat cannot publish the whole operation or release its owner.
The existing response is consumed by the original store micro-operation.
The retained END phase then supplies functional completion to the duration
policy. It does not depend on `operation_valid`, which is false at END.

This milestone deliberately retains serialized functional completion.
It does not qualify the historical single write buffer's ability to let
the EU execute another instruction before the bus has finished. That C09
overlap remains a separate acceptance gate; serial completion must not be
used as the final historical write-buffer timing model.

## Timing reference

The [pinned Intel extraction](P06_INTEL_TIMING_REFERENCE_20261003.md) gives
A3 a minimum of three clocks (programmer B-73/PDF 281). B-6/PDF 214 adds
two clocks for an odd word reference and charges additional memory READ
waits. WRITE waits are not a READ correction and do not increment this EU
budget. In the serialized pilot, real WRITE completion remains a dependency
that may extend retirement beyond the minimum of three/five clocks.

Parity becomes known after opcode admission. A separate accepted odd-Ts
event adds two clocks once. Its eligibility is retained separately from
permission to charge READ waits. This prevents A3's absence of a READ from
either suppressing alignment or incorrectly charging WRITE waits.

Hardware 3-17/PDF 67 describes Ts/Tc and WRITE acceptance; 3-25/PDF 75 and
4-4 describe one retained write and EU overlap. Native 86Box's A3 handler
writes memory and charges two clocks in its simplified execution model.
It provides a functional comparison, not an exact Intel issue-phase oracle.
No aggregate table minimum here certifies native pin phases or EU lookahead.

## Cancellation and reset

Cancellation cannot undo a physical write. An accepted canceled odd word
drains both halves using the existing retained address/payload, suppressing
logical response and instruction retirement. Invalid HOLD scope also blocks
publication while physical work drains; its scope remains sticky until reset.

Reset interrupts the original BIU immediately. Reset after the first odd
WRITE can leave a partial memory update and must not be described as draining
the entire word. The mutable-memory fixture retains already accepted lane
effects and separately rebases the CPU after reset.

## Acceptance and cost

The directed gate checks caller-defined payloads, mutable memory at every
edge, early/exact-Tc/late physical READY, independent 0/1/2 board waits per
beat, warm/cold fetch, pauses and abandonment. It also requires original
versus private MAX trace equality, frozen READ trace preservation, strict
lint, component bypass proofs and negative controls.

The caller's AX snapshot is assigned explicitly after each file scan. An
initial continuous alias of the scanned register vector retained the previous
row under Verilator; a two-row reduction showed correct DUT AX/TMP0 with a
stale fixture expectation. The corrected fixture retains the original payload
assertion and requires a fresh complete dual-simulator acceptance run.

Both simulators pass 2,227 timed cases: 834 caller vectors warm/cold, 556
pause/cancel/reset/scope controls and three exact-final-Tc cases. All 47 dual
trace pairs are byte-identical. Original and private MAX each pass the same
834 WRITE cases. The frozen M6e READ matrix retains its exact 834 warm/cold
traces with WRITE enabled. Eight specified mutants fail independent oracles
for alignment, incorrect WRITE-as-READ wait accounting, early retirement,
missing END handshake, early second request, first-beat publication,
premature owner release and wrong payload lane.

Four affected MAX unit benches and microcode consistency pass. Component
preparation passes strict lint in five configurations, MAX and WRITE-disabled
sequential equivalence, and private-input cone checks. WRITE disabled retains
the M6e component counts exactly. No full-CPU formal equivalence is claimed.

| Generic component | Frozen M6e | WRITE candidate | Increment |
| --- | ---: | ---: | ---: |
| BIU cells / register bits | 573 / 82 | 579 / 82 | +6 / 0 |
| Duration cells / register bits | 306 / 19 | 313 / 20 | +7 / 1 |

The combined isolated increase is 13 generic cells and one control register
bit. There is no new payload slot, register bank, queue capacity or PLL.
Top-level qualification is outside these two component measurements. Generic
Yosys cells/register bits are not Quartus ALMs or complete CPU/FPGA cost. This
milestone does not include a full regression, fit, STA or a new RBF.

```sh
python3 scripts/run_p06_write_cpu.py --output build/p06-write-reproduce
python3 docs/evidence/p06-core-write-20261004/audit.py --output build/p06-write-audit
```

The [frozen checkpoint](../evidence/p06-core-write-20261004/README.md) binds
source/generated hashes, caller fixtures, traces, mutations and checks.
This advances only the WRITE subset of C08/C10/C15. Consecutive writes,
same-address following READ, historical write-buffer overlap, RMW and the
remaining instruction/event/public-speed coverage remain separately open.
