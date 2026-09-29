# SPK286 absent-descriptor inspection import — 2026-09-29

Upstream: `9e4348a300ba5523710014ecbd5c77746522f056` on SPK286 branch
`codex/protected-mode-windows31`.

Windows progresses beyond the previous RETF trap but exits to DOS. The
captured loader uses `LSL CX,BX` at `043F:58C1` with BX=0B2F to recover
the module selector from an absent code descriptor's limit field, 0ADF.
The incorrect presence prerequisite left CX zero, and the following
`MOV ES,CX` / NE-header read raised #GP at `043F:58C8`.

The imported change permits LAR/LSL inspection of absent but visible
descriptors. It preserves segment-load and transfer presence checks and
the downstream fetch-wrap correction. Intel's 286 LAR/LSL definitions and
86Box's original implementations support this behavior.

Validation:

- Synthetic inspection and loader-continuation bank: 162 checks / 72 cases
  pass in both simulators, upstream and in this vendor tree.
- Upstream protected-system bank: 538 checks pass in both simulators.
  This older vendor suite does not contain that bank; its corrected
  LAR/LSL absent-descriptor expectations are documented upstream.
- Both trees pass Verilator lint and microcode consistency.
- The 86Box WSL Release build completes using this source.

Logs: `vendor/spk286/build/descriptor-inspection-*.log`, corresponding
upstream logs and `86box_dev/build/spk286/descriptor-inspection-build.log`.
Full regression and synthesis were not run, following the user's bounded
validation request. The next Windows integration run remains pending.
