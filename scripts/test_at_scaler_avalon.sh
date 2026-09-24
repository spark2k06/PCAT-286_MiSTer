#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
build="$root/build/at-scaler-avalon"
mkdir -p "$build"
docker run --rm -v "$root:/work" -w /work/build/at-scaler-avalon \
  ghdl/ghdl:ubuntu22-llvm-11 bash -lc '
    set -e
    ghdl -a --std=93 ../../sys/at_cdc_snapshot.vhd ../../sys/ascal.vhd
    ghdl -a --std=08 ../../sys/at_cdc_snapshot.vhd ../../sys/ascal.vhd ../../sim/spk286_integration/at_scaler_avalon_tb.vhd
    ghdl -e --std=08 at_scaler_avalon_tb
    ghdl -r --std=08 at_scaler_avalon_tb --assert-level=error --ieee-asserts=disable --vcd=progressive.vcd
    ghdl -r --std=08 at_scaler_avalon_tb -gPHASE_NS=3 -gINTERLACED=true --assert-level=error --ieee-asserts=disable --vcd=interlaced.vcd
  ' >"$build/ghdl.log" 2>&1 || { tail -40 "$build/ghdl.log"; exit 1; }
grep AT_SCALER_AVALON_PASS "$build/ghdl.log"
for mode in progressive interlaced; do
  python3 "$root/scripts/check_at_scaler_vcd.py" "$build/$mode.vcd" | tee "$build/$mode.log"
done
