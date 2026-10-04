#!/usr/bin/env python3
"""Directed MAX equivalence and private full-CPU 6 MHz register acceptance."""
import argparse
import csv
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET
from run_p06_pilot import generic_stats

from build_p06_register_cpu import build
from run_p06_core_register import ROOT, CPU, sources, sha, run, vectors


def simulate(out, name, rtl, bench, top, vector_path, extra=()):
    directory = out / name
    directory.mkdir()
    include = ["-I" + str(CPU / "rtl"), "-I" + str(CPU / "sim/unit")]
    run(["iverilog", "-g2012", "-s", top, *include, "-o", directory / "test.vvp", *rtl, bench], directory / "iverilog-build.log")
    run(["verilator", "--binary", "--timing", "--assert", "-j", "4", "--top-module", top,
         "--Mdir", directory / "obj", "-o", "cpu-test", *include, *rtl, bench], directory / "verilator-build.log", timeout=600)
    return execute(directory, "normal", vector_path, extra)


def execute(directory, label, vector_path, extra=()):
    prefix = directory / label
    for tool, command in [("iverilog", ["vvp", directory / "test.vvp"]),
                          ("verilator", [directory / "obj/cpu-test"])]:
        run([*command, f"+vectors={vector_path}", f"+trace={prefix}-{tool}-trace.csv",
             f"+summary={prefix}-{tool}-summary.csv", *extra], directory / (label + "-" + tool + "-run.log"))
    for artifact in ["trace.csv", "summary.csv"]:
        assert Path(str(prefix) + "-iverilog-" + artifact).read_bytes() == Path(str(prefix) + "-verilator-" + artifact).read_bytes(), (label, artifact)
    return list(csv.DictReader(Path(str(prefix) + "-iverilog-summary.csv").open()))


