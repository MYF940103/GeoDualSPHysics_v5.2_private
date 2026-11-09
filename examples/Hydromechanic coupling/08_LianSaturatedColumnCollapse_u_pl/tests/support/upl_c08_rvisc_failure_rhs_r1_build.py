"""Author-only: one helper CL/link, reusing the closed residual-viscosity R2 physical object."""
import argparse, os, shutil, subprocess
from pathlib import Path
import upl_c08_residual_visc_cpu_r2_build as old

T,L,S=old.T,old.L,old.S
TAG='upl_c08_rvisc_failure_rhs_r1'
CPP=T/'support'/(TAG+'.cpp'); NOTE=T/'notes'/(TAG+'.md')
HELPER=T/'outputs'/(TAG+'_helper'); PROGRAM=HELPER/'component.exe'
need,read,stat,bind,save,invoke=old.need,old.read,old.stat,old.bind,old.save,old.invoke


def build():
    check=L/(TAG+'.build.json'); need(not HELPER.exists() and not check.exists(),'Existing complete/partial build protected'); before=[]; calls=[]
    try:
        priorp=L/'upl_c08_residual_visc_cpu_r2.build.json'; prior=read(priorp)
        need(prior['passed'] and prior['consumed_stats_unchanged'] and prior['project_non_main_objects']==86 and prior['retained_physical_objects']==85 and prior['physical_objects_recompiled']==0 and prior['adopted_physical_objects']==prior['helper_objects_compiled']==prior['compile_invocations']==prior['link_invocations']==1 and prior['actual_link_objects']==87 and prior['candidate_macro']=='C08_RESIDUAL_VISCOSITY_CANDIDATE','Closed R2 physical-object/ABI closure required')
        cp,lp=(Path(bind(e)['path']) for e in prior['calls']); c,l=read(cp),read(lp)
        need(c['actual_Popen_wait_exit']==c['actual_Win32_exit']==l['actual_Popen_wait_exit']==l['actual_Win32_exit']==0 and c['ownership_failure'] is l['ownership_failure'] is None,'Actual closed R2 helper CL/link required')
        base=read(bind(prior['source_build'])['path']); objects=[e for e in base['project_objects'] if Path(e['path']).name.lower()!='main.obj']; original=prior['original_physical_object']; adopted=prior['adopted_physical_object']; retained=[e for e in objects if e!=original]
        need(base['passed'] and base['actual_typed_exit_code']==base['actual_Win32_exit']==0 and len(base['project_objects'])==87 and len(objects)==86 and len(retained)==85 and prior['replacement_physical_object']==adopted and base['source_capture']==prior['source_capture'] and base['source_archive']==prior['source_archive'],'Same frozen bedkeep source and 85+one private object required')
        source=Path(bind(prior['source'])['path']).read_text(encoding='utf-8'); candidate=CPP.read_text(encoding='utf-8')
        blocks=[('struct Mat2','struct Snapshot'),('  std::vector<unsigned> Map()const','  struct Response'),('  Graph MakeGraph()const','  void Execute(')]
        need(all(source[source.index(a):source.index(z)]==candidate[candidate.index(a):candidate.index(z)] for a,z in blocks),'Math, state restoration, or candidate hook changed from closed R2')
        oldroot=Path(prior['program']['path']).parent
        ca=[str(CPP) if x==prior['source']['path'] else x if x.startswith('/I') else x.replace(str(oldroot),str(HELPER)) for x in c['arguments']]
        la=[x.replace(str(oldroot),str(HELPER)) for x in l['arguments']]
        need(all(x in ca for x in ('/Od','/MTd','/Zi','/RTC1','/fp:precise','/std:c++17','/openmp')) and '/D_WITHGPU' not in ca and str(CPP) in ca,'Closed DebugCPU helper flags required')
        need(sum(x.lower().endswith('.obj') for x in la)==87 and la.count(adopted['path'])==1 and original['path'] not in la and all(e['path'] in la for e in retained) and str(HELPER/'helper.obj') in la,'Link must contain exactly 85 retained + adopted Single + new helper')
        before=[stat(p) for p in (Path(__file__),Path(old.__file__),Path(old.old.__file__),priorp,cp,lp,CPP,NOTE)]+[bind(prior[k]) for k in ('program','source','source_build','source_capture','source_archive','private_source_capture','private_source_archive','private_cpu_source','adopted_physical_object','adopted_physical_compile_call')]+[bind(e) for e in retained]+[bind(e) for e in prior['frozen_headers']]+[bind(e) for e in prior['source_dependencies']]+[bind(e) for e in prior['runtime']]
        setup=subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
        need(setup.returncode==0,'MSVC environment setup failed'); env=dict(os.environ); env.update(x.split('=',1) for x in setup.stdout.decode('mbcs').splitlines() if '=' in x and not x.startswith('=')); need(env['VCTOOLSVERSION']=='14.36.32532','Original MSVC14.36 required'); env.pop('CL',None); env.pop('_CL_',None)
        HELPER.mkdir(); calls.append(invoke(TAG+'.helper_compile',[c['program'],*ca],S,env)); calls.append(invoke(TAG+'.link',[l['program'],*la],S,env))
        depspath=HELPER/'compile.dependencies.json'; deps=read(depspath); includes={Path(p).resolve() for p in deps['Data']['Includes']}; frozen=next(Path(x['path']).parent for x in prior['frozen_headers'] if Path(x['path']).name=='JSphCpuSingle.h')
        need(Path(deps['Data']['Source']).resolve()==CPP.resolve() and all((frozen/n).resolve() in includes for n in ('JSphCpuSingle.h','JSphCpu.h','JSph.h')),'Compiler used another source/header ABI')
        runtime=[]
        for e in prior['runtime']:
            dest=HELPER/Path(e['path']).name; shutil.copy2(e['path'],dest); q=stat(dest); need((q['bytes'],q['mtime_ns'])==(e['bytes'],e['mtime_ns']),'Runtime copy differs'); runtime.append(q)
        need(len(runtime)==4 and all(stat(e['path'])==e for e in before),'Closed objects, sources, headers, or programs changed')
        save(check,dict(stage=TAG+'.build',passed=True,program=stat(PROGRAM),source=stat(CPP),prior_build=stat(priorp),source_build=prior['source_build'],source_capture=prior['source_capture'],source_archive=prior['source_archive'],runtime_r6_GPU_build=prior['runtime_r6_GPU_build'],private_cpu_source=prior['private_cpu_source'],private_source_capture=prior['private_source_capture'],private_source_archive=prior['private_source_archive'],adopted_physical_object=adopted,adopted_physical_compile_call=prior['adopted_physical_compile_call'],project_non_main_objects=86,retained_physical_objects=85,adopted_physical_objects=1,physical_objects_recompiled=0,helper_objects_compiled=1,actual_link_objects=87,candidate_macro=prior['candidate_macro'],same_candidate_physical_object_as_closed_r2=True,math_and_restore_blocks_byte_exact=True,frozen_headers=prior['frozen_headers'],source_dependencies=stat(depspath),runtime=runtime,calls=calls,compile_invocations=1,link_invocations=1,solver_builds=0,component_invocations=0,production_source_changed=False,physical_acceptance=False,consumed=before,consumed_stats_unchanged=True,SHA_scans=0))
    except Exception as error:
        if not check.exists():save(check,dict(stage=TAG+'.build',passed=False,first_failure=str(error),calls=calls,consumed=before,physical_acceptance=False,SHA_scans=0))
        raise


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--execution-authorized',action='store_true'); a=p.parse_args(); need(a.execution_authorized,'Author-only until root full-read'); build()
