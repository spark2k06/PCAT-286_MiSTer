#!/usr/bin/env python3
"""Directed private M6g XOR [disp16],imm16 read/modify/write qualification."""
import argparse
import gzip
import itertools
import json
import subprocess
from pathlib import Path
from build_p06_rmw_cpu import build, M6F_RECEIPT_SHA256
from build_p06_register_cpu import replace_once
from check_p06_rmw_components import prepare, select
from run_p06_core_register import ROOT, CPU, sources, run, sha
from run_p06_timed_register import simulate, execute
from run_p06_odd_read_cpu import odd_vectors, max_units
from run_p06_write_cpu import write_vectors
from run_p06_iu import stream_vectors

TOP = "p06_core_rmw_tb"
MODES = list(range(1, 29))
ABANDONED = set(range(6, 29))
RESET_MODES = set(range(20, 27))


def validate_rows(records, path, timed, warm, mode):
    caller = {int(f[0]): f for f in (line.split() for line in path.read_text().splitlines())}
    assert {int(r["id"]) for r in records} == set(caller) and len(records) == len(caller)
    for row in records:
        f = caller[int(row["id"])]
        assert (int(row["timed"]), int(row["warm"]), int(row["mode"])) == (timed, warm, mode), row
        assert int(row["retired"]) == int(mode not in ABANDONED), row
        result = int(f[5], 16) ^ int(f[6], 16)
        if mode not in RESET_MODES:
            assert int(row["gpr"], 16) == int(f[7], 16), row
            assert int(row["flags"], 16) == (xor_flags(int(f[8], 16), result)
                if int(row["retired"]) else int(f[8], 16)), row
        if int(row["retired"]):
            assert int(row["ip"], 16) == (int(f[1], 16) + 6) & 0xffff, row
            assert int(row["memory"], 16) == result, row
            odd = int(f[4], 16) & 1
            assert int(row["read_captures"]) == int(row["write_captures"]) == 1 + odd, row
            assert all(int(row[k]) == 1 for k in ["read_accepts", "write_accepts", "read_responses", "write_responses"]), row
            if timed:
                assert int(row["form_count"]) == 1 and int(row["alignment_count"]) == 2 * odd, row
                assert (int(row["read_wait1"]), int(row["read_wait2"])) == (int(f[10]), odd * int(f[11])), row
                assert (int(row["write_wait1"]), int(row["write_wait2"])) == (int(f[12]), odd * int(f[13])), row
                minimum = 7 + 4 * odd + int(f[10]) + odd * int(f[11])
                assert int(row["scheduled"]) == minimum and int(row["elapsed"]) >= minimum, row
    return len(records)


def xor_flags(old, value):
    """ISA-defined XOR flags plus the unchanged MAX policy for undefined AF."""
    result = (0x80 if value & 0x8000 else 0) | (0x40 if value == 0 else 0)
    result |= 4 if (value & 255).bit_count() % 2 == 0 else 0
    return (old & ~0x8c5) | result


