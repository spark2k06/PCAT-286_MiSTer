#!/usr/bin/env python3
"""Prove the actual scaler terminal comparison and complete OSWEEP transition.

Use existing GHDL Docker and Yosys tools. The current production process is the
candidate; reconstruct its reference by undoing only the terminal predicate.
No production files, timing constraints or expected architectural data change.
"""
from pathlib import Path
import argparse
import hashlib
import json
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output", type=Path, default=Path("build/ascal-terminal-equivalence"),
                    help="fresh output directory inside this repository's build directory")
parser.add_argument("--hacc-proof-receipt", type=Path,
                    help="source-bound hacc PASS receipt; required for the installed hacc reorder")
args = parser.parse_args()
OUT = (ROOT / args.output).resolve() if not args.output.is_absolute() else args.output.resolve()
assert OUT.is_relative_to((ROOT / "build").resolve()), "output must stay inside the repository build directory"
assert not OUT.exists(), "output directory must be fresh; preserve previous evidence"
OUT.mkdir(parents=True)
SOURCE = ROOT / "sys/ascal.vhd"
DEPENDENCY = ROOT / "sys/at_cdc_snapshot.vhd"
IMAGE = "ghdl/ghdl:ubuntu22-llvm-11"
PRIVATE_PROOF_REFERENCE_SHA256 = "966157e71f22a94123597188cbba91e28943c71368670d0a13a5bd8b0baf61e4"
HACC_REFERENCE_SOURCE_SHA256 = "412aa4c447e9b6389600dabb0072ffdc5bffdd14a310962e2dc5ebff01be5186"
HACC_CANDIDATE_SOURCE_SHA256 = "8a8382913f007cf7405aad235d6df9558ec14fc493251e31783ddb00031fd687"
HACC_PROOF_HELPER_SHA256 = "214ba1367775b2aa67a90ebf81740b41e54cc48a8d0acf535bef50daab24700b"
HACC_REFERENCE_ASSIGNMENT = "o_hacc_next<=(dif_v + 2*o_ihsize + (4*OHRESH)) MOD (4*OHRESH);"
HACC_CANDIDATE_ASSIGNMENT = "o_hacc_next<=(o_hacc_next + 2*o_ihsize - 2*o_hsize + (8*OHRESH)) MOD (4*OHRESH);"
EXPECTED_HIDE_DIAGNOSTICS = [
    (446, 55, 'declaration of "freeze" hides port "freeze"'),
    (600, 97, 'declaration of "format" hides port "format"'),
    (614, 30, 'declaration of "i_dw" hides signal "i_dw"'),
    (618, 30, 'declaration of "format" hides port "format"'),
    (649, 66, 'declaration of "format" hides port "format"'),
    (667, 65, 'declaration of "format" hides port "format"'),
    (718, 66, 'declaration of "format" hides port "format"'),
    (737, 90, 'declaration of "format" hides port "format"'),
    (758, 82, 'declaration of "format" hides port "format"'),
    (1154, 26, 'declaration of "frac" hides generic "FRAC"'),
]

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def run(name, args, cwd=OUT, expect=0):
    log = OUT / f"{name}.log"
    with log.open("w") as stream:
        result = subprocess.run(args, cwd=cwd, stdout=stream, stderr=subprocess.STDOUT)
    if expect == 0:
        assert result.returncode == 0, (name, result.returncode, log)
    else:
        assert result.returncode != 0, (name, "negative control unexpectedly passed")
    return result.returncode

source_sha = sha(SOURCE)
helper_sha = sha(__file__)
dependency_sha = sha(DEPENDENCY)
image_id = subprocess.check_output(
    ["docker", "image", "inspect", "--format={{.Id}}", IMAGE], text=True).strip()
