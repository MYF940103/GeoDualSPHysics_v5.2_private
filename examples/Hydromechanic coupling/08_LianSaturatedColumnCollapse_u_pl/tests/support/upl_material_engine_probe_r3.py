"""One explicitly selected actual-engine component; no solver, retry or chaining."""
import argparse,ctypes,datetime,json,os,shutil,subprocess,time,traceback
from ctypes import wintypes as w
from pathlib import Path
import psutil
T=Path(__file__).resolve().parents[1];L=T/'logs';S=T.parents[3]/'src'
PROFILES={'periodic_cpu':'upl_material_periodic_cpu_r4'}
def need(b,s):
    if not b:raise RuntimeError(s)
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def stat(p):
    p=Path(p).resolve();s=p.stat();return dict(path=str(p),bytes=s.st_size,mtime_ns=s.st_mtime_ns)
def save(p,d):
    with Path(p).open('x',encoding='utf-8') as f:json.dump(d,f,indent=2);f.write('\n')
K=ctypes.WinDLL('kernel32',use_last_error=True);K.GetExitCodeProcess.argtypes=[w.HANDLE,ctypes.POINTER(w.DWORD)]
def main():
    parser=argparse.ArgumentParser();parser.add_argument('profile',choices=PROFILES);parser.add_argument('--execution-authorized',action='store_true');a=parser.parse_args();need(a.execution_authorized,'Explicit root-reviewed component required')
    tag=PROFILES[a.profile];out=T/'outputs'/tag;check=L/(tag+'.check.json');need(not out.exists() and not check.exists(),'Existing/partial component protected')
    consumed=[];calls=[];result=dict(stage=tag,passed=False,SHA_scans=0,spatial_solver_invocations=0,physical_acceptance=False)
    def bind(e):
        need(stat(e['path'])==e,'Consumed file differs: '+e['path']);consumed.append(e);return e
    def invoke(phase,argv,env):
        log=L/(tag+'.'+phase+'.log');path=L/(tag+'.'+phase+'.call.json');need(not log.exists() and not path.exists(),'Existing component call protected')
        owner=psutil.Process();started=datetime.datetime.now(datetime.timezone.utc).isoformat();wall=time.monotonic()
        with log.open('xb') as f:
            p=subprocess.Popen(argv,cwd=S,env=env,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW);q=psutil.Process(p.pid);child=dict(pid=q.pid,created_epoch=q.create_time(),exe=q.exe(),argv=q.cmdline(),parent_pid=q.ppid());need(child['parent_pid']==owner.pid and Path(child['exe']).samefile(argv[0]),'Actual tool identity differs');rc=p.wait();code=w.DWORD();got=bool(K.GetExitCodeProcess(int(p._handle),ctypes.byref(code)))
        record=dict(phase=phase,owner=dict(pid=owner.pid,created_epoch=owner.create_time()),child=child,argv=argv,actual_Popen_wait_exit=rc,actual_Win32_exit=code.value if got else None,started_utc=started,elapsed_s=time.monotonic()-wall,log=stat(log));save(path,record);calls.append(stat(path));need(got and rc==code.value==0,'Actual '+phase+' failed; inspect '+str(log))
    try:
        bp=L/'upl_material_release_DebugCPU_r3.build.json';b=read(bp);bind(stat(bp));need(b['passed'] and b['actual_typed_exit_code']==b['actual_Win32_exit']==0 and b['non_main_objects']==85,'Passed r3 CPU project required')
        objects=[e for e in b['project_objects'] if Path(e['path']).name.lower()!='main.obj'];need(len(objects)==85,'Current CPU object closure differs')
        for e in objects:bind(e)
        capture=bind(b['source_capture']);snapshot=read(capture['path']);bind(snapshot['archive'])
        for name in ('JSphCpu.cpp','JSphCpu.h','JSphCpuSingle.cpp','FunSoilMaterial.h','DualSphDef.h'):
            bind(next(e for e in snapshot['files'] if Path(e['path'])==S/'source'/name))
        src=T/'support'/(tag+'.cpp');bind(stat(src));bind(stat(__file__));bind(stat(T/'support/upl_material_unified_candidate_r1.h'))
        ca=read(L/'upl_preload_handoff_native_r1.compile.call.json');la=read(L/'upl_preload_handoff_native_r1.link.call.json');old=str(T/'outputs/upl_preload_handoff_native_r1');exe=out/(tag+'.exe')
        cc=[x.replace(old,str(out)).replace('upl_preload_handoff_native_r1.cpp',src.name) for x in ca['arguments']];ll=[]
        for x in la['arguments']:
            if x.lower().endswith('.obj'):
                if Path(x).name.lower()=='helper.obj':ll.extend([str(out/'helper.obj')]+[e['path'] for e in objects])
            else:ll.append(x.replace(old,str(out)).replace('upl_preload_handoff_native_r1.exe',exe.name))
        setup=subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',capture_output=True);need(setup.returncode==0,'MSVC environment failed');env=dict(os.environ);env.update(x.split('=',1) for x in setup.stdout.decode('mbcs').splitlines() if '=' in x and not x.startswith('='));need(env['VCTOOLSVERSION']=='14.36.32532','MSVC14.36 required')
        out.mkdir();invoke('compile',[ca['program'],*cc],env);invoke('link',[la['program'],*ll],env)
        for name in ('DsphConfig.xml','ChronoEngine.dll','dsphchrono.dll','vcomp140.dll'):
            srcdll=T/'outputs/upl_prestress_check_CPU_r1_runtime'/name;bind(stat(srcdll));shutil.copy2(srcdll,out/name);need(stat(srcdll)['bytes']==stat(out/name)['bytes'],'Runtime copy size differs');bind(stat(out/name))
        save(L/(tag+'.build.json'),dict(passed=True,program=stat(exe),consumed=consumed.copy(),actual_build_calls=calls.copy(),project_build=stat(bp),SHA_scans=0,physical_acceptance=False))
        invoke('run',[str(exe),'--out',str(out/'result')],env);done=read(out/'result/completion.json');need(done['passed'] and done['stage']==tag,'Actual component completion differs')
        if a.profile=='stage_cpu':need(done['manufactured_points']==14 and done['rows']==26 and done['actual_Pre_calls']==done['actual_Cor_calls']==12 and done['actual_Verlet_calls']==2,'Stage coverage differs')
        else:need(done['copy_rows']==8 and done['sort_rows']==12 and done['actual_periodic_copy_calls']==4 and done['actual_public_Divide_calls']==2,'Copy/sort coverage differs')
        need(all(stat(e['path'])==e for e in consumed),'Consumed component closure changed');result.update(passed=True,completion=done,consumed_stats_unchanged=True,outputs=[stat(p) for p in sorted((out/'result').iterdir())])
    except Exception as e:result.update(first_failure=str(e),traceback=traceback.format_exc())
    result.update(consumed=consumed,calls=calls);save(check,result);print(json.dumps({k:v for k,v in result.items() if k not in ('consumed','calls','outputs')}),flush=True);return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
