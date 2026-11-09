"""Build isolated pair-ID causal observers from the sealed old causal archive; never run them."""
import argparse,os,re,shutil,subprocess,zipfile
from pathlib import Path,PurePosixPath
import mdbc_partition_components_r3 as e
import upl_c08_shepard_release_r1_build as recipe
T=Path(__file__).resolve().parents[1];L=T/'logs';S=T.parents[3]/'src';CAP=T/'outputs/upl_c08_pairtrace_r1_source';RUNTIME=T.parent/'support/runtime_r6'
NOTE=T/'notes/upl_c08_pairtrace_r1.md';MACROS=('C08_STAGE_TRACE','C08_CAUSAL_TRACE')
need,read,stat,bind,save,invoke=e.need,e.read,e.stat,e.bind,e.save,e.invoke

def build(conf):
 tag='upl_c08_pairtrace_'+conf+'_r1';out=T/'outputs'/tag;check=L/(tag+'.build.json');before=[];calls=[];gpu=conf=='Release'
 need(not out.exists() and not check.exists() and not any(L.glob(tag+'.*.call.json')) and not any(L.glob(tag+'.*.log')),'Existing complete/partial build protected')
 try:
  bp=L/('upl_c08_causal_'+conf+'_r1.build.json');b=read(bp);sc=read(CAP/'source.json');expected=113 if gpu else 87
  names=('JSphGpu.cpp','JSphGpu_ker.cu','JSphGpuSimple_ker.cu') if gpu else ('JSphCpuSingle.cpp',)
  need(b['passed'] and b['configuration']==conf and b['actual_typed_exit_code']==b['actual_Win32_exit']==0 and b['source_stats_unchanged'] and len(b['project_objects'])==expected,'Closed same-configuration causal build required')
  need(sc['baseline_capture']==b['source_capture'] and sc['baseline_archive']==b['source_archive'] and sc['old_observed_IDs']==[7017,5944,6814] and sc['observed_IDs']==[7011,7012,6230] and sc['ID_mapping_sites_changed']==4 and sc['only_observer_ID_literals_changed'] and sc['reverse_reconstruction_original_bytes_exact'] and sc['all_other_archive_member_bytes_exact'] and not sc['observer_layout_changed'] and not sc['sampler_changed'] and not sc['physical_equations_changed'],'Reviewed reversible ID-only private capture required')
  archive=Path(bind(sc['archive'])['path']);objects=b['project_objects'];oldobjs={name:next(v for v in objects if Path(v['path']).name.lower()==(name+'.obj' if name.endswith('.cu') else Path(name).stem+'.obj').lower()) for name in names};retained=[v for v in objects if v not in oldobjs.values()]
  need(len(retained)==expected-len(names) and sum(Path(v['path']).name.lower()=='main.obj' for v in retained)==1,'Original object closure including main must be retained')
  intdir=Path(objects[0]['path']).parent;ctlog=intdir/'DualSPHysics.tlog/CL.command.1.tlog';ltlog=ctlog.with_name('link.command.1.tlog');cllines=ctlog.read_text(encoding='utf-16').splitlines();ll=ltlog.read_text(encoding='utf-16').splitlines();need(sum(x.startswith('^') for x in ll)==1,'One original link command required');la=recipe.windows_args(' '.join(x for x in ll if x and not x.startswith('^')))
  sourcecall=read(bind(b['actual_call'])['path']);originlog=Path(bind(sourcecall['log'])['path'])
  cpu_runtime=T/'outputs/upl_c08_bedkeep_DebugCPU_r1';runtime=[stat(cpu_runtime/p) for p in ('DsphConfig.xml','ChronoEngine.dll','dsphchrono.dll','vcomp140.dll')] if not gpu else [stat(p) for p in sorted(RUNTIME.iterdir()) if p.is_file() and (p.suffix.lower()=='.dll' or p.name=='DsphConfig.xml')];need(len(runtime)==(7 if gpu else 4),'Runtime dependency closure differs')
  before=[stat(__file__),stat(NOTE),stat(e.__file__),stat(recipe.__file__),stat(bp),bind(b['actual_call']),bind(b['program']),bind(b['source_capture']),bind(b['source_archive']),stat(ctlog),stat(ltlog),stat(originlog),stat(CAP/'source.json'),stat(archive),bind(sc['diff']),*[bind(v) for v in sc['private_sources']],*[bind(v) for v in objects],*runtime]
  out.mkdir();frozen=out/'frozen/src/source';extracted=[]
  with zipfile.ZipFile(archive) as z:
   for info in z.infolist():
    p=PurePosixPath(info.filename);need(not p.is_absolute() and '..' not in p.parts,'Invalid archive path')
    if not info.is_dir() and p.parts[:2]==('src','source'):
     need(p.suffix.lower() not in ('.obj','.o','.exe','.dll','.lib','.pdb'),'Source-only archive required');dest=out/'frozen'/Path(*p.parts);dest.parent.mkdir(parents=True,exist_ok=True)
     with dest.open('xb') as f:f.write(z.read(info))
     extracted.append(stat(dest))
  before+=extracted;replacement={name:out/(name+'.obj' if name.endswith('.cu') else Path(name).stem+'.obj') for name in names};deps=[];commands=[]
  cpp=names[0];at=[i for i,x in enumerate(cllines) if x.startswith('^') and Path(x[1:]).name.lower()==cpp.lower()];need(len(at)==1,'One authoritative CL command required');ca=recipe.windows_args(cllines[at[0]+1])
  need('/fp:precise' in ca and '/openmp' in ca and ('/O2' if gpu else '/Od') in ca and ('/MT' if gpu else '/MTd') in ca and not any(x.lower().startswith(('/yu','/yc','/gl')) for x in ca) and not any(m in x for m in MACROS for x in ca),'Original noPCH/noGL CL flags required; old macro injection was environmental')
  dep=out/(cpp+'.dependencies.json');deps.append(dep);ca=['/I'+str(frozen),*['/Fo'+str(replacement[cpp]) if x.lower().startswith('/fo') else '/Fd'+str(out/(cpp+'.pdb')) if x.lower().startswith('/fd') else str(frozen/cpp) if x.lower().endswith(cpp.lower()) else x for x in ca],'/sourceDependencies',str(dep)]
  if gpu:ca=['/D'+m for m in MACROS]+ca
  setup=subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW);need(setup.returncode==0,'MSVC setup failed');env=dict(os.environ);env.update(x.split('=',1) for x in setup.stdout.decode('mbcs').splitlines() if '=' in x and not x.startswith('='));need(env['VCTOOLSVERSION']=='14.36.32532','Original MSVC14.36 required')
  for key in list(env):
   if key.upper() in ('CL','_CL_','NVCC_PREPEND_FLAGS','NVCC_APPEND_FLAGS'):env.pop(key)
  cl=Path(env['VCToolsInstallDir'])/'bin/Hostx64/x64/cl.exe';link=cl.with_name('link.exe');before += [stat(cl),stat(link)];commands.append((cpp,[str(cl),*ca]))
  if gpu:
   for name in names[1:]:
    rows=[x.split(b'>',1)[1].strip().decode('ascii') for x in originlog.read_bytes().splitlines() if b'nvcc.exe' in x.lower() and name.lower().encode('ascii') in x.lower()];need(len(rows)==1,'One original ASCII NVCC command per changed CUDA TU required');nv=recipe.windows_args(rows[0]);nvcc=Path(nv.pop(0));need('/CUDA/v11.7/' in str(nvcc).replace('\\','/') and all(x in nv for x in ('--compile','--machine','64','-cudart','static','-use_fast_math','-D_WITHGPU')) and any('compute_86' in x and 'sm_86' in x for x in nv) and not any(m in x for m in MACROS for x in nv),'Original CUDA11.7/sm86 command required; environmental macros restored explicitly')
    pdbcount=0
    for i,x in enumerate(nv):
     if i and nv[i-1]=='-Xcompiler':nv[i],count=re.subn(r'(?i)(?<!\S)/Fd[^\s]+','/Fd'+Path(name).stem+'.pdb',x);pdbcount+=count
    need(pdbcount==1 and nv.count('-o')==nv.count('--keep-dir')==1,'One CUDA host PDB/output/scratch option required');nv[nv.index('-o')+1]=str(replacement[name]);nv[nv.index('--keep-dir')+1]=str(out);nv=[str(frozen/name) if Path(x).name.lower()==name.lower() else x for x in nv];nv=['-D'+m for m in MACROS]+['-I'+str(frozen)]+nv;commands.append((name,[str(nvcc),*nv]));before.append(stat(nvcc))
  program=out/Path(b['program']['path']).name;outputs={'/out:':program,'/pdb:':out/(program.stem+'.pdb'),'/implib:':out/(program.stem+'.lib'),'/ltcgout:':out/(program.stem+'.iobj')};seen=set();linked=[]
  for x in la:
   for name,old in oldobjs.items():
    if x.lower().endswith('.obj') and Path(x).resolve()==Path(old['path']).resolve():x=str(replacement[name]);break
   for key,dest in outputs.items():
    if x.lower().startswith(key):x=key+str(dest);seen.add(key);break
   linked.append(x)
  actual=[Path(x).resolve() for x in linked if x.lower().endswith('.obj')];need(seen==set(outputs) and len(actual)==expected and set(actual)=={Path(v['path']).resolve() for v in retained}|{p.resolve() for p in replacement.values()},'Exactly the changed-TU replacements, no old duplicate object')
  libdirs=[S/'VS']+[Path(x.split(':',1)[1]) if Path(x.split(':',1)[1]).is_absolute() else S/'VS'/x.split(':',1)[1] for x in linked if x.lower().startswith('/libpath:')]+[Path(x) for x in env.get('LIB','').split(';') if x]
  for x in linked:
   if x.lower().endswith('.lib') and not x.startswith('/'):
    candidates=[Path(x)] if Path(x).is_absolute() else [p/x for p in libdirs];lib=next((p for p in candidates if p.is_file()),None);need(lib is not None,'Explicit original library missing: '+x);before.append(stat(lib))
  need(all(stat(v['path'])==v for v in before),'Closed inputs changed before compile')
  for name,argv in commands:
   calls.append(invoke(tag+'.compile_'+Path(name).stem,argv,out,env))
   text=Path(read(calls[-1]['path'])['log']['path']).read_bytes();need((b'C08_STAGE_TRACE enabled' in text)==gpu,'Actual compiler macro announcement differs')
  calls.append(invoke(tag+'.link',[str(link),*linked],S/'VS',env))
  includes={Path(p).resolve() for p in read(dep)['Data']['Includes']};need(all((frozen/p).resolve() in includes for p in (['JSph.h','JSphGpu.h','C08StageTrace.h'] if gpu else ['JSph.h','JSphCpu.h','JSphCpuSingle.h'])),'CL used headers outside frozen ABI closure')
  copied=[]
  for v in runtime:
   dest=out/Path(v['path']).name;shutil.copy2(v['path'],dest);s=stat(dest);need((s['bytes'],s['mtime_ns'])==(v['bytes'],v['mtime_ns']) and Path(v['path']).read_bytes()==dest.read_bytes(),'Runtime copy differs');copied.append(s)
  need(all(stat(v['path'])==v for v in before),'Original source/object/runtime inputs changed')
  save(check,dict(stage=tag+'.build',passed=True,configuration=conf,program=stat(program),source_capture=stat(CAP/'source.json'),source_archive=stat(archive),baseline_source_build=stat(bp),baseline_source_capture=b['source_capture'],baseline_source_archive=b['source_archive'],observed_IDs=[7011,7012,6230],trace_macros_enabled=gpu,CPU_observer_enabled=False,CPU_check_recompiles_unchanged_TU=(not gpu),physical_objects_recompiled=len(names),retained_physical_objects=len(retained),actual_link_objects=expected,compile_invocations=len(commands),CUDA_compile_invocations=(2 if gpu else 0),link_invocations=1,replacement_objects=[stat(p) for p in replacement.values()],source_dependencies=[stat(p) for p in deps],frozen_sources=extracted,runtime=copied,calls=calls,consumed=before,consumed_stats_unchanged=True,solver_invocations=0,native_decodes=0,physical_acceptance=False,SHA_scans=0));print('PAIRTRACE_BUILD_PASSED',conf,program,flush=True)
 except Exception as error:
  if not check.exists():save(check,dict(stage=tag+'.build',passed=False,configuration=conf,first_failure=str(error),calls=calls,consumed=before,solver_invocations=0,native_decodes=0,physical_acceptance=False,SHA_scans=0))
  raise
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--configuration',choices=('DebugCPU','Release'),default='DebugCPU');p.add_argument('--execution-authorized',action='store_true');a=p.parse_args();need(a.execution_authorized,'Author-only until root reviews the private capture and configuration recipe');build(a.configuration)