assert re.fullmatch(r"sha256:[0-9a-f]{64}", image_id), "installed GHDL image identity unavailable"
candidate_bytes = SOURCE.read_bytes()
assert source_sha in (HACC_REFERENCE_SOURCE_SHA256, HACC_CANDIDATE_SOURCE_SHA256), "unreviewed full-file scaler source"
hacc_installed = "reference" if source_sha == HACC_REFERENCE_SOURCE_SHA256 else "candidate"
if hacc_installed == "reference":
    assert candidate_bytes.count(HACC_REFERENCE_ASSIGNMENT.encode()) == 1
    assert HACC_CANDIDATE_ASSIGNMENT.encode() not in candidate_bytes
    hacc_reference_bytes = candidate_bytes
    hacc_candidate_bytes = candidate_bytes.replace(HACC_REFERENCE_ASSIGNMENT.encode(), HACC_CANDIDATE_ASSIGNMENT.encode())
else:
    assert candidate_bytes.count(HACC_CANDIDATE_ASSIGNMENT.encode()) == 1
    assert HACC_REFERENCE_ASSIGNMENT.encode() not in candidate_bytes
    hacc_candidate_bytes = candidate_bytes
    hacc_reference_bytes = candidate_bytes.replace(HACC_CANDIDATE_ASSIGNMENT.encode(), HACC_REFERENCE_ASSIGNMENT.encode())
assert hashlib.sha256(hacc_reference_bytes).hexdigest() == HACC_REFERENCE_SOURCE_SHA256
assert hashlib.sha256(hacc_candidate_bytes).hexdigest() == HACC_CANDIDATE_SOURCE_SHA256
assert hacc_reference_bytes.replace(HACC_REFERENCE_ASSIGNMENT.encode(), HACC_CANDIDATE_ASSIGNMENT.encode()) == hacc_candidate_bytes
hacc_binding = {"installed_variant": hacc_installed,
                "reference_source_sha256": HACC_REFERENCE_SOURCE_SHA256,
                "candidate_source_sha256": HACC_CANDIDATE_SOURCE_SHA256,
                "proof_required": hacc_installed == "candidate"}
hacc_receipt_path = None
if args.hacc_proof_receipt is not None:
    hacc_receipt_path = ((ROOT / args.hacc_proof_receipt).resolve() if not args.hacc_proof_receipt.is_absolute()
                         else args.hacc_proof_receipt.resolve())
    assert any(hacc_receipt_path.is_relative_to((ROOT / directory).resolve())
               for directory in ("build", "docs/evidence")), "hacc receipt must be owned repository evidence"
    hacc_receipt_sha = sha(hacc_receipt_path)
    hacc_proof = json.loads(hacc_receipt_path.read_text())
    assert hacc_proof["status"] == "PASS"
    assert hacc_proof["helper_sha256"] == HACC_PROOF_HELPER_SHA256
    assert sha(ROOT / "scripts/test_ascal_hacc_equivalence.py") == HACC_PROOF_HELPER_SHA256
    assert hacc_proof["reference_sha256"] == HACC_REFERENCE_SOURCE_SHA256
    assert hacc_proof["candidate_sha256"] == HACC_CANDIDATE_SOURCE_SHA256
    assert hacc_proof["installed_source_sha256"] in (HACC_REFERENCE_SOURCE_SHA256, HACC_CANDIDATE_SOURCE_SHA256)
    assert hacc_proof["dependency_sha256"] == dependency_sha and hacc_proof["ghdl_image"] == image_id
    assert hacc_proof["outputs_proved"] == ["dif_v", "o_hacc", "o_hacc_next", "hcarry_v"]
    assert hacc_proof["ohresh_values"] == [1024, 2048, 4096]
    assert hacc_proof["positive_miters"] == 3 and hacc_proof["rejected_mutants"] == 9
    assert hacc_proof["native_boundary_random_cases"] == 135168
    assert hacc_proof["added_state"] == 0 and hacc_proof["added_cycles"] == 0
    assert hacc_proof["new_extracted_native_formal_warnings"] == 0
    for standard in ("93", "08"):
        analysis = hacc_proof["full_file_analysis"][standard]
        assert analysis["reference"] == analysis["candidate"] == "PASS"
        assert analysis["inherited_Whide_count_per_file"] == 10 and analysis["new_warnings"] == 0
        assert analysis["normalized_diagnostics_equal"] is True
    for relative, expected_sha in hacc_proof["artifacts"].items():
        artifact = (hacc_receipt_path.parent / relative).resolve()
        assert artifact.is_relative_to(hacc_receipt_path.parent), "unsafe hacc artifact path"
        assert artifact.is_file() and sha(artifact) == expected_sha, ("hacc artifact mismatch", relative)
    assert (hacc_receipt_path.parent / "full_reference.vhd").read_bytes() == hacc_reference_bytes
    assert (hacc_receipt_path.parent / "full_candidate.vhd").read_bytes() == hacc_candidate_bytes
    hacc_binding.update(proof_receipt=str(hacc_receipt_path.relative_to(ROOT)),
                        proof_receipt_sha256=hacc_receipt_sha,
                        proof_helper_sha256=HACC_PROOF_HELPER_SHA256,
                        all_proof_artifacts_verified=True)
