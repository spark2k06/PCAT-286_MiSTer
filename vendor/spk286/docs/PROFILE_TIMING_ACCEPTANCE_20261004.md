# Portable CPU profile checkpoint, 2026-10-04

The CPU-only package is reproduced from the synchronized functional baseline
`b27fb51`. The original flat CPU RTL and generated microcode remain unchanged.
The accepted overlay manifest SHA-256 is
`a135100ee555b477e1b5fa2e7726bd153e1e0f3bdd48b9840d006e27c85cfb04`.

## Directed standalone checks

| Check | Result |
| --- | --- |
| Generated TOP/events identity to the PCAT candidate | Exact bytes |
| Windows builder versus two independent Linux generations | Exact bytes and generation manifest |
| Strict full profiled CPU Verilator Wall lint | Passed, no warnings |
| Independent interval schedule | 45 checks in each simulator |
| Passive complete-CPU LOCK/REP/override budgets | 8 cases in each simulator |
| Original reset/fetch assertions | Passed in MAX and historical modes, Icarus |
| Independent opcode/form metadata oracle | 43,878 cases in each simulator; identical CSV |
| Metadata negative controls | 7 rejected, including the explicit include-guard compile failure |
| Isolated metadata synthesis | 1,073 generic cells, 0 register bits, 0 memories |

The generic synthesis count is not an FPGA ALM count or a complete CPU fit.
The schedule and metadata have independent caller oracles. No original CPU
fixture assertion was changed. The source pins and artifact hashes were checked
again after the standalone run.

Generated TOP SHA-256:
`f45787c2e5e30ae94370ba164ddbf3f1d8058ef52a023c05355131aea3755501`.
Generated events SHA-256:
`a158e55b5b0a66060784c4901576fb717842cc9a009e3656d5feaaf76b51fbef`.

The small [CPU receipt](evidence/profile-cpu-20261004/receipt.json) and
[metadata receipt](evidence/profile-cpu-20261004/metadata-receipt.json) are saved.
Complete rerunnable build logs and traces are in
`build/profile-cpu-focused-standalone-20261004`; the commands in the
[timing contract](PROFILE_TIMING_CONTRACT.md) reproduce them in a fresh build
directory without a PCAT checkout or private evidence bundle.

This is a provisional CPU instruction-interval checkpoint. It does not close
P06/P12, Phase 9, historical timing calibration, a complete functional regression,
Quartus timing closure, board-bus or OS acceptance. Frequency selection, logical
Ts/Tc publication and external READ waits remain host integration responsibilities.
The original CPU-only variant remains available for the established MAX baseline.
