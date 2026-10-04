#!/usr/bin/env python3
"""Directed retained CODE timing acceptance; private CPU, production unchanged."""
import argparse
import csv
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

from build_p06_fetch_cpu import build, replace_once
from run_p06_core_register import ROOT, CPU, sources, sha, run, vectors
from run_p06_pilot import generic_stats
from run_p06_timed_register import simulate, execute, unit


def full_cpu_bench(out):
    """Extend the frozen M3 oracle; warm/cold fetch are separate experiments."""
    text = (ROOT / "sim/spk286_timing_pilot/p06_core_timed_register_tb.sv").read_text()
    text = text.replace("p06_core_timed_register_tb", "p06_core_timed_fetch_tb")
    text = replace_once(text, ".P06_REGISTER_PILOT(1'b1)", ".P06_REGISTER_PILOT(1'b1), .P06_FETCH_PILOT(1'b1)")
    text = replace_once(text, "bit scope_test = 0", "bit warm_test = 0, warming = 0;\n    integer reserved_bytes;\n    bit scope_test = 0")
    text = replace_once(text, "if (address < 4096)", "if (ready && bus_valid && address < 4096)")
    text = replace_once(text, "data_in = 16'hffff;", "data_in = 16'hBAD0;")
    text = replace_once(text, "(control_error && !(action == 2 && redirect && !ip_write_en))", "(control_error && !warming && !(action == 2 && redirect && !ip_write_en))")
    text = replace_once(text, "checks = checks + 1;", """checks = checks + 1;
                reserved_bytes = (dut.fetch.p06_historical.state_q == 1 || dut.fetch.p06_historical.state_q == 2) ?
                    int'(dut.fetch.request_count_q) : (dut.fetch.raw_response_valid ? int'(dut.fetch.raw_response_count) : 0);
                if (int'(debug_prefetch_count)+reserved_bytes > 6)
                    $fatal(1, "full CPU prefetch plus reserved bytes exceed six");
                if (dut.p06_code_bus.scope_error) $fatal(1, "unqualified CODE pilot bus request");""")
    text = replace_once(text, "end else setup();", """end else begin
                setup();
                if (warm_test && !scope_test) begin
                    // Existing invalid-controller transaction holds EU, while
                    // the real fetch fills its six bytes. No forced queue state.
                    warming = 1; redirect = 1; ip_write_en = 0; ready = 1;
                    while ((debug_prefetch_count < 5 || bus_valid || dut.fetch.raw_response_valid) && cycle < 300) tick();
                    // An odd first fetch contributes one byte, then two words:
                    // five bytes are available; a further word would exceed six.
                    if (debug_prefetch_count < 5 || started != 0 || dut.fetch.raw_response_valid || bus_valid)
                        $fatal(1, "warm setup did not prefill bytes before dispatch");
                    redirect = 0; warming = 0;
                    cycle = 0; consumes = 0; transfers = 0; writes = 0;
                end
            end""")
    text = replace_once(text, 'scope_test = $test$plusargs("scope_test");', 'warm_test = $test$plusargs("warm_test");\n        scope_test = $test$plusargs("scope_test");')
    # Preserve the independent 2/3-clock minima and architectural oracle. A
    # cold missing ModRM/immediate is a real dependency, not a board wait.
    text = replace_once(text, "action == 0 && ready_mode < 2 && retire_clock", "warm_test && action == 0 && ready_mode < 2 && retire_clock")
    text = replace_once(text, "start_clock-previous_retire_clock != 1", "start_clock-previous_retire_clock < 1")
    path = out / "p06_core_timed_fetch_tb.sv"
    path.write_text(text, newline="\n")
    return path


