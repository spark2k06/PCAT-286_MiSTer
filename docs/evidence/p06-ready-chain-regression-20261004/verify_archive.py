#!/usr/bin/env python3
"""Verify every raw and compressed artifact of the new regression packet."""
import gzip
import hashlib
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = next(parent for parent in OUT.parents
            if (parent / "vendor/spk286").is_dir() and (parent / "docs").is_dir())
DEST = ROOT / "docs/evidence/p06-ready-chain-regression-20261004"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    manifest_path = DEST / "archive-manifest.json"
    manifest = json.loads(manifest_path.read_text())
    names = set()
    for item in manifest["artifacts"]:
        name = item["artifact"]
        if name in names:
            raise RuntimeError("Duplicate artifact " + name)
        names.add(name)
        path = (DEST / name).resolve()
        if not path.is_relative_to(DEST.resolve()):
            raise RuntimeError("Artifact outside exact evidence packet")
        encoded = path.read_bytes()
        if "artifact_bytes" in item and len(encoded) != item["artifact_bytes"]:
            raise RuntimeError("Stored artifact size drift: " + name)
        if sha(encoded) != item["artifact_sha256"]:
            raise RuntimeError("Stored artifact drift: " + name)
        raw = gzip.decompress(encoded) if item["gzip"] else encoded
        if "raw_bytes" in item and len(raw) != item["raw_bytes"]:
            raise RuntimeError("Raw artifact size drift: " + name)
        if sha(raw) != item["raw_sha256"]:
            raise RuntimeError("Raw artifact drift: " + name)
    inventory = {path.relative_to(DEST).as_posix() for path in DEST.rglob("*") if path.is_file()}
    if inventory != names | {"archive-manifest.json"}:
        raise RuntimeError("Archive inventory differs from manifest: " + repr(sorted(inventory ^ (names | {"archive-manifest.json"}))))
    sources = [item for item in manifest["artifacts"] if item["artifact"].startswith("compiled-source/")]
    if len(sources) != manifest["compiled_source_count"]:
        raise RuntimeError("Compiled-source archive count mismatch")
    final = json.loads((DEST / "v3/receipt.json").read_text())
    for item in sources:
        relative = item["artifact"][len("compiled-source/"):]
        if item["gzip"]:
            relative = relative[:-3]
        if final["snapshot_sha256_after"][relative] != item["raw_sha256"]:
            raise RuntimeError("Archived compiled source differs from final receipt")
        if sha((ROOT / relative).read_bytes()) != item["raw_sha256"]:
            raise RuntimeError("Current compiled source differs from final receipt")
    result = {"status": "REGRESSION_ARCHIVE_AND_LIVE_SOURCE_PASS", "artifact_count": len(names),
              "compiled_source_count": len(sources), "corpus_bindings": len(final["corpus_sha256_after"]),
              "manifest_sha256": sha(manifest_path.read_bytes()),
              "verification_script_sha256": sha(Path(__file__).read_bytes()),
              "scope": "Every stored/raw artifact and each archived compiled source versus final receipt/current workspace. Corpus bytes already checked before/after by final regression receipt."}
    result_path = ROOT / "build/p06-ready-chain-regression-20261004-v3/archive-verification.json"
    result_path.parent.mkdir(parents=True, exist_ok=True)
    encoded_result = json.dumps(result, indent=2) + "\n"
    result_path.write_text(encoded_result)
    # The sibling receipt binds the sealed manifest without introducing a
    # circular manifest/receipt hash or an unlisted file inside the packet.
    sidecar = DEST.parent / (DEST.name + "-verification.json")
    sidecar.write_text(encoded_result)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
