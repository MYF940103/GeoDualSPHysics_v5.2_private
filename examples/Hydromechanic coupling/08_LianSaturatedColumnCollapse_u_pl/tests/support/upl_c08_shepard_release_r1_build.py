"""One private GPU host TU plus the original112 objects; build only, no solver or decoder."""
import argparse,ctypes,os,shutil,subprocess,zipfile
from pathlib import Path,PurePosixPath
import mdbc_partition_components_r3 as e
T=Path(__file__).resolve().parents[1];L=T/'logs';S=T.parents[3]/'src';CAP=T/'outputs/upl_c08_shepard_release_r1_source';RUNTIME=T.parent/'support/runtime_r6'
need,read,stat,bind,save,invoke=e.need,e.read,e.stat,e.bind,e.save,e.invoke

def windows_args(line):
 shell=ctypes.WinDLL('shell32',use_last_error=True);shell.CommandLineToArgvW.argtypes=[ctypes.c_wchar_p,ctypes.POINTER(ctypes.c_int)];shell.CommandLineToArgvW.restype=ctypes.POINTER(ctypes.c_wchar_p);n=ctypes.c_int();p=shell.CommandLineToArgvW('tool.exe '+line,ctypes.byref(n));need(bool(p),'Cannot parse original Windows build command')
 try:return [p[i] for i in range(1,n.value)]
 finally:free=ctypes.WinDLL('kernel32').LocalFree;free.argtypes=[ctypes.c_void_p];free.restype=ctypes.c_void_p;free(ctypes.cast(p,ctypes.c_void_p))

