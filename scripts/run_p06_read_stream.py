#!/usr/bin/env python3
"""Qualify real consecutive aligned A1 reads without changing M6c RTL."""
import argparse
import csv
import json
import subprocess
from pathlib import Path
from build_p06_memory_cpu import build, replace_once
from run_p06_memory_cpu import select, lint
from run_p06_core_register import ROOT, CPU, sources, sha, run
from run_p06_timed_register import simulate, execute


def stream_vectors(path):
    """Caller-only sparse memory and per-read schedules; no DUT expectations."""
    records = []
    def add(count,alignment,cw,cl,pattern,seed):
        index = len(records)
        cs,ds = [(0,0),(0x1234,0xffff),(0xffff,0x1234),(1,0)][seed%4]
        regs = [(seed*0x2345+r*0x1357)&0xffff for r in range(8)]; regs[4] = 0x8000
        flags = [2,0x403,0x8d7][seed%3]
        pool = [0,2,0xfe,0xfffe,0x1200,0x1202,0x2200,0x2202]
        offsets = [pool[(r if pattern<2 else r%2 if pattern==2 else 0)] for r in range(count)]
        values = [((offset*0x57)^ (seed*0xa55a) ^0x1234)&0xffff for offset in offsets]
        if seed == 0 and pattern == 0: values[0] = regs[0]
        waits = [pattern if pattern<3 else r%3 for r in range(count)]
        delays = [pattern if pattern<3 else r%4 for r in range(count)]
        pack = lambda items,width: sum(item<<(width*r) for r,item in enumerate(items))
        code_first = (cs<<4)+0x100+alignment
        for offset in offsets:
            address = (ds<<4)+offset
            assert offset%2 == 0 and (address+1<code_first or address>code_first+3*count+5)
        records.append(f"{index} {count} {0x100+alignment:04x} {cs:04x} {ds:04x} "
            f"{pack(regs,16):032x} {flags:04x} {cw} {cl} {pack(offsets,16):032x} "
            f"{pack(values,16):032x} {pack(waits,2):04x} {pack(delays,2):04x}")
    for count in [2,4,8]:
        for alignment in [0,1]:
            for cw in range(3):
                for cl in [0,-1,80]:
                    for pattern in range(4): add(count,alignment,cw,cl,pattern,(count+alignment+cw+pattern)%4)
    # Extra architectural seeds and segment carry; include alternating and
    # repeated addresses while retaining one value per physical location.
    for seed in range(8):
        for count in [2,4,8]: add(count,seed%2,0,0,seed%4,seed)
    assert len(records) == 240
    path.write_text("\n".join(records)+"\n")
    return len(records)


def control_vectors(out):
    lines = (out/"streams.txt").read_text().splitlines()
    # Each length, alignment and backend class. Selected cases expose
    # association under early/exact/late READY and all external wait counts.
    chosen = lines[::13]
    path = out/"selected-streams.txt"; path.write_text("\n".join(chosen)+"\n")
    return path


def validate_rows(records,vector_path,timed,warm,mode):
    caller = {int(f[0]):f for f in (line.split() for line in vector_path.read_text().splitlines())}
    expected = {(identifier,n) for identifier,f in caller.items() for n in range(int(f[1]))}
    assert {(int(r["id"]),int(r["read_index"])) for r in records} == expected
    assert len(records) == len(expected)
    for r in records:
        f = caller[int(r["id"])]; n = int(r["read_index"])
        assert int(r["count"]) == int(f[1])
        assert (int(r["timed"]),int(r["warm"]),int(r["mode"])) == (timed,warm,mode)
        recovered = mode in range(3,9)
        assert int(r["recovered"]) == int(recovered)
        value = (int(f[10],16)>>(16*n))&0xffff
        if recovered: value ^= 0xa55a
        expected_gpr = (int(f[5],16)&~0xffff)|value
        assert int(r["gpr"],16) == expected_gpr,(r,f)
        assert int(r["flags"],16) == int(f[6],16)
        ip = int(f[2],16)^(0x400 if recovered else 0)
        assert int(r["ip"],16) == (ip+3*(n+1))&0xffff
        assert all(int(r[k]) == 1 for k in ["data_accepts","data_captures","data_responses"])
        if timed:
            assert int(r["data_external"]) == ((int(f[11],16)>>(2*n))&3)
            assert int(r["elapsed"]) == int(r["retire_cpu"])-int(r["start_cpu"])
            assert int(r["elapsed"])>=5+int(r["data_external"])
        if n>0 and timed:
            previous = next(p for p in records if p["id"] == r["id"] and int(p["read_index"]) == n-1)
            assert int(r["start_cpu"])>int(previous["retire_cpu"])
        if recovered:
            assert int(r["action_retired"]) == 1
            assert int(r["recovery_resets"]) == int(mode in range(5,9))
    return len(expected)


