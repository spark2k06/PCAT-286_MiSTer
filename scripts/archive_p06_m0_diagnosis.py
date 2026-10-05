#!/usr/bin/env python3
"""Seal bounded M0 diagnosis evidence before deleting owned temporary builds."""
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import shutil
import tarfile


def digest(stream):
    result = hashlib.sha256()
    length = 0
    while chunk := stream.read(1024 * 1024):
        result.update(chunk)
        length += len(chunk)
    return result.hexdigest(), length


def file_digest(path):
    with path.open("rb") as stream:
        return digest(stream)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--refresh-analysis", action="store_true",
                        help="Bind completed phase analyses after an already sealed archive")
    args = parser.parse_args()
    incoming, out = args.input.resolve(), args.output.resolve()
    if out.exists() and not args.refresh_analysis:
        raise RuntimeError("Fresh archive directory required")
    out.mkdir(parents=True, exist_ok=args.refresh_analysis)
    diagnosis = incoming / "v2"
    receipt = json.loads((diagnosis / "receipt.json").read_text())
    if receipt["status"] != "P06_M0_SOURCE_FROZEN_TRACE_PASS":
        raise RuntimeError("Completed source-frozen diagnosis required")
    phase = incoming / "phase8-v4"
    prelude = incoming / "prelude8-v1"
    for path in (phase, prelude):
        item = json.loads((path / "receipt.json").read_text())
        if item["status"] != "P06_M0_FULL_STARTUP_PHASE_SWEEP_PASS":
            raise RuntimeError("Completed startup control required: " + str(path))
    manifest = json.loads((out / "manifest.json").read_text()) if args.refresh_analysis else {"status": "RUNNING", "artifacts": [], "source_members": [],
                "input_directory": str(incoming),
                "interpretation": "v2 is accepted current/previous exact M0 diagnosis. "
                "phase8-v4 is a natural profile epoch sweep; prelude8-v1 uses legal NOP preludes. "
                "phase8-v1 execute_enable delay is ineffective admission coverage. "
                "v1 and phase8-v2/v3 are failed harness attempts, never accepted CPU results."}

    def preserve(path, relative):
        target = out / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        raw_hash, raw_bytes = file_digest(path)
        if path.suffix == ".gz":
            shutil.copy2(path, target)
            with gzip.open(target, "rb") as stream:
                original_hash, original_bytes = digest(stream)
            manifest["artifacts"].append({"input": str(path.relative_to(incoming)),
                "archive": str(target.relative_to(out)), "input_sha256": raw_hash,
                "input_bytes": raw_bytes, "raw_sha256": original_hash, "raw_bytes": original_bytes,
                "archive_sha256": raw_hash, "archive_bytes": raw_bytes})
        elif path.suffix in (".json", ".md"):
            shutil.copy2(path, target)
            manifest["artifacts"].append({"input": str(path.relative_to(incoming)),
                "archive": str(target.relative_to(out)), "input_sha256": raw_hash,
                "raw_sha256": raw_hash, "raw_bytes": raw_bytes,
                "archive_sha256": raw_hash, "archive_bytes": raw_bytes})
        else:
            target = target.with_suffix(target.suffix + ".gz")
            with path.open("rb") as source, target.open("wb") as stream:
                with gzip.GzipFile(fileobj=stream, mode="wb", filename="", mtime=0) as compressed:
                    shutil.copyfileobj(source, compressed, 1024 * 1024)
            with gzip.open(target, "rb") as stream:
                actual_hash, actual_bytes = digest(stream)
            if (actual_hash, actual_bytes) != (raw_hash, raw_bytes):
                raise RuntimeError("Archive round-trip mismatch: " + str(path))
            packed_hash, packed_bytes = file_digest(target)
            manifest["artifacts"].append({"input": str(path.relative_to(incoming)),
                "archive": str(target.relative_to(out)), "input_sha256": raw_hash,
                "raw_sha256": raw_hash, "raw_bytes": raw_bytes,
                "archive_sha256": packed_hash, "archive_bytes": packed_bytes})

    if args.refresh_analysis:
        for name, archive_name in (("phase8-v4", "epoch8"), ("prelude8-v1", "prelude8")):
            analysis = json.loads((incoming / name / "analysis.json").read_text())
            if analysis["status"] != "P06_M0_RAW_PHASE_TRACE_ANALYSIS_PASS":
                raise RuntimeError("Completed raw phase analysis required")
            for file_name in ("analysis.json", "analysis-runner.py"):
                source = incoming / name / file_name
                manifest["artifacts"] = [item for item in manifest["artifacts"]
                    if item["input"] != str(source.relative_to(incoming))]
                preserve(source, Path(archive_name) / file_name)
        manifest["archive_bytes"] = sum(item["archive_bytes"] for item in manifest["artifacts"]) + manifest["source_archive"]["bytes"]
        manifest["status"] = "P06_M0_COMPACT_ARCHIVE_PASS"
        (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        print(json.dumps({"status": manifest["status"], "artifacts": len(manifest["artifacts"]),
                          "archive_bytes": manifest["archive_bytes"]}))
        return

    for name, archive_name in (("v2", "diagnosis"), ("phase8-v4", "epoch8"),
                               ("prelude8-v1", "prelude8"), ("phase8-v1", "ineffective-execute-delay"),
                               ("phase8-v2", "failed-reset-input-wiring"), ("phase8-v3", "failed-static-wire-wiring")):
        directory = incoming / name
        for path in sorted(directory.rglob("*")):
            if path.is_file() and not any(part in ("current-source", "previous-source") for part in path.relative_to(directory).parts):
                preserve(path, Path(archive_name) / path.relative_to(directory))
    # The first attempt failed the kernel-byte guard before CPU compilation.
    for relative in ("source-binding.json", "programs/nasm.log", "programs/T286REF.COM",
                     "programs/T286REF.lst", "current-source/scripts/trace_p06_m0_diagnosis.py"):
        path = incoming / "v1" / relative
        preserve(path, Path("failed-kernel-byte-guard") / relative)

    binding = json.loads((diagnosis / "source-binding.json").read_text())
    names = [("current", name, value) for name, value in binding["current_sha256"].items()]
    names += [("previous", name, item["previous"]) for name, item in binding["differences"].items()]
    packed = out / "frozen-sources.tar.gz"
    with packed.open("wb") as stream:
        with gzip.GzipFile(fileobj=stream, mode="wb", filename="", mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w|") as archive:
                for version, name, expected in names:
                    path = diagnosis / (version + "-source") / name
                    content = path.read_bytes()
                    actual = hashlib.sha256(content).hexdigest()
                    if actual != expected:
                        raise RuntimeError("Frozen source drift: " + str(path))
                    member = version + "/" + name
                    entry = tarfile.TarInfo(member)
                    entry.size, entry.mtime, entry.mode = len(content), 0, 0o644
                    archive.addfile(entry, io.BytesIO(content))
                    manifest["source_members"].append({"member": member, "sha256": actual, "bytes": len(content)})
    with tarfile.open(packed, "r:gz") as archive:
        for item in manifest["source_members"]:
            actual_hash, actual_bytes = digest(archive.extractfile(item["member"]))
            if (actual_hash, actual_bytes) != (item["sha256"], item["bytes"]):
                raise RuntimeError("Source archive round-trip mismatch")
    packed_hash, packed_bytes = file_digest(packed)
    manifest["source_archive"] = {"archive": packed.name, "sha256": packed_hash,
                                  "bytes": packed_bytes, "member_count": len(names),
        "restore": "Extract current/ as the source root. Clone it for the previous CPU, "
                   "then overlay the three files under previous/. Full previous hashes are in diagnosis/source-binding.json."}
    # Verify receipt-bound complete traces against the compact packet.
    for archive_name, run_receipt in (("diagnosis", receipt),
        ("epoch8", json.loads((phase / "receipt.json").read_text())),
        ("prelude8", json.loads((prelude / "receipt.json").read_text()))):
        for item in run_receipt["runs"]:
            for field in ("trace", "backend"):
                if field not in item:
                    continue
                relative = Path(archive_name) / item[field]
                selected = next(entry for entry in manifest["artifacts"]
                    if entry["archive"] in (str(relative), str(relative) + ".gz"))
                if selected["raw_sha256"] != item[field + "_sha256"]:
                    raise RuntimeError("Receipt raw-stream digest mismatch: " + str(relative))
    manifest["archive_bytes"] = sum(item["archive_bytes"] for item in manifest["artifacts"]) + packed_bytes
    manifest["status"] = "P06_M0_COMPACT_ARCHIVE_PASS"
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"status": manifest["status"], "artifacts": len(manifest["artifacts"]),
                      "source_members": len(names), "archive_bytes": manifest["archive_bytes"]}))


if __name__ == "__main__":
    main()
