#!/usr/bin/env python3
"""Freeze accepted M6a evidence, compressing edge traces losslessly."""
import argparse
import gzip
import json
from pathlib import Path
import shutil
from run_p06_core_register import ROOT, sha


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input",type=Path,required=True)
    args = parser.parse_args(); source = args.input.resolve()
    receipt = json.loads((source/"receipt.json").read_text())
    assert receipt["status"] == "P06_PRIVATE_DATA_READ_PASS"
    target = ROOT/"docs/evidence/p06-core-data-20261004"
    target.mkdir(parents=True,exist_ok=True)
    assert not (target/"receipt.json").exists(), "Use a new evidence milestone; do not replace a frozen receipt"
    for name,expected in receipt["artifacts_sha256"].items():
        original = source/name; assert sha(original) == expected,name
        destination = target/name; destination.parent.mkdir(parents=True,exist_ok=True)
        if name.endswith("-trace.csv"):
            destination = Path(str(destination)+".gz")
            destination.write_bytes(gzip.compress(original.read_bytes(),compresslevel=9,mtime=0))
        else: shutil.copyfile(original,destination)
    shutil.copyfile(source/"receipt.json",target/"receipt.json")
    frozen = {"sha256":{p.relative_to(target).as_posix():sha(p) for p in target.rglob("*")
        if p.is_file() and p.name not in ["freeze.json","acceptance.json"]},
        "freezer_sha256":sha(Path(__file__)),
        "trace_encoding":"CSV gzip; original uncompressed SHA256 remains in receipt.json",
        "source_build":source.relative_to(ROOT).as_posix()}
    (target/"freeze.json").write_text(json.dumps(frozen,indent=2)+"\n")
    print(f"DATA_FROZEN artifacts={len(receipt['artifacts_sha256'])}")


if __name__ == "__main__": main()
