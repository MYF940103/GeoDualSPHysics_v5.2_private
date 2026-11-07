"""One serial /O2 material benchmark and existing-reference join; no engine objects or new oracle solve."""
import argparse,csv,ctypes,datetime,json,math,os,statistics,subprocess,time,traceback
from ctypes import wintypes as w
from pathlib import Path
import psutil
T=Path(__file__).resolve().parents[1];R=T.parents[3];L=T/'logs';TAG='upl_material_cost_r1';OUT=T/'outputs'/TAG;CHECK=L/(TAG+'.check.json')
K=ctypes.WinDLL('kernel32',use_last_error=True)
K.GetExitCodeProcess.argtypes=[w.HANDLE,ctypes.POINTER(w.DWORD)]
K.QueryFullProcessImageNameW.argtypes=[w.HANDLE,w.DWORD,w.LPWSTR,ctypes.POINTER(w.DWORD)]
def need(b,s):
    if not b:raise RuntimeError(s)
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def stat(p):
    p=Path(p).resolve();s=p.stat();return dict(path=str(p),bytes=s.st_size,mtime_ns=s.st_mtime_ns)
def save(p,d):
    with Path(p).open('x',encoding='utf-8') as f:json.dump(d,f,indent=2,allow_nan=False);f.write('\n')
def table(p):
    with Path(p).open(newline='',encoding='utf-8-sig') as f:return list(csv.DictReader(f))
def write(p,rows):
    with Path(p).open('x',encoding='utf-8',newline='') as f:q=csv.DictWriter(f,fieldnames=list(rows[0]));q.writeheader();q.writerows(rows)
