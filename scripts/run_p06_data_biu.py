#!/usr/bin/env python3
"""M6a real BIU/operand READ timing acceptance; production and MAX unchanged."""
import argparse
import json
from pathlib import Path
import subprocess
from build_p06_data_biu import build, replace_once
from run_p06_core_register import ROOT, CPU, sources, sha, run, vectors
from run_p06_timed_register import simulate, execute
from run_p06_pilot import generic_stats


def units(out, modified):
    results = {}
    top_source = max_top(out)
    rtl = [top_source if p.name == "spk286.sv" else modified if p.name == "spk286_biu.sv" else p
           for p in sources()]
    include = ["-I"+str(CPU/"rtl"), "-I"+str(CPU/"sim/unit")]
    for name in ["spk286_biu", "spk286_biu_width_io", "spk286_biu_hold_lock",
                 "spk286_operand_service", "spk286_operand_lifecycle", "spk286_operand_byte"]:
        top = name + "_tb"; directory = out/name; directory.mkdir()
        text = (CPU/"sim/unit"/(top+".sv")).read_text()
        if name.startswith("spk286_biu"):
            text = replace_once(text,"module "+top+";","module "+top+";\n"+
                "    wire p06_cpu_boundary = 1'b0, p06_board_ready = 1'b1;\n"+
                "    wire p06_scope_error;")
        bench = out/(top+".sv"); bench.write_text(text,newline="\n")
        run(["iverilog","-g2012","-s",top,*include,"-o",directory/"test.vvp",*rtl,bench],directory/"iverilog-build.log")
        run(["vvp",directory/"test.vvp"],directory/"iverilog-run.log")
        run(["verilator","--binary","--timing","--assert","-j","4","--top-module",top,
             "--Mdir",directory/"obj","-o","unit-test",*include,*rtl,bench],directory/"verilator-build.log",timeout=600)
        run([directory/"obj/unit-test"],directory/"verilator-run.log")
        markers = [[line for line in (directory/(tool+"-run.log")).read_text().splitlines() if "PASS" in line]
                   for tool in ["iverilog","verilator"]]
        assert markers[0] == markers[1] and len(markers[0]) == 1,name
        results[name] = markers[0][0]
    return results


def synthesis(out, modified):
    original = CPU/"rtl/spk286_biu.sv"; measured = {}
    for label,path,param in [("original",original,None),("max",modified,0),("timed",modified,1)]:
        net = out/f"generic-{label}.json"; script = out/f"generic-{label}.ys"
        script.write_text(f"read_verilog -sv {path}\n"+
            (f"chparam -set P06_DATA_TIMING {param} spk286_biu\n" if param is not None else "")+
            f"synth -top spk286_biu -flatten\nwrite_json {net}\n")
        run(["yosys","-Q","-s",script],out/f"yosys-{label}.log")
        assert "Warning:" not in (out/f"yosys-{label}.log").read_text()
        measured[label] = generic_stats(net)
    assert measured["max"]["register_bits"] == measured["original"]["register_bits"]
    proof = out/"max-biu-equivalence.ys"
    proof.write_text(f"read_verilog -sv {original}\nproc\nopt\nrename spk286_biu gold\n"+
        f"read_verilog -sv {modified}\nchparam -set P06_DATA_TIMING 0 spk286_biu\nproc\nopt\nrename spk286_biu gate\n"+
        "delete -input gate/p06_cpu_boundary gate/p06_board_ready\ndelete -output gate/p06_scope_error\n"+
        "equiv_make gold gate equiv\nhierarchy -top equiv\nequiv_simple\nequiv_induct -seq 4\nequiv_status -assert\n")
    result = run(["yosys","-Q","-s",proof],out/"max-biu-equivalence.log")
    assert "Equivalence successfully proven!" in result
    return measured


