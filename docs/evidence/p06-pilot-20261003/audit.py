#!/usr/bin/env python3
"""Audit frozen component receipts against this milestone's checkout."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    reference = json.loads((ROOT / "docs/evidence/p06-intel-contract-20261003/manifest.json").read_text())
    production = reference["integration_reference"]["sources"]
    for path, meta in production.items():
        assert sha(ROOT / path) == meta["sha256"], f"Production source changed: {path}"
    final = {"clock": "acceptance/clock", "bus": "acceptance/bus",
             "duration": "duration", "fixture": "fixture"}
    stages = {}
    log_count = 0
    for stage, folder in final.items():
        path = HERE / folder / "receipt.json"
        receipt = json.loads(path.read_text())
        assert receipt["status"] == "P06_DIRECTED_COMPONENT_PASS" and receipt["stage"] == stage
        assert receipt["production_sources_unchanged"] == len(production)
        assert receipt["production_qip_excludes_pilot"]
        for name, expected in receipt["sources_sha256"].items():
            assert sha(ROOT / name) == expected, f"Component input changed: {name}"
        for name, expected in receipt["log_sha256"].items():
            assert sha(path.parent / name) == expected, f"Frozen log changed: {folder}/{name}"
            log_count += 1
        assert receipt["negative_control"]["returncode"] != 0
        reason = receipt["negative_control"]["expected_reason"]
        assert reason in (path.parent / "negative-run.log").read_text()
        marker = "P06_" + ("DURATION" if stage == "duration" else stage.upper()) + "_PASS"
        summaries = {}
        for simulator in ["iverilog", "verilator"]:
            matches = [line for line in (path.parent / (simulator + "-run.log")).read_text().splitlines()
                       if line.startswith(marker)]
            assert len(matches) == 1
            summaries[simulator] = matches[0]
        assert len(set(summaries.values())) == 1
        assert receipt["generic_synthesis"]["0"]["register_bits"] == 0
        stages[stage] = {"receipt": path.relative_to(ROOT).as_posix(),
                         "sha256": sha(path), "summary": summaries,
                         "generic_synthesis_top": receipt["generic_synthesis_top"],
                         "generic_synthesis": receipt["generic_synthesis"]}
    for folder, commit in [("clock", "905a786"), ("bus", "dcb6f38")]:
        receipt = json.loads((HERE / folder / "receipt.json").read_text())
        for name, expected in receipt["log_sha256"].items():
            assert sha(HERE / folder / name) == expected
        # Earlier runner versions are preserved in their milestone commits.
        for name, expected in receipt["sources_sha256"].items():
            historical = subprocess.check_output(["git", "show", f"{commit}:{name}"], cwd=ROOT)
            assert hashlib.sha256(historical).hexdigest() == expected
    assert "spk286_timing_pilot" not in (ROOT / "rtl/spk286_integration/spk286_integration.qip").read_text()
    com = ROOT / "docs/evidence/p06-timing-reference-20261003/T286REF.COM"
    assert sha(com) == "006a7be0bd962859bf929e6b0d6678c400607461ed095c9e164789acf05f2643"
    assert sha(ROOT / "scripts/test_at_landmark_dma.sh") == "0fba7826ccc810c5fa151115416d74357c0919f531a1f5e2ff795ea1a6c3d28c"
    documents = ["docs/optimization/" + name for name in [
        "P06_CPU_SPEED_PROFILES.md", "P06_INTEL_TIMING_REFERENCE_20261003.md",
        "P06_PILOT_PROGRESS_20261003.md", "P06_TIMING_CONTRACT_20261003.md",
        "P06_TIMING_REFERENCE_PLAN_20261003.md", "P12_REAL_CHECKNUM_MEMORY_ATTRIBUTION_20261002.md",
        "README.md"]] + ["rtl/spk286_timing_pilot/README.md",
                       "docs/evidence/p06-pilot-20261003/README.md"]
    links = 0
    preexisting_missing_links = []
    for document in documents:
        path = ROOT / document
        for target in re.findall(r"\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
            if "://" in target or target.startswith("#"):
                continue
            if not (path.parent / target.split("#")[0]).exists():
                # Preserve unrelated pre-existing index defects, with an explicit
                # baseline check and a recorded finding rather than a green link claim.
                old_document = subprocess.check_output(["git", "show", f"dcb6f38:{document}"], cwd=ROOT).decode("utf-8")
                assert "](" + target + ")" in old_document, f"New missing link {document}: {target}"
                missing = (path.parent / target.split("#")[0]).resolve().relative_to(ROOT).as_posix()
                old_target = subprocess.run(["git", "cat-file", "-e", f"dcb6f38:{missing}"],
                                            cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                assert old_target.returncode != 0, f"Existing target was removed: {missing}"
                preexisting_missing_links.append({"document": document, "target": target,
                                                  "baseline": "dcb6f38"})
                continue
            links += 1
    result = {"status": "P06_COMPONENT_ACCEPTANCE_PASS", "stages": stages,
              "production_sources_unchanged": len(production), "logs_verified": log_count,
              "old_milestone_receipts_unchanged": ["905a786", "dcb6f38"],
              "dos_com_unchanged": True, "user_owned_script_unchanged": True,
              "local_links_checked": links,
              "preexisting_missing_links": preexisting_missing_links,
              "audit_sha256": sha(Path(__file__)),
              "documents_sha256": {name: sha(ROOT / name) for name in documents},
              "scope": "Directed unwired components and abstract caller; no full CPU historical timing, full project regression, Quartus fit or physical validation"}
    if args.output:
        with args.output.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: result[key] for key in ["status", "production_sources_unchanged",
                      "logs_verified", "local_links_checked", "dos_com_unchanged"]}, indent=2))


if __name__ == "__main__":
    main()
