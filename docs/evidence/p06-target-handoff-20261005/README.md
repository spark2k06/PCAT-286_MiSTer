# Historical target handoff: directed evidence

Date: 2026-10-05. The packet preserves the source-retained historical deadline,
metadata and replay unit checks, and the original exact B0/branch comparison.
It does not replace the complete CPU regression or fitted resource/timing work.

The [manifest](manifest.json) binds all 824 members. The [verification](verification.json)
rechecks source identities, all 304 run metrics, 152 complete paired traces and
208,327 applicable paired rows. It preserves 3,724 declared empty-head
four-state differences without altering architectural or accepted bus data.

Verify from the repository root:

```powershell
python -B scripts/verify_p06_target_handoff_evidence.py --evidence docs/evidence/p06-target-handoff-20261005
```

For an isolated reproduction, extract the tar into a fresh disposable directory
under `build`. Its `source` subtree is a complete source-bound CPU fixture;
no production file needs replacement. In WSL, run its builder at
`source/build/p06-target-b0-20261005-v2/branch_probe.py`. The builder derives
its root from that location and compiles only the archived source subtree.
It recreates the complete COM images and reruns both simulators at all four
profiles. The unchanged COM guard is
`006a7be0bd962859bf929e6b0d6678c400607461ed095c9e164789acf05f2643`.

`unit/focused-v6` is the accepted final controller/scheduler/replay result;
`unit/metadata-v2` is the final source-bound exhaustive metadata result.
`superseded` contains historical receipts and the first B0 compiler-portability
failure only. It also records an initial archive omission rejected by the
verifier and corrected before acceptance. No superseded attempt is release
acceptance. Compiler objects and executable binaries are excluded.
