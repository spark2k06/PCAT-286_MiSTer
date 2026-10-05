#!/usr/bin/env python3
"""Summarize exact M0 traces without adjusting timing or discarding raw rows."""
import argparse
from collections import Counter
import csv
import gzip
import hashlib
import json
from pathlib import Path


def read(path):
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt") as stream:
        return list(csv.DictReader(stream))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def counter(items):
    return dict(sorted(Counter(items).items()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    directory = args.input.resolve()
    receipt = json.loads((directory / "receipt.json").read_text())
    if receipt["status"] != "P06_M0_SOURCE_FROZEN_TRACE_PASS":
        raise RuntimeError("Completed source-frozen receipt required")
    result = {"receipt_sha256": sha(directory / "receipt.json"),
              "sampling": "Pre-update fabric edges; measured inclusive start through final LOOP retirement. "
                          "Elapsed fabric_clocks=end-start; state buckets use start<=edge<end.",
              "runs": [], "comparisons": []}
    for run in receipt["runs"]:
        path = directory / run["trace"]
        if not path.exists():
            path = path.with_suffix(path.suffix + ".gz")
        rows = read(path)
        start, end = int(run["start"]), int(run["end"])
        measured = [r for r in rows if start <= int(r["edge"]) <= end]
        state = measured[:-1]
        if len(state) != int(run["fabric_clocks"]):
            raise RuntimeError("Noncontiguous measurement")
        retires = [r for r in measured if r["retire_fire"] == "1"]
        if len(retires) != int(run["instructions"]):
            raise RuntimeError("Retirement count mismatch")
        starts = [r for r in measured if r["opcode_start"] == "1"]
        if len(starts) != len(retires):
            raise RuntimeError("Opcode/retirement count mismatch")
        spans = []
        for begin, retire in zip(starts, retires):
            if int(begin["edge"]) > int(retire["edge"]):
                raise RuntimeError("Instruction pairing failure")
            spans.append({"opcode": begin["queue_byte"], "ip": begin["ip"],
                          "start": int(begin["edge"]), "retire": int(retire["edge"]),
                          "clocks": int(retire["edge"]) - int(begin["edge"]),
                          "extension": int(retire["implementation_extension"])})
        by_ip = {}
        for ip in sorted({s["ip"] for s in spans}):
            selected = [s for s in spans if s["ip"] == ip]
            by_ip[ip] = {"opcode": selected[0]["opcode"], "instructions": len(selected),
                         "start_to_retire_clocks": counter(s["clocks"] for s in selected),
                         "extensions": sum(s["extension"] for s in selected)}
        # Consecutive retirement intervals include the following instruction's
        # opcode admission delay; start-to-retire above excludes that gap.
        retirement_intervals = {}
        for previous, retire in zip(retires, retires[1:]):
            key = retire["opcode"]
            retirement_intervals.setdefault(key, []).append(int(retire["edge"]) - int(previous["edge"]))
        loops = [int(r["edge"]) for r in retires if r["opcode"] == "e2"]
        bus_kind = lambda r: "idle" if r["bus_valid"] != "1" else {"13": "CODE", "5": "READ", "6": "WRITE"}.get(r["bus_status"], "other")
        transactions = []
        active = None
        for row in rows:
            if row["bus_valid"] == "1":
                if active is None:
                    active = {"start": int(row["edge"]), "address": row["address"],
                              "kind": bus_kind(row), "ip": row["ip"], "opcode": row["opcode"]}
                elif active["address"] != row["address"] or active["kind"] != bus_kind(row):
                    raise RuntimeError("Uncompleted bus transaction changed")
                if row["ready"] == "1":
                    active.update({"ready": int(row["edge"]), "visible_to_ready_clocks": int(row["edge"]) - active["start"]})
                    transactions.append(active)
                    active = None
            elif active is not None:
                raise RuntimeError("Visible bus request withdrawn before READY")
        measured_transactions = [t for t in transactions if start <= t["start"] and t["ready"] <= end]
        item = {k: run[k] for k in ("version", "path", "profile", "kind", "iterations", "start", "end", "fabric_clocks", "instructions", "extensions")}
        item.update({"by_instruction_ip": by_ip,
                     "retirement_intervals": {k: counter(v) for k, v in retirement_intervals.items()},
                     "loop_intervals": counter(b-a for a, b in zip(loops, loops[1:])),
                     "bus_state_edge_counts": counter(bus_kind(r) for r in state),
                     "CODE_with_DATA_active_edges": sum(bus_kind(r) == "CODE" and r["biu_data_active"] == "1" for r in state),
                     "CODE_with_operand_request_edges": sum(bus_kind(r) == "CODE" and r["operand_request"] == "1" for r in state),
                     "memory_request_acceptances": sum(r["memory_request"] == r["memory_request_ready"] == "1" for r in state),
                     "queue_empty_edges": sum(r["queue_count"] == "0" for r in state),
                     "transactions": {kind: {"count": len(selected), "visible_to_ready_clocks": counter(t["visible_to_ready_clocks"] for t in selected)}
                         for kind in ("CODE", "READ", "WRITE")
                         if (selected := [t for t in measured_transactions if t["kind"] == kind])},
                     "first_three_iterations": {"instructions": spans[:15],
                         "bus_transactions": [t for t in transactions if start <= t["start"] <= (loops[2] if len(loops) >= 3 else end)]}})
        if "backend" in run:
            backend_path = directory / run["backend"]
            if not backend_path.exists():
                backend_path = backend_path.with_suffix(backend_path.suffix + ".gz")
            backend = read(backend_path)
            if [r["edge"] for r in rows] != [r["edge"] for r in backend]:
                raise RuntimeError("CPU/backend edge alignment mismatch")
            interval = [r for r in backend if start <= int(r["edge"]) < end]
            by_edge = {int(r["edge"]): r for r in backend}
            # Bind exact bridge Ts admission and terminal READY to each native
            # transaction, keeping backend command acceptance independent.
            for transaction in transactions:
                segment = [by_edge[edge] for edge in range(transaction["start"], transaction["ready"] + 1)]
                match = [r for r in segment if r["bridge_ts_admit"] == "1"]
                if len(match) != 1:
                    raise RuntimeError("Native transaction Ts admission ambiguity")
                transaction["ts"] = int(match[0]["edge"])
                transaction["ts_boundary"] = int(match[0]["cpu_boundary"])
                segment = segment[transaction["ts"] - transaction["start"]:]
                transaction["backend_accept"] = [int(r["edge"]) for r in segment if r["command"] == r["accept"] == "1"]
                transaction["first_tc_state"] = next((int(r["edge"]) for r in segment if r["timing_tc"] == "1"), None)
            item["backend"] = {"bridge_deadline_miss_edges": sum(r["bridge_deadline_miss"] == "1" for r in interval),
                "physical_sdram_READ_commands": sum(r["sdram_read"] == "1" for r in interval),
                "physical_write_acceptances": sum(r["physical_accept"] == r["physical_command"] == r["physical_write"] == "1" for r in interval),
                "AT_refresh_grant_edges": sum(r["refresh_grant"] == "1" for r in interval),
                "HOLD_edges": sum(r["cpu_hold"] == "1" for r in interval),
                "P03_hit_delta": int(interval[-1]["p03_hits"]) - int(interval[0]["p03_hits"]),
                "P03_miss_delta": int(interval[-1]["p03_misses"]) - int(interval[0]["p03_misses"]),
                "data_hit_delta": int(interval[-1]["data_hits"]) - int(interval[0]["data_hits"]),
                "data_miss_delta": int(interval[-1]["data_misses"]) - int(interval[0]["data_misses"])}
            warm = [r for r in interval if int(r["edge"]) > loops[0]]
            item["backend"]["after_first_LOOP_retirement"] = {
                "start_edge": loops[0] + 1, "end_exclusive": end,
                "physical_sdram_READ_commands": sum(r["sdram_read"] == "1" for r in warm),
                "bridge_deadline_miss_edges": sum(r["bridge_deadline_miss"] == "1" for r in warm),
                "AT_refresh_grant_edges": sum(r["refresh_grant"] == "1" for r in warm),
                "HOLD_edges": sum(r["cpu_hold"] == "1" for r in warm)}
        result["runs"].append(item)
    for path in ("ideal", "pcat"):
        for profile in ("1", "2", "4"):
            entries = [r for r in result["runs"] if r["path"] == path and r["profile"] == profile]
            values = {(r["version"], r["kind"]): int(r["fabric_clocks"]) for r in entries}
            before, after = values[("previous", "m0")], values[("current", "m0")]
            result["comparisons"].append({"path": path, "profile": profile, "previous_M0": before,
                "current_M0": after, "delta": after-before, "percent": (after/before - 1)*100,
                "previous_baseline": values[("previous", "baseline")], "current_baseline": values[("current", "baseline")]})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result["comparisons"], indent=2))


if __name__ == "__main__":
    main()
