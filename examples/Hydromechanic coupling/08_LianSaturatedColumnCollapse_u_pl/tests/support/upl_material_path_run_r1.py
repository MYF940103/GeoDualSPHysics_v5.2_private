"""Compile/link and execute one CPU material-only path probe. No spatial solver."""
import ctypes,datetime,json,os,shutil,subprocess,time,traceback
from ctypes import wintypes as w
from pathlib import Path
T=Path(__file__).resolve().parents[1];R=T.parents[3];L=T/'logs'
TAG='upl_material_path_r1';HELP=T/'outputs/upl_material_path_CPU_r1';OUT=T/'outputs'/TAG
CHECK=L/f'{TAG}.check.json'

def need(b,s):
    if not b:raise RuntimeError(s)

def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))

def save(p,d):
    with Path(p).open('x',encoding='utf-8') as f:json.dump(d,f,indent=2,allow_nan=False);f.write('\n')

def stat(p):
    p=Path(p).resolve();s=p.stat();return dict(path=str(p),bytes=s.st_size,mtime_ns=s.st_mtime_ns)

K=ctypes.WinDLL('kernel32',use_last_error=True)
K.GetExitCodeProcess.argtypes=[w.HANDLE,ctypes.POINTER(w.DWORD)]
K.GetProcessTimes.argtypes=[w.HANDLE,*([ctypes.POINTER(w.FILETIME)]*4)]

def invoke(phase,argv,env):
    log=L/f'{TAG}.{phase}.log';receipt=L/f'{TAG}.{phase}.call.json'
    need(not log.exists() and not receipt.exists(),'Existing tool/target evidence protected')
    started=datetime.datetime.now(datetime.timezone.utc).isoformat();clock=time.monotonic()
    with log.open('xb') as f:
        p=subprocess.Popen(argv,executable=argv[0],shell=False,env=env,cwd=R/'src',stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        ft=[w.FILETIME() for _ in range(4)];created=bool(K.GetProcessTimes(int(p._handle),*[ctypes.byref(x) for x in ft]))
        rc=p.wait();code=w.DWORD();captured=bool(K.GetExitCodeProcess(int(p._handle),ctypes.byref(code)))
    d=dict(program=stat(argv[0]),argv=argv,pid=p.pid,creation_time_win32_100ns=(ft[0].dwHighDateTime<<32)|ft[0].dwLowDateTime if created else None,actual_wait_exit=rc,actual_Win32_exit=code.value if captured else None,started_utc=started,elapsed_s=time.monotonic()-clock,log=stat(log))
    save(receipt,d);calls.append(stat(receipt));need(created and captured and rc==code.value==0,f'{phase} failed; retain actual log and exit')
    return d

calls=[];consumed=[];result=dict(stage=TAG,passed=False,spatial_solver_invocations=0,SHA_scans=0,production_changed=False,physical_acceptance=False)
try:
    need(not CHECK.exists() and not HELP.exists() and not (OUT/'native.csv').exists(),'Fresh material probe required; never rerun old evidence')
    bp=L/'upl_material_3d_probe_r2.build.json';b=read(bp)
    need(b['passed'] and b['consumed_stats_unchanged'],'Closed CPU object fixture required')
    for e in b['objects']:need(stat(e['path'])==e,'Frozen CPU object identity changed')
    source=T/'support/upl_material_path_probe_r1.cpp'
    paths=[bp,source,T/'support/upl_material_general_candidate_r1.h',T/'notes/upl_material_path_r1.json',OUT/'input.csv',OUT/'prepared.json',R/'src/source/FunSoilMaterial.h',R/'src/source/JSphCpu.cpp',R/'src/source/JSph.cpp',T.parent/'support/LianCollapse_upl_win64_r2.zip',Path(__file__)]
    consumed=[stat(p) for p in paths]
    oldc=read(L/'upl_material_3d_probe_r2.compile.call.json');oldl=read(L/'upl_material_3d_probe_r2.link.call.json')
    oldroot=str(T/'outputs/upl_material_3d_CPU_helper_r2');exe=HELP/'upl_material_path_r1.exe'
    ca=[x.replace(oldroot,str(HELP)).replace('upl_material_3d_probe_r2.cpp',source.name) for x in oldc['arguments']]
    la=[x.replace(oldroot,str(HELP)).replace('upl_material_3d_probe_r2.exe',exe.name) for x in oldl['arguments']]
    setup=subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    need(setup.returncode==0,'MSVC setup failed');env=dict(os.environ);env.update(x.split('=',1) for x in setup.stdout.decode('mbcs').splitlines() if '=' in x and not x.startswith('='))
    need(env['VCTOOLSVERSION']=='14.36.32532','Authoritative MSVC14.36 fixture required')
    HELP.mkdir();invoke('compile',[oldc['program'],*ca],env);invoke('link',[oldl['program'],*la],env)
    for e in b['runtime']:
        need(stat(e['path'])==e,'Frozen runtime identity changed');shutil.copy2(e['path'],HELP/Path(e['path']).name)
    build=dict(stage=TAG+'.build',passed=True,program=stat(exe),source=stat(source),fixture=stat(bp),calls=calls.copy(),consumed=consumed,SHA_scans=0,production_changed=False)
    save(L/f'{TAG}.build.json',build)
    call=invoke('run',[str(exe),'--input',str(OUT/'input.csv'),'--out',str(OUT/'native.csv')],env)
    completion=read(OUT/'native.completion.json')
    need(completion['passed'] and completion['rows']==22680,'Material path completion/check failed')
    need(all(stat(e['path'])==e for e in consumed),'Consumed input/source/package changed during probe')
    result.update(passed=True,actual_completion=completion,build=stat(L/f'{TAG}.build.json'),outputs=[stat(OUT/'native.csv'),stat(OUT/'native.completion.json')],consumed_stats_unchanged=True,consumed=consumed,calls=calls,elapsed_material_program_s=call['elapsed_s'])
except Exception as e:
    result.update(first_failure=str(e),traceback=traceback.format_exc(),calls=calls)
save(CHECK,result);print(json.dumps(result,indent=2));raise SystemExit(0 if result['passed'] else 1)
