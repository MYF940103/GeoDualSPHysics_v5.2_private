"""Private macro-off GPU AS-input intervention: one original CUDA TU and one link; no program run."""
import argparse,ctypes,difflib,os,re,shutil,subprocess,zipfile
from pathlib import Path,PurePosixPath
import upl_c08_asn4_zero_cpu_r2_build as base
T,L,S=base.T,base.L,base.S;TAG='upl_c08_as_effective_gpu_r1';NOTE=T/'notes'/(TAG+'.md')
CAP=T/'outputs'/(TAG+'_source');OUT=T/'outputs'/(TAG+'_build');PROGRAM=OUT/'DualSPHysics5.2_GEO_win64.exe'
BASE=L/'upl_c08_bedkeep_Release_r1.build.json';RUNTIME=T.parent/'support/runtime_r6'
need,read,stat,bind,save,invoke=base.need,base.read,base.stat,base.bind,base.save,base.invoke

def windows_args(line):
 shell=ctypes.WinDLL('shell32',use_last_error=True);shell.CommandLineToArgvW.argtypes=[ctypes.c_wchar_p,ctypes.POINTER(ctypes.c_int)];shell.CommandLineToArgvW.restype=ctypes.POINTER(ctypes.c_wchar_p);count=ctypes.c_int();p=shell.CommandLineToArgvW('tool.exe '+line,ctypes.byref(count));need(bool(p),'Cannot parse the actual Windows build command')
 try:return [p[i] for i in range(1,count.value)]
 finally:free=ctypes.WinDLL('kernel32').LocalFree;free.argtypes=[ctypes.c_void_p];free.restype=ctypes.c_void_p;free(ctypes.cast(p,ctypes.c_void_p))

