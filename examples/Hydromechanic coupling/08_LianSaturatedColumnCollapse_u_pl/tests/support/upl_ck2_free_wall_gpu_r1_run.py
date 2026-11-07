"""One owned GPU zero-step Ck2 composition under memcheck. No solver, decoder, retry or queue."""
import csv,ctypes,datetime,json,os,re,subprocess,time
from ctypes import wintypes as w
from pathlib import Path
import psutil
T=Path(__file__).resolve().parents[1];L=T/'logs';TAG='upl_ck2_free_wall_GPU_r1';OUT=T/'outputs'/TAG
BUILD=L/'upl_ck2_free_wall_gpu_r1.build.json';SEED=T/'outputs/upl_c08_observer_r1_seed/CaseLianSaturatedColumnCollapse_geometry_r1'
SAN=Path('C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v11.7/compute-sanitizer/compute-sanitizer.exe')
CALL=L/(TAG+'.call.json');CHECK=L/(TAG+'.check.json');START=L/(TAG+'.start.json');LOG=L/(TAG+'.log');SANLOG=L/(TAG+'.sanitizer.log')
def need(b,s):
    if not b:raise RuntimeError(s)
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def stat(p):
    p=Path(p).resolve();s=p.stat();return dict(path=str(p),bytes=s.st_size,mtime_ns=s.st_mtime_ns)
def save(p,d):
    with Path(p).open('x',encoding='utf-8') as f:json.dump(d,f,indent=2);f.write('\n')
def bind(e):
    a=stat(e['path']);need((a['bytes'],a['mtime_ns'])==(e['bytes'],e['mtime_ns']),'Closed helper binding changed: '+e['path']);return a
K=ctypes.WinDLL('kernel32',use_last_error=True)
K.OpenProcess.argtypes=[w.DWORD,w.BOOL,w.DWORD];K.OpenProcess.restype=w.HANDLE;K.CloseHandle.argtypes=[w.HANDLE]
K.GetExitCodeProcess.argtypes=[w.HANDLE,ctypes.POINTER(w.DWORD)];K.GetExitCodeProcess.restype=w.BOOL
K.GetProcessTimes.argtypes=[w.HANDLE,*([ctypes.POINTER(w.FILETIME)]*4)];K.GetProcessTimes.restype=w.BOOL
K.QueryFullProcessImageNameW.argtypes=[w.HANDLE,w.DWORD,w.LPWSTR,ctypes.POINTER(w.DWORD)];K.QueryFullProcessImageNameW.restype=w.BOOL
def identity(handle,pid):
    ft=[w.FILETIME() for _ in range(4)];need(K.GetProcessTimes(handle,*[ctypes.byref(x) for x in ft]),'Actual native creation times absent');n=w.DWORD(32768);exe=ctypes.create_unicode_buffer(n.value);need(K.QueryFullProcessImageNameW(handle,0,exe,ctypes.byref(n)),'Actual process image absent')
    try:q=psutil.Process(pid);argv=q.cmdline();ppid=q.ppid()
    except psutil.NoSuchProcess:argv=None;ppid=None
    return dict(pid=pid,creation_filetime_100ns=(ft[0].dwHighDateTime<<32)|ft[0].dwLowDateTime,exe=exe.value,argv=argv,parent_pid=ppid)
