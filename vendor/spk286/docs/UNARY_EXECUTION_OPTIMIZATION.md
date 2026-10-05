# Unary register execution optimization — 2026-09-22

This increment shortens the internal execution path for register-direct
`NOT`, `NEG`, `INC` and `DEC` operations. It is a functional scheduling
optimization in the standalone CPU; it does not add T-states, wait states,
cache behavior or machine integration, and it is not a claim of historical
80286 cycle accuracy.

The six Group 3/5 byte and word entries use dedicated format-22 controls.
When ModR/M selects a register, the executor captures the source and the
opcode-selected constant, runs the existing ALU, and commits the result and
masked FLAGS atomically on the next enabled clock. The scalar `INC/DEC r16`
entry uses the same direct destination capture. `NOT` supplies all ones,
`NEG` supplies zero with the existing reversed ALU operands, and `INC/DEC`
supply one. The existing decoder and ALU remain the only sources of operation
semantics and flag masks.

Memory ModR/M forms retain their original `READ_RM`, ALU, writeback and
`COMMIT_FLAGS` tail. The compiler validates that tail and the generated ROM,
symbol and validation artifacts are regenerated from the `.mc` sources. Only
the accepted ModR/M byte can trigger the shortcut; displacement and operand
bus bytes cannot create a register capture.

The optimized path is cancellation-safe: pause holds the captured operands,
redirect/reset clears pending state, and retirement remains a single
microsequencer-owned pulse. The unary lifecycle test also covers cached EA
context reuse after Group 3/5 dispatch, operand stalls, cancellation, reset,
invalid extensions and a following instruction stream.

Focused validation completed for this increment:

* 95 Python microcode/compiler tests;
* microcode audit and generated-image consistency check;
* 10,832 directed unary instruction cases, 752,840 checks, zero immediate
  stalls (Verilator);
* 70 unary lifecycle cases, 3,150 checks (Verilator and Icarus);
* 78 register execution cases and 184 immediate execution cases (Verilator
  and Icarus).

The remaining sequential memory path and the instruction-fetch/BIU boundary
are unchanged. Any measured throughput gain therefore depends on the ratio of
register-direct unary operations and must be assessed separately from
historical timing and downstream SDRAM behavior.
