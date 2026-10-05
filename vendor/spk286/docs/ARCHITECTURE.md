# SPK286 Architecture

Current Phase 7 integration uses ordered microcode formats 15/16/17 (100 entries,
612 words), shared CPU owners and the D-037 functional acceptance contract.
See [PHASE7_FUNCTIONAL_POLICY.md](PHASE7_FUNCTIONAL_POLICY.md),
[PHASE7_MEMORY_STRINGS.md](PHASE7_MEMORY_STRINGS.md), [PHASE7_IO.md](PHASE7_IO.md)
and [PHASE7_EMULATOR_REFERENCE.md](PHASE7_EMULATOR_REFERENCE.md). Earlier
increment counts and pending inventories below are historical snapshots.

Phases 4 and 5 extend this foundation with ALU/FLAGS and stack/near-control services documented below.

## Inherited Phase 3 boundary

`spk286` connects architectural register storage, visible/hidden segment state,
the READY-gated fetch service, a six-byte instruction queue, decoder, generated
microcode ROM, generic microsequencer, logical operand service and shared BIU.
The reset/fetch proof from Phase 0 and the architectural
state foundation from Phase 1 are preserved. All eight word GPRs and their byte
aliases, IP, FLAGS storage, and four segment caches have functional datapath
read/commit interfaces. See [STATE_INTERFACE.md](STATE_INTERFACE.md) for the
Phase 1 storage contract.

`spk286_fetch` holds one outstanding transaction and one response. Its cursor
advances when data arrives; architectural IP advances only when the frontend
consumes an instruction byte. Control transfers coordinate CS/IP updates,
queue flush and fetch restart. Stale in-flight reads are drained and discarded.
`spk286_prefetch_queue` stores six ordered bytes and supports simultaneous
consumption/refill without exposing stale data after a redirect.

`spk286_decoder` recognizes `B8..BF`, `89` and `8B`, selecting the generated
MOV entry and, for immediate MOV, destination `opcode[2:0]`. Opcode consumption atomically
latches the destination and starts `spk286_microsequencer`. The sequencer holds
micro-PC/entry and exposes the current operation until it completes. It knows
neither x86 opcodes nor register encoding. Invalid entries/ROM words and
fallthrough beyond ROM latch `microcode_fault` without retirement.

`spk286_micro_executor` implements `FETCH_IMM16 -> TMP0` with two ordered byte
handshakes. A partial low byte survives queue starvation or an execution pause;
the micro-PC advances only when the high byte is accepted. `TMP0 -> DST` writes
the full word through the register commit port. The following generated `END`
produces one retirement pulse and releases decode. No FLAGS write is generated.
The old instruction-specific MOV FSM has been removed.

Unsupported opcodes latch a development-only indication and remain unconsumed.
`execute_enable` separates autonomous execution from the Phase 1 state-vector
setup controls. There is no ALU, prefix execution, exception delivery,
descriptor loader or protected-mode activation.

## Protected-Mode PM0 foundation

The PM0 foundation is documented in [PROTECTED_MODE_PM0.md](PROTECTED_MODE_PM0.md).
`spk286_selector`, `spk286_descriptor` and `spk286_protected_state` implement
selector decomposition, typed 80286 descriptor candidates, table-limit
arithmetic and protected-state commit storage. PM1a/PM1b/PM1c/PM1d/PM1e/PM1f/PM1g now connect the live
decoder/microcode/BIU path for `SGDT`, `SIDT`, `LGDT`, `LIDT`, `SMSW`, `LMSW`,
`SLDT`, `STR`, `LLDT`, `LTR`, `VERR`, `VERW`, `LAR`, `LSL`, `ARPL` and `CLTS`.
The bounded PM1 contract is recorded in
[PROTECTED_MODE_PM1.md](PROTECTED_MODE_PM1.md).