def build(conf):
 tag='upl_c08_shepard_release_'+conf+'_r1';out=T/'outputs'/tag;check=L/(tag+'.build.json');before=[];calls=[]
 need(not out.exists() and all(not (L/(tag+s)).exists() for s in ('.build.json','.compile.call.json','.compile.log','.link.call.json','.link.log')),'Existing complete or partial build protected')
 try:
  bp=L/('upl_c08_bedkeep_'+conf+'_r1.build.json');b=read(bp);sc=read(CAP/'source.json');source=Path(bind(sc['private_host_source'])['path']);archive=Path(bind(sc['archive'])['path'])
  need(b['passed'] and b['configuration']==conf and b['actual_typed_exit_code']==b['actual_Win32_exit']==0 and b['source_stats_unchanged'] and len(b['project_objects'])==113,'Closed original113-object GPU configuration required')
  need(sc['baseline_capture']==b['source_capture'] and sc['baseline_archive']==b['source_archive'] and sc['reverse_reconstruction_original_bytes_exact'] and sc['only_release_Shepard_flag_and_output_meter_changed'] and not sc['public_interfaces_changed'] and not sc['trace_macros_enabled'],'Read-reviewed reversible original-total-AS host intervention required')
  objects=b['project_objects'];original=next(v for v in objects if Path(v['path']).name.lower()=='jsphgpusingle.obj');retained=[v for v in objects if v!=original];need(len(retained)==112 and sum(Path(v['path']).name.lower()=='main.obj' for v in retained)==1,'Retain112 objects including original solver main')
  intdir=Path(original['path']).parent;ctlog=intdir/'DualSPHysics.tlog/CL.command.1.tlog';ltlog=ctlog.with_name('link.command.1.tlog');lines=ctlog.read_text(encoding='utf-16').splitlines();at=[i for i,s in enumerate(lines) if s.startswith('^') and Path(s[1:]).name.lower()=='jsphgpusingle.cpp'];need(len(at)==1,'One authoritative JSphGpuSingle CL command required');ca=windows_args(lines[at[0]+1]);ll=ltlog.read_text(encoding='utf-16').splitlines();need(sum(s.startswith('^') for s in ll)==1,'One actual project link command required');la=windows_args(' '.join(s for s in ll if s and not s.startswith('^')))
  need(sum(s.lower().endswith('jsphgpusingle.cpp') for s in ca)==1 and not any(s.lower().startswith(('/yu','/yc','/gl')) for s in ca) and '/fp:precise' in ca and '/openmp' in ca and ('/Od' if conf=='Debug' else '/O2') in ca and ('/MTd' if conf=='Debug' else '/MT') in ca,'Original project flags/noPCH/noGL required')
  runtime=[stat(p) for p in sorted(RUNTIME.iterdir()) if p.is_file() and (p.suffix.lower()=='.dll' or p.name=='DsphConfig.xml')];need(len(runtime)==7,'Original seven runtime dependencies required')
  before=[stat(__file__),stat(T/'notes/upl_c08_shepard_release_r1.md'),stat(e.__file__),stat(bp),bind(b['actual_call']),bind(b['program']),bind(b['source_capture']),bind(b['source_archive']),stat(ctlog),stat(ltlog),stat(CAP/'source.json'),stat(source),stat(archive),bind(sc['diff']),*[bind(v) for v in objects],*runtime]
  out.mkdir();frozen=out/'frozen/src/source';frozen_entries=[]
  with zipfile.ZipFile(archive) as z:
   need(z.read('src/source/JSphGpuSingle.cpp')==source.read_bytes(),'Private host source differs from complete frozen ZIP')
   for info in z.infolist():
    p=PurePosixPath(info.filename);need(not p.is_absolute() and '..' not in p.parts,'Invalid frozen source archive path')
    if not info.is_dir() and len(p.parts)>=3 and p.parts[:2]==('src','source'):
     need(p.suffix.lower() not in ('.obj','.o','.pdb','.exe','.dll','.lib'),'No old binary artifacts in source extraction');dest=out/'frozen'/Path(*p.parts);dest.parent.mkdir(parents=True,exist_ok=True);data=z.read(info)
     with dest.open('xb') as f:f.write(data)
     frozen_entries.append(stat(dest))
  need(all((frozen/name).is_file() for name in ('JSphGpuSingle.h','JSphGpu.h','JSph.h','DualSphDef.h')),'Frozen class-header closure absent');before+=frozen_entries
  obj=out/'JSphGpuSingle.obj';program=out/Path(b['program']['path']).name
  # Put all archived headers first; only the selected private CPP is compiled.
  ca=['/I'+str(frozen),*['/Fo'+str(obj) if x.lower().startswith('/fo') else '/Fd'+str(out/'physical.pdb') if x.lower().startswith('/fd') else str(source) if x.lower().endswith('jsphgpusingle.cpp') else x for x in ca],'/sourceDependencies',str(out/'physical.dependencies.json')]
  need(not any('C08_STAGE_TRACE' in x or 'C08_CAUSAL_TRACE' in x for x in ca),'Original macro-off host flags required')
  outputs={'/out:':program,'/pdb:':out/(program.stem+'.pdb'),'/implib:':out/(program.stem+'.lib'),'/ltcgout:':out/(program.stem+'.iobj')};seen=set();linked=[]
  for arg in la:
   if arg.lower().endswith('.obj') and Path(arg).resolve()==Path(original['path']).resolve():arg=str(obj)
   for key,target in outputs.items():
    if arg.lower().startswith(key):arg=key+str(target);seen.add(key);break
   linked.append(arg)
  actual=[Path(x).resolve() for x in linked if x.lower().endswith('.obj')];need(seen==set(outputs) and len(actual)==113 and set(actual)=={Path(v['path']).resolve() for v in retained}|{obj.resolve()},'Exactly112 retained objects plus one private host object required')
  setup=subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW);need(setup.returncode==0,'MSVC setup failed');env=dict(os.environ);env.update(s.split('=',1) for s in setup.stdout.decode('mbcs').splitlines() if '=' in s and not s.startswith('='));need(env['VCTOOLSVERSION']=='14.36.32532','Original MSVC14.36 required')
  for key in list(env):
   if key.upper() in ('CL','_CL_','NVCC_PREPEND_FLAGS','NVCC_APPEND_FLAGS'):env.pop(key)
  cl=Path(env['VCToolsInstallDir'])/'bin/Hostx64/x64/cl.exe';link=cl.with_name('link.exe');before += [stat(cl),stat(link)]
  libdirs=[S/'VS']+[Path(x.split(':',1)[1]) if Path(x.split(':',1)[1]).is_absolute() else S/'VS'/x.split(':',1)[1] for x in linked if x.lower().startswith('/libpath:')]+[Path(x) for x in env.get('LIB','').split(';') if x]
  for arg in linked:
   if arg.lower().endswith('.lib') and not arg.startswith('/'):
    candidates=[Path(arg)] if Path(arg).is_absolute() else [p/arg for p in libdirs];lib=next((p for p in candidates if p.is_file()),None);need(lib is not None,'Original explicit library unavailable: '+arg);before.append(stat(lib))
  need(all(stat(v['path'])==v for v in before),'Closed source/objects/runtime changed before compilation');calls.append(invoke(tag+'.compile',[str(cl),*ca],out,env));calls.append(invoke(tag+'.link',[str(link),*linked],S/'VS',env))
  deps=read(out/'physical.dependencies.json');includes={Path(p).resolve() for p in deps['Data']['Includes']};need(all((frozen/name).resolve() in includes for name in ('JSphGpuSingle.h','JSphGpu.h','JSph.h')),'Compiler used another class-header ABI')
  copied=[]
  for entry in runtime:
   dest=out/Path(entry['path']).name;need(not dest.exists(),'Existing new runtime file protected');shutil.copy2(entry['path'],dest);v=stat(dest);need((v['bytes'],v['mtime_ns'])==(entry['bytes'],entry['mtime_ns']) and Path(entry['path']).read_bytes()==dest.read_bytes(),'Private runtime copy differs');copied.append(v)
  need(all(stat(v['path'])==v for v in before),'Original inputs/source/program/object/runtime changed')
  save(check,dict(stage=tag+'.build',passed=True,configuration=conf,program=stat(program),source_capture=stat(CAP/'source.json'),source_archive=stat(archive),private_host_source=stat(source),baseline_source_build=stat(bp),baseline_source_capture=b['source_capture'],baseline_source_archive=b['source_archive'],original_physical_object=original,replacement_physical_object=stat(obj),physical_objects_recompiled=1,retained_physical_objects=112,actual_link_objects=113,compile_invocations=1,link_invocations=1,source_dependencies=stat(out/'physical.dependencies.json'),frozen_sources=frozen_entries,release_Shepard_policy='RetainLoadedFlag',meter_scope='existing_filter_wrapper_plus_FS_projection',meter_csv='C08ReleaseShepard.csv',AS_stress_space='original_total',trace_macros_enabled=False,public_interfaces_changed=False,production_source_changed=False,runtime=copied,calls=calls,consumed=before,consumed_stats_unchanged=True,solver_invocations=0,native_decodes=0,physical_acceptance=False,SHA_scans=0));print('PRIVATE_RELEASE_SHEPARD_BUILD_PASSED',conf,program,flush=True)
 except Exception as error:
  if not check.exists():save(check,dict(stage=tag+'.build',passed=False,configuration=conf,first_failure=str(error),calls=calls,consumed=before,solver_invocations=0,native_decodes=0,physical_acceptance=False,SHA_scans=0))
  raise
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--configuration',choices=('Debug','Release'),required=True);p.add_argument('--execution-authorized',action='store_true');a=p.parse_args();need(a.execution_authorized,'Author-only until root reads source/diff/flags/closure');build(a.configuration)
