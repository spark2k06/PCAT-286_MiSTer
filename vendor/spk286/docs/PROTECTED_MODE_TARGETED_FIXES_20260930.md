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
