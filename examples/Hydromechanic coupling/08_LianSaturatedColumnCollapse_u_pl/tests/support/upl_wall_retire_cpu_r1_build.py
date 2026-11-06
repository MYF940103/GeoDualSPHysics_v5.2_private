"""Build only one fresh wall-retirement component from the closed CPU85 closure; no target."""
import ctypes,datetime,json,os,shutil,subprocess,traceback
from ctypes import wintypes as w
from pathlib import Path
import psutil
T=Path(__file__).resolve().parents[1];R=T.parents[3];L=T/'logs';S=R/'src';TAG='upl_wall_retire_cpu_r1'
HELP=T/'outputs/upl_wall_retire_CPU_helper_r1';CHECK=L/(TAG+'.build.json');before=[];calls=[]
def need(b,s):
    if not b:raise RuntimeError(s)
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def save(p,d):
    with Path(p).open('x',encoding='utf-8') as f:json.dump(d,f,indent=2);f.write('\n')
def stat(p):
    p=Path(p).resolve();s=p.stat();return dict(path=str(p),bytes=s.st_size,mtime_ns=s.st_mtime_ns)
def bind(p,e=None):
    a=stat(p)
    if e:need((a['bytes'],a['mtime_ns'])==(e['bytes'],e['mtime_ns']),'Closed input/object SMT changed: '+str(p))
    before.append(a);return a
K=ctypes.WinDLL('kernel32',use_last_error=True);K.GetExitCodeProcess.argtypes=[w.HANDLE,ctypes.POINTER(w.DWORD)];K.GetExitCodeProcess.restype=w.BOOL
def invoke(phase,argv,env):
    log=L/(TAG+'.'+phase+'.log');path=L/(TAG+'.'+phase+'.call.json');need(not log.exists() and not path.exists(),'Existing tool artifacts protected')
    record=dict(stage=TAG+'.'+phase,owner=dict(pid=os.getpid(),created_epoch=psutil.Process().create_time()),program=argv[0],arguments=argv[1:],cwd=str(S),started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),SHA_scans=0)
    with log.open('xb') as f:
        p=subprocess.Popen(argv,cwd=S,env=env,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        try:q=psutil.Process(p.pid);record['child']=dict(pid=p.pid,created_epoch=q.create_time(),exe=q.exe(),argv=q.cmdline(),parent_pid=q.ppid())
        except Exception as e:record['identity_observation_failure']=str(e);record['child']=dict(pid=p.pid)
        rc=p.wait();code=w.DWORD();got=bool(K.GetExitCodeProcess(int(p._handle),ctypes.byref(code)))
    record.update(actual_Popen_wait_exit=rc,actual_Win32_exit=code.value if got else None,ended_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),console=stat(log));save(path,record);calls.append(stat(path))
    need(got and rc==code.value==0 and 'identity_observation_failure' not in record,'Actual '+phase+' failed or identity unavailable; preserve '+str(log))
try:
    need(not HELP.exists() and not CHECK.exists(),'Fresh helper/build receipt required')
    bp=L/'upl_prestress_DebugCPU_r1.build.json';b=read(bp);need(b['passed'] is True and b['actual_typed_exit_code']==0 and b['source_stats_unchanged'] is True and b['non_main_objects']==85,'Closed prestress DebugCPU closure required');bind(bp)
    objects=b['project_objects'];need(len(objects)==86 and sum(Path(e['path']).name.lower()=='main.obj' for e in objects)==1,'86objects with one original main required');objects=[e for e in objects if Path(e['path']).name.lower()!='main.obj'];need(len(objects)==85,'Exactly85 nonmain objects required')
    for e in objects:bind(e['path'],e)
    source=T/'support'/(TAG+'.cpp');bind(source);bind(T/'notes'/ (TAG+'.json'));bind(__file__)
    cp=L/'upl_prestress_shepard_cpu_r1.compile.call.json';lp=L/'upl_prestress_shepard_cpu_r1.link.call.json';oldc,oldl=read(cp),read(lp);bind(cp);bind(lp)
    need(oldc['actual_Popen_wait_exit']==oldc['actual_Win32_exit']==oldl['actual_Popen_wait_exit']==oldl['actual_Win32_exit']==0,'Successful retained component CL/link recipe required')
    oldroot=str(T/'outputs/upl_prestress_shepard_cpu_r1');exe=HELP/(TAG+'.exe')
    ca=[x.replace(oldroot,str(HELP)).replace('upl_prestress_shepard_cpu_r1.cpp',source.name) for x in oldc['arguments']];la=[]
    for x in oldl['arguments']:
        if x.lower().endswith('.obj'):
            if Path(x).name.lower()=='helper.obj':la.extend([str(HELP/'helper.obj')]+[e['path'] for e in objects])
        else:la.append(x.replace(oldroot,str(HELP)).replace('upl_prestress_shepard_cpu_r1.exe',exe.name))
    need(sum(x.lower().endswith('.obj') for x in la)==86 and str(source) in ca,'Exact fresh main+85 link/source substitution required')
    runtime_sources=[bind(T/'outputs/upl_prestress_check_CPU_r1_runtime'/name) for name in ('DsphConfig.xml','ChronoEngine.dll','dsphchrono.dll','vcomp140.dll')]
    setup=subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW);need(setup.returncode==0,'MSVC setup failed');env=dict(os.environ);env.update(x.split('=',1) for x in setup.stdout.decode('mbcs').splitlines() if '=' in x and not x.startswith('='));need(env['VCTOOLSVERSION']=='14.36.32532','MSVC14.36 required')
    HELP.mkdir();invoke('compile',[oldc['program'],*ca],env);invoke('link',[oldl['program'],*la],env)
    runtime=[]
    for e in runtime_sources:
        dst=HELP/Path(e['path']).name;shutil.copy2(e['path'],dst);a=stat(dst);need((a['bytes'],a['mtime_ns'])==(e['bytes'],e['mtime_ns']),'Closed runtime copy SMT differs');runtime.append(a)
    need(all(stat(e['path'])==e for e in before),'Consumed CPU closure/source/runtime SMT changed')
    save(CHECK,dict(stage=TAG+'.build',passed=True,source=stat(source),source_build=stat(bp),program=stat(exe),objects=objects,runtime=runtime,runtime_sources=runtime_sources,calls=calls,consumed_stats=before,consumed_stats_unchanged=True,SHA_scans=0,target_invocations=0,solver_invocations=0,physical_acceptance=False));print('WALL_RETIRE_COMPONENT_BUILD_PASSED',str(exe),flush=True)
except Exception as e:
    if not CHECK.exists():save(CHECK,dict(stage=TAG+'.build',passed=False,first_failure=str(e),traceback=traceback.format_exc(),calls=calls,SHA_scans=0,target_invocations=0,solver_invocations=0,physical_acceptance=False))
    raise
