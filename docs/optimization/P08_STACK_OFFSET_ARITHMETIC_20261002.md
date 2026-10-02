# P08: independent stack-offset arithmetic - 2026-10-02

## Physical hypothesis

The downstream PCAT RTC lookup seed-2 fit has CPU setup slack -0.141 ns
at slow 100 C and -0.239 ns at slow -40 C. Its critical route passes
through late operation qualification, stack-offset mux/arithmetic,
protected access checking, operand completion and GPR priority logic.
The standalone change completes the independent subtraction/addition
before the offset mux and keeps those combinational boundaries.

The call-parameter write offset remains `stack_cursor_q - 2`. The outer
return offset remains `return_stack_pointer + (allocation_valid_q ?
allocation_q : 0)`. All arithmetic remains 16 bits. The mux priority is
unchanged: parameter read, parameter write, outer return, frame read,
then the native stack offset.

No register, clock, microinstruction, enable, bus handshake or instruction
cycle count changes. There is no new architectural behavior. A fresh fit
is required to determine whether the structure improves physical timing;
formal correctness alone does not establish an improvement.

## Bounded verification

`scripts/prove_stack_offset_arithmetic.py` extracts the actual assignments
from reference commit `792f652` and the candidate. Yosys proves equality
for all 101 two-state input bits, including simultaneous selectors,
allocation-valid choices, subtraction underflow and addition wrap. A
whole-module guard permits only the three helpers and the offset mux to
differ; the surrounding combinational and sequential RTL is identical.
Wrong decrement and missing allocation mutants both produce SAT
counterexamples and are rejected.

`scripts/test_stack_offset_arithmetic.sh` checks generated microcode
consistency, strict whole-CPU Verilator Wall lint, and three affected
test banks with both Icarus and Verilator in both profiles:

| Bank | Checks per run | Additional coverage |
| --- | ---: | --- |
| Call-stack precheck | 9 | frame/range boundary behavior |
| Protected outer event | 6 | privilege stack transition and READY stalls |
| Call-gate accessed | 420 | 144 cases and descriptor/accessed behavior |

The production profile enables P01, P02, P05, P06 and P07. All 12 bank
runs pass, both lint logs are empty, simulator result lines agree, and
the candidate/proof/runner hashes match again at the end. Expected test
results are unchanged. Evidence is in
`docs/evidence/stack-offset-arithmetic-20261002`.

No full CPU regression or hardware test was performed. The physical fit
and current CheckIT measurements remain separate evidence.

## PCAT integration

The vendor executor is byte-identical to the proven standalone source at
commit `64cdc0b`. Two previously absent affected unit banks are copied
unchanged; existing expected results and the vendor signal declarations
are retained. The actual vendor base and production profiles pass strict
whole-CPU Wall lint and all three banks in both simulators. Production
macros are read from the same config.tcl as Quartus, including P07.

Every cycle, stall, bus, register and memory metric in the eight physical
SDRAM-owner CheckIT fixtures equals the previous P07 baseline. The sole
CPU integration wrap_ip binding is retained. CheckIT hardware results
have not been measured again. No global CPU regression was run.

The next frozen-input fit uses the original 20 ns system and unchanged
SDRAM/held-payload budgets; it does not select the rejected 0.6/1.0 ns
route-bound experiments. The completed seed-2 fit has CPU setup +0.540 ns
at slow 100 C and +0.467 ns at slow -40 C, with CPU hold positive in all
four models. Complete-design setup still fails: the global minima are
-0.255/-0.033 ns, and warm scaled HDMI output also has -0.214 ns. Seed 3
has CPU setup -0.160/-0.005 ns and is not selected. Both measured fits,
unchanged timing budgets and controlled regenerated metadata are retained
in `P05_STACK_OFFSET_SEED2_FIT_20261002.md` and the seed-3 counterpart.
Complete-design closure remains pending.
