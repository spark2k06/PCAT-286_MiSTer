#!/usr/bin/env bash
# Exhaustive combinational and cycle-exact old/new keyboard checks only.
set -euo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
output=$(realpath -m "${1:-$root/build/at-keyboard-packing}")
[[ $# -le 1 && ! -e "$output" ]]
cd "$root"
python3 scripts/prepare_at_keyboard_packing.py "$output"
verilator --lint-only -Wall --top-module spk286_at_keyboard \
  rtl/spk286_integration/spk286_at_keyboard.sv > "$output/lint.log" 2>&1
for kind in packing cycle; do
  if [[ $kind == packing ]]; then
    top=spk286_at_keyboard_packing_tb
    sources=("$output/packing_reference.sv" "$output/packing_candidate.sv" \
      sim/spk286_integration/spk286_at_keyboard_packing_tb.sv)
  else
    top=spk286_at_keyboard_cycle_equivalence_tb
    sources=("$output/keyboard_reference.sv" rtl/spk286_integration/spk286_at_keyboard.sv \
      sim/spk286_integration/spk286_at_keyboard_cycle_equivalence_tb.sv)
  fi
  iverilog -g2012 -s "$top" -o "$output/${kind}_iv" "${sources[@]}" \
    > "$output/${kind}-iverilog-build.log" 2>&1
  vvp "$output/${kind}_iv" | tee "$output/${kind}-iverilog-run.log"
  verilator --binary --timing --top-module "$top" -Wno-fatal -j 4 \
    --Mdir "$output/${kind}-verilator-obj" -o equivalence "${sources[@]}" \
    > "$output/${kind}-verilator-build.log" 2>&1
  "$output/${kind}-verilator-obj/equivalence" | tee "$output/${kind}-verilator-run.log"
  # Simulator-specific finish diagnostics differ; compare the actual result.
  grep '^AT_KEYBOARD_' "$output/${kind}-iverilog-run.log" > "$output/${kind}-iverilog-result.txt"
  grep '^AT_KEYBOARD_' "$output/${kind}-verilator-run.log" > "$output/${kind}-verilator-result.txt"
  cmp "$output/${kind}-iverilog-result.txt" "$output/${kind}-verilator-result.txt"
done
echo AT_KEYBOARD_PACKING_DIRECTED_PASS
