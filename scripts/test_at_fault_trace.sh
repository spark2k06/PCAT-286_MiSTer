#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
build_dir="${PCAT_BUILD_DIR:-$root/build/at-fault_trace}"
mkdir -p "$build_dir"
cd "$root"
sources=(rtl/spk286_integration/spk286_at_fault_trace.sv sim/spk286_integration/spk286_at_fault_trace_tb.sv)
iverilog -g2012 -s spk286_at_fault_trace_tb -o "$build_dir/test_iv" "${sources[@]}" >"$build_dir/iverilog-build.log" 2>&1
vvp "$build_dir/test_iv" | tee "$build_dir/iverilog-run.log"
verilator --binary --timing --top-module spk286_at_fault_trace_tb -Wno-fatal -j 4 --Mdir "$build_dir/verilator-obj" -o test_vlt "${sources[@]}" >"$build_dir/verilator-build.log" 2>&1
"$build_dir/verilator-obj/test_vlt" | tee "$build_dir/verilator-run.log"
