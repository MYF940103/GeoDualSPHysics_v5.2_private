"""One fresh, gated 3-D boundary sequence and one terminal same-thread queue."""
import argparse
import ctypes
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from spr_planes_run import TESTS,REPO,bound

TAG='spr_3d_next_r1'
STATE=TESTS/'logs'/(TAG+'.status.json')
THREAD='01a07683-bc64-7463-8db7-9ee6243967d8'
CODEX=Path(r'C:\Users\syosh\.vscode\extensions\openai.chatgpt-26.1007.21434-win32-x64\bin\windows-x86_64\codex.exe')


def utc():return datetime.now(timezone.utc).isoformat()


def save(path,value):
    temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(value,indent=2),encoding='utf8');temporary.replace(path)


def alive(pid):
    kernel=ctypes.windll.kernel32;kernel.OpenProcess.restype=ctypes.c_void_p
    kernel.GetExitCodeProcess.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.c_ulong)];kernel.CloseHandle.argtypes=[ctypes.c_void_p]
    handle=kernel.OpenProcess(0x1000,False,pid)
    if not handle:return False
    code=ctypes.c_ulong();ok=kernel.GetExitCodeProcess(handle,ctypes.byref(code));kernel.CloseHandle(handle)
    return bool(ok and code.value==259)


