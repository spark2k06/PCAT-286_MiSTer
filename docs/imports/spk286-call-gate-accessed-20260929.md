# SPK286 H22 call-gate Accessed-bit fix

Date: 2026-09-29.

Imported from SPK286 commit `f083333` on `codex/protected-mode-windows31`.

## Change

The descriptor phase-3 transition now enters the existing Accessed-bit write
phase for a valid call-gate code target with A=0 and a valid target offset.
Previously `VALIDATE_CALL_CS` repeatedly read the target and never completed.
This is H22, an independent defect rather than H19's boundary/restart matrix.

Imported files:

- `vendor/spk286/rtl/spk286_micro_executor.sv` (identical to upstream).
- `vendor/spk286/sim/unit/spk286_call_gate_accessed_tb.sv` (identical to upstream).
- One test registration in the existing vendor `scripts/test_units.sh`.

Executor SHA-256:
`dbe6d503de33e14728dbfdf17ef4f999f51e087ba7565d66c4d6038e33d7f558`.
Unit SHA-256:
`e5da1816b5ae495e61a532c2c4fd8a818b389a5f7e428f2b72a3877dc807aec7`.

## Validation

- Upstream directed call-gate bank: 420 checks / 144 cases, both Icarus and
  Verilator, including A=0/1, READY stalls, timing policies and #NP repair/retry.
- Same bank against the vendored RTL: Icarus PASS, 420 checks / 144 cases.
- Upstream lint and microcode consistency PASS; affected protected-system,
  direct-call and RETF banks PASS in Icarus.
- Yosys micro-executor `hierarchy; proc; opt; check -assert`: zero problems.
  No Quartus/RBF build or full regression was run for this individual fix.
- 86Box rebuilt using this vendor tree. Normal executable:
  `D:/GitHub/86box_dev/build/spk286/86Box-linux`, SHA-256
  `dfe0726661e92cd39083c34048a4c8723031c1666f7144492ab7e5e507005eac`.

## OS/2 result

The isolated MR BIOS / 6 MHz / 2 MB / EGA trial passes the former call-gate
stall at `0257:214C` and executes inside target `007E`, with A now set.
The next recorded discrepancy is #GP(`006C`) at `0228:7A57`,
`LDS SI, SS:[BX]`, loading readable conforming DPL2 code into DS at CPL0.
This matches the existing pending H06 finding; it is not corrected here.
No completed desktop boot is claimed.

Detailed evidence and interpretation:
`D:/GitHub/SPK286/docs/OS2_CALL_GATE_ACCESSED_20260929.md`.
Profiles/logs: `D:/GitHub/86box_dev/build/spk286/os2-callgate-20260929-before/`
and `os2-callgate-20260929-after/`. Both used disposable copies of the VHD;
the original was unchanged.
