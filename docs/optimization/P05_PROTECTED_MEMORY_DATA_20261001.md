# P05: direct data for protected-memory services

Date: 2026-10-01. Scope: a combinational CPU data path; no new register,
micro-operation, instruction cycle or bus transaction.

## Change and invariant

`spk286.sv` gives the micro-executor raw `memory_read_data` directly while a
descriptor, protected event gate or TSS service is active. All other accesses
retain the existing operand mux. The existing register-direct binding forbids
register selection for those services, and each of their state flags already
dominates the operand module's `select_rm` input. The original operand result
is therefore exactly the same raw sixteen-bit memory word in these states,
including byte-request combinations.

This makes the required data source explicit before the executor parses a
descriptor. Previously, synthesis left a path through instruction decoding,
operand register-index selection and the register/memory mux before descriptor
reserved-form validation and exception error-code capture. The change removes
that unnecessary dependency without changing descriptor rules or fault order.

## Validation

`scripts/prove_protected_memory_data.py` extracts the actual operand equations
and checks the actual service aliases, selector prefix and CPU bindings. It
proves equivalence for all two-state input data, register values, indices and
qualifiers with Yosys SAT. The remaining `select_rm` OR terms are unconstrained,
a stronger space than the reachable CPU states. A deliberately wrong memory
word fails the proof. A source guard verifies that surrounding CPU top and
sequential logic are unchanged relative to `2073e967`.

`scripts/test_protected_memory_data.sh` runs strict CPU `-Wall` lint and four
directed banks in both Icarus and Verilator, with both the base configuration
and the actual PCAT P01/P02/P05/P06 options:

| Bank | Result in each simulator/profile |
| --- | --- |
| Call gates and accessed descriptors | 420 checks / 144 cases |
| Protected system operations, with READY stalls | 538 checks |
| CPU double-fault handling | 132 checks / 26 cases |
| Protected task LDT handling | 27 checks |

The downstream PCAT vendor tree also passes strict lint and call-gate and
CPU double-fault banks in both simulators with production options. Its
existing protected-mode fetch `wrap_ip` integration remains intact.

The proof concerns two-state equivalence, not arbitrary X propagation. No
full CPU regression or physical hardware test was run for this milestone.
The formal receipt is retained in
[formal receipt](../evidence/protected-data-sdram-entry-20261001/formal-receipt.json).

## Fitted evidence

The downstream frozen Quartus run
`build/protected-data-sdram-entry-fit-20261001` also includes the separately
tested registered SDRAM-owner entry. All four corner reports and exact source
identities are retained downstream. Timing results must be read together with
the SDRAM external-budget qualification; this milestone alone does not imply
whole-system 50 MHz closure.

Fitted results (ns), with the inherited SDRAM budget:

| Corner | Global setup | Global hold | Owner setup | SDRAM output setup |
| --- | ---: | ---: | ---: | ---: |
| 7_slow_1100mv_100c | -4.229 | +0.107 | +1.741 | +8.904 |
| 7_slow_1100mv_-40c | -4.053 | +0.003 | +1.848 | +9.154 |
| MIN_fast_1100mv_100c | +2.124 | +0.120 | +8.805 | +12.754 |
| MIN_fast_1100mv_-40c | +2.379 | +0.053 | +9.334 | +13.572 |

RBF SHA-256: `379d280aa429761828722e3ff72509c692e51ae3ec2d24da03a0efed6f6d8beb`. Owner incoming setup is now positive
in both slow corners, from -1.819/-2.047 ns previously to +1.741/+1.848 ns.
The remaining CPU critical path still has 23/21 logic levels through
operand completion, descriptor form validation and error-word capture.
All constrained recovery/removal checks remain positive.
