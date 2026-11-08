"""Build CPU Debug after retracting the unselected half-stage ponding trial; no solver."""
import json, os, subprocess, time
from pathlib import Path

T=Path(__file__).resolve().parents[1]; R=T.parents[3]; S=R/'src'
TAG='upl_c08_stage_ponding_retract_DebugCPU_r1'; L=T/'logs'
OUT=T/'outputs'/TAG; INT=Path(os.environ['LOCALAPPDATA'])/'Temp'/TAG/'int'
FILES=('src/source/JSphCpu.cpp','src/source/JSphGpu.cpp','src/source/JSph.cpp','doc/xml_format/_FmtXML_ElastoplasticSoil.xml')
def stat(p):
    p=Path(p).resolve(); s=p.stat(); return dict(path=str(p),bytes=s.st_size,mtime_ns=s.st_mtime_ns)
def save(p,d):
    with p.open('x',encoding='utf8') as f: json.dump(d,f,ensure_ascii=False,indent=2)

if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser(description=__doc__); ap.add_argument('--execution-authorized',action='store_true'); a=ap.parse_args()
    if not a.execution_authorized: raise SystemExit('Explicit reviewed build authorization required')
    receipt=L/(TAG+'.build.json'); call=L/(TAG+'.call.json'); log=L/(TAG+'.log')
    if any(p.exists() for p in (OUT,INT.parent,receipt,call,log)): raise SystemExit('Prior build or partial output protected')
    if subprocess.check_output(['git','diff','e2fa301','--',*FILES],cwd=R): raise SystemExit('Selected source must equal the preserved CompletedOnly base')
    old=json.loads((L/'upl_c08_stage_ponding_DebugCPU_r2.call.json').read_text(encoding='utf8'))
    args=[('/p:OutDir='+OUT.as_posix()+'/') if x.startswith('/p:OutDir=') else ('/p:IntDir='+INT.as_posix()+'/') if x.startswith('/p:IntDir=') else '/bl:'+str(L/(TAG+'.binlog')) if x.startswith('/bl:') else x for x in old['arguments']]
    protected=[R/'bin/windows'/n for n in ('DualSPHysics5.2CPU_win64_debug.exe','DualSPHysics5.2_win64_debug.exe','DualSPHysics5.2CPU_win64.exe','DualSPHysics5.2_GEO_win64.exe')]
    protected += list((T.parent/'support/runtime_r5').iterdir())+[T.parent/'CaseLianSaturatedColumnCollapse_shared_preload_r2_GPU_out/data/Part_1000.bi4']
    protected=[stat(p) for p in protected if p.is_file()]; inputs=[stat(R/n) for n in FILES]
    result=dict(stage=TAG,passed=False,configuration='DebugCPU',solution=str(S/'VS/DualSPHysics5ReCpu_vs2022.sln'),base='e2fa301',four_selected_files_equal_base=True,inputs=inputs,protected=protected,solver_invocations=0,SHA_scans=0)
    try:
        setup=subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
        if setup.returncode: raise RuntimeError('MSVC setup failed')
        env=dict(os.environ); env.update(x.split('=',1) for x in setup.stdout.decode('mbcs').splitlines() if '=' in x and not x.startswith('='))
        if any('C08_STAGE_TRACE' in env.get(k,'') for k in ('CL','_CL_','NVCC_PREPEND_FLAGS','NVCC_APPEND_FLAGS')): raise RuntimeError('Unexpected inherited trace macro')
        OUT.mkdir(); INT.mkdir(parents=True); begin=time.monotonic()
        with log.open('xb') as f:
            q=subprocess.Popen([old['program'],*args],cwd=S,env=env,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW); rc=q.wait()
        save(call,dict(stage=TAG+'.call',program=old['program'],arguments=args,pid=q.pid,actual_Popen_wait_exit=rc,elapsed_s=time.monotonic()-begin,log=stat(log)))
        result.update(actual_exit=rc,call=stat(call))
        if rc: raise RuntimeError('MSBuild failed; original log preserved')
        exe=OUT/'DualSPHysics5.2CPU_win64_debug.exe'
        if not exe.is_file(): raise RuntimeError('CPU Debug executable missing')
        result.update(program=stat(exe),object_count=len(list(INT.glob('*.obj'))))
        if [stat(R/n) for n in FILES]!=inputs or [stat(e['path']) for e in protected]!=protected: raise RuntimeError('Build input or protected artifact changed')
        result.update(passed=True,inputs_and_protected_unchanged=True)
    except Exception as e: result['first_failure']=str(e)
    save(receipt,result); print(json.dumps(result,ensure_ascii=False),flush=True)
    raise SystemExit(0 if result['passed'] else 1)
