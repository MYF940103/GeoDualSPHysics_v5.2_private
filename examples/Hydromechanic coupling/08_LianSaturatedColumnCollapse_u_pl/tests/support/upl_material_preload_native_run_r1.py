"""Single offline decode of the completed GPU preload; never launches a physical solver."""
from pathlib import Path
import datetime,json,subprocess,time
T=Path(__file__).resolve().parents[1];TAG='upl_material_preload_GPU_r1';L=T/'logs'
def stat(p):
 p=Path(p).resolve();s=p.stat();return dict(path=str(p),bytes=s.st_size,mtime_ns=s.st_mtime_ns)
def save(p,d):
 with p.open('x',encoding='utf-8') as f:json.dump(d,f,indent=2,allow_nan=False);f.write('\n')
owner=L/(TAG+'.run.json');run=json.loads(owner.read_text());assert run['passed'] and run['actual_exit']==0 and run['actual_steps']==8192 and run['saved_frames']==257
build=L/'upl_material_preload_native_r1.build.json';b=json.loads(build.read_text());assert b['passed']
exe=Path(b['program']['path']);assert stat(exe)==b['program']
out=T/'outputs'/(TAG+'_native_r1');call=L/(TAG+'_native_r1.call.json');log=L/(TAG+'_native_r1.log')
assert not out.exists() and not call.exists() and not log.exists(),'Existing decoder evidence protected'
data=T/'outputs'/TAG/'data';parts=sorted(data.glob('Part_*.bi4'));assert len(parts)==257,len(parts)
consumed=[stat(p) for p in [owner,build,exe,T/'support/upl_material_preload_native_r1.cpp',T/'outputs/upl_c08_global_CPU_r1/ids.csv']+parts]
argv=[str(exe),'--read','GPU',str(data),str(out)];started=datetime.datetime.now(datetime.timezone.utc).isoformat();wall=time.monotonic()
with log.open('xb') as f:
 p=subprocess.Popen(argv,cwd=T.parent,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
 import psutil
 q=psutil.Process(p.pid);identity=dict(pid=p.pid,created_epoch=q.create_time(),exe=q.exe(),argv=q.cmdline())
 print(json.dumps(dict(reader_started=identity)),flush=True);rc=p.wait()
save(call,dict(stage=TAG+'_native_r1',program=stat(exe),argv=argv,reader=identity,actual_Popen_wait_exit=rc,actual_Win32_exit=rc,started_utc=started,ended_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),wall_s=time.monotonic()-wall,log=stat(log),consumed=consumed,decoder_invocations=1,solver_invocations=0,SHA_scans=0))
assert rc==0,'Native review failed; keep partial exports and original log'
assert all(stat(p['path'])==p for p in consumed),'Consumed decoder inputs changed'
d=json.loads((out/'completion.json').read_text());assert d['passed'] and d['samples']==257 and d['completed_steps']==8192
save(L/(TAG+'_native_r1.check.json'),dict(stage=TAG+'_native_r1',passed=True,owner_run=stat(owner),reader_call=stat(call),reader_build=stat(build),native_completion=stat(out/'completion.json'),original_guards_passed=True,consumed_stats_unchanged=True,physical_acceptance=False,SHA_scans=0))
print(json.dumps(dict(native_completed=True,completion=d)),flush=True)
