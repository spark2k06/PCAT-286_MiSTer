# Source provenance

This repository is an integration work tree. It retains the selected PCXT
machine source hierarchy and vendors a complete, pinned SPK286 indexed tree.
Normal builds do not read either source checkout.

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

At any integration commit, verify every unchanged PCXT import and the complete
unmodified SPK286 vendor snapshot with:

```sh
python3 scripts/verify_imports.py verify
```

Intentional edits to imported PCXT paths are recorded in
`docs/imports/pcxt-modified-files.txt`. New integration paths are not PCXT
imports and therefore do not appear in the PCXT source manifest.
