#!/usr/bin/env bash
set -euo pipefail

root=$(cd "$(dirname "$0")/.." && pwd)
build_dir="${PCAT_BUILD_DIR:-$root/build/i4-machine-events}"
mkdir -p "$build_dir"
cd "$root"

python3 scripts/build_event_diag_rom.py --check
python3 scripts/check_pcat_project.py

cpu_sources=(
  vendor/spk286/microcode/generated/spk286_microcode_pkg.sv
  vendor/spk286/microcode/generated/spk286_microcode_rom.sv
)
for source in vendor/spk286/rtl/*.sv; do
  [[ "$source" == "vendor/spk286/rtl/spk286_operand.sv" ]] || cpu_sources+=("$source")
done
cpu_sources+=(
  rtl/spk286_integration/spk286_operand_timing.sv
  rtl/spk286_integration/spk286_xt_address_map.sv
  rtl/spk286_integration/spk286_xt_bridge.sv
  rtl/spk286_integration/spk286_machine_cpu.sv
)
pic_sources=(
  rtl/KFPC-XT/HDL/KF8259/HDL/KF8259_Priority_Resolver.sv
  rtl/KFPC-XT/HDL/KF8259/HDL/KF8259_Interrupt_Request.sv
  rtl/KFPC-XT/HDL/KF8259/HDL/KF8259_In_Service.sv
  rtl/KFPC-XT/HDL/KF8259/HDL/KF8259_Control_Logic.sv
  rtl/KFPC-XT/HDL/KF8259/HDL/KF8259_Bus_Control_Logic.sv
  rtl/KFPC-XT/HDL/KF8259/HDL/KF8259.sv
)
pic_include=(-Irtl/KFPC-XT/HDL/KF8259/HDL)

# Icarus runs the whole CPU program against a deliberately narrow functional
# PIC boundary. The unchanged production KF8259 is used by the Verilator run
# below and by a focused dual-simulator spurious-request test.
iverilog -g2012 "${pic_include[@]}" -s spk286_event_diagnostic_tb \
  -DI4_PIC_MODEL -o "$build_dir/event_iv" "${cpu_sources[@]}" \
  sim/spk286_integration/spk286_pic_model.sv \
  sim/spk286_integration/spk286_event_diagnostic_tb.sv \
  >"$build_dir/event-iverilog-build.log" 2>&1
timeout 180s vvp "$build_dir/event_iv" | tee "$build_dir/event-iverilog-run.log"

rm -rf "$build_dir/event-verilator-obj"
verilator --binary --timing --top-module spk286_event_diagnostic_tb \
  -Wno-fatal "${pic_include[@]}" --Mdir "$build_dir/event-verilator-obj" \
  -o event_vlt "${cpu_sources[@]}" "${pic_sources[@]}" \
  sim/spk286_integration/spk286_event_diagnostic_tb.sv \
  >"$build_dir/event-verilator-build.log" 2>&1
"$build_dir/event-verilator-obj/event_vlt" | tee "$build_dir/event-verilator-run.log"

pic_spurious_sources=(
  "${pic_sources[@]}"
  sim/spk286_integration/spk286_pic_spurious_tb.sv
)
iverilog -g2012 "${pic_include[@]}" -s spk286_pic_spurious_tb \
  -o "$build_dir/pic-spurious_iv" "${pic_spurious_sources[@]}" \
  >"$build_dir/pic-spurious-iverilog-build.log" 2>&1
vvp "$build_dir/pic-spurious_iv" | tee "$build_dir/pic-spurious-iverilog-run.log"

rm -rf "$build_dir/pic-spurious-verilator-obj"
verilator --binary --timing --top-module spk286_pic_spurious_tb \
  -Wno-fatal "${pic_include[@]}" \
  --Mdir "$build_dir/pic-spurious-verilator-obj" -o pic_spurious_vlt \
  "${pic_spurious_sources[@]}" \
  >"$build_dir/pic-spurious-verilator-build.log" 2>&1
"$build_dir/pic-spurious-verilator-obj/pic_spurious_vlt" \
  | tee "$build_dir/pic-spurious-verilator-run.log"

diag_monitor_sources=(
  rtl/spk286_integration/spk286_diag_monitor.sv
  sim/spk286_integration/spk286_diag_monitor_tb.sv
)
iverilog -g2012 -s spk286_diag_monitor_tb \
  -o "$build_dir/diag-monitor_iv" "${diag_monitor_sources[@]}" \
  >"$build_dir/diag-monitor-iverilog-build.log" 2>&1
vvp "$build_dir/diag-monitor_iv" | tee "$build_dir/diag-monitor-iverilog-run.log"

rm -rf "$build_dir/diag-monitor-verilator-obj"
verilator --binary --timing --top-module spk286_diag_monitor_tb \
  -Wno-fatal --Mdir "$build_dir/diag-monitor-verilator-obj" \
  -o diag_monitor_vlt "${diag_monitor_sources[@]}" \
  >"$build_dir/diag-monitor-verilator-build.log" 2>&1
"$build_dir/diag-monitor-verilator-obj/diag_monitor_vlt" \
  | tee "$build_dir/diag-monitor-verilator-run.log"

rom_loader_sources=(
  rtl/KFPC-XT/HDL/rom_presence_latch.sv
  rtl/KFPC-XT/HDL/ega_bios_loaded_latch.sv
  rtl/KFPC-XT/HDL/bios_hold_notice.sv
  rtl/spk286_integration/pcat_rom_loader.sv
  sim/spk286_integration/pcat_rom_loader_tb.sv
)
iverilog -g2012 -s pcat_rom_loader_tb \
  -o "$build_dir/rom-loader_iv" "${rom_loader_sources[@]}" \
  >"$build_dir/rom-loader-iverilog-build.log" 2>&1
vvp "$build_dir/rom-loader_iv" | tee "$build_dir/rom-loader-iverilog-run.log"

rm -rf "$build_dir/rom-loader-verilator-obj"
verilator --binary --timing --top-module pcat_rom_loader_tb \
  -Wno-fatal --Mdir "$build_dir/rom-loader-verilator-obj" -o rom_loader_vlt \
  "${rom_loader_sources[@]}" >"$build_dir/rom-loader-verilator-build.log" 2>&1
"$build_dir/rom-loader-verilator-obj/rom_loader_vlt" \
  | tee "$build_dir/rom-loader-verilator-run.log"

frontend_sources=(
  rtl/spk286_integration/spk286_xt_address_map.sv
  rtl/spk286_integration/spk286_xt_bridge.sv
  rtl/KFPC-XT/HDL/KF8288/HDL/KF8288.sv
  sim/spk286_integration/spk286_8288_frontend_tb.sv
)
iverilog -g2012 "${pic_include[@]}" -DI4_PIC_MODEL \
  -s spk286_8288_frontend_tb -o "$build_dir/frontend_iv" \
  sim/spk286_integration/spk286_pic_model.sv "${frontend_sources[@]}" \
  >"$build_dir/frontend-iverilog-build.log" 2>&1
vvp "$build_dir/frontend_iv" | tee "$build_dir/frontend-iverilog-run.log"

rm -rf "$build_dir/frontend-verilator-obj"
verilator --binary --timing --top-module spk286_8288_frontend_tb \
  -Wno-fatal "${pic_include[@]}" \
  --Mdir "$build_dir/frontend-verilator-obj" -o frontend_vlt \
  "${pic_sources[@]}" "${frontend_sources[@]}" \
  >"$build_dir/frontend-verilator-build.log" 2>&1
"$build_dir/frontend-verilator-obj/frontend_vlt" | tee "$build_dir/frontend-verilator-run.log"

ownership_sources=(
  sim/spk286_integration/spk286_bus_ownership_tb.sv
  rtl/KFPC-XT/HDL/Bus_Arbiter_SPK286.sv
)
iverilog -g2012 -s spk286_bus_ownership_tb \
  -o "$build_dir/ownership_iv" "${ownership_sources[@]}" \
  >"$build_dir/ownership-iverilog-build.log" 2>&1
vvp "$build_dir/ownership_iv" | tee "$build_dir/ownership-iverilog-run.log"

rm -rf "$build_dir/ownership-verilator-obj"
verilator --binary --timing --top-module spk286_bus_ownership_tb \
  -Wno-fatal --Mdir "$build_dir/ownership-verilator-obj" -o ownership_vlt \
  "${ownership_sources[@]}" >"$build_dir/ownership-verilator-build.log" 2>&1
"$build_dir/ownership-verilator-obj/ownership_vlt" | tee "$build_dir/ownership-verilator-run.log"

# Retain the inherited machine-side readiness, ROM presence and SDRAM refresh
# collision regressions. These benches exercise unchanged baseline modules.
for inherited in Ready ega_bios_loaded_latch ram_refresh_collision; do
  TB_BUILD="$build_dir/inherited" \
    bash rtl/KFPC-XT/TESTBENCH/run_tests.sh "$inherited" \
    | tee "$build_dir/inherited-$inherited.log"
done

echo I4_MACHINE_EVENTS_TEST_PASS