def build():
 check=L/(TAG+'.build.json');need(not CAP.exists() and not OUT.exists() and not check.exists(),'Existing complete/partial private build is protected');before=[];calls=[]
 try:
  b=read(BASE);need(b['passed'] and b['configuration']=='Release' and b['actual_typed_exit_code']==b['actual_Win32_exit']==0 and b['source_stats_unchanged'] and len(b['project_objects'])==113,'Closed macro-off bedkeep Release113 closure required')
  objects=b['project_objects'];original=next(e for e in objects if Path(e['path']).name.lower()=='jsphgpu_ker.cu.obj');retained=[e for e in objects if e!=original];need(len(retained)==112 and sum(Path(e['path']).name.lower()=='main.obj' for e in retained)==1,'Retain112 objects including the original solver main')
  call=read(bind(b['actual_call'])['path']);log=Path(bind(call['log'])['path']);intdir=Path(original['path']).parent;tlog=intdir/'DualSPHysics.tlog/link.command.1.tlog'
  lines=log.read_bytes().splitlines();nv=[line.split(b'>',1)[1].strip().decode('ascii') for line in lines if b'nvcc.exe' in line.lower() and b'jsphgpu_ker.cu' in line.lower()];need(len(nv)==1,'One actual ASCII project NVCC command required');ca=windows_args(nv[0]);nvcc=Path(ca.pop(0))
  original_includes=[arg[2:] for arg in ca if arg.startswith('-I')];need(len(original_includes)==1 and Path(original_includes[0]).resolve()==(nvcc.parent.parent/'include').resolve() and '-I' not in ca and not any(arg.startswith('--include-path') for arg in ca),'Original explicit include must be CUDA only, without live project include paths')
  lines=tlog.read_text(encoding='utf-16').splitlines();need(sum(line.startswith('^') for line in lines)==1,'One original link-command block required');la=windows_args(' '.join(line for line in lines if line and not line.startswith('^')))
  runtime=[stat(p) for p in sorted(RUNTIME.iterdir()) if p.is_file()];oldprogram=stat(RUNTIME/PROGRAM.name);need((oldprogram['bytes'],oldprogram['mtime_ns'])==(b['program']['bytes'],b['program']['mtime_ns']),'runtime_r6 must remain the original closed bedkeep solver')
  protected=[stat(S.parent/'bin/windows'/leaf) for leaf in ('DualSPHysics5.2CPU_win64_debug.exe','DualSPHysics5.2_win64_debug.exe','DualSPHysics5.2CPU_win64.exe','DualSPHysics5.2_GEO_win64.exe') if (S.parent/'bin/windows'/leaf).exists()]
  before=[stat(BASE),bind(b['actual_call']),stat(log),stat(tlog),bind(b['program']),bind(b['source_capture']),bind(b['source_archive']),*[bind(e) for e in objects],*runtime,*protected,stat(__file__),stat(NOTE),stat(base.__file__),stat(base.old.__file__)]
  CAP.mkdir();OUT.mkdir();frozen=CAP/'frozen/src/source';headers=[];cu=CAP/'JSphGpu_ker.cu'
  with zipfile.ZipFile(b['source_archive']['path']) as z:
   original_bytes=z.read('src/source/JSphGpu_ker.cu');nl=b'\r\n' if b'\r\n' in original_bytes else b'\n'
   decl=b'const tsymatrix3d sig=sigma[p];const double pw=double(porepress[p]);'
   expression=b'KerComputeBuiArtificialStress(make_float2(float(sig.xx-pw),float(sig.xy)),make_float2(float(sig.xz),float(sig.yy-pw)),make_float2(float(sig.yz),float(sig.zz-pw)),1.f,CTE.artificialstresscoef,rstress_xx_xy,rstress_xz_yy,rstress_yz_zz);'
   old=decl+nl+b'        '+expression;new=b'const tsymatrix3d sig=sigma[p];'+nl+b'        '+expression.replace(b'sig.xx-pw',b'sig.xx').replace(b'sig.yy-pw',b'sig.yy').replace(b'sig.zz-pw',b'sig.zz')
   need(original_bytes.count(old)==1,'Original total-stress porepress branch must match once');modified=original_bytes.replace(old,new);need(modified.count(new)==1 and modified.replace(new,old)==original_bytes,'One reversible porepress-branch-only intervention required')
   with cu.open('xb') as f:f.write(modified)
   patch=CAP/'production.diff';patch.write_text(''.join(difflib.unified_diff(original_bytes.decode('utf-8-sig').splitlines(True),modified.decode('utf-8-sig').splitlines(True),fromfile='bedkeep/src/source/JSphGpu_ker.cu',tofile='effective_test_only/src/source/JSphGpu_ker.cu')),encoding='utf-8')
   archive=CAP/'source.zip'
   with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED) as dst:
    for name in z.namelist():
     p=PurePosixPath(name);need(not p.is_absolute() and '..' not in p.parts,'Invalid original archive member');data=modified if name=='src/source/JSphGpu_ker.cu' else z.read(name);dst.writestr(name,data)
     if len(p.parts)>=3 and p.parts[:2]==('src','source') and p.suffix.lower() in ('.h','.hpp','.cuh'):
      target=CAP/'frozen'/Path(*p.parts);target.parent.mkdir(parents=True,exist_ok=True)
      with target.open('xb') as f:f.write(data)
      need(target.read_bytes()==data,'Frozen include copy differs');headers.append(stat(target))
  need(all((frozen/leaf).is_file() for leaf in ('JSphGpu_ker.h','JSphGpu_mdbc_ker.cuh','DualSphDef.h','FunSphKernel_iker.h')),'Frozen GPU source includes absent')
  capture=CAP/'source.json';save(capture,dict(stage=TAG+'.source',AS_stress_space='effective_test_only',baseline_capture=b['source_capture'],baseline_archive=b['source_archive'],private_gpu_source=stat(cu),diff=stat(patch),archive=stat(archive),frozen_headers=headers,exact_porepress_branch_only=True,reverse_reconstruction_original_bytes_exact=True,public_interfaces_changed=False,legacy_rho_normalized_branch_changed=False,raw_Pa_rho1_J_pair_and_ReleaseOnly_unchanged=True,trace_macros_enabled=False,physical_acceptance=False,SHA_scans=0));before += [stat(capture),stat(cu),stat(patch),stat(archive),*headers]
  # Rehome only compiler scratch/output. Original objects are read-only link inputs.
  oldstyles=(str(intdir),str(intdir).replace('\\','/'))
  def rehome(value):
   for prefix in oldstyles:value=re.sub(re.escape(prefix),lambda _:str(OUT).replace('\\','/'),value,flags=re.I)
   return value
  ca=[str(cu) if Path(arg).name.lower()=='jsphgpu_ker.cu' else rehome(arg) for arg in ca];obj=OUT/'JSphGpu_ker.cu.obj';need(ca.count('-o')==1 and ca.count('--keep-dir')==1,'Original NVCC output/scratch flags differ');ca[ca.index('-o')+1]=str(obj);ca[ca.index('--keep-dir')+1]=str(OUT);ca.insert(0,'-I'+str(frozen))
  need(sum(Path(arg).name.lower()=='jsphgpu_ker.cu' for arg in ca)==1 and all(v in ca for v in ('--compile','--machine','64','-cudart','static','-use_fast_math','-D_WITHGPU')) and any('compute_86' in v and 'sm_86' in v for v in ca) and any('/O2' in v and '/MT' in v for v in ca) and not any('C08_STAGE_TRACE' in v or 'C08_CAUSAL_TRACE' in v or v in ('-G','--device-link','-dc') or 'rdc=true' in v for v in ca),'Original macro-off Release/sm86 flags required')
  outputs={'/out:':PROGRAM,'/pdb:':OUT/'DualSPHysics5.2_GEO_win64.pdb','/implib:':OUT/'DualSPHysics5.2_GEO_win64.lib','/ltcgout:':OUT/'DualSPHysics5.2_GEO_win64.iobj'};seen=set();linked=[]
  for arg in la:
   if arg.lower().endswith('.obj') and Path(arg).resolve()==Path(original['path']).resolve():arg=str(obj)
   for key,target in outputs.items():
    if arg.lower().startswith(key):arg=key+str(target);seen.add(key);break
   linked.append(arg)
  linkobjs=[Path(arg).resolve() for arg in linked if arg.lower().endswith('.obj')];need(seen==set(outputs) and len(linkobjs)==113 and set(linkobjs)=={Path(e['path']).resolve() for e in retained}|{obj.resolve()},'Exactly112 retained plus one private CUDA object required')
  setup=subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW);need(setup.returncode==0,'MSVC setup failed');env=dict(os.environ);env.update(line.split('=',1) for line in setup.stdout.decode('mbcs').splitlines() if '=' in line and not line.startswith('='));need(env['VCTOOLSVERSION']=='14.36.32532','Original MSVC14.36 required')
  for key in list(env):
   if key.upper() in ('CL','_CL_','NVCC_PREPEND_FLAGS','NVCC_APPEND_FLAGS'):env.pop(key)
  need(ca.count('-ccbin')==1,'One actual project MSVC host-tool directory required');link=Path(ca[ca.index('-ccbin')+1])/'link.exe';need('CUDA/v11.7' in str(nvcc).replace('\\','/') and '/14.36.32532/' in str(link).replace('\\','/'),'Original CUDA11.7/MSVC tools required');before += [stat(nvcc),stat(link)]
  # Resolve only explicitly named original link libraries; never scan a library tree.
  libdirs=[S/'VS']+[Path(arg.split(':',1)[1]) if Path(arg.split(':',1)[1]).is_absolute() else S/'VS'/arg.split(':',1)[1] for arg in linked if arg.lower().startswith('/libpath:')]+[Path(p) for p in env.get('LIB','').split(';') if p]
  for arg in linked:
   if arg.lower().endswith('.lib') and not arg.startswith('/'):
    candidates=[Path(arg)] if Path(arg).is_absolute() else [p/arg for p in libdirs];library=next((p for p in candidates if p.is_file()),None);need(library is not None,'Original explicit link library unavailable: '+arg);before.append(stat(library))
  need(all(stat(e['path'])==e for e in before),'Source/closed inputs changed before compilation');calls.append(invoke(TAG+'.compile',[str(nvcc),*ca],S/'VS',env));calls.append(invoke(TAG+'.link',[str(link),*linked],S/'VS',env))
  copied=[]
  for entry in runtime:
   source=Path(entry['path'])
   if source.suffix.lower()=='.dll' or source.name=='DsphConfig.xml':
    dest=OUT/source.name;need(not dest.exists(),'Existing new runtime file protected');shutil.copy2(source,dest);entry_copy=stat(dest);need((entry_copy['bytes'],entry_copy['mtime_ns'])==(entry['bytes'],entry['mtime_ns']) and source.read_bytes()==dest.read_bytes(),'New private runtime byte/stat copy differs');copied.append(entry_copy)
  need(len(copied)==7 and all(stat(e['path'])==e for e in before),'Original program/object/source/runtime changed or runtime incomplete')
  save(check,dict(stage=TAG+'.build',passed=True,AS_stress_space='effective_test_only',program=stat(PROGRAM),private_gpu_source=stat(cu),source_capture=stat(capture),source_archive=stat(archive),baseline_source_build=stat(BASE),baseline_source_capture=b['source_capture'],baseline_source_archive=b['source_archive'],original_physical_object=original,replacement_physical_object=stat(obj),physical_objects_recompiled=1,retained_physical_objects=112,actual_link_objects=113,compile_invocations=1,link_invocations=1,trace_macros_enabled=False,public_interfaces_changed=False,production_source_changed=False,full_project_builds=0,solver_invocations=0,native_decodes=0,physical_acceptance=False,runtime=copied,calls=calls,consumed=before,consumed_stats_unchanged=True,SHA_scans=0))
 except Exception as error:
  if not check.exists():save(check,dict(stage=TAG+'.build',passed=False,AS_stress_space='effective_test_only',first_failure=str(error),calls=calls,consumed=before,solver_invocations=0,native_decodes=0,physical_acceptance=False,SHA_scans=0))
  raise
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execution-authorized',action='store_true');a=p.parse_args();need(a.execution_authorized,'Author-only until root review and CPU evidence admission');build()
