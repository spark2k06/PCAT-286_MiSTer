#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
build_dir="${TMPDIR:-/tmp}/pcat286-keyboard-path"
mkdir -p "$build_dir"
cd "$repo_root"

iverilog -g2012 -s keyboard_path_tb \
  -o "$build_dir/keyboard_path.vvp" \
  -I rtl/KFPC-XT/HDL/KF8255/HDL \
  -I rtl/KFPC-XT/HDL/KF8259/HDL \
  rtl/KFPC-XT/HDL/KFPS2KB/HDL/KFPS2KB.sv \
  rtl/KFPC-XT/HDL/KFPS2KB/HDL/KFPS2KB_Shift_Register.sv \
  rtl/KFPC-XT/HDL/KF8255/HDL/KF8255.sv \
  rtl/KFPC-XT/HDL/KF8255/HDL/KF8255_Control_Logic.sv \
  rtl/KFPC-XT/HDL/KF8255/HDL/KF8255_Group.sv \
  rtl/KFPC-XT/HDL/KF8255/HDL/KF8255_Port.sv \
  rtl/KFPC-XT/HDL/KF8255/HDL/KF8255_Port_C.sv \
  rtl/KFPC-XT/HDL/KF8259/HDL/KF8259.sv \
  rtl/KFPC-XT/HDL/KF8259/HDL/KF8259_Bus_Control_Logic.sv \
  rtl/KFPC-XT/HDL/KF8259/HDL/KF8259_Control_Logic.sv \
  rtl/KFPC-XT/HDL/KF8259/HDL/KF8259_In_Service.sv \
  rtl/KFPC-XT/HDL/KF8259/HDL/KF8259_Interrupt_Request.sv \
  rtl/KFPC-XT/HDL/KF8259/HDL/KF8259_Priority_Resolver.sv \
  sim/keyboard_path/keyboard_path_tb.sv

vvp "$build_dir/keyboard_path.vvp"
