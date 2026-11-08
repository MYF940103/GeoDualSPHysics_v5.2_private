"""One build-only owner: capture, default CPU Debug, trace GPU Debug/Release; no solver."""
import argparse,datetime,json,os,subprocess,time
from pathlib import Path
import psutil
import upl_c08_stage_trace_build_r1 as build
T=Path(__file__).resolve().parents[1];L=T/'logs';TAG='upl_c08_stage_trace_sequence_r1'
THREAD='01a07683-bc64-7463-8db7-9ee6243967d8'
CLI=Path('C:/Users/syosh/.vscode/extensions/openai.chatgpt-26.1021.22027-win32-x64/bin/windows-x86_64/codex.exe')
def write(p,data,replace=False):
    with p.open('w' if replace else 'x',encoding='utf-8') as f:json.dump(data,f,indent=2);f.write('\n')
def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--execution-authorized',action='store_true');args=ap.parse_args()
    assert args.execution_authorized and CLI.is_file()
    assert not any((L/(TAG+s)).exists() for s in ('.start.json','.run.json','.queue_attempt.json'))
    started=time.monotonic();owner=dict(pid=os.getpid(),created_epoch=psutil.Process().create_time(),exe=psutil.Process().exe(),argv=psutil.Process().cmdline())
    consumed=[build.stat(p) for p in (Path(__file__),Path(build.__file__),T/'notes/upl_c08_stage_trace_build_r1.md',T/'support/upl_c08_stage_trace_r1.patch')]
    write(L/(TAG+'.start.json'),dict(stage=TAG,owner=owner,started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),consumed=consumed,actions=['capture','DebugCPU','Debug','Release'],solver_invocations=0))
    rows=[];failure=None
    try:
        build.capture()
        for configuration in ('DebugCPU','Debug','Release'):
            write(L/(TAG+'.status.json'),dict(stage=TAG,owner=owner,state='building_'+configuration,solver_invocations=0),True)
            rc=build.build(configuration);receipt=L/('upl_c08_stage_trace_'+configuration+'_r1.build.json');r=build.read(receipt)
            rows.append(dict(configuration=configuration,receipt=build.stat(receipt),passed=bool(rc==0 and r['passed'])))
            if not rows[-1]['passed']:raise RuntimeError('Build rejected: '+configuration+'; inspect preserved receipt')
        assert build.unchanged(consumed),'Build-owner inputs changed'
    except Exception as error:failure=str(error)
    result=dict(stage=TAG,owner=owner,passed=failure is None,first_failure=failure,builds=rows,elapsed_s=time.monotonic()-started,consumed=consumed,solver_invocations=0,help_invocations=0,native_reader_invocations=0,physical_acceptance=False,runtime_installed=False,SHA_scans=0)
    write(L/(TAG+'.run.json'),result);write(L/(TAG+'.status.json'),dict(stage=TAG,owner=owner,state='builds_passed_pending_review' if result['passed'] else 'build_failed_preserved',solver_invocations=0),True)
    message=('User-authorized same-thread C08 stage-observer build continuation, not a physical observation. Event='+('three_builds_passed_pending_implementation_review' if result['passed'] else 'build_rejected_or_interrupted')+'. Read '+str(L/(TAG+'.run.json'))+' and original start/status plus all immutable CPU Debug/GPU Debug/Release build calls/receipts. This stage builds only: no help, solver, native read, VTK or physical acceptance. Verify actual tool exits, enabled/undefined macro, frozen source and original r2 PRE/runtime protection. Preserve failures and repair only new candidate artifacts. The accepted r5 psi0 solver/postprocessing is complete; pressure pulses and early arrest remain unresolved. No automatic other-psi, half, preload or long solver launch. Continue reviewed output-only instrumentation and original authorized diagnosis without another progress prompt. Never restart/rearm this owner, old workers or connectivity self-tests; this direct owner queues once only.')
    attempt=dict(stage=TAG,owner=owner,message=message,notification_attempts=1,timeout_s=45,timeout_may_have_delivered=True)
    write(L/(TAG+'.queue_attempt.json'),attempt)
    try:
        q=subprocess.run([str(CLI),'queue','--thread',THREAD,'--message',message],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=45,creationflags=subprocess.CREATE_NO_WINDOW)
        notice=dict(exit=q.returncode,stdout=q.stdout.decode('utf-8',errors='replace'),stderr=q.stderr.decode('utf-8',errors='replace'),attempts=1)
    except subprocess.TimeoutExpired:notice=dict(timeout=True,may_have_delivered=True,attempts=1)
    write(L/(TAG+'.queue_result.json'),notice)
    print(json.dumps(dict(passed=result['passed'],first_failure=failure,notification=notice)),flush=True)
    return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
