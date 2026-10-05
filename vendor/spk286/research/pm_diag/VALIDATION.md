# Portable protected-mode diagnostic v0.1 validation

Date: 2026-09-15. CPU baseline: SPK286 post-fix working tree (the commit is
recorded with this evidence). The change is limited to protected FLAGS/task
transfer behavior; it changes no microcode, original diagnostic ROM or
downstream PCAT/PCXT project. It does not close protected-mode architectural
certification or any independent review.

## Measured executable results

| Environment | Program/path | Result |
|---|---|---|
| NASM 2.16.01 (WSL) and 2.16.03 (Windows) | Production builds | Identical COM/image bytes; warning-as-error builds; deterministic rebuild test |
| DOSBox-X 2024.03.01, normal/286, hidden SDL dummy | Both COMs with `/S` | DOS loading/output PASS; returns to DOS; **no PM validation** |
| Bochs 2.7, Pentium model, legacy BIOS, private terminal | PM286.IMG | **17/17 PASS**, `COMPLETE failures=0000` |
| Bochs, same configuration | PMROM.IMG | **17/17 PASS**; this emulator preserves incoming NT across task JMP |
| Bochs | Unmodified PM286.COM, boot adapter at segment 1379 | **17/17 PASS**; independent relocation check |
| Bochs | Development fixture: task B identity changed from 2 to 3 | T000D `FAIL FFFF/0000`, counters `0001/0000`; never claims completion |
| Bochs | Development fixture: incoming task CS not present | T000D `#NP(0004)` captured, counters `0000/0000`; never claims completion |
| QEMU 10.2.0, TCG/486 | Both boot images and relocated COM | 16 PASS, T0008 FAIL: this configuration does **not** raise the expected segment-limit #GP. Not an all-pass result |
| SPK286, Icarus, normal CPU bus, READY waits | PM286 BIN and COM at segment 1000 | **17/17 PASS**, `COMPLETE failures=0000`; stable terminal HLT |
| SPK286, same harness | PMROM BIN and COM at segment 1000 | **17/17 PASS**, `COMPLETE failures=0000`; stable terminal HLT |
| SPK286, same harness | Relocated COM at segment 1379 | T0001 PASS; T0002 raises `#GP(0018)` and shuts down before the protected IDT can handle it |
| User's 86Box 286 and FPGA core | Distribution executables | **Pending user execution** |

Bochs/QEMU use later CPU models. Their execution is useful differential evidence,
not a physical 80286 oracle. A local 86Box 6.0 hidden-launch attempt did not reach
emulation or produce a diagnostic trace; it is **not counted as validation**.
The user-owned 86Box run must still be recorded independently.

The displayed 80x25 screen was inspected from an actual QEMU screenshot. All
test IDs, verdicts and terminal context fit on one screen without truncation.
The CPU harness also dumps the actual 80x25 character memory after terminal HLT.

## Findings and implementation changes

### Final task return: original ROM dependency — resolved

PMROM retains the original CALL -> alternating JMP task gates -> IRET control
flow. SPK286 now preserves the incoming target-TSS NT image for the JMP path,
so the final IRET performs the nested task return and the original sequence
completes. The application's relocated task-A IRET is at `0004:0040`; it is not
the original ROM's absolute instruction address.

SPK286 observations after the fix: CALL FLAGS `4002`, after-JMP FLAGS `4003`,
pre-IRET FLAGS `4046`, control-POPF sentinel `FFFF`. Bochs records the same
sequence. The Intel-table discrepancy is preserved as a documented compatibility
decision rather than hidden.

See the repository's
`docs/PROTECTED_MODE_NT_JMP_RESEARCH_20260913.md` for the Intel-documentation
discrepancy and the explicit compatibility decision.

### Additional POPF/NT finding — resolved

PM286 explicitly requests NT=1 before the same final IRET. The fixed SPK286
records `4046` after the control POPF and the final IRET completes.

The fix in `rtl/spk286_micro_executor.sv` makes the `restore_flags` mask
mode/privilege aware: protected-mode POPF restores NT, and IOPL is writable
only at CPL0; real-mode POPF keeps the prior mask. The register block continues
to filter reserved bits.

### Relocation-sensitive protected-mode entry

The unchanged PM286.COM passes its complete suite in Bochs at load segment
1379. SPK286 shuts down during T0002 at that segment, with `#GP(0018)` during
the first protected far JMP. At segments 1000 **and the adjacent 1378** it
reaches T000D. Both successful entry paragraphs have their low two bits clear.
The real-mode CS low bits feed `.protected_cpl(debug_cs[1:0])` in the current
CPU integration; this is a lead for a separate focused investigation, not a
completed RTL fix. Do not alter the COM to hide this diagnostic observation.

If DOS placement prevents reaching the task test on the FPGA, run the provided
boot image (fixed load segment 1000) as a **separately recorded** run. The COM
result remains a failure to investigate, not a waived test.

## Reproduction and evidence

Build and run the packaging self-test:

```sh
python3 -m research.pm_diag.build
python3 -m unittest research.pm_diag.test_build
python3 -m research.pm_diag.run_dosbox --dosbox /usr/bin/dosbox-x --directory build/pm-diag
bash research/pm_diag/run_rtl.sh
```

`run_rtl.sh` first checks generated microcode, runs Verilator lint, compiles the
CPU-only harness with Icarus, and runs the program. It returns **nonzero** when
the program does not report `COMPLETE failures=0000`, even if the harness itself
reached a stable HLT. This is intentional for a diagnostic failure. The post-fix
PM286 and PMROM runs are both expected to return zero; no large regression or
Quartus run is claimed by this focused validation.

For extra load addresses, reuse the compiled harness:

```sh
vvp build/pm-diag-validation/rtl/pm_diag.vvp \
  +IMAGE=build/pm-diag/PM286.COM +LOAD_SEG=1379 \
  +SCREEN=build/pm-diag-validation/rtl/relocated-screen.txt
```

`run_bochs.py` takes `--prefix` pointing to a user-local extracted Ubuntu Bochs,
bochs-term, bochsbios and vgabios package set (no system installation needed),
plus `--image` and `--output`. `run_qemu.py` takes `--qemu`, `--image`, `--output`.
Each retains the command, exact image hash, result and full transcript. Both
report nonzero for a diagnostic failure. Negative fixtures must be evaluated
against their expected error, never described as all-pass CPU runs.

Logs and screenshots for this run are under `build/pm-diag-validation/` and the
distribution ZIP includes compact transcripts. `manifest.json` identifies the
normal binaries. Input-fault binaries and third-party emulators/BIOSes are not
part of the distribution. The source ROM SHA-256 is recorded in README; no
original-ROM binary or patched ROM is included.

## Remaining scope

- Record actual 86Box **80286** results, then the FPGA core's results.
- Diagnose/fix the separately recorded relocation-sensitive protected-mode entry
  finding in a separately authorized task.
- Extend the application beyond this initial table/task-focused subset:
  descriptor/privilege matrices, segment types/presence/limits, gates,
  privilege-changing events/returns, TSS exception paths and instruction families.
- Preserve the distinction between compatibility observations, emulator evidence,
  Intel requirements and physical 286 evidence. No timing accuracy is claimed.
