#!/usr/bin/env python3
"""Passive verification of the final acceptance receipt supplement."""
import gzip
import hashlib
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = next(parent for parent in OUT.parents if (parent / "vendor/spk286").is_dir() and (parent / "docs").is_dir())
DEST = ROOT / "docs/evidence/p06-ready-chain-regression-20261004-composed"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    manifest_path = DEST / "archive-manifest.json"
    manifest = json.loads(manifest_path.read_bytes())
    assert manifest["status"] == "FINAL_STANDALONE_COMPOSITION_SUPPLEMENT_HASH_VERIFIED"
    assert not manifest["standalone_full_make_regression_executed"]
    names, decoded = set(), {}
    for row in manifest["artifacts"]:
        name = row["artifact"]
        assert name not in names, name
        names.add(name)
        path = (DEST / name).resolve()
        assert path.is_relative_to(DEST.resolve()), name
        stored = path.read_bytes()
        assert len(stored) == row["artifact_bytes"] and sha(stored) == row["artifact_sha256"], name
        raw = gzip.decompress(stored) if row["gzip"] else stored
        assert len(raw) == row["raw_bytes"] and sha(raw) == row["raw_sha256"], name
        decoded[name.removesuffix(".gz") if row["gzip"] else name] = raw
    assert len(names) == manifest["artifact_count"]
    assert {path.relative_to(DEST).as_posix() for path in DEST.rglob("*") if path.is_file()} == names | {"archive-manifest.json"}
    composed = json.loads(decoded["native/composed-receipt.json"])
    review = json.loads(decoded["review/spk286-ready-chain-composed-independent-review-20261004.json"])
    assert composed["status"] == manifest["composed_status"] == "STANDALONE_COMPOSED_GATES_PASS"
    assert sha(decoded["native/composed-receipt.json"]) == manifest["composed_receipt_sha256"] == review["composed_receipt_sha256"]
    assert composed["shared"]["vendor_receipt_sha256_at_compose"] == manifest["broad_receipt_sha256"] == review["broad_receipt_sha256"]
    assert composed["fresh"]["commands"] == manifest["fresh_native_commands"] == 33
    for key, name in (("main_receipt_sha256", "receipt.json"), ("native_receipt_sha256", "smoke-state-receipt.json")):
        assert composed["fresh"][key] == sha(decoded["native/" + name])
    for key, name in (("snapshot_manifest_sha256", "manifest.json"), ("regression_scope_audit_sha256", "regression-scope-audit.json"),
                      ("composer_sha256", "compose_receipt.py")):
        assert composed[key] == sha(decoded["native/" + name])
    for prefix in ("spk286-ready-chain-composed", "spk286-ready-chain-sentinel", "spk286-ready-chain-portable-archive"):
        base = "review/" + prefix + "-independent-review-20261004"
        receipt = json.loads(decoded[base + ".json"])
        key = "reviewer_source_sha256" if "reviewer_source_sha256" in receipt else "reviewer_sha256"
        assert receipt[key] == sha(decoded[base + ".py"])
    linked = (("broad_manifest_sha256", "broad-archive-manifest.json", "p06-ready-chain-regression-20261004/archive-manifest.json"),
              ("historical_fresh_manifest_sha256", "historical-fresh-archive-manifest.json", "spk286-ready-chain-20261004/fresh-archive-manifest.json"))
    for key, archived, current in linked:
        assert sha(decoded["linked/" + archived]) == manifest[key]
        assert sha((DEST.parent / current).read_bytes()) == manifest[key]
    assert sha(decoded["linked/portable-final-manifest.json"]) == manifest["portable_manifest_sha256"]
    portable_review = json.loads(decoded["review/spk286-ready-chain-portable-archive-independent-review-20261004.json"])
    assert portable_review["manifest_sha256"] == manifest["portable_manifest_sha256"]
    broad_review = json.loads(decoded["review/p06-ready-chain-regression-archive-independent-review-20261004.json"])
    assert broad_review["manifest_sha256"] == manifest["broad_manifest_sha256"]
    result = {"status": "FINAL_STANDALONE_COMPOSITION_SUPPLEMENT_PASS", "artifact_count": len(names),
              "manifest_sha256": sha(manifest_path.read_bytes()), "verification_script_sha256": sha(Path(__file__).read_bytes()),
              "broad_manifest_sha256": manifest["broad_manifest_sha256"], "composed_status": composed["status"],
              "scope": "Passive local exact inventory/raw/stored bytes and receipt/helper/sibling manifest binding. No new tests or source edits."}
    (DEST.parent / (DEST.name + "-verification.json")).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
