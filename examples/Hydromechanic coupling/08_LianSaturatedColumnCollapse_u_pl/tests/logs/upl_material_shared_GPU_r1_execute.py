import csv,ctypes,datetime,json,os,subprocess,time,traceback
from ctypes import wintypes as w
from pathlib import Path
import psutil
T=Path(__file__).resolve().parents[1];S=T.parents[3]/'src';L=T/'logs';TAG='upl_material_shared_GPU_r1'
STAGE=T/'outputs'/TAG;CHECK=L/(TAG+'.check.json');INPUTS={};CALLS=[]
def need(b,s):
    if not b:raise RuntimeError(s)
def read(p):return json.loads(Path(p).read_text())
def save(p,j):
    with Path(p).open('x',encoding='utf-8') as f:json.dump(j,f,indent=2)
def stat(p):
    p=Path(p).resolve();a=p.stat();return dict(path=str(p),bytes=a.st_size,mtime_ns=a.st_mtime_ns)
def bind(p,expected=None):
    a=stat(p);INPUTS[a['path']]=a
    if expected:need(a==expected,'Closed source/input stat mismatch: '+str(p))
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
k=ctypes.WinDLL('kernel32',use_last_error=True)
k.GetProcessTimes.argtypes=[w.HANDLE,*([ctypes.POINTER(w.FILETIME)]*4)];k.GetExitCodeProcess.argtypes=[w.HANDLE,ctypes.POINTER(w.DWORD)]
k.QueryFullProcessImageNameW.argtypes=[w.HANDLE,w.DWORD,w.LPWSTR,ctypes.POINTER(w.DWORD)]
k.OpenProcess.argtypes=[w.DWORD,w.BOOL,w.DWORD];k.OpenProcess.restype=w.HANDLE;k.CloseHandle.argtypes=[w.HANDLE]
def identity(h,pid):
    a=[w.FILETIME() for _ in range(4)];need(k.GetProcessTimes(h,*[ctypes.byref(v) for v in a]),'Process time unavailable')
    n=w.DWORD(32768);image=ctypes.create_unicode_buffer(n.value);need(k.QueryFullProcessImageNameW(h,0,image,ctypes.byref(n)),'Process image unavailable')
    try:argv=psutil.Process(pid).cmdline()
    except psutil.NoSuchProcess:argv=None
    return dict(pid=pid,creation_epoch=((a[0].dwHighDateTime<<32)|a[0].dwLowDateTime)/1e7-11644473600,exe=image.value,argv=argv)
def invoke(label,argv,env,target=None):
    console=L/(TAG+'.'+label+'.console.log');record=L/(TAG+'.'+label+'.call.json');handle=None
    need(not console.exists() and not record.exists(),'Call collision');r=dict(stage=TAG+'.'+label,arguments=argv,owner=dict(pid=os.getpid(),creation_epoch=psutil.Process().create_time()),cwd=str(STAGE),started_utc=utc(),SHA_scans=0)
    try:
        with console.open('xb') as f:
            p=subprocess.Popen(argv,cwd=STAGE,env=env,stdout=f,stderr=subprocess.STDOUT);r['tool']=identity(int(p._handle),p.pid)
            if target:
                while p.poll() is None:
                    if handle is None:
                        try:children=psutil.Process(p.pid).children(recursive=True)
                        except psutil.NoSuchProcess:children=[]
                        for q in children:
                            try:
                                if q.name().lower()!=target.name.lower():continue
                                h=k.OpenProcess(0x1000|0x100000,False,q.pid)
                                if not h:continue
                                d=identity(h,q.pid)
                                if not Path(d['exe']).samefile(target):k.CloseHandle(h);continue
                                handle=h;r['target']=d;break
                            except psutil.NoSuchProcess:continue
                    time.sleep(.005)
            rc=p.wait();actual=w.DWORD();need(k.GetExitCodeProcess(int(p._handle),ctypes.byref(actual)),'Tool exit unavailable')
            r.update(actual_Popen_wait_exit=rc,actual_tool_Win32_exit=actual.value,ended_utc=utc(),console_log=stat(console))
            if handle:
                c=w.DWORD();need(k.GetExitCodeProcess(handle,ctypes.byref(c)),'Target exit unavailable');r['actual_target_Win32_exit']=c.value
            save(record,r);CALLS.append(stat(record))
        need(Path(r['tool']['exe']).samefile(argv[0]) and rc==actual.value==0,'Actual '+label+' failed; preserve '+str(console))
        if target:need(handle is not None and r['actual_target_Win32_exit']==0,'Target retained-handle exit missing/nonzero')
    finally:
        if handle:k.CloseHandle(handle)
