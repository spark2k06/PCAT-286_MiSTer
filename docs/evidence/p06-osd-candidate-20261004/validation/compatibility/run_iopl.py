"""IOPL: original assertions, Icarus MAX/6, Verilator eight profiles."""
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts"))
import test_p06_profile_compatibility as h

original_run = h.run
host_runs = []

def bounded_run(command, log, timeout=300, check=True):
    # Only host wall-clock allowance changes. The original SV watchdogs,
    # fixed stimulus timing, assertions and emitted per-edge bytes are intact.
    if "iopl_access" in str(log) and timeout == 300:
        timeout = 900
    started = time.monotonic()
    result = original_run(command, log, timeout=timeout, check=check)
    host_runs.append({"log": str(log.relative_to(ROOT)), "host_timeout_seconds": timeout,
                      "seconds": time.monotonic() - started, "returncode": result.returncode})
    return result

h.run = bounded_run
helper_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
sys.argv = [str(ROOT / "scripts/test_p06_profile_compatibility.py"),
    "--output", str(OUT / "iopl-paired"), "--units", "iopl_access",
    "--profiles", "0,1", "--dual-units", "iopl_access"]
started = time.monotonic()
h.main()
paired_path = OUT / "iopl-paired/receipt.json"
paired = json.loads(paired_path.read_text())
assert paired["status"] == "PASS" and not paired["source_changes"]
directory = OUT / "iopl-paired/iopl_access"
results = list(paired["results"])
for profile in range(2, 8):
    trace = directory / f"profile-{profile}-verilator.csv"
    result = h.test_run([directory / "obj/profiled-test"],
        directory / f"profile-{profile}-verilator.log", trace, profile, 16, "digest")
    observed = h.trace_info(trace)
    assert result.returncode == 0 and h.pass_lines(result.stdout), f"IOPL functional assertions failed, profile={profile}"
    results.append({"unit": "iopl_access", "profile": profile, "name": h.PROFILE_NAMES[profile],
        "simulator": "verilator", "status": "PASS", "returncode": result.returncode,
        "pass": h.pass_lines(result.stdout), "trace_sha256": observed["sha256"],
        "canonical_trace_sha256": observed["canonical_sha256"], "trace": observed,
        "comparison": "unpaired Verilator functional assertions; no Icarus trace comparison"})
    print("IOPL_UNPAIRED_FUNCTIONAL_PASS", h.PROFILE_NAMES[profile], flush=True)
changes = [name for name, digest in paired["source_sha256"].items() if h.sha(ROOT / name) != digest]
assert not changes, f"IOPL source changed: {changes}"
assert hashlib.sha256(Path(__file__).read_bytes()).hexdigest() == helper_hash
receipt = {**paired, "profiles": list(range(8)), "results": results,
    "counts": {"iverilog": 2, "verilator": 8, "max_equivalence": 1, "dual_trace_pairs": 2,
               "unpaired_verilator_functional": 6},
    "host_timeout": "900 seconds for IOPL simulator host processes only; no SV timing or assertion adaptation",
    "helper_sha256": helper_hash, "paired_receipt_sha256": h.sha(paired_path),
    "seconds": time.monotonic() - started, "host_runs": host_runs,
    "scope": "directed functional compatibility; raw MAX equality; canonical paired MAX/6; other six Verilator profiles unpaired"}
(OUT / "iopl-paired/iopl-expanded-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print("IOPL_REFERENCE_PASS Icarus=2 Verilator=8 dual_pairs=2 MAX=1", flush=True)
