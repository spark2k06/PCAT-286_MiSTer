# Engineering Decisions

## D-001 — WSL is the primary development environment

**Context:** The repository is physically stored on Windows at `D:\GitHub\SPK286`
and is visible in WSL as `/mnt/d/GitHub/SPK286`.

**Decision:** Use Ubuntu 24.04 under WSL2 for normal HDL development, while
keeping one authoritative Windows Git working tree.

**Rationale:** WSL provides the cleanest CLI toolchain and Docker access. The
project is small enough that the mounted-tree performance cost is acceptable;
no duplicate checkout is justified.

**Consequences:** Commands are documented from WSL. `.gitattributes` forces LF
for scripts and source so Windows `core.autocrlf=true` cannot break execution.

## D-002 — Verilator primary, Icarus secondary

**Context:** Future validation will exercise a large 80286 instruction corpus.

**Decision:** Verilator 5.020 is the primary lint/build/regression engine;
Icarus Verilog 12.0 is an independent smoke and portability check.

**Rationale:** Compiled Verilator execution is appropriate for high-volume
testing, while a second simulator catches non-portable or order-dependent RTL.

**Consequences:** The same reset test is compiled and run through both paths;
Quartus is not required by normal tests.

## D-003 — Simple Make plus shell/Python tooling

**Context:** Phase 0 needs a non-interactive interface without a framework.

**Decision:** Use a root Makefile, small POSIX shell scripts, and Python's
standard library.

**Rationale:** This keeps agent and CI invocation transparent and avoids a
dependency-heavy test framework before the CPU architecture exists.

**Consequences:** Pytest/cocotb are intentionally deferred. The loader is
covered by `unittest` and can later feed a C++ or Python execution adapter.

## D-004 — Docker only for heavy/version-sensitive FPGA tooling

**Context:** `raetro/quartus:mister` is already present locally and Quartus
17.0.2 is not installed in WSL.

**Decision:** Keep Quartus in Docker and outside `make test`/the fast loop.

**Rationale:** Quartus is heavyweight and version-sensitive; simulation should
remain seconds-scale.

**Consequences:** `make quartus-info` verifies the image. A future Quartus
project can be invoked with the documented Docker command without coupling CPU
tests to it.

## D-005 — Phase 0 RTL is a reset/fetch skeleton only

**Context:** The project explicitly forbids implementing the CPU during Phase 0.

**Decision:** Add only enough synthesizable RTL to prove reset and the first
code-fetch bus request.

**Rationale:** This is the smallest end-to-end proof of source, lint, compile,
simulation, comparison, waveform, and synthesis paths.

**Consequences:** Instruction execution, microcode, and architectural modules
remain honest Phase 1 work; the instruction matrix records this explicitly.

## D-006 — External reference code is not copied

**Context:** Relevant local projects and online references have different
licenses and architectural targets.

**Decision:** Record references and licenses in `SOURCE_NOTES.md`; reuse ideas
only, with no source copied into SPK286.

**Rationale:** This preserves licensing clarity and avoids importing 8086/80186/
80386 behavior into an 80286 design.

**Consequences:** Future reuse requires a deliberate per-file license review.

## D-007 — Architectural storage precedes instruction control

**Context:** The Phase 1 session scope is the architectural foundation, a
prerequisite of RM1 in `SPK286_REALMODE_MVP.md`, not the full instruction set
called "Phase 1" in the original broad specification.

**Decision:** Add a synchronous `spk286_registers` block with two asynchronous
read ports, one word/byte GPR write port, an independent IP write port, and a
masked FLAGS write port. Use the x86 register encoding. Reset wins over writes;
otherwise independent write ports can commit on the same edge.

**Rationale:** These are datapath commit mechanisms for later decoder/microcode
control, not instruction implementations or simulation-only state injection.
IP does not advance just because the BIU fetched bytes. No microcode compiler,
sequencer or ALU is needed to verify storage.

**Reset and FLAGS:** Intel hardware manual table 3-6 and programmer manual
section 10.4 define IP=FFF0 and FLAGS=0002. GPR zero initialization is a
deterministic SPK286 choice; those tables do not specify GPR values. Store all
defined 286 flag fields, including IOPL/NT, with writable mask 7FD5. Reserved
positions retain their reset representation (bit 1 set; 15/5/3 clear). This is
a storage invariant, not a claim that POPF/IRET can write every stored bit in
real mode. Instruction-specific masks, privilege rules and undefined arithmetic
flags must be verified when those instructions are added.

**Verification:** Directed tests cover all word/byte encodings, preservation,
disabled and concurrent writes, each FLAGS mask bit and repeated reset. An
Icarus failure exposed a read function with an implicit reference to GPR state;
passing state as an explicit function argument removed the stale read in both
simulators without changing expected values.

## D-008 — Separate visible segments and 286 hidden caches

**Decision:** `spk286_segments` stores four independent visible 16-bit values,
24-bit bases, 16-bit byte limits, and 8-bit access fields. Segment encoding is
ES/CS/SS/DS = 0/1/2/3. There are no 386 descriptor granularity/default-size bits.
Access bit 7 represents cache validity; bits 6:5 carry DPL, bit 4 the descriptor
class and bits 3:0 the segment type. Future checked descriptor commits can
extend this storage boundary without changing physical address consumers.

**Real mode:** Reset CS is F000:base FF0000. DS/SS/ES reset to zero selector and
base. All four limits are FFFF. Every ordinary real-mode reload atomically
replaces the selected visible value and base (`selector * 16`), with normal
FFFF limit and normalized access 93. Even reloading an identical selector
updates its cache. Other segments hold. Arbitrary hidden-state writes and
protected-mode descriptor loading are not exposed or implemented.

