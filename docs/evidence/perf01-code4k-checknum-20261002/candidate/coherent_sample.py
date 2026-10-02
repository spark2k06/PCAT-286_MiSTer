"""Read one coherent snapshot of the launcher-owned emulator process."""
import os
from pathlib import Path
import signal
import time


class SampleUnavailable(RuntimeError):
    """Transient stop timeout; no incoherent sample may be accepted."""


def capture_owned(proc, exe, symbols, expected_hz, is_spk, layout, spk_symbols):
    os.kill(proc.pid, signal.SIGSTOP)
    try:
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            states = [p.read_text().split('State:', 1)[1].splitlines()[0].strip()
                      for p in Path(f'/proc/{proc.pid}/task').glob('*/status')]
            if states and all(s.startswith('T') for s in states):
                break
            time.sleep(.005)
        else:
            raise SampleUnavailable('Owned emulator threads did not all stop in 5s')
        maps = Path(f'/proc/{proc.pid}/maps').read_text().splitlines()
        base = int(next(l.split('-')[0] for l in maps
                        if l.endswith(str(exe)) and l.split()[2] == '00000000'), 16)
        fd = os.open(f'/proc/{proc.pid}/mem', os.O_RDONLY)
        try:
            def integer(address, size):
                data = os.pread(fd, size, address)
                assert len(data) == size
                return int.from_bytes(data, 'little')
            cpu = integer(base + symbols['cpu_s'], 8)
            ram = integer(base + symbols['ram'], 8)
            state = {
                'cpu_hz_actual': integer(cpu + 24, 4),
                'isa_hz': integer(base + symbols['cpu_isa_speed'], 4),
                'isa_cycle_divisor': integer(base + symbols['isa_cycles'], 4),
                'tsc': integer(base + symbols['tsc'], 8),
                'bios_ticks': integer(ram + 0x46c, 4),
                'cpu_exec_actual': integer(base + symbols['cpu_exec'], 8) - base,
            }
            assert state['cpu_hz_actual'] == expected_hz, state
            dispatcher = 'exec_spk286' if is_spk else 'exec386_2386'
            assert state['cpu_exec_actual'] == symbols[dispatcher], state
            assert state['isa_hz'] == 8000000, state
            if is_spk:
                top = base + spk_symbols['(anonymous namespace)::top']
                ports = {'debug_cs': 2, 'debug_instruction_ip': 2,
                         'debug_timing_cycle_count': 8, 'halted': 1,
                         'shutdown': 1, 'control_error': 1,
                         'microcode_fault': 1, 'unsupported_opcode': 1}
                for name, size in ports.items():
                    ptr = integer(top + layout[name], 8)
                    state[name] = integer(ptr, size)
            return state
        finally:
            os.close(fd)
    finally:
        os.kill(proc.pid, signal.SIGCONT)
