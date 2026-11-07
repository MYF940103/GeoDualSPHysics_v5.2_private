"""One selected actual CUDA wrapper component, linked to the closed r3 project."""
import argparse,json,os,shutil,subprocess,traceback
from pathlib import Path
import upl_material_unified_gpu_build_run_r1 as owner
T=Path(__file__).resolve().parents[1];R=T.parents[3];L=T/'logs'
PROFILES={'stage':'upl_material_stage_gpu_r1','periodic':'upl_material_periodic_gpu_r2'}
def main():
    ap=argparse.ArgumentParser();ap.add_argument('profile',choices=PROFILES);ap.add_argument('--execution-authorized',action='store_true');a=ap.parse_args();owner.need(a.execution_authorized,'Root-reviewed component required')
    tag=PROFILES[a.profile];owner.TAG=tag;owner.STAGE=T/'outputs'/tag;owner.CHECK=L/(tag+'.check.json');owner.CALLS=[];consumed=[]
    result=dict(stage=tag,passed=False,spatial_solver_invocations=0,SHA_scans=0,physical_acceptance=False)
    def bind(e):
        owner.need(owner.stat(e['path'])==e,'Consumed binding changed: '+e['path']);consumed.append(e);return e
    try:
        owner.need(not owner.STAGE.exists() and not owner.CHECK.exists(),'Existing/partial component protected')
        bp=L/'upl_material_release_Debug_r3.build.json';b=owner.read(bp);bind(owner.stat(bp));owner.need(b['passed'] and b['actual_typed_exit_code']==b['actual_Win32_exit']==0 and b['non_main_objects']==110,'Passed r3 GPU closure required')
        objects=[e for e in b['project_objects'] if Path(e['path']).name.lower()!='main.obj'];owner.need(len(objects)==110,'Wrong GPU non-main closure')
        for e in objects:bind(e)
        snap=owner.read(bind(b['source_capture'])['path']);bind(snap['archive'])
        for n in ('FunSoilMaterial.h','JSphGpuSimple_ker.h','JSphGpuSimple_ker.cu','JSphGpu_ker.h','JSphGpu_ker.cu','DualSphDef.h'):
            bind(next(e for e in snap['files'] if Path(e['path'])==R/'src/source'/n))
        src=T/'support'/(tag+'.cpp');bind(owner.stat(src));bind(owner.stat(__file__));bind(owner.stat(Path(owner.__file__)));bind(owner.stat(T/'support/upl_material_unified_candidate_r1.h'))
        base='upl_material_gpu_step_r2';ca=owner.read(L/(base+'.compile.call.json'));la=owner.read(L/(base+'.link.call.json'));old=str(T/'outputs'/base);exe=owner.STAGE/(tag+'.exe')
        cc=[x.replace(old,str(owner.STAGE)).replace(base+'.cpp',src.name) for x in ca['arguments']];ll=[]
        for x in la['arguments']:
            if x.lower().endswith('.obj'):
                if Path(x).name.lower()=='helper.obj':ll.extend([str(owner.STAGE/'helper.obj')]+[e['path'] for e in objects])
            else:ll.append(x.replace(old,str(owner.STAGE)).replace(base+'.exe',exe.name))
        target=[str(exe)]
        if a.profile=='stage':
            cp=L/'upl_material_stage_cpu_r1.check.json';c=owner.read(cp);owner.need(c['passed'] and c['consumed_stats_unchanged'],'Closed actual CPU stage required');bind(owner.stat(cp));csv=T/'outputs/upl_material_stage_cpu_r1/result/stages.csv';bind(next(e for e in c['outputs'] if Path(e['path'])==csv));bind(owner.stat(csv.parent/'completion.json'));target+=['--cpu',str(csv)]
        target+=['--out',str(owner.STAGE/'result')]
        setup=subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',capture_output=True);owner.need(setup.returncode==0,'MSVC setup failed');env=dict(os.environ);env.update(x.split('=',1) for x in setup.stdout.decode('mbcs').splitlines() if '=' in x and not x.startswith('='));owner.need(env['VCTOOLSVERSION']=='14.36.32532','MSVC14.36 required')
        owner.STAGE.mkdir();owner.invoke('compile',[ca['program'],*cc],env);owner.invoke('link',[la['program'],*ll],env)
        for name in ('DsphConfig.xml','ChronoEngine.dll','dsphchrono.dll','vcomp140.dll'):
            p=T/'outputs/upl_prestress_check_GPU_r1_runtime'/name;bind(owner.stat(p));shutil.copy2(p,owner.STAGE/name);q=owner.stat(owner.STAGE/name);owner.need((q['bytes'],q['mtime_ns'])==(owner.stat(p)['bytes'],owner.stat(p)['mtime_ns']),'Runtime copy differs');bind(q)
        owner.save(L/(tag+'.build.json'),dict(passed=True,program=owner.stat(exe),project_build=owner.stat(bp),non_main_objects=110,consumed=consumed.copy(),calls=owner.CALLS.copy(),SHA_scans=0,physical_acceptance=False))
        san=Path('C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v11.7/compute-sanitizer/compute-sanitizer.exe');log=L/(tag+'.memcheck.sanitizer.log')
        owner.invoke('memcheck',[str(san),'--tool','memcheck','--leak-check','full','--target-processes','all','--error-exitcode','86','--log-file',str(log),*target],env,exe)
        text=log.read_text();owner.need('ERROR SUMMARY: 0 errors' in text and 'LEAK SUMMARY: 0 bytes leaked in 0 allocations' in text,'Actual memcheck failed')
        d=owner.read(owner.STAGE/'result/completion.json');owner.need(d['passed'] and d['stage']==tag,'Actual component identity differs')
        if a.profile=='stage':owner.need(d['actual_wrapper_calls']==26 and d['Pre_old_kappa_checks']==12 and d['Cor_commit_checks']==11 and d['expected_Cor_rejections']==1 and d['Verlet_pairing_raw_DK_checks']==2,'Stage coverage differs')
        else:owner.need(d['copy_rows']==8 and d['sort_rows']==12 and d['actual_periodic_copy_calls']==4 and d['public_Divide_calls']==2 and d['public_history_SortDataArrays_calls']==5,'Periodic/sort coverage differs')
        owner.need(all(owner.stat(e['path'])==e for e in consumed),'Consumed project closure changed');result.update(passed=True,completion=d,memcheck_zero_errors_and_leaks=True,consumed_stats_unchanged=True,outputs=[owner.stat(p) for p in sorted((owner.STAGE/'result').iterdir()) if p.is_file()])
    except Exception as e:result.update(first_failure=str(e),traceback=traceback.format_exc())
    result.update(consumed=consumed,calls=owner.CALLS);owner.save(owner.CHECK,result);print(json.dumps({k:v for k,v in result.items() if k not in ('consumed','calls','outputs')}),flush=True);return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
