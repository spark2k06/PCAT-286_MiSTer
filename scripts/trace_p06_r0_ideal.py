#!/usr/bin/env python3
"""Trace exact T286REF kernels on the production CPU with immediate ideal RAM.

Diagnostic only: preserve RTL/vendor files and derive bytes and original kernel
locations from an unchanged assembly of SW/CPUTIME/t286ref.asm. Physical fabric
is 50 MHz; reset-applied CPU profiles are 20 and 25 MHz. Both simulators must
agree on the complete passive trace and architectural result.
"""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
TOP = "spk286_r0_profile_trace_tb"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command, log, timeout=180):
    started = time.monotonic()
    with log.open("w") as stream:
        proc = subprocess.Popen(list(map(str, command)), cwd=ROOT, stdout=stream,
                                stderr=subprocess.STDOUT, start_new_session=True)
        try:
            code = proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL); proc.wait()
            raise RuntimeError("Hard timeout: " + str(log)) from None
    if code:
        raise RuntimeError(f"Command failed ({code}): {log}")
    return round(time.monotonic()-started, 3)


def sources():
    cpu = ROOT / "vendor/spk286"
    names = ["microcode/generated/spk286_microcode_pkg.sv",
             "microcode/generated/spk286_microcode_rom.sv",
             "microcode/generated/spk286_microcode_sync_rom.sv",
             "rtl/spk286_protected_pkg.sv", "rtl/spk286_tss_pkg.sv"]
    paths = [cpu / name for name in names]
    return paths + [p for p in sorted((cpu / "rtl").glob("*.sv")) if p not in paths] + [
        ROOT / "rtl/spk286_integration/spk286_machine_cpu.sv",
        ROOT / "rtl/spk286_integration/spk286_at_cpu_profile.sv",
        ROOT / "sim/spk286_timing" / (TOP + ".sv")]


def kernels(listing, binary):
    lines = listing.splitlines()
    result = {}
    for name, next_name in (("baseline", "r0"), ("r0", "b0")):
        start_line = next(i for i, line in enumerate(lines) if re.search(r"\bkernel_" + name + r":", line))
        end_line = next(i for i, line in enumerate(lines) if re.search(r"\bkernel_" + next_name + r":", line))
        starts = [int(m[1], 16) for line in lines[start_line:end_line]
                  if (m := re.match(r"\s*\d+\s+([0-9A-F]{8})\s+", line))]
        end = next(int(m[1], 16) for line in lines[end_line:]
                   if (m := re.match(r"\s*\d+\s+([0-9A-F]{8})\s+", line)))
        begin = starts[0]
        result[name] = {"offset": begin, "ip": begin + 256,
                        "bytes": binary[begin:end].hex(), "length": end-begin}
    return result


