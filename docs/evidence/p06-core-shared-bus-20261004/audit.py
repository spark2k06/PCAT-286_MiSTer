#!/usr/bin/env python3
"""Audit frozen M6b shared CODE/DATA evidence; no new simulation or fitting."""
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
from build_p06_shared_bus import build
from run_p06_core_register import sha, vectors
from run_p06_shared_bus import max_top, validate_component_coverage
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
    assert receipt["status"] == "P06_PRIVATE_SHARED_BUS_PASS"
    assert receipt["coverage_checked"] and receipt["max_private_control_cones_absent"]
    for name,expected in freeze["sha256"].items(): assert sha(HERE/name) == expected,name
    assert sha(ROOT/"scripts/freeze_p06_shared_bus.py") == freeze["freezer_sha256"]
    for name,expected in receipt["sources_sha256"].items(): assert sha(ROOT/name) == expected,name
    for name,expected in receipt["artifacts_sha256"].items():
        assert hashlib.sha256(data(name)).hexdigest() == expected,name
    for name,path in build(out).items(): assert sha(path) == receipt["generated_sha256"][name],name
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
    normal = rows("shared/normal-iverilog-summary.csv")
    lifecycle = rows("shared/lifecycle-iverilog-summary.csv")
    cancel = rows("shared/cancel-scope-iverilog-summary.csv")
    validate_component_coverage(normal,lifecycle,cancel)
    assert len(normal) == receipt["transition_cases"] == 972
    assert len(lifecycle) == receipt["lifecycle_cases"]
    assert len(cancel) == receipt["cancel_scope_cases"]
    keys = ["direction","code_odd","data_lane","code_waits","data_waits","code_latency","data_latency"]
    expected = {(str(d),str(o),str(l),str(cw),str(dw),str(cl),str(dl))
        for d in range(2) for o in range(2) for l in range(3) for cw in range(3) for dw in range(3)
        for cl in [0,-1,80] for dl in [0,-1,80]}
    assert {tuple(r[k] for k in keys) for r in normal} == expected
    for r in normal:
        assert all(int(r[k]) == 1 for k in ["code_accepts","data_accepts","code_captures","data_captures",
            "code_completes","data_completes","code_responses","data_responses","handoffs"])
        assert int(r["code_external"]) == int(r["code_waits"])
        assert int(r["data_external"]) == int(r["data_waits"])
        assert r["data_start_cpu"] == r["code_complete_cpu"] if r["direction"] == "0" else r["code_start_cpu"] == r["data_complete_cpu"]
    for name in receipt["generic_component_synthesis"]:
        for label in ["original","max","timed"]:
            assert generic_stats(HERE/f"generic-{name}-{label}.json") == receipt["generic_component_synthesis"][name][label]
        assert "Equivalence successfully proven!" in data(f"max-{name}-equivalence.log").decode()
        assert "delete -input" not in data(f"max-{name}-equivalence.ys").decode()
        maximum = json.loads(data(f"generic-{name}-max.json"))["modules"][name]
        inputs = (["p06_cpu_boundary","p06_board_ready","p06_code_issue","p06_code_complete","p06_code_canceled"]
                  if name == "spk286_biu" else ["p06_cpu_boundary","p06_board_ready","p06_admission_enable","p06_scope_block"])
        control_bits = {bit for p in inputs for bit in maximum["ports"][p]["bits"] if isinstance(bit,int)}
        used_bits = {bit for cell in maximum["cells"].values() for bits in cell["connections"].values()
                     for bit in bits if isinstance(bit,int)}
        output_bits = {bit for p in maximum["ports"].values() if p["direction"] == "output"
                       for bit in p["bits"] if isinstance(bit,int)}
        assert not control_bits & (used_bits | output_bits),name
        golden = (ROOT/f"vendor/spk286/rtl/{name}.sv").read_text()
        assert golden.count(f"module {name} (") == 1
        golden = golden.replace(f"module {name} (",f"module {name} (\n    input logic "+", ".join(inputs)+",")
        assert data(f"max-{name}-gold.sv").decode() == golden,name
    for label,marker in [("owner","shared logical owner oracle failed"),("scope","CODE publication oracle failed")]:
        assert receipt["negative_returncodes"][label] != 0
        assert marker in data(f"negative-{label}-run.log").decode()
    for name,marker in receipt["max_units"].items():
        assert marker in data(name+"/iverilog-run.log").decode()
        assert marker in data(name+"/verilator-run.log").decode()
    assert sha(ROOT/"scripts/test_at_landmark_dma.sh") == "0fba7826ccc810c5fa151115416d74357c0919f531a1f5e2ff795ea1a6c3d28c"
    assert "spk286_timing_pilot" not in (ROOT/"rtl/spk286_integration/spk286_integration.qip").read_text()
    result = {"status":"P06_M6B_FROZEN_SHARED_BUS_PASS","artifacts_checked":len(receipt["artifacts_sha256"]),
        "dual_trace_pairs":paired,"private_components_and_max_top_reconstructed":True,
        "transition_cases":len(normal),"lifecycle_cases":len(lifecycle),"cancel_scope_cases":len(cancel),
        "same_tc_cross_owner_handoffs":972,"max_full_cpu_cases":208,"production_guards_unchanged":True,
        "exact_coverage_checked":True,"max_private_control_cones_absent":True,
        "receipt_sha256":sha(HERE/"receipt.json"),"scope":receipt["scope"]}
    (out/"acceptance.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))


if __name__ == "__main__": main()
