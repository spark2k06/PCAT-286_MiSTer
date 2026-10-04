#!/usr/bin/env python3
"""Extract inclusive/self hierarchy accounting from a Quartus fitter report."""
import argparse
import hashlib
import json
from pathlib import Path
import re


def amount(value):
    match = re.fullmatch(r"(-?[\d,.]+)(?:\s+\((-?[\d,.]+)\))?", value)
    if not match:
        raise ValueError(value)
    total = float(match[1].replace(",", ""))
    own = float(match[2].replace(",", "")) if match[2] else None
    return {"inclusive": total, "self_reported": own}


def parse(report):
    text = report.read_text(errors="strict")
    marker = "; Fitter Resource Utilization by Entity "
    start = text.index(marker)
    lines = text[start:].splitlines()
    header = None; rows = []
    for line in lines[1:]:
        fields = [p.strip() for p in line.split(";")[1:-1]]
        if fields and fields[0] == "Compilation Hierarchy Node":
            header = fields; continue
        if header and fields and fields[0].startswith("|"):
            assert len(fields) == len(header)
            raw = dict(zip(header, fields))
            row = {"path": raw["Full Hierarchy Name"], "entity": raw["Entity Name"],
                   "depth": raw["Full Hierarchy Name"].count("|") - 1}
            columns = {"alm_needed": "ALMs needed [=A-B+C]", "alm_placed": "[A] ALMs used in final placement",
                "alm_recoverable": "[B] Estimate of ALMs recoverable by dense packing", "alm_unavailable": "[C] Estimate of ALMs unavailable",
                "aluts": "Combinational ALUTs", "registers": "Dedicated Logic Registers", "io_registers": "I/O Registers",
                "memory_bits": "Block Memory Bits", "m10k": "M10Ks", "dsp": "DSP Blocks"}
            row.update({name: amount(raw[column]) for name, column in columns.items()})
            rows.append(row)
        elif rows and fields and not fields[0].startswith("|"):
            break
    assert rows and rows[0]["path"] == "|sys_top"
    assert len({r["path"] for r in rows}) == len(rows)
    for row in rows:
        children = [r for r in rows if r["depth"] == row["depth"]+1 and r["path"].startswith(row["path"]+"|")]
        for key in columns:
            residual = row[key]["inclusive"] - sum(r[key]["inclusive"] for r in children)
            row[key]["self_from_children"] = round(residual, 3)
    return rows


METRICS = ["alm_needed", "alm_placed", "registers", "io_registers", "memory_bits", "m10k", "dsp"]
GROUPS = {
    "CPU SPK286": ["spk286_machine_cpu"],
    "EGA/VGA+ adapter and VRAM": ["spk286_at_video_adapter"],
    "RAM read buffers and posted writes": ["spk286_at_sdram_data_buffer", "spk286_at_sdram_read_buffer", "spk286_at_posted_write_buffer"],
    "PC sound devices and MT32-Pi": ["spk286_at_sound", "mt32pi"],
    "RTC/CMOS and clock": ["spk286_at_rtc_cmos", "spk286_at_rtc_clock"],
    "DMA": ["spk286_at_dma"],
    "PIC": ["spk286_at_pic"],
    "PIT and clock": ["spk286_at_pit", "spk286_at_pit_clock"],
    "Keyboard, 8042 and serial mouse": ["spk286_at_keyboard", "spk286_at_8042", "MSMouseWrapper"],
    "IDE and floppy": ["spk286_at_xtide", "spk286_at_fdc"],
    "Serial ports and MPU401": ["spk286_at_serial"],
    "Core framebuffer and video output": ["ega_fb_capture", "ega_fb_readout", "ega_ddr_arbiter", "video_mixer", "video_monochrome_converter", "video_source_switch", "at_video_options_cdc", "ega_monitor_profile_latch", "at_cdc_snapshot:at_crt350_config_cdc"],
    "MiSTer scaler and HDMI/VGA output": ["ascal", "at_scaler_config", "at_hdmi_output", "at_hdmi_vsync", "at_scanlines_status", "at_video_output_config", "at_frame_counter", "csync", "pll_cfg_hdmi", "pll_hdmi", "pll_hdmi_adj", "scanlines", "shadowmask", "sync_fix", "vga_out", "yc_out"],
    "MiSTer OSD": ["osd"],
    "MiSTer audio output and ALSA": ["audio_out", "alsa"],
    "HPS I/O, ROM loading and control": ["hps_io", "hps_ext", "spk286_at_hps_rom_loader", "at286ctl", "at286ctl_resolve"],
    "Memory bridge, SDRAM and arbitration": ["spk286_at_bus_bridge", "spk286_at_mister_memory_port", "spk286_at_mister_sdram_owner", "spk286_at_arbiter", "spk286_at_memory_decode", "spk286_at_refresh", "sysmem_lite", "ddr_svc"],
    "Other integration and peripherals": [],
}


def classify(row):
    segments = row["path"].split("|")[1:]
    for label, prefixes in GROUPS.items():
        if any(s == p or s.startswith(p+":") for s in segments for p in prefixes):
            return label
    return "Other integration and peripherals"


def grouped(rows):
    totals = {label: {key: 0.0 for key in METRICS} for label in GROUPS}
    for row in rows:
        label = classify(row)
        row["group"] = label
        for key in METRICS:
            totals[label][key] += row[key]["self_from_children"]
    for key in METRICS:
        assert abs(sum(g[key] for g in totals.values()) - rows[0][key]["inclusive"]) < 0.02, key
    return [{"block": label, **{key: round(value, 3) for key, value in values.items()}}
            for label, values in totals.items()]


