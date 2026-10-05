# Source provenance

This repository is an integration work tree. It retains the selected PCXT
machine source hierarchy and vendors a complete, pinned SPK286 indexed tree.
Normal builds do not read either source checkout.

## Current SPK286 synchronization

The current portable CPU mirror is recorded independently in
`docs/imports/current-spk286.json`, with its upstream commit, canonical Git
blob/SHA256 identities and retained consumer files. The original import
manifests below remain historical records.

Synchronize from a clean standalone checkout and verify it with:

```sh
python3 -B scripts/sync_spk286_vendor.py --source /path/to/SPK286 --sync
python3 -B scripts/sync_spk286_vendor.py --source /path/to/SPK286 --check
```

The whole `vendor/spk286/rtl/timed/` directory is the PCAT-generated timing
overlay. Its source hashes are recorded and it is preserved during mirroring.
Use the PCAT root generator and qualification tools for this overlay. The
mirrored standalone generator's default `rtl/timed` output and installed-
profile checker target the standalone variant and must not overwrite or
qualify the consumer variant. Other vendor-only paths are retained explicitly
in the current ledger.

The snapshot sections below describe the original import. Subsequent CPU
updates include the [2026-09-22 LOADALL integration](AT_HIMEM_LOADALL.md),
selectively imported from SPK286 `aa922e53a579db17c67aeba37962a3683353813c`.
The original `spk286-9d3a69eb.sha256` manifest is historical and is not a hash
manifest of the updated CPU; it has not been silently regenerated.

## PCXT machine baseline

- Source directory at import time: `D:/GitHub/PCXT-EGA_MiSTer_devel`.
- Upstream URL: `https://github.com/MiSTer-devel/PCXT-EGA_MiSTer.git`.
- Selected branch at import time: `main` (clean working tree).
- Selected commit: `c6b4dc8107bade3f41d94599720bd82706331c4e`.
- Commit date and subject: 2026-09-04, `Document partial Mode X support`.
- Import policy: every tracked path except `games/` and `releases/` was copied
  at the selected commit. Those exclusions avoid importing an upstream hard-disk
  image and historical compiled RBF files; they are not build inputs.
- License: the imported root `LICENSE` and all component notices are preserved.
- Original file hashes: `docs/imports/pcxt-c6b4dc81.sha256`.

The attached directory differs from the preparation-time checkout named in the
specification. The current clean, associated `*_devel` checkout was selected
deliberately; no interface assumptions from revision
`7bbdbbbe5ba1c2737da88943bbc668f5520faa31` or the unavailable preparation path
were mixed into the integration.

## SPK286 CPU snapshot

- Source directory at import time: `D:/GitHub/SPK286`.
- Upstream URL: `https://github.com/spark2k06/SPK286.git`.
- Branch at import time: `codex/phase7-realmode-completion`.
- Base commit: `e2bc4a7839cd0aa594b543d8dcaaf253c310a63a`.
- Imported indexed-tree object: `9d3a69eb0e9d7bed32a9a8672a3ce8b464865101`.
- Source condition: 110 staged paths over the base commit and no unstaged
  changes. HEAD alone is not the selected CPU delivery.
- Import policy: all 434 indexed files were copied under `vendor/spk286/`.
  Ignored build outputs, caches, external SingleStep corpora and `.git` metadata
  were not imported.
- Original file hashes: `docs/imports/spk286-9d3a69eb.sha256`.
- Licensing: SPK286 did not contain a root license file in the selected tree;
  its existing notices are preserved without inventing a license.

The selected tree contains the complete RTL, SPK286 BIU and prefetch path,
authoritative `.mc` inputs, compiler/audit tools, generated package/ROM/listing,
tests, documentation and evidence records. The user's integration acceptance
explicitly treats the five D-026/D-037 notes as nonblocking and does not require
Phase 8 completion. They remain recorded in `docs/KNOWN_LIMITATIONS.md`.

## Reproduction and integrity

At the import commit, regenerate the manifests with:

```sh
python3 scripts/verify_imports.py write \
  --pcxt-source /mnt/d/GitHub/PCXT-EGA_MiSTer_devel \
  --spk-source /mnt/d/GitHub/SPK286
```

At the original import commit, verify the then-unmodified source snapshots
with:

```sh
python3 scripts/verify_imports.py verify
```

Intentional edits to imported PCXT paths are recorded in
`docs/imports/pcxt-modified-files.txt`. New integration paths are not PCXT
imports and therefore do not appear in the PCXT source manifest.

The PCXT README and AT286CTL reference are adapted only to remove inherited
MCL86/8088 claims and describe the PCAT-286 menu contract. Their originals are
identified by the PCXT manifest and selected commit. Production RTL changes
are kept in new `PCAT-286*`, `files_pcat286.qip`, `Chipset_SPK286.sv`,
`Bus_Arbiter_SPK286.sv` and `rtl/spk286_integration/` paths; the corresponding
PCXT originals remain present.

The passive SPK286 display methodology in
`rtl/common/spk286_debug_overlay.sv` is adapted from the user's
`D:/GitHub/PCXT_MiSTer_devel` branch `test/crtc-debug`, commit
`f553fb076f102e81c5e58dee4a9c2ea2a2ce9af5` (`Add CRTC Debug Overlay with OSD
toggle`). The new file records that source and license in its header. The
imported `rtl/common/common.qip` is changed only to register the new source and
is therefore listed explicitly in `docs/imports/pcxt-modified-files.txt`.

## Consumer-side SPK286 timing variant

Historical initial-import variant: the then-complete `vendor/spk286/` snapshot
remained byte-for-byte unchanged. The
PCAT-286 QIP substitutes
`rtl/spk286_integration/spk286_operand_timing.sv` for the vendored
`spk286_operand.sv`. It factors the `done` expression around the registered
pending state, removing a false combinational dependency from an accepted
memory response without adding a register or changing cycle behavior.

`scripts/test_i5_timing_equivalence.sh` compares every output and internal
state element of the two implementations for directed cases and 50,000
randomized cycles in both Icarus and Verilator. This generic refactor is a
candidate for a later SPK286 upstream change. The XT bridge, local reset
release, bus pacing and machine timing constraints are consumer-specific and
do not belong in the CPU repository.
