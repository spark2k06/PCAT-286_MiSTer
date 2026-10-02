#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd)
run="$root/build/perf01-write-admission-fit-20261002"
cp "$run/work/PCAT-286.qsf" "$run/qsf-before-export.txt"
cp "$run/work/build_id.v" "$run/build-id-before.v"
date --iso-8601=seconds > "$run/compile-started.txt"
docker image inspect raetro/quartus:mister --format '{{.Id}}' > "$run/quartus-image.txt"
docker run --rm -v "$run/work:/build" -w /build raetro/quartus:mister \
  bash -c 'quartus_sh --flow compile PCAT-286' > "$run/compile.log" 2>&1
date --iso-8601=seconds > "$run/compile-finished.txt"
python3 - "$run" <<'PY'
from pathlib import Path
import hashlib,json,shlex,sys
run=Path(sys.argv[1]); work=run/'work'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest=json.loads((run/'manifest.json').read_text())
changed=[name for name,h in manifest['source_sha256'].items() if sha(work/name)!=h]
assert set(changed)<= {'PCAT-286.qsf','build_id.v'},changed
old=(run/'qsf-before-export.txt').read_text(); new=(work/'PCAT-286.qsf').read_text()
assert new.startswith(old)
assignments=set()
for name in ['PCAT-286.qsf','config.tcl','sys/sys.tcl','sys/sys_analog.tcl','files.qip']:
 source=(run/'qsf-before-export.txt') if name=='PCAT-286.qsf' else work/name
 for line in source.read_text().splitlines():
  if line.startswith('set_'): assignments.add(tuple(shlex.split(line)))
extra=[line for line in new[len(old):].splitlines() if line.startswith('set_')]
assert all(tuple(shlex.split(line)) in assignments for line in extra),extra
build=(work/'build_id.v').read_text()
assert build.strip()=='`define BUILD_DATE "261002"',build
assert (work/'output_files/PCAT-286.rbf').exists()
record={'changed_source_files':changed,'qsf_appended_existing_assignments':len(extra),
        'build_id':build,'source_file_count':len(manifest['source_sha256']),
        'artifacts':{name:sha(work/'output_files'/name) for name in [
         'PCAT-286.fit.rpt','PCAT-286.fit.summary','PCAT-286.sta.rpt',
         'PCAT-286.sta.summary','PCAT-286.rbf']}}
(run/'post-source-verification.json').write_text(json.dumps(record,indent=2)+'\n')
print('WRITE_ADMISSION_FIT_INPUTS_VERIFIED',json.dumps(record))
PY
