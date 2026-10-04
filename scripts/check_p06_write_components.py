#!/usr/bin/env python3
"""Bounded M6f lint, component costs and MAX/WRITE-disabled proofs.

No Quartus, full regression or production selection. Generic Yosys counts
include existing WRITE logic restored by qualification; they are not ALMs.
"""
import argparse
import json
from pathlib import Path
from build_p06_odd_read_cpu import build as build_odd
from build_p06_write_cpu import build, M6E_RECEIPT_SHA256
from build_p06_register_cpu import replace_once
from check_p06_odd_components import (
    BIU_INPUTS, BIU_OUTPUTS, select as select_odd, synthesize, prove,
    no_private_input_cone,
)
from run_p06_core_register import ROOT, CPU, run, sha


def select(selected):
    return select_odd(selected)


def prepare(out, selected):
    out = Path(out)
    receipt_path = ROOT / "docs/evidence/p06-core-odd-read-20261004/receipt.json"
    assert sha(receipt_path) == M6E_RECEIPT_SHA256
    receipt = json.loads(receipt_path.read_text())
    for name, expected in receipt["sources_sha256"].items():
        assert sha(ROOT / name) == expected, name
    previous_dir = out / "m6e-component-source"
    previous_dir.mkdir()
    previous = build_odd(previous_dir)
    assert set(previous) == set(receipt["generated_cpu_sha256"])
    for name, path in previous.items():
        assert sha(path) == receipt["generated_cpu_sha256"][name], name

    for label, timed, odd, write in [("max", 0, 0, 0), ("aligned-read", 1, 0, 0),
            ("read", 1, 1, 0), ("aligned-write", 1, 0, 1), ("write", 1, 1, 1)]:
        params = [f"-G{name}=1'b{timed}" for name in [
            "P06_REGISTER_PILOT", "P06_FETCH_PILOT", "P06_IU_PILOT", "P06_MEMORY_PILOT"]]
        params += [f"-GP06_ODD_READ_PILOT=1'b{odd}", f"-GP06_WRITE_PILOT=1'b{write}"]
        run(["verilator", "--lint-only", "--Wall", "--top-module", "spk286", *params,
             "-I" + str(CPU / "rtl"), *select(selected)], out / f"lint-{label}.log")
        print(f"M6F_LINT_PASS {label}", flush=True)

    costs = {"spk286_biu": {}, "p06_instruction_duration": {}}
    biu = selected["spk286_biu.sv"]
    timed_setting = "chparam -set P06_DATA_TIMING 1 -set P06_SHARED_TIMING 1 -set P06_ODD_READ_TIMING 1"
    for label, path, setting in [
        ("original", CPU / "rtl/spk286_biu.sv", ""),
        ("m6e", previous["spk286_biu.sv"], timed_setting + " spk286_biu\n"),
        ("write-off", biu, timed_setting + " -set P06_WRITE_TIMING 0 spk286_biu\n"),
        ("write", biu, timed_setting + " -set P06_WRITE_TIMING 1 spk286_biu\n"),
        ("max", biu, ""),
    ]:
        costs["spk286_biu"][label] = synthesize(out, "spk286_biu", label, path, setting)
    policy = selected["p06_instruction_duration.sv"]
    for label, path, setting in [
        ("m6e", previous["p06_instruction_duration.sv"],
         "chparam -set P06_LATE_ALIGNMENT 1 p06_instruction_duration\n"),
        ("write-off", policy, "chparam -set P06_LATE_ALIGNMENT 1 -set P06_WRITE_ALIGNMENT 0 p06_instruction_duration\n"),
        ("write", policy, "chparam -set P06_LATE_ALIGNMENT 1 -set P06_WRITE_ALIGNMENT 1 p06_instruction_duration\n"),
        ("late-off", policy, "chparam -set P06_LATE_ALIGNMENT 0 -set P06_WRITE_ALIGNMENT 1 p06_instruction_duration\n"),
        ("max", policy, "chparam -set HISTORICAL 0 -set P06_LATE_ALIGNMENT 1 -set P06_WRITE_ALIGNMENT 1 p06_instruction_duration\n"),
    ]:
        costs["p06_instruction_duration"][label] = synthesize(out, "p06_instruction_duration", label, path, setting)
    for module in costs:
        assert costs[module]["write-off"]["register_bits"] == costs[module]["m6e"]["register_bits"]
    assert costs["spk286_biu"]["max"]["register_bits"] == costs["spk286_biu"]["original"]["register_bits"]
    assert costs["p06_instruction_duration"]["max"]["register_bits"] == 0

    # Arbitrary private inputs in the original golden are ignored. Never
    # delete an input or a functional output to manufacture a MAX proof.
    golden = out / "biu-max-gold.sv"
    golden.write_text(replace_once((CPU / "rtl/spk286_biu.sv").read_text(), "module spk286_biu (",
        "module spk286_biu (\n    input logic " + ", ".join(BIU_INPUTS) + ","), newline="\n")
    proofs = {"biu_max": prove(out, "spk286_biu", "biu-max", golden, biu, outputs=BIU_OUTPUTS)}
    proofs["biu_write_off"] = prove(out, "spk286_biu", "biu-write-off",
        previous["spk286_biu.sv"], biu, setting=timed_setting + " spk286_biu\n")
    proofs["duration_write_off"] = prove(out, "p06_instruction_duration", "duration-write-off",
        previous["p06_instruction_duration.sv"], policy,
        setting="chparam -set P06_LATE_ALIGNMENT 1 p06_instruction_duration\n")
    proofs["duration_max"] = prove(out, "p06_instruction_duration", "duration-max",
        previous["p06_instruction_duration.sv"], policy,
        setting="chparam -set HISTORICAL 0 -set P06_LATE_ALIGNMENT 1 p06_instruction_duration\n")
    maximum = json.loads((out / "generic-spk286_biu-max.json").read_text())["modules"]["spk286_biu"]
    no_private_input_cone(maximum, BIU_INPUTS)
    for name, constant in [("p06_scope_error", "0"), ("p06_scope_block", "0"),
            ("p06_code_admission", "1"), ("p06_read_wait_event", "0"), ("p06_alignment_event", "0")]:
        assert maximum["ports"][name]["bits"] == [constant], name
    for label in ["late-off", "max"]:
        net = json.loads((out / f"generic-p06_instruction_duration-{label}.json").read_text())["modules"]["p06_instruction_duration"]
        no_private_input_cone(net, ["alignment_event"])
    proofs.update({"max_biu_private_input_cones_absent": True,
                   "duration_late0_alignment_cone_absent": True,
                   "duration_hist0_alignment_cone_absent": True})
    result = {"costs": costs, "proofs": proofs, "ancestor_receipt_sha256": M6E_RECEIPT_SHA256,
        "scope": "Isolated generic BIU/duration mapping and MAX/WRITE-disabled equivalence; not directed A3 acceptance, historical write-buffer overlap, full FPGA cost, fit or STA"}
    (out / "component-checks.json").write_text(json.dumps(result, indent=2) + "\n")
    print("M6F_COMPONENT_PREPARE_PASS", flush=True)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    out.relative_to(ROOT.resolve())
    out.mkdir(parents=True, exist_ok=False)
    prepare(out, build(out))
