# P06: source-bound 80286 encoding preview

The historical target handoff can qualify one instruction's full encoding
without executing it. `spk286_encoding_preview` accepts only target-epoch bytes
selected by its caller. It has no GPR, FLAGS, segment, operand, memory-write or
event-commit interface. Ordinary execution receives the retained bytes through
the separate replay boundary.

## Shared syntax and functional equivalence

Compiler 27.2 derives `micro_instruction_syntax(entry)` from the validated
canonical microcode acquisition operations. The seven bits describe known
entry, ModR/M, conditional port byte, decoded dispatch and trailing bytes.
Acquisition micro-PCs bind the metadata to source statements. Optimized
accumulator ALU and its validated old immediate-fetch tail count one immediate;
far immediates count four bytes and ENTER counts three.

The existing functional decoder and group dispatcher have a `SYNTAX_ONLY`
parameter, default zero. Each existing microcode-entry leaf selects either its
original entry or the generated syntax constant. Opcode/group predicates are
unchanged. This avoids another opcode table and lets synthesis fold the syntax
at each leaf instead of composing a large decoded-entry lookup. Prefix context
and 16-bit ModR/M displacement size reuse the existing functional modules.

Default decoder/group selectors and entries match frozen commit
`b155891c215a1a4048e7b531ba4bfcfd8582f0d4` for 49,152 combinations in both
Icarus and Verilator. Syntax-mode non-entry outputs also match, and every
qualified syntax leaf equals the generated shape for the original entry.

## Preview contract

- `start` resets the stream and takes no byte on that edge. `cancel` discards
  context and requires another start. The caller owns redirect-epoch isolation.
- Only `byte_valid && byte_ready` counts a byte. `length[3:0]` includes prefixes
  and the 0F escape, up to ten bytes. An eleventh byte is never accepted.
- `complete` and its reason persist until reset, cancel or start. `valid_length`
  means a known full syntactic encoding. Other terminal reasons are the existing
  decoder's invalid-opcode classification, unsupported functional form,
  overlength, or caller-qualified `abort_fetch`.
- `abort_fetch` consumes no byte. Partial bytes and the fault remain successor
  work; the caller must preserve them for ordinary replay/fault delivery.
- Syntactic completion does not certify semantic validity. LOCK rules,
  memory-only forms, privilege and operand faults stay in ordinary execution;
  their existing architectural predicates were not extracted or changed.
- The existing prefix context is reused exactly, including its extended-map
  prefix behavior. Nested future dispatch shapes are rejected as unsupported;
  no fabricated length or historical delay is substituted.

## Verification and generic cost

| Check | Result |
| --- | --- |
| Canonical generated-file consistency | PASS |
| Focused Python syntax tests | 4 PASS |
| Existing microcode compiler tests | 114 PASS |
| Strict standalone Verilator lint | PASS |
| Encoding stream vectors, each simulator | 3,110 PASS |
| Default functional/syntax equivalence, each simulator | 49,152 PASS |
| Source identity before/after focused proof | PASS |
| Flattened Yosys synthesis/check | PASS |

The stream vectors include all 256 ModR/M encodings for twelve forms/groups/maps,
immediate-port versus DX forms, mixed/far immediates, prefixes, invalid and
unsupported forms, enable/cancel, stable terminal outputs and fetch abort.

| Isolated boundary | Generic cells | Register bits |
| --- | ---: | ---: |
| Preview including shared decoder logic | 1,039 | 36 |
| Preview and ten-byte target replay | 1,284 | 128 |
| Same wrapper disabled at elaboration | 0 | 0 |

These are Yosys generic counts, not Cyclone V ALMs or a timing/fit result.
Elaboration-disabled MAX is a removal control; selecting MAX dynamically in an
OSD does not remove historical-profile hardware. The initial intermediate-entry
design cost 2,461 generic cells after flattening; constant-folded shared leaves
reduce the accepted preview count by 57.8%.

The accepted focused packet is
[`docs/evidence/p06-encoding-preview-20261005/manifest.json`](../evidence/p06-encoding-preview-20261005/manifest.json).
It contains frozen source, literal baseline decoder controls, benches, exact
logs and generic netlists. The runner is
`scripts/test_spk286_encoding_preview.py`. Compile-portability/PCH failures from
development are recorded separately and superseded by the accepted proof.

The new preview bank is registered in the standard CPU unit and lint paths;
focused syntax tests also run before the broad tests. With the separately proven
portable length-boundary bank, the registry contains 132 Icarus banks and 131
Verilator banks (the pre-existing full expand-down bank has its recorded
Verilator skip). Full CPU regression was started, then explicitly deferred by
the user; its partial packet is marked USER_DEFERRED. Integrated historical
handoff checks and the bounded raw-CPU follow-up are separate gates; this encoding
packet does not claim them.