else:
    assert hacc_installed == "reference", "installed hacc reorder requires --hacc-proof-receipt"
source = SOURCE.read_text()
processes = re.findall(r"\bOSWEEP:PROCESS\(o_clk\) IS.*?END PROCESS OSWEEP;", source, re.S)
assert len(processes) == 1
needle = "IF o_hcpt+1<o_htotal THEN"
replacement = "IF o_htotal>0 AND o_hcpt<o_htotal-1 THEN"
candidate = processes[0]
assert candidate.count(replacement) == 1 and candidate.count(needle) == 0
reference = candidate.replace(replacement, needle)
assert reference.replace(needle, replacement) == candidate
assert candidate_bytes.count(replacement.encode()) == 1 and candidate_bytes.count(needle.encode()) == 0
reference_bytes = candidate_bytes.replace(replacement.encode(), needle.encode())
assert reference_bytes.replace(needle.encode(), replacement.encode()) == candidate_bytes
reference_sha = hashlib.sha256(reference_bytes).hexdigest()
# Keep the pinned historical file unchanged. Only this independently proved
# one-assignment hacc update may be reversed for the historical full-file guard.
# The files analyzed below and the OSWEEP bodies remain the actual current pair.
historical_reference_bytes = reference_bytes
if hacc_installed == "candidate":
    assert historical_reference_bytes.count(HACC_CANDIDATE_ASSIGNMENT.encode()) == 1
    historical_reference_bytes = historical_reference_bytes.replace(HACC_CANDIDATE_ASSIGNMENT.encode(), HACC_REFERENCE_ASSIGNMENT.encode())
historical_reference_sha = hashlib.sha256(historical_reference_bytes).hexdigest()
assert historical_reference_sha == PRIVATE_PROOF_REFERENCE_SHA256, "unreviewed changes outside the two exact proven rewrites"
(OUT / "full_candidate.vhd").write_bytes(candidate_bytes)
(OUT / "full_reference.vhd").write_bytes(reference_bytes)
mutant = reference.replace(needle, "IF o_hcpt<o_htotal THEN")
subtype = re.findall(r"\bSUBTYPE uint12 IS natural RANGE 0 TO 4095;", source)
assert len(subtype) == 1
function = re.findall(r"\bFUNCTION to_std_logic \(a : boolean\).*?END FUNCTION to_std_logic;", source, re.S)
assert len(function) == 1
plain_process = re.sub(r"--[^\n]*", "", reference)
state_names = sorted(set(re.findall(r"\b(o_\w+)\s*(?:\([^;]*?\))?\s*<=", plain_process)))
ids = set(re.findall(r"\b(?:o_\w+|at_config_retime|AT_LOCAL_CONFIG|vtotal)\b", plain_process))
context_names = sorted(ids - set(state_names) - {"o_clk"})
types = {}
for names, kind in re.findall(r"\bSIGNAL\s+([a-zA-Z0-9_, ]+)\s*:\s*([^;]+);", source, re.I):
    for name in names.replace(" ", "").split(","):
        types[name] = kind.strip().split(":=")[0].strip()
types.update(o_ce="std_logic", at_config_retime="std_logic", AT_LOCAL_CONFIG="boolean", vtotal="uint12")
assert set(state_names + context_names) <= set(types)
assert all(types[x] in ("uint12", "boolean", "std_logic", "unsigned(0 TO 11)") for x in state_names + context_names)