**Access representation:** 93 is SPK286's canonical valid, DPL-zero, accessed,
writable expand-up data representation, including CS in normal real mode.
It expresses the real-mode access contract, not an asserted byte-for-byte
silicon cache dump. Intel documents valid caches and zero privilege fields at
reset, and real-mode segments as readable/writable/executable. The unobservable
accessed bit and exact LOADALL/STOREALL reset image require physical evidence
before implementing those instructions. Current tests check this declared
internal representation separately from externally defined behavior.

**Addressing:** Use cached base plus zero-extended 16-bit offset on a 24-bit
path. A20 gating remains outside the CPU. This is address formation only;
operand-width/limit checks, exceptions and protected-mode access checks are
later work. A 16-bit limit is sufficient for the 286; the Phase 0 handoff's
"24-bit base/limit" shorthand must not be interpreted as a 24-bit limit.

**Evidence:** Intel hardware table 3-6, programmer sections 5.1, 6.3/6.4 and
Appendix C p. C-3; Intel's undated LOADALL note p. 3 describes the cache layout
and ordinary real-mode reload. These sources justify the representation and
normal reset-to-real-mode path; LOADALL-altered cache corner cases are deferred.

## D-009 — Architectural commits and fetch progress are distinct

**Decision:** Replace the Phase 0 top-level storage with the tested registers
and segments, and a small `spk286_fetch` transaction service. Its independent
17-bit cursor retains segment exhaustion. It supports one response slot with
backpressure, not a replacement for the eventual six-byte 286 prefetch queue.

**Control contract:** Sequential IP commits leave prefetched data intact.
A redirect requires an IP write; a CS load additionally requires a redirect.
Malformed controller transactions assert `control_error` and suppress all state
writes and the redirect. This is protocol protection, not an x86 exception.
The normal controller ports are temporarily exposed at `spk286`; they will move
inside the core when the decoder/microsequencer is introduced. Debug ports
observe the same registers used by functional addressing.

**Fetch:** Automatically issue the first reset fetch and the first fetch after
a redirect, then accept explicit requests from the future prefetch controller.
Snapshot address, offset and byte count at issue, capture data only at READY,
and hold the response until accepted. A redirect flushes buffered data and
marks any outstanding read for discard. Even repeated redirects and a redirect
coincident with READY retain the latest architectural target. A bus completion
never changes architectural IP. Stop fetching at the segment end; exception
delivery requires a future instruction-consumption boundary.

**Evidence and limits:** Intel hardware manual chapter 3 and the SingleStep
README describe physical address lanes; programmer Appendix C requires 24-bit
address formation. Phase 0 had no queue or native timing to preserve. Its
passive raw status 0 decoded as INTA in the project's reader, so use F (PASV,
S1:S0=11). No CODE request is driven during reset. None of the simplified
handshake sequencing claims to reproduce the native reset delay or Ts/Tc/Ti.

**Verification:** Directed fetch and core tests exercise independent state
writes, near/far restart, same-selector CS reload, 1 MiB carry, READY stalls,
response backpressure, canceled completions, repeated redirects, inactive
lanes, limits, malformed controls and repeated reset under both simulators.

## D-010 — Six-byte prefetch storage and first execution frontend

**Context:** Phase 2 needs an instruction stream that can consume bytes while
the bus fetches ahead, without confusing prefetched progress with architectural
IP or reusing stale bytes after a redirect.

**Decision:** Keep `spk286_fetch` as the READY-gated one-transaction service and
add an independent six-byte FIFO, `spk286_prefetch_queue`, between that service
and the frontend. The FIFO uses explicit six-entry storage, modulo-six head and
tail pointers, and a byte count. A two-byte response enters low byte first;
simultaneous fill/consume updates the count by `fill_count - 1`.

The first frontend is a small hardwired state machine rather than a generated
microcode path. It recognizes only `B8..BF`, consumes opcode/low/high bytes,
writes the decoder-derived three-bit register selector through the existing GPR
commit interface, and never enables FLAGS writes. Unsupported opcodes are
latched as a development indication and remain in the queue; this is not yet
an architectural invalid-opcode exception.

**Rationale:** Intel's 80286 Hardware Reference Manual describes a six-byte
prefetch queue, word-oriented prefetches, and queue reset on program transfer.
The existing fetch service already owns address formation, byte lanes, READY
waits and stale-response cancellation. Keeping those responsibilities separate
allows later bus timing refinement and a future decoder/microcode entry point
without rewriting queue storage.

**Consequences:** `execute_enable` explicitly selects autonomous instruction
execution; when low, the Phase 1 state-vector/debug commit interface remains
available. `debug_ip` is the next architectural instruction byte, while the
fetch cursor is the next bus-prefetch offset. The current refill policy keeps
two free slots so a word response is never split or lost; exact historical
prefetch timing remains deferred.


## D-011 — Functional semantics and timing policy are separate

**Context:** SPK286 is intended to support both historically compatible 80286
timing and accelerated execution modes from the same functional CPU
implementation. The project must preserve a path toward cycle-accurate
instruction/bus behavior without forcing every functional state or
microinstruction to consume a historical CPU cycle.

**Decision:** Functional semantics and timing policy are separate architectural
concerns. SPK286 shall use one functional execution architecture and a distinct
timing-policy mechanism. The timing model is defined in
`SPK286_TIMING_MODEL.md`.

The intended timing modes are conceptually:

- **Accurate:** honor validated historical instruction and BIU timing for a
  selected 80286/80C286 profile;
