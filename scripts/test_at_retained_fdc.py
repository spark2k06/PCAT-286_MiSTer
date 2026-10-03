#!/usr/bin/env python3
"""Run six bounded, paired retained-FDC directed cases on proven raw RTL.

Usage: test_at_retained_fdc.py --proof-directory DIR --output NEW_DIRECTORY

The proof directory must be a successful result of the current
prove_at_retained_fdc_write.py. Its active1 positive gold/gate sources contain
the actual bridge, source-extracted route, FDC wrapper, floppy and FIFO without
formal state cuts. This runner never reconstructs RTL or device decodes.
Separate A5 DMA512 and actual CPU/machine smoke receipts are not generated here.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time


ROOT = Path(__file__).resolve().parents[1]
SOURCE_FILES = {
    "rtl/spk286_integration/spk286_at_bus_bridge.sv",
    "rtl/spk286_integration/spk286_at_machine.sv",
    "rtl/spk286_integration/spk286_at_device_router.sv",
    "rtl/spk286_integration/spk286_at_storage_video.sv",
    "rtl/spk286_integration/spk286_at_fdc.sv",
    "rtl/common/floppy.v",
    "rtl/common/simple_fifo.v",
}
CASES = [
    ("composed-mode-0", 0, "spk286_at_retained_fdc_tb", 46,
     "RETAINED_FDC_COMPOSED_PASS"),
    ("composed-mode-1", 1, "spk286_at_retained_fdc_tb", 46,
     "RETAINED_FDC_COMPOSED_PASS"),
    ("malformed-mode-0", 0, "spk286_at_retained_fdc_malformed_tb", 22,
     "RETAINED_FDC_MALFORMED_PASS"),
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_path(value):
    """Resolve source roots recorded by either Windows or WSL proof runs."""
    value = value.replace("\\", "/")
    if os.name == "nt" and value.startswith("/mnt/"):
        return Path(value[5].upper() + ":" + value[6:]).resolve()
    if os.name != "nt" and len(value) > 2 and value[1:3] == ":/":
        return Path("/mnt/" + value[0].lower() + value[2:]).resolve()
    return Path(value).resolve()


def child_path(parent, value):
    result = (parent / value).resolve()
    assert result.is_relative_to(parent), ("Path outside proof", value)
    return result


def run(log, command):
    """Bound each compilation/run to 300 seconds; terminate its process group."""
    with log.open("w") as stream:
        process = subprocess.Popen(
            list(map(str, command)), stdout=stream, stderr=subprocess.STDOUT,
            start_new_session=(os.name != "nt"),
        )
        try:
            result = process.wait(timeout=300)
        except subprocess.TimeoutExpired:
            if os.name == "nt":
                process.kill()
            else:
                os.killpg(process.pid, signal.SIGKILL)
            process.wait()
            raise RuntimeError(f"300-second timeout: {log}") from None
    assert result == 0, ("Tool failed", str(log), result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proof-directory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    proof = args.proof_directory.resolve()
    output = args.output.resolve()
    assert not output.exists(), "A fresh output directory is required"
    assert not output.is_relative_to(proof), "Output must be outside frozen proof"

    proof_receipt = proof / "receipt.json"
    proof_script = ROOT / "scripts/prove_at_retained_fdc_write.py"
    receipt = json.loads(proof_receipt.read_text())
    assert receipt["status"] == "RETAINED_FDC_WRITE_PORTABLE_EQUIVALENCE_PASS"
    assert receipt["proof_script_sha256"] == sha(proof_script), "Stale proof tool"
    assert set(receipt["source_sha256"]) == SOURCE_FILES
    assert {
        (p["profile"], p["complete_on_cpu_sample"])
        for p in receipt["profiles"]
    } == {("active1", 0), ("active1", 1), ("default0", 0), ("default0", 1)}
    inputs = {proof_receipt: sha(proof_receipt), proof_script: sha(proof_script),
              Path(__file__).resolve(): sha(Path(__file__).resolve())}
    for side in ("reference", "candidate"):
        source_root = source_path(receipt[side + "_root"])
        for relative, digests in receipt["source_sha256"].items():
            path = child_path(source_root, relative)
            assert sha(path) == digests[side], ("Changed proof input", str(path))
            inputs[path] = digests[side]
    for relative, digest in receipt["artifacts"].items():
        path = child_path(proof, relative)
        assert sha(path) == digest, ("Changed proof artifact", relative)
        inputs[path] = digest
    for _, _, top, _, _ in CASES:
        path = ROOT / "sim/spk286_integration" / (top + ".sv")
        inputs[path] = sha(path)

    output.mkdir(parents=True)
    report = {
        "status": "RUNNING",
        "proof_directory": str(proof),
        "proof_receipt_sha256": sha(proof_receipt),
        "proof_script_sha256": sha(proof_script),
        "runner_sha256": sha(Path(__file__).resolve()),
        "source_sha256": receipt["source_sha256"],
        "cases": [],
        "scope": "Six runs: actual composed raw bridge/route/FDC/core/FIFO in "
                 "both CPU completion modes and direct malformed endpoint mode0; "
                 "Icarus plus Verilator --assert -j2. All observed public outputs "
                 "and raw common-core outputs unmasked; complete before/after CSV "
                 "compared within each simulator. External memory/3F6 completion "
                 "boundary only. No FDC mock or formal state cuts in simulation.",
        "limits": "Not the separate A5 DMA512 or actual CPU/machine smoke bank; "
                  "no fullmachine equivalence, full regression, four-state formal "
                  "proof, timing/resource-fit or hardware claim. Uninitialized "
                  "values may differ across simulators; no cross-simulator "
                  "byte-identity claim. Tracing starts after reset.",
    }

    def save():
        (output / "receipt.json").write_text(json.dumps(report, indent=2) + "\n")

    save()
    start = time.monotonic()
    try:
        for label, mode, top, observed_outputs, pass_label in CASES:
            case = output / label
            case.mkdir()
            files = []
            for side in ("gold", "gate"):
                relative = f"active1/mode-{mode}/positive/{side}.sv"
                assert relative in receipt["artifacts"]
                original = child_path(proof, relative)
                text = original.read_text()
                assert "module buffer_" + side + "(" in text
                assert "module spk286_at_fdc_" + side in text
                if side == "gate":
                    assert ".RETAINED_FDC_WRITE(1'b1)" in text
                path = case / (side + ".sv")
                path.write_bytes(original.read_bytes())
                inputs[path] = sha(path)
                files.append(path)
            original = ROOT / "sim/spk286_integration" / (top + ".sv")
            bench = case / (top + ".sv")
            bench.write_bytes(original.read_bytes())
            inputs[bench] = sha(bench)
            files.append(bench)

            iv = case / "fdc-iv.vvp"
            run(case / "iv-build.log", ["iverilog", "-g2012", "-s", top,
                                         "-o", iv, *files])
            run(case / "iv-run.log", ["vvp", iv, "+TRACE=" + str(case / "iv")])
            obj = case / "obj"
            run(case / "vlt-build.log", ["verilator", "--binary", "--timing",
                "--assert", "-j", "2", "--top-module", top, "-Wno-fatal",
                "--Mdir", obj, "-o", "fdc-vlt", *files])
            run(case / "vlt-run.log", [obj / "fdc-vlt", "+TRACE=" + str(case / "vlt")])

            for simulator, binary in (("iv", iv), ("vlt", obj / "fdc-vlt")):
                log = case / (simulator + "-run.log")
                lines = log.read_text().splitlines()
                summaries = [line for line in lines if line.startswith(pass_label + " ")]
                assert len(summaries) == 1, (label, simulator, "Missing PASS")
                assert not any("ERROR:" in line or "Assertion failed" in line for line in lines)
                gold = case / (simulator + "-gold.csv")
                gate = case / (simulator + "-gate.csv")
                assert gold.read_bytes() == gate.read_bytes(), (label, simulator, "Trace difference")
                rows = gold.read_text().splitlines()
                assert rows and all(len(row.split(",")) == observed_outputs + 1 for row in rows)
                report["cases"].append({
                    "case": label, "simulator": simulator,
                    "complete_on_cpu_sample": mode, "summary": summaries[0],
                    "original_outputs_unmasked": observed_outputs,
                    "trace_rows": len(rows), "trace_byte_identical": True,
                    "trace_sha256": sha(gold), "binary_sha256": sha(binary),
                    "build_log_sha256": sha(case / (simulator + "-build.log")),
                    "run_log_sha256": sha(log),
                })
                save()
        assert len(report["cases"]) == 6
        for path, digest in inputs.items():
            assert sha(path) == digest, ("Input changed during execution", str(path))
        report["inputs_sha256_before_after"] = {str(path): digest for path, digest in inputs.items()}
        report["status"] = "RETAINED_FDC_PORTABLE_DIRECTED_PASS"
        report["wall_seconds"] = round(time.monotonic() - start, 3)
        save()
        print(report["status"])
        for case in report["cases"]:
            print(case["case"], case["simulator"], case["summary"])
    except Exception as error:
        report["status"] = "FAIL"
        report["failure"] = str(error)
        save()
        raise


if __name__ == "__main__":
    main()
