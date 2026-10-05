#!/usr/bin/env python3
"""Source-frozen exact T286REF M0 on ideal RAM and the production PCAT chain.

Run in WSL. The previous version replaces only the CPU/fetch/profile files
changed by READY chaining; motherboard sources and workload are identical.
All observed values are pre-update fabric-edge samples. No production writes.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
IDEAL_TOP = "spk286_m0_profile_trace_tb"
PCAT_TOP = "spk286_m0_pcat_trace_tb"
CPU_FILES = ("vendor/spk286/rtl/spk286.sv", "vendor/spk286/rtl/spk286_fetch.sv",
             "vendor/spk286/rtl/timed/spk286_profiled.sv")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, data):
    path.write_text(json.dumps(data, indent=2) + "\n")


def run(command, cwd, log, timeout=600):
    started = time.monotonic()
    with log.open("w") as stream:
        proc = subprocess.Popen(list(map(str, command)), cwd=cwd, stdout=stream,
                                stderr=subprocess.STDOUT, start_new_session=True)
        try:
            code = proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait()
            raise RuntimeError("Hard timeout: " + str(log)) from None
    duration = round(time.monotonic() - started, 3)
    print(f"COMMAND seconds={duration} exit={code} log={log}", flush=True)
    if code:
        raise RuntimeError(f"Command failed ({code}): {log}")
    return duration


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def freeze(out, previous_ref):
    current = out / "current-source"
    current.mkdir()
    # Include complete small RTL directories so quoted root/local includes and
    # text-loaded video ROM files are preserved without transitive guesswork.
    dirs = ("rtl", "sys", "vendor/spk286/rtl", "vendor/spk286/microcode/generated")
    for name in dirs:
        shutil.copytree(ROOT / name, current / name)
    names = ("PCAT-286.sv", "scripts/test_at_machine_boundary.sh",
             "scripts/trace_p06_r0_ideal.py", "scripts/trace_p06_r0_pcat.py",
             "scripts/trace_p06_m0_diagnosis.py", "SW/CPUTIME/t286ref.asm",
             "sim/spk286_timing/spk286_r0_profile_trace_tb.sv",
             "sim/spk286_integration/spk286_at_machine_tb.sv",
             "sim/spk286_integration/spk286_at_machine_pic_model.sv",
             "sim/spk286_integration/dpram_model.sv")
    for name in names:
        target = current / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, target)
    hashes = {p.relative_to(current).as_posix(): sha(p)
              for p in sorted(current.rglob("*")) if p.is_file()}
    for name, digest in hashes.items():
        if sha(ROOT / name) != digest:
            raise RuntimeError("Source drift during freeze: " + name)
    previous = out / "previous-source"
    shutil.copytree(current, previous)
    for name in CPU_FILES:
        (previous / name).write_bytes(subprocess.check_output(
            ["git", "show", previous_ref + ":" + name], cwd=ROOT))
    previous_hashes = {p.relative_to(previous).as_posix(): sha(p)
                       for p in sorted(previous.rglob("*")) if p.is_file()}
    differences = {name: {"current": digest, "previous": previous_hashes[name]}
                   for name, digest in hashes.items() if previous_hashes[name] != digest}
    if set(differences) != set(CPU_FILES):
        raise RuntimeError("Unexpected CPU comparison boundary")
    binding = {"head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT,
               text=True).strip(), "previous_ref": previous_ref,
               "current_sha256": hashes, "previous_sha256": previous_hashes,
               "differences": differences}
    save(out / "source-binding.json", binding)
    return current, previous, binding


def symbol_offset(listing, symbol):
    lines = listing.splitlines()
    start = next(i for i, line in enumerate(lines)
                 if re.search(r"\b" + re.escape(symbol) + r"(?:\s|:)", line))
    return next(int(m[1], 16) for line in lines[start:]
                if (m := re.match(r"\s*\d+\s+([0-9A-F]{8})\s+", line)))


def build_program(root, out, kind):
    binary, listing = out / "T286REF.COM", out / "T286REF.lst"
    if not binary.exists():
        run(["nasm", "-f", "bin", "-l", listing, root / "SW/CPUTIME/t286ref.asm",
             "-o", binary], root, out / "nasm.log")
    original = binary.read_bytes()
    text = listing.read_text()
    # Find labels by their assembly source field, excluding earlier references.
    def label(name):
        lines = text.splitlines()
        at = next(i for i, line in enumerate(lines) if re.search(r"\b" + name + r":\s*$", line))
        return next(int(m[1], 16) for line in lines[at:]
                    if (m := re.match(r"\s*\d+\s+([0-9A-F]{8})\s+", line)))
    begins = {name: label("kernel_" + name) for name in ("baseline", "r0", "m0")}
    ends = {"baseline": begins["r0"], "m0": label("emit_case_kind")}
    data = next(int(m[1], 16) for line in text.splitlines()
                if "data_words dw" in line and
                (m := re.match(r"\s*\d+\s+([0-9A-F]{8})\s+", line))) + 256
    start, end = begins[kind], ends[kind]
    kernel = original[start:end]
    expected_m0 = (b"\xA1" + data.to_bytes(2, "little") + b"\x03\x06" +
                   (data + 2).to_bytes(2, "little") + b"\xA3" +
                   (data + 4).to_bytes(2, "little") + b"\x81\x36" +
                   (data + 6).to_bytes(2, "little") + bytes.fromhex("5a5ae2eec3"))
    if kernel != (bytes.fromhex("e2fec3") if kind == "baseline" else expected_m0):
        raise RuntimeError("Original M0/baseline kernel bytes changed: " + kernel.hex())
    image = bytearray([0xF4] * 65536)
    image[256:256 + len(original)] = original
    # CLI; CS -> DS; SP=FF00 (SS reset=0); original GPR setup; CX=256; CALL.
    boot = bytearray.fromhex("fa0e1fbc00ffb83412bb7856babc9abff0deb90001")
    call_ip = 0x40 + len(boot)
    boot += b"\xE8" + ((start + 256 - call_ip - 3) & 65535).to_bytes(2, "little") + b"\xF4"
    image[0x40:0x40 + len(boot)] = boot
    segment = out / (kind + "-256.hex")
    segment.write_text("\n".join(f"{b:02x}" for b in image) + "\n")
    ram = out / (kind + "-256-ram.hex")
    ram.write_text("@0106e0\n" + segment.read_text())
    rom = bytearray([0xF4] * 65536)
    rom[0xFFF0:0xFFF5] = bytes.fromhex("ea40006e10")
    rom_file = out / (kind + "-256.rom")
    rom_file.write_bytes(rom)
    info = {"kernel_ip": start + 256, "kernel_length": end - start,
            "kernel_bytes": kernel.hex(), "data_offset": data, "loops": 256,
            "cs": 0x106E, "ds": 0x106E, "initial_words": [0x1234, 0x5678, 0, 0x3C3C],
            "expected_words": [0x1234, 0x5678, 0x68AC if kind == "m0" else 0, 0x3C3C],
            "expected_ax": 0x68AC if kind == "m0" else 0x1234,
            "expected_flags": 6 if kind == "m0" else 2,
            "original_com_sha256": sha(binary), "segment_sha256": sha(segment),
            "rom_sha256": sha(rom_file)}
    save(out / (kind + "-256-program.json"), info)
    return {**info, "segment": segment, "ram": ram, "rom": rom_file}


def generate_benches(root, out):
    ideal_module = module(root / "scripts/trace_p06_r0_ideal.py", "trace_p06_r0_ideal")
    # The shared generator imports its sibling by name.
    import sys
    sys.modules["trace_p06_r0_ideal"] = ideal_module
    pcat_module = module(root / "scripts/trace_p06_r0_pcat.py", "trace_p06_r0_pcat")
    ideal_module.ROOT = pcat_module.ROOT = root
    composed = pcat_module.generate_bench(out)
    original = (root / "sim/spk286_timing/spk286_r0_profile_trace_tb.sv").read_text()
    def adapt(text, pcat):
        text = text.replace("spk286_r0_profile_trace_tb", IDEAL_TOP).replace(
            "spk286_r0_pcat_trace_tb", PCAT_TOP).replace("P06_R0_", "P06_M0_")
        text = text.replace('kind == "r0"', 'kind == "m0"').replace('kind != "r0"', 'kind != "m0"')
        text = text.replace('(profile_arg != 6 && profile_arg != 7)',
                            '(profile_arg != 1 && profile_arg != 2 && profile_arg != 4)')
        text = text.replace('(selected_cpu_profile != 6 && selected_cpu_profile != 7)',
                            '(selected_cpu_profile != 1 && selected_cpu_profile != 2 && selected_cpu_profile != 4)')
        text = text.replace('(iterations != 32 && iterations != 256)', '(iterations != 256)')
        text = text.replace('(16\'h1234 + iterations * 16\'h5678 + iterations * (iterations - 1) / 2) & 65535', "16'h68AC")
        text = text.replace("16'(16'h5678 + (kind == \"m0\" ? iterations : 0))", "16'h5678")
        text = text.replace("integer iterations, kernel_ip, kernel_length, trace_fd, backend_fd;",
                            "integer iterations, kernel_ip, kernel_length, trace_fd, backend_fd, data_offset;")
        text = text.replace("integer profile_arg, iterations, kernel_ip, kernel_length, trace_fd;",
                            "integer profile_arg, iterations, kernel_ip, kernel_length, trace_fd, data_offset;")
        text = text.replace('if (!$value$plusargs("', 'if (!$value$plusargs("DATA_OFFSET=%d", data_offset) ||\n            !$value$plusargs("', 1)
        cpu = "dut.u_cpu.cpu" if pcat else "u_cpu.cpu"
        extra_names = "memory_request,memory_request_ready,memory_write,memory_response_valid,memory_response_ready,operand_request,operand_done,operand_service_wait,biu_data_active,biu_owner_valid,biu_owner,fetch_active,fetch_request,fetch_request_ready,fetch_response_count,stream_restart,flags"
        text = text.replace('refill_accept,gpr"', 'refill_accept,gpr,' + extra_names + '"')
        text = text.replace('%032h"', '%032h,' + ','.join(['%0d'] * 16) + ',%04h"')
        extra = ["memory_request", "memory_request_ready", "memory_write", "memory_response_valid",
                 "memory_response_ready", "operand_request", "operand_done", "operand_service_wait",
                 "biu.data_active_q", "biu.owner_valid_q", "biu.owner_q", "fetch.active_q",
                 "fetch_request_internal", "fetch_request_ready_internal", "fetch_response_count", "stream_restart"]
        text = text.replace("                    debug_gpr);", "                    debug_gpr,\n                    " +
                            ", ".join(cpu + "." + name for name in extra) + ", " + cpu + ".debug_flags);")
        memory = "base_ram[24'h0106E0+data_offset" if pcat else "code[data_offset"
        checks = "\n".join("                if ({" + memory + f"+{i*2+1}], " + memory + f"+{i*2}]}} !== " +
                           ("(kind == \"m0\" ? 16'h68AC : 16'h0000)" if i == 2 else f"16'h{[0x1234,0x5678,0,0x3c3c][i]:04X}") +
                           f') $fatal(1,"Data word {i} mismatch");' for i in range(4))
        text = text.replace('                $display("P06_M0_',
            f"                if (kernel_retirements != iterations * (kind == \"m0\" ? 5 : 1) ||\n" +
            f"                    debug_gpr[79:64] !== 16'hFF00 ||\n" +
            f"                    {cpu}.debug_flags !== (kind == \"m0\" ? 16'h0006 : 16'h0002))\n" +
            '                    $fatal(1,"Instruction work, SP or FLAGS mismatch");\n' + checks +
            '\n                $display("P06_M0_')
        if not pcat:
            anchor = "            if (u_cpu.cpu.opcode_start"
            writes = """            if (bus_valid && bus_write && address >= 24'h0106E0 && address < 24'h0206E0) begin
                if (!address[0]) code[16'(address-24'h0106E0)] <= data_out[7:0];
                if (!bus_bhe_n) code[16'({address[23:1],1'b1}-24'h0106E0)] <= data_out[15:8];
            end