def table(items, total):
    text = "| Block | ALMs needed | ALMs placed | % of placed design | Registers | M10K | DSP |\n"
    text += "| --- | ---: | ---: | ---: | ---: | ---: | ---: |\n"
    for item in items:
        text += f"| {item['block']} | {item['alm_needed']:,.1f} | {item['alm_placed']:,.1f} | {100*item['alm_placed']/total:.2f}% | {int(item['registers']+item['io_registers']):,} | {int(item['m10k'])} | {int(item['dsp'])} |\n"
    return text


def write_analysis(report, rows, output):
    root = Path(__file__).resolve().parents[1]
    selection_path = root / "docs/evidence/fixed50-timing-20261003/admission-retained-fdc-selection.json"
    selected = json.loads(selection_path.read_text())
    assert selected["selected_run"] in report.as_posix()
    rbf = report.with_name("PCAT-286.rbf")
    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    assert digest(rbf) == selected["rbf"]["sha256"]
    summary = report.with_suffix(".summary")
    frozen_summary = root / "docs/evidence/fixed50-timing-20261003/admission-retained-fdc-seed1-PCAT-286.fit.summary"
    assert summary.read_bytes() == frozen_summary.read_bytes()
    totals = {"alm_needed": 29993, "alm_placed": 35698, "registers": 38070, "io_registers": 49,
              "memory_bits": 3301019, "m10k": 416, "dsp": 39}
    assert rows[0]["registers"]["inclusive"] + rows[0]["io_registers"]["inclusive"] == 38119
    for key in ["m10k", "memory_bits", "dsp"]:
        assert rows[0][key]["inclusive"] == totals[key]
    # Hierarchy attribution gives 35697.0; global placement rounds/accounts one
    # additional ALM. Keep that difference explicit rather than assigning to CPU.
    blocks = grouped(rows)
    residual = {"block": "Global/hierarchy rounding and unattributed placement", **{
        key: round(totals[key]-rows[0][key]["inclusive"], 3) for key in METRICS}}
    blocks.append(residual)
    for key in METRICS:
        assert abs(sum(g[key] for g in blocks)-totals[key]) < 0.02
    cpu = next(r for r in rows if r["entity"] == "spk286" and r["path"].endswith("|spk286:cpu"))
    children = [r for r in rows if r["depth"] == cpu["depth"]+1 and r["path"].startswith(cpu["path"]+"|")]
    cpu_blocks = [{"block": r["entity"], **{key:r[key]["inclusive"] for key in METRICS}} for r in children]
    cpu_blocks.append({"block": "CPU top-level glue", **{key:cpu[key]["self_from_children"] for key in METRICS}})
    cpu_blocks.sort(key=lambda r:r["alm_placed"], reverse=True)
    for key in METRICS:
        assert abs(sum(g[key] for g in cpu_blocks)-cpu[key]["inclusive"]) < 0.02
    output.mkdir(parents=True, exist_ok=False)
    result = {"status": "SELECTED_FIT_HIERARCHY_ACCOUNTING_PASS", "selected_run": selected["selected_run"],
        "report_sha256": digest(report), "fit_summary_sha256": digest(summary), "rbf_sha256": digest(rbf),
        "selection_sha256": digest(selection_path), "hierarchy_entities": len(rows),
        "global": totals, "device": {"alm":41910,"m10k":553,"dsp":112,"pll":6},
        "cpu_percent_placed_design": 100*cpu["alm_placed"]["inclusive"]/totals["alm_placed"],
        "cpu_percent_placed_device": 100*cpu["alm_placed"]["inclusive"]/41910,
        "cpu_percent_needed_design": 100*cpu["alm_needed"]["inclusive"]/totals["alm_needed"],
        "blocks": blocks, "cpu_blocks": cpu_blocks, "entities": rows,
        "scope": "Hierarchy attribution, not standalone synthesis costs or additive placed-ALM guarantees. P06 private pilot excluded."}
    (output / "resources.json").write_text(json.dumps(result,indent=2)+"\n",newline="\n")
    text = report.read_text(); begin = text.index("; Fitter Resource Utilization by Entity ")
    end = text.index("\n\n", begin)
    (output / "hierarchy.rpt").write_text(text[begin:end]+"\n",newline="\n")
    (output / "PCAT-286.fit.summary").write_bytes(summary.read_bytes())
    (output / "blocks.md").write_text(table(blocks+[{'block':'TOTAL', **totals}],totals["alm_placed"]),newline="\n")
    (output / "cpu.md").write_text(table(cpu_blocks,cpu["alm_placed"]["inclusive"]),newline="\n")
    (output / "manifest.json").write_text(json.dumps({"sha256": {p.name:digest(p) for p in output.iterdir() if p.is_file()},
        "analyzer_sha256":digest(Path(__file__)),"selected_run":selected["selected_run"]},indent=2)+"\n",newline="\n")
    print(table(blocks+[{'block':'TOTAL', **totals}],totals["alm_placed"]))
    print(table(cpu_blocks,cpu["alm_placed"]["inclusive"]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--depth", type=int, default=3)
    parser.add_argument("--analysis", type=Path, help="Write selected-fit block and CPU accounting")
    args = parser.parse_args()
    rows = parse(args.report)
    if args.analysis:
        write_analysis(args.report, rows, args.analysis)
        return
    result = {"report": args.report.as_posix(), "sha256": hashlib.sha256(args.report.read_bytes()).hexdigest(), "entities": rows}
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n", newline="\n")
    for row in rows:
        if row["depth"] <= args.depth:
            print(f"{row['path']}: needed={row['alm_needed']['inclusive']} placed={row['alm_placed']['inclusive']} regs={row['registers']['inclusive']} M10K={row['m10k']['inclusive']} DSP={row['dsp']['inclusive']}")
    print("Entities:", len(rows))


if __name__ == "__main__":
    main()
