#!/usr/bin/env python3
"""Directed M6b shared CODE/DATA component acceptance; no production change."""
import argparse
import json
from pathlib import Path
import subprocess
from build_p06_shared_bus import build, replace_once
from run_p06_core_register import ROOT, CPU, sources, sha, run, vectors
from run_p06_timed_register import simulate, execute
from run_p06_pilot import generic_stats

UNIT_NAMES = ["spk286_biu","spk286_biu_width_io","spk286_biu_hold_lock",
              "spk286_fetch","spk286_prefetch_queue","spk286_operand_service",
              "spk286_operand_lifecycle","spk286_operand_byte"]


def validate_component_coverage(normal, lifecycle, cancel):
    """Reject omissions/duplicates independently of the bench PASS marker."""
    assert [int(r["case"]) for r in normal] == list(range(972))
    assert [int(r["case"]) for r in lifecycle] == list(range(8))
    assert [int(r["case"]) for r in cancel] == list(range(107))
    keys = ["direction","code_odd","data_lane","code_waits","data_waits","code_latency","data_latency"]
    expected = {(d,o,l,cw,dw,cl,dl) for d in range(2) for o in range(2) for l in range(3)
        for cw in range(3) for dw in range(3) for cl in [0,-1,80] for dl in [0,-1,80]}
    assert {tuple(int(r[k]) for k in keys) for r in normal} == expected
    for r in normal:
        assert int(r["kind"]) == 0
        assert all(int(r[k]) == 1 for k in ["code_accepts","data_accepts","code_captures","data_captures",
            "code_completes","data_completes","code_responses","data_responses","handoffs"])
        assert r["code_external"] == r["code_waits"] and r["data_external"] == r["data_waits"]
        assert (r["data_start_cpu"] == r["code_complete_cpu"] if r["direction"] == "0"
                else r["code_start_cpu"] == r["data_complete_cpu"])
    # Retained CODE, held DATA, paused real operand, poisoned metadata in both
    # directions, two full-queue streams and one interleaved four-packet stream.
    life_keys = {tuple(int(r[k]) for k in ["kind","direction","code_odd"]) for r in lifecycle}
    assert life_keys == {(1,0,1),(2,1,0),(3,1,1),(4,0,1),(4,1,1),(7,0,0),(7,0,1),(8,0,1)}
    for r in lifecycle:
        packets = 4 if int(r["kind"]) in [7,8] else 1
        assert all(int(r[k]) == packets for k in ["code_accepts","code_captures","code_completes","code_responses"])
        assert all(int(r[k]) == 1 for k in ["data_accepts","data_captures","data_completes","data_responses"])
    for kind,stages in [(5,range(6)),(10,range(1,6)),(11,range(6))]:
        selected = [r for r in cancel if int(r["kind"]) == kind]
        assert len(selected) == 2*len(stages)
        assert {(int(r["direction"]),int(r["lifecycle_stage"])) for r in selected} == {
            (d,s) for d in range(2) for s in stages}
        assert all(int(r["guard_kind"]) == -1 for r in selected)
    guards = [r for r in cancel if int(r["kind"]) == 6]
    assert len(guards) == 72
    assert {(int(r["direction"]),int(r["lifecycle_stage"]),int(r["guard_kind"])) for r in guards} == {
        (d,s,g) for d in range(2) for s in range(6) for g in range(6)}
    assert all(int(r["code_responses"]) == int(r["data_responses"]) == 0 for r in guards)
    opposite = [r for r in cancel if int(r["kind"]) == 10]
    assert all(int(r["code_responses"]) == int(r["data_responses"]) == 1 for r in opposite)
    recovery = [r for r in cancel if int(r["kind"]) == 9]
    assert len(recovery) == 1 and int(recovery[0]["code_responses"]) == int(recovery[0]["data_responses"]) == 1
    assert {int(r["kind"]) for r in cancel} == {5,6,9,10,11}


