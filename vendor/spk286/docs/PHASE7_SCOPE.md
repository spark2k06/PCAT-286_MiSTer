# Phase 7 — ordinary Real Mode completion

Current D-037 policy (2026-09-09): the corrected strings/REP and scalar/string
I/O implementation is integrated in ordinary repository sources. All 307
required files remain in scope. REP initial-zero-count ordering is an open
engineering policy; exactly one incomplete E7 capture is NOT EVALUABLE, with
4,999 evaluable E7 records still required. These and the three inherited D-026
notes are nonblocking for functional/development acceptance. Final executable
validation, independent functional approval and verified delivery remain required.
See [the current policy](PHASE7_FUNCTIONAL_POLICY.md). Historical text below
retains its original dates, counts and conclusions; its incompatible REP/E7
closure prerequisites are superseded by D-037.

Closure update (2026-09-09): production admission still has 285 of 307 required
files. All 307 are implemented in the preserved ordered candidate, whose local
review findings are now corrected and independently reviewed. E7 remains required
and fails capture admission; REP initial CX=0 remains a new evidence blocker.
The production `phase7_forms.json` is intentionally not changed to imply delivery
of the 22 isolated forms. See [current closure](PHASE7_CLOSURE_20260909.md).
Bounded Phase 8 preparation is documented separately; implementation has not begun.

Status (2026-09-08): implementation in progress; no complete Phase 7 validation or readiness
claim. This is the incremental phase following interrupts/exceptions, not the
system/protected-mode numbering of the original long-term specification. Phase 8
has not started. D-026 separates provisional development from architectural release.

## Source and admission contract

Intel 210498-005 (1987), chapters 2–5 and Appendix B, Intel 210498-003 (1985),
and Intel 210760-002 (1987) govern new instruction semantics. The B-2/B-3 sheet's
instruction-length correction requires #GP for instructions longer than ten
bytes. The pinned physical corpus is
`37c73caf53dcd22d3dd369ff09305d13d117a4fe`, Harris N80C286-12, with the vendor's
stepping qualification retained. It does not exercise arbitrary IF/TF delivery,
READY waits or streaming prefetch. Emulator agreement is not physical adjudication.

`phase7_forms.json` records required forms, the pinned corpus file inventory and
explicit exclusions. A required form remains required while implementation or
verification is pending. Metadata status `alias`, `undocumented` and `fpu` is not
silently treated as a documented opcode. Unsupported legal/undocumented forms
remain distinct from invalid encodings; the decoder must not invent #UD merely
because a form is absent from the implementation.

## Required forms

| Group | Encodings and forms |
|---|---|
| MOV | 88/89 and 8A/8B both directions, byte/word, all register/ModR/M addressing; B0–BF register immediate; A0–A3 accumulator moffs; C6/C7 /0 immediate to RM |
| Segments | 8C /0–3 stores; 8E /0,/2,/3 loads; PUSH ES/CS/SS/DS (06/0E/16/1E), POP ES/SS/DS (07/17/1F); invalid segment encodings including MOV CS checked |
| Pointer/address | LEA 8D, LES C4, LDS C5 (memory-only); XLAT D7 |
| Exchange | XCHG 86/87 byte/word RM/register and 90–97 AX/register including NOP; automatic LOCK contract |
| Binary arithmetic | ADD/OR/ADC/SBB/AND/SUB/XOR/CMP: group bases 00/08/10/18/20/28/30/38 with forms +0 through +5; 80/81/83 /0–7 immediate RM forms |
| TEST and unary | TEST 84/85, A8/A9, F6/F7 /0; NOT /2, NEG /3; INC/DEC 40–4F and FE/FF /0,/1 |
| Conversion/adjust | CBW 98, CWD 99, DAA 27, DAS 2F, AAA 37, AAS 3F, AAM D4 and AAD D5, including immediate-byte acquisition and actual #DE where applicable |
| Shifts/rotates | C0/C1 immediate count, D0/D1 count one, D2/D3 CL: /0 ROL, /1 ROR, /2 RCL, /3 RCR, /4 SHL/SAL, /5 SHR, /7 SAR; byte/word, register/memory |
| Multiply/divide | F6/F7 /4 MUL, /5 IMUL, /6 DIV, /7 IDIV; IMUL 69 imm16 and 6B sign-extended imm8, register destination and RM16 source; true #DE |
| Stack/control | Inherited near/conditional/loop/stack forms; PUSHA 60, POPA 61, ENTER C8 imm16,imm8, LEAVE C9; BOUND 62 register against memory pair and true #BR |
| Far transfer | Direct CALL 9A ptr16:16 and JMP EA ptr16:16; indirect FF /3,/5 memory pointers; RETF CA imm16 and CB; invalid register-direct far forms |
| FLAGS | CLC F8, STC F9, CMC F5, CLD FC, STD FD, SAHF 9E, LAHF 9F; preserve inherited CLI/STI/PUSHF/POPF/IRET policy |
| Prefixes | Segment 26/2E/36/3E, LOCK F0, REPNE F2, REP/REPE F3; accumulation, duplicate handling, length faults, cancellation and restart |
| Memory strings | MOVS A4/A5, CMPS A6/A7, STOS AA/AB, LODS AC/AD, SCAS AE/AF, byte/word, nonrepeated/repeated, both DF directions |
| Port I/O | IN E4/E5 imm8, EC/ED DX; OUT E6/E7 imm8, EE/EF DX; byte/word |
| String I/O | INS 6C/6D, OUTS 6E/6F, byte/word, nonrepeated/repeated; independent port transaction effects |

