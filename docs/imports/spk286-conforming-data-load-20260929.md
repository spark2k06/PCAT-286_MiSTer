# SPK286 H06: readable conforming code in DS/ES

Date: 2026-09-29. Imported from SPK286 commit `52c45fc` on
`codex/protected-mode-windows31`.

## Change

Readable conforming code can be loaded into DS or ES at any CPL, DPL or RPL.
The prior predicates incorrectly applied the conforming CS execution rule
`DPL<=CPL` to data-register reads. Both the ordinary segment reload path and
the task-switch ES/DS cache builder are corrected. CS and SS rules are
unchanged. This follows Intel 80286 sections 7.4.1, 11.2.1 and task-switch
page 8-13, and agrees with native 86Box's `loadseg_2386` path.

Imported RTL and directed units are byte-identical to the upstream files:

- `vendor/spk286/rtl/spk286_micro_executor.sv`.
- `vendor/spk286/rtl/spk286_task_segment_service.sv`.
- `vendor/spk286/sim/unit/spk286_conforming_data_load_tb.sv`.
- `vendor/spk286/sim/unit/spk286_task_segment_service_tb.sv`.

The two units are registered in the vendor test script. RTL SHA-256 values:
`acd121e2d67c6b331c997535887d225267f4d0b412c3ffb4941eafba250af5df`
and `924de921f1a9fcc1b05d9d0b70c0f758405583fe9ff9f1d94cbd8582e86d3ef5`.

## Validation

- Before the fix, a CPL0→DPL2 LDS case generated #GP and the task-segment
  matrix rejected CPL0/DPL1/RPL0.
- After the fix, the core bank passed 100 checks / 77 cases in Icarus and
  Verilator. The task-segment bank passed 180 checks in each, including all
  64 CPL/DPL/RPL combinations for incoming conforming ES/DS.
- Both banks passed against the vendored RTL in Icarus. The upstream
  protected-system and POP-segment restart banks, lint and targeted Yosys
  checks also passed. No full regression or Quartus/RBF build was run for
  this individual fix.

86Box was rebuilt with this vendor tree. The normal launcher still invokes
`D:/GitHub/86box_dev/build/spk286/86Box-linux`, SHA-256
`68954ca890b25af10ae8706382df365e8c4edf4177aa28e84d721bb8303ed4a2`.

The isolated OS/2 trial passed the former #GP(`006C`) at `0228:7A57`, loaded
HPFS and other device drivers, and executed code in later modules. During the
13-minute observation it did not show a desktop; the screen became black while
the CPU continued to advance. The trial was then stopped. The original VHD
retained its initial hash; testing used a disposable copy.

Detailed evidence: `D:/GitHub/SPK286/docs/OS2_CONFORMING_DATA_LOAD_20260929.md`.
Profile and log: `D:/GitHub/86box_dev/build/spk286/os2-h06-20260929/`.
