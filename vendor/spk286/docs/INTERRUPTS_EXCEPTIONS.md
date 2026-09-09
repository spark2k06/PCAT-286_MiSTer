# Real-mode event architecture

Current Phase 7 integration uses ordered microcode formats 15/16/17 (100 entries,
612 words), shared CPU owners and the D-037 functional acceptance contract.
See [PHASE7_FUNCTIONAL_POLICY.md](PHASE7_FUNCTIONAL_POLICY.md),
[PHASE7_MEMORY_STRINGS.md](PHASE7_MEMORY_STRINGS.md), [PHASE7_IO.md](PHASE7_IO.md)
and [PHASE7_EMULATOR_REFERENCE.md](PHASE7_EMULATOR_REFERENCE.md). Earlier
increment counts and pending inventories below are historical snapshots.

Status: implemented candidate; architectural release blocked by the unresolved
286 distinctions in [PHASE6_ARCHITECTURAL_REVIEW.md](PHASE6_ARCHITECTURAL_REVIEW.md).
The original contract was written before RTL changes.

## Sources and adjudication

* Intel **iAPX 286 Programmer's Reference Manual**, 210498-003 (1985),
  chapters 2, 5, 9 and appendix B. [Original scan](https://bitsavers.trailing-edge.com/components/intel/80286/210498-003_iAPX_286_Programmers_Reference_1985.pdf).
  SHA-256 `9c6067e777ae694d5f71d8ade23014558be4e9d156041c778aed84c1246d8538`.
  STI B-102 (PDF page 302) explicitly delays recognition until after the next
  instruction and gives STI/RET and STI/CLI examples. This resolves the abbreviated
  STI wording in the later 210498-005 scan. IRET B-48–50 specifies ordered IP, CS,
  FLAGS pops and a real-mode fault for a popped word at FFFF.
* Intel **80286 Hardware Reference Manual**, 210760-002 (1987), chapter 3:
  priority, NMI edge/pending behavior, INTA, halt/shutdown and bus ownership.
  [Original scan](https://bitsavers.trailing-edge.com/components/intel/80286/210760-002_80286_Hardware_Reference_Manual_1987.pdf).
  SHA-256 `d3ece037a200b17ef32d78a055d0d96c3e47474d755d94569b9576a9a68c6915`.
* Intel **80286 B-2/B-3 Step Information**, 21 November 1984,
  [transcription and original Intel pages](https://www.pcjs.org/documents/manuals/intel/80286/b2_b3_info/):
  INT clears TF after saving FLAGS and does not single-step into its handler.
  LOCK covers both INTA transactions and links them to the first stack push.
  These corrections take precedence over superseded manual text. Known early
  stepping bugs are not additional architectural requirements.
* Intel 210498-005, chapter 5/table 5-2 and appendix B, corroborates real-mode
  saved IPs, no error codes, shutdown on INT/INTO with SP=1,3,5, and PUSHF with
  SP=1. SHA-256 `ad487ba99b48cd9f61b14c0fe912a04c7cdb4c7c14a18419aa9faf62d8962460`.
* [SingleStepTests/80286](https://github.com/SingleStepTests/80286/tree/37c73caf53dcd22d3dd369ff09305d13d117a4fe),
  captured on Harris N80C286-12, independently identified by case index/hash.
  All 189 invalid 8F captures raise #UD(6), resolving a conflict with appendix C
  wording suggesting vector 13. All 33 non-prefixed 8F destination-limit faults
  retain the successful POP's SP+2. For example 8F/568 starts SP=23143 and has
  post-entry SP=23139: +2 for the pop, then -6 for the exception frame. This is
  a hardware-backed correction to Phase 5's precheck/no-SP-effect assumption.
  Successful POP behavior and golden hardware values remain unchanged.

## State ownership and completion

The architectural GPR/FLAGS/IP block, segment caches, stack arithmetic service,
operand service and physical BIU remain the only owners of their respective
state. An event controller arbitrates requests and snapshots return context;
it does not become an alternative execution engine. Generated project-owned
microcode performs frame pushes, IVT reads and context commits through those
services. Cancellation discards transient candidates; it cannot undo an
accepted external write. Real faults have their own saved-start context and
completion, distinct from the debug redirect/cancel protocol.

Capture instruction-start CS:IP and TF when the opcode is consumed. Keep that
context through all subsequent ModR/M, displacement and immediate reads. Current
architectural IP is the consumed-byte cursor/next IP; fetch cursor is speculative
and never supplies a return IP. With future prefixes, start capture will precede
the first prefix; no prefix support is claimed here.

`instruction_retired` is an ordinary instruction completion pulse; a faulting
instruction never retires. Software INT retires only when its entry completes.
`event_completed` independently identifies a completed delivery, including a
fault. Neither pulse repeats when execution is paused. A halt retires once and
has a persistent halt indication. A shutdown is a distinct terminal state.

## Selection and saved context

| Request | Eligibility / priority | Vector | Saved IP | Saved FLAGS | Retirement |
|---|---|---|---|---|---|
| Instruction fault | Fault producer; before lower-priority boundary events | 6 or 13 | instruction start | current architecturally committed FLAGS | No |
| TF single step | TF sampled on instruction start; after completion; below fault | 1 | completed next/target IP | post-instruction FLAGS | Target already retired |
| NMI | Latched rising edge, unblocked, instruction boundary | 2 | next instruction IP | boundary FLAGS | No new instruction |
| INTR | Level high, IF=1, no STI shadow, boundary | second INTA low byte | next instruction IP | boundary FLAGS | No new instruction |
| INT3 / INT imm8 / INTO taken | Executed software event; cannot be interrupted mid-instruction | 3 / imm8 / 4 | next consumed-byte IP | pre-clear FLAGS | After entry |

Intel's priority tables place instruction faults before TF before NMI before
INTR; an external request eligible at a boundary is serviced before decoding
the next software INT. An executed INT suppresses the TF trap per B-2 correction.
No event is admitted in the middle of a frame or a physical operand word. Lower
priority pending events survive and may be admitted before the first handler
instruction when still eligible after IF/TF clearing. An unavailable *next*
opcode does not precede an already owed boundary event, including after pause.

The candidate creates an STI shadow only on the transition from IF=0 to IF=1.
The old-IF qualifier requires further 286 evidence; it is not a validated fact. The following
instruction consumes it; CLI in that position clears IF before arbitration.
POPF and IRET restore IF without creating an STI shadow. TF is sampled before
instruction execution: setting TF with POPF/IRET traps after the following
instruction, whereas clearing an already sampled TF does not erase that trap.
The candidate does not manufacture a retirement-based single-step trap for a
fault. This follows the Real Mode body text but conflicts with Appendix C/D;
the independent review records that unresolved evidence explicitly.

NMI keeps one pending edge, including while NMI delivery is blocked. A held high
pin cannot retrigger. NMI acceptance blocks subsequent NMI until execution of
IRET. The candidate unblocks at opcode acceptance, including a failed attempt;
that failed-IRET distinction is unvalidated and blocks release. The latch is independent of
the execution pause. Reset clears pending/block/shadow/halt/shutdown state.
The exact internal clock of NMI unblocking is not claimed as historical timing;
architectural acceptance remains restricted to safe instruction boundaries.

Interruptibility is source-specific: IF and the STI shadow qualify INTR, while
NMI inhibition and sampled TF have independent state. The independent model
tests the compact cross-product of these predicates. Future MOV SS/POP SS work
must introduce its separately evidenced source-inhibition rule at this same
instruction-boundary qualification layer; it must not infer NMI/TF eligibility
from IF or count micro-operations as completed instructions. No SS-load opcode,
SS-specific inhibition behavior or corresponding hardware coverage is claimed.

## Shared entry and commit matrix

Entry obtains INTA when required, then pushes FLAGS, CS and return IP in that
order. Each word uses SS and 16-bit stack offsets, with 24-bit physical addition.
Clear IF/TF after preserving their frame image. Read IVT offset at vector*4 and
selector at vector*4+2. Only after both reads complete, commit CS/cache and IP,
flush the queue, cancel stale code responses and restart at the handler. Real
mode pushes no error-code word. The resulting stack top is IP, CS, FLAGS.

| Stage | May become architectural / externally visible | Must remain transient on failure |
|---|---|---|
| Opcode and operand-byte consumption | Internal IP cursor only; start context is stable | No GPR/FLAGS result |
| Data source read | Bus read; successful POP advances SP | Uncommitted ALU/destination candidate |
| Word destination write | Each accepted physical byte; logical completion commits associated SP | No later false retirement |
| Frame FLAGS/CS/IP pushes | Each completed word decrements SP; physical halves cannot be rolled back | Handler CS/IP not yet installed |
| IVT reads | Read transactions only | Candidate handler IP/CS |
| Entry context commit | CS selector and normal real cache plus IP together; IF/TF clear | Stale instruction queue/response |
| IRET stack reads | Successful ordered pops advance SP; candidate IP/CS/FLAGS held | No partially installed CS/IP/FLAGS |
| IRET final commit | Candidate CS/cache, IP and masked FLAGS together | Old prefetched stream |

Word limit failure is detected before that word issues a physical bus cycle.
An odd word's two physical halves retain ownership until completion, including
under pause. A POP-to-memory destination fault follows the successful stack read
and SP increment, as required by physical evidence. There is no global rollback.
Stack offsets wrap between words; a word beginning at FFFF faults. Thus even
SP=0,2,4 are not blanket-rejected for entry. If a frame push cannot be completed,
enter shutdown; do not recurse forever into an impossible exception frame.
Frame words already written remain observable. NMI or reset can leave shutdown;
if NMI itself cannot establish a frame, remain shut down until reset (NMI stays
blocked). No fabricated protected-mode #DF/error-code sequence is introduced.

PUSHF/POPF and IRET use normalized 286 reserved bits. Real-mode stack restores
modify application/control bits 0FD5; IOPL/NT retain their stored values. The
storage/debug mask 7FD5 remains a distinct policy. CLI/STI modify only IF;
entry modifies only IF/TF. Arithmetic's defined/undefined masks are unchanged.

## Bus and suspension contract

INTA comprises two independently READY-qualified, non-memory transactions.
Status identifies INTA, A0 is low, the second vector is sampled from D7:0, and
the CPU does not drive data. The first vector value is ignored. LOCK retains
ownership across both acknowledgements and through the first complete stack
word; HOLD/HLDA cannot split that chain or an odd data word. No prefetch request
can masquerade as an acknowledge. Historical idle clocks are timing policy.

Halt/shutdown indications are normalized idle-status indications, not memory
transactions. Halt stops new code requests after any owned physical cycle drains.
Eligible INTR, NMI or reset resumes halt; masked INTR does not. Shutdown ignores
INTR. Debug pause suppresses new functional micro-operations while the BIU drains
already accepted words and holds responses; reset and explicit debug cancel
have their documented stronger lifecycle semantics.
