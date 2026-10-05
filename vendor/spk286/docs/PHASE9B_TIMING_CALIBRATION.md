# Phase 9B — instruction-timing calibration

Status: normalized functional calibration suite implemented. This is not a
historical 80286 timing certification and does not close Phase 9B.

## Scope

The suite measures isolated instruction intervals using the existing debug
retirement/event and timing-observer counters. The workloads run in Real Mode
with immediate `READY`, no compatibility padding and a deterministic memory
model. Each bank also checks the architectural checkpoint for the measured
class; the final state is not the only acceptance criterion. The `ADD AX,BX`
checkpoint additionally requires `FLAGS=0006` (PF and the architectural
reserved bit 1 set, with the other defined ADD flags clear):

| Class | Instruction form | Start | End | Observed cycles |
| --- | --- | ---: | ---: | ---: |
| `mov_ax_imm` | `MOV AX,1234` | `0100` | `0103` | 4 |
| `mov_bx_imm` | `MOV BX,5678` | `0103` | `0106` | 3 |
| `alu_reg` | `ADD AX,BX` | `0106` | `0108` | 2 |
| `mov_mem_read` | `MOV AX,[0200]` | `0108` | `010C` | 9 |
| `mov_mem_write` | `MOV [0202],AX` | `010C` | `0110` | 9 |
| `branch_short` | `JMP short` | `0110` | `0114` | 4 |
| `odd_word_read` | `MOV AX,[0301]` | `0100` | `0104` | 11 |
| `near_call` | near `CALL` | `0100` | `0106` | 11 |
| `near_ret` | near `RET` | `0109` | `0103` | 7 |
| `rep_movsb` | `REP MOVSB` | `0100` | `0102` | 22 |
| `int3` | `INT 3` event completion | `0100` | `0200` | 31 |
| `divide_fault` | divide-error event completion | `0100` | `0200` | 73 |

The register execution increment on 2026-09-22 reduced `alu_reg` from 8 to 2
clocks, preserving its exact result and FLAGS. It may now end during a code
request with no accepted bus transfer inside the measured interval; the
validator also retains admission of the original capture. See
[the optimization receipt](REGISTER_EXECUTION_OPTIMIZATION.md) for whole-stream
measurements and the distinction between execution and sustained throughput.

The immediate execution increment later that day reduced `mov_ax_imm` from 5
to 4 clocks and `mov_bx_imm` from 4 to 3 clocks. The latter now ends with the
next code request active. That endpoint is admitted alongside the historical
one; counter bounds, exact FLAGS, bus partition and memory requirements remain
enforced. See [the immediate receipt](IMMEDIATE_EXECUTION_OPTIMIZATION.md).

The values are measurements of the current normalized implementation. They
include the observed instruction-stream/prefetch and operand-service work, so
they must not be interpreted as intrinsic historical 80286 cycle counts.
The memory classes observe operand-service activity; the register/ALU/branch
classes do not. The workload also checks the final architectural state and
that no unsupported-opcode, microcode or control error occurred.

## Evidence and provenance

The selected target is the 80286 Real-Mode instruction architecture. No
physical 80286 trace is currently available for this increment; the evidence
level is therefore `normalized functional observation`. The calibration tool
records the simulator(s), source revision, complete RTL/generated/support
input hashes and CSV hashes in a JSON manifest. The input set includes both
calibration banks, so changes to the remaining-class bank cannot be hidden by
an unchanged baseline hash. With `--simulator both` it runs the two banks in
Verilator and Icarus and validates each result before accepting equality. The
version-2 manifest preserves the complete normalized rows, CSV schema and the
per-simulator raw-output hashes. It supports both the repository build
directory and an external `--build-dir`.

Run it with:

```text
make timing-calibration
```

The outputs are `build/timing/spk286_timing_calibration.csv` and
`build/timing/spk286_timing_calibration.json`. The CSV is assembled from
`sim/unit/spk286_timing_calibration_tb.sv` and
`sim/unit/spk286_timing_calibration_extra_tb.sv`; their schemas and case order
are validated by `tools/capture_timing_calibration.py`.

## Calibration-bank controls

The bank rejects a changed instruction start, an unexpected endpoint, an
unclassified measured instruction, a counter that exceeds the measured
interval or its published 64-bit width, an out-of-range IP, and a missing
class record. It also checks every published terminal field: the exact
per-class FLAGS checkpoint, the normalized final phase/status/owner tuple, the
policy, the lock marker and the complete counter set. For every interval it
also requires the BIU partition `biu_busy_cycles == accepted_transfers +
ready_wait_cycles`; operand, prefetch and queue metrics remain independent and
may overlap. Register and branch
classes must not report operand waits; memory classes must report operand
service. Near return and repeated string execution may legitimately have zero
queue-consume delta inside their measured interval because queue work can
overlap the selected boundary.

CSV parsing uses the original field sequence and requires the exact column
count for every row. In particular, a `csv.DictReader` overflow field cannot
be silently discarded during normalization. Both these parser/validator
failures are exercised through the `main()` path with identical invalid
simulator outputs; no success manifest is published.

The negative CSV fixtures in `tests/fixtures/phase9b/` are independent
validator counterexamples, not CPU captures. They cover an incorrect ADD
FLAGS result, incoherent terminal bus metadata and a counter beyond the
measured interval. The `main()` path validates each simulator's records before
publishing a manifest, so two simulators agreeing on the same invalid rows
still produce a rejection and no new manifest.

Event classes are labelled by their completion semantics: `INT 3` records the
software-event completion and `divide_fault` records vector 0 delivery. They
are not presented as ordinary retired-instruction latency.

## Validation status

The focused calibration bank and the remaining-class bank pass in both
Verilator and Icarus, and the combined capture compares equal across the two
simulators. The manifest keeps each original bank output separately: six rows
per bank and twelve rows only in the combined CSV, with per-file paths, hashes
and counts. This remains true for a single simulator and for an external
output directory; combining the rows no longer overwrites a raw baseline
capture.

Python validation covers the valid twelve-record suite, FLAGS and
terminal-bus mismatches, the BIU partition, exact CSV row width, all published
counter bounds, wrong case order, unexpected READY waits, missing memory
operand observation, invalid IPs and the preserved independent negative
fixtures. Historical accuracy, a physical reference comparison, native
T-state calibration and the compatibility timing profiles remain pending.

The suite remains evidence level `normalized functional observation`. Its
measurements include instruction-stream/prefetch and real dependency work;
they are not intrinsic historical cycle counts. Functional/dependency waits
remain separate from any future compatibility timing policy.
