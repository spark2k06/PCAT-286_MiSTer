#!/usr/bin/env python3
"""Freeze the pre-refactor keyboard and generate combinational probe modules."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

REFERENCE = "20cf243ee4df684e6cfeca3b0cf7c1fa3f6db60d"
SOURCE = "rtl/spk286_integration/spk286_at_keyboard.sv"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def probe(text, name):
    start = text.index("    wire [7:0] translated =")
    end = text.index("    assign keyboard_byte =")
    return f"""`timescale 1ns/1ps
module {name} (
    input logic [7:0] code,
    input logic pressed, extended, translate_set1, num_lock,
    input logic left_shift_q, right_shift_q,
    output logic [63:0] next_sequence,
    output logic [3:0] next_length
);
    logic [63:0] base_sequence;
    logic [3:0] base_length;
{text[start:end]}
endmodule
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError(output)
    reference_raw = subprocess.check_output(["git", "show", f"{REFERENCE}:{SOURCE}"], cwd=root)
    candidate_raw = (root / SOURCE).read_bytes()
    reference = reference_raw.decode().replace("\r\n", "\n")
    candidate = candidate_raw.decode().replace("\r\n", "\n")
    # Guard the scope independently of the simulation: all source outside
    # build_sequence, including the FIFO/sequential block, must be identical.
    start = "    always_comb begin : build_sequence"
    end = "    assign keyboard_byte ="
    for text in (reference, candidate):
        if text.count(start) != 1 or text.count(end) != 1:
            raise ValueError("Packing block markers missing/ambiguous")
    def outside(text):
        return text[:text.index(start)], text[text.index(end):]
    if outside(reference) != outside(candidate):
        raise ValueError("Keyboard change extends outside build_sequence")
    output.mkdir(parents=True)
    full_reference = reference.replace("module spk286_at_keyboard (",
                                       "module spk286_at_keyboard_reference (", 1)
    (output / "keyboard_reference.sv").write_text(full_reference)
    (output / "packing_reference.sv").write_text(probe(reference, "keyboard_packing_reference"))
    (output / "packing_candidate.sv").write_text(probe(candidate, "keyboard_packing_candidate"))
    sources = (SOURCE, "scripts/prepare_at_keyboard_packing.py",
               "scripts/test_at_keyboard_packing.sh",
               "sim/spk286_integration/spk286_at_keyboard_packing_tb.sv",
               "sim/spk286_integration/spk286_at_keyboard_cycle_equivalence_tb.sv")
    receipt = {"reference_commit": REFERENCE,
               "reference_git_blob_sha256": digest(reference_raw),
               "candidate_sha256": digest(candidate_raw),
               "scope_guard": "only build_sequence changed; other source text identical",
               "source_sha256": {path: digest((root / path).read_bytes()) for path in sources},
               "generated_sha256": {path.name: digest(path.read_bytes()) for path in output.glob("*.sv")}}
    (output / "sources.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(f"AT_KEYBOARD_PACKING_PREPARED reference={REFERENCE} scope=packing_only")


if __name__ == "__main__":
    main()
