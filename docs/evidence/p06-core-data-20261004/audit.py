#!/usr/bin/env python3
"""Audit frozen M6a read timing evidence without new simulation or fitting."""
import argparse
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0,str(ROOT/"scripts"))
from build_p06_data_biu import build
from run_p06_core_register import sha, vectors
from run_p06_data_biu import max_top
from run_p06_pilot import generic_stats


def data(name):
    path = HERE/name
    return path.read_bytes() if path.is_file() else gzip.decompress(Path(str(path)+".gz").read_bytes())


def rows(name): return list(csv.DictReader(io.StringIO(data(name).decode())))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,required=True)
    args = parser.parse_args(); out = args.output.resolve(); out.mkdir(parents=True,exist_ok=False)
    freeze = json.loads((HERE/"freeze.json").read_text())
    receipt = json.loads((HERE/"receipt.json").read_text())
    assert receipt["status"] == "P06_PRIVATE_DATA_READ_PASS"
    for name,expected in freeze["sha256"].items(): assert sha(HERE/name) == expected,name
    assert sha(ROOT/"scripts/freeze_p06_data_biu.py") == freeze["freezer_sha256"]
    for name,expected in receipt["sources_sha256"].items(): assert sha(ROOT/name) == expected,name
    for name,expected in receipt["artifacts_sha256"].items():
        assert hashlib.sha256(data(name)).hexdigest() == expected,name
    assert sha(build(out)) == receipt["generated_biu_sha256"]
    assert sha(max_top(out)) == receipt["generated_max_top_sha256"]
    assert vectors(out/"vectors.txt") == 208
    assert (out/"vectors.txt").read_bytes() == data("vectors.txt")
    paired = 0
    for name in receipt["artifacts_sha256"]:
        if name.endswith("-iverilog-summary.csv"):
            for suffix in ["summary.csv","trace.csv"]:
                left = name.removesuffix("summary.csv")+suffix
                assert data(left) == data(left.replace("-iverilog-","-verilator-")),left
            paired += 1
    assert paired == 5
    for suffix in ["summary.csv","trace.csv"]:
        assert data("original-max/normal-iverilog-"+suffix) == data("private-max/normal-iverilog-"+suffix)
    normal = rows("data/normal-iverilog-summary.csv")
    lifecycle = rows("data/lifecycle-iverilog-summary.csv")
    guards = rows("data/guards-iverilog-summary.csv")
    assert (len(normal),len(lifecycle),len(guards)) == (432,33,42)
    expected = {(str(w),str(l),str(d)) for w in range(3) for l in range(3) for d in [*range(46),-1,80]}
    assert {(r["waits"],r["lane"],r["latency"]) for r in normal} == expected
    for r in normal:
        assert all(int(r[k]) == 1 for k in ["accepts","reads","captures","completes","responses"])
        assert int(r["external_waits"]) == int(r["waits"]) and int(r["scope_error"]) == 0
        if int(r["latency"]) == -1: assert int(r["misses"]) == 0
        if int(r["latency"]) == 80: assert int(r["misses"]) > 0
    assert sum(int(r["off_boundary"]) for r in normal) == receipt["off_boundary_matrix_captures"] > 0
    kinds = {kind:sum(r["kind"] == str(kind) for r in lifecycle) for kind in range(1,10)}
    assert kinds == {1:3,2:3,3:6,4:6,5:0,6:3,7:3,8:6,9:3}
    assert all(int(r["scope_error"]) == 1 and int(r["responses"]) == 0 for r in guards)
    assert {(int(r["guard_kind"]),int(r["lifecycle_stage"])) for r in guards} == {
        (guard,stage) for guard in range(7) for stage in range(6)}
    for label in ["original","max","timed"]:
        assert generic_stats(HERE/f"generic-{label}.json") == receipt["generic_biu_synthesis"][label]
    assert "Equivalence successfully proven!" in data("max-biu-equivalence.log").decode()
    assert receipt["negative_returncode"] != 0
    assert "independent logical publication oracle failed" in data("negative-run.log").decode()
    for name,marker in receipt["max_units"].items():
        assert marker in data(name+"/iverilog-run.log").decode()
        assert marker in data(name+"/verilator-run.log").decode()
    assert sha(ROOT/"scripts/test_at_landmark_dma.sh") == "0fba7826ccc810c5fa151115416d74357c0919f531a1f5e2ff795ea1a6c3d28c"
    assert "spk286_timing_pilot" not in (ROOT/"rtl/spk286_integration/spk286_integration.qip").read_text()
    result = {"status":"P06_M6A_FROZEN_DATA_EVIDENCE_PASS","artifacts_checked":len(receipt["artifacts_sha256"]),
        "dual_trace_pairs":paired,"private_biu_and_max_top_reconstructed":True,
        "data_cases":432,"lifecycle_cases":33,"guard_cases":42,
        "off_boundary_matrix_captures":receipt["off_boundary_matrix_captures"],
        "max_full_cpu_cases":208,"production_guards_unchanged":True,
        "receipt_sha256":sha(HERE/"receipt.json"),"scope":receipt["scope"]}
    (out/"acceptance.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))


if __name__ == "__main__": main()
