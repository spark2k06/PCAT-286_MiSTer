#!/usr/bin/env bash
set -euo pipefail

root=$(cd "$(dirname "$0")/.." && pwd)
build_dir="${PCAT_BUILD_DIR:-$root/build/i2-bridge}"
mkdir -p "$build_dir"
cd "$root"

sources=(
  rtl/spk286_integration/spk286_xt_address_map.sv
  rtl/spk286_integration/spk286_xt_bridge.sv
  rtl/spk286_integration/spk286_xt_ownership.sv
  sim/spk286_integration/spk286_xt_bridge_tb.sv
)

iverilog -g2012 -s spk286_xt_bridge_tb \
  -o "$build_dir/bridge_iv" "${sources[@]}"
vvp "$build_dir/bridge_iv" | tee "$build_dir/iverilog.log"

verilator --binary --timing --top-module spk286_xt_bridge_tb \
  -Wno-fatal --Mdir "$build_dir/verilator-obj" \
  -o bridge_vlt "${sources[@]}" >"$build_dir/verilator-build.log" 2>&1
"$build_dir/verilator-obj/bridge_vlt" | tee "$build_dir/verilator-run.log"

mutation_names=(
  wrong-code-status
  swapped-high-byte
  early-word-ack
  duplicated-port-write
  stale-input-data
  merged-inta
  premature-dma-grant
)

for mutation in 1 2 3 4 5 6 7; do
  output="$build_dir/mutation-$mutation.log"
  iverilog -g2012 -s spk286_xt_bridge_tb \
    -Pspk286_xt_bridge_tb.MUTATION="$mutation" \
    -o "$build_dir/mutation-$mutation" "${sources[@]}"
  if vvp "$build_dir/mutation-$mutation" >"$output" 2>&1; then
    echo "Mutation $mutation (${mutation_names[$((mutation - 1))]}) survived" >&2
    exit 1
  fi
  if ! grep -q 'CHECK_FAIL' "$output"; then
    echo "Mutation $mutation did not fail a targeted check" >&2
    exit 1
  fi
  echo "MUTATION_DETECTED $mutation ${mutation_names[$((mutation - 1))]}"
done

echo I2_BRIDGE_TEST_PASS
