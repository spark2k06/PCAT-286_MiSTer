#!/usr/bin/env python3
"""Preserve final native-port acceptance beside the immutable broad packet."""
import gzip
import hashlib
import json
from pathlib import Path
import shutil

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
DEST = ROOT / "docs/evidence/p06-ready-chain-regression-20261004-composed"
NATIVE = ROOT / "build/spk286-ready-chain-standalone-gates-20261004-v1"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def main():
    broad_manifest = ROOT / "docs/evidence/p06-ready-chain-regression-20261004/archive-manifest.json"
    broad_receipt = OUT / "receipt.json"
    broad_verify = ROOT / "docs/evidence/p06-ready-chain-regression-20261004-verification.json"
    historic = ROOT / "docs/evidence/spk286-ready-chain-20261004/fresh-archive-manifest.json"
    portable = NATIVE / "portable/docs/evidence/ready-chaining-20261004/manifest.json"
    composed_path = NATIVE / "composed-receipt.json"
    composed = read(composed_path)
    independent_path = ROOT / "build/spk286-ready-chain-composed-independent-review-20261004.json"
    independent = read(independent_path)
    sentinel_path = ROOT / "build/spk286-ready-chain-sentinel-independent-review-20261004.json"
    sentinel = read(sentinel_path)
    portable_review_path = ROOT / "build/spk286-ready-chain-portable-archive-independent-review-20261004.json"
    portable_review = read(portable_review_path)
    broad_review_path = ROOT / "build/p06-ready-chain-regression-archive-independent-review-20261004.json"
    broad_review = read(broad_review_path)
    assert read(broad_receipt)["status"] == "SPK286_READY_CHAIN_REGRESSION_PASS"
    assert read(broad_verify)["status"] == "REGRESSION_ARCHIVE_AND_LIVE_SOURCE_PASS"
    assert read(broad_verify)["manifest_sha256"] == digest(broad_manifest)
    assert composed["status"] == "STANDALONE_COMPOSED_GATES_PASS"
    assert independent["status"] == "STANDALONE_COMPOSED_INDEPENDENT_REVIEW_PASS"
    assert independent["composed_receipt_sha256"] == digest(composed_path)
    assert independent["broad_receipt_sha256"] == digest(broad_receipt)
    assert composed["shared"]["vendor_receipt_sha256_at_compose"] == digest(broad_receipt)
    assert sentinel["status"] == "STANDALONE_SENTINEL_ADAPTER_INDEPENDENT_REVIEW_PASS"
    assert portable_review["status"] == "STANDALONE_PORTABLE_ARCHIVE_INDEPENDENT_REVIEW_PASS"
    assert portable_review["manifest_sha256"] == digest(portable)
    assert broad_review["manifest_sha256"] == digest(broad_manifest)
    assert not composed["standalone_full_make_regression_executed"]
    for key, filename in (("main_receipt_sha256", "receipt.json"),
                          ("native_receipt_sha256", "smoke-state-receipt.json")):
        assert composed["fresh"][key] == digest(NATIVE / filename)
    assert composed["snapshot_manifest_sha256"] == digest(NATIVE / "manifest.json")
    assert composed["regression_scope_audit_sha256"] == digest(NATIVE / "regression-scope-audit.json")
    assert composed["composer_sha256"] == digest(NATIVE / "compose_receipt.py")
    for prefix in ("spk286-ready-chain-composed", "spk286-ready-chain-sentinel", "spk286-ready-chain-portable-archive"):
        data = read(ROOT / ("build/" + prefix + "-independent-review-20261004.json"))
        key = "reviewer_source_sha256" if "reviewer_source_sha256" in data else "reviewer_sha256"
        assert data[key] == digest(ROOT / ("build/" + prefix + "-independent-review-20261004.py"))
    if DEST.exists():
        raise RuntimeError("Fresh sibling directory required; sealed packets must not be overwritten")
    DEST.mkdir(parents=True)
    records = []

    def add(path, name):
        path = Path(path)
        raw = path.read_bytes()
        compress = path.suffix in (".json", ".log") and len(raw) > 4096
        stored_name = name + (".gz" if compress else "")
        target = DEST / stored_name
        if target.exists():
            raise RuntimeError("Duplicate artifact: " + stored_name)
        target.parent.mkdir(parents=True, exist_ok=True)
        if compress:
            target.write_bytes(gzip.compress(raw, mtime=0))
        else:
            shutil.copyfile(path, target)
        stored = target.read_bytes()
        assert (gzip.decompress(stored) if compress else stored) == raw
        records.append({"artifact": stored_name, "original_path": path.relative_to(ROOT).as_posix(),
                        "raw_sha256": hashlib.sha256(raw).hexdigest(), "raw_bytes": len(raw),
                        "artifact_sha256": hashlib.sha256(stored).hexdigest(), "artifact_bytes": len(stored),
                        "gzip": compress})

    # Exact receipts and original-path helpers; this supplement adds no tests.
    native_names = ("compose_receipt.py", "composed-receipt.json", "external-post-gates-check.json",
                    "FINAL_REPORT.md", "manifest.json", "prepare_portable.py", "receipt.json",
                    "regression-scope-audit.json", "run_gates.py", "run_smoke_state.py",
                    "smoke-state-receipt.json", "stage-inventory.json")
    for name in native_names:
        add(NATIVE / name, "native/" + name)
    for prefix in ("spk286-ready-chain-composed", "spk286-ready-chain-sentinel", "spk286-ready-chain-portable-archive",
                   "p06-ready-chain-regression-archive"):
        for extension in (".py", ".json"):
            name = prefix + "-independent-review-20261004" + extension
            add(ROOT / "build" / name, "review/" + name)
    add(broad_manifest, "linked/broad-archive-manifest.json")
    add(broad_verify, "linked/broad-verification.json")
    add(historic, "linked/historical-fresh-archive-manifest.json")
    add(portable, "linked/portable-final-manifest.json")
    add(__file__, "archive_composed.py")
    add(OUT / "verify_composed.py", "verify_composed.py")
    readme = """# Final standalone composition supplement

This sibling packet preserves the final standalone/native-port acceptance,
sentinel adapter review, portable overlay review and independent broad archive
review. It supplements the immutable `../p06-ready-chain-regression-20261004`
and historical `../spk286-ready-chain-20261004` packets; neither was rewritten.

The final broad gate actually ran vendor `make regression` with all new
functional executions and vectors. Seventy verified Verilator compilations
were reused; its full scope and failed prior attempts remain in the main packet.
Standalone acceptance composes exact shared CPU/test/vector identities with
33 fresh native stages. It is not a literal standalone full make regression,
native pin timing certificate, physical hardware test or timing closure.

The native sources and raw fresh logs remain in the historical source archive
and fresh packet. The final portable overlay has its own manifest and independent
review; its manifest is pinned here. This packet preserves receipts and helpers,
with their original paths, rather than claiming those original-path helpers can
rerun the simulations from this directory without the original workspace.

Run `python verify_composed.py` to check exact local inventory, stored/raw SHA
and byte sizes, the acceptance bindings, and the linked sibling manifests. It
does not execute RTL, import the test helpers or modify this sealed packet.
"""
    (OUT / "composed-README.md").write_text(readme, encoding="utf-8", newline="\n")
    add(OUT / "composed-README.md", "README.md")
    manifest = {"status": "FINAL_STANDALONE_COMPOSITION_SUPPLEMENT_HASH_VERIFIED",
                "composed_status": composed["status"], "composed_receipt_sha256": digest(composed_path),
                "broad_manifest_sha256": digest(broad_manifest), "broad_receipt_sha256": digest(broad_receipt),
                "historical_fresh_manifest_sha256": digest(historic), "portable_manifest_sha256": digest(portable),
                "standalone_full_make_regression_executed": False,
                "fresh_native_commands": composed["fresh"]["commands"],
                "artifact_count": len(records), "artifacts": records}
    (DEST / "archive-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"status": manifest["status"], "artifacts": len(records),
                      "manifest_sha256": digest(DEST / "archive-manifest.json")}))


if __name__ == "__main__":
    main()