def record(name, fields):
    return "TYPE " + name + " IS RECORD\n" + "\n".join(f"  {x} : {types[x]};" for x in fields) + "\nEND RECORD;"

package = "LIBRARY ieee; USE ieee.std_logic_1164.ALL; USE ieee.numeric_std.ALL;\nPACKAGE sweep_types IS\n" + subtype[0] + "\n" + record("sweep_state", state_names) + "\n" + record("sweep_context", context_names) + "\nEND PACKAGE;\n"
(OUT / "sweep_types.vhd").write_text(package)
(OUT / "reference_process.vhd.txt").write_text(reference)
(OUT / "candidate_process.vhd.txt").write_text(candidate)

def entity(name, body):
    # Add only a private arbitrary-state load branch. The original complete
    # process body, its clock enable and last-assignment priorities stay intact.
    hook = "IF rising_edge(o_clk) THEN"
    assert body.count(hook) == 1
    load = "\nIF seed='1' THEN\n" + "\n".join(f"  {x}<=state_seed.{x};" for x in state_names) + "\nELSE\n"
    wrapped = body.replace(hook, hook + load)
    end_hook = "END PROCESS OSWEEP;"
    wrapped = wrapped.replace(end_hook, "END IF;\n" + end_hook)
    # The inserted extra END IF closes the outer edge conditional; the original
    # final END IF now closes the private seed branch. Nested priorities remain.
    declarations = "\n".join(f"SIGNAL {x} : {types[x]};" for x in state_names + context_names)
    assignments = "\n".join(f"{x}<=context_in.{x};" for x in context_names)
    assignments += "\n" + "\n".join(f"state_out.{x}<={x};" for x in state_names)
    return f"""LIBRARY ieee; USE ieee.std_logic_1164.ALL; USE ieee.numeric_std.ALL;
USE work.sweep_types.ALL;
ENTITY {name} IS PORT(o_clk,seed : IN std_logic; state_seed : IN sweep_state;
                     context_in : IN sweep_context; state_out : OUT sweep_state); END;
ARCHITECTURE extracted OF {name} IS
{declarations}
{function[0]}
BEGIN
{assignments}
{wrapped}
END;
"""

for name, body in (("sweep_reference", reference), ("sweep_candidate", candidate), ("sweep_mutant", mutant)):
    (OUT / f"{name}.vhd").write_text(entity(name, body))

def miter(name, variant):
    return f"""LIBRARY ieee; USE ieee.std_logic_1164.ALL; USE ieee.numeric_std.ALL;
USE work.sweep_types.ALL;
ENTITY {name} IS PORT(o_clk,seed : IN std_logic; state_seed : IN sweep_state;
                     context_in : IN sweep_context; match : OUT std_logic); END;
ARCHITECTURE compare OF {name} IS SIGNAL a,b : sweep_state;
BEGIN
ref: ENTITY work.sweep_reference PORT MAP(o_clk,seed,state_seed,context_in,a);
dut: ENTITY work.{variant} PORT MAP(o_clk,seed,state_seed,context_in,b);
match<='1' WHEN a=b ELSE '0';
END;
"""

(OUT / "sweep_miter.vhd").write_text(miter("sweep_miter", "sweep_candidate"))
(OUT / "sweep_mutant_miter.vhd").write_text(miter("sweep_mutant_miter", "sweep_mutant"))

# Native VHDL exhaustive predicate: 16,777,216 legal x/t pairs. Integer
# expressions retain x+1=4096 and t-1=-1 rather than unsigned twelve-bit wrap.
predicate_tb = f"""LIBRARY ieee; USE ieee.std_logic_1164.ALL; USE work.sweep_types.ALL;
ENTITY predicate_tb IS END; ARCHITECTURE test OF predicate_tb IS BEGIN
PROCESS VARIABLE o_hcpt,o_htotal : uint12; VARIABLE a,b,m : boolean;
VARIABLE bad : natural:=0;
BEGIN
FOR t IN 0 TO 4095 LOOP FOR x IN 0 TO 4095 LOOP
o_hcpt:=x; o_htotal:=t;
a:=o_hcpt+1<o_htotal; b:=o_htotal>0 AND o_hcpt<o_htotal-1;
m:=o_hcpt<o_htotal;
ASSERT a=b REPORT "Actual VHDL predicates differ" SEVERITY failure;
ASSERT a=(integer(t)-integer(x)>1) REPORT "Independent integer-distance oracle differs" SEVERITY failure;
IF a/=m THEN bad:=bad+1; END IF;
END LOOP; END LOOP;
ASSERT bad=4095 REPORT "Off-by-one control not detected exhaustively" SEVERITY failure;
REPORT "PREDICATE_PASS pairs=16777216 mutant_counterexamples=4095";
WAIT; END PROCESS; END;
"""
(OUT / "predicate_tb.vhd").write_text(predicate_tb)

