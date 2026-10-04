#!/usr/bin/env python3
"""Bounded private M6g preparation, lint, generic costs and bypass proofs.

Formal executor scope is the actual extracted pending/retire/commit_flags
assignments, not the entire executor. Full CPU elaboration uses strict lint;
directed dual-simulator acceptance is a separate runner milestone.
"""
import argparse
import json
import re
from pathlib import Path
from build_p06_rmw_cpu import build, ancestor, M6F_RECEIPT_SHA256, M6F_GENERATED_SHA256
from build_p06_register_cpu import replace_once
from check_p06_odd_components import (
    BIU_INPUTS, BIU_OUTPUTS, select as select_odd, synthesize, prove,
    no_private_input_cone,
)
from run_p06_core_register import ROOT, CPU, run, sha
from run_p06_pilot import generic_stats


def select(selected):
    return select_odd(selected)


def pre_abc(out, module, label, path, setting):
    """Measure mapping before ABC, distinguishing tool remapping from state."""
    stem = out / f"preabc-{module}-{label}"
    script, net = stem.with_suffix(".ys"), stem.with_suffix(".json")
    script.write_text(f"read_verilog -sv {path}\n" + setting +
        f"synth -top {module} -flatten -noabc\nwrite_json {net}\n")
    result = run(["yosys", "-Q", "-s", script], stem.with_suffix(".log"))
    assert "Warning:" not in result, (module, label)
    return generic_stats(net)


def commit_probe(out, label, source, new):
    """Extract real executor assignments, keeping their common input symbols."""
    package = (CPU / "microcode/generated/spk286_microcode_pkg.sv").read_text()
    width = int(re.search(r"MC_WORD_WIDTH = (\d+)", package)[1])
    fragment = re.search(r"    assign p06_memory_result_pending = .*?\n    assign operation_retire = .*?;",
        source.read_text(), re.S)[0]
    commit_flags = re.search(r"    assign commit_flags = .*?;", source.read_text(), re.S)[0]
    for name in ["MC_MOVE", "MC_COMMIT_FLAGS"]:
        constant = re.search(r"\b" + name + r" = ([^;]+);", package)[1]
        fragment = fragment.replace("spk286_microcode_pkg::" + name, constant)
        commit_flags = commit_flags.replace("spk286_microcode_pkg::" + name, constant)
    probe = out / f"commit-{label}.sv"
    probe.write_text("module p06_rmw_commit_cost #(parameter bit P06_MEMORY_TIMING=1'b0" +
        (", parameter bit P06_RMW_TIMING=1'b0" if new else "") + ") (\n" +
        f"input logic [{width-1}:0] operation, input logic [2:0] temporary_valid_q,\n" +
        "input logic p06_moffs_read, p06_rmw_form, register_complete, move_word, allowed, flags_valid_q, result_disposed_q,\n" +
        "output logic p06_memory_result_pending, operation_retire, commit_flags" +
        (", p06_rmw_result_pending" if new else "") + ");\n" +
        fragment + "\n" + commit_flags + "\nendmodule\n", newline="\n")
    return probe


