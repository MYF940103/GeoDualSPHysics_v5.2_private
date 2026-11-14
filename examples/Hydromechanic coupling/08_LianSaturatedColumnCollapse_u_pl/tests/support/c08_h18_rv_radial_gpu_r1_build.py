"""Build only two private radial objects against the112 sealed physical objects.

Author-only until root separately reviews/prepares the source and admits a build:
  D:/anaconda3/python.exe -X utf8 -B tests/support/c08_h18_rv_radial_gpu_r1_build.py --configuration Debug --execution-authorized
Repeat with Release only under its own root admission. Never invokes a program,
help, solver, reader, sanitizer, VTK, Git or notification. No old object or output
is overwritten. New CU inherits the actual config's NVCC flags and appends only
--fmad=false; the private host is genuinely recompiled in both configurations.
"""
import argparse,os,re,shutil,subprocess,zipfile
from pathlib import Path,PurePosixPath
import upl_c08_shepard_release_r1_build as recipe

T,L,S=recipe.T,recipe.L,recipe.S
need,read,stat,bind,save=recipe.need,recipe.read,recipe.stat,recipe.bind,recipe.save
TAG='c08_h18_rv_radial_gpu_r1';CAP=T/'outputs'/(TAG+'_source');NOTE=T/'notes'/(TAG+'.md')
OPERATOR='compression_only_radial_residual_limiter'


def unchanged(entries):
    for q in entries:bind(q)


def invoke(label,step,argv,cwd,env,calls):
    """Use existing actual process handles; keep a failed tool's genuine receipt."""
    call=L/(label+'.'+step+'.call.json')
    try:return recipe.invoke(label+'.'+step,[str(x) for x in argv],cwd,env)
    finally:
        if call.exists():calls.append(stat(call))


def sealed_recipe(conf,used):
    path=L/('c08_h18_rv_gpu_'+conf+'_r2.build.json');b=read(path);used.append(stat(path))
    need(b['passed'] and b['configuration']==conf and b['consumed_stats_unchanged']
        and b['retained_original_objects']==112 and b['private_objects']==2 and b['actual_link_objects']==114
        and b['compile_invocations']==2 and b['link_invocations']==1 and len(b['calls'])==3
        and b['original113_mtimes_within_actual_build'] and b['original_link_membership_exact']
        and b['original_physical_CUDA_objects_retained'] and not b['public_source_changed']
        and not b['class_or_CTE_layout_changed'],'Actual sealed config-specific112+2 original recipe required')
    calls=[]
    for entry in b['calls']:
        bind(entry);used.append(entry);a=read(entry['path']);calls.append(a)
        need(a['actual_Popen_wait_exit']==a['actual_Win32_exit']==0 and a['ownership_failure'] is None,'Original CL/NVCC/link handle exits must genuinely pass')
        used.append(bind(a['log']))
    base=read(bind(b['baseline_source_build'])['path']);actual=read(bind(b['original_actual_build_call'])['path'])
    need(base['passed'] and base['configuration']==conf and base['consumed_stats_unchanged']
        and actual['actual_Popen_wait_exit']==actual['actual_Win32_exit']==0 and actual['ownership_failure'] is None
        and '/p:Configuration='+conf in actual['arguments'] and '/p:VCToolsVersion=14.36.32532' in actual['arguments'],
        'Original authoritative schema2 solution/configuration/toolset receipt required')
    used += [bind(b[k]) for k in ('program','source_capture','source_archive','baseline_source_capture','baseline_source_build','original_actual_build_call',
        'original_host_recipe','original_CUDA_recipe_log','original_link_recipe')]
    retained=[bind(q) for q in b['retained_object_stats']];oldprivate=[bind(q) for q in b['new_private_objects']]
    runtime=[bind(q) for q in b['runtime']];used += retained+oldprivate+runtime
    need(len(retained)==112 and len({Path(q['path']).resolve() for q in retained})==112 and len(oldprivate)==2
        and Path(oldprivate[0]['path']).name=='JSphGpuSingle.obj' and Path(oldprivate[1]['path']).name=='c08_h18_rv_gpu_r1.cu.obj'
        and sum(Path(q['path']).name.lower()=='main.obj' for q in retained)==1
        and sum(Path(q['path']).name.lower()=='jsphgpu_ker.cu.obj' for q in retained)==1
        and len(runtime)==9 and len({Path(q['path']).name.lower() for q in runtime})==9,'Exact retained objects/private predecessor/runtime differs')
    return path,b,calls,retained,oldprivate,runtime


