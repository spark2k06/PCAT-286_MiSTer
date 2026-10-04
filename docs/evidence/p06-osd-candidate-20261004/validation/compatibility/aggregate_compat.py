"""Honest coverage aggregate: 202 Icarus, 64 Verilator, 26 raw MAX pairs."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts"))
import test_p06_profile_compatibility as h

LEAVES = [OUT / "shard-1/receipt.json", OUT / "shard-2/receipt.json",
          OUT / "shard-3-rest/receipt.json", OUT / "iopl-paired/iopl-expanded-receipt.json"]
assert not (OUT / "receipt.json").exists(), "aggregate receipt must be fresh"
results, sources, covered, references, adjustments = [], {}, set(), [], {}
generated_hashes = None
for path in LEAVES:
    leaf = json.loads(path.read_text())
    assert leaf["status"] == "PASS" and not leaf["failures"] and not leaf["source_changes"]
    assert leaf["profiles"] == list(range(8))
    units = set(leaf["units"])
    assert len(units) == len(leaf["units"]) and not covered & units
    covered |= units
    for name, digest in leaf["source_sha256"].items():
        assert name not in sources or sources[name] == digest, f"shard source mismatch: {name}"
        assert h.sha(ROOT / name) == digest, f"source changed: {name}"
        sources[name] = digest
    hashes = leaf["generated_source_sha256"]
    assert generated_hashes is None or generated_hashes == hashes, "generated CPU mismatch"
    generated_hashes = hashes
    for name, digest in hashes.items():
        assert h.sha(path.parent / "generated" / name) == digest
    if "helper_sha256" in leaf:
        assert h.sha(OUT / "run_iopl.py") == leaf["helper_sha256"]
        assert h.sha(path.parent / "receipt.json") == leaf["paired_receipt_sha256"]
    for record in leaf["results"]:
        assert record["status"] == "PASS" and record["unit"] in units
        if record.get("kind") == "MAX per-edge equivalence":
            assert record["original_trace_sha256"] == record["profiled_trace_sha256"]
        else:
            stem = path.parent / record["unit"] / f"profile-{record['profile']}-{record['simulator']}.csv"
            observed = h.trace_info(stem)
            assert observed == record["trace"], "trace metadata changed"
            if stem.exists():
                assert h.sha(stem) == observed["sha256"]
        results.append({**record, "artifact_root": path.parent.relative_to(ROOT).as_posix(),
                        "leaf_receipt": path.relative_to(ROOT).as_posix()})
    adjustments.update(leaf["code_stimulus_adjustments"])
    references.append({"path": path.relative_to(ROOT).as_posix(), "sha256": h.sha(path)})
assert covered == set(h.UNITS), "unit coverage incomplete"
actual = [(r["unit"], r.get("simulator", "MAX equivalence"), r.get("profile", 0)) for r in results]
expected = [(unit, "iverilog", profile) for unit in h.UNITS for profile in range(8)
            if unit != "iopl_access" or profile in (0, 1)]
expected += [(unit, "verilator", profile) for unit in h.DUAL + ["iopl_access"] for profile in range(8)]
expected += [(unit, "MAX equivalence", 0) for unit in h.UNITS]
assert len(actual) == len(set(actual)) and set(actual) == set(expected), "exact simulator coverage mismatch"
indexed = {(r["unit"], r["simulator"], r["profile"]): r for r in results if "simulator" in r}
paired = 0
for unit in h.DUAL + ["iopl_access"]:
    for profile in range(8):
        key = (unit, "iverilog", profile)
        if key not in indexed:
            record = indexed[(unit, "verilator", profile)]
            assert unit == "iopl_access" and profile in range(2, 8)
            assert "unpaired" in record["comparison"]
            continue
        a, b = indexed[key]["trace"], indexed[(unit, "verilator", profile)]["trace"]
        assert (a["canonical_sha256"], a["canonical_bytes"], a["rows"]) == (b["canonical_sha256"], b["canonical_bytes"], b["rows"])
        paired += 1
assert paired == 58
receipt = {"status": "PASS", "units": h.UNITS, "profiles": list(range(8)),
    "counts": {"iverilog": 202, "verilator": 64, "max_equivalence": 26,
               "dual_trace_pairs": 58, "unpaired_verilator_functional": 6},
    "scope": "directed functional compatibility; full 26 by 8 coverage in at least one simulator; raw MAX stream equality; 58 declared canonical dual pairs; six IOPL profiles are unpaired Verilator functional assertions; no hardware historical timing claim",
    "omitted_icarus": [{"unit": "iopl_access", "profile": p, "name": h.PROFILE_NAMES[p]} for p in range(2, 8)],
    "source_sha256": sources, "generated_source_sha256": generated_hashes,
    "leaf_receipts": references, "code_stimulus_adjustments": adjustments,
    "verification_source_sha256": {path.name: h.sha(path) for path in
        (Path(__file__).resolve(), OUT / "run_iopl.py", OUT / "audit_max.py")},
    "results": results, "failures": [], "source_changes": []}
(OUT / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print("P06_PROFILE_COMPATIBILITY_AGGREGATE_PASS Icarus=202 Verilator=64 MAX=26 dual_pairs=58 unpaired=6")
