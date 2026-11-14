"""Release-only RV FMA diagnostic build: adopt r2 host/112 objects, compile one unchanged CU."""
import argparse,os,re,shutil,subprocess
from pathlib import Path
import upl_c08_shepard_release_r1_build as recipe
T,L,S=recipe.T,recipe.L,recipe.S
need,read,stat,bind,save,invoke=recipe.need,recipe.read,recipe.stat,recipe.bind,recipe.save,recipe.invoke
TAG='c08_h18_rv_gpu_Release_r3';NOTE=T/'notes/c08_h18_rv_gpu_build_r3.md'

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execution-authorized',action='store_true');a=p.parse_args();need(a.execution_authorized,'Independent root build admission required')
    out=T/'outputs'/TAG;intdir=Path(os.environ['TEMP'])/'c08_h18_rv_gpu_r3/Release';check=L/(TAG+'.build.json');calls=[];before=[]
    need(' 'not in str(intdir.resolve())and not out.exists()and not intdir.exists()and all(not(L/(TAG+s)).exists()for s in ('.build.json','.cuda_compile.call.json','.cuda_compile.log','.link.call.json','.link.log')),'Fresh r3 output/IntDir/receipts required')
    try:
        bp=L/'c08_h18_rv_gpu_Release_r2.build.json';b=read(bp)
        need(b['passed']and b['configuration']=='Release'and b['consumed_stats_unchanged']and b['retained_original_objects']==112 and b['private_objects']==2 and b['actual_link_objects']==114 and len(b['calls'])==3,'Actually passed Release r2 build/object contract required')
        prior=[read(bind(q)['path'])for q in b['calls']]
        need(all(q['actual_Popen_wait_exit']==q['actual_Win32_exit']==0 and q['ownership_failure']is None for q in prior),'Actual r2 CL/NVCC/link handles/exits required')
        hostcall,cudacall,linkcall=prior;oldhost,oldcuda=b['new_private_objects'];bind(oldhost);bind(oldcuda)
        need(Path(oldhost['path']).name=='JSphGpuSingle.obj'and Path(oldcuda['path']).name=='c08_h18_rv_gpu_r1.cu.obj','Exact adopted r2 host/CU identity required')
        sources={k:bind(b['private_sources'][k])for k in ('host','CUDA','header')};source_capture=bind(b['source_capture']);sc=read(source_capture['path'])
        need(sc['passed']and sc['prepared_only']and sc['private_sources']==sources and sc['exact_reverse_original_host_bytes']and sc['original_CUDA_members_unchanged']and sc['alpha']==.1 and sc['policy_schema']==2,'Same actual frozen r1 preparation required')
        cuargs=list(cudacall['arguments']);linked=list(linkcall['arguments']);nvcc=Path(cudacall['program']);link=Path(linkcall['program']);cudaobj=intdir/'c08_h18_rv_gpu_r1.cu.obj';program=out/Path(b['program']['path']).name
        need('-use_fast_math'in cuargs and '--use-local-env'in cuargs and cuargs.count('-ccbin')==cuargs.count('-o')==cuargs.count('--keep-dir')==1 and not any('fmad' in q.lower()for q in cuargs),'Unmodified actual r2 fast-math/local-env recipe required')
        cu_source=[Path(q)for q in cuargs if Path(q).name=='c08_h18_rv_gpu_r1.cu'];need(len(cu_source)==1 and stat(cu_source[0])in b['frozen_sources'],'Original r2 frozen CU compile source required')
        need(cu_source[0].read_bytes()==Path(sources['CUDA']['path']).read_bytes(),'R2 compile source and frozen r1 private CU differ')
        nfd=0
        for i,q in enumerate(cuargs):
            if i and cuargs[i-1]=='-Xcompiler':cuargs[i],n=re.subn(r'(?i)(?<!\S)/Fd[^\s]+',lambda m:'/Fd'+str(intdir/'cuda.pdb'),q);nfd+=n
        need(nfd==1,'One original CUDA compiler PDB output required');cuargs[cuargs.index('-o')+1]=str(cudaobj);cuargs[cuargs.index('--keep-dir')+1]=str(intdir)
        # This explicit last option overrides only the new TU's inherited fast-math FMA setting.
        cuargs.append('--fmad=false');need(cuargs.index('-use_fast_math')<cuargs.index('--fmad=false'),'Explicit FMA override must follow inherited fast math')
        targets={'/out:':program,'/pdb:':out/(program.stem+'.pdb'),'/implib:':out/(program.stem+'.lib'),'/ltcgout:':intdir/(program.stem+'.iobj'),'/ilk:':out/(program.stem+'.ilk'),'/map:':out/(program.stem+'.map'),'/manifestfile:':intdir/'program.manifest','/pgd:':intdir/'program.pgd','/tlbout:':intdir/'program.tlb','/winmdfile:':intdir/'program.winmd'};seen={};replaced=0
        for i,q in enumerate(linked):
            if q.lower().endswith('.obj')and Path(q).resolve()==Path(oldcuda['path']).resolve():q=str(cudaobj);replaced+=1
            for key,target in targets.items():
                if q.lower().startswith(key):need(key not in seen,'Duplicate link output switch');seen[key]=str(target);q=key+str(target);break
            linked[i]=q
        retained=[bind(q)for q in b['retained_object_stats']];actual=[Path(q).resolve()for q in linked if q.lower().endswith('.obj')]
        need(replaced==1 and all(k in seen for k in ('/out:','/pdb:','/implib:','/ltcgout:'))and len(actual)==len(set(actual))==114 and set(actual)=={Path(q['path']).resolve()for q in retained}|{Path(oldhost['path']).resolve(),cudaobj.resolve()},'Exact112 old+adopted r2 host+one new CU and rehomed link outputs required')
        runtime=[bind(q)for q in b['runtime']];need(len(runtime)==9,'Actual r2 nine-file runtime required')
        before=[stat(q)for q in (Path(__file__),NOTE,Path(recipe.__file__),Path(recipe.e.__file__),bp)]+[bind(q)for q in b['calls']]+[bind(q['log'])for q in prior]+[source_capture,bind(b['source_archive']),bind(b['baseline_source_capture']),bind(b['program']),oldhost,oldcuda,*sources.values(),*retained,*runtime]+[bind(q)for q in b['frozen_sources']]
        need(all(stat(q['path'])==q for q in before),'Frozen original/source/runtime changed before new build')
        setup=subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW);need(setup.returncode==0,'MSVC setup failed')
        env=dict(os.environ);env.update(q.split('=',1)for q in setup.stdout.decode('mbcs').splitlines()if '='in q and not q.startswith('='));need(env['VCTOOLSVERSION']=='14.36.32532','Same original MSVC14.36 required')
        for key in list(env):
            if key.upper()in ('CL','_CL_','NVCC_PREPEND_FLAGS','NVCC_APPEND_FLAGS'):env.pop(key)
        cudaenv=dict(env);cuda_path=env.get('Path',env.get('PATH',''))
        for key in list(cudaenv):
            if key.upper()=='PATH':cudaenv.pop(key)
        ccbin=Path(cuargs[cuargs.index('-ccbin')+1]);need(ccbin.is_dir()and'14.36.32532'in str(ccbin),'Unchanged actual r2 ccbin required');cudaenv['PATH']=str(ccbin)+os.pathsep+cuda_path
        before += [stat(nvcc),stat(link)]
        libdirs=[Path(linkcall['cwd'])]+[Path(q.split(':',1)[1])if Path(q.split(':',1)[1]).is_absolute()else Path(linkcall['cwd'])/q.split(':',1)[1]for q in linked if q.lower().startswith('/libpath:')]+[Path(q)for q in env.get('LIB','').split(';')if q]
        for q in linked:
            if q.lower().endswith('.lib')and not q.startswith('/'):
                lib=next((v for v in ([Path(q)]if Path(q).is_absolute()else[d/q for d in libdirs])if v.is_file()),None);need(lib is not None,'Actual linked library missing: '+q);before.append(stat(lib))
        out.mkdir();intdir.mkdir(parents=True);need(all(stat(q['path'])==q for q in before),'Consumed input changed before compile')
        calls.append(invoke(TAG+'.cuda_compile',[str(nvcc),*cuargs],intdir,cudaenv));calls.append(invoke(TAG+'.link',[str(link),*linked],Path(linkcall['cwd']),env))
        copied=[]
        for q in runtime:
            dest=out/Path(q['path']).name;need(not dest.exists(),'Existing new runtime protected');shutil.copy2(q['path'],dest);v=stat(dest);need((v['bytes'],v['mtime_ns'])==(q['bytes'],q['mtime_ns'])and dest.read_bytes()==Path(q['path']).read_bytes(),'Actual runtime copy differs');copied.append(v)
        need(all(stat(q['path'])==q for q in before),'Adopted/source/object/program/runtime changed during build')
        warnings=[line for q in calls for line in Path(read(q['path'])['log']['path']).read_bytes().decode('mbcs').splitlines()if re.search(r'\bwarning\b',line,re.I)]
        save(check,dict(stage=TAG+'.build',passed=True,configuration='Release',program=stat(program),source_capture=source_capture,source_archive=b['source_archive'],baseline_source_capture=b['baseline_source_capture'],private_sources=sources,baseline_source_build=stat(bp),adopted_host_object=oldhost,adopted_host_call=b['calls'][0],host_object_recompiled=False,original_physical_CUDA_objects_retained=True,retained_original_objects=112,private_objects=2,actual_link_objects=114,retained_object_stats=retained,new_private_objects=[oldhost,stat(cudaobj)],actual_link_inputs=[str(q)for q in actual],frozen_sources=b['frozen_sources'],same_frozen_r2_CUDA_source=stat(cu_source[0]),new_CUDA_flag='--fmad=false',flag_after_inherited_fast_math=True,all_other_NVCC_flags_inherited_except_new_outputs=True,original_private_CUDA_object=b['new_private_objects'][1],OFF_equivalence_scope='implementation inheritance from same host and112 original objects; no new-binary native bitproof',Debug_evidence_scope='same source memory/math; not Release bit truth',ON_runtime_env='C08_RV_H18=1',OFF_env_absent_no_RV_allocation_launch_sidecar=True,main_columns=66,manufactured_columns=40,policy_schema=2,runtime=copied,IntDir=str(intdir),OutDir=str(out),calls=calls,link_output_flags=seen,warning_lines=warnings,new_warning_free_claimed=False,consumed=before,consumed_stats_unchanged=True,public_source_changed=False,class_or_CTE_layout_changed=False,numerical_budgets_changed=False,compile_invocations=1,host_compile_invocations=0,link_invocations=1,full_project_builds=0,solver_invocations=0,help_invocations=0,memcheck_invocations=0,native_decodes=0,physical_acceptance=False,SHA_scans=0))
        print('C08_H18_RV_RELEASE_FMAD_FALSE_BUILD_PASSED',program,flush=True)
    except Exception as error:
        if not check.exists():save(check,dict(stage=TAG+'.build',passed=False,configuration='Release',first_failure=str(error),calls=calls,consumed=before,solver_invocations=0,native_decodes=0,physical_acceptance=False,SHA_scans=0))
        raise

if __name__=='__main__':main()
