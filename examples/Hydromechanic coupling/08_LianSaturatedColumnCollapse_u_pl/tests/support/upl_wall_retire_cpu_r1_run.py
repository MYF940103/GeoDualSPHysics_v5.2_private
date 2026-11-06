"""One owned zero-step wall-retirement component invocation; no solver, retry or queue."""
import csv,ctypes,datetime,json,subprocess,time
from ctypes import wintypes as w
from pathlib import Path
import psutil
T=Path(__file__).resolve().parents[1];L=T/'logs';TAG='upl_wall_retire_CPU_r1';OUT=T/'outputs'/TAG
BUILD=L/'upl_wall_retire_cpu_r1.build.json';SEED=T/'outputs/upl_c08_observer_r1_seed/CaseLianSaturatedColumnCollapse_geometry_r1'
CALL=L/(TAG+'.call.json');CHECK=L/(TAG+'.check.json');START=L/(TAG+'.start.json');LOG=L/(TAG+'.log')
def need(b,s):
    if not b:raise RuntimeError(s)
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def stat(p):
    p=Path(p).resolve();s=p.stat();return dict(path=str(p),bytes=s.st_size,mtime_ns=s.st_mtime_ns)
def save(p,d):
    with Path(p).open('x',encoding='utf-8') as f:json.dump(d,f,indent=2);f.write('\n')
def bind(e):
    a=stat(e['path']);need((a['bytes'],a['mtime_ns'])==(e['bytes'],e['mtime_ns']),'Closed helper binding changed: '+e['path']);return a
def identity(q):return dict(pid=q.pid,created_epoch=q.create_time(),exe=q.exe(),argv=q.cmdline(),parent_pid=q.ppid())
K=ctypes.WinDLL('kernel32',use_last_error=True);K.GetExitCodeProcess.argtypes=[w.HANDLE,ctypes.POINTER(w.DWORD)];K.GetExitCodeProcess.restype=w.BOOL
need(not any(p.exists() for p in (OUT,CALL,CHECK,START,LOG)),'Existing component result/receipt protected')
result=dict(stage=TAG,passed=False,physical_steps=0,solver_invocations=0,component_invocations=0,SHA_scans=0,physical_acceptance=False);before=[]
try:
    b=read(BUILD);need(b['passed'] and b['consumed_stats_unchanged'] and len(b['objects'])==85,'Closed fresh helper build required')
    before=[stat(BUILD),bind(b['program']),bind(b['source']),bind(b['source_build']),*[bind(e) for e in b['runtime']],stat(__file__),stat(T/'notes/upl_wall_retire_cpu_r1.json')]
    before += [stat(str(SEED)+suffix) for suffix in ('.xml','.bi4','_Normals.nbi4')]
    exe=Path(b['program']['path']);need(exe.samefile(T/'outputs/upl_wall_retire_CPU_helper_r1/upl_wall_retire_cpu_r1.exe'),'Unexpected helper executable')
    active=[q.info for q in psutil.process_iter(['pid','name','cmdline']) if (q.info['name'] or '').lower()==exe.name.lower()];need(not active,'A matching wall-retirement component is already active')
    argv=[str(exe),'--retire','-cpu','-ompthreads:1','-stable','-mdbc_freeslip',str(SEED),str(OUT)];owner=identity(psutil.Process());started=datetime.datetime.now(datetime.timezone.utc).isoformat();wall=time.monotonic();observation_error=None
    with LOG.open('xb') as stream:
        p=subprocess.Popen(argv,cwd=T.parent,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW);child=dict(pid=p.pid);result['component_invocations']=1
        try:
            child=identity(psutil.Process(p.pid));need(Path(child['exe']).samefile(exe) and child['argv'][1:]==argv[1:] and child['parent_pid']==owner['pid'],'Actual component child identity differs');save(START,dict(stage=TAG+'.start',owner=owner,child=child,argv=argv,cwd=str(T.parent),source_build=stat(BUILD),consumed_stats=before,physical_steps=0))
        except Exception as e:observation_error=str(e)
        rc=p.wait();code=w.DWORD();got=bool(K.GetExitCodeProcess(int(p._handle),ctypes.byref(code)))
    save(CALL,dict(stage=TAG+'.call',owner=owner,child=child,program=b['program'],argv=argv,cwd=str(T.parent),started_utc=started,ended_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),actual_Popen_wait_exit=rc,actual_Win32_exit=code.value if got else None,identity_observation_failure=observation_error,elapsed_s=time.monotonic()-wall,log=stat(LOG),physical_steps=0,component_invocations=1,solver_invocations=0,SHA_scans=0))
    result.update(actual_call=stat(CALL),actual_Popen_wait_exit=rc,actual_Win32_exit=code.value if got else None);need(got and rc==code.value==0 and observation_error is None,'Actual component failed; preserve first output/log, no retry')
    d=read(OUT/'completion.json');expected=dict(stage='upl_wall_retire_cpu_r1',passed=True,retired_native_begin=1800,retired_native_count=260,active_native_count=6800,remaining_fixed=1800,preserved_soil_IDs=5000,remaining_wall_rows=1800,retired_boundary_candidates=0,original_case_ID_registry_unchanged=True,persistent_member_bits_not_struct_padding_compared=True,physical_steps=0,production_release_event_tested=False,physical_acceptance=False)
    need(all(d[k]==v for k,v in expected.items()) and d['positive_projection_rows']>0 and d['new_surface_positive_projection_rows']>0 and d['active_remaining_wall_closures']>0 and d['actual_boundary_cell_candidates']>0,'Actual completed component coverage differs')
    files=[]
    for leaf,columns,ids in (('retired.csv',9,set(range(1800,2060))),('soil.csv',17,set(range(2060,7060))),('walls.csv',17,set(range(1800)))):
        path=OUT/leaf
        with path.open(encoding='utf-8',newline='') as f:r=csv.DictReader(f);need(len(r.fieldnames)==columns,'Actual CSV width differs: '+leaf);rows=list(r)
        need(len(rows)==len(ids) and {int(q['native_id']) for q in rows}==ids and all(None not in q and None not in q.values() for q in rows),'Actual native CSV membership/width differs: '+leaf);files.append(stat(path))
    need(all(stat(e['path'])==e for e in before),'Consumed helper/input/runtime SMT changed')
    result.update(passed=True,source_build=stat(BUILD),native_completion=stat(OUT/'completion.json'),actual_completion=d,files=files,consumed_stats=before,consumed_stats_unchanged=True)
except Exception as e:result.update(first_failure=str(e),consumed_stats=before)
save(CHECK,result);print(json.dumps(dict(passed=result['passed'],check=str(CHECK),component_invocations=result['component_invocations'],first_failure=result.get('first_failure'))),flush=True)
raise SystemExit(0 if result['passed'] else 1)
