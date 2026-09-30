# Phar Lap: protected HLT service-stub diagnosis

Date: 2026-09-30. Baseline: `c01e9e9`. Finding: **H02, HLT portion corrected**.
This record does not close the remaining H02 IOPL/CLI/STI/I/O/LOCK matrix.

## Workload and independent comparison

The user supplied `D:/GitHub/PCAT-286_MiSTer/SW/PHAR_LAP`. Disposable copies of
`D:/ISOs/MiSTer/286_win3.1.vhd` were prepared with the programs and an automatic
DOS batch. The source has a raw MBR/FAT16 layout despite its filename suffix.
Its SHA-256 remained
`cc544775154d8f6093bb6075a21a00e3d391b979bd954ad811709d291555145f`.

Both arms used the MR BIOS 286 machine, 6 MHz, 4096 KiB, the native IBM EGA
device, IDE disk geometry 17/15/1020 and the same initial CMOS image. Native
86Box used its original 286 interpreter, rebuilt without `USE_SPK286_BACKEND`;
the SPK286 arm used the copied PCAT RTL, with the established P02/P05 options.

| Executable | SHA-256 |
|---|---|
| Native 286 control | `af294129bd0f01d3a3c90d03d4199e90f5cf602b8608dc60c8c34985555dcc8f` |
| Initial SPK286 | `ac35f28d44a8f405224e861faa846c2e02e9a646fa4f06406b8fb3ee41fe0ac5` |
| HLT-corrected SPK286 | `ad6711d36cc3ca7341fe62b942f0b4384af0310d21060eb8bb0f61739f19c6b5` |

Native HELLO printed `Hello from protected mode!` and returned DOS errorlevel 0.
Initial SPK286 never completed HELLO. The coherent final capture showed:

```text
CS:IP/instruction-IP = 011B:0057
CS base/limit/access = 09E340/010F/FB   (CPL3 code)
opcode = F4; halted = 1; shutdown = 0; control_error = 0
FLAGS = 3202 (IOPL3, IF1); MSW = FFF1 (PE1)
SS:SP = 0037:0766; SS base/limit/access = 09AF90/0885/F3
DS = 0047; DS base/limit/access = 130400/59DF/F3
AX/CX/DX/BX/BP/SI/DI = 0205/0017/C3C8/0031/076E/0000/0000
```

The code bytes from offset 0027 through the captured instruction contained
HLT service stubs. Phar Lap depends on their general-protection handler being
entered. IOPL=3 does not make HLT legal at CPL3.

## Architectural rule and implementation

Intel 210498-005, printed page **B-42**, specifies #GP(0) for protected HLT when
CPL is nonzero; real-mode HLT has no such exception. Native
`86Box/src/cpu/x86_ops_misc.h::opHLT` checks the protected CPL before halting.
The local Intel PDF/text cache used by the global review supplies the primary
reference; no 386 VM86 or SMM behavior was imported.

`spk286_micro_executor.sv` now routes a nonzero-CPL protected `MC_HALT` through
the existing general-protection fault path and suppresses `halt_request`.
Instruction-start restart state, including a segment prefix, is preserved.
Microcode is unchanged. Real mode and protected CPL0 still halt normally.

## Executed checks

The new `spk286_hlt_privilege_tb` uses LOADALL only to create independent
execution contexts, then executes the real instruction and event path with
READY stalls. It covers all CPL/IOPL pairs, prefixed/unprefixed forms and all
three timing policies, plus real-mode controls: **104 cases, 208 checks**, in
Verilator and Icarus. Before the fix, CPL1/IOPL0 entered HALT and failed the
expected #GP(0) assertion; after the fix both simulators pass.

Additional bounded validation:

- Verilator RTL lint and generated microcode consistency: pass.
- `spk286_event_instructions`, both simulators: 1932 cases / 428467 checks.
- `spk286_protected_event_outer`, both simulators: 6 checks.
- `spk286_protected_retf`, both simulators: 62 checks.
- Physical SingleStepTests F4 sample: 100 passed, zero failed, real mode only.
- Existing expand-down bank termination smoke, Icarus: 26 checks.
- Integration: corrected HELLO and MEM1 both return errorlevel 0 with the
  native-control text; MEM1 reports a successful one-megabyte allocation.

