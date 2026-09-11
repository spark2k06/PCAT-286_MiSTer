#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="$ROOT_DIR/build/at-profile-elab"
mkdir -p "$BUILD_DIR"

if ! grep -q '`ifdef AT_PROFILE' "$ROOT_DIR/sys/sys_top.v" || \
   ! grep -q 'emu_at emu' "$ROOT_DIR/sys/sys_top.v"; then
  echo "AT_PROFILE selector is missing" >&2
  exit 1
fi

mapfile -t AT_SOURCES < <(
  sed -n 's/.*SYSTEMVERILOG_FILE "\([^"]*\.sv\)".*/\1/p' \
    "$ROOT_DIR/rtl/spk286_integration/spk286_integration.qip"
)

KF8259_DIR="$ROOT_DIR/rtl/KFPC-XT/HDL/KF8259/HDL"
SOURCE_FILES=(
  "$ROOT_DIR/sim/spk286_integration/hps_io_elab_stub.sv"
  "$ROOT_DIR/rtl/KFPC-XT/HDL/KFSDRAM/HDL/KFSDRAM.sv"
  "$KF8259_DIR/KF8259_Common_Package.svh"
  "$KF8259_DIR/KF8259_Priority_Resolver.sv"
  "$KF8259_DIR/KF8259_Interrupt_Request.sv"
  "$KF8259_DIR/KF8259_In_Service.sv"
  "$KF8259_DIR/KF8259_Control_Logic.sv"
  "$KF8259_DIR/KF8259_Bus_Control_Logic.sv"
  "$KF8259_DIR/KF8259.sv"
)
for source in "${AT_SOURCES[@]}"; do
  SOURCE_FILES+=("$ROOT_DIR/$source")
done

iverilog -g2012 -Wall -Wno-timescale \
  -t null \
  -s emu_at \
  -I"$ROOT_DIR" \
  -I"$KF8259_DIR" \
  "${SOURCE_FILES[@]}" \
  >"$BUILD_DIR/compile.log" 2>&1 || {
    cat "$BUILD_DIR/compile.log"
    exit 1
  }

echo "AT_PROFILE_SELECTOR_PASS"
echo "AT_PROFILE_ELAB_PASS"
