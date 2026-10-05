#!/usr/bin/env python3
"""Prove the scaler horizontal-accumulator reorder without changing production RTL.

Run with existing GHDL Docker and Yosys tools (normally from WSL). Both the
pre-reorder and installed one-line variant are accepted only at their exact
source pins. The complete horizontal arithmetic block is extracted from the
reference, including its original branch, accumulator, next and carry outputs.
This is a combinational cone proof, not a whole-scaler transition proof.
"""
from pathlib import Path
import argparse
import difflib
import hashlib
import json
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "sys/ascal.vhd"
DEPENDENCY = ROOT / "sys/at_cdc_snapshot.vhd"
IMAGE = "ghdl/ghdl:ubuntu22-llvm-11"
IMAGE_PIN = "sha256:278c884bb99cb6e02ee31732da673a5fd537b52da5789191eff28a51b905a36b"
REFERENCE_PIN = "412aa4c447e9b6389600dabb0072ffdc5bffdd14a310962e2dc5ebff01be5186"
CANDIDATE_PIN = "8a8382913f007cf7405aad235d6df9558ec14fc493251e31783ddb00031fd687"
OLD = "o_hacc_next<=(dif_v + 2*o_ihsize + (4*OHRESH)) MOD (4*OHRESH);"
NEW = "o_hacc_next<=(o_hacc_next + 2*o_ihsize - 2*o_hsize + (8*OHRESH)) MOD (4*OHRESH);"
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

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output", type=Path, default=Path("build/ascal-hacc-equivalence"),
                    help="fresh output directory under this repository's build directory")
args = parser.parse_args()
OUT = (ROOT / args.output).resolve() if not args.output.is_absolute() else args.output.resolve()
assert OUT.is_relative_to((ROOT / "build").resolve()), "output must remain inside repository build"
assert not OUT.exists(), "preserve previous proof evidence; output must be fresh"
OUT.mkdir(parents=True)

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def digest(data):
    return hashlib.sha256(data).hexdigest()

def run(name, command, expected=0):
    with (OUT / (name + ".log")).open("w") as stream:
        result = subprocess.run(command, cwd=OUT, stdout=stream, stderr=subprocess.STDOUT)
    assert result.returncode == expected, (name, result.returncode, "see preserved log")

source_bytes = SOURCE.read_bytes()
source_sha = digest(source_bytes)
helper_sha = sha(__file__)
dependency_sha = sha(DEPENDENCY)
if source_sha == REFERENCE_PIN:
    assert source_bytes.count(OLD.encode()) == 1 and NEW.encode() not in source_bytes
    reference_bytes = source_bytes
    candidate_bytes = source_bytes.replace(OLD.encode(), NEW.encode())
    installed = "reference"
elif source_sha == CANDIDATE_PIN:
    assert source_bytes.count(NEW.encode()) == 1 and OLD.encode() not in source_bytes
    candidate_bytes = source_bytes
    reference_bytes = source_bytes.replace(NEW.encode(), OLD.encode())
    installed = "candidate"
else:
    raise AssertionError("actual scaler differs from the reviewed reference/candidate pins")
assert digest(reference_bytes) == REFERENCE_PIN
assert digest(candidate_bytes) == CANDIDATE_PIN
assert reference_bytes.replace(OLD.encode(), NEW.encode()) == candidate_bytes
assert candidate_bytes.replace(NEW.encode(), OLD.encode()) == reference_bytes
(OUT / "full_reference.vhd").write_bytes(reference_bytes)
(OUT / "full_candidate.vhd").write_bytes(candidate_bytes)
(OUT / "candidate.diff").write_text("".join(difflib.unified_diff(
    reference_bytes.decode().splitlines(True), candidate_bytes.decode().splitlines(True),
    fromfile="sys/ascal.vhd", tofile="candidate/sys/ascal.vhd")))
