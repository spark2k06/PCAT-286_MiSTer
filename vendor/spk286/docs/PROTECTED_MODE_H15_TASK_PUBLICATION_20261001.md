# H15: incoming task state and late descriptor faults

Date: 2026-10-01. Baseline SPK286 `4dab80c`, PCAT CPU vendor `9e3905f`.
This closes H15's documented publication defect; H16 and the remaining H19
boundary matrix are separate work.

## Architectural contract

The primary source is Intel 80286/80287 PRM 210498-005 (1987), the
`SWITCH_TASKS` algorithm on B-12/B-13, with section 8.4's task sequence.
[Intel manual](https://bitsavers.org/components/intel/80286/210498-005_80286_and_80287_Programmers_Reference_Manual_1987.pdf).
The cached PDF SHA-256 is
`ad487ba99b48cd9f61b14c0fe912a04c7cdb4c7c14a18419aa9faf62d8962460`.

After the TSS save/load and BUSY/backlink effects, incoming registers,
selectors and TR belong to the new task. Outgoing segment caches cannot
remain usable during incoming validation. Earlier successful cache loads
survive a later fault. The exception restart context is the incoming CS:IP,
even though a CALL/JMP/IRET microprogram has not retired.

| Fault stage | Incoming segment caches already valid | Incoming LDTR |
|---|---|---|
| LDTR | None | Incoming selector, invalid cache |
| SS | None | Validated LDT, or validly disabled null LDT |
| CS | SS | Same |
| First data segment | SS, CS | Same |
| Second data segment | SS, CS, earlier data segment | Same |
| Incoming IP beyond CS.limit | All validated non-null segments | Same |

The manual orders LDTR, SS, CS and then the DS/ES pair. It does not establish
an observable ordering inside that pair. SPK286 retains its existing ES then
DS policy; the tests document that implementation order, without claiming a
physical 286 discriminator. Invalid cache payload fields are cleared for
internal safety; their raw values are not claimed to reproduce inaccessible
physical cache bits.

Type/privilege failures precede presence failures, preserving H13. SS absence
raises #SS, code/data absence #NP, invalid task selectors/descriptors #TS,
and an out-of-range incoming IP #GP(0). Later handler delivery and #DF retain
H11's independently tested rules.

## Implementation

- The composite task service waits for architectural state publication before
  issuing any incoming LDTR validation fault. The executor acknowledges after
  publishing GPRs, FLAGS, IP, TR, visible segment selectors and cache invalidation.
- The segment service validates SS, CS, ES and DS individually, completes each
  Accessed-byte write, and publishes that cache before advancing. A later fault
  does not roll back earlier caches or writes. Null data selectors remain visible
  and invalid; their descriptor is not fetched.
- Temporary invalid incoming CS blocks prefetch. A fetch exception is demanded
  at instruction dispatch, rather than interrupting the task validation itself.
  Validated CS publication flushes previously fetched bytes again.
- Initial late-task exceptions use incoming CS:IP instead of the outgoing
  instruction ledger. SS shadow detection uses the actual cache commit index.
- All new wires are internal. The external CPU interface is unchanged.

The previous PM5 grouped/transactional cache publication is superseded by this
dated contract. Existing BUSY, backlink, outgoing TSS save and fault precedence
fixes remain in force. No 386 or 287 behavior is introduced.

## Executable comparison with native 86Box

`sim/programs/task_late_fault.asm` is a project-owned 64 KiB reset program. It
constructs its own RAM tables and protected environment, then enters a task by
CALL, JMP, software-INT task gate or nested IRET. It needs neither an operating
system disk nor third-party BIOS bytes. The same assembled ROMs execute in RTL
and in isolated native/SPK286 instances of 86Box.

For an absent incoming CS after valid SS, CALL entry produces:

| Observation | Original native 86Box | SPK286 before H15 | SPK286 after H15 |
|---|---|---|---|
| AX | 1111, outgoing | BEEF, incoming | BEEF, incoming |
| TR | 0018, outgoing | 0020, incoming | 0020, incoming |
| DS / ES | 0060 / 0060 | 0060 / 0060 | 0048 / 0040 |
| Handler SS:SP | 0010:0EF8 | 0010:0EF8 | 0038:0EF8 |
| Saved CS:IP | 0008:0053 | 0008:0053 | 0030:005D |
| Incoming SS Accessed | Unset | Unset | Set |

The native `taskswitch286` implementation validates CS before loading all
general/segment state and updates TR at the end. Its executable observation
therefore conflicts with Intel's incoming-context sequence in these late-fault
cases. It is useful comparative evidence, not an acceptance oracle for H15.
Neither native 86Box nor expected results were changed to conceal that conflict.
The extra illegal-LDTR.TI and nested-IRET controls are recorded in the receipt.

The 86Box helper `tools/spk286_cpu/run_task_probe.py` supplies private ROMs,
configuration, CMOS, logs and RAM snapshots for each arm, and closes both
processes. The existing production disk/profile is untouched. Example in WSL:

```sh
python3 -m tools.task_late_vectors --output build/h15-vectors
# From the 86Box source directory:
python3 tools/spk286_cpu/run_task_probe.py --build build/spk286 \
  --rom /mnt/d/GitHub/SPK286/build/h15-vectors/s3-e0-a1-h0.rom \
  --out build/h15-probe
```

## Directed validation and limits

The [receipt](REGRESSION_H15_TASK_PUBLICATION_20261001.json) records exact source,
ROM, executable and log hashes and the before/after observations.

- Both simulators: 80 executable late-task cases, 1,100 checks per simulator,
  covering all four task-entry forms, each validation stage, type/presence
  failures, early no-fetch LDTR.TI failure, interrupt/task-gate handlers, BUSY,
  backlink, earlier Accessed writes and incoming exception frames.
- Both simulators: 20 additional affected task, descriptor, event, outer-stack,
  double-fault, LOADALL, metadata and precedence banks.
- PCAT vendor with P01/P02/P05: six affected banks, including the same 80 ROMs.
  The downstream real-mode fetch-wrap adaptation remains intact.
- Python tests, microcode consistency/audit, Verilator lint and portable Yosys
  synthesis pass. Five isolated publication/context mutations are rejected;
  the pristine four-ROM audit control passes.
- 15,000 physical SingleStep captures for 9A, EA and CF pass with no skips.
  These are real-mode controls, not physical protected task-switch captures.
- Twelve ROM cases were run before and after in both native/SPK 86Box arms.
  Every arm reached its guest completion signature.

An early mutation selection failed to detect premature validation because its
LDTR descriptor fetch outlasted state publication. The final audit uses the
illegal TI selector, which faults without a descriptor fetch, and rejects the
mutation. An affected-bank shell invocation also failed after a running script
was edited; its final immutable rerun passed. These failed attempts are retained
in ignored build logs and are not counted as successful validation.

This milestone is directed validation, not a new full project regression.
No new OS/2 boot, Quartus synthesis, FPGA timing result or physical protected
task-fault capture is claimed. The 86Box executable was rebuilt from the PCAT
vendor with its existing P02/P05 options; hardware validation remains available
to the user. H16's exact-zero-only incoming null LDTR predicate is unchanged here.
