# Phase 7 shift/rotate semantics and physical flag policy

This is an implementation decision for the 42 documented C0/C1/D0/D1/D2/D3
families (/0–5 and /7). Undocumented /6 remains outside the claimed scope.
The isolated prototype passed all 210,000 pinned physical records; the integrated
gate and its exact source identity are recorded separately in PHASE7_HANDOFF.md.

## Architectural rules

Intel 210498-005 Appendix B, B-90/B-91 and B-97/B-98, specifies the five-bit
count, unchanged FLAGS for a zero count and single-count OF. OF for multiple
shifts/rotates and AF for shifts are undefined. Rotations preserve SF/ZF/AF/PF;
shifts update SF/ZF/PF. Through-carry rotations use the operand plus CF as a
nine- or seventeen-bit ring. Undefined bits are an explicit implementation
choice; their selected physical behavior is not promoted into an Intel guarantee.

The arithmetic service snapshots the operand, width, kind, carry and masked
count. Each busy cycle performs an elementary bit operation. This implements
a real dependency, not historical timing padding. Pause freezes progress;
response backpressure, reset and cancellation have explicit ownership rules.
No historical cycle-accuracy claim follows from this iteration count.

Zero count still requires the normal operand read and limit check. Captures
show memory reads without a data write; a word at offset FFFF still faults.
Consequently microcode obtains the operand even at zero count, while the
service marks the result as discarded and commits no FLAGS bits. CL is obtained
before the operand, so CL/CX destination aliases use the original count. Immediate
bytes are acquired before data access, preserving overlength fault order.

## Evidence for undefined OF

The first full prototype run executed 210,000 records and failed 13,166, confined
to D2/D3 SHL/SHR/SAR. It preserved OF at counts other than one. The reduced
original case D2.4 index 2, hash `a330abb69ab6128bbdb627931f05a38843c0cd0e`,
has operand 66, CL C5 (masked count 5), result C0, initial FLAGS 0452 and
expected FLAGS 0C86 under mask FFEF. A VCD showed candidate FLAGS 0884 but
commit mask 00C5: OF was computed but incorrectly excluded from the selected
physical policy. AF's raw difference was outside the physical mask.

The retained [analysis record](phase7_shift_flag_observations.json) checks
90,000 original records across the 18 SHL/SHR/SAR files against the independent
upstream parser, including the wire RMSK/EXCP fields. It contains 89,704 normal
flag comparisons and 296 faults. A final-elementary-step OF hypothesis has
zero differences under the original masks. Its raw AF-zero hypothesis differs
in 62,849 unmasked comparisons; that is not an exact raw-FLAGS pass and does not
justify changing the implementation's preserved AF policy.

| Files | Captured mask | Implementation policy |
|---|---|---|
| C0/C1 SHL, SHR | F7EE | Deterministic final-step CF/OF; masks do not adjudicate these bits |
| C0/C1 SAR | F7EF | CF from final step; OF zero; AF preserved |
| D0/D1 SHL, SHR | FFEF | Defined single-count CF/OF; AF preserved |
| D0/D1 SAR | F7EF | CF from final step; OF zero; AF preserved |
| D2/D3 SHL, SHR, SAR | FFEF | Final-step CF/OF for every nonzero count; AF preserved |

For nonzero rotations, the separate full-domain physical analysis agrees with
the final-step OF: result sign XOR CF for left rotations, or the two highest
result bits XOR for right rotations. All zero-count flag bits remain unchanged.
The 210,000-record RTL rerun then passed with zero skips, revocations or failures.
No expected result, captured transaction or comparison mask was changed.

## Reproduction and limits

The pinned corpus revision remains `37c73caf53dcd22d3dd369ff09305d13d117a4fe`.
The original failure, reduced VCD and successful rerun are retained under
`build/phase7-preparation`; they are not relabeled as one passing run.

- Failed physical log SHA256: `054b0405276dd97f644347542e1a0f853dafef05aed1915f8b2db9611388bb13`.
- Reduced VCD: `shift-d2-4-index2.vcd`; original input snapshot: `shift-first-inputs.json`.
- Corrected physical log SHA256: `3e93ea5bd93877494ef7f1d231a4c978f5cc9cf53a895640ee6ca73a561951e7`.
- An intermediate invocation failed before execution because it used the wrong
  corpus environment variable; the fresh successful command passes `--repo`
  explicitly. That invocation provides no physical pass evidence.

The independent mathematical oracle uses closed-form integer arithmetic rather
than duplicating the RTL's bit recurrence. Directed tests cover 154,112 arithmetic
vectors and 12,222 complete CPU cases, with count boundaries, byte aliases,
READY, immediate starvation, memory limits and zero-count traffic. Mutation
audits must reject intended defects with pristine controls. Complete Phase 7,
independent architectural review and historical timing remain separate gates.
