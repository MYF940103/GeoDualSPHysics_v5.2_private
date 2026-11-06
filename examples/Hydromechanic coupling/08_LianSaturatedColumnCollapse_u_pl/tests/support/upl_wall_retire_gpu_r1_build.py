"""Build one fresh GPU retirement helper from the closed110 objects; never start a target."""
import ctypes,datetime,json,os,shutil,subprocess,traceback
from ctypes import wintypes as w
from pathlib import Path
import psutil
T=Path(__file__).resolve().parents[1];R=T.parents[3];S=R/'src';L=T/'logs';TAG='upl_wall_retire_gpu_r1'
HELP=T/'outputs/upl_wall_retire_GPU_helper_r1';CHECK=L/(TAG+'.build.json');before=[];calls=[]

def need(b,s):
    if not b:raise RuntimeError(s)
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def save(p,d):
    with Path(p).open('x',encoding='utf-8') as f:json.dump(d,f,indent=2);f.write('\n')
def stat(p):
    p=Path(p).resolve();s=p.stat();return dict(path=str(p),bytes=s.st_size,mtime_ns=s.st_mtime_ns)
def bind(p,e=None):
    a=stat(p)
    if e:need((a['bytes'],a['mtime_ns'])==(e['bytes'],e['mtime_ns']),'Closed consumed SMT changed: '+str(p))
    before.append(a);return a
K=ctypes.WinDLL('kernel32',use_last_error=True);K.GetExitCodeProcess.argtypes=[w.HANDLE,ctypes.POINTER(w.DWORD)];K.GetExitCodeProcess.restype=w.BOOL
def invoke(phase,argv,env):
    log=L/(TAG+'.'+phase+'.log');receipt=L/(TAG+'.'+phase+'.call.json');need(not log.exists() and not receipt.exists(),'Existing CL/link artifact protected')
    rec=dict(stage=TAG+'.'+phase,owner=dict(pid=os.getpid(),created_epoch=psutil.Process().create_time()),program=argv[0],arguments=argv[1:],cwd=str(S),started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),SHA_scans=0)
    with log.open('xb') as f:
        p=subprocess.Popen(argv,cwd=S,env=env,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW);rec['child']=dict(pid=p.pid)
        try:q=psutil.Process(p.pid);rec['child']=dict(pid=p.pid,created_epoch=q.create_time(),exe=q.exe(),argv=q.cmdline(),parent_pid=q.ppid())
        except Exception as e:rec['identity_observation_failure']=str(e)
        rc=p.wait();code=w.DWORD();got=bool(K.GetExitCodeProcess(int(p._handle),ctypes.byref(code)))
    rec.update(actual_Popen_wait_exit=rc,actual_Win32_exit=code.value if got else None,ended_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),console=stat(log));save(receipt,rec);calls.append(stat(receipt))
    need(got and rc==code.value==0 and 'identity_observation_failure' not in rec,'Actual '+phase+' failed; preserve first artifacts, no retry')
    need(Path(rec['child']['exe']).samefile(argv[0]) and rec['child']['argv'][1:]==argv[1:],'Actual CL/link identity differs')
