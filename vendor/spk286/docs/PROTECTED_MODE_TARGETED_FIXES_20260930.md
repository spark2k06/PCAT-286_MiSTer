# Protected-mode targeted milestones — 2026-09-30

The user authorized H04, H14, H01 and H02's CLI/STI and I/O subset, with a
separate commit per verified milestone. Whole-project regression is explicitly
deferred to a later task. Expectations derive from Intel 210498-005, with the
native 86Box 286 paths as supporting evidence; no 386 facilities are imported.

## H04 — Ordinary gate entry clears NT

Intel section 10.1 requires saving old FLAGS before clearing NT on an interrupt
without a task switch. Native `x86seg.c::pmodeint` likewise clears TF/NT for
interrupt/trap gates, and only interrupt gates clear IF. The RTL change is
limited to the ordinary event FLAGS mask; microcode is unchanged.

Before correction, the directed bank fails with live FLAGS=7002 on an
interrupt gate entered with NT=1. After correction:

| Check | Actual result |
|---|---|
| New `spk286_event_nt`, Verilator and Icarus | 158 cases / 944 checks in each |
| Existing `spk286_protected_event_outer`, both | 6 checks in each |
| Existing `spk286_protected_task_gate`, both | 9 checks in each; nested NT preserved |
| Verilator RTL lint | Pass |
| Generated microcode consistency | Pass, unchanged 122 entries / 723 words |
| Physical SingleStep CD sample | 100 passed / 0 failed; real mode only |

The new bank executes real instructions from an independent LOADALL fixture,
with READY stalls, NT=0/1, interrupt/trap gates, software INT and #GP sources,
same/inward privilege transfers, all three timing policies and real-mode
controls. It checks saved FLAGS, live FLAGS, frame size, destination context and
ordinary handler IRET. H03's restoration of NT/IOPL from return FLAGS remains
open; it is not asserted as fixed by this milestone.

Reproduction:

```sh
SPK286_BUILD_DIR="$PWD/build/pm-targeted-20260930" SPK286_BUILD_JOBS=4 \
  bash scripts/test_units.sh both spk286_event_nt
```

Local before/after, affected-bank, lint and SingleStep logs are retained under
`build/h04-*.log` and `build/pm-targeted-*.log`. No full regression, new OS boot,
Quartus synthesis or physical protected-mode measurement was performed.

## H14 — Valid unaligned protected stacks

Intel section 2.2 explicitly permits unaligned words, including stacks. Native
286 gate/return paths check byte ranges without imposing general SP alignment.
Removed only `return_stack_pointer[0]` from the outer-return range predicate
and `call_stack_sp_q[0]` from the inward-frame predicate. The low-SP/FFFF
overrun checks remain; these check complete accesses, not general alignment.

Before correction, RETF with valid source SP=F001 raises #GP instead of
returning. After correction:

| Check | Actual result |
|---|---|
| New `spk286_odd_protected_stack`, both simulators | 216 cases / 951 checks in each |
| Existing `spk286_call_stack_precheck`, both | 9 checks in each; SP=3 rejected before writes |
| Existing `spk286_outer_return_sp`, both | 216 cases / 693 checks in each |
| Verilator lint / generated consistency | Pass |
| Physical SingleStep CB/CA/CF samples | 300 passed / 0 failed; real mode only |

The directed bank covers RETF, RETF-immediate, IRET, inward CALL with two
parameters, interrupt and trap gates, their return frames, odd/even SP,
ordinary/expand-down stacks, all timing policies and READY stalls. It verifies
exact frame words, transfer counts and paired high/low byte lanes. Invalid
limits, frame underflow and FFFF crossing must still fault before publishing
the return or writing the gate frame.

The invalid outer-return controls expose an existing H12 discrepancy: the
micro-executor range signal routes to #GP(0) where Intel requires #SS(0).
Those controls assert rejection and preserved restart state; they deliberately
do not assert the incorrect vector as an architectural expectation. Inward
gate range controls additionally assert #SS. H12 remains open; H14 changes
only alignment acceptance. Local logs: `build/h14-*.log`.

```sh
SPK286_BUILD_DIR="$PWD/build/pm-targeted-20260930" SPK286_BUILD_JOBS=4 \
  bash scripts/test_units.sh both spk286_odd_protected_stack
```

Whole-project regression and hardware/synthesis checks remain deferred as
requested; no new OS boot was run for this milestone.
