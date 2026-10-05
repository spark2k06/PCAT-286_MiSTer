# Phase 7 functional-delivery recovery — 2026-09-09

This guide covers the integrated D-037 functional delivery. The older closure
archive remains preserved and is a historical input, not the delivered source.
The final functional package is `.cache/phase7-functional-20260909.zip`; its
adjacent `.zip.sha256` file and `build/phase7-functional-package.json` record its
exact digest, size, source/manifests and delivered Git commit. The post-delivery
receipt `build/phase7-functional-delivery.json` records the base, implementation,
delivery, remote and actual CI identities without circular commit hashes.
The package constructor is preserved as
[`phase7_functional_package.py`](phase7_functional_package.py); it requires the
clean delivered checkout and the documented retained validation directories.
The packaged delivery receipt records the state observed at package creation.
Later CI and recovery observations are appended to the external delivery receipt;
a queued or running workflow in the package is not reported as a successful run.

## Package contents and trust checks

- `source/` contains canonical Git blobs from the delivered commit, with exactly
  the paths and byte hashes in `source-manifest.json`.
- `file-modes.json` contains the Git executable/regular file modes; the recovery
  helper validates and restores them.
- `executable-inputs.json` and `policy-inputs.json` contain the independently
  approved 337 executable and 10 policy inputs. Every entry must also match the
  full source manifest.
- `evidence/phase7-functional-full-1/` retains the complete executable receipt,
  every receipt-bound artifact, physical reports and identities, detailed
  pristine/mutation/comparator logs, synthetic results, batches and binaries.
- Other `evidence/` directories retain the independent reviewer experiments,
  emulator harness, focused verification and separately identified failed
  preparation attempts. Those attempts are not reported as successful runs.
- `references/` preserves the exact original E7 source, pinned reader/reference
  information, and attributed 86Box original files/license. The complete corpus
  is acquired with the pinned repository fetch workflow; it is not in this ZIP.
- `SHA256SUMS` must exactly enumerate all other payloads. The helper verifies
  every payload before extraction, rejects unsafe paths and never overlays an
  existing destination.

The manifest equality establishes the reviewed executable/policy identity across
final documentation and review metadata. The full source manifest and Git tree
identify those additional delivery files separately.

## Restore and finalize retained evidence

Use the exact recorded digest and a previously absent child of the selected
workspace's `build` directory. Inspect
[`phase7_functional_recovery.py`](phase7_functional_recovery.py) and its preserved
[`phase7_closure_recovery.py`](phase7_closure_recovery.py) dependency before use.
For example, on a native Linux filesystem:

```sh
mkdir -p /tmp/spk286-functional-recovery-workspace
python3 docs/phase7_functional_recovery.py \
  --archive "$PWD/.cache/phase7-functional-20260909.zip" \
  --sha256 "<exact recorded archive SHA256>" \
  --workspace /tmp/spk286-functional-recovery-workspace \
  --destination /tmp/spk286-functional-recovery-workspace/build/restore-1 \
  --require-native-modes
cd /tmp/spk286-functional-recovery-workspace/build/restore-1/source
git init
git add --all
python3 -m tools.phase6_inputs --manifest ../executable-inputs.json --check
python3 -m tools.phase7_policy --manifest ../policy-inputs.json --check
make microcode-check
SPK286_PHASE7_RECEIPT=../evidence/phase7-functional-full-1/execution-receipt.json make phase7-check
```

An isolated Git index is necessary because executable input enumeration uses
`git ls-files`. Staging this isolated recovered tree does not modify the actual
development checkout. Choose a new restore suffix on every attempt.

DrvFS without metadata can expose every Windows file as mode `0777`; this is not
evidence that recorded `0644`/`0755` modes were retained. Use native WSL storage
with `--require-native-modes` to verify the actual modes, as done for delivery.
The helper still checks canonical source/mode manifests on either filesystem.

Retained-result finalization verifies every receipt artifact, unchanged sources
and policy, the completed stages, population and scoped independent approval.
It does not claim a new simulator replay. To run a new complete validation, use
the normal documented toolchain, `make mcl86-fetch singlestep-fetch`, and
`SPK286_BUILD_JOBS=4 SPK286_BUILD_DIR="$PWD/build/fresh-phase7" make phase7-check`
with an absent output directory. This runs all required executable work again.

Strict evidence remains separate: `make phase7-evidence-check` reports the five
authorized open notes and fails the physical-completeness criterion. It does
not invalidate the reviewed functional baseline or authorize Phase 8 code here.
