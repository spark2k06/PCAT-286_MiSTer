# SPK286 absent-segment correction import — 2026-09-29

Upstream: `7a0ed7029292b47e6ba1a2de93a9afb2be9b2eef` on SPK286 branch
`codex/protected-mode-windows31`.

The next Windows 3.1 trace advanced past the earlier direct-CALL failure.
It then reported #GP(0447) at `043F:9525`, calling absent code at `0447:0B7E`.
The captured LDT descriptor is `2F 04 90 82 1F 7B 10 00`. Its final word is
ignored for 286 code/data descriptors, and the correct exception is #NP(0444).

The imported parser and executor changes correct segment upper-word handling,
direct code type/privilege/presence ordering, and selector error encoding.
The expanded test checks normal calls, negative cases and a guest #NP handler
which loads a segment and IRETs to retry CALL successfully. The descriptor
foundation test follows the Intel evidence documented upstream. The existing
downstream fetch-wrap correction remains intact.

Validation in this vendor tree:

- Direct CALL / #NP retry: 300 checks / 144 cases in both simulators.
- Descriptor foundation: 65,573 checks in both simulators.
- Verilator RTL lint and generated microcode consistency pass.
- 86Box WSL Release build completes using this vendor source.

Upstream also passes the incoming task-state bank (202 checks / 36 cases)
and protected-system bank (538 checks), each in both simulators. The incoming
task-state test is not part of this older vendor test suite; it was updated
and run upstream. Full regression and synthesis were not run, per the user's
request for bounded validation. Windows desktop startup still needs the next
manual integration run.

Evidence: `vendor/spk286/build/descriptor-np-*.log`, upstream files with the
same prefix, and `86box_dev/build/spk286/descriptor-np-build.log`.
