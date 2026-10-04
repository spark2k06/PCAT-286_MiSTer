#!/usr/bin/env python3
"""Supplement the frozen OSD fit recorder with independent evidence checks.

This build-only auditor does not alter the fitted sources or frozen recorder.
Evidence integrity PASS is separate from physical timing PASS. Inherited
platform I/O and the conditional SDRAM board/device budget remain declared;
no hardware acceptance, complete OS regression or cycle-accuracy claim.
"""
import argparse
import ast
from collections import Counter
from datetime import datetime
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import shlex
import sys

ROOT = Path(__file__).resolve().parents[3]
RECORDER_SHA256 = "ec7960ce24ba02cef0cdb160a5b2cc0c617be4db25570112c1ce4a87cb3d1316"
BASELINE_JSON_SHA256 = "fd9a484da7ebc3f409a03bd14b4318043f3d9d56a62ac0e53471f3c2e30a5808"
BASELINE_SUMMARY_SHA256 = "db26c7c1b20019325054299692e07326558726f062d1d0dbb44df312e5054e82"
CPU_SHA256 = {
    "spk286_profiled.sv": "f45787c2e5e30ae94370ba164ddbf3f1d8058ef52a023c05355131aea3755501",
    "spk286_profiled_events.sv": "a158e55b5b0a66060784c4901576fb717842cc9a009e3656d5feaaf76b51fbef",
}
EXPECTED_COUNTS = dict(iverilog=202, verilator=64, max_equivalence=26,
                       dual_trace_pairs=58, unpaired_verilator_functional=6)
CHECK_COUNTS = dict(no_clock=3713, multiple_clock=32, no_input_delay=20,
                    no_output_delay=85, partial_min_max_delay=24)
UNCLOCKED = {"sysmem_lite:sysmem": 1239, "h2f_gp": 617, "uart": 619,
             "spi": 621, "hdmi_i2c": 617}
CANONICAL_RULES = {
    "pre_reset": ["address=0", "status=0", "hlda=0"],
    "datain": "bit-precise observed two-state input helper",
    "datain_unknown_mask": "diagnostic mask set to 0 only in canonical view",
    "architecture": "unchanged",
}


def require(ok, message):
    if not ok:
        raise AssertionError(message)


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def within(base, name):
    """Resolve a receipt-relative artifact without allowing escape."""
    name = str(name).replace("\\", "/")
    candidate = (base / name).resolve()
    require(candidate.is_relative_to(base.resolve()), "Artifact escapes root: " + name)
    return candidate


def snapshot_helpers(work, sources):
    """Import only the prehashed frozen helper closure, never live scripts."""
    # Loading a frozen source must not write a bytecode artifact into the fit.
    sys.dont_write_bytecode = True
    modules, bindings = {}, {}
    for name in ("summarize_at_50mhz_timing", "analyze_pcat_resources",
                 "check_sync_microcode_image", "audit_fixed50_fit"):
        relative = "scripts/" + name + ".py"
        path = within(work, relative)
        require(relative in sources and sha(path) == sources[relative],
                "Frozen imported helper changed: " + relative)
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        modules[name] = module
        bindings[relative] = sha(path)
    return modules, bindings


def source_binding(receipt, work, label):
    bound = {}
    require(receipt.get("source_sha256"), label + ": missing source closure")
    for name, digest in receipt["source_sha256"].items():
        path = within(work, name)
        require(sha(path) == digest, label + " source drift: " + name)
        bound[name.replace("\\", "/")] = digest
    return bound


def literals(path, names):
    found = {}
    for node in ast.parse(path.read_text()).body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in names:
                    found[target.id] = ast.literal_eval(node.value)
    require(set(found) == set(names), "Frozen fixture inventory missing")
    return found