def rmw_vectors(path):
    """Nineteen caller inputs; READ and WRITE waits are chosen independently."""
    records = []

    def add(odd, seed, cw, rw1, rw2, ww1, ww2, cl, rl1, rl2, wl1, wl2, payload=None):
        cs, ds = [(0, 1), (0x1234, 0xffff), (0xffff, 0x1234), (1, 0)][seed % 4]
        offset = ([1, 3, 0x0f, 0xfffd] if odd else [0, 2, 0xfe, 0xfffe])[seed % 4]
        if odd and seed % 7 == 0:
            cs, ds, offset = 0x1234, 0xffff, 0x000f
        if odd and seed == 23:
            cs, ds, offset = 0xffff, 1, 0xffef
        ip = 0x100 + seed % 2
        value = [0, 0xffff, 0x00ff, 0xff00, 0xa55a, 0x5aa5][seed % 6]
        immediate = [0xffff, 0, 0xff00, 0x00ff, 0xa55a, 0x8001][seed % 6]
        if payload is not None:
            value, immediate = payload
        regs = [(seed * 0x1234 + n * 0x1357) & 0xffff for n in range(8)]
        regs[4] = 0x8000
        packed = sum(v << (16 * n) for n, v in enumerate(regs))
        flags = [2, 0x403, 0x8d7][seed % 3]
        data_address, code_address = (ds << 4) + offset, (cs << 4) + ip
        assert offset < 0xffff and (offset & 1) == odd
        assert data_address + 1 < code_address - 1 or data_address > code_address + 10
        assert odd or (rw2 == ww2 == rl2 == wl2 == 0)
        records.append(f"{len(records)} {ip:04x} {cs:04x} {ds:04x} {offset:04x} "
            f"{value:04x} {immediate:04x} {packed:032x} {flags:04x} "
            f"{cw} {rw1} {rw2} {ww1} {ww2} {cl} {rl1} {rl2} {wl1} {wl2}")

    for seed, (cw, rw1, rw2, ww1, ww2, latency) in enumerate(itertools.product(
            range(3), range(3), range(3), range(3), range(3), [0, -1, 80])):
        add(1, seed, cw, rw1, rw2, ww1, ww2, latency, latency, latency, latency, latency)
    for seed, (cw, rw, ww, latency) in enumerate(itertools.product(
            range(3), range(3), range(3), [0, -1, 80])):
        add(0, seed, cw, rw, 0, ww, 0, latency, latency, 0, latency, 0)
    architectural = [(0x8000, 0x8001), (0xff00, 0xfeff), (0x0080, 0x0001),
                     (0x1234, 0x1237), (0x0000, 0x8000), (0xa55a, 0xa55a)]
    for seed in range(24):
        add(seed % 2, seed, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, architectural[seed % 6])
    # Isolate a late or exact response at each of the four DATA halves.
    for seed, (beat, latency, waits) in enumerate(itertools.product(range(4), [-1, 80], range(3))):
        latencies = [0] * 4
        latencies[beat] = latency
        add(1, seed, 0, waits, waits, waits, waits, 0, *latencies)
    assert len(records) == 858
    path.write_text("\n".join(records) + "\n")
    return len(records)


def controlled_vectors(out):
    fields = [line.split() for line in (out / "rmw-vectors.txt").read_text().splitlines()]
    control = out / "rmw-control-vectors.txt"
    chosen = [f for f in fields if int(f[4], 16) & 1 and f[14:19] == ["0"] * 5][::19]
    assert len(chosen) == 14
    control.write_text("\n".join(" ".join(f) for f in chosen) + "\n")
    deadline = out / "rmw-deadline-vectors.txt"
    chosen = [next(f for f in fields if int(f[4], 16) & 1 and
        f[9:14] == ["0"] + [str(w)] * 4 and f[14:19] == ["0"] * 5) for w in range(3)]
    deadline.write_text("\n".join(" ".join(f) for f in chosen) + "\n")
    late_paths = []
    for name, index in [("read", 15), ("write", 17)]:
        path = out / ("rmw-" + name + "-late-vectors.txt")
        chosen = [f for f in fields if int(f[4], 16) & 1 and f[index] == "80"][::18]
        assert len(chosen) == 14
        path.write_text("\n".join(" ".join(f) for f in chosen) + "\n")
        late_paths.append(path)
    return control, deadline, *late_paths


