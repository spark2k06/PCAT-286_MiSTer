#!/usr/bin/env python3
"""Directed private register handoff acceptance; no production/86Box/RBF edits."""
import argparse
import json
import subprocess
import re
from pathlib import Path
from build_p06_iu_cpu import build
from run_p06_core_register import ROOT, CPU, sources, sha, run, vectors
from run_p06_timed_register import simulate, execute, unit
from run_p06_timed_fetch import full_cpu_bench, fetch_unit
from run_p06_pilot import generic_stats


SPECS = [([0x01,0xD8],0,0,3,None), ([0x03,0xD8],0,3,0,None),
         ([0x31,0xFA],1,2,7,None), ([0x33,0xD7],1,2,7,None),
         ([0x39,0xD8],2,0,3,None), ([0x3B,0xC3],2,0,3,None),
         ([0x83,0xC3,1],3,3,None,1), ([0x83,0xC3,0xFF],3,3,None,0xFFFF),
         ([0x81,0xF7,0xAA,0x55],4,7,None,0x55AA), ([0x05,1,0],3,0,None,1),
         ([0x35,0xAA,0x55],4,0,None,0x55AA), ([0x83,0xF7,0xFF],4,7,None,0xFFFF),
         ([0x81,0xC3,1,0],3,3,None,1)]


def stream_vectors(path):
    pack = lambda regs: sum(r << (16*i) for i,r in enumerate(regs))
    records = []
    pairs = [(a,b) for a in range(len(SPECS)) for b in range(len(SPECS))]
    sequences = [[a,b] for a,b in pairs] + [[0]*8, [9,0,1,6,5,10,0,12], [2,3,8,11,4,0,1,5]]
    for sequence in sequences:
        for seed in [0,0x7FFF,0xFFFF,0x1234]:
            i = len(records); regs = [(seed+j*0x1111)&0xFFFF for j in range(8)]; regs[4] = 0x800
            flags = 0x403 if seed&1 else 2
            rows = [f"{i} {len(sequence)} {0x100+(i%2):04x} {i%2} {pack(regs):032x} {flags:04x}"]
            for index in sequence:
                code,form,dst,src,imm = SPECS[index]
                a,b = regs[dst],regs[src] if src is not None else imm
                result = ((a+b) if form in [0,3] else (a-b) if form==2 else a^b)&0xFFFF
                logical = form in [1,4]
                f = (0x80 if result&0x8000 else 0)|(0x40 if result==0 else 0)|(4 if (result&255).bit_count()%2==0 else 0)
                if not logical:
                    f |= int(a<b) if form==2 else int(a+b>0xFFFF)
                    f |= 0x10 if (a^b^result)&0x10 else 0
                    overflow = ((a^b)&(a^result)) if form==2 else ((~(a^b))&(a^result))
                    f |= 0x800 if overflow&0x8000 else 0
                flags = (flags&~(0x8C5 if logical else 0x8D5))|f
                if form != 2: regs[dst] = result
                rows.append(f"{form} {len(code)} {int.from_bytes(bytes(code),'little'):08x} {pack(regs):032x} {flags:04x}")
            records.append("\n".join(rows))
    path.write_text("\n".join(records)+"\n")
    return len(records)


def select_streams(source, target, flags=0, late=False):
    lines = source.read_text().splitlines(); chosen = []; pos = 0
    # Repeated ADD plus reverse-direction, CMP, XOR and RI dependencies.
    identifiers = {0, 4, 16, 24, 52, 260, 364, 468, 676, 680, 684}
    while pos < len(lines):
        header = lines[pos].split(); count = int(header[1]); block = lines[pos:pos+count+1]; pos += count+1
        if int(header[0]) not in identifiers: continue
        header[4] = f"{int(header[4],16):032x}"
        header[5] = f"{int(header[5],16)|flags:04x}"
        if late: header[3] = "2"
        block[0] = " ".join(header)
        for i in range(1,len(block)):
            fields = block[i].split(); fields[4] = f"{int(fields[4],16)|flags:04x}"; block[i] = " ".join(fields)
        chosen.extend(block)
    target.write_text("\n".join(chosen)+"\n")
    return len(identifiers)


