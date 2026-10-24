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
            command=[sys.executable,'-B',str(TESTS/'scripts/spr_yao_step_review.py'),'--tag',tag,'--reference','spr_yao_grid02_r1']
            record['analysis_command']=command;record['status']='offline_review_running';save()
            try:
                with (TESTS/'logs'/(tag+'.review.log')).open('xb') as stream:
                    check=subprocess.run(command,cwd=CASE,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW,timeout=1800)
                record['analysis_exit_code']=check.returncode
            except Exception as error:record['analysis_error']=repr(error)
    message=(f"User-authorized same-thread Yao CPU multi-plane SPR continuation {tag}, not a new human observation. Detected {event}. "
        f"Read {source}, {watcher}, tests/notes/spr_yao_r1.md, the new review.json/review.log and case02 tests/notes/spr_planes_r1.md. "
        "Formal three-group figures and CSVs were verified current; do not rerun or rewrite accepted case02 data. This stage is three fresh CPU8 fixed-face Yao .1-s off/on/half runs, dt2e-5/1e-5, dp.1, same20301 native soil nodes, HG/NoPen off. "
        "Verify exact owned exits, actual times/IDs/build-input-output hashes, native load/drainage/geometry/elastic/natural-step safety and all101 actual-matched 5Pa/.005mm half pairs. Check all21 same-dt prefixes against spr_yao_grid02_r1 (not shifted original output frames). "
        "Original strict strip has59 loaded interior nodes (5.9m vs ideal6m, -1.667% quadrature); disclose it, do not silently change loading or apply the 1D100Pa uniform-stress gate to nonuniform2D. "
        "Inspect both new history/field PNGs and CSVs, report Chinese quantified findings proactively; .1s startup is not full2D theory/long-cycle acceptance. If analysis alone failed, repair only fresh analysis artifacts; never rerun completed solvers. On runtime failure inspect actual reason/time and surviving owned processes, do not duplicate or relax thresholds. "
        "Continue the authorized CPU multi-plane/NoPen/2D then GPU candidate work in justified gated order without another progress question. CPU three-file candidate currently has18 multi-face manufactured,18 legacy fields,eight2ms pulse half pairs,and final SPRoff/on one-plane31-frame0ULP regressions. Source is frozen under case02 outputs/spr_planes_cpu_short_verified. "
        "Original inclined NoPen is not rotation-consistent even SPRoff; only axis-aligned CPU NoSlip/FreeSlip candidate admitted. GPU unchanged single-plane, no curves/motion/plasticity/large-rotation/exactHG restart acceptance. Preserve all raw evidence; keep tests shallow and XML docs synchronized. "
        "This watcher queues once and runs no physical solver; never restart/rearm it, old workers, or connectivity tests. Use one verified completion mechanism for a genuinely new later long stage.")
    attempt=TESTS/'logs'/(tag+'.queue_attempt.json')
    with attempt.open('x',encoding='utf8') as stream:json.dump(dict(utc=utc(),thread=thread,event=event,message=message),stream,indent=2)
    try:
        q=subprocess.run([codex,'queue','--thread',thread,'--message',message],capture_output=True,timeout=45,creationflags=subprocess.CREATE_NO_WINDOW)
        record.update(status='queued' if q.returncode==0 else 'queue_failed_no_retry',queue_exit_code=q.returncode,reply=(q.stdout+q.stderr).decode(errors='replace'))
    except Exception as error:record.update(status='queue_uncertain_no_retry',queue_error=repr(error))
    record['finished_utc']=utc();save()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--tag',required=True);parser.add_argument('--worker',action='store_true');parser.add_argument('--codex');parser.add_argument('--thread');args=parser.parse_args()
    assert args.tag=='spr_yao_grid10_r1'  # This one-shot is not a generic recurring monitor.
    if args.worker:worker(args.tag,args.codex,args.thread);return
    for suffix in ('.followup.status.json','.followup.launch.json','.queue_attempt.json'):assert not (TESTS/'logs'/(args.tag+suffix)).exists()
    state=json.loads((TESTS/'logs'/(args.tag+'.status.json')).read_text());assert state['status']=='running'
    prior=json.loads((REPO/'examples/Hydromechanic coupling/02_TerzaghiConsolidation_q0_PR/tests/logs/k5_cpu_timing_followup_r1.launch.json').read_text())
    codex=prior['argv'][prior['argv'].index('--codex')+1];thread=os.environ['CODEX_THREAD_ID'];assert thread==prior['thread'] and Path(codex).is_file()
    argv=[sys.executable,'-B',str(Path(__file__).resolve()),'--tag',args.tag,'--worker','--codex',codex,'--thread',thread]
    with (TESTS/'logs'/(args.tag+'.followup.log')).open('xb') as stream:child=subprocess.Popen(argv,cwd=CASE,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
    with (TESTS/'logs'/(args.tag+'.followup.launch.json')).open('x',encoding='utf8') as stream:
        json.dump(dict(pid=child.pid,argv=argv,thread=thread,inputs=[bound(__file__),bound(codex),bound(TESTS/'scripts/spr_yao_step_review.py')],no_connectivity_test=True),stream,indent=2)
    print('One-shot follow-up launched',child.pid,'for',args.tag,'on the current thread')


if __name__=='__main__':main()
