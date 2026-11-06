"""One40-update actual GPU Debug target under memcheck; retain real nested exits."""
import ctypes,datetime,json,os,shutil,subprocess,time
from ctypes import wintypes as w
from pathlib import Path
import psutil
T=Path(__file__).resolve().parents[1];R=T.parents[3];L=T/'logs';TAG='upl_gravity_release_smoke_GPU_r1'
OUT=T/'outputs'/TAG;RUN=T/'outputs'/(TAG+'_runtime');BP=L/'upl_gravity_release_Debug_r1.build.json'
SAN=Path('C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v11.7/compute-sanitizer/compute-sanitizer.exe')
SEED=T/'outputs/upl_gravity_release_smoke_r1_seed/CaseLianSaturatedColumnCollapse_releasesmoke_r1'
def stat(p):
    p=Path(p).resolve();s=p.stat();return dict(path=str(p),bytes=s.st_size,mtime_ns=s.st_mtime_ns)
def js(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def save(p,d):
    with Path(p).open('x',encoding='utf-8') as f:json.dump(d,f,indent=2);f.write('\n')
for p in (OUT,RUN,L/(TAG+'.start.json'),L/(TAG+'.call.json'),L/(TAG+'.check.json')):assert not p.exists(),p
for tag in ('upl_prestress_check_CPU_r1','upl_prestress_check_release_CPU_r1'):
    assert js(L/(tag+'_native_r1.check.json'))['passed']
b=js(BP);assert b['passed'];exe=Path(b['program']['path']);assert stat(exe)==b['program']
assert not any((p.info['name'] or '').lower().startswith('dualsphysics') for p in psutil.process_iter(['name']))
inputs=[stat(p) for p in (BP,exe,SAN,Path(__file__),Path(str(SEED)+'.xml'),Path(str(SEED)+'.bi4'),Path(str(SEED)+'_Normals.nbi4'))]
RUN.mkdir();shutil.copy2(exe,RUN/exe.name)
for name in ('DsphConfig.xml','ChronoEngine.dll','dsphchrono.dll','vcomp140.dll'):shutil.copy2(T/'outputs/upl_prestress_check_GPU_r1_runtime'/name,RUN/name)
target=RUN/exe.name;sanlog=L/(TAG+'.sanitizer.log');log=L/(TAG+'.console.log')
argv=[str(target),'-gpu:0','-stable','-mdbc_freeslip',str(SEED),str(OUT),'-dirdataout','data','-svres','-nsteps:40']
command=[str(SAN),'--tool','memcheck','--leak-check','full','--target-processes','all','--error-exitcode','86','--log-file',str(sanlog),*argv]
K=ctypes.WinDLL('kernel32',use_last_error=True);K.OpenProcess.argtypes=[w.DWORD,w.BOOL,w.DWORD];K.OpenProcess.restype=w.HANDLE
K.GetExitCodeProcess.argtypes=[w.HANDLE,ctypes.POINTER(w.DWORD)];K.CloseHandle.argtypes=[w.HANDLE]
K.GetProcessTimes.argtypes=[w.HANDLE,ctypes.POINTER(w.FILETIME),ctypes.POINTER(w.FILETIME),ctypes.POINTER(w.FILETIME),ctypes.POINTER(w.FILETIME)]
handle=None;identity=None;wall=time.monotonic();started=datetime.datetime.now(datetime.timezone.utc).isoformat()
with log.open('xb') as f:
    p=subprocess.Popen(command,cwd=T.parent,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
    tool=psutil.Process(p.pid);tool_id=dict(pid=p.pid,created_epoch=tool.create_time(),exe=tool.exe(),argv=tool.cmdline())
    save(L/(TAG+'.start.json'),dict(stage=TAG,owner=dict(pid=os.getpid(),created_epoch=psutil.Process().create_time()),tool=tool_id,target_argv=argv,inputs=inputs))
    print(json.dumps(dict(memcheck_started=tool_id['pid'])),flush=True)
    while p.poll() is None:
        if handle is None:
            for q in tool.children(recursive=True):
                try:
                    if os.path.normcase(q.exe())!=os.path.normcase(str(target.resolve())):continue
                    handle=K.OpenProcess(0x101000,False,q.pid);assert handle
                    times=[w.FILETIME() for _ in range(4)];assert K.GetProcessTimes(handle,*[ctypes.byref(x) for x in times])
                    identity=dict(pid=q.pid,creation_filetime_100ns=(times[0].dwHighDateTime<<32)|times[0].dwLowDateTime,exe=q.exe(),argv=q.cmdline());assert identity['argv']==argv
                    print(json.dumps(dict(actual_target=identity)),flush=True);break
                except psutil.NoSuchProcess:continue
        time.sleep(.02)
    rc=p.wait();tool_exit=w.DWORD();assert K.GetExitCodeProcess(int(p._handle),ctypes.byref(tool_exit))
solver_exit=w.DWORD(259)
if handle:
    assert K.GetExitCodeProcess(handle,ctypes.byref(solver_exit));K.CloseHandle(handle)
save(L/(TAG+'.call.json'),dict(stage=TAG,tool=tool_id,actual_target=identity,target_argv=argv,actual_Popen_wait_exit=rc,actual_tool_Win32_exit=tool_exit.value,actual_solver_Win32_exit=solver_exit.value,started_utc=started,ended_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),elapsed_s=time.monotonic()-wall,console=stat(log),SHA_scans=0))
assert identity is not None and rc==tool_exit.value==solver_exit.value==0,'Preserve unexpected tool/target exit, no retry'
text=sanlog.read_text(encoding='utf-8');assert 'ERROR SUMMARY: 0 errors' in text and 'LEAK SUMMARY: 0 bytes leaked in 0 allocations' in text
report=(OUT/'Run.out').read_text(encoding='utf-8',errors='replace')
assert report.count('GravityPreload: phase=released')==1 and 'completed_step=20' in report and 'retired=260' in report,'Missing actual short release event'
assert all(stat(e['path'])==e for e in inputs)
save(L/(TAG+'.check.json'),dict(stage=TAG,passed=True,actual_tool_exit=0,actual_solver_exit=0,memcheck_zero_errors_and_leaks=True,source_build=stat(BP),actual_call=stat(L/(TAG+'.call.json')),sanitizer_log=stat(sanlog),short_memory_screen_only=True,not_native_field_or_physical_acceptance=True,SHA_scans=0))
print(json.dumps(dict(memory_screen_passed=True,actual_solver_exit=0,physical_acceptance=False)),flush=True)
