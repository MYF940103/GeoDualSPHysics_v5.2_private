"""Standalone CPU Debug material-only checks, no project or solver build."""
import ctypes,datetime,json,os,subprocess,time,traceback
from ctypes import wintypes as w
from pathlib import Path
T=Path(__file__).resolve().parents[1];R=T.parents[3];L=T/'logs';TAG='upl_material_unified_r1'
BUILD=T/'outputs/upl_material_unified_CPU_r1';OUT=T/'outputs/upl_material_unified_result_r1'
CHECK=L/f'{TAG}.check.json'

def need(b,s):
    if not b:raise RuntimeError(s)

def stat(p):
    p=Path(p).resolve();s=p.stat();return dict(path=str(p),bytes=s.st_size,mtime_ns=s.st_mtime_ns)

def save(p,d):
    with Path(p).open('x',encoding='utf-8') as f:json.dump(d,f,indent=2,allow_nan=False);f.write('\n')

K=ctypes.WinDLL('kernel32',use_last_error=True)
K.GetExitCodeProcess.argtypes=[w.HANDLE,ctypes.POINTER(w.DWORD)]
K.GetProcessTimes.argtypes=[w.HANDLE,*([ctypes.POINTER(w.FILETIME)]*4)]
calls=[]
def invoke(phase,argv,env):
    log=L/f'{TAG}.{phase}.log';call=L/f'{TAG}.{phase}.call.json'
    need(not log.exists() and not call.exists(),'Existing material check evidence protected')
    started=datetime.datetime.now(datetime.timezone.utc).isoformat();clock=time.monotonic()
    with log.open('xb') as f:
        p=subprocess.Popen(argv,executable=argv[0],shell=False,cwd=R/'src',env=env,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        ft=[w.FILETIME() for _ in range(4)];created=bool(K.GetProcessTimes(int(p._handle),*[ctypes.byref(x) for x in ft]));rc=p.wait();code=w.DWORD();captured=bool(K.GetExitCodeProcess(int(p._handle),ctypes.byref(code)))
    d=dict(program=stat(argv[0]),argv=argv,pid=p.pid,creation_time_win32_100ns=(ft[0].dwHighDateTime<<32)|ft[0].dwLowDateTime if created else None,actual_wait_exit=rc,actual_Win32_exit=code.value if captured else None,started_utc=started,elapsed_s=time.monotonic()-clock,log=stat(log))
    save(call,d);calls.append(stat(call));need(created and captured and rc==code.value==0,f'{phase} failed; preserve actual exit/log')

d=dict(stage=TAG,passed=False,spatial_solver_invocations=0,production_changed=False,physical_acceptance=False,SHA_scans=0)
try:
    need(not CHECK.exists() and not BUILD.exists() and not OUT.exists(),'Fresh component required; never overwrite old material tests')
    src=T/'support/upl_material_unified_probe_r1.cpp'
    files=[src,T/'support/upl_material_unified_candidate_r1.h',T/'support/upl_material_general_candidate_r1.h',T/'notes/upl_material_unified_candidate_r1.md',R/'src/source/DualSphDef.h',R/'src/source/FunSoilMaterial.h',R/'src/source/JSphCpu.cpp',T.parent/'support/LianCollapse_upl_win64_r2.zip',Path(__file__)]
    before=[stat(p) for p in files]
    setup=subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    need(setup.returncode==0,'Authoritative MSVC setup failed');env=dict(os.environ);env.update(x.split('=',1) for x in setup.stdout.decode('mbcs').splitlines() if '=' in x and not x.startswith('='))
    need(env['VCTOOLSVERSION']=='14.36.32532','MSVC14.36 fixture required')
    cl=Path(env['VCToolsInstallDir'])/'bin/Hostx64/x64/cl.exe';BUILD.mkdir();exe=BUILD/'upl_material_unified_r1.exe'
    args=[str(cl),'/nologo','/std:c++17','/EHsc','/MTd','/Od','/W3','/fp:precise','/Zi','/DWIN32','/D_CONSOLE','/D_MBCS','/I'+str(R/'src/source'),'/I'+str(T/'support'),'/Fo'+str(BUILD/'apex.obj'),'/Fd'+str(BUILD/'compile.pdb'),'/Fe'+str(exe),str(src),'/link','/INCREMENTAL:NO','/PDB:'+str(BUILD/'apex.pdb')]
    invoke('build',args,env)
    save(L/f'{TAG}.build.json',dict(passed=True,source=stat(src),program=stat(exe),compiler=stat(cl),consumed=before,calls=calls.copy(),SHA_scans=0,production_changed=False))
    invoke('run',[str(exe),'--out',str(OUT)],env)
    c=json.loads((OUT/'completion.json').read_text());need(c['passed'],'Native component checks did not pass')
    need(all(stat(e['path'])==e for e in before),'Bound material source/package changed during check')
    d.update(passed=True,completion=c,consumed=before,consumed_stats_unchanged=True,calls=calls,outputs=[stat(p) for p in sorted(OUT.iterdir())])
except Exception as e:d.update(first_failure=str(e),traceback=traceback.format_exc(),calls=calls)
save(CHECK,d);print(json.dumps(d,indent=2));raise SystemExit(0 if d['passed'] else 1)
