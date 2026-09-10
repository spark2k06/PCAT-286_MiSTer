#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
quartus_image="${QUARTUS_IMAGE:-raetro/quartus:mister}"

cd "$repo_root"

bash scripts/test_i5_timing_equivalence.sh

docker run --rm \
    -v "$repo_root:/build" \
    -w /build \
    "$quartus_image" \
    quartus_sh --flow compile PCAT-286.qsf

docker run --rm \
    -v "$repo_root:/build" \
    -w /build \
    "$quartus_image" \
    quartus_sta -t scripts/report_i5_spk286_timing.tcl

timing_reports=(
    output_files_pcat286/PCAT-286.spk286_internal_setup.rpt
    output_files_pcat286/PCAT-286.spk286_internal_hold.rpt
    output_files_pcat286/PCAT-286.spk286_to_bridge_setup.rpt
    output_files_pcat286/PCAT-286.bridge_to_spk286_setup.rpt
    output_files_pcat286/PCAT-286.spk286_debug_capture_setup.rpt
    output_files_pcat286/PCAT-286.chipset_clock_setup.rpt
    output_files_pcat286/PCAT-286.chipset_clock_hold.rpt
)
for timing_report in "${timing_reports[@]}"; do
    if ! grep -Eq '^Report Timing: Found [1-9][0-9]* (setup|hold) paths \(0 violated\)' "$timing_report"; then
        echo "Focused timing gate failed: $timing_report" >&2
        exit 1
    fi
done

sha256sum \
    output_files_pcat286/PCAT-286.rbf \
    output_files_pcat286/PCAT-286.sof \
    > output_files_pcat286/PCAT-286.bitstreams.sha256
