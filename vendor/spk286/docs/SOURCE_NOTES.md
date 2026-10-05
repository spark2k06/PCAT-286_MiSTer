# Reference and License Notes

Current Phase 7 integration uses ordered microcode formats 15/16/17 (100 entries,
612 words), shared CPU owners and the D-037 functional acceptance contract.
See [PHASE7_FUNCTIONAL_POLICY.md](PHASE7_FUNCTIONAL_POLICY.md),
[PHASE7_MEMORY_STRINGS.md](PHASE7_MEMORY_STRINGS.md), [PHASE7_IO.md](PHASE7_IO.md)
and [PHASE7_EMULATOR_REFERENCE.md](PHASE7_EMULATOR_REFERENCE.md). Earlier
increment counts and pending inventories below are historical snapshots.

SPK286 uses references for evidence and engineering ideas. No RTL, microcode,
generated source, or substantial implementation fragment from these projects
was copied into this repository during Phase 0.

| Source | License observed | Use in Phase 0 |
| --- | --- | --- |
| Intel 80286 manuals, [Bitsavers archive](https://www.bitsavers.org/components/intel/80286/) | Historical vendor documentation; use as architectural evidence | Reset state, 24-bit bus, 286 scope |
| [SingleStepTests/80286](https://github.com/SingleStepTests/80286) | MIT; repository `LICENSE` checked | Hardware-derived future functional/bus/cycle oracle |
| [dbalsom/moo](https://github.com/dbalsom/moo) | MIT; repository metadata checked | MOO 1.1 chunk format used by the independent reader |
| Local `MCL86_BoggerMann` sources | SPDX MIT headers in inspected files | 8086 microsequencer/BIU ideas only; no code reused |
| [MCL86](https://github.com/MicroCoreLabs/Projects/tree/master/MCL86) | Root license was not assumed; per-file review required | Reference-only microsequencer and EU/BIU separation |
| [S80186 / 80x86](https://github.com/jamieiles/80x86) | GPL-3.0 repository metadata checked | Organization, verification, and Cyclone V ideas only |
| [z386](https://github.com/nand2mario/z386) | Apache-2.0 repository metadata and license checked | Prefetch/decomposition/MiSTer ideas only; 386 behavior is not evidence |
| Local `PCXT_MiSTer` | GPL-3.0 root `LICENSE` checked | MiSTer/Quartus workflow and boundary reference only |
| Local `ao486_MiSTer` | BSD license for `rtl`, `ao486_tool`, and `sim` noted in file | FPGA integration reference only; 486 behavior is out of scope |

The existing project documents remain the authority for SPK286 scope. Any
future source reuse needs a new per-file license decision recorded here before
the code is copied or adapted.

## LOADALL evidence (2026-09-16)

The 80286 LOADALL source provenance, exact image layout, opcode ambiguity,
86Box comparison and validation boundary are recorded in
[LOADALL_EVIDENCE.md](LOADALL_EVIDENCE.md). The implementation is an
independent SPK286 service; no 86Box or other emulator source was copied.
The pinned SingleStepTests real-mode checkout explicitly excludes `0F 05` and
reserves the unreal-mode suite for future data, so it is not claimed as direct
LOADALL evidence.

The local PCem source is also used as a second bounded emulator reference for
the LOADALL differential. The executed cases, source revisions/hashes and the
two unresolved differences from the current SPK286 contract are recorded in
[LOADALL_EMULATOR_DIFFERENTIAL_20260916.md](LOADALL_EMULATOR_DIFFERENTIAL_20260916.md).

## Protected-Mode PM0 evidence (2026-09-11)

- [Intel iAPX 286 Programmer's Reference Manual, 210498-003 (1985)](https://www.bitsavers.org/components/intel/80286/210498-003_iAPX_286_Programmers_Reference_1985.pdf), sections 6.6, 7.1–7.5, 8 and 10, including tables 7-1/7-2 and figures 7-1/7-10: selector fields, 8-byte 286 descriptors, access byte, typed system descriptors, hidden caches, gates and the fixed 16-bit TSS. Consulted as architecture evidence; no source or tables copied.
- [Intel 80286 and 80287 Programmer's Reference Manual, 210498-005 (1987)](https://bitsavers.trailing-edge.com/components/intel/80286/210498-005_80286_and_80287_Programmers_Reference_Manual_1987.pdf), section 10.4, p. 10-6 (PDF p. 281): reset `MSW=FFF0h`, `IDTR.base=0`, `IDTR.limit=03FFh`; section 10.3 and figures 10-1/10-3: 24-bit table bases and 16-bit limits. This is the PM0 reset policy.
- [Intel 80286 Hardware Reference Manual, 210760-002 (1987)](https://bitsavers.trailing-edge.com/components/intel/80286/210760-002_80286_Hardware_Reference_Manual_1987.pdf), table 3-6: independently records reset system state and conflicts with the programmer manual on the IDTR limit. PM0 records the discrepancy and does not use IDTR for execution; resolution remains required before PM3.
- The PM0 RTL and tests are independent project-owned implementations. No external RTL, microcode, descriptor table or reference-core source was copied.

## Phase 1 evidence

No external RTL or microcode was reused. Intel manuals were downloaded to
ignored `build/references/` for text and visual inspection, not redistributed.

- [80286 Hardware Reference Manual, 210760-002 (1987)](https://bitsavers.trailing-edge.com/components/intel/80286/210760-002_80286_Hardware_Reference_Manual_1987.pdf),
  pp. 3-65 and 3-67, table 3-6 (PDF pages 115 and 117): visible segments,
  24-bit bases, 16-bit limits, FLAGS/IP reset and valid/privilege fields. The
  reset table was also visually inspected. It does not specify GPR values.
- [80286 and 80287 Programmer's Reference Manual, 210498-005 (1987)](https://bitsavers.trailing-edge.com/components/intel/80286/210498-005_80286_and_80287_Programmers_Reference_Manual_1987.pdf),
  sections 2.3 and 10.4: register roles, flag fields and reset state. FLAGS
  storage preserves the reserved positions' reset representation; per-instruction
  reserved/system-bit behavior remains separate work.
- The same programmer manual, Appendix C, p. C-3 (PDF page 329), explicitly
  specifies 16-bit offset plus 24-bit base in both modes and external A20
  handling. This resolves the misleading "20-bit" shorthand in section 5.1;
  it must not be used to truncate CPU address arithmetic.
- The manuals disagree on IDTR reset limit (hardware table 3-6: FFFF;
  programmer section 10.4: 03FF). IDTR is outside this milestone and no choice
  is implemented. Resolve with further Intel errata/physical evidence before
  adding system state. Their reset timing descriptions also differ; this
  milestone does not claim pin-cycle timing.
- [Intel, Undocumented iAPX 286 Test Instruction (undated)](https://docs.pcjs.org/manuals/intel/80286/80286_LOADALL.pdf),
  pp. 1 and 3: independent hidden base/limit/access state; 24-bit base, 8-bit
  access with a validity bit, 16-bit limit; ordinary real-mode reload. Used only
  as architectural evidence, no instruction or source reused. Do not generalize
  this milestone to arbitrary LOADALL-modified state without hardware tests.
- Programmer manual section 5.1 defines the normal real-mode access contract;
  section 6.4 and table 7-1 define segment descriptor fields. SPK286's canonical
  cache access value 93 is documented in D-008 and is not physical dump evidence.

## Phase 2.75 evidence

The Intel 80286/80287 Programmer's Reference Manual, 210498-005 (1987),
p. 8-73 (PDF page 281, linked above), was read and visually checked for MOV.
It defines `B8+rw dw` as an immediate word transfer to a word register and
specifies no modified or undefined FLAGS. The scanned text's OCR confuses
several `8`/`B` opcode digits; the rendered table confirms the encoding.
Its timing column is not used to pad the functional microcode.

The unchanged pinned SingleStep corpus was inspected for B8/BF examples and
executed across all B8..BF cases before migration: 40,000 passed, zero failures.
Its little-endian instruction bytes, sparse final state and HALT-inclusive IP
agree with the existing adapter contract. No expected values were changed.
The compiler, generated microcode and execution-control implementation are
project-owned; no external CPU implementation source was reused.

## Phase 3 addressing evidence

The Intel 80286/80287 Programmer's Reference Manual, 210498-005 (linked above),
sections 2.4.3.1/2.4.3.2, table 2-2 and the ModR/M encoding tables are the
primary evidence for the independent address implementation. Offsets wrap
modulo 65536, disp8 is sign-extended, BP-relative operands use SS and direct
displacement addressing uses DS. The MOV table at B-73 confirms 89/8B, operand
direction and FLAGS preservation. Appendix B's Real Address Mode Exceptions
explains that a word at FFFF crosses to offset 10000 rather than wrapping its
second byte. The downloaded manual remains ignored under `.cache/intel286`.
No external RTL, microcode or CPU implementation was reused.

The pinned 89/8B hardware captures independently include exception 13 for
word operands at offset FFFF (for example, 89 index 520 and 8B index 536).
These are diagnostic evidence for the general bound check, never RTL case
identifiers. Delivery of those exceptions remains a later architectural phase.

## Evidencia de Phase 2.80

Las fuentes públicas MCL86 consultadas, sus revisiones, sus licencias
inspeccionadas y los hashes exactos se registran en
[research/mcl86/README.md](../research/mcl86/README.md) y
[sources.json](../research/mcl86/sources.json). Las cabeceras del TXT de Ted
Fried y del RTL original y reescrito contienen MIT; las imágenes ROM no tienen
cabecera propia. Se descargan sólo como referencias ignoradas en `.cache/`.
No se incorporan RTL, microcódigo ni tablas externas a la CPU SPK286.

La implementación independiente de assembler/disassembler/checker estudia
empaquetado, diagnóstico, determinismo, comparación exhaustiva y round-trip.
No importa la arquitectura, el dispatch, la latencia síncrona de ROM, los
marcadores de micro-PC ni el timing de MCL86. La comparación demuestra igualdad
con la ROM original v4 y 431 diferencias con la ROM de la reescritura; ambas
ROMs completan un round-trip sin pérdida de palabras. Esto no demuestra
equivalencia arquitectónica entre MCL86 y SPK286 ni corrección ISA de MCL86.

## Phase 4 ALU/FLAGS evidence

Intel 210498-005, table 3-1 (3-6), sections 3.3.1/3.3.2, and Appendix B's
ADD/ADC, AND, CMP, OR, SBB, SUB and XOR descriptions define the word ALU contract.
The cached programmer.pdf hash remains
ad487ba99b48cd9f61b14c0fe912a04c7cdb4c7c14a18419aa9faf62d8962460.
CF means carry or borrow; SBB subtracts incoming CF. Signed range defines OF;
AF reflects nibble carry/borrow. Table 3-1 explicitly defines PF as even parity
of the low eight bits and resolves section 2.3's reversed prose. Arithmetic
updates all six status flags; logic clears CF/OF, derives PF/ZF/SF and leaves
AF undefined. Sign-extended word immediates are distinct from signed disp8.

All 40 selected hardware files at pinned commit
37c73caf53dcd22d3dd369ff09305d13d117a4fe were inspected. Logical records supply
mask F7EE and captured AF=0; the mask is retained exactly. AF=0 is not promoted
to an ISA guarantee. Directed tests check CF/OF independently because the
upstream mask omits them. The mathematical model and RTL are project-owned;
no external CPU implementation or microcode was copied. External vectors and
manuals remain ignored. See PHASE4_SCOPE for exact forms and policy.

The [MOO 1.1 specification](https://github.com/dbalsom/moo/blob/main/doc/moo_format_v1.md)
defines RMSK register-presence bits and little-endian mask values, at file or
final-state scope. The pinned 80286 moo2json converter omits RMSK, so the release
audit separately reads these wire fields without reusing production parsing.
Its fixture/negative tests reject missing or changed masks; the corpus and
production reader remain unchanged. This closes an audit coverage gap exposed
by the new logical families, not a CPU or hardware-expectation defect.

## Phase 5 stack and near-control evidence

Intel 80286 Programmer's Reference Manual, Appendix B: PUSH B-87/B-88,
POP B-83/B-84, CALL B-23 onward, JMP B-56 onward, RET B-94 onward, and the
Jcc/LOOP instruction definitions establish word/SP ordering, architectural
next-IP relative targets, near returns and condition/count behavior. The
cached manual hash is
`ad487ba99b48cd9f61b14c0fe912a04c7cdb4c7c14a18419aa9faf62d8962460`.
PUSH SP stores original SP on the 80286; POP SP loads the popped destination
over the intermediate increment. No 8086 PUSH SP convention was imported.

The unchanged pinned physical corpus independently confirms these semantics.
Its README documents HLT injection at control-transfer destinations and final
IP after HLT. Before implementation, independent arithmetic matched 122,694
admitted Jcc/LOOP/relative CALL/JMP/RET target records and all 4,860 admitted
POP SP destination records. These research comparisons are evidence, not a
substitute for executing the complete admitted corpus against SPK286.
No external CPU implementation or microcode source was reused.
# Phase 6 evidence addendum

The Phase 6 source inventory, hashes, event ordering adjudications and primary
links are in [INTERRUPTS_EXCEPTIONS.md](INTERRUPTS_EXCEPTIONS.md). The correct
hardware reference is Intel 210760-002 **1987**; the B-2/B-3 Information Sheet is
dated **21 November 1984**. Older mistaken draft dates/URLs are superseded.

Physical provenance remains the clean pinned Harris N80C286-12 capture set at
`37c73caf53dcd22d3dd369ff09305d13d117a4fe`. It resolves invalid 8F #UD and the
SP+2 effect of 8F destination-limit faults, but does not exercise TF/IF delivery,
READY variation or arbitrary prefetch streams. It cannot adjudicate failed-IRET
NMI inhibition or the old-IF STI qualifier. The conflicting fault/TF passages
remain explicit in [the independent review](PHASE6_ARCHITECTURAL_REVIEW.md).
No external CPU implementation or microcode was copied into the production core.

## Phase 6 evidence-closure research

[PHASE6_EVIDENCE_CLOSURE.md](PHASE6_EVIDENCE_CLOSURE.md) records newly inspected
Intel 210498-001 (1983) and Doc.1634c C-2 (21 November 1984), original artifact
hashes, page images, narrow correction scope and remaining competing hypotheses.
Additional 210760-002 NMI pulse/clock and INTR lead-time passages constrain the
physical experiments but do not resolve the three architectural policies.

ArduinoX86 fixture source was inspected at
`2ccae6470ef2cc12e247b74e3ad2d226b7f74936` for interface capabilities only. Exact
URLs/hashes are retained in ignored `build/phase6-evidence-closure/fixture-sources`.
No ArduinoX86 source was copied into the new project-owned assembly, bounded
mechanics interpreter or result parser. No new physical captures were obtained.
Downloaded scans/source stay ignored and are not redistributed with the portable
capture package. The malformed 1987 programmer-manual hash in the event contract
was corrected against the original; it is a documentation-only correction.

The user's emulator question prompted a pinned inspection of 86Box
`62c26bac3050808ca8fec2c93e14fb678ac0a9ad` and wfeldt/libx86emu
`ce81129c57fdfbf690bebc210a8db97d926cc5e7`. The dossier distinguishes their
implementation choices from physical evidence. In particular, the inspected
86Box STI delay is unconditional and renewing; this differs from SPK286's
provisional transition-only policy. Source hashes and the independent emulator
review are preserved in recovery evidence. No external implementation was run,
copied or used to override the unresolved architectural evidence gate.

## Phase 7 byte/prefix and I/O research (2026-09-08)

Primary semantic sources remain Intel 210498-005 (1987 programmer reference;
SHA256 `ad487ba99b48cd9f61b14c0fe912a04c7cdb4c7c14a18419aa9faf62d8962460`)
and 210760-002 (1987 hardware reference). Relevant passages include byte
registers and arithmetic FLAGS; Appendix B instruction encodings; the corrected
ten-byte instruction limit; LOCK B-68; MOV B-73; OUT B-81; REP B-92–93; and
hardware section 2's lock/arbitration description. The local primary scans and
extracted text remain ignored, with their existing provenance retained.

The complete pinned physical inventory is 326 files and 1,478,000 records at
`37c73caf53dcd22d3dd369ff09305d13d117a4fe`; the explicit Phase 7 inventory
requires 307 files and excludes 19. The current 150-file increment readmits all
old prefix cases without changing original bytes, RAM or expected results.
A physical overlength immediate ALU case showed that instruction bytes must be
acquired before requesting data memory; the core now respects that fault order.

ED/EF and INS/OUTS captures independently show A16 carrying on the second
physical half of an odd word I/O at port FFFF. Scalar I/O's prototype compares
latched Ts address/lane and completed Tc data, with an independent FF responder.
An exhaustive scan of its eight source files found one incomplete IOW capture
in E7 (hash `c56d37647cc2dbcce82ca640fdd25ddea1f3ee5e`). Upstream parsing agrees
and the hash is not revoked; no repair or local exclusion was applied.
See [the reduced evidence](PHASE7_IO_CAPTURE_REVIEW.md).

The [pinned corpus methodology](https://github.com/SingleStepTests/80286/blob/37c73caf53dcd22d3dd369ff09305d13d117a4fe/README.md)
describes potential missing cycles from capture errors and the upstream
revocation mechanism. That is a possible explanation, not proof of this anomaly's
cause. New REP/SS-load/event obligations are explicit in the
[restart contract](PHASE7_RESTART_CONTRACT.md); no inherited evidence waiver
automatically resolves them. No external CPU implementation was copied.

### Direct scalar and TEST evidence

Intel 210498-005 Appendix B specifies CBW (B-27), CWD (B-35), DEC (B-38),
INC (B-46), LAHF (B-59), SAHF (B-96), and TEST (B-110), plus the CLC/STC/CMC
and CLD/STD entries. TEST's definition clears CF and OF; the chapter-3 OCR
rendering that reads DF is contradicted by the original instruction entry and
physical outcomes. INC/DEC preserve CF; SAHF modifies only five status flags.
LAHF reserved bits are described as indeterminate; this implementation retains
the existing register owner's low FLAGS representation, with the physical
corpus masks unaltered. Full pinned scalar files provide 63,000 independent
captures; no physical count is inferred from a directed model.

### Shift/rotate flags and zero count

Intel 210498-005 Appendix B B-90/B-91 and B-97/B-98 supplies the masked-count,
rotation and shift semantics. The 42 pinned files contain 210,000 independent
physical records. The [shift decision](PHASE7_SHIFT_FLAGS.md) separates Intel
defined/preserved bits from deterministic choices for undefined OF/AF, records
the original failed run, and links the 90,000-record independent mask analysis.
Zero-count memory captures retain reads and limit faults without data writes.
No corpus expectation, mask or revocation was changed.

### Data-transfer forms

Intel 210498-005 Appendix B B-63 (LEA), B-114 (XCHG), B-115 (XLAT) and the MOV
entries define the data-transfer forms. Intel 210760-002 table 3-3 specifies
implicit LOCK for memory XCHG. The sixteen pinned files contain 48,000 records,
including 1,280 register-source LEA #UD and 34 word-limit XCHG #GP captures.
All are included without changing bytes, masks or expected values. The isolated
prototype passed the full cohort; integrated status is in PHASE7_HANDOFF.md.

### Unary arithmetic

Intel 210498-005 Appendix B B-38, B-46, B-77 and B-79 define DEC, INC, NEG and
NOT. Independent integer/address calculations matched all 39,868 non-fault
records in eight complete pinned files. The full 40,000-case prototype RTL run
also passed 132 word-limit faults. Five affected prior TEST/near-control files
passed 25,000 additional records, already included in the inherited cohort.
No expected result, mask, revocation or source byte was changed.

Adjustment semantics use Intel 210498-005 Appendix B B-15 through B-18 and
B-36/B-37. Pinned physical D4/D5 captures provide nondecimal-radix evidence;
all eleven zero-radix D4 cases provide unmasked saved FLAGS bytes. The latter
policy is explicitly observational and leaves the three Phase 6 questions
pending. PHASE7_DECIMAL_ADJUST.md and its adjacent identity file record the
arithmetic/reference calculations and retained failed verification runs.

### Segment transfers and SS protection

Intel 210498-005 Appendix B MOV B-73 and POP B-83 define legal 286 segment
indices and protection through the instruction following an SS load, including
NMI. All 45,000 records from 06/07/0E/16/17/1E/1F/8C/8E were compared, including
1,481 #UD and 131 #GP outcomes. Initial IF/TF are clear in this cohort; these
records do not independently establish interrupt inhibition. The directed
event tests and physical cache/data evidence remain separate. Identities and
integer-model observations are in phase7_segment_observations.json.

### Stack frames and signed bounds

Intel 210498-005 Appendix B BOUND B-22, ENTER B-40/B-41, LEAVE B-64,
POPA B-85 and PUSHA B-88 are the primary instruction definitions. Independent
raw bus/final-memory comparisons refine ENTER fault write survival and the
BOUND FFFE/0000 even wrap. The original contrary assumptions and failed runs
are preserved; the corpus and its existing C8 revocation were not changed.
See PHASE7_STACK_FRAME.md and phase7_stack_frame_observations.json. No 386
operand/address size or historical timing behavior was inferred.

## Far transfers — Phase 7 candidate

Intel 210498-005 sections 3.6/3.8 and Appendix B CALL/JMP/RET/LDS/LES define the
pointer and return-frame contracts. Pinned SingleStepTests/80286 revision
37c73caf53dcd22d3dd369ff09305d13d117a4fe supplies all 40,000 records in C4/C5,
9A/EA, CA/CB and FF /3,/5, including invalid register forms and fault frames.
No source capture, register/memory expectation or revocation was edited. The
275-file independent parser audit and observation hashes are recorded in
PHASE7_FAR_TRANSFERS.md and phase7_far_observations.json.