need(not any(p.exists() for p in (OUT,CALL,CHECK,START,LOG,SANLOG)),'Existing GPU component result/receipt protected')
result=dict(stage=TAG,passed=False,physical_steps=0,solver_invocations=0,component_invocations=0,physical_acceptance=False,SHA_scans=0);before=[];handle=None
try:
    b=read(BUILD);need(b['passed'] and b['consumed_stats_unchanged'] and len(b['objects'])==110 and b['actual_link_object_inputs']==111,'Closed current GPU helper build required')
    before=[stat(BUILD),bind(b['program']),bind(b['source']),bind(b['source_build']),*[bind(e) for e in b['runtime']],stat(__file__),stat(T/'notes/upl_ck2_free_wall_gpu_r1.json'),stat(SAN)]
    before += [stat(str(SEED)+suffix) for suffix in ('.xml','.bi4','_Normals.nbi4')]
    exe=Path(b['program']['path']);need(exe.samefile(T/'outputs/upl_ck2_free_wall_gpu_build_r1/upl_ck2_free_wall_gpu_r1.exe'),'Unexpected GPU helper executable')
    need(not any((q.info['name'] or '').lower()==exe.name.lower() for q in psutil.process_iter(['name'])),'A matching GPU Ck2 component is already active')
    cpucheck=T/'logs/upl_ck2_free_wall_CPU_r1.check.json';cpu=read(cpucheck);need(cpu['passed'] and cpu['consumed_stats_unchanged'],'Closed CPU independent reference required');before += [stat(cpucheck),bind(cpu['native_completion']),*[bind(e) for e in cpu['files']]]
    reference=T/'outputs/upl_ck2_free_wall_CPU_r1'
    target_argv=[str(exe),'--check','--cpu-reference',str(reference),'-gpu:0','-stable','-mdbc_freeslip',str(SEED),str(OUT)]
    argv=[str(SAN),'--tool','memcheck','--leak-check','full','--target-processes','all','--error-exitcode','86','--log-file',str(SANLOG),*target_argv]
    owner=psutil.Process();owner_id=dict(pid=owner.pid,created_epoch=owner.create_time(),exe=owner.exe(),argv=owner.cmdline());started=datetime.datetime.now(datetime.timezone.utc).isoformat();wall=time.monotonic();observation_error=None;target=None;tool=None
    with LOG.open('xb') as stream:
        p=subprocess.Popen(argv,cwd=T.parent,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW);result['component_invocations']=1
        try:tool=identity(int(p._handle),p.pid);need(Path(tool['exe']).samefile(SAN) and tool['argv'][1:]==argv[1:],'Actual memcheck tool identity differs')
        except Exception as e:observation_error=str(e)
        try:save(START,dict(stage=TAG+'.start',owner=owner_id,tool=tool,target_argv=target_argv,cwd=str(T.parent),source_build=stat(BUILD),consumed_stats=before,physical_steps=0))
        except Exception as e:observation_error=observation_error or str(e)
        print(json.dumps(dict(actual_memcheck_PID=p.pid,target_pending=True)),flush=True)
        while p.poll() is None:
            if handle is None:
                try:children=psutil.Process(p.pid).children(recursive=True)
                except psutil.NoSuchProcess:children=[]
                for q in children:
                    candidate=None
                    try:
                        if q.name().lower()!=exe.name.lower():continue
                        candidate=K.OpenProcess(0x101000,False,q.pid)
                        if not candidate:continue
                        item=identity(candidate,q.pid)
                        if not Path(item['exe']).samefile(exe):K.CloseHandle(candidate);candidate=None;continue
                        handle=candidate;candidate=None;target=item
                        need(item['argv'][1:]==target_argv[1:] and tool is not None and item['creation_filetime_100ns']>=tool['creation_filetime_100ns'],'Actual owned target creation/argv differs');print(json.dumps(dict(actual_target=item)),flush=True);break
                    except psutil.NoSuchProcess:
                        if candidate:K.CloseHandle(candidate)
                    except Exception as e:
                        if candidate:K.CloseHandle(candidate)
                        observation_error=observation_error or str(e)
            time.sleep(.005)
        rc=p.wait();toolcode=w.DWORD();toolgot=bool(K.GetExitCodeProcess(int(p._handle),ctypes.byref(toolcode)));targetcode=w.DWORD();targetgot=bool(handle and K.GetExitCodeProcess(handle,ctypes.byref(targetcode)))
    save(CALL,dict(stage=TAG+'.call',owner=owner_id,tool=tool,actual_target=target,target_argv=target_argv,argv=argv,cwd=str(T.parent),started_utc=started,ended_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),actual_Popen_wait_exit=rc,actual_tool_Win32_exit=toolcode.value if toolgot else None,actual_target_Win32_exit=targetcode.value if targetgot else None,identity_observation_failure=observation_error,elapsed_s=time.monotonic()-wall,log=stat(LOG),physical_steps=0,component_invocations=1,solver_invocations=0,SHA_scans=0))
    result.update(actual_call=stat(CALL),actual_Popen_wait_exit=rc,actual_tool_Win32_exit=toolcode.value if toolgot else None,actual_target_Win32_exit=targetcode.value if targetgot else None)
    need(toolgot and targetgot and target is not None and rc==toolcode.value==targetcode.value==0 and observation_error is None,'Actual memcheck/component failed or ownership incomplete; retain first evidence, no retry')
    text=SANLOG.read_text(encoding='utf-8');errors=re.findall(r'ERROR SUMMARY: ([0-9,]+) errors',text);leaks=re.findall(r'LEAK SUMMARY: ([0-9,]+) bytes leaked in ([0-9,]+) allocations',text)
    need(errors and leaks and all(int(x.replace(',',''))==0 for x in errors) and all(int(x.replace(',',''))==int(y.replace(',',''))==0 for x,y in leaks),'Actual memcheck errors/leaks missing or nonzero')
    runout=(OUT/'Run.out').read_text(encoding='utf-8',errors='replace');need('Device selected: 0 "NVIDIA GeForce RTX 3050"' in runout,'Actual selected GPU is not the declared localRTX3050')
    d=read(OUT/'completion.json');expected=dict(stage='upl_ck2_free_wall_gpu_r1',passed=True,native_IDs=7060,soil=5000,fixed=2060,fields=2,rate_rows=162,wall_rows=820,mask_rows=10000,FS_counts=[100,100],true_inner_counts=[4900,4900],analytic_core_rows=54,nonzero_chain_witnesses=27,positive_FS_canaries_projected=1,Ck=2,CPU_C_reference_not_independent_GPU_allpair_truth=True,FSNormal_bits_cross_backend_required=False,physical_steps=0,actual_momentum_called=False,public_scope_admitted=False,Eq25_conservative_flux_proven=False,physical_acceptance=False)
    need(all(d[k]==v for k,v in expected.items()) and all(d[k]<=1 for k in ('max_rate_over_original_CPU_reference_budget','max_static_selected_rate_over_original_budget','max_wall_over_original_CPU_condition_budget')) and d['minimum_chain_signal_over_original_budget']>1 and len(d['conductivity_gradient_speed'])==2 and all(x>0 for x in d['conductivity_gradient_speed']),'Actual GPU Ck2 component coverage or original budgets differ')
    files=[]
    for leaf,columns,count in (('rates.csv',15,162),('walls.csv',14,820),('mask.csv',8,10000),('projection.csv',5,3)):
        path=OUT/leaf
        with path.open(encoding='utf-8',newline='') as f:r=csv.DictReader(f);need(len(r.fieldnames)==columns,'Actual CSV width differs: '+leaf);rows=list(r)
        need(len(rows)==count and all(None not in q and None not in q.values() for q in rows),'Actual GPU CSV row/width differs: '+leaf)
        if leaf!='projection.csv':
            need({int(q['field']) for q in rows}=={0,1},'Both GPU manufactured fields required')
            for field in (0,1):
                group=[q for q in rows if int(q['field'])==field];ids={int(q['native_id']) for q in group};need(len(ids)==len(group),'Duplicate GPU field native ID')
                if leaf=='mask.csv':need(ids==set(range(2060,7060)),'All5000 actual GPU soil IDs required')
                elif leaf=='rates.csv':need(len(ids)==81 and ids<=set(range(2060,7060)) and sum(int(q['true_core']) for q in group)==27,'Actual GPU receiver/core scope differs')
                else:need(len(ids)==410 and ids<=set(range(2060)),'Actual GPU wall IDs differ')
        else:need({float(q['input_p']) for q in rows}=={16.,0.,-16.} and all(float(q['actual_p'])==(0. if float(q['input_p'])>0 else float(q['input_p'])) for q in rows),'GPU positive-only free projection differs')
        files.append(stat(path))
    need(all(stat(e['path'])==e for e in before),'Consumed GPU helper/input/runtime SMT changed')
    result.update(passed=True,source_build=stat(BUILD),native_completion=stat(OUT/'completion.json'),actual_completion=d,files=files,sanitizer_log=stat(SANLOG),actual_selected_GPU='NVIDIA GeForce RTX 3050',memcheck_zero_errors_and_leaks=True,consumed_stats=before,consumed_stats_unchanged=True)
except Exception as e:result.update(first_failure=str(e),consumed_stats=before)
finally:
    if handle:K.CloseHandle(handle)
save(CHECK,result);print(json.dumps(dict(passed=result['passed'],check=str(CHECK),component_invocations=result['component_invocations'],first_failure=result.get('first_failure'))),flush=True)
raise SystemExit(0 if result['passed'] else 1)