"""
            text = text.replace(anchor, writes + anchor)
        else:
            text = text.replace("fetch_active,fetch_response_fire\"", "fetch_active,fetch_response_fire,write,byte_enable,bridge_ts_admit,timing_terminal,bridge_cpu_ready,p03_fills,p03_physical_reads,posted_pending,data_hits,data_misses,physical_write,physical_command\"")
            text = text.replace('dut.u_cpu.cpu.fetch.response_fire);',
                'dut.u_cpu.cpu.fetch.response_fire, backend_write,backend_byte_enable,\n' +
                '                    dut.u_bridge.state_q == 0 && cpu_bus_valid && dut.u_bridge.timing_admit && !dut.u_bridge.drain_barrier,\n' +
                '                    dut.u_bridge.timing_terminal,dut.u_bridge.cpu_ready,\n' +
                '                    p03_fill_count,p03_physical_read_count,at_posted_write_pending,\n' +
                '                    u_at_ram_read_buffer.debug_hit_count,u_at_ram_read_buffer.debug_miss_count,posted_out_write,posted_out_command);')
            # Backend fdisplay gains twelve additional fields; CPU dump has a
            # distinct final hexadecimal GPR format and is unaffected.
            text = text.replace('%0d,%0d,%0d,%0d,%0d,%0d\",\n                    cycle,backend_valid',
                '%0d,%0d,%0d,%0d,%0d,%0d,' + ','.join(['%0d'] * 12) + '\",\n                    cycle,backend_valid')
        return text
    ideal = out / (IDEAL_TOP + ".sv")
    ideal.write_text(adapt(original, False))
    pcat = out / (PCAT_TOP + ".sv")
    pcat.write_text(adapt(composed.read_text(), True))
    composed.unlink()
    return ideal, pcat, ideal_module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--previous-ref", default="6441d8d")
    args = parser.parse_args()
    out = args.output.resolve()
    if out.exists():
        raise RuntimeError("Fresh output directory required")
    out.mkdir(parents=True)
    current, previous, binding = freeze(out, args.previous_ref)
    programs_dir = out / "programs"
    programs_dir.mkdir()
    programs = {kind: build_program(current, programs_dir, kind) for kind in ("baseline", "m0")}
    receipt = {"status": "RUNNING", "source_binding": "source-binding.json",
               "scope": "50 MHz fabric; exact original 256-iteration M0/baseline; profiles 6/8/12.5 MHz. "
               "Ideal RAM and literal PCAT chain; AT refresh unprogrammed/disabled, owner refresh active. "
               "Behavioral SDRAM peer; no DOS/PIT/BIOS instrumentation or electrical SDRAM claims.",
               "builds": [], "runs": []}
    receipt_path = out / "receipt.json"
    save(receipt_path, receipt)
    runtime = Path(tempfile.mkdtemp(prefix="p06-m0-diagnosis-"))
    receipt["runtime_directory"] = str(runtime)
    for version, root in (("current", current), ("previous", previous)):
        version_dir = out / version
        version_dir.mkdir()
        ideal, pcat, cpu_module = generate_benches(root, version_dir)
        for path_kind, top, bench in (("ideal", IDEAL_TOP, ideal), ("pcat", PCAT_TOP, pcat)):
            src = cpu_module.sources()[:-1]
            flags = []
            if path_kind == "pcat":
                runner = (root / "scripts/test_at_machine_boundary.sh").read_text()
                extra = re.findall(r"^  ((?:rtl|sys|sim)/\S+\.(?:sv|v))$", runner, re.M)
                src += [root / p for p in extra]
                src += sorted((root / "rtl/video").glob("*.v")) + sorted((root / "rtl/video").glob("*.sv"))
                src += [root / "sim/spk286_integration/spk286_at_machine_pic_model.sv"]
                src += [root / ("rtl/spk286_integration/" + name + ".sv") for name in
                        ("spk286_at_sdram_read_buffer", "spk286_at_sdram_data_buffer", "spk286_at_posted_write_buffer")]
                flags = ["-Irtl/KFPC-XT/HDL/KF8253/HDL", "-Irtl/KFPC-XT/HDL/KF8259/HDL",
                         "-DSPK286_AT_SIM_MODEL", "-DAT_MACHINE_PIC_MODEL"]
            src = list(dict.fromkeys(src)) + [bench]
            obj = runtime / version / path_kind
            obj.mkdir(parents=True)
            command = ["verilator", "--binary", "--timing", "--assert", "-j", "2", "-I.",
                       "--top-module", top, "-Wno-fatal", "--Mdir", obj, "-o", "trace_m0"] + flags + src
            duration = run(command, root, version_dir / (path_kind + "-build.log"), 600)
            receipt["builds"].append({"version": version, "path": path_kind, "seconds": duration,
                "bench_sha256": sha(bench), "command": list(map(str, command)),
                "binary_sha256": sha(obj / "trace_m0"),
                "compiled_source_sha256": {str(p.relative_to(root)) if p.is_relative_to(root) else str(p): sha(p) for p in src}})
            save(receipt_path, receipt)
            for profile in (1, 2, 4):
                for kind, program in programs.items():
                    name = f"{path_kind}-p{profile}-{kind}-256"
                    log, trace, backend = [version_dir / (name + ext) for ext in (".log", ".csv", "-backend.csv")]
                    execute = [obj / "trace_m0", f"+LOOPS=256", f"+KIND={kind}",
                               f"+KERNEL_IP={program['kernel_ip']}", f"+KERNEL_LENGTH={program['kernel_length']}",
                               f"+DATA_OFFSET={program['data_offset']}", f"+TRACE={trace}"]
                    if path_kind == "ideal":
                        execute += [f"+PROFILE={profile}", f"+IMAGE={program['segment']}"]
                    else:
                        execute += [f"+CPU_PROFILE={profile}", f"+ROM={program['rom']}",
                                    f"+RAM={program['ram']}", f"+BACKEND_TRACE={backend}"]
                    duration = run(execute, root, log, 90)
                    marker = next(line for line in log.read_text().splitlines() if line.startswith("P06_M0_"))
                    values = dict(re.findall(r"(\w+)=(\S+)", marker))
                    receipt["runs"].append({"version": version, "path": path_kind, **values,
                        "seconds": duration, "trace": str(trace.relative_to(out)),
                        "trace_sha256": sha(trace), "log_sha256": sha(log),
                        **({"backend": str(backend.relative_to(out)), "backend_sha256": sha(backend)} if backend.exists() else {})})
                    save(receipt_path, receipt)
                    print(version, path_kind, marker, flush=True)
    for version, root in (("current", current), ("previous", previous)):
        for name, digest in binding[version + "_sha256"].items():
            if sha(root / name) != digest:
                raise RuntimeError("Frozen source drift: " + version + "/" + name)
    receipt["status"] = "P06_M0_SOURCE_FROZEN_TRACE_PASS"
    save(receipt_path, receipt)
    print(receipt["status"], flush=True)


if __name__ == "__main__":
    main()
