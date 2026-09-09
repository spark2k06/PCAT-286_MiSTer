# Phase 0 Progress Report

## Scope

Completed the repository, environment, dual-simulator, data-loader, waveform,
and lightweight synthesis foundation. No functional CPU block was implemented.

## Verification evidence

- Verilator lint/build/smoke: PASS.
- Icarus reset/fetch smoke: PASS.
- Python JSON/MOO reader tests: 4 PASS.
- Yosys synthesis check: PASS, 0 structural problems.
- Negative-path check: PASS; both simulators return non-zero for a wrong
  expected address.
- Waveform check: PASS; opt-in VCD generated.
- Quartus availability: PASS; local Docker image reports Quartus 17.0.2.

The detailed handoff and final command record are in
`docs/PHASE0_HANDOFF.md`.