def trace_metadata(stem, artifact_hashes):
    """Rehash retained files and raw CSV if present; never manufacture digests.

    The accepted runner streams every byte into raw/canonical SHA256 and retains
    bounded samples. Those complete streams cannot be reconstructed from the
    samples. The bound original receipt and digest artifacts preserve that limit.
    """
    metadata = stem.with_suffix(".digest.json")
    observed = read_json(metadata)
    artifact_hashes[str(metadata.relative_to(ROOT))] = sha(metadata)
    for key in ("sha256", "canonical_sha256"):
        require(re.fullmatch("[0-9a-f]{64}", observed[key]), "Invalid trace digest")
    for key in ("bytes", "canonical_bytes", "rows"):
        require(type(observed[key]) is int and observed[key] > 0, "Invalid trace count")
    require(observed["canonical_rules"] == CANONICAL_RULES, "Canonical view changed")
    if stem.exists():
        raw, canonical = hashlib.sha256(), hashlib.sha256()
        total = ctotal = rows = resets = unknown_rows = unknown_bits = 0
        with stem.open("rb") as source:
            for index, line in enumerate(source):
                require(line.endswith(b"\n"), "Incomplete raw observer line")
                raw.update(line)
                total += len(line)
                fields = line[:-1].split(b",")
                require(len(fields) == 40, "Raw observer field count changed")
                if index:
                    rows += 1
                    if fields[1] == b"1":
                        resets += 1
                        fields[9], fields[10], fields[16] = b"000000", b"0", b"0"
                    mask = int(fields[39], 16)
                    unknown_rows += bool(mask)
                    unknown_bits += mask.bit_count()
                    fields[14], fields[39] = fields[38], b"0000"
                view = b",".join(fields) + b"\n"
                canonical.update(view)
                ctotal += len(view)
        computed = dict(sha256=raw.hexdigest(), canonical_sha256=canonical.hexdigest(),
                        bytes=total, canonical_bytes=ctotal, rows=rows, reset_rows=resets,
                        input_unknown_rows=unknown_rows, input_unknown_bits=unknown_bits)
        require(all(observed[k] == v for k, v in computed.items()), "Raw CSV metadata drift")
        artifact_hashes[str(stem.relative_to(ROOT))] = sha(stem)
    else:
        require(observed["storage"] == "streamed raw/canonical SHA256", "Missing raw CSV")
        for suffix in (".prefix.txt", ".tail.txt"):
            sample = stem.with_suffix(suffix)
            require(sample.is_file() and sample.stat().st_size > 0, "Trace sample missing")
            artifact_hashes[str(sample.relative_to(ROOT))] = sha(sample)
    return observed


