# Restartable protected returns — 2026-09-29

## Windows 3.1 failure

After the absent-segment fix, the saved 86Box run reaches `043F:9F05`.
Windows has just installed an exception-6 handler with DPMI function 0203,
then deliberately executes `0F FF`. The handler adjusts the interrupted
IP/CS and executes `RETF` at `043F:9F31`.

DOSX deliberately supplied `00E0:140C` as the handler's return address.
Selector 00E0 is nonconforming DPL0 code, so this CPL3 return must raise
`#GP(00E0)`. DOSX's ring-0 handler recognizes this error, loads the saved
client SS:SP, checks `[SP+2]` for 00E0 and changes it to the client alias
0053. It then returns with IRET so the original RETF can be retried.

SPK286 advanced architectural SP from 0FEC to 0FF0 while reading the return
IP and CS, before validation failed. The exception therefore saved 0FF0.
DOSX inspected the wrong words and rejected its own service frame. The
later `0053:1E4D` exception loop belongs to error reporting.

Captured input, retained outside Git in the 86Box build directory:

- `profile-ibmat-mrbios-ega/spk286.after-descriptor-np-20260929-131720.log`
- `live-guest-ram-after-descriptor-np-20260929-131720.bin`

## Evidence and scope

Intel 80286/80287 Programmer's Reference Manual 210498-005, sections 9.6,
9.6.7 and 11.1, describes restartable faults and preservation of the state
needed to retry the failing instruction. The RET/IRET protection checks
must not consume their return frame when they fail. The local reference
text and PDF are retained under `build/references/intel-286-programmer.*`.

Local 86Box `src/cpu/x86seg.c::pmoderetf()` saves old SP and restores it
before reporting a code privilege/presence fault; its protected IRET path
likewise restores old SP on failed validation. This corroborates the Intel
restart contract and the recovered DOSX handler's explicit dependency.

Protected RETF and non-task IRET now read through a tentative stack cursor.
SP is committed together with the validated context. Outer-frame reads and
range checks use the cursor, and RETF's immediate allocation is applied at
commit. Fault cleanup discards the cursor. Real-mode returns and nested-task
IRET keep their existing paths. No microcode image or timing policy changes
are required.

Seven old negative expectations in `spk286_protected_retf_tb` incorrectly
accepted partial SP advances (9FF8 or 9FFC from an initial 9FF4). They now
require the original 9FF4, based on the restart contract above. Successful
returns, outer-frame bus rejection and all descriptor checks remain covered.

## Bounded verification

`spk286_protected_return_restart_tb` reconstructs the client return and
privilege-changing exception path using a small synthetic memory image.
It covers RETF, RETF 4 and IRET, privilege/presence/offset faults, all three
timing policies, READY stalls, saved original SS:SP, a guest handler that
repairs the frame and a successful retry. It contains no guest binaries.

The pre-fix RTL failed all 81 checks in 27 cases. With the fix, the 81
checks pass in Icarus and Verilator, both upstream and in the PCAT vendor
tree used by 86Box. Relevant lint and microcode consistency checks pass.

Affected upstream banks also pass in both simulators:

| Bank | Checks |
| --- | ---: |
| Protected RETF, including outer-stack rejection | 62 |
| Protected outer event and IRET | 6 |
| Direct CALL and absent-segment handler/retry | 300 / 144 cases |
| Nested-task IRET | 10 |

Logs are retained under `build/return-restart-*.log`. The WSL Release build
of 86Box completes against the imported vendor RTL.

The user requested bounded checks instead of the full regression. No full
regression, synthesis or physical 286 qualification is claimed. A new
Windows integration run is still needed to establish subsequent progress.
