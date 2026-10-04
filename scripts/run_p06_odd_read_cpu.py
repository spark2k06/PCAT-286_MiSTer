#!/usr/bin/env python3
"""Directed private M6e A1 two-beat CPU acceptance, never production selection."""
import argparse
import csv
import gzip
import itertools
import json
import subprocess
from pathlib import Path
from build_p06_odd_read_cpu import build, M6C_RECEIPT_SHA256
from build_p06_register_cpu import replace_once
from check_p06_odd_components import prepare, select
from run_p06_core_register import ROOT, CPU, sources, run, sha
from run_p06_timed_register import simulate, execute
from run_p06_memory_cpu import memory_vectors, private_bench
from run_p06_read_stream import stream_vectors

TOP = "p06_core_odd_read_tb"
UNIT_NAMES = ["spk286_biu", "spk286_biu_width_io", "spk286_biu_hold_lock",
              "spk286_operand_byte"]


def odd_vectors(path):
    """Fourteen caller inputs, independently chosen lanes and response schedules."""
    records = []
    def add(odd, seed, cw, dw1, dw2, cl, dl1, dl2):
        cs, ds = [(0, 1), (0x1234, 0xffff), (0xffff, 0x1234), (1, 0)][seed % 4]
        offset = ([1, 3, 0x0f, 0xfffd] if odd else [0, 2, 0xfe, 0xfffe])[seed % 4]
        # Include an odd word whose second physical byte crosses one MiB.
        if odd and seed % 7 == 0:
            cs, ds, offset = 0x1234, 0xffff, 0x000f
        if odd and seed == 23:
            cs, ds, offset = 0xffff, 1, 0xffef
        ip = 0x100 + seed % 2
        value = [0, 0xffff, 0x00ff, 0xff00, 0xa55a, 0x5aa5][seed % 6]
        regs = [(seed * 0x1234 + n * 0x1357) & 0xffff for n in range(8)]
        regs[4] = 0x8000
        if seed % 11 == 0:
            regs[0] = value
        packed = sum(v << (16*n) for n, v in enumerate(regs))
        flags = [2, 0x403, 0x8d7][seed % 3]
        data_address, code_address = (ds << 4) + offset, (cs << 4) + ip
        assert (offset & 1) == odd and offset < 0xffff
        assert data_address + 1 < code_address - 1 or data_address > code_address + 7
        assert odd or (dw2 == 0 and dl2 == 0)
        records.append(f"{len(records)} {ip:04x} {cs:04x} {ds:04x} {offset:04x} "
            f"{value:04x} {packed:032x} {flags:04x} {cw} {dw1} {dw2} {cl} {dl1} {dl2}")
    for seed, (cw, dw1, dw2, cl, dl1, dl2) in enumerate(itertools.product(
            range(3), range(3), range(3), [0, -1, 80], [0, -1, 80], [0, -1, 80])):
        add(1, seed, cw, dw1, dw2, cl, dl1, dl2)
    for seed, (cw, dw, cl, dl) in enumerate(itertools.product(
            range(3), range(3), [0, -1, 80], [0, -1, 80])):
        add(0, seed, cw, dw, 0, cl, dl, 0)
    for seed in range(24):
        add(seed % 2, seed, 0, 0, 0, 0, 0, 0)
    assert len(records) == 834
    path.write_text("\n".join(records) + "\n")
    return len(records)


def controlled_vectors(out):
    fields = [line.split() for line in (out / "odd-vectors.txt").read_text().splitlines()]
    # Controls before the first logical Tc require an early first physical
    # READY; later controls retain exact/late final READY and each wait count.
    chosen = [f for f in fields if int(f[4], 16) & 1 and f[11:13] == ["0", "0"]][::7]
    path = out / "odd-control-vectors.txt"
    path.write_text("\n".join(" ".join(f) for f in chosen) + "\n")
    deadline = out / "odd-deadline-vectors.txt"
    chosen_deadline = [next(f for f in fields if int(f[4], 16) & 1 and
        f[8:14] == ["0", str(w), str(w), "0", "0", "0"]) for w in range(3)]
    deadline.write_text("\n".join(" ".join(f) for f in chosen_deadline) + "\n")
    before_ready = out / "odd-before-ready-vectors.txt"
    chosen_late = [f for f in fields if int(f[4], 16) & 1 and f[11:13] == ["0", "80"]][::7]
    before_ready.write_text("\n".join(" ".join(f) for f in chosen_late) + "\n")
    return path, deadline, before_ready


