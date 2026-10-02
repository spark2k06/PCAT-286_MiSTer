#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd)
run="$root/build/perf01-entry-overlap-userfit-review-20261002"
[[ -f "$run/manifest.json" && ! -e "$run/path-extraction-started.txt" ]]
date --iso-8601=seconds > "$run/path-extraction-started.txt"
docker image inspect raetro/quartus:mister --format '{{.Id}}' > "$run/quartus-image.txt"
docker run --rm -v "$run/work:/build" \
  -v "$root/build/perf01-entry-overlap-20261002:/analysis:ro" -w /build \
  raetro/quartus:mister bash -c \
  'quartus_sta -t /analysis/report_user_fit_paths.tcl PCAT-286 /build/review-paths' \
  > "$run/path-extraction.log" 2>&1
date --iso-8601=seconds > "$run/path-extraction-finished.txt"
python3 - "$run" <<'PY'
from pathlib import Path
import hashlib,json,sys
run=Path(sys.argv[1]);work=run/'work'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest=json.loads((run/'manifest.json').read_text())
for group in ('source_sha256','fit_sha256'):
 assert all(sha(work/n)==h for n,h in manifest[group].items()),group
record={'fitted_artifacts_unchanged':True,'source_files_unchanged':True,
        'source_files':len(manifest['source_sha256']),
        'fitted_artifacts':len(manifest['fit_sha256']),
        'scope':'Bounded timing extraction only; no synthesis, fitting, RTL or SDC change.',
        'reports_sha256':{str(p.relative_to(work/'review-paths')):sha(p)
                          for p in sorted((work/'review-paths').rglob('*')) if p.is_file()}}
(run/'path-verification.json').write_text(json.dumps(record,indent=2)+'\n')
print('P17_USER_FIT_SOURCE_ARTIFACTS_VERIFIED',len(record['reports_sha256']))
PY
