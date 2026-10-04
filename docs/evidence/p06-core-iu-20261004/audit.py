#!/usr/bin/env python3
"""Audit the bounded M5 register handoff evidence; no new simulation or fit."""
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
from build_p06_iu_cpu import build
from run_p06_core_register import sha
from run_p06_iu import stream_vectors
from run_p06_pilot import generic_stats


def data(name):
    path = HERE/name
    return path.read_bytes() if path.is_file() else gzip.decompress(Path(str(path)+".gz").read_bytes())


def rows(name): return list(csv.DictReader(io.StringIO(data(name).decode())))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,required=True)
    args = parser.parse_args(); out = args.output.resolve(); out.mkdir(parents=True,exist_ok=False)
    freeze = json.loads((HERE/"freeze.json").read_text()); receipt = json.loads((HERE/"receipt.json").read_text())
    assert receipt["status"] == "P06_PRIVATE_IU_HANDOFF_PASS"
    for name,expected in freeze["sha256"].items(): assert sha(HERE/name) == expected, name
    for name,expected in receipt["sources_sha256"].items(): assert sha(ROOT/name) == expected,name
    for name,expected in receipt["artifacts_sha256"].items():
        assert hashlib.sha256(data(name)).hexdigest() == expected,name
    recreated = build(out)
    for name,path in recreated.items(): assert sha(path) == receipt["generated_cpu_sha256"][name],name
    assert stream_vectors(out/"streams.txt") == 688
    assert (out/"streams.txt").read_bytes() == data("streams.txt")
    paired = 0
    for name in receipt["artifacts_sha256"]:
        if name.endswith("-iverilog-summary.csv"):
            for suffix in ["summary.csv","trace.csv"]:
                left = name.removesuffix("summary.csv")+suffix
                assert data(left) == data(left.replace("-iverilog-","-verilator-")),left
            paired += 1
    for suffix in ["summary.csv","trace.csv"]:
        assert data("original-max/normal-iverilog-"+suffix) == data("private-max/normal-iverilog-"+suffix)
    warm = rows("streams/normal-iverilog-summary.csv"); cold = rows("streams/cold-iverilog-summary.csv")
    baseline = rows("baseline/normal-iverilog-summary.csv")
    assert len(warm) == len(cold) == len(baseline) == 1448
    assert sum(int(r["relaunch"]) for r in warm) == 760
    savings = []
    for new,old in zip(warm,baseline):
        assert (new["id"],new["instruction"],new["gpr"],new["flags"]) == (old["id"],old["instruction"],old["gpr"],old["flags"])
        assert int(old["relaunch"]) == 0
        if new["instruction"] == "1": savings.append(int(old["start_delta"])-int(new["start_delta"]))
    assert len(savings) == 688 and set(savings) == {1}
    for r in warm+cold:
        assert int(r["elapsed"]) >= (2 if int(r["form"])<3 else 3)
    for r in rows("single/warm-iverilog-summary.csv"):
        assert int(r["elapsed"]) == (2 if int(r["form"])<3 else 3)
    for mode in range(1,16):
        assert "cases=11" in data(f"streams/mode{mode}-iverilog-run.log").decode()
    for name in receipt["generic_component_synthesis"]:
        for label in ["original","max","timed"]:
            assert generic_stats(HERE/f"generic-{name}-{label}.json") == receipt["generic_component_synthesis"][name][label]
        assert "Equivalence successfully proven!" in data(f"equivalence-{name}.log").decode()
    assert receipt["negative_returncode"] != 0 and "stream architectural mismatch" in data("negative-run.log").decode()
    assert sha(ROOT/"scripts/test_at_landmark_dma.sh") == "0fba7826ccc810c5fa151115416d74357c0919f531a1f5e2ff795ea1a6c3d28c"
    assert "spk286_timing_pilot" not in (ROOT/"rtl/spk286_integration/spk286_integration.qip").read_text()
    result = {"status":"P06_M5_FROZEN_IU_EVIDENCE_PASS","artifacts_checked":len(receipt["artifacts_sha256"]),
        "dual_trace_pairs":paired,"private_cpu_reconstructed":True,"streams":688,"instructions":1448,
        "paired_first_handoffs":688,"first_handoff_saving_cpu_clocks":1,"production_guards_unchanged":True,
        "receipt_sha256":sha(HERE/"receipt.json"),"scope":receipt["scope"]}
    (out/"acceptance.json").write_text(json.dumps(result,indent=2)+"\n"); print(json.dumps(result,indent=2))


if __name__ == "__main__": main()