def build_program(out, loops, kernel):
    """Shared image builder for ideal/composed traces; no production mutations.

    Returns segment_hex (CS106E = 4206 decimal), ROM64K reset vector, sparse physical RAM hex,
    a physical-byte JSON map and independently calculated architectural results.
    """
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    binary, listing = out / "T286REF.COM", out / "T286REF.lst"
    if not binary.exists() or not listing.exists():
        run(["nasm", "-f", "bin", "-l", listing, "SW/CPUTIME/t286ref.asm", "-o", binary], out / "nasm.log")
    original = binary.read_bytes()
    info = kernels(listing.read_text(), original)
    if info["baseline"]["bytes"] != "e2fec3" or info["r0"]["bytes"] != "01d831fa83c30181f7aa55e2f3c3":
        raise RuntimeError("Original T286REF kernel bytes changed; review rather than normalize")
    if loops not in (32, 256) or kernel not in ("baseline", "r0"):
        raise ValueError("Only the original baseline/R0 with 32/256 fixed iterations")
    image = bytearray([0xF4] * 65536)
    image[256:256+len(original)] = original
    # CLI; MOV SP,FF00; AX/BX/DX/DI/CX matching T286REF setup; CALL; HLT.
    bootstrap = bytearray.fromhex("fabc00ffb83412bb7856babc9abff0deb9")
    bootstrap += loops.to_bytes(2, "little")
    call_ip = 0x40 + len(bootstrap)
    displacement = (info[kernel]["ip"] - (call_ip + 3)) & 65535
    bootstrap += b"\xE8" + displacement.to_bytes(2, "little") + b"\xF4"
    image[0x40:0x40+len(bootstrap)] = bootstrap
    prefix = f"{kernel}-{loops}"
    segment = out / (prefix + ".hex")
    segment.write_text("\n".join(f"{byte:02x}" for byte in image) + "\n")
    reset_vector = bytes.fromhex("ea40006e10")
    rom = bytearray([0xF4] * 65536); rom[0xFFF0:0xFFF5] = reset_vector
    rom_path = out / (prefix + "-rom64.hex")
    rom_path.write_text("\n".join(f"{byte:02x}" for byte in rom) + "\n")
    sparse_ram = out / (prefix + "-ram-physical.hex")
    # The composed peer initializes its remaining RAM to zero before loading.
    sparse_ram.write_text("@0106e0\n" + "\n".join(f"{byte:02x}" for byte in image) + "\n")
    physical = {f"{0x106e0+256+i:06x}": value for i, value in enumerate(original)}
    physical.update({f"{0x106e0+0x40+i:06x}": value for i, value in enumerate(bootstrap)})
    physical.update({f"{0xFFFFF0+i:06x}": value for i, value in enumerate(reset_vector)})
    expected = {"ax": ((0x1234 + loops*0x5678 + loops*(loops-1)//2) & 65535)
                       if kernel == "r0" else 0x1234,
                "cx": 0, "dx": 0x9ABC, "bx": (0x5678 + (loops if kernel == "r0" else 0)) & 65535,
                "di": 0xDEF0, "sp": 0xFF00}
    map_path = out / (prefix + "-physical-map.json")
    map_path.write_text(json.dumps({"cs": 0x106E, "entry_ip": 0x40,
        "kernel": kernel, "loops": loops, "kernel_info": info[kernel],
        "byte_map": physical, "default_other_rom_byte": 0xF4,
        "default_other_ram_byte": 0, "expected_gpr": expected}, indent=2) + "\n")
    return {"segment_hex": segment, "rom_hex": rom_path, "ram_hex": sparse_ram,
            "physical_map_json": map_path, "kernel_ip": info[kernel]["ip"],
            "kernel_length": info[kernel]["length"], "kernel_info": info,
            "expected_gpr": expected, "original_com_sha256": sha(binary)}


def compare_traces(left_path, right_path):
    """Keep raw four-state traces and reject every applicable signal mismatch.

    Before the first valid queue byte, the unused queue head is uninitialized
    in Icarus but zero in Verilator. Only that head and its combinational timing
    metadata may differ while there is no interval/body/consumption. No CPU input
    or architectural state is normalized, and all executed instructions compare.
    """
    with left_path.open() as stream: left = list(csv.DictReader(stream))
    with right_path.open() as stream: right = list(csv.DictReader(stream))
    if len(left) != len(right): raise RuntimeError("Trace length mismatch")
    differences = []
    started = False
    allowed = {"queue_byte", "metadata_valid", "metadata_clocks", "scheduled"}
    for a, b in zip(left, right):
        if a["consume_valid"] == "1" or b["consume_valid"] == "1": started = True
        delta = {name: [a[name], b[name]] for name in a if a[name] != b[name]}
        if not delta: continue
        empty_idle = all(row[field] == "0" for row in (a, b)
                         for field in ("in_kernel", "start_interval", "start_body",
                                       "body_active", "opcode_start", "consume_valid"))
        if started or not empty_idle or not set(delta) <= allowed:
            raise RuntimeError(f"Applicable trace disagreement edge {a['edge']}: {delta}")
        differences.append({"edge": int(a["edge"]), "unused_startup_fields": delta})
    if len(differences) > 3: raise RuntimeError("Unexpected extended uninitialized startup")
    return {"rows": len(left), "all_applicable_fields_identical": True,
            "raw_traces_preserved": True, "empty_queue_startup_differences": differences}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    if out.exists(): raise RuntimeError("Fresh output directory required")
    out.mkdir(parents=True)
    src = sources()
    includes = [ROOT / p for p in ("rtl/spk286_timing/spk286_instruction_timing.sv",
        "rtl/spk286_timing/spk286_instruction_schedule.sv",
        "vendor/spk286/rtl/timed/spk286_profiled.sv",
        "vendor/spk286/rtl/timed/spk286_profiled_events.sv", "SW/CPUTIME/t286ref.asm")]
    inputs = {p.relative_to(ROOT).as_posix(): sha(p) for p in src + includes + [Path(__file__)]}
    images = {}
    for kind in ("baseline", "r0"):
        for iterations in (32, 256):
            program = build_program(out, iterations, kind)
            images[(kind, iterations)] = program["segment_hex"]
            kernel_info = program["kernel_info"]
    receipt = {"status": "RUNNING", "source_sha256": inputs,
        "original_com_sha256": program["original_com_sha256"], "kernels": kernel_info,
        "scope": "Immediate READY ideal RAM, unmodified production CPU/profile; "
                 "exact original kernel bytes/locations and CS106E (4206 decimal). Real-mode reset "
                 "bootstrap replaces DOS/PIT instrumentation. No PCAT bus timing "
                 "or hardware calibration claim.", "runs": [], "comparisons": []}
    receipt_path = out / "receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
    for simulator in ("iverilog", "verilator"):
        if simulator == "iverilog":
            executable = out / "test_iv"
            command = ["iverilog", "-g2012", "-I.", "-s", TOP, "-o", executable] + src
            execute = ["vvp", executable]
        else:
            build = out / "verilator-obj"
            command = ["verilator", "--binary", "--timing", "--assert", "-I.", "--top-module",
                       TOP, "-Wno-fatal", "-j", "2", "--Mdir", build, "-o", "test_vlt"] + src
            execute = [build / "test_vlt"]
        run(command, out / (simulator + "-build.log"))
        for iterations in (32, 256):
            for profile in (6, 7):
                for kind in ("baseline", "r0"):
                    name = f"{simulator}-p{profile}-{kind}-{iterations}"
                    trace = out / (name + ".csv"); log = out / (name + ".log")
                    run(execute + [f"+PROFILE={profile}", f"+LOOPS={iterations}",
                        f"+KERNEL_IP={kernel_info[kind]['ip']}",
                        f"+KERNEL_LENGTH={kernel_info[kind]['length']}", f"+KIND={kind}",
                        f"+IMAGE={images[(kind, iterations)]}", f"+TRACE={trace}"], log, timeout=45)
                    marker = next(line for line in log.read_text().splitlines() if line.startswith("P06_R0_IDEAL_PASS "))
                    values = dict(re.findall(r"(\w+)=(\S+)", marker))
                    receipt["runs"].append({"simulator": simulator, **values,
                                           "trace_sha256": sha(trace), "log_sha256": sha(log)})
                    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
                    print(marker, flush=True)
    for profile in (6, 7):
        for kind in ("baseline", "r0"):
            for iterations in (32, 256):
                pair = [item for item in receipt["runs"] if int(item["profile"]) == profile and
                        item["kind"] == kind and int(item["iterations"]) == iterations]
                if len(pair) != 2: raise RuntimeError("Missing paired simulator run")
                fields = ("start", "end", "fabric_clocks", "instructions", "extensions", "kernel_ip", "kernel_length")
                if any(pair[0][field] != pair[1][field] for field in fields):
                    raise RuntimeError("Simulator measurement disagreement")
                name = f"p{profile}-{kind}-{iterations}.csv"
                comparison = compare_traces(out / ("iverilog-" + name), out / ("verilator-" + name))
                receipt["comparisons"].append({"profile": profile, "kind": kind,
                                               "iterations": iterations, **comparison})
    for relative, digest in inputs.items():
        if sha(ROOT / relative) != digest: raise RuntimeError("Source changed: " + relative)
    receipt["status"] = "P06_R0_IDEAL_DUAL_TRACE_PASS"
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
    print(receipt["status"], flush=True)


if __name__ == "__main__": main()
