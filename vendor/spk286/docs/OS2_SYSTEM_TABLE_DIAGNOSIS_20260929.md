# OS/2 1.3: descriptor-table operand on an expand-down stack

## Captured failure

The downstream 86Box/SPK286 machine uses MR BIOS, a 6 MHz 286, 2 MB RAM,
EGA and the user's IBM_OS2.vhd. OS/2 reports TRAP 000D during startup.
The pre-delivery exception log identifies:

```text
CS:IP = 0380:2136, bytes 0F 01 46 FA   SGDT [BP-6]
BP = F89C, SP = F896, FLAGS = 0086, MSW = FFF1
SS = 0038, base = 08B120, limit = F4DF, access = 97
GDTR = 110020:1AFF, IDTR = 113336:03FF
```

The operand occupies SS:F896..F89B. Every byte is above the expand-down
limit F4DF and below 10000. The executor's table-specific six-byte precheck
instead treated F4DF as an upper limit and incorrectly requested #GP(0).
Ordinary operand checks already understood expand-down segments.

The RAM snapshot also contains the next instructions:

```text
2136  SGDT [BP-6]
213A  MOV AX,2157
213D  MOV BX,217B
2140  CMP BYTE [BP-1],FF
2144  JZ 214C
2146  MOV AX,21AF
2149  MOV BX,21D9
```

SGDT/SIDT previously wrote only five bytes, leaving the tested sixth byte
unchanged. This is a separate compatibility defect in the same operation.

## Implementation and reference

- Pass the selected operand segment's expand-down classification to the
  micro-executor. Validate the whole six-byte range before any transfer,
  honoring both the lower bound and non-wrapping FFFF upper bound.
- Classify an invalid protected SS table operand as #SS(0); other segment
  range violations remain #GP(0).
- Store all six bytes for SGDT/SIDT, using FF for byte six. Loads still
  consume the 24-bit base and ignore the sixth byte.

Intel's *80286 and 80287 Programmer's Reference Manual* (1987), SGDT/SIDT,
section 8, page 8-101, specifies six stored bytes and the #SS/#GP distinction.
It leaves byte six **undefined**. FF is a compatibility choice supported by
the local native 86Box implementation (`src/cpu/x86_ops_pmode.h`,
`op0F01_common`, `base |= 0xff000000` for a 286) and explicitly inspected by
the captured OS/2 code. No new physical CPU measurement is claimed.

Reference: <https://bitsavers.org/components/intel/80286/210498-005_80286_and_80287_Programmers_Reference_Manual_1987.pdf>

## Reproducer and validation

`spk286_system_table_range_tb` exercises SGDT, SIDT, LGDT and LIDT through
SS and a DS override, ordinary and expand-down data segments, six boundary
cases including odd offsets, and all three timing policies. It checks
continuation, table data including byte six, guard bytes, unchanged FLAGS
and SP, exception classification, and rejection before partial writes or
table-register commits.

The unchanged RTL failed 288 assertions across the 288-case matrix in
Icarus. With the fix, both Verilator and Icarus pass all 1056 checks across
288 cases. The existing protected-system bank passes all 538 checks in
both simulators. Verilator lint and microcode consistency pass.
The existing expand-down bank also passes 2183 checks in Icarus. In the
actual PCAT vendor tree, the new matrix passes the same 1056 checks in
both simulators, with lint and microcode consistency passing.

The existing real-mode SGDT/SIDT expectations now assert the intentional
FF compatibility value instead of an untouched zero-filled byte. This
does not turn Intel's undefined-byte specification into a guaranteed value.
The pinned SingleStep 80286 corpus has no 0F instruction forms, so no
hardware-derived SGDT/SIDT test coverage is claimed.

The source changes are also applied to the PCAT vendor copy used by the
86Box build. Complete OS/2 startup and MiSTer hardware confirmation remain
pending the user's next run. This bounded fix does not repeat the complete
regression suite. The fixes are committed at the user's request with the
validation scope recorded here and full OS/2 startup still pending.

## Local evidence

- `86box_dev/build/spk286/os2-trap-20260929-170550/`: original log,
  two-megabyte RAM snapshot, live register samples, configuration and
  disassembly. The captured CPU was looping at 01F8:11A0 after OS/2's trap.
- `SPK286/build/os2-system-table-before.log`
- `SPK286/build/os2-system-table-after.log`
- `SPK286/build/os2-system-table-lint.log`
- `SPK286/build/os2-protected-system.log`
- `SPK286/build/os2-expand-down.log`
- `PCAT-286_MiSTer/vendor/spk286/build/os2-system-table-after.log`

The rebuilt 86Box launcher binary was installed with SHA-256
`90fd90a8d746522acceb44311d0771eb051d00cce3d03dedd36f821a751d787a`.
The previous executable is retained as
`86Box-linux.pre-os2-system-table-20260929-171627` beside it.