def freeze_sources(out,archive,sources):
    frozen=out/'frozen/src/source';entries=[];hosts=0
    with zipfile.ZipFile(archive) as z:
        for info in z.infolist():
            q=PurePosixPath(info.filename);need(not q.is_absolute() and '..' not in q.parts,'Unsafe original source archive member')
            if info.is_dir() or len(q.parts)<3 or q.parts[:2]!=('src','source'):continue
            need(q.suffix.lower() not in ('.obj','.o','.pdb','.exe','.dll','.lib'),'Binary artifact in source-only archive')
            dest=out/'frozen'/Path(*q.parts);dest.parent.mkdir(parents=True,exist_ok=True)
            if q.as_posix()=='src/source/JSphGpuSingle.cpp':data=sources['host'].read_bytes();hosts+=1
            else:data=z.read(info)
            with dest.open('xb') as f:f.write(data)
            entries.append(stat(dest))
        need(hosts==1 and (frozen/'JSphGpu_ker.cu').read_bytes()==z.read('src/source/JSphGpu_ker.cu'),'One private host replacement; original physical CUDA source must remain exact')
    for key in ('CUDA','header'):
        dest=frozen/sources[key].name
        with dest.open('xb') as f:f.write(sources[key].read_bytes())
        entries.append(stat(dest))
    need(all((frozen/name).is_file() for name in ('JSphGpuSingle.h','JSphGpu.h','JSph.h','JSphGpu_ker.h','FunctionsBasic_iker.h','FunSphKernel_iker.h','JCellSearch_iker.h')),
        'Full archived class/kernel header closure required')
    return frozen,entries