- **Fast:** remove artificial instruction-level compatibility delays while
  retaining compatibility-oriented BIU timing;
- **Max:** remove removable historical delays from both execution and BIU
  operation while preserving every real dependency.

The exact RTL encoding, timing metadata format, historical profile list, and
user-facing mode names remain deferred until timing convergence work begins.

**Real dependencies:** READY, BIU completion, required instruction bytes,
operand availability, required memory writes, bus ownership, queue
flush/redirect completion, interrupt/exception ordering, and other
architecturally required serialization must be honored in every timing mode.

**Compatibility delays:** Historical delay that exists only to reproduce 80286
timing may later be represented through timing metadata, timing classes, cycle
budgets, scheduler tables, or another explicit mechanism. Such delay must not be
encoded by scattering semantically meaningless idle/NOP states throughout
opcode-specific RTL or microcode.

**Microcode consequence:** The number of microinstructions used to implement an
architectural operation does not, by itself, define the historical cycle count
of that operation. Future microcode timing metadata must remain explicit and
separable from functional sequencing.

**Clocking consequence:** The physical FPGA master clock and the emulated CPU
timing profile are independent concepts. Historical profiles may be generated
through clock-enable/timing-policy logic while the FPGA core runs at a
higher implementation clock.

**System consequence:** Accelerating the CPU must not automatically accelerate
future PC/AT peripherals. PIT, RTC, ISA timing, keyboard interfaces, DMA and
other system components shall retain their own required timing domains unless a
specific machine profile deliberately changes them.

**Validation:** Timing work shall progress independently from functional
correctness:

1. architectural state;
2. bus transaction ordering/data;
3. cycle-state timing.

Once multiple timing modes exist, the same initial state and instruction stream
must produce identical architectural results across Accurate, Fast, and Max,
except for timing/debug observations.

**Rationale:** This permits SPK286 to serve both as a hardware-faithful 80286 and
as an experimental accelerated "super 286" without maintaining multiple CPU
implementations. It also prevents early functional RTL from becoming coupled to
unverified historical cycle counts.

**Reference lesson:** MCL86 demonstrates the useful architectural principle of
separating functional sequencing from optional cycle-compatible timing. SPK286
adopts the principle only; it must derive 80286 timing from Intel documentation,
SingleStep hardware traces, and other verified 80286 evidence rather than
copying 8086 timing.

**Consequences:** Current functional phases are not blocked by unfinished
cycle accuracy. Agents must preserve timing extensibility, classify timing debt
separately from functional failures, and never claim a profile is
cycle-accurate merely because its nominal clock rate or aggregate instruction
count matches a published value.


## D-012 — Deterministic, committed generated microcode

**Decision:** The Phase 2.75 `.mc` DSL is authoritative. A standard-library
Python compiler uses explicit parsed and expanded IR, source locations and
deterministic symbol assignment. Commit generated RTL, listing, symbols and
validation metadata; normal builds verify byte-for-byte consistency and fail
on stale artifacts. `make microcode` is the explicit regeneration command.

**Rationale:** A checkout and downstream CPU package have readable, reproducible
RTL without needing to infer how an opaque image was assembled. Sorting source
paths and preserving source order avoids host-dependent allocation. The output
contains no timestamp or absolute host paths. Transient logs/caches remain
ignored under `build/` or the existing Python cache exclusions.

**Initial representation:** Two-bit functional control: invalid, fetch imm16
to TMP0, move TMP0 to decoder-resolved DST, END. The three-word combinational
case ROM has a validity output and a two-bit address. Generated package
constants use qualified names, accepted by the installed Yosys frontend.
Public package constants locally suppress only UNUSEDPARAM because isolated
module checks intentionally consume subsets of the shared interface. No other
warning is suppressed by this decision. A larger memory image/HEX export,
ALU/bus fields and physical FPGA ROM resource selection remain deferred.

**Subset and extensibility:** Format 1 supports entries, sequential statements,
one word temporary, END and scoped debug labels. Labels name operations;
executable branches are not yet supported. Undefined debug-symbol queries,
invalid operands, missing END, use-before-definition, overflow and malformed
sources fail explicitly. No historical timing syntax or ROM bits are added.
The versioned IR/output schemas provide a later metadata extension point.

## D-013 — Generic sequencing and functional operation ownership

**Decision:** The decoder consumes a supported opcode while latching destination
metadata and starting the generated entry. B8..BF share one microprogram.
The reusable microsequencer owns micro-PC/entry, active state, sequential
advancement and END. It advances only with completion permission. The executor
owns TMP0, byte assembly and register commit; prefetch retains FIFO ownership
and the fetch service retains physical READY/address/lane/redirect handling.

**Completion:** FETCH_IMM16 remains one ROM word while the executor accepts low
then high bytes from the stream. Each accepted byte increments architectural
IP once. MOVE writes the full word, regardless of external setup byte controls;
FLAGS are not written. END emits a single registered retirement pulse and
releases decode independently of prefetch or the next bus response. The pulse
clears even if execution pauses immediately afterward. There is one production
MOV path; the Phase 2 hardwired instruction FSM is removed.

**Cancellation and pause:** Reset/valid redirect cancel remaining operations and
temporary acquisition. Redirect suppresses a simultaneous writeback/END but
does not roll back a prior completed write. External setup controls are not a
precise exception interface. Pausing execution holds microstate, temporary
bytes and FIFO consumption. A response held at the setup boundary must not be
repeatedly inserted into the queue, so FIFO fill is qualified by autonomous
execution. Malformed control transactions freeze functional progress as well
as architectural writes. These integration fixes are covered by directed tests.

