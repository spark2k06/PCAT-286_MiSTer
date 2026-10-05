# H22: call-gate target Accessed-bit completion

Date: 2026-09-29.

## Scope and diagnosis

Baseline: SPK286 `7c333cd`, PCAT-286_MiSTer `8340da8`, native/adapter
86Box `f46f62eaf`. H07 had removed the conforming-return #GP. The next OS/2
stall was at `0257:214C`, bytes `9A 00 00 F8 04`, micro-PC `01DE`
(`VALIDATE_CALL_CS`).

A temporary read-only probe in the Verilator adapter sampled the call target
at completion of descriptor phase 3:

```text
gate=04F8 target=007E offset=0151 descriptor@1DE4B8
before #NP: 0326 006F 5A00 0000
after retry: 0326 1620 DA1C 0000 (repeated)
```

The present target is readable non-conforming code, DPL2, base `1C1620`, limit
`0326`, Accessed=0. OS/2 repaired the absent descriptor, but SPK286 kept reading
it and never reached the target. The previous `#NP(007C)` was a legitimate
demand-load event, not the cause of the infinite loop.

In `rtl/spk286_micro_executor.sv`, `descriptor_operation_done` already waits
for the Accessed write for a valid call-gate target with A=0. `descriptor_write`
also already supports it. However, the phase-3 state transition did not include
`call_gate_cs_validation_operation`, so it cleared `descriptor_active_q` instead
of advancing to phase 4. The unfinished microinstruction started another read.

The two-line correction enters phase 4 when call-gate target validation succeeds,
the target offset is valid and A=0. Existing bus completion, cache publication
and call-frame logic then complete the operation.

## Architectural/reference basis

- Intel 80286 and 80287 Programmer's Reference Manual, 210498-005 (1987),
  section 7.4, printed page 7-11: loading a segment descriptor sets its table
  Accessed bit. The pinned PDF and local OCR cache are identified in the
  [global review](PROTECTED_MODE_GLOBAL_REVIEW_20260929.md).
- Native 86Box `src/cpu/x86seg.c::loadcscall`, the 286 call-gate paths, updates
  the target descriptor using `segdat[2] | 0x100`. Same-level/conforming and
  inner-privilege paths both contain the update.

No reference emulator code was copied into the RTL. Exact cycle counts and
physical 286 bus ordering are not established by these functional checks.

## Classification

This is **H22**, an additional confirmed implementation defect. The earlier
H19 association was provisional: the stall followed #NP, suggesting restart
handling. A minimal valid call with no previous fault reproduces the same
micro-PC loop, proving that restart is not required. H19 remains pending;
H09's JMP-through-gate and H21's POP-segment restart are separate cases.

The pre-existing call-gate success tests used targets with A already set. Their
coverage did not force the missing write phase. The new bank explicitly crosses
target type, privilege and table selection with A=0/1.

## Directed validation

New bank: `sim/unit/spk286_call_gate_accessed_tb.sv`, registered in
`scripts/test_units.sh`.

- Immediate `9A` and indirect `FF /3` CALL; gate/target in GDT or LDT.
- A=0 and A=1; same-level, inner CPL0, inner CPL2 and conforming DPL2 targets.
- READY stalls and all three timing policies.
- Exactly one Accessed write for A=0, none for A=1; memory and CS cache updated.
- Correct return frame, parameter copy and RETF back to the caller.
- Absent target: an executed #NP handler sets P, removes the error code and
  IRETs to retry the same CALL; includes inner CPL2 as in the OS/2 case.
- Wrong target type and out-of-limit offset: correct fault, unchanged caller,
  no target Accessed write or CALL frame publication.

Before the RTL correction the first valid A=0 same-level case timed out at
micro-PC `01DE`, CS:IP=`001B:0105`, SS:SP=`0043:1000`, with no exception.
Local log: `build/callgate-accessed-before.log`.

Results:

