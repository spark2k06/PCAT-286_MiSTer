# OS/2 1.3: restoring an empty outer stack with RETF

## Captured failure

After the SGDT correction, OS/2 proceeds further and reports TRAP 000C.
The pre-delivery log identifies `0270:0985`, opcode CB (`RETF`), with
SS=0038, SP=F8F2, SS base 1D0800, limit F4DF and access 97.
The saved return frame is intact in the two-megabyte RAM capture:

| Old SS offset | Value | Meaning |
| --- | --- | --- |
| F8F2 | 32D0 | Return IP |
| F8F4 | 13A3 | Return CS, CPL3 |
| F8F6 | 0800 | Return SP |
| F8F8 | 0067 | Return SS, LDT, RPL3 |

The return CS descriptor is present DPL3 code (access FB), base 1E7960,
limit 819E. LDT base is 1DE420. Its SS descriptor at 1DE480 is:

```text
FF 07 E0 75 1D F3 00 00
base = 1D75E0, limit = 07FF, access = F3
```

SP=0800 represents an empty ordinary 0800-byte stack. RETF does not
dereference that pointer. A later PUSH decrements it before accessing
the valid word at 07FE..07FF.

## Root cause and correction

`iret_outer_restored_range_fault` applied an extra late check to RETF's
restored SP plus immediate adjustment. That check incorrectly requested
#SS(0067) for the valid OS/2 frame. It did not gate the separate IRET commit
path, despite its name.

Remove this extra check and its fault/commit wiring. The current-stack
return frame, target CS and target SS descriptors remain validated. The
16-bit SP assignment still applies RETF's immediate adjustment modulo
65536. Any later actual stack access checks its own address range.

This follows Intel's *80286 and 80287 Programmer's Reference Manual*
(1987), RET, pp. 8-94..8-95, and the interlevel-return checks in chapter 7:
the current frame must fit; the restored SS descriptor and return IP are
validated; the new SP is loaded without a memory access or range test.
The same sequence is visible in local 86Box `src/cpu/x86seg.c`,
`pmoderetf[_2386]`: validate new SS, assign SP, then add the immediate using
16-bit arithmetic. No new hardware measurement is claimed.

Reference: <https://bitsavers.org/components/intel/80286/210498-005_80286_and_80287_Programmers_Reference_Manual_1987.pdf>

## Regression contract

The new `spk286_outer_return_sp_tb` covers RETF, RETF 4 and IRET across
three timing policies, normal and expand-down stacks, empty/out-of-range/
odd/wrapping SP values, plus null, absent, wrong-privilege and code-as-stack
SS descriptors. It checks continuation after return, no writes to the new
stack before PUSH, and either a successful PUSH/POP pair or #SS(0) at that
later PUSH. Invalid SS descriptors must still fault before context commit.

The pre-fix RTL fails 51 assertions in its 162-case matrix. IRET cases are
included as an unchanged-behavior control. The older PM4b.7 test claimed
that restoring SP above the outer limit must fault; that expectation is
contradicted by Intel's return algorithm and the captured OS/2 use. Its
replacement tests a valid RETF 4 frame restoring FF04 with limit FF03.
The previous RETF 8 setup also skipped beyond the fixture's two-parameter
frame, so its failure was not sufficient evidence for the claimed rule.

The corrected RTL passes all 450 checks / 162 cases in both Verilator and
Icarus. The existing protected-RETF bank passes 62 checks in both; the
Windows exception-return restart reproducer passes 81 checks / 27 cases
in both. Verilator lint and generated microcode consistency also pass.
The actual PCAT vendor copy passes the same 450-check matrix in both
simulators, plus lint and microcode consistency.
The existing expand-down bank also passes all 2183 checks in Icarus
(`build/os2-return-expand-down.log`).

## Evidence and scope

- `86box_dev/build/spk286/os2-trap-20260929-172143/`: preserved log,
  full guest RAM, samples, configuration, frame/descriptor decoding.
- `SPK286/build/os2-outer-return-before.log`
- `SPK286/build/os2-outer-return-after.log`
- `SPK286/build/os2-outer-return-lint.log`
- `SPK286/build/os2-retf-regression.log`
- `SPK286/build/os2-return-restart-regression.log`

Successful full OS/2 startup remains pending a new integration run.

The rebuilt launcher binary is installed with SHA-256
`3e1a2aca871abceccd5c390e24f0ac8bc537a287c3966746169ae494ad12358e`.
Its predecessor is preserved as
`86Box-linux.pre-os2-outer-return-20260929-173119` beside the executable.
The MR BIOS / 6 MHz / 2 MB / EGA OS/2 profile is unchanged. This bounded
validation does not repeat the entire regression suite. The user requested
committing the verified fixes before the next manual OS/2 startup run.
