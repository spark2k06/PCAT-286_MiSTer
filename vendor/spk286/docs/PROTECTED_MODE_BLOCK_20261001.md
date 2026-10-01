# Protected-mode follow-up block: H03, H10, H12, H13

Baseline: `b5a82d8`, 2026-10-01. The user authorized this four-story block,
directed validation and separate milestone commits in SPK286 and PCAT.
The whole-project regression will run after the block.

## H03 — POPF and ordinary IRET FLAGS privilege masks

**Implemented and directed validation passed.** Intel 80286 PRM 210498-005,
section 10.1, permits POPF/IRET to restore NT, restricts IOPL writes to CPL0,
and restricts IF writes to executing CPL <= old IOPL. The decision must use
the pre-return context, not the destination CPL or the popped IOPL.
Real-mode POPF/IRET preserve NT/IOPL under the existing 286 compatibility
contract, corroborated by native 86Box `opPOPF_286` and physical real-mode data.
Native protected `pmodeiret` computes its flag mask before publishing CS/CPL.

Before correction the new bank fails on ordinary CPL0 IRET: old FLAGS `00D7`,
popped `9DD5`, expected `1DD7`, actual `0DD7`. A shared instruction FLAGS mask
now implements those rules for POPF and ordinary IRET. Task-return FLAGS use
their existing separate path. No microcode or timing policy changed.

| Directed validation | Result |
|---|---|
| `spk286_return_flags`, Icarus and Verilator | 5892 cases / 20280 checks each |
| Same bank with PCAT P01/P02/P05 options, both simulators | Same totals, passed |
| Existing ordinary-gate NT bank, both | 158 cases / 944 checks each |
| Existing protected return/retry bank, both | 27 cases / 81 checks each |
| Existing nested-task IRET bank, both | 10 checks each, passed |
| Existing stack/control bank, both | 9128 cases / 1944134 checks each |
| Complete physical real-mode 9D and CF files | 10000 passed, zero failures/skips |
| RTL lint, compiler tests and reset smoke | Passed; 105 compiler tests |

The new bank covers all CPL/IOPL pairs, opposite old/new IF, incoming NT and
IOPL combinations, same/outer IRET, real-mode controls, failed returns,
READY stalls and all three timing policies. Failed IRET preserves source
FLAGS/CPL/SP. Physical files establish real-mode compatibility; they are not
a silicon oracle for protected-mode gates.

Reproduce with `bash scripts/test_units.sh both spk286_return_flags`.
Logs and the failing baseline are retained in `build/pm-block-20261001/h03-*`.

## H10 — Interrupt/trap gate target selector RPL

**Implemented and directed validation passed.** Intel 80286 PRM chapter 9
and INT pseudocode distinguish the software gate-DPL check, target-code DPL,
and the resulting CPL. Gate target selector RPL is ignored. Native 86Box
`pmodeint` corroborates the distinction. Direct transfers retain their own
selector checks.

Before correction, changing only the target RPL from zero to one makes the
new bank fail on a valid CPL0 ordinary gate. The gate-specific code predicate
now requires target DPL <= source CPL independently of target RPL. Existing
publication normalizes CS RPL to the resulting CPL; conforming code retains
the source CPL. No microcode or event-order policy changed.

| Directed validation | Result |
|---|---|
| `spk286_gate_target_rpl`, both simulators | 1476 cases / 9240 checks each |
| Same bank with PCAT P01/P02/P05, both | Same totals, passed |
| Ordinary gate NT bank, both | 158 cases / 944 checks each |
| Protected outer event bank, both | 6 checks each, passed |
| Task-gate event/privilege/outer bank, both | 144 cases / 448 checks each |
| Normal and PCAT-option RTL lint | Passed |