| Check | Result |
|---|---|
| New call-gate bank, Icarus | PASS, 420 checks / 144 cases |
| New call-gate bank, Verilator | PASS, 420 checks / 144 cases |
| `scripts/lint.sh` | PASS, including microcode consistency |
| `spk286_protected_system`, Icarus | PASS, 538 checks |
| `spk286_protected_direct_call`, Icarus | PASS, 300 checks / 144 cases |
| `spk286_protected_retf`, Icarus | PASS, 62 checks |
| Vendored call-gate bank in PCAT, Icarus | PASS, 420 checks / 144 cases |
| Yosys micro-executor `hierarchy; proc; opt; check -assert` | PASS, 0 problems; not a mapped FPGA build |

Local logs: `build/callgate-accessed-final.log`, `build/callgate-lint.log`,
`build/callgate-system.log`, `build/callgate-direct.log`, `build/callgate-retf.log`,
`build/callgate-yosys.log`; vendor log in the 86Box build directory,
`callgate-vendor-unit.log`.

The user requested bounded checks for individual fixes and reserves the long
full regression for batches of commits. No full regression is run for H22.
The real-mode SingleStep corpus cannot exercise this protected call-gate path.

## Integration reproduction

Disposable profiles under `D:/GitHub/86box_dev/build/spk286/`:

- `os2-callgate-20260929-before/`: H07 plus temporary descriptor probe;
  `callgate-target.txt` records the four observations above.
- `os2-callgate-20260929-after/`: corrected RTL with the normal adapter.

Both begin from a copy of `D:/ISOs/MiSTer/IBM_OS2.vhd`, SHA-256
`cd4dfe0440df06d85410c931114e49d1e88a63318762ed10e99bf5882a260901`.
Configuration: MR BIOS 286, 6 MHz, 2 MB, EGA, IDE 0:0, geometry 1020/15/17.
Each has its own NVR and global configuration; emulator fast-forward is enabled.

Corrected executable `build/spk286/86Box-linux` SHA-256:
`dfe0726661e92cd39083c34048a4c8723031c1666f7144492ab7e5e507005eac`.
The temporary probe source was restored before the final build; no permanent
86Box source change is required by this fix.

The corrected run passes the former stall. Snapshot 35 observes the subsequent
demand-load fault for inner stack `0086` at micro-PC `01E1`; snapshot 36 executes
inside the target at `007E:0183`. Its descriptor is now `0326 1620 DB1C 0000`
(A=1), cached CS access is `DB`, and SS:SP is `0086:01E4` with access `D3`.
Later snapshots record further segment loads and calls. These observations
establish progress past H22, independently of the final boot outcome.

### Next observed discrepancy: H06 remains pending

Snapshot 47 reports #GP(`006C`) at `0228:7A57`, bytes `36 C5 37`
(`LDS SI, SS:[BX]`), micro-PC `01D7` (`LOAD_SEG`). Target descriptor
`1DE4A8 = 12AA 0B80 DF1A 0000` describes present readable conforming code,
DPL2, base `1A0B80`, limit `12AA`. The caller has CPL0. The data-register
validation predicate incorrectly requires DPL<=CPL for conforming code,
matching the already documented **H06**. This is a later issue, separate from
the corrected call-gate completion loop. H06 was not changed by the H22 commit;
its later correction is recorded in
[H06 diagnosis and validation](OS2_CONFORMING_DATA_LOAD_20260929.md).

The run did not reach a desktop during observation (about nine wall-clock
minutes, including boot). The last screenshot still shows the OS/2 startup
banner: `screenshots/Monitor_1_1260829-203828-565.png`. No final TRAP banner
was captured, so this report does not claim that H06 alone explains all
remaining boot behavior.

After requesting pause, live port values were saved in `final-live-ports.json`
using a read-only process-memory helper (`build/spk286/read-live-ports.py`;
field offsets derived from the generated model header by the compiler).
The snapshot shows instruction `01F8:2CF1`, opcode `C3`, micro-PC `0059`,
event requests/completions both `04DA`, and no shutdown/control/microcode error.
These paused samples are not evidence of a CPU loop. Monitor exit did not
complete promptly, so the disposable test process was terminated with SIGTERM.
The original and test-copy VHD hashes both still match the initial value.