def commands(conf,b,prior,sources,frozen,intdir,out,retained,oldprivate):
    hostcall,cudacall,linkcall=prior;clargs=list(hostcall['arguments']);cuargs=list(cudacall['arguments']);linked=list(linkcall['arguments'])
    oldfrozen=Path(b['OutDir'])/'frozen/src/source';hostobj=intdir/'JSphGpuSingle.obj';cudaobj=intdir/(TAG+'.cu.obj')
    program=out/Path(b['program']['path']).name
    old_host_source=str(oldfrozen/'JSphGpuSingle.cpp');old_cu_source=str(oldfrozen/'c08_h18_rv_gpu_r1.cu')
    host_include='/I'+str(oldfrozen);cu_include='-I'+str(oldfrozen)
    need(clargs.count(host_include)==clargs.count(old_host_source)==clargs.count('/sourceDependencies')==1
        and sum(x.lower().startswith('/fo') for x in clargs)==sum(x.lower().startswith('/fd') for x in clargs)==1
        and not any(x.lower().startswith(('/yu','/yc','/gl')) for x in clargs),'One original single-source/non-PCH host recipe required')
    for index,x in enumerate(clargs):
        if x==host_include:clargs[index]='/I'+str(frozen)
        elif x==old_host_source:clargs[index]=str(frozen/'JSphGpuSingle.cpp')
        elif x.lower().startswith('/fo'):clargs[index]='/Fo'+str(hostobj)
        elif x.lower().startswith('/fd'):clargs[index]='/Fd'+str(intdir/'host.pdb')
    clargs[clargs.index('/sourceDependencies')+1]=str(intdir/'host.dependencies.json')
    need(cuargs.count(cu_include)==cuargs.count(old_cu_source)==cuargs.count('-o')==cuargs.count('--keep-dir')==cuargs.count('-ccbin')==1
        and '-use_fast_math' in cuargs and '--use-local-env' in cuargs and not any('fmad' in x.lower() for x in cuargs),'One original fast-math/non-FMA-overridden CUDA recipe required')
    need(Path(cuargs[cuargs.index('-o')+1]).resolve()==Path(oldprivate[1]['path']).resolve(),'Actual old CU object output differs')
    replacements=0
    for index,x in enumerate(cuargs):
        if x==cu_include:cuargs[index]='-I'+str(frozen)
        elif x==old_cu_source:cuargs[index]=str(frozen/sources['CUDA'].name)
        elif index and cuargs[index-1]=='-Xcompiler':
            cuargs[index],count=re.subn(r'(?i)(?<!\S)/Fd[^\s]+',lambda match:'/Fd'+str(intdir/'cuda.pdb'),x);replacements+=count
    need(replacements==1,'One original NVCC host-compiler PDB output required')
    cuargs[cuargs.index('-o')+1]=str(cudaobj);cuargs[cuargs.index('--keep-dir')+1]=str(intdir)
    cuargs.append('--fmad=false')
    opt='/Od' if conf=='Debug' else '/O2';crt='/MTd' if conf=='Debug' else '/MT'
    need(all(x in clargs for x in (opt,crt,'/fp:precise','/openmp')) and all(x in cuargs for x in ('--compile','-use_fast_math','-D_WITHGPU'))
        and any('compute_86' in x and 'sm_86' in x for x in cuargs) and any(opt in x and crt in x for x in cuargs)
        and ('-G' in cuargs)==(conf=='Debug') and cuargs[-1]=='--fmad=false'
        and not any('C08_STAGE_TRACE' in x or 'C08_CAUSAL_TRACE' in x or 'rdc=true' in x or x in ('--device-link','-dc') for x in (*clargs,*cuargs)),
        'Sealed config/CRT/sm86/non-RDC flags must remain; only the new CU gets final FMA override')
    outputs={'/out:':program,'/pdb:':out/(program.stem+'.pdb'),'/implib:':out/(program.stem+'.lib'),'/ltcgout:':intdir/(program.stem+'.iobj'),
        '/ilk:':out/(program.stem+'.ilk'),'/map:':out/(program.stem+'.map'),'/manifestfile:':intdir/'program.manifest','/pgd:':intdir/'program.pgd',
        '/tlbout:':intdir/'program.tlb','/winmdfile:':intdir/'program.winmd'}
    seen={};replaced=[0,0]
    for index,x in enumerate(linked):
        for k,(old,new) in enumerate(zip(oldprivate,(hostobj,cudaobj))):
            if x.lower().endswith('.obj') and Path(x).resolve()==Path(old['path']).resolve():x=str(new);replaced[k]+=1;break
        for key,target in outputs.items():
            if x.lower().startswith(key):need(key not in seen,'Duplicate link output switch');seen[key]=str(target);x=key+str(target);break
        linked[index]=x
    actual=[Path(x).resolve() for x in linked if x.lower().endswith('.obj')]
    need(replaced==[1,1] and all(k in seen for k in ('/out:','/pdb:','/implib:','/ltcgout:')) and len(actual)==len(set(actual))==114
        and set(actual)=={Path(q['path']).resolve() for q in retained}|{hostobj.resolve(),cudaobj.resolve()},'Exactly112 retained + new host + new CU with independent link outputs required')
    return clargs,cuargs,linked,hostobj,cudaobj,program,actual,seen


