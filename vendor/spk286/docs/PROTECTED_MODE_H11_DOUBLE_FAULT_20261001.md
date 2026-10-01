# H11: exception delivery, double fault and shutdown

Date: 2026-10-01. Baseline SPK286 `5791657`, PCAT `3516454`.
Contract written before the implementation and directed tests.

## 286 classification

Intel 80286/80287 PRM 210498-005 (1987), 9.6.2, B-8 and 11.6 are the oracle.
Native 86Box's `386.c` fallback to `pmodeint_2386(8, 0)` demonstrates a
delivery step but does not supply the complete 286 classification.

| Active delivery origin | Fault detected before entry completes | Action |
|---|---|---|
| Actual exception #0, #10, #11, #12 or #13 | Second exception | Cancel old entry and deliver #DF |
| Actual #DF | Any further exception | Shutdown |
| #1/#2/#3/#4/#5/#6/#7/#9/#16, INTR or software INT | Second exception | Cancel old entry and deliver that exception |
| NMI accepted as an exit from shutdown | Any exception during its entry | Shutdown; only RESET can recover |
| Handler already entered | Fault in its instruction stream | Ordinary new exception |

This is the **286** first-exception rule, not the 386 page-fault pair table.
The source kind matters: `INT 8` is not an actual double fault; `INT 0` is
not a divide exception. Protected #DF carries exactly one zero error word.
Real-mode delivery uses its ordinary no-error-word frame.

## Context and lifecycle

- Cancel and drain the failed service using the existing semantic-cancel
  path, then dispatch the replacement exactly once. Do not re-acknowledge
  INTR. Never mark the abandoned software INT as successfully retired.
- Before an architectural entry handoff, retain the original exception or
  external-boundary CS:IP/FLAGS. A software INT that fails entry uses its
  first opcode/prefix address, rather than its successful return address.
- After an entry commits a new execution context, a later fault belongs to
  that live context. Do not restore prior stack/TSS writes or impose rollback.
  Record the committed-context checkpoint independently of the event vector.
- A task-gate exception saves the event's restart address and FLAGS into the
  outgoing TSS. Live GPRs, SP and segment state retain completed effects.
  Use a valid dedicated task for #DF so a failed source stack is not reused.
- Retain EXT provenance from the original external event across replacements.
  Changing the event kind to #GP must not erase an originating INTR/NMI/#NM.
- Pause must not accept a pending delivery failure. Redirect/reset cancels
  the entire chain without stale dispatch, completion or error metadata.
- Shutdown has HALT bus status and A1=0; HLT has A1=1. INTR is ignored.
  A fresh NMI may leave shutdown even if the failed chain had blocked NMI.
  A failing recovery NMI makes RESET the only exit. Successful NMI preserves
  PE; RESET clears the event chain and restores the reset architectural state.

## Validation scope

Directed tests must cover the full first-exception matrix, software/external
origins, zero error code, restart and committed context, EXT persistence,
successful/failing #DF task gates, failure after entering a handler, disabled
execution, cancellation, shutdown bus state and NMI/RESET recovery. They run
under both simulators; CPU integration also uses baseline and Max policies.

H15's task-switch fault-stage audit and H20's existing event-ordering policies
remain independent work. These tests do not certify all late task-fault stages,
all interrupt priorities or the entire protected-mode implementation.

## Implementation and additional finding

`spk286_events` classifies a failure while entry is active, cancels the failed
service and dispatches #DF or the replacement exception through existing
microcode. Its committed-context checkpoint and EXT latch survive that
replacement. Shutdown and recovery-NMI state remain in the CPU controller.
The top-level task service uses the saved event IP/FLAGS instead of the
already advanced instruction pointer. The new ports are internal; the CPU's
external board interface is unchanged.

Shutdown also clears stale instruction shadows. An SS cache load during a
failed task handoff otherwise leaves `ss_shadow` asserted with no instruction
available to release it, preventing the architectural NMI exit. A directed
controller case reproduces this before the fix; the CPU test fails its #DF
error push after handoff, accepts a recovery NMI and confirms that its still
invalid stack makes this NMI fail into reset-only shutdown. This cleanup is
specific to shutdown and leaves the separate H20 normal-execution policies.

