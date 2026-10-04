from pathlib import Path
import hashlib
import json
import sys

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_p06_profile_cpu import build, sha
from check_p06_profile_components import select
from run_p06_core_register import run

source = (ROOT / "sim/spk286_timing/spk286_profile_prefix_tb.sv").read_text()
source = source.replace("module spk286_profile_prefix_tb;", "module profile_pause_pending_tb;")
source = source.replace("    logic checked;", """    logic checked;
    logic saw_raw = 0, saw_pause_retire = 0;
    logic [127:0] saved_gpr;
    logic [15:0] saved_flags, saved_ip;
    integer pause_boundaries = 0, paused_retire_count = 0;
""")
old = "        clk = 1; #5; clk = 0; #1; edges++;"
new = """        begin
            bit raw_now;
            raw_now = execute_enable && dut.raw_retired;
            clk = 1; #5; clk = 0; #1; edges++;
            if (raw_now) begin
                saw_raw = 1; execute_enable = 0;
                saved_gpr = debug_gpr; saved_flags = debug_flags; saved_ip = debug_ip;
                $display("PAUSE_RAW_CAPTURE edge%0d elapsed%0d budget%0d", edges,
                         dut.profile_elapsed, dut.profile_scheduled);
            end
            if (saw_raw) begin
                if (cpu_boundary) pause_boundaries++;
                check(debug_gpr === saved_gpr && debug_flags === saved_flags && debug_ip === saved_ip,
                      "no architectural action while verifier paused after raw completion");
                check(!dut.opcode_start && !dut.effective_gpr_write_en &&
                      !dut.effective_flags_write_en && !dut.effective_ip_write_en,
                      "no new opcode or architectural write during verifier pause");
                check(!(bus_valid && ready && bus_write), "no accepted CPU write during pause");
                if (instruction_retired) begin saw_pause_retire = 1; paused_retire_count++; end
            end
        end"""
assert source.count(old) == 1
source = source.replace(old, new)
initial = source.index("    initial begin\n")
source = source[:initial] + """    initial begin
        // A1 aligned READ is actually complete before the five-clock deadline.
        // Continue virtual clock pulses while execute_enable selects verifier.
        setup(64'h0300A1, 3, 0, 5, 0);
        check(saw_raw && saw_pause_retire && !execute_enable,
              "completed instruction publishes deferred notification during verifier pause");
        repeat(24) tick();
        check(pause_boundaries > 0 && paused_retire_count == 1,
              "running clock and exactly one notification, with no following CPU action");
        $display("PROFILE_PAUSE_PENDING_PASS retire%0d pause_boundaries%0d checks%0d",
                 paused_retire_count, pause_boundaries, checks);
        $finish;
    end
endmodule
"""
bench = OUT / "probe.sv"
bench.write_text(source, newline="\n")
selected = build(OUT / "candidate")
binary = OUT / "probe.vvp"
run(["iverilog", "-g2012", "-s", "profile_pause_pending_tb",
     "-I" + str(ROOT / "vendor/spk286/sim/unit"), "-o", binary, *select(selected), bench],
    OUT / "build.log")
result = run(["vvp", binary], OUT / "run.log")
assert "PROFILE_PAUSE_PENDING_PASS retire1" in result
receipt = {
    "status": "CPU_COMPLETED_INTERVAL_NOTIFICATION_DURING_VERIFIER_PAUSE_PASS",
    "source_sha256": {p.relative_to(ROOT).as_posix(): sha(p) for p in [Path(__file__), bench,
        ROOT / "scripts/build_p06_profile_cpu.py", ROOT / "rtl/spk286_timing/spk286_instruction_schedule.sv"]},
    "generated_sha256": {name: sha(path) for name, path in selected.items()},
    "artifact_sha256": {name: sha(OUT / name) for name in ("build.log", "run.log")},
    "scope": "One aligned A1 completed on fabric before deadline; execute_enable0 afterwards with virtual clock running. Exactly one deferred retirement notification; no subsequent opcode or GPR/FLAGS/IP/accepted bus write while paused. Not a stopped CPU-clock or paused-before-functional-completion case.",
}
(OUT / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", newline="\n")
print(result)
