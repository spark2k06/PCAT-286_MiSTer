#!/usr/bin/env bash
set -euo pipefail

root=$(cd "$(dirname "$0")/.." && pwd)
build_dir="${PCAT_BUILD_DIR:-$root/build/i3-diagnostic}"
mkdir -p "$build_dir"
cd "$root"

python3 scripts/build_diag_rom.py --check

sources=(
  vendor/spk286/microcode/generated/spk286_microcode_pkg.sv
  vendor/spk286/microcode/generated/spk286_microcode_rom.sv
)
for source in vendor/spk286/rtl/*.sv; do
  [[ "$source" == "vendor/spk286/rtl/spk286_operand.sv" ]] || sources+=("$source")
done
sources+=(
  rtl/spk286_integration/spk286_operand_timing.sv
  rtl/spk286_integration/spk286_xt_address_map.sv
  rtl/spk286_integration/spk286_xt_bridge.sv
  rtl/spk286_integration/spk286_machine_cpu.sv
  sim/spk286_integration/spk286_diagnostic_tb.sv
)

iverilog -g2012 -s spk286_diagnostic_tb \
  -o "$build_dir/diagnostic_iv" "${sources[@]}"
timeout 120s vvp "$build_dir/diagnostic_iv" | tee "$build_dir/iverilog.log"

verilator --binary --timing --top-module spk286_diagnostic_tb \
  -Wno-fatal --Mdir "$build_dir/verilator-obj" \
  -o diagnostic_vlt "${sources[@]}" >"$build_dir/verilator-build.log" 2>&1
timeout 120s "$build_dir/verilator-obj/diagnostic_vlt" | tee "$build_dir/verilator-run.log"

echo I3_DIAGNOSTIC_TEST_PASS