def negative(out,selected,bench,label,marker,path,old,new,vector):
    mutant = out/("negative-"+label+"-"+path.name)
    mutant.write_text(replace_once(path.read_text(),old,new),newline="\n")
    executable = out/("negative-"+label+".vvp")
    run(["iverilog","-g2012","-s","p06_core_read_stream_tb","-I"+str(CPU/"rtl"),
         "-I"+str(CPU/"sim/unit"),"-o",executable,
         *[mutant if p==path else p for p in select(selected)],bench],out/("negative-"+label+"-build.log"))
    result = subprocess.run(["vvp",str(executable),f"+vectors={vector}",f"+trace={out}/negative-{label}-trace.csv",
        f"+summary={out}/negative-{label}-summary.csv"],cwd=ROOT,text=True,stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,timeout=30)
    (out/("negative-"+label+"-run.log")).write_text(result.stdout)
    assert result.returncode != 0 and marker in result.stdout,(label,result.stdout)
    return {"marker":marker,"returncode":result.returncode}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--prepare",action="store_true")
    args = parser.parse_args(); out = args.output.resolve(); out.mkdir(parents=True,exist_ok=False)
    bench = ROOT/"sim/spk286_timing_pilot/p06_core_read_stream_tb.sv"
    names = ["scripts/run_p06_read_stream.py","scripts/build_p06_memory_cpu.py","scripts/run_p06_memory_cpu.py",
        "scripts/build_p06_shared_bus.py","scripts/build_p06_data_biu.py","scripts/build_p06_iu_cpu.py",
        "scripts/build_p06_fetch_cpu.py","scripts/build_p06_register_cpu.py","scripts/run_p06_iu.py",
        "scripts/run_p06_core_register.py","scripts/run_p06_timed_register.py","scripts/run_p06_pilot.py",
        "scripts/run_p06_timed_fetch.py","rtl/spk286_timing_pilot/p06_clock.sv",
        "rtl/spk286_timing_pilot/p06_instruction_duration.sv","config.tcl","scripts/test_at_landmark_dma.sh",
        "rtl/spk286_integration/spk286_integration.qip","docs/evidence/p06-core-memory-20261004/receipt.json",
        "vendor/spk286/sim/unit/spk286_signals.svh"]
    names += [p.relative_to(ROOT).as_posix() for p in (ROOT/"rtl/spk286_timing_pilot").glob("*connection.svh")
        if "odd" not in p.name]
    inputs = sources()+[ROOT/name for name in names]+([] if args.prepare else [bench])
    before = {p.relative_to(ROOT).as_posix():sha(p) for p in inputs}
    old = json.loads((ROOT/"docs/evidence/p06-core-memory-20261004/receipt.json").read_text())
    assert sha(ROOT/"scripts/build_p06_memory_cpu.py") == old["sources_sha256"]["scripts/build_p06_memory_cpu.py"]
    selected = build(out)
    assert {name:sha(path) for name,path in selected.items()} == old["generated_cpu_sha256"]
    lint(out,selected)
    count = stream_vectors(out/"streams.txt")
    if args.prepare:
        print(f"READ_STREAM_PREPARE_PASS cases={count} generated_RTL_unchanged",flush=True); return
    versions = {name:run(command,out/(name+"-version.log")).splitlines()[0] for name,command in [
        ("iverilog",["iverilog","-V"]),("verilator",["verilator","--version"])]}
    path = out/"streams.txt"
    normal = simulate(out,"streams",select(selected),bench,"p06_core_read_stream_tb",path)
    cold = execute(out/"streams","cold",path,["+cold"])
    for warm,rows in [(1,normal),(0,cold)]: assert validate_rows(rows,path,1,warm,0) == 1120
    print("READ_STREAM_MATRIX_PASS streams=240 instructions=1120 warm_and_cold",flush=True)
    controlled = control_vectors(out); controls = {}
    for mode in range(1,10):
        for warm in [1,0]:
            label=f"mode{mode}-"+("warm" if warm else "cold")
            rows = execute(out/"streams",label,controlled,[f"+mode={mode}",
                "+action_read="+("0" if mode==9 else "1")]+([] if warm else ["+cold"]))
            controls[label] = validate_rows(rows,controlled,1,warm,mode)
        print(f"READ_STREAM_CONTROL_PASS mode={mode}",flush=True)
    chosen=[]
    lines=path.read_text().splitlines()
    for pattern in range(3):
        chosen.append(next(line for line in lines if line.split()[1:3]==["2","0100"] and
            line.split()[7:9]==["0","0"] and int(line.split()[11],16)==sum(pattern<<(2*n) for n in range(2))))
    deadline = out/"deadline-streams.txt"; deadline.write_text("\n".join(chosen)+"\n")
    rows = execute(out/"streams","mode12-warm",deadline,["+mode=12","+action_read=0"])
    controls["mode12-warm"] = validate_rows(rows,deadline,1,1,12)
    # No private MAX input is assumed for the original CPU. The fixture and
    # memory response schedules are identical for both source selections.
    maximum=out/"read-stream-max-tb.sv"
    maximum.write_text(replace_once(bench.read_text(),"parameter bit TIMED=1'b1","parameter bit TIMED=1'b0"),newline="\n")
    original=out/"read-stream-original-tb.sv"
    original.write_text("`define P06_ORIGINAL\n"+maximum.read_text(),newline="\n")
    gold=simulate(out,"original-max",sources(),original,"p06_core_read_stream_tb",path)
    gate=simulate(out,"private-max",select(selected),maximum,"p06_core_read_stream_tb",path)
    for rows in [gold,gate]: assert validate_rows(rows,path,0,1,0)==1120
    for suffix in ["summary.csv","trace.csv"]:
        assert (out/("original-max/normal-iverilog-"+suffix)).read_bytes()==(
            out/("private-max/normal-iverilog-"+suffix)).read_bytes()
    negatives={
        "permit":negative(out,selected,bench,"permit","read stream first eligible commit oracle failed",
            selected["spk286.sv"],"(!p06_result_pending || permit)","1'b1",path),
        "waits":negative(out,selected,bench,"waits","read stream per-instruction READ wait budget oracle failed",
            selected["spk286.sv"],".read_wait_event(p06_timed_read && p06_read_wait_event)",".read_wait_event(1'b0)",path)}
    # The data association oracle must reject a semantically wrong payload,
    # even if a simulator agrees and all temporal milestones remain legal.
    negatives["payload"]=negative(out,selected,bench,"payload","read stream retained DATA association oracle failed",
        selected["spk286_biu.sv"],": raw_data_read_data;",": (raw_data_read_data ^ 16'h0001);",path)
    run(["python3","-m","tools.microcode.compile_microcode","--check"],out/"microcode.log",cwd=CPU)
    assert before == {p.relative_to(ROOT).as_posix():sha(p) for p in inputs}
    assert "spk286_timing_pilot" not in (ROOT/"rtl/spk286_integration/spk286_integration.qip").read_text()
    receipt={"status":"P06_PRIVATE_READ_STREAM_PASS","streams":count,"instructions_per_matrix":1120,
        "controls":controls,"dual_traces_equal":True,"max_traces_equal":True,
        "generated_rtl_unchanged":True,"new_rtl_cost":0,"negative_checks":negatives,
        "tool_versions":versions,"sources_sha256":before,
        "generated_cpu_sha256":{name:sha(p) for name,p in selected.items()},
        "production_unchanged":True,"scope":"M6d existing serialized aligned A1 reuse, real full CPU, "
            "without removal of the DATA gap or any timing/production RTL change. "
            "Not odd-word timing, exact Intel IU issue phasing, complete profiles or FPGA fit/STA.",
        "artifacts_sha256":{p.relative_to(out).as_posix():sha(p) for p in out.rglob("*") if p.is_file() and
            "obj" not in p.relative_to(out).parts and p.suffix!=".vvp" and p.name!="receipt.json"}}
    (out/"receipt.json").write_text(json.dumps(receipt,indent=2)+"\n")
    print(json.dumps({k:v for k,v in receipt.items() if k not in ["sources_sha256","artifacts_sha256"]},indent=2),flush=True)


if __name__ == "__main__": main()