All applicable ModR/M register and memory directions, displacement forms,
immediate values and exceptional outcomes are in scope. Word accesses at FFFF,
multiword pointer and stack boundaries, byte-at-FFFF, invalid owned groups,
ten-byte length and actual #DE/#BR producers need directed and physical coverage
where available. An absent corpus case requires directed verification, not an
invented physical pass. Defined, preserved and undefined FLAGS are separate.

## Explicit exclusions

Protected-mode activation/protection/gates/tasks and system-state expansion are
excluded: 0F system groups (SLDT/STR/LLDT/LTR/VERR/VERW, SGDT/SIDT/LGDT/LIDT,
SMSW/LMSW), LAR/LSL, CLTS, ARPL 63, LOADALL/STOREALL/ICE. WAIT 9B, ESC D8–DF,
80287 execution and complete NPX handshake are excluded. Undocumented SALC D6,
82 aliases, shift /6 and F6/F7 /1 aliases are inventoried separately; they are
not claimed as implemented or architectural #UD. These exclusions are scope
distinctions, not case-by-case exclusions used to obtain passing results.

No 386 operand/address-size prefixes or architectural extensions, chipset/BIOS
glue, MiSTer machine integration, full native pin timing or Accurate/Fast/Max
profile is introduced. Functional dependencies remain mandatory.

## Ownership and completion

Existing architectural GPR/FLAGS and segment/cache storage, operand/EA service,
stack arithmetic, event controller, fetch queue and BIU remain authoritative.
The microsequencer remains generic. Human-readable microcode is authoritative;
format growth must preserve historical compiler fixtures and independent active
audits. No generated artifact is edited by hand.

Byte operands use AL/CL/DL/BL/AH/CH/DH/BH encoding independently of word-register
selection, preserving the opposite half on writes. The BIU snapshots width,
space, address and write data at logical acceptance; each physical READY edge
belongs to exactly one code, memory, I/O or INTA transaction. A paused consumer
does not resubmit its pending request. A20 remains a CPU-side physical bit.

Far transfers stage sources and return context before stack writes that can
alias them, then commit CS/cache/IP through the established redirect/drain
contract. Partial stack/multiword effects must follow evidence for the exact
form. Existing POP SP+2 before destination fault and owed-TF before next-opcode
fault behavior are retained.

See `PHASE7_RESTART_CONTRACT.md` for iteration boundaries and open new research
items. Required behavior is not waived by listing an unresolved implementation
question there.

## Evidence dependency and validation

| Scenario | Evidence dependency |
|---|---|
| Ordinary successful scalar/string/I/O architectural result, no competing event | Independent of the three Phase 6 questions |
| Fault from any new form with TF=1 | `fault-tf`; selected no-new-trap policy, independent fault/frame/write invariants still required |
| STI with old IF=1 followed by a new form | `sti-old-if`; recorded transition-only policy |
| IRET fault with queued NMI during a new-form interaction | `failed-iret-nmi`; release-on-attempt policy |
| SS-load inhibition, REP stepping/restart, I/O read side effects | New Phase 7 semantics requiring their own evidence; not covered by the waiver |

Preserve the unique inherited cohort (474,049), its 440,574/1,423/32,052
subcohorts and 43,951 individually identified prefix exclusions. Reassess every
old prefix exclusion; admit supported complete cases with disjoint identities.
Full required new families include their prefixes and exception outcomes. Full
acceptance has zero selection skips, unexplained failures or missing files.

Required validation includes independent models and compiler audits, Verilator
lint, affected benches in both simulators, complete legacy and newly admitted
physical cohorts, parser/mask/EXCP/provenance accounting, lifecycle/stream/restart
and exact port/bus scoreboards, all inherited and new mutations/comparator
negatives, traces, Yosys and regression. The final fresh `phase7-check` may emit
a development pass only after all required forms/checks pass. Architectural
evidence status and independent review remain separately reported.
