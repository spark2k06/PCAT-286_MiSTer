> Historical prototype record. The four failures and tentative format 14 below

Current functional delivery (2026-09-09, D-037): **Phase 7 milestones 1–9
are integrated, executable-validated and independently approved for functional
development.** All 307 required files are covered: 1,386,996 evaluable records
passed, exactly one E7 capture is NOT EVALUABLE, and there are no unexpected
omissions or executable failures. The three inherited Phase 6 notes and the two
named Phase 7 notes remain open and nonblocking; historical timing is not
certified. Phase 8 may start from this accepted functional baseline; no Phase 8
implementation is included. E7 issue publication remains pending by user request.
See the [functional closure record](PHASE7_FUNCTIONAL_CLOSURE_20260909.md),
[new independent approval](PHASE7_FUNCTIONAL_REVIEW_20260909.md) and
[functional recovery guide](PHASE7_FUNCTIONAL_RECOVERY.md).

## Preserved historical record — superseded for current status

The text below retains its original dates, counts and conclusions. Its earlier
REP/E7 blocking criteria are superseded by D-037 and the functional delivery
above; historical validation and withheld-approval decisions are not rewritten.

> describe the preserved frame-based candidate. See PHASE7_ARITHMETIC.md and
> PHASE7_IDIV_COMPATIBILITY.md for the corrected candidate and current status.

# Integer arithmetic candidate: verification remains incomplete

This isolated development candidate implements MUL/IMUL/DIV/IDIV in byte and
word forms and both 286 immediate IMUL forms. It is not delivered or a Phase 7
PASS: the complete 50,000-record physical run has **49,996 passes and four
failures**, with no revocations, exclusions or changed expected results.

## Functional ownership

A captured iterative service receives a typed operation, width, dividend and
source. It has no opcode, register-file or bus ownership. Products use 8/16
shift/add steps; quotients use 32 restoring steps over captured magnitudes.
Signed division truncates toward zero, gives the remainder the dividend sign,
and checks the mathematical quotient range before either destination write.
Zero-divisor and overflow faults preserve AX/DX and restart at the first prefix.
Microcode disposes AX and then DX where applicable, commits explicit FLAGS, and
checks the captured arithmetic fault. Immediate IMUL uses the captured ModR/M
register destination. Pause, response backpressure, redirect and reset retain or
cancel actual owned dependencies; no historical cycle count is claimed.

The source format 14 image has 80 entries / 462 words and preserves all previous
433 words and branch targets. This candidate is based on the frame prototype;
it must be rebased and regenerated if another independently delivered family
uses these next control encodings first. Generated artifacts are never merged
by hand.

## Defined results and physical FLAGS

Intel's 80286 Programmer's Reference, DIV and IDIV instruction descriptions,
defines the quotient/remainder and divide-error conditions but leaves CF, PF,
AF, ZF, SF and OF undefined. SPK286 preserves those six bits during division;
this is an explicit functional policy with no physical undefined-bit claim.
MUL/IMUL use defined CF/OF range overflow. The captured upper product explains
SZP throughout the normal physical multiplication corpus; AF is preserved.

The initial physical reproduction compared the entire exception-frame RAM and
failed 11,244 cases. The upstream corpus documents EXCP.flag_address expressly
for applying undefined-FLAGS comparison masks, including DIV. The revised
adapter carries the **original RMSK** only into the two original FLAGS bytes of
a DIV/IDIV #DE frame. It checks the address against the original SS:SP stack
word and requires both bytes in the captured final RAM. It rejects any mask
that drops a defined bit. It changes neither expected bytes nor the source
corpus. Other faults, AAM frames, CS/IP, GPRs, memory-address sets and all other
memory bits retain their previous checks. Unmasked batches retain format 2;
format 3 adds an explicit optional RAM mask map.

Four pristine physical #DE cases and 24 declared undefined-bit variants pass;
176 mutations of defined frame bits or address sets fail. The independent
277-file parser audit also passed its 67 ordinary and 1,858 event comparison
probes, preserving the older exact AAM/frame checks.

Sources: [Intel manual](https://bitsavers.trailing-edge.com/components/intel/80286/210498-005_80286_and_80287_Programmers_Reference_Manual_1987.pdf)
and [upstream exception convention](https://github.com/SingleStepTests/80286#exceptions).

## Four unresolved signed-byte captures

The remaining failures are F6.7 indexes 952, 1085, 2653 and 4297. Their computed
signed quotients are -260, -287, -675 and -359, outside [-128,127]. The captures
instead retire with AL=80h. Source bytes, registers, memory, every bus cycle,
RMSK and absence of EXCP independently match the upstream parser. None is
revoked. They are already discussed in the open upstream
[IDIV issue](https://github.com/SingleStepTests/80286/issues/1).

This does not settle whether the cause is a capture defect or undocumented
physical behavior. No address/index/hash/corpus-specific CPU rule, local
revocation, substituted expected result, or false full-gate PASS is permitted.
A repeat physical capture or authoritative evidence for a general behavioral
rule is needed. This is a separate unresolved Phase 7 validation problem; the
three inherited D-026 questions do not waive it. Other instruction families
can continue independently.

## Executed prototype evidence

- 284,500 independent arithmetic vectors and 7,497,611 checks in both simulators.
- 17,508 full-CPU cases and 2,163,297 checks in both simulators.
- 780 iteration/pause/cancel/reset/event/fault cases and 57,104 checks in both simulators.
- 226 ordinary tests, 82 compiler tests, consistent generation and Verilator lint.
- Fourteen new RTL mutants rejected with three pristine benches; twelve existing
  decimal/radix mutants also rejected. Original failed audit attempts are kept:
  one removed only a redundant zero guard, another expected a later assertion
  although the first held-response check had already rejected the enable bypass.
- Yosys synthesis passed: 15759 mapped / 1393 sequential cells.
- The full physical result remains 49,996/50,000, so integration and complete
  regression/delivery are pending. Self-checks are not independent review.

Exact sources, original records, run exit codes and log hashes are in
[phase7_muldiv_observations.json](phase7_muldiv_observations.json).
