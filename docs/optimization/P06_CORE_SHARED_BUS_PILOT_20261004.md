# P06 M6b — shared logical CODE/READ ownership

Date: 2026-10-04. Status: **private directed acceptance passed**.

This component milestone connects the real fetch, six-byte prefetch queue,
operand service and BIU. It extends the frozen [M4 CODE timing](P06_CORE_FETCH_PILOT_20261004.md)
and [M6a READ timing](P06_CORE_DATA_READ_PILOT_20261004.md) through separate,
reproducible source generation. It does not enable a historical profile in
the production CPU or change the selected MiSTer RBF.

## Ownership contract

The [Intel-derived contract](P06_TIMING_CONTRACT_20261003.md) separates physical
READY from logical Ts/Tc completion. A physical READ can finish on any 50 MHz
fabric edge; CODE or DATA retains the logical bus until its qualified Tc.
Capturing an early result cannot make the other client start early.

M6b reuses the original BIU owner registers, fetch response slot and DATA
response slot. It adds no owner, cancellation or payload register bank, queue
capacity or second functional engine. CODE issue and DATA acceptance acquire
ownership; logical completion releases it. A new opposite-class request can
start on that same Tc boundary, including when physical READY also occurs on
the boundary. An accepted canceled READ drains physically before releasing
the bus. Restart invalidates CODE; DATA cancellation invalidates DATA.

DATA priority is evaluated from an eligible, unaccepted request. An accepted
request still held by its caller, or an occupied DATA response slot, does not
claim priority over new CODE. Once Tc has completed, a paused consumer keeps
its result in the original slot without retaining logical bus ownership.
CODE queue admission reserves the pending packet's bytes and cannot exceed
six bytes in queue plus reservation.

The valid private configurations are MAX with all timing parameters zero, or
timed fetch together with both BIU DATA and shared timing enabled. These are
test parameters, not restored production config switches. Unsupported ACK,
HOLD, LOCK, writes, I/O and odd-word DATA produce a sticky scope stop. It blocks
new requests and invalidated publication, including an already-PUBLISHED
CODE packet, while allowing an accepted physical READ to drain. Reset clears
the shared context.

## Directed acceptance scope

The fixture runs on a common 50 MHz clock with the qualified 6 MHz rational
boundary (3/25). Abstract board waits of 0/1/2 are test inputs, not a calibrated
motherboard or the native 86Box automatic-wait setting.

| Check | Coverage |
| --- | --- |
| Opposite-owner transition matrix | 972 cases: 2 directions x 2 CODE alignments x 3 DATA lane forms x 3 CODE waits x 3 DATA waits x 3 CODE READY patterns x 3 DATA READY patterns |
| READY patterns | Early physical capture, exact earliest Tc, and fabric delay 80 |
| Same-Tc cross-owner start | All 972 transition cases require the new start to equal the previous completion boundary |
| Consumer/queue stress | 8 cases: paused CODE publication, held accepted DATA, paused real operand, poisoned metadata in both directions, two full/near-full queue streams, and an interleaved four-packet CODE stream |
| Cancel selected owner | 12 cases: both clients x 6 phases; physical drain and fresh opposite client recover without reset |
| Cancel opposite client | 10 cases: both clients x 5 phases, including paused PUBLISHED results |
| Reset | 12 cases: both clients x 6 phases, with physical/response/queue state cleared |
| Unsupported scope | 72 cases: both clients x 6 phases x 6 explicit guards |
| Fresh reset context | 1 further CODE/READ pair after the scope matrix |

The observer derives virtual boundaries, earliest completion, mandatory issue,
cursor, request metadata, payload, response readiness, queue occupancy and
logical ownership independently. It requires the physical bus to appear after
acceptance and stay present until READY. It checks DATA priority, lane
normalization, queue byte order, exact result association, no replay and no
operand side effect under pause/cancel. Poisoned live data and requester fields
expose a response incorrectly sourced from the current bus or caller.

The runner and frozen auditor require exact case sets, not merely PASS markers
or agreement between simulators. A premature-owner-release mutant must fail
`shared logical owner oracle failed`; removing CODE publication's scope guard
must fail `CODE publication oracle failed`.

MAX acceptance includes eight affected unit benches in Icarus and Verilator,
208 original/private full-CPU cases with byte-identical per-edge traces, strict
component and full-MAX lint, and generated microcode consistency. Sequential
BIU and fetch proofs keep the new input controls arbitrary on both interfaces;
the golden component ignores them. MAX synthesized netlists additionally
require every private input control to have no logic or original-output cone.

Both simulators pass all **1,087 component cases**, with byte-identical edge
traces and summaries. The transition matrix captures 1,296 responses outside
virtual boundaries; stress and lifecycle/scope fixtures capture another 109.
Both negative controls fail their specified oracles. BIU and fetch MAX
sequential proofs establish 145 and 170 equivalence cells respectively.
M3/M4/M5/M6a preservation audits pass.

## Partial resource measurement

| Isolated component | Original/MAX generic cells | Original/MAX register bits | Timed generic cells | Timed register bits |
| --- | ---: | ---: | ---: | ---: |
| BIU | 504 | 88 | 540 | 78 |
| Fetch | 508 | 98 | 605 | 102 |

These are restricted generic Yosys mappings, **not Quartus ALMs or the cost of
the complete timed CPU**. Unqualified ACK/HOLD/LOCK/I/O/write cones are statically
pruned; net reductions in register bits do not establish FPGA savings. The
figures exclude full-CPU issue/commit control and subsequent services. MAX
matches each original component. No new FPGA fit, STA or RBF is part of M6b.
The [production resource baseline](PCAT_RESOURCE_BREAKDOWN_20261004.md) remains
the previous fit.

## Reproduction and next gate

```sh
python3 scripts/run_p06_shared_bus.py --output build/p06-shared-reproduce
python3 docs/evidence/p06-core-shared-bus-20261004/audit.py --output build/p06-shared-audit
```

The [frozen evidence](../evidence/p06-core-shared-bus-20261004/README.md) binds
source hashes, generated components, simulator logs, edge traces, MAX proofs
and isolated synthesis. M3/M4/M5/M6a sources and evidence remain frozen.

Same-Tc cross-owner handoff is qualified here. Consecutive DATA reuse still
requires the M6a IDLE/empty-slot gap. This component does not establish full
instruction execution timing, EU-demand lookahead, odd-word beat timing,
writes/write-buffer overlap, I/O, INTA/HOLD/LOCK, PM or events. It does not
produce new DOS benchmark measurements or calibrate a physical AT.

Next connect these services to a private full CPU and qualify actual aligned
memory READ instruction issue, retained operand/result, architectural commit
and retirement. Preserve explicit unsupported scope and the M5 register
handoff; do not substitute a mock functional dependency for real execution.
Odd-word/write and bus/event milestones, the DOS timer/setup/return wrapper,
all historical speeds, public selector, machine integration, total FPGA cost
and STA remain separate gates. Initial work continues against the identified
Intel/native 86Box references while physical collaborator calibration is
pending.
