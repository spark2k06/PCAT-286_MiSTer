"""Read stable diagnostic output bytes without stopping or writing the guest."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time

root = Path(__file__).resolve().parent
arm = root / 'pcat-write-admission/spk50'
exe = (root / 'probe/86Box-memory-probe').resolve()
pid = int((arm / 'pid').read_text())
assert Path(f'/proc/{pid}/exe').resolve() == exe
listing = subprocess.check_output(['nm', '-S', '-C', str(exe)], text=True)
symbol = int(next(line.split()[0] for line in listing.splitlines()
                  if line.endswith(' ram')), 16)
maps = Path(f'/proc/{pid}/maps').read_text().splitlines()
base = int(next(line.split('-')[0] for line in maps
                if line.endswith(str(exe)) and line.split()[2] == '00000000'), 16)
fd = os.open(f'/proc/{pid}/mem', os.O_RDONLY)
try:
    ram = int.from_bytes(os.pread(fd, 8, base + symbol), 'little')
    a = os.pread(fd, 1024 * 1024, ram)
    time.sleep(.2)
    b = os.pread(fd, len(a), ram)
finally:
    os.close(fd)
hits = []
for pattern in (rb'TICKS_BEGIN=[0-9]+[\r\n ]+[0-9]+(?:\.[0-9]+)?',
                rb'[0-9]{4,5}\r\n', rb'TICKS_BEGIN=', rb'%\.0f\r\n'):
    for match in re.finditer(pattern, b):
        start, end = match.span()
        if a[start:end] == b[start:end]:
            hits.append({'guest_address':hex(start),
                         'ascii':b[start:end].decode('ascii'),
                         'context':repr(b[max(0,start-30):min(len(b),end+50)])})
result = {'pid':pid, 'ram_pointer':hex(ram), 'ram_nonzero_bytes':sum(x != 0 for x in b),
          'stack_region':repr(b[0x4ca00:0x4cb00]),
          'method':'Two read-only guest-RAM reads; no stop, monitor command or guest write',
          'diagnostic_only':True, 'hits':hits,
          'binary_sha256':hashlib.sha256(exe.read_bytes()).hexdigest()}
(root / 'partial-guest-output.json').write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps(result, indent=2))
