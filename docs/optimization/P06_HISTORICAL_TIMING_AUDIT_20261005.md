# P06/P12: historical timing and target handoff audit

Date: 2026-10-05. This is an unchanged-production-RTL audit and directed
diagnosis, not a timing correction, new fit, or historical release acceptance.
The unchanged T286REF2 COM remains SHA-256
`006a7be0bd962859bf929e6b0d6678c400607461ed095c9e164789acf05f2643`.

## Result

R0's arithmetic minima and the shared LOOP 8/4 clocks agree with Intel.
The production taken-Jcond/JMP path has a demonstrated target-handoff gap:
real fetches occur, but their overlap does not enforce Intel's additional
one clock per byte of the next executed instruction. With equal two-clock
target instructions of lengths 1/2/3, JE/JMP take 7 clocks and the pair takes
9 clocks at 6, 12.5 and 20 MHz. The Intel table reference for those pairs is
10/11/12 clocks. This conclusion is based on actual fetch, consumption and
retirement traces, not the passive `estimated` flag.

The unchanged B0 body correspondingly subtracts to about 19 clocks per
iteration at 6/12.5 MHz; its two taken transfers each target a two-byte
instruction, giving an Intel table reference of 23 clocks. This does not
justify extending the footnote to LOOP, adding a generic refill penalty,
or altering R0 to match 86Box. The gross native disagreement also contains
prefetch, bus and instrumentation effects; handler constants alone do not
explain its magnitude.

## Primary sources and exact locations

The local Intel publications were hashed against the earlier
[frozen manifest](../evidence/p06-intel-contract-20261003/manifest.json).
PDF page numbers here are one based. Branch/CALL/RET/LOOP notes were checked
in rendered scans, in addition to full-text extraction.

