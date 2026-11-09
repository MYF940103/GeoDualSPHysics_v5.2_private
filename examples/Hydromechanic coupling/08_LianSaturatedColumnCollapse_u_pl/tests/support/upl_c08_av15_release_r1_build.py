"""Build two private host TUs for release-only AV.15; no CUDA compilation or physical invocation."""
import argparse,os,shutil,subprocess,zipfile
from pathlib import Path,PurePosixPath
import mdbc_partition_components_r3 as e
import upl_c08_shepard_release_r1_build as recipe
T=Path(__file__).resolve().parents[1];L=T/'logs';S=T.parents[3]/'src';CAP=T/'outputs/upl_c08_av15_release_r1_source';RUNTIME=T.parent/'support/runtime_r6'
need,read,stat,bind,save,invoke=e.need,e.read,e.stat,e.bind,e.save,e.invoke
def build(conf):
 tag='upl_c08_av15_release_'+conf+'_r1';out=T/'outputs'/tag;check=L/(tag+'.build.json');before=[];calls=[]
 need(not out.exists() and not check.exists() and not any(L.glob(tag+'.*.call.json')),'Existing complete/partial private build protected')
 try:
  bp=L/('upl_c08_bedkeep_'+conf+'_r1.build.json');b=read(bp);sc=read(CAP/'source.json');expected=87 if conf=='DebugCPU' else 113;single='JSphCpuSingle' if conf=='DebugCPU' else 'JSphGpuSingle';names=('JSph',single)
  need(b['passed'] and b['configuration']==conf and b['actual_typed_exit_code']==b['actual_Win32_exit']==0 and b['source_stats_unchanged'] and len(b['project_objects'])==expected,'Closed original87 CPU or113 GPU objects required')
  need(sc['baseline_capture']==b['source_capture'] and sc['baseline_archive']==b['source_archive'] and sc['reverse_reconstruction_original_bytes_exact'] and sc['all_other_archive_member_bytes_exact'] and sc['only_release_AV_override_and_actual_metadata_changed'] and not sc['public_interfaces_changed'] and not sc['class_layout_changed'] and not sc['CUDA_source_changed'] and not sc['trace_macros_enabled'],'Reviewed reversible private AV-only source required')
  sources={Path(v['path']).stem:Path(bind(v)['path']) for v in sc['private_sources']};archive=Path(bind(sc['archive'])['path']);objects=b['project_objects'];originals={name:next(v for v in objects if Path(v['path']).stem.lower()==name.lower()) for name in names};retained=[v for v in objects if v not in originals.values()]
  need(len(retained)==expected-2 and sum(Path(v['path']).name.lower()=='main.obj' for v in retained)==1,'Retain all other original objects including solver main')
  intdir=Path(originals[single]['path']).parent;ctlog=intdir/'DualSPHysics.tlog/CL.command.1.tlog';ltlog=ctlog.with_name('link.command.1.tlog');lines=ctlog.read_text(encoding='utf-16').splitlines();ll=ltlog.read_text(encoding='utf-16').splitlines();need(sum(s.startswith('^') for s in ll)==1,'One authoritative project link command required');la=recipe.windows_args(' '.join(s for s in ll if s and not s.startswith('^')))
  origin=Path(b['program']['path']).parent;runtime=[stat(origin/p) for p in ('DsphConfig.xml','ChronoEngine.dll','dsphchrono.dll','vcomp140.dll')] if conf=='DebugCPU' else [stat(p) for p in sorted(RUNTIME.iterdir()) if p.is_file() and (p.suffix.lower()=='.dll' or p.name=='DsphConfig.xml')];need(len(runtime)==(4 if conf=='DebugCPU' else 7),'Original runtime dependency closure differs')
  before=[stat(__file__),stat(T/'notes/upl_c08_av15_release_r1.md'),stat(e.__file__),stat(recipe.__file__),stat(bp),bind(b['actual_call']),bind(b['program']),bind(b['source_capture']),bind(b['source_archive']),stat(ctlog),stat(ltlog),stat(CAP/'source.json'),stat(archive),bind(sc['diff']),*[bind(v) for v in sc['private_sources']],*[bind(v) for v in objects],*runtime]
  out.mkdir();frozen=out/'frozen/src/source';frozen_entries=[]
  with zipfile.ZipFile(archive) as z:
   for name in sources:need(z.read('src/source/'+name+'.cpp')==sources[name].read_bytes(),'Private CPP/archive differs')
   for info in z.infolist():
    p=PurePosixPath(info.filename);need(not p.is_absolute() and '..' not in p.parts,'Invalid archived source path')
    if not info.is_dir() and len(p.parts)>=3 and p.parts[:2]==('src','source'):
     need(p.suffix.lower() not in ('.obj','.o','.pdb','.exe','.dll','.lib'),'No binary artifacts in source extraction');dest=out/'frozen'/Path(*p.parts);dest.parent.mkdir(parents=True,exist_ok=True)
     with dest.open('xb') as f:f.write(z.read(info))
     frozen_entries.append(stat(dest))
  before+=frozen_entries;compile_args={};replacement={name:out/(name+'.obj') for name in names};dependencies=[]
  for name in names:
   at=[i for i,s in enumerate(lines) if s.startswith('^') and Path(s[1:]).name.lower()==name.lower()+'.cpp'];need(len(at)==1,'One authoritative CL command required for '+name);ca=recipe.windows_args(lines[at[0]+1]);need(sum(x.lower().endswith(name.lower()+'.cpp') for x in ca)==1 and not any(x.lower().startswith(('/yu','/yc','/gl')) for x in ca) and '/fp:precise' in ca and '/openmp' in ca and ('/Od' if conf=='DebugCPU' else '/O2') in ca and ('/MTd' if conf=='DebugCPU' else '/MT') in ca,'Original noPCH/noGL compiler flags differ')
   need(any('_WITHGPU' in x for x in ca)==(conf=='Release') and not any('C08_STAGE_TRACE' in x or 'C08_CAUSAL_TRACE' in x for x in ca),'Actual original backend/macros differ');dep=out/(name+'.dependencies.json');dependencies.append(dep)
   compile_args[name]=['/I'+str(frozen),*['/Fo'+str(replacement[name]) if x.lower().startswith('/fo') else '/Fd'+str(out/(name+'.pdb')) if x.lower().startswith('/fd') else str(sources[name]) if x.lower().endswith(name.lower()+'.cpp') else x for x in ca],'/sourceDependencies',str(dep)]
  program=out/Path(b['program']['path']).name;outputs={'/out:':program,'/pdb:':out/(program.stem+'.pdb'),'/implib:':out/(program.stem+'.lib'),'/ltcgout:':out/(program.stem+'.iobj')};seen=set();linked=[]
  for arg in la:
   for name in names:
    if arg.lower().endswith('.obj') and Path(arg).resolve()==Path(originals[name]['path']).resolve():arg=str(replacement[name]);break
   for key,target in outputs.items():
    if arg.lower().startswith(key):arg=key+str(target);seen.add(key);break
   linked.append(arg)
  actual=[Path(x).resolve() for x in linked if x.lower().endswith('.obj')];need(seen==set(outputs) and len(actual)==expected and set(actual)=={Path(v['path']).resolve() for v in retained}|{v.resolve() for v in replacement.values()},'Exactly two replacement host objects with no old duplicate required')
  setup=subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW);need(setup.returncode==0,'MSVC setup failed');env=dict(os.environ);env.update(x.split('=',1) for x in setup.stdout.decode('mbcs').splitlines() if '=' in x and not x.startswith('='));need(env['VCTOOLSVERSION']=='14.36.32532','Original MSVC14.36 required')
  for key in list(env):
   if key.upper() in ('CL','_CL_','NVCC_PREPEND_FLAGS','NVCC_APPEND_FLAGS'):env.pop(key)
  cl=Path(env['VCToolsInstallDir'])/'bin/Hostx64/x64/cl.exe';link=cl.with_name('link.exe');before += [stat(cl),stat(link)]
  libdirs=[S/'VS']+[Path(x.split(':',1)[1]) if Path(x.split(':',1)[1]).is_absolute() else S/'VS'/x.split(':',1)[1] for x in linked if x.lower().startswith('/libpath:')]+[Path(x) for x in env.get('LIB','').split(';') if x]
  for arg in linked:
   if arg.lower().endswith('.lib') and not arg.startswith('/'):
    candidates=[Path(arg)] if Path(arg).is_absolute() else [p/arg for p in libdirs];lib=next((p for p in candidates if p.is_file()),None);need(lib is not None,'Original explicit library missing: '+arg);before.append(stat(lib))
  need(all(stat(v['path'])==v for v in before),'Closed inputs changed before compile')
  for name in names:calls.append(invoke(tag+'.compile_'+name,[str(cl),*compile_args[name]],out,env))
  calls.append(invoke(tag+'.link',[str(link),*linked],S/'VS',env))
  for name,dep in zip(names,dependencies):
   includes={Path(p).resolve() for p in read(dep)['Data']['Includes']};required=['JSph.h']+(['JSphCpuSingle.h','JSphCpu.h'] if name=='JSphCpuSingle' else ['JSphGpuSingle.h','JSphGpu.h'] if name=='JSphGpuSingle' else []);need(all((frozen/p).resolve() in includes for p in required),'Compiler used another class-header ABI')
  copied=[]
  for entry in runtime:
   dest=out/Path(entry['path']).name;need(not dest.exists(),'New runtime file already exists');shutil.copy2(entry['path'],dest);v=stat(dest);need((v['bytes'],v['mtime_ns'])==(entry['bytes'],entry['mtime_ns']) and Path(entry['path']).read_bytes()==dest.read_bytes(),'Runtime copy differs');copied.append(v)
  need(all(stat(v['path'])==v for v in before),'Original source/object/program/runtime changed')
  save(check,dict(stage=tag+'.build',passed=True,configuration=conf,program=stat(program),source_capture=stat(CAP/'source.json'),source_archive=stat(archive),private_host_sources=[stat(sources[n]) for n in names],baseline_source_build=stat(bp),baseline_source_capture=b['source_capture'],baseline_source_archive=b['source_archive'],original_physical_objects=list(originals.values()),replacement_physical_objects=[stat(replacement[n]) for n in names],physical_objects_recompiled=2,retained_physical_objects=expected-2,actual_link_objects=expected,compile_invocations=2,link_invocations=1,CUDA_compile_invocations=0,source_dependencies=[stat(p) for p in dependencies],frozen_sources=frozen_entries,AV_policy='ReleaseOnly',preload_input_AV_literal='.1f',released_AV_literal='.15f',actual_AV_metadata_key='DynamicArtificialViscosityCoef',AS_stress_space='original_total',trace_macros_enabled=False,public_interfaces_changed=False,production_source_changed=False,runtime=copied,calls=calls,consumed=before,consumed_stats_unchanged=True,solver_invocations=0,native_decodes=0,physical_acceptance=False,SHA_scans=0));print('PRIVATE_AV15_BUILD_PASSED',conf,program,flush=True)
 except Exception as error:
  if not check.exists():save(check,dict(stage=tag+'.build',passed=False,configuration=conf,first_failure=str(error),calls=calls,consumed=before,solver_invocations=0,native_decodes=0,physical_acceptance=False,SHA_scans=0))
  raise
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--configuration',choices=('DebugCPU','Release'),required=True);p.add_argument('--execution-authorized',action='store_true');a=p.parse_args();need(a.execution_authorized,'Author-only until root reads the private source and two-host-TU build');build(a.configuration)
