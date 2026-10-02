#!/usr/bin/env python3
"""Run an unchanged Python audit with more host time per subprocess.

Only a finite subprocess.run timeout is increased. HDL watchdogs, commands,
expected results, assertions and return-code checks are not changed. This is
for a separately retained replay after a host-timeout failure.
"""
import argparse
import runpy
import subprocess
import sys

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--seconds', type=int, default=600)
    p.add_argument('module')
    p.add_argument('arguments', nargs=argparse.REMAINDER)
    a = p.parse_args()
    assert a.seconds > 0
    original_run = subprocess.run
    def with_budget(*args, **kwargs):
        limit = kwargs.get('timeout')
        if limit is not None and limit < a.seconds:
            print(f'HOST_TIMEOUT_BUDGET original={limit} replay={a.seconds}', flush=True)
            kwargs['timeout'] = a.seconds
        return original_run(*args, **kwargs)
    subprocess.run = with_budget
    sys.argv = [a.module, *a.arguments]
    # Keep the caller's working-directory module resolution (frozen CPU tree).
    sys.path.insert(0, str(__import__('pathlib').Path.cwd()))
    runpy.run_module(a.module, run_name='__main__')

if __name__ == '__main__':
    main()
