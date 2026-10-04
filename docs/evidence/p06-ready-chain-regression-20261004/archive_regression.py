#!/usr/bin/env python3
"""Seal broad attempts and exact replay inputs without compiled object caches."""
import difflib
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import sys

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
DEST = ROOT / "docs/evidence/p06-ready-chain-regression-20261004"


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    current = json.loads((OUT / "receipt.json").read_text())
    if current["status"] != "SPK286_READY_CHAIN_REGRESSION_PASS":
        raise RuntimeError("Only a completed actual make regression PASS can be sealed as final")
    if any(current[name] for name in ("source_changes", "snapshot_changes", "corpus_changes", "cache_changes", "reused_binary_changes", "cache_event_binding_errors")):
        raise RuntimeError("Final receipt contains input/provenance drift")
    final_review = OUT.parent / "p06-ready-chain-regression-final-review-20261004.json"
    if not final_review.is_file():
        raise RuntimeError("Independent final review must exist before sealing")
    reviewed = json.loads(final_review.read_text())
    if (reviewed["status"] != "BROAD_REGRESSION_INDEPENDENT_SOURCE_CORPUS_EXECUTION_AUDIT_PASS" or
            reviewed["regression_receipt_sha256"] != sha(OUT / "receipt.json")):
        raise RuntimeError("Independent final review does not accept this exact receipt")
    if DEST.exists():
        raise RuntimeError("Fresh evidence directory required; never overwrite sealed evidence")
    records = []
    DEST.mkdir(parents=True)

    def add(path, relative, expected=None, compress=None):
        path = Path(path)
        raw_sha = sha(path)
        if expected is not None and raw_sha != expected:
            raise RuntimeError("Evidence drift before archive: " + str(path))
        if compress is None:
            compress = path.suffix in (".log", ".txt", ".sv", ".svh") and path.stat().st_size > 4096
        relative = str(relative) + (".gz" if compress else "")
        target = DEST / relative
        if target.exists():
            raise RuntimeError("Duplicate archive artifact: " + relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        if compress:
            with path.open("rb") as original, target.open("wb") as output:
                with gzip.GzipFile(filename="", mode="wb", fileobj=output, mtime=0) as encoded:
                    shutil.copyfileobj(original, encoded)
        else:
            shutil.copy2(path, target)
        record = {"artifact": relative, "original_path": str(path),
                  "raw_sha256": raw_sha, "artifact_sha256": sha(target),
                  "raw_bytes": path.stat().st_size, "artifact_bytes": target.stat().st_size,
                  "gzip": compress}
        if compress:
            if hashlib.sha256(gzip.decompress(target.read_bytes())).hexdigest() != raw_sha:
                raise RuntimeError("Archive decompression verification failed")
        elif sha(target) != raw_sha:
            raise RuntimeError("Archive copy verification failed")
        records.append(record)

    attempts = {}
    for version in ("v1", "v2", "v3"):
        directory = OUT.parent / ("p06-ready-chain-regression-20261004-" + version)
        receipt = json.loads((directory / "receipt.json").read_text())
        attempts[version] = {"status": receipt["status"], "exit_code": receipt["exit_code"],
                             "elapsed_seconds": receipt["elapsed_seconds"],
                             "original_runner_sha_recorded": "runner_sha256" in receipt}
        add(directory / "receipt.json", version + "/receipt.json")
        add(directory / "regression.log", version + "/regression.log", receipt["log_sha256"])
        add(directory / "run_regression.py", version + "/run_regression.py", receipt.get("runner_sha256"))
        for cleanup in sorted(directory.glob("cleanup-*.json")):
            add(cleanup, version + "/" + cleanup.name)
        if (directory / "cleanup_completed.ps1").is_file():
            add(directory / "cleanup_completed.ps1", version + "/cleanup_completed.ps1")
    for name, expected in current["cache_sha256_after"].items():
        if name == "run_regression.py":
            continue  # Already preserved as the real runner above.
        add(OUT / name, "v3/" + name, expected)
    add(OUT / "CACHE_PROTOCOL.md", "v3/CACHE_PROTOCOL.md")
    add(__file__, "archive_regression.py")
    add(OUT / "verify_archive.py", "verify_archive.py")
    for event in current["cache_events"]:
        add(event["event_file"], "v3/cache-events/" + Path(event["event_file"]).name,
            event["event_file_sha256"])
    # Preserve commands and historic compile logs, but not reproducible .o/.gch
    # caches or bulky executable copies. Their identities are in the proofs.
    manifest = json.loads((OUT / "cache-manifest.json").read_text())
    for event in current["cache_events"]:
        if event["status"] != "CACHE_HIT":
            continue
        unit = event["unit"]
        entry = manifest["units"][unit]
        add(entry["dat"], "v2/compile-proofs/" + unit + "/original__verFiles.dat", entry["dat_sha256"])
        add(entry["build_log"], "v2/compile-proofs/" + unit + "/historical-build.log", entry["build_log_sha256"])
        add(Path(event["output_directory"]) / "build.log", "v3/compile-proofs/" + unit + "/build.log")
    fresh_compile_logs = {}
    for dat in sorted((OUT / "work").rglob("*__verFiles.dat")):
        proof_dir = "v3/fresh-compile-proofs/" + dat.parent.relative_to(OUT / "work").as_posix()
        add(dat, proof_dir + "/" + dat.name)
        own_log = dat.parent / "build.log"
        if own_log.is_file():
            add(own_log, proof_dir + "/build.log")
            fresh_compile_logs[dat.relative_to(OUT).as_posix()] = proof_dir + "/build.log"
        else:
            # Existing smoke/SST scripts print compilation into the global
            # make log; they do not create a per-directory compile log.
            fresh_compile_logs[dat.relative_to(OUT).as_posix()] = "v3/regression.log.gz"
    for name, expected in current["snapshot_sha256_after"].items():
        add(OUT / "snapshot" / name, "compiled-source/" + name, expected, compress=True)
    for name, expected in current["regenerated_vector_sha256"].items():
        add(OUT / name, "v3/regenerated/" + name, expected, compress=True)
    runtime_derivatives = {}
    for path in sorted((OUT / "work").rglob("*")):
        parts = path.relative_to(OUT / "work").parts
        is_sst_batch = path.suffix == ".bin" and parts[:2] == ("singlestep", "batches")
        is_yosys_report = path.suffix == ".log" and parts[:1] == ("reports",)
        if (not path.is_file() or
                not (path.suffix in (".hex", ".mem", ".json", ".csv") or is_sst_batch or is_yosys_report) or
                "verilator" in parts or "iverilog" in parts):
            continue
        name = path.relative_to(OUT).as_posix()
        runtime_derivatives[name] = sha(path)
        add(path, "v3/postrun-derived/" + name, runtime_derivatives[name], compress=True)

    focused = OUT.parent / "p06-ready-chain-adjust-20261004-v1"
    focal_receipt = json.loads((focused / "receipt.json").read_text())
    add(focused / "receipt.json", "adjust-focused/receipt.json")
    add(focused / "focused.log", "adjust-focused/focused.log", focal_receipt["log_sha256"])
    add(focused / "run_focused.py", "adjust-focused/run_focused.py")
    before = OUT.parent / "p06-ready-chain-regression-20261004-v2/snapshot/vendor/spk286/sim/unit/spk286_adjust_instructions_tb.sv"
    after = OUT / "snapshot/vendor/spk286/sim/unit/spk286_adjust_instructions_tb.sv"
    add(before, "adjust-focused/source-before.sv", compress=False)
    add(after, "adjust-focused/source-after.sv", compress=False)
    diff = "".join(difflib.unified_diff(before.read_text().splitlines(keepends=True), after.read_text().splitlines(keepends=True),
                                        fromfile="source-before.sv", tofile="source-after.sv"))
    (DEST / "adjust-focused/stimulus.diff").write_text(diff)
    records.append({"artifact": "adjust-focused/stimulus.diff", "raw_sha256": sha(DEST / "adjust-focused/stimulus.diff"),
                    "artifact_sha256": sha(DEST / "adjust-focused/stimulus.diff"), "gzip": False,
                    "raw_bytes": (DEST / "adjust-focused/stimulus.diff").stat().st_size,
                    "artifact_bytes": (DEST / "adjust-focused/stimulus.diff").stat().st_size,
                    "derivation": "Exact before/after focused testbench unified diff; no architectural oracle changes."})
    preflight = OUT.parent / "p06-ready-chain-starvation-preflight-20261004-v1"
    preflight_manifest = json.loads((preflight / "evidence-manifest.json").read_text())
    add(preflight / "evidence-manifest.json", "starvation-preflight/evidence-manifest.json")
    # The collaborator manifest is the authoritative complete 19-file artifact list.
    collection = preflight_manifest.get("artifacts", preflight_manifest.get("files"))
    if collection is None:
        raise RuntimeError("Unknown preflight evidence manifest schema")
    if isinstance(collection, dict):
        items = [(name, value if isinstance(value, str) else value["sha256"]) for name, value in collection.items()]
    else:
        items = [(item.get("path", item.get("artifact", item.get("relative_path"))), item.get("sha256", item.get("raw_sha256"))) for item in collection]
    for name, expected in items:
        if name == "evidence-manifest.json":
            continue
        add(preflight / name, "starvation-preflight/" + name, expected)
    for name in ("p06-ready-chain-regression-cache-review-20261004.json",
                 "p06-ready-chain-regression-final-review-20261004.json",
                 "p06-ready-chain-regression-final-review-20261004.py",
                 "verify_ready_chain_final.py", "p06-ready-chain-final-integrity.json"):
        path = OUT.parent / name
        if path.is_file():
            add(path, "independent-review/" + name)
    readme = (
        "# READY chaining: broad functional regression evidence\n\n"
        "The real `make regression` completed in the third attempt. Every functional\n"
        "simulation and vector generator ran again. Validated previous Verilator\n"
        "unit compilations were reused; this is not a full fresh Verilator build.\n\n"
        "- `v1` remains FAILED: historical microcode fixtures produced three failures\n"
        "  and five errors before RTL tests. The separate microcode-repair packet\n"
        "  records their explicit migration and the preserved negative checks.\n"
        "- `v2` remains FAILED: architecture comparisons passed through the adjust\n"
        "  bank, whose radix-byte starvation coverage assertion then failed.\n"
        "- `adjust-focused` contains the exact source before/after/diff. Only CODE\n"
        "  READY latency was strengthened by sixteen cycles. All 8184 cases,\n"
        "  architectural expected values, timeout and coverage assertion remain.\n"
        "- `starvation-preflight` contains the unchanged stack/far/muldiv full\n"
        "  dual banks, source receipts and their original generated vectors.\n"
        "- `v3` contains the successful fresh execution log, source/corpus receipts,\n"
        "  exact compile-cache implementation, controls, command/source proofs and\n"
        "  per-hit receipts. Historical compile logs are explicitly labelled.\n"
        "- `compiled-source` preserves every tracked input of the tested snapshot\n"
        "  compressed with its original SHA. Corpus hashes refer to the original\n"
        "  external corpus; the existing smoke policy is recorded in the log.\n\n"
        "`v3/postrun-derived` also preserves generated runtime ROM HEX files,\n"
        "manifests, trace CSV, all 97 SST binary batches/identities/reports and\n"
        "Yosys reports. These are hashed after execution, not\n"
        "presented as pre-existing inputs with fabricated before hashes. Their\n"
        "generators/source and fresh invocation logs remain independently bound.\n\n"
        "Existing script policy runs the full protected expand-down matrix only\n"
        "in Icarus. All 130 Icarus and 129 Verilator unit banks are independently\n"
        "counted in the final review. Simulator/state smoke, Python/compiler tests,\n"
        "four SingleStep smoke groups and Yosys synthesis sanity follow the banks.\n"
        "The scope excludes a complete external corpus, physical/PCAT OS testing,\n"
        "STA and Quartus fit.\n\n"
        "`archive-manifest.json` binds every stored artifact and its uncompressed\n"
        "SHA. The archive verification helper rechecks those hashes and all live\n"
        "compiled inputs. Exact absolute build paths remain in original receipts\n"
        "as provenance; a replay can restore the snapshot and run normal make\n"
        "regression with fresh compilation. v1 did not originally record its\n"
        "runner SHA; its runner is preserved with a new archive hash, while its\n"
        "original source/log hashes and FAILED status remain unchanged.\n"
    )
    readme_path = DEST / "README.md"
    readme_path.write_text(readme)
    records.append({"artifact": "README.md", "raw_sha256": sha(readme_path),
                    "artifact_sha256": sha(readme_path), "raw_bytes": readme_path.stat().st_size,
                    "artifact_bytes": readme_path.stat().st_size, "gzip": False,
                    "derivation": "Summary of final receipts and independently audited scope."})
    packet = {"status": "BROAD_REGRESSION_ARCHIVE_HASH_VERIFIED", "attempts": attempts,
              "final_make_exit_code": current["exit_code"], "fresh_execution_acceptance": "Actual new REGRESSION PASS in v3 log; no simulation output reused.",
              "compiled_source_count": len(current["snapshot_sha256_after"]),
              "external_corpus_inputs": len(current["corpus_sha256_after"]),
              "cache_hits": current["cache_hit_count"], "cache_misses": current["cache_miss_count"],
              "cache_controls": 17, "existing_script_skips": current["skips"],
              "postrun_runtime_derivative_sha256": runtime_derivatives,
              "fresh_compile_log_locations": fresh_compile_logs,
              "source_corpus_cache_changes": [], "artifacts": records,
              "scope": current["scope"], "archiver_sha256": sha(__file__)}
    (DEST / "archive-manifest.json").write_text(json.dumps(packet, indent=2) + "\n")
    print(json.dumps({"status": packet["status"], "artifacts": len(records),
                      "bytes": sum(item.get("artifact_bytes", 0) for item in records), "destination": str(DEST)}))


if __name__ == "__main__":
    main()
