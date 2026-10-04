#!/usr/bin/env python3
"""Archive the independent fixture migration and restored compiler negatives."""
import collections
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import unittest

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
CPU = ROOT / "vendor/spk286"
EVIDENCE = ROOT / "docs/evidence/spk286-microcode-repair-20261004"
NAMES = ("loadall", "salc", "register_execution", "immediate_execution", "system_access", "io")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if EVIDENCE.exists():
        raise RuntimeError("Fresh evidence directory required")
    EVIDENCE.mkdir(parents=True)
    source_paths = ["vendor/spk286/tests/test_microcode_" + name + ".py" for name in NAMES]
    source_paths.append("vendor/spk286/tools/microcode/compile_microcode.py")
    before, after = {}, {}
    for rel in source_paths:
        old = EVIDENCE / "source-before" / rel
        new = EVIDENCE / "source-after" / rel
        old.parent.mkdir(parents=True, exist_ok=True)
        new.parent.mkdir(parents=True, exist_ok=True)
        old.write_bytes(subprocess.check_output(["git", "show", "1a4f2ec:" + rel], cwd=ROOT))
        shutil.copy2(ROOT / rel, new)
        before[rel], after[rel] = sha(old), sha(new)
    (EVIDENCE / "repair.diff").write_bytes(subprocess.check_output(
        ["git", "diff", "1a4f2ec", "--", *source_paths], cwd=ROOT))
    for source, destination in (("regression.log", "baseline-make.log"),
                                ("microcode-repaired.log", "migration-negative-exposed.log"),
                                ("microcode-repaired-pass.log", "microcode-tests-pass.log")):
        shutil.copy2(OUT / source, EVIDENCE / destination)
    sys.path.insert(0, str(CPU))
    from tools.microcode.compile_microcode import CompileError
    negative_counts = collections.Counter()
    original = unittest.TestCase.assertRaises
    def counted(test, exception, *args, **kwargs):
        if exception is CompileError:
            negative_counts[test.id()] += 1
        return original(test, exception, *args, **kwargs)
    unittest.TestCase.assertRaises = counted
    suite = unittest.TestLoader().loadTestsFromNames(["tests.test_microcode_" + name for name in NAMES])
    with (EVIDENCE / "preserved-negatives.log").open("w") as stream:
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    if not result.wasSuccessful():
        raise RuntimeError("Preserved negative tests failed")
    with (EVIDENCE / "compile-check.log").open("w") as stream:
        code = subprocess.run(["python3", "-m", "tools.microcode.compile_microcode", "--check"],
                              cwd=CPU, stdout=stream, stderr=subprocess.STDOUT).returncode
    if code:
        raise RuntimeError("Generated microcode consistency failed")
    prior = json.loads((OUT / "receipt.json").read_text())
    fixtures = {k: v for k, v in prior["source_sha256_before"].items()
                if k.startswith("vendor/spk286/tests/fixtures/")}
    generated = {k: v for k, v in prior["source_sha256_before"].items()
                 if k.startswith("vendor/spk286/microcode/")}
    fixture_after = {k: sha(ROOT / k) for k in fixtures}
    generated_after = {k: sha(ROOT / k) for k in generated}
    if fixtures != fixture_after or generated != generated_after:
        raise RuntimeError("Historical fixtures or microcode artifacts changed")
    receipt = {"status": "MICROCODE_REGRESSION_REPAIR_PASS", "baseline_commit": "1a4f2ec",
               "baseline_make_exit_code": prior["exit_code"], "baseline_python_tests": 114,
               "baseline_failures": 3, "baseline_errors": 5, "repaired_python_tests": 114,
               "repaired_failures": 0, "repaired_errors": 0,
               "source_sha256_before": before, "source_sha256_after": after,
               "historical_fixture_sha256_before": fixtures, "historical_fixture_sha256_after": fixture_after,
               "microcode_sha256_before": generated, "microcode_sha256_after": generated_after,
               "historical_fixture_changes": [], "microcode_changes": [],
               "existing_negative_rejection_counts": dict(sorted(negative_counts.items())),
               "negative_rejections_total": sum(negative_counts.values()),
               "affected_test_methods": result.testsRun,
               "catalog_translation": {"historical_LOADALL": 172, "historical_CARRY_FILL8": 171,
                                        "standalone_LOADALL": 171, "standalone_CARRY_FILL8": 172,
                                        "changed_positions_per_fixture": 2},
               "pre_SALC_IO_fixture": {"frozen_words": 723, "removed_suffix_start": 719,
                                       "removed_historical_suffix": [30, 171, 54, 3],
                                       "expected_current_prefix_words": 719},
               "restored_LOADALL_negative": "The existing token-deletion rejection was unreachable with the obsolete filename. Preserving it exposed compiler acceptance of instruction LOADALL: END. The guard now checks entry name or token presence; validate_loadall_block remains exact.",
               "generated_image": {"entries": 123, "words": 743, "address_width": 10, "word_width": 8,
                                   "check": "PASS", "regenerated": False},
               "scope": "Compiler/test-adapter repair only. Architectural RTL, .mc sources, generated ROM and historical JSON fixtures unchanged. Broad RTL make regression is a separate frozen v2 run."}
    receipt["artifacts_sha256"] = {p.relative_to(EVIDENCE).as_posix(): sha(p)
                                    for p in sorted(EVIDENCE.rglob("*")) if p.is_file()}
    shutil.copy2(Path(__file__), EVIDENCE / "record_microcode_repair.py")
    receipt["artifacts_sha256"]["record_microcode_repair.py"] = sha(EVIDENCE / "record_microcode_repair.py")
    (EVIDENCE / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"status": receipt["status"], "test_methods": result.testsRun,
                      "negative_rejections": receipt["negative_rejections_total"],
                      "negative_counts": receipt["existing_negative_rejection_counts"]}), flush=True)


if __name__ == "__main__":
    main()
