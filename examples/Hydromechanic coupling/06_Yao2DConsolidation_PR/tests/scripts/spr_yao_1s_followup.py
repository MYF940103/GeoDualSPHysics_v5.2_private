"""One-shot same-thread follow-up for the new 1-s sequence, never a solver."""
from pathlib import Path
import argparse
import json
import os
import subprocess
import sys
import time
from spr_yao_short import TESTS,CASE,REPO,bound
from spr_yao_followup import alive,utc

TAG='spr_yao_cpu_gpu_1s_r1'


def worker(codex,thread):
    source=TESTS/'logs'/(TAG+'.status.json');watcher=TESTS/'logs'/(TAG+'.followup.status.json');assert not watcher.exists()
    r=dict(status='waiting',pid=os.getpid(),thread=thread,started_utc=utc(),watched=str(source),never_runs_solver=True)
    def save():
        temporary=watcher.with_suffix('.tmp');temporary.write_text(json.dumps(r,indent=2),encoding='utf8');os.replace(temporary,watcher)
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
    message=(f"User-authorized same-thread Yao 1-s CPU/GPU continuation {TAG}, not a new human observation. Detected {event}. "
        f"Read {source}, {watcher}, its queue_attempt.json, tests/notes/spr_yao_1s_r1.md and tests/notes/spr_yao_r1.md. "
        "Three fresh runs only: CPU8 SPR-on coarse20us, GPU SPR-on coarse20us then half10us, dp.1, same20301 soil IDs, original strip load, HG/NoPen off, 1ms native saves. "
        "Each full1001-sample native gate must pass before the next run; CPU/GPU cross comparison must pass before GPU half is launched. Inspect frozen per-run run.json and all cpu_c/gpu_c/gpu_h/cross/half/final checks/logs. "
        "Verify exact owned exits/actual times/build-input-output hashes/native IDs, geometry/load/drainage/elastic/natural-step safety, CPU101 same-dt .1-s prefix and GPU301 same-dt .3-s prefixes0ULP. "
        "Keep original all1001-sample5Pa/.005mm cross and independent GPU half bounds; same-dt CPU/GPU native load difference must stay below .002N/m. Do not confuse ramp half-step load timing with a same-dt backend error. "
        "If passed, inspect history PNG/CSV, generate justified native field plots and proactively report Chinese quantified pressure/material settlement/total stress/near-wall/load changes and observed loop timings; not full2D theory or controlled benchmark acceptance. "
        "The original strict strip has59/61-node quadrature (-1.667/+1.667percent); preserve/disclose it, no silent loading change or1D100Pa uniform-stress gate. "
        "If runtime/check interrupted, inspect exact cause/time and surviving owned processes, preserve all partial evidence and do not duplicate or restart old solvers/watchers. If only analysis failed repair fresh analysis, never rerun completed solvers or relax gates. "
        "Production candidate is backed up locally AND remote u-pw at7fda9ffe8c3ee657fe7d5279f9f35565f199719c, eight source files; scope is static convex planar SPR with bounded operator/pulse/Yao checks, not full physical release. "
        "Formal case02 three groups and plots/CSVs stand; do not rerun/rewrite or reopenKEEP. Inclined NoPen/curves/motion/plasticity/large rotation/exactHG restart remain unaccepted. "
        "Continue authorized justified 2D/axis-NoPen delivery, dependency-aware cleanup and later selective Git without waiting for a progress question. This one-shot queues once, runs no solver, never rearm/restart it or send connectivity tests. Use one verified completion only for a genuinely new later long stage.")
    attempt=TESTS/'logs'/(TAG+'.queue_attempt.json')
    with attempt.open('x',encoding='utf8') as stream:json.dump(dict(utc=utc(),thread=thread,event=event,message=message),stream,indent=2)
    try:
        result=subprocess.run([codex,'queue','--thread',thread,'--message',message],capture_output=True,timeout=45,creationflags=subprocess.CREATE_NO_WINDOW)
        r.update(status='queued' if result.returncode==0 else 'queue_failed_no_retry',queue_exit_code=result.returncode,reply=(result.stdout+result.stderr).decode(errors='replace'))
    except Exception as error:r.update(status='queue_uncertain_no_retry',queue_error=repr(error))
    r['finished_utc']=utc();save()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--worker',action='store_true');parser.add_argument('--codex');parser.add_argument('--thread');args=parser.parse_args()
    if args.worker:worker(args.codex,args.thread);return
    for suffix in ('.followup.launch.json','.followup.status.json','.queue_attempt.json'):assert not (TESTS/'logs'/(TAG+suffix)).exists()
    state=json.loads((TESTS/'logs'/(TAG+'.status.json')).read_text());assert state['status']=='running' and alive(state['owned_sequence_pid'])
    prior=json.loads((REPO/'examples/Hydromechanic coupling/02_TerzaghiConsolidation_q0_PR/tests/logs/k5_cpu_timing_followup_r1.launch.json').read_text())
    codex=prior['argv'][prior['argv'].index('--codex')+1];thread=os.environ['CODEX_THREAD_ID'];assert thread==prior['thread'] and Path(codex).is_file()
    argv=[sys.executable,'-B',str(Path(__file__).resolve()),'--worker','--codex',codex,'--thread',thread]
    with (TESTS/'logs'/(TAG+'.followup.log')).open('xb') as stream:child=subprocess.Popen(argv,cwd=CASE,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
    with (TESTS/'logs'/(TAG+'.followup.launch.json')).open('x',encoding='utf8') as stream:json.dump(dict(pid=child.pid,argv=argv,thread=thread,
        inputs=[bound(__file__),bound(codex),bound(TESTS/'scripts/spr_yao_followup.py')],no_connectivity_test=True),stream,indent=2)
    print('One-shot 1-s follow-up launched',child.pid,'on the verified current thread')


if __name__=='__main__':main()
