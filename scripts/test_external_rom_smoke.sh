#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
rom_path="${1:?usage: scripts/test_external_rom_smoke.sh path/to/64KiB.rom [max_cycles] [minimum_beats]}"
max_cycles="${2:-2000000}"
minimum_beats="${3:-128}"
rom_runtime_path="$rom_path"
if command -v cygpath >/dev/null 2>&1; then
  rom_runtime_path="$(cygpath -w "$rom_path")"
fi
build_dir="$repo_root/build/external_rom_smoke"
mkdir -p "$build_dir"
cd "$repo_root"

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
  rtl/KFPC-XT/HDL/KF8288/HDL/KF8288.sv
  rtl/KFPC-XT/HDL/Ready.sv
  sim/spk286_integration/spk286_external_rom_smoke_tb.sv
)

verilator --binary --timing --top-module spk286_external_rom_smoke_tb \
  -Wno-fatal --Mdir "$build_dir/verilator-obj" \
  -o external_rom_smoke_vlt "${sources[@]}" \
  >"$build_dir/verilator-build.log" 2>&1
timeout 120s "$build_dir/verilator-obj/external_rom_smoke_vlt" \
  "+ROM=$rom_runtime_path" "+MAX_CYCLES=$max_cycles" \
  "+MIN_BEATS=$minimum_beats"
