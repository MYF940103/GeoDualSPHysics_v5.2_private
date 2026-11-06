"""One owned CPU read of the fresh completed 10s preload; no solver or restart."""
import ctypes,datetime,json,subprocess,sys,time
from ctypes import wintypes as w
from pathlib import Path
import psutil
T=Path(__file__).resolve().parents[1];L=T/'logs'
window,backend=sys.argv[1:];assert window=='preload10' and backend=='CPU'
tag='upl_prestress10_CPU_r1';owner=L/(tag+'.run.json');build=L/'upl_prestress10_native_r1.build.json'
out=T/'outputs'/(tag+'_native_r1');data=T/'outputs'/tag/'data';call=L/(tag+'_native_r1.call.json');check=L/(tag+'_native_r1.check.json');log=L/(tag+'_native_r1.log')
def stat(p):
    p=Path(p).resolve();s=p.stat();return dict(path=str(p),bytes=s.st_size,mtime_ns=s.st_mtime_ns)
def js(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def save(p,d):
    with Path(p).open('x',encoding='utf-8') as f:json.dump(d,f,indent=2);f.write('\n')
assert not any(p.exists() for p in (out,call,check,log))
run,b=js(owner),js(build);steps=4000000
assert run['passed'] and run['actual_exit']==run['actual_Win32_exit']==0 and run['consumed_stats_unchanged'] and steps<=run['actual_steps']<=steps+1 and b['passed']
solver_call=Path(run['actual_call']['path']);assert stat(solver_call)==run['actual_call'];actual=js(solver_call);assert actual['actual_Popen_wait_exit']==actual['actual_Win32_exit']==0
assert all(stat(e['path'])==e for e in run['consumed'])
exe=Path(b['program']['path']);assert stat(exe)==b['program']
parts=sorted(data.glob('Part_*.bi4'));assert len(parts)==run['saved_frames']
consumed=[*run['consumed'],stat(solver_call),*b['runtime']]+[stat(p) for p in (owner,build,exe,Path(__file__),T/'support/upl_prestress10_native_r1.cpp',T/'notes/upl_prestress10_native_r1.json',T/'outputs/upl_c08_global_CPU_r1/ids.csv')]+[stat(p) for p in parts]
assert all(stat(e['path'])==e for e in consumed)
argv=[str(exe),'--read',window,backend,str(data),str(out)];started=datetime.datetime.now(datetime.timezone.utc).isoformat();wall=time.monotonic()
with log.open('xb') as f:
    p=subprocess.Popen(argv,cwd=T.parent,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
    q=psutil.Process(p.pid);child=dict(pid=p.pid,created_epoch=q.create_time(),exe=q.exe(),argv=q.cmdline())
    print(json.dumps(dict(reader_started=child)),flush=True);rc=p.wait()
    K=ctypes.WinDLL('kernel32',use_last_error=True);K.GetExitCodeProcess.argtypes=[w.HANDLE,ctypes.POINTER(w.DWORD)];code=w.DWORD();assert K.GetExitCodeProcess(int(p._handle),ctypes.byref(code))
save(call,dict(stage=tag+'_native_r1',child=child,argv=argv,actual_Popen_wait_exit=rc,actual_Win32_exit=code.value,started_utc=started,ended_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),elapsed_s=time.monotonic()-wall,log=stat(log),consumed=consumed,decoder_invocations=1,solver_invocations=0,SHA_scans=0))
assert rc==code.value==0,'Keep failed decode and original log; no retry or overwrite'
assert all(stat(e['path'])==e for e in consumed)
d=js(out/'completion.json');assert d['passed'] and d['stage']=='upl_prestress10_native_r1' and d['input_run_tag']==tag and d['samples']==run['saved_frames'] and d['completed_steps']==run['actual_steps'] and d['gravitypreload_metadata_absent_verified']
save(check,dict(stage=tag+'_native_r1',passed=True,source_run=stat(owner),source_run_call=stat(solver_call),reader_call=stat(call),reader_build=stat(build),native_completion=stat(out/'completion.json'),original_native_guards_passed=True,consumed_stats_unchanged=True,physical_acceptance=False,SHA_scans=0))
print(json.dumps(dict(native_completed=True,samples=d['samples'],actual_end_s=d['actual_end_s'],soil_ledger_checks=d['soil_ledger_checks'],FS_checks=d['saved_FS23_soil_checks'],P0_checks=d['all_ID_p0_float_bits_checks'],physical_acceptance=False)),flush=True)
