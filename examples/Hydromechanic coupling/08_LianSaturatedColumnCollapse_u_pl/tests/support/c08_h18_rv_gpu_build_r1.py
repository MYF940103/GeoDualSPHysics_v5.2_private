"""Private H1.8 RV build only:112 original objects plus one host and one CUDA object."""
import argparse,datetime,os,re,shutil,subprocess,zipfile
from pathlib import Path,PurePosixPath
import upl_c08_shepard_release_r1_build as recipe
T,L,S=recipe.T,recipe.L,recipe.S
need,read,stat,bind,save,invoke=recipe.need,recipe.read,recipe.stat,recipe.bind,recipe.save,recipe.invoke
TAG='c08_h18_rv_gpu_r1';CAP=T/'outputs'/(TAG+'_source');NOTE=T/'notes'/(TAG+'.md')

def baseline(conf):
    p=L/('c08_preload_schema2_'+conf+'_r1.build.json');b=read(p)
    need(b['passed'] and b['configuration']==conf and b['consumed_stats_unchanged'],'Successful unchanged schema2 baseline required')
    a=read(bind(b['actual_call'])['path'])
    need(a['actual_Popen_wait_exit']==a['actual_Win32_exit']==0 and a['ownership_failure'] is None,'Actual original MSBuild handles/exit required')
    need(any('/p:Configuration='+conf==v for v in a['arguments']) and any('/p:VCToolsVersion=14.36.32532'==v for v in a['arguments']),'Original authoritative solution/config/toolset required')
    return p,b,a

