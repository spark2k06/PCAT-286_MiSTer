#!/usr/bin/env python3
"""Prepare isolated M6e lint, costs and default-bypass proofs.

No full regression, Quartus, production selection or ancestor edits. Yosys
costs are generic cells/register bits, not Cyclone V ALMs or total CPU cost.
"""
import argparse
import json
from pathlib import Path
from build_p06_memory_cpu import build as build_memory
from build_p06_odd_read_cpu import build, M6C_RECEIPT_SHA256
from build_p06_register_cpu import replace_once
from run_p06_core_register import ROOT, CPU, sources, run, sha
from run_p06_pilot import generic_stats

BIU_INPUTS = ["p06_cpu_boundary", "p06_board_ready", "p06_code_issue",
              "p06_code_complete", "p06_code_canceled"]
BIU_OUTPUTS = ["p06_scope_error", "p06_code_admission", "p06_scope_block",
               "p06_read_wait_event", "p06_alignment_event"]


def select(selected):
    """Select one functional CPU and the generated late-alignment policy."""
    return [selected.get(p.name, p) for p in sources()] + [
        ROOT / "rtl/spk286_timing_pilot/p06_clock.sv",
        selected["p06_instruction_duration.sv"],
    ]


def no_private_input_cone(module, inputs):
    private_bits = {bit for name in inputs for bit in module["ports"][name]["bits"] if isinstance(bit, int)}
    used_bits = {bit for cell in module["cells"].values() for bits in cell["connections"].values()
                 for bit in bits if isinstance(bit, int)}
    output_bits = {bit for port in module["ports"].values() if port["direction"] == "output"
                   for bit in port["bits"] if isinstance(bit, int)}
    assert not private_bits & (used_bits | output_bits), inputs


def synthesize(out, module, label, path, setting):
    stem = out / f"generic-{module}-{label}"
    script = stem.with_suffix(".ys")
    net = stem.with_suffix(".json")
    script.write_text(f"read_verilog -sv {path}\n" + setting +
                      f"synth -top {module} -flatten\nwrite_json {net}\n")
    log = run(["yosys", "-Q", "-s", script], stem.with_suffix(".log"))
    assert "Warning:" not in log, (module, label)
    return generic_stats(net)


def prove(out, module, label, golden, changed, setting="", outputs=(), state_renames=()):
    script = out / f"{label}-equivalence.ys"
    script.write_text(f"read_verilog -sv {golden}\n" + setting +
        f"proc\nopt\nrename {module} gold\nread_verilog -sv {changed}\n" + setting +
        f"proc\nopt\nrename {module} gate\n" +
        ("cd gate\n" + "".join(f"rename {old} {new}\n" for old, new in state_renames) + "cd ..\n" if state_renames else "") +
        ("delete -output " + " ".join("gate/" + name for name in outputs) + "\n" if outputs else "") +
        "equiv_make gold gate equiv\nhierarchy -top equiv\nequiv_simple\n" +
        "equiv_induct -seq 4\nequiv_status -assert\n")
    result = run(["yosys", "-Q", "-s", script], out / f"{label}-equivalence.log")
    assert "Equivalence successfully proven!" in result, label
    return True


