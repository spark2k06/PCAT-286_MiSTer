#!/usr/bin/env python3
"""Cycle equivalence of the production PolyFetch process against the pre-split RTL.

The reference is pinned to the last committed scaler before this optimization.
Both harnesses contain the actual declarations, functions and complete process;
the testbench also checks luminance and weights against an integer scoreboard.
Run under Linux/WSL with Docker available. No Quartus synthesis is performed.
"""
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build/at-scaler-luminance/equivalence"
REFERENCE = "a8bc4f12e50317f29bb316367e1bbf477aee262b:sys/ascal.vhd"


def one(pattern, source):
    matches = re.findall(pattern, source, re.S | re.I)
    assert len(matches) == 1, (pattern, len(matches))
    return matches[0]


def harness(source, entity):
    types = "\n".join(one(r"\bTYPE " + name + r" IS RECORD.*?END RECORD;", source)
                      for name in ("poly_phase_t", "poly_phase_interp_t", "type_poly_t"))
    declarations = one(r"\bSIGNAL o_h_poly_mem\b.*?(?=\bFUNCTION poly_unpack)", source)
    functions = "\n".join(one(r"\bFUNCTION " + name + r"\(.*?END FUNCTION;", source)
                          for name in ("poly_unpack", "poly_lerp", "poly_cvt", "poly_nn",
                                       "poly_max" if "FUNCTION poly_max(" in source else "poly_lum"))
    process = one(r"\bPolyFetch:PROCESS.*?END PROCESS PolyFetch;", source)
    return f"""LIBRARY ieee;
USE ieee.std_logic_1164.ALL;
USE ieee.numeric_std.ALL;
ENTITY {entity} IS
  PORT(clk : IN std_logic; h_rgb,v_rgb : IN unsigned(23 DOWNTO 0);
       hm,vm : IN unsigned(2 DOWNTO 0); adaptive : IN std_logic_vector(1 DOWNTO 0);
       hf,vf : IN unsigned(7 DOWNTO 0);
       lum : OUT unsigned(7 DOWNTO 0); ta,tb : OUT signed(9 DOWNTO 0);
       phases : OUT std_logic_vector(143 DOWNTO 0); address : OUT natural);
END;
ARCHITECTURE test OF {entity} IS
  CONSTANT FRAC : natural := 8;
  TYPE type_pix IS RECORD r,g,b : unsigned(7 DOWNTO 0); END RECORD;
  TYPE arr_uv40 IS ARRAY(natural RANGE <>) OF unsigned(39 DOWNTO 0);
  TYPE frac_array IS ARRAY(0 TO 3) OF unsigned(11 DOWNTO 0);
  SIGNAL o_clk : std_logic;
  SIGNAL o_hmode,o_vmode : unsigned(2 DOWNTO 0);
  SIGNAL o_hfrac : frac_array;
  SIGNAL o_vfrac : unsigned(11 DOWNTO 0);
  ATTRIBUTE ramstyle : string;
  FUNCTION to_std_logic(a : boolean) RETURN std_logic IS
  BEGIN IF a THEN RETURN '1'; ELSE RETURN '0'; END IF; END FUNCTION;
  {types}
  {declarations}
  {functions}
BEGIN
  o_clk<=clk; o_hmode<=hm; o_vmode<=vm; poly_adaptive_local<=adaptive;
  o_hfrac<=(OTHERS=>hf & "0000"); o_vfrac<=vf & "0000";
  o_h_lum_pix<=(h_rgb(23 DOWNTO 16),h_rgb(15 DOWNTO 8),h_rgb(7 DOWNTO 0));
  o_v_lum_pix<=(v_rgb(23 DOWNTO 16),v_rgb(15 DOWNTO 8),v_rgb(7 DOWNTO 0));
  lum<=o_poly_lum1; ta<=o_poly_lerp_ta; tb<=o_poly_lerp_tb;
  address<=o_a_poly_addr;
  phases<=std_logic_vector(o_h_poly_phase.t0 & o_h_poly_phase.t1 &
                          o_h_poly_phase.t2 & o_h_poly_phase.t3 &
                          o_v_poly_phase.t0 & o_v_poly_phase.t1 &
                          o_v_poly_phase.t2 & o_v_poly_phase.t3);
  -- Distinct, phase-dependent signed tables make coefficient misalignment visible.
  PROCESS
    VARIABLE h,v,a : unsigned(39 DOWNTO 0);
  BEGIN
    FOR phase IN 0 TO 255 LOOP
      FOR tap IN 0 TO 3 LOOP
        h(39-tap*10 DOWNTO 30-tap*10):=unsigned(to_signed((phase*3+tap*53) MOD 512-256,10));
        v(39-tap*10 DOWNTO 30-tap*10):=unsigned(to_signed((phase*5+tap*29) MOD 512-256,10));
        a(39-tap*10 DOWNTO 30-tap*10):=unsigned(to_signed((phase*7+tap*71) MOD 512-256,10));
      END LOOP;
      o_h_poly_mem(phase)<=h; o_v_poly_mem(phase)<=v; o_a_poly_mem(phase)<=a;
    END LOOP;
    WAIT;
  END PROCESS;
  {process}
END;
"""


def main():
    BUILD.mkdir(parents=True, exist_ok=True)
    reference = subprocess.check_output(["git", "show", REFERENCE], cwd=ROOT, text=True)
    candidate = (ROOT / "sys/ascal.vhd").read_text()
    for name, source in (("reference", reference), ("candidate", candidate)):
        (BUILD / f"{name}.vhd").write_text(harness(source, f"polyfetch_{name}"))
    command = """set -e
ghdl -a --std=93 /work/sys/at_cdc_snapshot.vhd /work/sys/ascal.vhd
ghdl -a --std=08 reference.vhd candidate.vhd /work/sim/spk286_integration/at_scaler_luminance_tb.vhd
ghdl -e --std=08 at_scaler_luminance_tb
ghdl -r --std=08 at_scaler_luminance_tb --assert-level=error --ieee-asserts=disable
"""
    with (BUILD / "simulation.log").open("w") as log:
        result = subprocess.run(["docker", "run", "--rm", "-v", f"{ROOT}:/work:ro",
                                 "-v", f"{BUILD}:/results", "-w", "/results",
                                 "ghdl/ghdl:ubuntu22-llvm-11", "bash", "-lc", command],
                                stdout=log, stderr=subprocess.STDOUT)
    print((BUILD / "simulation.log").read_text())
    result.check_returncode()


if __name__ == "__main__":
    main()