# Independently modeled edge transitions, checked against actual complete
# extracted processes. Use records so every state bit is compared each edge.
oracle = """
FUNCTION edge_oracle(q : sweep_state; c : sweep_context) RETURN sweep_state IS
VARIABLE n : sweep_state:=q;
BEGIN
IF c.o_ce='1' THEN
IF integer(c.o_htotal)-integer(q.o_hcpt)>1 THEN n.o_hcpt:=(q.o_hcpt+1) MOD 4096;
ELSE
n.o_hcpt:=0;
IF q.o_vcpt_sync<4095 THEN n.o_vcpt_sync:=q.o_vcpt_sync+1; END IF;
IF integer(c.o_vtotal)-integer(q.o_vcpt_pre3)<=1 THEN n.o_vcpt_pre3:=0;
ELSIF q.o_vrr_sync2 THEN n.o_vcpt_pre3:=c.o_vsstart; n.o_sync:=false;
ELSE n.o_vcpt_pre3:=(q.o_vcpt_pre3+1) MOD 4096; END IF;
n.o_vcpt_pre2:=q.o_vcpt_pre3; n.o_vcpt_pre:=q.o_vcpt_pre2; n.o_vcpt:=q.o_vcpt_pre;
END IF;
n.o_end(0):=to_std_logic(q.o_vcpt>=c.o_vdisp);
n.o_dev(0):=to_std_logic(q.o_hcpt<c.o_hdisp AND q.o_vcpt<c.o_vdisp);
n.o_pev(0):=to_std_logic(q.o_hcpt>=c.o_hmin AND q.o_hcpt<=c.o_hmax AND q.o_vcpt>=c.o_vmin AND q.o_vcpt<=c.o_vmax);
n.o_hsv(0):=to_std_logic(q.o_hcpt>=c.o_hsstart AND q.o_hcpt<c.o_hsend);
n.o_vsv(0):=to_std_logic((q.o_vcpt=c.o_vsstart AND q.o_hcpt>=c.o_hsstart) OR (q.o_vcpt>c.o_vsstart AND q.o_vcpt<c.o_vsend) OR (q.o_vcpt=c.o_vsend AND q.o_hcpt<c.o_hsstart));
n.o_vss:=to_std_logic(q.o_vcpt_pre2>=c.o_vmin AND q.o_vcpt_pre2<=c.o_vmax);
n.o_hsv(1 TO 11):=q.o_hsv(0 TO 10); n.o_vsv(1 TO 11):=q.o_vsv(0 TO 10);
n.o_dev(1 TO 11):=q.o_dev(0 TO 10); n.o_pev(1 TO 11):=q.o_pev(0 TO 10); n.o_end(1 TO 11):=q.o_end(0 TO 10);
IF c.o_run='0' THEN n.o_hsv(2):='0'; n.o_vsv(2):='0'; n.o_dev(2):='0'; n.o_pev(2):='0'; n.o_end(2):='0'; END IF;
END IF;
n.o_vcpt_sync2:=q.o_vcpt_sync; n.o_vrr_min:=q.o_vcpt_sync2<c.o_vtotal;
n.o_vrr_min2:=q.o_vrr_min; n.o_vrr_max:=q.o_vcpt_sync2<c.o_vrrmax; n.o_vrr_max2:=q.o_vrr_max;
IF c.o_isync2='1' THEN n.o_vcpt_sync:=0; n.o_sync_max:=q.o_vrr_max2; IF q.o_vrr_min2 THEN n.o_sync:=true; END IF; END IF;
n.o_vcpt2:=q.o_vcpt_pre3;
n.o_vrr_sync:=c.o_vrr='1' AND (q.o_sync OR q.o_sync_max) AND q.o_vcpt2>=c.o_vdisp AND q.o_vcpt2<c.o_vsstart;
n.o_vrr_sync2:=q.o_vrr_sync;
IF c.AT_LOCAL_CONFIG AND c.at_config_retime='1' THEN
n.o_hcpt:=0;
IF c.vtotal>0 THEN n.o_vcpt_pre3:=c.vtotal-1; n.o_vcpt_pre2:=c.vtotal-1; n.o_vcpt_pre:=c.vtotal-1; n.o_vcpt:=c.vtotal-1; n.o_vcpt2:=c.vtotal-1;
ELSE n.o_vcpt_pre3:=0; n.o_vcpt_pre2:=0; n.o_vcpt_pre:=0; n.o_vcpt:=0; n.o_vcpt2:=0; END IF;
n.o_dev:=(OTHERS=>'0'); n.o_pev:=(OTHERS=>'0'); n.o_hsv:=(OTHERS=>'0'); n.o_vsv:=(OTHERS=>'0'); n.o_end:=(OTHERS=>'1');
n.o_vcpt_sync:=0; n.o_sync:=false; n.o_sync_max:=false; n.o_vrr_sync:=false; n.o_vrr_sync2:=false;
END IF;
RETURN n; END FUNCTION;
"""

