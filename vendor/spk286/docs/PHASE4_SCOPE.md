# Phase 4 scope and implementation contract

Base: `e040229ad4e363a833f9dc74b414cdb2217cf664`, independently reviewed
Phase 3. Work branch: `codex/phase4-alu-flags`.

## Scope reconciliation before implementation

The SPEC's broad milestone numbers are not the incremental delivery phases
(D-007). SPEC's dependency roadmap and REALMODE_MVP sections 11 and 39 place
basic ALU/FLAGS after MOV/addressing and before stack/control flow. Neither
requires the entire real-mode ISA in this incremental phase. The instruction
matrix currently admits only word MOV. The Phase 4 task explicitly calls for
reusable word arithmetic/logical operations and defers byte operands.

Admit the following unprefixed 16-bit forms, including register-direct and
memory ModR/M operands. Each row has five hardware corpus files:

| Family | r/m16,r16 | r16,r/m16 | AX,imm16 | r/m16,imm16 | r/m16,sign-extended imm8 |
| --- | --- | --- | --- | --- | --- |
| ADD | 01 /r | 03 /r | 05 iw | 81 /0 iw | 83 /0 ib |
| OR | 09 /r | 0B /r | 0D iw | 81 /1 iw | 83 /1 ib |
| ADC | 11 /r | 13 /r | 15 iw | 81 /2 iw | 83 /2 ib |
| SBB | 19 /r | 1B /r | 1D iw | 81 /3 iw | 83 /3 ib |
| AND | 21 /r | 23 /r | 25 iw | 81 /4 iw | 83 /4 ib |
| SUB | 29 /r | 2B /r | 2D iw | 81 /5 iw | 83 /5 ib |
| XOR | 31 /r | 33 /r | 35 iw | 81 /6 iw | 83 /6 ib |
| CMP | 39 /r | 3B /r | 3D iw | 81 /7 iw | 83 /7 ib |

The pinned corpus tree contains all 40 files, 5,000 records each. Discovery is
not execution or admission. Prefixes and exception delivery remain excluded
with separate exact accounting. All inherited B8..BF/89/8B cases remain required.
Byte instructions, TEST, unary INC/DEC/NEG/NOT, flag-control instructions,
shifts, stack and later phases are not admitted. TEST is conditional in the
task and not explicitly assigned to this phase by the project documents.
CMP supplies the required no-write operation; the mechanism will also serve
TEST when its opcode family is deliberately admitted.

## Intended ownership

- One pure word ALU owns seven functional operations: ADD, ADC, SUB, SBB,
  AND, OR, XOR. It receives A, B and carry/borrow input and emits a result and
  candidate flags, without opcode, micro-PC, operand or bus interpretation.
- Instruction decode resolves ALU operation, result-write permission and
  defined/undefined flag masks from the captured opcode and captured group
  extension. CMP selects SUB and suppresses result writeback.
- Executor TMP0 is A (original destination), TMP1 is B (source), and TMP2 is
  the result. The executor also holds candidate flags until explicit commit.
  Register/memory access still belongs to the existing operand service.
- Five shared microprograms express the five form columns above. Decoded
  semantic controls parameterize the ALU and conditional result write, never
  the generic microsequencer. FLAGS commit follows completed result writeback;
  CMP commits flags after discarding the result. END retires exactly once.
- Reset, redirect and instruction start clear temporary and pending flag state.
  Pause holds semantic state; READY and operand/byte availability remain real
  dependencies. The Phase 3 non-rollback cancellation contract is unchanged.

## Flag evidence and policy

Intel 210498-005, table 3-1 (printed 3-6), sections 3.3.1/3.3.2 and Appendix B
ADD/ADC, AND, CMP, OR, SBB, SUB and XOR define the arithmetic contract. CF is
unsigned carry or borrow; ADC adds incoming CF and SBB subtracts it. OF reports
a signed result outside -32768..32767. AF is nibble carry/borrow, and PF is
even parity of only the low eight result bits. Table 3-1 resolves the reversed
PF wording in section 2.3's prose; hardware-derived evidence must agree.

Arithmetic updates mask `08D5` (CF/PF/AF/ZF/SF/OF). Logic updates `08C5`,
clearing CF/OF and deriving PF/ZF/SF; AF is architecturally undefined (`0010`).
The chosen undefined policy leaves stored AF unchanged rather than making it
an architectural output of logical computation. This is not a guarantee that
all physical 286 parts preserve AF. Unrelated FLAGS retain their existing
storage contract; there is no second architectural FLAGS register.

The pinned logical captures supply FLAGS comparison mask `F7EE`: they omit
CF, AF and OF. Preserve that upstream mask exactly. Independent directed and
reference-model checks must therefore verify defined logical CF=OF=0, as well
as defined arithmetic flags and preservation. Captured logical AF=0 is not
promoted into an ISA guarantee or used to override the upstream mask.

Primary source is the cached, previously verified Intel programmer manual
`.cache/intel286/programmer.pdf` (SHA-256
`ad487ba99b48cd9f61b14c0fe912a04c7cdb4c7c14a18419aa9faf62d8962460`),
with its text extraction, and the unchanged SingleStepTests/80286 commit
`37c73caf53dcd22d3dd369ff09305d13d117a4fe`. No external CPU source is reused.