CALLS=[]
def invoke(phase,argv,env):
    log=L/f'{TAG}.{phase}.log';record=L/f'{TAG}.{phase}.call.json';need(not log.exists() and not record.exists(),'Existing call evidence protected');start=datetime.datetime.now(datetime.timezone.utc).isoformat();clock=time.monotonic()
    with log.open('xb') as f:
        p=subprocess.Popen(argv,executable=argv[0],cwd=R/'src',env=env,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        q=psutil.Process(p.pid);identity=dict(pid=p.pid,created_epoch=q.create_time(),argv=q.cmdline(),parent_pid=q.ppid());n=w.DWORD(32768);image=ctypes.create_unicode_buffer(n.value);image_ok=bool(K.QueryFullProcessImageNameW(int(p._handle),0,image,ctypes.byref(n)));identity['actual_image']=image.value if image_ok else None
        code=p.wait();actual=w.DWORD();got=bool(K.GetExitCodeProcess(int(p._handle),ctypes.byref(actual)))
    d=dict(stage=TAG+'.'+phase,argv=argv,program=stat(argv[0]),child=identity,actual_Popen_wait_exit=code,actual_Win32_exit=actual.value if got else None,started_utc=start,elapsed_s=time.monotonic()-clock,log=stat(log));save(record,d);CALLS.append(stat(record))
    need(image_ok and Path(image.value).samefile(argv[0]) and got and code==actual.value==0,phase+' failed; retain first evidence without retry')

def analyze(result,reference):
    refs={};
    for r in table(reference):
        k=(r['model'],int(r['N']),int(r['step']));need(k not in refs,'Duplicate existing reference state');refs[k]=r
    need(len(refs)==7560,'Existing reference must contain exactly7560 states');groups={};seen=set()
    for r in table(result/'path_states.csv'):
        k=(r['model'],int(r['N']),int(r['step']));full=(r['method'],*k);need(full not in seen and k in refs and r['method'] in ('linearized_dev','endpoint'),'Path/reference identity differs');seen.add(full);ref=refs[k]
        values=[float(r[x]) for x in ('I_Pa','q_Pa','saved_kappa','local_continuous_kappa','yield_saved_Pa','yield_continuous_Pa','closure_xx','closure_yy','closure_zz')];need(all(math.isfinite(x) for x in values) and int(r['status']) in (1,2),'A failed/nonfinite material return is not an accuracy or cost sample')
        dI=values[0]-float(ref['I_Pa']);dq=values[1]-float(ref['q_Pa']);dk=values[2]-float(ref['kappa']);dlocal=values[3]-float(ref['kappa']);key=(r['model'],r['method'],int(r['N']))
        g=groups.setdefault(key,dict(model=key[0],method=key[1],N=key[2],increments=0,max_stress_Frobenius_error_Pa=0.,max_stress_component_error_Pa=0.,max_I_error_Pa=0.,max_q_error_Pa=0.,max_saved_kappa_error=0.,max_local_continuous_kappa_error=0.,max_plastic_yield_saved_abs_Pa=0.,max_plastic_yield_continuous_abs_Pa=0.,min_elastic_yield_Pa=0.,max_strain_closure_abs=0.))
        plastic=int(r['status'])==2
        if not plastic:g['min_elastic_yield_Pa']=min(g['min_elastic_yield_Pa'],values[4])
        g['increments']+=1;errors=dict(max_stress_Frobenius_error_Pa=math.sqrt(dI*dI/3.+2*dq*dq),max_stress_component_error_Pa=max(abs(dI/3.+dq),abs(dI/3.-dq),abs(dI/3.)),max_I_error_Pa=abs(dI),max_q_error_Pa=abs(dq),max_saved_kappa_error=abs(dk),max_local_continuous_kappa_error=abs(dlocal),max_plastic_yield_saved_abs_Pa=abs(values[4]) if plastic else 0.,max_plastic_yield_continuous_abs_Pa=abs(values[5]) if plastic else 0.,max_strain_closure_abs=max(map(abs,values[6:])))
        for name,value in errors.items():g[name]=max(g[name],value)
    need(len(seen)==15120 and len(groups)==168 and all(v['increments']==3*v['N'] for v in groups.values()),'Two-method path coverage incomplete');write(result/'accuracy_by_path.csv',[groups[k] for k in sorted(groups)])
    timings=table(result/'timings.csv');need(len(timings)==28,'Exactly28 recorded timing batches required');summary=[]
    for phase in ('fixed_common_incoming','independent_paths'):
        values={}
        for method in ('linearized_dev','endpoint'):
            rows=[r for r in timings if r['phase']==phase and r['method']==method];need(len(rows)==7 and {int(r['round']) for r in rows}==set(range(7)),'Seven rotated-order timing samples required');ns=[float(r['ns_per_return']) for r in rows];need(all(math.isfinite(x) and x>0 for x in ns),'Invalid elapsed timing');values[method]=statistics.median(ns)
            summary.append(dict(phase=phase,method=method,median_ns_per_return=values[method],minimum_ns_per_return=min(ns),maximum_ns_per_return=max(ns),samples=7,minimum_actual_batch_s=min(float(r['elapsed_s']) for r in rows),endpoint_over_taylor_median_ratio=0.))
        ratio=values['endpoint']/values['linearized_dev'];
        for row in summary:
            if row['phase']==phase:row['endpoint_over_taylor_median_ratio']=ratio
    write(result/'cost_summary.csv',summary);return dict(accuracy_groups=168,accuracy_states=15120,cost=summary,reference_reintegrated=False,stress_reference_reconstruction='diag I/3+q, I/3-q, I/3; declared signed q stays positive',saved_float_history_error_included_in_path_error=True)

def main():
    p=argparse.ArgumentParser();p.add_argument('--execution-authorized',action='store_true');a=p.parse_args();need(a.execution_authorized,'Execution follows root full review')
    inputs=[];answer=dict(stage=TAG,passed=False,SHA_scans=0,engine_objects=0,spatial_solver_invocations=0,old_actual_sft_included=False,physical_acceptance=False)
    try:
        need(not OUT.exists() and not CHECK.exists(),'Fresh benchmark required; no automatic rerun')
        bp=T/'logs/upl_material_release_DebugCPU_r3.build.json';b=read(bp);need(b['passed'] and b['actual_typed_exit_code']==b['actual_Win32_exit']==0,'Closed production r3 CPU build required');capture=b['source_capture'];need(stat(capture['path'])==capture,'Production source-capture binding changed');closed=read(capture['path'])
        prod=[R/'src/source/FunSoilMaterial.h',R/'src/source/DualSphDef.h',R/'src/source/TypesDef.h']
        for f in prod:need(stat(f)==next(e for e in closed['files'] if Path(e['path']).resolve()==f.resolve()),'Current production material headers differ from r3')
        old=T/'outputs/upl_material_path_r1';prepared=read(old/'prepared.json');need(prepared['reference_checks_passed'] and prepared['models']==21 and prepared['rows']==22680 and stat(old/'input.csv')==prepared['input'],'Closed unchanged path/reference preparation required')
        source=T/'support/upl_material_cost_r1.cpp';inputs=[stat(f) for f in [Path(__file__),source,*prod,bp,Path(capture['path']),old/'prepared.json',old/'input.csv',old/'reference.csv',old/'reference_checks.json',R/'src/VS/DualSPHysics5ReCpu.vcxproj']]
        setup=subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',capture_output=True);need(setup.returncode==0,'MSVC setup failed');env=dict(os.environ);env.update(s.split('=',1) for s in setup.stdout.decode('mbcs').splitlines() if '=' in s and not s.startswith('='));need(env['VCTOOLSVERSION']=='14.36.32532','MSVC14.36 required')
        OUT.mkdir();cl=Path(env['VCToolsInstallDir'])/'bin/Hostx64/x64/cl.exe';exe=OUT/'upl_material_cost_r1.exe';result=OUT/'result'
        argv=[str(cl),'/nologo','/std:c++17','/EHsc','/O2','/MT','/fp:precise','/GL-','/W3','/DWIN32','/D_CONSOLE','/D_MBCS','/I'+str(R/'src/source'),'/Fo'+str(OUT/'cost.obj'),'/Fe'+str(exe),str(source),'/link','/INCREMENTAL:NO','/OPT:REF','/OPT:NOICF']
        invoke('build',argv,env);save(L/(TAG+'.build.json'),dict(passed=True,program=stat(exe),compiler_argv=argv,consumed=inputs,engine_objects=0,optimization='O2; MT; fp:precise; GL-; noinline entry, volatile function pointer',OpenMP_regions=0,SHA_scans=0))
        busy=[q.info['name'] for q in psutil.process_iter(['name']) if (q.info['name'] or '').lower() in ('msbuild.exe','cl.exe','link.exe','nvcc.exe') or (q.info['name'] or '').lower().startswith('dualsphysics')];need(not busy,'Another build/solver is active; preserve idle benchmark admission without stopping it: '+str(busy))
        invoke('run',[str(exe),'--input',str(old/'input.csv'),'--out',str(result)],env);done=read(result/'completion.json');need(done['passed'] and done['canonical_paths']==84 and done['accuracy_rows']==15120 and done['timing_batches']==28,'Native benchmark completion incomplete');analysis=analyze(result,old/'reference.csv')
        need(all(stat(e['path'])==e for e in inputs),'Consumed source/reference changed');answer.update(passed=True,completion=done,analysis=analysis,consumed=inputs,consumed_stats_unchanged=True,calls=CALLS,outputs=[stat(f) for f in sorted(result.iterdir())],serial_CPU_only=True)
    except Exception as e:answer.update(first_failure=str(e),traceback=traceback.format_exc(),calls=CALLS,consumed=inputs)
    save(CHECK,answer);print(json.dumps(answer,indent=2));return 0 if answer['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
