# Protected Mode PM2e — Expand-Down Data and Stack Limits

Status: implemented as a bounded PM2–PM4 completion slice. This increment
extends the existing protected descriptor/cache paths with 80286 expand-down
range semantics for ordinary data accesses and protected privilege-transition
stacks.

## Implemented contract

- Protected byte and word operand services accept an offset only when it is
  strictly above an expand-down descriptor limit and the complete access still
  ends at or below `FFFFh`.
- Protected DS/ES/SS hidden-cache validation continues to use the descriptor
  class and accessed-bit writeback already established by PM2a.
- TSS-selected event and inter-level call-gate stacks accept expand-down data
  descriptors when their privilege and writable checks pass.
- Event, call-gate and inter-level return range checks use the correct lower
  bound and 16-bit wrap rules. Event frame preflight accounts for the complete
  outer event frame, including an optional error code; call-gate preflight
  accounts for saved context and copied parameters.
- Source parameter reads, target stack writes and restored `SS:SP` validation
  remain separate from architectural context commit. A rejected frame does
  not issue a partial stack transfer.
- Real Mode stack and operand behavior remains unchanged.

Task gates, task switching, and broader fault-escalation policy remain outside
this slice. Historical timing is not inferred from the added checks; BIU,
READY, descriptor, TSS and queue dependencies remain functional requirements.

## Verification

The focused expand-down bench checks a valid DS access, null `DS`/`ES` loads
with null `SS` rejection, CPL1 `DS`/`ES` reloads rejected against a present
DPL0 descriptor, an RPL3 `DS` rejection against that descriptor, a valid outer
event frame on a TSS-selected expand-down stack, a CPL1 software `INT` rejected
by a DPL0 gate before the first destination write, and a lower-bound rejection
before the first destination write under deliberate READY stalls. It now also
exhausts the CPL1 `DS`/`ES`/`SS` matrix across DPL1/DPL2/DPL3 and RPL0..RPL3,
including present, not-present, writable data, read-only data and
non-readable code descriptors. It also checks read/write permissions and
normal/expand-down word-limit boundaries, including 16-bit wrap rejection.
The same DPL/RPL/type/presence matrix is executed at CPL0 after a real
inter-level call-gate transition onto the TSS-selected stack, and at CPL3
after a real CPL0 outer `IRET` to DPL3 code and stack descriptors. The same
fixture now adds the equivalent CPL2 matrix after a real CPL0 outer `IRET` to
DPL2 code and stack descriptors. The CPL2 matrix covers normal and
expand-down data, read-only/readable-code and non-readable-code types,
not-present data/code descriptors and the GDT-limit boundary for DS/ES/SS.
The same fixture now adds the PM2b direct far-CS matrix across CPL0/CPL1/CPL2/CPL3;
the CPL2 slice contributes 56 direct-transfer cases covering readable and
non-readable code, conforming code, presence and the GDT-limit boundary. The
fixture also exercises a 96-case PM4 inter-level
call-gate privilege matrix across CPL0/CPL1/CPL2/CPL3, gate RPL0..RPL3, gate
DPL0..DPL3, present/not-present descriptors and the GDT-limit boundary. The
new CPL2 slice contributes 24 real outer-`IRET` to call-gate transition
cases. The
combined fixture now adds an 89-case PM3 event target/gate matrix covering
CPL0/CPL1/CPL2/CPL3, target DPL/RPL relationships, interrupt/trap and invalid
gate types, gate/target presence, conforming and non-readable code, and CS/IDT
limits. It also adds 352 CPL1, 352 CPL3 and 448 CPL2 PM1 selector-inspection
checks across VERR/VERW/LAR/LSL. The CPL2 slice enters through a real outer
`IRET` and covers normal/expand-down data, code types, presence and the GDT
limit boundary. The fixture also adds 28 CPL2 PM4a same-level gate cases
covering gate DPL/RPL, presence, GDT limit and target code/data classes,
bringing the combined fixture to 2183 checks in Icarus.

The protected-system bench additionally exercises a parameter-copying call gate
with an expand-down TSS stack. The protected-RETF bench covers an expand-down
caller stack through outer `IRET`, inter-level call-gate source reads and
`RETF 4` restored-`SS:SP` commit.

The relevant Icarus directed benches pass with the existing protected-system,
event, RETF, segment and operand-service coverage. Verilator and Yosys remain
environment-dependent checks when those tools are available.
