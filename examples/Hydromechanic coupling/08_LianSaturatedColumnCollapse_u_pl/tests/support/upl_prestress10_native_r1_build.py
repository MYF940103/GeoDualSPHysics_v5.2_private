import ctypes,datetime,json,os,shutil,subprocess,traceback
from ctypes import wintypes as w
from pathlib import Path
import psutil
T=Path(__file__).resolve().parents[1];R=T.parents[3];L=T/'logs';S=R/'src';TAG='upl_prestress10_native_r1';HELP=T/'outputs'/TAG
CHECK=L/(TAG+'.build.json');before=[];calls=[]
def need(b,s):
 if not b:raise RuntimeError(s)
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def save(p,j):
 with Path(p).open('x',encoding='utf-8') as f:json.dump(j,f,indent=2);f.write('\n')
def stat(p):
 p=Path(p).resolve();s=p.stat();return dict(path=str(p),bytes=s.st_size,mtime_ns=s.st_mtime_ns)
def bind(p,e=None):
 a=stat(p)
 if e:need((a['bytes'],a['mtime_ns'])==(e['bytes'],e['mtime_ns']),'Closed CPU object SMT differs')
 before.append(a);return a
K=ctypes.WinDLL('kernel32',use_last_error=True);K.GetExitCodeProcess.argtypes=[w.HANDLE,ctypes.POINTER(w.DWORD)]
def invoke(phase,argv,env):
 need(not (L/(TAG+'.'+phase+'.call.json')).exists(),'Existing call protected')
 log=L/(TAG+'.'+phase+'.log');record=dict(stage=TAG+'.'+phase,owner=dict(pid=os.getpid(),created_epoch=psutil.Process().create_time()),program=argv[0],arguments=argv[1:],cwd=str(S),started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),SHA_scans=0)
 with log.open('xb') as f:
  p=subprocess.Popen(argv,cwd=S,env=env,stdout=f,stderr=subprocess.STDOUT);q=psutil.Process(p.pid);record['child']=dict(pid=p.pid,created_epoch=q.create_time(),exe=q.exe(),argv=q.cmdline());rc=p.wait();code=w.DWORD();need(K.GetExitCodeProcess(int(p._handle),ctypes.byref(code)),'Actual Win32 tool exit unavailable')
 record.update(actual_Popen_wait_exit=rc,actual_Win32_exit=code.value,ended_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),console=str(log));path=L/(TAG+'.'+phase+'.call.json');save(path,record);calls.append(str(path));need(rc==0 and code.value==0,'Actual '+phase+' failed; preserve '+str(log))
try:
 need(not HELP.exists() and not CHECK.exists(),'Fresh reader helper/build receipt required')
 bp=L/'upl_gravity_release_DebugCPU_r1.build.json';b=read(bp);need(b['passed'] is True and b['actual_typed_exit_code']==0 and b['source_stats_unchanged'] is True and b['non_main_objects']==85,'Closed current gravity-release CPU closure is not passed');bind(bp)
 objects=b['project_objects'];need(len(objects)==86 and sum(Path(e['path']).name.lower()=='main.obj' for e in objects)==1,'86objects with one main required');objects=[e for e in objects if Path(e['path']).name.lower()!='main.obj'];need(len(objects)==85,'85 nonmain objects required')
 for e in objects:bind(e['path'],e)
 source=T/'support'/(TAG+'.cpp');bind(source);bind(Path(__file__));bind(R/'examples/Hydromechanic coupling/02_TerzaghiConsolidation_q0_PR/tests/support/upl_cpu_public_native_r1.cpp')
 oldc=read(L/'upl_plastic_dilation_native_r1.compile.call.json');oldl=read(L/'upl_plastic_dilation_native_r1.link.call.json');oldroot=str(T/'outputs/upl_plastic_dilation_native_r1');exe=HELP/(TAG+'.exe')
 ca=[x.replace(oldroot,str(HELP)).replace('upl_plastic_dilation_native_r1.cpp',source.name) for x in oldc['arguments']];la=[]
 for x in oldl['arguments']:
  if x.lower().endswith('.obj'):
   if Path(x).name.lower()=='helper.obj':la.extend([str(HELP/'helper.obj')]+[e['path'] for e in objects])
  else:la.append(x.replace(oldroot,str(HELP)).replace('upl_plastic_dilation_native_r1.exe',exe.name))
 setup=subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',stdout=subprocess.PIPE,stderr=subprocess.PIPE);need(setup.returncode==0,'MSVC setup failed');env=dict(os.environ);env.update(x.split('=',1) for x in setup.stdout.decode('mbcs').splitlines() if '=' in x and not x.startswith('='));need(env['VCTOOLSVERSION']=='14.36.32532','MSVC14.36 required')
 HELP.mkdir();invoke('compile',[oldc['program'],*ca],env);invoke('link',[oldl['program'],*la],env)
 runtime=[]
 for name in ('DsphConfig.xml','ChronoEngine.dll','dsphchrono.dll','vcomp140.dll'):
  p=T/'outputs/upl_prestress_check_CPU_r1_runtime'/name;bind(p);shutil.copy2(p,HELP/name);a=stat(p);c=stat(HELP/name);need((a['bytes'],a['mtime_ns'])==(c['bytes'],c['mtime_ns']),'Runtime copy SMT differs');runtime.append(c)
 need(all(stat(e['path'])==e for e in before),'Consumed CPU closure/source SMT changed')
 save(CHECK,dict(stage=TAG+'.build',passed=True,source=stat(source),source_build=stat(bp),program=stat(exe),objects=objects,runtime=runtime,calls=calls,consumed_stats_unchanged=True,consumed_stats=before,SHA_scans=0,decoder_invocations=0,solver_invocations=0,physical_acceptance=False));print('READER_BUILD_PASSED',str(exe),flush=True)
except BaseException as e:
 if not CHECK.exists():save(CHECK,dict(stage=TAG+'.build',passed=False,first_failure=str(e),traceback=traceback.format_exc(),calls=calls,SHA_scans=0,decoder_invocations=0,solver_invocations=0,physical_acceptance=False))
 print(traceback.format_exc(),flush=True);raise