reference_source = reference_bytes.decode()
for anchor in (
    "SUBTYPE uint12 IS natural RANGE 0 TO 4095;",
    "SIGNAL o_hsize,o_vsize : uint12;",
    "SIGNAL o_ihsize,o_ihsizem,o_ivsize : uint12;",
    "SIGNAL o_hacc,o_hacc_ini,o_hacc_next,o_vacc,o_vacc_next,o_vacc_ini : natural RANGE 0 TO 4*OHRESH-1;",
    "Scalaire:PROCESS (o_clk,o_reset_na) IS",
    "VARIABLE hcarry_v,vcarry_v : boolean;",
    "VARIABLE dif_v : natural RANGE 0 TO 8*OHRESH-1;",
    "CONSTANT OHRESH : natural := ohres_h(OHRES);",
):
    assert reference_source.count(anchor) == 1, ("source-width/control anchor", anchor)
function = re.findall(r"FUNCTION ohres_h\(CONSTANT r : natural\) RETURN natural IS.*?END FUNCTION;",
                      reference_source, re.S)
assert len(function) == 1
assert re.sub(r"\s+", "", function[0]) == (
    "FUNCTIONohres_h(CONSTANTr:natural)RETURNnaturalISBEGINCASErIS"
    "WHEN1024=>RETURN1024;WHEN2048=>RETURN2048;WHENOTHERS=>RETURN4096;ENDCASE;ENDFUNCTION;")
(OUT / "ohres_h.actual.vhd.txt").write_text(function[0])
pattern = r"dif_v:=\(o_hacc_next - 2\*o_hsize \+ \(8\*OHRESH\)\) MOD \(8\*OHRESH\);\s*IF dif_v>=4\*OHRESH THEN.*?hcarry_v:=true;\s*END IF;"
blocks = re.findall(pattern, reference_source, re.S)
assert len(blocks) == 1
reference = blocks[0]
assert re.sub(r"\s+", "", reference) == (
    "dif_v:=(o_hacc_next-2*o_hsize+(8*OHRESH))MOD(8*OHRESH);"
    "IFdif_v>=4*OHRESHTHENo_hacc<=o_hacc_next;o_hacc_next<=o_hacc_next+2*o_ihsize;hcarry_v:=false;"
    "ELSEo_hacc<=dif_v;o_hacc_next<=(dif_v+2*o_ihsize+(4*OHRESH))MOD(4*OHRESH);hcarry_v:=true;ENDIF;")
candidate = reference.replace(OLD, NEW)
assert candidate_bytes.decode().count(candidate) == 1
(OUT / "reference.block.vhd.txt").write_text(reference)
(OUT / "candidate.block.vhd.txt").write_text(candidate)

def entity(name, body, bound, narrow=False):
    # Preserve every original expression and branch. Only connect output names
    # and Boolean carry to private ports; dif_out reports the actual variable.
    body = body.replace("o_hacc<=", "acc_out<=").replace("o_hacc_next<=", "next_out<=")
    body = body.replace("hcarry_v:=false;", "carry_out<='0';").replace("hcarry_v:=true;", "carry_out<='1';")
    result_bound = 4 * bound - 1 if narrow else 65535
    return f"""LIBRARY ieee; USE ieee.std_logic_1164.ALL; USE ieee.numeric_std.ALL;
ENTITY {name} IS PORT(o_hacc_next : IN natural RANGE 0 TO {4*bound-1};
o_hsize,o_ihsize : IN natural RANGE 0 TO 4095;
acc_out,next_out : OUT natural RANGE 0 TO {result_bound};
dif_out : OUT natural RANGE 0 TO 65535; carry_out : OUT std_logic); END;
ARCHITECTURE extracted OF {name} IS CONSTANT OHRESH : natural := {bound};
BEGIN PROCESS(o_hacc_next,o_hsize,o_ihsize) IS VARIABLE dif_v : natural RANGE 0 TO 8*OHRESH-1;
BEGIN
{body}
dif_out<=dif_v;
END PROCESS; END;
"""

