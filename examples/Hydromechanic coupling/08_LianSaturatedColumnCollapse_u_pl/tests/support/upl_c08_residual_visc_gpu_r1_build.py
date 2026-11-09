"""Private residual-viscosity GPU build only: one host TU, one CUDA TU,111 retained objects."""
import argparse,os,re,shutil,subprocess,zipfile
from pathlib import Path,PurePosixPath
import upl_c08_shepard_release_r1_build as recipe
T,L,S=recipe.T,recipe.L,recipe.S
need,read,stat,bind,save,invoke=recipe.need,recipe.read,recipe.stat,recipe.bind,recipe.save,recipe.invoke
TAG='upl_c08_residual_visc_gpu_r1';CAP=T/'outputs'/(TAG+'_source');NOTE=T/'notes/upl_c08_residual_visc_gpu_build_r1.md'
MACRO='C08_RESIDUAL_VISCOSITY_CANDIDATE';OFF='C08_RESIDUAL_VISCOSITY_ALPHA0';PROFILES=('Debug','Release_alpha0','Release')
SOURCE_KEYS={'private_host_source':'src/source/JSphGpuSingle.cpp','private_gpu_header':'src/source/JSphGpu_ker.h','private_gpu_source':'src/source/JSphGpu_ker.cu'}
CPU=L/'upl_c08_residual_visc_cpu_r2.check.json';MATH=L/'upl_c08_residual_visc_gpu_math_r1.check.json';RUNTIME=T.parent/'support/runtime_r6'

def baseline(conf):
 p=L/('upl_c08_bedkeep_'+conf+'_r1.build.json');b=read(p);need(b['passed'] and b['configuration']==conf and b['actual_typed_exit_code']==b['actual_Win32_exit']==0 and b['source_stats_unchanged'] and len(b['project_objects'])==113,'Closed original113-object GPU configuration required');return p,b