def validate_compatibility(path, work):
    receipt = read_json(path)
    require(receipt["status"] == "PASS" and not receipt["failures"] and
            not receipt["source_changes"], "Compatibility is not accepted")
    inventory = literals(work / "scripts/test_p06_profile_compatibility.py",
                         ("UNITS", "DUAL", "PROFILE_NAMES"))
    units, dual = inventory["UNITS"], inventory["DUAL"]
    require(len(units) == len(set(units)) == 26 and len(dual) == len(set(dual)) == 7,
            "Fixture inventory must be unique 26/7")
    require(receipt["units"] == units and receipt["profiles"] == list(range(8)),
            "Compatibility profiles/units changed")
    require(receipt["counts"] == EXPECTED_COUNTS, "Compatibility count claim changed")
    expected = {(u, "iverilog", p) for u in units for p in range(8)
                if u != "iopl_access" or p in (0, 1)}
    expected |= {(u, "verilator", p) for u in dual + ["iopl_access"] for p in range(8)}
    expected |= {(u, "MAX equivalence", 0) for u in units}
    omitted = [{"unit": "iopl_access", "profile": p, "name": inventory["PROFILE_NAMES"][p]}
               for p in range(2, 8)]
    require(receipt["omitted_icarus"] == omitted, "Undeclared Icarus omission")
    require(receipt["generated_source_sha256"] == CPU_SHA256, "Generated CPU revision changed")
    bindings = source_binding(receipt, work, "compatibility")
    artifacts, leaves, leaf_units = {}, {}, set()
    for helper, digest in receipt["verification_source_sha256"].items():
        target = within(path.parent, helper)
        require(sha(target) == digest, "Acceptance helper changed: " + helper)
        artifacts[target.relative_to(ROOT).as_posix()] = digest
    references = receipt["leaf_receipts"]
    require(len(references) == 4 and len({r["path"] for r in references}) == 4,
            "Expected four unique accepted compatibility leaves")
    for reference in references:
        leaf_path = within(ROOT, reference["path"])
        require(leaf_path.is_relative_to(path.parent.resolve()), "Leaf outside acceptance root")
        require(sha(leaf_path) == reference["sha256"], "Leaf receipt drift")
        leaf = read_json(leaf_path)
        require(leaf["status"] == "PASS" and not leaf["failures"] and
                not leaf["source_changes"], "Leaf no longer accepted")
        selected_units = set(leaf["units"])
        require(len(selected_units) == len(leaf["units"]) and not leaf_units & selected_units,
                "Leaf unit coverage overlaps or duplicates")
        leaf_units |= selected_units
        require(leaf["profiles"] == list(range(8)), "Leaf profile set changed")
        leaf_keys = [(r["unit"], r.get("simulator", "MAX equivalence"), r.get("profile", 0))
                     for r in leaf["results"]]
        require(len(leaf_keys) == len(set(leaf_keys)) and
                all(r["unit"] in selected_units for r in leaf["results"]), "Leaf result scope changed")
        require(leaf["generated_source_sha256"] == CPU_SHA256, "Leaf CPU drift")
        source_binding(leaf, work, "leaf")
        for name, digest in CPU_SHA256.items():
            target = within(leaf_path.parent, "generated/" + name)
            require(sha(target) == digest, "Generated leaf artifact drift")
            artifacts[target.relative_to(ROOT).as_posix()] = digest
        artifacts[leaf_path.relative_to(ROOT).as_posix()] = reference["sha256"]
        if "helper_sha256" in leaf:
            require(sha(path.parent / "run_iopl.py") == leaf["helper_sha256"], "IOPL helper drift")
            require(sha(leaf_path.parent / "receipt.json") == leaf["paired_receipt_sha256"],
                    "IOPL paired receipt drift")
        leaves[reference["path"]] = leaf
    require(leaf_units == set(units), "Accepted leaves do not cover all units")
    indexed, max_records = {}, {}
    actual = []
    for record in receipt["results"]:
        require(record["status"] == "PASS", "Non-PASS compatibility result")
        kind = record.get("simulator", "MAX equivalence")
        key = (record["unit"], kind, record.get("profile", 0))
        actual.append(key)
        require(record["leaf_receipt"] in leaves, "Result references unbound leaf")
        leaf_path = within(ROOT, record["leaf_receipt"])
        directory = within(ROOT, record["artifact_root"])
        require(directory == leaf_path.parent, "Result artifact root differs from accepted leaf")
        bare = {k: v for k, v in record.items() if k not in ("artifact_root", "leaf_receipt")}
        matches = [r for r in leaves[record["leaf_receipt"]]["results"] if r == bare]
        require(len(matches) == 1, "Aggregate record differs from leaf")
        target = within(directory, record["unit"])
        if kind == "MAX equivalence":
            require(record.get("kind") == "MAX per-edge equivalence", "Unknown result kind")
            max_records[record["unit"]] = (record, target)
        else:
            require(record["returncode"] == 0 and record["pass"], "Functional run not PASS")
            require(record["name"] == inventory["PROFILE_NAMES"][record["profile"]],
                    "Profile label drift")
            stem = target / f"profile-{record['profile']}-{kind}.csv"
            observed = trace_metadata(stem, artifacts)
            require(observed == record["trace"] and observed["sha256"] == record["trace_sha256"]
                    and observed["canonical_sha256"] == record["canonical_trace_sha256"],
                    "Trace artifact differs from accepted record")
            log = stem.with_suffix(".log")
            text = log.read_text(errors="strict")
            require(all(marker in text for marker in record["pass"]) and "FATAL" not in text,
                    "Functional log differs from recorded PASS")
            artifacts[log.relative_to(ROOT).as_posix()] = sha(log)
            indexed[key] = observed
    require(len(actual) == len(set(actual)) and set(actual) == expected,
            "Compatibility must be exactly unique 202 Icarus / 64 Verilator / 26 MAX")
    require(len(actual) == sum(len(leaf["results"]) for leaf in leaves.values()),
            "Aggregate omitted a result from an accepted leaf")
    for unit, (record, target) in max_records.items():
        original = trace_metadata(target / "original-max.csv", artifacts)
        profiled = trace_metadata(target / "profile-0-iverilog.csv", artifacts)
        require(profiled == indexed[(unit, "iverilog", 0)], "MAX trusted metadata drift")
        require(original["sha256"] == record["original_trace_sha256"] and
                profiled["sha256"] == record["profiled_trace_sha256"], "MAX raw binding failed")
        require(all(original[k] == profiled[k] for k in (
            "sha256", "bytes", "rows", "canonical_sha256", "canonical_bytes", "reset_rows",
            "input_unknown_rows", "input_unknown_bits")), "MAX complete raw stream mismatch")
        log = target / "original-run.log"
        require("PASS" in log.read_text() and "FATAL" not in log.read_text(), "MAX original log failed")
        artifacts[log.relative_to(ROOT).as_posix()] = sha(log)
    pairs = 0
    for unit in dual + ["iopl_access"]:
        for profile in range(8):
            vl = indexed[(unit, "verilator", profile)]
            ic = indexed.get((unit, "iverilog", profile))
            if ic is None:
                require(unit == "iopl_access" and profile in range(2, 8), "Missing dual peer")
            else:
                require(all(ic[k] == vl[k] for k in ("canonical_sha256", "canonical_bytes", "rows")),
                        "Declared dual stream mismatch")
                pairs += 1
    require(pairs == 58, "Dual pair count differs")
    coverage = {(u, p) for u, sim, p in actual if sim != "MAX equivalence"}
    require(coverage == {(u, p) for u in units for p in range(8)}, "Missing unit/profile coverage")
    return dict(receipt_sha256=sha(path), counts=EXPECTED_COUNTS, unit_profile_coverage=208,
                generated_cpu_sha256=CPU_SHA256, source_binding=bindings, artifacts_sha256=artifacts,
                omitted_icarus=omitted,
                trace_scope="Complete streamed raw/canonical digests were bound to accepted receipts; bounded retained samples are not a reconstruction of the full streams. Raw CSV, when retained, was independently rehashed.")


