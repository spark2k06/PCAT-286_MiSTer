#!/usr/bin/env bash
set -euo pipefail

root=$(cd "$(dirname "$0")/.." && pwd)
build_dir="${PCAT_BUILD_DIR:-$root/build/i5-timing-equivalence}"
mkdir -p "$build_dir"
cd "$root"

sources=(
  rtl/spk286_integration/spk286_operand_timing.sv
  sim/spk286_integration/spk286_operand_timing_tb.sv
)

iverilog -g2012 -s spk286_operand_timing_tb \
  -o "$build_dir/operand_timing_iv" "${sources[@]}"
vvp "$build_dir/operand_timing_iv" | tee "$build_dir/iverilog.log"

rm -rf "$build_dir/verilator-obj"
verilator --binary --timing --top-module spk286_operand_timing_tb \
  -Wno-fatal --Mdir "$build_dir/verilator-obj" -o operand_timing_vlt \
  "${sources[@]}" >"$build_dir/verilator-build.log" 2>&1
"$build_dir/verilator-obj/operand_timing_vlt" | tee "$build_dir/verilator-run.log"

echo I5_TIMING_EQUIVALENCE_TEST_PASS