**Faults and observability:** Out-of-range entries, invalid ROM words and ROM
fallthrough fail closed with sticky `microcode_fault`; no retirement is emitted.
Reset/redirect clears it. Current/entry PCs, decoded word and active status are
numeric debug outputs; source text lives in the generated JSON/listing. The
SingleStep harness reports microstate on failure and Python `--pc` resolves it.

**Timing and Phase 3:** `enable` and functional completion define implementation
scheduling, not historical clocks. Future timing policy must gate acceptance
and advancement together or retain completed responses, without repeating
side effects. There are no compatibility delays or timing modes. New operand
services such as READ_RM16/WRITE_RM16 can extend decoder metadata and executor
operations while retaining the microsequencer's completion/END contract.

## D-014 — Reusable 16-bit ModR/M and effective address metadata

**Decision:** `spk286_modrm` decodes the three fields, register-direct flag
and required displacement length. `spk286_effective_address` is the single
base/index table and DS/SS default implementation. Its displacement input is
a 16-bit word; the stream consumer sign-extends disp8 before using this port.
Every intermediate offset sum is 16 bits. Physical translation remains in
the existing segment-cache subsystem.

**Evidence:** Intel 80286/80287 Programmer's Reference Manual, 210498-005,
sections 2.4.3.1/2.4.3.2 and table 2-2 (printed 2-18/2-19) specify BP-relative
SS, ordinary DS, sign extension and modulo-65536 offset arithmetic. Direct
`mod=00,r/m=110` has no BP term and uses DS. Appendix B specifies that the
second byte of a word at FFFF is at 10000, not zero; a later logical operand
request must check the whole width before a memory side effect. Exception
delivery is outside Phase 3.

**Verification:** All 256 ModR/M bytes and 25,056 independent integer-table
EA checks cover every mode/r/m, all disp8 representations, required disp16
boundaries, distinct base/index values and wrap. Both simulators must pass.
These component tests are addressing evidence, not instruction execution or
historical timing claims.

## D-015 — Captured operand context and minimal microcode format 2

**Decision:** A single `DECODE_MODRM` functional operation acquires ModR/M and
displacement through the existing byte stream, then captures EA/default segment
in `spk286_operand_decode`. REG16/RM16 reads and writes are reusable operations
served by `spk286_operand`. The existing segment translation and GPR commit
storage remain authoritative. The microsequencer contains no new opcode logic
and its RTL is unchanged. Explicit END retains exactly-once retirement.

**Representation:** The minimal five new operations require format 2 and
encoding 2 with four control bits. The active three-entry ROM has eleven words
and four address bits. B8..BF keeps its original entry, words and behavior.
Format 1 still compiles; its immutable historical fixture remains independently
tested. A separate Phase 3 fixture pins the new versions, widths, symbols and
words. Compiler, consistency and emitted-ROM round-trip checks all enforce it.
Generated artifacts are regenerated, never edited by hand.

**Reuse and timing:** Context contains 16-bit displacement/offset, mode, REG/RM
and default segment; future ALU operations can acquire/write operands through
the same service. Byte availability, context capture, request acceptance and
response completion are real dependencies. No micro-op count represents a
historical clock budget, and no artificial delay/NOP is introduced.

## D-016 — Shared BIU ownership, logical word completion and cancellation

**Decision:** `spk286_biu` is the sole external arbiter. Fetch remains a code
client with its existing cursor/response/stale-read behavior. Data words are
snapshotted at logical acceptance and take priority only at a free cycle
boundary. A visible waiting code or data cycle retains ownership until READY.
The unchanged six-byte queue is never flushed by normal data traffic.

**Words and completion:** Even words use both lanes. Odd words use D15:8 at N
then D7:0 at N+1, independently READY-gated. The BIU retains data ownership
across both cycles and holds one complete response until consumed. The operand
pending bit prevents repeat submission while micro-PC waits. Pauses and malformed
controls stop semantic advancement while physical work may complete.

**Boundaries:** The operand service checks the entire word with 17-bit
`offset+1 <= limit` before issuing a request. Overflow latches a development
`operand_blocked`, never performs half a write and never retires. Intel Appendix
B/B-74 requires real-mode interrupt 13 for a word at FFFF; delivery remains
outside this phase. Physical address formation preserves CPU A20 carry.

**Cancellation:** Redirect cancels semantic consumption, drains an accepted
logical word (including remaining write bytes) and discards its response. Reset
aborts pending physical work. Neither action rolls back already accepted external
writes. This extends the existing development redirect contract and is not a
precise exception mechanism. Future interrupt/exception entry must serialize
against committed memory side effects deliberately.

## D-017 — Explicit hardware-vector scope and strict data memory

**Decision:** Add complete supported unprefixed normal 89/8B families to the
required SingleStep gates and CI, preserving all 40,000 B8..BF cases. New opcode
families explicitly exclude known 286 prefixes and exception outcomes. Counts
and index/hash/reason reports are mandatory; exclusions cannot appear as passes.
Revocation precedes prefix exclusion, then exception exclusion, then sampling.
B8..BF remains strict. Unknown encodings and malformed in-scope cases fail.

**Memory:** Unspecified CODE prefetch returns zero as before. Every selected
MEMR byte must exist in the supplied sparse RAM or execution fails. MEMW affects
only selected lanes on READY; complete resulting RAM is compared, including
unexpected writes. HALT remains a corpus terminator adapted by final IP minus
one; it is never executed or special-cased by RTL.