| Publication | SHA-256 | Locations used |
| --- | --- | --- |
| [Intel 210498-005, 1987 Programmer's Reference](https://bitsavers.trailing-edge.com/components/intel/80286/210498-005_80286_and_80287_Programmers_Reference_Manual_1987.pdf) | `ad487ba99b48cd9f61b14c0fe912a04c7cdb4c7c14a18419aa9faf62d8962460` | B-6/PDF214: clock units, total timing, EA/odd/read-wait corrections; B-19/227 ADD; B-23/231 CALL; B-33/241 CMP; B-45/253 IN; B-54/262 Jcond; B-56/264 JMP; B-70/278 LOOP; B-73/281 MOV; B-77/285 NEG; B-81/289 OUT; B-83/291 POP; B-86/294 POPF; B-87/295 PUSH; B-89/297 PUSHF; B-94/302 RET; B-97/305 shifts; B-114/322 XCHG; B-116/324 XOR |
| [Intel 210760-002, 1987 Hardware Reference](https://bitsavers.trailing-edge.com/components/intel/80286/210760-002_80286_Hardware_Reference_Manual_1987.pdf) | `d3ece037a200b17ef32d78a055d0d96c3e47474d755d94569b9576a9a68c6915` | 3-3/PDF53: six-byte prefetch and separate three-entry decoded queue; 3-15..3-19/65..69: clock phases, Ts/Tc and pipelining; 3-24..3-25/74..75: prefetch, demand priority and one buffered write; 3-32/82: READY and extra Tc |

B-54/B-56 require an additional clock for each byte of the next instruction
after the transfer; B-23 and B-94 apply the same qualification to CALL and
RET. B-70 has no such qualification for LOOP. JCXZ belongs to B-54 even
though the implementation groups it with LOOP. Prefix bytes belong to the
instruction encoding; the prefixed probe results below do not qualify the
production prefix timing fallback as an Intel execution-time reference.

B-6 supplies total instruction clocks, including memory forms. Normal
two-clock operand bus service must not be added again as an EU-only charge.
Its aggregate 5-10% fetch estimate is not a per-kernel correction factor.

## Kernel and instrumentation audit

| Executed form | Current table | Intel reference | Finding |
| --- | ---: | ---: | --- |
| R0 ADD AX,BX; XOR DX,DI | 2 each | 2 each | Correct documented minima |
| R0 ADD BX,imm8s; XOR DI,imm16 | 3 each | 3 each | Correct; inspected native handlers use 2 each |
| Shared LOOP | 8 taken / 4 exit | 8 / 4 | Correct; inspected native handler uses 11 for both outcomes |
| B0 CMP AX,AX; JNE not taken | 2; 3 | 2; 3 | Correct |
| B0 JE taken to JMP short | 7 | 7 + 2 | Target handoff absent from the qualified interval |
| B0 JMP short to LOOP | 7 | 7 + 2 | Same gap; LOOP's own cost remains 8/4 |
| M0 A1 aligned moffs16 read | 5 | 5 | Correct table; operand availability remains a dependency |
| M0 ADD AX,[disp16] | 7 | 7 | Correct, no base+index+displacement surcharge |
| M0 A3 aligned moffs16 store | 3 | 3 | Correct table; CPU write-buffer overlap remains provisional |
| M0 XOR [disp16],imm16 | 7 | 7 | Correct table; real READ and WRITE remain distinct dependencies |

There are 255 taken LOOPs and one exit in every 256-iteration kernel and
baseline. B0's INC and NOP are skipped. M0 performs three data reads and two
data writes per iteration. All its words are even. The timer/setup/signature
code introduces further memory accesses, CALL/RET, branches and I/O.

The PIT latch endpoints are the two read-back OUT commands, not instruction
retirements. Consequently no sum of whole wrapper instruction minima alone
establishes exact gross latch-to-latch time. The actual new hardware captures
use PIT mode 2; mode 3 has additional SHR/TEST/branch work. Both paths exist
in the unchanged program.

| Wrapper forms | Current policy | Qualification |
| --- | --- | --- |
| MOV register/immediate/register-to-register; byte/word signature stores | 2 / 3 for stores; A1 read 5 | Matches B-73; direct forms have no EA surcharge |
| CMP/AND/TEST immediate register or direct memory; NEG register; SHR by one | 3 immediate-register, 6 compare/test-memory, 2 NEG/one-bit shift | Matches relevant forms; exact encoded operands must select these forms |
| PUSHF/PUSH BX; POPF/POP BX; CLI/CLC | 3 / 5 / 3 / 2 | Documented ordinary minima; actual stack references and READY remain dependencies |
| IN AL,40h; OUT 43h,AL | 5 / 3 | Documented minima; real I/O service can extend them, no memory-read-wait surcharge |
| XCHG AL,AH | 3 | Documented register form |
| Three `EB 00` timer-delay JMPs | 7 each | Each targets two-byte IN, so table reference is 9 each; a zero displacement still redirects |
| Relative CALL pit_read/pit_validate/pit_phase | 7 | Target lengths 1/1/2 require 8/8/9 before actual dependencies |
| Indirect `FF 16` CALL [kernel_ptr] | 11 | First target instruction is 2 bytes for baseline/R0/B0 and 3 for M0: 13/13/13/14 |
| Near RET | 11 | Target-length qualification is required: start pit_read returns to a three-byte CALL, pit_validate to a two-byte JC, pit_phase to a four-byte CMP, kernel to three-byte A3 |

These are catalogued forms, not a completed timing measurement of every
wrapper path. Setup/probe/output also use string operations, DIV and DOS
INT21h outside the timed kernel window. Their existing functional behavior
and estimated complex-event metadata are not historical closure evidence.

## What production currently guarantees

`rtl/spk286_timing/spk286_instruction_timing.sv:210` supplies 7 for
CALL/JMP-relative; lines 213 and 218 supply 7/3 for Jcond and 8/4 for LOOP.
Lines 196, 211, 216 and 224 explicitly mark target-length distinctions as
estimated. That flag is passive in
`vendor/spk286/rtl/timed/spk286_profiled.sv:455`; it changes no interval.

The scheduler starts at prefix/opcode admission, updates qualified form
metadata, freezes it at functional completion, and delays public retirement
until a processor boundary reaches the budget and the real operation has
finished (`spk286_instruction_schedule.sv:31`, `:49`, `:77`). Following opcode
admission is gated until that retirement and context release. The functional
decoder has no independent target instruction length input or lookahead.

Redirect occurs inside the branch body. It flushes the six-byte queue and
restarts fetch (`spk286_profiled.sv:573`, `:932`, `:945`). The resulting CODE
transfers and operand-byte acquisition are real dependencies. They can refill
the target before the branch's seven-clock minimum expires; target decode
and its own interval then proceed at fabric speed. Thus actual refill is
present, but it does not entail the additional per-byte delivery interval.

The AT machine ties `timing_read_wait_event` to zero
(`rtl/spk286_integration/spk286_at_machine.sv:745`). B-6's additional memory
READ wait correction is therefore an available controller interface, not an
implemented motherboard wait policy. Backend lateness can still extend
functional completion. It cannot be silently reclassified as a board wait
count, nor charged twice as both dependency extension and inferred debt.
Odd-word corrections are charged once per original reference, before BIU
splitting; this policy agrees with B-6 and does not affect these aligned M0
operands.

## Directed evidence

The packet runs unmodified production CPU, profile generator and AT bridge
against a one-fabric-edge accepted RAM peer. There is no downstream cache,
refresh, DOS or PIT in this fixture. CS106E and the complete unchanged COM
are present; exact baseline/B0 bytes and locations are guarded. Standalone
probes place their branch at IP0480 and target at IP0500 or IP0501, keeping
placement and initial state fixed within each alignment. Targets 1/2/3 are
INC AX, MOV AX,BX and MOV AX,1234h, all with a documented two-clock minimum.
Targets 4/5/6 add DS prefixes to the three-byte MOV and only diagnose encoded
length/prefix handling. LOOP is an independent control with no target note.

Icarus and Verilator complete **304 runs**: 38 cases at four profiles in each
simulator. All applicable columns of all 152 paired complete passive traces
agree, including GPR/FLAGS, fetch, redirect, bridge ownership and retirement.
Raw traces preserve explicitly reported X-versus-zero unused queue-head
values when no valid byte can be consumed. No architectural field or accepted
transfer is normalized. Exploratory prefix-observer and unused-head comparison
failures are retained as fixture/audit failures, not production failures.

| Nominal profile | JE/JMP clocks, lengths 1/2/3, both alignments | Pair clocks, lengths 1/2/3 | LOOP clocks, lengths 1/2/3 |
| --- | --- | --- | --- |
| 6 MHz | 7 / 7 / 7 | 9 / 9 / 9 | 8 / 8 / 8 |
| 12.5 MHz | 7 / 7 / 7 | 9 / 9 / 9 | 8 / 8 / 8 |
| 20 MHz | 7 / 7 / 7 | 9 / 9 / 9 | 8 / 8 / 8 |
| 25 MHz | 7 / 7 / 7 | 9 / 9 / 10 | 8 / 8 / 8 |

The 25 MHz extra pair clock is a functional implementation extension on the
three-byte target, not a monotonic per-byte branch allowance. Lengths 4..6
also leave JE/JMP retirement at 7; their successor intervals include the
explicitly provisional prefix fallback.

At 6 MHz, the even-target JE probes all admit the branch at edge360, redirect
at363, receive first target CODE READY at392, and retire the branch at417.
Target admission occurs at418; last target-byte consumption is418/419/420
for lengths1/2/3, and target retirement is434 for all three. Required bytes
are being fetched and consumed; the per-byte branch reference is still absent.

| Exact 256-iteration image | 6 MHz virtual clocks | 12.5 MHz virtual clocks | 20 MHz virtual clocks | 25 MHz virtual clocks |
| --- | ---: | ---: | ---: | ---: |
| Baseline, first opcode through last LOOP | 2044 | 2044 | 2044 | 2044 |
| B0, same boundary definition | 6909 | 6909 | 6910 | 7420 |
| Difference / 256 | 19.00390625 | 19.00390625 | 19.0078125 | 21.00000000 |

The Intel no-added-wait table lower bounds are baseline2044 and B0
`256*(2+3+9+9+8)-4 = 7932`, giving 23 body clocks. This is an isolated
table comparison and a discriminating dependency diagnosis. It does not
predict complete instrumented hardware samples or certify the fixture as
an electrical 80286 model.

## Bridge epoch and Ts/Tc consistency

The bridge clears `timing_tc_q` at every admission. The next boundary begins
Tc and the following one permits READY. Physical response data is retained
until logical publication, and a new transfer is never published before its
own admission/Tc sequence. Existing ownership and stale-response rules remain
causal (`spk286_at_bus_bridge.sv:121`, `:309`, `:325`).

Chained admission can nevertheless occur between boundaries via the retained
window. For example, the 6 MHz trace has old READY at edge25/tick3, next
command admission at26/tick3 with boundary0/window1, Tc beginning at34/tick4,
and next READY at42/tick5. The next transfer has two **logical** clock epochs
from the preceding completion, while its actual command admission happens
one fabric edge later. Calling that admission the literal beginning of a
full-length Ts is inconsistent with Intel 3-17/3-18. This is a normalized
same-clock scheduling convention; it needs an explicit retained epoch and
address/status milestone to claim literal historical Ts/Tc.

Two alternatives should be discriminated: reserve the next request with valid
address/status at the previous boundary, then begin Ts there; or assign Ts
only to the first boundary at which the request is actually qualified. Do
not mark Tc retroactively complete or add a compulsory idle clock to every
transfer. The present deadline diagnostic starts after admission and does
not measure waiting to acquire that epoch.

## Concrete correction model and resource boundary

A scalar cost transferred to the next instruction can enforce a pair lower
bound, but leaves branch retirement and asynchronous event eligibility early.
Holding branch retirement until the ordinary next decoder supplies length
deadlocks: that decoder is gated by the held retirement. Neither is full
closure of the Intel branch-to-target handoff.

A reviewable strict implementation needs an independent, side-effect-free
target encoding preview and retained bytes. One slot of at most ten encoded
bytes can be used without adding Intel's complete three-entry decoded queue.
The source branch context and its normal metadata remain active while actual
post-redirect fetch fills that slot. The preview determines the complete
encoding length, including all prefixes, 0F escape, ModR/M, displacement and
immediate bytes. It must derive form classification from the functional
decoder/microcode specification and reuse `spk286_modrm`; it must not add a
workload-specific opcode/length table or execute target micro-operations.

Once length L and all required bytes are qualified, the source deadline is
`base + EA/odd/read-wait corrections + L`. Actual CODE availability and source
operand/ownership completion additionally gate retirement. They do not add
a second generic refill budget. The controller must accept late length
qualification after functional RAW completion rather than freezing an
incomplete seven-clock total. Jcond not taken and LOOP do not acquire this
allowance; JCXZ taken does. CALL/JMP/RET should use their documented form and
gate/task qualification before applying it.

On source retirement, normal event arbitration runs before target dispatch.
If no event wins, replay the staged bytes exactly once through the ordinary
decoder. A fetch word crossing the first-instruction boundary must route its
trailing byte to the existing queue, without duplicating a fill or refetch.
Reservation/backpressure must account for staged, queued, outstanding and
held-response bytes separately. Existing GPR/FLAGS/IP/event services remain
the sole architectural authority.

Reset, external redirect and semantic cancellation invalidate preview data.
An already accepted stale fetch must drain under the existing owner before
discard; an invisible prepared fetch may be cancelled. A winning event at
the delayed branch boundary discards the unexecuted target preview, then
uses the original frame/INTA path. NMI/INTR must not bypass the handoff; no
target GPR/FLAGS/memory effect may precede this arbitration. Source faults
retain source context. Invalid/truncated/overlength target encodings must
complete the source boundary and preserve the next instruction's fault IP;
they must never become source-branch faults or wait forever for a valid
length. Their historical fault timing requires an explicit estimated policy
until separately supported by Intel/physical evidence. MAX must bypass all
preview/timing storage and preserve every existing raw stream.

Storage planning only: a simple ten-byte staging slot is **80 data bits**,
plus roughly **30-50 control bits** for occupancy, parsed length/state and
cancel/replay qualification, before any implementation or synthesis. This
is not a measured ALM cost or a guaranteed minimum. An opcode/group syntax
classifier can have substantial combinational cost. Reusing the six-byte
queue alone cannot retain a fully qualified ten-byte encoding while its
source branch context is held. Any cheaper storage reuse needs a concrete
protocol proof. No dummy NOPs, duplicated bus-service charge or fixed B0
penalty is justified.

The manuals constrain total minima and independent IU operation; they do
not specify every internal decode/interrupt/fault milestone of this proposed
preview. Therefore this audit does not promote that design to historical
pin accuracy or implement a production patch. First qualify the byte-preview
protocol, then measure its cost and instruction-boundary behavior.

Required discrimination before promotion: lengths1..10 with identical
placement and known target costs; taken/not-taken Jcond, JCXZ and LOOP controls;
relative/indirect CALL/JMP and RET; even/odd targets; prefix/0F/ModR/M/group
immediate variations; target crossing the six-byte queue boundary; held READY,
missing bytes, backpressure, stale fetch drain and boundary-straddling words;
interrupt/NMI at every handoff milestone; source faults versus target faults;
reset/redirect/LOCK/HOLD; all MAX raw comparisons; and broad architectural
regression followed by measured generic and fitted resource/50 MHz timing
cost. A complete DOS/PIT trace is still needed for gross calibration.

## Reproduction and evidence limits

The [compact source-bound packet](../evidence/p06-historical-timing-audit-20261005/README.md)
was generated under `build/p06-timing-audit-20261005` and is now archived in
`docs/evidence/p06-historical-timing-audit-20261005`. It preserves the runnable builder, bench,
manual hashes, source identities, complete compressed traces, logs, paired
comparison receipt and bridge epoch examples. Compiler objects, duplicate
uncompressed traces and extracted full-manual text are disposable after the
packet is reviewed. No production file or expected architectural result is
changed by this milestone.

An independent hash/source and full paired-trace review passed before cleanup:
304 run metrics, 152 paired comparisons, 188,145 rows and the 3,724 declared
unused-head differences were recomputed from the compressed packet. See the
[verification receipt](../evidence/p06-historical-timing-audit-20261005/verification.json).

From the repository root, restore the disposable fixture before running it:

```sh
tar -xzf docs/evidence/p06-historical-timing-audit-20261005/p06-historical-timing-audit-20261005.tar.gz
python3 build/p06-timing-audit-20261005/branch_probe.py
```

This uses installed NASM-independent frozen COM bytes, Icarus and Verilator
under WSL from the repository root. It rechecks every guarded source after
execution. This is directed proof of the present gap, not a complete CPU,
OS, physical bus, motherboard wait-state or fitted timing acceptance.
