"""Observe already-live owned CUDA processes through retained Win32 handles; never launch them."""
import argparse, ctypes, hashlib, json, os, subprocess, sys, time
from ctypes import wintypes
from datetime import datetime, timezone
from pathlib import Path
import psutil

T=Path(__file__).resolve().parents[1]
TAG='upl_cryer_live_exit_r1'
L=T/'logs'
THREAD='01a07683-bc64-7463-8db7-9ee6243967d8'
START=L/'upl_cryer_gpu_component_Debug_probe_r3.start.json'
OUT=T/'outputs/upl_cryer_gpu_component_Debug_probe_r3'
PIDS={'tool':52096,'target':43136}

def need(ok,why):
    if not ok: raise ValueError(why)
def utc(): return datetime.now(timezone.utc).isoformat()
def seal(path,obj):
    with path.open('x',encoding='utf-8') as f: json.dump(obj,f,ensure_ascii=False,indent=2); f.write('\n'); f.flush(); os.fsync(f.fileno())
def entry(path):
    path=Path(path).resolve(strict=True); h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''): h.update(b)
    return dict(path=str(path),bytes=path.stat().st_size,sha256=h.hexdigest())
def read(path): return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def worker(args):
    paths={key:L/(TAG+'.'+key+'.json') for key in ('opened','result','queue_attempt','queue_result')}
    need(all(not p.exists() for p in paths.values()),'Existing capture evidence protected; no restart')
    k=ctypes.WinDLL('kernel32',use_last_error=True)
    k.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]; k.OpenProcess.restype=wintypes.HANDLE
    k.CloseHandle.argtypes=[wintypes.HANDLE]
    k.GetProcessTimes.argtypes=[wintypes.HANDLE,*([ctypes.POINTER(wintypes.FILETIME)]*4)]
    k.WaitForSingleObject.argtypes=[wintypes.HANDLE,wintypes.DWORD]; k.WaitForSingleObject.restype=wintypes.DWORD
    k.GetExitCodeProcess.argtypes=[wintypes.HANDLE,ctypes.POINTER(wintypes.DWORD)]
    handles={}; identities={}; exits={}; failure=None; bindings=[]
    try:
        need(not psutil.pid_exists(57736),'Original owner still exists; inspect before independent capture')
        start=read(START)
        need(start['owner_pid']==57736 and start['configuration']=='Debug','Original start identity differs')
        # Acquire both handles BEFORE any potentially slow file hashing. The held
        # kernel objects retain actual exit codes even if their PIDs later recycle.
        for role,pid in PIDS.items():
            p=psutil.Process(pid); h=k.OpenProcess(0x100000|0x1000,False,pid)
            need(bool(h),'Cannot acquire live owned process handle: '+role); handles[role]=h
            ft=[wintypes.FILETIME() for _ in range(4)]
            need(k.GetProcessTimes(h,*[ctypes.byref(x) for x in ft]),'GetProcessTimes failed')
            created=(ft[0].dwHighDateTime<<32)|ft[0].dwLowDateTime
            epoch=created/10000000-11644473600
            need(abs(epoch-p.create_time())<.002,'Opened process instance differs')
            identities[role]=dict(pid=pid,parent_pid=p.ppid(),created_epoch=p.create_time(),
                created_FILETIME_100ns=created,exe=p.exe(),arguments=p.cmdline(),
                process_handle_opened=True,opened_utc=utc(),access='SYNCHRONIZE|QUERY_LIMITED_INFORMATION')
        need(identities['tool']['parent_pid']==57736 and identities['target']['parent_pid']==52096,'Owned parent chain differs')
        target=start['program']; need(Path(identities['target']['exe']).resolve()==Path(target['path']).resolve(),'Target executable differs')
        need(target['sha256']=='6c4f35af9f0cb862aeaf9ffbbed076b3899c91f296442ca771e5d0f78ec77b92','Frozen target identity differs')
        tool_args=identities['tool']['arguments']; child_args=identities['target']['arguments']
        need('--tool' in tool_args and tool_args[tool_args.index('--tool')+1]=='memcheck' and '--error-exitcode' in tool_args,'Actual sanitizer arguments differ')
        need('--out' in child_args and Path(child_args[child_args.index('--out')+1]).resolve()==OUT.resolve(),'Target output differs')
        bindings=[entry(__file__),entry(T/'notes'/ (TAG+'.json')),entry(START),entry(target['path']),entry(identities['tool']['exe'])]
        need(bindings[3]['bytes']==target['bytes'] and bindings[3]['sha256']==target['sha256'],'Target file changed')
        seal(paths['opened'],dict(stage=TAG,utc=utc(),observer_pid=os.getpid(),identities=identities,
            bindings=bindings,original_owner_absent=True,source_start=start,
            native_processes_started_stopped_or_modified=False,old_receipts_written=False,physical_acceptance=False))
        while len(exits)<2:
            for role,h in handles.items():
                if role in exits: continue
                wait=k.WaitForSingleObject(h,0)
                need(wait in (0,258),'WaitForSingleObject failed for '+role)
                if wait==0:
                    code=wintypes.DWORD(); need(k.GetExitCodeProcess(h,ctypes.byref(code)),'Native exit query failed')
                    exits[role]=dict(role=role,pid=PIDS[role],exit_code=int(code.value),observed_utc=utc(),
                        wait_object_signaled=True,method='GetExitCodeProcess on handle opened while original process was live',
                        original_PowerShell_LASTEXITCODE_claimed=False)
                    seal(L/(TAG+'.'+role+'_exit.json'),exits[role])
            if len(exits)<2: time.sleep(2)
        for expected in bindings: need(entry(expected['path'])==expected,'Frozen observer input changed')
    except Exception as exc: failure=str(exc)
    finally:
        for h in handles.values(): k.CloseHandle(h)
    result=dict(stage=TAG,utc=utc(),capture_complete=len(exits)==2 and failure is None,
        actual_exit_codes=exits,all_actual_exits_zero=len(exits)==2 and all(e['exit_code']==0 for e in exits.values()),
        failure=failure,bindings=bindings,opened_record=entry(paths['opened']) if paths['opened'].exists() else None,
        original_owner_exit_unknown=True,original_r3_call_or_run_fabricated=False,
        component_completion_memcheck_or_physics_validated=False,solver_or_program_restarted=False,physical_acceptance=False)
    seal(paths['result'],result)
    message=('User-authorized same-thread Cryer live-exit recovery continuation, not a new human observation. Read '+str(paths['opened'])+' and '+str(paths['result'])+
        '. Original r3 PowerShell owner57736 exited while tool52096/target43136 remained live; native process handles were acquired before their exits. '
        'Inspect actual Win32 exit captures, native completion, memcheck, frozen hashes and task interruption evidence. Do not invent original LASTEXITCODE or old r3 receipts. '
        'No program was restarted. Preserve original results; repair only fresh audit/reviewer artifacts when justified. Actual exits/normal completion do not prove component or physical acceptance. '
        'Keep original numerical budgets, CPU comparison and all six-probe checks. Current CPU HG half and lossless VTK cleanup remain active; do not duplicate or stop them. '
        'Report in Chinese and continue authorized u-pl development and cleanup. This one-shot observer queues once, never restart/rearm or resend on uncertainty.')
    argv=[args.codex,'queue','--thread',THREAD,'--message',message]
    seal(paths['queue_attempt'],dict(stage=TAG,utc=utc(),attempt=1,thread=THREAD,result=entry(paths['result']),arguments=argv,timeout_s=45))
    outcome=dict(stage=TAG,utc=utc(),attempts=1,automatic_retry=False)
    try:
        q=subprocess.run(argv,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,
            encoding='utf-8',errors='replace',timeout=45,creationflags=subprocess.CREATE_NO_WINDOW)
        outcome.update(status='queued' if q.returncode==0 else 'queue_failed',exit_code=q.returncode,output=q.stdout)
    except (OSError,subprocess.TimeoutExpired) as exc: outcome.update(status='queue_delivery_uncertain',error=str(exc),do_not_resend=True)
    seal(paths['queue_result'],outcome)

def main():
    p=argparse.ArgumentParser(description=__doc__);g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--launch',action='store_true');g.add_argument('--worker',action='store_true')
    p.add_argument('--thread',required=True);p.add_argument('--codex',required=True);a=p.parse_args()
    need(os.name=='nt' and a.thread==THREAD and Path(a.codex).is_file(),'Exact Windows thread and existing Codex path required')
    if a.worker: worker(a); return
    lock=L/(TAG+'.lock.json'); log=L/(TAG+'.worker.log')
    need(not lock.exists() and not log.exists(),'Existing recovery protected; no rearm')
    seal(lock,dict(stage=TAG,utc=utc(),thread=THREAD,script=entry(__file__),purpose='Observe already-live tool/target only'))
    with log.open('x',encoding='utf-8') as f:
        child=subprocess.Popen([sys.executable,'-u','-B',str(Path(__file__).resolve()),'--worker','--thread',THREAD,'--codex',a.codex],
            stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
    print(json.dumps(dict(observer_pid=child.pid,opened_record=str(L/(TAG+'.opened.json')),native_program_started=False)))

if __name__=='__main__': main()
