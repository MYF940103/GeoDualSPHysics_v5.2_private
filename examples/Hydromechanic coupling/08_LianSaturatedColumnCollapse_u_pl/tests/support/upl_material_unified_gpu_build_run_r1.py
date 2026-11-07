"""One fresh standalone CUDA Debug build + one memcheck; no engine/solver execution."""
import argparse,ctypes,datetime,json,os,subprocess,time,traceback
from ctypes import wintypes as w
from pathlib import Path
import psutil
T=Path(__file__).resolve().parents[1];R=T.parents[3];L=T/'logs';TAG='upl_material_unified_GPU_r1'
STAGE=T/'outputs'/TAG;CHECK=L/(TAG+'.check.json');CALLS=[]

def need(b,s):
    if not b:raise RuntimeError(s)
def stat(p):
    p=Path(p).resolve();s=p.stat();return dict(path=str(p),bytes=s.st_size,mtime_ns=s.st_mtime_ns)
def save(p,j):
    with Path(p).open('x',encoding='utf-8') as f:json.dump(j,f,indent=2,allow_nan=False);f.write('\n')
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
K=ctypes.WinDLL('kernel32',use_last_error=True)
K.GetProcessTimes.argtypes=[w.HANDLE,*([ctypes.POINTER(w.FILETIME)]*4)]
K.GetExitCodeProcess.argtypes=[w.HANDLE,ctypes.POINTER(w.DWORD)]
K.QueryFullProcessImageNameW.argtypes=[w.HANDLE,w.DWORD,w.LPWSTR,ctypes.POINTER(w.DWORD)]
K.OpenProcess.argtypes=[w.DWORD,w.BOOL,w.DWORD];K.OpenProcess.restype=w.HANDLE;K.CloseHandle.argtypes=[w.HANDLE]

def identity(handle,pid):
    ft=[w.FILETIME() for _ in range(4)];need(K.GetProcessTimes(handle,*[ctypes.byref(x) for x in ft]),'Process creation time missing')
    size=w.DWORD(32768);image=ctypes.create_unicode_buffer(size.value);need(K.QueryFullProcessImageNameW(handle,0,image,ctypes.byref(size)),'Actual process image missing')
    try:argv=psutil.Process(pid).cmdline()
    except psutil.NoSuchProcess:argv=None
    return dict(pid=pid,created_win32_100ns=(ft[0].dwHighDateTime<<32)|ft[0].dwLowDateTime,exe=image.value,argv=argv)

