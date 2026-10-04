#!/usr/bin/env python3
"""Trace original R0 through the production AT machine and PCAT memory chain.

Derive the bench from existing fixtures and literal PCAT instances, hash all
inputs, and keep CPU/profile/bridge RTL unchanged. The observer and executable
kernel images are shared with the immediate-RAM diagnostic. This does not run
DOS, PIT instrumentation or the full BIOS peripheral initialization.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

from trace_p06_r0_ideal import ROOT, build_program, run, sha, sources as cpu_sources

TOP = "spk286_r0_pcat_trace_tb"


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise RuntimeError("Fixture anchor changed: " + old[:100])
    return text.replace(old, new)


def generate_bench(out):
    base = (ROOT / "sim/spk286_integration/spk286_at_machine_tb.sv").read_text()
    top = (ROOT / "PCAT-286.sv").read_text()
    ideal = (ROOT / "sim/spk286_timing/spk286_r0_profile_trace_tb.sv").read_text()
    # Literal production connection block, excluding its memory-port instance:
    # the machine fixture already contains that same serialized interface.
    chain = top.split("    wire        p03_out_valid;", 1)[1]
    chain = "    wire        p03_out_valid;" + chain.split("    logic counter_clock;", 1)[0]
    port_start = chain.index("    spk286_at_mister_memory_port u_at_memory_port (")
    port_end = chain.index("    // P03 is placed below", port_start)
    chain = chain[:port_start] + chain[port_end:]
    chain = replace_once(chain, "    wire        sdram_owner_protocol_error;\n", "")
    # Startup delay only; steady-state owner timings remain the RTL defaults.
    chain = replace_once(chain, "spk286_at_mister_sdram_owner u_at_sdram_owner (",
                         "spk286_at_mister_sdram_owner #(.SDRAM_INIT_WAIT(16'd32)) u_at_sdram_owner (")
    for old, new in (("CLK_50M", "clk"), ("RESET", "reset"),
                     ("at_machine_reset | at_cpu_reset_request", "cpu_reset_request"),
                     ("at_cpu_bus_lock", "cpu_bus_lock")):
        chain = chain.replace(old, new)
    chain = "    wire physical_idle;\n" + chain
    base = replace_once(base, "module spk286_at_machine_tb;", f"module {TOP};")
    base = replace_once(base, "always #5 clk = ~clk;", "always #10 clk = ~clk;")
    owner_start = base.index("    spk286_at_mister_sdram_owner #(")
    owner_end = base.index("    spk286_at_machine dut (", owner_start)
    base = base[:owner_start] + chain + base[owner_end:]
    base = replace_once(base, "        .memory_accept(memory_accept), .memory_ready(memory_ready),",
                        "        .memory_drain_pending(at_posted_write_pending),\n"
                        "        .memory_accept(memory_accept), .memory_ready(memory_ready),")
    base = replace_once(base, "        .debug_bus_state(debug_bus_state), .refresh_count(refresh_count),",
                        "        .debug_gpr(debug_gpr),\n"
                        "        .debug_bus_state(debug_bus_state), .refresh_count(refresh_count),")
    base = base.split("    initial begin : run", 1)[0]
    # Retain the behavioral command/data peer from machine_tb. KFSDRAM
    # emits a READ command per word during logical four-word fills; each READ
    # is sampled separately here. This is not an electrical SDRAM model.
    observer = ideal.split("    always @(posedge clk) begin : observer", 1)[1]
    observer = "    always @(posedge clk) begin : observer" + observer.split("    initial begin\n", 1)[0]
    write_start = observer.index("            if (bus_valid && bus_write")
    write_end = observer.index("            if (u_cpu.cpu.opcode_start", write_start)
    observer = observer[:write_start] + observer[write_end:]
    observer = observer.replace("u_cpu.cpu", "dut.u_cpu.cpu")
    for old, new in (("active", "applied_cpu_profile"), ("cpu_boundary", "dut.timing_cpu_boundary"),
                     ("bus_valid", "cpu_bus_valid"), ("bus_status", "cpu_bus_status"),
                     ("address", "cpu_address"), ("bus_write", "cpu_bus_write"),
                     ("halted", "cpu_halted")):
        observer = re.sub(r"\b" + old + r"\b", new, observer)
    observer = replace_once(observer,
        "if (shutdown || unsupported_opcode || microcode_fault || control_error)",
        "if (cpu_shutdown || cpu_fault || protocol_error || memory_port_protocol_error || "
        "sdram_owner_protocol_error || posted_buffer_error)")
    observer = replace_once(observer, "cpu_bus_write, cpu_bus_valid, dut.u_cpu.cpu.fetch_bus_valid,",
                            "cpu_bus_write, cpu_ready, dut.u_cpu.cpu.fetch_bus_valid,")
    observer = observer.replace("P06_R0_IDEAL_PASS", "P06_R0_PCAT_PASS")
    observer = observer.replace("Bounded ideal-RAM watchdog", "Bounded PCAT watchdog")
    observer = replace_once(observer, "            if (cpu_halted) begin",
        "            if (cpu_halted && physical_idle) begin\n"
        "                if (kernel_retirements != iterations * (kind == \"r0\" ? 5 : 1) ||\n"
        "                    debug_gpr[79:64] !== 16'hFF00)\n"
        "                    $fatal(1, \"Kernel work or stack mismatch\");")
    observer = replace_once(observer, "                $fclose(trace_fd); $finish;",
        "                $display(\"P06_PCAT_CACHE hits=%0d misses=%0d fills=%0d physical_reads=%0d\",\n"
        "                         p03_hit_count,p03_miss_count,p03_fill_count,p03_physical_read_count);\n"
        "                $fclose(trace_fd); $fclose(backend_fd); $finish;")
    observer = replace_once(observer, "            cycle = cycle + 1;",
        "            cycle = cycle + 1;\n" + backend_dump())
    header = """
    wire [127:0] debug_gpr;
    integer iterations, kernel_ip, kernel_length, trace_fd, backend_fd;
    integer cycle = 0, first_edge = -1, last_edge = -1, loops_retired = 0;
    integer kernel_retirements = 0, kernel_extensions = 0;
    logic in_kernel = 0;
    string trace_path, backend_path, ram_path, kind;