def preservation(out, selected):
    result = {}
    for label, generator, top, parameter, ancestor in [
        ("odd-read", odd_vectors, "p06_core_odd_read_tb", ".P06_ODD_READ_PILOT(TIMED)",
         "docs/evidence/p06-core-odd-read-20261004/odd"),
        ("write-preserved", write_vectors, "p06_core_write_tb", ".P06_WRITE_PILOT(TIMED)",
         "docs/evidence/p06-core-write-20261004/write"),
    ]:
        path = out / (label + "-vectors.txt")
        assert generator(path) == 834
        original = ROOT / "sim/spk286_timing_pilot" / (top + ".sv")
        adapted = out / (label + "-tb.sv")
        extension = ",.P06_RMW_PILOT(TIMED)"
        if label == "odd-read":
            extension += ",.P06_WRITE_PILOT(TIMED)"
        adapted.write_text(replace_once(original.read_text(), parameter, parameter + extension), newline="\n")
        simulate(out, label, select(selected), adapted, top, path)
        execute(out / label, "cold", path, ["+cold"])
        for temperature in ["normal", "cold"]:
            for tool in ["iverilog", "verilator"]:
                for suffix in ["summary.csv", "trace.csv"]:
                    name = f"{temperature}-{tool}-{suffix}"
                    old = ROOT / ancestor / name
                    previous = gzip.decompress(Path(str(old) + ".gz").read_bytes()) if suffix == "trace.csv" else old.read_bytes()
                    assert (out / label / name).read_bytes() == previous, (label, name)
        result[label] = 834
        print(f"RMW_PRESERVATION_PASS {label} warm_and_cold", flush=True)
    path = out / "register-streams.txt"
    assert stream_vectors(path) == 688
    old = ROOT / "sim/spk286_timing_pilot/p06_core_iu_tb.sv"
    adapted = out / "register-streams-tb.sv"
    text = replace_once(old.read_text(), "module p06_core_iu_tb #(parameter bit OVERLAP = 1'b1);",
        "module p06_core_iu_tb #(parameter bit OVERLAP = 1'b1);\n    wire p06_code_board_ready=1, p06_data_board_ready=1;")
    text = replace_once(text, ".P06_IU_PILOT(OVERLAP)",
        ".P06_IU_PILOT(OVERLAP),.P06_MEMORY_PILOT(1'b1),.P06_ODD_READ_PILOT(1'b1),.P06_WRITE_PILOT(1'b1),.P06_RMW_PILOT(1'b1)")
    adapted.write_text(text, newline="\n")
    rows = simulate(out, "register-streams", select(selected), adapted, "p06_core_iu_tb", path)
    assert len(rows) == 1448
    execute(out / "register-streams", "cold", path, ["+cold"])
    ancestor = ROOT / "docs/evidence/p06-core-memory-20261004/memory-iu"
    for temperature in ["normal", "cold"]:
        for tool in ["iverilog", "verilator"]:
            for suffix in ["summary.csv", "trace.csv"]:
                name = f"{temperature}-{tool}-{suffix}"
                old = ancestor / name
                previous = gzip.decompress(Path(str(old) + ".gz").read_bytes()) if suffix == "trace.csv" else old.read_bytes()
                assert (out / "register-streams" / name).read_bytes() == previous, name
    result["register-streams"] = {"programs": 688, "instructions": 1448}
    print("RMW_REGISTER_PRESERVATION_PASS programs=688 instructions=1448 warm_and_cold", flush=True)
    return result


def negative(out, selected, bench, label, marker, path, before, after, vectors, extra=()):
    mutant = out / ("negative-" + label + "-" + path.name)
    mutant.write_text(replace_once(path.read_text(), before, after), newline="\n")
    executable = out / ("negative-" + label + ".vvp")
    run(["iverilog", "-g2012", "-s", TOP, "-I" + str(CPU / "rtl"), "-I" + str(CPU / "sim/unit"),
        "-o", executable, *[mutant if p == path else p for p in select(selected)], bench],
        out / ("negative-" + label + "-build.log"))
    attempt = subprocess.run(["vvp", str(executable), f"+vectors={vectors}",
        f"+trace={out}/negative-{label}-trace.csv", f"+summary={out}/negative-{label}-summary.csv", *extra],
        cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30)
    (out / ("negative-" + label + "-run.log")).write_text(attempt.stdout)
    assert attempt.returncode != 0 and marker in attempt.stdout, (label, attempt.stdout)
    return {"marker": marker, "returncode": attempt.returncode, "source": path.name,
            "before": before, "after": after, "vectors": vectors.name, "extra": list(extra)}


