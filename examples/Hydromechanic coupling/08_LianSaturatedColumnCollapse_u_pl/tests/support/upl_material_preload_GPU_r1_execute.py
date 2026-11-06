"""One owned ordinary GPU preload; no solver replay, SHA sweep or automatic next run."""
from pathlib import Path
import csv,ctypes,datetime,json,os,shutil,subprocess,time,traceback
from ctypes import wintypes as w

T=Path(__file__).resolve().parents[1];C=T.parent
TAG='upl_material_preload_GPU_r1';NAME='CaseLianSaturatedColumnCollapse_preload_r1'
OUT=T/'outputs'/TAG;RUN=T/'outputs'/(TAG+'_runtime');SEED=T/'outputs/upl_material_preload_r1_seed'
LOG=T/'logs';BUILD=LOG/'upl_material_gravity_Debug_r1.build.json'
def stat(p):
 p=Path(p).resolve();s=p.stat();return dict(path=str(p),bytes=s.st_size,mtime_ns=s.st_mtime_ns)
def save(p,d):
 with Path(p).open('x',encoding='utf-8') as f:json.dump(d,f,indent=2,allow_nan=False);f.write('\n')
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def need(v,msg):
 if not v:raise RuntimeError(msg)
def identity(handle,pid):
 k=ctypes.WinDLL('kernel32',use_last_error=True);k.GetProcessTimes.argtypes=[w.HANDLE,ctypes.POINTER(w.FILETIME),ctypes.POINTER(w.FILETIME),ctypes.POINTER(w.FILETIME),ctypes.POINTER(w.FILETIME)]
 a,b,c,d=w.FILETIME(),w.FILETIME(),w.FILETIME(),w.FILETIME();need(k.GetProcessTimes(w.HANDLE(int(handle)),ctypes.byref(a),ctypes.byref(b),ctypes.byref(c),ctypes.byref(d)),'GetProcessTimes failed')
 return dict(pid=pid,creation_filetime_100ns=(a.dwHighDateTime<<32)|a.dwLowDateTime)

def main():
 need(not any(p.exists() for p in [OUT,RUN,LOG/(TAG+'.start.json'),LOG/(TAG+'.call.json')]),'Existing candidate/owner record protected')
 b=json.loads(BUILD.read_text(encoding='utf-8-sig'));need(b['passed'],'GPU build not closed')
 control=LOG/'upl_material_gravity_GPU_r1_native_r1.check.json';need(json.loads(control.read_text(encoding='utf-8-sig'))['passed'],'Short native prerequisite failed')
 program=Path(b['program']['path']);need(stat(program)==b['program'],'Closed GPU program identity changed')
 files=[SEED/(NAME+e) for e in ['.xml','.bi4','_Normals.nbi4']]+[BUILD,Path(b['source']),control]
 BIN=C.parents[2]/'bin/windows';runtime=[BIN/n for n in ['DsphConfig.xml','ChronoEngine.dll','dsphchrono.dll','vcomp140.dll']]
 before=[stat(p) for p in files+[program]+runtime]
 RUN.mkdir();OUT.mkdir();shutil.copy2(program,RUN/program.name)
 for p in runtime:shutil.copy2(p,RUN/p.name)
 exe=RUN/program.name;argv=[str(exe),'-gpu:0','-stable','-mdbc_freeslip',str(SEED/NAME),str(OUT),'-dirdataout','data','-svres','-nsteps:8192']
 consumed=before+[stat(p) for p in RUN.iterdir() if p.is_file()]
 console=LOG/(TAG+'.console.log');started=now();wall=time.monotonic()
 with console.open('xb') as f:
  process=subprocess.Popen(argv,cwd=C,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
  own=identity(process._handle,process.pid)
  save(LOG/(TAG+'.start.json'),dict(stage=TAG,owner_pid=os.getpid(),solver=own,argv=argv,working_directory=str(C),started_utc=started,program_source_truth='Retained closed gravity GPU program and original archive; subsequent live edit only regrouped input reads',consumed=consumed,SAN_invocations=0,solver_invocations=1,SHA_scans=0,native_review_pending=True))
  print(json.dumps(dict(actual_solver_started=True,solver=own,argv=argv)),flush=True)
  rc=process.wait()
 call=dict(stage=TAG,solver=own,argv=argv,actual_Popen_wait_exit=rc,actual_solver_Win32_exit=rc,started_utc=started,ended_utc=now(),wall_s=time.monotonic()-wall,console=stat(console),solver_invocations=1,SAN_invocations=0,SHA_scans=0,physical_acceptance=False)
 save(LOG/(TAG+'.call.json'),call)
 need(all(stat(p['path'])==p for p in consumed),'Consumed program/input/runtime changed')
 need(rc==0,'Actual GPU solver failed; preserve console/output')
 with (OUT/'Run.csv').open(encoding='utf-8-sig') as f:
  rows=list(csv.DictReader(f,delimiter=';'))
 need(len(rows)==1,'Completed Run.csv missing');summary=rows[0]
 for key,value in dict(Steps=8192,PartFiles=257,Np=7060,Nbound=2060,Nfixed=2060,PartsOut=0,PartsOutRhop=0,PartsOutVel=0).items():need(int(summary[key])==value,'Unexpected run summary '+key)
 save(LOG/(TAG+'.run.json'),dict(stage=TAG,passed=True,solver=own,actual_exit=rc,summary=summary,consumed_stats_unchanged=True,actual_steps=8192,saved_frames=257,console=stat(console),native_review_pending=True,physical_acceptance=False,SHA_scans=0))
 print(json.dumps(dict(solver_summary_completed=True,steps=8192,frames=257,native_review_pending=True)),flush=True)

if __name__=='__main__':
 try:main()
 except Exception as e:
  p=LOG/(TAG+'.failure.json')
  if not p.exists():save(p,dict(stage=TAG,passed=False,reason=str(e),traceback=traceback.format_exc(),observed_utc=now(),no_automatic_retry=True,physical_acceptance=False))
  raise