def miter(name, reference_name, candidate_name, bound):
    return f"""LIBRARY ieee; USE ieee.std_logic_1164.ALL; USE ieee.numeric_std.ALL;
ENTITY {name} IS PORT(o_hacc_next : IN natural RANGE 0 TO {4*bound-1};
o_hsize,o_ihsize : IN natural RANGE 0 TO 4095; match : OUT std_logic); END;
ARCHITECTURE compare OF {name} IS
SIGNAL a,b,c,d,e,f : natural RANGE 0 TO 65535; SIGNAL g,h : std_logic;
BEGIN
ref: ENTITY work.{reference_name} PORT MAP(o_hacc_next,o_hsize,o_ihsize,a,b,e,g);
dut: ENTITY work.{candidate_name} PORT MAP(o_hacc_next,o_hsize,o_ihsize,c,d,f,h);
match<='1' WHEN a=c AND b=d AND e=f AND g=h ELSE '0'; END;
"""

top_names = []
for bound in (1024, 2048, 4096):
    variants = {"reference": reference, "candidate": candidate,
        "mutant_coefficient": candidate.replace("- 2*o_hsize", "- o_hsize"),
        "mutant_one": candidate.replace("+ (8*OHRESH)) MOD (4*OHRESH)", "+ (8*OHRESH) + 1) MOD (4*OHRESH)"),
        "mutant_boundary": candidate.replace("IF dif_v>=4*OHRESH THEN", "IF dif_v>=4*OHRESH-1 THEN")}
    assert all(body != candidate for key, body in variants.items() if key.startswith("mutant"))
    for kind, body in variants.items():
        name = f"hacc_{kind}_{bound}"
        (OUT / (name + ".vhd")).write_text(entity(name, body, bound))
    for kind in ("candidate", "mutant_coefficient", "mutant_one", "mutant_boundary"):
        name = f"hacc_miter_{kind}_{bound}"
        top_names.append((name, not kind.startswith("mutant")))
        (OUT / (name + ".vhd")).write_text(miter(name, f"hacc_reference_{bound}", f"hacc_{kind}_{bound}", bound))
# Keep cost outputs identical to the original screen (without debug dif_out).
for kind, body in (("reference", reference), ("candidate", candidate)):
    name = "hacc_cost_" + kind
    wrapper = entity(name, body, 4096, narrow=True)
    wrapper = wrapper.replace("dif_out : OUT natural RANGE 0 TO 65535; ", "").replace("dif_out<=dif_v;\n", "")
    (OUT / (name + ".vhd")).write_text(wrapper)

native_instances = []
for index, bound in enumerate((1024, 2048, 4096)):
    for kind, suffix in (("reference", "r"), ("candidate", "c")):
        native_instances.append(f"{suffix}{index}: ENTITY work.hacc_{kind}_{bound} PORT MAP(aa{index},hh({index}),ii({index}),a{suffix}({index}),n{suffix}({index}),d{suffix}({index}),k{suffix}({index}));")
