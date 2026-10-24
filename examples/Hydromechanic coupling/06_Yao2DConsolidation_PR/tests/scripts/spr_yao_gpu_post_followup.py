"""One-shot offline review/queue for this new stage; never runs physical solvers."""
from pathlib import Path
from datetime import datetime,timezone
import argparse
import ctypes
import hashlib
import json
import os
import subprocess
import sys
import time
from spr_yao_short import TESTS,CASE,REPO,bound


def utc():return datetime.now(timezone.utc).isoformat()


def alive(pid):
    kernel=ctypes.windll.kernel32;kernel.OpenProcess.restype=ctypes.c_void_p
    handle=kernel.OpenProcess(0x1000,False,int(pid))
    if not handle:return False
    try:
        code=ctypes.c_ulong();return bool(kernel.GetExitCodeProcess(ctypes.c_void_p(handle),ctypes.byref(code))) and code.value==259
    finally:kernel.CloseHandle(ctypes.c_void_p(handle))


def worker(tag,codex,thread):
    watcher=TESTS/'logs'/(tag+'.followup.status.json');assert not watcher.exists()
    source=TESTS/'logs'/(tag+'.status.json');record=dict(status='waiting',pid=os.getpid(),thread=thread,started_utc=utc(),watched=str(source),never_runs_solver=True)
    def save():
        tmp=watcher.with_suffix('.tmp');tmp.write_text(json.dumps(record,indent=2),encoding='utf8');os.replace(tmp,watcher)
    save();misses=0
    while True:
        try:
            state=json.loads(source.read_text());misses=0
            if state['status']!='running':event=state['status'];break
            if not alive(state['owned_wrapper_pid']):
                time.sleep(2);state=json.loads(source.read_text())
                if state['status']=='running' and not alive(state['owned_wrapper_pid']):event='owned_wrapper_exited_without_terminal_record';break
        except Exception as error:
            misses+=1
            if misses>=5:event='status_unreadable';record['read_error']=repr(error);break
        time.sleep(10)
    record.update(status='terminal_observed',event=event,observed_utc=utc());save()
    if event=='completed_pending_review':
        receipt=TESTS/'logs'/(tag+'.review.json')
        if receipt.exists():record['analysis']='receipt_already_present_not_overwritten'
        else:
            command=[sys.executable,'-B',str(TESTS/'scripts/spr_yao_gpu_post_review.py'),'--tag',tag]
            record['analysis_command']=command;record['status']='offline_review_running';save()
            try:
                with (TESTS/'logs'/(tag+'.review.log')).open('xb') as stream:
                    check=subprocess.run(command,cwd=CASE,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW,timeout=1800)
                record['analysis_exit_code']=check.returncode
            except Exception as error:record['analysis_error']=repr(error)
    message=(f"User-authorized same-thread Yao GPU post-ramp continuation {tag}, not a new human observation. Detected {event}. "
        f"Read {source}, {watcher}, its queue_attempt.json and review.json/review.log, case06 tests/notes/spr_yao_r1.md and case02 tests/notes/spr_gpu_planes_r1.md. "
        "This is a genuinely new fresh .3-s off/on/half GPU window, not a restart of the old CPU .1-s watcher. Three runs use dt20/10us, dp.1, same20301 soil IDs, HG/NoPen off and original strict nodal strip load. "
        "Verify exact owned exits, actual times/native IDs, build-input-output hashes, geometry/load/drainage/elastic/natural-step safety, all301 original5Pa/.005mm half pairs and all101 same-dt .1-s prefixes0ULP. "
        "CPU controls exist ONLY through .1s; never claim .3-s CPU comparison from a prefix. Current .1-s GPU half passed .277974Pa/.000287018mm and cross-backend maxima .00132398Pa/2.84413e-6mm. "
        "GPU source also has an output-only actual-load diagnostic repair: prior .02-s physical fields except load_az remain0ULP; old single-plane SPR/HG four paths31frames all fields0ULP. "
        "The existing 59/61-node strict strip has -1.667/+1.667percent quadrature bias; quantify it without silently changing load physics or applying the1D100Pa stress gate to nonuniform2D. "
        "Inspect history PNG/CSV, generate justified fresh field plots, report quantified Chinese pressure/material settlement/total stress/near-wall changes. Short agreement is not full2D theory or long-cycle acceptance. "
        "If only analysis failed, repair new analysis without rerunning completed solvers. On runtime failure inspect surviving owned processes and exact reason/time, preserve outputs, no duplicate solver, guard relaxation or old-worker restart. "
        "Continue authorized multi-plane/axis-NoPen/2D delivery in justified gated order without another progress prompt. CPU/GPU static convex planar candidate is locally frozen at case02 outputs/spr_planes_cpu_gpu_short_verified, not a new cloud Git backup. "
        "GPU18 multi-face+36 legacy manufactured, eight2ms pulse half pairs and current Debug3D edge memcheck passed. Inclined NoPen remains rejected due original rotation inconsistency; curves/motion/plasticity/large rotation/exactHG restart not accepted. "
        "Formal case02 three-group figures/CSVs and data stand; never rerun/rewrite them or reopenKEEP. Source is currently uncommitted; verified selective Git and dependency-aware cleanup remain later tasks. "
        "This watcher queues once and runs no solver. Never restart/rearm it, any old watcher or connectivity self-test. Use one verified same-thread mechanism only for a genuinely new later long stage.")
    attempt=TESTS/'logs'/(tag+'.queue_attempt.json')
    with attempt.open('x',encoding='utf8') as stream:json.dump(dict(utc=utc(),thread=thread,event=event,message=message),stream,indent=2)
    try:
        q=subprocess.run([codex,'queue','--thread',thread,'--message',message],capture_output=True,timeout=45,creationflags=subprocess.CREATE_NO_WINDOW)
        record.update(status='queued' if q.returncode==0 else 'queue_failed_no_retry',queue_exit_code=q.returncode,reply=(q.stdout+q.stderr).decode(errors='replace'))
    except Exception as error:record.update(status='queue_uncertain_no_retry',queue_error=repr(error))
    record['finished_utc']=utc();save()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--tag',required=True);parser.add_argument('--worker',action='store_true');parser.add_argument('--codex');parser.add_argument('--thread');args=parser.parse_args()
    assert args.tag=='spr_yao_gpu_post03_r1'  # This one-shot is not a generic recurring monitor.
    if args.worker:worker(args.tag,args.codex,args.thread);return
    for suffix in ('.followup.status.json','.followup.launch.json','.queue_attempt.json'):assert not (TESTS/'logs'/(args.tag+suffix)).exists()
    state=json.loads((TESTS/'logs'/(args.tag+'.status.json')).read_text());assert state['status']=='running'
    prior=json.loads((REPO/'examples/Hydromechanic coupling/02_TerzaghiConsolidation_q0_PR/tests/logs/k5_cpu_timing_followup_r1.launch.json').read_text())
    codex=prior['argv'][prior['argv'].index('--codex')+1];thread=os.environ['CODEX_THREAD_ID'];assert thread==prior['thread'] and Path(codex).is_file()
    argv=[sys.executable,'-B',str(Path(__file__).resolve()),'--tag',args.tag,'--worker','--codex',codex,'--thread',thread]
    with (TESTS/'logs'/(args.tag+'.followup.log')).open('xb') as stream:child=subprocess.Popen(argv,cwd=CASE,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
    with (TESTS/'logs'/(args.tag+'.followup.launch.json')).open('x',encoding='utf8') as stream:
        json.dump(dict(pid=child.pid,argv=argv,thread=thread,inputs=[bound(__file__),bound(codex),bound(TESTS/'scripts/spr_yao_gpu_post_review.py')],no_connectivity_test=True),stream,indent=2)
    print('One-shot follow-up launched',child.pid,'for',args.tag,'on the current thread')


if __name__=='__main__':main()