The dedicated #DF task test exposed a second defect in the shared executor:
the latched task-completed condition contributed to `operation_done` for
every following micro-operation. It could finish `PUSH_EVENT_ERROR` before
the write response and target-SP commit. That condition is now restricted to
`TASK_SWITCH`; the existing task-tail skip leaves the error push live until
its real completion. The old #GP task-gate test additionally asserts SP=00FE,
and the #DF test requires SP=2FFE, one zero push and entry completion afterward.
This addresses a concrete task-gate effect also relevant to H15; it does not
close H15's broader staged task-switch review.

The inherited INTA lifecycle fixture now ends its modelled LOCK chain at
semantic cancellation, as well as at the first push. Previously it stopped
observing immediately at the old shutdown response. Its successful-entry
LOCK/READY/HOLD assertions and the exact two acknowledgements, preserved SP
and partial write counts on the impossible-stack cases remain asserted.

The lifecycle fixture also declares the existing downstream fetch profile.
Standalone runs retain the #GP oracle for an incomplete immediate at FFFE;
PCAT (`SPK286_TEST_REAL_MODE_FETCH_WRAP=1`) instead must fetch the high byte
at wrapped IP=0000, retire exactly one MOV with AX=3412/IP=0001 and issue no
fault/frame/write. All 468 cases still run. The unmodified pre-H11 PCAT
`3516454` reproduces the original no-wrap assertion failure at case 463;
this fixture distinction does not change production fetch behavior.

## Executable results

- Both simulators: 475 event-controller cases / 5,723 assertions each,
  including a 15-by-15 first/second vector matrix in PE=0/1. Software INT,
  INTR, NMI and trap origins are separate; vector #9 remains benign.
- Both simulators: 26 complete-CPU cases / 132 assertions each, under baseline
  and Max. Dedicated #DF task, backlink/busy bits, outgoing first-prefix IP,
  exact frames/error codes, no duplicate INTA, software-INT non-retirement,
  pause/resume/redirect, successful/failing shutdown recovery, an NMI-origin
  failed chain, and fault after a task handoff or in a handler instruction.
- Thirteen affected event, exception and task-gate banks pass in both
  simulators, including all 468 inherited lifecycle scenarios.
- Seven H11 RTL mutants are rejected by their intended functional assertions;
  pristine banks pass and production bytes remain unchanged. Six selected
  inherited event mutants likewise fail at their intended assertions.
- All 33,000 physical captures across the nine event/FLAGS opcodes pass,
  with no prefix/exception/revocation skips. The 10,000 D8/WAIT captures
  also pass; the H19 correction is retained.
- Compiler/Python tests, deterministic ROM audit, lint, reset smokes, state
  vectors and mapped portable synthesis pass. No new microcode format is
  required by H11 (format 27 remains the H19 image).
- Exact PCAT vendor passes eight affected banks under both simulators with
  P01/P02/P05; top/fetch real-mode wrap integration is preserved.

See [machine-readable receipt](REGRESSION_H11_DOUBLE_FAULT_20261001.json)
for source/log hashes and cohort identities. Physical comparisons above
cover real-mode inherited behavior; the new protected #DF cases use the
Intel-derived directed oracle, not physical protected-mode captures.
No full project regression or new OS/hardware boot is claimed.

## Reproduction and test executable

From the SPK286 root under WSL:

```sh
export SPK286_BUILD_DIR=$PWD/build/h11-20261001 SPK286_BUILD_JOBS=4
bash scripts/test_units.sh both spk286_double_fault_events
bash scripts/test_units.sh both spk286_double_fault_cpu
python3 -m tools.audit_double_fault --output "$SPK286_BUILD_DIR/double-fault-audit"
make state-smoke microcode-test microcode-audit lint
python3 -m tools.run_singlestep --events --full --include-prefixes --include-exceptions
python3 -m tools.run_singlestep --opcode D8 --opcode 9B --full --include-prefixes --include-exceptions
```

86Box Release is rebuilt from the exact vendor, retaining P02/P05 and the
existing profiles, and installed at `D:/GitHub/86Box_dev/build/spk286/86Box-linux`.
SHA-256: `8b0b1f33630789cf45a1f071bfe33405db8eee22fc474744dabf350e78ebea9e`.
The prior executable is retained as `86Box-linux.pre-h11-20261001`; build log
is `D:/GitHub/86Box_dev/build/spk286/h11-20261001-build.log`.

Primary source: [Intel 286 PRM](https://bitsavers.org/components/intel/80286/210498-005_80286_and_80287_Programmers_Reference_Manual_1987.pdf).
