#!/usr/bin/env bash
# Compare the RAM-inference rewrite with the accepted 4 KiB implementation.
set -euo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
output=${PCAT_BUILD_DIR:-$root/build/at-code-buffer-equivalence}
baseline=${PCAT_CODE_BUFFER_BASELINE:-0399806}
mkdir -p "$output"
cd "$root"
git show "$baseline:rtl/spk286_integration/spk286_at_sdram_read_buffer.sv" > "$output/before.sv"
rtl=rtl/spk286_integration/spk286_at_sdram_read_buffer.sv
bench=sim/spk286_integration/spk286_at_multiline_code_buffer_tb.sv
sha256sum "$rtl" "$bench" scripts/test_at_code_buffer_equivalence.sh \
  "$output/before.sv" > "$output/sources.sha256"
python3 - "$output" "$rtl" "$bench" <<'PY'
from pathlib import Path
import re, sys
output, rtl, bench = map(Path, sys.argv[1:])
before = (output/'before.sv').read_text()
(output/'before-renamed.sv').write_text(before.replace(
    'module spk286_at_sdram_read_buffer #(', 'module code_buffer_before #(', 1))
ports = rtl.read_text().split(') (', 1)[1].split('\n);', 1)[0]
decls, connections, checks = [], [], []
for direction, width, name in re.findall(
        r'(input|output)\s+logic\s*(\[[^\]]+\])?\s*(\w+)', ports):
    if direction == 'output':
        decls.append(f'wire {width} before_{name};')
        connections.append(f'.{name}(before_{name})')
        guard = ('in_read_data_valid' if name == 'in_read_data' else
                 'out_valid && out_command_valid' if name in (
                     'out_owner', 'out_write', 'out_refresh', 'out_code_fetch',
                     'out_burst', 'out_cycle_class', 'out_address',
                     'out_byte_enable', 'out_data_out') else "1'b1")
        checks.append(f'if (({guard}) && ({name} !== before_{name})) '
                      f'$fatal(1, "CYCLE_EQUIVALENCE_FAIL {name} cycle=%0d", cycles);')
    else:
        connections.append(f'.{name}({name})')
insertion = '\n'.join(decls) + '\n' + '''
code_buffer_before #(.ENABLE(ENABLE), .LINE_COUNT(LINE_COUNT), .SYNC_TAGS(SYNC_TAGS))
before_dut (
''' + ',\n'.join(connections) + ''');
integer compared_cycles = 0;
always @(negedge clk) begin
    #1;
    if (!reset) begin
        compared_cycles = compared_cycles + 1;
''' + '\n'.join(checks) + '''
    end
end
'''
needle = 'spk286_at_sdram_read_buffer #(.ENABLE(ENABLE), .LINE_COUNT(LINE_COUNT), .SYNC_TAGS(SYNC_TAGS)) dut (.*);'
source = bench.read_text()
assert source.count(needle) == 1
assert source.count('$finish;') == 1
paired = source.replace(needle, needle+'\n'+insertion)
paired = paired.replace('$finish;',
    '$display("CODE_BUFFER_CYCLE_EQUIVALENCE_PASS cycles=%0d", compared_cycles);\n        $finish;')
(output/'paired_tb.sv').write_text(paired)
PY
top=spk286_at_multiline_code_buffer_tb
iverilog -g2012 -Wall -Wno-timescale -DPCAT_PRODUCTION_CODE_BUFFER \
  -s "$top" -P "$top.LINE_COUNT=512" -o "$output/paired" \
  "$rtl" "$output/before-renamed.sv" "$output/paired_tb.sv" \
  > "$output/compile.log" 2>&1
vvp "$output/paired" | tee "$output/paired.log"
sha256sum --check "$output/sources.sha256" > "$output/sources-verified.log"
