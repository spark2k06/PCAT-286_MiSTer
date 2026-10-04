# P06 M6a — retained READ timing in the real BIU and operand service

Date: 2026-10-04. Status: **private directed acceptance passed**.
Work resumed after the user's M5 pause. This milestone builds a private copy
of the original BIU; production RTL, MAX configuration and the selected RBF
remain unchanged. It does not enable a historical profile in MiSTer.

## Scope and contract

The [Intel-derived contract](P06_TIMING_CONTRACT_20261003.md) distinguishes
physical completion from logical Ts/Tc completion. A memory READ can become
READY on any 50 MHz fabric edge. Its result must remain retained until the
qualified processor boundary and board READY permit logical completion.
The [Intel extraction](P06_INTEL_TIMING_REFERENCE_20261003.md) defines one Ts
and at least one Tc processor clock per transaction.

M6a covers byte READ at even/odd addresses and aligned word READ, with **CODE=0**.
It uses the real `spk286_biu`, real `spk286_operand` and the existing final
response storage. It adds neither a packet queue nor a second result buffer.
Admission is a qualified virtual boundary; physical capture is never gated
by that boundary. A same-edge READY/Tc completion uses the original lane
normalization. Early completion uses the retained slot, not live bus data.

The rational 6 MHz scheduler remains on the common 50 MHz clock (3/25 enable
ratio). The independent bench derives boundaries with integer arithmetic;
it derives address, BHE and payload from the accepted request. It poisons
live input data and requester fields after acceptance to expose stale/live
metadata use. It separately counts abstract board waits and an implementation
result arriving after its earliest permitted deadline.

The 0/1/2 board waits here are an **abstract fixture**, not a calibrated AT
motherboard profile or the native 86Box automatic-wait setting. This milestone
does not run the DOS timing wrapper or claim new 86Box benchmark measurements.

## Lifecycle and exclusions

Logical completion does not release a paused consumer's result. Cancel drops
the logical lifetime while the original BIU drains an accepted physical READ;
the canceled result cannot be published or reused by a later READ. Reset
clears both logical and physical state. Unsupported CODE, odd-word, write,
I/O, ACK, HOLD or LOCK requests produce a sticky private scope stop; they
cannot admit an unsupported operation, including a false ACK handshake.
An already active READ still drains under a scope stop.

There is a deliberately bounded gap between consecutive READs: this pilot
requires IDLE and an empty original raw slot before the next admission. It
does **not** yet validate a new Ts immediately on the preceding Tc. Removing
that gap requires separately qualified reuse and shared logical bus ownership.

M6a does not time memory instructions inside the full EU, each half of an odd
word, writes, I/O, INTA, HOLD/LOCK, arbitration, events or protected-mode
operations. It also does not combine M4 CODE timing with DATA timing. Physical
fetch completion can precede its logical release; a complete integration must
retain bus ownership until logical completion before letting DATA take over.

## Directed acceptance

| Check | Result |
| --- | --- |
| Real operand/BIU READ matrix | 432 cases: 3 lane forms x 3 board waits x 48 READY patterns |
| READY patterns | Fabric delays 0–45, exact logical Tc, late delay 80 |
| Captures outside virtual boundaries in matrix | 378 |
| Lifecycle and direct service | 33 cases: real caller pauses, retained backpressure, repeated identical requests, held READY, poisoned requester, cancel/reset and recovery without reset |
| Explicit unsupported scope guards | 42 cases: 7 guards x 6 lifecycle phases |
| Dual simulators | Icarus/Verilator summaries and all edge traces byte-identical |
| Independent negative control | Early raw publication mutant fails the specific logical-publication oracle |
| MAX affected compatibility | BIU, width/I/O, HOLD/LOCK, operand API, operand lifecycle and byte/register storage pass both simulators |
| MAX full CPU | 208 cases; original/private per-edge traces and summaries identical |
| MAX BIU sequential equivalence | Yosys proves the default-disabled adapter equivalent |
| Lint and generated microcode | Strict BIU MAX/timed and full MAX CPU lint pass; compiler consistency passes |

The oracle checks exact earliest Tc publication, read address/lanes,
payload, wait classification, no replay and no architectural operand side
effect while paused/canceled. It does not accept agreement between simulators
as a substitute for independently specified results.

## Partial resource measurement

| Isolated BIU mapping | Generic cells | Register bits |
| --- | ---: | ---: |
| Original | 504 | 88 |
| Private adapter, MAX | 504 | 88 |
| Restricted timed READ subset | 558 | 90 |
| Net restricted delta | +54 | +2 |

These are generic Yosys cells, **not FPGA ALMs or a complete P06/P12 cost**.
The restricted timed configuration statically prunes CODE/ACK/HOLD/LOCK logic;
that pruning can offset added temporal control. The complete BIU with those
services re-enabled needs another measurement. No new Quartus fit, RBF or STA
was produced for this private component. The selected production resource
baseline remains [the existing fit](PCAT_RESOURCE_BREAKDOWN_20261004.md).

## Reproduction and next gate

```sh
python3 scripts/run_p06_data_biu.py --output build/p06-data-reproduce
python3 docs/evidence/p06-core-data-20261004/audit.py --output build/p06-data-audit
```

The [frozen evidence](../evidence/p06-core-data-20261004/README.md) binds source
hashes, generated source, tools, logs, generic netlists, proofs and losslessly
compressed edge traces. The M3/M4/M5 frozen inputs remain unchanged.

Next is shared CODE/DATA logical ownership through the real components and
then a private full CPU, followed by memory instruction issue/commit milestones
and odd-word beat timing. Full IU
lookahead, instruction/event/PM coverage, the DOS timer/setup/return wrapper,
all historical speeds, public selector, machine integration, FPGA cost/STA
and later physical calibration remain separate acceptance gates.

The initial shared-ownership gate should first connect real fetch/queue,
operand and BIU components. Retain the logical owner beyond early physical
READY until Tc, using existing owner state where possible. Only an eligible
unaccepted DATA request may outrank new CODE; held accepted requests or an
occupied DATA result slot must not create false priority. After Tc, a paused
PUBLISHED result retains its association in its original slot without holding
the shared bus indefinitely. Guarding new issue alone is insufficient: the
shared scope stop must also prevent an old CODE result from being published.

Required directed cases include both owner transitions with early/exact/late
READY and 0/1/2 waits, active CODE versus new DATA priority, retained result
backpressure in both directions, cancel/redirect with drain and recovery,
independent address/BHE/status/payload, queue plus reservation at most six,
one logical owner and MAX equivalence. Same-Tc handoff, consecutive DATA reuse
and Intel EU-demand lookahead must each be explicitly qualified; this M6a
receipt does not establish them.
