#!/usr/bin/env python3
"""Observe an owned measurement's output without stopping or writing the guest.

Stable RAM matches are diagnostic evidence, not proof of successful DOS exit.
The expected formatter buffer is specific to the frozen CHECKNUM DOS fixture.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--arm', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    arm = args.arm.resolve()
    start = json.loads((arm/'measurement-start.json').read_text())
    exe = Path(start['command'][0]).resolve()
    pid = int((arm/'pid').read_text())
    assert pid == start['pid']
    assert Path(f'/proc/{pid}/exe').resolve() == exe
    digest = hashlib.sha256(exe.read_bytes()).hexdigest()
    assert digest == start['binary_sha256'], 'Measurement binary changed'
    profile = json.loads((arm/'memory-profile.json').read_text())
    assert start['image_sha256_before'] == '7a50d61047b47a4913474a29e90bc35ebd3a666824509c9deffd8904ef740b74'
    assert profile['main_cs'] == 1747, 'Formatter address belongs to this frozen DOS load'
    listing = subprocess.check_output(['nm', '-S', '-C', str(exe)], text=True)
    symbol = int(next(line.split()[0] for line in listing.splitlines()
                      if line.endswith(' ram')), 16)
    maps = Path(f'/proc/{pid}/maps').read_text().splitlines()
    base = int(next(line.split('-')[0] for line in maps
                    if line.endswith(str(exe)) and line.split()[2] == '00000000'), 16)
    fd = os.open(f'/proc/{pid}/mem', os.O_RDONLY)
    try:
        ram = int.from_bytes(os.pread(fd, 8, base + symbol), 'little')
        first = os.pread(fd, 1024 * 1024, ram)
        time.sleep(.2)
        second = os.pread(fd, len(first), ram)
    finally:
        os.close(fd)
    matches = []
    for match in re.finditer(rb'(?:[0-9]{4,5}|[0-9]{2,3}\.[0-9])\r\n', second):
        low, high = match.span()
        if first[low:high] == second[low:high]:
            matches.append({'guest_address': hex(low),
                            'ascii': second[low:high].decode('ascii'),
                            'context_hex': second[max(0, low-16):high+16].hex()})
    # This address was established from the formatter buffer in the unchanged
    # DOS image. Also require the profiler to have left the integer benchmark.
    formatted = next((m for m in matches if m['guest_address'] == '0x4cb38'), None)
    after_integer = profile['phase'] in ('integer_format', 'whetstone', 'math_format', 'done')
    value = int(formatted['ascii'].strip()) if formatted and after_integer and '.' not in formatted['ascii'] else None
    math_value = float(formatted['ascii'].strip()) if formatted and profile['phase'] == 'math_format' and '.' in formatted['ascii'] else None
    result = {'pid': pid, 'binary_sha256': digest, 'phase': profile['phase'],
              'profile_clocks': profile['clocks'], 'dhrystone_partial': value,
              'kwhetstone_partial': math_value,
              'stable_integer_matches': matches, 'diagnostic_only': True,
              'method': 'Two read-only RAM reads; no stop, monitor command or guest write'}
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