The matrix varies all four target RPLs, source CPL0..3, all reachable target
DPLs, conforming/nonconforming code, interrupt/trap gates, software INT,
INTR with two-phase INTA and NMI, all timing policies and READY stalls.
It verifies saved frame state, live FLAGS, resulting CPL and ordinary IRET.
Negative software gate-DPL controls reject while external delivery ignores
gate DPL. Delivery of a fault raised during gate validation is H11; these
negative controls inspect the first fault, not a claimed working #DF path.

Reproduce with `bash scripts/test_units.sh both spk286_gate_target_rpl`.
Logs and the failing baseline are retained in `build/pm-block-20261001/h10-*`.

## H12 — Stack vectors and selector error provenance

**Implemented and directed validation passed.** The handwritten fault ledger
uses Intel 80286 PRM 9.6, B-1, CALL B-24/B-25 and INT/IRET algorithms:

| Fault site | Vector | Error provenance |
|---|---|---|
| Invalid source return frame or stack-word range | #SS | Literal zero |
| Multiword operand wrap through SS | #SS | Literal zero |
| Missing/short current TSS while obtaining an inward stack | #TS | Current TR selector, RPL cleared, EXT from event origin |
| Null/out-of-table/type/privilege invalid new SS from TSS | #TS | New SS selector, RPL cleared, EXT from origin |
| Otherwise valid absent new SS | #SS | New SS selector, RPL cleared, EXT from origin |
| Insufficient new stack or source parameter range | #SS | Literal zero |
| Absent call gate | #NP | Gate selector, RPL cleared |
| Absent IDT gate | #NP | IDT entry offset with IDT bit and origin EXT |
| Absent target code / invalid code type | #NP / #GP | Target CS selector, RPL cleared, origin EXT |
| Target offset out of range | #GP | Literal zero |

Before correction the new bank reports #TS(`0030`) for a short current TSS
whose TR is `0028`: it incorrectly names the call gate. The CPU now separates
stack-range faults, uses the current TR for TSS prechecks, classifies TSS-derived
SS access faults as #TS, and assigns zero to stack capacity/range failures.
The obsolete saved gate-selector register was removed after all uses disappeared.
EXT recognizes INTR/NMI, single-step and NPX #NM/#9 delivery; ordinary
instruction-generated protection faults and software INT use EXT=0. This does
not implement H11's delivery-failure/#DF state machine.

| Directed validation | Result |
|---|---|
| `spk286_fault_metadata`, both simulators | 996 cases / 3300 checks each |
| Same bank with PCAT P01/P02/P05, both | Same totals, passed |
| Odd stack bank, both; strengthened to require #SS on failed returns | 216 cases / 951 checks each |
| Protected return/retry, both | 27 cases / 81 checks each |
| Call-gate Accessed bank, both | 144 cases / 420 checks each |
| POP segment restart, both | 36 cases / 96 checks each |
| Task-gate error and fault banks, both | 7 checks; 13 cases / 49 checks, passed |
| Normal and PCAT-option RTL lint | Passed |
| Entire Python suite | 340 passed |
| Actual event mutation audit | 22 injected faults rejected; 2 pristine controls passed |

The matrix varies selector RPL, GDT/LDT error provenance, software CALL/INT,
INTR, NMI, instruction #GP and single-step, return and SS-override boundaries,
all timing policies and READY stalls. It captures the first fault and checks
that source FLAGS/CS/SP remain intact and no frame write occurs. NPX delivery
classification follows the explicit manual rule; executable ESC/WAIT support
is still H18. Mixed-invalid descriptor priority remains H13.

The event-audit's historical real-mode IRET mutation anchor was adapted to
H03's shared mask; its actual mutant still fails the unchanged frame assertion.
No expected architectural result was weakened. Logs are under
`build/pm-block-20261001/h12-*`.

## H13 — Descriptor type/privilege before presence