def random_assignment(prefix, names):
    statements=[]
    for x in names:
        kind=types[x]
        expr="rand12" if kind=="uint12" else "rand12 MOD 2=1" if kind=="boolean" else "to_std_logic(rand12 MOD 2=1)" if kind=="std_logic" else "to_unsigned(rand12,12)"
        statements.append(f"{prefix}.{x}:={expr};")
    return "\n".join(statements)

transition_tb = f"""LIBRARY ieee; USE ieee.std_logic_1164.ALL; USE ieee.numeric_std.ALL; USE std.env.ALL;
USE work.sweep_types.ALL;
ENTITY transition_tb IS END;
ARCHITECTURE test OF transition_tb IS
SIGNAL clk,seed : std_logic:='0'; SIGNAL s,observed_reference,observed_candidate : sweep_state; SIGNAL observed_context : sweep_context;
{function[0]}
{oracle}
BEGIN
ref: ENTITY work.sweep_reference PORT MAP(clk,seed,s,observed_context,observed_reference);
dut: ENTITY work.sweep_candidate PORT MAP(clk,seed,s,observed_context,observed_candidate);
PROCESS
VARIABLE q,e : sweep_state; VARIABLE v : sweep_context;
VARIABLE rng : unsigned(31 DOWNTO 0):=x"2A351C81"; VARIABLE cases,edges : natural:=0;
IMPURE FUNCTION rand12 RETURN natural IS BEGIN
rng:=rng(30 DOWNTO 0) & (rng(31) XOR rng(21) XOR rng(1) XOR rng(0)); RETURN to_integer(rng(11 DOWNTO 0)); END;
PROCEDURE pulse IS BEGIN clk<='0'; WAIT FOR 1 ns; clk<='1'; WAIT FOR 1 ns; clk<='0'; WAIT FOR 1 ns; END;
PROCEDURE check IS BEGIN
s<=q; observed_context<=v; seed<='1'; pulse;
ASSERT observed_reference=q AND observed_candidate=q REPORT "Arbitrary-state seed differs" SEVERITY failure;
seed<='0';
FOR j IN 0 TO 3 LOOP
IF j>0 THEN {random_assignment('v', context_names)} END IF;
observed_context<=v; e:=edge_oracle(q,v); pulse;
ASSERT observed_reference=e REPORT "Original complete process disagrees with independent edge oracle" SEVERITY failure;
ASSERT observed_candidate=e REPORT "Private candidate disagrees with independent edge oracle" SEVERITY failure;
q:=e; edges:=edges+1;
END LOOP; cases:=cases+1; END;
BEGIN
FOR i IN 0 TO 9999 LOOP
{random_assignment('q', state_names)}
{random_assignment('v', context_names)}
-- Directed boundary cross-product starts from arbitrary complete state.
IF i<64 THEN
CASE i MOD 4 IS WHEN 0=>v.o_htotal:=0; q.o_hcpt:=4095;
WHEN 1=>v.o_htotal:=4095; q.o_hcpt:=4094;
WHEN 2=>v.o_htotal:=1; q.o_hcpt:=0;
WHEN OTHERS=>v.o_htotal:=4095; q.o_hcpt:=4093; END CASE;
v.o_ce:=to_std_logic((i/4) MOD 2=1); v.AT_LOCAL_CONFIG:=(i/8) MOD 2=1;
v.at_config_retime:=to_std_logic((i/16) MOD 2=1); v.o_isync2:=to_std_logic((i/32) MOD 2=1);
v.vtotal:=0;
END IF; check;
END LOOP;
REPORT "TRANSITION_PASS cases=" & integer'image(cases) & " edges=" & integer'image(edges);
stop; WAIT; END PROCESS;
END;
"""
(OUT / "transition_tb.vhd").write_text(transition_tb)

