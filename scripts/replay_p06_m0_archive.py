#!/usr/bin/env python3
"""Restore source-bound M0 evidence and prepare relocatable replay recipes.

Default operation only restores and validates inputs and writes replay.json.
--execute explicitly compiles and runs those recipes. Neither mode reads
production sources from the working tree or depends on original /tmp paths.
"""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tarfile
import time


def run(command, cwd, log, timeout):
    """Execute an explicitly requested replay with a bounded process group."""
    started = time.monotonic()
    with log.open("w") as stream:
        proc = subprocess.Popen(command, cwd=cwd, stdout=stream,
                                stderr=subprocess.STDOUT, start_new_session=True)
        try:
            code = proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait()
            raise RuntimeError("Hard timeout: " + str(log)) from None
    duration = round(time.monotonic() - started, 3)
    print(f"COMMAND seconds={duration} exit={code} log={log}", flush=True)
    if code:
        raise RuntimeError(f"Command failed ({code}): {log}")
    return duration


def sha(content):
    return hashlib.sha256(content).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    archive_root, out = args.archive.resolve(), args.output.resolve()
    if out.exists():
        raise RuntimeError("Fresh replay directory required")
    manifest = json.loads((archive_root / "manifest.json").read_text())
    if manifest["status"] != "P06_M0_COMPACT_ARCHIVE_PASS":
        raise RuntimeError("Sealed compact archive required")
    out.mkdir(parents=True)
    shutil.copy2(Path(__file__), out / "replay-runner.py")
    artifact_map = {item["archive"]: item for item in manifest["artifacts"]}

    def artifact(relative):
        selected = artifact_map.get(relative) or artifact_map.get(relative + ".gz")
        if selected is None:
            raise RuntimeError("Unbound archive artifact: " + relative)
        path = archive_root / selected["archive"]
        packed = path.read_bytes()
        if sha(packed) != selected["archive_sha256"]:
            raise RuntimeError("Packed artifact drift: " + relative)
        content = gzip.decompress(packed) if path.suffix == ".gz" else packed
        if sha(content) != selected["raw_sha256"] or len(content) != selected["raw_bytes"]:
            raise RuntimeError("Raw artifact drift: " + relative)
        return content

    def materialize(relative):
        target = out / "fixtures" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        content = artifact(relative)
        target.write_bytes(content)
        return target

    binding = json.loads(artifact("diagnosis/source-binding.json"))
    source_archive = archive_root / manifest["source_archive"]["archive"]
    if sha(source_archive.read_bytes()) != manifest["source_archive"]["sha256"]:
        raise RuntimeError("Frozen source archive drift")
    sources = {version: out / "sources" / version for version in ("current", "previous")}
    with tarfile.open(source_archive, "r:gz") as archive:
        expected_members = {item["member"]: item for item in manifest["source_members"]}
        actual_members = archive.getnames()
        if len(actual_members) != len(expected_members) or set(actual_members) != set(expected_members):
            raise RuntimeError("Source member inventory mismatch")
        for member in actual_members:
            if member.startswith("current/"):
                relative = Path(member.removeprefix("current/"))
                target = sources["current"] / relative
                if not target.resolve().is_relative_to(sources["current"].resolve()):
                    raise RuntimeError("Unsafe source member")
                content = archive.extractfile(member).read()
                if sha(content) != expected_members[member]["sha256"]:
                    raise RuntimeError("Source member drift: " + member)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)
        shutil.copytree(sources["current"], sources["previous"])
        for member in actual_members:
            if member.startswith("previous/"):
                relative = Path(member.removeprefix("previous/"))
                target = sources["previous"] / relative
                if not target.resolve().is_relative_to(sources["previous"].resolve()):
                    raise RuntimeError("Unsafe previous source member")
                content = archive.extractfile(member).read()
                if sha(content) != expected_members[member]["sha256"]:
                    raise RuntimeError("Previous source member drift")
                target.write_bytes(content)
    restored = {}
    for version, root in sources.items():
        actual = {path.relative_to(root).as_posix(): sha(path.read_bytes())
                  for path in root.rglob("*") if path.is_file()}
        if actual != binding[version + "_sha256"]:
            raise RuntimeError("Full restored source view mismatch: " + version)
        restored[version] = {"file_count": len(actual), "all_bound_files_identical": True}

    replay = {"status": "RUNNING", "archive_manifest_sha256": sha((archive_root / "manifest.json").read_bytes()),
        "runner_sha256": sha(Path(__file__).read_bytes()), "sources": restored,
        "scope": "Relocatable restoration and original source-bound compile/run recipe preparation. "
                 "No original build or /tmp path is used. Execution occurs only with --execute.",
        "builds": [], "runs": [], "executed": args.execute}
    binaries = {}
    original_compiled = {}
    for suite in ("diagnosis", "epoch8", "prelude8"):
        receipt = json.loads(artifact(suite + "/receipt.json"))
        for original in receipt["builds"]:
            version, path_kind = original["version"], original.get("path", "pcat")
            root = sources[version]
            command = original["command"][:]
            original_bench = command[-1]
            bench_relative = (suite + "/" + version + "/" + Path(original_bench).name
                              if suite == "diagnosis" else suite + "/" + Path(original_bench).name)
            bench = materialize(bench_relative)
            if sha(bench.read_bytes()) != original["bench_sha256"]:
                raise RuntimeError("Bound generated bench mismatch")
            object_dir = out / "objects" / suite / version / path_kind
            command[command.index("--Mdir") + 1] = str(object_dir)
            command[-1] = str(bench)
            rewritten = []
            compiled = {}
            changed_indices = {command.index("--Mdir") + 1, len(command) - 1}
            source_marker = "/" + version + "-source/"
            for index, token in enumerate(command):
                if source_marker in token:
                    relative = token.split(source_marker, 1)[1]
                    if relative not in binding[version + "_sha256"]:
                        raise RuntimeError("Unbound compile source: " + token)
                    target = root / relative
                    rewritten.append(str(target))
                    compiled[relative] = sha(target.read_bytes())
                    changed_indices.add(index)
                else:
                    rewritten.append(token)
            for token in rewritten:
                if token.startswith("/") and not Path(token).resolve().is_relative_to(out):
                    raise RuntimeError("Original absolute compile path survived: " + token)
            if suite == "diagnosis":
                expected = {name: value for name, value in original["compiled_source_sha256"].items()
                            if not name.startswith("/")}
                if compiled != expected:
                    raise RuntimeError("Compile operand set/hash changed during rebase")
                original_compiled[(version, path_kind)] = compiled
            elif compiled != original_compiled[(version, "pcat")]:
                raise RuntimeError("Phase compile source operands differ from bound PCAT recipe")
            original_command = original["command"]
            if len(rewritten) != len(original_command) or any(
                    old != new for index, (old, new) in enumerate(zip(original_command, rewritten))
                    if index not in changed_indices):
                raise RuntimeError("Non-path compile contract changed")
            build = {"suite": suite, "version": version, "path": path_kind,
                "cwd": str(root), "command": rewritten, "bench_sha256": original["bench_sha256"],
                "compiled_source_sha256": compiled,
                "contract": {"compile_flags_and_operand_order_unchanged": True,
                    "all_source_operands_and_bench_identical": True,
                    "changed_token_indices": sorted(changed_indices)}}
            replay["builds"].append(build)
            binaries[(suite, version, path_kind)] = object_dir / rewritten[rewritten.index("-o") + 1]
        for original in receipt["runs"]:
            version, path_kind = original["version"], original.get("path", "pcat")
            kind, loops = original["kind"], int(original["iterations"])
            if suite == "diagnosis":
                program = json.loads(artifact(f"diagnosis/programs/{kind}-256-program.json"))
                image = materialize(f"diagnosis/programs/{kind}-256.hex")
                ram = materialize(f"diagnosis/programs/{kind}-256-ram.hex")
                rom = materialize(f"diagnosis/programs/{kind}-256.rom")
                if sha(image.read_bytes()) != program["segment_sha256"] or sha(rom.read_bytes()) != program["rom_sha256"]:
                    raise RuntimeError("Program image binding mismatch")
            else:
                programs = json.loads(artifact(suite + "/programs.json"))
                prelude = int(original.get("prelude_NOPs", 0))
                matches = [p for p in programs.values() if int(p["loops"]) == loops and int(p.get("prelude_NOPs", 0)) == prelude]
                if len(matches) != 1:
                    raise RuntimeError("Phase program identity ambiguity")
                program = matches[0]
                ram = materialize(suite + "/" + Path(program["ram"]).name)
                rom = materialize("diagnosis/programs/m0-256.rom")
                if sha(ram.read_bytes()) != program["ram_sha256"]:
                    raise RuntimeError("Phase image binding mismatch")
            if (int(original["kernel_ip"], 16) != int(program["kernel_ip"]) or
                    int(original["kernel_length"]) != int(program["kernel_length"]) or
                    int(program["loops"]) != loops):
                raise RuntimeError("Original run scalar contract changed")
            name = Path(original["trace"]).name.removesuffix(".gz").removesuffix(".csv")
            results = out / "results" / suite / version
            trace, backend = results / (name + ".csv"), results / (name + "-backend.csv")
            command = [str(binaries[(suite, version, path_kind)]), f"+LOOPS={loops}", f"+KIND={kind}",
                f"+KERNEL_IP={program['kernel_ip']}", f"+KERNEL_LENGTH={program['kernel_length']}",
                f"+DATA_OFFSET={program['data_offset']}", f"+TRACE={trace}"]
            if path_kind == "ideal":
                command += [f"+PROFILE={original['profile']}", f"+IMAGE={image}"]
            else:
                command += [f"+CPU_PROFILE={original['profile']}", f"+ROM={rom}", f"+RAM={ram}", f"+BACKEND_TRACE={backend}"]
                if suite != "diagnosis":
                    command += [f"+START_DELAY={original['phase_delay']}"]
            for token in command:
                if token.startswith("/") and not Path(token).resolve().is_relative_to(out):
                    raise RuntimeError("Original absolute run path survived")
                if token.startswith(("+ROM=", "+RAM=", "+IMAGE=", "+TRACE=", "+BACKEND_TRACE=")):
                    if not Path(token.split("=", 1)[1]).resolve().is_relative_to(out):
                        raise RuntimeError("Original plusarg path survived")
            replay["runs"].append({"suite": suite, "version": version, "path": path_kind,
                "cwd": str(sources[version]), "command": command,
                "expected_fabric_clocks": int(original["fabric_clocks"]),
                "expected_instructions": int(original["instructions"]),
                "contract": {"profile": int(original["profile"]), "kind": kind,
                    "iterations": loops, "kernel_ip": int(program["kernel_ip"]),
                    "kernel_length": int(program["kernel_length"]), "data_offset": int(program["data_offset"]),
                    "phase_delay": int(original.get("phase_delay", 0)),
                    "prelude_NOPs": int(original.get("prelude_NOPs", 0)),
                    "scalar_arguments_unchanged": True, "all_images_hash_bound": True},
                "log": str(results / (name + ".log"))})
    replay["status"] = "P06_M0_RELOCATABLE_REPLAY_PREPARED"
    if args.execute:
        for index, build in enumerate(replay["builds"]):
            object_dir = Path(build["command"][build["command"].index("--Mdir") + 1])
            object_dir.mkdir(parents=True)
            build["seconds"] = run(build["command"], Path(build["cwd"]), out / f"build-{index}.log", 600)
        for item in replay["runs"]:
            log = Path(item["log"])
            log.parent.mkdir(parents=True, exist_ok=True)
            item["seconds"] = run(item["command"], Path(item["cwd"]), log, 90)
            expected = f"fabric_clocks={item['expected_fabric_clocks']} "
            if expected not in log.read_text() or f"instructions={item['expected_instructions']} " not in log.read_text():
                raise RuntimeError("Replay measurement disagreement")
        replay["status"] = "P06_M0_RELOCATABLE_REPLAY_EXECUTED_PASS"
    (out / "replay.json").write_text(json.dumps(replay, indent=2) + "\n")
    print(json.dumps({key: replay[key] for key in ("status", "sources", "executed")} | {
        "build_recipes": len(replay["builds"]), "run_recipes": len(replay["runs"])}))


if __name__ == "__main__":
    main()