The first PM2 slice connects protected `MOV Sreg,r/m16` reloads for DS, ES and
SS to the descriptor service. GDT and LDT selectors are range-checked before
the ordered descriptor reads; null DS/ES loads, descriptor privilege/type
rules, present faults and the descriptor accessed-bit write are handled before
one atomic hidden-cache commit. While PE is set, the selected protected cache
supplies the logical-to-physical base/limit/access translation, and a complete
word access is rejected before the BIU request when its type or limit is
invalid. The follow-on PM2b slice adds protected CS validation for the
existing direct far-transfer protocols, including candidate cache latching,
conforming/non-conforming privilege checks, accessed-bit writeback and atomic
CS/IP/prefetch redirect commit. PM3a–PM3d
add bounded protected event gates, external events, error frames and outer
IRET; PM3e adds outer-level event entry through TSS-selected stacks, and PM2e
extends the data, event, call-gate and outer-return paths with expand-down
limits. Task gates, task switching and the remaining full-fault policy remain
deferred. See
[PROTECTED_MODE_PM2.md](PROTECTED_MODE_PM2.md),
[PROTECTED_MODE_PM2B.md](PROTECTED_MODE_PM2B.md) and
[PROTECTED_MODE_PM3E.md](PROTECTED_MODE_PM3E.md),
[PROTECTED_MODE_PM2E.md](PROTECTED_MODE_PM2E.md).

### ModR/M and logical operands

`DECODE_MODRM` enables `spk286_operand_decode`. It acquires the ModR/M byte
and zero, one or two displacement bytes from the existing queue handshake.
`spk286_modrm` supplies mode, REG, RM, register-direct and displacement length.
The context holds those fields and a 16-bit displacement (signed extension of
disp8, little-endian disp16). A resolution edge captures effective offset and
segment before completing the operation; live future queue bytes cannot alter
the executing instruction. This edge stores required context, not timing padding.

`spk286_effective_address` owns the only base/index table. BX+SI, BX+DI, SI,
DI and BX default to DS; BP+SI, BP+DI and displaced BP default to SS. Direct
`mod=00,rm=110` takes disp16 alone and DS. Offset arithmetic wraps at 16 bits.
The existing segment-cache read/translation port selects that context during
execution; physical address remains cached base plus offset on a 24-bit path.
The external setup address query retains its original meaning when paused.

`spk286_operand` selects REG or RM through one word-register mux over the
actual architectural register state. Register accesses complete locally;
register writes use the existing commit port. Memory RM accesses first check
the entire word against the selected cached limit, then submit one logical
request to `spk286_biu`. A pending bit prevents duplicate submission and holds
the micro-operation until the BIU's retained response is accepted. Reads return
a word which the executor captures in its TMP0; the operand service has no
temporary-register ownership. Writes accept the executor's word input and
acknowledge completion before END can retire. Both directions
share this service. FLAGS and segments are preserved.

The BIU is the sole external bus arbiter. Accepted data words have priority at
a free physical-cycle boundary; a visible waiting code cycle retains ownership
through READY. It handles aligned/odd word lanes, response storage and physical
completion. Fetch remains a code client that owns its cursor, response metadata
and stale-stream cancellation. The six-byte queue is unchanged, and data traffic
does not flush it. See [BUS_INTERFACE.md](BUS_INTERFACE.md) for the protocol.

### Stream and retirement semantics

- `debug_ip` is the architectural next instruction byte. It advances once per
  consumed opcode, ModR/M, displacement or immediate byte; prefetch does not change it.
- `debug_fetch_cursor` is the next byte offset requested from the code bus and
  may run ahead of `debug_ip` by up to the queue capacity plus one response.
- Queue bytes are ordered low-byte first for each fetch response. A word response
  enters as `response_data[7:0]`, then `[15:8]`.
- Refill requires at least two free queue slots. This keeps the current one
  response slot lossless while still permitting consumption during refill.
- `redirect` flushes the queue and frontend, while `spk286_fetch` drains any
  obsolete in-flight bus read before issuing the new stream.
- Decode consumes one opcode. The executor consumes two immediate bytes for
  B8..BF or ModR/M plus displacement for 89/8B. Writeback and END consume no
  bytes. Instruction lengths are respectively 3 and 2/3/4 bytes.
- `instruction_retired` is a one-clock pulse after the END edge. The previous
  writeback is complete, and the next opcode has not yet been consumed. Refill
  and READY do not gate retirement. The pulse clears even if execution pauses.
- A valid redirect cancels all remaining micro-operations, including writeback
  on that edge. It does not roll back a write that completed on a previous edge.
  This is a development control contract, not a precise exception mechanism.
- An accepted data word drains on redirect, including both byte cycles of an
  odd write, but its completion is discarded. Reset aborts pending transactions.
  Neither control can undo writes already accepted by external memory.
