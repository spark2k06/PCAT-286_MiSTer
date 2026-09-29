# SPK286 protected-mode entry checkpoint — 2026-09-29

This imports the CPL correction developed in the standalone SPK286 branch
`codex/protected-mode-windows31`. A real-mode CS retains privilege zero after
LMSW until a protected CS load commits; selector bits are not interpreted as
RPL during that transitional state. The executor and LOADALL share this CPL
value. Debug exception outputs and the directed entry test are included.

Upstream commit: `348c57c4b6ccf37df46bef9955267ea73a40af39`.

The existing downstream real-mode IP-wrap correction is preserved.

## Evidence

- The original directed reproducer failed 63 of 81 cases before the fix.
- All 81 cases / 162 checks pass in Verilator and Icarus in both the standalone
  repository and this vendor tree.
- Verilator lint and generated microcode consistency pass in both trees.
- Standalone protected-system, LOADALL privilege, CLTS privilege, outer event,
  task-gate event privilege and reset smoke tests also pass in both simulators.
- The user confirmed that Windows 3.1 no longer restarts at its first protected
  entry; live 86Box samples confirm further protected-mode execution.

Windows still encounters a later MS-DOS Extender fault loop. This checkpoint
does not claim successful desktop startup, physical CPU validation or FPGA
hardware validation of the change.

The user explicitly requested cancelling the extensive regression and
committing with the completed directed checks. Both `make regression` runs
were stopped before completion; no failure was reported before cancellation.
The partial logs are `build/cpl-commit-regression.log` under each CPU tree.
The synthesis stage of those runs was not reached.
