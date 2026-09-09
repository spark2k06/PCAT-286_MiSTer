#!/usr/bin/env python3
"""Create and verify deterministic source-import SHA-256 manifests."""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_DIR = ROOT / "docs" / "imports"
PCXT_MANIFEST = MANIFEST_DIR / "pcxt-c6b4dc81.sha256"
SPK_MANIFEST = MANIFEST_DIR / "spk286-9d3a69eb.sha256"
PCXT_MODIFIED = MANIFEST_DIR / "pcxt-modified-files.txt"
PCXT_COMMIT = "c6b4dc8107bade3f41d94599720bd82706331c4e"
SPK_INDEX_TREE = "9d3a69eb0e9d7bed32a9a8672a3ce8b464865101"


def run_git(repo: Path, *args: str) -> list[str]:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    return [line for line in result.stdout.splitlines() if line]


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def write_manifest(output: Path, prefix: Path, paths: list[str]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for relative in sorted(paths):
        source = prefix / relative
        if not source.is_file():
            raise FileNotFoundError(f"missing imported file: {source}")
        lines.append(f"{digest(source)}  {relative}")
    output.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def load_manifest(path: Path) -> list[tuple[str, str]]:
    entries = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        try:
            expected, relative = line.split("  ", 1)
        except ValueError as error:
            raise ValueError(f"{path}:{number}: malformed manifest line") from error
        entries.append((expected, relative))
    return entries


def verify_manifest(path: Path, prefix: Path, allowed_changes: set[str]) -> int:
    failures = 0
    verified = 0
    skipped = 0
    for expected, relative in load_manifest(path):
        source = prefix / relative
        if relative in allowed_changes:
            if not source.is_file():
                print(f"MISSING ALLOWLISTED {relative}")
                failures += 1
            else:
                skipped += 1
            continue
        if not source.is_file():
            print(f"MISSING {relative}")
            failures += 1
        elif digest(source) != expected:
            print(f"CHANGED {relative}")
            failures += 1
        else:
            verified += 1
    print(
        f"{path.name}: verified={verified} allowed_changes={skipped} failures={failures}"
    )
    return failures


def write(args: argparse.Namespace) -> int:
    pcxt_source = Path(args.pcxt_source).resolve()
    spk_source = Path(args.spk_source).resolve()

    pcxt_paths = [
        path
        for path in run_git(pcxt_source, "ls-tree", "-r", "--name-only", PCXT_COMMIT)
        if not path.startswith(("games/", "releases/"))
    ]
    spk_paths = run_git(spk_source, "ls-tree", "-r", "--name-only", SPK_INDEX_TREE)

    write_manifest(PCXT_MANIFEST, ROOT, pcxt_paths)
    write_manifest(SPK_MANIFEST, ROOT / "vendor" / "spk286", spk_paths)
    if not PCXT_MODIFIED.exists():
        PCXT_MODIFIED.write_text(
            "# Imported PCXT paths intentionally changed by this integration.\n",
            encoding="utf-8",
            newline="\n",
        )
    print(f"wrote {PCXT_MANIFEST.relative_to(ROOT)} ({len(pcxt_paths)} files)")
    print(f"wrote {SPK_MANIFEST.relative_to(ROOT)} ({len(spk_paths)} files)")
    return 0


def verify(_: argparse.Namespace) -> int:
    allowed = {
        line.strip()
        for line in PCXT_MODIFIED.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    failures = verify_manifest(PCXT_MANIFEST, ROOT, allowed)
    failures += verify_manifest(SPK_MANIFEST, ROOT / "vendor" / "spk286", set())
    if failures:
        print(f"IMPORT_VERIFICATION_FAIL failures={failures}")
        return 1
    print("IMPORT_VERIFICATION_PASS")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    writer = subparsers.add_parser("write", help="write manifests from pinned sources")
    writer.add_argument("--pcxt-source", required=True)
    writer.add_argument("--spk-source", required=True)
    writer.set_defaults(handler=write)
    verifier = subparsers.add_parser("verify", help="verify imported files")
    verifier.set_defaults(handler=verify)
    args = parser.parse_args()
    return args.handler(args)


if __name__ == "__main__":
    sys.exit(main())
