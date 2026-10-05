# P05: descriptor and exception predicate selection

Date: 2026-10-01. These two combinational changes target the fitted
prefetch/decode -> limit qualification -> descriptor validation -> event
error-word path. They add no state, instruction cycles or bus transactions.

## Word-3 selection

Only the reserved-form check uses the high word of an eight-byte 286
descriptor. Other parser fields come from the three previously latched words.
The executor now checks both possible high words for zero in parallel and
selects the resulting predicate on completion. The unchanged parser checks
the lower words with a zero high word; the executor then qualifies its valid
and reserved-form outputs with the selected predicate. Code/data descriptors
still ignore the high word on a 286. The same factoring applies to IDT gates.

`prove_descriptor_word_select.py` reads the actual parser and both actual
executor fragments. Yosys SAT proves **all eighteen parser outputs** equivalent
for arbitrary two-state words, incoming data, phase and completion flags. It
also checks that the parser and surrounding executor are unchanged relative
to `fd9cd4c`. A wrong incoming-word zero predicate is rejected for each service.

## Exception classification

The CPU classifies whether each fault source carries an error word before
the final vector priority mux, preserving that mux itself and its complete
priority. The classification result selects the same validity bit directly.
The code data and event capture are unchanged.

`prove_fault_error_classification.py` proves the actual new expression against
the old expression using the actual unchanged vector-priority equation. All
source flags, all 256 values of both variable vectors, protected state and
segment index are unconstrained. This includes simultaneous diagnostic
faults, without assumptions about mutually exclusive instruction types.
Removing the invalid-opcode priority makes the negative control fail.

## Directed evidence and timing status

`test_descriptor_fault_timing.sh` runs both proofs, strict CPU `-Wall` lint in
base and production P01/P02/P05/P06 configurations, and call-gate/accessed,
protected-system, CPU-double-fault and task-LDT banks in both simulators. All
pass with the same check counts and cycle counts as before: 420/144 cases,
538 checks, 132/26 cases and 27 checks respectively.

PCAT's actual vendor tree also passes strict lint and the call-gate and
CPU-double-fault banks in both simulators under its production options.
Its protected-mode fetch `wrap_ip` binding is retained.

The formal and directed receipts are in
`docs/evidence/descriptor-fault-predicates-20261001/`. They concern two-state
combinational equivalence and directed execution, not a full CPU regression
or arbitrary X propagation. No MiSTer run was performed. The downstream
fresh fit `build/descriptor-predicate-sdram-budget-fit-20261001` includes these
changes and the corrected external SDRAM budget; its result is recorded
separately when available. This document does not assert 50 MHz closure.
