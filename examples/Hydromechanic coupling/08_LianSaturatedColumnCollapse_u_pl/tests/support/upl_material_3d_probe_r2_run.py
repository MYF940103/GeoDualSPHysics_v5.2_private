"""One CPU material-point candidate execution; no spatial solver or retry."""
import ctypes,datetime,json,subprocess,time
from ctypes import wintypes as w
from pathlib import Path
T=Path(__file__).resolve().parents[1];L=T/'logs';TAG='upl_material_3d_probe_r2';B=L/(TAG+'.build.json');OUT=T/'outputs/upl_material_3d_CPU_result_r2'
def stat(p):
 p=Path(p).resolve();s=p.stat();return dict(path=str(p),bytes=s.st_size,mtime_ns=s.st_mtime_ns)
def js(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def save(p,d):
 with Path(p).open('x',encoding='utf-8') as f:json.dump(d,f,indent=2,allow_nan=False)
def need(b,s):
 if not b:raise RuntimeError(s)
CHECK=L/(TAG+'.check.json');CALL=L/(TAG+'.run.call.json');LOG=L/(TAG+'.run.log')
need(not any(p.exists() for p in (OUT,CHECK,CALL,LOG)),'Existing artifacts protected')
b=js(B);need(b['passed'] and b['consumed_stats_unchanged'],'Closed CPU helper required')
entries=[stat(B),b['program'],b['source'],b['source_build'],*b['runtime'],stat(T/'support/upl_material_3d_candidate_r1.h'),stat(T/'notes/upl_material_3d_candidate_r1.json'),stat(__file__)]
need(all(stat(e['path'])==e for e in entries),'Bound helper/input changed')
argv=[b['program']['path'],'--out',str(OUT)];result=dict(stage=TAG,passed=False,spatial_solver_invocations=0,physical_acceptance=False,SHA_scans=0)
K=ctypes.WinDLL('kernel32',use_last_error=True);K.GetExitCodeProcess.argtypes=[w.HANDLE,ctypes.POINTER(w.DWORD)];K.GetProcessTimes.argtypes=[w.HANDLE,*([ctypes.POINTER(w.FILETIME)]*4)]
try:
 started=datetime.datetime.now(datetime.timezone.utc).isoformat();wall=time.monotonic()
 with LOG.open('xb') as f:
  p=subprocess.Popen(argv,executable=argv[0],shell=False,cwd=T.parent,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
  ft=[w.FILETIME() for _ in range(4)];created=bool(K.GetProcessTimes(int(p._handle),*[ctypes.byref(x) for x in ft]));rc=p.wait();code=w.DWORD();captured=bool(K.GetExitCodeProcess(int(p._handle),ctypes.byref(code)))
 call=dict(program=b['program'],argv=argv,pid=p.pid,explicit_CreateProcess_applicationName=argv[0],creation_time_win32_100ns=(ft[0].dwHighDateTime<<32)|ft[0].dwLowDateTime if created else None,actual_Popen_wait_exit=rc,actual_Win32_exit=code.value if captured else None,started_utc=started,elapsed_s=time.monotonic()-wall,log=stat(LOG),consumed=entries)
 save(CALL,call);result.update(actual_call=stat(CALL),actual_Popen_wait_exit=rc,actual_Win32_exit=code.value if captured else None)
 need(created and captured and rc==code.value==0,'Actual material-point target failed; preserve evidence')
 d=js(OUT/'completion.json');need(d['passed'] and d['stage']==TAG and d['rows']==41 and d['DP_PS_exact_rows']==14 and d['rotation_checks']==9 and d['independent_derivative_sets']==14 and d['finite_difference_max_ratio']<=1,'Declared material-point checks not passed')
 need(all(stat(e['path'])==e for e in entries),'Bound helper/input changed during target')
 result.update(passed=True,source_build=stat(B),actual_completion=d,outputs=[stat(p) for p in sorted(OUT.iterdir())],consumed=entries,consumed_stats_unchanged=True,production_source_changed=False,delivered_r2_changed=False)
except Exception as e:result['first_failure']=str(e)
save(CHECK,result);print(json.dumps(result,indent=2));raise SystemExit(0 if result['passed'] else 1)
