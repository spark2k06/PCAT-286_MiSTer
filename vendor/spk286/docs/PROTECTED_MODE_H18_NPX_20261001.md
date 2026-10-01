# H18: CPU-side ESC/WAIT traps in the no-NPX profile

Historical H18 receipt: the negative D8 results and binary below describe that
milestone. The subsequent [H19 ESC boundary fix](PROTECTED_MODE_H19_ESC_BOUNDARY_20261001.md)
resolves all 33 retained failures; current D8 execution should pass.

Date: 2026-10-01. Baseline: SPK286 `3657489`.

## Scope and architectural contract

H18 implements the CPU-side no-coprocessor contract, independently of PE and
CPL. It does not implement 80287 arithmetic, an external NPX interface, BUSY
waiting, numeric error delivery or operand transfer to an NPX. BUSY is inactive
in this profile. MSW initialization is unchanged; software controls EM/MP/TS.

Intel's 80286 Programmer's Reference Manual, 210498-005 (1987), section 10.2.2,
tables 10-1/10-2 and exception #NM (B-2), supplies the oracle:

- ESC (D8..DF): fault #NM when EM or TS is set.
- WAIT (9B): fault #NM when MP and TS are both set; EM alone does not trap WAIT.
- Otherwise WAIT completes, and a valid no-NPX ESC consumes ModR/M and
  displacement syntax without executing numeric arithmetic.
- #NM has no error word. The saved CS:IP identifies the first opcode/prefix
  byte. Faulting ESC must not consume its ModR/M before the MSW check, retire,
  change GPR/FLAGS/segment state, or access an operand/port.
- CLTS can clear TS at CPL0, followed by IRET and a single successful retry.
  A software emulation handler instead advances saved IP past the instruction;
  it must not retry with EM still set.

| TS | EM | MP | ESC | WAIT |
|---|---|---|---|---|
| 0 | 0 | 0 | Complete | Complete |
| 0 | 0 | 1 | Complete | Complete |
| 0 | 1 | 0 | #NM | Complete |
| 0 | 1 | 1 | #NM | Complete |
| 1 | 0 | 0 | #NM | Complete |
| 1 | 0 | 1 | #NM | #NM |
| 1 | 1 | 0 | #NM | Complete |
| 1 | 1 | 1 | #NM | #NM |

The abbreviated WAIT entry (B-113) omits MP from its TS wording. The explicit
control-register explanation and #NM entry resolve that abbreviation. Native
86Box `src/cpu/x86_ops_fpu_2386.h::opWAIT` checks `(cr0 & 0xA) == 0xA`;
`src/cpu/x87_ops.h::FP_ENTER` and `op_nofpu_a16` check `cr0 & 0xC` for ESC.
This agrees with the selected CPU-side oracle. Those reference paths contain
other processor/FPU behavior that is outside this implementation.