def invoke(phase,argv,env,target=None):
    log=L/f'{TAG}.{phase}.log';receipt=L/f'{TAG}.{phase}.call.json';handle=None
    need(not log.exists() and not receipt.exists(),'Existing call evidence protected')
    d=dict(stage=TAG+'.'+phase,argv=argv,cwd=str(STAGE),owner_pid=os.getpid(),owner_created=psutil.Process().create_time(),started_utc=utc());clock=time.monotonic()
    try:
        with log.open('xb') as f:
            p=subprocess.Popen(argv,executable=argv[0],cwd=STAGE,env=env,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
            d['tool']=identity(int(p._handle),p.pid)
            if target:
                while p.poll() is None:
                    if handle is None:
                        try:children=psutil.Process(p.pid).children(recursive=True)
                        except psutil.NoSuchProcess:children=[]
                        for child in children:
                            try:
                                if child.name().lower()!=target.name.lower():continue
                                h=K.OpenProcess(0x1000|0x100000,False,child.pid)
                                if not h:continue
                                found=identity(h,child.pid)
                                if not Path(found['exe']).samefile(target):K.CloseHandle(h);continue
                                handle=h;d['target']=found;break
                            except psutil.NoSuchProcess:continue
                    time.sleep(.005)
            code=p.wait();actual=w.DWORD();need(K.GetExitCodeProcess(int(p._handle),ctypes.byref(actual)),'Actual tool exit missing')
            d.update(actual_Popen_wait_exit=code,actual_tool_Win32_exit=actual.value,elapsed_s=time.monotonic()-clock,ended_utc=utc(),log=stat(log))
            if handle:
                child_code=w.DWORD();need(K.GetExitCodeProcess(handle,ctypes.byref(child_code)),'Actual target exit missing');d['actual_target_Win32_exit']=child_code.value
            save(receipt,d);CALLS.append(stat(receipt))
        need(Path(d['tool']['exe']).samefile(argv[0]) and code==actual.value==0,phase+' failed; preserve first evidence')
        if target:need(handle is not None and d['actual_target_Win32_exit']==0,'Target handle exit missing/nonzero')
    finally:
        if handle:K.CloseHandle(handle)

def main():
    a=argparse.ArgumentParser();a.add_argument('--execution-authorized',action='store_true');args=a.parse_args();need(args.execution_authorized,'Execution flag required after root review')
    consumed=[];summary=dict(stage=TAG,passed=False,SHA_scans=0,engine_objects=0,spatial_solver_invocations=0,production_changed=False,physical_acceptance=False)
    try:
        need(not STAGE.exists() and not CHECK.exists(),'Fresh build/result/check required; no automatic retry')
        cpucheck=T/'logs/upl_material_unified_r1.check.json';cpu=read(cpucheck);need(cpu['passed'] and cpu['completion']['passed'] and cpu['completion']['point_count']==109,'Closed CPU unified component prerequisite required')
        src=T/'support/upl_material_unified_gpu_probe_r1.cu';header=T/'support/upl_material_unified_candidate_r1.h';bound=next(e for e in cpu['consumed'] if Path(e['path']).samefile(header));need(stat(header)==bound,'Current candidate differs from completed CPU candidate')
        consumed=[stat(p) for p in (Path(__file__),src,header,cpucheck,R/'src/source/DualSphDef.h',R/'src/source/TypesDef.h')]
        need(not any((p.info['name'] or '').lower()=='upl_material_unified_gpu_probe_r1.exe' for p in psutil.process_iter(['name'])),'Same material target is active')
        STAGE.mkdir();temp=Path(os.environ['LOCALAPPDATA'])/'Temp/upl_material_unified_gpu_r1';need(not temp.exists(),'Fresh compile temp required');temp.mkdir()
        cuda=Path('C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v11.7');nvcc=cuda/'bin/nvcc.exe';san=cuda/'compute-sanitizer/compute-sanitizer.exe'
        setup=subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',capture_output=True)
        need(setup.returncode==0,'Authoritative MSVC setup failed');env=dict(os.environ);env.update(x.split('=',1) for x in setup.stdout.decode('mbcs').splitlines() if '=' in x and not x.startswith('='));need(env['VCTOOLSVERSION']=='14.36.32532','MSVC14.36 required')
        compiler=Path(env['VCToolsInstallDir'])/'bin/Hostx64/x64';exe=STAGE/'upl_material_unified_gpu_probe_r1.exe';out=STAGE/'result'
        flags=[str(nvcc),'-gencode=arch=compute_86,code=[sm_86,compute_86]','--use-local-env','-ccbin',str(compiler),'-x','cu','-std=c++17','-G','-g','-use_fast_math','--machine','64','-cudart','static','-maxrregcount=0','-D_WITHGPU','-DWIN32','-D_CONSOLE','-D_MBCS','-I'+str(R/'src/source'),'-I'+str(T/'support'),'-Xcompiler','/EHsc,/W3,/Od,/MTd,/Zi,/RTC1,/wd4267,/Fd'+str(temp/'compile.pdb'),'-Xlinker','/DEBUG,/PDB:'+str(temp/'link.pdb'),'-o',str(exe),str(src)]
        invoke('nvcc_compile_link',flags,env)
        save(L/(TAG+'.build.json'),dict(passed=True,program=stat(exe),compiler=stat(nvcc),compiler_argv=flags,consumed=consumed,calls=CALLS.copy(),engine_objects=0,cudart='static',MSVC_CRT='MTd static',copied_runtime_DLLs=[],SHA_scans=0))
        sanlog=L/(TAG+'.memcheck.sanitizer.log');need(not sanlog.exists(),'Existing sanitizer evidence protected')
        invoke('memcheck',[str(san),'--tool','memcheck','--leak-check','full','--target-processes','all','--error-exitcode','86','--log-file',str(sanlog),str(exe),'--out',str(out)],env,exe)
        text=sanlog.read_text();need('ERROR SUMMARY: 0 errors' in text and 'LEAK SUMMARY: 0 bytes leaked in 0 allocations' in text,'Sanitizer errors/leaks or missing final summaries')
        done=read(out/'completion.json');need(done['passed'] and done['points']==69 and done['kernel_launches']==1 and done['failed_state_bit_checks']==7 and done['same_device_constant_entry_checks']==24 and done['rotated_points']==20 and done['input_points_scalar_checks']==71 and done['output_tail_defined_member_checks']==2,'Declared material coverage incomplete')
        need(all(stat(e['path'])==e for e in consumed),'Consumed source/reference SMT changed')
        summary.update(passed=True,completion=done,consumed=consumed,consumed_stats_unchanged=True,calls=CALLS,memcheck_zero_errors_and_leaks=True,memcheck=stat(sanlog),outputs=[stat(p) for p in sorted(out.iterdir())])
    except Exception as e:summary.update(first_failure=str(e),traceback=traceback.format_exc(),calls=CALLS,consumed=consumed)
    save(CHECK,summary);print(json.dumps(summary,indent=2));return 0 if summary['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
