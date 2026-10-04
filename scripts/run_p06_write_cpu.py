#!/usr/bin/env python3
"""Directed private M6f serialized A3 WRITE acceptance; never production selection."""
import argparse
import gzip
import json
import subprocess
from pathlib import Path
from build_p06_write_cpu import build, M6E_RECEIPT_SHA256
from build_p06_register_cpu import replace_once
from check_p06_write_components import prepare, select
from run_p06_core_register import ROOT, CPU, sources, run, sha
from run_p06_timed_register import simulate, execute
from run_p06_odd_read_cpu import odd_vectors, controlled_vectors, max_units

TOP = "p06_core_write_tb"
MODES = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 14, 15, 16, 17, 18, 19, 20, 21]
ABANDONED = {3, 4, 5, 6, 7, 8, 10, 11, 12, 15, 16, 17, 18, 19, 20, 21}
RESET_MODES = {5, 6, 11, 18, 21}


def write_vectors(path):
    """Same independent address/lane/backend schedules as frozen M6e, now A3."""
    return odd_vectors(path)


def controls(out):
    temporary = out / "control-generation"
    temporary.mkdir()
    write_vectors(temporary / "odd-vectors.txt")
    paths = controlled_vectors(temporary)
    result = []
    for old, name in zip(paths, ["write-control-vectors.txt", "write-deadline-vectors.txt",
                               "write-before-ready-vectors.txt"]):
        new = out / name
        new.write_bytes(old.read_bytes())
        result.append(new)
    return tuple(result)


def validate_rows(records, path, timed, warm, mode):
    caller = {int(f[0]): f for f in (line.split() for line in path.read_text().splitlines())}
    assert {int(r["id"]) for r in records} == set(caller) and len(records) == len(caller)
    for row in records:
        f = caller[int(row["id"])]
        assert (int(row["timed"]), int(row["warm"]), int(row["mode"])) == (timed, warm, mode)
        assert int(row["retired"]) == int(mode not in ABANDONED), row
        if mode not in RESET_MODES:
            assert int(row["gpr"], 16) == int(f[6], 16), row
            assert int(row["flags"], 16) == int(f[7], 16), row
        if int(row["retired"]):
            assert int(row["ip"], 16) == (int(f[1], 16) + 3) & 0xffff, row
            assert int(row["memory"], 16) == int(f[6], 16) & 0xffff, row
            assert int(row["data_captures"]) == 1 + (int(f[4], 16) & 1), row
        if timed and int(row["retired"]):
            odd = int(f[4], 16) & 1
            assert int(row["data_accepts"]) == int(row["data_responses"]) == 1, row
            assert (int(row["wait1"]), int(row["wait2"])) == (int(f[9]), odd * int(f[10])), row
            assert int(row["alignment_count"]) == odd, row
            assert int(row["scheduled"]) == 3 + 2 * odd, row
            assert int(row["elapsed"]) >= 3 + 2 * odd, row
    return len(records)


def preservation(out, selected):
    """WRITE capability must preserve frozen M6e warm/cold READ edge traces."""
    directory = out / "odd-read"
    path = out / "read-vectors.txt"
    assert odd_vectors(path) == 834
    bench = out / "read-preservation-tb.sv"
    old = ROOT / "sim/spk286_timing_pilot/p06_core_odd_read_tb.sv"
    bench.write_text(replace_once(old.read_text(), ".P06_ODD_READ_PILOT(TIMED)",
        ".P06_ODD_READ_PILOT(TIMED),.P06_WRITE_PILOT(TIMED)"), newline="\n")
    simulate(out, "odd-read", select(selected), bench, "p06_core_odd_read_tb", path)
    execute(directory, "cold", path, ["+cold"])
    ancestor = ROOT / "docs/evidence/p06-core-odd-read-20261004/odd"
    for name in ["normal", "cold"]:
        for tool in ["iverilog", "verilator"]:
            for artifact in ["summary.csv", "trace.csv"]:
                relative = f"{name}-{tool}-{artifact}"
                previous = ancestor / relative
                expected = gzip.decompress(Path(str(previous) + ".gz").read_bytes()) if artifact == "trace.csv" else previous.read_bytes()
                assert (directory / relative).read_bytes() == expected, relative
    print("WRITE_READ_PRESERVATION_PASS cases=834 warm_and_cold", flush=True)
    return {"odd-read": 834}


