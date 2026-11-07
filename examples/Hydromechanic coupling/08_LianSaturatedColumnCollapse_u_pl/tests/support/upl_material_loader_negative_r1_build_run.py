"""One fresh host-only real-loader component build/run, using the new r3 CPU ABI. No solver."""
import argparse,json,os,shutil,subprocess,traceback
from pathlib import Path
import upl_material_unified_gpu_build_run_r1 as owner
T=Path(__file__).resolve().parents[1];R=T.parents[3];L=T/'logs';TAG='upl_material_loader_negative_r1'
def main():
    a=argparse.ArgumentParser();a.add_argument('--execution-authorized',action='store_true');args=a.parse_args();owner.need(args.execution_authorized,'Root-reviewed execution flag required')
    owner.TAG=TAG;owner.STAGE=T/'outputs'/TAG;owner.CHECK=L/(TAG+'.check.json');owner.CALLS=[];before=[]
    summary=dict(stage=TAG,passed=False,solver_invocations=0,native_loader_component_invocations=0,SHA_scans=0,production_changed=False,physical_acceptance=False)
    def bind(e):
        actual=owner.stat(e['path']);owner.need(actual==e,'Frozen binding changed: '+e['path']);before.append(actual);return actual
    try:
        owner.need(not owner.STAGE.exists() and not owner.CHECK.exists(),'Fresh component output/check required; no retries')
        bp=L/'upl_material_release_DebugCPU_r3.build.json';b=owner.read(bp);owner.need(b['passed'] and b['actual_typed_exit_code']==b['actual_Win32_exit']==0 and b['source_stats_unchanged'] and b['canonical_and_package_stats_unchanged'],'Closed r3 DebugCPU build required');bind(owner.stat(bp));bind(b['program']);bind(b['source_capture']);bind(owner.read(b['source_capture']['path'])['archive'])
        objects=b['project_objects'];owner.need(len(objects)==86 and b['non_main_objects']==85,'Authoritative86-object r3 CPU layout required');objects=[e for e in objects if Path(e['path']).name.lower()!='main.obj'];owner.need(len(objects)==85,'Exclude exactly original main');[bind(e) for e in objects]
        cp=L/'upl_material_release_native_r1_source_CPU.native.check.json';c=owner.read(cp);owner.need(c['passed'] and c['original_native_guards_passed'] and c['qualified_elastic_PRE_verified'] and c['consumed_stats_unchanged'] and c['actual_completion']['source_material_law_version']==2,'Passed new Version2 CPU source native gate required');bind(owner.stat(cp));pre=Path(bind(c['certified_pre_file'])['path']);bind(c['native_completion']);run=owner.read(c['source_run']['path']);owner.need(run['passed'] and Path(run['program']['path']).parent.name=='upl_material_release_DebugCPU_r3','Actual new-source r3 program required');bind(c['source_run']);bind(run['actual_call'])
        root_source=owner.read(b['source_capture']['path']);src=T/'support'/(TAG+'.cpp')
        for rel in ('JGravityPreloadState.h','JPartsLoad4.h','JPartsLoad4.cpp','JBinaryData.h','JBinaryData.cpp','JPartDataBi4.h','JPartDataBi4.cpp'):
            p=R/'src/source'/rel;expected=next(e for e in root_source['files'] if Path(e['path']).resolve()==p.resolve());bind(expected)
        [bind(owner.stat(p)) for p in (src,Path(__file__),Path(owner.__file__))]
        oldc=L/'upl_preload_handoff_native_r1.compile.call.json';oldl=L/'upl_preload_handoff_native_r1.link.call.json';compilecall=owner.read(oldc);linkcall=owner.read(oldl);bind(owner.stat(oldc));bind(owner.stat(oldl));oldroot=str(T/'outputs/upl_preload_handoff_native_r1');exe=owner.STAGE/(TAG+'.exe')
        ca=[x.replace(oldroot,str(owner.STAGE)).replace('upl_preload_handoff_native_r1.cpp',src.name) for x in compilecall['arguments']];la=[]
        for x in linkcall['arguments']:
            if x.lower().endswith('.obj'):
                if Path(x).name.lower()=='helper.obj':la.extend([str(owner.STAGE/'helper.obj')]+[e['path'] for e in objects])
            else:la.append(x.replace(oldroot,str(owner.STAGE)).replace('upl_preload_handoff_native_r1.exe',exe.name))
        setup=subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',capture_output=True);owner.need(setup.returncode==0,'MSVC setup failed');env=dict(os.environ);env.update(x.split('=',1) for x in setup.stdout.decode('mbcs').splitlines() if '=' in x and not x.startswith('='));owner.need(env['VCTOOLSVERSION']=='14.36.32532','MSVC14.36 required')
        owner.STAGE.mkdir();owner.invoke('compile',[compilecall['program'],*ca],env);owner.invoke('link',[linkcall['program'],*la],env)
        for name in ('DsphConfig.xml','ChronoEngine.dll','dsphchrono.dll','vcomp140.dll'):
            src_runtime=T/'outputs/upl_prestress_check_CPU_r1_runtime'/name;original=bind(owner.stat(src_runtime));dst=owner.STAGE/name;shutil.copy2(src_runtime,dst);copy=owner.stat(dst);owner.need((copy['bytes'],copy['mtime_ns'])==(original['bytes'],original['mtime_ns']),'Host runtime copy differs');bind(copy)
        owner.save(L/(TAG+'.build.json'),dict(stage=TAG+'.build',passed=True,program=owner.stat(exe),source_build=owner.stat(bp),objects=objects,actual_calls=owner.CALLS.copy(),consumed=before.copy(),solver_invocations=0,SHA_scans=0,physical_acceptance=False))
        result=owner.STAGE/'result';owner.invoke('host_run',[str(exe),'--pre',str(pre),'--out',str(result)],env);summary['native_loader_component_invocations']=1
        done=owner.read(result/'completion.json');owner.need(done['passed'] and done['actual_cases']==6 and done['qualified_positive_imports']==1 and done['actual_PRE_rejections']==4 and done['actual_generic_PART_rejections']==1,'Actual six-case loader coverage incomplete');owner.need(done['original_source_whole_file_unchanged'] and done['fixture_payload_unchanged_after_calls'] and done['generic_nonzero_kappa_fixture'] and done['partial_loader_memory_state_not_inspected'] and not done['memory_atomic_restore_claimed'],'Loader proof scope or immutable-state guards differ')
        owner.need(all(owner.stat(e['path'])==e for e in before),'Consumed current headers/objects/receipts/runtime/source PRE changed');summary.update(passed=True,completion=done,consumed=before,consumed_stats_unchanged=True,calls=owner.CALLS,outputs=[owner.stat(p) for p in sorted(result.rglob('*')) if p.is_file()])
    except Exception as e:summary.update(first_failure=str(e),traceback=traceback.format_exc(),calls=owner.CALLS,consumed=before)
    owner.save(owner.CHECK,summary);print(json.dumps(summary,indent=2));return 0 if summary['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
