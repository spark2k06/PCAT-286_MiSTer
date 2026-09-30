# SPK286 H09: far JMP through a call gate

Date: 2026-09-30. Imported from SPK286 commit `5a2af85` on
`codex/protected-mode-windows31`.

## Change

Immediate and indirect protected far JMP now resolve 286 call gates, validate
their target using JMP privilege rules and commit its CS:IP without a CALL
frame or a privilege/stack change. Gate target null/table/LDTR prechecks run
before descriptor reads. Type/privilege faults precede absence; a valid absent
target raises retryable #NP. The target Accessed write precedes cache commit.

The RTL and new directed bank are byte-identical to upstream:

- `vendor/spk286/rtl/spk286_micro_executor.sv`, SHA-256
  `b5822d6226a207f7676d6983c05c7b9e125f18dd9681a626e99f7d1927eef692`.
- `vendor/spk286/sim/unit/spk286_jmp_call_gate_tb.sv`, SHA-256
  `f5f65ba37b57b84ad71cd0689f85162a020d0b611d3fa5dda50bfb662c968f4c`.

The new bank is registered in the existing vendor test script. Microcode
sequences and generated images are unchanged. `config.tcl`'s local 25 MHz
debug selection was preserved and is not part of this import commit.

## Validation

- Upstream: 816 cases / 1,704 checks in both Icarus and Verilator.
- Vendor: the same bank passes with P01/P02/P05/P06 enabled, matching the
  functional CPU options in the current PCAT configuration.
- Upstream full-module lint, vendor core lint with those options, and
  microcode consistency checks pass.
- Existing upstream CALL, protected-system, outer-event, task-gate and
  far-transfer lifecycle banks pass in Icarus. No full regression or Quartus
  synthesis was run for this incremental CPU fix.

The normal 86Box executable was rebuilt from this vendor tree and installed
at `D:/GitHub/86box_dev/build/spk286/86Box-linux`, SHA-256
`90c980caee812bdecc6379b0f8aeb7f9b7ee8d9cf80c70d37e15e41f18779bb5`.
A full OS/2 desktop trial on a disposable VHD is in progress in
`build/spk286/os2-desktop-20260930-h09-final/`. Hardware and complete desktop
startup are not yet claimed at this checkpoint.

Diagnosis, Intel contract, baseline failures and complete focused results:
`D:/GitHub/SPK286/docs/OS2_DESKTOP_JMP_CALL_GATE_20260930.md`.
