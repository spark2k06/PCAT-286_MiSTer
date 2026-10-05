# LDT-backed task-switch correction and Landmark diagnosis - 2026-09-13

Scope: focused CPU fixes prompted by the Landmark/Supersoft protected-mode
failure. The user requested bounded tests and a commit, explicitly excluding
the extensive regression and any downstream PCAT modification. The user also
authorized the subsequently isolated LDTR-cache, accessed-byte and prefetch
corrections. No independent review or architectural PM closure is claimed.

## Confirmed defects and corrections

1. **Null selectors.** `spk286_selector` ignored TI and rejected `0004..0007`.
   Only GDT index zero is null: `0000..0003`. LDT index zero remains usable.
   The task segment service now applies the same full-index/TI predicate to
   ES/DS validation, cache publication and accessed updates, ignoring RPL.
2. **Incoming LDTR cache.** Early TR/LDTR publication preceded validation of
   the incoming LDT descriptor. Its validated hidden metadata was never
   republished. Refresh it while waiting for late segment checks; a later
   CS/SS/ES/DS fault must retain an already validated LDT. Invalidate the
   service's previous candidate when starting another switch.
3. **Accessed-byte address.** The task segment service wrote byte 4, corrupting
   the descriptor's high base byte. Write byte 5 (access rights), preserving
   the base. Correct the old unit expectation that incorrectly required byte 4.
4. **Instruction stream after CS publication.** The early task redirect
   published incoming IP before the new CS cache. A second redirect when CS
   is committed discards prefetched bytes from the outgoing physical base.
   Keep early IP publication for the existing late-fault state contract.

Primary evidence:

- Intel, *80286 (B-2/B-3) Information Sheet*, 21 November 1984, p. 4,
  null-selector background: index and TI must both be zero
  ([scan](https://docs.pcjs.org/manuals/intel/80286/80286_B2_B3_Errata-1984-11-21.pdf)).
- Intel 210498-005, section 8.3 steps 6-8 and Appendix B `SWITCH_TASKS`,
  B-12/B-13: validate/load the LDT before segment caches, and use the incoming
  CS:IP for execution. Descriptor layout and accessed-bit semantics: section
  6.3/6.4 and section 11.2. The cached manual text was consulted; no reference
  implementation source was copied.

The null rule also corrects the earlier local protected-mode draft's section
6.1. Pre-existing untracked specification files and unrelated README/Phase 8
changes are deliberately excluded from this correction's commit.

## Executable evidence

The new selector sweep failed on `0004` before the RTL correction. A separate
diagnostic sweeping all values identified exactly `0004..0007` as mismatches.
The old foundation test explicitly expected `0004` to be null.

The task/LDT test now waits for completion of cache publication, rather than
assuming four clocks after TR publication. Its original LDTR metadata assertion
then exposes the missing cache update. A distinct incoming CS base (`008000`)
and different instruction payload expose stale prefetch. The accessed-byte
assertion separately exposes the byte-4 corruption.

Focused Icarus results before the NT-policy investigation:

| Test | Checks |
| --- | ---: |
| protected_foundation | 65,571 |
| task_segment_service | 48 |
| task_switch_service | 45 |
| protected_task_ldt | 27 |
| protected_task | 21 |
| protected_task_gate_far | 14 |
| protected_task_iret | 10 |
| protected_task_state_fault | 204 (36 cases) |

The first four also pass in Verilator. Whole-core/module Verilator lint and
generated microcode consistency pass. Relevant checks are run via
`bash scripts/test_units.sh <simulator> <spk286_test_name>` and
`bash scripts/lint.sh`.

## Landmark reproduction and remaining NT source conflict

Original ROM SHA-256:
`A8310F83DE0F3E6B71E4A3FF82A01FFE3C3B5A957677AED2FAD17B96BCE2E577`.

The user-provided FPGA screenshots confirmed the original simulation's
`#TS(0004)` at saved `0018:A4AC`: the diagnostic stopped at `0018:B356`,
with AX=000A, BX=0004, CX=A4AC, DX=0018. This confirms the FPGA failure;
it is not evidence from a physical Intel 80286.

After the four fixes, the standalone diagnostic executes both LDT-backed tasks
and reaches the final `IRET` at `0004:0028` (physical ROM offset A519). NT is
clear after the task JMPs, so IRET attempts an ordinary stack return and raises
`#GP(0)` instead of returning to the original task.

A simulation-only counterfactual preserving incoming NT on task JMP reaches
the ROM's success/reset path: CMOS shutdown code 2, restored TR=0068, no
exception. The diagnostic removes only the two CX-exhausting busy-wait LOOP
instructions from its in-memory ROM fixture, retaining task counters,
transfers and result comparisons. Original ROM files are unchanged. This is
not a complete original-ROM/full-POST or historical-timing pass.

There is a primary-source discrepancy to resolve explicitly:

- Intel 210498-005 table 8-2 says incoming NT is cleared by task JMP.
- The same manual's Appendix B `SWITCH_TASKS` restores FLAGS and sets NT only
  for nesting, without specifying that clearing operation. The 1983 Intel
  Operating Systems Writer's Guide section on task switching describes the
  same restore/set-on-CALL sequence.
- PCjs's 286 `Segx86.switchTSS` preserves restored NT when not nesting
  ([reference code](https://github.com/jeffpar/pcjs/blob/master/machines/pcx86/modules/v2/segx86.js)).
  Reference code and a passing ROM are not substitutes for physical 286
  validation. No unconditional claim about all 86Box paths is made.

The production NT rule has not been changed at this checkpoint. A provisional
policy change requires the user's explicit choice; physical 286 confirmation
remains outstanding. The earlier PM5 independent review is retained unchanged
as a historical record, not silently rewritten to hide this discrepancy.

## Validation boundary

No extensive regression, full-corpus SingleStep run, broad synthesis, Quartus
build, downstream transfer, or new independent review was performed. These
focused results do not certify the entirety of Protected Mode. Local ROM
diagnostic artifacts remain ignored under `build/`; the permanent unit tests
do not depend on copyrighted BIOS images or motherboard logic.
