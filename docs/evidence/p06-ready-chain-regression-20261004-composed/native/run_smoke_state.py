"""Execute the distinct native driver/state stages on frozen standalone inputs."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import threading
import time

RUN = Path(__file__).resolve().parent
SNAP = RUN/'snapshot'
LOCK = threading.Lock()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest = json.loads((RUN/'manifest.json').read_text())
    for name, value in manifest['source_sha256'].items():
        assert sha(SNAP/name) == value, name
    receipt = dict(status='STANDALONE_NATIVE_SMOKE_STATE_RUNNING',
                   started_utc=datetime.now(timezone.utc).isoformat(),
                   manifest_sha256=sha(RUN/'manifest.json'), source_sha256=manifest['source_sha256'],
                   results={}, scope='Fresh native standalone driver/reset/state-vector and microcode audit stages. State vectors execute no instructions. No corpus, board or complete regression claim.')

    def save():
        (RUN/'smoke-state-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')

    def execute(key,args):
        log=RUN/'logs'/(key+'.log')
        env=os.environ.copy()
        env['SPK286_BUILD_DIR']=str(SNAP/'build/native-driver')
        env['SPK286_BUILD_JOBS']='1'
        started=time.monotonic()
        with log.open('w') as output:
            process=subprocess.Popen(args,cwd=SNAP,env=env,stdout=output,
                                     stderr=subprocess.STDOUT,start_new_session=True)
            try:
                code=process.wait(timeout=1200)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid,signal.SIGTERM)
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid,signal.SIGKILL);process.wait()
                code=None
        text=log.read_text(errors='replace')
        row=dict(status='TIMEOUT' if code is None else 'PASS' if code==0 else 'FAIL',
                 exit_code=code,elapsed_seconds=round(time.monotonic()-started,3),command=args,
                 log=log.relative_to(RUN).as_posix(),log_sha256=sha(log),
                 markers=[line for line in text.splitlines() if 'PASS' in line or 'ERROR' in line or 'FATAL' in line])
        with LOCK:
            receipt['results'][key]=row;save()
        print(key,json.dumps(row),flush=True)
        return code==0

    def native_driver():
        if execute('native-verilator-smoke',['bash','scripts/test_verilator.sh']):
            execute('native-state-default',['python3','-B','-m','tools.state_vectors'])
            execute('native-state-fixture',['python3','-B','-m','tools.state_vectors','--source','tests/fixtures/state_vectors.json'])

    def other_stages():
        execute('native-icarus-reset',['bash','scripts/test_iverilog.sh'])
        execute('native-microcode-audit',['python3','-B','-m','tools.microcode.audit_microcode','--output',str(SNAP/'build/native-microcode-audit')])

    save()
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(native_driver),pool.submit(other_stages)]
        for future in as_completed(futures):future.result()
    for name,value in manifest['source_sha256'].items():
        assert sha(SNAP/name)==value,'Source mutated: '+name
    receipt['sources_unchanged_after_run']=True
    expected={'native-verilator-smoke','native-state-default','native-state-fixture','native-icarus-reset','native-microcode-audit'}
    receipt['status']=('STANDALONE_NATIVE_SMOKE_STATE_PASS'
                       if set(receipt['results'])==expected and all(r['status']=='PASS' for r in receipt['results'].values())
                       else 'STANDALONE_NATIVE_SMOKE_STATE_COMPLETED_WITH_FAILURES')
    receipt['completed_utc']=datetime.now(timezone.utc).isoformat()
    receipt['runner_sha256']=sha(Path(__file__))
    save();print(receipt['status'],flush=True)


if __name__=='__main__':main()
