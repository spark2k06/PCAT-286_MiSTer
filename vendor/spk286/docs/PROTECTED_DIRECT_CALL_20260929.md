# Protected direct far CALL correction — 2026-09-29

## First Windows 3.1 fault

The bounded exception trace added to the 86Box SPK286 backend captured the
first relevant exception before the MS-DOS Extender's repeated error-handler
faults. A read-only guest RAM snapshot confirms the operand and descriptors:

```text
CS:IP = 0307:B595, CPL=3, bytes FF 1E B0 09 (CALL FAR [DS:09B0])
DS base = 09EA50, pointer at 09F400 = CD 1C 53 00 -> 0053:1CCD
CS cache = 08FC20:FFFF, access FB
GDTR = 110800:011F, LDTR = 0038:114C50:5FFF
GDT[0053] at 110850 = 30 43 20 09 11 FB 00 00
Target = present nonconforming DPL3 code, base 110920, limit 4330
Fault = #GP, latched error 0053, micro-PC 1F7, operation VALIDATE_CALL_GATE
```

The target selector has RPL3, its DPL equals CPL, and the offset is within
the segment limit. This is a valid direct same-level call. The later loop
at `0053:1E4D` occurs while the extender is reporting an earlier error;
it was not the initial failing instruction.

## Cause and correction

Both immediate and indirect far CALL microcode enter `VALIDATE_CALL_GATE`
before validating the code segment. That operation accepted call gates,
task gates and available TSS descriptors, but rejected ordinary code.
Furthermore, `VALIDATE_CALL_CS` unconditionally applied gate-target rules,
which would be too permissive for a direct nonconforming transfer.

The executor now accepts valid direct code at the first validation stage.
When no call gate has been resolved, the next stage uses the ordinary CS
validation path shared with direct JMP. That path checks the target offset,
updates the descriptor's accessed bit, preserves CPL (including conforming
targets), and commits the code cache. Real call gates retain their existing
target validation and stack-switch path. Microcode and timing policy are
unchanged. No guest address, selector, or operating system is special-cased.

Architectural reference: Intel 80286 Programmer's Reference Manual
210498-005, sections 7.4 and 7.5, in the local
`build/references/intel-286-programmer.pdf`. The local 86Box reference
`src/cpu/x86seg.c`, `loadcscall()`, likewise separates direct segments from
system descriptors and enforces nonconforming DPL=CPL and RPL<=CPL.

## Bounded validation

`spk286_protected_direct_call_tb` reconstructs the captured addresses and
descriptors through LOADALL, then executes real CALL and RETF instructions.
Its 108 cases cover immediate/indirect calls, all four privilege levels,
all three timing policies, READY stalls, accessed-bit updates, GDT/LDT,
lower RPL, conforming code, and rejected privilege/type/presence/limit cases.
It checks the code cache, normalized CS, unchanged SS, return frame, and
successful return. Negative cases require rejection before call-frame writes.

- Before the fix: Icarus reports 72 failures / 108 cases, reproducing the
  captured Windows exception exactly. All 72 valid-call cases are rejected.
- After the fix: 180 checks / 108 cases pass in both Verilator and Icarus.
- Verilator RTL lint and generated microcode consistency pass.
- Existing protected-system bank: 538 checks pass in both simulators,
  including same-level and inter-level call gates and fault handling.
- Existing far task-gate bank: 14 checks pass in both simulators.
- Existing real-mode far-instruction bank: 6,760 cases / 650,606 checks
  pass in Icarus.
- The downstream PCAT vendor copy used by 86Box also passes all 108 new
  cases in both simulators, RTL lint and microcode consistency.

Logs are `build/direct-call-*.log`. The user explicitly requested bounded
checks instead of another extensive regression. No full regression,
synthesis, physical CPU or FPGA validation is claimed for this checkpoint.
Windows desktop startup still requires a fresh integration run.
