# P06 M6e — private full-CPU odd-word A1 READ

Date: 2026-10-04. Status: directed acceptance PASS; frozen audit PASS.
This extends the frozen [M6c CPU](P06_CORE_MEMORY_CPU_PILOT_20261004.md)
and [M6d consecutive aligned evidence](P06_CORE_READ_STREAM_20261004.md).
Production source selection, config, physical 50 MHz clock and selected RBF
remain unchanged. This is a private 6 MHz virtual pilot, not a public profile.

## Functional and temporal boundary

Prefix-free Real Mode `MOV AX,[moffs16]` retains its original microcode,
operand service, TMP0/MOVE, first-byte register and final response slot.
Aligned words use one physical READ; odd words use two byte-lane READs.
The first READY captures the low byte from the high bus lane. The second
READ uses the incremented physical address and the low bus lane, including
carry across A16/A20. Segment-limit crossing at offset FFFF is excluded,
as it belongs to a separate fault qualification.

The accepted odd word owns DATA through both logical cycles. First physical
READY and first logical Tc cannot publish the complete word or release the
owner. The second physical request starts after the first logical Tc. Final
READY may occur between CPU ticks or on final Tc; either path must assemble
the same complete word. Pausing the EU cannot lose the accepted response.

The [Intel-derived contract](P06_INTEL_TIMING_REFERENCE_20261003.md) supplies
the A1 minimum of five clocks, plus two for an odd word and actual additional
READ waits. The offset parity is unknown at opcode admission. A distinct,
single accepted odd-Ts event therefore adds two to the existing duration
budget when parity becomes available. It is not a READ wait, and the current
physical address must not define parity after the first byte increments it.
Each half independently contributes its actual READY waits. Real fetch and
backend dependencies can extend execution beyond the minimum. These tests
do not certify exact native Intel issue/pin phases or EU-demand lookahead.

## Cancellation and restricted scope

Cancel retains the original physical lifetime until both accepted halves
drain, without requiring virtual Tc or board READY. The canceled result is
discarded. Reset interrupts the original backend immediately; reset tests
must not claim that an abandoned physical word drains in two captures.

HOLD is an unsupported historical scope guard in this pilot, not completed
historical HOLD/HLDA service. It blocks publication and retirement, while
physical work drains. Its sticky invalid scope is cleared by reset; a raw
response slot may remain occupied and hidden under that scope. Redirect
recovery after an invalid HOLD scope is not accepted here.

## Directed acceptance gates

The accepted build passes 2,143 timed cases (1,668 warm/cold matrix cases,
472 lifecycle cases and three deadline cases). Both simulators produce
43 byte-identical full-CPU trace pairs across timing, MAX and preservation
runs. Eight specific mutants fail their required independent assertions.
Lint, four affected MAX unit benches, microcode consistency, three component
equivalence proofs and private-input cone checks pass.

- 834 caller-defined vectors, warm and cold, including odd and aligned words,
  0/1/2 independent waits for CODE and each READ half, and early/exact-Tc/late
  physical responses. Lane poison values reject full-bus-word shortcuts.
- Pauses at acceptance, TMP0, between READ phases and final Tc; cancellation,
  reset and scope controls before/with first READY and between the halves.
- READY/final Tc on the independent `5 + 2 + waits` deadline, with commit at
  the following first eligible boundary once original TMP0 is ready.
- Original/private MAX executes the same 834 vectors with identical traces.
- The previous 267 aligned A1 and 240 consecutive programs retain their
  exact frozen warm/cold traces under the expanded private CPU.
- Required negative failures for duration/alignment, wait accounting, early
  commit, early second request, first-beat publication, premature owner
  release and wrong final assembly.
- Strict full-CPU lint for MAX/aligned/odd configurations, affected MAX units,
  microcode consistency, default bypass proofs and source guards.

The trace's `first_tc`/`final_tc` fields are post-edge diagnostic levels;
they are not pre-edge event pulses. The independent bench counts and checks
actual completions before each edge. The auditor separately reconstructs
the first eligible Tc from acceptance, capture and virtual boundaries.

## Isolated cost and defaults

| Generic component | Previous aligned | Odd candidate | Increment |
| --- | ---: | ---: | ---: |
| BIU cells / register bits | 546 / 78 | 573 / 82 | +27 / +4 |
| Duration cells / register bits | 303 / 19 | 306 / 19 | +3 / 0 |

These are isolated Yosys mappings, not Quartus ALMs or complete CPU/FPGA
overhead. The phase FSM expands from four to eight states; mapping recodes
its state bits. There is no new payload buffer, register bank, queue capacity
or PLL. Existing executor commit logic is reused; top-level qualification
is not included in the two isolated measurements.

The new parameters default to zero. BIU MAX is sequentially equivalent to
the original CPU with arbitrary private control inputs. Odd-disabled BIU
is equivalent to frozen M6c (one explicit hierarchical state-name mapping,
without removing equivalence obligations). The duration policy is equivalent
with late alignment disabled, and that input has no functional cone in the
MAX/default bypass. No FPGA fit, STA, new RBF or total regression is included.

```sh
python3 scripts/run_p06_odd_read_cpu.py --output build/p06-odd-read-reproduce
python3 docs/evidence/p06-core-odd-read-20261004/audit.py --output build/p06-odd-read-audit
```

[Frozen evidence](../evidence/p06-core-odd-read-20261004/README.md) binds
the exact generated CPU, caller coverage, traces, mutations and checks.
Writes/write-buffer overlap and read/modify/write remain the next memory
services; branches/events, decoded lookahead, the DOS wrapper, complete
public speeds and physical collaborator calibration remain separate gates.