- With `execute_enable=0`, microstate, partial bytes and operand context hold.
  Accepted data cycles may finish, and their response remains held until resume.
  Prefetch responses
  enter the FIFO only during autonomous execution, avoiding duplicate insertion
  of a response held by the setup interface. Changing architectural setup state
  requires a coordinated redirect before resuming a different stream.
- Malformed control transactions freeze semantic advancement as well as
  architectural writes; independent physical bus work may still finish.
- A word beyond the segment limit latches `operand_blocked` before a data
  request. It does not retire or issue either byte. Reset/redirect clears the
  development indication. Architectural exception delivery is deferred; a word
  at offset FFFF must never wrap its second byte to offset zero.

### Functional timing boundary

`enable` and `operation_valid/operation_done` control implementation scheduling,
not historical clocks. A future timing policy must coordinate functional
acceptance and advancement, retaining completed responses while delayed and
preventing repeated side effects. It must continue honoring READY, queue and
operand dependencies. No timing modes, counters, padding or idle micro-ops exist.
The deferred instruction/BIU/pin timing work is tracked separately in the
[Phase 9 timing-fidelity plan](PHASE9_TIMING_FIDELITY.md).

The generated four-bit control and source maps are described in
[../microcode/README.md](../microcode/README.md). Numeric `debug_micro_pc`,
`debug_micro_entry`, `debug_micro_instruction`, `debug_micro_active` and
`microcode_fault` observe the actual functional path. No source strings are
synthesized.

The reset contract exercised by both simulators is:

```text
visible CS       = F000
hidden CS base   = FF0000
IP               = FFF0
first fetch      = FFFFF0
```

The bus status value `0xD` is the 80286 `CODE` status encoding used by the
SingleStep format. `bus_bhe_n` follows the active-low physical naming used by
the 80286 bus; the first word fetch asserts it low.

## Intended future decomposition

The target architecture remains a standalone CPU with these separable areas:

```text
instruction unit / six-byte prefetch
            |
            v
decoder -> microsequencer -> execution unit
                              |       |
                              v       v
                    segmentation   exception state
                              |
                              v
                         bus interface
```

MiSTer, PC/AT chipset logic, RAM controllers, video, storage, and peripherals
belong above this boundary. Phase 4 can reuse the captured operand context,
REG/RM read/write service and BIU dependency to add arithmetic and FLAGS.
Additional temporaries and operations will require an explicit DSL extension;
they do not require duplicating addressing or physical bus sequencing.

## Phase 4 ALU and FLAGS execution

The admitted ISA is the 40 word forms in PHASE4_SCOPE.md. The initial decoder
chooses one of five ALU microprograms and sets DST=AX for accumulator forms.
spk286_alu_decode resolves operation, result-write permission, defined mask and
undefined mask from captured opcode and captured ModR/M extension. Future queue
bytes cannot alter them. CMP selects SUB and disables result writeback.

spk286_alu owns only word semantics. Encodings: ADD=0, OR=1, ADC=2, SBB=3,
AND=4, SUB=5, XOR=6. It receives A/B/carry and emits result/candidate flags.
Arithmetic explicitly uses 17 bits. SUB/SBB CF means borrow, including the
B=FFFF/borrow=1 boundary. OF uses operand/result sign relations; AF uses bit-4
carry/borrow; PF is low-byte even parity; ZF/SF describe the word result.

The executor owns TMP0=A (original destination), TMP1=B (source), TMP2=result,
three valid bits, candidate FLAGS and a pending mask. Five shared microprograms
acquire operands, compute, dispose of the result, commit FLAGS, then END.
IF_WRITE writes only when decode permits; otherwise it consumes the result
without register or bus write. That is functional CMP disposition, not timing
padding. FLAGS commit follows the complete logical write, including both odd
subcycles. Architectural FLAGS remain solely in spk286_registers.

Arithmetic updates 08D5; logic updates 08C5 with undefined mask 0010. The
pending effective mask excludes undefined bits. Logic clears CF/OF and preserves
stored AF as an explicit undefined-value policy, not a physical-CPU promise.
Control/system and reserved bits retain their storage contract. The corpus's
logical F7EE mask is unchanged; directed tests verify CF/OF independently.

