# Phase 9E P3 resolution — Verilator adapter initialization

Date: 2026-09-15  
Branch: `codex/phase9-timing-tstates`  
Snapshot: `a3c493a` (`test: initialize timing policy in Verilator adapters`)

## Finding and scope

The independent boundary review identified that the new
`timing_policy_request` input was initialized by the HDL testbench include but
was not driven by the C++ adapters before reset. With Verilator randomized
initialization, the integrated model could therefore sample an unsupported
request such as `3` and report `debug_timing_policy_error=1`, even though the
baseline policy remained active.

This correction is limited to the Verilator adapter initialization and its
focused test. It does not change RTL, microcode, instruction behavior or the
timing-policy selector contract.

## Correction

`sim/verilator/state_inputs.h` now assigns
`dut.timing_policy_request = 0` in `clear_execution_inputs()` before the
adapter performs the reset edge. The reset-smoke, state-vector and SingleStep
adapters all use this helper, so the baseline selection is established at one
shared initialization boundary.

`sim/verilator/timing_policy_init.cpp` and
`scripts/test_timing_policy_init.sh` add a focused integrated check. The test
uses `Verilated::randReset(1)`, deliberately starts the request and other
inputs non-zero, calls the real shared adapter initializer, and checks:

- request `0` before the reset-boundary sample;
- active policy `0` during and after reset;
- no selector error during or after reset;
- selection locked after reset release.

The original omission was reproduced before the correction. The focused test
then failed with:

```text
TIMING_POLICY_INIT FAIL: adapter did not select baseline request
TIMING_POLICY_INIT FAIL: selector reported an initialization error
TIMING_POLICY_INIT FAIL: selector error appeared after reset
```

After the correction it reports:

```text
TIMING_POLICY_INIT PASS request=0 active=0 error=0 locked=1
```

## Verification performed

All commands were run from the repository root at snapshot `a3c493a` unless
otherwise stated. The full regression remains intentionally deferred.

| Check | Result | Evidence |
| --- | --- | --- |
| Focused C++ initialization test | PASS; detects the pre-fix omission and then passes after the helper assignment | `build/verilator/timing-policy-init/` |
| Microcode consistency and Verilator lint | PASS; 120 entries, 717 words, 10-bit addresses, 8-bit control | `scripts/lint.sh` output; `build/verilator/timing-policy-init/build.log` |
| Reset smoke, Verilator | PASS; CS `F000`, base `FF0000`, IP `FFF0`, fetch `FFFFF0` | `build/p3-verilator/verilator/obj_dir/spk286_smoke` |
| Reset smoke, Icarus | PASS; same architectural reset/fetch checks | `build/p3-iverilog/iverilog/spk286_reset_tb.vvp` |
| State vectors | PASS; 1 sample and 3 fixture cases, no instructions executed | `build/p3-verilator/state-vectors/` |
| SingleStep focal case | PASS; opcode `B8`, one selected/executed/passed case, 10 cycles | `build/p3-verilator/singlestep/` |
| Timing-policy selector | PASS in Verilator and Icarus; 6 checks each | `build/verilator/spk286_timing_policy_tb/`, `build/iverilog/spk286_timing_policy_tb/` |
| Timing-policy integrated contract | PASS in Verilator and Icarus; 63 checks each | `build/verilator/spk286_timing_policy_contract_tb/`, `build/iverilog/spk286_timing_policy_contract_tb/` |

The Icarus run emits its existing `sorry: constant selects in always_*`
diagnostics; the smoke test still exits successfully. No RTL or generated
microcode files changed in this increment, so no synthesis run was required.

The relevant toolchain was the repository-configured Verilator/Icarus pair;
the source and generated-input identity is the Git snapshot `a3c493a`, and
`scripts/rtl_sources.sh` reran the microcode consistency check for each RTL
build. The observed versions were Verilator `5.020 2024-01-01 rev`
(`Debian 5.020-1`) and Icarus Verilog `12.0` (runtime `12.0`).

## Status and remaining work

P3 is closed. The selector contract remains unchanged and policy `0` is still
the only active baseline. H4, B1, B2 and B3 remain closed. V1, historical
timing validation, the complete Phase 9 regression and later Phase 9 work
remain pending under the existing policy.