def component(out, selected):
    rtl = [selected["spk286_fetch.sv"], CPU / "rtl/spk286_prefetch_queue.sv",
           ROOT / "rtl/spk286_timing_pilot/p06_clock.sv"]
    rows = simulate(out, "fetch", rtl, ROOT / "sim/spk286_timing_pilot/p06_fetch_timing_tb.sv",
                    "p06_fetch_timing_tb", out / "vectors.txt")
    assert len(rows) == 297
    # Force publication of the original slot before Tc: timing oracle must fail.
    mutant = out / "mutant-fetch.sv"
    text = selected["spk286_fetch.sv"].read_text()
    text = replace_once(text, "((state_q == PUBLISHED && raw_response_valid) || p06_complete)",
                        "(raw_response_valid || p06_complete)")
    mutant.write_text(text, newline="\n")
    run(["iverilog", "-g2012", "-s", "p06_fetch_timing_tb", "-o", out / "negative.vvp",
         mutant, *rtl[1:], ROOT / "sim/spk286_timing_pilot/p06_fetch_timing_tb.sv"], out / "negative-build.log")
    result = subprocess.run(["vvp", str(out / "negative.vvp"), f"+trace={out}/negative-trace.csv",
                             f"+summary={out}/negative-summary.csv"], cwd=ROOT, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30)
    (out / "negative-run.log").write_text(result.stdout)
    assert result.returncode != 0 and "publication before logical Tc" in result.stdout
    return rows, result.returncode


def fetch_unit(out, selected):
    # Keep the production test assertions. Only new private inputs are adapted.
    text = (CPU / "sim/unit/spk286_fetch_tb.sv").read_text()
    text = replace_once(text, "module spk286_fetch_tb;", "module spk286_fetch_tb;\n    wire p06_cpu_boundary = 1'b0, p06_board_ready = 1'b1, p06_admission_enable = 1'b1;")
    bench = out / "spk286_fetch_tb.sv"; bench.write_text(text, newline="\n")
    directory = out / "fetch-max-unit"; directory.mkdir()
    run(["iverilog", "-g2012", "-s", "spk286_fetch_tb", "-o", directory / "test.vvp",
         selected["spk286_fetch.sv"], bench], directory / "iverilog-build.log")
    a = run(["vvp", directory / "test.vvp"], directory / "iverilog-run.log")
    run(["verilator", "--binary", "--timing", "--assert", "-j", "4", "--top-module", "spk286_fetch_tb",
         "--Mdir", directory / "obj", "-o", "cpu-test", selected["spk286_fetch.sv"], bench], directory / "verilator-build.log", timeout=600)
    b = run([directory / "obj/cpu-test"], directory / "verilator-run.log")
    markers = lambda text: [line for line in text.splitlines() if "PASS" in line]
    assert markers(a) == markers(b) and len(markers(a)) == 1
    return markers(a)[0]