def synthesis(out, selected):
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
        assert measured[name]["max"]["register_bits"] == measured[name]["original"]["register_bits"]
        if name == "spk286_biu":
            inputs = ["p06_cpu_boundary","p06_board_ready","p06_code_issue","p06_code_complete","p06_code_canceled"]
            outputs = ["p06_scope_error","p06_code_admission","p06_scope_block"]
        else:
            inputs = ["p06_cpu_boundary","p06_board_ready","p06_admission_enable","p06_scope_block"]
            outputs = ["p06_bus_issue","p06_bus_complete","p06_bus_canceled"]
        # New private controls must have no MAX cone, even with arbitrary input
        # values. Do not rely on deleting undriven ports in the formal adapter.
        maximum = json.loads((out/f"generic-{name}-max.json").read_text())["modules"][name]
        control_bits = {bit for p in inputs for bit in maximum["ports"][p]["bits"] if isinstance(bit,int)}
        used_bits = {bit for cell in maximum["cells"].values() for bits in cell["connections"].values()
                     for bit in bits if isinstance(bit,int)}
        output_bits = {bit for p in maximum["ports"].values() if p["direction"] == "output"
                       for bit in p["bits"] if isinstance(bit,int)}
        assert not control_bits & (used_bits | output_bits), (name,"private control influences MAX")
        # Give the golden interface the same arbitrary private inputs, ignored
        # by construction, rather than deleting inputs from the gate module.
        golden = out/f"max-{name}-gold.sv"
        golden.write_text(replace_once(original.read_text(),f"module {name} (",
            f"module {name} (\n    input logic "+", ".join(inputs)+","),newline="\n")
        proof = out/f"max-{name}-equivalence.ys"
        proof.write_text(f"read_verilog -sv {golden}\nproc\nopt\nrename {name} gold\n"+
            f"read_verilog -sv {changed}\nproc\nopt\nrename {name} gate\n"+
            "delete -output "+" ".join("gate/"+p for p in outputs)+"\n"+
            "equiv_make gold gate equiv\nhierarchy -top equiv\nequiv_simple\nequiv_induct -seq 4\nequiv_status -assert\n")
        result = run(["yosys","-Q","-s",proof],out/f"max-{name}-equivalence.log")
        assert "Equivalence successfully proven!" in result
    return measured


def max_top(out):
    text = (CPU/"rtl/spk286.sv").read_text()
    text = replace_once(text,"    spk286_biu biu (",
        "    /* verilator lint_off UNUSEDSIGNAL */\n"+
        "    logic p06_scope_unused, p06_code_admission_unused, p06_scope_block_unused;\n"+
        "    logic p06_issue_unused, p06_complete_unused, p06_canceled_unused;\n"+
        "    /* verilator lint_on UNUSEDSIGNAL */\n"+
        "    spk286_biu biu (\n"+
        "        .p06_cpu_boundary(1'b0), .p06_board_ready(1'b1),\n"+
        "        .p06_code_issue(1'b0), .p06_code_complete(1'b0), .p06_code_canceled(1'b0),\n"+
        "        .p06_scope_error(p06_scope_unused), .p06_code_admission(p06_code_admission_unused),\n"+
        "        .p06_scope_block(p06_scope_block_unused),")
    text = replace_once(text,"    spk286_fetch fetch (",
        "    spk286_fetch fetch (\n"+
        "        .p06_cpu_boundary(1'b0), .p06_board_ready(1'b1), .p06_admission_enable(1'b1),\n"+
        "        .p06_scope_block(1'b0), .p06_bus_issue(p06_issue_unused),\n"+
        "        .p06_bus_complete(p06_complete_unused), .p06_bus_canceled(p06_canceled_unused),")
    top = out/"private-rtl/spk286.sv"; top.write_text(text,newline="\n")
    return top


