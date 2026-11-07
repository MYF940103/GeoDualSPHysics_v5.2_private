"""One tiny offline inspection of saved rejected-source files; never retries or runs a solver."""
import ctypes,datetime,json,os,subprocess,time
from ctypes import wintypes as w
from pathlib import Path
T=Path(__file__).resolve().parents[1];L=T/'logs';TAG='upl_preload_handoff_reject_native_r1';RUN=L/'upl_preload_handoff_reject_CPU_r1.run.json';BUILD=L/(TAG+'.build.json');OUT=T/'outputs/upl_preload_handoff_reject_CPU_r1_native_inspect_r1';DATA=T/'outputs/upl_preload_handoff_reject_CPU_r1/data'
CHECK=L/(TAG+'.check.json');CALL=L/(TAG+'.call.json');START=L/(TAG+'.start.json');LOG=L/(TAG+'.log')
def need(b,s):
    if not b:raise RuntimeError(s)
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def stat(p):
    p=Path(p).resolve();s=p.stat();return dict(path=str(p),bytes=s.st_size,mtime_ns=s.st_mtime_ns)
def save(p,d):
    with Path(p).open('x',encoding='utf-8') as f:json.dump(d,f,indent=2);f.write('\n')
need(not any(p.exists() for p in (OUT,CHECK,CALL,START,LOG)),'Existing inspection/partial evidence protected; no retry')
K=ctypes.WinDLL('kernel32',use_last_error=True);K.GetExitCodeProcess.argtypes=[w.HANDLE,ctypes.POINTER(w.DWORD)];K.GetExitCodeProcess.restype=w.BOOL;K.GetProcessTimes.argtypes=[w.HANDLE,*([ctypes.POINTER(w.FILETIME)]*4)];K.GetProcessTimes.restype=w.BOOL
bound=[];result=dict(stage=TAG,passed=False,solver_invocations=0,inspector_invocations=0,SHA_scans=0,physical_acceptance=False)
def bind(e):
    a=stat(e['path']);need(a==e,'Consumed file changed: '+e['path']);bound.append(a);return a
try:
    run,build=read(RUN),read(BUILD);bind(stat(RUN));bind(stat(BUILD));bind(stat(__file__))
    need(run['passed'] and run['expected_rejection'] and run['expected_rejection_observed'] and run['actual_exit']==run['actual_Win32_exit']==1 and run['actual_status_mask']==4 and run['consumed_stats_unchanged'],'Original owned expected predictor rejection is not closed')
    call=read(run['actual_call']['path']);bind(run['actual_call']);need(call['actual_Popen_wait_exit']==call['actual_tool_Win32_exit']==call['actual_solver_Win32_exit']==1 and not call['ownership_errors'],'Original expected rejection exits/ownership differ')
    need(build['passed'] and build['consumed_stats_unchanged'],'Closed tiny inspector build required');bind(build['program']);bind(build['source']);bind(build['source_build'])
    for e in build['runtime']:bind(e)
    parts=sorted(DATA.glob('Part_*.bi4'));need([p.name for p in parts]==['Part_0000.bi4'],'Unexpected rejected-source saved files')
    for p in parts:bind(stat(p))
    exe=Path(build['program']['path']);argv=[str(exe),'--inspect',str(DATA),str(OUT)];started=datetime.datetime.now(datetime.timezone.utc).isoformat();wall=time.monotonic()
    # Explicit lpApplicationName fixes the invoked native image even if this tiny reader exits before an image query.
    with LOG.open('xb') as f:
        proc=subprocess.Popen(argv,executable=str(exe),shell=False,cwd=T.parent,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW);result['inspector_invocations']=1
        creation,exit_time,kernel,user=w.FILETIME(),w.FILETIME(),w.FILETIME(),w.FILETIME();need(K.GetProcessTimes(int(proc._handle),ctypes.byref(creation),ctypes.byref(exit_time),ctypes.byref(kernel),ctypes.byref(user)),'Actual native creation time unavailable')
        created=(creation.dwHighDateTime<<32)|creation.dwLowDateTime;child=dict(pid=proc.pid,creation_time_win32_100ns=created,explicit_CreateProcess_applicationName=str(exe),argv=argv,image_name_queried=False)
        save(START,dict(stage=TAG+'.start',owner_pid=os.getpid(),child=child,source_run=stat(RUN),reader_build=stat(BUILD),consumed=bound));rc=proc.wait();code=w.DWORD();need(K.GetExitCodeProcess(int(proc._handle),ctypes.byref(code)),'Actual inspector exit unavailable')
    save(CALL,dict(stage=TAG+'.call',owner_pid=os.getpid(),child=child,actual_Popen_wait_exit=rc,actual_Win32_exit=code.value,started_utc=started,ended_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),elapsed_s=time.monotonic()-wall,log=stat(LOG)))
    need(rc==code.value==0,'Native inspector failed; preserve output, no retry');d=read(OUT/'completion.json')
    need(d['passed'] and d['stage']==TAG and d['inspected_native_frames']==1 and d['last_saved_time_s']==0 and d['last_saved_step']==0 and d['last_saved_kappa_max']==0 and d['original_IDs']==7060 and d['typed_arrays']==22 and d['all_four_handoff_certification_keys_absent'],'Actual saved initial/native-cert absence mismatch')
    need(d['failure_time_known'] is False and d['failure_time_s'] is None and d['last_saved_state_is_not_the_failure_state'] and d['all22_array_values_fully_decoded'] is False,'Inspector improperly inferred failure time or full-state decoding')
    need(all(stat(e['path'])==e for e in bound),'Consumed closed evidence changed')
    result.update(passed=True,original_expected_reject_run=stat(RUN),original_actual_solver_exit=1,original_predictor_status_mask=4,native_completion=stat(OUT/'completion.json'),actual_saved_state=d,actual_inspector_call=stat(CALL),consumed=bound,consumed_stats_unchanged=True,failure_time_s=None,last_saved_time_s=0,qualified_handoff_written=False)
except Exception as e:result.update(first_failure=str(e),consumed=bound)
save(CHECK,result);print(json.dumps(result,indent=2));raise SystemExit(0 if result['passed'] else 1)