def negative_checks(out, selected, bench, path, control):
    top, biu, executor = (selected[name] for name in
                          ["spk286.sv", "spk286_biu.sv", "spk286_micro_executor.sv"])
    specifications = [
        ("late-form", "RMW independent late form event oracle failed", top,
         ".rmw_form_valid(p06_timed_rmw)", ".rmw_form_valid(1'b0)", path, ()),
        ("alignment", "RMW alignment/wait budget oracle failed", top,
         ".alignment_event(p06_timed_data && p06_alignment_event)",
         ".alignment_event(1'b0)", path, ()),
        ("read-wait", "RMW alignment/wait budget oracle failed", top,
         ".read_wait_event((p06_timed_read || p06_timed_rmw) && p06_read_wait_event)",
         ".read_wait_event(1'b0)", path, ()),
        ("write-as-read-wait", "RMW independent alignment/wait event oracle failed", biu,
         "wire p06_read_cycle = !P06_WRITE_TIMING || !write_q;",
         "wire p06_read_cycle = 1'b1;", path, ()),
        ("permit-boundary", "RMW first eligible FLAGS commit oracle failed", top,
         "(!p06_result_pending || permit)", "1'b1", path, ()),
        ("early-flags", "RMW first eligible FLAGS commit oracle failed", executor,
         "assign commit_flags = allowed && operation == spk286_microcode_pkg::MC_COMMIT_FLAGS && flags_valid_q && result_disposed_q;",
         "assign commit_flags = allowed && flags_valid_q && (operation == spk286_microcode_pkg::MC_COMMIT_FLAGS || operation == spk286_microcode_pkg::MC_WRITE_RESULT_RM16);",
         path, ()),
        ("retire-at-alu", "RMW first eligible retirement oracle failed", executor,
         "(P06_RMW_TIMING && p06_rmw_form && commit_flags)",
         "(P06_RMW_TIMING && p06_rmw_form && compute_alu)", path, ()),
        ("read-assembly", "RMW independent READ response payload oracle failed", biu,
         "(second_q ? {data_in[7:0], low_byte_q} : data_in)) : raw_data_read_data;",
         "(second_q ? {low_byte_q, data_in[7:0]} : data_in)) : raw_data_read_data;", path, ()),
        ("write-payload", "RMW caller-derived logical request oracle failed", executor,
         "(result_operation ? tmp2_q : tmp0_q)",
         "(result_operation ? tmp0_q : tmp0_q)", path, ()),
    ]
    result = {}
    for label, marker, source, before, after, vectors, extra in specifications:
        result[label] = negative(out, selected, bench, label, marker, source, before, after, vectors, extra)
        print(f"RMW_NEGATIVE_PASS {label}", flush=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--prepare", action="store_true")
    args = parser.parse_args()
    out = args.output.resolve()
    out.relative_to(ROOT.resolve())
    out.mkdir(parents=True, exist_ok=False)
    prior = ROOT / "docs/evidence/p06-core-write-20261004/receipt.json"
    assert sha(prior) == M6F_RECEIPT_SHA256
    names = set(json.loads(prior.read_text())["sources_sha256"])
    names.update([prior.relative_to(ROOT).as_posix(), "scripts/build_p06_rmw_cpu.py",
        "scripts/check_p06_rmw_components.py", "scripts/run_p06_rmw_cpu.py",
        "scripts/run_p06_iu.py", "sim/spk286_timing_pilot/p06_core_iu_tb.sv"])
    bench = ROOT / "sim/spk286_timing_pilot" / (TOP + ".sv")
    if not args.prepare:
        names.add(bench.relative_to(ROOT).as_posix())
    inputs = [ROOT / name for name in sorted(names)]
    before = {p.relative_to(ROOT).as_posix(): sha(p) for p in inputs}
    selected = build(out)
    components = prepare(out, selected)
    count = rmw_vectors(out / "rmw-vectors.txt")
    control, deadline, read_late, write_late = controlled_vectors(out)
    if args.prepare:
        print(f"RMW_PREPARE_PASS cases={count}", flush=True)
        return
    versions = {name: run(command, out / (name + "-version.log")).splitlines()[0] for name, command in [
        ("iverilog", ["iverilog", "-V"]), ("verilator", ["verilator", "--version"]), ("yosys", ["yosys", "-V"])]}
    path = out / "rmw-vectors.txt"
    normal = simulate(out, "rmw", select(selected), bench, TOP, path)
    cold = execute(out / "rmw", "cold", path, ["+cold"])
    for warm, rows in [(1, normal), (0, cold)]:
        assert validate_rows(rows, path, 1, warm, 0) == count
    print(f"RMW_MATRIX_PASS cases={count} warm_and_cold", flush=True)
    controlled = {}
    for mode in MODES:
        mode_path = read_late if mode == 27 else write_late if mode == 28 else control
        for warm in [1, 0]:
            label = f"mode{mode}-" + ("warm" if warm else "cold")
            rows = execute(out / "rmw", label, mode_path, [f"+mode={mode}"] + ([] if warm else ["+cold"]))
            controlled[label] = validate_rows(rows, mode_path, 1, warm, mode)
        print(f"RMW_CONTROL_PASS mode={mode}", flush=True)
    controlled["mode29-warm"] = validate_rows(execute(out / "rmw", "mode29-warm", deadline,
        ["+mode=29"]), deadline, 1, 1, 29)
    maximum = out / "rmw-max-tb.sv"
    maximum.write_text(replace_once(bench.read_text(), "parameter bit TIMED=1'b1", "parameter bit TIMED=1'b0"), newline="\n")
    original = out / "rmw-original-tb.sv"
    original.write_text("`define P06_ORIGINAL\n" + maximum.read_text(), newline="\n")
    for label, rtl, probe in [("original-max", sources(), original), ("private-max", select(selected), maximum)]:
        assert validate_rows(simulate(out, label, rtl, probe, TOP, path), path, 0, 1, 0) == count
    for suffix in ["summary.csv", "trace.csv"]:
        assert (out / ("original-max/normal-iverilog-" + suffix)).read_bytes() == (out / ("private-max/normal-iverilog-" + suffix)).read_bytes()
    preserved = preservation(out, selected)
    units = max_units(out, selected)
    negatives = negative_checks(out, selected, bench, path, control)
    assert negatives, "Required mutation checks have not been defined"
    run(["python3", "-m", "tools.microcode.compile_microcode", "--check"], out / "microcode.log", cwd=CPU)
    assert before == {p.relative_to(ROOT).as_posix(): sha(p) for p in inputs}, "Sources changed during acceptance"
    assert "spk286_timing_pilot" not in (ROOT / "rtl/spk286_integration/spk286_integration.qip").read_text()
    receipt = {"status": "P06_PRIVATE_RMW_CPU_PASS", "matrix_cases": count,
        "controls": controlled, "components": components, "preserved": preserved,
        "max_units": units, "negative_checks": negatives, "tool_versions": versions,
        "sources_sha256": before, "generated_cpu_sha256": {name: sha(p) for name, p in selected.items()},
        "dual_traces_equal": True, "max_traces_equal": True, "previous_traces_preserved": True,
        "production_unchanged": True,
        "scope": "Private M6g 6 MHz virtual Real Mode prefix-free 81 36 disp16 imm16 XOR word RMW. "
            "Retained decoder late form +4, per-reference odd +2 READ/+2 WRITE, READ waits only, original final FLAGS and retirement together. "
            "Not write-buffer EU overlap, exact Intel issue phasing, arbitrary EA/LOCK/events, public profiles, physical calibration or FPGA fit/STA/RBF.",
        "artifacts_sha256": {p.relative_to(out).as_posix(): sha(p) for p in out.rglob("*") if p.is_file()
            and "obj" not in p.relative_to(out).parts and p.suffix != ".vvp" and p.name != "receipt.json"}}
    (out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print("P06_PRIVATE_RMW_CPU_PASS", flush=True)


if __name__ == "__main__":
    main()
