#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
build_dir="${PCAT_BUILD_DIR:-$root/build/rtc-bcd-lookup}"
mkdir -p "$build_dir"
cd "$root"
sha256sum rtl/spk286_integration/spk286_at_rtc_cmos.sv \
  rtl/spk286_integration/spk286_at_rtc_clock.sv > "$build_dir/sources.sha256"
python3 scripts/prove_rtc_bcd.py "$build_dir"
verilator --lint-only --Wall --top-module rtc_bcd_candidate \
  "$build_dir/rtc_bcd_candidate.sv" > "$build_dir/conversion-wall.log" 2>&1
sources=("$build_dir/rtc_bcd_reference.sv" "$build_dir/rtc_bcd_candidate.sv"
         sim/spk286_integration/rtc_bcd_equivalence_tb.sv)
iverilog -g2012 -DTEST_FOUR_STATE -s rtc_bcd_equivalence_tb \
  -o "$build_dir/conversion.iv" "${sources[@]}" > "$build_dir/conversion-iverilog-build.log" 2>&1
vvp "$build_dir/conversion.iv" | tee "$build_dir/conversion-iverilog-run.log"
verilator --binary --timing --top-module rtc_bcd_equivalence_tb -j 4 \
  --Mdir "$build_dir/conversion-obj" -o run "${sources[@]}" \
  > "$build_dir/conversion-verilator-build.log" 2>&1
"$build_dir/conversion-obj/run" | tee "$build_dir/conversion-verilator-run.log"
PCAT_BUILD_DIR="$build_dir/rtc-banks" bash scripts/test_at_rtc_cmos.sh
sha256sum -c "$build_dir/sources.sha256" | tee "$build_dir/source-end-check.log"
echo RTC_BCD_LOOKUP_DIRECTED_PASS
