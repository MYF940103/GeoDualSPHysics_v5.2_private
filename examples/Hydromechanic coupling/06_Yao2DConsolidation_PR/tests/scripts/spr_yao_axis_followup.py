"""One-shot terminal follow-up for axis-NoPen .1 s, never runs a solver."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from spr_yao_short import TESTS,CASE,bound
from spr_yao_axis_run import TAG
from spr_yao_followup import alive,utc


def worker(codex,thread):
    source=TESTS/'logs'/(TAG+'.status.json');watcher=TESTS/'logs'/(TAG+'.followup.status.json');assert not watcher.exists()
    r=dict(status='waiting',pid=os.getpid(),thread=thread,started_utc=utc(),watched=str(source),never_runs_solver=True)
    def save():
        tmp=watcher.with_suffix('.tmp');tmp.write_text(json.dumps(r,indent=2),encoding='utf8');os.replace(tmp,watcher)
    save();misses=0
    while True:
        try:
            state=json.loads(source.read_text());misses=0
            if state['status']!='running':event=state['status'];break
            if not alive(state['owned_sequence_pid']):
                time.sleep(2);state=json.loads(source.read_text())
                if state['status']=='running' and not alive(state['owned_sequence_pid']):event='sequence_exited_without_terminal_record';break
        except Exception as error:
            misses+=1
            if misses>=5:event='status_unreadable';r['read_error']=repr(error);break
        time.sleep(10)
    r.update(status='terminal_observed',event=event,observed_utc=utc());save()
    message=(f'User-authorized same-thread Yao axis-NoPen continuation {TAG}, not a new human observation. Detected {event}. '
        f'Read {source}, {watcher}, its queue_attempt.json, tests/notes/spr_yao_axis_r1.md and tests/notes/spr_yao_1s_r1.md before claims. '
        'Only three fresh .1-s CPU8/GPU coarse20us/GPU half10us runs were admitted; dp.1, 20301 soil IDs, existing axis-aligned NoPen plus SPR, HG off, original nodal loading/material/drainage. '
        'Inspect frozen run/build/input/output hashes, exact owned exits/actual times/IDs, all101-sample native safety and original5Pa/.005mm cross and independent GPU half gates; same-dt force difference<.002N/m. '
        'Every single/cross gate must pass before the later run. Original 59/61 load quadrature remains unchanged; do not apply 1D100Pa uniform-stress guard or silently change load. '
        'Compare NoPen-on versus retained NoPen-off 1-s same-dt first101 frames: pressure/material settlement/stress/near-wall changes and observed timing; these changes are not theory errors. Inspect history PNG/CSV and generate justified fresh fields. '
        'If runtime/check failed, inspect exact cause/time and surviving owned processes, preserve evidence and repair within scope without duplicate solvers, overwritten outputs or relaxed bounds. If analysis alone failed repair new analysis only. '
        'On pass proactively report quantified Chinese bounded result and continue justified 2D/axis-NoPen delivery, dependency-aware cleanup and verified selective Git without waiting for another progress query. .1-s is not1-s/full2D theory/long-cycle admission. '
        'No production/formal source changes in this stage. Checkpoint7fda9ffe holds the static convex planar candidate; original inclined NoPen remains rotation-inconsistent and explicitly rejected. Curves/motion/plasticity/large rotation/exactHG restart remain unaccepted. '
        'Case02 three accepted groups/figures/CSVs stand; never rerun/rewrite or reopenKEEP. Previous1-s CPU/GPU sequence was reviewed and passed1001 pairs; do not restart it. '
        'This one-shot queues once and runs no solver. Never restart/rearm it, any old watcher, or connectivity self-tests. Use one verified completion only for a genuinely new later long stage.')
    with (TESTS/'logs'/(TAG+'.queue_attempt.json')).open('x',encoding='utf8') as f:json.dump(dict(utc=utc(),thread=thread,event=event,message=message),f,indent=2)
    try:
        p=subprocess.run([codex,'queue','--thread',thread,'--message',message],capture_output=True,timeout=45,creationflags=subprocess.CREATE_NO_WINDOW)
        r.update(status='queued' if p.returncode==0 else 'queue_failed_no_retry',queue_exit_code=p.returncode,reply=(p.stdout+p.stderr).decode(errors='replace'))
    except Exception as error:r.update(status='queue_uncertain_no_retry',error=repr(error))
    r['finished_utc']=utc();save()


def main():
    p=argparse.ArgumentParser();p.add_argument('--worker',action='store_true');p.add_argument('--codex');p.add_argument('--thread');a=p.parse_args()
    if a.worker:worker(a.codex,a.thread);return
    for suffix in ('.followup.launch.json','.followup.status.json','.queue_attempt.json'):assert not (TESTS/'logs'/(TAG+suffix)).exists()
    state=json.loads((TESTS/'logs'/(TAG+'.status.json')).read_text());assert state['status']=='running' and alive(state['owned_sequence_pid'])
    codex=Path(r'C:\Users\syosh\.vscode\extensions\openai.chatgpt-26.1007.21434-win32-x64\bin\windows-x86_64\codex.exe')
    thread=os.environ['CODEX_THREAD_ID'];assert thread==os.environ['CODEX_SESSION_ID']=='01a07683-bc64-7463-8db7-9ee6243967d8' and codex.is_file()
    argv=[sys.executable,'-B',str(Path(__file__).resolve()),'--worker','--codex',str(codex),'--thread',thread]
    with (TESTS/'logs'/(TAG+'.followup.log')).open('xb') as f:child=subprocess.Popen(argv,cwd=CASE,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
    with (TESTS/'logs'/(TAG+'.followup.launch.json')).open('x',encoding='utf8') as f:json.dump(dict(pid=child.pid,argv=argv,thread=thread,inputs=[bound(__file__),bound(codex),bound(TESTS/'scripts/spr_yao_followup.py')],no_connectivity_test=True),f,indent=2)
    print('One new axis-NoPen terminal follow-up launched:',child.pid)


if __name__=='__main__':main()
