#!/usr/bin/env bash
# Front-end check ONLY. No mapping synthesis, fitter, assembler or RBF.
set -euo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
output="$root/build/at-cdc"
mkdir -p "$output"
docker run --rm -v "$root:/source:ro" -v "$output:/results" \
  raetro/quartus:mister bash -c '
    set -euo pipefail
    mkdir -p /build
    for dir in rtl sys vendor SW scripts; do cp -a "/source/$dir" "/build/$dir"; done
    for ext in sv v vh qpf qsf qip sdc tcl mif mem hex; do
      for file in /source/*.$ext; do
        if [[ -f "$file" ]]; then cp "$file" /build/; fi
      done
    done
    cd /build
    sha256sum PCAT-286_AT.qsf PCAT-286_AT.sdc sys/sys_top.sdc sys/sys_top.v \
      sys/hps_io.sv sys/osd.v sys/ascal.vhd sys/pll_hdmi_adj.vhd \
      sys/at_cdc_snapshot.sv sys/at_cdc_snapshot.vhd > /results/frontend-inputs.sha256
    quartus_sh -t scripts/check_p05_at_project.tcl PCAT-286_AT > /results/project-final.log 2>&1
    quartus_map --analysis_and_elaboration PCAT-286_AT -c PCAT-286_AT > /results/quartus-final-elaboration.log 2>&1
    test ! -e output_files_pcat286_at_cdc/PCAT-286_AT.rbf
  '
grep 'Analysis & Elaboration was successful' "$output/quartus-final-elaboration.log"
echo 'AT_CDC_QUARTUS_FRONTEND_PASS (no synthesis/fitter/RBF)'
