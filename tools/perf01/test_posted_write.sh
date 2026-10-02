#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd)
private=${1:?Frozen experiment root required}
out=${2:?New validation output directory required}
[[ ! -e "$out" ]]
mkdir -p "$out"
sources=(
  "$root/tools/perf01/prototypes/spk286_at_posted_write_buffer.sv"
  "$private/candidate/rtl/spk286_integration/spk286_at_bus_bridge.sv"
  "$root/rtl/spk286_integration/spk286_at_arbiter.sv"
  "$root/rtl/spk286_integration/spk286_at_mister_sdram_owner.sv"
  "$root/rtl/KFPC-XT/HDL/KFSDRAM/HDL/KFSDRAM.sv"
  "$root/sim/spk286_integration/spk286_sdram_pin_model.sv"
  "$root/tools/perf01/prototypes/spk286_at_posted_write_buffer_tb.sv"
)
sha256sum "${sources[@]}" > "$out/sources.sha256"
verilator --binary --timing --assert -j 4 -Wno-fatal \
  -DSPK286_P01_FAST_MEMORY_START -DSPK286_P06_EARLY_MEMORY_ADDRESS \
  --top-module spk286_at_posted_write_buffer_tb --Mdir "$out/obj" \
  -o posted_test "${sources[@]}" > "$out/build.log" 2>&1
timeout 45s "$out/obj/posted_test" | tee "$out/run.log"
sha256sum --check "$out/sources.sha256" > "$out/verified.log"
