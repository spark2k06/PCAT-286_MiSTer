# Milestone 7 — 80286 LOADALL / Unreal Mode

Status: **functional slice implemented; evidence and corner-case closure pending**
Owner: SPK286 CPU core
Date opened: 2026-09-16

Current implementation review: 2026-09-16

The first implementation slice is now present in the CPU core. It is
deliberately not declared a complete historical LOADALL implementation: the
current claim is limited to the fixed-image functional contract and directed
verification recorded in [LOADALL_EVIDENCE.md](LOADALL_EVIDENCE.md).

This milestone defines the evidence, architectural contract, implementation gates,
and acceptance criteria for the undocumented 80286 `LOADALL` instruction and the
unreal-mode behavior that it enables. It is a CPU-core milestone; it is not a
PCAT, BIOS, MiSTer, or Titus-specific workaround.

The decoder now classifies `0F 05` as a dedicated 80286 LOADALL operation rather
than as `#UD`, and the microcode/RTL path performs the fixed-image load. Invalid
`0F` holes remain separate from this legal operation.

## Current implementation slice

The following gates are implemented and tested:

- format-21 microcode contains a dedicated `LOADALL` token and `END` entry;
- `0F 05` dispatches only to that entry; `0F 04`, `0F 07` and other holes stay
  on the invalid-opcode path;
- a standalone service reads 51 little-endian words from physical `000800h`
  and stages the complete 102-byte image;
- GPRs, IP, FLAGS, MSW, GDTR, IDTR, LDTR, TR, visible selectors and hidden
  segment/system caches commit atomically after the final response;
- real-mode hidden-cache translation is exercised by a post-LOADALL fetch and
  data read above 1 MiB, including READY stalls, under both Verilator and
  Icarus;
- local protected-mode checks reject non-zero CPL with `#GP(0)` and reject a
  protected-mode image that clears PE, without publishing staged state.
- the service test also covers the protected CPL=0 success path and cancellation
  restart;
- the top-level protected test enters a CPL=1 context, executes a second
  `LOADALL`, and verifies the normal event path delivers `#GP(0)` with the
  saved `FLAGS`, `CS`, `IP` and error word.
- the real-mode integration holds READY low on selected image words, injects
  reset after acquisition has started, asserts HOLD during LOADALL traffic,
  and raises NMI during the image read; bus ownership, atomic restart, HLDA
  suppression and deferred NMI state are checked.

The exact evidence, assumptions and current validation receipts are maintained
in [LOADALL_EVIDENCE.md](LOADALL_EVIDENCE.md) and
[LOADALL_VALIDATION_RECEIPT_20260916.md](LOADALL_VALIDATION_RECEIPT_20260916.md).
The remaining gates below are still required before this milestone can be
marked complete.

## 1. Authority and evidence policy

The sources below do not have equal authority. SPK286 must implement the 80286
behavior supported by the strongest available evidence, and must document any
remaining uncertainty rather than silently adopting a later x86 behavior.

1. **Primary architectural source:** Intel, *80286 and 80287 Programmer's
   Reference Manual*, order number 210498-005 (1987). This is the authority for
   documented 80286 instruction decoding, exception delivery, saved `CS:IP`,
   error-code rules, and documented protected-mode behavior.
2. **Primary undocumented-behavior source:** Intel, *Undocumented iAPX 286 Test
   Instruction*. The archived copy describes `LOADALL`, its 102-byte physical
   memory image, hidden descriptor-cache loading, and special 286 forms. It is
   valuable primary-era evidence, but contains an opcode-reference inconsistency
   (`0F04H` versus `0F05H`) that must not be hidden in the implementation.
