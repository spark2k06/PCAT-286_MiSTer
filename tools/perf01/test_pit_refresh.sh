#!/usr/bin/env bash
set -euo pipefail
[[ $# == 2 ]]
work=$(realpath "$1")
out=$(realpath -m "$2")
[[ ! -e "$out" ]]
mkdir -p "$out"
root=$(cd "$(dirname "$0")/../.." && pwd)
sources=("$work/rtl/spk286_integration/spk286_at_refresh.sv"
 "$work/rtl/spk286_integration/spk286_at_pit.sv"
 "$work/rtl/spk286_integration/spk286_at_pit_clock.sv")
mapfile -t counters < <(find "$work/rtl/KFPC-XT/HDL/KF8253/HDL" -maxdepth 1 -name '*.sv' -o -name '*.v' | sort)
sources+=("${counters[@]}" "$root/tools/perf01/prototypes/spk286_at_pit_refresh_tb.sv")
sha256sum "${sources[@]}" > "$out/sources.sha256"
verilator --lint-only --timing --assert -Wall --top-module spk286_at_refresh "${sources[0]}" > "$out/strict-lint.log" 2>&1
iverilog -g2012 -I "$work/rtl/KFPC-XT/HDL/KF8253/HDL" -s spk286_at_pit_refresh_tb -o "$out/test.vvp" "${sources[@]}" > "$out/iverilog-build.log" 2>&1
vvp "$out/test.vvp" | tee "$out/iverilog-run.log"
verilator --binary --timing --assert -j 4 -Wno-fatal -I"$work/rtl/KFPC-XT/HDL/KF8253/HDL" --top-module spk286_at_pit_refresh_tb --Mdir "$out/obj" -o pit_refresh "${sources[@]}" > "$out/verilator-build.log" 2>&1
"$out/obj/pit_refresh" | tee "$out/verilator-run.log"
sha256sum -c "$out/sources.sha256" > "$out/source-guard.log"
