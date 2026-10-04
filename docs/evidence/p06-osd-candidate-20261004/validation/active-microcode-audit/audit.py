"""Bounded source-generation and unchanged upstream contract audit."""
from pathlib import Path
import hashlib
import importlib.util
import json
import subprocess
import sys

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
VENDOR = ROOT / "vendor/spk286"

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

spec = importlib.util.spec_from_file_location("profile_builder", ROOT / "scripts/build_p06_profile_cpu.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)
rebuilt = builder.build(OUT / "rebuilt")
selected = VENDOR / "rtl/timed"
for name, path in rebuilt.items():
    if path.read_bytes() != (selected / name).read_bytes():
        raise RuntimeError(f"Selected generated source differs: {name}")
if (OUT / "rebuilt/generation.json").read_bytes() != (selected / "generation.json").read_bytes():
    raise RuntimeError("Selected generation manifest differs")

checks = {}
commands = {
    "microcode_coupling_roundtrip": [sys.executable, "-B", "-m", "tools.microcode.audit_microcode",
        "--output", str(OUT / "microcode")],
    "focused_upstream_units": [sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests",
        "-p", "test_microcode_audit.py"],
}
focused = (
    "test_microcode_events", "test_microcode_strings", "test_microcode_shift",
    "test_microcode_operands", "test_microcode_system_access", "test_singlestep_events",
    "test_singlestep_runner", "test_singlestep_byte_prefix", "test_singlestep_strings",
    "test_singlestep_shift", "test_rtl_sources",
)
commands["focused_adapters_and_microcode"] = [sys.executable, "-B", "-m", "unittest", *focused]
import os
env = dict(os.environ)
env["PYTHONPATH"] = os.pathsep.join((str(VENDOR), str(VENDOR / "tests")))
env["PYTHONDONTWRITEBYTECODE"] = "1"
for name, command in commands.items():
    result = subprocess.run(command, cwd=VENDOR, env=env, capture_output=True, text=True)
    log = OUT / f"{name}.log"
    log.write_text(result.stdout + result.stderr, newline="\n")
    checks[name] = {"returncode": result.returncode, "log": str(log.relative_to(ROOT)),
                    "sha256": sha(log), "command": command}
    if result.returncode:
        known = "FAIL: test_frozen_h01_rom_adds_only_the_eight_documented_checks (test_microcode_system_access.SystemAccessMicrocodeTests.test_frozen_h01_rom_adds_only_the_eight_documented_checks)"
        expected_failure = name == "focused_adapters_and_microcode" and known in result.stderr and "FAILED (failures=1)" in result.stderr and "ERROR:" not in result.stderr
        if not expected_failure:
            raise RuntimeError(f"Unexpected {name} failure; see {log}")
    print(name, "PASS" if result.returncode == 0 else "EXISTING_UPSTREAM_UNIT_FAILURE")

inputs = {p.relative_to(ROOT).as_posix(): sha(p) for p in (
    ROOT / "scripts/build_p06_profile_cpu.py",
    ROOT / "rtl/spk286_timing/spk286_instruction_schedule.sv",
    ROOT / "rtl/spk286_timing/spk286_instruction_timing.sv",
    ROOT / "scripts/check_p06_profile_components.py",
    ROOT / "sim/spk286_timing/spk286_instruction_schedule_tb.sv",
    ROOT / "sim/spk286_timing/spk286_profile_prefix_tb.sv",
    *sorted((VENDOR / "microcode/source").rglob("*.mc")),
    *sorted((VENDOR / "microcode/generated").glob("*")),
    *sorted((VENDOR / "rtl").glob("*.sv")),
    *sorted((VENDOR / "tools").rglob("*.py")),
    *sorted((VENDOR / "tests").rglob("*.py")),
    *sorted((VENDOR / "tests/fixtures").rglob("*.json")),
) if p.is_file()}
report = {
    "status": "PROFILE_GENERATION_AND_ACTIVE_MICROCODE_PASS_WITH_UPSTREAM_UNIT_FAILURE",
    "sources_sha256": inputs,
    "selected_sha256": {name: sha(selected / name) for name in (*rebuilt, "generation.json")},
    "checks": checks,
    "upstream_unit_failure": {
        "test": "test_microcode_system_access.SystemAccessMicrocodeTests.test_frozen_h01_rom_adds_only_the_eight_documented_checks",
        "detail": "Historical immediate/system-access fixture conversion swaps encoded operations171 and172 at word725; active current ESC-boundary microcode contract and roundtrip pass. Generated profile sources do not modify those originals or fixtures.",
        "action": "Reported upstream separately; preserved source and expectations.",
    },
    "scope": "Deterministic generated profile RTL and manifest; original microcode source/ROM/symbol contract and canonical roundtrip; focused existing Python microcode/SingleStep adapter unit checks. This is not an external SingleStep corpus CPU simulation, portable bus validation, FPGA synthesis or complete profile acceptance.",
}
(OUT / "receipt.json").write_text(json.dumps(report, indent=2) + "\n", newline="\n")
print(report["status"])