def compatibility(out, selected):
    original = sources(); top = max_top(out)
    private = [top if p.name == "spk286.sv" else selected.get(p.name,p) for p in original]
    run(["verilator","--lint-only","--Wall","--top-module","spk286","-I"+str(CPU/"rtl"),*private],out/"lint-full-max.log")
    include = ["-I"+str(CPU/"rtl"),"-I"+str(CPU/"sim/unit")]; results = {}
    for name in UNIT_NAMES:
        module = name+"_tb"; directory = out/name; directory.mkdir()
        text = (CPU/"sim/unit"/(module+".sv")).read_text()
        if name.startswith("spk286_biu"):
            text = replace_once(text,"module "+module+";","module "+module+";\n"+
                "    wire p06_cpu_boundary=0, p06_board_ready=1;\n"+
                "    wire p06_code_issue=0, p06_code_complete=0, p06_code_canceled=0;\n"+
                "    wire p06_scope_error, p06_code_admission, p06_scope_block;")
        if name == "spk286_fetch":
            text = replace_once(text,"module "+module+";","module "+module+";\n"+
                "    wire p06_cpu_boundary=0, p06_board_ready=1, p06_admission_enable=1, p06_scope_block=0;\n"+
                "    wire p06_bus_issue, p06_bus_complete, p06_bus_canceled;")
        bench = out/(module+".sv"); bench.write_text(text,newline="\n")
        run(["iverilog","-g2012","-s",module,*include,"-o",directory/"test.vvp",*private,bench],directory/"iverilog-build.log")
        run(["vvp",directory/"test.vvp"],directory/"iverilog-run.log")
        run(["verilator","--binary","--timing","--assert","-j","4","--top-module",module,
             "--Mdir",directory/"obj","-o","unit-test",*include,*private,bench],directory/"verilator-build.log",timeout=600)
        run([directory/"obj/unit-test"],directory/"verilator-run.log")
        markers = [[line for line in (directory/(tool+"-run.log")).read_text().splitlines() if "PASS" in line]
                   for tool in ["iverilog","verilator"]]
        assert markers[0] == markers[1] and len(markers[0]) == 1,name
        results[name] = markers[0][0]
    count = vectors(out/"vectors.txt"); probe = ROOT/"sim/spk286_timing_pilot/p06_core_register_tb.sv"
    simulate(out,"original-max",original,probe,"p06_core_register_tb",out/"vectors.txt")
    simulate(out,"private-max",private,probe,"p06_core_register_tb",out/"vectors.txt")
    for suffix in ["trace.csv","summary.csv"]:
        assert (out/("original-max/normal-iverilog-"+suffix)).read_bytes() == (out/("private-max/normal-iverilog-"+suffix)).read_bytes()
    return results,count,sha(top)


