# Protected Mode PM2b — Protected CS Validation and Direct Far Transfers

Status: implemented as a bounded PM2b slice. This increment validates a
protected CS candidate before direct far control-transfer side effects and
commits the CS hidden cache together with the target IP and prefetch redirect.
It does not claim complete protected-mode transfer, gate, privilege-transition
or fault-delivery semantics.

## Implemented contract

The project-owned `VALIDATE_CS` micro-operation is inserted into the existing
far-pointer protocols. In protected mode it:

- resolves the target selector through the GDT or the currently loaded LDT and
  rejects null, out-of-table and unavailable-LDT selectors before descriptor
  commit;
- reads the complete eight-byte descriptor and requires a present code
  descriptor with the current-CPL/RPL rules for non-conforming code, or
  `DPL <= CPL` with the selector RPL ignored for conforming code;
- retains the caller CPL and stack for conforming targets, normalizing the
  committed CS RPL to the retained CPL;
- checks the target IP against the candidate code limit;
- writes the descriptor accessed bit before accepting a candidate whose bit A
  was clear;
- latches the candidate CS selector, base, limit, access, class, presence,
  DPL, table indicator and RPL;
- commits the candidate only at `CONTEXT_COMMIT`, together with the target IP
  and existing queue flush/fetch restart path.

Valid descriptor absence reports #NP; invalid type, selector, privilege or
offset reports #GP. Real Mode treats `VALIDATE_CS` as a no-op, preserving the
existing far-instruction behavior.

The validation is present in direct immediate and memory far CALL/JMP and in
the existing RETF protocols. RETF stack-pop atomicity, inter-privilege
transfers, inter-level/task gates and complete protected event-entry semantics
remain deferred. Same-level call gates are documented separately in
`PROTECTED_MODE_PM4A.md`; the bounded same-level IDT gate slice is documented
in `PROTECTED_MODE_PM3A.md`.

## Verification

`sim/unit/spk286_protected_system_tb.sv` adds PM2b checks for:

- a direct far JMP to a present code descriptor with A-bit writeback;
- a direct far JMP to a conforming code descriptor whose selector RPL differs
  from CPL, including retained CS/CPL and stack state;
- atomic CS cache, target IP and redirect state, followed by execution at the
  protected target;
- rejection of a data descriptor as CS with #GP and preservation of the
  previously committed CS cache.

The integrated protected-system bench passes in Icarus with 100 checks. The
focused protected matrix now adds direct far-CS coverage for CPL0, CPL1 and
CPL3 across DPL/RPL, conforming/non-conforming, code type and presence cases;
the combined protected fixture now passes 510 checks in Icarus; the direct
far-CS portion remains 132 matrix checks. The inherited
far-instruction and far-lifecycle matrices also pass in both simulators (6,760
and 247 cases respectively).

The functional rules follow the
[Intel 80286 Programmer's Reference Manual](https://bitsavers.trailing-edge.com/components/intel/80286/210498-005_80286_and_80287_Programmers_Reference_Manual_1987.pdf).
Historical timing remains separate from descriptor, BIU, queue and redirect
dependencies.