def synthesis(out, selected):
    measured = {}; proofs = {}
    package = (CPU/"microcode/generated/spk286_microcode_pkg.sv").read_text()
    width = int(re.search(r"MC_ADDR_WIDTH = (\d+)",package)[1])
    depth = int(re.search(r"MC_DEPTH = (\d+)",package)[1])
    for name in ["spk286_microsequencer", "spk286_operand_decode", "spk286_instruction_context"]:
        original = CPU/"rtl"/(name+".sv"); modified = selected[name+".sv"]
        measured[name] = {}
        parameters = f"chparam -set ADDRESS_WIDTH {width} -set ROM_DEPTH {depth} {name}\n" if name == "spk286_microsequencer" else ""
        for label,source,param in [("original",original,None),("max",modified,0),("timed",modified,1)]:
            net = out/f"generic-{name}-{label}.json"; script = out/f"generic-{name}-{label}.ys"
            script.write_text(f"read_verilog -sv {source}\n"+
                (f"chparam -set P06_IU_OVERLAP {param} {name}\n" if param is not None else "")+parameters+
                f"read_verilog -sv {CPU}/rtl/spk286_modrm.sv {CPU}/rtl/spk286_effective_address.sv\n"+
                f"synth -top {name} -flatten\nwrite_json {net}\n")
            run(["yosys","-Q","-s",script],out/f"yosys-{name}-{label}.log")
            measured[name][label] = generic_stats(net)
        # ABC can choose different gates for equivalent rewritten expressions;
        # sequential proof, not gate-count identity, is the MAX acceptance gate.
        assert measured[name]["original"]["register_bits"] == measured[name]["max"]["register_bits"],name
        script = out/f"equivalence-{name}.ys"
        script.write_text(f"read_verilog -sv {CPU}/rtl/spk286_modrm.sv {CPU}/rtl/spk286_effective_address.sv\n"+
            f"read_verilog -sv {original}\n"+parameters+f"proc\nopt\nrename {name} gold\n"+
            f"read_verilog -sv {modified}\nchparam -set P06_IU_OVERLAP 0 {name}\n"+parameters+f"proc\nopt\nrename {name} gate\n"+
            ("delete -input gate/p06_relaunch_window\n" if name != "spk286_instruction_context" else "")+
            "equiv_make gold gate equiv\nhierarchy -top equiv\nequiv_simple\nequiv_induct -seq 4\nequiv_status -assert\n")
        result = run(["yosys","-Q","-s",script],out/f"equivalence-{name}.log")
        assert "Equivalence successfully proven!" in result; proofs[name] = True
    return measured,proofs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--smoke",action="store_true")
    args = parser.parse_args(); out = args.output.resolve(); out.mkdir(parents=True,exist_ok=False)
    original = sources()
    inputs = original + [ROOT/p for p in ["scripts/build_p06_register_cpu.py","scripts/build_p06_fetch_cpu.py",
        "scripts/build_p06_iu_cpu.py","scripts/run_p06_iu.py","scripts/run_p06_timed_fetch.py",
        "scripts/run_p06_timed_register.py","scripts/run_p06_core_register.py","scripts/run_p06_pilot.py",
        "rtl/spk286_timing_pilot/p06_iu_connection.svh","rtl/spk286_timing_pilot/p06_register_connection.svh",
        "rtl/spk286_timing_pilot/p06_fetch_connection.svh","rtl/spk286_timing_pilot/p06_fetch_cpu_connection.svh",
        "rtl/spk286_timing_pilot/p06_clock.sv","rtl/spk286_timing_pilot/p06_instruction_duration.sv",
        "sim/spk286_timing_pilot/p06_core_iu_tb.sv","sim/spk286_timing_pilot/p06_core_register_tb.sv",
        "sim/spk286_timing_pilot/p06_core_timed_register_tb.sv","scripts/test_at_landmark_dma.sh",
        "rtl/spk286_integration/spk286_integration.qip","docs/evidence/p06-core-fetch-20261004/receipt.json"]]
    unit_names = ["spk286_register_execution","spk286_immediate_execution","spk286_timing_policy_equivalence"]
    inputs += [CPU/"sim/unit"/(n+"_tb.sv") for n in unit_names+["spk286_fetch"]]
    before = {p.relative_to(ROOT).as_posix():sha(p) for p in inputs}
    selected = build(out)
    private = [selected.get(p.name,p) for p in original]+[ROOT/"rtl/spk286_timing_pilot"/p for p in
        ["p06_clock.sv","p06_instruction_duration.sv"]]
    for reg,fetch,iu in [(0,0,0),(1,1,0),(1,1,1)]:
        run(["verilator","--lint-only","--Wall","--top-module","spk286",
             f"-GP06_REGISTER_PILOT=1'b{reg}",f"-GP06_FETCH_PILOT=1'b{fetch}",f"-GP06_IU_PILOT=1'b{iu}",
             "-I"+str(CPU/"rtl"),*private],out/f"lint-{reg}{fetch}{iu}.log")
    stream_count = stream_vectors(out/"streams.txt")
    rows = simulate(out,"streams",private,ROOT/"sim/spk286_timing_pilot/p06_core_iu_tb.sv",
                    "p06_core_iu_tb",out/"streams.txt")
    print(f"IU_STREAM_PASS cases={stream_count} instructions={len(rows)}",flush=True)
    if args.smoke: return
    select_streams(out/"streams.txt",out/"selected-streams.txt")
    select_streams(out/"streams.txt",out/"late-streams.txt",late=True)
    select_streams(out/"streams.txt",out/"if-streams.txt",flags=0x200)
    select_streams(out/"streams.txt",out/"tf-streams.txt",flags=0x100)
    cold = execute(out/"streams","cold",out/"streams.txt",["+cold"])
    late = execute(out/"streams","late",out/"late-streams.txt",["+cold"])
    controls = {}
    for mode in [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15]:
        path = out/("if-streams.txt" if mode == 6 else "tf-streams.txt" if mode == 7 else "selected-streams.txt")
        # Boundary events after the first handoff intentionally stop at the
        # second instruction, even for longer streams.
        controls[str(mode)] = len(execute(out/"streams",f"mode{mode}",path,[f"+mode={mode}"]))
    baseline = out/"p06_core_iu_baseline_tb.sv"
    baseline.write_text((ROOT/"sim/spk286_timing_pilot/p06_core_iu_tb.sv").read_text().replace("p06_core_iu_tb","p06_core_iu_baseline_tb").replace("OVERLAP = 1'b1","OVERLAP = 1'b0"))
    base = simulate(out,"baseline",private,baseline,"p06_core_iu_baseline_tb",out/"streams.txt")
    assert len(base) == len(rows)
    assert all(int(r["relaunch"]) == 0 for r in base)
    comparisons = []
    for new,old in zip(rows,base):
        assert (new["id"],new["instruction"],new["gpr"],new["flags"]) == (old["id"],old["instruction"],old["gpr"],old["flags"])
        if int(new["instruction"]) == 1:
            saving = int(old["start_delta"])-int(new["start_delta"])
            assert saving == 1, (new,old)
            comparisons.append(saving)
    print(f"IU_BASELINE_PASS pairs={len(comparisons)} saving=1_cpu_clock",flush=True)
    # Mutate the independent architectural oracle: no acceptance by agreement
    # between simulators or by checking only the timing controller.
    bad = (out/"selected-streams.txt").read_text().splitlines(); fields = bad[1].split()
    fields[3] = f"{int(fields[3],16)^1:032x}"; bad[1] = " ".join(fields)
    (out/"negative-streams.txt").write_text("\n".join(bad)+"\n")
    negative = subprocess.run(["vvp",str(out/"streams/test.vvp"),f"+vectors={out}/negative-streams.txt",
        f"+trace={out}/negative-trace.csv",f"+summary={out}/negative-summary.csv"],cwd=ROOT,text=True,
        stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=30)
    (out/"negative-run.log").write_text(negative.stdout)
    assert negative.returncode != 0 and "stream architectural mismatch" in negative.stdout
    # Focused compatibility tests, not the total project regression.
    count = vectors(out/"vectors.txt"); probe = ROOT/"sim/spk286_timing_pilot/p06_core_register_tb.sv"
    simulate(out,"original-max",original,probe,"p06_core_register_tb",out/"vectors.txt")
    simulate(out,"private-max",private,probe,"p06_core_register_tb",out/"vectors.txt")
    for artifact in ["trace.csv","summary.csv"]:
        assert (out/("original-max/normal-iverilog-"+artifact)).read_bytes() == (out/("private-max/normal-iverilog-"+artifact)).read_bytes()
    bench = full_cpu_bench(out)
    bench.write_text(bench.read_text().replace(".P06_FETCH_PILOT(1'b1)",".P06_FETCH_PILOT(1'b1), .P06_IU_PILOT(1'b1)"))
    singles = simulate(out,"single",private,bench,"p06_core_timed_fetch_tb",out/"vectors.txt")
    warm_singles = execute(out/"single","warm",out/"vectors.txt",["+warm_test"])
    assert len(singles) == len(warm_singles) == count
    assert all(int(r["elapsed"]) == (2 if int(r["form"])<3 else 3) for r in warm_singles)
    checks = {name:unit(out,name,private) for name in unit_names}
    checks["spk286_fetch"] = fetch_unit(out,selected)
    run(["python3","-m","tools.microcode.compile_microcode","--check"],out/"microcode.log",cwd=CPU)
    costs,proofs = synthesis(out,selected)
    assert before == {p.relative_to(ROOT).as_posix():sha(p) for p in inputs}
    assert "spk286_timing_pilot" not in (ROOT/"rtl/spk286_integration/spk286_integration.qip").read_text()
    receipt = {"status":"P06_PRIVATE_IU_HANDOFF_PASS","stream_cases":stream_count,"stream_instructions":len(rows),
        "warm_overlaps":sum(int(r["relaunch"]) for r in rows),"cold_instructions":len(cold),"late_instructions":len(late),
        "boundary_control_cases_per_mode":11,"boundary_control_instruction_or_cancel_records":controls,
        "paired_first_handoffs":len(comparisons),"first_handoff_saving_cpu_clocks":1,
        "single_instruction_cases":count,"max_units":checks,"max_trace_equal":True,"dual_traces_equal":True,
        "max_component_proofs":proofs,"generic_component_synthesis":costs,"negative_returncode":negative.returncode,
        "sequencer_synthesis_parameters":{"ADDRESS_WIDTH":10,"ROM_DEPTH":743},
        "production_unchanged":True,"sources_sha256":before,
        "generated_cpu_sha256":{p.name:sha(p) for p in selected.values()},
        "scope":"Private register handoff. Not the three-entry decoded IU queue, data/event timing, full FPGA cost or complete speed integration.",
        "artifacts_sha256":{p.relative_to(out).as_posix():sha(p) for p in out.rglob("*") if p.is_file() and
            "obj" not in p.relative_to(out).parts and p.suffix not in [".vvp",".xml"] and p.name != "receipt.json"}}
    (out/"receipt.json").write_text(json.dumps(receipt,indent=2)+"\n")
    print(json.dumps({k:v for k,v in receipt.items() if k not in ["sources_sha256","artifacts_sha256"]},indent=2),flush=True)


if __name__ == "__main__": main()