**Implemented and directed validation passed.** Intel 80286 PRM load, CALL,
RET/IRET algorithms, interrupt table 9-1 and task-switch B-12/B-13 validate access/type and
privilege before presence. A descriptor with both invalid access and P=0 must
report the access exception (#GP, or #TS for task/TSS-derived segments).
Only otherwise valid absent descriptors request #NP/#SS. Native 86Box's
16-bit segment and transfer paths corroborate these separate checks.

Before correction, the new CPU bank's first case (MOV DS, invalid system
descriptor, P=0) reports #NP(`0030`) instead of #GP(`0030`). The new task
service cases also reject the isolated old service at invalid absent ES.

Separate access predicates now drive fault classification for ordinary
segment loads, return CS/SS, call/task gates and their targets, TSS-derived
SS, LLDT/LTR and IDT gates. The success predicates additionally require P.
Task validation selects invalid before absent within each segment while
retaining SS -> CS -> ES -> DS ordering. CS presence is excluded from the
task CS privilege predicate, so a valid absent CS correctly remains #NP.
Task hidden-state publication and timing policies are unchanged; H15 stays open.

| Directed validation | Result |
|---|---|
| `spk286_fault_precedence`, both simulators | 1356 cases / 5424 checks each |
| Same bank with PCAT P01/P02/P05, both | Same totals, passed |
| Expanded task segment service, both | 424 checks, including 82 new mixed-condition cases |
| H12 first-fault metadata bank, both | 996 cases / 3300 checks each |
| Existing task state/privilege/fault banks, both | 36/32/13 cases; 202/116/49 checks, passed |
| Existing LTR and protected system banks, both | 23 / 538 checks, passed |
| Existing direct CALL, conforming data and JMP gate banks, both | 144/77/816 cases; 300/100/1704 checks, passed |
| Normal/PCAT-option RTL lint and Python suite | Passed; 340 Python tests |

The CPU bank covers 19 load/return/gate/TSS instruction paths, wrong type
and wrong privilege with P=0/1, valid absent controls, table-limit controls,
selector RPL variants, all timing policies and READY stalls. It requires exact
vector/error provenance, unchanged GPRs/selectors/FLAGS/SP and no rejected
descriptor Accessed/BUSY/TR/LDTR publication. The service bank verifies task
segment ordering separately; its raw-selector metadata is normalized by the
CPU executor as recorded under H12.

Reproduce with `bash scripts/test_units.sh both spk286_fault_precedence` and
`bash scripts/test_units.sh both spk286_task_segment_service`.
Logs are under `build/pm-block-20261001/h13-*`.

## Inherited matrix expectation corrections

The first whole-project run stopped in the established Icarus expand-down
matrix. The CPL1 SS absent-descriptor case expected #SS even for RPL0,
although Intel MOV B-73/B-74 requires RPL=CPL before testing presence.
Other DS/ES/SS and CALL-gate absent cases had the same mixed-condition
expectation issue. Their vector expressions now distinguish invalid privilege
(#GP) from otherwise valid absence (#NP/#SS).

The subsequent matrix run exposed historical ordinary-event target-RPL
rejections. These now require successful delivery and normalized CS for all
four target RPLs, as specified by H10. Gate-DPL and outward-target rejection
controls remain. No cases or state assertions were removed; no production RTL,
microcode, physical identities or comparison masks changed during this repair.

For interrupt targets, the access-before-presence classification follows
Intel table 9-1 and native 86Box's 16-bit `pmodeint` DPL check. The appendix
INT overview places target presence earlier in its narrative algorithm; this
block does not establish silicon sequencing of every simultaneous gate,
target and new-stack fault. General cross-stage delivery remains H11/H19.

The original regression failure and intermediate matrix failure remain in
`build/pm-block-20261001/full/regression-first.log` and
`build/pm-block-20261001/h10-h13-inherited-first.log`.

## Remaining protected-mode stories after this block

H02 is partial (explicit LOCK and protected zero-count REP precedence).
H05, H11, H15, H16, H17, H18, H19 and H20 remain open. The four changes do
not resolve uncertain physical policies, general boundary/partial-execution
coverage, double-fault delivery or late task-cache publication.