def validate_machine(path, work):
    receipt = read_json(path)
    require(receipt["status"] == "AT_SPEED_PROFILES_DIRECTED_PASS", "Machine not accepted")
    bindings = source_binding(receipt, work, "machine")
    require(len(receipt["results"]) == 8 and
            {r["profile"] for r in receipt["results"]} == set(range(8)),
            "Machine profiles must be uniquely 0..7")
    artifacts = {}
    for record in receipt["results"]:
        log = path.parent / f"profile-{record['profile']}.log"
        require(sha(log) == record["log_sha256"] and record["marker"].startswith("AT_SYSTEM_BOUNDARY_PASS")
                and record["marker"] in log.read_text(), "Machine PASS log binding failed")
        artifacts[log.relative_to(ROOT).as_posix()] = sha(log)
    for name, digest in CPU_SHA256.items():
        relative = "vendor/spk286/rtl/timed/" + name
        require(bindings.get(relative) == digest, "Machine generated CPU not explicitly bound")
    return dict(receipt_sha256=sha(path), profiles=list(range(8)), source_binding=bindings,
                artifacts_sha256=artifacts, scope=receipt["scope"])


def audit_sta(run, modules, recorded):
    reports, out = run / "timing", run / "work/output_files"
    helper = modules["audit_fixed50_fit"]
    parser = modules["summarize_at_50mhz_timing"]
    inventory = (reports / "collections.txt").read_text()
    require(inventory.count("fixed_cpu_profile=1 observers=0") == 1 and
            "AT_DEBUG_CPU_CLK" not in inventory, "Unapproved fabric clock selection")
    clocks = re.findall(r"^clock=(.+) period=([\d.]+)\s*$", inventory, re.M)
    require(clocks and len(clocks) == len({name for name, _ in clocks}), "Duplicate clock inventory")
    clocks = {name: float(period) for name, period in clocks}
    require(clocks.get("FPGA_CLK2_50") == 20 and clocks.get("SDRAM_CLK") == 20,
            "CPU fabric and SDRAM must remain 50 MHz")
    for group in ("cpu", "bridge", "port", "code_buffer", "data_buffer", "sdram_owner",
                  "keyboard", "video", "prebios_stage1", "prebios_stage2"):
        matches = re.findall(r"^" + group + r"=(\d+)\s*$", inventory, re.M)
        require(len(matches) == 1 and int(matches[0]) > 0, "Missing STA register collection: " + group)
    expected = {(c, g, k) for c in helper.CORNERS for g in helper.GROUPS for k in ("setup", "hold")}
    expected |= {(c, "global", k) for c in helper.CORNERS for k in ("recovery", "removal")}
    rows = [line.split() for line in (reports / "path_counts.txt").read_text().splitlines() if line.strip()]
    require(all(len(row) == 5 for row in rows) and len(rows) == len(expected) and
            {tuple(row[:3]) for row in rows} == expected, "STA count keys must be unique complete 144")
    margins, parsed_reports = {}, {}
    for corner, group, kind, count, slack in rows:
        require(count.isdigit(), "Invalid STA path count")
        count = int(count)
        report = reports / corner / (group + "_" + kind + ".rpt")
        parsed = parser.parse_report(report)
        require(parsed["reported_paths"] == count, "Raw report count differs: " + str(report))
        value = None
        if count:
            value = float(slack)
            require(math.isfinite(value) and
                    abs(parsed["top_paths"][0]["slack_ns"] - value) < 0.00001,
                    "Raw report margin differs: " + str(report))
        if group == "global":
            command = report.read_text().split("Tcl Command:", 1)[1].split("Options:", 1)[0]
            require(not re.search(r"-(from|to)(?:_clock)?\s", command), "Global report was filtered")
            if kind in ("setup", "hold"):
                require(count > 0, "Empty global setup/hold")
        margins.setdefault(corner, {}).setdefault(group, {})[kind] = value
        parsed_reports[report.relative_to(run).as_posix()] = parsed
    require(margins == recorded["timing_ns"], "Frozen recorder timing differs from raw STA")
    coverage = {}
    for corner in helper.CORNERS:
        check = (reports / corner / "check_timing.rpt").read_text()
        pairs = [r for r in parser.table_rows(check.split("; No Clock", 1)[0])
                 if len(r) == 2 and r[1].isdigit()]
        require(len(pairs) == len({r[0] for r in pairs}), "Duplicate check_timing diagnostic")
        checks = {r[0]: int(r[1]) for r in pairs}
        mandatory = set(CHECK_COUNTS) | {"loops", "latches", "generated_clock", "virtual_clock",
                     "partial_multicycle", "multicycle_consistency", "pll_cross_check", "uncertainty"}
        require(mandatory.issubset(checks) and all(n == CHECK_COUNTS.get(k, 0)
                for k, n in checks.items()), "Inherited timing coverage changed: " + corner)
        families = Counter()
        for row in parser.table_rows(check):
            if len(row) == 2 and row[1] == "No clock feeds this register's clock port.":
                families[re.split(r"[|~]", row[0], maxsplit=1)[0]] += 1
        require(dict(families) == UNCLOCKED, "Unclocked families changed")
        unconstrained = (reports / corner / "unconstrained.rpt").read_text()
        upairs = [r for r in parser.table_rows(unconstrained.split("; Clock Status Summary", 1)[0])
                  if len(r) == 3 and r[1].isdigit() and r[2].isdigit()]
        require(len(upairs) == len({r[0] for r in upairs}), "Duplicate unconstrained summary")
        counts = {r[0]: [int(r[1]), int(r[2])] for r in upairs}
        require(counts.get("Illegal Clocks") == [0, 0] and
                counts.get("Unconstrained Clocks") == [0, 0], "Illegal/unconstrained clock")
        require(counts, "Missing unconstrained coverage inventory")
        coverage[corner] = dict(checks=checks, unclocked_families=dict(families),
            unconstrained=counts, fmax_mhz=parser.parse_fmax((reports / corner / "fmax.rpt").read_text()))
    summary = (out / "PCAT-286.sta.summary").read_text(encoding="latin-1")
    srows = [(m[1], float(m[2]), float(m[3])) for m in re.finditer(
        r"Type\s*:\s*(.+?)\nSlack\s*:\s*(-?[\d.]+)\nTNS\s*:\s*(-?[\d.]+)", summary)]
    require(len(srows) > 50 and len(srows) == len({name for name, _, _ in srows}),
            "STA summary missing or duplicate margins")
    models = {"7_slow_1100mv_100c": "Slow 1100mV 100C Model",
              "7_slow_1100mv_-40c": "Slow 1100mV -40C Model",
              "MIN_fast_1100mv_100c": "Fast 1100mV 100C Model",
              "MIN_fast_1100mv_-40c": "Fast 1100mV -40C Model"}
    for corner, model in models.items():
        for kind in ("Setup", "Hold", "Minimum Pulse Width"):
            require(any(name.startswith(model + " " + kind + " ") for name, _, _ in srows),
                    "Missing STA summary corner/category: " + corner + " " + kind)
        for kind in ("Setup", "Hold"):
            worst = min(value for name, value, _ in srows if name.startswith(model + " " + kind + " "))
            require(abs(worst - margins[corner]["global"][kind.lower()]) < 0.00001,
                    "Global raw margin differs from STA summary: " + corner + " " + kind)
    nonnegative = all(margins[c]["global"][k] is not None and margins[c]["global"][k] >= 0
                      for c in helper.CORNERS for k in ("setup", "hold"))
    nonnegative &= all(margins[c]["global"][k] is None or margins[c]["global"][k] >= 0
                       for c in helper.CORNERS for k in ("recovery", "removal"))
    require(nonnegative == recorded["global_setup_hold_recovery_removal_nonnegative"],
            "Recorder closure claim differs from raw evidence")
    nonpositive = [dict(type=name, slack_ns=value, tns_ns=tns) for name, value, tns in srows if value <= 0]
    return dict(path_count_rows=len(rows), unique_corner_group_kind=len(expected), timing_ns=margins,
                global_setup_hold_recovery_removal_nonnegative=nonnegative,
                all_summary_margins_positive=not nonpositive, nonpositive_summary_margins=nonpositive,
                clock_inventory_ns=clocks, coverage=coverage, summary_margin_count=len(srows),
                parsed_raw_reports=parsed_reports,
                scope="Inherited platform I/O coverage is explicitly retained; positive reported margins do not establish complete I/O/board closure or hardware acceptance.")