def bus_scope_bench(out, historical_bench):
    """Fault-inject otherwise out-of-scope demand at the private bus boundary."""
    text = historical_bench.read_text().replace("p06_core_timed_fetch_tb", "p06_core_fetch_scope_tb")
    text = replace_once(text, 'if (dut.p06_code_bus.scope_error) $fatal(1, "unqualified CODE pilot bus request");',
                        '// Scope stop is the expected result in this guard fixture.')
    text = text[:text.index("    initial begin")] + """    integer bus_mode;
    initial begin
        if (!$value$plusargs("vectors=%s", vectors_path) ||
            !$value$plusargs("trace=%s", trace_path) || !$value$plusargs("summary=%s", summary_path) ||
            !$value$plusargs("bus_mode=%d", bus_mode)) $fatal(1, "required scope fixture inputs missing");
        vector_fd = $fopen(vectors_path,"r"); trace_fd = $fopen(trace_path,"w"); summary_fd = $fopen(summary_path,"w");
        $fwrite(summary_fd,"id,bus_mode,scope_error,hlda,writes,retired\\n");
        while (!$feof(vector_fd)) begin
            scan = $fscanf(vector_fd,"%d %d %d %h %d %h %h %h %h %h %h\\n", id,form,length,start_ip,ready_mode,
                code,initial_gpr,initial_flags,expected_gpr,expected_flags,flags_mask);
            if (scan != 11) $fatal(1,"invalid scope vector");
            setup(); ready = 1;
            while (!dut.micro_executor.register_pending_q && cycle < 500) tick();
            if (!dut.micro_executor.register_pending_q) $fatal(1,"scope injection point not reached");
            case (bus_mode)
                1: hold_request = 1;
                2: force dut.bus_lock = 1'b1;
                3: force dut.memory_request = 1'b1;
                4: force dut.ack_request = 1'b1;
                default: $fatal(1,"invalid bus mode");
            endcase
            repeat (25) begin
                tick();
                if (hlda || instruction_retired || writes != 0 ||
                    (bus_valid && bus_status != 4'hD) || debug_gpr !== initial_gpr || debug_flags !== initial_flags)
                    $fatal(1,"unqualified request leaked grant/traffic/commit");
            end
            if (!dut.p06_code_bus.scope_error) $fatal(1,"bus guard failed to stop explicitly");
            $fwrite(summary_fd,"%0d,%0d,%0d,%0d,%0d,%0d\\n",id,bus_mode,dut.p06_code_bus.scope_error,hlda,writes,instruction_retired);
            hold_request = 0;
            release dut.bus_lock; release dut.memory_request; release dut.ack_request;
            execute_enable = 0; cases = cases + 1;
        end
        $fclose(trace_fd); $fclose(summary_fd); $fclose(vector_fd);
        $display("P06_FETCH_SCOPE_PASS cases=%0d bus_mode=%0d",cases,bus_mode); $finish;
    end
endmodule
"""
    path = out / "p06_core_fetch_scope_tb.sv"; path.write_text(text, newline="\n")
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    out = args.output.resolve(); out.mkdir(parents=True, exist_ok=False)
    original = sources()
    names = ["spk286_register_execution", "spk286_immediate_execution", "spk286_timing_policy_equivalence"]
    inputs = original + [ROOT / p for p in [
        "rtl/spk286_timing_pilot/p06_register_connection.svh", "rtl/spk286_timing_pilot/p06_fetch_connection.svh",
        "rtl/spk286_timing_pilot/p06_fetch_cpu_connection.svh", "rtl/spk286_timing_pilot/p06_clock.sv",
        "rtl/spk286_timing_pilot/p06_instruction_duration.sv", "scripts/build_p06_register_cpu.py",
        "scripts/build_p06_fetch_cpu.py", "scripts/run_p06_core_register.py", "scripts/run_p06_timed_register.py",
        "scripts/run_p06_timed_fetch.py", "scripts/run_p06_pilot.py", "scripts/test_at_landmark_dma.sh",
        "sim/spk286_timing_pilot/p06_core_register_tb.sv", "sim/spk286_timing_pilot/p06_core_timed_register_tb.sv",
        "sim/spk286_timing_pilot/p06_fetch_timing_tb.sv", "rtl/spk286_integration/spk286_integration.qip"]]
    inputs += [CPU / "sim/unit" / (name + "_tb.sv") for name in names + ["spk286_fetch"]]
    before = {p.relative_to(ROOT).as_posix(): sha(p) for p in inputs}
    selected = build(out)
    private = [selected.get(p.name, p) for p in original] + [ROOT / "rtl/spk286_timing_pilot" / p
              for p in ["p06_clock.sv", "p06_instruction_duration.sv"]]
    for historical in [0, 1]:
        value = f"1'b{historical}"
        run(["verilator", "--lint-only", "--Wall", "--top-module", "spk286",
             f"-GP06_REGISTER_PILOT={value}", f"-GP06_FETCH_PILOT={value}", "-I" + str(CPU / "rtl"), *private], out / f"lint-cpu-{historical}.log")
        run(["verilator", "--lint-only", "--Wall", "--top-module", "spk286_fetch",
             f"-GP06_FETCH_TIMING={value}", selected["spk286_fetch.sv"]], out / f"lint-fetch-{historical}.log")
    count = vectors(out / "vectors.txt")
    fetch_rows, negative_rc = component(out, selected)
    if args.smoke:
        print("FETCH_SMOKE_PASS"); return
    run(["python3", "-m", "tools.microcode.compile_microcode", "--check"], out / "microcode.log", cwd=CPU)
    probe = ROOT / "sim/spk286_timing_pilot/p06_core_register_tb.sv"
    simulate(out, "original-max", original, probe, "p06_core_register_tb", out / "vectors.txt")
    simulate(out, "private-max", private, probe, "p06_core_register_tb", out / "vectors.txt")
    for artifact in ["trace.csv", "summary.csv"]:
        assert (out / ("original-max/normal-iverilog-" + artifact)).read_bytes() == (out / ("private-max/normal-iverilog-" + artifact)).read_bytes()
    bench = full_cpu_bench(out)
    cold = simulate(out, "historical", private, bench, "p06_core_timed_fetch_tb", out / "vectors.txt")
    warm = execute(out / "historical", "warm", out / "vectors.txt", ["+warm_test"])
    assert len(cold) == count and len(warm) == count
    for row in warm:
        assert int(row["elapsed"]) == (2 if int(row["form"]) < 3 else 3)
    lines = (out / "vectors.txt").read_text().splitlines()
    (out / "lifecycle-vectors.txt").write_text("\n".join(lines[::16]) + "\n")
    for action in range(1, 6):
        execute(out / "historical", f"action{action}", out / "lifecycle-vectors.txt", [f"+action={action}", "+warm_test"])
    guard_bench = bus_scope_bench(out, bench)
    simulate(out, "bus-guards", private, guard_bench, "p06_core_fetch_scope_tb", out / "lifecycle-vectors.txt", ["+bus_mode=1"])
    for mode in range(2, 5):
        execute(out / "bus-guards", f"mode{mode}", out / "lifecycle-vectors.txt", [f"+bus_mode={mode}"])
    late = []
    for i, line in enumerate(lines[::16]):
        fields = line.split(); fields[0] = str(i); fields[4] = "2"; late.append(" ".join(fields))
    (out / "late-vectors.txt").write_text("\n".join(late) + "\n")
    late_rows = execute(out / "historical", "late", out / "late-vectors.txt")
    scopes = [([0x90], 1), ([0xf3, 0x01, 0xd8], 1), ([0x01, 0x00], 2),
              ([0x81, 0xd3, 1, 0], 2), ([0x83, 0xfb, 1], 2), ([0x30, 0xfa], 1)]
    records = []
    for i, (code, reason) in enumerate(scopes):
        fields = lines[0].split(); fields[:3] = [str(i), str(reason), str(len(code))]
        fields[5] = f"{int.from_bytes(bytes(code), 'little'):08x}"; records.append(" ".join(fields))
    (out / "scope-vectors.txt").write_text("\n".join(records) + "\n")
    execute(out / "historical", "scope", out / "scope-vectors.txt", ["+scope_test"])
    fields = lines[0].split(); fields[1] = "3"
    (out / "protected-vector.txt").write_text(" ".join(fields) + "\n")
    execute(out / "historical", "protected", out / "protected-vector.txt", ["+scope_test", "+protected_test"])
    stream = []; regs = int(lines[0].split()[6], 16); old = 2
    for i, flags in enumerate([6, 6, 0x886, 0x86]):
        fields = lines[0].split(); fields[0] = str(i); fields[3] = f"{0x100+2*i:04x}"
        fields[6] = f"{regs:032x}"; fields[7] = f"{old:04x}"
        regs = (regs & ~0xffff) | ((i+1)*0x3333 & 0xffff)
        fields[8] = f"{regs:032x}"; fields[9] = f"{flags:04x}"
        stream.append(" ".join(fields)); old = flags
    (out / "stream-vectors.txt").write_text("\n".join(stream) + "\n")
    stream_rows = execute(out / "historical", "stream", out / "stream-vectors.txt", ["+stream_test", "+warm_test"])
    max_units = {name: unit(out, name, private) for name in names}
    max_units["spk286_fetch"] = fetch_unit(out, selected)
    run(["verilator", "--xml-only", "--flatten", "--top-module", "spk286", "-GP06_REGISTER_PILOT=1'b0",
         "-GP06_FETCH_PILOT=1'b0", "--xml-output", out / "maximum.xml", "-I" + str(CPU / "rtl"), *private], out / "maximum-elaboration.log")
    xml_names = [node.attrib.get("name", "") for node in ET.parse(out / "maximum.xml").iter()]
    assert not any("p06_register." in n or "p06_historical." in n or "p06_code_bus." in n for n in xml_names)
    measured = {}
    for name, source, historical in [("original", CPU / "rtl/spk286_fetch.sv", None),
                                      ("max", selected["spk286_fetch.sv"], 0), ("timed", selected["spk286_fetch.sv"], 1)]:
        netlist = out / f"generic-{name}.json"; ys = out / f"generic-{name}.ys"
        ys.write_text(f"read_verilog -sv {source}\n" + (f"chparam -set P06_FETCH_TIMING {historical} spk286_fetch\n" if historical is not None else "") +
                      f"synth -top spk286_fetch -flatten\nwrite_json {netlist}\n")
        run(["yosys", "-Q", "-s", ys], out / f"yosys-{name}.log")
        measured[name] = generic_stats(netlist)
        assert "Warning:" not in (out / f"yosys-{name}.log").read_text()
    # Alias names can alter ABC's gate choices; compare aggregate cells/storage
    # and prove sequential fetch equivalence below instead of gate-type identity.
    for key in ["register_bits", "generic_cells"]:
        assert measured["max"][key] == measured["original"][key]
    proof = out / "max-fetch-equivalence.ys"
    proof.write_text(f"read_verilog -sv {CPU}/rtl/spk286_fetch.sv\nproc\nopt\nrename spk286_fetch gold\n" +
        f"read_verilog -sv {selected['spk286_fetch.sv']}\nchparam -set P06_FETCH_TIMING 0 spk286_fetch\nproc\nopt\nrename spk286_fetch gate\n" +
        "delete -input gate/p06_cpu_boundary gate/p06_board_ready gate/p06_admission_enable\n" +
        "equiv_make gold gate equiv\nhierarchy -top equiv\nequiv_simple\nequiv_induct -seq 4\nequiv_status -assert\n")
    run(["yosys", "-Q", "-s", proof], out / "max-fetch-equivalence.log")
    assert "Equivalence successfully proven!" in (out / "max-fetch-equivalence.log").read_text()
    assert before == {p.relative_to(ROOT).as_posix(): sha(p) for p in inputs}
    assert "spk286_timing_pilot" not in (ROOT / "rtl/spk286_integration/spk286_integration.qip").read_text()
    receipt = {"status": "P06_PRIVATE_CODE_FETCH_PASS", "cold_cases": len(cold), "warm_exact_minima": len(warm),
        "fetch_cases": len(fetch_rows), "late_cases": len(late_rows), "lifecycle_cases": 65, "scope_stop_cases": 7,
        "unsupported_bus_guard_cases": 52,
        "stream_cases": len(stream_rows), "max_units": max_units, "negative_returncode": negative_rc,
        "sources_sha256": before, "generated_cpu_sha256": {p.name: sha(p) for p in selected.values()},
        "generated_bench_sha256": sha(bench), "max_trace_equal": True, "dual_simulator_traces_equal": True,
        "production_unchanged": True, "max_fetch_sequential_equivalence": True, "generic_fetch_synthesis": measured,
        "cold_dependency_extensions": [int(r["elapsed"])-(2 if int(r["form"]) < 3 else 3) for r in cold],
        "scope": "Private 6 MHz register/CODE pilot. Data/INTA/HOLD/LOCK/IU/event timing and profile integration remain open.",
        "artifacts_sha256": {p.relative_to(out).as_posix(): sha(p) for p in out.rglob("*")
            if p.is_file() and p.suffix in [".log", ".csv", ".txt", ".ys", ".json", ".sv"]}}
    (out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({k:v for k,v in receipt.items() if k not in ["sources_sha256", "artifacts_sha256", "cold_dependency_extensions"]}, indent=2))


if __name__ == "__main__":
    main()
