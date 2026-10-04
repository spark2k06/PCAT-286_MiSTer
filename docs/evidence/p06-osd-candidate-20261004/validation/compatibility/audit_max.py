"""Independently revalidate all original/profiled MAX raw stream metadata."""
import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]

def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(65536):
            digest.update(chunk)
    return digest.hexdigest()

def pair(original, profiled, trusted_profiled, max_record):
    assert profiled == trusted_profiled, "MAX profiled metadata binding failed"
    for data in (original, profiled):
        assert re.fullmatch("[0-9a-f]{64}", data["sha256"]), "MAX raw digest syntax failed"
        assert type(data["bytes"]) is int and data["bytes"] > 0, "MAX byte count type failed"
        assert type(data["rows"]) is int and data["rows"] > 0, "MAX row count type failed"
    assert original["sha256"] == max_record["original_trace_sha256"], "MAX original raw digest binding failed"
    assert profiled["sha256"] == max_record["profiled_trace_sha256"], "MAX profiled raw digest binding failed"
    assert original["sha256"] == profiled["sha256"], "MAX raw digest equality failed"
    assert original["bytes"] == profiled["bytes"] and original["rows"] == profiled["rows"], "MAX stream count oracle failed"
    for key in ("canonical_sha256", "canonical_bytes", "reset_rows", "input_unknown_rows", "input_unknown_bits"):
        assert original[key] == profiled[key], "MAX input view metadata oracle failed"

def raw_file_if_present(path, metadata):
    if not path.exists():
        return "complete streamed hash; bounded samples retained"
    row_count = 0
    with path.open("rb") as source:
        while chunk := source.read(65536):
            row_count += chunk.count(b"\n")
    assert sha(path) == metadata["sha256"], "MAX raw CSV digest changed"
    assert path.stat().st_size == metadata["bytes"] and row_count - 1 == metadata["rows"], "MAX raw CSV count changed"
    return "raw CSV independently rehashed"

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    directory = args.root.resolve()
    assert directory.is_relative_to(ROOT / "build"), "audit root outside workspace build"
    output = args.output.resolve() if args.output else directory / "max-audit.json"
    assert output.is_relative_to(directory) and not output.exists(), "audit output must be fresh under acceptance root"
    aggregate = json.loads((directory / "receipt.json").read_text())
    assert aggregate["status"] == "PASS" and aggregate["counts"] == {"iverilog": 202, "verilator": 64, "max_equivalence": 26,
        "dual_trace_pairs": 58, "unpaired_verilator_functional": 6}
    references = {item["path"]: item["sha256"] for item in aggregate["leaf_receipts"]}
    max_records = [record for record in aggregate["results"] if record.get("kind") == "MAX per-edge equivalence"]
    assert len(max_records) == 26 and len({record["unit"] for record in max_records}) == 26
    rows = []
    negatives = 0
    for record in max_records:
        shard = (ROOT / record["artifact_root"]).resolve()
        assert shard.is_relative_to(directory), "MAX artifact outside acceptance root"
        leaf_path = ROOT / record["leaf_receipt"] if "leaf_receipt" in record else shard / "receipt.json"
        assert leaf_path.resolve().is_relative_to(shard), "MAX leaf receipt outside shard"
        assert sha(leaf_path) == references[leaf_path.relative_to(ROOT).as_posix()], "leaf receipt changed"
        leaf = json.loads(leaf_path.read_text())
        assert leaf["status"] == "PASS" and not leaf["failures"] and not leaf["source_changes"]
        unit = record["unit"]
        trusted = [item for item in leaf["results"] if item.get("unit") == unit and item.get("simulator") == "iverilog" and item.get("profile") == 0]
        leaf_max = [item for item in leaf["results"] if item.get("unit") == unit and item.get("kind") == "MAX per-edge equivalence"]
        assert len(trusted) == len(leaf_max) == 1
        assert {key: value for key, value in record.items() if key not in ("artifact_root", "leaf_receipt")} == leaf_max[0], "aggregate MAX recipe changed"
        target = shard / unit
        original_path = target / "original-max.digest.json"
        profiled_path = target / "profile-0-iverilog.digest.json"
        original = json.loads(original_path.read_text())
        profiled = json.loads(profiled_path.read_text())
        pair(original, profiled, trusted[0]["trace"], record)
        log = target / "original-run.log"
        text = log.read_text()
        assert "PASS" in text and "FATAL" not in text, "original MAX functional log not PASS"
        storage = [raw_file_if_present(target / "original-max.csv", original),
                   raw_file_if_present(target / "profile-0-iverilog.csv", profiled)]
        rows.append({"unit": unit, "leaf_receipt_sha256": sha(leaf_path),
            "original_log_sha256": sha(log), "original_meta_sha256": sha(original_path),
            "profiled_meta_sha256": sha(profiled_path), "raw_sha256": original["sha256"],
            "bytes": original["bytes"], "rows": original["rows"], "storage": storage})
        # Metadata integrity mutations only; these are not RTL mutants.
        mutations = [("sha256", "0" * 64), ("bytes", original["bytes"] + 1),
                     ("rows", original["rows"] + 1), ("canonical_sha256", "0" * 64)]
        for key, value in mutations:
            changed = {**original, key: value}
            rejected = False
            try:
                pair(changed, profiled, trusted[0]["trace"], record)
            except AssertionError:
                rejected = True
            assert rejected, f"MAX integrity mutant survived: {unit} {key}"
            negatives += 1
        rejected = False
        try:
            pair(original, {**profiled, "sha256": "0" * 64}, trusted[0]["trace"], record)
        except AssertionError:
            rejected = True
        assert rejected, "MAX profiled metadata integrity mutant survived"
        negatives += 1
    receipt = {"status": "PASS", "scope": "independent raw MAX metadata/artifact integrity audit; no new RTL timing claim",
        "auditor_sha256": sha(Path(__file__).resolve()), "aggregate_receipt_sha256": sha(directory / "receipt.json"),
        "max_pairs": 26, "metadata_negative_checks": negatives, "results": rows}
    output.write_text(json.dumps(receipt, indent=2) + "\n")
    print(f"P06_PROFILE_MAX_INDEPENDENT_AUDIT_PASS pairs=26 metadata_negatives={negatives}")

if __name__ == "__main__":
    main()