FETCH_IMM16 to TMP1 consumes low then high bytes; FETCH_IMM8S to TMP1 consumes
one byte and sign-extends independently of displacement handling. Both hold
on missing bytes. Reset, redirect and instruction start clear temporary/valid/
pending state. Pause or malformed controls inhibit semantic acceptance;
accepted BIU work may complete into a held response. Redirect retains the
inherited drain/non-rollback contract: prior GPR/FLAGS or external writes are
not undone. Precise exception rollback remains deferred.

Phase 3 operand, ModR/M, EA, register/segment storage, BIU, fetch, queue and
microsequencer RTL are unchanged. Format 3 uses five-bit controls and eight
entries in 45 ROM words with six-bit addresses. The first eleven MOV words and
entries are unchanged. Phase 5 can reuse acquisition, ALU, masks, routing and
writeback; new constants/selectors can extend these interfaces without replacing
their owners. No Phase 5 instruction or timing policy is implemented.

## Phase 5 stack and near control flow

`spk286_stack` is the shared combinational stack address/SP arithmetic service.
It reads the authoritative SP in `spk286_registers`, produces SS:SP or
SS:(SP-2), and enables SP writeback only after the existing operand service
completes the logical word. Explicit stack release uses the same adder.
There is no shadow stack pointer, second operand FSM, or physical stack bus.
`spk286_operand` adds a validate-only request: POP's RM destination is checked
before reading the stack, so an invalid destination cannot partially advance SP.
The existing 17-bit whole-word limit check remains authoritative.

The executor captures PUSH sources before SP changes. POP first consumes the
stack response and commits SP+2, then writes its destination; POP SP therefore
loads the popped word over that intermediate increment. CALL rel16 explicitly
reads architectural next IP into TMP0. Indirect CALL selects architectural next
IP as its push source after capturing the indirect target. Neither uses the
speculative fetch cursor. RET captures its popped target before optional
unsigned stack release. Near transfers preserve CS and all FLAGS.

`spk286_condition` owns the sixteen flag predicates; `spk286_control_decode`
turns captured opcode/ModR/M metadata into functional selectors. LOOP decrements
CX in an explicit COUNT operation before deciding the branch; JCXZ preserves CX.
The executor holds one candidate target and validity bit, computes relative
addition modulo 65536, and issues a conditional REDIRECT operation.

Internal REDIRECT is accepted at the edge that writes IP and flushes the
six-byte queue/restarts `spk286_fetch`. It advances the owning microprogram to
END. It is intentionally separate from the external development redirect,
which cancels the sequencer, executor, operand decoder and logical data service.
The unchanged fetch owner drains/discards outstanding old code responses before
issuing replacement traffic. END may retire while that drain is still pending;
no new instruction can consume the discarded stream. Not-taken branches issue
no redirect and preserve queued bytes.

The microsequencer, BIU, fetch, queue, register file, segment caches and EA
algorithm are unchanged. Physical READY and odd-word dependencies remain real
in every future timing mode. These primitives support future serialized
interrupt/exception entry without implementing its vectoring, FLAGS frame,
CS changes, INTA, IRET or fault delivery in this phase.

## Phase 6 candidate extension

`spk286_events` owns event qualification, start CS:IP, sampled TF, pending NMI,
NMI inhibition, STI shadow, halt/shutdown and saved event context. Its dispatch
starts `EVENT_ENTRY`; it does not write the architectural register file or own
a second stack bus. The generic microsequencer remains unaware of x86 events.
`INTERRUPT_RETURN` stages three ordered stack reads before one CS/cache/IP/FLAGS
installation. The existing segment-cache owner performs normal Real Mode reload.

The BIU arbitrates code, operand data and acknowledgement owners. Accepted words
and acknowledgements drain through READY even when functional execution pauses;
responses remain owned until consumed. Entry discards stale instruction bytes,
then installs the vector context and redirects through the existing fetch owner.
No extra instruction timing padding or profile is introduced.

The Phase 5 POP-memory precheck is superseded: the pinned 286 destination-fault
captures require a completed POP/SP+2 before the destination #GP. Microcode format
5 removes that single precheck; normal inherited forms remain unchanged.
See [the event commit matrix](INTERRUPTS_EXCEPTIONS.md) and
[open architectural findings](PHASE6_ARCHITECTURAL_REVIEW.md).

## Phase 7 byte/prefix increment

`spk286_instruction_context` owns prefix accumulation, the consumed-byte count
and context lifetime. `spk286_events` captures restart state at the first byte,
while final opcode dispatch preserves the existing STI/IRET policy selectors.
The implementation has no REP iteration engine yet. `repeat_kind` is retained
for future functional use and is ignored for current non-string forms.