Primary manual: [Intel 1987 reference](https://bitsavers.org/components/intel/80286/210498-005_80286_and_80287_Programmers_Reference_Manual_1987.pdf).
The cached PDF identity is recorded in the
[global review](PROTECTED_MODE_GLOBAL_REVIEW_20260929.md); the current native
reference commit is pinned in the receipt. Physical data is from
SingleStepTests/80286 commit `37c73caf53dcd22d3dd369ff09305d13d117a4fe`.

## Implementation

Microcode format 26 adds `CHECK_NPX_ESC` (196) and `CHECK_NPX_WAIT` (197).
ESC's terminal program is check, decode syntax, END; WAIT's is check, END.
The compiler rejects missing, late, duplicate or wrong checks and any operand,
port or register-writing operation in these programs. Frozen older ESC images
remain readable; the active ROM is checked against an independent transformation
of the frozen format-25 image. The ROM has 123 entries / 742 words and retains
8-bit controls and 10-bit addresses. All other entry bodies and branch targets
are preserved after address relocation.

The micro-executor tests MSW only for a valid, enabled operation, honoring
start/reset/cancel/pause. #NM is selected before the real-mode #UD fallback.
The existing fault/event machinery delivers the frame and prevents retirement;
no new top-level ports, duplicate x86 decoder or synthetic timing delays are
added. Instruction semantics remain separate from timing policy.

PCAT receives the same decoder, micro-executor, microcode compiler/source/ROM,
tests and evidence. Its existing real-mode fetch IP-wrap customization in the
top/fetch files is preserved. The directed vendor run enables P01 memory start,
P02 fetch chaining and P05 parallel limit checks together.

## Directed validation

The new CPU bank uses executable LOADALL fixtures, real memory/READY traffic
and actual real-mode or same-level protected #NM delivery. It uses no force or
injected event response. The matrix contains:

- 9,000 combinations of all eight MSW controls, real mode or protected CPL0..3,
  no prefix/CS override/REP+SS override, WAIT or all eight ESC opcodes in three
  ModR/M forms, and policy requests 0/1/2, plus one EM-blind baseline control.
- 54 CLTS/retry and emulation/skip cases through actual handlers and IRET.
  Successful retries use a valid memory pointer. An invalid FFFF pointer is
  used only in the truth-matrix cases where #NM must precede operand checks.
- 24 pause/resume and redirect/cancel cases at the NPX check boundary.

Policy 0 and Max (2) are the supported schedules. Request 1 is explicitly
verified as rejected, with a diagnostic and fallback to policy 0; this is not
a claim of three supported timing modes or historical cycle accuracy.

The bank asserts the first-fault vector/state/IP, no error word, no subject
operand/port traffic, exact three-word frame, no premature retirement,
single successful retirement/length, retry/skip and absence of stale faults
after cancellation. Pre-change ESC EM=1 and unsupported WAIT reproducers fail
before the correction. Compiler/audit, lint, affected banks, both reset smokes,
state vectors and portable mapped synthesis are recorded in the
[validation receipt](REGRESSION_H18_NPX_20261001.json).

Final results: **9,079 cases / 58,615 assertions pass per simulator** for the
new bank, both standalone and with the PCAT options. Thirteen related banks
pass in both simulators; six vendor banks pass with P01/P02/P05. All 109
compiler tests and 347 Python tests pass. Microcode consistency/independent
audit, strict lint, both reset smokes, state vectors and fully mapped portable
CPU synthesis pass. The D8 physical failures below remain explicitly open.

This is a directed H18 validation, not another complete project regression.
The preceding full block regression remains a separate historical result.
No new OS boot or MiSTer hardware execution is claimed here.

## Additional physical finding: H19 remains open

The supplemental physical probe admits WAIT (9B) and ESC (D8) without changing
the frozen Phase 6/7 cohorts. The independent upstream parser, raw EXCP and
RMSK readers agree for all 10,000 records. No revocation, exclusion, missing
payload or relaxed comparison is introduced.

- WAIT: **5,000 / 5,000 pass**.
- D8: **4,967 pass / 33 fail**. This is a real, retained failure, not a waiver.
- An independently rebuilt pre-H18 `3657489` CPU fails the same 33 D8 captures.
  All 33 physical #GP captures fail both before and after H18; the remaining
  4,967 pass. H18 did not introduce or repair that boundary defect.
- Every failing capture uses a memory effective offset FFFF, independently
  recomputed from source registers and instruction bytes. The physical 286
  raises real-mode #GP rather than retiring ESC. The current no-NPX program
  only decodes the pointer and retires.

First reproducer: D8 index 78, hash
`65e4a86f5069143ad8b8cf3f63b6c1cfc28d6927`, `esc [ds:si]`, SI=FFFF,
CS:IP=FC6B:FBF0. Physical delivery ends at D206:869E with SP=AC60; the current
CPU instead retires at FC6B:FBF2 with SP=AC66. Native 86Box's no-FPU path also
only decodes EA, so it cannot establish correctness for this boundary.

This belongs to H19's FFFF crossing / operand precheck matrix. Resolve the
CPU-side ESC address validation width/type and fault priority there using the
physical captures and directed protected/cache tests. Keep #NM before operand
validation, do not introduce NPX arithmetic or operand bus transfers, and do not
classify these 33 captures as non-evaluable. Exact identities are retained in
the receipt. Full ESC conformance remains open even though H18's scoped MSW
trap contract is implemented.

## Reproduction and downstream binary

From the SPK286 root under WSL:

```sh
SPK286_BUILD_DIR=$PWD/build/h18-20261001 bash scripts/test_units.sh both spk286_npx_traps
make microcode-test microcode-audit lint
SPK286_BUILD_DIR=$PWD/build/h18-20261001 python3 -m tools.run_singlestep --opcode 9B --full --include-prefixes --include-exceptions
# Retained H19 failure; this command must currently return failure.
SPK286_BUILD_DIR=$PWD/build/h18-20261001 python3 -m tools.run_singlestep --opcode D8 --full --include-prefixes --include-exceptions
```

The Release 86Box backend is rebuilt from the exact PCAT vendor and installed
at `D:/GitHub/86Box_dev/build/spk286/86Box-linux`, retaining P02/P05 and the
existing profiles. SHA-256:
`e32abb43767e6724bd913d7fa8f6349b2dc0f7b815507ef513e8a5aefbaf3823`.
Build log: `D:/GitHub/86Box_dev/build/spk286/h18-20261001-build.log`.
Previous binary: `86Box-linux.pre-h18-20261001` in the same directory.

H18 closes only the CPU-side no-NPX trap scope agreed with the user. Remaining
stories: H02 (partial), H05, H11, H15, H16, H17, H19 and H20. The concrete D8
boundary reproducer is an actionable starting point for H19.
