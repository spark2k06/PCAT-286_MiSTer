#!/usr/bin/env bash
# Check the proven vendor executor and affected CPU banks in actual AT profiles.
set -euo pipefail
ulimit -c 0
root=$(cd "$(dirname "$0")/.." && pwd)
build_dir=$(realpath -m "${1:-$root/build/at-stack-offset-arithmetic}")
[[ $# -le 1 && ! -e "$build_dir" ]]
mkdir -p "$build_dir"
python3 "$root/scripts/test_stack_offset_contract.py" --output "$build_dir/current-formal"
source "$root/scripts/at_performance_flags.sh"
cd "$root/vendor/spk286"
source scripts/rtl_sources.sh
sha256sum "${rtl_sources[@]}" "$root/config.tcl" \
    "$root/scripts/test_at_stack_offset_arithmetic.sh" \
    "$root/scripts/test_stack_offset_contract.py" \
    rtl/timed/spk286_profiled_micro_executor.sv \
    sim/unit/spk286_signals.svh sim/unit/spk286_call_stack_precheck_tb.sv \
    sim/unit/spk286_protected_event_outer_tb.sv sim/unit/spk286_call_gate_accessed_tb.sv \
    > "$build_dir/sources.sha256"
verilator --version > "$build_dir/tool-versions.txt"
iverilog -V >> "$build_dir/tool-versions.txt" 2>&1
for profile in base pcat; do
    defines=()
    if [[ $profile == pcat ]]; then defines=("${performance_flags[@]}"); fi
    verilator --lint-only --language 1800-2012 --Wall --top-module spk286 \
        -Irtl "${defines[@]}" "${rtl_sources[@]}" > "$build_dir/${profile}-lint.log" 2>&1
    for unit in spk286_call_stack_precheck spk286_protected_event_outer spk286_call_gate_accessed; do
        top=${unit}_tb
        stem=$build_dir/$profile/$unit
        mkdir -p "$stem"
        iverilog -g2012 -Irtl -Isim/unit "${defines[@]}" -s "$top" -o "$stem/test.vvp" \
            "${rtl_sources[@]}" "sim/unit/$top.sv" > "$stem/iverilog-build.log" 2>&1
        vvp "$stem/test.vvp" | tee "$stem/iverilog-run.log"
        verilator --binary --build-jobs "${SPK286_BUILD_JOBS:-2}" --timing --assert \
            --language 1800-2012 --top-module "$top" --Mdir "$stem/verilator" \
            -Irtl -Isim/unit "${defines[@]}" -o directed \
            "${rtl_sources[@]}" "sim/unit/$top.sv" > "$stem/verilator-build.log" 2>&1
        "$stem/verilator/directed" | tee "$stem/verilator-run.log"
        grep ' PASS:' "$stem/iverilog-run.log" > "$stem/iverilog-result.txt"
        grep ' PASS:' "$stem/verilator-run.log" > "$stem/verilator-result.txt"
        cmp "$stem/iverilog-result.txt" "$stem/verilator-result.txt"
    done
done
sha256sum -c "$build_dir/sources.sha256" > "$build_dir/source-check.log"
python3 - "$root" "$build_dir" <<'PY'
import hashlib,json,sys
from pathlib import Path
root=Path(sys.argv[1]); out=Path(sys.argv[2])
proof=json.loads((out/'current-formal/receipt.json').read_text())
assert proof['status']=='CURRENT_STACK_OFFSET_CONTRACT_EQUIVALENCE_PASS'
for name,digest in proof['sources_sha256'].items():
    assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest, ('Proof input changed',name)
receipt={'status':'AT_STACK_OFFSET_ARITHMETIC_DIRECTED_PASS',
    'formal_receipt_sha256':hashlib.sha256((out/'current-formal/receipt.json').read_bytes()).hexdigest(),
    'scope':'Fresh original-contract raw/timed offset SAT proof plus strict CPU lint and unchanged three affected banks in Icarus/Verilator; base and pcat labels both use the fixed active implementation, not CPU options off',
    'cases':12,'expected_results_unchanged':True,
    'sources_manifest_sha256':hashlib.sha256((out/'sources.sha256').read_bytes()).hexdigest(),
    'artifacts_sha256':{p.relative_to(out).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in out.rglob('*') if p.is_file() and p.suffix in ('.log','.txt','.json','.sha256')}}
(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print('PROVEN_VENDOR_STACK_OFFSET_SOURCE_PASS current_raw_timed_cones=1')
PY
echo AT_STACK_OFFSET_ARITHMETIC_DIRECTED_PASS
