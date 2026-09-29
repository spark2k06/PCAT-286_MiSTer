# SPK286 direct protected far CALL import — 2026-09-29

Upstream: `D:/GitHub/SPK286`, branch `codex/protected-mode-windows31`, commit
`124b4d3a892d4a46f9a7edd2d179096168b0c4d3`.

Windows 3.1's first relevant exception was captured at `0307:B595`:
`CALL FAR [DS:09B0]` resolves to present DPL3 code at `0053:1CCD`, with
CPL=RPL=DPL=3 and an offset inside the segment limit. SPK286 rejected this
ordinary code descriptor in `VALIDATE_CALL_GATE`, producing #GP before
writing the return frame. The extender later entered the observed error loop.

This imports the executor correction and its bounded CPU reproducer. Direct
calls pass the initial descriptor classification and use normal CS validation;
resolved call gates retain gate-target semantics. The existing downstream
fetch-wrap correction is preserved. No machine profile or clock setting changes.

## Validation

- Upstream pre-fix reproducer: 72 failures / 108 cases in Icarus.
- Fixed reproducer: 180 checks / 108 cases pass in both Verilator and Icarus,
  in both upstream and the vendor tree used by 86Box.
- RTL lint and generated microcode consistency pass in both CPU trees.
- Upstream protected-system bank: 538 checks pass in both simulators.
- Upstream far task-gate bank: 14 checks pass in both simulators.
- Upstream real-mode far-instruction bank: 6,760 cases / 650,606 checks pass
  in Icarus.
- The configured 86Box WSL Release build completes against this vendor copy.

Logs: `vendor/spk286/build/direct-call-*.log`, the corresponding upstream
`build/direct-call-*.log`, and `86box_dev/build/spk286/direct-call-build.log`.
Full regression and synthesis were not run, following the user's request
for bounded validation. A fresh Windows run is needed to establish whether
startup progresses beyond this newly corrected fault.