command = """set -e
ghdl --version > ghdl-version.txt
for standard in 93 08; do
  for variant in reference candidate; do
    mkdir -p full-$variant-$standard
    if ! ghdl -a --std=$standard --workdir=full-$variant-$standard /work/sys/at_cdc_snapshot.vhd full_$variant.vhd > full-$variant-$standard/analysis.log 2>&1; then
      cat full-$variant-$standard/analysis.log
      exit 1
    fi
  done
done
echo FULL_SCALER_ANALYSIS_PASS_STANDARDS_93_08
ghdl -a --std=93 sweep_types.vhd sweep_reference.vhd sweep_candidate.vhd sweep_mutant.vhd sweep_miter.vhd sweep_mutant_miter.vhd predicate_tb.vhd
ghdl -e --std=93 predicate_tb
ghdl -r --std=93 predicate_tb --assert-level=error
ghdl -a --std=08 sweep_types.vhd sweep_reference.vhd sweep_candidate.vhd transition_tb.vhd
ghdl -e --std=08 transition_tb
ghdl -r --std=08 transition_tb --assert-level=error
ghdl synth --std=93 --out=verilog sweep_miter > sweep_miter.v
ghdl synth --std=93 --out=verilog sweep_mutant_miter > sweep_mutant_miter.v
"""
run("native-vhdl", ["docker", "run", "--rm", "--pull=never", "-v", f"{ROOT}:/work:ro", "-v", f"{OUT}:/results", "-w", "/results", image_id, "bash", "-lc", command])
# The complete scaler already has ten declaration-hiding diagnostics. Compare
# entire diagnostics, source lines and carets after normalizing only filenames;
# also pin their class, exact messages, source locations and count. Any changed
# or additional warning fails. Extracted proof and synthesis remain warning-free.
full_analysis = {}
for standard in (93, 8):
    standard_name = "08" if standard == 8 else "93"
    diagnostics = []
    for variant in ("reference", "candidate"):
        diagnostic_text = (OUT / f"full-{variant}-{standard_name}/analysis.log").read_text()
        normalized = diagnostic_text.replace(f"full_{variant}.vhd", "full_scaler.vhd")
        matches = re.findall(r'^full_scaler\.vhd:(\d+):(\d+):warning: (.*?) \[-Whide\]$', normalized, re.M)
        assert [(int(line), int(column), message) for line, column, message in matches] == EXPECTED_HIDE_DIAGNOSTICS, (variant, standard_name, "unexpected full-file diagnostics")
        warning_blocks = normalized.splitlines()
        assert len(warning_blocks) == 3 * len(EXPECTED_HIDE_DIAGNOSTICS), "unexpected additional full-file diagnostic text"
        for index, (line, _, _) in enumerate(EXPECTED_HIDE_DIAGNOSTICS):
            # GHDL renders literal source tabs at eight-column tab stops.
            assert warning_blocks[index * 3 + 1] == source.splitlines()[line - 1].expandtabs(8), "diagnostic source anchor differs"
            assert re.fullmatch(r"\s*\^", warning_blocks[index * 3 + 2]), "unexpected diagnostic caret"
        diagnostics.append(normalized)
    assert diagnostics[0] == diagnostics[1], "reference/candidate full-file diagnostics differ"
    full_analysis[standard_name] = {"reference": "PASS", "candidate": "PASS",
                                   "unchanged_warning_count_per_variant": len(EXPECTED_HIDE_DIAGNOSTICS),
                                   "warning_class": "Whide", "new_warnings": 0,
                                   "normalized_diagnostics_equal": True}
