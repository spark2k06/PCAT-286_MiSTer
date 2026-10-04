"""Compare FIFO hashes to full raw CSV from the identical compiled CPU."""
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import test_p06_profile_compatibility as h

OUT = Path(__file__).resolve().parent
RAW = OUT / "raw/event_lifecycle"
STREAM = OUT / "stream"
STREAM.mkdir(exist_ok=False)
source_receipt = json.loads((OUT / "raw/receipt.json").read_text())
assert source_receipt["status"] == "PASS"
assert source_receipt["source_sha256"]["scripts/test_p06_profile_compatibility.py"] == h.sha(Path(h.__file__))
assert source_receipt["source_sha256"]["scripts/test_p06_profile_compatibility.py"] == "c25f53ec8220a8aa309fa46508c74166dd42ac6a36009558d1fd8e1809d03de7"
source_before = {name: h.sha(ROOT / name) for name in source_receipt["source_sha256"]}
assert source_before == source_receipt["source_sha256"]
results = []
for profile in (0, 1):
    started = time.monotonic()
    trace = STREAM / f"profile-{profile}-iverilog.csv"
    result = h.test_run(["vvp", RAW / "profiled.vvp"], STREAM / f"profile-{profile}.log",
                        trace, profile, 16, "digest")
    observed = h.trace_info(trace)
    expected = h.trace_info(RAW / f"profile-{profile}-iverilog.csv")
    assert result.returncode == 0 and h.pass_lines(result.stdout)
    for key in ("sha256", "canonical_sha256", "bytes", "canonical_bytes", "rows",
                "reset_rows", "input_unknown_rows", "input_unknown_bits"):
        assert observed[key] == expected[key], (profile, key, observed[key], expected[key])
    results.append({"profile": profile, "seconds": time.monotonic() - started,
                    "raw_and_canonical_identical_to_csv": True, "trace": observed})
    print("FIFO_RAW_AND_CANONICAL_MATCH", profile, observed["rows"], flush=True)

with (RAW / "profile-0-iverilog.csv").open("rb") as source:
    header = source.readline().rstrip(b"\n")
    fields = source.readline().rstrip(b"\n").split(b",")
fields[1], fields[9], fields[10], fields[16] = b"1", b"00000X", b"X", b"x"
fields[14], fields[38], fields[39] = b"x5x1", b"1551", b"e0e0"
raw = header + b"\n" + b",".join(fields) + b"\n"
canonical = fields.copy()
canonical[9], canonical[10], canonical[16] = b"000000", b"0", b"0"
canonical[14], canonical[39] = b"1551", b"0000"
expected_canonical = header + b"\n" + b",".join(canonical) + b"\n"
for width in (1, 7, 65536):
    acc = h.TraceAccumulator()
    for offset in range(0, len(raw), width):
        acc.update(raw[offset:offset + width])
    observed = acc.finish("synthetic")
    assert observed["sha256"] == hashlib.sha256(raw).hexdigest()
    assert observed["canonical_sha256"] == hashlib.sha256(expected_canonical).hexdigest()
    assert observed["input_unknown_rows"] == observed["reset_rows"] == observed["rows"] == 1
    assert observed["input_unknown_bits"] == int("e0e0", 16).bit_count()

def canonical_hash(value):
    acc = h.TraceAccumulator()
    acc.update(header + b"\n" + b",".join(value) + b"\n")
    return acc.finish("synthetic")["canonical_sha256"]

for index, bad in ((17, b"x" + fields[17][1:]), (13, b"ffff"), (38, b"1550")):
    changed = fields.copy()
    changed[index] = bad
    assert canonical_hash(changed) != canonical_hash(fields), index
nonreset = fields.copy()
nonreset[1], nonreset[10] = b"0", b"f"
changed = nonreset.copy()
changed[10] = b"0"
assert canonical_hash(changed) != canonical_hash(nonreset)
receipt = {"status": "PASS", "results": results,
    "source_sha256": source_before,
    "generated_source_sha256": source_receipt["generated_source_sha256"],
    "raw_receipt_sha256": h.sha(OUT / "raw/receipt.json"),
    "verification_helper_sha256": h.sha(Path(__file__)),
    "synthetic": "all chunk sizes preserve raw/canonical bytes; architecture, output payload, defined input and nonreset status differences remain detectable"}
assert source_before == {name: h.sha(ROOT / name) for name in source_before}
(OUT / "stream-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print("P06_PROFILE_STREAM_ADAPTER_PASS", flush=True)
