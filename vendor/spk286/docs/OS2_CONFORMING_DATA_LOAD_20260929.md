# H06: readable conforming code loaded into DS/ES

Date: 2026-09-29.

## Observed failure

After H22, OS/2 1.3 reached `0228:7A57`, bytes `36 C5 37`
(`LDS SI, SS:[BX]`), and SPK286 raised #GP(`006C`). The descriptor at
`1DE4A8` was `12AA 0B80 DF1A 0000`: present readable conforming code,
DPL2, base `1A0B80`, limit `12AA`. The caller was CPL0.

The protected segment-reload predicate in `spk286_micro_executor.sv` tested
`DPL <= CPL` for conforming code loaded into a data register. That is the rule
for executing through CS, not for reading the segment via DS or ES.
`spk286_task_segment_service.sv` repeated the check when building incoming
ES/DS caches during task switches.

## Architectural basis

- Intel 80286 and 80287 Programmer's Reference Manual, 210498-005 (1987),
  sections 7.4.1 and 11.2.1: readable conforming code may be read at any
  privilege level. The task-switch pseudocode on printed page 8-13 checks
  DPL against CPL/RPL only for data or nonconforming code. The VERR
  description on printed page 8-111 confirms that a readable conforming
  descriptor can have any DPL and describes its check as equivalent to
  loading DS/ES and reading. The PDF and local OCR cache are identified in
  the [global review](PROTECTED_MODE_GLOBAL_REVIEW_20260929.md).
- Native 86Box `src/cpu/x86seg.c::loadseg_2386`, in its DS/ES arm,
  applies the DPL/RPL comparison to data and readable nonconforming code;
  readable conforming types `0x1e` and `0x1f` pass that comparison.

The correction removes this privilege condition in both SPK286 paths.
Descriptor type/readability, presence, table limits and Accessed-bit updates
remain separately checked. CS transfers retain their conforming DPL<=CPL
rule, and SS still requires writable data with DPL=RPL=CPL.

## Focused executable evidence

The new `spk286_conforming_data_load_tb.sv` executes MOV DS/ES, POP DS/ES,
LDS SI and LES DI from protected code. It checks hidden cache and table
Accessed bits, pointer-offset publication, fault selectors and stack state.
It covers CPL0→DPL2 (the OS/2 case), high/low CPL/DPL/RPL combinations,
READY stalls and all three timing policies. Execute-only, absent and
inaccessible nonconforming targets remain rejected.

The expanded `spk286_task_segment_service_tb.sv` checks all 64 CPL/DPL/RPL
combinations for task-loaded readable conforming ES and DS, including
Accessed updates and cache publication. It also keeps execute-only and
not-present controls.

Before the correction:

- The standalone LDS case failed at micro-PC `01D7`, #GP(`0070`), with a
  present readable conforming DPL2 target at CPL0.
- The task-segment matrix first failed for CPL0/DPL1/RPL0.

After the correction:

| Check | Result |
|---|---|
| Core data-register bank, Icarus and Verilator | PASS, 100 checks / 77 cases each |
| Task-segment bank, Icarus and Verilator | PASS, 180 checks each |
| Same two banks against PCAT vendored core, Icarus | PASS |
| Protected-system bank, Icarus | PASS, 538 checks |
| Protected POP-segment restart bank, Icarus | PASS, 96 checks / 36 cases |
| `scripts/lint.sh`, including microcode consistency | PASS |
| Yosys `hierarchy; proc; opt; check -assert` for both modules | PASS, 0 problems each |

Logs: `build/h06-*.log` in SPK286; vendored logs `h06-vendor-*.log` in
the 86Box build directory. The user requested bounded checks per fix and
reserves a full regression for a batch of commits. No full regression or
Quartus/RBF build was run for H06.

## OS/2 integration

The trial uses a fresh copy of `D:/ISOs/MiSTer/IBM_OS2.vhd`, SHA-256
`cd4dfe0440df06d85410c931114e49d1e88a63318762ed10e99bf5882a260901`.
Profile and log: `D:/GitHub/86box_dev/build/spk286/os2-h06-20260929/`.
Configuration: MR BIOS 286, 6 MHz, 2 MB, EGA, IDE 0:0, 1020/15/17 geometry,
isolated NVR and global configuration. Fast-forward was enabled.

The normal 86Box executable is built against
`D:/GitHub/PCAT-286_MiSTer/vendor/spk286` and is at
`D:/GitHub/86box_dev/build/spk286/86Box-linux`, SHA-256
`68954ca890b25af10ae8706382df365e8c4edf4177aa28e84d721bb8303ed4a2`.

The corrected run passes the former `0228:7A57` #GP(`006C`) site. Snapshot 47
is instead a later demand-load #NP(`0154`) at `0137:001F`; snapshots 48–50
show code in `0137` and `013F`, further segment loads and far calls. Thus H06
no longer blocks this OS/2 path. The remaining boot outcome is recorded below.

The VM subsequently displayed messages that the HPFS, serial mouse, OS/2 mouse
support and DOS Programs Device Driver modules were loaded. Screenshot:
`screenshots/Monitor_1_1260829-205853-269.png` in the trial profile. These
messages are integration progress, not a claim of a completed desktop boot.

The trial ran for about 13 wall-clock minutes. The display then became black
without a captured trap banner or desktop. The log reached exception snapshot
138, a later #NP(`0814`) while loading code at `0837:25D0`; intervening
snapshots show many distinct modules and task contexts. Three live port samples
in `live-ports.json` also showed distinct CS:IP values and rising cycle counts,
with no shutdown or core-control error. They establish that the CPU was
advancing during the black display. The run was stopped after this observation.
No further architectural failure is attributed to H06 from this result.

The original VHD retained its initial hash. The disposable copy changed during
normal OS/2 disk writes; its final SHA-256 was
`712e49eb27f4012a161f14d354f17f868399b37454a5f1cd18237351af0f4a6c`.