assert "warning:" not in (OUT / "native-vhdl.log").read_text(), "unexpected native VHDL diagnostic"
for name in ("sweep_miter", "sweep_mutant_miter"):
    script=f"read_verilog {name}.v; prep -top {name}; flatten; opt; sat -seq 3 -set-at 1 seed 1 -set-at 2 seed 0 -set-at 3 seed 0 -prove match 1 -prove-skip 2 -verify -show-inputs -show-outputs"
    run(name, ["yosys", "-Q", "-p", script], expect=0 if name=="sweep_miter" else 1)
    log=(OUT/f"{name}.log").read_text()
    assert "SUCCESS" in log if name=="sweep_miter" else "proof did fail" in log

assert sha(SOURCE)==source_sha, "production source changed during proof"
assert sha(DEPENDENCY)==dependency_sha, "VHDL dependency changed during proof"
assert sha(__file__)==helper_sha, "proof helper changed during proof"
if hacc_receipt_path is not None:
    assert sha(hacc_receipt_path)==hacc_receipt_sha, "hacc proof receipt changed during terminal proof"
    assert sha(ROOT / "scripts/test_ascal_hacc_equivalence.py")==HACC_PROOF_HELPER_SHA256
receipt={"schema":1,"status":"OSWEEP_TERMINAL_COMPARE_EQUIVALENCE_PASS",
         "production_unchanged_during_proof":True,
         "sources_sha256":{"sys/ascal.vhd":source_sha,"sys/at_cdc_snapshot.vhd":dependency_sha,
                            "scripts/test_ascal_terminal_equivalence.py":helper_sha},
         "reconstructed_reference_sha256":reference_sha,
         "private_proof_reference_sha256":PRIVATE_PROOF_REFERENCE_SHA256,
         "reference_matches_private_proof":historical_reference_sha==PRIVATE_PROOF_REFERENCE_SHA256,
         "historical_reference_after_exact_hacc_undo_sha256":historical_reference_sha,
         "historical_reference_normalization":"reverse independently source-bound hacc assignment only" if hacc_installed=="candidate" else "none",
         "hacc_source_binding":hacc_binding,
         "ghdl_image_id":image_id,
         "full_scaler_vhdl_analysis":full_analysis,
         "extracted_process_native_and_synthesis_warnings":0,
         "domain":"actual VHDL uint12 natural0..4095; integer intermediates, no unsigned wrap",
         "rewrite":{"reference":needle,"candidate":replacement},
         "exhaustive_predicate_pairs":16777216,"predicate_mutant_counterexamples":4095,
         "native_process_cases":10000,"native_process_edges":40000,
         "formal":"actual GHDL-synthesized complete processes; arbitrary seeded state, all context fields unconstrained; one-step induction basis after arbitrary-state load",
         "state_fields":state_names,"context_fields":context_names,
         "negative_control":"wrong end-line predicate x<t rejected natively and by complete-process SAT",
         "limits":["actual extracted production process proof", "full-file analysis is not whole-scaler regression or Quartus placement/timing proof", "all fields modeled as binary legal values; std_logic unknowns not architectural inputs"],
         "artifacts_sha256":{str(p.relative_to(OUT)):sha(p) for p in sorted(OUT.rglob("*")) if p.is_file() and p.name!="receipt.json"}}
(OUT/"receipt.json").write_text(json.dumps(receipt,indent=2)+"\n")
print(json.dumps({"status":receipt["status"],"receipt":str(OUT/"receipt.json")}))