def build(profile):
 conf='Debug' if profile=='Debug' else 'Release';alpha=0. if profile=='Release_alpha0' else .1;label='upl_c08_residual_visc_gpu_'+profile+'_r1';out=T/'outputs'/label;intdir=Path(os.environ['TEMP'])/TAG/profile;check=L/(label+'.build.json');before=[];calls=[]
 need(' ' not in str(intdir.resolve()) and not out.exists() and not intdir.exists() and all(not(L/(label+s)).exists() for s in ('.build.json','.host_compile.call.json','.host_compile.log','.cuda_compile.call.json','.cuda_compile.log','.link.call.json','.link.log')),'Fresh isolated OutDir/no-space IntDir and receipts required')
 try:
  cpu,math=read(CPU),read(MATH);need(cpu['passed'] and cpu['consumed_stats_unchanged'] and cpu['force_evaluations']==cpu['Darcy_evaluations']==4 and cpu['actual_physical_steps']==0 and cpu['OFF_baseline_alignment']['mismatched_fields']==0 and math['passed'] and math['consumed_stats_unchanged'] and math['host_function_calls']==8 and math['memcheck_zero_errors_and_leaks'],'Actual closed CPU four-call and GPU-math eight-case prerequisites required')
  bp,b=baseline(conf);db,d=baseline('Debug');rb,r=baseline('Release');sc=read(CAP/'source.json');need(d['source_capture']==r['source_capture']==sc['baseline_capture'] and d['source_archive']==r['source_archive']==sc['baseline_archive'],'Private capture must derive from the same closed bedkeep source')
  need(sc['only_three_archive_members_changed'] and sc['macro_off_reverse_original_bytes_exact'] and sc['all_other_archive_member_bytes_exact'] and sc['release_only'] and sc['true_cell_neighbor_search'] and sc['physical_objects_required']==2 and sc['retained_original_objects']==111 and sc['actual_link_objects']==113 and not sc['class_layout_changed'] and not sc['CTE_layout_changed'] and not sc['public_interfaces_changed'] and sc['candidate_macro']==MACRO and sc['alpha0_macro']==OFF,'Read-reviewed three-file reversible candidate source proof/ABI/macros required')
  sources={k:Path(bind(sc[k])['path']) for k in SOURCE_KEYS};archive=Path(bind(sc['archive'])['path']);objects=b['project_objects'];removed={Path(e['path']).name.lower():e for e in objects if Path(e['path']).name.lower() in ('jsphgpusingle.obj','jsphgpu_ker.cu.obj')};retained=[e for e in objects if e not in removed.values()];need(len(removed)==2 and len(retained)==111 and sum(Path(e['path']).name.lower()=='main.obj' for e in retained)==1,'Exactly111 original objects including main must remain')
  oldint=Path(removed['jsphgpusingle.obj']['path']).parent;ctlog=oldint/'DualSPHysics.tlog/CL.command.1.tlog';ltlog=ctlog.with_name('link.command.1.tlog');lines=ctlog.read_text(encoding='utf-16').splitlines();at=[i for i,x in enumerate(lines) if x.startswith('^') and Path(x[1:]).name.lower()=='jsphgpusingle.cpp'];need(len(at)==1,'One authoritative Single CL command required');clargs=recipe.windows_args(lines[at[0]+1]);ll=ltlog.read_text(encoding='utf-16').splitlines();need(sum(x.startswith('^') for x in ll)==1,'One original link block required');linkargs=recipe.windows_args(' '.join(x for x in ll if x and not x.startswith('^')))
  actual=read(bind(b['actual_call'])['path']);log=Path(bind(actual['log'])['path']);nv=[x.split(b'>',1)[1].strip().decode('ascii') for x in log.read_bytes().splitlines() if b'nvcc.exe' in x.lower() and b'jsphgpu_ker.cu' in x.lower()];need(len(nv)==1,'One actual ASCII NVCC command required');cuargs=recipe.windows_args(nv[0]);nvcc=Path(cuargs.pop(0));incs=[x[2:] for x in cuargs if x.startswith('-I')];need(len(incs)==1 and Path(incs[0]).resolve()==(nvcc.parent.parent/'include').resolve() and '-I' not in cuargs and not any(x.startswith('--include-path') for x in cuargs),'Original CUDA-only include list changed')
  runtime=[stat(p) for p in sorted(RUNTIME.iterdir()) if p.is_file() and (p.suffix.lower()=='.dll' or p.name=='DsphConfig.xml')];need(len(runtime)==7,'Seven original GPU runtime dependencies required');pre=read(L/'upl_c08_causal_window_GPU_r1.run.json')['source_pre_file'];protected=[stat(S.parent/'bin/windows'/n) for n in ('DualSPHysics5.2CPU_win64_debug.exe','DualSPHysics5.2_win64_debug.exe','DualSPHysics5.2CPU_win64.exe','DualSPHysics5.2_GEO_win64.exe') if(S.parent/'bin/windows'/n).exists()]+[stat(p) for name in ('runtime_r5','runtime_r6') for p in (T.parent/'support'/name).iterdir() if p.is_file()]+[bind(pre)]
  before=[stat(p) for p in (Path(__file__),NOTE,Path(recipe.__file__),Path(recipe.e.__file__),CPU,MATH,bp,db,rb,ctlog,ltlog,log,CAP/'source.json')]+[bind(sc[k]) for k in (*SOURCE_KEYS,'archive','diff')]+[bind(b[k]) for k in ('source_capture','source_archive','actual_call')]+[bind(d['program']),bind(r['program'])]+[bind(e) for e in objects]+runtime+protected
  out.mkdir();intdir.mkdir(parents=True);frozen=out/'frozen/src/source';frozen_entries=[]
  with zipfile.ZipFile(archive) as z:
   need(all(z.read(member)==sources[k].read_bytes() for k,member in SOURCE_KEYS.items()),'Private CPP/header/CU disagree with their source archive')
   for info in z.infolist():
    p=PurePosixPath(info.filename);need(not p.is_absolute() and '..' not in p.parts,'Invalid archived source path')
    if not info.is_dir() and len(p.parts)>=3 and p.parts[:2]==('src','source'):
     need(p.suffix.lower() not in ('.obj','.o','.pdb','.exe','.dll','.lib'),'No binary/object cache copied');dest=out/'frozen'/Path(*p.parts);dest.parent.mkdir(parents=True,exist_ok=True)
     with dest.open('xb') as f:f.write(z.read(info))
     frozen_entries.append(stat(dest))
  need(all((frozen/n).is_file() for n in ('JSphGpuSingle.h','JSphGpu.h','JSph.h','JSphGpu_ker.h','JSphGpu_mdbc_ker.cuh','JSphGpu_InOut_iker.cu')),'Complete frozen header/included-CUDA closure required');before+=frozen_entries
  definitions=[MACRO]+([OFF] if alpha==0. else []);hostobj=intdir/'JSphGpuSingle.obj';cudaobj=intdir/'JSphGpu_ker.cu.obj';program=out/Path(b['program']['path']).name
  need(sum(x.lower().startswith('/fo') for x in clargs)==sum(x.lower().startswith('/fd') for x in clargs)==sum(x.lower().endswith('jsphgpusingle.cpp') for x in clargs)==1 and not any(x.lower().startswith(('/yu','/yc','/gl')) for x in clargs),'Original one-source non-PCH/non-GL CL recipe required')
  clargs=['/I'+str(frozen),*['/D'+x for x in definitions],*['/Fo'+str(hostobj) if x.lower().startswith('/fo') else '/Fd'+str(intdir/'host.pdb') if x.lower().startswith('/fd') else str(frozen/'JSphGpuSingle.cpp') if x.lower().endswith('jsphgpusingle.cpp') else x for x in clargs],'/sourceDependencies',str(intdir/'host.dependencies.json')]
  nfd=0
  for i,x in enumerate(cuargs):
   if i and cuargs[i-1]=='-Xcompiler':cuargs[i],n=re.subn(r'(?i)(?<!\S)/Fd[^\s]+','/Fdcuda.pdb',x);nfd+=n
  need(nfd==1 and cuargs.count('-o')==cuargs.count('--keep-dir')==1,'One original NVCC host-PDB/object/keep-dir required');cuargs=[str(frozen/'JSphGpu_ker.cu') if Path(x).name.lower()=='jsphgpu_ker.cu' else x for x in cuargs];cuargs[cuargs.index('-o')+1]=str(cudaobj);cuargs[cuargs.index('--keep-dir')+1]=str(intdir);cuargs=['-I'+str(frozen),*['-D'+x for x in definitions],*cuargs]
  opt='/Od' if conf=='Debug' else '/O2';crt='/MTd' if conf=='Debug' else '/MT';need(all(x in clargs for x in (opt,crt,'/fp:precise','/openmp')) and all(x in cuargs for x in ('--compile','-use_fast_math','-D_WITHGPU')) and any('compute_86' in x and 'sm_86' in x for x in cuargs) and any(opt in x and crt in x for x in cuargs) and not any('C08_STAGE_TRACE' in x or 'C08_CAUSAL_TRACE' in x or 'rdc=true' in x or x in ('--device-link','-dc') for x in (*clargs,*cuargs)),'Original config/sm86/CRT/fast-math/non-RDC flags required; no trace macros')
  targets={'/out:':program,'/pdb:':out/(program.stem+'.pdb'),'/implib:':out/(program.stem+'.lib'),'/ltcgout:':intdir/(program.stem+'.iobj'),'/ilk:':out/(program.stem+'.ilk'),'/map:':out/(program.stem+'.map'),'/manifestfile:':intdir/'program.manifest','/pgd:':intdir/'program.pgd','/tlbout:':intdir/'program.tlb','/winmdfile:':intdir/'program.winmd'};seen={};linked=[]
  for arg in linkargs:
   if arg.lower().endswith('.obj'):
    if Path(arg).resolve()==Path(removed['jsphgpusingle.obj']['path']).resolve():arg=str(hostobj)
    elif Path(arg).resolve()==Path(removed['jsphgpu_ker.cu.obj']['path']).resolve():arg=str(cudaobj)
   for key,target in targets.items():
    if arg.lower().startswith(key):need(key not in seen,'Duplicate original link-output flag');seen[key]=str(target);arg=key+str(target);break
   linked.append(arg)
  linkobjects=[Path(x).resolve() for x in linked if x.lower().endswith('.obj')];need(all(k in seen for k in ('/out:','/pdb:','/implib:','/ltcgout:')) and len(linkobjects)==113 and set(linkobjects)=={Path(e['path']).resolve() for e in retained}|{hostobj.resolve(),cudaobj.resolve()},'Link must be111 retained+two private objects with all original outputs rehomed')
  setup=subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW);need(setup.returncode==0,'MSVC setup failed');env=dict(os.environ);env.update(x.split('=',1) for x in setup.stdout.decode('mbcs').splitlines() if '=' in x and not x.startswith('='));need(env['VCTOOLSVERSION']=='14.36.32532','Original MSVC14.36 required')
  for key in list(env):
   if key.upper() in ('CL','_CL_','NVCC_PREPEND_FLAGS','NVCC_APPEND_FLAGS'):env.pop(key)
  cl=Path(env['VCToolsInstallDir'])/'bin/Hostx64/x64/cl.exe';link=cl.with_name('link.exe');need('CUDA/v11.7' in str(nvcc).replace('\\','/') and cuargs.count('-ccbin')==1 and Path(cuargs[cuargs.index('-ccbin')+1]).resolve()==cl.parent.resolve(),'Authoritative CUDA11.7/MSVC14.36 tools required');before += [stat(cl),stat(nvcc),stat(link)]
  libdirs=[S/'VS']+[Path(x.split(':',1)[1]) if Path(x.split(':',1)[1]).is_absolute() else S/'VS'/x.split(':',1)[1] for x in linked if x.lower().startswith('/libpath:')]+[Path(x) for x in env.get('LIB','').split(';') if x]
  for arg in linked:
   # /IMPLIB is an output switch, never an input library.
   if arg.lower().endswith('.lib') and not arg.startswith('/'):
    candidates=[Path(arg)] if Path(arg).is_absolute() else[p/arg for p in libdirs];lib=next((p for p in candidates if p.is_file()),None);need(lib is not None,'Original explicit link library missing: '+arg);before.append(stat(lib))
  need(all(stat(e['path'])==e for e in before),'Frozen original/source/runtime changed before build');calls.append(invoke(label+'.host_compile',[str(cl),*clargs],intdir,env));calls.append(invoke(label+'.cuda_compile',[str(nvcc),*cuargs],intdir,env));calls.append(invoke(label+'.link',[str(link),*linked],S/'VS',env))
  deps=read(intdir/'host.dependencies.json');includes={Path(p).resolve() for p in deps['Data']['Includes']};need(all((frozen/n).resolve() in includes for n in ('JSphGpuSingle.h','JSphGpu.h','JSph.h','JSphGpu_ker.h')),'Host compiler used another header ABI')
  copied=[]
  for entry in runtime:
   dest=out/Path(entry['path']).name;need(not dest.exists(),'Existing new runtime dependency protected');shutil.copy2(entry['path'],dest);e=stat(dest);need((e['bytes'],e['mtime_ns'])==(entry['bytes'],entry['mtime_ns']) and dest.read_bytes()==Path(entry['path']).read_bytes(),'Private runtime copy differs');copied.append(e)
  warnings=[line for entry in calls for line in Path(read(entry['path'])['log']['path']).read_bytes().decode('mbcs').splitlines() if re.search(r'\bwarning\b',line,re.I)];need(all(stat(e['path'])==e for e in before),'Original source/program/object/PRE/runtime changed during build')
  save(check,dict(stage=label+'.build',passed=True,configuration=conf,profile=profile,alpha=alpha,candidate_macro=MACRO,alpha0_macro=OFF if alpha==0. else None,macros_in_both_translation_units=definitions,numerical_damping_candidate=True,alpha0_whole_hook_skipped=alpha==0.,program=stat(program),source_capture=stat(CAP/'source.json'),source_archive=stat(archive),private_sources={k:stat(v) for k,v in sources.items()},baseline_source_build=stat(bp),baseline_source_capture=b['source_capture'],baseline_source_archive=b['source_archive'],CPU_component=stat(CPU),GPU_math_component=stat(MATH),physical_objects_recompiled=2,retained_physical_objects=111,actual_link_objects=113,actual_link_inputs=[str(x) for x in linkobjects],replacement_physical_objects=[stat(hostobj),stat(cudaobj)],compile_invocations=2,actual_CL_calls=1,actual_NVCC_calls=1,link_invocations=1,calls=calls,original_host_recipe=stat(ctlog),original_CUDA_recipe_log=stat(log),original_link_recipe=stat(ltlog),link_output_flags=seen,IntDir=str(intdir),OutDir=str(out),frozen_sources=frozen_entries,runtime=copied,warning_lines=warnings,baseline_warning_lines=b['warning_lines'],inherited_Debug_LNK4098_disclosed=conf=='Debug',new_warning_free_claimed=False,consumed=before,consumed_stats_unchanged=True,public_interfaces_changed=False,class_layout_changed=False,trace_macros_enabled=False,production_source_changed=False,full_project_builds=0,solver_invocations=0,help_invocations=0,memcheck_invocations=0,native_decodes=0,physical_acceptance=False,SHA_scans=0));print('RESIDUAL_VISCOSITY_PRIVATE_GPU_BUILD_PASSED',profile,program,flush=True)
 except Exception as error:
  if not check.exists():save(check,dict(stage=label+'.build',passed=False,configuration=conf,profile=profile,alpha=alpha,first_failure=str(error),calls=calls,consumed=before,solver_invocations=0,native_decodes=0,SHA_scans=0))
  raise

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--profile',choices=PROFILES,required=True);p.add_argument('--execution-authorized',action='store_true');a=p.parse_args();need(a.execution_authorized,'Author-only until root full-read of private integration/recipes');build(a.profile)