"""
    # Same trace column contract as the ideal peer, except READY is real.
    trace_header = re.search(r'\$fdisplay\(trace_fd, "(edge,profile,[^"]+)"\);', ideal)[1]
    initialize = """
    initial begin : trace_run
        if (!$value$plusargs("CPU_PROFILE=%d", selected_cpu_profile) ||
            !$value$plusargs("LOOPS=%d", iterations) ||
            !$value$plusargs("KERNEL_IP=%d", kernel_ip) ||
            !$value$plusargs("KERNEL_LENGTH=%d", kernel_length) ||
            !$value$plusargs("KIND=%s", kind) ||
            !$value$plusargs("RAM=%s", ram_path) ||
            !$value$plusargs("TRACE=%s", trace_path) ||
            !$value$plusargs("BACKEND_TRACE=%s", backend_path)) $fatal(1,"Missing arguments");
        if ((selected_cpu_profile != 6 && selected_cpu_profile != 7) ||
            (iterations != 32 && iterations != 256) ||
            (kind != "baseline" && kind != "r0")) $fatal(1,"Out-of-scope run");
        // PIT/AT refresh is intentionally unprogrammed; owner SDRAM refresh
        // stays active. This isolates the CPU + common-clock memory chain.
        refresh_enable = 0;
        #1; $readmemh(ram_path,base_ram);
        trace_fd = $fopen(trace_path,"w");
        backend_fd = $fopen(backend_path,"w");
        if (!trace_fd || !backend_fd) $fatal(1,"Cannot open trace files");
        $fdisplay(trace_fd,"TRACE_HEADER");
        $fdisplay(backend_fd,"edge,valid,command,code,address,accept,ready,cpu_ready,refresh_grant,cpu_hold,p03_state,p03_hits,p03_misses,physical_accept,physical_address,physical_ready,physical_read_valid,sdram_read,bridge_deadline_miss,bridge_state,timing_active,timing_tc,admission_window,cpu_boundary,fetch_active,fetch_response_fire");
        repeat(8) @(negedge clk);
        reset = 0;
        #1;
        if (applied_cpu_profile !== 3'(selected_cpu_profile) || cpu_profile_pending)
            $fatal(1,"Profile not applied through reset");
    end
    initial begin #11_000_000; $fatal(1,"PCAT trace timeout"); end
endmodule
""".replace("TRACE_HEADER", trace_header)
    path = out / (TOP + ".sv")
    path.write_text(base + header + observer + initialize)
    return path


def backend_dump():
    # Same pre-update edge and counter as the CPU observer: no second always
    # block reading a counter that is assigned by a different active process.
    return """            if (backend_fd != 0)
                $fdisplay(backend_fd,"%0d,%0d,%0d,%0d,%06h,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%06h,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d",
                    cycle,backend_valid,backend_command_valid,backend_code_fetch,backend_address,
                    backend_accept,backend_ready,cpu_ready,refresh_grant,cpu_hold_request,
                    p03_debug_state,p03_hit_count,p03_miss_count,physical_accept,
                    posted_out_address,physical_ready,physical_read_data_valid,
                    sdram_command_read,dut.u_bridge.timing_deadline_miss,
                    dut.u_bridge.state_q,dut.u_bridge.timing_active_q,
                    dut.u_bridge.timing_tc_q,dut.u_bridge.timing_admission_window_q,
                    dut.timing_cpu_boundary,dut.u_cpu.cpu.fetch.active_q,
                    dut.u_cpu.cpu.fetch.response_fire);
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    if out.exists(): raise RuntimeError("Fresh output directory required")
    out.mkdir(parents=True)
    bench = generate_bench(out)
    # Derive the already maintained machine-fixture source list; include all
    # packages ahead of modules and use the bounded PIC model for this CLI test.
    runner = (ROOT / "scripts/test_at_machine_boundary.sh").read_text()
    extra = re.findall(r"^  ((?:rtl|sys|sim)/\S+\.(?:sv|v))$", runner, re.M)
    src = cpu_sources()[:-1] + [ROOT / p for p in extra]
    src += sorted((ROOT / "rtl/video").glob("*.v")) + sorted((ROOT / "rtl/video").glob("*.sv"))
    src += [ROOT / "sim/spk286_integration/spk286_at_machine_pic_model.sv"]
    src += [ROOT / ("rtl/spk286_integration/" + name + ".sv") for name in
            ("spk286_at_sdram_read_buffer", "spk286_at_sdram_data_buffer", "spk286_at_posted_write_buffer")]
    src = list(dict.fromkeys(src))
    guarded = src + [ROOT / p for p in (
        "PCAT-286.sv", "scripts/test_at_machine_boundary.sh", "scripts/trace_p06_r0_ideal.py",
        "sim/spk286_integration/spk286_at_machine_tb.sv", "sim/spk286_timing/spk286_r0_profile_trace_tb.sv",
        "rtl/spk286_timing/spk286_instruction_timing.sv", "rtl/spk286_timing/spk286_instruction_schedule.sv",
        "vendor/spk286/rtl/timed/spk286_profiled.sv", "vendor/spk286/rtl/timed/spk286_profiled_events.sv",
        "SW/CPUTIME/t286ref.asm")] + [Path(__file__)]
    for directory in ("vendor/spk286", "rtl/spk286_integration", "rtl/spk286_timing",
                      "rtl/KFPC-XT/HDL/KF8253/HDL", "rtl/KFPC-XT/HDL/KF8259/HDL", "rtl/video"):
        for suffix in ("*.svh", "*.vh"):
            guarded += sorted((ROOT / directory).rglob(suffix))
    inputs = {p.relative_to(ROOT).as_posix(): sha(p) for p in guarded}
    programs = {(kind, loops): build_program(out, loops, kind)
                for kind in ("baseline", "r0") for loops in (32, 256)}
    for program in programs.values():
        path = program["rom_hex"].with_suffix(".rom")
        path.write_bytes(bytes(int(line,16) for line in program["rom_hex"].read_text().splitlines()))
        program["rom_binary"] = path
    obj = out / "verilator-obj"
    run(["verilator", "--binary", "--timing", "--assert", "-j", "2", "-I.",
        "-Irtl/KFPC-XT/HDL/KF8253/HDL", "-Irtl/KFPC-XT/HDL/KF8259/HDL",
        "-DSPK286_AT_SIM_MODEL", "-DAT_MACHINE_PIC_MODEL", "--top-module", TOP,
        "-Wno-fatal", "--Mdir", obj, "-o", "trace_pcat"] + src + [bench],
        out / "verilator-build.log", timeout=600)
    receipt = {"status": "RUNNING", "source_sha256": inputs,
               "generated_bench_sha256": sha(bench),
               "scope": "Unmodified production CPU, AT machine and literal PCAT P03(512)/data/posted/owner chain. "
                        "Exact NASM kernels at CS106E original IP; behavioral SDRAM command/data fixture. "
                        "No BIOS/DOS/PIT workload instrumentation; AT refresh disabled, owner refresh active.",
               "runs": []}
    for (kind, loops), program in programs.items():
        for profile in (6, 7):
            name = f"verilator-p{profile}-{kind}-{loops}"
            log = out / (name + ".log")
            trace = out / (name + ".csv")
            backend = out / (name + "-backend.csv")
            run([obj / "trace_pcat", f"+CPU_PROFILE={profile}", f"+LOOPS={loops}",
                 f"+KERNEL_IP={program['kernel_ip']}", f"+KERNEL_LENGTH={program['kernel_length']}",
                 f"+KIND={kind}", f"+ROM={program['rom_binary']}", f"+RAM={program['ram_hex']}",
                 f"+TRACE={trace}", f"+BACKEND_TRACE={backend}"], log, timeout=90)
            marker = next(line for line in log.read_text().splitlines() if line.startswith("P06_R0_PCAT_PASS "))
            values = dict(re.findall(r"(\w+)=(\S+)", marker))
            receipt["runs"].append({**values, "trace_sha256": sha(trace),
                                    "backend_sha256": sha(backend), "log_sha256": sha(log)})
            print(marker, flush=True)
    for relative, digest in inputs.items():
        if sha(ROOT / relative) != digest: raise RuntimeError("Source changed: " + relative)
    receipt["status"] = "P06_R0_PCAT_TRACE_PASS"
    (out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(receipt["status"], flush=True)


if __name__ == "__main__": main()
