#!/usr/bin/env python3
"""Prove the actual RTC byte conversion against its pre-optimization source."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess


ROOT = Path(__file__).resolve().parents[1]
RTL = Path("rtl/spk286_integration/spk286_at_rtc_cmos.sv")
FUNCTION = re.compile(
    r"    function automatic logic \[7:0\] binary_to_bcd\(.*?endfunction", re.S
)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def wrapper(name, function):
    return ("`timescale 1ns/1ps\n"
            + f"module {name}(input logic [7:0] byte_in, output logic [7:0] result);\n"
            + function + "\n    assign result = binary_to_bcd(byte_in);\nendmodule\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--reference", default="5198af1")
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    original_bytes = subprocess.check_output(
        ["git", "show", f"{args.reference}:{RTL.as_posix()}"], cwd=ROOT
    )
    candidate_bytes = (ROOT / RTL).read_bytes()
    original = original_bytes.decode().replace("\r\n", "\n")
    candidate = candidate_bytes.decode().replace("\r\n", "\n")
    old_matches = list(FUNCTION.finditer(original))
    new_matches = list(FUNCTION.finditer(candidate))
    if len(old_matches) != 1 or len(new_matches) != 1:
        raise ValueError("Expected exactly one actual binary_to_bcd function")
    old_function, new_function = old_matches[0].group(), new_matches[0].group()
    if candidate.replace(new_function, old_function) != original:
        raise ValueError("Other RTC logic changed: whole-module guard failed")
    if "/ 8'd10" not in old_function or "% 8'd10" not in old_function:
        raise ValueError("Reference is not the original byte-width arithmetic")
    baseline_dir = output / "baseline"
    baseline_dir.mkdir(exist_ok=True)
    (baseline_dir / RTL.name).write_text(original)
    lint_warnings = []
    for label, source in (("reference", baseline_dir / RTL.name),
                          ("candidate", ROOT / RTL)):
        lint = subprocess.run([
            "verilator", "--lint-only", "--Wall", "--top-module",
            "spk286_at_rtc_cmos", str(source)
        ], capture_output=True)
        log = lint.stdout + lint.stderr
        (output / f"rtc-{label}-wall.log").write_bytes(log)
        warnings = re.findall(
            r"^%Warning-([A-Z0-9_]+): .*?\.sv:\d+:\d+: (.*)$",
            log.decode(), re.M
        )
        if lint.returncode not in (0, 1) or (
            lint.returncode and not re.search(
                rb"%Error: Exiting due to \d+ warning\(s\)\s*$", log
            )
        ):
            raise RuntimeError("RTC module lint has a non-warning error")
        lint_warnings.append(warnings)
    eliminated = {
        ("UNUSEDSIGNAL", "Bits of signal are not used: 'tens'[7:4]"),
        ("UNUSEDSIGNAL", "Bits of signal are not used: 'ones'[7:4]"),
    }
    expected_remaining = [warning for warning in lint_warnings[0]
                          if warning not in eliminated]
    if expected_remaining != lint_warnings[1]:
        raise ValueError("RTC module Wall has a new or changed warning")
    print(f"RTC_WALL_NO_ADDED_WARNING existing={len(lint_warnings[1])}")
    for name, function in (("rtc_bcd_reference", old_function),
                           ("rtc_bcd_candidate", new_function)):
        (output / f"{name}.sv").write_text(wrapper(name, function))
    mutant = new_function.replace("8'd10: binary_to_bcd = 8'h10;",
                                  "8'd10: binary_to_bcd = 8'h11;", 1)
    if mutant == new_function:
        raise ValueError("Negative control did not mutate the actual truth table")
    (output / "rtc_bcd_mutant.sv").write_text(wrapper("rtc_bcd_mutant", mutant))
    for name, should_pass in (("rtc_bcd_candidate", True), ("rtc_bcd_mutant", False)):
        miter = output / f"{name}_miter.sv"
        miter.write_text(
            "module miter(input [7:0] value, output ok);\n"
            "wire [7:0] reference_result, candidate_result;\n"
            "rtc_bcd_reference reference_dut(value, reference_result);\n"
            f"{name} candidate_dut(value, candidate_result);\n"
            "assign ok = reference_result == candidate_result;\nendmodule\n"
        )
        script = output / f"{name}.ys"
        script.write_text(
            f'read_verilog -sv "{output / "rtc_bcd_reference.sv"}" '
            f'"{output / (name + ".sv")}" "{miter}"\n'
            "hierarchy -check -top miter\nproc\nflatten\nopt\nmemory_map\nopt\n"
            "sat -verify -prove ok 1 -show value -show reference_result "
            "-show candidate_result\n"
        )
        result = subprocess.run(["yosys", "-s", str(script)], capture_output=True)
        (output / f"{name}.log").write_bytes(result.stdout + result.stderr)
        success_marker = b"SAT proof finished - no model found: SUCCESS!"
        fail_marker = b"proof did fail"
        if should_pass:
            if result.returncode != 0 or success_marker not in result.stdout:
                raise RuntimeError("Actual RTL equivalence failed")
        elif result.returncode == 0 or fail_marker not in result.stderr:
            raise RuntimeError("Incorrect conversion was not rejected by SAT")
        print("RTC_BCD_EQUIVALENT" if should_pass else "RTC_BCD_MUTANT_REJECTED")
    if (ROOT / RTL).read_bytes() != candidate_bytes:
        raise ValueError("RTC source changed during proof")
    (output / "proof.json").write_text(json.dumps({
        "status": "PASS", "reference": args.reference,
        "reference_rtc_sha256": digest(original_bytes),
        "candidate_rtc_sha256": digest(candidate_bytes),
        "whole_module_guard": "Only binary_to_bcd differs",
        "module_wall": "No added warning; existing baseline warnings retained",
        "module_wall_warnings": lint_warnings[0],
        "input_domain": "All 256 concrete byte values, including invalid CMOS",
        "negative_control": "Value 10 changed from 0x10 to 0x11: rejected",
        "four_state_scope": "Separate Icarus conversion test",
        "sequential_change": False,
    }, indent=2) + "\n")


if __name__ == "__main__":
    main()