def max_top(out):
    text = (CPU/"rtl/spk286.sv").read_text()
    text = replace_once(text,"    spk286_biu biu (","    /* verilator lint_off UNUSEDSIGNAL */\n"+
        "    logic p06_scope_unused;\n    /* verilator lint_on UNUSEDSIGNAL */\n"+
        "    spk286_biu biu (\n        .p06_cpu_boundary(1'b0), .p06_board_ready(1'b1),\n"+
        "        .p06_scope_error(p06_scope_unused),")
    top = out/"private-rtl/spk286.sv"; top.write_text(text,newline="\n")
    return top


def full_max(out, modified):
    original = sources()
    top = max_top(out)
    private = [top if p.name=="spk286.sv" else modified if p.name=="spk286_biu.sv" else p for p in original]
    run(["verilator","--lint-only","--Wall","--top-module","spk286","-I"+str(CPU/"rtl"),*private],out/"lint-full-max.log")
    count = vectors(out/"vectors.txt"); probe = ROOT/"sim/spk286_timing_pilot/p06_core_register_tb.sv"
    simulate(out,"original-max",original,probe,"p06_core_register_tb",out/"vectors.txt")
    simulate(out,"private-max",private,probe,"p06_core_register_tb",out/"vectors.txt")
    for kind in ["trace.csv","summary.csv"]:
        assert (out/("original-max/normal-iverilog-"+kind)).read_bytes() == (out/("private-max/normal-iverilog-"+kind)).read_bytes()
    return count,sha(top)


