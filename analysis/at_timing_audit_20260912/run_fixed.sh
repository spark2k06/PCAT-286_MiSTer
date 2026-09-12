#!/bin/bash
set -euo pipefail
mkdir -p /build
cp -a /source/db /build/db
cp /source/*.qpf /source/*.qsf /source/*.qip /source/*.sdc /source/*.tcl /build/
ln -s /source/rtl /build/rtl
ln -s /source/sys /build/sys
ln -s /source/vendor /build/vendor
cd /build
quartus_sta -t /audit/audit_fixed.tcl > /audit/run_fixed.log 2>&1