def prepare(out, selected, development=False):
    out = Path(out)
    previous_dir = out / "m6f-component-source"
    previous_dir.mkdir()
    previous = ancestor(previous_dir, development)
    assert sha(selected["spk286_biu.sv"]) == sha(previous["spk286_biu.sv"])
    assert sha(previous["spk286_biu.sv"]) == M6F_GENERATED_SHA256["spk286_biu.sv"]

    for label, timed, odd, rmw in [("max", 0, 0, 0), ("aligned-write-off", 1, 0, 0),
            ("write-off", 1, 1, 0), ("aligned-rmw", 1, 0, 1), ("rmw", 1, 1, 1)]:
        params = [f"-G{name}=1'b{timed}" for name in [
            "P06_REGISTER_PILOT", "P06_FETCH_PILOT", "P06_IU_PILOT", "P06_MEMORY_PILOT", "P06_WRITE_PILOT"]]
        params += [f"-GP06_ODD_READ_PILOT=1'b{odd}", f"-GP06_RMW_PILOT=1'b{rmw}"]
        run(["verilator", "--lint-only", "--Wall", "--top-module", "spk286", *params,
             "-I" + str(CPU / "rtl"), *select(selected)], out / f"lint-{label}.log")
        print(f"M6G_LINT_PASS {label}", flush=True)

    costs = {"spk286_biu": {}, "p06_instruction_duration": {}, "executor_commit_assignments": {}}
    biu = selected["spk286_biu.sv"]
    timed_biu = "chparam -set P06_DATA_TIMING 1 -set P06_SHARED_TIMING 1 -set P06_ODD_READ_TIMING 1 -set P06_WRITE_TIMING 1 spk286_biu\n"
    for label, path, setting in [("original", CPU / "rtl/spk286_biu.sv", ""),
            ("m6f", previous["spk286_biu.sv"], timed_biu), ("rmw", biu, timed_biu), ("max", biu, "")]:
        costs["spk286_biu"][label] = synthesize(out, "spk286_biu", label, path, setting)
    policy = selected["p06_instruction_duration.sv"]
    common_duration = "-set P06_LATE_ALIGNMENT 1 -set P06_WRITE_ALIGNMENT 1"
    for label, path, setting in [
        ("m6f", previous["p06_instruction_duration.sv"], f"chparam {common_duration} p06_instruction_duration\n"),
        ("rmw-off", policy, f"chparam {common_duration} -set P06_RMW_TIMING 0 p06_instruction_duration\n"),
        ("rmw", policy, f"chparam {common_duration} -set P06_RMW_TIMING 1 p06_instruction_duration\n"),
        ("max", policy, f"chparam -set HISTORICAL 0 {common_duration} -set P06_RMW_TIMING 1 p06_instruction_duration\n"),
    ]:
        costs["p06_instruction_duration"][label] = synthesize(out, "p06_instruction_duration", label, path, setting)
    old_commit = commit_probe(out, "m6f", previous["spk286_micro_executor.sv"], False)
    new_commit = commit_probe(out, "m6g", selected["spk286_micro_executor.sv"], True)
    for label, path, setting in [
        ("m6f", old_commit, "chparam -set P06_MEMORY_TIMING 1 p06_rmw_commit_cost\n"),
        ("rmw-off", new_commit, "chparam -set P06_MEMORY_TIMING 1 p06_rmw_commit_cost\n"),
        ("rmw", new_commit, "chparam -set P06_MEMORY_TIMING 1 -set P06_RMW_TIMING 1 p06_rmw_commit_cost\n"),
        ("max", new_commit, ""),
    ]:
        costs["executor_commit_assignments"][label] = synthesize(out, "p06_rmw_commit_cost", label, path, setting)
    assert costs["spk286_biu"]["rmw"] == costs["spk286_biu"]["m6f"]
    for module in ["p06_instruction_duration", "executor_commit_assignments"]:
        assert costs[module]["rmw-off"]["register_bits"] == costs[module]["m6f"]["register_bits"], module
        assert costs[module]["rmw"]["register_bits"] == costs[module]["m6f"]["register_bits"], module
    assert costs["spk286_biu"]["max"]["register_bits"] == costs["spk286_biu"]["original"]["register_bits"]
    assert costs["p06_instruction_duration"]["max"]["register_bits"] == 0
    assert costs["p06_instruction_duration"]["max"]["generic_cells"] == 3
    preabc = {}
    for label, path, setting in [
        ("m6f", previous["p06_instruction_duration.sv"], f"chparam {common_duration} p06_instruction_duration\n"),
        ("rmw-off", policy, f"chparam {common_duration} -set P06_RMW_TIMING 0 p06_instruction_duration\n"),
        ("rmw", policy, f"chparam {common_duration} -set P06_RMW_TIMING 1 p06_instruction_duration\n"),
    ]:
        preabc[label] = pre_abc(out, "p06_instruction_duration", label, path, setting)

    # New inputs are free in both gold/gate. Gold explicitly ignores them.
    # Delete only the new diagnostic pending output from the commit gate.
    golden_policy = out / "duration-m6f-gold.sv"
    golden_policy.write_text(replace_once(previous["p06_instruction_duration.sv"].read_text(),
        "    output logic [7:0] elapsed_clocks, scheduled_clocks\n",
        "    output logic [7:0] elapsed_clocks, scheduled_clocks,\n    input logic rmw_form_valid\n"), newline="\n")
    proofs = {
        "duration_rmw_off": prove(out, "p06_instruction_duration", "duration-rmw-off", golden_policy, policy,
            setting=f"chparam {common_duration} p06_instruction_duration\n"),
        "duration_max": prove(out, "p06_instruction_duration", "duration-max", golden_policy, policy,
            setting=f"chparam -set HISTORICAL 0 {common_duration} p06_instruction_duration\n"),
        "executor_assignments_rmw_off": prove(out, "p06_rmw_commit_cost", "commit-rmw-off", old_commit, new_commit,
            setting="chparam -set P06_MEMORY_TIMING 1 p06_rmw_commit_cost\n", outputs=["p06_rmw_result_pending"]),
        "executor_assignments_max": prove(out, "p06_rmw_commit_cost", "commit-max", old_commit, new_commit,
            outputs=["p06_rmw_result_pending"]),
    }
    golden_biu = out / "biu-max-gold.sv"
    golden_biu.write_text(replace_once((CPU / "rtl/spk286_biu.sv").read_text(), "module spk286_biu (",
        "module spk286_biu (\n    input logic " + ", ".join(BIU_INPUTS) + ","), newline="\n")
    proofs["biu_max"] = prove(out, "spk286_biu", "biu-max", golden_biu, biu, outputs=BIU_OUTPUTS)
    maximum_biu = json.loads((out / "generic-spk286_biu-max.json").read_text())["modules"]["spk286_biu"]
    no_private_input_cone(maximum_biu, BIU_INPUTS)
    for name, constant in [("p06_scope_error", "0"), ("p06_scope_block", "0"),
            ("p06_code_admission", "1"), ("p06_read_wait_event", "0"), ("p06_alignment_event", "0")]:
        assert maximum_biu["ports"][name]["bits"] == [constant], name
    for label in ["rmw-off", "max"]:
        net = json.loads((out / f"generic-p06_instruction_duration-{label}.json").read_text())["modules"]["p06_instruction_duration"]
        no_private_input_cone(net, ["rmw_form_valid"])
        if label == "max":
            no_private_input_cone(net, ["alignment_event"])
        net = json.loads((out / f"generic-p06_rmw_commit_cost-{label}.json").read_text())["modules"]["p06_rmw_commit_cost"]
        no_private_input_cone(net, ["p06_rmw_form"])
        assert net["ports"]["p06_rmw_result_pending"]["bits"] == ["0"]
    proofs.update({"biu_source_identical_to_m6f": True, "max_biu_private_cones_absent": True,
        "duration_rmw_off_input_cone_absent": True, "duration_hist0_private_cones_absent": True,
        "executor_assignments_rmw_off_private_cone_absent": True,
        "executor_assignments_max_private_cone_absent": True})
    result = {"status": "DEV_NOT_ACCEPTED" if development else "PINNED_COMPONENT_PREPARED",
        "ancestor_receipt_sha256": M6F_RECEIPT_SHA256, "costs": costs, "proofs": proofs,
        "duration_pre_abc": preabc,
        "duration_rmw_off_pre_abc_identical": preabc["rmw-off"] == preabc["m6f"],
        "mapping_note": "Disabled RMW must preserve sequential equivalence, input-cone exclusion and register bits. ABC generic gate totals are measured independently and may differ with source ordering; they are not an exact FPGA resource prediction.",
        "scope": "Strict full CPU lint; isolated BIU/duration mapping and extracted real executor pending/retire/commit_flags assignments; no directed RMW acceptance, write-buffer overlap, full executor formal, total FPGA cost, fit or STA"}
    (out / "component-checks.json").write_text(json.dumps(result, indent=2) + "\n")
    print("M6G_COMPONENT_PREPARE_PASS", flush=True)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--development", action="store_true")
    args = parser.parse_args()
    out = args.output.resolve()
    out.relative_to(ROOT.resolve())
    out.mkdir(parents=True, exist_ok=False)
    prepare(out, build(out, args.development), args.development)