def build(conf):
    label='c08_h18_rv_gpu_'+conf+'_r1';out=T/'outputs'/label;intdir=Path(os.environ['TEMP'])/TAG/conf
    check=L/(label+'.build.json');calls=[];before=[]
    need(' ' not in str(intdir.resolve()) and not out.exists() and not intdir.exists() and all(not(L/(label+s)).exists() for s in ('.build.json','.host_compile.call.json','.host_compile.log','.cuda_compile.call.json','.cuda_compile.log','.link.call.json','.link.log')),'Fresh isolated outputs/receipts/no-space IntDir required')
    try:
        bp,b,a=baseline(conf);db,d,_=baseline('Debug');rb,r,_=baseline('Release');sc=read(CAP/'source.json')
        need(sc['passed'] and sc['prepared_only'] and sc['exact_reverse_original_host_bytes'] and sc['original_CUDA_members_unchanged'] and not sc['public_source_changed'] and not sc['class_or_CTE_layout_changed'],'Reviewed reversible private preparation required')
        need(sc['default_OFF_env_absent'] and sc['explicit_ON_env']=='C08_RV_H18=1' and sc['alpha']==.1 and sc['policy_schema']==2 and sc['main_columns']==66 and sc['manufactured_columns']==40 and sc['physical_objects_retained']==112 and sc['private_objects_required']==2 and sc['actual_link_objects_required']==114,'Exact private scope/schema/object count required')
        need(d['source_archive']==r['source_archive']==sc['source_archive'] and d['source_capture']==r['source_capture']==sc['baseline_source_capture'],'Same original schema2 archive/capture required')
        prep=L/(TAG+'.prepare.json');pr=read(prep);need(pr['passed'] and pr['consumed_stats_unchanged'] and pr['source_capture']==stat(CAP/'source.json'),'Successful actual source preparation required')
        sources={k:Path(bind(sc['private_sources'][k])['path']) for k in ('host','CUDA','header')};archive=Path(bind(sc['source_archive'])['path'])
        oldint=Path(b['intermediate']);ctlog=oldint/'DualSPHysics.tlog/CL.command.1.tlog';ltlog=ctlog.with_name('link.command.1.tlog')
        lines=ctlog.read_text(encoding='utf-16').splitlines();at=[i for i,x in enumerate(lines) if x.startswith('^') and Path(x[1:]).name.lower()=='jsphgpusingle.cpp']
        need(len(at)==1,'One authoritative original host CL block required');clargs=recipe.windows_args(lines[at[0]+1])
        ll=ltlog.read_text(encoding='utf-16').splitlines();need(sum(x.startswith('^') for x in ll)==1,'One original link block required');linkargs=recipe.windows_args(' '.join(x for x in ll if x and not x.startswith('^')))
        # This is an honest NEW inventory, not a historical object seal from the old receipt.
        objects=[stat(p) for p in sorted(oldint.rglob('*.obj'))];linked_original=[Path(x).resolve() for x in linkargs if x.lower().endswith('.obj')]
        start=datetime.datetime.fromisoformat(a['started_utc']).timestamp();end=datetime.datetime.fromisoformat(a['ended_utc']).timestamp()
        need(len(objects)==113 and len(linked_original)==113 and len(set(linked_original))==113 and set(linked_original)=={Path(v['path']).resolve() for v in objects},'Fresh113-object inventory must match actual link membership exactly')
        need(all(start<=v['mtime_ns']/1e9<=end for v in objects),'Original object mtime outside genuine original MSBuild call')
        removed=[v for v in objects if Path(v['path']).name.lower()=='jsphgpusingle.obj'];retained=[v for v in objects if v not in removed]
        need(len(removed)==1 and len(retained)==112 and sum(Path(v['path']).name.lower()=='main.obj' for v in retained)==sum(Path(v['path']).name.lower()=='jsphgpu_ker.cu.obj' for v in retained)==1,'Retain112 including original main and physical CUDA object')
        log=Path(bind(a['log'])['path']);nv=[x.split(b'>',1)[-1].strip().decode('ascii') for x in log.read_bytes().splitlines() if b'nvcc.exe' in x.lower() and b'jsphgpu_ker.cu' in x.lower()]
        need(len(nv)==1,'One actual NVCC command required');cuargs=recipe.windows_args(nv[0]);nvcc=Path(cuargs.pop(0));incs=[x[2:] for x in cuargs if x.startswith('-I')]
        need(len(incs)==1 and Path(incs[0]).resolve()==(nvcc.parent.parent/'include').resolve() and '-I' not in cuargs and not any(x.startswith('--include-path') for x in cuargs),'Original CUDA include recipe changed')
        runtime=[bind(v['destination']) for v in b['runtime']];need(len(runtime)==9 and len({Path(v['path']).name.lower() for v in runtime})==9,'Actual original nine-file runtime required')
        pre=T/'outputs/c08_h18_wend_psi0_pre_r2/data/Part_1000.bi4'
        protected=[stat(pre)]+[stat(q) for name in ('runtime_r5','runtime_r6') for q in (T.parent/'support'/name).iterdir() if q.is_file()]
        protected += [stat(S.parent/'bin/windows'/n) for n in ('DualSPHysics5.2CPU_win64_debug.exe','DualSPHysics5.2_win64_debug.exe','DualSPHysics5.2CPU_win64.exe','DualSPHysics5.2_GEO_win64.exe') if(S.parent/'bin/windows'/n).exists()]
        before=[stat(q) for q in (Path(__file__),NOTE,Path(recipe.__file__),Path(recipe.e.__file__),bp,db,rb,ctlog,ltlog,log,CAP/'source.json',prep)]+[bind(sc['host_diff'])]+[stat(q)for q in sources.values()]+[bind(b[k])for k in ('actual_call','source_capture','source_archive')]+[bind(d['program']),bind(r['program'])]+objects+runtime+protected
        out.mkdir();intdir.mkdir(parents=True);frozen=out/'frozen/src/source';frozen_entries=[]
        with zipfile.ZipFile(archive) as z:
            for info in z.infolist():
                q=PurePosixPath(info.filename);need(not q.is_absolute() and '..' not in q.parts,'Unsafe source archive path')
                if not info.is_dir() and len(q.parts)>=3 and q.parts[:2]==('src','source'):
                    need(q.suffix.lower() not in ('.obj','.o','.pdb','.exe','.dll','.lib'),'Binary in source archive')
                    dest=out/'frozen'/Path(*q.parts);dest.parent.mkdir(parents=True,exist_ok=True)
                    data=sources['host'].read_bytes() if q.as_posix()=='src/source/JSphGpuSingle.cpp' else z.read(info)
                    with dest.open('xb')as f:f.write(data)
                    frozen_entries.append(stat(dest))
            need((frozen/'JSphGpu_ker.cu').read_bytes()==z.read('src/source/JSphGpu_ker.cu'),'Original physical CUDA source must remain unmodified')
        for k in ('CUDA','header'):
            dest=frozen/sources[k].name
            with dest.open('xb')as f:f.write(sources[k].read_bytes())
            frozen_entries.append(stat(dest))
        need(all((frozen/n).is_file() for n in ('JSphGpuSingle.h','JSphGpu.h','JSph.h','JSphGpu_ker.h','FunctionsBasic_iker.h','FunSphKernel_iker.h','JCellSearch_iker.h')),'Complete actual private header closure required');before+=frozen_entries
        hostobj=intdir/'JSphGpuSingle.obj';cudaobj=intdir/'c08_h18_rv_gpu_r1.cu.obj';program=out/Path(b['program']['path']).name
        need(sum(x.lower().startswith('/fo') for x in clargs)==sum(x.lower().startswith('/fd') for x in clargs)==sum(x.lower().endswith('jsphgpusingle.cpp') for x in clargs)==1 and not any(x.lower().startswith(('/yu','/yc','/gl')) for x in clargs),'Original single-source non-PCH/non-GL host recipe required')
        clargs=['/I'+str(frozen),*['/Fo'+str(hostobj) if x.lower().startswith('/fo') else '/Fd'+str(intdir/'host.pdb') if x.lower().startswith('/fd') else str(frozen/'JSphGpuSingle.cpp') if x.lower().endswith('jsphgpusingle.cpp') else x for x in clargs],'/sourceDependencies',str(intdir/'host.dependencies.json')]
        nfd=0
        for i,x in enumerate(cuargs):
            if i and cuargs[i-1]=='-Xcompiler':cuargs[i],n=re.subn(r'(?i)(?<!\S)/Fd[^\s]+',lambda m:'/Fd'+str(intdir/'cuda.pdb'),x);nfd+=n
        need(nfd==1 and cuargs.count('-o')==cuargs.count('--keep-dir')==1 and sum(Path(x).name.lower()=='jsphgpu_ker.cu' for x in cuargs)==1,'One actual NVCC source/object/PDB/keep directory required')
        cuargs=[str(frozen/sources['CUDA'].name) if Path(x).name.lower()=='jsphgpu_ker.cu' else x for x in cuargs];cuargs[cuargs.index('-o')+1]=str(cudaobj);cuargs[cuargs.index('--keep-dir')+1]=str(intdir);cuargs=['-I'+str(frozen),*cuargs]
        opt='/Od' if conf=='Debug' else '/O2';crt='/MTd' if conf=='Debug' else '/MT'
        need(all(x in clargs for x in (opt,crt,'/fp:precise','/openmp')) and all(x in cuargs for x in ('--compile','-use_fast_math','-D_WITHGPU')) and any('compute_86' in x and 'sm_86' in x for x in cuargs) and any(opt in x and crt in x for x in cuargs) and not any('C08_STAGE_TRACE' in x or 'C08_CAUSAL_TRACE' in x or 'rdc=true' in x or x in ('--device-link','-dc') for x in (*clargs,*cuargs)),'Original config/CRT/sm86/non-RDC flags required with no observer macros')
        targets={'/out:':program,'/pdb:':out/(program.stem+'.pdb'),'/implib:':out/(program.stem+'.lib'),'/ltcgout:':intdir/(program.stem+'.iobj'),'/ilk:':out/(program.stem+'.ilk'),'/map:':out/(program.stem+'.map'),'/manifestfile:':intdir/'program.manifest','/pgd:':intdir/'program.pgd','/tlbout:':intdir/'program.tlb','/winmdfile:':intdir/'program.winmd'};seen={};linked=[]
        for arg in linkargs:
            if arg.lower().endswith('.obj') and Path(arg).resolve()==Path(removed[0]['path']).resolve():arg=str(hostobj)
            for key,target in targets.items():
                if arg.lower().startswith(key):need(key not in seen,'Duplicate link output switch');seen[key]=str(target);arg=key+str(target);break
            linked.append(arg)
        linked.append(str(cudaobj));actual=[Path(x).resolve()for x in linked if x.lower().endswith('.obj')]
        need(all(k in seen for k in ('/out:','/pdb:','/implib:','/ltcgout:')) and len(actual)==len(set(actual))==114 and set(actual)=={Path(v['path']).resolve()for v in retained}|{hostobj.resolve(),cudaobj.resolve()},'Exactly112 retained+two private objects and fully rehomed link outputs required')
        setup=subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW);need(setup.returncode==0,'MSVC setup failed')
        env=dict(os.environ);env.update(x.split('=',1)for x in setup.stdout.decode('mbcs').splitlines()if '=' in x and not x.startswith('='));need(env['VCTOOLSVERSION']=='14.36.32532','Actual original MSVC14.36 required')
        for key in list(env):
            if key.upper()in ('CL','_CL_','NVCC_PREPEND_FLAGS','NVCC_APPEND_FLAGS'):env.pop(key)
        cl=Path(env['VCToolsInstallDir'])/'bin/Hostx64/x64/cl.exe';link=cl.with_name('link.exe')
        need('CUDA/v11.7' in str(nvcc).replace('\\','/') and cuargs.count('-ccbin')==1 and '14.36.32532' in cuargs[cuargs.index('-ccbin')+1] and Path(cuargs[cuargs.index('-ccbin')+1]).is_dir(),'Authoritative CUDA11.7/MSVC14.36 ccbin required');before += [stat(cl),stat(nvcc),stat(link)]
        libdirs=[S/'VS']+[Path(x.split(':',1)[1]) if Path(x.split(':',1)[1]).is_absolute()else S/'VS'/x.split(':',1)[1]for x in linked if x.lower().startswith('/libpath:')]+[Path(x)for x in env.get('LIB','').split(';')if x]
        for arg in linked:
            if arg.lower().endswith('.lib')and not arg.startswith('/'):
                candidates=[Path(arg)]if Path(arg).is_absolute()else[p/arg for p in libdirs];lib=next((q for q in candidates if q.is_file()),None);need(lib is not None,'Actual original library missing: '+arg);before.append(stat(lib))
        need(all(stat(v['path'])==v for v in before),'Frozen inputs changed before compilation')
        calls.append(invoke(label+'.host_compile',[str(cl),*clargs],intdir,env));calls.append(invoke(label+'.cuda_compile',[str(nvcc),*cuargs],intdir,env));calls.append(invoke(label+'.link',[str(link),*linked],S/'VS',env))
        deps=read(intdir/'host.dependencies.json');includes={Path(x).resolve()for x in deps['Data']['Includes']};need(all((frozen/n).resolve()in includes for n in ('JSphGpuSingle.h','JSphGpu.h','JSph.h','JSphGpu_ker.h',sources['header'].name)),'Host used another class/header ABI')
        copied=[]
        for entry in runtime:
            dest=out/Path(entry['path']).name;need(not dest.exists(),'Existing private runtime protected');shutil.copy2(entry['path'],dest);v=stat(dest);need((v['bytes'],v['mtime_ns'])==(entry['bytes'],entry['mtime_ns'])and dest.read_bytes()==Path(entry['path']).read_bytes(),'Private runtime copy differs');copied.append(v)
        need(all(stat(v['path'])==v for v in before),'Original object/source/program/PRE/runtime changed during build')
        warning_lines=[line for q in calls for line in Path(read(q['path'])['log']['path']).read_bytes().decode('mbcs').splitlines()if re.search(r'\bwarning\b',line,re.I)]
        save(check,dict(stage=label+'.build',passed=True,configuration=conf,program=stat(program),source_capture=stat(CAP/'source.json'),source_archive=stat(archive),baseline_source_capture=b['source_capture'],private_sources={k:stat(v)for k,v in sources.items()},baseline_source_build=stat(bp),original_actual_build_call=b['actual_call'],original_build_started_utc=a['started_utc'],original_build_ended_utc=a['ended_utc'],original_objects_historical_seal_claimed=False,fresh_original_objects=objects,original113_mtimes_within_actual_build=True,original_link_membership_exact=True,retained_original_objects=112,private_objects=2,actual_link_objects=114,retained_object_stats=retained,new_private_objects=[stat(hostobj),stat(cudaobj)],actual_link_inputs=[str(q)for q in actual],original_host_recipe=stat(ctlog),original_CUDA_recipe_log=stat(log),original_link_recipe=stat(ltlog),link_output_flags=seen,private_header_dependencies=stat(intdir/'host.dependencies.json'),frozen_sources=frozen_entries,IntDir=str(intdir),OutDir=str(out),runtime=copied,calls=calls,warning_lines=warning_lines,new_warning_free_claimed=False,consumed=before,consumed_stats_unchanged=True,public_source_changed=False,class_or_CTE_layout_changed=False,original_physical_CUDA_objects_retained=True,ON_runtime_env='C08_RV_H18=1',OFF_env_absent_no_RV_allocation_launch_sidecar=True,main_columns=66,manufactured_columns=40,policy_schema=2,compile_invocations=2,link_invocations=1,full_project_builds=0,solver_invocations=0,help_invocations=0,memcheck_invocations=0,native_decodes=0,physical_acceptance=False,SHA_scans=0))
        print('C08_H18_RV_PRIVATE_BUILD_PASSED',conf,program,flush=True)
    except Exception as error:
        if not check.exists():save(check,dict(stage=label+'.build',passed=False,configuration=conf,first_failure=str(error),calls=calls,consumed=before,solver_invocations=0,native_decodes=0,physical_acceptance=False,SHA_scans=0))
        raise

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--configuration',choices=('Debug','Release'),required=True);p.add_argument('--execution-authorized',action='store_true');a=p.parse_args();need(a.execution_authorized,'Independent root full-read/build admission required');build(a.configuration)
