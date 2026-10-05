# Recovery of the reviewed Phase 7 closure candidate

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

This procedure reconstructs the **blocked, unintegrated** candidate and its
evidence. Recovery is not integration or architectural approval. See the
[closure dossier](PHASE7_CLOSURE_20260909.md) for current status.

The new local package is `.cache/phase7-closure-20260909.zip`. Its archive SHA256
and actual verified-restoration result are recorded under `closure_20260909` in
[the candidate validation record](phase7_pending_candidate_validation.json).
The archive contains its own `SHA256SUMS` for every payload; its external archive
hash, internal payload hashes, source manifests and Git delivery SHA are distinct.
Archives, raw corpus files and build products are local recovery artifacts and
are not committed to Git. Preserve this package alongside the two original
archives; the original source/packages/logs were not overwritten.

Actual archive SHA256:
`83b339bc38437255091b2e486a9d481c21d3d36091c40e265cb3797b7e705c8c`.
Restoration completed at 2026-09-09 11:12:56 UTC: all **1,663 payload hashes**, the
412-file candidate and all 328 indexed executable inputs matched. The restored
three completion tests and deterministic microcode check passed. Receipt:
`build/phase7-closure-20260909-main/closure-restoration-result.json`.
The package's bundled top-level documentation predates its own external archive
hash/restoration/Git receipts; this delivered guide and validation JSON record
those completed operations without rewriting the frozen source image.

Run from the delivered repository in WSL Ubuntu-24.04, using an absent output
directory. The tested restoration directory is already occupied after this
session; choose a different absent name for another restoration.

```bash
python3 docs/phase7_closure_recovery.py \
  --archive .cache/phase7-closure-20260909.zip \
  --sha256 "$(python3 -c 'import json; print(json.load(open("docs/phase7_pending_candidate_validation.json"))["closure_20260909"]["recovery"]["archive_sha256"])')" \
  --workspace . \
  --destination build/phase7-closure-restored-next
```

The helper verifies the complete ZIP and all payload hashes before extraction,
rejects absolute/traversal paths, duplicate/case-colliding names, symlinks and
special entries, and refuses an existing destination or a destination outside
the explicitly selected workspace. It does not reset, delete or overlay files.
It then verifies the restored 412-file source and 328-file executable manifests.
Safe executable bits are retained for direct POSIX script invocation; setuid,
setgid, sticky and group/other write bits are not restored.

The restored directory has a repository-shaped layout:

- `build/phase7-closure-20260909-final-candidate`: the complete final 412-file
  snapshot, including generated microcode, tests, scripts and evidence records.
- `build/phase7-closure-20260909-main`: manifests, new commands/results/logs,
  exact four-file correction patch, diagnostic batch/identities, source research
  and updated local E7 draft.
- `build/phase7-closure-20260909-review`: original independent reports, supporting
  source experiments and logs. Compiled executables are omitted and reproducible.
- `build/phase7-preparation`: selected original manifests, result/log records and
  the original E7 draft/reproducer; the original complete archives remain separate.
- `.cache/intel286`: inspected primary documents; `.cache/singlestep-80286`
  contains the pinned E7 input and provenance required for its reduced diagnostic,
  not the entire physical corpus.

Source identity: `delivery-source-manifest.json` SHA256
`b4f8a5af3139c8d804438928a9a741c25fdf6a0cde85b1a1f2305312980274d1`.
Executable identity: `final-executable-inputs.json` SHA256
`f5da66b8427b83d44aa2da2b61e70105d072564653b17793dbf2359dcf76adba`.
All 328 executable inputs equal the corrected 409-file candidate used for the
new regression. Evidence-only overlays explain the final 412-file snapshot.

To use the project's Git-based input fingerprint helper, initialize a **new local
index inside the restored candidate**, not the production repository:

```bash
cd build/phase7-closure-restored-next/build/phase7-closure-20260909-final-candidate
git init -b codex/phase7-restored-local
git config core.autocrlf false
git add .
python3 -m tools.phase6_inputs \
  --manifest ../phase7-closure-20260909-main/final-executable-inputs.json --check
python3 -m unittest tests.test_phase7_completion
make microcode-check
```

No commit is required for fingerprinting. The independent repository/index is
necessary because the production repository ignores `build/`; running the helper
inside an unindexed ignored directory can otherwise yield an empty inventory.
The ZIP preserves exact source bytes, including original line endings. The
separate `review-corrections.patch` uses UTF-8 LF text consistent with
`.gitattributes`; its application was tested against an absent isolated copy of
the original four files. It is supplemental provenance, not a replacement for
the full source image. Never apply it over the original frozen candidate or an
already corrected candidate.

For a fresh regression, use a new `SPK286_BUILD_DIR`, set
`SPK286_SINGLESTEP_ROOT` to the complete pinned corpus, and run `make regression`.
Required tools used here: Python 3.12.3, Verilator 5.020, Icarus 12.0 and Yosys
0.33 on Ubuntu-24.04. New heavy jobs used `SPK286_BUILD_JOBS=4` where supported
and were serialized. Exact commands, versions and durations are in run receipts;
old absolute log paths identify their original execution locations.

To obtain the full corpus, follow the candidate's pinned `singlestep-fetch`
workflow into a separate cache or use the existing verified cache. Retain
revision `37c73caf53dcd22d3dd369ff09305d13d117a4fe` and verify its input hashes.
The complete Phase 7 gate is expected to remain blocked at REP zero-count
evidence and strict E7 admission. A restored candidate must not be labelled
approved merely because focused tests pass.
