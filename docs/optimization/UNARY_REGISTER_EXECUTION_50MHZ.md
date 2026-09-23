# Unary register execution optimization

This change shortens register-direct `NOT`, `NEG`, `INC` and `DEC` execution.
It changes the functional schedule while preserving the existing ALU, decoder,
register file and flag masks. It does not add historical T-states, wait states,
or cache behavior, and does not claim cycle accuracy.

For Group 3/5 byte and word operations, the executor captures the register
operand and operation-specific constant, then commits the ALU result and flags
as one operation. Scalar `INC/DEC r16` uses the same direct destination path.
Memory operands keep the original read, ALU and writeback sequence. The
compiler validates that fallback before emitting the ROM.

The PCAT vendor copy keeps its downstream control encodings unchanged:
`CARRY_FILL8=171` and `LOADALL=172`. The added unary controls use 190 through
192, so the LOADALL and SALC extensions remain intact.

Validation completed for this transfer:

* 17 compiler, microcode and audit contract tests passed;
* register execution and immediate execution suites passed under Icarus and
  Verilator, including protected-mode LOADALL;
* Yosys synthesis sanity passed;
* the standalone SPK286 full regression and SingleStep sample passed.

The new PCAT no-debug RBF was generated at
`output_files/PCAT-286_UNARY_OPT_50MHz.RBF` (SHA-256
`f4a578a45e99a3a05ff8b6187ae537e2edec29604eed0d5990238c4053043b25`). The
CheckIt run reported 3,584 Dhrystones and 71.9K Whetstones at 35.01 MHz;
the preceding run reported 3,489 Dhrystones and 71.9K Whetstones at 34.96 MHz.
This is a modest observed Dhrystone increase, with no visible Whetstone change.

Timing remains open. Quartus reports 41.84 MHz Fmax for `FPGA_CLK2_50` in the
slow 100 C model. Its worst path starts at the executor's
`allocation_valid_q`, passes through bounds/fault and operand logic, and ends
at a general-purpose register write. The full design also has slower unrelated
generated-clock paths; timing work should use the per-clock paths to keep the
CPU result distinct from video and system clocks.
