#!/usr/bin/env python3
"""Sweep the natural profile epoch on frozen exact M0 CPU/PCAT comparisons.

Only the bench releases the profile generator's input reset 0..24 fabric edges
before CPU/memory reset. Its counter advances naturally using unchanged RTL.
CPU/memory stay in reset until the cold run starts. No register is forced,
and no measured wait, prefetch response or workload byte is changed.
"""
import argparse
import gzip
import json
import math
from pathlib import Path
import re
import shutil
import tempfile

from trace_p06_m0_diagnosis import run, save, sha

TOP = "spk286_m0_phase_trace_tb"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frozen", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--profile", type=int, default=2, choices=(1, 2, 4))
    parser.add_argument("--prelude-sweep", action="store_true",
                        help="Sweep 0..24 executed NOPs before CALL with epoch offset zero")
    args = parser.parse_args()
    frozen, out = args.frozen.resolve(), args.output.resolve()
    if out.exists():
        raise RuntimeError("Fresh output directory required")
    out.mkdir(parents=True)
    shutil.copy2(Path(__file__), out / "runner.py")
    original_receipt = json.loads((frozen / "receipt.json").read_text())
    if original_receipt["status"] != "P06_M0_SOURCE_FROZEN_TRACE_PASS":
        raise RuntimeError("Completed source-frozen fixture required")
    binding = json.loads((frozen / "source-binding.json").read_text())
    increment = {1: 12, 2: 16, 4: 25}[args.profile]
    accumulator_period = 50 // math.gcd(increment, 50)
    carries = increment * accumulator_period // 50
    period = accumulator_period * (1 if carries % 2 == 0 else 2)
    receipt = {"status": "RUNNING", "frozen_receipt_sha256": sha(frozen / "receipt.json"),
        "source_binding_sha256": sha(frozen / "source-binding.json"),
        "runner_sha256": sha(Path(__file__)), "profile": args.profile,
        "search_control": "NOP prelude length" if args.prelude_sweep else "generator epoch offset",
        "phase_increment": increment, "full_generator_period": period,
        "control": "Fresh CPU/memory reset per run resets PCAT buffers; AT refresh disabled, owner refresh active. "
                   "Bench instantiates the unmodified production generator with separately released reset "
                   "and connects its boundary to the machine timing_cpu_boundary wire, "
                   "which advances naturally for phase edges while CPU/memory remain in reset. "
                   "execute_enable remains asserted; no RTL register is forced. "
                   "Exact M0 kernel/location/data; 32 iterations for search, 256 for extrema confirmation.",
        "builds": [], "runs": []}
    receipt_path = out / "receipt.json"
    save(receipt_path, receipt)
    programs = {}
    for loops, prelude in ((loops, prelude) for loops in (32, 256)
                           for prelude in (range(25) if args.prelude_sweep else (0,))):
        image = bytearray(int(line, 16) for line in (frozen / "programs/m0-256.hex").read_text().splitlines())
        bootstrap = image[0x40:0x80]
        if bootstrap.count(bytes.fromhex("b90001e8")) != 1:
            raise RuntimeError("Bootstrap count anchor changed")
        at = 0x40 + bootstrap.index(bytes.fromhex("b90001e8")) + 1
        image[at:at+2] = loops.to_bytes(2, "little")
        info = json.loads((frozen / "programs/m0-256-program.json").read_text())
        call_ip = at + 2
        if prelude:
            boot = image[0x40:call_ip] + bytes([0x90] * prelude)
            new_call_ip = call_ip + prelude
            boot += b"\xE8" + ((info["kernel_ip"] - new_call_ip - 3) & 65535).to_bytes(2, "little") + b"\xF4"
            image[0x40:0x40+len(boot)] = boot
        ram = out / f"m0-{loops}-nop{prelude}-ram.hex"
        ram.write_text("@0106e0\n" + "\n".join(f"{b:02x}" for b in image) + "\n")
        if image[info["kernel_ip"]:info["kernel_ip"]+info["kernel_length"]].hex() != info["kernel_bytes"]:
            raise RuntimeError("M0 bytes changed during phase setup")
        programs[(loops, prelude)] = {**info, "loops": loops, "prelude_NOPs": prelude, "ram": ram,
                           "rom": frozen / "programs/m0-256.rom", "ram_sha256": sha(ram)}
    save(out / "programs.json", {str(k): {name: str(value) if isinstance(value, Path) else value
        for name, value in program.items()} for k, program in programs.items()})
    runtime = Path(tempfile.mkdtemp(prefix="p06-m0-phase-"))
    binaries = {}
    for version in ("current", "previous"):
        source = frozen / (version + "-source")
        recipe = next(b for b in original_receipt["builds"] if b["version"] == version and b["path"] == "pcat")
        old_bench = frozen / version / "spk286_m0_pcat_trace_tb.sv"
        bench_text = old_bench.read_text().replace("spk286_m0_pcat_trace_tb", TOP)
        bench_text = bench_text.replace("integer iterations, kernel_ip, kernel_length, trace_fd, backend_fd, data_offset;",
            "logic profile_epoch_reset = 1;\n" +
            "    wire [2:0] epoch_profile;\n" +
            "    wire epoch_pending, epoch_historical, epoch_phase_enable, epoch_phase_two, epoch_boundary;\n" +
            "    spk286_at_cpu_profile u_epoch_profile (\n" +
            "        .clk, .reset(profile_epoch_reset), .requested(3'(selected_cpu_profile)),\n" +
            "        .active(epoch_profile), .pending(epoch_pending), .historical(epoch_historical),\n" +
            "        .phase_enable(epoch_phase_enable), .phase_two(epoch_phase_two), .cpu_boundary(epoch_boundary)\n" +
            "    );\n" +
            "    always @(*) force dut.timing_cpu_boundary = epoch_boundary;\n" +
            "    integer iterations, kernel_ip, kernel_length, trace_fd, backend_fd, data_offset, start_delay;")
        bench_text = bench_text.replace("    initial begin : trace_run\n",
            '    initial begin : trace_run\n' +
            '        if (!$value$plusargs("START_DELAY=%d", start_delay)) $fatal(1,"Missing startup phase");\n')
        bench_text = bench_text.replace("(iterations != 256)", "(iterations != 32 && iterations != 256)")
        bench_text = bench_text.replace("        reset = 0;\n        #1;",
            "        profile_epoch_reset = 0;\n        repeat(start_delay) @(negedge clk);\n        reset = 0;\n        #1;")
        bench_text = bench_text.replace("                first_edge = cycle;",
            '                $display("P06_M0_EPOCH_START profile=%0d phase_delay=%0d accumulator=%0d parity=%0d boundary=%0d",\n' +
            '                    epoch_profile,start_delay,u_epoch_profile.phase_accumulator_q,\n' +
            '                    u_epoch_profile.phase_parity_q,dut.timing_cpu_boundary);\n' +
            '                first_edge = cycle;')
        bench_text = bench_text.replace('physical_write,physical_command"',
            'physical_write,physical_command,epoch_accumulator,epoch_parity"')
        bench_text = bench_text.replace('posted_out_write,posted_out_command);',
            'posted_out_write,posted_out_command,u_epoch_profile.phase_accumulator_q,u_epoch_profile.phase_parity_q);')
        bench_text = bench_text.replace('%0d,%0d,%0d,%0d,%0d,%0d",\n                    cycle,backend_valid',
            '%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d",\n                    cycle,backend_valid')
        bench_text = bench_text.replace("            cycle = cycle + 1;",
            '            if (epoch_profile !== applied_cpu_profile || epoch_pending || !epoch_historical ||\n' +
            '                dut.timing_cpu_boundary !== epoch_boundary)\n' +
            '                $fatal(1,"Profile epoch wiring mismatch: applied=%0d epoch=%0d pending=%0d historical=%0d boundary=%0d actual=%0d",\n' +
            '                    applied_cpu_profile,epoch_profile,epoch_pending,epoch_historical,epoch_boundary,dut.timing_cpu_boundary);\n' +
            '            cycle = cycle + 1;')
        bench = out / (version + "-" + TOP + ".sv")
        bench.write_text(bench_text)
        obj = runtime / version
        obj.mkdir()
        command = recipe["command"][:]
        command[command.index("--top-module")+1] = TOP
        command[command.index("--Mdir")+1] = str(obj)
        command[-1] = str(bench)
        seconds = run(command, source, out / (version + "-build.log"), 600)
        binary = obj / "trace_m0"
        binaries[version] = binary
        receipt["builds"].append({"version": version, "seconds": seconds, "command": command,
                                  "bench_sha256": sha(bench), "binary_sha256": sha(binary)})
        save(receipt_path, receipt)

    def execute(version, control, loops):
        phase = 0 if args.prelude_sweep else control
        prelude = control if args.prelude_sweep else 0
        name = f"{version}-p{args.profile}-phase{phase}-nop{prelude}-m0-{loops}"
        log, trace, backend = [out / (name + suffix) for suffix in (".log", ".csv", "-backend.csv")]
        program = programs[(loops, prelude)]
        command = [binaries[version], f"+CPU_PROFILE={args.profile}", f"+LOOPS={loops}",
            "+KIND=m0", f"+START_DELAY={phase}", f"+KERNEL_IP={program['kernel_ip']}",
            f"+KERNEL_LENGTH={program['kernel_length']}", f"+DATA_OFFSET={program['data_offset']}",
            f"+TRACE={trace}", f"+BACKEND_TRACE={backend}", f"+ROM={program['rom']}", f"+RAM={program['ram']}"]
        seconds = run(command, frozen / (version + "-source"), log, 90)
        marker = next(line for line in log.read_text().splitlines() if line.startswith("P06_M0_PCAT_PASS "))
        values = dict(re.findall(r"(\w+)=(\S+)", marker))
        epoch_marker = next(line for line in log.read_text().splitlines() if line.startswith("P06_M0_EPOCH_START "))
        epoch_values = dict(re.findall(r"(\w+)=(\S+)", epoch_marker))
        if int(epoch_values["profile"]) != args.profile or int(epoch_values["phase_delay"]) != phase:
            raise RuntimeError("Generator profile/epoch control mismatch")
        item = {"version": version, "phase_delay": phase, "prelude_NOPs": prelude, **values, "seconds": seconds,
            "kernel_start_mod_period": int(values["start"]) % period,
            "kernel_epoch": epoch_values,
            "trace": trace.name, "backend": backend.name,
            "trace_sha256": sha(trace), "backend_sha256": sha(backend), "log_sha256": sha(log)}
        # Preserve the complete raw stream as deterministic gzip and unlink
        # only the two just-created trace files after successful compression.
        for field, path in (("trace", trace), ("backend", backend)):
            packed = path.with_suffix(path.suffix + ".gz")
            with path.open("rb") as incoming, packed.open("wb") as target:
                with gzip.GzipFile(fileobj=target, mode="wb", filename="", mtime=0) as outgoing:
                    shutil.copyfileobj(incoming, outgoing, 1024 * 1024)
            item[field] = packed.name
            item[field + "_gzip_sha256"] = sha(packed)
            path.unlink()
        receipt["runs"].append(item)
        save(receipt_path, receipt)
        print(name, marker, flush=True)
        return int(values["fabric_clocks"])

    search = {}
    for control in range(25 if args.prelude_sweep else period):
        search[control] = {version: execute(version, control, 32) for version in ("current", "previous")}
    confirm = {0}
    for version in ("current", "previous"):
        confirm.add(min(search, key=lambda phase: search[phase][version]))
        confirm.add(max(search, key=lambda phase: search[phase][version]))
    confirm.add(max(search, key=lambda phase: search[phase]["current"] - search[phase]["previous"]))
    confirm.add(min(search, key=lambda phase: search[phase]["current"] - search[phase]["previous"]))
    receipt["search"] = search
    receipt["kernel_epoch_coverage"] = {version: sorted({
        (int(r["kernel_epoch"]["accumulator"]), int(r["kernel_epoch"]["parity"]))
        for r in receipt["runs"] if r["version"] == version and r["iterations"] == "32"})
        for version in ("current", "previous")}
    receipt["confirmation_phases"] = sorted(confirm)
    for phase in sorted(confirm):
        for version in ("current", "previous"):
            execute(version, phase, 256)
    for version in ("current", "previous"):
        source = frozen / (version + "-source")
        for name, digest in binding[version + "_sha256"].items():
            if sha(source / name) != digest:
                raise RuntimeError("Source drift: " + version + "/" + name)
    receipt["status"] = "P06_M0_FULL_STARTUP_PHASE_SWEEP_PASS"
    save(receipt_path, receipt)
    print(receipt["status"], flush=True)


if __name__ == "__main__":
    main()
