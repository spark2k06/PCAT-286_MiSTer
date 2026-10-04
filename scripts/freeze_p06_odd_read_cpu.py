#!/usr/bin/env python3
"""Freeze accepted M6e evidence with lossless compressed edge traces."""
import argparse
import gzip
import json
from pathlib import Path
import shutil
from run_p06_core_register import ROOT, sha


def relative_name(name):
    path = Path(name)
    assert not path.is_absolute() and not path.drive and ".." not in path.parts, name
    assert path.as_posix() == name, name
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    args = parser.parse_args()
    source = args.input.resolve()
    source.relative_to(ROOT.resolve())
    receipt = json.loads((source / "receipt.json").read_text())
    assert receipt["status"] == "P06_PRIVATE_ODD_READ_CPU_PASS"
    assert receipt["artifacts_sha256"], "Missing accepted artifacts"
    target = ROOT / "docs/evidence/p06-core-odd-read-20261004"
    assert not (target / "receipt.json").exists(), "Do not replace frozen evidence"
    assert not (target / "freeze.json").exists(), "Do not replace frozen evidence"
    assert {p.relative_to(target).as_posix() for p in target.rglob("*") if p.is_file()} <= {"audit.py"}, "Unexpected files in new evidence directory"
    # Validate all accepted artifacts before writing the new checkpoint.
    for name, expected in receipt["artifacts_sha256"].items():
        original = source / relative_name(name)
        assert name not in ["receipt.json", "freeze.json", "acceptance.json", "audit.py"], name
        original.resolve().relative_to(source)
        assert sha(original) == expected, name
    target.mkdir(parents=True, exist_ok=True)
    for name in receipt["artifacts_sha256"]:
        original = source / relative_name(name)
        destination = target / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        if name.endswith("-trace.csv"):
            destination = Path(str(destination) + ".gz")
            destination.write_bytes(gzip.compress(original.read_bytes(), compresslevel=9, mtime=0))
        else:
            shutil.copyfile(original, destination)
    shutil.copyfile(source / "receipt.json", target / "receipt.json")
    frozen = {
        "sha256": {p.relative_to(target).as_posix(): sha(p) for p in sorted(target.rglob("*"))
                   if p.is_file() and p.name not in ["freeze.json", "acceptance.json"]},
        "freezer_sha256": sha(Path(__file__)),
        "trace_encoding": "CSV gzip; original uncompressed SHA256 remains in receipt.json",
        "source_build": source.relative_to(ROOT).as_posix(),
    }
    (target / "freeze.json").write_text(json.dumps(frozen, indent=2) + "\n")
    print(f"ODD_READ_CPU_FROZEN artifacts={len(receipt['artifacts_sha256'])}")


if __name__ == "__main__":
    main()