def prepare(out, selected):
    """Return recorded costs/proofs after bounded component preparation."""
    out = Path(out)
    receipt_path = ROOT / "docs/evidence/p06-core-memory-20261004/receipt.json"
    assert sha(receipt_path) == M6C_RECEIPT_SHA256
    receipt = json.loads(receipt_path.read_text())
    for name, expected in receipt["sources_sha256"].items():
        assert sha(ROOT / name) == expected, name
    previous_dir = out / "m6c-component-source"
    previous_dir.mkdir()
    previous = build_memory(previous_dir)
    assert set(previous) == set(receipt["generated_cpu_sha256"])
    for name, path in previous.items():
        assert sha(path) == receipt["generated_cpu_sha256"][name], name

    for label, timed, odd in [("max", 0, 0), ("aligned", 1, 0), ("odd", 1, 1)]:
        params = [f"-G{name}=1'b{timed}" for name in [
            "P06_REGISTER_PILOT", "P06_FETCH_PILOT", "P06_IU_PILOT", "P06_MEMORY_PILOT"]]
        params.append(f"-GP06_ODD_READ_PILOT=1'b{odd}")
        run(["verilator", "--lint-only", "--Wall", "--top-module", "spk286", *params,
             "-I" + str(CPU / "rtl"), *select(selected)], out / f"lint-{label}.log")
        print(f"M6E_LINT_PASS {label}", flush=True)

    costs = {"spk286_biu": {}, "p06_instruction_duration": {}}
    biu = selected["spk286_biu.sv"]
    for label, path, timed, odd in [
        ("original", CPU / "rtl/spk286_biu.sv", None, None),
        ("m6c", previous["spk286_biu.sv"], 1, None),
        ("aligned", biu, 1, 0), ("odd", biu, 1, 1), ("max", biu, 0, 0),
    ]:
        setting = ""
        if timed is not None:
            setting = f"chparam -set P06_DATA_TIMING {timed} -set P06_SHARED_TIMING {timed}"
            if odd is not None:
                setting += f" -set P06_ODD_READ_TIMING {odd}"
            setting += " spk286_biu\n"
        costs["spk286_biu"][label] = synthesize(out, "spk286_biu", label, path, setting)

    policy = selected["p06_instruction_duration.sv"]
    original_policy = ROOT / "rtl/spk286_timing_pilot/p06_instruction_duration.sv"
    for label, path, historical, late in [
        ("original", original_policy, 1, None),
        ("aligned", policy, 1, 0), ("odd", policy, 1, 1), ("max", policy, 0, 1),
    ]:
        setting = f"chparam -set HISTORICAL {historical}"
        if late is not None:
            setting += f" -set P06_LATE_ALIGNMENT {late}"
        setting += " p06_instruction_duration\n"
        costs["p06_instruction_duration"][label] = synthesize(out, "p06_instruction_duration", label, path, setting)
    for module, old in [("spk286_biu", "m6c"), ("p06_instruction_duration", "original")]:
        assert costs[module]["aligned"]["register_bits"] == costs[module][old]["register_bits"]
    assert costs["spk286_biu"]["max"]["register_bits"] == costs["spk286_biu"]["original"]["register_bits"]
    assert costs["p06_instruction_duration"]["max"]["register_bits"] == 0
    assert costs["p06_instruction_duration"]["odd"]["register_bits"] == costs["p06_instruction_duration"]["original"]["register_bits"]

    # Golden inputs are arbitrary but ignored by the unchanged original logic.
    # Delete only new gate outputs, never private inputs or functional ports.
    golden = out / "biu-max-gold.sv"
    golden.write_text(replace_once((CPU / "rtl/spk286_biu.sv").read_text(), "module spk286_biu (",
        "module spk286_biu (\n    input logic " + ", ".join(BIU_INPUTS) + ","), newline="\n")
    proofs = {"biu_max": prove(out, "spk286_biu", "biu-max", golden, biu, outputs=BIU_OUTPUTS)}
    # The extra generate alternative changes only the aligned state wire's
    # hierarchical name. Establish its explicit structural correspondence;
    # no inputs, transition logic, outputs or equivalence obligations change.
    proofs["biu_aligned"] = prove(out, "spk286_biu", "biu-aligned", previous["spk286_biu.sv"], biu,
        setting="chparam -set P06_DATA_TIMING 1 -set P06_SHARED_TIMING 1 spk286_biu\n",
        outputs=["p06_alignment_event"],
        state_renames=[("genblk2.p06_data.state_q", "p06_data.state_q")])
    golden = out / "duration-aligned-gold.sv"
    golden.write_text(replace_once(original_policy.read_text(), "    input logic read_wait_event,",
        "    input logic alignment_event,\n    input logic read_wait_event,"), newline="\n")
    proofs["duration_aligned"] = prove(out, "p06_instruction_duration", "duration-aligned", golden, policy)

    maximum = json.loads((out / "generic-spk286_biu-max.json").read_text())["modules"]["spk286_biu"]
    no_private_input_cone(maximum, BIU_INPUTS)
    for name, constant in [("p06_scope_error", "0"), ("p06_scope_block", "0"),
                           ("p06_code_admission", "1"), ("p06_read_wait_event", "0"),
                           ("p06_alignment_event", "0")]:
        assert maximum["ports"][name]["bits"] == [constant], name
    for label in ["aligned", "max"]:
        module = json.loads((out / f"generic-p06_instruction_duration-{label}.json").read_text())["modules"]["p06_instruction_duration"]
        no_private_input_cone(module, ["alignment_event"])
    proofs["max_biu_private_control_cones_absent"] = True
    proofs["duration_late0_alignment_cone_absent"] = True
    proofs["duration_hist0_alignment_cone_absent"] = True
    result = {"costs": costs, "proofs": proofs,
              "ancestor_receipt_sha256": M6C_RECEIPT_SHA256,
              "aligned_state_correspondence": {"gate": "genblk2.p06_data.state_q", "gold": "p06_data.state_q"},
              "scope": "Isolated BIU/duration Yosys mapping and MAX/default bypass; not directed odd-word CPU acceptance, total FPGA cost, fit or STA"}
    (out / "component-checks.json").write_text(json.dumps(result, indent=2) + "\n")
    print("M6E_COMPONENT_PREPARE_PASS", flush=True)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    out.relative_to(ROOT.resolve())
    out.mkdir(parents=True, exist_ok=False)
    prepare(out, build(out))