def worker():
    assert not STATE.exists()
    admission=TESTS/'logs/spr_3d_admission_r1.json';assert json.loads(admission.read_text())['passed']
    inputs=[bound(__file__),bound(admission),bound(REPO/'src/source/JSphGpu.cpp')]
    for name in ['spr_3d_run.py','spr_3d_review.py','spr_3d_test.cpp']:inputs.append(bound(TESTS/'support'/name))
    r=dict(status='running',owned_sequence_pid=os.getpid(),started_utc=utc(),stage='admitted',inputs=inputs,stages=[],physical_acceptance=False)
    save(STATE,r)
    try:
        # Only the genuinely unrun pairs; completed edge3 FreeSlip stays untouched.
        for geometry,slip in [('corner3',3),('edge3',2),('corner3',2)]:
            for backend in ['cpu','gpu']:
                name=f'spr_3d_r1_{geometry}_s{slip}_{backend}'
                command=[sys.executable,'-B','-u',str(TESTS/'support/spr_3d_run.py'),'--backend',backend,'--geometry',geometry,'--slip',str(slip)]
                log=TESTS/'logs'/(name+'.sequence.log');assert not log.exists()
                r.update(stage=name,active_log=str(log));save(STATE,r)
                with log.open('xb') as stream:
                    child=subprocess.Popen(command,cwd=TESTS.parent,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
                    r['owned_wrapper_pid']=child.pid;save(STATE,r);code=child.wait()
                status=TESTS/'logs'/(name+'.status.json');result=json.loads(status.read_text())
                assert code==0 and result['passed'] and all(x['owned_exited'] for x in result['runs']),(name,code,result.get('error'))
                r['stages'].append(dict(name=name,exit_code=code,owned_exited=True,status=bound(status),log=bound(log)));save(STATE,r)
            command=[sys.executable,'-B','-u',str(TESTS/'support/spr_3d_review.py'),'--geometry',geometry,'--slip',str(slip)]
            log=TESTS/'logs'/f'spr_3d_r1_{geometry}_s{slip}.review.log'
            with log.open('xb') as stream:subprocess.run(command,cwd=TESTS.parent,stdout=stream,stderr=subprocess.STDOUT,check=True,creationflags=subprocess.CREATE_NO_WINDOW)
            review=TESTS/'logs'/f'spr_3d_r1_{geometry}_s{slip}.review.json';assert json.loads(review.read_text())['passed']
            r['stages'].append(dict(name=geometry+'_s'+str(slip)+'_cross',review=bound(review),log=bound(log)));save(STATE,r)
        for item in inputs:assert bound(item['path'])['sha256']==item['sha256'],'Sequence input changed'
        r.update(status='completed_pending_visual_review',stage='all_remaining_native_half_cross_gates_passed')
    except BaseException as error:r.update(status='rejected_or_interrupted',error=repr(error));raise
    finally:r['finished_utc']=utc();save(STATE,r)


def watch(thread):
    path=TESTS/'logs'/(TAG+'.followup.status.json');assert not path.exists()
    r=dict(status='waiting',pid=os.getpid(),thread=thread,never_runs_solver=True,started_utc=utc());save(path,r);misses=0
    while True:
        try:
            s=json.loads(STATE.read_text());misses=0
            if s['status']!='running':event=s['status'];break
            if not alive(s['owned_sequence_pid']):event='sequence_exited_without_terminal_record';break
        except Exception as error:
            misses+=1
            if misses>=5:event='status_unreadable';r['read_error']=repr(error);break
        time.sleep(10)
    message=(f'User-authorized same-thread 3D fixed-boundary continuation {TAG}, not a new human observation. Detected {event}. '
        f'Read {STATE}, {path}, tests/notes/spr_3d_r1.md, spr_3d_cleanup_r1.md and logs/spr_3d_admission_r1.json before claims. '
        'The new sequence runs ONLY previously unrun corner3 FreeSlip, edge3 NoSlip and corner3 NoSlip: CPU/GPU coarse1us/half0.5us, 2ms, 201 native samples each. Existing edge3 FreeSlip is retained, never rerun. '
        'Verify exact owned exits/actual times/native IDs/build-input-output hashes, all saved geometry/elastic/natural-step/energy<=1.1 guards, every independent half and same-dt CPU/GPU0.5Pa/1e-5mm bound. '
        'HG/NoPen/damping/drainage/loading off; original float u-pw and double stress unchanged. Initial velocities are anisotropic nonzero XYZ; NoSlip has a startup tangential transient, not an exact affine truth. '
        'Inspect all generated half/history/native-slice PNGs and matching CSVs, quantify pressure/displacement/stress/energy and all wall/corner limitations. Normal completion and short agreement are not full3D theory or general-boundary acceptance. '
        'GPU Debug observer and actual program exposed a pre-existing gauge-buffer cudaFree after cudaDeviceReset at exit. Minimal JSphGpu.cpp destructor patch deletes GaugeSystem before context reset; both new memchecks0errors and before/after saved native fields0ULP are in spr_3d_cleanup_r1.check.json. Old failure logs/source/program and old runner are archived in spr_3d_precleanup_r1; do not rewrite historical hashes. '
        'If analysis alone failed repair fresh analysis without rerunning completed solvers. On runtime/check failure inspect actual cause/time/surviving owned processes, preserve evidence and diagnose without duplicate solver, raised damping or relaxed guards. '
        'Proactively report in Chinese and continue justified original delivery: consolidate bounded boundary evidence, docs/cleanup/selective Git, then choose formal2D/3D readiness. Yao10s and case02 accepted three groups/figures/CSVs stand, do not rerun them just for labels. Selborne3D still lacks multi-material/local pressure boundary implementation; never bypass its disabled BAT. InclinedNoPen/curves/moving walls/plastic/large rotation/exactHG restart remain unaccepted; do not reopen KEEP/u-pl/TPI. '
        'This one-shot queues once and runs no solver. Never restart/rearm it or any old worker, and no connectivity self-test. Continue without a progress prompt; use one verified mechanism only for a genuinely new admitted later long stage.')
    attempt=TESTS/'logs'/(TAG+'.queue_attempt.json')
    with attempt.open('x',encoding='utf8') as f:json.dump(dict(event=event,thread=thread,message=message,utc=utc()),f,indent=2)
    try:
        result=subprocess.run([str(CODEX),'queue','--thread',thread,'--message',message],capture_output=True,timeout=45,creationflags=subprocess.CREATE_NO_WINDOW)
        r.update(status='queued' if result.returncode==0 else 'queue_failed_no_retry',queue_exit_code=result.returncode,reply=(result.stdout+result.stderr).decode(errors='replace'))
    except Exception as error:r.update(status='queue_uncertain_no_retry',error=repr(error))
    r.update(event=event,finished_utc=utc());save(path,r)


def main():
    p=argparse.ArgumentParser();p.add_argument('--worker',action='store_true');p.add_argument('--watch',action='store_true');p.add_argument('--thread');a=p.parse_args()
    if a.worker:worker();return
    if a.watch:watch(a.thread);return
    assert os.environ['CODEX_THREAD_ID']==os.environ['CODEX_SESSION_ID']==THREAD and CODEX.is_file()
    launch=TESTS/'logs'/(TAG+'.launch.json');assert not launch.exists() and not STATE.exists()
    logfile=TESTS/'logs'/(TAG+'.sequence.log')
    with logfile.open('xb') as stream:child=subprocess.Popen([sys.executable,'-B',str(Path(__file__).resolve()),'--worker'],cwd=TESTS.parent,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
    for _ in range(50):
        if STATE.exists():break
        assert child.poll() is None,'Worker failed during startup';time.sleep(.2)
    assert STATE.exists() and alive(child.pid)
    with (TESTS/'logs'/(TAG+'.followup.log')).open('xb') as stream:watcher=subprocess.Popen([sys.executable,'-B',str(Path(__file__).resolve()),'--watch','--thread',THREAD],cwd=TESTS.parent,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
    with launch.open('x',encoding='utf8') as f:json.dump(dict(worker_pid=child.pid,watcher_pid=watcher.pid,thread=THREAD,inputs=[bound(__file__),bound(CODEX)],no_connectivity_test=True),f,indent=2)
    print('Launched genuinely new 3-D sequence and one terminal follow-up:',child.pid,watcher.pid)


if __name__=='__main__':main()
