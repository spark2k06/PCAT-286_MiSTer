#!/usr/bin/env python3
"""Full SPK286 register timing probe, directed only, isolated output directory."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
CPU = ROOT / "vendor/spk286"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sources():
    packages = ["microcode/generated/spk286_microcode_pkg.sv",
                "microcode/generated/spk286_microcode_rom.sv",
                "microcode/generated/spk286_microcode_sync_rom.sv",
                "rtl/spk286_protected_pkg.sv", "rtl/spk286_tss_pkg.sv"]
    paths = [CPU / p for p in packages]
    paths += [p for p in sorted((CPU / "rtl").glob("*.sv")) if p not in paths]
    return paths


def run(args, log, cwd=ROOT, timeout=300):
    result = subprocess.run([str(x) for x in args], cwd=cwd, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
    log.write_text(result.stdout)
    if result.returncode:
        raise RuntimeError(f"Command failed: {args}\n{result.stdout[-5000:]}")
    return result.stdout


def vectors(path):
    specs = [([0x01, 0xd8], 0, 0, 3, None), ([0x03, 0xd8], 0, 3, 0, None),
             ([0x31, 0xfa], 1, 2, 7, None), ([0x33, 0xd7], 1, 2, 7, None),
             ([0x39, 0xd8], 2, 0, 3, None), ([0x3b, 0xc3], 2, 0, 3, None),
             ([0x83, 0xc3, 1], 3, 3, None, 1), ([0x83, 0xc3, 0xff], 3, 3, None, 0xffff),
             ([0x81, 0xf7, 0xaa, 0x55], 4, 7, None, 0x55aa),
             ([0x05, 1, 0], 3, 0, None, 1), ([0x35, 0xaa, 0x55], 4, 0, None, 0x55aa),
             ([0x83, 0xf7, 0xff], 4, 7, None, 0xffff), ([0x81, 0xc3, 1, 0], 3, 3, None, 1)]
    records = []
    for encoded, form, dst, src, immediate in specs:
        for seed in [0, 0x7fff, 0xffff, 0x1234]:
            for start in [0x100, 0x101]:
                for ready in [0, 1]:
                    regs = [(seed + i * 0x1111) & 0xffff for i in range(8)]
                    regs[4] = 0x800
                    old = 0x403 if seed & 1 else 2
                    a, b = regs[dst], regs[src] if src is not None else immediate
                    result = ((a + b) if form in [0, 3] else (a - b) if form == 2 else a ^ b) & 0xffff
                    flags = (0x80 if result & 0x8000 else 0) | (0x40 if result == 0 else 0) | \
                            (4 if (result & 255).bit_count() % 2 == 0 else 0)
                    logical = form in [1, 4]
                    if not logical:
                        subtract = form == 2
                        flags |= int(a < b) if subtract else int(a + b > 0xffff)
                        flags |= 0x10 if (a ^ b ^ result) & 0x10 else 0
                        overflow = ((a ^ b) & (a ^ result)) if subtract else ((~(a ^ b)) & (a ^ result))
                        flags |= 0x800 if overflow & 0x8000 else 0
                    affected = 0x8c5 if logical else 0x8d5
                    expected_flags = (old & ~affected) | flags
                    pack = lambda words: sum(word << (i * 16) for i, word in enumerate(words))
                    initial = pack(regs)
                    if form != 2:
                        regs[dst] = result
                    code = int.from_bytes(bytes(encoded), "little")
                    records.append(f"{len(records)} {form} {len(encoded)} {start:04x} {ready} {code:08x} {initial:032x} {old:04x} {pack(regs):032x} {expected_flags:04x} {0xffff if not logical else 0xffef:04x}")
    path.write_text("\n".join(records) + "\n")
    return len(records)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve(); out.mkdir(parents=True, exist_ok=False)
    rtl = sources()
    bench = ROOT / "sim/spk286_timing_pilot/p06_core_register_tb.sv"
    inputs = rtl + [bench, Path(__file__)]
    before = {p.relative_to(ROOT).as_posix(): sha(p) for p in inputs}
    versions = {tool: run(arguments, out / (tool + "-version.log")).splitlines()[0]
                for tool, arguments in [("iverilog", ["iverilog", "-V"]),
                                        ("verilator", ["verilator", "--version"])]}
    run(["python3", "-m", "tools.microcode.compile_microcode", "--check"], out / "microcode.log", cwd=CPU)
    count = vectors(out / "vectors.txt")
    run(["verilator", "--lint-only", "--Wall", "--top-module", "spk286", "-I" + str(CPU / "rtl"), *rtl], out / "lint.log")
    top = "p06_core_register_tb"
    include = ["-I" + str(CPU / "rtl"), "-I" + str(CPU / "sim/unit")]
    run(["iverilog", "-g2012", "-s", top, *include, "-o", out / "test.vvp", *rtl, bench], out / "iverilog-build.log")
    run(["vvp", out / "test.vvp", f"+vectors={out}/vectors.txt", f"+trace={out}/iverilog-trace.csv",
         f"+summary={out}/iverilog-summary.csv"], out / "iverilog-run.log")
    run(["verilator", "--binary", "--timing", "--assert", "-j", "4", "--top-module", top,
         "--Mdir", out / "obj", "-o", "core-test", *include, *rtl, bench], out / "verilator-build.log", timeout=600)
    run([out / "obj/core-test", f"+vectors={out}/vectors.txt", f"+trace={out}/verilator-trace.csv",
         f"+summary={out}/verilator-summary.csv"], out / "verilator-run.log")
    for artifact in ["trace.csv", "summary.csv"]:
        assert (out / ("iverilog-" + artifact)).read_bytes() == (out / ("verilator-" + artifact)).read_bytes(), f"Dual-simulator disagreement: {artifact}"
    bad = (out / "vectors.txt").read_text().splitlines()
    fields = bad[0].split(); fields[8] = f"{int(fields[8], 16) ^ 1:032x}"
    bad[0] = " ".join(fields)
    (out / "negative-vectors.txt").write_text("\n".join(bad) + "\n")
    negative = subprocess.run(["vvp", str(out / "test.vvp"), f"+vectors={out}/negative-vectors.txt",
                               f"+trace={out}/negative-trace.csv", f"+summary={out}/negative-summary.csv"],
                              cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30)
    (out / "negative-run.log").write_text(negative.stdout)
    assert negative.returncode != 0 and "probe result mismatch" in negative.stdout
    summaries = list(csv.DictReader((out / "iverilog-summary.csv").open()))
    assert len(summaries) == count
    ranges = {}
    for row in summaries:
        duration = int(row["retire_edge"]) - int(row["start_edge"])
        key = f'form{row["form"]}/ready{row["ready_mode"]}'
        ranges.setdefault(key, []).append(duration)
    ranges = {k: {"min_fabric_edges": min(v), "max_fabric_edges": max(v)} for k, v in ranges.items()}
    assert before == {p.relative_to(ROOT).as_posix(): sha(p) for p in inputs}
    receipt = {"status": "P06_FULL_CPU_REGISTER_PROBE_PASS", "cases": count,
               "tool_versions": versions, "negative_control": {"expected_GPR_bit_flipped": True,
                   "returncode": negative.returncode, "reason": "probe result mismatch"},
               "sources_sha256": before, "dual_simulator_trace_equal": True,
               "intervals": ranges, "artifacts_sha256": {p.name: sha(p) for p in out.iterdir() if p.is_file()},
               "scope": "Full functional CPU register execution, not historical timing or FPGA fit"}
    (out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"status": receipt["status"], "cases": count, "intervals": ranges}, indent=2))


if __name__ == "__main__":
    main()
