#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
build="$root/build/at-ram-trace"
mkdir -p "$build"
rtl="$root/rtl/spk286_integration/spk286_at_ram_trace.sv"
tb="$root/sim/spk286_integration/spk286_at_ram_trace_tb.sv"
verilator --lint-only --top-module spk286_at_ram_trace "$rtl"
iverilog -g2012 -s spk286_at_ram_trace_tb -o "$build/trace.vvp" "$rtl" "$tb"
vvp "$build/trace.vvp"
verilator --binary --timing --top-module spk286_at_ram_trace_tb -j 4 \
    --Mdir "$build/obj" -o trace "$rtl" "$tb" > "$build/build.log" 2>&1
"$build/obj/trace"
echo AT_RAM_TRACE_TEST_PASS
