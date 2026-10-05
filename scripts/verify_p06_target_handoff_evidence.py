#!/usr/bin/env python3
"""Verify sealed target-handoff source identities and complete paired traces."""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import tarfile


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    manifest = json.loads((args.evidence / "manifest.json").read_text())
    archive = args.evidence / manifest["archive"]
    assert digest(archive.read_bytes()) == manifest["archive_sha256"]
    with tarfile.open(archive, "r:gz") as packet:
        members = {item.name: item for item in packet.getmembers()}
        assert set(members) == set(manifest["members"])
        for name, member in members.items():
            path = PurePosixPath(name)
            assert member.isfile() and not path.is_absolute() and ".." not in path.parts
            raw = packet.extractfile(member).read()
            bound = manifest["members"][name]
            assert len(raw) == bound["bytes"] and digest(raw) == bound["sha256"], name
        def read(name):
            return packet.extractfile(name).read()
        def receipt(name):
            return json.loads(read(name))
        branch = receipt("branch/branch-receipt.json")
        assert branch["status"] == "P06_BRANCH_TARGET_HANDOFF_DUAL_PASS"
        assert len(branch["runs"]) == 304 and len(branch["comparisons"]) == 152
        for relative, expected in branch["sources"].items():
            assert digest(read("source/" + relative)) == expected, relative
        paired_rows = 0
        declared_unused = 0
        rows_by_profile = {}
        for item in branch["comparisons"]:
            profile, name = item["profile"], item["name"]
            rows = []
            for simulator in ("iverilog", "verilator"):
                trace_name = f"{simulator}-p{profile}-{name}.csv"
                raw = read("branch/" + trace_name)
                run = next(r for r in branch["runs"] if r["simulator"] == simulator and
                           r["profile"] == profile and r["name"] == name)
                assert digest(raw) == run["trace_sha256"]
                rows.append(list(csv.DictReader(io.StringIO(raw.decode()))))
            assert len(rows[0]) == len(rows[1]) == item["rows"]
            differences = []
            allowed = {"queue_byte", "metadata_valid", "metadata_clocks", "scheduled", "estimated"}
            for left, right in zip(*rows):
                delta = {key: [left[key], right[key]] for key in left if left[key] != right[key]}
                if delta:
                    assert all(r["consume_valid"] == r["opcode_start"] == r["start_interval"] == "0"
                               for r in (left, right)) and set(delta) <= allowed
                    differences.append({"edge": int(left["edge"]), "unused_empty_queue_fields": delta})
            assert differences == item["empty_queue_differences"]
            paired_rows += len(rows[0])
            declared_unused += len(differences)
            for simulator, trace in zip(("iverilog", "verilator"), rows):
                run = next(r for r in branch["runs"] if r["simulator"] == simulator and
                           r["profile"] == profile and r["name"] == name)
                first = next(r for r in trace if r["start_interval"] == "1" and
                             int(r["cs"], 16) == 0x106E and int(r["ip"], 16) == run["branch_ip"])
                if name in ("baseline", "b0"):
                    last = [r for r in trace if r["retire_fire"] == "1" and r["opcode"] == "e2"][-1]
                    measured = int(last["tick"]) - int(first["tick"])
                    assert measured == run["processor_boundaries"]
                    rows_by_profile[(simulator, profile, name)] = measured
                else:
                    last = next(r for r in trace if r["retire_fire"] == "1" and
                                int(r["instruction_ip"], 16) == run["branch_ip"])
                    measured = int(last["tick"]) - int(first["tick"])
                    assert measured == run["branch_processor_clocks"]
                    minimum = 8 if name.startswith("loop-") else 7 + run["target_length"]
                    assert measured >= minimum
                    assert int(last["scheduled"]) == run["branch_schedule"] == minimum
        for item in branch["prior_comparison"]:
            simulator, profile = item["simulator"], item["profile"]
            baseline = rows_by_profile[(simulator, profile, "baseline")]
            b0 = rows_by_profile[(simulator, profile, "b0")]
            assert baseline == item["baseline_after"] == 2044
            assert (b0 - baseline) / 256 == item["candidate_body_net"] == (24 if profile == 7 else 23)
        focused = receipt("unit/focused-v6/receipt.json")
        metadata = receipt("unit/metadata-v2/receipt.json")
        assert focused["status"] == metadata["status"] == "PASS"
        assert metadata["coverage"]["cases"] == 43878
        for relative, expected in {**focused["source_sha256"], **metadata["source_sha256"]}.items():
            assert digest(read("source/" + relative)) == expected, relative
        for relative, expected in metadata["artifacts_sha256"].items():
            assert digest(read("unit/metadata-v2/" + relative)) == expected
        result = {"status": "PASS", "archive_sha256": manifest["archive_sha256"],
                  "members": len(members), "runs": 304, "pairs": 152,
                  "paired_rows": paired_rows, "declared_unused_empty_head_rows": declared_unused,
                  "metadata_cases_per_simulator": 43878,
                  "scope": "sealed source/trace proof; not complete architectural regression or fitted timing"}
    if args.output:
        args.output.write_text(json.dumps(result, indent=2) + "\n", newline="\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
