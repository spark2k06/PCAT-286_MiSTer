#!/usr/bin/env python3
"""Directed M6c real A1 CPU acceptance, independent of production selection."""
import argparse
import csv
import json
import re
import subprocess
from pathlib import Path
from build_p06_memory_cpu import build, replace_once
from build_p06_iu_cpu import build as build_iu
from run_p06_iu import stream_vectors
from run_p06_core_register import ROOT, CPU, sources, sha, run, vectors
from run_p06_timed_register import simulate, execute
from run_p06_pilot import generic_stats

UNIT_NAMES = ["spk286_biu","spk286_biu_width_io","spk286_biu_hold_lock","spk286_fetch",
    "spk286_prefetch_queue","spk286_operand_service","spk286_operand_lifecycle","spk286_operand_byte",
    "spk286_register_execution","spk286_immediate_execution","spk286_timing_policy_equivalence"]


def memory_vectors(path):
    """Independent sparse-memory A1 caller inputs, no DUT-derived expectations."""
    records = []
    def add(seed,ip,cs,ds,offset,value,flags,cw,dw,cl,dl):
        regs = [(seed+r*0x1357)&0xffff for r in range(8)]; regs[4] = 0x8000
        packed = sum(v<<(16*r) for r,v in enumerate(regs))
        data_address = (ds<<4)+offset
        code_address = (cs<<4)+ip
        assert data_address%2 == 0 and not (code_address-1<=data_address<=code_address+7)
        records.append(f"{len(records)} {ip:04x} {cs:04x} {ds:04x} {offset:04x} {value:04x} {packed:032x} {flags:04x} {cw} {dw} {cl} {dl}")
    for i in range(24):
        add(i*0x1234,0x100+i%2,[0,1,0x1234,0xffff][i%4],
            [0,1,0x2345,0xffff][(i//4)%4],[0,2,0xfe,0xfffe][i%4],
            [0,0xffff,0xff,0xff00,0xa55a,0x5aa5][i%6],[2,0x403,0x8d7][i%3],0,0,0,0)
    for seed in range(3):
        for cw in range(3):
            for dw in range(3):
                for cl in [0,-1,80]:
                    for dl in [0,-1,80]:
                        add([0,0xffff,0x1234][seed],0x100+seed%2,[0,0x2345,0xffff][seed],
                            [1,0x1234,0xabcd][seed],[2,0xfe,0xfffe][seed],
                            [0xa55a,0x1234,0][seed],[2,0x403,0x8d7][seed],cw,dw,cl,dl)
    assert len(records) == 267
    path.write_text("\n".join(records)+"\n")
    return len(records)


def private_bench(out,name):
    """Adapt only the new private ports, retaining production unit assertions."""
    module = name+"_tb"
    text = (CPU/"sim/unit"/(module+".sv")).read_text()
    wires = "\n    wire p06_code_board_ready=1, p06_data_board_ready=1;"
    if name.startswith("spk286_biu"):
        wires += ("\n    wire p06_cpu_boundary=0, p06_board_ready=1, p06_code_issue=0, p06_code_complete=0, p06_code_canceled=0;\n"+
            "    wire p06_scope_error, p06_code_admission, p06_scope_block, p06_read_wait_event;")
    if name == "spk286_fetch":
        wires += ("\n    wire p06_cpu_boundary=0, p06_board_ready=1, p06_admission_enable=1, p06_scope_block=0;\n"+
            "    wire p06_bus_issue, p06_bus_complete, p06_bus_canceled;")
    text = replace_once(text,"module "+module+";","module "+module+";"+wires)
    path = out/(module+".sv"); path.write_text(text,newline="\n")
    return path


def select(selected):
    return [selected.get(p.name,p) for p in sources()]+[
        ROOT/"rtl/spk286_timing_pilot/p06_clock.sv",
        ROOT/"rtl/spk286_timing_pilot/p06_instruction_duration.sv"]


def lint(out,selected):
    for timed in [0,1]:
        params = [f"-G{name}=1'b{timed}" for name in [
            "P06_REGISTER_PILOT","P06_FETCH_PILOT","P06_IU_PILOT","P06_MEMORY_PILOT"]]
        run(["verilator","--lint-only","--Wall","--top-module","spk286",*params,
             "-I"+str(CPU/"rtl"),*select(selected)],out/f"lint-full-{timed}.log")


def max_compatibility(out,selected):
    private = select(selected); results = {}
    includes = ["-I"+str(CPU/"rtl"),"-I"+str(CPU/"sim/unit")]
    for name in UNIT_NAMES:
        module = name+"_tb"; directory = out/name; directory.mkdir()
        bench = private_bench(out,name)
        run(["iverilog","-g2012","-s",module,*includes,"-o",directory/"test.vvp",*private,bench],directory/"iverilog-build.log")
        run(["vvp",directory/"test.vvp"],directory/"iverilog-run.log")
        run(["verilator","--binary","--timing","--assert","-j","4","--top-module",module,
             "--Mdir",directory/"obj","-o","unit-test",*includes,*private,bench],directory/"verilator-build.log",timeout=600)
        run([directory/"obj/unit-test"],directory/"verilator-run.log")
        markers = [[line for line in (directory/(tool+"-run.log")).read_text().splitlines() if "PASS" in line]
                   for tool in ["iverilog","verilator"]]
        assert markers[0] == markers[1] and len(markers[0]) == 1,name
        results[name] = markers[0][0]
        print("MAX_UNIT_PASS "+name,flush=True)
    count = vectors(out/"register-vectors.txt")
    original_probe = ROOT/"sim/spk286_timing_pilot/p06_core_register_tb.sv"
    text = replace_once(original_probe.read_text(),"module p06_core_register_tb;",
        "module p06_core_register_tb;\n    wire p06_code_board_ready=clk, p06_data_board_ready=!clk;")
    private_probe = out/"private-max-probe.sv"; private_probe.write_text(text,newline="\n")
    simulate(out,"original-register-max",sources(),original_probe,"p06_core_register_tb",out/"register-vectors.txt")
    simulate(out,"private-register-max",private,private_probe,"p06_core_register_tb",out/"register-vectors.txt")
    for suffix in ["trace.csv","summary.csv"]:
        assert (out/("original-register-max/normal-iverilog-"+suffix)).read_bytes() == (
            out/("private-register-max/normal-iverilog-"+suffix)).read_bytes()
    assert count == 208
    return results,count


def component_synthesis(out,selected):
    measured = {}
    for name in ["spk286_biu","spk286_fetch"]:
        original = CPU/"rtl"/(name+".sv"); changed = selected[name+".sv"]
        measured[name] = {}
        for label,path,param in [("original",original,None),("max",changed,0),("timed",changed,1)]:
            net = out/f"generic-{name}-{label}.json"; script = out/f"generic-{name}-{label}.ys"
            setting = ""
            if param is not None:
                setting = (f"chparam -set P06_DATA_TIMING {param} -set P06_SHARED_TIMING {param} {name}\n"
                           if name == "spk286_biu" else f"chparam -set P06_FETCH_TIMING {param} {name}\n")
            script.write_text(f"read_verilog -sv {path}\n"+setting+
                             f"synth -top {name} -flatten\nwrite_json {net}\n")
            run(["yosys","-Q","-s",script],out/f"yosys-{name}-{label}.log")
            assert "Warning:" not in (out/f"yosys-{name}-{label}.log").read_text()
            measured[name][label] = generic_stats(net)
        if name == "spk286_biu":
            inputs = ["p06_cpu_boundary","p06_board_ready","p06_code_issue","p06_code_complete","p06_code_canceled"]
            outputs = ["p06_scope_error","p06_code_admission","p06_scope_block","p06_read_wait_event"]
        else:
            inputs = ["p06_cpu_boundary","p06_board_ready","p06_admission_enable","p06_scope_block"]
            outputs = ["p06_bus_issue","p06_bus_complete","p06_bus_canceled"]
        maximum = json.loads((out/f"generic-{name}-max.json").read_text())["modules"][name]
        control_bits = {bit for p in inputs for bit in maximum["ports"][p]["bits"] if isinstance(bit,int)}
        used_bits = {bit for cell in maximum["cells"].values() for bits in cell["connections"].values()
                     for bit in bits if isinstance(bit,int)}
        output_bits = {bit for p in maximum["ports"].values() if p["direction"] == "output"
                       for bit in p["bits"] if isinstance(bit,int)}
        assert not control_bits & (used_bits | output_bits),name
        assert measured[name]["max"]["register_bits"] == measured[name]["original"]["register_bits"]
        golden = out/f"max-{name}-gold.sv"
        golden.write_text(replace_once(original.read_text(),f"module {name} (",
            f"module {name} (\n    input logic "+", ".join(inputs)+","),newline="\n")
        proof = out/f"max-{name}-equivalence.ys"
        proof.write_text(f"read_verilog -sv {golden}\nproc\nopt\nrename {name} gold\n"+
            f"read_verilog -sv {changed}\nproc\nopt\nrename {name} gate\n"+
            "delete -output "+" ".join("gate/"+p for p in outputs)+"\n"+
            "equiv_make gold gate equiv\nhierarchy -top equiv\nequiv_simple\nequiv_induct -seq 4\nequiv_status -assert\n")
        assert "Equivalence successfully proven!" in run(["yosys","-Q","-s",proof],out/f"max-{name}-equivalence.log")
    return measured


def commit_control_synthesis(out,selected):
    """Map the actual new executor assignments only; excludes full CPU scope."""
    package = (CPU/"microcode/generated/spk286_microcode_pkg.sv").read_text()
    width = int(re.search(r"MC_WORD_WIDTH = (\d+)",package)[1])
    move = re.search(r"MC_MOVE = ([^;]+);",package)[1]
    executor = selected["spk286_micro_executor.sv"].read_text()
    fragment = re.search(r"    assign p06_memory_result_pending = .*?\n    assign operation_retire = .*?;",executor,re.S)[0]
    fragment = fragment.replace("spk286_microcode_pkg::MC_MOVE",move)
    probe = out/"p06_memory_commit_cost.sv"
    probe.write_text("module p06_memory_commit_cost #(parameter bit P06_MEMORY_TIMING=1'b0) (\n"+
        f"input logic [{width-1}:0] operation, input logic [2:0] temporary_valid_q,\n"+
        "input logic p06_moffs_read, register_complete, move_word,\n"+
        "output logic p06_memory_result_pending, operation_retire);\n"+fragment+"\nendmodule\n")
    result = {}
    for timed in [0,1]:
        net = out/f"generic-commit-control-{timed}.json"; script = out/f"generic-commit-control-{timed}.ys"
        script.write_text(f"read_verilog -sv {probe}\nchparam -set P06_MEMORY_TIMING {timed} p06_memory_commit_cost\n"+
            f"synth -top p06_memory_commit_cost -flatten\nwrite_json {net}\n")
        run(["yosys","-Q","-s",script],out/f"yosys-commit-control-{timed}.log")
        result[str(timed)] = generic_stats(net)
        assert result[str(timed)]["register_bits"] == 0
    return result


def directed_vectors(out):
    lines = (out/"memory-vectors.txt").read_text().splitlines()
    # All four DS/offset/value classes plus each abstract wait pair and
    # deliberately late physical dependencies. Preserve the caller schema.
    rows = lines[:24:3] + [line for line in lines[24:] if line.split()[10:] == ["0","0"]]
    rows += [line for line in lines[24:] if line.split()[8:] == ["2","2","80","80"]]
    paths = {}
    for name,chosen in [("directed",rows),
        ("odd",[line for line in rows if int(line.split()[4],16)<=0xfffc]),
        ("tc-waits",[line for line in rows if int(line.split()[9])>0]),
        ("deadline",[next(line for line in lines[24:] if line.split()[8:] == ["0",str(wait),"0","0"])
            for wait in range(3)])]:
        paths[name] = out/(name+"-vectors.txt")
        paths[name].write_text("\n".join(chosen)+"\n")
    return paths


def memory_acceptance(out,selected):
    bench = ROOT/"sim/spk286_timing_pilot/p06_core_memory_tb.sv"
    path = out/"memory-vectors.txt"; count = memory_vectors(path)
    normal = simulate(out,"memory",select(selected),bench,"p06_core_memory_tb",path)
    cold = execute(out/"memory","cold",path,["+cold"])
    assert len(normal) == len(cold) == count == 267
    assert all(int(r["retired"]) == 1 and int(r["data_accepts"]) == 1 and int(r["data_captures"]) == 1
               and int(r["elapsed"]) >= 5+int(r["data_external"]) for r in normal+cold)
    assert {int(r["data_external"]) for r in normal+cold} == {0,1,2}
    assert sum(int(r["off_boundary"]) for r in normal+cold)>0
    assert any(int(r["data_misses"])>0 for r in normal+cold)
    assert any(int(r["code_misses"])>0 for r in cold)
    print("A1_MATRIX_PASS warm=267 cold=267",flush=True)
    paths = directed_vectors(out); controls = {}
    for mode in [1,2,3,4,5,6,7,8,9,10,12,13,14,15,16,17,18,20,21]:
        path = paths["tc-waits" if mode in [15,17,18] else "deadline" if mode == 16 else "odd" if mode == 12 else "directed"]
        for warm in [True,False]:
            label = f"mode{mode}-"+("warm" if warm else "cold")
            rows = execute(out/"memory",label,path,[f"+mode={mode}"]+([] if warm else ["+cold"]))
            assert len(rows) == len(path.read_text().splitlines())
            assert all(int(r["mode"]) == mode and bool(int(r["warm"])) == warm for r in rows)
            if mode in [3,4,8,9,18]: assert all(int(r["retired"]) == 0 for r in rows)
            elif mode in [5,10,12,13,14,17]:
                assert all(int(r["retired"]) == 0 and int(r["scope"]) == 1 for r in rows)
            else: assert all(int(r["retired"]) == 1 for r in rows)
            if mode in [20,21]:
                assert all(int(r["rr_started"]) == 1 and int(r["rr_retired"]) == 1 for r in rows)
                if mode == 20 and warm:
                    assert all(int(r["start_cpu"]) == int(r["rr_retire_cpu"]) for r in rows)
                if mode == 21:
                    assert all(int(r["rr_start_cpu"])>int(r["retire_cpu"]) for r in rows)
            controls[label] = len(rows)
        print(f"A1_DIRECTED_PASS mode={mode}",flush=True)
    # A1 MAX uses the exact original instruction path, including its original
    # MOVE/END separation. Full traces, not just final AX, must match.
    maximum = out/"p06_core_memory_max_tb.sv"
    maximum.write_text(replace_once(bench.read_text(),"parameter bit TIMED=1'b1","parameter bit TIMED=1'b0"),newline="\n")
    original = out/"p06_core_memory_original_tb.sv"
    original.write_text("`define P06_ORIGINAL\n"+maximum.read_text(),newline="\n")
    gold = simulate(out,"original-memory-max",sources(),original,"p06_core_memory_tb",out/"memory-vectors.txt")
    gate = simulate(out,"private-memory-max",select(selected),maximum,"p06_core_memory_tb",out/"memory-vectors.txt")
    assert len(gold) == len(gate) == 267
    for suffix in ["trace.csv","summary.csv"]:
        assert (out/("original-memory-max/normal-iverilog-"+suffix)).read_bytes() == (
            out/("private-memory-max/normal-iverilog-"+suffix)).read_bytes()
    print("A1_MAX_TRACE_EQUAL cases=267",flush=True)
    return {"aligned_cases":count,"warm":len(normal),"cold":len(cold),"max_memory":len(gate),"directed":controls,
        "off_boundary_captures":sum(int(r["off_boundary"]) for r in normal+cold)}


def preserve_iu(out,selected):
    directory = out/"frozen-iu-source"; directory.mkdir()
    previous = build_iu(directory)
    path = out/"iu-streams.txt"; count = stream_vectors(path)
    bench = ROOT/"sim/spk286_timing_pilot/p06_core_iu_tb.sv"
    text = replace_once(bench.read_text(),"module p06_core_iu_tb #(parameter bit OVERLAP = 1'b1);",
        "module p06_core_iu_tb #(parameter bit OVERLAP = 1'b1);\n"+
        "    wire p06_code_board_ready=1, p06_data_board_ready=1;")
    text = replace_once(text,".P06_IU_PILOT(OVERLAP)",".P06_IU_PILOT(OVERLAP), .P06_MEMORY_PILOT(1'b1)")
    new_bench = out/"p06_core_iu_memory_tb.sv"; new_bench.write_text(text,newline="\n")
    old = simulate(out,"frozen-iu",select(previous),bench,"p06_core_iu_tb",path)
    new = simulate(out,"memory-iu",select(selected),new_bench,"p06_core_iu_tb",path)
    for label,extra in [("normal",[]),("cold",["+cold"])]:
        if extra:
            execute(out/"frozen-iu",label,path,extra); execute(out/"memory-iu",label,path,extra)
        for suffix in ["trace.csv","summary.csv"]:
            assert (out/("frozen-iu/"+label+"-iverilog-"+suffix)).read_bytes() == (
                out/("memory-iu/"+label+"-iverilog-"+suffix)).read_bytes(), (label,suffix)
    assert count == 688 and len(old) == len(new) == 1448
    print("IU_PRESERVATION_PASS streams=688 instructions=1448 warm_and_cold",flush=True)
    return {"rr_ri_streams":count,"rr_ri_instructions":len(new)}


def negative(out,rtl,bench,label,marker,path=None,old=None,new=None,vector=None,extra=()):
    if path is not None:
        mutant = out/("negative-"+label+"-"+path.name)
        mutant.write_text(replace_once(path.read_text(),old,new),newline="\n")
        rtl = [mutant if p == path else p for p in rtl]
    executable = out/("negative-"+label+".vvp")
    run(["iverilog","-g2012","-s","p06_core_memory_tb","-I"+str(CPU/"rtl"),
        "-I"+str(CPU/"sim/unit"),"-o",executable,*rtl,bench],out/("negative-"+label+"-build.log"))
    result = subprocess.run(["vvp",str(executable),f"+vectors={vector or out/'memory-vectors.txt'}",
        f"+trace={out}/negative-{label}-trace.csv",f"+summary={out}/negative-{label}-summary.csv",*extra],
        cwd=ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=30)
    (out/("negative-"+label+"-run.log")).write_text(result.stdout)
    assert result.returncode != 0 and marker in result.stdout,(label,result.stdout)
    return {"returncode":result.returncode,"marker":marker}


def negative_checks(out,selected):
    rtl = select(selected); bench = ROOT/"sim/spk286_timing_pilot/p06_core_memory_tb.sv"
    checks = {}
    checks["permit"] = negative(out,rtl,bench,"permit","A1 first eligible commit oracle failed",
        selected["spk286.sv"],"(!p06_result_pending || permit)","1'b1")
    checks["duration"] = negative(out,rtl,bench,"duration","A1 READ wait budget oracle failed",
        ROOT/"rtl/spk286_timing_pilot/p06_instruction_duration.sv",
        "base_clocks = 6'd5; memory_form = 1'b1; permits_read_wait = 1'b1;",
        "base_clocks = 6'd6; memory_form = 1'b1; permits_read_wait = 1'b1;")
    checks["read-waits"] = negative(out,rtl,bench,"read-waits","A1 READ wait budget oracle failed",
        selected["spk286.sv"],".read_wait_event(p06_timed_read && p06_read_wait_event)",".read_wait_event(1'b0)",
        out/"tc-waits-vectors.txt")
    checks["pending"] = negative(out,rtl,bench,"pending","A1 original TMP0 pending oracle failed",
        selected["spk286_micro_executor.sv"],
        "operation == spk286_microcode_pkg::MC_MOVE && temporary_valid_q[0];",
        "operation == spk286_microcode_pkg::MC_MOVE && !temporary_valid_q[0];")
    for reg,fetch in [(0,0),(0,1),(1,0)]:
        label=f"config-{reg}{fetch}"
        invalid = out/(label+"-tb.sv")
        # Missing historical generate aliases must not obscure the intended
        # parameter diagnostic; this fixture checks elaborated configuration.
        text = "`timescale 1ns/1ps\nmodule p06_core_memory_tb;\n"+\
            '    `include "spk286_signals.svh"\n'+\
            "    wire p06_code_board_ready=1,p06_data_board_ready=1;\n"+\
            f"    spk286 #(.P06_REGISTER_PILOT(1'b{reg}),.P06_FETCH_PILOT(1'b{fetch}),"+\
            ".P06_MEMORY_PILOT(1'b1)) dut (.*);\n    initial begin #20; $fatal(1,\"missing configuration guard\"); end\nendmodule\n"
        invalid.write_text(text,newline="\n")
        checks[label] = negative(out,rtl,invalid,label,"M6c requires REGISTER and FETCH timing")
    print("A1_NEGATIVE_CHECKS_PASS count=7",flush=True)
    return checks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--prepare",action="store_true")
    parser.add_argument("--max-check",action="store_true")
    args = parser.parse_args(); out = args.output.resolve(); out.mkdir(parents=True,exist_ok=False)
    names = ["scripts/build_p06_memory_cpu.py","scripts/run_p06_memory_cpu.py",
        "scripts/build_p06_shared_bus.py","scripts/build_p06_data_biu.py","scripts/build_p06_iu_cpu.py",
        "scripts/build_p06_fetch_cpu.py","scripts/build_p06_register_cpu.py","scripts/run_p06_iu.py",
        "scripts/run_p06_core_register.py","scripts/run_p06_timed_register.py","scripts/run_p06_timed_fetch.py",
        "scripts/run_p06_pilot.py","rtl/spk286_timing_pilot/p06_clock.sv",
        "rtl/spk286_timing_pilot/p06_instruction_duration.sv","rtl/spk286_timing_pilot/p06_register_connection.svh",
        "rtl/spk286_timing_pilot/p06_fetch_connection.svh","rtl/spk286_timing_pilot/p06_fetch_cpu_connection.svh",
        "rtl/spk286_timing_pilot/p06_iu_connection.svh","rtl/spk286_timing_pilot/p06_data_biu_connection.svh",
        "rtl/spk286_timing_pilot/p06_shared_biu_connection.svh","sim/spk286_timing_pilot/p06_core_memory_tb.sv",
        "sim/spk286_timing_pilot/p06_core_iu_tb.sv","sim/spk286_timing_pilot/p06_core_register_tb.sv",
        "docs/evidence/p06-core-iu-20261004/receipt.json","docs/evidence/p06-core-shared-bus-20261004/receipt.json",
        "docs/evidence/p06-core-data-20261004/receipt.json","docs/evidence/p06-core-fetch-20261004/receipt.json",
        "rtl/spk286_integration/spk286_integration.qip","config.tcl","scripts/test_at_landmark_dma.sh",
        "vendor/spk286/sim/unit/spk286_signals.svh"]
    inputs = sources()+[ROOT/name for name in names]+[CPU/"sim/unit"/(name+"_tb.sv") for name in UNIT_NAMES]
    before = {p.relative_to(ROOT).as_posix():sha(p) for p in inputs}
    selected = build(out)
    lint(out,selected)
    costs = component_synthesis(out,selected)
    commit_cost = commit_control_synthesis(out,selected)
    print("MEMORY_LINT_FORMAL_COST_PASS",flush=True)
    (out/"prepare.json").write_text(json.dumps({"components":costs,"commit_control":commit_cost},indent=2)+"\n")
    if args.max_check:
        results,count = max_compatibility(out,selected)
        (out/"max-checks.json").write_text(json.dumps({"units":results,"register_cases":count},indent=2)+"\n")
        return
    if args.prepare: return
    versions = {name:run(command,out/(name+"-version.log")).splitlines()[0] for name,command in [
        ("iverilog",["iverilog","-V"]),("verilator",["verilator","--version"]),("yosys",["yosys","-V"])]}
    counts = memory_acceptance(out,selected)
    counts.update(preserve_iu(out,selected))
    negatives = negative_checks(out,selected)
    max_units,counts["max_register"] = max_compatibility(out,selected)
    run(["python3","-m","tools.microcode.compile_microcode","--check"],out/"microcode.log",cwd=CPU)
    assert before == {p.relative_to(ROOT).as_posix():sha(p) for p in inputs}, "Sources changed during acceptance"
    assert "spk286_timing_pilot" not in (ROOT/"rtl/spk286_integration/spk286_integration.qip").read_text()
    receipt = {"status":"P06_PRIVATE_MEMORY_CPU_PASS","counts":counts,"components":costs,
        "commit_control":commit_cost,"negative_checks":negatives,"max_units":max_units,
        "dual_traces_equal":True,"max_memory_trace_equal":True,"max_register_trace_equal":True,
        "rr_ri_preserved_warm_cold":True,"max_biu_fetch_sequential_equivalence":True,
        "max_private_control_cones_absent":True,"production_unchanged":True,
        "tool_versions":versions,"sources_sha256":before,
        "generated_cpu_sha256":{name:sha(path) for name,path in selected.items()},
        "scope":"Private M6c full CPU aligned prefix-free Real Mode A1 READ, 6 MHz virtual pilot. "
                "Five-clock minimum plus qualified READ waits; physical dependencies may extend execution. "
                "Not exact Intel issue phasing, decoded three-entry IU, odd words, writes, I/O, "
                "bus/events, complete historical profiles, DOS benchmarks, total FPGA cost, fit or STA.",
        "generic_cost_scope":"Isolated BIU/fetch plus actual executor commit assignments; "
            "not Quartus ALMs or complete timed CPU overhead, and restricted services remain pruned.",
        "artifacts_sha256":{p.relative_to(out).as_posix():sha(p) for p in out.rglob("*") if p.is_file() and
            "obj" not in p.relative_to(out).parts and p.suffix != ".vvp" and p.name != "receipt.json"}}
    (out/"receipt.json").write_text(json.dumps(receipt,indent=2)+"\n")
    print(json.dumps({k:v for k,v in receipt.items() if k not in ["sources_sha256","artifacts_sha256"]},indent=2),flush=True)


if __name__ == "__main__": main()