The old expand-down bank used HLT as a generic terminator at CPL1/2/3. Those
fixtures now use the unprivileged `JMP $` instruction and assert reaching that
loop without entering HALT. The register/selector/flag/memory expectations
remain intact. `SPK286_EXPAND_DOWN_TERMINATION_SMOKE=1` selects the new bounded
fixture check; the default retains the complete existing matrix.

```sh
SPK286_BUILD_DIR="$PWD/build/pharlap-hlt" bash scripts/test_units.sh both spk286_hlt_privilege
SPK286_BUILD_DIR="$PWD/build/pharlap-hlt" SPK286_EXPAND_DOWN_TERMINATION_SMOKE=1 \
  bash scripts/test_units.sh iverilog spk286_protected_expand_down
```

The user requested a separate commit for verified corrections and deferred
large regressions until several commits accumulate. The complete expand-down
matrix, whole-project regression and a new Quartus synthesis were not run for
this isolated change. No physical MiSTer result is claimed yet.

Local integration evidence is retained under
`D:/GitHub/86Box_dev/build/pharlap/initial-20260930-165628` and
`D:/GitHub/86Box_dev/build/pharlap/hlt-fixed-20260930-171437`. The second run was
stopped after HELLO/MEM1 to continue the other programs in a separate disk copy;
it is not a completed whole-suite result. Native complete control is in
`fixed-batch-control-20260930-170355`, with BIG in the first control and the
actual `XMEMTEST -TEST` sweep in `xmem-control-20260930-172553`.

The control batch uses unique short numeric labels: DOS GOTO treats only the
first eight label characters as significant. An earlier batch accidentally
looped TELLPROT through matching long labels; that harness issue was corrected
before the complete control and is not classified as a CPU failure. XMEMTEST
without arguments only reports available memory and returns nonzero; the
successful `-TEST` sweep, rather than that informational invocation, is the
memory-test acceptance criterion.

## Extended integration acceptance recorded after the HLT fix

Eight supplied programs now return DOS errorlevel 0 with the original 286's
functional results: HELLO, MEM1, MEMTEST, TELLME, TELLPROT, `SWTEST /n1`,
`XMEMTEST -TEST` and BIOSDUMP. BIG's unmodified million-position traversal is
still running; it is not included in acceptance. This is not whole-suite closure.

MEMTEST matches byte for byte. XMEMTEST traverses all 97 reported blocks and
prints `All Extended Memory tested O.K.`; its complete output matches after
removing only the observation time and elapsed-time line. TELLPROT/SWTEST match
apart from timings. TELLME matches apart from time, measured speed, RUN286
timings, the distinct test batches and resulting file-date/free-space fields. These utilities do not
cover the full remaining CLI/STI/I/O/LOCK matrix in H02.

BIOSDUMP returns identical 65536-byte BIOS.OUT contents in the isolated and
matched-sequence comparisons, SHA-256
`6f936ee53ba58663d1ccc7b80b1f5caba841f3f816c4dca15477ca540f9f252f`.
Its IVT/BDA dump has time-dependent differences: the floppy timeout and BIOS
ticks, plus an old POST stack word at physical `03C2`. The surrounding words
are AX=`8C80`, IP=`D170`/`D172`, CS=`F000`, FLAGS=`0246`. MR BIOS sets its POST
stack below `0400` and its captured ROM contains `D170: OUT EB,AX` followed by
`D172: LOOP D164`, with AX=`8C80` loaded before the wait. This is consistent with
retained context sampled at adjacent interrupt boundaries, rather than two
different installed F0 handlers. Other IVT bytes match; no new CPU fault is
established by these differences. H20 event-order cases remain independently open.

The complete result table, local trial locations, binary hashes, interpretation
and host-teardown issue are recorded in the integration repository at
`D:/GitHub/86Box_dev/docs/SPK286_PHAR_LAP_20260930.md`. The control is the original
86Box 286 interpreter, not a new physical protected-mode silicon measurement.