def negative(out,selected,rtl,bench,label,old,new,marker):
    mutant = out/("negative-"+label+".sv")
    component = "spk286_biu.sv" if label == "owner" else "spk286_fetch.sv"
    mutant.write_text(replace_once(selected[component].read_text(),old,new),newline="\n")
    changed = [mutant if p == selected[component] else p for p in rtl]
    run(["iverilog","-g2012","-s","p06_shared_bus_tb","-o",out/("negative-"+label+".vvp"),*changed,bench],out/("negative-"+label+"-build.log"))
    result = subprocess.run(["vvp",str(out/("negative-"+label+".vvp")),f"+trace={out}/negative-{label}-trace.csv",
        f"+summary={out}/negative-{label}-summary.csv",f"+vectors={out}/vectors.txt","+mode=0" if label == "owner" else "+mode=2"],
        cwd=ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=30)
    (out/("negative-"+label+"-run.log")).write_text(result.stdout)
    assert result.returncode != 0 and marker in result.stdout,(label,result.stdout)
    return result.returncode


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--prepare",action="store_true",help="lint/formal/generic cost only")
    args = parser.parse_args(); out = args.output.resolve(); out.mkdir(parents=True,exist_ok=False)
    names = ["scripts/build_p06_shared_bus.py","scripts/run_p06_shared_bus.py","scripts/build_p06_data_biu.py",
        "scripts/build_p06_fetch_cpu.py","scripts/build_p06_register_cpu.py","scripts/run_p06_core_register.py",
        "scripts/run_p06_timed_register.py","scripts/run_p06_pilot.py","rtl/spk286_timing_pilot/p06_clock.sv",
        "rtl/spk286_timing_pilot/p06_shared_biu_connection.svh","rtl/spk286_timing_pilot/p06_data_biu_connection.svh",
        "rtl/spk286_timing_pilot/p06_fetch_connection.svh","docs/evidence/p06-core-data-20261004/receipt.json",
        "docs/evidence/p06-core-fetch-20261004/receipt.json","docs/evidence/p06-core-iu-20261004/receipt.json",
        "rtl/spk286_integration/spk286_integration.qip","config.tcl","scripts/test_at_landmark_dma.sh",
        "sim/spk286_timing_pilot/p06_core_register_tb.sv","vendor/spk286/sim/unit/spk286_signals.svh"]
    inputs = sources()+[ROOT/p for p in names]+[CPU/"sim/unit"/(n+"_tb.sv") for n in UNIT_NAMES]
    bench = ROOT/"sim/spk286_timing_pilot/p06_shared_bus_tb.sv"
    if not args.prepare: inputs.append(bench)
    before = {p.relative_to(ROOT).as_posix():sha(p) for p in inputs}
    selected = build(out)
    versions = {name:run(command,out/(name+"-version.log")).splitlines()[0] for name,command in [
        ("iverilog",["iverilog","-V"]),("verilator",["verilator","--version"]),("yosys",["yosys","-V"])]}
    for name,path in selected.items():
        module = path.stem
        for timed in [0,1]:
            parameters = ([f"-GP06_DATA_TIMING=1'b{timed}",f"-GP06_SHARED_TIMING=1'b{timed}"]
                          if module == "spk286_biu" else [f"-GP06_FETCH_TIMING=1'b{timed}"])
            run(["verilator","--lint-only","--Wall","--top-module",module,*parameters,path],out/f"lint-{module}-{timed}.log")
    costs = synthesis(out,selected)
    print("SHARED_LINT_FORMAL_COST_PASS",flush=True)
    if args.prepare:
        (out/"prepare.json").write_text(json.dumps(costs,indent=2)+"\n"); return
    (out/"vectors.txt").write_text("component fixture\n")
    rtl = [*selected.values(),CPU/"rtl/spk286_operand.sv",CPU/"rtl/spk286_prefetch_queue.sv",ROOT/"rtl/spk286_timing_pilot/p06_clock.sv"]
    normal = simulate(out,"shared",rtl,bench,"p06_shared_bus_tb",out/"vectors.txt")
    lifecycle = execute(out/"shared","lifecycle",out/"vectors.txt",["+mode=1"])
    cancel = execute(out/"shared","cancel-scope",out/"vectors.txt",["+mode=2"])
    validate_component_coverage(normal,lifecycle,cancel)
    negative_codes = {
        "owner":negative(out,selected,rtl,bench,"owner","if (p06_shared_release) owner_valid_q <= 1'b0;",
            "if (p06_shared_release || (bus_valid && ready)) owner_valid_q <= 1'b0;","shared logical owner oracle failed"),
        "scope":negative(out,selected,rtl,bench,"scope","assign response_valid = !reset && !restart && !p06_scope_block &&",
            "assign response_valid = !reset && !restart &&","CODE publication oracle failed")}
    checks,count,top_sha = compatibility(out,selected)
    run(["python3","-m","tools.microcode.compile_microcode","--check"],out/"microcode.log",cwd=CPU)
    assert before == {p.relative_to(ROOT).as_posix():sha(p) for p in inputs}
    assert "spk286_timing_pilot" not in (ROOT/"rtl/spk286_integration/spk286_integration.qip").read_text()
    receipt = {"status":"P06_PRIVATE_SHARED_BUS_PASS","transition_cases":len(normal),"lifecycle_cases":len(lifecycle),
        "cancel_scope_cases":len(cancel),"dual_traces_equal":True,"max_units":checks,"max_full_cpu_cases":count,
        "max_full_cpu_trace_equal":True,"max_biu_fetch_sequential_equivalence":True,
        "max_private_control_cones_absent":True,"coverage_checked":True,"negative_returncodes":negative_codes,
        "generic_component_synthesis":costs,"generic_cost_scope":"Isolated BIU and fetch generic mappings, not whole CPU/FPGA overhead; unsupported ACK/HOLD/LOCK/I/O/write services remain pruned.",
        "tool_versions":versions,"generated_sha256":{name:sha(path) for name,path in selected.items()},
        "generated_max_top_sha256":top_sha,"production_unchanged":True,"sources_sha256":before,
        "scope":"M6b real fetch/queue/operand/BIU shared CODE and byte/even-word READ ownership. Not full memory instruction timing, odd words, writes, I/O, events, complete profiles, FPGA fit or STA.",
        "artifacts_sha256":{p.relative_to(out).as_posix():sha(p) for p in out.rglob("*") if p.is_file() and
            "obj" not in p.relative_to(out).parts and p.suffix != ".vvp" and p.name != "receipt.json"}}
    (out/"receipt.json").write_text(json.dumps(receipt,indent=2)+"\n")
    print(json.dumps({k:v for k,v in receipt.items() if k not in ["artifacts_sha256","sources_sha256"]},indent=2),flush=True)


if __name__ == "__main__": main()