**Evidence:** The pinned physical corpus has 5,000 cases per new opcode.
89 executes/passes 3,955 with 1,016 prefix and 29 exception exclusions; 8B
executes/passes 3,940 with 1,031 prefix and 29 exception exclusions. No revocations
or failures occur. All 50,000 discovered records, including excluded ones, are
independently compared with the upstream parser; adversarial real-executable
probes prove missing/changed read bytes and wrong written-memory expectations
fail. This is architectural state evidence, not captured bus/timing equivalence.

## D-018 - Reusable word ALU, explicit candidate masks and executor temporaries

**Decision:** Phase 4 admits the 40 unprefixed binary word forms in PHASE4_SCOPE,
with byte/unary/TEST and later phases deferred. One pure spk286_alu takes A/B
and carry/borrow; operation encoding is ADD=0, OR=1, ADC=2, SBB=3, AND=4,
SUB=5, XOR=6. Instruction semantics remain in decode. CMP maps to SUB with
result write disabled. A is always the original destination, B the source.

**Ownership:** Executor TMP0/TMP1/TMP2 hold A/B/result. Three valid bits and
pending candidate FLAGS/mask prevent stale execution. The reviewed operand
service accepts caller words without knowing temporary identities. Architectural
FLAGS remain only in existing register storage. ALU computation never commits
flags directly. Arithmetic mask is 08D5; logic mask is 08C5 with undefined
0010. Undefined AF preserves stored state as a deliberate implementation policy,
not a claim that physical 286 parts preserve it. All other bits are preserved.

**Evidence:** Intel table 3-1 and instruction descriptions, independent signed
range/nibble/parity mathematics, directed RTL and pinned physical corpus.
The corpus logical mask F7EE is unchanged, with separate directed CF/OF checks.
No 386 semantics, reference CPU source or case-specific expected-state repair.

## D-019 - Format 3 functional sequencing and result disposition

**Decision:** Five shared microprograms acquire word operands, request decoded
ALU semantics, explicitly write/discard TMP2, commit FLAGS, and END. Format 3
adds ten functional controls, requiring only five bits; the active ROM has
45 words, six address bits and eight entries. All eleven inherited MOV words
and their entries remain unchanged. Frozen format-1/2 fixtures remain tested;
the active format-3 contract and emitted-ROM audit are separate.

**Commit and cancellation:** IF_WRITE is explicit result disposition; CMP
performs no register/memory write. FLAGS follows completed logical writeback,
including both odd subcycles. Candidate/temporary state clears on reset,
redirect and instruction start, and holds under pause/malformed controls.
Redirect retains the reviewed non-rollback contract; previously committed
GPR/FLAGS or external writes are not undone. Precise exceptions need future
serialization. No microsequencer, operand, BIU, EA, fetch or queue change is
required, and no historical delay, timing mode or Phase 5 opcode is added.

**Validation:** Independent model and dual-simulator component/instruction/
lifecycle/stream tests, strict full hardware families, preserved inherited
checks, eight copied-input ALU mutants and a mandatory phase4-check release
entry point. Missing corpus fails the gate. Phase 5 extends selectors/policies
as needed while reusing these ownership and commit boundaries.

## D-020 - Stack words reuse operand/BIU ownership

The stack service owns offset and SP arithmetic, not storage or bus sequencing.
SP commits on logical word completion; PUSH's source precedes decrement and
POP's destination follows increment. RET release is explicit unsigned SP
adjustment. SS selection passes through the existing segment translation port.
A validate-only operand request checks POP memory destinations before stack
side effects. Invalid whole words fail closed; exception delivery and shutdown
semantics are deferred. External debug cancellation retains the existing
non-rollback contract: accepted physical words drain, completed writes and
previously committed register effects are not undone. Reset aborts the bus.

## D-021 - Internal transfer completion is distinct from external cancellation

Taken near transfers synchronously write architectural IP, flush prefetch and
restart the existing fetch owner, then retire at the owning microprogram's END.
Their restart does not cancel that microprogram. Not-taken transfers do not
flush. Outstanding old fetch responses drain/discard in the unchanged fetch
service. CALL uses the next consumed architectural IP; RET uses its stack word;
relative targets wrap at sixteen bits. A pure condition evaluator consumes
architectural FLAGS. COUNT decrements CX only for LOOP/LOOPE/LOOPNE, before the
branch predicate; JCXZ only tests CX. Later interrupt entry can reuse this
boundary with explicit serialization and coordinated CS/IP loading.

## D-022 - Format 4 stack/control functional operations

Format 4 adds ten controls (19..28) in the existing five-bit word and grows
address width to seven bits: 20 entries, 97 words. The first 45 words and eight
Phase 4 entries remain identical. `word_stack_control.mc` is authoritative;
compiler 4.0 emits all ROM/constants/maps and a format version declaration.
The frozen Phase 4 contract remains tested separately from the active Phase 5
contract. Generic sequencer behavior is unchanged. Conditional PUSH/REDIRECT
and COUNT are explicit decoded functional effects for shared instruction
forms, not historical timing delays or a second x86 decoder.

## Unresolved, non-blocking questions

- Exact final native bus wrapper and signal polarity beyond the Phase 0 proof.
- Complete streaming MOO adapter and functional/bus/cycle comparator.
- Quartus project/device assignments for the first Cyclone V synthesis target.
- Exact timing-policy representation: timing classes, cycle budgets, scheduler
  tables, per-micro-operation minima, or another mechanism.
- Exact validated historical timing profiles and any behavioral differences
  between Intel/Harris/other 80286 and 80C286 speed grades.
- Exact boundary between microsequencer timing metadata and BIU timing control.
- Which SingleStep cycle fields can be made gating for historical timing
  validation without conflating constrained prefetch behavior with general
  queue behavior.

## D-023 — Phase 6 shared event ownership and partial effects