def negative(out, selected, bench, label, marker, path, before, after, vectors, extra=()):
    """A mutation must fail the specified independent assertion, not any error."""
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
    # Mutate generated copies only; exact anchors are guarded by replace_once.
    top, biu = selected["spk286.sv"], selected["spk286_biu.sv"]
    result = {}
    result["alignment"] = negative(out, selected, bench, "alignment",
        "A3 write alignment/wait budget oracle failed", top,
        ".alignment_event(p06_timed_data && p06_alignment_event)", ".alignment_event(1'b0)", path)
    result["write-as-read-wait"] = negative(out, selected, bench, "write-as-read-wait",
        "A3 write independent alignment/wait event oracle failed", biu,
        "wire p06_read_cycle = !P06_WRITE_TIMING || !write_q;", "wire p06_read_cycle = 1'b1;", path)
    result["permit"] = negative(out, selected, bench, "permit",
        "A3 first eligible retirement oracle failed", top,
        "(!p06_result_pending || permit)", "1'b1", path)
    result["end-handshake"] = negative(out, selected, bench, "end-handshake",
        "A3 write retirement/architectural oracle failed", top,
        ".retire_ready(execution_allowed && (operation_valid || p06_write_end_pending))",
        ".retire_ready(execution_allowed && operation_valid)", path)
    result["second-early"] = negative(out, selected, bench, "second-early",
        "A3 write logical owner oracle failed: physical presence/second gate", biu,
        "state_q == SECOND_TS || state_q == SECOND_TC ||", "1'b1 ||", path)
    result["first-publication"] = negative(out, selected, bench, "first-publication",
        "A3 write word publication oracle failed", biu,
        "assign p06_complete = sample_tc && state_q != ODD_TC && p06_board_ready && available;",
        "assign p06_complete = sample_tc && p06_board_ready && (available || first_available);", path)
    result["first-release"] = negative(out, selected, bench, "first-release",
        "A3 write logical owner oracle failed", biu,
        "(!P06_ODD_READ_TIMING || !address_q[0] || byte_q)", "1'b1", control, ["+mode=16"])
    result["payload-lane"] = negative(out, selected, bench, "payload-lane",
        "A3 write caller-derived address/lane/payload oracle failed", biu,
        "(address_q[0] ? {write_data_q[7:0], 8'h00} :",
        "(address_q[0] ? {write_data_q[15:8], 8'h00} :", path)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--prepare", action="store_true")
    args = parser.parse_args()
    out = args.output.resolve()
    out.relative_to(ROOT.resolve())
    out.mkdir(parents=True, exist_ok=False)
    bench = ROOT / "sim/spk286_timing_pilot" / (TOP + ".sv")
    prior = ROOT / "docs/evidence/p06-core-odd-read-20261004/receipt.json"
    assert sha(prior) == M6E_RECEIPT_SHA256
    names = set(json.loads(prior.read_text())["sources_sha256"])
    names.update([prior.relative_to(ROOT).as_posix(), "scripts/run_p06_write_cpu.py",
        "scripts/build_p06_write_cpu.py", "scripts/check_p06_write_components.py",
        "rtl/spk286_timing_pilot/p06_write_biu_connection.svh"])
    if not args.prepare:
        names.add(bench.relative_to(ROOT).as_posix())
    inputs = [ROOT / name for name in sorted(names)]
    before = {p.relative_to(ROOT).as_posix(): sha(p) for p in inputs}
    selected = build(out)
    components = prepare(out, selected)
    count = write_vectors(out / "write-vectors.txt")
    control, deadline, before_ready = controls(out)
    if args.prepare:
        print(f"WRITE_PREPARE_PASS cases={count}", flush=True)
        return
    versions = {name: run(command, out / (name + "-version.log")).splitlines()[0] for name, command in [
        ("iverilog", ["iverilog", "-V"]), ("verilator", ["verilator", "--version"]), ("yosys", ["yosys", "-V"])]}
    path = out / "write-vectors.txt"
    normal = simulate(out, "write", select(selected), bench, TOP, path)
    cold = execute(out / "write", "cold", path, ["+cold"])
    for warm, rows in [(1, normal), (0, cold)]:
        assert validate_rows(rows, path, 1, warm, 0) == count
    print(f"WRITE_MATRIX_PASS cases={count} warm_and_cold", flush=True)
    controlled = {}
    for mode in MODES:
        mode_path = before_ready if mode == 15 else control
        for warm in [1, 0]:
            label = f"mode{mode}-" + ("warm" if warm else "cold")
            rows = execute(out / "write", label, mode_path, [f"+mode={mode}"] + ([] if warm else ["+cold"]))
            controlled[label] = validate_rows(rows, mode_path, 1, warm, mode)
        print(f"WRITE_CONTROL_PASS mode={mode}", flush=True)
    controlled["mode13-warm"] = validate_rows(execute(out / "write", "mode13-warm", deadline,
        ["+mode=13"]), deadline, 1, 1, 13)
    maximum = out / "write-max-tb.sv"
    maximum.write_text(replace_once(bench.read_text(), "parameter bit TIMED=1'b1",
        "parameter bit TIMED=1'b0"), newline="\n")
    original = out / "write-original-tb.sv"
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
    receipt = {"status": "P06_PRIVATE_WRITE_CPU_PASS", "matrix_cases": count,
        "controls": controlled, "components": components, "preserved": preserved,
        "max_units": units, "negative_checks": negatives, "tool_versions": versions,
        "sources_sha256": before, "generated_cpu_sha256": {name: sha(p) for name, p in selected.items()},
        "dual_traces_equal": True, "max_traces_equal": True, "read_traces_preserved": True,
        "production_unchanged": True,
        "scope": "Private M6f 6 MHz virtual Real Mode prefix-free A3 word WRITE, serialized END after final logical Tc. "
            "Separate +2 alignment and no WRITE wait increment in EU budget. Not buffered EU overlap, exact Intel issue phases, "
            "RMW/events, public profiles, physical calibration or complete FPGA fit/STA/RBF.",
        "artifacts_sha256": {p.relative_to(out).as_posix(): sha(p) for p in out.rglob("*") if p.is_file()
            and "obj" not in p.relative_to(out).parts and p.suffix != ".vvp" and p.name != "receipt.json"}}
    (out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print("P06_PRIVATE_WRITE_CPU_PASS", flush=True)


if __name__ == "__main__":
    main()
