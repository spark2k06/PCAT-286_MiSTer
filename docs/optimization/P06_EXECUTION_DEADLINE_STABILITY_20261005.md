# P06 execution deadline timing work — 2026-10-05

## Critical-path hypothesis

The registered-head fit still has −16.044 ns worst setup at the existing
physical 50 MHz. Its worst path traverses prefetch data, opcode decoding,
metadata classification and arithmetic, deadline comparison, EU exception
selection, and microsequencer admission. There are 31 logic levels.

The original metadata lane selects the next decoded head before a body starts
and the retained instruction context during execution. Physically, this puts
admission decoding on the retirement/REP permission cone, even though a body
deadline is never needed for the admission case.

Add a parallel combinational metadata lane using only the retained execution
opcode/entry, with the same event context, operands, outcome/count, prefixes,
REP policy and READ qualification. Use it for the deadline comparison. Preserve
the original admission metadata for captured state, elapsed accounting and
scheduled-clock telemetry. No register or virtual-clock stage is inserted.
No instruction minimum, divisor, PLL, dependency, timing constraint, event
priority or raw CPU behavior is changed.

## Verification

| Gate | Result |
| --- | --- |
| Existing scheduler, handoff and replay units, each simulator | 54 / 398 / 246 checks PASS |
| Existing five negative controller mutations | All rejected; adapted only implementation anchors |
| Strict helper and generated full-CPU lint | PASS |
| Symbolic metadata lane equality | PASS using expressions extracted from the actual generator |
| Scheduler state and every public output | Induction PASS under the proved lane contract |
| Wrong next-head opcode in execution lane | Rejected with counterexample |
| Full CPU handoff, all eight profiles | 777 cases in each simulator PASS |
| Exact prior directed receipt comparison | All results, clocks, budgets, frames, faults, cancellations, HOLD and MAX public-stream digest unchanged |
| Directed compatibility: execution, prefixes, events, REP memory/I/O zero-count | 15 Icarus + 15 Verilator records at MAX/6/25 PASS; five MAX raw CPU pairs exact |
| Generic synthesis | Scheduler 383 → 525 generic cells; 37 retained register bits unchanged |

The lane theorem holds for arbitrary context inputs whenever `body_active` is
true. The caller's original `candidate_body` expression then excludes the
next-head opcode. Qualification, clock budget and READ policy match exactly.
The scheduler proof equates its 37 retained bits and every public output after
zero initialization and reset at step one. Outside a body, the two metadata
inputs may differ freely. These assumptions are explicit and discharged by
the actual-context theorem, not treated as unverified timing exceptions.

The first formal adapter attempt omitted Yosys `-set-assumes`; independent
arbitrary lane values then produced an expected mismatch. That failed record
is retained. The corrected run applies the separately proved contract without
changing the production implementation or expected outputs.

The two existing scheduler benches only wire the additional lane inputs to
their original stimulus. Architectural assertions, instruction kernels and
expected clock values are unchanged. The ordinary timing policy module and
raw CPU sources retain their earlier validated hashes. The full compatibility
regression remains **USER_DEFERRED**.

## Cost, fit and evidence

Generic cell counts are not FPGA ALM estimates. Duplicated combinational
classification may increase ALMs; Quartus must measure actual sharing,
placement, setup and hold before judging this tradeoff. No new registers,
memory, DSP or clock hardware are requested by the implementation.

The [sealed packet](../evidence/p06-execution-deadline-20261005/manifest.json)
retains exact tested sources, fixtures, logs, proof scripts, counterexamples,
receipts and baseline comparisons. Simulator objects are excluded and removed
after byte verification. Verified implementation commit: `99c4934`.

A fresh all-features 50 MHz compile started at 2026-10-05 10:56:40 UTC in
`build/p06-execution-deadline-allfeatures-20261005-v1`, from 1,375 frozen input
files. It remains pending; no physical setup improvement or FPGA cost is claimed
yet. Adlib/OPL2 stays enabled. Four-corner detailed timing follows the fit.
The previous RBF remains the hardware/profile measurement reference.

After checking the sealed packet against every archived byte and confirming
the directed processes had completed, five owned test directories and the
collector were removed: 1,300,998,280 logical bytes. The active fit workspace and
earlier RBFs were retained. The packet directory contains the cleanup receipt;
the fit's databases will be cleaned after its effective sources and results
have been preserved.