def negative(out, modified, rtl, bench):
    # Independent old-result/timing oracle must reject early raw publication.
    text = modified.read_text()
    text = replace_once(text,"((state_q == PUBLISHED && raw_data_response_valid) || p06_complete)",
                        "(raw_data_response_valid || p06_complete)")
    mutant = out/"negative-biu.sv"; mutant.write_text(text,newline="\n")
    run(["iverilog","-g2012","-s","p06_data_biu_tb","-o",out/"negative.vvp",mutant,*rtl[1:],bench],out/"negative-build.log")
    result = subprocess.run(["vvp",str(out/"negative.vvp"),f"+trace={out}/negative-trace.csv",
        f"+summary={out}/negative-summary.csv",f"+vectors={out}/vectors.txt"],cwd=ROOT,text=True,
        stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=30)
    (out/"negative-run.log").write_text(result.stdout)
    assert result.returncode != 0 and "independent logical publication oracle failed" in result.stdout,\
        "early publication mutant did not fail its timing oracle"
    return result.returncode


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--prepare",action="store_true",help="lint/formal/cost only; no acceptance claim")
    args = parser.parse_args(); out = args.output.resolve(); out.mkdir(parents=True,exist_ok=False)
    unit_names = ["spk286_biu","spk286_biu_width_io","spk286_biu_hold_lock",
                  "spk286_operand_service","spk286_operand_lifecycle","spk286_operand_byte"]
    inputs = sources()+[ROOT/p for p in ["scripts/build_p06_data_biu.py","scripts/run_p06_data_biu.py",
        "scripts/build_p06_register_cpu.py","scripts/run_p06_core_register.py","scripts/run_p06_timed_register.py","scripts/run_p06_pilot.py",
        "rtl/spk286_timing_pilot/p06_data_biu_connection.svh","rtl/spk286_timing_pilot/p06_clock.sv",
        "rtl/spk286_integration/spk286_integration.qip","scripts/test_at_landmark_dma.sh",
        "docs/evidence/p06-core-iu-20261004/receipt.json","sim/spk286_timing_pilot/p06_core_register_tb.sv",
        "vendor/spk286/sim/unit/spk286_signals.svh"]]
    inputs += [CPU/"sim/unit"/(n+"_tb.sv") for n in unit_names]
    bench = ROOT/"sim/spk286_timing_pilot/p06_data_biu_tb.sv"
    if not args.prepare: inputs.append(bench)
    before = {p.relative_to(ROOT).as_posix():sha(p) for p in inputs}
    modified = build(out)
    versions = {name:run(command,out/(name+"-version.log")).splitlines()[0] for name,command in [
        ("iverilog",["iverilog","-V"]),("verilator",["verilator","--version"]),("yosys",["yosys","-V"])]}
    for historical in [0,1]:
        run(["verilator","--lint-only","--Wall","--top-module","spk286_biu",
             f"-GP06_DATA_TIMING=1'b{historical}",modified],out/f"lint-biu-{historical}.log")
    costs = synthesis(out,modified)
    print("DATA_LINT_FORMAL_COST_PASS",flush=True)
    if args.prepare:
        (out/"prepare.json").write_text(json.dumps(costs,indent=2)+"\n"); return
    (out/"vectors.txt").write_text("standalone directed fixture\n")
    rtl = [modified,CPU/"rtl/spk286_operand.sv",ROOT/"rtl/spk286_timing_pilot/p06_clock.sv"]
    normal = simulate(out,"data",rtl,bench,"p06_data_biu_tb",out/"vectors.txt")
    lifecycle = execute(out/"data","lifecycle",out/"vectors.txt",["+mode=1"])
    guards = execute(out/"data","guards",out/"vectors.txt",["+mode=2"])
    assert (len(normal),len(lifecycle),len(guards)) == (432,33,42)
    assert all(all(int(r[k]) == 1 for k in ["accepts","reads","captures","completes","responses"])
               and int(r["external_waits"]) == int(r["waits"]) and int(r["scope_error"]) == 0 for r in normal)
    assert all(int(r["misses"]) == 0 for r in normal if int(r["latency"]) == -1)
    assert all(int(r["misses"]) > 0 for r in normal if int(r["latency"]) == 80)
    assert all(int(r["scope_error"]) == 1 and int(r["responses"]) == 0 for r in guards)
    assert {(int(r["guard_kind"]),int(r["lifecycle_stage"])) for r in guards} == {
        (guard,stage) for guard in range(7) for stage in range(6)}
    print("DATA_DIRECTED_PASS matrix=432 lifecycle=33 guards=42",flush=True)
    negative_rc = negative(out,modified,rtl,bench)
    checks = units(out,modified)
    max_count,top_sha = full_max(out,modified)
    run(["python3","-m","tools.microcode.compile_microcode","--check"],out/"microcode.log",cwd=CPU)
    assert before == {p.relative_to(ROOT).as_posix():sha(p) for p in inputs}
    assert "spk286_timing_pilot" not in (ROOT/"rtl/spk286_integration/spk286_integration.qip").read_text()
    receipt = {"status":"P06_PRIVATE_DATA_READ_PASS","data_cases":len(normal),"lifecycle_cases":len(lifecycle),
        "guard_cases":len(guards),"dual_traces_equal":True,"max_units":checks,"max_full_cpu_cases":max_count,
        "max_full_cpu_trace_equal":True,"max_biu_sequential_equivalence":True,"negative_returncode":negative_rc,
        "generic_biu_synthesis":costs,"generic_cost_scope":"Net isolated restricted BIU delta; CODE/ACK/HOLD/LOCK are statically pruned. Not the cost of the complete timed BIU or FPGA ALMs.",
        "off_boundary_matrix_captures":sum(int(r["off_boundary"]) for r in normal),"tool_versions":versions,
        "generated_biu_sha256":sha(modified),"generated_max_top_sha256":top_sha,
        "production_unchanged":True,"sources_sha256":before,
        "scope":"M6a BIU/operand isolated READ byte/even-word, CODE=0. Not full memory-instruction timing, shared logical ownership, odd words, writes, I/O, events, complete profiles or FPGA fit/STA.",
        "artifacts_sha256":{p.relative_to(out).as_posix():sha(p) for p in out.rglob("*") if p.is_file() and
            "obj" not in p.relative_to(out).parts and p.suffix != ".vvp" and p.name != "receipt.json"}}
    (out/"receipt.json").write_text(json.dumps(receipt,indent=2)+"\n")
    print(json.dumps({k:v for k,v in receipt.items() if k not in ["artifacts_sha256","sources_sha256"]},indent=2),flush=True)


if __name__ == "__main__": main()