3. **Physical evidence:** direct 80286 hardware captures and the
   [SingleStepTests 80286 project](https://github.com/SingleStepTests/80286),
   especially its future/available unreal-mode suite when it is published or
   otherwise made available. The repository currently pins a hardware-derived
   real-mode suite; that is not evidence that LOADALL has already been tested.
4. **Reference implementations:** [86Box](https://github.com/86Box/86Box),
   Bochs, PCem/related emulators, and other compatible implementations may be
   used for hypotheses, opcode-map comparison, and differential tests. They are
   not architectural authority and their source must not be copied into SPK286.
5. **Later Intel IA-32 manuals:** useful for terminology and general exception
   descriptions, but not authority for undocumented 80286 behavior or for
   back-porting 386 prefixes/instructions into the 286 core.

### Evidence recording requirements

Every behavior that is not directly specified in the public 80286 manual must
have an evidence entry containing:

- source name, URL or local revision, and acquisition date;
- exact page, table, opcode, or test identifier;
- the observed behavior and the confidence level;
- whether the evidence is architectural, silicon-specific, emulator-derived, or
  an SPK286 implementation choice;
- the unresolved alternatives and the test that would distinguish them.

The final implementation PR must add or update a dedicated evidence report and
the decision log. This milestone document is the plan, not a substitute for
that report.

## 2. Problem definition

`LOADALL` is not an ordinary register-load instruction. It changes CPU state
that is normally hidden from software, including the descriptor caches used for
segment translation. A correct implementation therefore has to define more
than the visible register file:

- general registers, `IP`, and `FLAGS`;
- `MSW` and the system registers `GDTR`, `IDTR`, `LDTR`, and `TR`;
- visible segment selectors and their hidden cache state;
- descriptor-cache base, limit, access/type bits, and validity/presence state;
- the mode/privilege transition rules and exception frame;
- the memory transaction sequence used to fetch the image from physical memory;
- atomicity: what is visible if the instruction is interrupted, reset, held, or
  faults before completion.

The documented 80286-era note describes a 102-byte image beginning at physical
address `000800h`, and explains that arbitrary hidden segment-cache values can
be installed. That is the mechanism commonly called 286 “unreal mode”. The
image layout and all corner cases must be treated as an evidence-backed contract
before RTL state is committed.

## 3. Provisional opcode and exception contract

This is the contract for the decoder and exception boundary while the full
instruction is being developed. “Provisional” means that a later evidence
report may refine an item; it does not permit a generic fallback to a 386 rule.

| Encoding | Provisional 80286 classification | Required handling / current boundary |
|---|---|---|
| `0F 05` | Undocumented 286 `LOADALL` | Dedicated fixed-image implementation slice; do not classify as invalid/#UD |
| `0F 04` | Invalid in the ordinary 286 opcode map | `#UD` pending resolution of the Intel note's `0F04H`/`0F05H` inconsistency |
| `0F 07` | 386 `LOADALLD`, not a 286 instruction | `#UD` |
| `0F FF` and other holes in the 286 `0F` map | Invalid | `#UD` |
| `64h`–`67h` | Invalid first bytes on 80286; they are not 386 segment/operand/address-size prefixes | `#UD`; saved `CS:IP` must identify the first byte |
| `D6`, `F1`, `82h` aliases, `D0/D1 /6`, `F6/F7 /1` | Separate undocumented-compatibility cohort | Do not bundle into LOADALL; retain explicit evidence and per-form tests |

The public Intel manual's invalid-opcode rules are the baseline for `#UD`:

- vector 6;
- no error code;
- no retirement of the invalid instruction;
- saved `CS:IP` points to the first byte of the offending instruction,
  including any leading prefixes accepted by the decoder;
- the handler may inspect or skip the bytes and emulate an extension.

The `64h` example, the two-byte `0F FF` example, invalid ModR/M extensions, and
the distinction between an invalid encoding and an unimplemented legal form
must remain covered by decoder tests. In particular, a legal-but-unimplemented
form must not be converted into invented `#UD` solely to make a game progress.

## 4. Known LOADALL evidence to resolve

The archived Intel test-instruction note reports the following behavior. These
items are starting hypotheses, not yet an SPK286 implementation claim:

- `LOADALL (0F05H)` is an undocumented 80286 instruction intended to load all
  visible and hidden CPU state from memory.
- The source image is 102 bytes at physical `000800h` in the described real-mode
  use case.
- The image includes the machine-status word, task/local descriptor registers,
  `GDTR`/`IDTR`, visible registers, and four hidden segment descriptors.
- The hidden descriptors can be made inconsistent with the visible selectors,
  allowing segment accesses beyond the normal real-mode 64-KiB limit.
- The note reports a protected-mode privilege restriction for non-zero CPL and
  describes a general-protection exception with error code zero. This must be
  confirmed against physical 80286 evidence and the exact SPK286 protected-mode
  exception boundary before being made normative.
- The same note discusses `STOREALL`, ICE/test forms, and other undocumented
  opcodes. They are related evidence, not automatic scope for this milestone.

The note is internally inconsistent about whether the test opcode is `0F04H` or
`0F05H`. The public 80286 opcode map and 86Box's 286 table both map `0F05` to
`LOADALL` and leave `0F04` illegal, while the archived note must still be
preserved as historical evidence. The implementation must record which silicon
and test setup resolves that conflict; it must not silently reinterpret one
opcode as the other.

### Candidate image layout

The exact byte layout is to be copied into the evidence report only after the
Intel note has been checked visually and against tests. The implementation
should model the layout as named fields, not as an opaque array or a guessed
packed SystemVerilog struct. At minimum the report must identify offsets,
widths, byte order, and whether each field affects visible state, hidden state,
or both.

The hidden descriptor records require special attention. For each of `ES`, `CS`,
`SS`, and `DS`, the report must establish the meaning of every field, including
base width, limit width, access/type bits, and valid/present semantics. The
80286 has 24-bit physical addresses; no 386-only cache fields or 32-bit
registers may be introduced as a convenience.

## 5. Scope

### In scope

1. A named, reviewable 80286 `LOADALL` image definition.
2. Ownership of all visible and hidden state needed by the 286 segmentation
   unit, including reset values and state-retention rules.
3. Decoder classification of `0F05` as a special 286 instruction and separation
   from invalid `0F` holes and 386-only encodings.
4. A micro-operation sequence that reads the image through the existing BIU /
   memory interface at physical `000800h` and respects the core's wait-state,
   hold, reset, and currently representable interrupt contracts. Bus-error
   behavior is deferred because the CPU-only interface has no bus-error input.
5. Staged/atomic state commit, with no partially loaded architectural state on a
   fault or aborted transaction unless physical evidence explicitly requires it.
6. Real-mode execution and the resulting hidden-cache/unreal-mode accesses.
7. Protected-mode privilege and exception behavior once independently evidenced.
8. Directed RTL tests, differential traces against reference emulators, and
   synthesis/lint/regression coverage.

### Explicitly out of scope

- 80386 `LOADALLD (0F07h)` or any 386 operand/address-size behavior;
- treating `66h`/`67h` as prefixes in an 80286 decoder;
- 80287/NPX state and `ESC` instruction implementation;
- copying 86Box, Bochs, PCem, or other emulator RTL/source;
- implementing `STOREALL`, ICE entry, or every undocumented alias as an
  implied part of LOADALL;
- PCAT integration, BIOS changes, MiSTer timing policy, or a Titus-specific
  opcode skip;
- claiming cycle-accurate behavior without bus-level evidence for the selected
  80286 silicon revision.

## 6. Implementation gates

### Gate 0 — Evidence and contract

- Add `docs/LOADALL_EVIDENCE.md` with page-level citations and source hashes.
- Resolve the image layout from the Intel note and at least one independent test
  source.
- Record the target silicon assumption (Intel 80286 or Harris/AMD-compatible
  variant) and any intentionally unsupported revision-specific behavior.
- Define the protected-mode fault frame and the point at which state commits.

### Gate 1 — State owner

- Add or verify explicit 286 hidden descriptor-cache state in the CPU core.
- Keep selector state separate from cache state; ordinary `MOV Sreg`, `POP Sreg`,
  far control transfers, and `LAR`/`LSL` must continue to use the same owner.
- Define reset, task-switch, mode-switch, and `LOADALL` update rules.
- Add assertions preventing accidental 386-only fields or 32-bit address math.

### Gate 2 — Decoder and microcode entry

- Retain the tested distinction between invalid encodings and legal-but-
  unsupported forms.
- Add a dedicated `LOADALL` entry that cannot be reached by `0F04`, `0F07`, or
  arbitrary unsupported legal forms.
- Verify no premature register write occurs while the image is being fetched.

### Gate 3 — Real-mode LOADALL

- Fetch the complete image from physical `000800h`.
- Stage all fields, then commit according to the evidence-backed atomicity rule.
- Verify every visible register, system register, selector, and hidden cache.
- Demonstrate a post-LOADALL access whose result depends on the loaded hidden
  cache rather than on a 386-style address-size feature.

### Gate 4 — Protected mode and faults

- Exercise the evidenced CPL=0 success path.
- Exercise the evidenced non-zero-CPL fault path, including vector and error
  code, with no accidental partial commit.
- Verify interaction with `PE`, descriptor-table state, NMI/INTR boundaries,
  reset, and bus hold/wait behavior. A bus-abort/error input is not part of the
  current CPU-only contract and must not be simulated through READY or
  cancellation.

### Gate 5 — Independent validation

- Run the dedicated SPK286 directed tests and the full regression suite.
- Run the available `v1_unreal_mode` SingleStepTests suite when it exists for
  the supported 80286 target; if unavailable, retain a clearly marked evidence
  gap rather than treating emulator agreement as a substitute.
- Differentially compare functional traces with 86Box and at least one other
  emulator, recording disagreements instead of choosing the majority result.
  The bounded 86Box/PCem result is recorded in
  [LOADALL_EMULATOR_DIFFERENTIAL_20260916.md](LOADALL_EMULATOR_DIFFERENTIAL_20260916.md).
- Run the repository's [physical DOS LOADALL probe](../research/loadall_probe/)
  on the selected 80286 stepping and archive the screen capture, CPU marking and
  test environment. The current probe is screen-only and emits `Phase:` lines
  so a hang can be localized from the last visible line.
- Re-run synthesis, lint, and integration tests for the target board.

The point-4 validation pass was completed for the dedicated decoder, LOADALL
service, integration and protected-mode tests under both Icarus and Verilator,
plus lint and synthesis. The receipt records the one unrelated repository-state
error in the broad Python discovery run and does not claim that the full
repository regression is green.

## 7. Test matrix

| Area | Required cases | Pass condition |
|---|---|---|
| Classification | `0F05`, `0F04`, `0F07`, `0FFF`, `64h`–`67h` | Exact special/invalid distinction; only evidenced invalid cases raise `#UD` |
| Image fetch | all 102 bytes, byte order, physical `000800h`, READY wait states | Exact addresses and lanes; no skipped or duplicated byte |
| Visible state | each GPR, `IP`, `FLAGS`, `MSW`, visible selectors | Exact post-commit values |
| System state | `GDTR`, `IDTR`, `LDTR`, `TR` | Exact base/limit/selector/cache result |
| Segment caches | `ES`, `CS`, `SS`, `DS` base/limit/access/valid behavior | Subsequent translation matches the loaded hidden state |
| Unreal access | 24-bit physical address above 1 MiB and limit edge cases | Correct bus address and protection behavior |
| Atomicity | reset, HOLD, READY wait, NMI during acquisition; bus fault only when an external error contract exists | Behavior matches available evidence; no accidental partial commit |
| Protected mode | CPL=0 and non-zero CPL, error-code and saved-frame checks | Exact vector/frame and state-retention behavior |
| Regression | ordinary real/protected mode and existing SingleStep suites | No regressions or changed exception classification |
| Differential | 86Box plus another emulator, where both implement the form | Agreement recorded; disagreement escalated to primary evidence |

## 8. Emulator reference protocol

The local 86Box source supplied for this investigation is under
`D:\GitHub\86Box_dev\src` (the working tree may contain unrelated user edits;
do not modify them). The second local source reference is under
`D:\GitHub\pcem`. Before using either as a regression oracle, record the exact
commit and clean/dirty status in the evidence report.

The relevant 86Box implementation points reviewed for this milestone are:

- `src/cpu/cpu.c`: 286 CPU selection installs the 286 opcode tables;
- `src/cpu/386_ops.h`: the 286 `0F` table maps `0F05` to `opLOADALL` and leaves
  `0F04`/other holes illegal; the 286 primary table leaves `64h`–`67h` illegal;
- `src/cpu/386.c`: the opcode-table dispatch path;
- `src/cpu/386_common.c`: the emulator's illegal-opcode exception path.

The executed source-function differential and its controlled-host limitations
are recorded in
[LOADALL_EMULATOR_DIFFERENTIAL_20260916.md](LOADALL_EMULATOR_DIFFERENTIAL_20260916.md).

These observations establish a useful classification reference, not a proof of
silicon behavior. A differential test must compare observable outcomes—memory
transactions, visible registers, hidden-cache effects, exception frame, and
subsequent address translation—rather than copying internal 86Box structure or
timing assumptions. The 86Box project is GPL-2.0; SPK286 remains independently
implemented under its repository policy.

## 9. Deliverables

When this milestone is implemented, the change should include:

- `docs/LOADALL_EVIDENCE.md` with primary-source extracts/paraphrases, page
  references, hashes, silicon scope, and unresolved discrepancies;
- an update to `docs/DECISIONS.md` recording the image-layout, atomicity,
  privilege, and revision decisions;
- an update to `docs/INSTRUCTION_MATRIX.md` for `0F05`, `0F04`, `0F07`, and any
  separately approved undocumented forms;
- a dedicated decoder/LOADALL RTL testbench and a protected-mode testbench;
- a machine-readable image-layout or test-vector artifact where practical;
- a validation receipt covering Icarus/Verilator, lint, synthesis, and
  integration tests;
- a short compatibility note stating exactly which 80286 revision(s) are
  claimed and which historical variations remain unsupported.

## 10. Open questions that block implementation completion

1. Which exact Intel/Harris/AMD 80286 stepping is the compatibility target?
2. Does the target stepping consistently use `0F05` for LOADALL, and how should
   the Intel note's `0F04H` references be interpreted?
3. What are the exact offsets, widths, and semantics of every 102-byte image
   field, especially hidden-cache validity/access bits?
4. What state is committed if a memory cycle is held, aborted, or faulted?
5. What are the exact protected-mode privilege, error-code, and saved-frame
   rules?
6. Do `STOREALL`, ICE entry, and undocumented aliases need separate milestones
   for the chosen Titus/PCAT compatibility target?
7. Which bus-level timing properties are architectural requirements and which
   are implementation policy for SPK286/MiSTer?

No LOADALL implementation should be considered complete while any answer above
is being guessed from a single emulator.

## 11. Primary references

- Intel, *80286 and 80287 Programmer's Reference Manual*, 210498-005 (1987):
  [archived PDF at Bitsavers](https://bitsavers.trailing-edge.com/components/intel/80286/210498-005_80286_and_80287_Programmers_Reference_Manual_1987.pdf).
- Intel, *Undocumented iAPX 286 Test Instruction*:
  [archived technical note at PCjs](https://docs.pcjs.org/manuals/intel/80286/80286_LOADALL.pdf)
  and [HTML transcription](https://www.pcjs.org/documents/manuals/intel/80286/loadall/).
- Intel 80286 exception notes:
  [archived exception reference at PCjs](https://www.pcjs.org/documents/manuals/intel/80286/exceptions/).
- SingleStepTests, [80286 hardware-derived test project](https://github.com/SingleStepTests/80286).
- 86Box, [official source repository](https://github.com/86Box/86Box).
- Intel, *Intel 64 and IA-32 Architectures Software Developer's Manual*:
  [official PDF](https://www.intel.com/content/dam/support/us/en/documents/processors/pentium4/sb/25366821.pdf).
  This later manual is included for terminology only; it is not used to infer
  undocumented 80286 semantics.
