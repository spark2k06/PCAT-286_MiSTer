"""Record completed production-buffer checks and bind them to sources/logs."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def artifact(path):
    path = Path(path)
    if not path.is_absolute():
        path = ROOT / path
    return dict(path=path.relative_to(ROOT).as_posix(),
                sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def verify(entry):
    assert artifact(entry["path"])["sha256"] == entry["sha256"], entry["path"]


def main():
    build = ROOT / "build/code-buffer-production"
    for line in (build / "sources.sha256").read_text().splitlines():
        expected, path = line.split("  ", 1)
        assert artifact(path)["sha256"] == expected, path
    runs = []
    for lines in (1, 64):
        for enabled in (1, 0):
            pair = []
            for simulator in ("iv", "vlt"):
                path = build / f"{simulator}-l{lines}-e{enabled}.log"
                results = [line for line in path.read_text().splitlines()
                           if line.startswith("MULTILINE_COHERENCE_PASS ")]
                assert len(results) == 1, path
                row = {k: int(v) for k, v in (item.split("=") for item in results[0].split()[1:])}
                assert (row["lines"], row["ways"], row["extra"], row["ENABLE"]) == (lines, 1, 0, enabled)
                pair.append(row)
                runs.append(dict(simulator=simulator, result=row, log=artifact(path)))
            assert pair[0] == pair[1], (lines, enabled)
    mutations = json.loads((ROOT / "build/code-buffer-production-mutants/results.json").read_text())
    assert mutations["production"] and mutations["pristine"]["passed"]
    assert len(mutations["mutants"]) == 6 and all(m["rejected"] for m in mutations["mutants"])
    for source in mutations["sources"]:
        verify(source)
    for row in [mutations["pristine"], *mutations["mutants"]]:
        verify(row["log"])
        verify(row["compile_log"])
    coherence = json.loads((ROOT / "build/code-buffer-coherence-fixed/receipt.json").read_text())
    assert len(coherence["results"]) == 6 and all(r["result"] == "PASS" for r in coherence["results"])
    for key in ("production_rtl", "testbench", "runner"):
        verify(coherence[key])
    for row in coherence["results"]:
        verify(row["log"])
    driver = ROOT / "build/code-buffer-integration-final.log"
    text = driver.read_text()
    assert "AT_CODE_BUFFER_INTEGRATION_PASS" in text
    names = [line.split()[1] for line in text.splitlines() if line.startswith("CODE_BUFFER_INTEGRATION_PASS ")]
    assert len(names) == 8 and len(set(names)) == 8
    integration = [dict(test=name, log=artifact(f"build/code-buffer-integration/{name}.log")) for name in names]
    reset_runs = []
    for state in (0, 4, 5, 6):
        path = ROOT / f"build/code-buffer-warm-reset/state-{state}.log"
        text = path.read_text()
        assert f"FORCE_WARM_RESET_PASS state={state} " in text
        assert "CODE_BUFFER_RESET_STRESS irq_handlers=1 refresh=253 hits=225 misses=78" in text
        reset_runs.append(dict(state=state, log=artifact(path)))
    comparison = ROOT / "build/code-buffer-512b-performance-final/production-comparison.json"
    performance = json.loads(comparison.read_text())
    assert performance["exact_model_and_bypass_match"] and len(performance["runs"]) == 8
    for row in performance["runs"]:
        assert artifact(row["log"])["sha256"] == row["log_sha256"]
    for path, expected in performance["simulation_source_sha256"].items():
        assert artifact(path)["sha256"] == expected, path
    sources = [
        "rtl/spk286_integration/spk286_at_sdram_read_buffer.sv",
        "sim/spk286_integration/spk286_at_multiline_code_buffer_tb.sv",
        "sim/spk286_integration/spk286_at_bios_first_fetch_tb.sv",
        "sim/spk286_integration/spk286_at_memory_perf_tb.sv",
        "tests/firmware/code_buffer_reset_stress.asm",
        "scripts/test_at_code_buffer_production.sh", "scripts/test_at_code_buffer_integration.sh",
        "scripts/test_at_code_buffer_warm_reset.sh", "scripts/record_code_buffer_validation.py",
    ]
    receipt = dict(scope="Production instruction buffer; standalone CPU RTL unchanged",
                   sources=[artifact(path) for path in sources],
                   scoreboard_runs=runs,
                   totals=dict(runs=len(runs), requests=sum(r["result"]["requests"] for r in runs),
                               checks=sum(r["result"]["checks"] for r in runs)),
                   mutation_audit=mutations, coherence_regression=coherence,
                   integration=integration, integration_driver=artifact(driver),
                   warm_resets=reset_runs, performance_comparison=artifact(comparison))
    output = ROOT / "build/code-buffer-production-validation.json"
    output.write_text(json.dumps(receipt, indent=2) + "\n")
    print(f"CODE_BUFFER_VALIDATION_RECEIPT_PASS {receipt['totals']} path={output}")


if __name__ == "__main__":
    main()
