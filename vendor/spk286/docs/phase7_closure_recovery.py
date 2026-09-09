"""Verify and restore the Phase 7 closure archive into an absent workspace child."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import stat
import zipfile


def digest(stream):
    value = hashlib.sha256()
    for block in iter(lambda: stream.read(1024 * 1024), b""):
        value.update(block)
    return value.hexdigest()


def safe_name(name):
    path = PurePosixPath(name)
    if (not name or "\\" in name or ":" in name or "\0" in name
            or path.is_absolute() or path.as_posix() != name
            or any(part in ("", ".", "..", ".git") for part in path.parts)):
        raise ValueError(f"Unsafe archive path: {name!r}")
    return path


def restore(archive, expected_sha256, workspace, destination):
    workspace = workspace.resolve(strict=True)
    if destination.exists() or destination.is_symlink():
        raise ValueError("Destination must be absent; restoration never overlays existing files")
    destination = destination.resolve()
    if destination == workspace or not destination.is_relative_to(workspace):
        raise ValueError("Destination must stay inside the explicitly selected workspace")
    if destination.exists():
        raise ValueError("Destination must be absent; restoration never overlays existing files")
    with archive.open("rb") as stream:
        actual = digest(stream)
    if actual != expected_sha256.lower():
        raise ValueError(f"Archive SHA256 mismatch: {actual}")
    with zipfile.ZipFile(archive) as package:
        entries = package.infolist()
        names = []
        for entry in entries:
            safe_name(entry.filename)
            mode = entry.external_attr >> 16
            if entry.is_dir() or stat.S_ISLNK(mode):
                raise ValueError("Only regular-file entries are accepted")
            if stat.S_IFMT(mode) not in (0, stat.S_IFREG):
                raise ValueError("Special archive entries are forbidden")
            names.append(entry.filename)
        if len(names) != len(set(name.casefold() for name in names)):
            raise ValueError("Duplicate or case-colliding archive destinations")
        recorded = {}
        for line in package.read("SHA256SUMS").decode("utf-8").splitlines():
            checksum, name = line.split("  ", 1)
            safe_name(name)
            if name in recorded or len(checksum) != 64 or any(c not in "0123456789abcdef" for c in checksum):
                raise ValueError("Invalid or duplicate checksum entry")
            recorded[name] = checksum
        if set(recorded) != set(names) - {"SHA256SUMS"}:
            raise ValueError("Checksum inventory does not exactly match the archive")
        for name, checksum in recorded.items():
            with package.open(name) as stream:
                if digest(stream) != checksum:
                    raise ValueError(f"Payload SHA256 mismatch: {name}")
        # Validate every destination before creating the absent restoration root.
        for name in names:
            if not (destination / name).resolve().is_relative_to(destination):
                raise ValueError(f"Destination escape: {name}")
        destination.mkdir(parents=True, exist_ok=False)
        for name in names:
            output = destination / name
            output.parent.mkdir(parents=True, exist_ok=True)
            with package.open(name) as source, output.open("xb") as target:
                for block in iter(lambda: source.read(1024 * 1024), b""):
                    target.write(block)
            # Retain execution bits for direct script invocation on POSIX.
            # Do not restore setuid/setgid, sticky or group/other write bits.
            output.chmod(0o644 | ((package.getinfo(name).external_attr >> 16) & 0o111))
    base = destination / "build/phase7-closure-20260909-main"
    candidate = destination / "build/phase7-closure-20260909-final-candidate"
    counts = {}
    for name in ("delivery-source-manifest.json", "final-executable-inputs.json"):
        manifest = json.loads((base / name).read_text())
        for path, checksum in manifest.items():
            safe_name(path)
            with (candidate / path).open("rb") as stream:
                if digest(stream) != checksum:
                    raise ValueError(f"Restored candidate mismatch: {path}")
        counts[name] = len(manifest)
    return {"archive_sha256": actual, "verified_payloads": len(recorded),
            "destination": str(destination), "candidate_manifests": counts,
            "status": "PASS", "overlay_performed": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(restore(args.archive, args.sha256, args.workspace, args.destination), indent=2))


if __name__ == "__main__":
    main()