def unit(out, name, rtl):
    directory = out / name; directory.mkdir()
    top = name + "_tb"
    include = ["-I" + str(CPU / "rtl"), "-I" + str(CPU / "sim/unit")]
    bench = CPU / "sim/unit" / (top + ".sv")
    run(["iverilog", "-g2012", "-s", top, *include, "-o", directory / "test.vvp", *rtl, bench], directory / "iverilog-build.log")
    run(["vvp", directory / "test.vvp"], directory / "iverilog-run.log")
    run(["verilator", "--binary", "--timing", "--assert", "-j", "4", "--top-module", top,
         "--Mdir", directory / "obj", "-o", "cpu-test", *include, *rtl, bench], directory / "verilator-build.log", timeout=600)
    run([directory / "obj/cpu-test"], directory / "verilator-run.log")
    markers = [[line for line in (directory / (tool + "-run.log")).read_text().splitlines() if "PASS" in line]
               for tool in ["iverilog", "verilator"]]
    assert markers[0] == markers[1] and len(markers[0]) == 1
    return markers[0][0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve(); out.mkdir(parents=True, exist_ok=False)
    original = sources()
    inputs = original + [ROOT / p for p in [
        "rtl/spk286_timing_pilot/p06_register_connection.svh",
        "rtl/spk286_timing_pilot/p06_clock.sv",
        "rtl/spk286_timing_pilot/p06_instruction_duration.sv",
        "sim/spk286_timing_pilot/p06_core_register_tb.sv",
        "sim/spk286_timing_pilot/p06_core_timed_register_tb.sv",
        "sim/spk286_timing_pilot/p06_register_policy_cost.sv",
        "scripts/build_p06_register_cpu.py", "scripts/run_p06_core_register.py",
        "scripts/run_p06_timed_register.py", "scripts/run_p06_pilot.py", "scripts/test_at_landmark_dma.sh",
        "rtl/spk286_integration/spk286_integration.qip"]]
    unit_names = ["spk286_register_execution", "spk286_immediate_execution", "spk286_timing_policy_equivalence"]
    inputs += [CPU / "sim/unit" / (name + "_tb.sv") for name in unit_names]
    before = {p.relative_to(ROOT).as_posix(): sha(p) for p in inputs}
    versions = {tool: run(args, out / (tool + "-version.log")).splitlines()[0] for tool, args in [
        ("iverilog", ["iverilog", "-V"]), ("verilator", ["verilator", "--version"]),
        ("yosys", ["yosys", "-V"])]}
    run(["python3", "-m", "tools.microcode.compile_microcode", "--check"], out / "microcode.log", cwd=CPU)
    replacements = build(out)
    private = [replacements.get(p.name, p) for p in original]
    private += [ROOT / "rtl/spk286_timing_pilot/p06_clock.sv",
                ROOT / "rtl/spk286_timing_pilot/p06_instruction_duration.sv"]
    for historical in [0, 1]:
        run(["verilator", "--lint-only", "--Wall", "--top-module", "spk286",
             f"-GP06_REGISTER_PILOT=1'b{historical}", "-I" + str(CPU / "rtl"), *private], out / f"lint-{historical}.log")
    count = vectors(out / "vectors.txt")
    probe = ROOT / "sim/spk286_timing_pilot/p06_core_register_tb.sv"
    simulate(out, "original-max", original, probe, "p06_core_register_tb", out / "vectors.txt")
    simulate(out, "private-max", private, probe, "p06_core_register_tb", out / "vectors.txt")
    for artifact in ["trace.csv", "summary.csv"]:
        assert (out / ("original-max/normal-iverilog-" + artifact)).read_bytes() == (out / ("private-max/normal-iverilog-" + artifact)).read_bytes(), "MAX changed: " + artifact
    lines = (out / "vectors.txt").read_text().splitlines()
    # Add 13 deliberately late physical dependencies. Never certify their
    # implementation extensions as physical board wait states.
    late = []
    for i, line in enumerate(lines[::16]):
        fields = line.split(); fields[0] = str(count + i); fields[4] = "2"
        late.append(" ".join(fields))
    (out / "timed-vectors.txt").write_text("\n".join(lines + late) + "\n")
    (out / "lifecycle-vectors.txt").write_text("\n".join(lines[::16]) + "\n")
    timed = simulate(out, "historical", private, ROOT / "sim/spk286_timing_pilot/p06_core_timed_register_tb.sv",
                     "p06_core_timed_register_tb", out / "timed-vectors.txt")
    assert len(timed) == count + len(late)
    for action in range(1, 6):
        execute(out / "historical", f"action{action}", out / "lifecycle-vectors.txt", [f"+action={action}"])
    scopes = [([0x90], 1), ([0xf3, 0x01, 0xd8], 1), ([0x01, 0x00], 2),
              ([0x81, 0xd3, 1, 0], 2), ([0x83, 0xfb, 1], 2), ([0x30, 0xfa], 1)]
    records = []
    for i, (code, reason) in enumerate(scopes):
        fields = lines[0].split(); fields[:3] = [str(i), str(reason), str(len(code))]
        fields[5] = f"{int.from_bytes(bytes(code), 'little'):08x}"
        records.append(" ".join(fields))
    (out / "scope-vectors.txt").write_text("\n".join(records) + "\n")
    execute(out / "historical", "scope", out / "scope-vectors.txt", ["+scope_test"])
    fields = lines[0].split(); fields[1] = "3"
    (out / "protected-vector.txt").write_text(" ".join(fields) + "\n")
    execute(out / "historical", "protected", out / "protected-vector.txt", ["+scope_test", "+protected_test"])
    stream = []
    regs = int(lines[0].split()[6], 16)
    old = 2
    # Independent expected stream: four ADD AX,BX, BX=3333h, AX initially zero.
    for i, flags in enumerate([6, 6, 0x886, 0x86]):
        fields = lines[0].split(); fields[0] = str(i); fields[3] = f"{0x100+2*i:04x}"
        fields[6] = f"{regs:032x}"; fields[7] = f"{old:04x}"
        regs = (regs & ~0xffff) | ((i+1)*0x3333 & 0xffff)
        fields[8] = f"{regs:032x}"; fields[9] = f"{flags:04x}"
        stream.append(" ".join(fields)); old = flags
    (out / "stream-vectors.txt").write_text("\n".join(stream) + "\n")
    stream_rows = execute(out / "historical", "stream", out / "stream-vectors.txt", ["+stream_test"])
    max_unit_results = {name: unit(out, name, private) for name in unit_names}
    # Timing bypass mutation: functional answers alone cannot pass acceptance.
    mutant = out / "mutant-spk286.sv"
    mutated = replacements["spk286.sv"].read_text()
    anchor = "(!p06_result_pending || permit)"
    assert mutated.count(anchor) == 1
    mutant.write_text(mutated.replace(anchor, "1'b1"))
    run(["iverilog", "-g2012", "-s", "p06_core_timed_register_tb", "-I" + str(CPU / "rtl"),
         "-I" + str(CPU / "sim/unit"), "-o", out / "negative.vvp",
         *[mutant if p == replacements["spk286.sv"] else p for p in private],
         ROOT / "sim/spk286_timing_pilot/p06_core_timed_register_tb.sv"], out / "negative-build.log")
    result = subprocess.run(["vvp", str(out / "negative.vvp"), f"+vectors={out}/vectors.txt",
        f"+trace={out}/negative-trace.csv", f"+summary={out}/negative-summary.csv"],
        cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30)
    (out / "negative-run.log").write_text(result.stdout)
    assert result.returncode != 0 and "commit preceded qualified virtual deadline" in result.stdout
    # MAX elaboration must discard the entire temporal generate branch.
    run(["verilator", "--xml-only", "--flatten", "--top-module", "spk286", "-GP06_REGISTER_PILOT=1'b0",
         "--xml-output", out / "maximum.xml", "-I" + str(CPU / "rtl"), *private], out / "maximum-elaboration.log")
    xml = ET.parse(out / "maximum.xml")
    scopes_xml = [node.attrib.get("name", "") for node in xml.iter()]
    assert not any("p06_register." in name or "p06_register__DOT__" in name or name == "p06_register"
                   for name in scopes_xml), "MAX retains temporal state"
    measured = {}
    top = "p06_register_policy_cost"
    for historical in [0, 1]:
        netlist = out / f"generic-{historical}.json"
        ys = out / f"generic-{historical}.ys"
        ys.write_text("read_verilog -sv -I" + str(ROOT / "rtl/spk286_timing_pilot") + " " +
            " ".join(str(ROOT / p) for p in ["rtl/spk286_timing_pilot/p06_clock.sv",
                "rtl/spk286_timing_pilot/p06_instruction_duration.sv",
                "sim/spk286_timing_pilot/p06_register_policy_cost.sv"]) + "\n" +
            f"chparam -set P06_REGISTER_PILOT {historical} {top}\n" +
            f"synth -top {top} -flatten\nwrite_json {netlist}\n")
        run(["yosys", "-Q", "-s", ys], out / f"yosys-{historical}.log")
        measured[str(historical)] = generic_stats(netlist)
        # An unresolved hierarchical diagnostic would make cost misleading.
        log = (out / f"yosys-{historical}.log").read_text()
        assert "Warning:" not in log and "ERROR:" not in log
    assert measured["0"]["register_bits"] == 0
    assert before == {p.relative_to(ROOT).as_posix(): sha(p) for p in inputs}
    assert "spk286_timing_pilot" not in (ROOT / "rtl/spk286_integration/spk286_integration.qip").read_text()
    receipt = {"status": "P06_PRIVATE_FULL_CPU_REGISTER_PASS", "normal_cases": count,
        "late_dependency_cases": len(late), "lifecycle_cases": 5 * len(lines[::16]),
        "scope_stop_cases": len(scopes) + 1, "stream_cases": len(stream_rows),
        "max_directed_units": max_unit_results, "tool_versions": versions,
        "sources_sha256": before, "generated_cpu_sha256": {p.name: sha(p) for p in replacements.values()},
        "max_cycle_trace_equal": True, "dual_simulator_all_traces_equal": True,
        "max_temporal_generate_pruned": True, "production_sources_unchanged": True,
        "production_qip_excludes_pilot": True,
        "negative_control": {"returncode": result.returncode, "expected_reason": "commit preceded qualified virtual deadline"},
        "minimum_clocks": {"register_register": 2, "register_immediate": 3},
        "generic_synthesis_top": top, "generic_synthesis": measured,
        "late_dependency_extensions": [int(r["elapsed"]) - (2 if int(r["form"]) < 3 else 3) for r in timed[count:]],
        "scope": "Private CPU register minima/architectural commit, not historical BIU/IU/events or FPGA cost/STA",
        "artifacts_sha256": {p.relative_to(out).as_posix(): sha(p) for p in out.rglob("*")
            if p.is_file() and p.suffix in [".log", ".csv", ".txt"]}}
    (out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({k: v for k, v in receipt.items() if k not in ["sources_sha256", "artifacts_sha256", "generated_cpu_sha256"]}, indent=2))


if __name__ == "__main__":
    main()