def validate_rows(records, path, timed, warm, mode):
    caller = {int(f[0]): f for f in (line.split() for line in path.read_text().splitlines())}
    assert {int(r["id"]) for r in records} == set(caller)
    assert len(records) == len(caller)
    # The bench is also responsible for every-edge commit/phase and owner
    # oracles. This independent caller check does not read any DUT permission.
    for row in records:
        f = caller[int(row["id"])]
        assert (int(row["timed"]), int(row["warm"]), int(row["mode"])) == (timed, warm, mode)
        if mode in [3, 4, 5, 6, 7, 8, 10, 11, 12, 15, 16, 17, 18]:
            # Controlled abandonment is accepted only after physical drain;
            # those runs deliberately have no architectural retirement.
            assert int(row["retired"]) == 0
            if mode not in [5, 6, 11, 18]:
                assert int(row["gpr"], 16) == int(f[6], 16)
                assert int(row["flags"], 16) == int(f[7], 16)
        else:
            assert int(row["retired"]) == 1
            assert int(row["gpr"], 16) == (int(f[6], 16) & ~0xffff) | int(f[5], 16)
            assert int(row["flags"], 16) == int(f[7], 16)
            assert int(row["ip"], 16) == (int(f[1], 16) + 3) & 0xffff
        if timed and int(row["retired"]):
            odd = int(f[4], 16) & 1
            assert int(row["data_captures"]) == 1 + odd
            assert int(row["data_accepts"]) == int(row["data_responses"]) == 1
            assert (int(row["wait1"]), int(row["wait2"])) == (int(f[9]), odd * int(f[10]))
            assert int(row["alignment_count"]) == odd
            assert int(row["elapsed"]) >= 5 + 2*odd + int(row["wait1"]) + int(row["wait2"])
    return len(records)


def preservation(out, selected):
    counts = {}
    for label, generator, bench_name, parameter, expected in [
        ("aligned-memory", memory_vectors, "p06_core_memory_tb", ".P06_MEMORY_PILOT(TIMED)", 267),
        ("aligned-stream", stream_vectors, "p06_core_read_stream_tb", ".P06_MEMORY_PILOT(TIMED)", 240),
    ]:
        path = out / (label + "-vectors.txt")
        assert generator(path) == expected
        frozen = ROOT / "sim/spk286_timing_pilot" / (bench_name + ".sv")
        adapted = out / (label + "-tb.sv")
        adapted.write_text(replace_once(frozen.read_text(), parameter,
            parameter + ", .P06_ODD_READ_PILOT(TIMED)"), newline="\n")
        simulate(out, label, select(selected), adapted, bench_name, path)
        execute(out / label, "cold", path, ["+cold"])
        ancestor = ROOT / ("docs/evidence/p06-core-memory-20261004/memory" if label == "aligned-memory"
            else "docs/evidence/p06-core-read-stream-20261004/streams")
        for name in ["normal", "cold"]:
            for tool in ["iverilog", "verilator"]:
                for artifact in ["summary.csv", "trace.csv"]:
                    relative = f"{name}-{tool}-{artifact}"
                    old = ancestor / relative
                    expected_bytes = gzip.decompress(Path(str(old) + ".gz").read_bytes()) if artifact == "trace.csv" else old.read_bytes()
                    assert (out / label / relative).read_bytes() == expected_bytes, (label, relative)
        counts[label] = expected
        print(f"ODD_ALIGNED_PRESERVATION_PASS {label} cases={expected} warm_and_cold", flush=True)
    return counts


def max_units(out, selected):
    results = {}
    for name in UNIT_NAMES:
        bench = private_bench(out, name)
        if name.startswith("spk286_biu"):
            bench.write_text(replace_once(bench.read_text(), "wire p06_scope_error,",
                "wire p06_alignment_event;\n    wire p06_scope_error,"), newline="\n")
        directory = out / name
        directory.mkdir()
        top = name + "_tb"
        include = ["-I" + str(CPU / "rtl"), "-I" + str(CPU / "sim/unit")]
        run(["iverilog", "-g2012", "-s", top, *include, "-o", directory / "test.vvp",
             *select(selected), bench], directory / "iverilog-build.log")
        run(["vvp", directory / "test.vvp"], directory / "iverilog-run.log")
        run(["verilator", "--binary", "--timing", "--assert", "-j", "4", "--top-module", top,
             "--Mdir", directory / "obj", "-o", "unit-test", *include, *select(selected), bench],
            directory / "verilator-build.log", timeout=600)
        run([directory / "obj/unit-test"], directory / "verilator-run.log")
        markers = [[line for line in (directory / (tool + "-run.log")).read_text().splitlines()
                    if "PASS" in line] for tool in ["iverilog", "verilator"]]
        assert len(markers[0]) == 1 and markers[0] == markers[1]
        results[name] = markers[0][0]
        print("ODD_MAX_UNIT_PASS " + name, flush=True)
    return results


