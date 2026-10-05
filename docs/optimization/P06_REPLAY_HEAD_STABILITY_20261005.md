# P06 replay head timing work — 2026-10-05

## Purpose and unchanged behavior

The previous all-features candidate's worst setup path starts in the target
replay's 80-bit M10K storage and returns to its read pointer through decoder,
timing policy and exception backpressure. Its setup slack is −19.145 ns at a
physical 50 MHz. This is an internal timing problem independent of outstanding
MiSTer measurements of the historical speed profiles.

Store the next replay byte directly at slot zero. An accepted consume shifts
the unread bytes; an accepted capture appends after that shift. The total
capture counter still rejects an eleventh byte, even after earlier consumption.
Reset, cancellation and new-epoch priority are unchanged. No additional edge,
historical clock, wait state or public handshake was introduced.

The active CPU generator records the new helper hash. Generated CPU and event
RTL bytes remain identical. No PLL, profile divisor, SDRAM relationship, timing
constraint, OSD setting or architectural decoder was changed. The earlier RBF
remains the hardware measurement reference.

## Directed verification

| Gate | Result |
| --- | --- |
| Existing unchanged replay unit | 246 checks in both Icarus and Verilator PASS |
| Strict Verilator helper lint | PASS |
| Formal state relation / output equivalence | Induction PASS for arbitrary control and byte inputs after reset |
| Corrupted capture and broken pop negative controls | Both rejected with counterexamples |
| Full CPU handoff integration | 777 cases per simulator, all eight profiles PASS |
| Comparison with the prior accepted directed receipt | Every result record, clock, budget, event frame, fault, cancellation, HOLD and MAX full raw-stream digest identical |
| Generic Yosys synthesis and structural check | PASS |

The formal instrumentation only adds observation ports to unchanged sequential
bodies. The invariant equates the total write count, read offset and ordered
unread bytes. Initialized state is zero and step one resets both implementations.
The first 24-step bounded SAT attempt timed out at 60 seconds; that record is
preserved. Adding explicit state invariants allows a successful induction proof,
without changing the implementation or output assertions.

Generic Yosys logic changes from 243 to 251 cells and from 92 to 88 register bits.
These are generic mapped cells, **not Cyclone V resource estimates**. Quartus
placement, setup and hold must be measured before assessing the physical benefit.

No new instruction behavior was added. The earlier raw CPU/SingleStep evidence
still applies to the unchanged CPU inputs. The complete compatibility regression
remains **USER_DEFERRED** as requested; these results are directed qualification.

## Evidence and next gate

The [sealed packet](../evidence/p06-replay-head-20261005/manifest.json) preserves
tested sources, unchanged benches, exact baseline comparison, proof scripts,
negative controls and simulator logs. Compiler objects and executables are not
archived.

Verified implementation commit: `c90f7b5`. A fresh all-features fit started at
2026-10-05 07:50:06 UTC under
`build/p06-replay-head-allfeatures-20261005-v1`, at the existing physical 50 MHz.
Four-corner setup/hold reporting and resource comparison follow compilation.
This change is not yet claimed to improve fitted timing or qualify hardware
stability.

After archive byte verification and confirmation that simulator processes had
finished, the four owned proof/integration work directories and temporary
collector were removed: 609,533,055 logical bytes. The active frozen fit and
earlier measurement RBF were retained. The cleanup receipt is in the packet's
directory; the ongoing fit databases will be removed only after its results
and effective inputs have been preserved.
