#!/usr/bin/env python3
"""Directed checks for unwired P06 components; no Quartus or full regression."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
STAGES = {
    "clock": {
        "sources": ["rtl/spk286_timing_pilot/p06_clock.sv"],
        "bench": "sim/spk286_timing_pilot/p06_clock_tb.sv",
        "top": "p06_clock", "pass": "P06_CLOCK_PASS",
        "negative": ("6'd6", "6'd5", "rational enable mismatch"),
    },
    "bus": {
        "sources": ["rtl/spk286_timing_pilot/p06_bus_cycle.sv",
                    "rtl/spk286_timing_pilot/p06_clock.sv"],
        "bench": "sim/spk286_timing_pilot/p06_bus_cycle_tb.sv",
        "top": "p06_bus_cycle", "pass": "P06_BUS_PASS",
        "negative": ("cpu_boundary && (state_q == TC)",
                     "1'b1 && (state_q == TC)", "early logical completion"),
    },
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(args, output, timeout=180):
    result = subprocess.run(args, cwd=ROOT, text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, timeout=timeout)
    output.write_text(result.stdout)
    if result.returncode:
        raise RuntimeError(f"Command failed ({result.returncode}): {args}\n"
                           f"{result.stdout[-4000:]}")
    return result.stdout


def generic_stats(path):
    design = json.loads(path.read_text())
    modules = design["modules"]
    assert len(modules) == 1, "synthesis must flatten the measured component"
    module = next(iter(modules.values()))
    cells = module.get("cells", {})
    counts = {}
    registers = 0
    for cell in cells.values():
        kind = cell["type"]
        counts[kind] = counts.get(kind, 0) + 1
        if "DFF" in kind.upper():
            registers += len(cell["connections"]["Q"])
    return {"generic_cells": len(cells), "register_bits": registers,
            "cell_types": counts,
            "scope": "Yosys generic mapping; not Cyclone V ALMs, fit or STA"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=STAGES, required=True)
    parser.add_argument("--output", type=Path, required=True)
    options = parser.parse_args()
    output = options.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    stage = STAGES[options.stage]
    top = stage["top"]
    bench_top = top + "_tb"
    sources = stage["sources"]
    paths = sources + [stage["bench"], "scripts/run_p06_pilot.py"]
    before = {path: sha(ROOT / path) for path in paths}
    baseline = json.loads((ROOT / "docs/evidence/p06-intel-contract-20261003/manifest.json").read_text())
    production = baseline["integration_reference"]["sources"]
    for path, metadata in production.items():
        assert sha(ROOT / path) == metadata["sha256"], f"Production changed: {path}"
    versions = {}
    for tool, args in [("iverilog", ["iverilog", "-V"]),
                       ("verilator", ["verilator", "--version"]),
                       ("yosys", ["yosys", "-V"])]:
        versions[tool] = run(args, output / (tool + "-version.log")).splitlines()[0]
    run(["verilator", "--lint-only", "--top-module", top, "-Wall", *sources],
        output / "lint.log")
    run(["iverilog", "-g2012", "-s", bench_top, "-o", str(output / "test.vvp"),
         *sources, stage["bench"]], output / "iverilog-build.log")
    iv = run(["vvp", str(output / "test.vvp")], output / "iverilog-run.log")
    run(["verilator", "--binary", "--timing", "-j", "4", "--top-module", bench_top,
         "--Mdir", str(output / "verilator-obj"), "-o", "pilot-test",
         *sources, stage["bench"]], output / "verilator-build.log")
    vlt = run([str(output / "verilator-obj/pilot-test")], output / "verilator-run.log")
    assert stage["pass"] in iv and stage["pass"] in vlt, "Missing explicit PASS"
    original = (ROOT / sources[0]).read_text()
    old, new, reason = stage["negative"]
    assert original.count(old) == 1, "Mutation source guard failed"
    mutant = output / "negative.sv"
    mutant.write_text(original.replace(old, new))
    run(["iverilog", "-g2012", "-s", bench_top, "-o", str(output / "negative.vvp"),
         str(mutant), *sources[1:], stage["bench"]], output / "negative-build.log")
    negative = subprocess.run(["vvp", str(output / "negative.vvp")], cwd=ROOT,
                              text=True, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, timeout=30)
    (output / "negative-run.log").write_text(negative.stdout)
    assert negative.returncode != 0 and reason in negative.stdout, "Negative control did not fail for the intended reason"
    measured = {}
    for historical in [0, 1]:
        netlist = output / f"generic-{historical}.json"
        # Paths belong to this fresh, caller-named output; no shell interpolation.
        ys = output / f"generic-{historical}.ys"
        ys.write_text("read_verilog -sv " + " ".join(sources) + "\n" +
                      f"chparam -set HISTORICAL {historical} {top}\n" +
                      f"synth -top {top} -flatten\n" +
                      f"write_json {netlist}\n")
        run(["yosys", "-Q", "-s", str(ys)], output / f"yosys-{historical}.log")
        measured[str(historical)] = generic_stats(netlist)
    assert before == {path: sha(ROOT / path) for path in paths}, "Inputs changed during checks"
    for path, metadata in production.items():
        assert sha(ROOT / path) == metadata["sha256"], f"Production changed: {path}"
    receipt = {"status": "P06_DIRECTED_COMPONENT_PASS", "stage": options.stage,
               "sources_sha256": before, "tool_versions": versions,
               "production_sources_unchanged": len(production),
               "production_qip_excludes_pilot": "spk286_timing_pilot" not in
                   (ROOT / "rtl/spk286_integration/spk286_integration.qip").read_text(),
               "generic_synthesis": measured,
               "negative_control": {"mutation": f"{old} -> {new}",
                                    "returncode": negative.returncode,
                                    "expected_reason": reason},
               "log_sha256": {p.name: sha(p) for p in output.glob("*.log")},
               "scope": "Unwired component, strict RTL lint, Icarus/Verilator directed checks and generic synthesis; no full regression, fit or historical CPU accuracy"}
    assert receipt["production_qip_excludes_pilot"]
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(iv.strip())
    print(json.dumps({"status": receipt["status"], "generic_synthesis": measured}, indent=2))


if __name__ == "__main__":
    main()