native = """LIBRARY ieee; USE ieee.std_logic_1164.ALL; USE ieee.numeric_std.ALL; USE std.env.ALL;
ENTITY hacc_native_tb IS END;
ARCHITECTURE native OF hacc_native_tb IS
TYPE narray IS ARRAY(0 TO 2) OF natural RANGE 0 TO 65535;
TYPE uint12array IS ARRAY(0 TO 2) OF natural RANGE 0 TO 4095;
TYPE sarray IS ARRAY(0 TO 2) OF std_logic;
SIGNAL aa:narray:=(OTHERS=>0); SIGNAL hh,ii:uint12array:=(OTHERS=>0);
SIGNAL aa0:natural RANGE 0 TO 4095:=0;
SIGNAL aa1:natural RANGE 0 TO 8191:=0;
SIGNAL aa2:natural RANGE 0 TO 16383:=0;
SIGNAL ar,ac,nr,nc,dr,dc:narray; SIGNAL kr,kc:sarray;
BEGIN
aa0<=aa(0);aa1<=aa(1);aa2<=aa(2);
""" + "\n".join(native_instances) + """
PROCESS IS
VARIABLE count:natural:=0; VARIABLE seed:natural:=233;
VARIABLE av,hv,iv,oh,m:natural; VARIABLE d,an,nn:natural; VARIABLE kn:std_logic;
PROCEDURE check(CONSTANT idx,aval,hval,ival,bound:natural) IS
VARIABLE diff,a_expected,n_expected:natural; VARIABLE k_expected:std_logic;
BEGIN
aa(idx)<=aval; hh(idx)<=hval; ii(idx)<=ival; WAIT FOR 1 ns;
diff:=(aval - 2*hval + 8*bound) MOD (8*bound);
IF diff>=4*bound THEN a_expected:=aval;n_expected:=aval+2*ival;k_expected:='0';
ELSE a_expected:=diff;n_expected:=(diff+2*ival+4*bound) MOD (4*bound);k_expected:='1'; END IF;
ASSERT ar(idx)=a_expected AND ac(idx)=a_expected AND nr(idx)=n_expected AND nc(idx)=n_expected
   AND dr(idx)=diff AND dc(idx)=diff AND kr(idx)=k_expected AND kc(idx)=k_expected
REPORT "native arithmetic mismatch" SEVERITY failure;
count:=count+1;
END PROCEDURE;
BEGIN
FOR idx IN 0 TO 2 LOOP
CASE idx IS WHEN 0=>oh:=1024;WHEN 1=>oh:=2048;WHEN OTHERS=>oh:=4096;END CASE;
m:=4*oh;
FOR h IN 0 TO 4095 LOOP
FOR isel IN 0 TO 1 LOOP
IF isel=0 THEN iv:=0; ELSE iv:=4095; END IF;
check(idx,0,h,iv,oh);check(idx,m-1,h,iv,oh);
check(idx,(2*h) MOD m,h,iv,oh);
check(idx,(2*h+m-1) MOD m,h,iv,oh);
check(idx,(2*h+1) MOD m,h,iv,oh);
END LOOP; END LOOP;
FOR r IN 0 TO 4095 LOOP
seed:=(seed*25173+13849) MOD 65521;av:=seed MOD m;
seed:=(seed*25173+13849) MOD 65521;hv:=seed MOD 4096;
seed:=(seed*25173+13849) MOD 65521;iv:=seed MOD 4096;
check(idx,av,hv,iv,oh);
END LOOP;
END LOOP;
ASSERT count=135168 REPORT "wrong native case count" SEVERITY failure;
REPORT "HACC_NATIVE_PASS cases=" & integer'image(count);
stop; WAIT; END PROCESS; END;
"""
(OUT / "hacc_native_tb.vhd").write_text(native)
image_id = subprocess.check_output(["docker", "image", "inspect", "--format={{.Id}}", IMAGE], text=True).strip()
assert image_id == IMAGE_PIN, "use the existing reviewed GHDL image; no download"
primitive_files = sorted(p.name for p in OUT.glob("hacc_*.vhd") if not p.name.startswith(("hacc_miter_", "hacc_native_")))
miter_files = sorted(p.name for p in OUT.glob("hacc_miter_*.vhd"))
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
"""
command += "ghdl -a --std=93 " + " ".join(primitive_files + miter_files) + "\n"
command += "\n".join(f"ghdl synth --std=93 --out=verilog {name} > {name}.v" for name, _ in top_names) + "\n"
command += "\n".join(f"ghdl synth --std=93 --out=verilog hacc_cost_{kind} > hacc_cost_{kind}.v" for kind in ("reference", "candidate")) + "\n"
native_primitives = [f"hacc_{kind}_{bound}.vhd" for bound in (1024, 2048, 4096) for kind in ("reference", "candidate")]
command += "ghdl -a --std=08 " + " ".join(native_primitives) + " hacc_native_tb.vhd\n"
command += "ghdl -e --std=08 hacc_native_tb\nghdl -r --std=08 hacc_native_tb --assert-level=error\n"
run("ghdl", ["docker", "run", "--rm", "--pull=never", "-v", f"{ROOT}:/work:ro", "-v", f"{OUT}:/results", "-w", "/results", image_id, "bash", "-lc", command])
ghdl_log = (OUT / "ghdl.log").read_text()
assert "warning:" not in ghdl_log
assert re.search(r"HACC_NATIVE_PASS cases=135168", ghdl_log)
assert len(ghdl_log.splitlines()) == 2, "unexpected extracted/native GHDL diagnostics"
full_analysis = {}
for standard in ("93", "08"):
    normalized_logs = []
    for variant, full_bytes in (("reference", reference_bytes), ("candidate", candidate_bytes)):
        text = (OUT / f"full-{variant}-{standard}/analysis.log").read_text()
        normalized = text.replace(f"full_{variant}.vhd", "full_scaler.vhd")
        diagnostics = re.findall(r'^full_scaler\.vhd:(\d+):(\d+):warning: (.*?) \[-Whide\]$', normalized, re.M)
        assert [(int(line), int(column), message) for line, column, message in diagnostics] == EXPECTED_HIDE_DIAGNOSTICS
        lines = normalized.splitlines()
        assert len(lines) == 3 * len(EXPECTED_HIDE_DIAGNOSTICS), "additional full-file diagnostics"
        full_lines = full_bytes.decode().splitlines()
        for index, (line, _, _) in enumerate(EXPECTED_HIDE_DIAGNOSTICS):
            assert lines[3 * index + 1] == full_lines[line - 1].expandtabs(8), "diagnostic source anchor differs"
            assert re.fullmatch(r"\s*\^", lines[3 * index + 2])
        normalized_logs.append(normalized)
    assert normalized_logs[0] == normalized_logs[1], "reference/candidate diagnostic drift"
    full_analysis[standard] = {"reference": "PASS", "candidate": "PASS", "inherited_Whide_count_per_file": 10, "new_warnings": 0, "normalized_diagnostics_equal": True}

worker = r'''from pathlib import Path
import json, subprocess
out=Path(__file__).resolve().parent
jobs=json.loads((out/"jobs.json").read_text())
for name,positive in jobs:
    mode="-verify" if positive else "-falsify"
    script=f"read_verilog {name}.v; hierarchy -check -top {name}; proc; flatten; opt; sat {mode} -prove match 1 -show-inputs -show-outputs"
    with (out/(name+".log")).open("w") as log:
        result=subprocess.run(["yosys","-Q","-p",script],cwd=out,stdout=log,stderr=subprocess.STDOUT)
    text=(out/(name+".log")).read_text()
    assert result.returncode==0 and "Warning:" not in text, (name,result.returncode)
    assert ("SUCCESS!" in text) if positive else ("FAIL!" in text), name
for kind in ("reference","candidate"):
    name=f"hacc_cost_{kind}"
    script=f"read_verilog {name}.v; synth -top {name} -flatten; stat; write_json {name}.json"
    with (out/(name+".log")).open("w") as log:
        result=subprocess.run(["yosys","-Q","-p",script],cwd=out,stdout=log,stderr=subprocess.STDOUT)
    assert result.returncode==0 and "Warning:" not in (out/(name+".log")).read_text()
(out/"yosys-version.txt").write_text(subprocess.check_output(["yosys","-V"],text=True))
'''
(OUT / "worker.py").write_text(worker)
(OUT / "jobs.json").write_text(json.dumps(top_names))
if sys.platform == "win32":
    wsl_root = "/mnt/d/GitHub/PCAT-286_MiSTer"
    worker_command = ["wsl.exe", "-d", "Ubuntu-24.04", "--", "python3", "-B", f"{wsl_root}/build/{OUT.name}/worker.py"]
else:
    worker_command = [sys.executable, "-B", str(OUT / "worker.py")]
run("formal-and-cost", worker_command)

def mapped_cost(kind):
    name = f"hacc_cost_{kind}"
    module = json.loads((OUT / (name + ".json")).read_text())["modules"][name]
    cells = module["cells"]
    assert all(not cell["type"].startswith(("$_DFF", "$_DLATCH")) for cell in cells.values())
    counts = {}
    for cell in cells.values():
        counts[cell["type"]] = counts.get(cell["type"], 0) + 1
    inputs = {key: set(value["bits"]) for key, value in module["ports"].items() if value["direction"] == "input"}
    outputs = {key: set(value["bits"]) for key, value in module["ports"].items() if value["direction"] == "output"}
    depth = {}
    for input_name, bits in inputs.items():
        levels = {bit: 0 for bit in bits if isinstance(bit, int)}
        for _ in range(len(cells) + 1):
            changed = False
            for cell in cells.values():
                ins = [b for port, bs in cell["connections"].items() if cell["port_directions"][port] == "input" for b in bs]
                known = [levels[b] for b in ins if b in levels]
                if not known:
                    continue
                level = max(known) + 1
                for port, bs in cell["connections"].items():
                    if cell["port_directions"][port] == "output":
                        for bit in bs:
                            if levels.get(bit, -1) < level:
                                levels[bit] = level
                                changed = True
            if not changed:
                break
        else:
            raise AssertionError("unexpected combinational loop")
        depth[input_name] = {key: max((levels[b] for b in bs if b in levels), default=0) for key, bs in outputs.items()}
    return {"cells": len(cells), "types": counts, "logic_depth_by_input_output": depth}

assert sha(SOURCE) == source_sha and sha(DEPENDENCY) == dependency_sha and sha(__file__) == helper_sha, "proof inputs changed"
receipt = {
    "status": "PASS", "scope": "source-extracted combinational horizontal arithmetic block; not full-scaler state equivalence or physical timing closure",
    "installed_variant": installed, "installed_source_sha256": source_sha, "helper_sha256": helper_sha,
    "reference_sha256": REFERENCE_PIN, "candidate_sha256": CANDIDATE_PIN,
    "dependency_sha256": dependency_sha, "ghdl_image": image_id,
    "delta": "one assignment; byte-exact full-file inverse replacement",
    "outputs_proved": ["dif_v", "o_hacc", "o_hacc_next", "hcarry_v"],
    "inputs": "arbitrary binary accumulator at declared 4*OHRESH width; arbitrary uint12 o_hsize and o_ihsize; no assumptions or reachability constraints",
    "ohresh_values": [1024, 2048, 4096], "positive_miters": 3, "rejected_mutants": 9,
    "native_boundary_random_cases": 135168, "added_state": 0, "added_cycles": 0,
    "range_semantics": "proof/native ports preserve complete arithmetic results up to 65535; unchanged negative branch may exceed original accumulator subtype for arbitrary states at smaller OHRESH, and is compared without truncation. This does not assume such states unreachable. For OHRESH4096 the branch-selected results always fit the original subtype.",
    "integer_bounds": "a<4*OHRESH, h/i<=4095, OHRESH>=1024; subtract numerator >=2; all intermediates <65536; positive MOD results fit. No integer-base subtraction overflow.",
    "full_file_analysis": full_analysis, "new_extracted_native_formal_warnings": 0,
    "cost_scope": "generic ABC mapping of actual OHRESH4096 arithmetic cone, original accumulator subtype, no debug dif output; not Quartus ALMs/slack",
    "cost": {kind: mapped_cost(kind) for kind in ("reference", "candidate")},
    "artifacts": {p.relative_to(OUT).as_posix(): sha(p) for p in OUT.rglob("*") if p.is_file()},
}
(OUT / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"status": "PASS", "receipt": str(OUT / "receipt.json"), "installed": installed, "cost": receipt["cost"]}, indent=2))