def build(conf):
    label='c08_h18_rv_radial_gpu_'+conf+'_r1';out=T/'outputs'/label;intdir=Path(os.environ['TEMP'])/TAG/conf
    check=L/(label+'.build.json');calls=[];before=[]
    need(' ' not in str(intdir.resolve()) and not out.exists() and not intdir.exists()
        and all(not (L/(label+x)).exists() for x in ('.build.json','.host_compile.call.json','.host_compile.log','.cuda_compile.call.json','.cuda_compile.log','.link.call.json','.link.log')),
        'Fresh isolated output, no-space IntDir and new immutable tool receipts required')
    try:
        bp,b,prior,retained,oldprivate,runtime=sealed_recipe(conf,before)
        capture=CAP/'source.json';prep=L/(TAG+'.prepare.json');sc=read(capture);pr=read(prep)
        need(sc['passed'] and sc['prepared_only'] and sc['exact_reverse_original_host_bytes'] and sc['original_CUDA_members_unchanged']
            and not sc['public_source_changed'] and not sc['class_or_CTE_layout_changed'] and sc['policy_schema']==3
            and sc['operator']==OPERATOR and sc['alpha']==.1 and sc['physical_objects_retained']==112 and sc['private_objects_required']==2
            and sc['actual_link_objects_required']==114 and sc['default_OFF_env_absent'] and sc['explicit_ON_env']=='C08_RV_RADIAL_H18=1',
            'Reviewed reversible private radial-only source scope required')
        need(sc['main_columns']==87 and sc['manufactured_columns']==57 and sc['fixture_columns']==6,
            'Exact new radial87/57/6 sidecar schema required; old66-column semantics are incompatible')
        need(pr['passed'] and pr['consumed_stats_unchanged'] and pr['source_capture']==stat(capture)
            and pr['private_sources']==sc['private_sources'] and b['source_archive']==sc['source_archive']
            and b['baseline_source_capture']==sc['baseline_source_capture'] and b['baseline_source_build'] in sc['baseline_builds'],
            'Prepared radial sources must retain the actual authoritative schema2 source archive/capture')
        sources={key:Path(bind(sc['private_sources'][key])['path']) for key in ('host','CUDA','header')}
        need(sources['host'].name=='JSphGpuSingle.cpp' and sources['CUDA'].name==TAG+'.cu' and sources['header'].name==TAG+'.h',
            'Only the three agreed private source filenames are admitted')
        archive=Path(bind(sc['source_archive'])['path']);before += [stat(q) for q in (Path(__file__),NOTE,Path(recipe.__file__),Path(recipe.e.__file__),capture,prep)]
        before += [bind(sc['host_diff']),*sc['private_sources'].values(),bind(sc['source_archive']),bind(sc['baseline_source_capture'])]
        for q in pr['consumed']:before.append(bind(q))
        protected=[T/'outputs/c08_h18_wend_psi0_pre_r2/data/Part_1000.bi4']
        protected += [q for name in ('runtime_r5','runtime_r6') for q in (T.parent/'support'/name).iterdir() if q.is_file()]
        protected += [S.parent/'bin/windows'/name for name in ('DualSPHysics5.2CPU_win64_debug.exe','DualSPHysics5.2_win64_debug.exe','DualSPHysics5.2CPU_win64.exe','DualSPHysics5.2_GEO_win64.exe') if (S.parent/'bin/windows'/name).is_file()]
        before += [stat(q) for q in protected];unchanged(before)
        out.mkdir();intdir.mkdir(parents=True);frozen,frozen_entries=freeze_sources(out,archive,sources);before += frozen_entries
        clargs,cuargs,linked,hostobj,cudaobj,program,actual,seen=commands(conf,b,prior,sources,frozen,intdir,out,retained,oldprivate)
        setup=subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',
            stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
        need(setup.returncode==0,'Original MSVC environment setup failed')
        env=dict(os.environ);env.update(x.split('=',1) for x in setup.stdout.decode('mbcs').splitlines() if '=' in x and not x.startswith('='))
        need(env['VCTOOLSVERSION']=='14.36.32532','Same authoritative MSVC14.36 toolset required')
        for key in list(env):
            if key.upper() in ('CL','_CL_','LINK','_LINK_','NVCC_PREPEND_FLAGS','NVCC_APPEND_FLAGS'):env.pop(key)
        cl=Path(prior[0]['program']);nvcc=Path(prior[1]['program']);link=Path(prior[2]['program']);ccbin=Path(cuargs[cuargs.index('-ccbin')+1])
        need(cl.resolve()==(Path(env['VCToolsInstallDir'])/'bin/Hostx64/x64/cl.exe').resolve() and link.resolve()==cl.with_name('link.exe').resolve()
            and 'CUDA/v11.7' in str(nvcc).replace('\\','/') and ccbin.is_dir() and '14.36.32532' in str(ccbin),'Actual sealed CL/NVCC/link/ccbin tool identity required')
        before += [stat(cl),stat(nvcc),stat(link)]
        cudaenv=dict(env);cuda_path=env.get('Path',env.get('PATH',''))
        for key in list(cudaenv):
            if key.upper()=='PATH':cudaenv.pop(key)
        cudaenv['PATH']=str(ccbin)+os.pathsep+cuda_path
        linkcwd=Path(prior[2]['cwd']);libdirs=[linkcwd]+[Path(x.split(':',1)[1]) if Path(x.split(':',1)[1]).is_absolute() else linkcwd/x.split(':',1)[1] for x in linked if x.lower().startswith('/libpath:')]
        libdirs += [Path(x) for x in env.get('LIB','').split(';') if x]
        for arg in linked:
            if arg.lower().endswith('.lib') and not arg.startswith('/'):
                possible=[Path(arg)] if Path(arg).is_absolute() else [q/arg for q in libdirs];library=next((q for q in possible if q.is_file()),None)
                need(library is not None,'Actual sealed link library missing: '+arg);before.append(stat(library))
        unchanged(before)
        invoke(label,'host_compile',[cl,*clargs],intdir,env,calls)
        invoke(label,'cuda_compile',[nvcc,*cuargs],intdir,cudaenv,calls)
        invoke(label,'link',[link,*linked],linkcwd,env,calls)
        deps=read(intdir/'host.dependencies.json');includes={Path(x).resolve() for x in deps['Data']['Includes']}
        need(Path(deps['Data']['Source']).resolve()==(frozen/'JSphGpuSingle.cpp').resolve()
            and all((frozen/name).resolve() in includes for name in ('JSphGpuSingle.h','JSphGpu.h','JSph.h','JSphGpu_ker.h',sources['header'].name)),
            'Actual private host compile must use the frozen class ABI and new radial header')
        copied=[]
        for entry in runtime:
            dest=out/Path(entry['path']).name;need(not dest.exists(),'Existing new runtime protected');shutil.copy2(entry['path'],dest);value=stat(dest)
            need((value['bytes'],value['mtime_ns'])==(entry['bytes'],entry['mtime_ns']) and dest.read_bytes()==Path(entry['path']).read_bytes(),'Private config-specific runtime copy differs')
            copied.append(value)
        unchanged(before)
        warnings=[line for q in calls for line in Path(read(q['path'])['log']['path']).read_bytes().decode('mbcs').splitlines() if re.search(r'\bwarning\b',line,re.I)]
        save(check,dict(stage=label+'.build',passed=True,configuration=conf,program=stat(program),source_capture=stat(capture),source_archive=stat(archive),
            baseline_source_capture=b['baseline_source_capture'],baseline_source_build=b['baseline_source_build'],recipe_build=stat(bp),recipe_calls=b['calls'],
            private_sources={k:stat(q) for k,q in sources.items()},retained_original_objects=112,private_objects=2,actual_link_objects=114,
            retained_object_stats=retained,new_private_objects=[stat(hostobj),stat(cudaobj)],old_private_objects_not_adopted=oldprivate,
            host_object_recompiled=True,actual_link_inputs=[str(q) for q in actual],frozen_sources=frozen_entries,
            private_header_dependencies=stat(intdir/'host.dependencies.json'),link_output_flags=seen,IntDir=str(intdir),OutDir=str(out),runtime=copied,calls=calls,
            new_CUDA_flag='--fmad=false',flag_after_inherited_fast_math=True,all_other_NVCC_flags_inherited_except_new_sources_outputs=True,
            original_physical_CUDA_objects_retained=True,original_physical_TUs_compiled=0,original_objects_historical_seal_reinvented=False,
            policy_schema=sc['policy_schema'],operator=sc['operator'],alpha=sc['alpha'],main_columns=sc['main_columns'],manufactured_columns=sc['manufactured_columns'],fixture_columns=sc['fixture_columns'],
            ON_runtime_env=sc['explicit_ON_env'],OFF_env_absent_no_RV_allocation_launch_sidecar=True,
            OFF_equivalence_scope='Bound source scope only; independent native implementation regression is pending',
            Debug_not_Release_bit_truth=True,build_not_implementation_or_physical_acceptance=True,warning_lines=warnings,new_warning_free_claimed=False,
            consumed=before,consumed_stats_unchanged=True,public_source_changed=False,class_or_CTE_layout_changed=False,canonical_programs_changed=False,
            compile_invocations=2,host_compile_invocations=1,CUDA_compile_invocations=1,link_invocations=1,full_project_builds=0,solver_invocations=0,
            help_invocations=0,memcheck_invocations=0,native_decodes=0,VTK_invocations=0,physical_acceptance=False,SHA_scans=0))
        print('C08_H18_RADIAL_PRIVATE_BUILD_PASSED',conf,program,flush=True)
    except Exception as error:
        if not check.exists():save(check,dict(stage=label+'.build',passed=False,configuration=conf,first_failure=str(error),calls=calls,consumed=before,
            partial_outputs_preserved=True,solver_invocations=0,native_decodes=0,physical_acceptance=False,SHA_scans=0))
        raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--configuration',choices=('Debug','Release'),required=True)
    parser.add_argument('--execution-authorized',action='store_true');args=parser.parse_args()
    need(args.execution_authorized,'Author-only until independent root source/recipe review and single build admission');build(args.configuration)