def negative(out, selected, bench, label, marker, path, before, after, vectors, extra=()):
    mutant = out / ("negative-" + label + "-" + path.name)
    mutant.write_text(replace_once(path.read_text(), before, after), newline="\n")
    executable = out / ("negative-" + label + ".vvp")
    run(["iverilog", "-g2012", "-s", TOP, "-I" + str(CPU / "rtl"), "-I" + str(CPU / "sim/unit"),
        "-o", executable, *[mutant if p == path else p for p in select(selected)], bench],
        out / ("negative-" + label + "-build.log"))
    result = subprocess.run(["vvp", str(executable), f"+vectors={vectors}",
        f"+trace={out}/negative-{label}-trace.csv", f"+summary={out}/negative-{label}-summary.csv", *extra],
        cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30)
    (out / ("negative-" + label + "-run.log")).write_text(result.stdout)
    assert result.returncode != 0 and marker in result.stdout, (label, result.stdout)
    return {"marker": marker, "returncode": result.returncode, "source": path.name,
            "before": before, "after": after, "vectors": vectors.name, "extra": list(extra)}


def negative_checks(out, selected, bench, path, control):
    # Mutations affect generated copies, not production or frozen ancestors.
    checks = {}
    checks["alignment"] = negative(out, selected, bench, "alignment", "odd read alignment/wait budget oracle failed",
        selected["spk286.sv"], ".alignment_event(p06_timed_read && p06_alignment_event)",
        ".alignment_event(1'b0)", path)
    checks["waits"] = negative(out, selected, bench, "waits", "odd read alignment/wait budget oracle failed",
        selected["spk286.sv"], ".read_wait_event(p06_timed_read && p06_read_wait_event)",
        ".read_wait_event(1'b0)", path)
    checks["permit"] = negative(out, selected, bench, "permit", "odd read first eligible commit oracle failed",
        selected["spk286.sv"], "(!p06_result_pending || permit)", "1'b1", path)
    biu = selected["spk286_biu.sv"]
    checks["second-early"] = negative(out, selected, bench, "second-early",
        "odd read logical owner oracle failed: physical presence/second gate", biu,
        "state_q == SECOND_TS || state_q == SECOND_TC ||", "1'b1 ||", path)
    checks["first-publication"] = negative(out, selected, bench, "first-publication",
        "odd read word publication oracle failed", biu,
        "assign p06_complete = sample_tc && state_q != ODD_TC && p06_board_ready && available;",
        "assign p06_complete = sample_tc && p06_board_ready && (available || first_available);", path)
    checks["first-release"] = negative(out, selected, bench, "first-release",
        "odd read logical owner oracle failed", biu,
        "(!P06_ODD_READ_TIMING || !address_q[0] || byte_q)", "1'b1", control, ["+mode=16"])
    checks["final-assembly"] = negative(out, selected, bench, "final-assembly",
        "odd read assembled payload oracle failed", biu,
        "(second_q ? {data_in[7:0], low_byte_q} : data_in)) : raw_data_read_data;",
        "(second_q ? {low_byte_q, data_in[7:0]} : data_in)) : raw_data_read_data;", path)
    checks["retained-assembly"] = negative(out, selected, bench, "retained-assembly",
        "odd read assembled payload oracle failed", biu,
        "raw_data_read_data <= byte_q ? {8'd0, (address_q[0] ? data_in[15:8] : data_in[7:0])} :\n"
        "                                      (second_q ? {data_in[7:0], low_byte_q} : data_in);",
        "raw_data_read_data <= byte_q ? {8'd0, (address_q[0] ? data_in[15:8] : data_in[7:0])} :\n"
        "                                      (second_q ? {low_byte_q, data_in[7:0]} : data_in);", path)
    return checks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--prepare", action="store_true")
    args = parser.parse_args()
    out = args.output.resolve()
    out.relative_to(ROOT.resolve())
    out.mkdir(parents=True, exist_ok=False)
    bench = ROOT / "sim/spk286_timing_pilot" / (TOP + ".sv")
    old = json.loads((ROOT / "docs/evidence/p06-core-memory-20261004/receipt.json").read_text())
    names = set(old["sources_sha256"])
    names.update(["scripts/run_p06_odd_read_cpu.py", "scripts/build_p06_odd_read_cpu.py",
        "scripts/check_p06_odd_components.py", "scripts/run_p06_read_stream.py",
        "rtl/spk286_timing_pilot/p06_odd_read_biu_connection.svh",
        "sim/spk286_timing_pilot/p06_core_read_stream_tb.sv",
        "docs/evidence/p06-core-memory-20261004/receipt.json",
        "docs/evidence/p06-core-read-stream-20261004/receipt.json"])
    if not args.prepare:
        names.add(bench.relative_to(ROOT).as_posix())
    inputs = [ROOT / name for name in sorted(names)]
    before = {p.relative_to(ROOT).as_posix(): sha(p) for p in inputs}
    assert before["docs/evidence/p06-core-memory-20261004/receipt.json"] == M6C_RECEIPT_SHA256
    selected = build(out)
    components = prepare(out, selected)
    count = odd_vectors(out / "odd-vectors.txt")
    control, deadline, before_ready = controlled_vectors(out)
    if args.prepare:
        print(f"ODD_PREPARE_PASS cases={count}", flush=True)
        return
    versions = {name: run(command, out / (name + "-version.log")).splitlines()[0] for name, command in [
        ("iverilog", ["iverilog", "-V"]), ("verilator", ["verilator", "--version"]), ("yosys", ["yosys", "-V"])]}
    path = out / "odd-vectors.txt"
    negatives = negative_checks(out, selected, bench, path, control)
    print("ODD_NEGATIVE_CHECKS_PASS count=8", flush=True)
    normal = simulate(out, "odd", select(selected), bench, TOP, path)
    cold = execute(out / "odd", "cold", path, ["+cold"])
    for warm, rows in [(1, normal), (0, cold)]:
        assert validate_rows(rows, path, 1, warm, 0) == count
    print(f"ODD_MATRIX_PASS cases={count} warm_and_cold", flush=True)
    controls = {}
    for mode in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 14, 15, 16, 17, 18]:
        mode_path = before_ready if mode == 15 else control
        for warm in [1, 0]:
            label = f"mode{mode}-" + ("warm" if warm else "cold")
            rows = execute(out / "odd", label, mode_path, [f"+mode={mode}"] + ([] if warm else ["+cold"]))
            controls[label] = validate_rows(rows, mode_path, 1, warm, mode)
        print(f"ODD_CONTROL_PASS mode={mode}", flush=True)
    controls["mode13-warm"] = validate_rows(execute(out / "odd", "mode13-warm", deadline,
        ["+mode=13"]), deadline, 1, 1, 13)
    maximum = out / "odd-max-tb.sv"
    maximum.write_text(replace_once(bench.read_text(), "parameter bit TIMED=1'b1",
        "parameter bit TIMED=1'b0"), newline="\n")
    original = out / "odd-original-tb.sv"
    original.write_text("`define P06_ORIGINAL\n" + maximum.read_text(), newline="\n")
    for label, rtl, probe in [("original-max", sources(), original), ("private-max", select(selected), maximum)]:
        assert validate_rows(simulate(out, label, rtl, probe, TOP, path), path, 0, 1, 0) == count
    for suffix in ["summary.csv", "trace.csv"]:
        assert (out / ("original-max/normal-iverilog-" + suffix)).read_bytes() == (out / ("private-max/normal-iverilog-" + suffix)).read_bytes()
    preserved = preservation(out, selected)
    units = max_units(out, selected)
    run(["python3", "-m", "tools.microcode.compile_microcode", "--check"], out / "microcode.log", cwd=CPU)
    assert before == {p.relative_to(ROOT).as_posix(): sha(p) for p in inputs}, "Sources changed during acceptance"
    assert "spk286_timing_pilot" not in (ROOT / "rtl/spk286_integration/spk286_integration.qip").read_text()
    receipt = {"status": "P06_PRIVATE_ODD_READ_CPU_PASS", "matrix_cases": count,
        "controls": controls, "components": components, "preserved": preserved,
        "max_units": units, "negative_checks": negatives, "tool_versions": versions,
        "sources_sha256": before, "generated_cpu_sha256": {name: sha(p) for name, p in selected.items()},
        "dual_traces_equal": True, "max_traces_equal": True, "aligned_traces_preserved": True,
        "production_unchanged": True,
        "scope": "Private M6e 6 MHz virtual Real Mode prefix-free A1 word READ; odd two-beat service, "
            "separate +2 alignment and per-beat READ waits. Not exact native Intel issue phasing, "
            "writes/RMW/events, public speed profiles, physical calibration, complete FPGA cost/fit/STA/RBF.",
        "artifacts_sha256": {p.relative_to(out).as_posix(): sha(p) for p in out.rglob("*") if p.is_file()
            and "obj" not in p.relative_to(out).parts and p.suffix != ".vvp" and p.name != "receipt.json"}}
    (out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print("P06_PRIVATE_ODD_READ_CPU_PASS", flush=True)


if __name__ == "__main__":
    main()