The event controller owns qualification and saved context; project-owned format 5
microcode owns functional entry/return sequencing through the original register,
segment, stack, operand and BIU services. Architectural events do not borrow the
external debug cancellation contract as a rollback mechanism. Completed POP/SP
effects and physical frame writes remain visible where 286 evidence requires.
The physical 8F destination-fault cases supersede the Phase 5 precheck assumption.

## D-024 — Phase 6 boundary ordering and evidence gate

An active instruction fault precedes lower-priority events; a next-opcode demand
fault follows events already owed at the prior completed boundary. Pausing after
retirement must not change that ordering. INTA uses the existing BIU with two
READY-qualified transactions and LOCK through the first complete stack word.

Failed-IRET NMI release, the STI old-IF qualifier and conflicting fault/TF text
remain explicit candidate interpretations. No model or emulator agreement closes
a missing primary/physical decision. The release gate must fail while these
findings are unresolved. Phase 7 remains unauthorized. See
[the independent review](PHASE6_ARCHITECTURAL_REVIEW.md).

## D-025 — Physical probe preparation cannot close unknown CPU semantics

The three required Phase 6 evidence decisions remain unresolved after additional
Intel source research. Portable 286 assembly, explicit memory/vector images,
post-observation diagnostic dumps and fail-closed result provenance provide a
capture handoff without changing the CPU policies. A bounded interpreter tests
payload mechanics under illustrative competing assumptions; synthetic results
remain separate from physical evidence and from the existing SingleStep cohort.

Native INTR lead time can make a short STI experiment inconclusive. A missing
pre-MOV acknowledgement cannot prove a shadow without an independently valid
recognition window. Unknown physical outcomes and partial effects must remain
observable data. No result parser or model updates the architectural evidence
gate automatically. NASM/NDISASM are explicit research-test prerequisites in CI
and bootstrap. See [closure](PHASE6_EVIDENCE_CLOSURE.md) and
[protocol](PHASE6_CAPTURE_PROTOCOL.md). No production RTL or timing-mode change
is justified by this research.

## D-026 — Provisional development is distinct from architectural release

Date: 2026-09-08. The active request is to implement incremental Phase 7 using
the supplied Phase 7 scope. The candidate is preserved with both its original
Phase 6 implementation and subsequent evidence-closure work. Development may
continue with `failed-iret-nmi`, `sti-old-if` and `fault-tf` unresolved, under
their recorded candidate policies, after fresh complete executable validation.
This supersedes D-024's Phase 7 prohibition and the equivalent historical scope
and handoff restrictions; it does not change the architectural findings.

`phase6-exec-check` and `phase6-check` share all executable steps. The former
also validates the narrow pending-evidence contract; the latter still requires
the original strict evidence checker. No arbitrary failure is waived. New
unknown prerequisites, altered policies, malformed evidence, missing families
and executable failures remain development failures. A future supported evidence
resolution reduces the actual pending set; bookkeeping does not resolve it.

CI runs the executable gate and separately classifies the exact strict evidence
result. Pending architectural evidence is displayed as pending, never approval.
Historical reports, capture packages, cohort identities and physical counts
retain their original meaning. Verified development commits may preserve this
provisional baseline; no release, main/master update or Phase 8 work is implied.

## D-027 — explicit byte service and instruction-prefix lifetime (2026-09-08)

The Phase 7 byte/prefix increment keeps one architectural register owner and
extends the existing operand/BIU service with explicit byte width. The encoded
byte-register index selects AL..BL/AH..BH; byte reads are zero extended and byte
writes preserve the other seven architectural words and the unselected half.
The pure ALU computes width-dependent arithmetic flags; existing defined masks
and the separate FLAGS commit remain authoritative.

A dedicated instruction-context module owns consumed-byte count, accumulated
segment/LOCK/repeat prefixes and their lifetime. The first prefix captures the
restart CS:IP and TF sample; final opcode dispatch applies existing STI/IRET
policy. Prefix acquisition does not retire an instruction. Segment override
applies to ordinary operand addressing, while code, stack and vector services
retain their own addressing rules. F2/F3 are retained and ignored on the current
non-string instruction set; this does not implement REP iteration.

The ten-byte limit raises #GP before an additional required byte can be consumed.
Immediate ALU forms acquire their complete immediate before accessing data.
The pinned `81.0` case index 5, hash
`f5c8f1014f6d85dd08d6a2aadc7fa04dd17c94c2`, demonstrates why the prior read-before-
immediate sequence cannot be retained when overlength prefixes are admitted.
The expected frame and RAM were not changed. Frozen format 1–5 fixtures remain
unchanged; active format 6 explicitly audits the two reordered word sequences.

Format 6 uses 58 defined controls including INVALID, 37 entries and 174 words;
the address width grows from seven to eight bits and the control width stays six.
The microsequencer remains generic. No idle state was added to approximate
historical instruction timing. The new normalized LOCK hold preserves RMW bus
ownership; exact historical LOCK pin timing is not claimed.

## D-028 — scalar decoded policies and one architectural commit owner (2026-09-08)

TEST uses the existing AND ALU with result writeback disabled; it clears CF/OF,
updates SF/ZF/PF and preserves the locally unspecified AF value. Register INC/DEC
reuse ADD/SUB with constant one and a mask that excludes CF. Byte and word TEST
retain ordinary operand faults, width, segment overrides and instruction-byte
acquisition before immediate-form data access. Other F6/F7 extensions remain
explicitly unsupported while their required implementation is pending.

