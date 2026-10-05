# LAR/LSL inspection of absent descriptors — 2026-09-29

## Captured Windows 3.1 progress and failure

The next integration run gets past the protected-return restart issue:
`043F:9F31` now saves the original SP=0FEC, and execution proceeds into
additional Windows modules. It eventually exits to DOS rather than remaining
in the previous error-reporting loop.

The next relevant sequence in the saved log is:

```text
0B07:09EF  CALL FAR 0B2F:0387 -> #NP(0B2C)
LDT[0B2F] @115778 = 0ADF 0000 7B00 0010
043F:58C1  0F 03 CB             LSL CX,BX       ; BX=0B2F
043F:58C4  8E C1                MOV ES,CX
043F:58C6  FE CB                DEC BL
043F:58C8  26 81 3E 00 00 4E 45 CMP ES:[0000],454E -> #GP(0)
Captured at #GP: CX=0000, ES=0000, BX=0B2E, CPL=3
```

The loader uses the absent segment's limit field as a module selector.
The descriptor is visible DPL3 code, so LSL must return 0ADF and set ZF
despite P=0. SPK286 incorrectly required presence and left CX at its previous
value of zero. MOV ES accepted this null selector; the following NE-header
read then faulted. The later exception-return traps at `043F:582B` are part
of DOSX's existing exception service, not new proof of a RETF defect.

Evidence retained outside Git in the 86Box build directory:

- `profile-ibmat-mrbios-ega/spk286.after-return-restart-20260929-134308.log`
- `live-guest-ram-after-return-restart-20260929-134308.bin`
- `after-return-kernel-loader.txt`

The RAM was captured after the return to DOS; discarded module memory can
already be reused. The fault log preserves descriptor and CPU state at the
actual exceptions, and the resident loader bytes identify the sequence above.

## Architectural and reference evidence

Intel 80286/80287 Programmer's Reference Manual 210498-005, Appendix B,
LAR (B-60) and LSL (B-71), defines success through descriptor visibility,
table bounds and applicable type checks. Presence is not a success condition.
Only ZF changes; a rejected inspection preserves its destination and does
not fault on the selector's value. The local reference PDF/text are retained
under `build/references/intel-286-programmer.*`.

86Box's `src/cpu/x86_ops_pmode.h` macros `opLAR` and `opLSL`, used by its
286 opcode table, likewise do not test the descriptor's P bit. Their 16-bit
forms return the access byte or limit field after their visibility checks.

## Change and bounded validation

Remove the presence prerequisite only from the shared LAR/LSL inspection
result. Segment loads and transfers retain their presence checks. Update
the old protected-system matrix's LAR/LSL absent-descriptor expectations
according to the Intel contract. VERR/VERW behavior is outside this change.

The new synthetic CPU bank covers both queries, present and absent code,
data and TSS descriptors, rejected privilege/null/table-bound cases, all
three timing policies and READY stalls. It checks the result, ZF, preserved
flags, unchanged descriptor bytes and the successful subsequent NE-header
read. The baseline failed 27 checks. Final results:

- New bank: 162 checks / 72 cases pass in Icarus and Verilator, both in
  SPK286 and in the actual PCAT vendor source consumed by 86Box.
- Upstream protected-system bank: 538 checks pass in both simulators,
  including the corrected absent-descriptor query matrix.
- Verilator lint and microcode consistency pass in both source trees.
- The 86Box WSL Release build completes with the imported change.

Logs are retained under each source tree's `build/descriptor-inspection-*.log`
and `86box_dev/build/spk286/descriptor-inspection-build.log`.

The user requested bounded validation, so no full regression or synthesis
is claimed. Windows desktop startup still requires the next integration run.