The existing register file remains the only GPR/FLAGS owner. Operand width flows
through executor, operand service and BIU; byte access at segment offset FFFF is
legal, while a word at FFFF still faults before either lane. An immediate-form
ALU now finishes instruction-byte acquisition before its operand read, which
makes overlength #GP precede data access.

The isolated scalar-I/O prototype is not integrated; see
[PHASE7_IO_CAPTURE_REVIEW.md](PHASE7_IO_CAPTURE_REVIEW.md). No machine devices,
protected-mode state or Phase 8 implementation were added.

## Phase 7 direct scalar and TEST increment

The instruction decoder captures source and destination GPR selectors separately;
CWD reads AX and writes DX, while the inherited mappings remain identical. A small
flag metadata decoder supplies candidates/masks for CLC/STC/CMC, CLD/STD and SAHF.
The shared executor and register file retain all architectural commit authority.
LAHF uses a flags read and the existing high-byte write. CBW/CWD transform a
temporary, and register INC/DEC use the shared ALU plus a real constant operand.
TEST reuses the six existing ALU entry shapes with AND and no result writeback.
No second x86 decoder is added to the microsequencer or executor.

## Phase 7 shift/rotate increment

The generic shift service snapshots kind, operand, count, width and carry, and
returns a result, FLAGS candidate/mask and write disposition. It owns only
transient arithmetic state. The existing executor handles acquisition, result
disposal and commit; the BIU remains the only physical bus owner. Count zero
still reads/checks memory but suppresses writeback. Every busy step computes
a real bit operation; microcode length is not a historical timing model.

## Phase 7 data-transfer increment

Direct MOV and XLAT reuse the operand service through a transient offset
selector. LEA reads the operand decoder's effective offset without a memory
request. Typed executor controls exchange captured values through the existing
register owner; memory XCHG commits the memory write before its register write
and requests implicit LOCK through the BIU. Source/target selectors distinguish
AX from its partner without introducing another architectural register copy.
See PHASE7_DATA_TRANSFER.md for fault, ownership and partial-commit contracts.

## Phase 7 unary and decoded dispatch increment

The existing control decoder chooses symbolic microcode targets after operand
acquisition. The generic sequencer accepts validated branches without x86
interpretation or retirement. An explicitly rearmed operand decoder returns
its cached EA once; no instruction byte or GPR is reread. Unary arithmetic
reuses the existing ALU, result and FLAGS owners with typed constants and a
decoded operand-direction selector. See D-031 and PHASE7_UNARY_DISPATCH.md.

Decimal/radix adjustment uses an internal captured request/response arithmetic
service, selected by existing decoded metadata. Iterative division and multiply
steps perform real arithmetic. The executor commits permitted AX and FLAGS
results, then checks pending arithmetic failure before END. The existing event
owner captures #DE and the first-prefix restart IP. Reset/cancel/start clear
transient arithmetic/fault state; pause holds it. No architectural owner or
physical bus sequencer is duplicated. See PHASE7_DECIMAL_ADJUST.md.

## Segment transfer increment

Control decode supplies the captured segment index independently of the operand
EA port. The executor transfers the selector through TMP0 and the existing
cache owner, while coordinated CS/IP event/debug reloads retain priority.
POP SS uses the old SS for its read, commits SP, then loads the new cache.
Successful SS loads arm the event owner's next-instruction inhibition; faults
and failed loads do not bypass the established event arbitration. See D-033.

## Stack/frame and BOUND increment

PUSHA/POPA use explicit microcode transfers and independent eight-word preflight.
ENTER's transient stack cursor feeds the established stack/operand service;
architectural BP/SP commit after the variable parent-copy loop. A fault clears
transient state but retains completed memory writes. BOUND uses two checked
word reads and signed inclusive comparisons through the existing event path.
Generated local branch targets retain the generic sequencer's range/validity
checks. See D-034 for evidence and ownership.

## Phase 7 far pointer/control candidate

The operand service captures both words before LDS/LES or far transfer commits.
CALL uses the stack service for old CS and the next IP; RETF acquires both return
words and applies optional allocation before the shared context commit. The
single segment/cache owner and existing redirect path remain authoritative.
No far return releases NMI blocking or changes FLAGS. See D-035.