CLC/STC/CMC, CLD/STD and SAHF receive a candidate and precise mask from opcode
metadata. The generic executor performs a typed FLAGS_DECODED operation through
the existing FLAGS owner. SAHF writes only SF/ZF/AF/PF/CF and preserves control
bits. LAHF uses the existing flag read and a byte write to AH. CBW/CWD are typed
temporary transforms; separately captured source/destination selectors let CWD
read AX and write DX without duplicating GPR state.

Format 7 preserves the exact prior words and adds five entries/nineteen words.
Four new controls remain six bits wide. Protocol validation and independent
fixtures cover source lifetime, single write/commit and malformed sequences.
The old CMP-write mutation now preserves TEST suppression while still injecting
the same forbidden CMP write. Seven additional mutations cover TEST writes and
undefined AF, INC carry preservation, SAHF control preservation, LAHF alias, CBW
sign and CWD source selection. No new Phase 6 evidence exception is introduced.

## D-029 — shift arithmetic ownership and zero-count disposition (2026-09-08)

The shared executor requests a generic mathematical shift service with captured
kind, width, operand, count and CF. It owns no architectural registers or bus
cycles. The five-bit count controls actual bit operations; the generic
microsequencer waits for completion. Pause, cancel/reset and response consumption
are explicit. This does not model historical compatibility delay.

CL is acquired before an aliased operand; immediate counts precede data access.
Zero count still reads memory and checks its word limit. The service's result
disposition suppresses writeback without bypassing a real operand dependency.
FLAGS still pass through the single architectural owner with an empty mask.

Intel leaves multi-count OF and shift AF undefined. Pinned CL shift captures
compare final-elementary-step OF. The initial preserve-OF policy failed 13,166
physical records; independent upstream/wire-mask analysis and the reduced VCD
identified the masked commit. The selected policy commits final-step OF for
nonzero operations and preserves AF, which all relevant masks exclude. The
corrected 210,000-case prototype run passed with original masks/results intact.
See PHASE7_SHIFT_FLAGS.md for the evidence, limits and failed-run identities.

Format 8 preserves prior source/encoding fixtures and adds six functional
programs. The inherited all-FLAGS mutation keeps its original ALU defect while
preserving the new shift branch. Nine new mutations test arithmetic, count,
snapshot, pause and zero-count CPU disposition; none edits production sources.

## D-030 — typed data addresses and ordered exchange commits (2026-09-08)

A transient executor address override allows direct MOV and XLAT to reuse the
existing operand service. It clears on start/cancel/reset. XLAT adds unsigned AL
to BX with a sixteen-bit offset wrap; segment selection remains outside this
operation. LEA reads the cached effective offset without making an operand
request. Register-source LEA is an owned #UD at ModR/M decode.

XCHG captures both sources, completes the RM write, then commits the captured RM
value through the existing GPR owner. Memory exchange requests implicit LOCK
from the existing BIU and cannot grant HOLD between read and write. Cancellation
preserves completed architectural writes and drains accepted physical writes.
A dedicated lifecycle bench checks both odd-word halves and each commit boundary.

Format 9 extends typed functional controls, preserving all earlier words and
fixtures. Seven synthetic legacy benches used 90 as an unsupported stop; now
that NOP is supported they use the unsupported system escape 0F with unchanged
state/non-retirement assertions. Physical records and frozen expected images
are not edited. No new Phase 6 evidence exception or timing claim is introduced.

## D-031 — terminal decoded dispatch and cached operand reuse (2026-09-08)

F6/F7 and FF acquire their operand context before a terminal generic dispatch.
The existing x86 metadata decoder supplies symbolic targets; the sequencer
receives only a request, target and valid bit. It validates range/validity,
honors pause/cancel/reset and retains the original instruction entry. Branching
neither retires nor resets architectural state. Existing TEST and GROUP5_NEAR
microprograms remain reusable and retain their previous control words.

Their DECODE_MODRM operation queries an explicitly rearmed cached context.
The operand decoder returns its stored offset/fields once without consuming
bytes or recomputing the EA from changed GPR values. Its ordinary single-pulse
completion contract is unchanged. A pending reuse freezes on pause and clears
at start/cancel/reset. This is a functional availability handshake.

NOT uses XOR/all-ones with an empty FLAGS mask. NEG uses decoded operand
reversal with zero and ordinary SUB status. Byte/word RM INC/DEC use constant
one and preserve CF. The existing architectural owner commits results and
FLAGS; memory completion precedes FLAGS. FE /2..7 fault at ModR/M. Legal
unsupported groups remain distinct from invalid encodings and internal errors.
See PHASE7_UNARY_DISPATCH.md for evidence, lifecycle checks and audit findings.

## D-032 — captured decimal/radix arithmetic and serialized #DE (2026-09-08)

DAA/DAS use original AL/AF/CF for correction; AAA/AAS adjust the full AX before
masking AL. AAM/AAD consume the captured radix byte, including nondecimal values
present in physical tests. A dedicated service implements genuine arithmetic
steps and owns no opcode, architectural state or bus. Completed results remain
stable under pause/backpressure and transient state clears on cancellation.

Format 11 requires result disposition and FLAGS commit before CHECK_ARITHMETIC.
AAM radix zero keeps AX, commits the physically observed 08D5 fault mask, and
raises #DE before END. All eleven original zero-radix frames are compared with
unmasked RAM bytes; no corpus mask or frame expectation is changed. The policy
is identified as physical evidence for otherwise undefined flags, not an Intel
guarantee or a resolution of the inherited fault-TF question. Ordinary undefined
flags remain separately specified. First-prefix restart and event ownership
stay in their existing components. See PHASE7_DECIMAL_ADJUST.md and the retained
phase7_adjust_zero_radix_observations.json identities.

