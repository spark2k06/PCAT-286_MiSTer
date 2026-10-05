# SPK286 portable protected-mode diagnostic v0.1

CPU-only experiments packaged as DOS COM applications and optional boot floppies.
This initial release targets the **late protected-mode/table/task block** of the
Supersoft/Landmark AT diagnostic, especially the failing CALL/JMP/IRET sequence.
It is not the whole ROM test and is not exhaustive PM1-PM5 certification.

## Run on 86Box or a core containing SPK286

Use a **286 machine with clean real-mode DOS**, without EMM386, Windows, DPMI,
or other protected-mode software. Copy both COM files to a DOS disk. Start with:

```text
PM286 /S
PM286
```

`/S` tests loading and DOS text output only, then returns to DOS. The normal
invocation takes over the CPU, enters protected mode, displays results, and
**halts permanently; reset the emulated/physical machine afterwards**. No DOS
return or result-file writing is attempted from protected mode. All test storage
is inside the program's allocation; no CMOS/A20/8042 reset trick is needed.
Use the default 80x25 text screen (color or monochrome).

After recording the control's results, reset and execute `PMROM`.
Alternatively boot `PM286.IMG` or `PMROM.IMG` as a 1.44 MB floppy. These are raw
standalone diagnostic images, **not FAT/DOS data disks**. They need no DOS files.

- **PM286** explicitly sets NT before the final IRET after the JMP task chain.
  This makes the intended nested return well-defined. It should report
  `COMPLETE failures=0000` on a correct implementation of the covered operations.
- **PMROM** retains the original dependency on NT surviving the JMP chain.
  The SPK286 compatibility policy preserves the incoming TSS NT image for this
  transfer, so the original SuperSoft sequence can complete as well. The
  Intel-table discrepancy remains documented in
  `docs/PROTECTED_MODE_NT_JMP_RESEARCH_20260913.md`.

Tests show hexadecimal IDs, `PASS`/`FAIL`, and `actual/expected` words. The last
printed ID is also the progress marker if execution hangs. An unexpected
exception prints vector, error code, saved CS:IP, FLAGS, TR, LDTR and MSW.
The final lines capture FLAGS at first CALL, after JMP, before final IRET, and
immediately after the control's POPF (`FFFF` means not executed), plus both task
counters (25 decimal = 0019 hexadecimal).

Record: application + manifest hash, emulator/core build, CPU model, BIOS,
PASS/FAIL IDs, last ID on a hang, exception fields, and the final FLAGS/counters.
Photographs of the terminal screen are sufficient for the first hardware runs.
The optional port E9 text output lets headless emulators collect the full log.
Use `RESULT_TEMPLATE.md` for a consistent record. Do not run with unsaved work;
hardware reset after the test is intentional. Maskable interrupts are disabled,
but this CPU test does not configure motherboard NMI/parity logic.

Current validation: Bochs and SPK286 pass all 17 checks; DOSBox-X passes the
DOS-only smoke. There is also a load-address-sensitive SPK286 entry failure: if
a COM stops at T0002, record it and try the standalone image as a separate run.
The actual 86Box 80286 and FPGA results are still pending. See `VALIDATION.md`
for details.

## Coverage and relationship to Superdiag

The private input ROM has SHA-256
`a8310f83de0f3e6b71e4a3ff82a01ffe3c3b5a957677aed2fad17b96bce2e577`.
No ROM binary is included in this package. The assembly is a source-level,
relocatable functional translation, with additional observations and controls.

| ID | Check | ROM correspondence |
|---|---|---|
| 0001 | GDTR/IDTR 0000, FFFF, 5555, AAAA patterns; five bytes | A3D1-A3FD / A53D-A570 |
| 0002 | LGDT/LIDT/LMSW and protected far JMP | A571-A5A7 |
| 0003-0004 | Two LLDT/SLDT selector checks | A41B-A440 |
| 0005-0006 | Two LTR/STR selector checks | A445-A46A |
| 0007 | LMSW cannot clear PE | Added architectural control |
| 0008 | LDT data limit fault #GP(0), correct saved IP and IRET recovery | Added diagnostic control |
| 0009-000C | CALL/IRET, LDT entry-zero CS, NT, backlink, BUSY | Added isolation of A4AC |
| 000D | CALL task gate, alternating JMP task gates, final IRET | A4AC / A4F1-A53C |
| 000E-0010 | Both 25-iteration counters and correct LDT data bases | A4B1-A4D0 |
| 0011 | CLTS clears TS | Added architectural control |

The selector layout is retained (CS=0018 in the caller, CS=0004 in both tasks,
LDTR=0038/0040, TSS=0048/0058/0068, task gates=0078/0080). Task code/data bases
are distinct and relocatable. Incoming task FLAGS have NT=0. The ROM's busy-wait
delays are omitted; the actual 25 task iterations remain. The initial earlier
PM exception/segment-cache sweep, motherboard resets, beeps and POST screen
logic are outside this first application. An emulator pass does not replace
Intel documentation or physical 286 evidence.

## Build

Requires Python 3.10+ and NASM 2.16+; no C runtime, DOS extender or network needed.

```sh
python3 -m research.pm_diag.build --output build/pm-diag
```

Use `--nasm /path/to/nasm` for a portable assembler. The build emits COMs,
bootable images, listings and SHA-256 manifests. All generated files go under
ignored `build/`. `--inject 1` corrupts one task's expected input identity;
`--inject 2` marks the incoming code descriptor not present. Use separate output
folders and never distribute those as the normal programs.

## Evidence sources

- Intel 80286/80287 Programmer's Reference (1987), chapters 7-10, especially
  [table 8-2](https://bitsavers.org/components/intel/80286/210498-005_80286_and_80287_Programmers_Reference_Manual_1987.pdf):
  task linking, NT, BUSY and 286 TSS layout.
- [Supersoft manual](https://retrocmp.de/ibm/5170/SUPERSOFT-LANDMARK-ROM_USERS%20MANUAL_V1-2_OCR.pdf),
  Protected Mode CPU Test description; private ROM disassembly for exact flow.
- [DOSBox-X source](https://raw.githubusercontent.com/joncampbell123/dosbox-x/master/src/cpu/cpu.cpp):
  16-bit task switching stops with `E_Exit("286 task switch")`. `/S` may be
  validated there; it cannot certify the full diagnostic.

See `VALIDATION.md` for measured results and remaining hardware validation.