try:
    need(not HELP.exists() and not CHECK.exists(),'Fresh helper/build receipt required')
    bp=L/'upl_prestress_Debug_r1.build.json';b=read(bp);need(b['passed'] and b['actual_typed_exit_code']==b['actual_Win32_exit']==0 and b['source_stats_unchanged'] and b['non_main_objects']==110,'Closed prestress GPU Debug111/110 closure required');bind(bp)
    objects=b['project_objects'];need(len(objects)==111 and sum(Path(e['path']).name.lower()=='main.obj' for e in objects)==1,'Actual111object closure/main differs');objects=[e for e in objects if Path(e['path']).name.lower()!='main.obj']
    for e in objects:bind(e['path'],e)
    bind(b['source_capture']['path'],b['source_capture']);expected={os.path.normcase(str(Path(e['path']).resolve())):e for e in read(b['source'])['files']}
    source=T/'support'/(TAG+'.cpp');bind(source);bind(T/'notes'/(TAG+'.json'));bind(__file__)
    cp=L/'upl_free_seepage_GPU_r1.new.compile.call.json';lp=L/'upl_free_seepage_GPU_r1.new.link.call.json';oldc,oldl=read(cp),read(lp);bind(cp);bind(lp)
    need(oldc['actual_Popen_wait_exit']==oldc['actual_tool_Win32_exit']==oldl['actual_Popen_wait_exit']==oldl['actual_tool_Win32_exit']==0,'Successful actual GPU component CL/link recipe required')
    oldroot=str(T/'outputs/upl_free_seepage_GPU_new_helper_r1');oldsource=next(x for x in oldc['arguments'] if x.lower().endswith('.cpp'));exe=HELP/(TAG+'.exe')
    ca=[str(source) if x==oldsource else x.replace(oldroot,str(HELP)) for x in oldc['arguments']]
    la=[x.replace(oldroot,str(HELP)).replace('upl_free_seepage_gpu_r1.exe',exe.name) for x in oldl['arguments'] if not x.lower().endswith('.obj')]+[str(HELP/'helper.obj'),*[e['path'] for e in objects]]
    need(str(source) in ca and '/D_WITHGPU' in ca and not any('_DISABLE_CUDA' in x.upper() for x in ca) and sum(x.lower().endswith('.obj') for x in la)==111,'Actual GPU flags/main+110 source substitution differs')
    runtime_sources=[]
    for name in ('DsphConfig.xml','ChronoEngine.dll','dsphchrono.dll','vcomp140.dll'):
        primary=bind(T/'outputs/upl_prestress_smoke_GPU_r1_runtime'/name);secondary=bind(T/'outputs/upl_prestress_check_GPU_r1_runtime'/name);runtime_sources.append(primary)
        need((primary['bytes'],primary['mtime_ns'])==(secondary['bytes'],secondary['mtime_ns']),'Known GPU runtime copies differ; do not guess a replacement')
    smoke=L/'upl_prestress_smoke_GPU_r1.check.json';sm=read(smoke);need(sm['passed'] and sm['memcheck_zero_errors_and_leaks'],'Closed matching Debug smoke required');bind(smoke);bind(sm['source_build']['path'],sm['source_build'])
    setup=subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW);need(setup.returncode==0,'MSVC setup failed');env=dict(os.environ);env.update(x.split('=',1) for x in setup.stdout.decode('mbcs').splitlines() if '=' in x and not x.startswith('='));need(env['VCTOOLSVERSION']=='14.36.32532','MSVC14.36 required')
    HELP.mkdir();invoke('compile',[oldc['program'],*ca],env)
    dep=HELP/'compile.dependencies.json';headers=[]
    for p in read(dep)['Data']['Includes']:
        key=os.path.normcase(str(Path(p).resolve()))
        if key in expected:headers.append(bind(p,expected[key]))
    need(any(Path(e['path']).name=='JSphGpuSingle.h' for e in headers),'Actual current GPU class header binding missing')
    invoke('link',[oldl['program'],*la],env);runtime=[]
    for e in runtime_sources:
        dst=HELP/Path(e['path']).name;shutil.copy2(e['path'],dst);a=stat(dst);need((a['bytes'],a['mtime_ns'])==(e['bytes'],e['mtime_ns']),'Known Debug runtime copy SMT differs');runtime.append(a)
    need(all(stat(e['path'])==e for e in before),'Consumed GPU closure/source/runtime changed')
    save(CHECK,dict(stage=TAG+'.build',passed=True,source=stat(source),source_build=stat(bp),program=stat(exe),objects=objects,actual_link_object_inputs=111,headers=headers,source_dependencies=stat(dep),runtime=runtime,runtime_sources=runtime_sources,calls=calls,consumed_stats=before,consumed_stats_unchanged=True,proven_GPU_link_recipe=stat(lp),NVCC_or_device_link_invocations=0,target_invocations=0,solver_invocations=0,physical_acceptance=False,SHA_scans=0));print('WALL_RETIRE_GPU_HELPER_BUILD_PASSED',str(exe),flush=True)
except Exception as e:
    if not CHECK.exists():save(CHECK,dict(stage=TAG+'.build',passed=False,first_failure=str(e),traceback=traceback.format_exc(),calls=calls,consumed_stats=before,target_invocations=0,solver_invocations=0,physical_acceptance=False,SHA_scans=0))
    raise