def audit_resources(run, modules, recorded, baseline):
    helper, accounting = modules["audit_fixed50_fit"], modules["analyze_pcat_resources"]
    out = run / "work/output_files"
    measured = helper.resources(out)
    require(measured == recorded["resources"], "Recorded resources differ from fitter")
    bm = read_json(baseline / "manifest.json")
    for name, expected in bm["sha256"].items():
        require(sha(within(baseline, name)) == expected, "Baseline artifact drift: " + name)
    require(sha(baseline / "resources.json") == BASELINE_JSON_SHA256 and
            sha(baseline / "PCAT-286.fit.summary") == BASELINE_SUMMARY_SHA256,
            "Selected baseline revision changed")
    base = read_json(baseline / "resources.json")
    require(base["status"] == "SELECTED_FIT_HIERARCHY_ACCOUNTING_PASS" and
            base["fit_summary_sha256"] == sha(baseline / "PCAT-286.fit.summary"), "Baseline summary binding failed")
    summary = (baseline / "PCAT-286.fit.summary").read_text(encoding="latin-1")
    pll = re.findall(r"^Total PLLs\s*:\s*([\d,]+)\s*/\s*([\d,]+)", summary, re.M)
    require(len(pll) == 1 and "Fitter Status : Successful" in summary, "Baseline PLL summary missing")
    baseline_plls = int(pll[0][0].replace(",", ""))
    require(baseline_plls == 3, "Selected baseline PLL cost changed")
    for field, label in dict(alm_needed="Logic utilization (in ALMs)", registers="Total registers",
                            memory_bits="Total block memory bits", m10k="Total RAM Blocks",
                            dsp="Total DSP Blocks").items():
        match = re.findall(r"^" + re.escape(label) + r"\s*:\s*([\d,]+)", summary, re.M)
        require(len(match) == 1, "Baseline summary field missing: " + label)
        expected = base["global"][field] + (base["global"]["io_registers"] if field == "registers" else 0)
        require(int(match[0].replace(",", "")) == expected, "Baseline global cost differs from summary")
    mapping = dict(equivalent_alms="alm_needed", placed_alms="alm_placed",
                   memory_bits="memory_bits", m10k="m10k", dsp="dsp")
    delta = {name: measured[name] - base["global"][key] for name, key in mapping.items()}
    delta["registers"] = measured["registers"] - base["global"]["registers"] - base["global"]["io_registers"]
    delta["plls"] = measured["plls"] - baseline_plls
    require(delta == recorded["delta_from_selected_fixed50"], "Resource delta differs from bound baseline")
    rows = accounting.parse(out / "PCAT-286.fit.rpt")
    cpus = [r for r in rows if r["entity"] == "spk286_profiled"]
    require(len(cpus) == 1 and cpus[0]["path"].endswith("|spk286_profiled:cpu") and
            not any(r["entity"] == "spk286" for r in rows), "Fitted design must contain one selected CPU")
    cpu = {k: cpus[0][k]["inclusive"] for k in accounting.METRICS}
    require(cpu == recorded["cpu_resources"], "CPU resource attribution drift")
    blocks = accounting.grouped(rows)
    totals = dict(alm_needed=measured["equivalent_alms"], alm_placed=measured["placed_alms"],
                  registers=rows[0]["registers"]["inclusive"],
                  io_registers=rows[0]["io_registers"]["inclusive"],
                  memory_bits=measured["memory_bits"], m10k=measured["m10k"], dsp=measured["dsp"])
    require(totals["registers"] + totals["io_registers"] == measured["registers"],
            "Hierarchy/global register split changed")
    residual = {"block": "Global/hierarchy rounding and unattributed placement",
                **{k: round(totals[k] - rows[0][k]["inclusive"], 3) for k in accounting.METRICS}}
    blocks.append(residual)
    require(all(abs(sum(b[k] for b in blocks) - totals[k]) < 0.02 for k in accounting.METRICS),
            "Global/hierarchy resource reconciliation failed")
    seed = helper.fitted_seed((run / "work/PCAT-286.qsf").read_text(),
                             (out / "PCAT-286.fit.rpt").read_text(encoding="latin-1"))
    require(seed == recorded["placement_seed"], "Fitted seed drift")
    return dict(resources=measured, delta_from_selected_fixed50=delta, cpu_resources=cpu,
                global_totals=totals, hierarchy_residual=residual, placement_seed=seed,
                baseline=dict(path=str(baseline), json_sha256=sha(baseline / "resources.json"),
                    manifest_sha256=sha(baseline / "manifest.json"),
                    selected_fit_summary_sha256=sha(baseline / "PCAT-286.fit.summary"),
                    parsed_plls=baseline_plls, device_plls=int(pll[0][1])),
                hierarchy_entities=len(rows), blocks=blocks), accounting.table(blocks, measured["placed_alms"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--record", type=Path, required=True, help="frozen recorder receipt")
    parser.add_argument("--machine", type=Path, required=True)
    parser.add_argument("--compatibility", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, default=ROOT / "docs/evidence/pcat-resources-20261004")
    parser.add_argument("--output", type=Path, required=True, help="fresh supplementary evidence directory")
    args = parser.parse_args()
    run, output = args.run.resolve(), args.output.resolve()
    for path in (run, args.record.resolve(), args.machine.resolve(), args.compatibility.resolve(), output):
        require(path.is_relative_to(ROOT), "Audit path outside workspace")
    require(output.is_relative_to(ROOT / "build") and not output.exists(), "Output must be fresh under build")
    work, out = run / "work", run / "work/output_files"
    manifest = read_json(run / "manifest.json")
    sources = {n.replace("\\", "/"): h for n, h in manifest["source_sha256"].items()}
    recorded = read_json(args.record)
    require(recorded["status"] == "NEW_OSD_RBF_MEASURED_NOT_HARDWARE_ACCEPTED" and
            recorded["manifest_sha256"] == sha(run / "manifest.json") and
            recorded["source_revision"] == manifest["head"] and recorded["source_count"] == len(sources),
            "Frozen recorder snapshot binding differs")
    require(recorded["auditor_sha256"] == RECORDER_SHA256 and
            sha(work / "scripts/record_p06_osd_fit.py") == RECORDER_SHA256 and
            sources["scripts/record_p06_osd_fit.py"] == RECORDER_SHA256,
            "Frozen recorder source revision differs")
    started = datetime.fromisoformat((run / "compile-started.txt").read_text().strip())
    compile_log = (run / "compile.log").read_text()
    require(re.search(r"Full Compilation was successful\. 0 errors", compile_log), "Compilation not successful")
    generated = {}
    for name, digest in sources.items():
        actual = sha(within(work, name))
        if actual != digest:
            value = '`define BUILD_DATE "' + started.strftime("%y%m%d") + '"'
            require(name == "build_id.v" and (work / name).read_text() == value and
                    "Generated: /build/build_id.v: " + value in compile_log,
                    "Frozen compiled source changed: " + name)
            generated[name] = dict(before=digest, compiled=actual, value=value)
    require(generated == recorded["generated_sources"], "Generated build-date binding differs")
    for name, digest in CPU_SHA256.items():
        require(sha(work / "vendor/spk286/rtl/timed" / name) == digest, "Compiled CPU revision differs")
    generation = read_json(work / "vendor/spk286/rtl/timed/generation.json")
    require(generation["generated_sha256"] == CPU_SHA256, "CPU generation receipt revision differs")
    for name, digest in generation["sources_sha256"].items():
        require(sources.get(name) == digest and sha(within(work, name)) == digest,
                "Generated CPU source guard drift: " + name)
    modules, helpers = snapshot_helpers(work, sources)
    for name, path in (("machine", args.machine), ("compatibility", args.compatibility)):
        require(recorded["validation"][name]["sha256"] == sha(path), "Recorder validation receipt drift")
        require(recorded["validation"][name]["scope"] == read_json(path)["scope"],
                "Recorder validation scope drift")
    machine = validate_machine(args.machine.resolve(), work)
    compatibility = validate_compatibility(args.compatibility.resolve(), work)
    timing = audit_sta(run, modules, recorded)
    resource, block_table = audit_resources(run, modules, recorded, args.baseline.resolve())
    compiled_rom = modules["check_sync_microcode_image"].analyze_compiled_image(run)
    # Host path spelling may differ between the Windows recorder and WSL audit.
    # The actual run manifest and image/contract digests still match exactly.
    def rom_identity(data):
        identity = {key: value for key, value in data.items() if key != "run"}
        identity["mif"] = identity["mif"].replace("\\", "/")
        return identity
    require(rom_identity(compiled_rom) == rom_identity(recorded["compiled_rom"]),
            "Compiled ROM image binding differs")
    artifacts = {}
    for name, expected in recorded["artifact_sha256"].items():
        name = name.replace("\\", "/")
        require(name not in artifacts, "Duplicate normalized recorded artifact key")
        target = within(run, name)
        require(sha(target) == expected, "Recorded fitted artifact drift: " + name)
        artifacts[name] = expected
    required = {"compile.log", "container-image.txt", "profile-check.log", "project-check.log",
                "work/output_files/PCAT-286.fit.rpt", "work/output_files/PCAT-286.fit.summary"}
    required |= {p.relative_to(run).as_posix() for p in (run / "timing").rglob("*") if p.is_file()}
    require(set(artifacts) == required, "Recorder fitted artifact inventory differs")
    for name in ("PCAT-286.rbf", "PCAT-286.sof"):
        target = out / name
        require(target.stat().st_size > 0 and target.stat().st_mtime > (run / "compile-started.txt").stat().st_mtime,
                "Fitted bitstream not newer than compile start")
        artifacts[target.relative_to(run).as_posix()] = sha(target)
    require(recorded["rbf"]["sha256"] == sha(out / "PCAT-286.rbf") and
            recorded["rbf"]["bytes"] == (out / "PCAT-286.rbf").stat().st_size and
            recorded["sof_sha256"] == sha(out / "PCAT-286.sof"), "Bitstream binding drift")
    artifacts["work/output_files/PCAT-286.sta.summary"] = sha(out / "PCAT-286.sta.summary")
    features = dict(re.findall(r'VERILOG_MACRO "(ENABLE_[A-Z0-9_]+)=([01])"',
                              (work / "config.tcl").read_text()))
    require(features == recorded["feature_configuration"], "Recorded feature configuration drift")
    inventory = (run / "timing/collections.txt").read_text()
    for name, value in features.items():
        require(re.search(r"^macro=" + re.escape(name + "=" + value) + r"\s*$", inventory, re.M),
                "STA feature macro differs from frozen config: " + name)
    output.mkdir(parents=True)
    source = Path(__file__).resolve()
    command = [sys.executable, str(source), str(run), "--record", str(args.record.resolve()),
               "--machine", str(args.machine.resolve()), "--compatibility", str(args.compatibility.resolve()),
               "--baseline", str(args.baseline.resolve()), "--output", "FRESH_OUTPUT_DIRECTORY"]
    result = dict(status="P06_OSD_FIT_SUPPLEMENTARY_EVIDENCE_INTEGRITY_PASS",
        auditor_sha256=sha(source), frozen_recorder_sha256=RECORDER_SHA256,
        recorder_receipt_sha256=sha(args.record), manifest_sha256=sha(run / "manifest.json"),
        source_revision=manifest["head"], source_count=len(sources), generated_sources=generated,
        imported_frozen_helpers_sha256=helpers, machine=machine, compatibility=compatibility,
        timing=timing, resource_accounting=resource, compiled_rom=compiled_rom,
        feature_configuration=features,
        run_artifacts_sha256=artifacts, rbf=recorded["rbf"],
        timing_result="NONPOSITIVE_REPORTED_MARGIN" if timing["nonpositive_summary_margins"] or
            not timing["global_setup_hold_recovery_removal_nonnegative"] else
            "POSITIVE_REPORTED_MARGINS_UNDER_DECLARED_COVERAGE",
        scope="Evidence integrity only; inherited unconstrained/partially constrained platform I/O and conditional SDRAM board/device budget remain declared. Directed functional coverage is 26 units x 8 profiles, not a full OS or hardware regression. Historical scheduling is provisional; no cycle-accuracy certification.",
        reproduce_cli=shlex.join(command))
    (output / "receipt.json").write_text(json.dumps(result, indent=2) + "\n", newline="\n")
    (output / "blocks.md").write_text(block_table, newline="\n")
    (output / "REPRODUCE.txt").write_text(shlex.join(command) + "\n", newline="\n")
    (output / "manifest.json").write_text(json.dumps({"auditor_sha256": sha(source), "sha256": {
        name: sha(output / name) for name in ("receipt.json", "blocks.md", "REPRODUCE.txt")}}, indent=2) + "\n")
    print(result["status"])
    print(result["timing_result"])
    print(json.dumps({"resources": resource["resources"], "delta": resource["delta_from_selected_fixed50"],
                      "rbf": result["rbf"]}, indent=2))


if __name__ == "__main__":
    main()