try:
    need(not STAGE.exists() and not CHECK.exists(),'Fresh stage/check required')
    cpuCheck=T/'logs/upl_material_shared_CPU_r1.check.json';cpu=read(cpuCheck);need(cpu['passed'],'CPU prerequisite failed');bind(cpuCheck)
    source=T/'support/upl_material_shared_gpu_r1.cu';note=T/'notes/upl_material_shared_gpu_r1.json';original=Path(cpu['source_reference']['path']);cpuCSV=Path(cpu['CSV']['path'])
    for p in (source,note,T/'support/upl_material_shared_candidate_r1.h',T/'support/upl_material_shared_cases_r1.h'):bind(p)
    for entry in (cpu['source_reference'],cpu['CSV'],cpu['completion']):bind(entry['path'],entry)
    for entry in cpu['source_inputs']:
        if Path(entry['path']).name in ('upl_material_shared_candidate_r1.h','upl_material_shared_cases_r1.h'):need(stat(entry['path'])==entry,'Shared CPU/GPU header differs')
    need(not any((p.info['name'] or '').lower()=='upl_material_shared_gpu_r1.exe' for p in psutil.process_iter(['name'])),'Duplicate material target active')
    STAGE.mkdir();temp=Path(os.environ['LOCALAPPDATA'])/'Temp/upl_material_gpu_r1';need(not temp.exists(),'Fresh compile temp required');temp.mkdir()
    cuda=Path('C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v11.7');nvcc=cuda/'bin/nvcc.exe';san=cuda/'compute-sanitizer/compute-sanitizer.exe'
    compiler=Path('D:/Program Files/VS2022/VC/Tools/MSVC/14.36.32532/bin/Hostx64/x64');exe=STAGE/'upl_material_shared_gpu_r1.exe';result=STAGE/'result'
    cmd=Path(os.environ['SystemRoot'])/'System32/cmd.exe';dev=Path('D:/Program Files/VS2022/Common7/Tools/VsDevCmd.bat')
    setup=subprocess.run('"'+str(cmd)+'" /d /c call "'+str(dev)+'" -arch=x64 -host_arch=x64 >nul && set',capture_output=True);need(setup.returncode==0,'VS environment setup failed')
    env=dict(os.environ);env.update(x.split('=',1) for x in setup.stdout.decode('mbcs').splitlines() if '=' in x and not x.startswith('='))
    flags=[str(nvcc),'-gencode=arch=compute_86,code=[sm_86,compute_86]','--use-local-env','-ccbin',str(compiler),'-x','cu','-std=c++17','-G','-g','-use_fast_math','--machine','64','-cudart','static','-maxrregcount=0','-D_WITHGPU','-DWIN32','-D_CONSOLE','-D_MBCS','-Xcompiler','/EHsc,/W3,/Od,/MTd,/Zi,/RTC1,/wd4267,/Fd'+str(temp/'compile.pdb'),'-Xlinker','/DEBUG,/PDB:'+str(temp/'link.pdb'),'-o',str(exe),str(source)]
    invoke('nvcc_compile_link',flags,env);save(L/(TAG+'.build.json'),dict(passed=True,program=stat(exe),compiler_argv=flags,source_inputs=list(INPUTS.values()),engine_objects=0,SHA_scans=0))
    mem=L/(TAG+'.memcheck.sanitizer.log');need(not mem.exists(),'Fresh sanitizer log required')
    invoke('memcheck',[str(san),'--tool','memcheck','--leak-check','full','--target-processes','all','--error-exitcode','86','--log-file',str(mem),str(exe),'--source',str(original),'--cpu',str(cpuCSV),'--out',str(result)],env,exe)
    log=mem.read_text();need('ERROR SUMMARY: 0 errors' in log and 'LEAK SUMMARY: 0 bytes leaked in 0 allocations' in log,'Sanitizer summaries missing/errors/leaks')
    done=read(result/'completion.json');need(done['passed'] and done['rows']==71 and done['kernel_launches']==1 and done['tail_results_member_checks']==2,'Material completion incomplete')
    rows=list(csv.DictReader((result/'points.csv').open(newline='')));parity=list(csv.DictReader((result/'CPU_GPU.csv').open(newline='')))
    need(len(rows)==len(parity)==71 and all(r['input_bits_equal']=='1' for r in parity),'Actual CPU/GPU comparison incomplete')
    failed=[r for r in rows if r['status'] in ('Invalid','ApexNeeded')];need(len(failed)==17 and all(r['result_state_bits']==':'.join(r['input_bits'].split(':')[:7]) for r in failed),'Failure state scalar bits not preserved')
    changed=[p for p,e in INPUTS.items() if stat(p)!=e];need(not changed,'Consumed source/input changed: '+str(changed))
    save(CHECK,dict(stage=TAG,passed=True,source_inputs=list(INPUTS.values()),consumed_stats_unchanged=True,completion=done,calls=CALLS,memcheck=stat(mem),points=stat(result/'points.csv'),CPU_GPU=stat(result/'CPU_GPU.csv'),failed_states_bit_checks=len(failed),SHA_scans=0,engine_objects=0,physical_solver_or_native_decoder=0,physical_acceptance=False));print(json.dumps(dict(passed=True,completion=done,failed_states_bit_checks=len(failed))),flush=True)
except BaseException as e:
    if not CHECK.exists():save(CHECK,dict(stage=TAG,passed=False,first_failure=str(e),traceback=traceback.format_exc(),calls=CALLS,source_inputs=list(INPUTS.values()),SHA_scans=0,physical_acceptance=False))
    print(traceback.format_exc(),flush=True);raise
