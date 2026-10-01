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

## Fresh fit with corrected SDRAM budget

| Corner | Global setup | Global hold | Owner setup | SDRAM output setup | SDRAM output hold |
| --- | ---: | ---: | ---: | ---: | ---: |
| 7_slow_1100mv_100c | -4.341 | -3.086 | +0.958 | +4.268 | -3.086 |
| 7_slow_1100mv_-40c | -3.878 | -3.071 | +0.927 | +4.903 | -3.071 |
| MIN_fast_1100mv_100c | +2.220 | -2.515 | +7.362 | +9.173 | -2.515 |
| MIN_fast_1100mv_-40c | +2.484 | -2.590 | +7.742 | +10.710 | -2.590 |

This is a failing timing checkpoint, not closure. The descriptor predicates
alone did not remove the late fault path. The external SDRAM hold failures
persist in a new fit with ALL_PATHS hold repair, rather than only in an SDC
overlay. The forwarded clock uses a global clock as output data: the worst
warm slow hold path has +5.044 ns skew, including 4.935 ns global-to-output
routing on the clock pin. The next experiment must change real clock/output
implementation and preserve the external delay budget.

Complete fitted audit and bitstream identity are retained in the evidence directory.
No hardware run or full CPU regression was performed.