## D-033 — segment ownership and post-SS interrupt inhibition (2026-09-08)

Captured opcode/ModR/M metadata selects a visible 286 segment independently of
EA translation. Generic microcode transfers that selector through the existing
segment/cache owner; invalid MOV CS or indices 4..7 fault before data access.
POP SS completes the old-stack read and SP update before loading the new cache.
The event owner arms inhibition only after successful SS writes. It protects
the next complete instruction, including its prefixes, from NMI, INTR and TF;
synchronous faults remain deliverable and repeated SS loads renew protection.
Intel 210498-005 MOV B-73 and POP B-83 specify this behavior. The 45,000 physical
cases all have initial IF/TF clear; directed event evidence is distinguished
from physical data/cache evidence. The three inherited evidence questions are
unchanged. See PHASE7_SEGMENT_TRANSFER.md for ownership and scope.

## D-034 — restartable stack cursor and bounded microcode branches (2026-09-09)

PUSHA captures original SP, while POPA discards the saved SP word. Eight-word
preflight checks modular word starts, preserving legal even wrap and rejecting
FFFF word starts. ENTER uses a transient cursor through the existing stack and
operand service; only successful completion installs BP/SP. Each actual parent
read and push is checked, and completed physical writes survive a later fault.
Thirteen full physical ENTER faults disproved the initial complete-transfer
preflight. Four BOUND captures require an even FFFE/0000 pair despite the
printed manual's blanket range rule; this physical-policy refinement is explicit.

Format 13 expresses the loop with a generic five-bit counter and validated
instruction-local symbolic branches. The existing sequencer owns branch
execution, the BIU owns every transfer, and architectural state has one owner.
No timing padding or second instruction engine is introduced. See
PHASE7_STACK_FRAME.md and phase7_stack_frame_observations.json for raw sources,
failed prototypes, exception ordering and verification boundaries.

## D-035 — shared pointer acquisition and far context commit (2026-09-09)

LDS/LES and memory far CALL/JMP acquire both pointer words through the existing
operand service. Pointer FFFE wraps the upper word to zero, matching the pinned
physical records; odd crossing words fault before either destination write.
CALL checks its full four-byte frame after operand acquisition, captures old CS
and the next IP, and uses the existing stack service. RETF acquires its complete
frame before the shared CS:IP context commit; immediate allocation is unsigned.
FLAGS and NMI blocking are preserved. Five READY variants of a handler CALL/RETF
round trip prove a queued NMI is released only by the following IRET.

Format 14 appends seven complete protocols and controls 113-115, retaining all
433 prior words, entry addresses and loop destinations. The generated image is
83 entries/492 words with nine-bit addresses and seven-bit controls. No second
decoder, segment owner or physical bus sequencer is introduced. The separate
arithmetic prototype must rebase its tentative format-14 source before reuse.
See PHASE7_FAR_TRANSFERS.md for primary/manual evidence and actual run hashes.

## D-036 — captured integer arithmetic and physical byte-IDIV overflow (2026-09-09)

An iterative service captures width, signedness, dividend and divisor/multiplier.
Microcode acquires bytes and operands first, then disposes typed AX/DX or decoded
register results and FLAGS before checking #DE. No arithmetic service owns the
bus or architectural registers. Mathematical division remains the default,
including positive overflow, unsigned division and word division.

Four unchanged physical byte-IDIV captures establish successful minimum-signed
quotients where mathematical negative overflow would fault. A finite eight-step
candidate reproduces all 5000 byte-IDIV records, and exhaustive research matches
all 4210433 mathematically legal input pairs. Reference-emulator predictions of
128 additional positive-overflow successes lack supporting capture evidence and
are not adopted. Only negative signed-byte overflow may accept its finite
minimum-signed quotient and corresponding remainder. No test identity, address,
byte sequence or expected register value is encoded in the CPU.

The finite candidate shares product storage during the ordinary division's real
iterations. It neither inserts idle states nor changes external dependencies.
The expected-state adapter uses original RMSK only at the original EXCP FLAGS
word for architecturally undefined divide flags. Defined frame bits and every
other register/memory check remain strict. Independent negative comparison
probes and unchanged physical records are mandatory evidence.

Format 15 appends controls 116..120 and 29 words to the delivered far image.
The isolated full-phase candidate uses a different temporary allocation and
must be rebased/regenerated before later integration; generated files are never
hand-merged. This decision is not a new unresolved D-026 waiver, a claim about
all silicon revisions, or independent architectural release approval. See
PHASE7_IDIV_COMPATIBILITY.md and the exact observation records.

## D-037 — functional Phase 7 closure with exact evidence notes (2026-09-09)

The user explicitly changes Phase 7 acceptance to functional/development
closure with the three inherited D-026 notes, REP initial-zero completion event
ordering and one precisely identified incomplete E7 physical capture open.
The normative contract is [PHASE7_FUNCTIONAL_POLICY.md](PHASE7_FUNCTIONAL_POLICY.md).
This new decision supersedes incompatible current completion prerequisites;
dated earlier reviews and blocked reports retain their original conclusions.
It neither rewrites D-026 nor grants historical architectural/timing approval.

The corrected ordered candidate is integrated from verified recovery, with
formats 15/16/17 preserving delivered arithmetic before strings and I/O. Human
microcode remains authoritative. Exact E7 admission lives outside strict parsing,
RTL and architectural comparison. Executable and policy manifests bind fresh
results and a separate independent functional reviewer. All evaluable records,
negative audits and real CPU dependencies remain mandatory. Phase 8 entry is
permitted after this scoped delivery, with the named notes recorded; no Phase 8
implementation or E7 issue publication is part of this decision.
