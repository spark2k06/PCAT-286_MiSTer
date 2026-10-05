# Phase 9 current status — 2026-09-16

This document is the current status receipt for Phase 9. Earlier audit and
resolution documents remain historical records and are not rewritten here.
The source snapshot for this receipt is `5769bd2b3933f6d773e65c940317eeaeed837906`
on branch `codex/phase9-timing-tstates`.

Phase 9 has passed its current functional validation gate, but it is not
historically timing-certified or fully closed. The remaining work is recorded
explicitly below.

## Final functional gate

The following commands were run from the repository through WSL with a
dedicated build directory:

```text
SPK286_BUILD_DIR=/mnt/d/GitHub/SPK286/build/phase9e-global-policy \
SPK286_BUILD_JOBS=2 bash scripts/test.sh
SPK286_BUILD_DIR=/mnt/d/GitHub/SPK286/build/phase9e-global-policy \
SPK286_BUILD_JOBS=2 bash scripts/synth_check.sh
```

Results:

- `scripts/test.sh`: passed with exit status `0`, including the global unit
  banks, microcode checks, lint-related stages, reset smoke, SingleStep sample
  and the protected-mode and timing banks selected by the repository runner.
- `scripts/synth_check.sh`: passed with exit status `0`.
- Yosys report: `build/phase9e-global-policy/reports/yosys_synth_check.log`;
  SHA-256
  `a85c7e2a406275205463cb4876f0beed314124ba132711ea3698b61e0f10d6bb`.
- The expand-down matrix follows the repository policy established by
  `34be022`: the long matrix is isolated from the Verilator loop and executes
  through Icarus. This is a test-runner policy, not a claim that both
  simulators completed that long matrix.
- Total elapsed time for the combined test and synthesis run was approximately
  `1 h 00 min 17 s`, measured from the build-directory and report timestamps.
- The resulting evidence is retained under
  `build/phase9e-global-policy/`. These build outputs are ignored artifacts;
  the reproducible source identity is the snapshot above.

The focused V1 evidence remains recorded in
[`PHASE9_V1_RESOLUTION_2026-09-15.md`](PHASE9_V1_RESOLUTION_2026-09-15.md).
Its focused mutation audit and original far-instruction bank passed, and the
global run above also passed the original far-instruction coverage. V1 is
therefore functionally closed for the current gate.

## Current Phase 9 matrix

| Increment | Current status | Remaining qualification |
| --- | --- | --- |
| 9A | Verified normalized observation contract | No physical pin trace or historical cycle certification |
| 9B | Verified functional twelve-class calibration | Native T-state calibration and physical/reference comparison |
| 9C | Verified normalized BIU contract for the covered matrix | Native `T1/T2/T3/Tw/T4`, complete native bus matrix and physical evidence |
| 9D | Verified normalized prefetch/instruction-unit behavior, including HLT resumption | Historical prefetch refill timing and cycle-level reference evidence |
| 9E policy 0 | Verified baseline policy | No historical claim |
| 9E policy 2 / Max | Verified functional equivalence with policy 0 | No historical claim; no removable delay has been validated |
| 9E Fast | Pending | Requires its own explicit contract and evidence |
| 9E Accurate | Pending | Requires a selected historical profile and reproducible reference evidence |
| 9F | Pending | Downstream PCAT-286 integration, RBF validation and consumer tests |

The closed items above preserve the existing separation between architectural
behavior, functional dependency waits and optional historical timing policy.
Passing the global regression does not turn the normalized timing captures into
physical 80286 evidence.

## Work still required for full Phase 9 closure

1. Select and document the target historical profile and evidence source.
2. Obtain or otherwise establish the physical/reference evidence needed for
   native bus phases, instruction timing and prefetch timing.
3. Define and validate the remaining `Fast` and `Accurate` policy contracts
   without changing architectural results or real dependencies.
4. Execute 9F in the downstream PCAT-286 project, recording the exact CPU
   revision, consumer revision, configuration and image hashes.
5. Publish a final named-profile closure receipt only after the uncovered
   behavior and the evidence limits are explicitly recorded.

There is no Phase 10 or later phase plan in this repository. Phase 9F is the
last documented increment, although historical timing work may continue within
Phase 9 until its acceptance criteria are met.
